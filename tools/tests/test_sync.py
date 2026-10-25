#!/usr/bin/env python3
"""Tests for tools/sync.py, on small made-up Logs: a bare repo as origin and clones of it, in a
temporary directory. git's global and system config are left out, so the tests see only the
identity they set.

  python3 -I tools/tests/test_sync.py
"""
import importlib.util, os, shutil, subprocess, sys, tempfile, unittest

sys.dont_write_bytecode = True   # the tool loaded below leaves no tools/__pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "sync.py")
spec = importlib.util.spec_from_file_location("sync", TOOL)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class Log(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        empty = os.path.join(self.tmp, "gitconfig")
        open(empty, "w").close()
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=empty, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
        self.env.pop("CAREER_LOG_UNATTENDED", None)
        self.origin = os.path.join(self.tmp, "origin.git")
        self.git(self.tmp, "init", "-q", "--bare", "-b", "master", self.origin)
        self.root = self.clone("log")
        self.write("README.md", "# Log\n")
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget\n---\n")
        self.write("tools/x.py", "engine\n")
        self.git(self.root, "add", "-A")
        self.git(self.root, "commit", "-q", "-m", "init")
        self.git(self.root, "push", "-q", "origin", "master")
        self.git(self.root, "remote", "set-head", "origin", "master")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, cwd, *args):
        p = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def clone(self, name, identity=True):
        path = os.path.join(self.tmp, name)
        self.git(self.tmp, "clone", "-q", self.origin, path)
        self.git(path, "config", "core.autocrlf", "false")
        if identity:
            self.git(path, "config", "--local", "user.name", "Test")
            self.git(path, "config", "--local", "user.email", "test@example.org")
        return path

    def write(self, rel, text, root=None):
        path = os.path.join(root or self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def sync(self, *args, root=None, env=None):
        p = subprocess.run([sys.executable, "-I", TOOL, "--root", root or self.root] + list(args),
                           capture_output=True, encoding="utf-8", env=dict(self.env, **(env or {})))
        return p.returncode, p.stdout

    def pushed(self, root=None):
        root = root or self.root
        return (self.git(root, "status", "--short") == ""
                and self.git(root, "rev-list", "--count", "origin/master..HEAD").strip() == "0")


class Pull(Log):
    def test_up_to_date(self):
        self.assertEqual(self.sync("pull"), (0, "pull: up to date\nsync: ok\n"))

    def test_new_commits(self):
        other = self.clone("other")
        self.write("profile.md", "# Profile\n", root=other)
        self.git(other, "add", "profile.md")
        self.git(other, "commit", "-q", "-m", "profile")
        self.git(other, "push", "-q")
        self.assertEqual(self.sync("pull"), (0, "pull: ok (1 new commit(s))\nsync: ok\n"))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "profile.md")))

    def test_skipped_with_log_changes(self):
        other = self.clone("other")
        self.write("profile.md", "# Profile\n", root=other)
        self.git(other, "add", "profile.md")
        self.git(other, "commit", "-q", "-m", "profile")
        self.git(other, "push", "-q")
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget 2\n---\n")
        self.assertEqual(self.sync("pull"), (0, "pull: skipped (uncommitted Log changes)\nsync: ok\n"))
        self.assertFalse(os.path.isfile(os.path.join(self.root, "profile.md")))
        # unattended, it pulls anyway and leaves the changes as they are
        self.assertEqual(self.sync("pull", env={"CAREER_LOG_UNATTENDED": "1"}), (0, "pull: ok (1 new commit(s))\nsync: ok\n"))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "profile.md")))
        self.assertEqual(self.git(self.root, "status", "--short"), " M entries/2031-01-widget.md\n")

    def test_engine_change_does_not_skip(self):
        self.write("tools/x.py", "changed\n")
        self.assertEqual(self.sync("pull")[1], "pull: up to date\nsync: ok\n")

    def test_unattended_pulls(self):
        other = self.clone("other")
        self.write("profile.md", "# Profile\n", root=other)
        self.git(other, "add", "profile.md")
        self.git(other, "commit", "-q", "-m", "profile")
        self.git(other, "push", "-q")
        self.assertEqual(self.sync("pull", env={"CAREER_LOG_UNATTENDED": "1"})[0], 0)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "profile.md")))

    def test_refused(self):
        other = self.clone("other")
        self.write("README.md", "# Theirs\n", root=other)
        self.git(other, "commit", "-q", "-am", "theirs")
        self.git(other, "push", "-q")
        self.write("README.md", "# Mine\n")
        self.git(self.root, "commit", "-q", "-am", "mine")
        code, out = self.sync("pull")
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(lines[0], "pull: refused")
        self.assertTrue(any(l.startswith("  ") for l in lines[1:-1]), out)
        self.assertTrue(lines[-1].startswith("next: stop: show the user git's message"), out)

    def test_no_remote(self):
        self.git(self.root, "remote", "remove", "origin")
        self.assertEqual(self.sync("pull"), (0, "pull: no remote\nsync: ok\n"))

    def test_unreachable_goes_on(self):
        # nothing listens on port 1: git fails to connect, as with no network
        self.git(self.root, "remote", "set-url", "origin", "http://127.0.0.1:1/origin.git")
        self.assertEqual(self.sync("pull"),
                         (0, "pull: offline (origin unreachable, working on the local copy)\nsync: ok\n"))

    def test_other_failure_stops(self):
        # a message that names no unreachable host (here: no repository at origin's path) stops
        self.git(self.root, "remote", "set-url", "origin", os.path.join(self.tmp, "gone.git"))
        code, out = self.sync("pull")
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[0], "pull: refused")

    def test_unreachable_message(self):
        self.assertTrue(sync.unreachable("fatal: unable to access 'https://h/x.git/': Could not resolve host: h"))
        self.assertTrue(sync.unreachable("ssh: connect to host h port 22: Connection timed out\n"
                                         "fatal: Could not read from remote repository."))
        self.assertFalse(sync.unreachable("git@h: Permission denied (publickey).\n"
                                          "fatal: Could not read from remote repository."))
        self.assertFalse(sync.unreachable("fatal: Authentication failed for 'https://h/x.git/'"))
        self.assertFalse(sync.unreachable("fatal: Not possible to fast-forward, aborting."))


