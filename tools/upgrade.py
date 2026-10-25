#!/usr/bin/env python3
"""The upgrade mode's tool (skills/career-log/modes/upgrade.md): move a Log to a newer Template.

  python3 -I <tool> plan <root> [--to <version>] [--url <url>]    (Windows: py -3 -I <tool> ...)
  python3 -I <tool> engine <root> <version>
  python3 -I <tool> reapply <root> (<path>... | --all)
  python3 -I <tool> clean <root>

<tool> is the target version's copy, which the mode puts at <root>/.build/upgrade/tools/upgrade.py, so
the newest rules run whatever Engine the Log has. <root> is the Log's root. See docs/adr/0011.

plan: needs a clean working tree. Fetches the Template's release tags (--url, default the public
Template) into refs/career-log-upgrade/, reads the Log's version from tools/TEMPLATE_VERSION, and
writes the plan to <root>/.build/upgrade/state.json. It prints `from:`, `to:`, `start:` (the
commit to go back to), one `step: <version>` line per Engine replacement in order (a version whose
release has an upgrade guide, then the target), and the Engine files this Log changed since its
version: `edited:` (changed), `added:` (the Log's own file, kept), `removed:` (deleted),
`overwritten:` (the Log's own file at a path a step's release has: replaced), and `dropped:` (an
Engine file the target no longer has, which a step deletes). A Log
before 0.1.0 (no stamp, or a commit other than 0.1.0's) gets `stop:` and 0.1.0's guide in
.build/upgrade/.
engine: replaces the Engine paths with <version>'s (the next step of the plan): checks out its
files, deletes the Engine files it no longer has unless the Log added them, and puts this Log's
own .gitignore lines back under `# This Log's own lines`. A front page (README.md, README.zh-TW.md)
whose text above its entries heading is still the old Template's, unedited, gets <version>'s text
there, its entries section and the rest kept. It copies that version's guide and script to
.build/upgrade/ and prints `guide: <file>`, or `guide: none`.
reapply: after the last step, merges the `edited:` files given (or all of them, --all) back into the
new Engine: `git merge-file` with the Log's version at `start:`, the old Template's as the base,
and the new one. Prints `merged:`, `conflict: <path>: <n>` (markers left in the file) or
`review:` (the new version has no such file).
clean: deletes refs/career-log-upgrade/ and .build/upgrade/.

Exit 0 on success, 1 on a `stop:` or a conflict, 2 on a bad argument or a git error. Standard
library only, Python 3.11+.
"""
import json, os, re, shutil, subprocess, sys, tempfile

URL = "https://github.com/mileschintw/career-log-template.git"
REFS = "refs/career-log-upgrade/"
BUILD = os.path.join(".build", "upgrade")
EXPORT = "tools/export-template.sh"
STAMP = "tools/TEMPLATE_VERSION"
GITIGNORE = ".gitignore"
OWN_LINES = "# This Log's own lines"
SKELETON_ENGINE = [".github"]   # Engine paths the export takes from tools/template/, not ALLOW
# Before semver, the stamp held the exported commit; 0.1.0's is the only one that names a release
STAMPS = {"e6a5565a4807db1ab30b0eb70f8c2fd1421ac4df": "0.1.0"}
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
GUIDE = "docs/upgrades/upgrade-%s.%s"
# The front pages, with the heading of their entries section (tools/config.py reads above it)
PAGES = {"README.md": "Entries", "README.zh-TW.md": "條目"}


class UpgradeError(Exception):
    pass


