#!/usr/bin/env python3
"""Tests for tools/checks_for.py: the checks it prints for typical changes, the changed paths it
reads from git, and, in the Template's source, that each workflow in .github/workflows/ runs on
the same `paths:` and the same steps as its group in GROUPS (skipped in a Template, which has none).

  python3 -I tools/tests/test_checks_for.py

The parity test compares the steps that run a test or a script: `python -I <script>`,
`sh -n <script>`, the PowerShell parse of `Resolve-Path <script>`, and tools/export-template.sh,
and fails on a run: line naming python, sh or the like in any other form, and on a path filter
other than `paths:` under `pull_request:`.
"""
import importlib.util, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
WORKFLOWS = os.path.join(REPO, ".github", "workflows")
NO_PATHS = {"closing-refs.yml"}   # runs on every pull request with a closing keyword, not on paths

spec = importlib.util.spec_from_file_location("checks_for", os.path.join(TOOLS, "checks_for.py"))
checks_for = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks_for)

STEP = re.compile(r"(?:python3?|py -3) -I (\S+\.py)|sh -n (\S+)|Resolve-Path (\S+?)\)|(?:ba)?sh (tools/export-template\.sh)")


def runs(paths):
    """The run: and do: lines for paths, against this repo."""
    return [l for l in checks_for.report(paths, REPO) if l.startswith(("run: ", "do: "))]


def scripts(lines):
    return [next(g for g in m.groups() if g) for l in lines for m in STEP.finditer(l)]


def indent(line):
    return len(line) - len(line.lstrip())


def workflow_paths(text):
    """The `paths:` list under `pull_request:`, or None; and the other path filters (paths: under
    another trigger, paths-ignore:), which the parity test does not read."""
    out, others, trigger = None, [], None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s+)([\w-]+):\s*$", line)
        if m and indent(line) == 2:
            trigger = m.group(2)
        if re.match(r"^\s+(paths|paths-ignore):", line):
            if trigger != "pull_request" or not re.match(r"^\s+paths:\s*$", line):
                others.append(line.strip())
                continue
            out = []
            for item in lines[i + 1:]:
                if item.lstrip().startswith("#"):
                    continue
                m = re.match(r"""^\s+-\s+["']?([^"'#]+?)["']?\s*$""", item)
                if not m:
                    break
                out.append(m.group(1))
    return out, others


def run_lines(text):
    """Every command line of the workflow's `run:` steps, a block's lines one by one."""
    out, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s+)(?:- )?run:\s*(.*)$", line)
        if not m:
            continue
        if m.group(2) not in ("|", ">", "|-", ">-"):
            out.append(m.group(2))
            continue
        for item in lines[i + 1:]:
            if item.strip() and indent(item) <= indent(line):
                break
            if item.strip():
                out.append(item.strip())
    return out


def workflow_steps(text):
    """The scripts the run: steps run, and the lines that look like a check STEP does not read."""
    found, unread = set(), []
    for cmd in (c.strip() for line in run_lines(text) for c in re.split(r"&&|\|\||;", line)):
        got = scripts([cmd])
        found.update(got)
        if not got and re.search(r"\b(python3?|py|pytest|unittest|sh|bash|pwsh)\b", cmd):
            unread.append(cmd)
    return sorted(found), unread


def as_globs(triggers):
    return sorted(t + "**" if t.endswith("/") else t for t in triggers)


def compare(group, name, text, root=REPO):
    """Problems between a group and its workflow's text; [] when they agree."""
    problems = []
    want = as_globs(checks_for.triggers(group, root))
    got, others = workflow_paths(text)
    problems += ["%s: a path filter the map cannot hold: %s" % (name, o) for o in others]
    if got is None:
        return problems + ["%s: no paths: list under pull_request:" % name]
    for p in sorted(set(want) - set(got)):
        problems.append("%s: paths: lacks %s (group %s has it)" % (name, p, group[0]))
    for p in sorted(set(got) - set(want)):
        problems.append("%s: paths: has %s (group %s lacks it)" % (name, p, group[0]))
    mine = sorted(set([c[1] for c in group[3] if c[0] == "py"]
                      + scripts([c[1] for c in group[3] if c[0] in ("sh", "ps")])))
    steps, unread = workflow_steps(text)
    if steps != mine:
        problems.append("%s: runs %s, group %s runs %s" % (name, steps, group[0], mine))
    problems += ["%s: a step the parity test cannot read: %s" % (name, u) for u in unread]
    return problems


