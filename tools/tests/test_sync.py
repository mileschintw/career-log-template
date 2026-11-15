#!/usr/bin/env python3
"""Tests for tools/sync.py, on small made-up Logs: a bare repo as origin and clones of it, in a
temporary directory. git's global and system config are left out, so the tests see only the
identity they set.

  python3 -I tools/tests/test_sync.py
"""
import datetime, importlib.util, json, os, shutil, subprocess, sys, tempfile, threading, time, unittest

sys.dont_write_bytecode = True   # the tool loaded below leaves no tools/__pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "sync.py")
spec = importlib.util.spec_from_file_location("sync", TOOL)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
logfiles = sync.logfiles


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

    def test_push_rebases_once_when_another_clone_pushed(self):
        other = self.clone("other")
        self.write("profile.md", "# Theirs\n", root=other)
        self.git(other, "add", "profile.md")
        self.git(other, "commit", "-q", "-m", "theirs")
        self.git(other, "push", "-q")
        self.write("README.md", "# Mine\n")
        self.write("entries/2031-02-live.md", "another session's file\n")   # left as it is
        code, out = self.sync("commit", "log(widget): mine", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[1:], ["push: rebased on origin/master", "pushed: origin/master", "sync: ok"])
        self.assertEqual(self.git(self.root, "log", "--format=%s", "-2").splitlines(), ["log(widget): mine", "theirs"])
        self.assertEqual(self.git(self.root, "status", "--short"), "?? entries/2031-02-live.md\n")
        self.assertEqual(self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip(), "0")

    def test_rebase_keeps_the_time_of_uncommitted_files(self):
        other = self.clone("other")
        self.write("profile.md", "# Theirs\n", root=other)
        self.git(other, "add", "profile.md")
        self.git(other, "commit", "-q", "-m", "theirs")
        self.git(other, "push", "-q")
        left = os.path.join(self.root, "entries", "2031-01-widget.md")
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget, left by an earlier session\n---\n")
        os.utime(left, (1_700_000_000, 1_700_000_000))   # an earlier session's file keeps its own time
        self.write("README.md", "# Mine\n")
        code, out = self.sync("commit", "log(widget): mine", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertIn("push: rebased on origin/master", out)
        self.assertEqual(self.git(self.root, "status", "--short"), " M entries/2031-01-widget.md\n")
        self.assertEqual(int(os.path.getmtime(left)), 1_700_000_000)

    def test_push_refused_when_the_rebase_fails(self):
        other = self.clone("other")
        self.write("README.md", "# Theirs\n", root=other)
        self.git(other, "commit", "-q", "-am", "theirs")
        self.git(other, "push", "-q")
        self.write("README.md", "# Mine\n")
        code, out = self.sync("commit", "log(widget): mine", "--", "README.md")
        self.assertEqual(code, 1)
        self.assertIn("committed: [master ", out)
        self.assertIn("push: refused (the commit is made, not pushed)", out)
        self.assertIn("Never force-push", out.splitlines()[-1])
        self.assertEqual(self.git(self.root, "log", "-1", "--format=%s").strip(), "log(widget): mine")
        self.assertEqual(self.git(self.root, "status", "--short"), "")   # the rebase was undone
        gitdir = self.git(self.root, "rev-parse", "--absolute-git-dir").strip()
        self.assertFalse(os.path.exists(os.path.join(gitdir, "rebase-merge")))

    def test_retries_while_another_session_holds_the_index(self):
        lock = os.path.join(self.root, ".git", "index.lock")
        open(lock, "w").close()
        threading.Timer(1.5, os.remove, [lock]).start()
        self.write("README.md", "# Log 2\n")
        code, out = self.sync("commit", "log(widget): while locked", "--", "README.md")
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed())

    def test_stops_when_the_index_stays_locked(self):
        lock = os.path.join(self.root, ".git", "index.lock")
        open(lock, "w").close()
        self.write("README.md", "# Log 2\n")
        code, out = self.sync("commit", "log(widget): locked", "--", "README.md")
        self.assertEqual(code, 1)
        self.assertIn("commit: refused (git add)", out)
        self.assertIn("index.lock", out)

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


