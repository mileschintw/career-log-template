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
spec = importlib.util.spec_from_file_location("logfiles", os.path.join(TOOLS, "logfiles.py"))
logfiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logfiles)

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


V020 = {
    "tools/export-template.sh": ALLOW,
    "tools/TEMPLATE_VERSION": "0.2.0\nsource 0000000\n",
    "skills/career-log/SKILL.md": "intro\nrule one\nrule two\nrule three\nend\n",
    "skills/career-log/modes/old.md": "an old mode\n",
    "AGENTS.md": "agents 0.2.0\n",
    ".gitignore": ".build/\n",
}
V030 = {
    "tools/TEMPLATE_VERSION": "0.3.0\nsource 1111111\n",
    "skills/career-log/SKILL.md": "intro 0.3.0\nrule one\nrule two\nrule three\nend\n",
    "skills/career-log/modes/old.md": None,
    "skills/career-log/modes/upgrade.md": "the mode\n",
    "docs/upgrades/upgrade-0.3.0.md": "# Upgrade to 0.3.0\n",
    "tools/export-template.sh": 'ALLOW="skills tools AGENTS.md .gitignore docs/upgrades"\n',
}
V031 = {"tools/TEMPLATE_VERSION": "0.3.1\nsource 2222222\n", "AGENTS.md": "agents 0.3.1\n"}


class Upgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tpl = os.path.join(self.tmp, "tpl")
        init(self.tpl)
        for version, files in (("0.2.0", V020), ("0.3.0", V030), ("0.3.1", V031)):
            write(self.tpl, files)
            git(self.tpl, "add", "-A")
            git(self.tpl, "commit", "-q", "-m", version)
            git(self.tpl, "tag", "v" + version)
        self.url = "file://" + self.tpl.replace("\\", "/")

    def tearDown(self):
        rmtree(self.tmp)

    def log(self, version="0.2.0", edits=None, name="log"):
        """A Log made from v<version>, its first commit only, with edits committed on top."""
        log = os.path.join(self.tmp, name)
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

    def test_split_page_reads_the_heading_as_entries_py_reads_it(self):
        """#651 C1: spaces after the marks and a CRLF page."""
        self.assertEqual(upgrade.split_page(b"# Log\r\n\r\n##  Entries \r\nrow\r\n", "Entries"),
                         ("# Log\n\n", "##  Entries \nrow\n"))
        self.assertIsNone(upgrade.split_page(b"# Log\n### Entries\n", "Entries"))
        self.assertEqual(upgrade.HEADING % "x", logfiles.heading_re("x").pattern)
        with open(os.path.join(TOOLS, "upgrade.py"), encoding="utf-8") as f:   # it runs with no logfiles.py beside it
            self.assertNotRegex(f.read(), r"(?m)^\s*(import|from) (logfiles|entries|config)\b")

    def test_plan_steps_and_engine_changes(self):
        log = self.log(edits={"skills/career-log/SKILL.md": "intro\nrule one, mine\nrule two\nrule three\nend\n",
                              "skills/career-log/modes/mine.md": "my own mode\n",
                              "AGENTS.md": None})
        rc, out = self.plan(log)
        self.assertEqual(rc, 0, out)
        self.assertIn("from: 0.2.0", out)
        self.assertIn("to: 0.3.1", out)
        # 0.3.0 has a guide, so it is a step of its own; 0.3.1 is the target
        self.assertEqual([l for l in out if l.startswith("step: ")], ["step: 0.3.0", "step: 0.3.1"])
        self.assertIn("edited: skills/career-log/SKILL.md", out)
        self.assertIn("added: skills/career-log/modes/mine.md", out)
        self.assertIn("removed: AGENTS.md", out)
        self.assertIn("dropped: skills/career-log/modes/old.md", out)   # 0.3.0 deletes it
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
        rc, out = self.plan(self.log(), "--to", "0.3.0")
        self.assertEqual(rc, 0, out)
        self.assertEqual([l for l in out if l.startswith("step: ")], ["step: 0.3.0"])

    def test_plan_patch_without_guide_is_one_step(self):
        rc, out = self.plan(self.log("0.3.0"))
        self.assertEqual(rc, 0, out)
        self.assertIn("from: 0.3.0", out)
        self.assertEqual([l for l in out if l.startswith("step: ")], ["step: 0.3.1"])

    def test_plan_already_there(self):
        rc, out = self.plan(self.log("0.3.1"))
        self.assertEqual(rc, 0)
        self.assertTrue(out[-1].startswith("OK: "), out)

    def test_plan_needs_a_clean_tree(self):
        log = self.log()
        write(log, {"entries/2026-01-x.md": "changed\n"})
        rc, out = self.plan(log)
        self.assertEqual(rc, 1)
        self.assertTrue(out[0].startswith("stop: uncommitted"), out)

    def test_plan_below_the_floor_stops_at_the_bridge(self):
        # #685: a Log older than 0.2.0 (0.1.0's commit stamp, another commit, no stamp, a semver below the
        # floor) is told to upgrade to v0.3.2 first, and nothing is planned
        for stamp in (OLD_SHA + "\n", "04708244d0ef0000000000000000000000000000\n", None, "0.1.0\nsource 0000000\n"):
            log = self.log(edits={"tools/TEMPLATE_VERSION": stamp})
            rc, out = self.plan(log)
            self.assertEqual(rc, 1, out)
            self.assertEqual(len(out), 1, out)
            self.assertTrue(out[0].startswith("stop: this Log is from before %s (" % upgrade.FLOOR), out)
            self.assertIn("upgrade to v%s first" % upgrade.BRIDGE, out[0])
            self.assertEqual((upgrade.FLOOR, upgrade.BRIDGE), ("0.2.0", "0.3.2"))   # the docs name both
            self.assertFalse(os.path.exists(upgrade.state_path(log)))
            rmtree(log)

    def test_plan_next_stamp(self):
        rc, out = self.plan(self.log(edits={"tools/TEMPLATE_VERSION": "next\nsource 3333333\n"}))
        self.assertEqual(rc, 1)
        self.assertIn("unreleased", out[0])

    def test_engine_steps_keep_the_logs_own(self):
        log = self.log(edits={".gitignore": ".build/\n# mine\nprivate/\n",
                              "skills/career-log/modes/mine.md": "my own mode\n"})
        self.assertEqual(self.plan(log)[0], 0)
        rc, out = self.run_tool("engine", log, "0.3.1")
        self.assertEqual(rc, 1, out)   # out of order
        rc, out = self.run_tool("engine", log, "0.3.0")
        self.assertEqual(rc, 0, out)
        self.assertIn("done: deleted skills/career-log/modes/old.md (not in 0.3.0)", out)
        self.assertTrue(out[-1].endswith("upgrade-0.3.0.md"), out)
        self.assertTrue(os.path.exists(os.path.join(log, "skills/career-log/modes/mine.md")))
        self.assertTrue(os.path.exists(os.path.join(log, "skills/career-log/modes/upgrade.md")))
        with open(os.path.join(log, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read(), ".build/\n\n# This Log's own lines\n# mine\nprivate/\n")
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "upgrade: Template 0.3.0")
        rc, out = self.run_tool("engine", log, "0.3.1")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out[-1], "guide: none")
        with open(os.path.join(log, "tools/TEMPLATE_VERSION"), encoding="utf-8") as f:
            self.assertEqual(f.readline().strip(), "0.3.1")
        with open(os.path.join(log, ".gitignore"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("private/"), 1)
        with open(os.path.join(log, "entries/2026-01-x.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "an entry\n")

    def test_reapply_merges_and_reports_conflicts(self):
        log = self.log(edits={"skills/career-log/SKILL.md": "intro\nrule one\nrule two\nrule three, mine\nend\n"})
        self.plan(log)
        self.assertEqual(self.run_tool("reapply", log, "--all")[0], 1)   # steps left
        for v in ("0.3.0", "0.3.1"):
            self.assertEqual(self.run_tool("engine", log, v)[0], 0)
            git(log, "add", "-A")
            git(log, "commit", "-q", "-m", "upgrade: Template " + v)
        self.assertEqual(self.run_tool("reapply", log)[0], 2)   # no path and no --all
        rc, out = self.run_tool("reapply", log, "--all")
        self.assertEqual((rc, out), (0, ["merged: skills/career-log/SKILL.md"]))
        with open(os.path.join(log, "skills/career-log/SKILL.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "intro 0.3.0\nrule one\nrule two\nrule three, mine\nend\n")
        # the same line changed on both sides is a conflict, markers in the file
        git(log, "checkout", "--", ".")
        state = upgrade.load(log)
        git(log, "checkout", state["start"], "--", "skills/career-log/SKILL.md")
        write(log, {"skills/career-log/SKILL.md": "intro, mine\nrule one\nrule two\nrule three\nend\n"})
        git(log, "commit", "-q", "-am", "edit")
        state["start"] = git(log, "rev-parse", "HEAD").strip()
        write(log, {"skills/career-log/SKILL.md": "intro 0.3.0\nrule one\nrule two\nrule three\nend\n"})
        git(log, "commit", "-q", "-am", "back to 0.3.0's")
        upgrade.save(log, state)
        rc, out = self.run_tool("reapply", log, "skills/career-log/SKILL.md")
        self.assertEqual((rc, out), (1, ["conflict: skills/career-log/SKILL.md: 1"]))
        with open(os.path.join(log, "skills/career-log/SKILL.md"), encoding="utf-8") as f:
            self.assertIn("<<<<<<< this Log", f.read())

    def test_reapply_file_gone_in_new_version(self):
        log = self.log(edits={"skills/career-log/modes/old.md": "an old mode, mine\n"})
        self.plan(log)
        for v in ("0.3.0", "0.3.1"):
            self.run_tool("engine", log, v)
            git(log, "add", "-A")
            git(log, "commit", "-q", "-m", "upgrade: Template " + v)
        rc, out = self.run_tool("reapply", log, "--all")
        self.assertEqual(rc, 0)
        self.assertTrue(out[0].startswith("review: skills/career-log/modes/old.md"), out)

    def test_engine_needs_the_step_before_committed(self):
        log = self.log()
        self.plan(log)
        self.assertEqual(self.run_tool("engine", log, "0.3.0")[0], 0)
        rc, out = self.run_tool("engine", log, "0.3.1")
        self.assertEqual(rc, 1, out)
        self.assertTrue(out[0].startswith("stop: uncommitted changes; commit the step before"), out)

    def test_plan_path_joining_the_engine(self):
        # 0.4.0 makes docs/ Engine; the Log had its own docs/notes.md and docs/mine.md, and 0.4.0
        # brings a docs/notes.md of its own
        write(self.tpl, {"tools/export-template.sh": 'ALLOW="skills tools AGENTS.md .gitignore docs"\n',
                         "docs/notes.md": "the release's notes\n"})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", "0.4.0")
        git(self.tpl, "tag", "v0.4.0")
        log = self.log("0.3.1", edits={"docs/notes.md": "my notes\n", "docs/mine.md": "mine\n"})
        rc, out = self.plan(log)
        self.assertEqual(rc, 0, out)
        self.assertIn("overwritten: docs/notes.md", out)
        self.assertIn("added: docs/mine.md", out)
        self.assertEqual(self.run_tool("engine", log, "0.4.0")[0], 0)
        self.assertTrue(os.path.exists(os.path.join(log, "docs", "mine.md")))

    def test_reapply_keeps_crlf_files_whole(self):
        # a file the Log checks out with CRLF (.gitattributes eol=crlf) merges line by line
        write(self.tpl, {".gitattributes": "*.ps1 text eol=crlf\n", "tools/setup.ps1": "a\nb\nc\nd\n",
                         "tools/TEMPLATE_VERSION": "0.3.2\nsource 4444444\n"})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", "0.3.2")
        git(self.tpl, "tag", "v0.3.2")
        write(self.tpl, {"tools/setup.ps1": "a 0.4.0\nb\nc\nd\n", "tools/TEMPLATE_VERSION": "0.4.0\nsource 5555555\n"})
        git(self.tpl, "commit", "-q", "-am", "0.4.0")
        git(self.tpl, "tag", "v0.4.0")
        log = self.log("0.3.2")
        p = os.path.join(log, "tools", "setup.ps1")
        os.remove(p)
        git(log, "checkout", "--", "tools/setup.ps1")   # with the eol rule now in place
        with open(p, "rb") as f:
            self.assertIn(b"\r\n", f.read())
        with open(p, "wb") as f:
            f.write(b"a\r\nb\r\nc\r\nd mine\r\n")
        git(log, "commit", "-q", "-am", "edit")
        self.plan(log)
        self.run_tool("engine", log, "0.4.0")
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "upgrade: Template 0.4.0")
        rc, out = self.run_tool("reapply", log, "tools/setup.ps1")
        self.assertEqual((rc, out), (0, ["merged: tools/setup.ps1"]))
        with open(p, "rb") as f:
            self.assertEqual(f.read(), b"a 0.4.0\r\nb\r\nc\r\nd mine\r\n")

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
        self.front_page_release("0.3.2", "# career-log\n\nStart with setup.\n\n", "# career-log\n\n先跑 setup。\n\n")
        self.front_page_release("0.4.0", "# career-log\n\nStart with the guide.\n\n", "# career-log\n\n先讀指南。\n\n")
        log = self.log("0.3.2", edits)
        self.assertEqual(self.plan(log)[0], 0)
        rc, out = self.run_tool("engine", log, "0.4.0")
        self.assertEqual(rc, 0, out)
        return log, out

    def test_engine_updates_an_unedited_front_page(self):
        row = "## Entries\n\n| Entry |\n|---|\n| [mine](entries/2026-01-x.md) |\n\n## License\n\nMIT\n"
        log, out = self.upgrade_front_page({"README.md": "# career-log\n\nStart with setup.\n\n" + row})
        self.assertIn("done: README.md above `## Entries`: the Template's page, unedited, now 0.4.0's", out)
        self.assertIn("done: README.zh-TW.md above `## 條目`: the Template's page, unedited, now 0.4.0's", out)
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

    def test_plan_flags_after_plan_name_the_flag(self):
        # only plan takes --to and --url; the others say which flag and why, from the plan's state
        log = self.log()
        rc, out = self.run_tool("engine", log, "0.3.0", "--url", self.url)
        self.assertEqual(rc, 2, out)
        self.assertEqual(out, ["error: engine takes no --url: plan fetches the releases, and engine reads them from there"])
        self.assertEqual(self.plan(log)[0], 0)
        rc, out = self.run_tool("engine", log, "0.3.0", "--url", self.url)
        self.assertEqual((rc, out), (2, ["error: engine takes no --url: plan fetched the releases (from %s), "
                                         "and engine reads them from there" % self.url]))
        rc, out = self.run_tool("reapply", log, "--all", "--to", "0.3.1")
        self.assertEqual((rc, out), (2, ["error: reapply takes no --to: plan set the target (0.3.1), "
                                         "and reapply reads it from the plan"]))
        rc, out = self.run_tool("clean", log, "--to", "0.3.1", "--url", self.url)
        self.assertEqual(rc, 2, out)
        self.assertEqual([l.split(":")[1] for l in out], [" clean takes no --to", " clean takes no --url"])
        self.assertEqual(upgrade.load(log)["done"], [])   # nothing ran

    # Dev builds (ADR 0015): `<next version>-dev.<n>`, tagged on the Engine repo's builds branch

    def dev_builds(self):
        """Tag two Dev builds of 0.3.2 after v0.3.1, each with the next guide as it stood."""
        for n in (1, 2):
            version = "0.3.2-dev.%d" % n
            write(self.tpl, {"tools/TEMPLATE_VERSION": "%s\nsource %d%d%d%d%d%d%d\n" % ((version,) + (n,) * 7),
                             "skills/career-log/SKILL.md": "intro 0.3.0\nrule one dev%d\nrule two\nrule three\nend\n" % n,
                             "docs/upgrades/upgrade-next.md": "# next, at dev.%d\n" % n,
                             "docs/upgrades/upgrade-next.py": "CHECKS = []\n"})
            git(self.tpl, "add", "-A")
            git(self.tpl, "commit", "-q", "-m", version)
            git(self.tpl, "tag", "v" + version)

    def release_032(self):
        """Release 0.3.2 after its Dev builds, with a guide of its own."""
        write(self.tpl, {"tools/TEMPLATE_VERSION": "0.3.2\nsource 7777777\n",
                         "docs/upgrades/upgrade-next.md": None, "docs/upgrades/upgrade-next.py": None,
                         "docs/upgrades/upgrade-0.3.2.md": "# Upgrade to 0.3.2\n"})
        git(self.tpl, "add", "-A")
        git(self.tpl, "commit", "-q", "-m", "0.3.2")
        git(self.tpl, "tag", "v0.3.2")

    def steps(self, out):
        return [l[len("step: "):] for l in out if l.startswith("step: ")]

    def test_dev_tags_leave_the_default_target_the_newest_release(self):
        self.dev_builds()
        rc, out = self.plan(self.log("0.3.0"))
        self.assertEqual(rc, 0, out)
        self.assertIn("to: 0.3.1", out)
        self.assertEqual(self.steps(out), ["0.3.1"])

    def test_dev_to_a_dev_build(self):
        self.dev_builds()
        log = self.log("0.3.1")
        rc, out = self.plan(log, "--to", "v0.3.2-dev.1")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out[:2], ["from: 0.3.1", "to: 0.3.2-dev.1"])
        self.assertEqual(self.steps(out), ["0.3.2-dev.1"])
        rc, out = self.run_tool("engine", log, "0.3.2-dev.1")
        self.assertEqual(rc, 0, out)
        # a Dev build's guide is the next guide as it stands, under the name the guide gives its script
        self.assertRegex(out[-1], r"^guide: .*/\.build/upgrade/upgrade-next\.md$")   # the Log's root may print long or short
        with open(os.path.join(log, ".build", "upgrade", "upgrade-next.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "# next, at dev.1\n")
        self.assertTrue(os.path.exists(os.path.join(log, ".build", "upgrade", "upgrade-next.py")))
        self.assertEqual(upgrade.stamped(log)[0], "0.3.2-dev.1")

    def test_dev_to_a_later_dev_build(self):
        self.dev_builds()
        log = self.log("0.3.2-dev.1")
        rc, out = self.plan(log, "--to", "0.3.2-dev.2")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out[:2], ["from: 0.3.2-dev.1", "to: 0.3.2-dev.2"])
        self.assertEqual(self.steps(out), ["0.3.2-dev.2"])
        self.assertFalse([l for l in out if l.startswith("edited:")], out)   # dev.2's changes are no edit
        rc, out = self.run_tool("engine", log, "0.3.2-dev.2")
        self.assertEqual(rc, 0, out)
        with open(os.path.join(log, ".build", "upgrade", "upgrade-next.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "# next, at dev.2\n")

    def test_dev_to_its_release(self):
        self.dev_builds()
        self.release_032()
        log = self.log("0.3.2-dev.2")
        rc, out = self.plan(log)   # the default target: the release after it
        self.assertEqual(rc, 0, out)
        self.assertEqual(out[:2], ["from: 0.3.2-dev.2", "to: 0.3.2"])
        self.assertEqual(self.steps(out), ["0.3.2"])
        rc, out = self.run_tool("engine", log, "0.3.2")
        self.assertEqual(rc, 0, out)
        self.assertTrue(out[-1].endswith("/upgrade-0.3.2.md"), out)   # the release's guide, run again
        self.assertIn("done: deleted docs/upgrades/upgrade-next.md (not in 0.3.2)", out)
        self.assertEqual(upgrade.stamped(log)[0], "0.3.2")

    def test_dev_merge_base_is_the_dev_builds_tag(self):
        # the Log on dev.1 changed rule three; dev.1 and dev.2 each changed rule one. Merged from
        # v0.3.1 instead, rule one would conflict
        self.dev_builds()
        log = self.log("0.3.2-dev.1", edits={
            "skills/career-log/SKILL.md": "intro 0.3.0\nrule one dev1\nrule two\nrule three, mine\nend\n"})
        rc, out = self.plan(log, "--to", "0.3.2-dev.2")
        self.assertEqual(rc, 0, out)
        self.assertEqual([l for l in out if l.startswith("edited:")], ["edited: skills/career-log/SKILL.md"])
        self.assertEqual(self.run_tool("engine", log, "0.3.2-dev.2")[0], 0)
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "upgrade: Template 0.3.2-dev.2")
        rc, out = self.run_tool("reapply", log, "--all")
        self.assertEqual((rc, out), (0, ["merged: skills/career-log/SKILL.md"]))
        with open(os.path.join(log, "skills/career-log/SKILL.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "intro 0.3.0\nrule one dev2\nrule two\nrule three, mine\nend\n")

    def test_dev_tags_come_from_the_engine_repo_only_for_a_dev_build(self):
        # Two scratch addresses, as the real ones: the Template's (releases only) and the Engine repo's
        # (Dev builds only). Each plan runs in this process with every git call recorded
        self.dev_builds()
        log, dev_log = self.log("0.3.0"), self.log("0.3.2-dev.1", name="dev-log")
        eng = os.path.join(self.tmp, "eng")
        git(self.tmp, "clone", "-q", self.tpl, eng)
        for t in git(self.tpl, "tag", "-l").split():
            git(self.tpl if "-dev." in t else eng, "tag", "-d", t)
        eng_url = "file://" + eng.replace("\\", "/")
        calls = []
        real_git = upgrade.git

        def recording(root, *args, **kw):
            calls.append(args)
            return real_git(root, *args, **kw)

        def fetched():
            return [a[a.index("--quiet") + 1] for a in calls if a[0] == "fetch"]

        saved = upgrade.URL, upgrade.DEV_URL, upgrade.git
        upgrade.URL, upgrade.DEV_URL, upgrade.git = self.url, eng_url, recording
        try:
            rc, out = upgrade.plan(log)   # a release to a release
            self.assertEqual(rc, 0, out)
            self.assertIn("to: 0.3.1", out)
            self.assertEqual(fetched(), [self.url])
            self.assertNotIn("-dev.", git(log, "for-each-ref", upgrade.REFS))
            calls.clear()
            rc, out = upgrade.plan(log, "0.3.2-dev.2")   # a release to a Dev build
            self.assertEqual(rc, 0, out)
            self.assertEqual(out[:2], ["from: 0.3.0", "to: 0.3.2-dev.2"])
            self.assertEqual(self.steps(out), ["0.3.2-dev.2"])   # 0.3.1 has no guide
            self.assertEqual(fetched(), [self.url, eng_url])
            self.assertRegex(upgrade.engine(log, "0.3.2-dev.2")[1][-1],   # the Engine repo's tag, checked out
                             r"^guide: .*/\.build/upgrade/upgrade-next\.md$")
            self.assertEqual(upgrade.stamped(log)[0], "0.3.2-dev.2")
            git(log, "reset", "-q", "--hard")   # back to 0.3.0
            rc, out = upgrade.plan(log)   # a release plan after a Dev build's: no Dev ref stays behind
            self.assertEqual(rc, 0, out)
            self.assertNotIn("-dev.", git(log, "for-each-ref", upgrade.REFS))
            calls.clear()
            rc, out = upgrade.plan(dev_log)   # a Log on a Dev build, by default: the newest release is older
            self.assertEqual(fetched(), [self.url, eng_url])
            self.assertEqual(rc, 0, out)
            self.assertTrue(out[-1].startswith("OK: this Log is at 0.3.2-dev.1, the target is 0.3.1"), out)
            self.assertIn("--to", out[-1])
        finally:
            upgrade.URL, upgrade.DEV_URL, upgrade.git = saved

    def test_dev_tags_from_a_url_given_come_from_it_alone(self):
        # a local Dev build is such a url: one folder holding the releases' tags and its Dev builds'.
        # The Engine repo's address is never contacted, from a release or from a Dev build
        self.dev_builds()
        log, dev_log = self.log("0.3.1"), self.log("0.3.2-dev.1", name="dev-log")
        calls = []
        real_git = upgrade.git

        def recording(root, *args, **kw):
            calls.append(args)
            return real_git(root, *args, **kw)

        saved = upgrade.DEV_URL, upgrade.git
        upgrade.DEV_URL, upgrade.git = "file:///nowhere/engine.git", recording
        try:
            for one, to in ((log, "0.3.2-dev.1"), (dev_log, "0.3.2-dev.2")):
                calls.clear()
                rc, out = upgrade.plan(one, to, self.url)
                self.assertEqual(rc, 0, out)
                self.assertEqual(out[1], "to: " + to)
                self.assertEqual([a[a.index("--quiet") + 1] for a in calls if a[0] == "fetch"], [self.url])
        finally:
            upgrade.DEV_URL, upgrade.git = saved

    def test_dev_refusals(self):
        self.dev_builds()
        log = self.log("0.3.2-dev.2")
        rc, out = self.plan(log, "--to", "0.3.2-dev.1")   # an older Dev build
        self.assertEqual(rc, 1, out)
        self.assertEqual(out, ["stop: the target 0.3.2-dev.1 is older than this Log's version 0.3.2-dev.2: "
                               "an upgrade goes only forward"])
        rc, out = self.plan(log, "--to", "0.3.2-dev.9")
        self.assertEqual(rc, 1, out)
        self.assertTrue(out[0].startswith("stop: no Dev build v0.3.2-dev.9 at "), out)
        self.assertIn("0.3.2-dev.1, 0.3.2-dev.2", out[0])
        self.assertEqual(self.plan(log, "--to", "next")[0], 2)   # `next` is never a target
        self.assertEqual(self.plan(log, "--to", "0.3.2-dev")[0], 2)
        rmtree(log)
        rc, out = self.plan(self.log(edits={"tools/TEMPLATE_VERSION": "0.3.2-dev.5\nsource 0000000\n"}))
        self.assertEqual(rc, 1, out)
        self.assertTrue(out[0].startswith("stop: this Log's version 0.3.2-dev.5 has no Dev build tag at "), out)

    def test_version_order(self):
        order = ["0.2.0", "0.3.1", "0.3.2-dev.1", "0.3.2-dev.2", "0.3.2-dev.10", "0.3.2", "0.4.0-dev.1", "0.4.0"]
        self.assertEqual(sorted(reversed(order), key=upgrade.key), order)
        self.assertTrue(upgrade.is_dev("0.3.2-dev.1"))
        self.assertFalse(upgrade.is_dev("0.3.2"))
        self.assertFalse(upgrade.VERSION.match("0.3.2-dev.0"))   # Dev builds count from 1, as the export's
        self.assertFalse(upgrade.SEMVER.match("0.3.2-dev.1"))   # a release, as check.py's update line reads it


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

    def export(self, *args, dest="out"):
        r = subprocess.run(["sh", "tools/export-template.sh", *args, os.path.join(self.tmp, dest)],
                           cwd=self.src, capture_output=True, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout

    def test_export_never_runs_deny_coverage(self):
        # ADR 0015: the export runs no coverage gate, even where an old .export-allow is left
        with open(os.path.join(self.src, "tools", "deny_coverage.py"), "w", encoding="utf-8", newline="\n") as f:
            f.write("import sys\nprint('coverage ran')\nsys.exit(1)\n")
        git(self.src, "commit", "-q", "-am", "a coverage check that always fails")
        with open(os.path.join(self.src, ".export-deny"), "w", encoding="utf-8", newline="\n") as f:
            f.write("# a Log's list\nzzqx-no-such-name\n")
        with open(os.path.join(self.src, ".export-allow"), "w", encoding="utf-8", newline="\n") as f:
            f.write("zzqx-allowed\n")
        rc, out = self.export()
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.splitlines()[-1], "OK")
        self.assertNotIn("coverage ran", out)

    @unittest.skipUnless(os.path.isdir(os.path.join(REPO, "maintainer")), "not the Template's source")
    def test_source_scans_the_starter_list(self):
        # the Engine repo has no .export-deny of its own: it scans with the list every Log starts with,
        # which has no pattern, and stamps the version
        self.assertFalse(os.path.exists(os.path.join(self.src, ".export-deny")))
        rc, out = self.export()
        self.assertEqual(rc, 0, out)
        with open(os.path.join(self.tmp, "out", "tools", "TEMPLATE_VERSION"), encoding="utf-8") as f:
            self.assertEqual(f.read().splitlines()[0], "next")
        with open(os.path.join(self.src, "tools", "template", ".export-deny"), "a", encoding="utf-8", newline="\n") as f:
            f.write("allowlist\n")   # a word export-template.sh uses
        rc, out = self.export(dest="out2")
        self.assertEqual(rc, 1, out)
        self.assertIn("personal content: /allowlist/", out)

    def test_version_must_be_semver(self):
        for bad in ("0.x", "0.4.1-dev", "0.4.1-dev.0", "0.4.1-rc.1", "v0.4.1-dev.1"):
            rc, out = self.export("--version", bad)
            self.assertEqual(rc, 1, bad)
            self.assertIn("takes a semver", out)

    def next_guide(self, change):
        """upgrade-next.* reset to the empty skeleton, with a Log format change in the .md when change."""
        up = os.path.join(self.src, "docs", "upgrades")
        for ext in ("md", "py"):
            shutil.copyfile(os.path.join(up, "upgrade-skeleton." + ext), os.path.join(up, "upgrade-next." + ext))
        if change:
            p = os.path.join(up, "upgrade-next.md")
            with open(p, encoding="utf-8") as f:
                text = f.read()
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(text.replace("No Log format change yet.", "- a format change, step 1"))
        git(self.src, "commit", "-q", "--allow-empty", "-am", "the next guide")
        with open(os.path.join(up, "upgrade-next.md"), "rb") as f:
            return f.read()

    def test_dev_build_ships_the_next_guide_as_it_stands(self):
        # a Dev build is no release: a guide holding a change does not stop it, and it ships the guide
        guide = self.next_guide(change=True)
        rc, out = self.export("--version", "0.5.0-dev.12")
        self.assertEqual(rc, 0, out)
        with open(os.path.join(self.tmp, "out", "tools", "TEMPLATE_VERSION"), encoding="utf-8") as f:
            self.assertEqual(f.read().splitlines()[0], "0.5.0-dev.12")
        with open(os.path.join(self.tmp, "out", "docs", "upgrades", "upgrade-next.md"), "rb") as f:
            self.assertEqual(f.read(), guide)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "out", "docs", "upgrades", "upgrade-next.py")))
        rc, out = self.export("--version", "0.5.0", dest="rel")   # a release is still refused
        self.assertEqual(rc, 1, out)
        self.assertIn("holds a Log format change or a new setting", out)

    def test_release_ships_no_next_guide(self):
        self.next_guide(change=False)
        rc, out = self.export("--version", "0.4.1")
        self.assertEqual(rc, 0, out)
        names = os.listdir(os.path.join(self.tmp, "out", "docs", "upgrades"))
        self.assertEqual([n for n in names if "next" in n or "skeleton" in n or n.startswith("test-")], [])

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


NEXT_SCRIPT = os.path.join(REPO, "docs", "upgrades", "upgrade-next.py")


def tree_state(root):
    """Every file under <root> but .git/ and __pycache__/, with its bytes' hash, and the commit HEAD."""
    import hashlib
    files = {}
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in (".git", "__pycache__"))
        for n in names:
            p = os.path.join(d, n)
            with open(p, "rb") as f:
                files[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(f.read()).hexdigest()
    head = subprocess.run(["git", "-C", root, "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, text=True).stdout
    return files, head.strip()


def run_again(log, script=NEXT_SCRIPT):
    """Run a guide's script a second time on <log>, which the guide already migrated: `--apply`, then a
    plain run. Return its faults, none when the run changed no file, made no commit, printed no `done:`
    line and nothing on stderr, and both runs end with `OK: nothing left to migrate` (docs/maintaining.md
    › Log format changes: a guide can be run again)."""
    faults = []
    before = tree_state(log)
    for args in (["--apply"], []):
        r = subprocess.run([sys.executable, "-I", script, log, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        lines = r.stdout.splitlines()
        name = " ".join(["upgrade-next.py"] + args)
        if r.stderr.strip():
            faults.append("%s: stderr: %s" % (name, r.stderr.strip().splitlines()[-1]))
        faults += ["%s: %s" % (name, line) for line in lines if line.startswith("done:")]
        if r.returncode != 0 or not lines or lines[-1] != "OK: nothing left to migrate":
            faults.append("%s: exit %d, last line %r" % (name, r.returncode, lines[-1] if lines else ""))
    after = tree_state(log)
    for path in sorted(set(before[0]) | set(after[0])):
        if before[0].get(path) != after[0].get(path):
            faults.append("changed: %s" % path)
    if before[1] != after[1]:
        faults.append("changed: HEAD")
    return faults


def migrated_log(tmp):
    """A Log in this source's formats, so one the pending guide has nothing left to migrate in: the
    export of HEAD, setup's config.toml and an entry with a Story, written by the export's own tools."""
    out = os.path.join(tmp, "export")
    r = subprocess.run(["sh", "tools/export-template.sh", out], cwd=REPO, capture_output=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise AssertionError("export failed:\n" + r.stdout + r.stderr)
    log = os.path.join(tmp, "log")
    init(log)
    shutil.copytree(out, log, dirs_exist_ok=True)

    def tool(*args):
        subprocess.run([sys.executable, "-I", *args, "--root", log], cwd=log, check=True, capture_output=True)
    tool("tools/config.py", "init")
    tool("tools/config.py", "set", "update_check", "off")
    tool("tools/entries.py", "new", "library", "--month", "2024-01", "--status", "imported",
         "--field", "title=Example Co — Shared library", "--field", "type=work", "--field", "period=2024-01 – 2025-06")
    tool("tools/entries.py", "story-add", "Proudest project", "entries/2024-01-library.md#my-contribution",
         "--summary", "started the shared library")
    git(log, "add", "-A")
    git(log, "commit", "-q", "-m", "a migrated Log")
    return log


class NextGuide(unittest.TestCase):
    """Guide cases: the pending guide, docs/upgrades/upgrade-next.*, can be run again on a Log it
    already migrated (ADR 0015: a Log that follows dev builds runs it on each of them)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        rmtree(self.tmp)

    def test_next_guide_runs_again_on_a_migrated_log(self):
        log = migrated_log(self.tmp)
        self.assertEqual(run_again(log), [])

    def test_a_step_that_cannot_run_again_fails(self):
        # the rule's own test: a check that appends on every --apply is caught
        bad = os.path.join(self.tmp, "upgrade-bad.py")
        with open(NEXT_SCRIPT, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("\nCHECKS = []\n", text)
        with open(bad, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("\nCHECKS = []\n", (
                "\ndef check_note(root, apply):\n"
                "    if apply:\n"
                "        with open(os.path.join(root, 'notes.md'), 'a', encoding='utf-8') as f:\n"
                "            f.write('migrated\\n')\n"
                "        return [('done', 'notes.md: a line added')]\n"
                "    return []\n\n"
                "CHECKS = [check_note]\n"), 1))
        log = os.path.join(self.tmp, "log")
        init(log)
        write(log, {"notes.md": "a note\n"})
        git(log, "add", "-A")
        git(log, "commit", "-q", "-m", "a Log")
        self.assertEqual(run_again(log, bad), ["upgrade-next.py --apply: done: notes.md: a line added", "changed: notes.md"])


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

    def test_guide_reviews_a_story_key_with_no_name_in_several_rows(self):
        # #695: one section listed under several types with no name may hold several Stories
        guides = sorted(f for f in os.listdir(os.path.join(REPO, "docs", "upgrades")) if re.fullmatch(r"upgrade-.*\.py", f))
        guide = None
        for name in guides:
            with open(os.path.join(REPO, "docs", "upgrades", name), encoding="utf-8") as f:
                if "def check_story_names(" in f.read():
                    spec = importlib.util.spec_from_file_location("upgrade_695", os.path.join(REPO, "docs", "upgrades", name))
                    guide = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(guide)
        if guide is None:
            self.skipTest("no guide holds #695's check")
        root = tempfile.mkdtemp()
        self.addCleanup(rmtree, root)
        os.makedirs(os.path.join(root, "tools"))
        for name in ("entries.py", "logfiles.py"):
            shutil.copy(os.path.join(TOOLS, name), os.path.join(root, "tools", name))
        w, g = "entries/2025-01-widget.md", "entries/2024-01-gadget.md"
        index = ("# Stories\n\n| Question type | Stories |\n|---|---|\n"
                 "| Conflict | [W](%s#contribution); [G](%s#pending) |\n"
                 "| Failure | [W](%s#contribution) — the launch; [G](%s#pending); [W](%s#context \"origin\") |\n"
                 "| Ownership | [W](%s#contribution); [W](%s#context \"origin\") |\n"
                 "| Leadership | [G](%s#context) |\n") % (w, g, w, g, w, w, w, g)
        write(root, {"entries/.keep": "", "stories.md": index})
        self.assertEqual(list(guide.check_story_names(root, False)), [
            ("review", "stories.md: %s#contribution: no name, in 3 rows: Conflict | Failure | Ownership" % w)])
        write(root, {"stories.md": index.replace("#contribution)", '#contribution "launch")')})
        self.assertEqual(list(guide.check_story_names(root, False)), [])
        os.remove(os.path.join(root, "stories.md"))
        self.assertEqual(list(guide.check_story_names(root, False)), [])

    def test_no_guide_at_or_below_the_floor(self):
        # #685: the guides and test scripts of 0.2.0 and before are gone; v0.3.2, the bridge, keeps them
        for name in os.listdir(os.path.join(REPO, "docs", "upgrades")):
            m = re.match(r"(?:upgrade|test)-(\d+\.\d+\.\d+)\.", name)
            if m:
                self.assertGreater(upgrade.key(m.group(1)), upgrade.key(upgrade.FLOOR), name)
        self.assertLess(upgrade.key(upgrade.FLOOR), upgrade.key(upgrade.BRIDGE))


def main_rerun(argv):
    """`test_upgrade.py rerun <log>`: run_again on a copy of <log>, the scratch Log the pending guide's
    test-next.sh built and the upgrade mode then migrated; the Log itself is left as it is."""
    if len(argv) != 1 or not os.path.isdir(os.path.join(argv[0], ".git")):
        print("usage: test_upgrade.py rerun <log>, <log> a Log the pending guide migrated")
        return 2
    tmp = tempfile.mkdtemp()
    try:
        log = os.path.join(tmp, "log")
        shutil.copytree(argv[0], log, symlinks=True)
        faults = run_again(log)
    finally:
        rmtree(tmp)
    for fault in faults:
        print("FAIL: " + fault)
    print("FAIL: the guide cannot run again" if faults else "OK: the guide ran again with no change")
    return 1 if faults else 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["rerun"]:
        sys.exit(main_rerun(sys.argv[2:]))
    unittest.main()