class Typical(unittest.TestCase):
    """The checks for typical changes, as SETUP.md step 7 lists them."""

    def test_one_mode_file(self):
        self.assertEqual(scripts(runs(["skills/career-log/modes/fit.md"])),
                         ["tools/export-template.sh", "tools/tests/test_guide.py",
                          "tools/tests/test_skill_lint.py", "tools/skill_lint.py"])

    def test_modes_the_grader_reads(self):
        got = scripts(runs(["skills/career-log/modes/scan.md"]))
        self.assertIn("tools/tests/test_check_run.py", got)
        self.assertIn("tools/skill_lint.py", got)

    def test_scan(self):
        self.assertEqual(scripts(runs(["tools/scan.py"])),
                         ["tools/export-template.sh", "tools/tests/test_scan.py", "tools/tests/test_fit.py",
                          "tools/tests/test_dashboard.py"])

    def test_entries(self):
        # tools/logfiles.py is imported by every tool tools/entries.py is, and by tools/sync.py and
        # tools/config.py (which test_guide.py and test_upgrade.py load too), tools/resume.py and tools/chat_export.py
        # (which test_perplexity.py loads)
        both = ["tools/export-template.sh", "tools/tests/test_chat_export.py", "tools/tests/test_check_run.py",
                "tools/tests/test_check_save.py", "tools/tests/test_deny_coverage.py", "tools/tests/test_logfiles.py",
                "tools/tests/test_entries.py"]
        self.assertEqual(scripts(runs(["tools/entries.py"])), both + [
            "tools/tests/test_check.py", "tools/setup.sh", "tools/setup.ps1", "tools/tests/test_scan.py",
            "tools/tests/test_fit.py", "tools/tests/test_dashboard.py", "tools/tests/test_writing_lint.py",
            "tools/tests/test_application.py"])
        self.assertEqual(scripts(runs(["tools/logfiles.py"])), both + [
            "tools/tests/test_config.py", "tools/tests/test_check.py", "tools/setup.sh", "tools/setup.ps1",
            "tools/tests/test_resume.py", "tools/tests/test_guide.py", "tools/tests/test_skill_lint.py", "tools/skill_lint.py", "tools/tests/test_scan.py",
            "tools/tests/test_fit.py", "tools/tests/test_dashboard.py", "tools/tests/test_sponsorship.py", "tools/tests/test_perplexity.py",
            "tools/tests/test_upgrade.py", "maintainer/tests/test_harness.py",
            "tools/tests/test_writing_lint.py", "tools/tests/test_application.py",
            "tools/tests/test_sync.py"])

    def test_writing_md(self):
        # tools/writing_lint.py reads its word lists from writing.md
        self.assertIn("tools/tests/test_writing_lint.py", scripts(runs(["skills/career-log/writing.md"])))

    def test_template_front_page(self):
        lines = checks_for.report(["tools/template/README.md"], REPO)
        self.assertTrue(any(l.startswith("warn: tools/template/README.md changed but tools/template/README.zh-TW.md")
                            for l in lines))
        self.assertIn("tools/skill_lint.py", scripts(lines))
        both = checks_for.report(list(checks_for.FRONT_PAGES), REPO)
        self.assertFalse(any(l.startswith("warn:") for l in both))

    def test_setup_script(self):
        got = runs(["tools/setup.ps1"])
        self.assertTrue(any(l.startswith("do: run SETUP.md step 5") for l in got))
        self.assertIn("tools/setup.ps1", scripts(got))

    def test_resume(self):
        got = runs(["tools/resume.py"])
        self.assertIn("tools/tests/test_resume.py", scripts(got))
        self.assertIn("tools/tests/test_check.py", scripts(got))
        self.assertIn("tools/tests/test_check_save.py", scripts(got))
        self.assertIn("tools/tests/test_resume.py", scripts(runs(["skills/career-log/examples/resume.tex"])))

    def test_each_command_once_with_its_check(self):
        lines = checks_for.report(["tools/config.py", "tools/check.py"], REPO)
        self.assertEqual(sum(1 for l in lines if l.startswith("run: ") and "test_check.py" in l), 1)
        for i, l in enumerate(lines):
            if l.startswith("run: "):
                self.assertTrue(lines[i + 1].startswith("check: "), lines[i:i + 2])

    def test_guide_write_hint(self):
        lines = checks_for.report(["docs/guide.md"], REPO)
        self.assertTrue(any("tools/guide.py write" in l for l in lines if l.startswith("check: ")))

    def test_nothing_matches(self):
        self.assertEqual(checks_for.report(["profile.md"], REPO), ["not engine: profile.md", "run: none (no check covers these paths)"])