def git(root, *args, check=True, binary=False):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True)
    if check and r.returncode != 0:
        raise UpgradeError("git %s: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def key(version):
    return tuple(int(n) for n in SEMVER.match(version).groups())


def ref(version):
    return REFS + "v" + version


def show(root, rev, path):
    """A file's bytes at rev, or None when rev has no such file."""
    r = subprocess.run(["git", "-C", root, "show", "%s:%s" % (rev, path)], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def engine_paths(root, rev):
    """The Engine paths of the tree at rev: its export's ALLOW list, plus the skeleton's."""
    text = show(root, rev, EXPORT)
    m = re.search(rb'^ALLOW="([^"]*)"', text or b"", re.M)
    if not m:
        raise UpgradeError("no ALLOW=\"...\" line in %s at %s" % (EXPORT, rev))
    return m.group(1).decode().split() + SKELETON_ENGINE


def files(root, rev, paths):
    return set(git(root, "ls-tree", "-r", "--name-only", rev, "--", *paths).splitlines())


def stamped(root):
    """The Log's version from tools/TEMPLATE_VERSION: a semver, `next`, or None (before 0.1.0)."""
    path = os.path.join(root, *STAMP.split("/"))
    try:
        with open(path, encoding="utf-8-sig") as f:   # -sig: a stamp saved with a BOM
            first = (f.readline().strip() or "")
    except OSError:
        return None, "no " + STAMP
    if SEMVER.match(first) or first == "next":
        return first, first
    return STAMPS.get(first), first or "an empty " + STAMP


def gitignore_lines(text):
    return [l for l in text.decode("utf-8", "replace").splitlines()]


def own_gitignore(root, base):
    """This Log's .gitignore lines that the Template at base did not have, in order."""
    ours = show(root, "HEAD", GITIGNORE) or b""
    theirs = set(l.strip() for l in gitignore_lines(show(root, base, GITIGNORE) or b""))
    return [l for l in gitignore_lines(ours) if l.strip() and l.strip() not in theirs and l.strip() != OWN_LINES]


def split_page(data, heading):
    """A front page's text as (above `## <heading>`, the rest), LF line ends; None when the page or
    the heading is missing."""
    if data is None:
        return None
    text = data.decode("utf-8", "replace").lstrip("\ufeff").replace("\r\n", "\n")
    m = re.search(r"^## %s[ \t]*$" % re.escape(heading), text, re.M)
    return (text[:m.start()], text[m.start():]) if m else None


def unedited_pages(root):
    """{front page: (above its entries heading, the rest)} for each page whose text above that heading
    is the Template's at HEAD."""
    out = {}
    for rel, heading in PAGES.items():
        mine = split_page(show(root, "HEAD", rel), heading)
        theirs = split_page(show(root, "HEAD", "tools/template/" + rel), heading)
        if mine and theirs and mine[0] == theirs[0]:
            out[rel] = mine
    return out


def update_pages(root, pages, version):
    """Give each unedited front page version's text above its entries heading, keeping the rest and
    the working tree's line ends."""
    lines = []
    for rel, (head, rest) in pages.items():
        new = split_page(show(root, ref(version), "tools/template/" + rel), PAGES[rel])
        if not new or new[0] == head:
            continue
        dest = os.path.join(root, *rel.split("/"))
        with open(dest, "rb") as f:
            crlf = b"\r\n" in f.read()
        out = (new[0] + rest).encode("utf-8")
        with open(dest, "wb") as f:
            f.write(out.replace(b"\n", b"\r\n") if crlf else out)
        lines.append("done: %s above `## %s`: the Template's page, unedited, now %s's" % (rel, PAGES[rel], version))
    return lines


def state_path(root):
    return os.path.join(root, BUILD, "state.json")


def load(root):
    try:
        with open(state_path(root), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        raise UpgradeError("no plan in %s: run plan first" % state_path(root))


def save(root, state):
    os.makedirs(os.path.join(root, BUILD), exist_ok=True)
    with open(state_path(root), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)


def copy_guide(root, target, version):
    """Copy <version>'s guide and script, as the target release has them, into .build/upgrade/."""
    out = []
    for ext in ("md", "py"):
        data = show(root, ref(target), GUIDE % (version, ext))
        if data is not None:
            dest = os.path.join(root, BUILD, "upgrade-%s.%s" % (version, ext))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            out.append(dest)
    return out


def plan(root, to=None, url=URL):
    lines = []
    dirty = git(root, "status", "--porcelain").splitlines()
    if dirty:
        return 1, ["stop: uncommitted changes; commit or discard them first:"] + ["  " + l for l in dirty]
    git(root, "fetch", "--no-tags", "--quiet", url, "+refs/tags/v*:%sv*" % REFS)
    tags = sorted((r[len(REFS) + 1:] for r in git(root, "for-each-ref", "--format=%(refname)", REFS).splitlines()
                   if SEMVER.match(r[len(REFS) + 1:])), key=key)
    if not tags:
        return 1, ["stop: no release tags at %s" % url]
    target = to or tags[-1]
    if target not in tags:
        return 1, ["stop: no release v%s at %s; releases: %s" % (target, url, ", ".join(tags))]
    version, seen = stamped(root)
    if version == "next":
        return 1, ["stop: %s says next, an unreleased build: there is no release to upgrade from" % STAMP]
    if version is None:
        copied = copy_guide(root, target, "0.1.0")
        if not copied:
            return 1, ["stop: this Log is from before 0.1.0 (%s), and v%s has no 0.1.0 guide" % (seen, target)]
        return 1, ["stop: this Log is from before 0.1.0 (%s): follow %s first, then run this mode again"
                   % (seen, copied[0].replace(os.sep, "/"))]
    if version not in tags:
        return 1, ["stop: this Log's version %s has no release tag at %s" % (version, url)]
    if key(target) <= key(version):
        return 0, ["OK: this Log is at %s, the target is %s: nothing to upgrade" % (version, target)]
    between = [v for v in tags if key(version) < key(v) <= key(target)]
    steps = [v for v in between if v != target and show(root, ref(target), GUIDE % (v, "md")) is not None] + [target]
    base = ref(version)
    # the Engine paths of both ends: a path can join the Engine, or move out of its ALLOW list
    paths = sorted(set(engine_paths(root, base)) | set(engine_paths(root, ref(target))))
    changed = {"edited": [], "added": [], "removed": [], "overwritten": [], "dropped": []}
    # --raw names both blobs: a file whose content is the release's (only its mode changed, as a
    # Windows clone can do) is not an edit
    for line in git(root, "diff", "--raw", "--no-renames", "--abbrev=40", base, "HEAD", "--", *paths).splitlines():
        meta, path = line.split("\t", 1)
        _, _, old, new, status = meta.split()
        if path in (GITIGNORE, STAMP) or old == new:
            continue
        kind = {"M": "edited", "A": "added", "D": "removed"}.get(status[0], "edited")
        if kind == "added" and any(show(root, ref(v), path) is not None for v in steps):
            kind = "overwritten"   # the Log's own file at a path a step's release has
        changed[kind].append(path)
    # the Engine files the target no longer has, which the steps delete (an edited one too)
    target_files = files(root, ref(target), paths)
    changed["dropped"] = sorted(p for p in files(root, base, paths) & files(root, "HEAD", paths)
                                if p not in target_files)
    start = git(root, "rev-parse", "HEAD").strip()
    save(root, {"url": url, "from": version, "to": target, "start": start, "steps": steps, "done": [],
                "gitignore": own_gitignore(root, base), **changed})
    lines += ["from: " + version, "to: " + target, "start: " + start]
    lines += ["step: " + v for v in steps]
    for kind in ("edited", "added", "removed", "overwritten", "dropped"):
        lines += ["%s: %s" % (kind, p) for p in changed[kind]]
    return 0, lines


def engine(root, version):
    state = load(root)
    left = [v for v in state["steps"] if v not in state["done"]]
    if not left or left[0] != version:
        return 1, ["stop: the next step of the plan is %s, not %s" % (left[0] if left else "none", version)]
    dirty = git(root, "status", "--porcelain").splitlines()
    if dirty:
        return 1, ["stop: uncommitted changes; commit the step before this one, or settle them as for plan: %s"
                   % ", ".join(l[3:] for l in dirty)]
    new = ref(version)
    paths_new = engine_paths(root, new)
    paths = sorted(set(paths_new) | set(engine_paths(root, "HEAD")))
    keep = set(state["added"])
    have = files(root, new, paths)
    gone = sorted(p for p in files(root, "HEAD", paths) if p not in have and p not in keep)
    lines = []
    if gone:
        git(root, "rm", "-q", "--ignore-unmatch", "--", *gone)
        lines += ["done: deleted %s (not in %s)" % (p, version) for p in gone]
    present = [p for p in paths_new if files(root, new, [p])]
    pages = unedited_pages(root)
    git(root, "checkout", new, "--", *present)
    lines.append("done: Engine paths from %s" % version)
    lines += update_pages(root, pages, version)
    own = state["gitignore"]
    if own and os.path.exists(os.path.join(root, GITIGNORE)):
        path = os.path.join(root, GITIGNORE)
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        there = set(l.strip() for l in text.splitlines())
        add = [l for l in own if l.strip() not in there]
        if add:
            nl = "\r\n" if "\r\n" in text else "\n"
            head = [] if OWN_LINES in there else ["", OWN_LINES]
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text.rstrip("\r\n") + nl + nl.join(head + add) + nl)
            lines.append("done: %d of this Log's own lines back in .gitignore" % len(add))
    copied = [c for c in copy_guide(root, state["to"], version) if c.endswith(".md")]
    lines.append("guide: " + (copied[0].replace(os.sep, "/") if copied else "none"))
    state["done"].append(version)
    save(root, state)
    return 0, lines


def reapply(root, only=()):
    state = load(root)
    if [v for v in state["steps"] if v not in state["done"]]:
        return 1, ["stop: run every step first: %s" % ", ".join(v for v in state["steps"] if v not in state["done"])]
    todo = state["edited"] if only == ["--all"] else list(only)
    unknown = [p for p in todo if p not in state["edited"]]
    if unknown:
        return 2, ["usage: not an edited file of the plan: %s" % ", ".join(unknown)]
    lines, rc = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for path in todo:
            dest = os.path.join(root, *path.split("/"))
            if not os.path.exists(dest):
                lines.append("review: %s: %s has no such file; this Log's version is `git show %s:%s`"
                             % (path, state["to"], state["start"][:12], path))
                continue
            # all three from git, so all have the repo's line ends; the result gets the working tree's
            parts = []
            for name, data in (("ours", show(root, state["start"], path)), ("base", show(root, ref(state["from"]), path) or b""),
                               ("theirs", show(root, "HEAD", path) or b"")):
                p = os.path.join(tmp, name)
                with open(p, "wb") as f:
                    f.write(data)
                parts.append(p)
            r = subprocess.run(["git", "merge-file", "-p", "-L", "this Log", "-L", state["from"], "-L", state["to"],
                                *parts], capture_output=True)
            if r.returncode < 0 or r.returncode > 127:
                raise UpgradeError("git merge-file %s: %s" % (path, r.stderr.decode("utf-8", "replace").strip()))
            with open(dest, "rb") as f:
                crlf = b"\r\n" in f.read()
            out = r.stdout.replace(b"\r\n", b"\n")
            with open(dest, "wb") as f:
                f.write(out.replace(b"\n", b"\r\n") if crlf else out)
            if r.returncode:
                lines.append("conflict: %s: %d" % (path, r.returncode))
                rc = 1
            else:
                lines.append("merged: " + path)
    return rc, lines


def clean(root):
    for r in git(root, "for-each-ref", "--format=%(refname)", REFS).splitlines():
        git(root, "update-ref", "-d", r)
    shutil.rmtree(os.path.join(root, BUILD), ignore_errors=True)
    return 0, ["done: removed %s and %s" % (REFS, BUILD.replace(os.sep, "/"))]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):   # a front page's heading (`## 條目`), whatever the code page
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    args, opts = [], {}
    it = iter(argv)
    for a in it:
        if a in ("--to", "--url"):
            opts[a] = next(it, None)
            if opts[a] is None:
                args = []
                break
        else:
            args.append(a)
    usage = __doc__.split("\n\n")[1]
    if len(args) < 2 or args[0] not in ("plan", "engine", "reapply", "clean"):
        print(usage)
        return 2
    cmd, root, rest = args[0], args[1], args[2:]
    if (opts and cmd != "plan") or (cmd == "engine" and len(rest) != 1) or (cmd in ("plan", "clean") and rest) \
            or (cmd == "reapply" and (not rest or ("--all" in rest and len(rest) > 1))):
        print(usage)
        return 2
    if "--to" in opts and not SEMVER.match(opts["--to"].lstrip("v")):
        print("usage: --to takes a version such as 0.2.0")
        return 2
    try:
        root = git(root, "rev-parse", "--show-toplevel").strip()
        if cmd == "plan":
            rc, lines = plan(root, (opts.get("--to") or "").lstrip("v") or None, opts.get("--url") or URL)
        elif cmd == "engine":
            rc, lines = engine(root, rest[0].lstrip("v"))
        elif cmd == "reapply":
            rc, lines = reapply(root, [p.replace("\\", "/") for p in rest])
        else:
            rc, lines = clean(root)
    except UpgradeError as e:
        print("error: %s" % e)
        return 2
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