class Commit(Log):
    def test_clean_commit(self):
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget\n---\n\n## Pending\n- 2031-01-02: shipped\n")
        self.write("sources/claude-code/2031-01-02-widget.md", "excerpt\n")
        self.write("profile.md", "# Waiting for a yes\n")   # another change, left out
        code, out = self.sync("commit", "log(widget): shipped", "--",
                              "entries/2031-01-widget.md", "sources/claude-code/2031-01-02-widget.md")
        self.assertEqual(code, 0, out)
        lines = out.splitlines()
        self.assertRegex(lines[0], r"^committed: \[master [0-9a-f]{7,}\] log\(widget\): shipped$")
        self.assertEqual(lines[1:], ["pushed: origin/master", "sync: ok"])
        self.assertEqual(self.git(self.root, "status", "--short"), "?? profile.md\n")
        self.assertEqual(self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip(), "0")
        self.assertEqual(self.git(self.root, "log", "-1", "--format=%s %ae").strip(),
                         "log(widget): shipped test@example.org")

    def test_only_its_paths_with_others_staged(self):
        self.write("profile.md", "# Staged elsewhere\n")
        self.git(self.root, "add", "profile.md")
        self.write("README.md", "# Log 2\n")
        code, out = self.sync("commit", "setup: quick", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git(self.root, "show", "--name-only", "--format=", "HEAD").split(), ["README.md"])
        self.assertEqual(self.git(self.root, "status", "--short"), "A  profile.md\n")

    def test_deleted_file_and_folder(self):
        os.remove(os.path.join(self.root, "entries/2031-01-widget.md"))
        self.write("outputs/dashboard/dashboard.html", "<p>x</p>\n")
        code, out = self.sync("commit", "dashboard: regenerate", "--", "entries/2031-01-widget.md", "outputs/dashboard/")
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed())

    def test_nothing_to_commit_still_pushes(self):
        self.write("README.md", "# Log 2\n")
        self.git(self.root, "commit", "-q", "-am", "local")
        code, out = self.sync("commit", "log(widget): x", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertIn("commit: nothing to commit", out)
        self.assertTrue(self.pushed())

    def test_no_identity(self):
        root = self.clone("noid", identity=False)
        self.git(root, "config", "user.email", "global@example.org")   # not --local: a global one is no identity
        self.git(root, "config", "--unset", "user.email")
        self.write("README.md", "# x\n", root=root)
        code, out = self.sync("commit", "log(x): y", "--", "README.md", root=root)
        self.assertEqual(code, 1)
        self.assertIn("identity: none", out)
        self.assertIn("SETUP.md step 3", out.splitlines()[-1])
        self.assertEqual(self.git(root, "status", "--short"), " M README.md\n")

    def test_push_refused(self):
        other = self.clone("other")
        self.write("profile.md", "# Theirs\n", root=other)
        self.git(other, "add", "profile.md")
        self.git(other, "commit", "-q", "-m", "theirs")
        self.git(other, "push", "-q")
        self.write("README.md", "# Mine\n")
        code, out = self.sync("commit", "log(widget): mine", "--", "README.md")
        self.assertEqual(code, 1)
        self.assertIn("committed: [master ", out)
        self.assertIn("push: refused (the commit is made, not pushed)", out)
        self.assertIn("Never force-push", out.splitlines()[-1])
        self.assertEqual(self.git(self.root, "log", "-1", "--format=%s").strip(), "log(widget): mine")

    def test_no_remote(self):
        self.git(self.root, "remote", "remove", "origin")
        self.write("README.md", "# Log 2\n")
        code, out = self.sync("commit", "log(widget): local", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[1:], ["push: no remote (the commit stays in this clone)", "sync: ok"])
        self.assertEqual(self.git(self.root, "status", "--short"), "")

    def test_no_push(self):
        self.write("README.md", "# Log 2\n")
        code, out = self.sync("commit", "--no-push", "setup: init", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[1:], ["push: held (--no-push)", "sync: ok"])
        self.assertEqual(self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip(), "1")
        self.write("profile.md", "# Profile\n")
        code, out = self.sync("settle", "commit", "--no-push")
        self.assertEqual(code, 0, out)
        self.assertIn("push: held (--no-push)", out)
        self.assertEqual(self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip(), "2")

    def test_other_branch_refused(self):
        self.git(self.root, "checkout", "-q", "-b", "feature")
        self.write("README.md", "# x\n")
        code, out = self.sync("commit", "log(x): y", "--", "README.md")
        self.assertEqual(code, 1)
        self.assertIn("branch: feature (default: master)", out)

    def test_scan_branch_pushes_upstream(self):
        self.git(self.root, "checkout", "-q", "-b", "scan/2031-01-02")
        self.write("scan-drafts/a/resume.tex", "x\n")
        code, out = self.sync("commit", "scan(2031-01-02): drafts for 1 postings", "--", "scan-drafts/")
        self.assertEqual(code, 0, out)
        self.assertIn("pushed: origin/scan/2031-01-02", out)
        self.assertIn("origin/scan/2031-01-02", self.git(self.root, "rev-parse", "--abbrev-ref", "@{upstream}"))

    def test_usage(self):
        self.assertEqual(self.sync("commit", "x")[0], 2)
        self.assertEqual(self.sync("commit", "--", "README.md")[0], 2)
        self.assertEqual(self.sync("commit", "x", "--", "nope.md")[0], 2)
        self.write("README.md", "# Log 2\n")
        code, out = self.sync("commit", "x", "--", "README.md", "outputs/reports/scan-declined.jsonl")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[0], "skipped: outputs/reports/scan-declined.jsonl (no such file, and none git knows)")
        self.assertEqual(self.sync("settle")[0], 2)
        self.assertEqual(self.sync("bogus")[0], 2)
        code, out = self.sync("--help")
        self.assertEqual(code, 0)
        self.assertIn("settle discard", out)