class Kinds(unittest.TestCase):
    """On a root built like the Template's source: the export script, ALLOW's folders, maintainer/."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for d in ("tools", "skills", "docs/adr", "maintainer"):
            os.makedirs(os.path.join(self.root, d))
        shutil.copy(os.path.join(TOOLS, "export-template.sh"), os.path.join(self.root, "tools"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_kinds(self):
        for path, want in [("tools/entries.py", "engine"), ("docs/guide.md", "engine"),
                           ("docs/social-preview/banner.svg", "engine"), ("docs/social-preview/x.png", "not engine"),
                           (".export-allow", "engine"), ("maintainer/readiness.py", "engine"),
                           ("docs/maintaining-tests.md", "engine"), (".github/workflows/x.yml", "engine"),
                           (".export-deny", "guard"), (".export-cleared", "guard"),
                           ("docs/coordination/plan.md", "coordination"), ("entries/2024-01-x.md", "not engine"),
                           ("entries/_template.md", "engine")]:
            self.assertEqual(checks_for.kind(path, self.root), want, path)

    def test_allow_read_from_the_export(self):
        self.assertIn("docs/guide.md", checks_for.allow(self.root))
        self.assertIn("skills/", checks_for.export_triggers(self.root))


class InATemplate(unittest.TestCase):
    """A root without maintainer/ leaves its checks out; a root without ALLOW is an error."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "tools", "tests"))
        shutil.copy(os.path.join(TOOLS, "export-template.sh"), os.path.join(self.root, "tools"))
        open(os.path.join(self.root, "tools", "tests", "test_entries.py"), "w").close()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_missing_script_left_out(self):
        lines = checks_for.report(["maintainer/readiness.py", "tools/tests/test_entries.py"], self.root)
        self.assertFalse(any("test_readiness" in l for l in lines))
        self.assertTrue(any("test_entries.py" in l for l in lines if l.startswith("run: ")))

    def test_source_only_engine_paths(self):
        self.assertEqual(checks_for.kind("maintainer/readiness.py", self.root), "not engine")
        self.assertEqual(checks_for.kind(".github/workflows/x.yml", self.root), "not engine")

    def test_no_allow(self):
        with open(os.path.join(self.root, "tools", "export-template.sh"), "w") as f:
            f.write("#!/bin/sh\n")
        with self.assertRaises(checks_for.ChecksError):
            checks_for.report(["tools/x.py"], self.root)


