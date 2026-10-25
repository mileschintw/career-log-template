#!/usr/bin/env python3
"""Find what a Log still has in the formats of 0.1.0, and fix what is mechanical.

  python3 -I upgrade-0.2.0.py <root> [--apply]      (Windows: py -3 -I ...)

<root> is the Log's root. The guide that goes with this script, upgrade-0.2.0.md, says what to do
with each line. Without --apply it only reads and prints. Each line starts with its kind:

  apply:   --apply changes it
  migrate: the agent changes it by hand as the guide says, with nothing to ask
  ask:     the user decides, in the guide's question round
  review:  show it to the user once in that round; keeping it as it is is an answer too
  later:   waits for a later mode; nothing to do now
  done:    --apply changed it, in the working tree only (nothing is staged or committed)

Each check in CHECKS is a function (log root, apply) returning (kind, text) pairs; a pull request
that changes a Log format adds its check here and its step to the guide.

Exit 0 with `OK: nothing left to migrate` when no apply, migrate or ask line is left, 1 otherwise,
2 on a bad argument. Standard library only, Python 3.11+.
"""
import os, re, subprocess, sys


def check_readme_order(root, apply):
    """README.md's Entries table in the order `entries.py readme-sort` gives (#292)."""
    tool = os.path.join(root, "tools", "entries.py")
    args = [sys.executable, "-I", tool, "readme-sort", "--root", root]
    p = subprocess.run(args + ([] if apply else ["--check"]), capture_output=True, encoding="utf-8", errors="replace")
    out = p.stdout.strip()
    if p.returncode == 2:
        return [("migrate", "README.md: tools/entries.py readme-sort cannot read it: %s" % out.splitlines()[0])]
    if apply and p.returncode == 0 and out.startswith("sorted:"):
        return [("done", "README.md: Entries table %s" % out)]
    if p.returncode == 1:
        return [("apply", "README.md: Entries table not in order (%d rows move)" % len(out.splitlines()))]
    return []


def check_direction(root, apply):
    """direction.md holds each section `tools/config.py` reads a Direction item from (#299): its
    `direction <item>: unreadable (...)` lines, which `show` prints with or without config.toml."""
    tool = os.path.join(root, "tools", "config.py")
    p = subprocess.run([sys.executable, "-I", tool, "show", "--root", root],
                       capture_output=True, encoding="utf-8", errors="replace")
    if p.returncode not in (0, 1) or not any(l.startswith("direction ") for l in p.stdout.splitlines()):
        said = (p.stderr.strip() or p.stdout.strip() or "no output").splitlines()[-1]
        return [("migrate", "direction.md: tools/config.py show failed: %s" % said)]
    why = {}
    for line in p.stdout.splitlines():
        m = re.match(r"direction (.+?): unreadable \((.*)\)$", line)
        if m:
            why.setdefault(m.group(2), []).append(m.group(1))
    return [("migrate", "direction.md: tools/config.py cannot read %s: %s" % (", ".join(items), reason))
            for reason, items in why.items()]


def check_visa_sponsorship(root, apply):
    """A need for visa sponsorship (or OPT or CPT, #377) that direction.md says in the user's own words,
    with no `**Visa sponsorship needed:**` line for the tools to read (#284): `tools/config.py show`'s
    work authorisation and other hard constraints lines (a `**Visa:**` line is one of those) while visa
    sponsorship is empty."""
    tool = os.path.join(root, "tools", "config.py")
    p = subprocess.run([sys.executable, "-I", tool, "show", "--root", root],
                       capture_output=True, encoding="utf-8", errors="replace")
    lines = p.stdout.splitlines()
    if "direction visa sponsorship: empty" not in lines:
        if not any(l.startswith("direction visa sponsorship: **") for l in lines):
            return []   # check_direction's migrate: line says why it cannot be read
        # set: its value must be one the tools read, or every lookup refuses
        q = subprocess.run([sys.executable, "-I", os.path.join(root, "tools", "sponsorship.py"), "need", "--root", root,
                            "check"], capture_output=True, encoding="utf-8", errors="replace")
        if q.returncode == 1:
            return [("migrate", "direction.md: its Visa sponsorship needed line cannot be read: %s"
                     % (q.stdout.strip() or q.stderr.strip() or "no output").splitlines()[-1])]
        return []
    out = []
    for line in lines:
        m = re.match(r"direction (?:work authorisation|other hard constraints): (.*)$", line)
        if m and re.search(r"sponsor|\bvisa\b|\bh-?1b\b|green card|\bperm\b|(?-i:\bOPT\b|\bCPT\b)", m.group(1), re.I) \
                and not re.search(r"\b(?:no|not|without|never)\b[^.;]*\b(?:sponsor|visa)|n't need|\bholder\b"
                                  r"|permanent resident", m.group(1), re.I):
            out.append(("review", "direction.md: `%s` speaks of visa sponsorship, and no **Visa sponsorship needed:**"
                                  " line says which" % m.group(1).strip()))
    return out