class Sessions(Log):
    """ADR 0014: a session claims the Log files it writes; commit holds a file another session claimed, or one
    in its own baseline, and the `next:` line under `owned:` and `held:` is the only place the user is asked
    whether another session is still going."""

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.root, ".git", "info", "exclude"), "a") as f:
            f.write(".build/\n")
        self.entry = "entries/2031-01-widget.md"
        self.a = logfiles.new_session(self.root, {})   # the pack session, started first
        self.b = logfiles.new_session(self.root, {})   # the talk session

    def head(self):
        return self.git(self.root, "rev-parse", "HEAD")

    def claims(self, key):
        return logfiles.read_session(self.root, key)["claims"]

    def asks_about(self, line, key):
        """The `next: stop:` line asks the user whether session key is still going, and names its end."""
        self.assertTrue(line.startswith("next: stop: nothing was changed."), line)
        self.assertIn("ask the user whether session %s is still going" % key, line)
        self.assertIn("`sync.py end --session %s`" % key, line)

    def test_another_sessions_claim_refuses_the_claim_and_holds_the_commit(self):
        code, out = self.sync("claim", "--session", self.a, "--", self.entry)
        self.assertEqual((code, out.splitlines()), (0, ["claimed: %s" % self.entry, "sync: ok"]))
        before = self.head()
        code, out = self.sync("claim", "--session", self.b, "--", self.entry, "profile.md")
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "owned: %s (session %s)" % (self.entry, self.a))
        self.asks_about(out.splitlines()[-1], self.a)
        self.assertEqual(self.claims(self.b), [])   # all or none: profile.md is not claimed either
        self.write(self.entry, "---\ntitle: Widget, by the talk session\n---\n")
        for folder in (self.entry, "entries/"):
            code, out = self.sync("commit", "--session", self.b, "log(widget): mine", "--", folder)
            self.assertEqual(code, 1, out)
            self.assertEqual(out.splitlines()[0], "held: %s (session %s)" % (self.entry, self.a))
            self.asks_about(out.splitlines()[-1], self.a)
            self.assertEqual(self.head(), before)

    def test_a_commit_never_claims_a_file_another_session_claimed_before_its_edit(self):
        """A claim comes before the first edit, so the claimed file may still match HEAD: a commit that names it
        is held all the same, and claims nothing."""
        self.assertEqual(self.sync("claim", "--session", self.a, "--", "README.md")[0], 0)
        self.write(self.entry, "---\ntitle: Widget, the talk session's\n---\n")
        code, out = self.sync("commit", "--session", self.b, "log(widget): mine", "--", self.entry, "README.md")
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "held: README.md (session %s)" % self.a)
        self.assertEqual(self.claims(self.b), [])
        self.assertEqual(self.claims(self.a), ["README.md"])

    def test_the_703_order_holds_the_session_that_did_not_claim(self):
        """#703: the pack session claims and edits the pack file, the talk session edits it too, and the pack
        session edits it last. By time on disk the file was the talk session's; by claim it is the pack's."""
        self.assertEqual(self.sync("claim", "--session", self.a, "--", self.entry)[0], 0)
        self.write(self.entry, "---\ntitle: Widget\n---\npack\n")
        self.write(self.entry, "---\ntitle: Widget\n---\npack\ntalk\n")
        time.sleep(0.05)
        self.write(self.entry, "---\ntitle: Widget\n---\npack\ntalk\npack again\n")   # the pack session edits last
        code, out = self.sync("commit", "--session", self.b, "interview: talk notes", "--", self.entry)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "held: %s (session %s)" % (self.entry, self.a))
        code, out = self.sync("commit", "--session", self.a, "interview: pack", "--", self.entry)
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed(), out)

    def test_a_commit_claims_what_it_commits(self):
        self.write(self.entry, "---\ntitle: Widget, logged\n---\n")
        code, out = self.sync("commit", "--session", self.b, "log(widget): mine", "--", self.entry, "profile.md")
        self.assertEqual(code, 0, out)
        self.assertIn("skipped: profile.md (no such file, and none git knows)", out)
        self.assertEqual(self.claims(self.b), [self.entry])   # committed and clean, still claimed until Next up
        code, out = self.sync("claim", "--session", self.a, "--", self.entry)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "owned: %s (session %s)" % (self.entry, self.b))

    def test_end_releases_another_sessions_claims(self):
        self.assertEqual(self.sync("claim", "--session", self.a, "--", self.entry, "profile.md")[0], 0)
        code, out = self.sync("end", "--session", self.a)   # on the user's word that session a has ended
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), ["released: %s" % self.entry, "released: profile.md",
                                            "session: %s ended (2 claim(s) released)" % self.a, "sync: ok"])
        self.assertIsNotNone(logfiles.read_session(self.root, self.a))   # an ended session keeps its record
        self.assertEqual(self.sync("claim", "--session", self.b, "--", self.entry)[0], 0)
        self.assertEqual(self.sync("end", "--session", self.a)[1].splitlines()[0],
                         "session: %s ended (it held no claim)" % self.a)

    def test_release_hands_a_file_on(self):
        self.assertEqual(self.sync("claim", "--session", self.a, "--", "./" + self.entry)[0], 0)
        code, out = self.sync("release", "--session", self.a, "--", self.entry, "profile.md")
        self.assertEqual(out.splitlines(), ["released: %s" % self.entry,
                                            "not claimed: profile.md (by session %s)" % self.a, "sync: ok"])
        self.assertEqual(self.sync("claim", "--session", self.b, "--", self.entry)[1].splitlines()[0],
                         "claimed: %s" % self.entry)
        self.assertEqual(self.sync("claim", "--session", self.b, "--", self.entry)[1].splitlines()[0],
                         "claimed: %s (already)" % self.entry)

    def test_an_idle_session_keeps_its_claims(self):
        """No timer: a session that ran no tool for hours still holds its files."""
        self.assertEqual(self.sync("claim", "--session", self.a, "--", self.entry)[0], 0)
        path = logfiles.session_path(self.root, self.a)
        record = logfiles.read_session(self.root, self.a)
        record["start"] = "2000-01-01T00:00:00+00:00"
        logfiles.write_session(self.root, self.a, record)
        os.utime(path, (time.time() - 30 * 3600,) * 2)
        os.utime(os.path.dirname(path), (time.time() - 30 * 3600,) * 2)
        code, out = self.sync("claim", "--session", self.b, "--", self.entry)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "owned: %s (session %s)" % (self.entry, self.a))

    def test_a_baseline_file_is_refused_until_settled_and_then_lapses_everywhere(self):
        self.write(self.entry, "---\ntitle: Widget, left by an earlier session\n---\n")
        found = {self.entry: logfiles.file_hash(self.root, self.entry)}
        c = logfiles.new_session(self.root, found)
        d = logfiles.new_session(self.root, dict(found))
        code, out = self.sync("claim", "--session", c, "--", self.entry)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "baseline: %s (uncommitted when this session started)" % self.entry)
        self.assertIn("settle commit --session %s -- <file>" % c, out.splitlines()[-1])
        code, out = self.sync("commit", "--session", c, "log(widget): mine", "--", self.entry)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "held: %s (uncommitted when this session started)" % self.entry)
        code, out = self.sync("settle", "commit", "--session", c, "--", self.entry)   # on the user's yes
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed(), out)
        self.assertEqual(self.claims(c), [])   # a settle claims nothing
        self.write(self.entry, "---\ntitle: Widget, this session's\n---\n")
        for key in (c, d):   # the entry lapsed in every session's baseline once it matched HEAD
            code, out = self.sync("claim", "--session", key, "--", self.entry)
            self.assertEqual(code, 0, out)
            self.assertEqual(logfiles.read_session(self.root, key)["baseline"], {})
            self.sync("release", "--session", key, "--", self.entry)

    def test_settle_commit_still_holds_another_sessions_file(self):
        self.write(self.entry, "---\ntitle: Widget, the pack session's\n---\n")
        self.assertEqual(self.sync("claim", "--session", self.a, "--", self.entry)[0], 0)
        code, out = self.sync("settle", "commit", "--session", self.b)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "held: %s (session %s)" % (self.entry, self.a))

    def test_settle_discard_never_puts_back_a_claimed_file(self):
        self.write(self.entry, "---\ntitle: Widget, the pack session's\n---\n")
        self.assertEqual(self.sync("claim", "--session", self.a, "--", self.entry)[0], 0)
        for args in ((), ("--session", self.b)):
            code, out = self.sync("settle", "discard", *args, "--", self.entry)
            self.assertEqual(code, 1, out)
            self.assertEqual(out.splitlines()[0], "held: %s (session %s)" % (self.entry, self.a))
            self.assertEqual(self.git(self.root, "status", "--short"), " M %s\n" % self.entry)
        code, out = self.sync("settle", "discard", "--session", self.a, "--", self.entry)
        self.assertEqual(code, 0, out)

    def test_a_commit_without_session_stops_while_another_session_holds_claims(self):
        self.write("README.md", "# Log, edited\n")
        self.assertEqual(self.sync("claim", "--session", self.a, "--", "profile.md")[0], 0)
        for args in (("commit", "log: readme", "--", "README.md"), ("settle", "commit")):
            code, out = self.sync(*args)
            self.assertEqual(code, 1, out)
            self.assertEqual(out.splitlines()[0], "session: none given (session %s holds claims in this Log)" % self.a)
            self.assertIn("run this command again with --session <key>", out.splitlines()[-1])
            self.assertIn("`session:` line", out.splitlines()[-1])
        self.assertEqual(self.sync("end", "--session", self.a)[0], 0)
        code, out = self.sync("commit", "log: readme", "--", "README.md")   # nobody holds claims: as before
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed(), out)

    def test_run_stands_for_the_session_its_run_recorded(self):
        """For one release, `--run <key>` (a mode file's older line) commits as the session `scan.py run
        --session` recorded; a run that recorded none commits as no session."""
        run = "2031-01-02-100000"
        self.write(".build/runs/%s/session" % run, self.a + "\n")
        self.assertEqual(self.sync("claim", "--session", self.a, "--", self.entry)[0], 0)
        self.write(self.entry, "---\ntitle: Widget, the run's\n---\n")
        code, out = self.sync("commit", "--run", run, "write: save", "--", self.entry)
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed(), out)
        self.assertEqual(self.sync("end", "--session", self.a)[0], 0)
        self.write(self.entry, "---\ntitle: Widget, a later run's\n---\n")
        os.makedirs(os.path.join(self.root, ".build", "runs", "2031-01-02-110000"))
        code, out = self.sync("commit", "--run", "2031-01-02-110000", "write: save", "--", self.entry)
        self.assertEqual(code, 0, out)

    def test_an_unknown_session(self):
        code, out = self.sync("claim", "--session", "2031-01-02-100000", "--", self.entry)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "session: 2031-01-02-100000 unknown (no record of it in .build/sessions/)")

    def test_usage(self):
        for args in (("commit", "--run", "x", "x", "--", self.entry),
                     ("commit", "--session", "nope", "x", "--", self.entry),
                     ("commit", "--session", self.a, "--run", self.b, "x", "--", self.entry),
                     ("commit", "--take", self.entry, "x", "--", self.entry),   # --take went with time attribution
                     ("claim", "--", self.entry), ("claim", "--session", self.a), ("claim", "--session", self.a, "--"),
                     ("claim", "--session", self.a, "--", "tools/x.py"),
                     ("claim", "--session", self.a, "--", "sources/inbox/cv.txt"),
                     ("release", "--session", self.a), ("end",), ("end", "--session", self.a, "--", self.entry),
                     ("settle", "discard", "--session", "nope")):
            self.assertEqual(self.sync(*args)[0], 2, args)


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
        self.write("README.md", "# Theirs\n", root=other)
        self.git(other, "commit", "-q", "-am", "theirs")
        self.git(other, "push", "-q")
        self.write("README.md", "# Mine\n")
        self.git(self.root, "commit", "-q", "-am", "mine")
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