class FromGit(unittest.TestCase):
    def git(self, *args):
        subprocess.run(["git", "-C", self.root] + list(args), check=True, capture_output=True)

    def write(self, rel, text="x\n"):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("tools/old.py")
        self.write("tools/staged.py")
        self.write("tools/edited.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_committed_staged_unstaged_untracked_and_renamed(self):
        self.git("mv", "tools/old.py", "tools/new.py")
        self.git("commit", "-qm", "rename")
        self.write("tools/staged.py", "y\n")
        self.git("add", "tools/staged.py")
        self.write("tools/edited.py", "y\n")
        self.write("tools/untracked dir/file.py")
        self.assertEqual(checks_for.changed(self.root, "HEAD~1"),
                         ["tools/edited.py", "tools/new.py", "tools/old.py", "tools/staged.py",
                          "tools/untracked dir/file.py"])

    def test_bad_base(self):
        with self.assertRaises(checks_for.ChecksError):
            checks_for.changed(self.root, "no-such-ref")

    def test_cli(self):
        p = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "checks_for.py"), "--paths", "tools/scan.py"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("engine: tools/scan.py", p.stdout)
        p = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "checks_for.py")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        p = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "checks_for.py"), "--paths", "./tools/scan.py",
                            "entries/2024-\u00e9.md"], capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = p.stdout.decode("utf-8")
        self.assertIn("engine: tools/scan.py", out)
        self.assertIn("not engine: entries/2024-\u00e9.md", out)
        p = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "checks_for.py"), "--help"], capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_absolute_paths(self):
        self.assertEqual(checks_for.relative(os.path.join(REPO, "tools", "scan.py"), REPO), "tools/scan.py")
        with self.assertRaises(checks_for.ChecksError):
            checks_for.relative(os.path.dirname(REPO), REPO)


@unittest.skipUnless(os.path.isdir(WORKFLOWS), "no .github/workflows/ (a Template)")
class Parity(unittest.TestCase):
    def test_every_workflow_matches_its_group(self):
        groups = {g[1]: g for g in checks_for.GROUPS if g[1]}
        problems = []
        for name in sorted(os.listdir(WORKFLOWS)):
            if not name.endswith(".yml") or name in NO_PATHS:
                continue
            with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
                text = f.read()
            if name not in groups:
                problems.append("%s: no group in tools/checks_for.py GROUPS" % name)
                continue
            problems += compare(groups.pop(name), name, text)
        problems += ["group %s: no .github/workflows/%s" % (g[0], name) for name, g in groups.items()]
        self.assertEqual(problems, [])

    def test_a_changed_workflow_fails(self):
        name = "scan-tests.yml"
        with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
            text = f.read()
        group = next(g for g in checks_for.GROUPS if g[1] == name)
        self.assertEqual(compare(group, name, text), [])
        dropped = text.replace('      - "tools/entries.py"\n', "")
        self.assertEqual(compare(group, name, dropped), ["scan-tests.yml: paths: lacks tools/entries.py (group scan has it)"])
        added = text.replace('      - "tools/scan.py"\n', '      - "tools/scan.py"\n      - "tools/x.py"\n')
        self.assertEqual(compare(group, name, added), ["scan-tests.yml: paths: has tools/x.py (group scan lacks it)"])
        step = text.replace("tools/tests/test_scan.py -v", "tools/tests/test_other.py -v")
        self.assertEqual(len(compare(group, name, step)), 1)
        for extra in ["python tools/tests/test_other.py -v", "python3 -I -m unittest discover"]:
            more = text.rstrip("\n") + "\n      - name: More\n        run: %s\n" % extra
            self.assertEqual(compare(group, name, more), ["scan-tests.yml: a step the parity test cannot read: " + extra])
        block = text.rstrip("\n") + "\n      - name: More\n        run: |\n          echo hi\n          python -I tools/tests/test_other.py\n"
        self.assertEqual(len(compare(group, name, block)), 1)
        chained = text.replace("tools/tests/test_scan.py -v", "tools/tests/test_scan.py -v && python tools/b.py")
        self.assertEqual(compare(group, name, chained), ["scan-tests.yml: a step the parity test cannot read: python tools/b.py"])
        push = text.replace("  pull_request:\n    paths:", "  pull_request:\n  push:\n    paths:")
        self.assertIn("scan-tests.yml: a path filter the map cannot hold: paths:", compare(group, name, push))


if __name__ == "__main__":
    unittest.main()