TEXT_UPDATES = [   # (file, a line only 0.1.0's Template had, 0.2.0's line)
    ("sources/keys.md",
     "Short citations for material imported into this log. The generic forms (`sources/resumes/<file>`, `<repo>@<sha>:<path>:<line>`) are in [SKILL.md › Source keys](../skills/career-log/SKILL.md#source-keys). Add a row whenever a new source folder or a new chat extract appears; session excerpts in `sources/<agent>/` need none.",
     "Short citations for material imported into this log. The generic forms (`sources/resumes/<file>`, `<repo>@<sha>:<path>:<line>`) are in [SKILL.md › Source keys](../skills/career-log/SKILL.md#source-keys). Add a row whenever a new source folder appears (`tools/chat_export.py extract --keys` writes a chat extract's); session excerpts in `sources/<agent>/` need none."),
]


def check_text_updates(root, apply):
    """A line of a Template file still as 0.1.0 wrote it, which 0.2.0 reworded (TEXT_UPDATES,
    #387): a line the user edited is no longer 0.1.0's, and stays. The file keeps its line endings."""
    out = []
    for rel in dict.fromkeys(f for f, _, _ in TEXT_UPDATES):
        path = os.path.join(root, *rel.split("/"))
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            continue
        lines = raw.decode("utf-8", errors="surrogateescape").split("\n")
        changed = False
        for _, old, new in (u for u in TEXT_UPDATES if u[0] == rel):
            for i, line in enumerate(lines):
                if line.rstrip() == old:
                    if apply:
                        lines[i] = new + line[len(old):]   # its \r and trailing spaces stay
                        changed = True
                        out.append(("done", "%s: line %d updated to 0.2.0's Template text" % (rel, i + 1)))
                    else:
                        out.append(("apply", "%s: line %d is 0.1.0's Template text `%s…`, which 0.2.0 rewords"
                                    % (rel, i + 1, old[:40])))
        if changed:
            with open(path, "wb") as f:
                f.write("\n".join(lines).encode("utf-8", errors="surrogateescape"))
    return out


# Each check goes into this list itself: the export reads `CHECKS = []` as no change.
CHECKS = [check_readme_order, check_direction, check_visa_sponsorship, check_text_updates]
BLOCKING = ("apply", "migrate", "ask")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    apply = "--apply" in argv
    rest = [a for a in argv if a != "--apply"]
    if len(rest) != 1 or not os.path.isdir(os.path.join(rest[0], ".git")):
        print("usage: upgrade-0.2.0.py <root> [--apply], <root> a Log's git checkout")
        return 2
    lines = [line for check in CHECKS for line in check(rest[0], apply)]
    for kind, text in lines:
        print("%s: %s" % (kind, text))
    if apply:   # every apply ends with a fresh check
        lines = [line for check in CHECKS for line in check(rest[0], False)]
        for kind, text in lines:
            print("%s: %s" % (kind, text))
    if any(kind in BLOCKING for kind, _ in lines):
        return 1
    print("OK: nothing left to migrate")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