class Push(Log):
    def test_pushes_commits_left_on_head(self):
        self.write("README.md", "# Log 2\n")
        self.git(self.root, "commit", "-q", "-am", "left by an earlier push that failed")
        self.write("profile.md", "# Profile\n")   # an uncommitted Log change stays as it is
        code, out = self.sync("push")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), ["pushed: origin/master", "sync: ok"])
        self.assertEqual(self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip(), "0")
        self.assertEqual(self.git(self.root, "status", "--short"), "?? profile.md\n")
        self.assertEqual(self.git(self.root, "rev-list", "--count", "HEAD").strip(), "2")   # nothing committed
        self.assertEqual(self.sync("push"), (0, "pushed: origin/master\nsync: ok\n"))   # nothing ahead

    def test_needs_no_identity(self):
        root = self.clone("noid", identity=False)
        self.git(root, "-c", "user.name=T", "-c", "user.email=t@example.org", "commit", "-q", "--allow-empty",
                 "-m", "x")
        code, out = self.sync("push", root=root)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git(root, "rev-list", "--count", "origin/master..HEAD").strip(), "0")

    def test_other_branch_refused(self):
        self.git(self.root, "checkout", "-q", "-b", "feature")
        self.git(self.root, "commit", "-q", "--allow-empty", "-m", "x")
        code, out = self.sync("push")
        self.assertEqual(code, 1)
        self.assertIn("branch: feature (default: master)", out)
        self.assertNotIn("feature", self.git(self.root, "branch", "-r"))

    def test_refused_and_no_remote(self):
        other = self.clone("other")
        self.git(other, "commit", "-q", "--allow-empty", "-m", "theirs")
        self.git(other, "push", "-q")
        self.git(self.root, "commit", "-q", "--allow-empty", "-m", "mine")
        code, out = self.sync("push")
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[0], "push: refused (nothing pushed)")
        self.assertIn("Never force-push", out.splitlines()[-1])
        self.git(self.root, "remote", "remove", "origin")
        self.assertEqual(self.sync("push"), (0, "push: no remote (the commits stay in this clone)\nsync: ok\n"))

    def test_usage(self):
        self.assertEqual(self.sync("push", "x")[0], 2)


