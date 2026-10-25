#!/usr/bin/env python3
"""Check the pointers and mode names in the skill (skills/career-log/), docs/guide.md and the
Template's front page (tools/template/README*.md).

  python3 -I tools/skill_lint.py [<root>]

Fails (exit 1, one line per problem) when, in any .md file under skills/career-log/:
- a link points at a missing file or a missing #anchor;
- a `file.md › Section` reference names a section the file does not have (a heading, a bold-label
  bullet such as `- **Commits.**`, or a step title such as `7. **Check the draft**`);
- a `file.md step N` reference names a step the file does not have (`## N.` or `N. `);
- a mode name appears that is not in SKILL.md's modes table: a retired name anywhere, or any name
  in a mode context (`X` mode, **X** mode, modes/X.md). A line that names it as old ("older upskill
  reports") is allowed.
It also fails when tools/check.py's mode lists disagree with the skill: MODES is the modes table but
NO_CHECK (the modes with no Trigger check), and NEEDS's modes with playwright-cli, but setup (which
installs it) and browser (browser.md's own check), are the modes whose files link browser.md (a file
modes/<mode>-<part>.md counts for <mode>).
In docs/guide.md it also fails on a generated block that is stale or missing, or a bad row of the
flows table (`tools/guide.py check`; `tools/guide.py write` regenerates the blocks).
<root> defaults to the repo this script is in. Standard library only, Python 3.11+.

There is no list of problems to ignore: a new check that finds breaks fixes them in the same pull
request, or lands after the fix.
"""
import ast, os, re, sys

SKILL = "skills/career-log"

# Names of modes that were removed or renamed, flagged anywhere as a whole word. Add a mode's name
# here when it is removed. A name that is also an ordinary word (a removed `apply` mode) stays out:
# the mode-context check below still catches it.
RETIRED = ("upskill",)
# Modes that run no Trigger check (SKILL.md › Trigger check), so tools/check.py has no MODES entry
NO_CHECK = ("guide", "upgrade")

OLD = re.compile(r"\b(old|older|former|formerly|renamed|retired|removed)\b", re.I)
# Bare names of files that live outside the skill: the Log skeleton files in the Template, and the
# Engine files at the repo root.
SKELETON = ("direction.md", "profile.md", "stories.md", "applications.md", "README.md")
ROOT_FILES = ("SETUP.md", "AGENTS.md", "CLAUDE.md", "GLOSSARY.md")

LINK = re.compile(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)\)")
# A file name, bare, in backticks, or as a link, followed by › or by "step N"
FILE_TOKEN = r"(?:\[[^\]]*\]\((?P<href>[^)\s]+)\)|(?P<open>`)?(?P<name>(?:\.\./)*[A-Za-z0-9_][A-Za-z0-9_./-]*\.md)(?P<close>`)?)"
SECTION_REF = re.compile(FILE_TOKEN + r" › ")
LINKED_SECTION = re.compile(r"\[`?(?P<name>[A-Za-z0-9_./-]+\.md)`? › (?P<rest>[^\]]+)\]\((?P<href>[^)\s]+)\)")
STEP_REF = re.compile(FILE_TOKEN + r" step (?P<n>\d+)\b")
MODE_CONTEXT = [
    re.compile(r"(?:`|\*\*)([a-z][a-z-]*)(?:`|\*\*) modes?\b"),
    re.compile(r"\bmodes? (?:`|\*\*)([a-z][a-z-]*)(?:`|\*\*)"),
    re.compile(r"\bmodes/([a-z][a-z-]*)\.md\b"),
]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def slug(heading):
    """GitHub's anchor for a heading."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[*`\[\]_]", "", text)).strip().lower()


class Doc:
    """A Markdown file's headings, anchors, labels (headings, bold-label bullets, step titles) and steps."""

    def __init__(self, path):
        self.anchors, self.labels, self.steps = set(), set(), set()
        counts = {}
        fenced = False
        for line in read(path).splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for a in re.findall(r"<a (?:id|name)=\"([^\"]+)\"", line):
                self.anchors.add(a)
            h = re.match(r"#{1,6} +(.*?) *#*$", line)
            if h:
                text = h.group(1)
                base = slug(text)
                n = counts.get(base, 0)
                counts[base] = n + 1
                self.anchors.add(base if n == 0 else "%s-%d" % (base, n))
                self.labels.add(norm(text))
                s = re.match(r"(\d+)\.\s+(.*)", text)
                if s:
                    self.steps.add(int(s.group(1)))
                    self.labels.add(norm(s.group(2)))
                continue
            s = re.match(r"\s*(\d+)\.\s", line)
            if s:
                self.steps.add(int(s.group(1)))
            b = re.match(r"\s*(?:\d+\.|[-*])?\s*\*\*(.+?)\*\*", line)
            if b:
                self.labels.add(norm(b.group(1).rstrip(".:")))

    def has_label(self, text, exact=False):
        """Whether text names a label. Unless it is exact (the whole reference, as in a link's text
        or `file.md › Section`), text runs on into the sentence, so a label it starts with counts.
        Either way it may shorten a label: `What to emphasise` for `What to emphasise, by target`."""
        t = norm(text)
        if not t:
            return False

        def starts(a, b):
            return a.startswith(b) and (len(a) == len(b) or not a[len(b)].isalnum())

        return any(starts(l, t) or (not exact and starts(t, l)) for l in self.labels if l)


