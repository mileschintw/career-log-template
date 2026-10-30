#!/usr/bin/env python3
"""Tests for tools/upgrade.py: the plan it makes from a Log's version and the release tags, the
Engine replacement per step, the Log's own .gitignore lines and Engine files, and the merge of the
Log's Engine edits. Each test builds a scratch Template repo with release tags and a Log made from
one of them ("Use this template": one commit, no history), in a temporary folder.

  python3 -I tools/tests/test_upgrade.py
"""
import importlib.util, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
TOOL = os.path.join(TOOLS, "upgrade.py")

spec = importlib.util.spec_from_file_location("upgrade", TOOL)
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)

ALLOW = 'ALLOW="skills tools AGENTS.md .gitignore"\n'
OLD_SHA = "e6a5565a4807db1ab30b0eb70f8c2fd1421ac4df"


def rmtree(path):
    """shutil.rmtree that also removes git's read-only object files on Windows."""
    def retry(func, p, _):
        os.chmod(p, 0o700)
        func(p)
    shutil.rmtree(path, onerror=retry)


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, "-c", "core.autocrlf=false", *args], check=True,
                          capture_output=True, text=True).stdout


def write(root, files):
    for path, text in files.items():
        p = os.path.join(root, *path.split("/"))
        if text is None:
            os.remove(p)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


def init(path):
    os.makedirs(path)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    git(path, "config", "core.autocrlf", "false")


V010 = {
    "tools/export-template.sh": ALLOW,
    "tools/TEMPLATE_VERSION": OLD_SHA + "\n",
    "skills/career-log/SKILL.md": "intro\nrule one\nrule two\nrule three\nend\n",
    "skills/career-log/modes/old.md": "an old mode\n",
    "AGENTS.md": "agents 0.1.0\n",
    ".gitignore": ".build/\n",
}
V020 = {
    "tools/TEMPLATE_VERSION": "0.2.0\nsource 1111111\n",
    "skills/career-log/SKILL.md": "intro 0.2.0\nrule one\nrule two\nrule three\nend\n",
    "skills/career-log/modes/old.md": None,
    "skills/career-log/modes/upgrade.md": "the mode\n",
    "docs/upgrades/upgrade-0.2.0.md": "# Upgrade to 0.2.0\n",
    "tools/export-template.sh": 'ALLOW="skills tools AGENTS.md .gitignore docs/upgrades"\n',
}
V021 = {"tools/TEMPLATE_VERSION": "0.2.1\nsource 2222222\n", "AGENTS.md": "agents 0.2.1\n"}


class Upgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tpl = os.path.join(self.tmp, "tpl")
        init(self.tpl)
        for version, files in (("0.1.0", V010), ("0.2.0", V020), ("0.2.1", V021)):
            write(self.tpl, files)
            git(self.tpl, "add", "-A")
            git(self.tpl, "commit", "-q", "-m", version)
            git(self.tpl, "tag", "v" + version)
        self.url = "file://" + self.tpl.replace("\\", "/")

    def tearDown(self):
        rmtree(self.tmp)

    def log(self, version="0.1.0", edits=None):
        """A Log made from v<version>, its first commit only, with edits committed on top."""
        log = os.path.join(self.tmp, "log")
        init(log)
        git(self.tpl, "--work-tree=" + log, "checkout", "v" + version, "--", ".")
        git(self.tpl, "reset", "-q")
        write(log, {"entries/2026-01-x.md": "an entry\n"})
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "Initial commit")
        if edits:
            write(log, edits)
            git(log, "add", "-A")
            git(log, "commit", "-q", "-m", "edits")
        return log

    def run_tool(self, *args):
        r = subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, encoding="utf-8")
        return r.returncode, r.stdout.splitlines()

    def plan(self, log, *more):
        return self.run_tool("plan", log, "--url", self.url, *more)

    def test_plan_steps_and_engine_changes(self):
        log = self.log(edits={"skills/career-log/SKILL.md": "intro\nrule one, mine\nrule two\nrule three\nend\n",
                              "skills/career-log/modes/mine.md": "my own mode\n",
                              "AGENTS.md": None})
        rc, out = self.plan(log)
        self.assertEqual(rc, 0, out)
        self.assertIn("from: 0.1.0", out)
        self.assertIn("to: 0.2.1", out)
        # 0.2.0 has a guide, so it is a step of its own; 0.2.1 is the target
        self.assertEqual([l for l in out if l.startswith("step: ")], ["step: 0.2.0", "step: 0.2.1"])
        self.assertIn("edited: skills/career-log/SKILL.md", out)
        self.assertIn("added: skills/career-log/modes/mine.md", out)
        self.assertIn("removed: AGENTS.md", out)
        self.assertIn("dropped: skills/career-log/modes/old.md", out)   # 0.2.0 deletes it
        self.assertNotIn("entries/2026-01-x.md", "\n".join(out))

    def test_plan_mode_change_is_no_edit(self):
        log = self.log()
        git(log, "update-index", "--chmod=+x", "tools/export-template.sh")
        git(log, "commit", "-q", "-m", "mode only")
        # the working tree too, so that a file system with modes (Linux, macOS) sees a clean tree
        p = os.path.join(log, "tools", "export-template.sh")
        os.chmod(p, os.stat(p).st_mode | 0o111)
        rc, out = self.plan(log)
        self.assertEqual(rc, 0, out)
        self.assertFalse([l for l in out if l.startswith(("edited:", "added:", "removed:"))], out)

    def test_plan_to_an_older_target(self):
        rc, out = self.plan(self.log(), "--to", "0.2.0")
        self.assertEqual(rc, 0, out)
        self.assertEqual([l for l in out if l.startswith("step: ")], ["step: 0.2.0"])

    def test_plan_patch_without_guide_is_one_step(self):
        rc, out = self.plan(self.log("0.2.0"))
        self.assertEqual(rc, 0, out)
        self.assertIn("from: 0.2.0", out)
        self.assertEqual([l for l in out if l.startswith("step: ")], ["step: 0.2.1"])

    def test_plan_already_there(self):
        rc, out = self.plan(self.log("0.2.1"))
        self.assertEqual(rc, 0)
        self.assertTrue(out[-1].startswith("OK: "), out)

    def test_plan_needs_a_clean_tree(self):
        log = self.log()
        write(log, {"entries/2026-01-x.md": "changed\n"})
        rc, out = self.plan(log)
        self.assertEqual(rc, 1)
        self.assertTrue(out[0].startswith("stop: uncommitted"), out)

    def test_plan_before_010(self):
        # the 0.1.0 guide lives in a later release's docs/upgrades/
        write(self.tpl, {"docs/upgrades/upgrade-0.1.0.md": "# Upgrade to 0.1.0\n"})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", "0.3.0")
        git(self.tpl, "tag", "v0.3.0")
        for stamp in ("04708244d0ef0000000000000000000000000000\n", None):
            log = self.log(edits={"tools/TEMPLATE_VERSION": stamp})
            rc, out = self.plan(log)
            self.assertEqual(rc, 1, out)
            self.assertIn("before 0.1.0", out[0])
            self.assertTrue(os.path.exists(os.path.join(log, ".build", "upgrade", "upgrade-0.1.0.md")))
            rmtree(log)

    def test_plan_next_stamp(self):
        rc, out = self.plan(self.log(edits={"tools/TEMPLATE_VERSION": "next\nsource 3333333\n"}))
        self.assertEqual(rc, 1)
        self.assertIn("unreleased", out[0])

    def test_engine_steps_keep_the_logs_own(self):
        log = self.log(edits={".gitignore": ".build/\n# mine\nprivate/\n",
                              "skills/career-log/modes/mine.md": "my own mode\n"})
        self.assertEqual(self.plan(log)[0], 0)
        rc, out = self.run_tool("engine", log, "0.2.1")
        self.assertEqual(rc, 1, out)   # out of order
        rc, out = self.run_tool("engine", log, "0.2.0")
        self.assertEqual(rc, 0, out)
        self.assertIn("done: deleted skills/career-log/modes/old.md (not in 0.2.0)", out)
        self.assertTrue(out[-1].endswith("upgrade-0.2.0.md"), out)
        self.assertTrue(os.path.exists(os.path.join(log, "skills/career-log/modes/mine.md")))
        self.assertTrue(os.path.exists(os.path.join(log, "skills/career-log/modes/upgrade.md")))
        with open(os.path.join(log, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read(), ".build/\n\n# This Log's own lines\n# mine\nprivate/\n")
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "upgrade: Template 0.2.0")
        rc, out = self.run_tool("engine", log, "0.2.1")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out[-1], "guide: none")
        with open(os.path.join(log, "tools/TEMPLATE_VERSION"), encoding="utf-8") as f:
            self.assertEqual(f.readline().strip(), "0.2.1")
        with open(os.path.join(log, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("private/"), 1)
        with open(os.path.join(log, "entries/2026-01-x.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "an entry\n")

    def test_reapply_merges_and_reports_conflicts(self):
        log = self.log(edits={"skills/career-log/SKILL.md": "intro\nrule one\nrule two\nrule three, mine\nend\n"})
        self.plan(log)
        self.assertEqual(self.run_tool("reapply", log, "--all")[0], 1)   # steps left
        for v in ("0.2.0", "0.2.1"):
            self.assertEqual(self.run_tool("engine", log, v)[0], 0)
            git(log, "add", "-A")
            git(log, "commit", "-q", "-m", "upgrade: Template " + v)
        self.assertEqual(self.run_tool("reapply", log)[0], 2)   # no path and no --all
        rc, out = self.run_tool("reapply", log, "--all")
        self.assertEqual((rc, out), (0, ["merged: skills/career-log/SKILL.md"]))
        with open(os.path.join(log, "skills/career-log/SKILL.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "intro 0.2.0\nrule one\nrule two\nrule three, mine\nend\n")
        # the same line changed on both sides is a conflict, markers in the file
        git(log, "checkout", "--", ".")
        state = upgrade.load(log)
        git(log, "checkout", state["start"], "--", "skills/career-log/SKILL.md")
        write(log, {"skills/career-log/SKILL.md": "intro, mine\nrule one\nrule two\nrule three\nend\n"})
        git(log, "commit", "-q", "-am", "edit")
        state["start"] = git(log, "rev-parse", "HEAD").strip()
        write(log, {"skills/career-log/SKILL.md": "intro 0.2.0\nrule one\nrule two\nrule three\nend\n"})
        git(log, "commit", "-q", "-am", "back to 0.2.0's")
        upgrade.save(log, state)
        rc, out = self.run_tool("reapply", log, "skills/career-log/SKILL.md")
        self.assertEqual((rc, out), (1, ["conflict: skills/career-log/SKILL.md: 1"]))
        with open(os.path.join(log, "skills/career-log/SKILL.md"), encoding="utf-8") as f:
            self.assertIn("<<<<<<< this Log", f.read())

    def test_reapply_file_gone_in_new_version(self):
        log = self.log(edits={"skills/career-log/modes/old.md": "an old mode, mine\n"})
        self.plan(log)
        for v in ("0.2.0", "0.2.1"):
            self.run_tool("engine", log, v)
            git(log, "add", "-A")
            git(log, "commit", "-q", "-m", "upgrade: Template " + v)
        rc, out = self.run_tool("reapply", log, "--all")
        self.assertEqual(rc, 0)
        self.assertTrue(out[0].startswith("review: skills/career-log/modes/old.md"), out)

    def test_engine_needs_the_step_before_committed(self):
        log = self.log()
        self.plan(log)
        self.assertEqual(self.run_tool("engine", log, "0.2.0")[0], 0)
        rc, out = self.run_tool("engine", log, "0.2.1")
        self.assertEqual(rc, 1, out)
        self.assertTrue(out[0].startswith("stop: uncommitted changes; commit the step before"), out)

    def test_plan_path_joining_the_engine(self):
        # 0.3.0 makes docs/ Engine; the Log had its own docs/notes.md and docs/mine.md, and 0.3.0
        # brings a docs/notes.md of its own
        write(self.tpl, {"tools/export-template.sh": 'ALLOW="skills tools AGENTS.md .gitignore docs"\n',
                         "docs/notes.md": "the release's notes\n"})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", "0.3.0")
        git(self.tpl, "tag", "v0.3.0")
        log = self.log("0.2.1", edits={"docs/notes.md": "my notes\n", "docs/mine.md": "mine\n"})
        rc, out = self.plan(log)
        self.assertEqual(rc, 0, out)
        self.assertIn("overwritten: docs/notes.md", out)
        self.assertIn("added: docs/mine.md", out)
        self.assertEqual(self.run_tool("engine", log, "0.3.0")[0], 0)
        self.assertTrue(os.path.exists(os.path.join(log, "docs", "mine.md")))

    def test_reapply_keeps_crlf_files_whole(self):
        # a file the Log checks out with CRLF (.gitattributes eol=crlf) merges line by line
        write(self.tpl, {".gitattributes": "*.ps1 text eol=crlf\n", "tools/setup.ps1": "a\nb\nc\nd\n",
                         "tools/TEMPLATE_VERSION": "0.2.2\nsource 4444444\n"})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", "0.2.2")
        git(self.tpl, "tag", "v0.2.2")
        write(self.tpl, {"tools/setup.ps1": "a 0.3.0\nb\nc\nd\n", "tools/TEMPLATE_VERSION": "0.3.0\nsource 5555555\n"})
        git(self.tpl, "commit", "-q", "-am", "0.3.0")
        git(self.tpl, "tag", "v0.3.0")
        log = self.log("0.2.2")
        p = os.path.join(log, "tools", "setup.ps1")
        os.remove(p)
        git(log, "checkout", "--", "tools/setup.ps1")   # with the eol rule now in place
        with open(p, "rb") as f:
            self.assertIn(b"\r\n", f.read())
        with open(p, "wb") as f:
            f.write(b"a\r\nb\r\nc\r\nd mine\r\n")
        git(log, "commit", "-q", "-am", "edit")
        self.plan(log)
        self.run_tool("engine", log, "0.3.0")
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "upgrade: Template 0.3.0")
        rc, out = self.run_tool("reapply", log, "tools/setup.ps1")
        self.assertEqual((rc, out), (0, ["merged: tools/setup.ps1"]))
        with open(p, "rb") as f:
            self.assertEqual(f.read(), b"a 0.3.0\r\nb\r\nc\r\nd mine\r\n")

    def front_page_release(self, version, head, zh_head):
        page = head + "## Entries\n\n| Entry |\n|---|\n\n## License\n\nMIT\n"
        zh = zh_head + "## 條目\n\n見英文版。\n"
        with open(os.path.join(TOOLS, "config.py"), encoding="utf-8") as f:
            config = f.read()
        with open(os.path.join(TOOLS, "logfiles.py"), encoding="utf-8") as f:
            logfiles = f.read()
        write(self.tpl, {"README.md": page, "README.zh-TW.md": zh, "tools/template/README.md": page,
                         "tools/template/README.zh-TW.md": zh, "tools/config.py": config, "tools/logfiles.py": logfiles,
                         "tools/TEMPLATE_VERSION": "%s\nsource 6666666\n" % version})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", version)
        git(self.tpl, "tag", "v" + version)

    def front_page_state(self, log):
        spec = importlib.util.spec_from_file_location("log_config", os.path.join(log, "tools", "config.py"))
        sys.path.insert(0, os.path.join(log, "tools"))
        try:
            config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config)
            return config.front_page_state(log)
        finally:
            sys.path.pop(0)
            sys.modules.pop("logfiles", None)

    def upgrade_front_page(self, edits):
        self.front_page_release("0.2.2", "# career-log\n\nStart with setup.\n\n", "# career-log\n\n先跑 setup。\n\n")
        self.front_page_release("0.3.0", "# career-log\n\nStart with the guide.\n\n", "# career-log\n\n先讀指南。\n\n")
        log = self.log("0.2.2", edits)
        self.assertEqual(self.plan(log)[0], 0)
        rc, out = self.run_tool("engine", log, "0.3.0")
        self.assertEqual(rc, 0, out)
        return log, out

    def test_engine_updates_an_unedited_front_page(self):
        row = "## Entries\n\n| Entry |\n|---|\n| [mine](entries/2026-01-x.md) |\n\n## License\n\nMIT\n"
        log, out = self.upgrade_front_page({"README.md": "# career-log\n\nStart with setup.\n\n" + row})
        self.assertIn("done: README.md above `## Entries`: the Template's page, unedited, now 0.3.0's", out)
        self.assertIn("done: README.zh-TW.md above `## 條目`: the Template's page, unedited, now 0.3.0's", out)
        with open(os.path.join(log, "README.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "# career-log\n\nStart with the guide.\n\n" + row)   # the entry row stays
        self.assertEqual(self.front_page_state(log), "template")

    def test_engine_keeps_an_edited_front_page(self):
        mine = "# My log\n\nMy own words.\n\n## Entries\n\n| Entry |\n|---|\n"
        log, out = self.upgrade_front_page({"README.md": mine, "README.zh-TW.md": None})
        self.assertFalse([l for l in out if "front page" in l or "README" in l], out)
        with open(os.path.join(log, "README.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), mine)
        self.assertFalse(os.path.exists(os.path.join(log, "README.zh-TW.md")))
        self.assertEqual(self.front_page_state(log), "edited")

    def test_clean(self):
        log = self.log()
        self.plan(log)
        self.assertEqual(self.run_tool("clean", log)[0], 0)
        self.assertEqual(git(log, "for-each-ref", upgrade.REFS), "")
        self.assertFalse(os.path.exists(os.path.join(log, ".build", "upgrade")))

    def test_usage(self):
        self.assertEqual(self.run_tool("plan")[0], 2)
        self.assertEqual(self.run_tool("engine", self.tpl)[0], 2)
        self.assertEqual(self.run_tool("plan", self.tpl, "--to", "x")[0], 2)


@unittest.skipUnless(shutil.which("sh"), "no sh on PATH")
class Export(unittest.TestCase):
    """tools/export-template.sh's --version checks, in a clone of this repo's HEAD."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "src")
        git(self.tmp, "clone", "-q", REPO, self.src)
        git(self.src, "config", "user.email", "test@example.com")
        git(self.src, "config", "user.name", "Test")

    def tearDown(self):
        rmtree(self.tmp)

    def export(self, *args):
        r = subprocess.run(["sh", "tools/export-template.sh", *args, os.path.join(self.tmp, "out")],
                           cwd=self.src, capture_output=True, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout

    def test_version_must_be_semver(self):
        rc, out = self.export("--version", "0.x")
        self.assertEqual(rc, 1)
        self.assertIn("takes a semver", out)

    def test_refuses_while_next_guide_holds_a_change(self):
        up = os.path.join(self.src, "docs", "upgrades")
        for ext in ("md", "py"):   # from an empty guide, whatever changes upgrade-next.* holds now
            shutil.copyfile(os.path.join(up, "upgrade-skeleton." + ext), os.path.join(up, "upgrade-next." + ext))
        git(self.src, "commit", "-q", "--allow-empty", "-am", "an empty next guide")
        for name, sentinel in (("upgrade-next.md", "No Log format change yet."), ("upgrade-next.py", "CHECKS = []"),
                               ("upgrade-next.md", "This release adds none.")):   # #329: a new setting ships it too
            p = os.path.join(self.src, "docs", "upgrades", name)
            with open(p, encoding="utf-8") as f:
                text = f.read()
            self.assertIn(sentinel, text)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(text.replace(sentinel, "a step"))
            git(self.src, "commit", "-q", "-am", "a step in " + name)
            rc, out = self.export("--version", "0.9.0")
            self.assertEqual(rc, 1, out)
            self.assertIn("holds a Log format change or a new setting", out)
            git(self.src, "reset", "-q", "--hard", "HEAD~1")


class Source(unittest.TestCase):
    """The tool against this repo's own export (skipped in a Template, which has the same files)."""

    def test_engine_paths_read_this_export(self):
        paths = upgrade.engine_paths(REPO, "HEAD")
        self.assertIn("skills", paths)
        self.assertIn("docs/upgrades", paths)
        self.assertIn(".github", paths)

    def test_skeleton_is_empty(self):
        # the empty form a release copies to upgrade-next.*: what the export's check reads as no change
        for name, sentinel in (("upgrade-skeleton.md", "No Log format change yet."), ("upgrade-skeleton.md", "This release adds none."),
                               ("upgrade-skeleton.py", "CHECKS = []")):
            with open(os.path.join(REPO, "docs", "upgrades", name), encoding="utf-8") as f:
                self.assertIn(sentinel, f.read().splitlines())

    def test_empty_next_guide_is_the_skeleton(self):
        # while upgrade-next.* holds no change, it is upgrade-skeleton.* as it is
        up = os.path.join(REPO, "docs", "upgrades")
        with open(os.path.join(up, "upgrade-next.md"), encoding="utf-8") as f:
            next_md = f.read()
        with open(os.path.join(up, "upgrade-next.py"), encoding="utf-8") as f:
            next_py = f.read()
        empty = {"No Log format change yet.", "This release adds none."}
        if empty <= set(next_md.splitlines()) and "CHECKS = []" in next_py.splitlines():
            for ext, text in (("md", next_md), ("py", next_py)):
                with open(os.path.join(up, "upgrade-skeleton." + ext), encoding="utf-8") as f:
                    self.assertEqual(text, f.read(), "upgrade-next.%s differs from upgrade-skeleton.%s" % (ext, ext))

    def test_020_guide_finds_direction_headings(self):
        # #299: a direction.md heading tools/config.py cannot read is a migrate: line, until renamed
        spec = importlib.util.spec_from_file_location("upgrade_020", os.path.join(REPO, "docs", "upgrades", "upgrade-0.2.0.py"))
        guide = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guide)
        if not hasattr(guide, "check_direction"):
            self.skipTest("the 0.2.0 guide no longer holds #299's check")
        root = tempfile.mkdtemp()
        self.addCleanup(rmtree, root)
        os.makedirs(os.path.join(root, "tools"))
        for name in ("config.py", "logfiles.py", "config.default.toml"):
            shutil.copy(os.path.join(TOOLS, name), os.path.join(root, "tools", name))
        self.assertEqual(guide.check_direction(root, False),
                         [("migrate", "direction.md: tools/config.py cannot read target roles, sorting order, work authorisation,"
                                      " visa sponsorship, other hard constraints, what to emphasise: direction.md is missing")])
        with open(os.path.join(TOOLS, "template", "direction.md"), encoding="utf-8") as f:
            template = f.read()
        old = template.replace("## Target roles, ranked", "## Target roles")
        write(root, {"direction.md": old})
        self.assertEqual(guide.check_direction(root, False),
                         [("migrate", "direction.md: tools/config.py cannot read target roles:"
                                      " direction.md has no `## Target roles, ranked` section")])
        write(root, {"direction.md": template})
        self.assertEqual(guide.check_direction(root, False), [])
        write(root, {"tools/config.py": "raise SystemExit(3)\n"})   # no lines at all is no all-clear
        self.assertEqual([k for k, _ in guide.check_direction(root, False)], ["migrate"])

    def test_030_guide_moves_the_status_and_writes_the_table(self):
        # #574: an entry's status moves from its README row to its front matter, then the table is generated
        path = os.path.join(REPO, "docs", "upgrades", "upgrade-0.3.0.py")
        spec = importlib.util.spec_from_file_location("upgrade_030", path)
        guide = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guide)
        if not hasattr(guide, "check_status"):
            self.skipTest("the 0.3.0 guide no longer holds #574's checks")
        root = tempfile.mkdtemp()
        self.addCleanup(rmtree, root)
        os.makedirs(os.path.join(root, "tools"))
        for name in ("entries.py", "logfiles.py"):
            shutil.copy(os.path.join(TOOLS, name), os.path.join(root, "tools", name))
        fm = "---\r\ntitle: %s\r\ntype: project\r\nperiod: %s\r\nlast_updated: 2026-10-01\r\n---\r\n\r\n# %s\r\n"
        write(root, {"entries/2025-01-widget.md": fm % ("Widget", "2025-01 – 2025-06", "Widget"),
                     "entries/2024-01-lamp.md": fm % ("Lamp", "2024-01 – 2024-02", "Lamp"),
                     "README.md": "# Log\n\n## Entries\n\n| Period | Entry | Type | Tags | Status |\n|---|---|---|---|---|\n"
                                  "| 2025-01 – 2025-06 | [Widget](entries/2025-01-widget.md) | project | go |"
                                  " consolidated (two gaps) |\n| 2024-01 – 2024-02 | [Lamp](entries/2024-01-lamp.md) |"
                                  " project | | done |\n| - | a note | | | |\n"})
        self.assertEqual(guide.check_status(root, False), [
            ("ask", "entries/2024-01-lamp.md: no status: its README row's 'done' is not a status"),
            ("apply", "entries/2025-01-widget.md: status: consolidated (two gaps), from its README row")])
        self.assertEqual(guide.check_readme(root, False),
                         [("ask", "README.md:9: - | a note |  |  | : links no entry, and the generated table leaves it out")])
        self.assertEqual(guide.check_status(root, True)[1][0], "done")
        with open(os.path.join(root, "entries", "2025-01-widget.md"), encoding="utf-8", newline="") as f:
            self.assertIn("last_updated: 2026-10-01\r\nstatus: consolidated (two gaps)\r\n---\r\n", f.read())
        write(root, {"entries/2024-01-lamp.md": (fm % ("Lamp", "2024-01 – 2024-02", "Lamp")).replace(
            "---\r\n\r\n", "status: stub\r\n---\r\n\r\n")})
        self.assertEqual(guide.check_status(root, False), [])
        self.assertEqual(guide.check_readme(root, False)[0][0], "ask")   # the table waits for the answer
        write(root, {"README.md": "# Log\n\n## Entries\n\n| Period | Entry | Type | Tags | Status |\n|---|---|---|---|---|\n"})
        self.assertEqual(guide.check_readme(root, False), [
            ("apply", "README.md: Entries table in the old layout, or not generated from the entries yet")])
        self.assertEqual(guide.check_readme(root, True), [("done", "README.md: readme written: README.md:5-8: 2 rows")])
        self.assertEqual(guide.check_readme(root, False), [])
        write(root, {"README.md": "# Log\n"})
        self.assertEqual([k for k, _ in guide.check_readme(root, False)], ["migrate"])

    def test_020_guide_reviews_a_sponsorship_need_in_other_words(self):
        # #284: a need for visa sponsorship with no Visa sponsorship needed line is a review: line
        spec = importlib.util.spec_from_file_location("upgrade_020", os.path.join(REPO, "docs", "upgrades", "upgrade-0.2.0.py"))
        guide = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guide)
        if not hasattr(guide, "check_visa_sponsorship"):
            self.skipTest("the 0.2.0 guide no longer holds #284's check")
        root = tempfile.mkdtemp()
        self.addCleanup(rmtree, root)
        os.makedirs(os.path.join(root, "tools"))
        for name in ("config.py", "logfiles.py", "config.default.toml", "sponsorship.py"):
            shutil.copy(os.path.join(TOOLS, name), os.path.join(root, "tools", name))
        with open(os.path.join(TOOLS, "template", "direction.md"), encoding="utf-8") as f:
            template = f.read()
        write(root, {"direction.md": template})
        self.assertEqual(guide.check_visa_sponsorship(root, False), [])   # the Template's: all empty
        constraints = "## Constraints\n"
        for lines, found in (
                ("- **Work authorisation:** Needs H-1B sponsorship (user, 2026-10-01)\n", ["Needs H-1B sponsorship"]),
                ("- **Work authorisation:** F-1 OPT (user, 2026-10-01)\n- **Visa:** green card later (user, 2026-10-01)\n",
                 ["F-1 OPT", "**Visa:** green card later"]),   # #377: OPT is a value the line takes
                ("- **Work authorisation:** On CPT this year (user, 2026-10-01)\n", ["On CPT this year"]),
                ("- Would opt for remote roles (user, 2026-10-01)\n", []),   # the verb is not OPT
                ("- **Work authorisation:** F-1 OPT (user, 2026-10-01)\n"
                 "- **Visa sponsorship needed:** OPT (user, 2026-10-01)\n", []),
                ("- **Work authorisation:** Citizen, no sponsorship needed (user, 2026-10-01)\n", []),
                ("- **Work authorisation:** Green card holder (user, 2026-10-01)\n", []),
                ("- **Work authorisation:** EU citizen, no visa needed for EU roles (user, 2026-10-01)\n", []),
                ("- **Work authorisation:** Needs H-1B sponsorship (user, 2026-10-01)\n"
                 "- **Visa sponsorship needed:** H-1B (user, 2026-10-01)\n", [])):
            write(root, {"direction.md": template.replace(constraints, constraints + lines, 1)})
            got = guide.check_visa_sponsorship(root, False)
            self.assertEqual([k for k, _ in got], ["review"] * len(found), lines)
            for (_, text), f in zip(got, found):
                self.assertIn(f, text)
        # a line the tools cannot read is a migrate: line
        write(root, {"direction.md": template.replace(
            constraints, constraints + "- **Visa sponsorship needed:** yes (user, 2026-10-01)\n", 1)})
        got = guide.check_visa_sponsorship(root, False)
        self.assertEqual([k for k, _ in got], ["migrate"])
        self.assertIn("`yes`", got[0][1])

    def test_020_guide_updates_template_text(self):
        # #477: a line still as 0.1.0's Template wrote it becomes 0.2.0's; an edited line stays
        spec = importlib.util.spec_from_file_location("upgrade_020", os.path.join(REPO, "docs", "upgrades", "upgrade-0.2.0.py"))
        guide = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guide)
        if not hasattr(guide, "check_text_updates"):
            self.skipTest("the 0.2.0 guide no longer holds #477's check")
        for rel, old, new in guide.TEXT_UPDATES:   # the new line is the Template's own
            with open(os.path.join(TOOLS, "template", *rel.split("/")), encoding="utf-8") as f:
                self.assertIn(new, f.read().splitlines(), rel)
        rel, old, new = guide.TEXT_UPDATES[0]
        with open(os.path.join(TOOLS, "template", *rel.split("/")), encoding="utf-8") as f:
            template = f.read()
        root = tempfile.mkdtemp()
        self.addCleanup(rmtree, root)
        p = os.path.join(root, *rel.split("/"))
        self.assertEqual(guide.check_text_updates(root, False), [])   # no file: nothing to do
        for eol in ("\n", "\r\n"):
            write(root, {rel: template.replace(new, old)})
            with open(p, "rb") as f:
                before = f.read().replace(b"\n", eol.encode())
            with open(p, "wb") as f:
                f.write(before)
            self.assertEqual([k for k, _ in guide.check_text_updates(root, False)], ["apply"])
            self.assertEqual([k for k, _ in guide.check_text_updates(root, True)], ["done"])
            with open(p, "rb") as f:
                self.assertEqual(f.read(), template.replace("\n", eol).encode())
            self.assertEqual(guide.check_text_updates(root, False), [])
            self.assertEqual(guide.check_text_updates(root, True), [])   # a second run changes nothing
            with open(p, "rb") as f:
                self.assertEqual(f.read(), template.replace("\n", eol).encode())
        edited = template.replace(new, old.replace("Add a row", "Add a row (and a note)"))
        write(root, {rel: edited})
        self.assertEqual(guide.check_text_updates(root, True), [])
        with open(p, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), edited)

    def test_stamp_known_matches_010_guide(self):
        guide = os.path.join(REPO, "docs", "upgrades", "upgrade-0.1.0.py")
        if not os.path.exists(guide):
            self.skipTest("no 0.1.0 guide here")
        with open(guide, encoding="utf-8") as f:
            sha = re.search(r'^ENGINE_VERSION = "([0-9a-f]{40})"', f.read(), re.M).group(1)
        self.assertEqual(upgrade.STAMPS, {sha: "0.1.0"})


if __name__ == "__main__":
    unittest.main()