class Settle(Log):
    def left(self):
        """An earlier session's leftovers: a changed entry, a new entry, a new source, an Engine edit."""
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget 2\n---\n")
        self.write("entries/2031-02-gadget.md", "---\ntitle: Gadget\n---\n")
        self.write("sources/resumes/cv.pdf", "pdf\n")
        self.write("tools/x.py", "engine edit\n")

    def test_status(self):
        self.assertEqual(self.sync("status"), (0, "log changes: none\nsync: ok\n"))
        self.left()
        code, out = self.sync("status")
        lines = out.splitlines()
        self.assertEqual(lines[0], "log changes: uncommitted (3 file(s))")
        self.assertIn("log change:  M entries/2031-01-widget.md", lines)
        self.assertIn("log change: ?? entries/2031-02-gadget.md", lines)
        self.assertIn("log change: ?? sources/resumes/cv.pdf", lines)
        self.assertFalse(any("tools/x.py" in l for l in lines))
        self.assertTrue(any("1 file changed" in l for l in lines), out)
        code, out = self.sync("status", "--", "entries/2031-02-gadget.md")
        self.assertEqual(out.splitlines()[:2], ["log changes: uncommitted (1 file(s))",
                                                "log change: ?? entries/2031-02-gadget.md"])

    def test_commit(self):
        self.left()
        code, out = self.sync("settle", "commit")
        self.assertEqual(code, 0, out)
        self.assertIn("] log: changes left uncommitted (2031-01-widget.md, 2031-02-gadget.md, cv.pdf)", out)
        self.assertEqual(self.git(self.root, "status", "--short"), " M tools/x.py\n")
        self.assertEqual(self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip(), "0")

    def test_staged_rename(self):
        self.git(self.root, "mv", "entries/2031-01-widget.md", "entries/2031-01-sorter.md")
        lines = self.sync("status")[1].splitlines()
        self.assertIn("log change: D  entries/2031-01-widget.md", lines)
        self.assertIn("log change: A  entries/2031-01-sorter.md", lines)
        code, out = self.sync("settle", "commit")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git(self.root, "status", "--short"), "")
        self.assertEqual(self.git(self.root, "ls-tree", "--name-only", "HEAD", "entries/").split(),
                         ["entries/2031-01-sorter.md"])

    def test_discard_staged_rename(self):
        self.git(self.root, "mv", "entries/2031-01-widget.md", "entries/2031-01-sorter.md")
        code, out = self.sync("settle", "discard")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git(self.root, "status", "--short"), "")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "entries/2031-01-widget.md")))

    def test_commit_with_subject(self):
        self.left()
        code, out = self.sync("settle", "commit", "--subject", "import: 1 file(s), 1 entry")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git(self.root, "log", "-1", "--format=%s").strip(), "import: 1 file(s), 1 entry")

    def test_discard_waits_for_sources(self):
        self.left()
        code, out = self.sync("settle", "discard")
        self.assertEqual(code, 1)
        self.assertIn("new source: sources/resumes/cv.pdf", out)
        self.assertIn("--sources-checked", out.splitlines()[-1])
        self.assertTrue(os.path.isfile(os.path.join(self.root, "entries/2031-02-gadget.md")))   # nothing changed

    def test_discard(self):
        self.left()
        os.makedirs(os.path.join(self.root, "sources/inbox"))
        os.replace(os.path.join(self.root, "sources/resumes/cv.pdf"), os.path.join(self.root, "sources/inbox/cv.pdf"))
        self.write(".gitignore", "sources/inbox/*\n")
        self.git(self.root, "add", "-N", "entries/2031-02-gadget.md")   # as consolidate step 5 leaves it
        code, out = self.sync("settle", "discard")
        self.assertEqual(code, 0, out)
        self.assertIn("restored: entries/2031-01-widget.md", out)
        self.assertIn("deleted: entries/2031-02-gadget.md", out)
        self.assertEqual(self.sync("status")[1], "log changes: none\nsync: ok\n")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "sources/inbox/cv.pdf")))
        self.assertEqual(self.git(self.root, "status", "--short", "--", "tools"), " M tools/x.py\n")

    def test_discard_sources_checked(self):
        self.left()
        code, out = self.sync("settle", "discard", "--sources-checked")
        self.assertEqual(code, 0, out)
        self.assertIn("deleted: sources/resumes/cv.pdf", out)

    def test_discard_only_paths(self):
        self.left()
        code, out = self.sync("settle", "discard", "--", "entries/2031-01-widget.md", "tools/x.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(out, "restored: entries/2031-01-widget.md\nsync: ok\n")
        self.assertIn(" M tools/x.py", self.git(self.root, "status", "--short"))


if __name__ == "__main__":
    unittest.main()