class Linter:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.skill = os.path.join(self.root, *SKILL.split("/"))
        self.docs = {}
        self.problems = []

    def doc(self, path):
        if path not in self.docs:
            self.docs[path] = Doc(path)
        return self.docs[path]

    def add(self, path, lineno, msg):
        self.problems.append((os.path.relpath(path, self.root).replace(os.sep, "/"), lineno, msg))

    def resolve_href(self, here, href, real=None):
        """The file a relative link points at, or None for links this lint does not check. A link
        from a file served at `here` but kept at `real` (tools/template/) may point at another file
        of the Template's skeleton, which the export overlays at the root."""
        if re.match(r"[a-z][a-z0-9+.-]*:", href, re.I) or "<" in href:
            return None
        path = href.split("#", 1)[0]
        if not path:
            return real or here
        p = os.path.normpath(os.path.join(os.path.dirname(here), *path.split("/")))
        if real and real != here:   # the skeleton's own file wins, as the export overlays it
            q = os.path.normpath(os.path.join(os.path.dirname(real), *path.split("/")))
            if os.path.exists(q):
                return q
        return p

    def resolve_name(self, here, name):
        """The file a bare name such as `direction.md` or `fit.md` means."""
        base = name.split("/")[-1]
        if "/" not in name.lstrip("./") and base in SKELETON:
            p = os.path.join(self.root, "tools", "template", base)
            if os.path.exists(p):
                return p
        if base in ROOT_FILES and "/" not in name.lstrip("./"):
            return os.path.join(self.root, base)
        for start in (os.path.dirname(here), self.skill, os.path.join(self.skill, "modes"), self.root):
            p = os.path.normpath(os.path.join(start, *name.split("/")))
            if os.path.exists(p):
                return p
        return None

    def target(self, here, path, lineno, m):
        if m.group("href"):
            return self.resolve_href(here, m.group("href"), path)
        p = self.resolve_name(here, m.group("name"))
        if p is None:
            self.add(path, lineno, "%s: no such file" % m.group("name"))
        return p

    def check_file(self, path, at=None):
        """Lint path; its links resolve from `at`, where the file is served (the Template's
        front page in tools/template/ sits at the root)."""
        here = at or path
        modes = self.modes
        fenced = False
        for lineno, line in enumerate(read(path).splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            # Links (not in code)
            if not fenced:
                prose = re.sub(r"`[^`]*`", "", line)
                for m in LINK.finditer(prose):
                    href = m.group(2)
                    p = self.resolve_href(here, href, path)
                    if p is None:
                        continue
                    if not os.path.exists(p):
                        self.add(path, lineno, "link %s: no such file" % href)
                        continue
                    if "#" in href and p.endswith(".md"):
                        anchor = href.split("#", 1)[1]
                        if anchor not in self.doc(p).anchors:
                            self.add(path, lineno, "link %s: no heading with that anchor" % href)
            # file.md › Section, written as a link: check its text against the file
            for m in LINKED_SECTION.finditer(line):
                p = self.resolve_href(here, m.group("href"), path)
                if p and os.path.exists(p) and p.endswith(".md") and not self.doc(p).has_label(m.group("rest"), exact=True):
                    self.add(path, lineno, "%s › %s: no such section" % (m.group("name"), m.group("rest")))
            # file.md › Section, bare or after a link
            # (a reference's text runs to the next reference on the line, or the line's end)
            text = LINKED_SECTION.sub(" ", line)
            refs = list(SECTION_REF.finditer(text))
            for i, m in enumerate(refs):
                p = self.target(here, path, lineno, m)
                if p and os.path.exists(p) and p.endswith(".md"):
                    rest = text[m.end():refs[i + 1].start() if i + 1 < len(refs) else len(text)]
                    exact = bool(m.group("open")) and not m.group("close")
                    if exact:
                        rest = rest.split("`", 1)[0]
                    if not self.doc(p).has_label(rest, exact):
                        shown = rest if exact else re.split(r"[.,;:()]\s", rest + " ", maxsplit=1)[0].strip()
                        self.add(path, lineno, "%s › %s: no such section" % (m.group("name") or m.group("href"), shown))
            # file.md step N
            for m in STEP_REF.finditer(line):
                p = self.target(here, path, lineno, m)
                if p and os.path.exists(p) and p.endswith(".md") and int(m.group("n")) not in self.doc(p).steps:
                    self.add(path, lineno, "%s step %s: no such step" % (m.group("name") or m.group("href"), m.group("n")))
            # Mode names
            if OLD.search(line):
                continue
            seen = set()
            for name in RETIRED:
                if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(name), line, re.I):
                    seen.add(name)
            for rx in MODE_CONTEXT:
                for name in rx.findall(line):
                    if name not in modes and name not in self.subfiles:
                        seen.add(name)
            for name in sorted(seen):
                self.add(path, lineno, "mode %s: not in SKILL.md's modes table" % name)

    def run(self):
        """The problems in the skill under the root, as (file, line, message)."""
        skill_md = os.path.join(self.skill, "SKILL.md")
        if not os.path.exists(skill_md):
            self.add(skill_md, 0, "missing")
            return self.problems
        table = re.search(r"^## Modes\n(.*?)(?=^## |\Z)", read(skill_md), re.M | re.S)
        self.modes = set(re.findall(r"^\| \*\*([a-z][a-z-]*)\*\* \|", table.group(1) if table else "", re.M))
        if not self.modes:
            self.add(skill_md, 0, "no modes table under ## Modes")
        # Files in modes/ that are parts of a mode (review.md, import-chats.md) may be linked
        modes_dir = os.path.join(self.skill, "modes")
        self.subfiles = {f[:-3] for f in os.listdir(modes_dir) if f.endswith(".md")} if os.path.isdir(modes_dir) else set()
        for d, dirs, files in os.walk(self.skill):
            dirs.sort()
            for f in sorted(files):
                if f.endswith(".md"):
                    self.check_file(os.path.join(d, f))
        # The guide and the Template's front page, where they exist: their links and references,
        # and the guide's generated blocks and flows table (tools/guide.py)
        for f in ("README.md", "README.zh-TW.md"):
            p = os.path.join(self.root, "tools", "template", f)
            if os.path.exists(p):
                self.check_file(p, at=os.path.join(self.root, f))
        self.check_mode_lists()
        guide_md = os.path.join(self.root, "docs", "guide.md")
        if os.path.exists(guide_md):
            self.check_file(guide_md)
            for f, n, msg in guide_module().problems(self.root):
                self.add(os.path.join(self.root, *f.split("/")), n, msg)
        return self.problems


    def check_mode_lists(self):
        """tools/check.py's MODES and NEEDS against the modes table and the files that link browser.md."""
        check_py = os.path.join(self.root, "tools", "check.py")
        if not self.modes or not os.path.exists(check_py):
            return
        found = {}
        for node in ast.parse(read(check_py)).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) in ("MODES", "NEEDS"):
                found[node.targets[0].id] = (node.lineno, ast.literal_eval(node.value))
        if set(found) != {"MODES", "NEEDS"}:
            self.add(check_py, 0, "no MODES or NEEDS literal to compare with the modes table")
            return
        line, modes = found["MODES"]
        want = self.modes - set(NO_CHECK)
        if set(modes) != want:
            self.add(check_py, line, "MODES differs from SKILL.md's modes table but %s: %s missing, %s extra"
                     % (", ".join(NO_CHECK), sorted(want - set(modes)) or "none", sorted(set(modes) - want) or "none"))
        line, needs = found["NEEDS"]
        browser = {m for m, tools in needs.items() if any(t == "playwright-cli" for t, _ in tools)} - {"setup", "browser"}
        linking = set()
        for f in sorted(self.subfiles):
            if re.search(r"\]\((?:\.\./)?browser\.md[#)]", read(os.path.join(self.skill, "modes", f + ".md"))):
                linking.add(max((m for m in self.modes if f == m or f.startswith(m + "-")), key=len, default=f))
        if browser != linking:
            self.add(check_py, line, "NEEDS's modes with playwright-cli differ from the modes whose files link browser.md:"
                     " %s only in NEEDS, %s only linking" % (sorted(browser - linking) or "none", sorted(linking - browser) or "none"))


def guide_module():
    """tools/guide.py beside this script: -I leaves this folder off sys.path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("guide", os.path.join(os.path.dirname(os.path.abspath(__file__)), "guide.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.rstrip())
        return 0
    root = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    problems = Linter(root).run()
    for f, n, msg in problems:
        print("%s:%d: %s" % (f, n, msg))
    if problems:
        print("skill lint: %d problem(s)" % len(problems))
        return 1
    print("skill lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
