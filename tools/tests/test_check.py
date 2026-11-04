#!/usr/bin/env python3
"""Tests for tools/check.py: what it prints for each machine.toml choice and tool state.

  python3 -I tools/tests/test_check.py

The tool states are faked, so the tests pass on any machine whatever it has installed.
"""
import datetime, http.server, importlib.util, io, json, os, shutil, socket, subprocess, sys, tempfile, threading, time, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "check.py")
spec = importlib.util.spec_from_file_location("check", TOOL)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

DEFAULTS = os.path.join(HERE, "..", "config.default.toml")
SCRIPTS = ("check.py", "resume.py", "entries.py", "logfiles.py", "config.py", "config.default.toml")

OK = (["x: ok"], [], [], [])
PDF = "next: when a step builds a PDF, first: "
MISSING = (["x: missing"], ["x"], [], [])


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.home, ignore_errors=True))
        self.saved_state = dict(check.STATE)
        self.addCleanup(lambda: check.STATE.update(self.saved_state))
        self.state(playwright_cli=OK, tinytex=OK)   # a test fakes the tool it is about
        self.saved_context = check.Context
        self.addCleanup(lambda: setattr(check, "Context", self.saved_context))
        home, root = self.home, os.path.join(self.home, "root")
        os.makedirs(root)
        shutil.copy(DEFAULTS, os.path.join(root, "config.toml"))   # setup has run for this Log
        check.Context = lambda mode, **_: self.saved_context(mode, root=root, home=home)
        for key in check.BROWSER_ENV:   # the machine's own; a test sets the one it is about
            if key in os.environ:
                self.addCleanup(os.environ.__setitem__, key, os.environ.pop(key))

    def machine(self, text):
        os.makedirs(os.path.join(self.home, ".career-log"))
        with open(os.path.join(self.home, ".career-log", "machine.toml"), "w") as f:
            f.write(text)

    def state(self, **states):
        for tool, value in states.items():
            check.STATE[tool.replace("_", "-")] = lambda ctx, value=value: value

    def run_check(self, mode):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check.main([mode])
        return code, out.getvalue().splitlines()

    def test_bad_mode(self):
        code, lines = self.run_check("deploy")
        self.assertEqual(code, 2)
        self.assertIn("usage:", lines[0])

    def test_help(self):
        """-h or --help anywhere prints the docstring and exits 0, as the other tools do (#227)."""
        for args in (["--help"], ["-h"], ["setup", "--help"], ["deploy", "-h"]):
            out = io.StringIO()
            with redirect_stdout(out):
                code = check.main(args)
            self.assertEqual(code, 0, args)
            self.assertEqual(out.getvalue().splitlines(), check.__doc__.rstrip().splitlines(), args)

    def test_mode_without_tools_goes_on(self):
        code, lines = self.run_check("log")
        self.assertEqual(code, 0)
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_leftover_tinytex_no_is_ignored(self):
        self.machine("tinytex = false\n")   # declined before TinyTeX was required
        self.state(tinytex=MISSING)
        code, lines = self.run_check("write")
        self.assertEqual(code, 0)   # write goes on until a step builds a PDF
        self.assertIn("tinytex: required", lines)
        run = [l for l in lines if l.startswith(PDF + "tinytex is part of this machine's setup")]
        self.assertEqual(len(run), 1)
        self.assertNotIn("-Yes" if os.name == "nt" else "--yes", run[0])
        self.assertIn("as a background command", run[0])
        self.assertFalse(any("ask the user" in l or "declined" in l or "stop:" in l for l in lines))
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_declined_soft_need_skips_without_offer(self):
        self.machine("playwright-cli = false\n")
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("rank")
        self.assertEqual(code, 0)
        off = [l for l in lines if "Browser capture is off on this machine" in l]
        self.assertEqual(len(off), 1)
        self.assertIn("Fallback order", off[0])
        self.assertFalse(any("ask the user" in l for l in lines))
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_declined_in_setup_is_a_state(self):
        """In setup, a declined tool is a state line, not a fallback step with nothing to do (#415)."""
        self.machine("playwright-cli = false\n")
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("setup")
        self.assertEqual(code, 0)
        wanted = [l for l in lines if l.startswith("playwright-cli wanted: ")]
        self.assertEqual(len(wanted), 1)
        self.assertTrue(wanted[0].startswith("playwright-cli wanted: no (declined) (Browser capture is off on this"
                                             " machine; nothing to do in setup unless the user asks to install it: `"),
                        wanted[0])
        self.assertFalse(any("playwright-cli" in l for l in lines if l.startswith("next:")), lines)
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_required_and_missing_runs_setup_without_asking(self):
        self.state(tinytex=MISSING)
        code, lines = self.run_check("write")
        self.assertEqual(code, 0)
        self.assertTrue(any(l.startswith(PDF + "tinytex is part of this machine's setup") for l in lines))
        self.assertFalse(any("ask the user" in l for l in lines))

    def test_soft_offer_waits_for_a_capture(self):
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("interview")
        self.assertEqual(code, 0)
        offer = [l for l in lines if "ask the user once" in l]
        self.assertTrue(offer[0].startswith("next: when a page needs a Browser capture"))
        yes, no = ("--yes playwright-cli", "--no playwright-cli") if os.name != "nt" else ("-Yes playwright-cli", "-No playwright-cli")
        self.assertIn(yes, offer[0])
        self.assertIn(no, offer[0])

    def test_chosen_and_missing_runs_setup_without_asking(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("rank")
        self.assertEqual(code, 0)
        run = [l for l in lines if "the user chose playwright-cli" in l]
        self.assertEqual(len(run), 1)
        self.assertIn("as a background command", run[0])
        self.assertFalse(any("ask the user" in l for l in lines))

    def test_all_ok(self):
        self.machine("playwright-cli = true\ntinytex = true\n")
        self.state(playwright_cli=OK, tinytex=OK)
        code, lines = self.run_check("setup")
        self.assertEqual(code, 0)
        self.assertEqual([l for l in lines if l.startswith("next:") and "career-log mode before" not in l],
                         ["next: go on with the mode"])

    def test_first_setup_does_not_call_the_tool_skipped(self):
        os.remove(os.path.join(self.home, "root", "config.toml"))
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("setup")
        self.assertIn("playwright-cli wanted: not asked", lines)
        self.assertFalse(any("skipped it in setup" in l or "ask the user" in l for l in lines))   # setup's round asks

    def test_setup_mode_lines_apply_now(self):
        self.state(playwright_cli=MISSING, tinytex=MISSING)
        code, lines = self.run_check("setup")
        self.assertFalse(any("ask the user once" in l for l in lines))   # skipped in setup: not asked again
        self.assertTrue(any("skipped it in setup" in l for l in lines))
        self.assertTrue(any(l.startswith("next: now, for tinytex, first: tinytex is part of") for l in lines))

    def test_now_step_that_reruns_the_check_holds_back_go_on(self):
        """A setup that left a tool missing does not end with `go on with the mode` (#314)."""
        cases = {"machine": (["x: missing"], ["x"], [], []),
                 "user": (["x: missing"], ["user:poppler:install poppler yourself"], [], []),
                 "sudo": (["x: missing"], ["sudo:a library:sudo install-a-library"], [], [])}
        for name, state in cases.items():
            self.state(tinytex=state)
            code, lines = self.run_check("setup")
            self.assertEqual(code, 0, name)
            self.assertNotIn("next: go on with the mode", lines, name)
            self.assertTrue(lines[-1].startswith("next: now, for tinytex, first: "), name)
            self.assertIn("run this check again", lines[-1], name)

    def test_now_step_without_a_rerun_goes_on(self):
        """`now` lines that need no rerun (a PATH line, the session check) leave `go on` last (#314)."""
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["node: ok but not on this shell's PATH"], [], [], ["/h/.nvm/versions/node/v22/bin"]))
        code, lines = self.run_check("setup")
        self.assertEqual(code, 0)
        self.assertTrue(any(l.startswith("next: now, for playwright-cli, first: start every command") for l in lines))
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_checkout_skill_installed_without_question(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["playwright-cli skill: missing"], [], ["skill"], []))
        code, lines = self.run_check("import")
        self.assertEqual(code, 0)
        install = [l for l in lines if "install --skills" in l and "with no question" in l]
        self.assertEqual(len(install), 1, lines)
        # #496: it also downloads FFmpeg into the Playwright cache when it is missing
        self.assertIn("files git ignores in this checkout and, when it is missing, about 3 MB of FFmpeg in"
                      " Playwright's cache.", install[0])

    def test_off_path_prints_the_path_line(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["node: ok but not on this shell's PATH"], [], [], ["/h/.nvm/versions/node/v22/bin"]))
        code, lines = self.run_check("rank")
        self.assertTrue(any("/h/.nvm/versions/node/v22/bin" in l for l in lines))

    def test_missing_pieces_read_as_one_sentence(self):
        """Each mix of machine pieces reads as a sentence: links broken, a tool missing, both (#277)."""
        local = os.path.join("/h", ".local", "bin")
        cases = [(["node"], "node is missing"),
                 (["node", "playwright-cli"], "node and playwright-cli are missing"),
                 (["old node", "playwright-cli", "browser"], "node is too old and playwright-cli and a browser are missing"),
                 (["links in %s" % local], "the links in %s are missing" % local),
                 (["broken links in %s" % local], "the links in %s are broken" % local),
                 (["broken links in %s" % local, "playwright-cli"],
                  "the links in %s are broken and playwright-cli is missing" % local),
                 (["pdflatex", "poppler"], "pdflatex and poppler are missing"),
                 (["Chromium's system libraries"], "Chromium's system libraries are missing")]
        for items, sentence in cases:
            self.assertEqual(check.missing_clause(items), sentence, items)

    def test_broken_links_and_missing_cli_next_line(self):
        """The Browser capture next: line of #277: broken links plus a missing playwright-cli."""
        local = os.path.join(self.home, ".local", "bin")
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["playwright-cli: missing"], ["broken links in %s" % local, "playwright-cli"], [], []))
        code, lines = self.run_check("rank")
        line = [l for l in lines if l.startswith("next: when a page needs a Browser capture")]
        self.assertEqual(len(line), 1, lines)
        self.assertIn("first: the user chose playwright-cli on this machine, and the links in %s are broken and"
                      " playwright-cli is missing: run `" % local, line[0])

    def test_sudo_piece_prints_the_command_for_the_user(self):
        self.state(tinytex=(["x: missing"], ["sudo:a library:sudo install-a-library"], [], []))
        code, lines = self.run_check("write")
        line = [l for l in lines if "sudo install-a-library" in l]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0].startswith(PDF + "stop: missing: a library"))
        self.assertIn("in their own terminal", line[0])
        self.assertFalse(any("setup.sh" in l or "setup.ps1" in l for l in lines))

    def test_user_piece_is_told_not_installed(self):
        self.state(tinytex=(["x: missing"], ["user:a library:install a library yourself"], [], []))
        code, lines = self.run_check("write")
        self.assertTrue(any(l.startswith(PDF + "stop: missing: a library") and "Tell the user to install a library yourself" in l
                            for l in lines))

    def unattended(self):
        self.addCleanup(setattr, check, "UNATTENDED", check.UNATTENDED)
        check.UNATTENDED = True

    def test_unattended_run_installs_and_asks_nothing(self):
        self.unattended()
        self.machine("playwright-cli = true\n")
        self.state(tinytex=MISSING, playwright_cli=MISSING)
        for mode, prefix in (("write", PDF + "stop: setup is needed on this machine: x is missing"),
                             ("rank", "next: when a page needs a Browser capture (item 2 of browser.md, Fallback order),"
                                      " first: setup is needed on this machine: x is missing")):
            code, lines = self.run_check(mode)
            self.assertEqual(code, 0)
            self.assertTrue(any(l.startswith(prefix) for l in lines), lines)
            self.assertFalse(any("ask the user" in l or "setup.sh" in l or "setup.ps1" in l for l in lines), lines)

    def test_unattended_run_defers_an_offer(self):
        self.unattended()
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("rank")
        line = [l for l in lines if "playwright-cli is not offered on this machine yet" in l]
        self.assertEqual(len(line), 1)
        self.assertIn("Fallback order", line[0])
        self.assertFalse(any("ask the user" in l or "setup.sh" in l or "setup.ps1" in l for l in lines))
        code, lines = self.run_check("setup")
        self.assertTrue(any("skipped it in setup" in l for l in lines))   # as when attended

    def test_offer_runs_setup_in_the_background(self):
        self.state(playwright_cli=MISSING)
        code, lines = self.run_check("rank")
        offer = [l for l in lines if "ask the user once" in l][0]
        self.assertIn("as a background command", offer)
        self.assertNotIn("no administrator prompt", offer)

    def test_unattended_sudo_piece_is_not_given_to_anyone(self):
        self.unattended()
        self.state(tinytex=(["x: missing"], ["sudo:a library:sudo install-a-library"], [], []))
        code, lines = self.run_check("write")
        self.assertTrue(any(l.startswith(PDF + "stop: setup is needed on this machine: a library is missing") for l in lines))
        self.assertFalse(any("install-a-library" in l for l in lines))

    def test_unreadable_machine_toml_stops(self):
        self.machine("playwright-cli = maybe\n")
        code, lines = self.run_check("rank")
        self.assertEqual(code, 1)
        self.assertTrue(lines[-1].startswith("next: stop:"))

    def test_old_python_stops_before_tomllib(self):
        class FakeSys:
            version_info = (3, 9, 6, "final", 0)
            executable = "/usr/bin/python3"
        real, real_newer = check.sys, check.newer_pythons
        check.sys, check.newer_pythons = FakeSys, lambda home: []
        try:
            lines, nexts, stop = check.check_python(check.Context("write"))
        finally:
            check.sys, check.newer_pythons = real, real_newer
        self.assertTrue(stop)
        self.assertIn("too old (3.9.6", lines[0])
        self.assertTrue(nexts[0].startswith("next: stop: setup is not done"))
        self.assertIn("as a background command", nexts[0])
        self.unattended()
        check.sys, check.newer_pythons = FakeSys, lambda home: []
        try:
            lines, nexts, stop = check.check_python(check.Context("write"))
        finally:
            check.sys, check.newer_pythons = real, real_newer
        self.assertTrue(nexts[0].startswith("next: stop: setup is needed on this machine"))
        self.assertNotIn("Ask the user", nexts[0])

    def test_old_python_points_at_a_newer_one(self):
        bindir = os.path.join(self.home, ".local", "bin")
        os.makedirs(bindir)
        newer = os.path.join(bindir, "python3.13")
        open(newer, "w").close()
        os.chmod(newer, 0o755)
        if os.name == "nt":
            self.skipTest("Windows looks in %LOCALAPPDATA%, not ~/.local/bin")
        self.assertEqual(check.newer_pythons(self.home), [newer])

    @unittest.skipUnless(os.name == "nt", "the winget zip layout is Windows's")
    def test_playwright_cli_in_wingets_node_folder(self):
        local = os.path.join(self.home, "Local")
        node_dir = os.path.join(local, "Microsoft", "WinGet", "Packages", "OpenJS.NodeJS.LTS_x", "node-v24.0.0-win-x64")
        os.makedirs(node_dir)
        open(os.path.join(node_dir, "playwright-cli.cmd"), "w").close()
        saved = {k: os.environ.get(k) for k in ("LOCALAPPDATA", "APPDATA", "PATH")}
        os.environ.update(LOCALAPPDATA=local, APPDATA=os.path.join(self.home, "Roaming"), PATH="")
        try:
            path, on_path = check.which("playwright-cli", check.npm_bin_dirs(self.home))
        finally:
            os.environ.update(saved)
        self.assertEqual((os.path.dirname(path), on_path), (node_dir, False))

    def nvm_node(self, version):
        """A fake nvm Node `version` in the fake home; returns its bin folder."""
        d = os.path.join(self.home, ".nvm", "versions", "node", version, "bin")
        os.makedirs(d)
        with open(os.path.join(d, "node"), "w") as f:
            f.write("#!/bin/sh\necho %s.0.0\n" % version.split(".")[0])
        os.chmod(os.path.join(d, "node"), 0o755)
        return d

    def no_path(self):
        saved = os.environ.get("PATH")
        os.environ["PATH"] = ""
        self.addCleanup(lambda: os.environ.update(PATH=saved))

    @unittest.skipIf(os.name == "nt", "nvm is macOS's and Linux's")
    def test_nvm_versions_newest_first_after_the_links(self):
        for v in ("v8.0.0", "v22.1.0", "v20.0.0"):
            self.nvm_node(v)
        names = [os.path.basename(os.path.dirname(d)) for d in check.node_dirs(self.home)[1:]]
        self.assertEqual(names, ["v22.1.0", "v20.0.0", "v8.0.0"])
        self.assertEqual(check.node_dirs(self.home)[0], os.path.join(self.home, ".local", "bin"))

    @unittest.skipIf(os.name == "nt", "nvm is macOS's and Linux's")
    def test_unlinked_nvm_node_runs_setup_for_the_links(self):
        self.nvm_node("v22.1.0")
        self.no_path()
        lines, machine, _, off_path = check.playwright_state(self.saved_context("setup", root=self.home, home=self.home))
        self.assertTrue(any("setup links it into" in l for l in lines), lines)
        self.assertIn("links in %s" % os.path.join(self.home, ".local", "bin"), machine)
        self.assertEqual(off_path, [])

    @unittest.skipIf(os.name == "nt", "nvm is macOS's and Linux's")
    def test_linked_node_off_path_prints_local_bin(self):
        d = self.nvm_node("v22.1.0")
        local = os.path.join(self.home, ".local", "bin")
        os.makedirs(local)
        os.symlink(os.path.join(d, "node"), os.path.join(local, "node"))
        self.no_path()
        lines, machine, _, off_path = check.playwright_state(self.saved_context("setup", root=self.home, home=self.home))
        self.assertIn("node: ok but not on this shell's PATH (%s)" % os.path.join(local, "node"), lines)
        self.assertEqual(off_path, [local])
        self.assertFalse([m for m in machine if "link" in m], machine)

    @unittest.skipIf(os.name == "nt", "nvm is macOS's and Linux's")
    def test_broken_link_runs_setup(self):
        self.nvm_node("v22.1.0")
        local = os.path.join(self.home, ".local", "bin")
        os.makedirs(local)
        gone = os.path.join(self.home, ".nvm", "versions", "node", "v20.0.0", "bin", "node")
        os.symlink(gone, os.path.join(local, "node"))
        self.no_path()
        lines, machine, _, _ = check.playwright_state(self.saved_context("setup", root=self.home, home=self.home))
        self.assertIn("%s: broken link (%s was uninstalled)" % (os.path.join(local, "node"), gone), lines)
        self.assertEqual([m for m in machine if "links in" in m], ["broken links in %s" % local], machine)

    @unittest.skipIf(os.name == "nt", "nvm is macOS's and Linux's")
    def test_users_own_node_link_is_left_to_the_path_line(self):
        d = self.nvm_node("v22.1.0")
        local = os.path.join(self.home, ".local", "bin")
        os.makedirs(local)
        os.symlink("/opt/elsewhere/node", os.path.join(local, "node"))   # not setup's, and dangling
        self.no_path()
        lines, machine, _, off_path = check.playwright_state(self.saved_context("setup", root=self.home, home=self.home))
        self.assertFalse([l for l in lines if "broken link" in l or "setup links" in l], lines)
        self.assertFalse([m for m in machine if "link" in m], machine)
        self.assertEqual(off_path, [d])

    def browser_roots(self, *installed):
        """Fake %LOCALAPPDATA%, %ProgramFiles% and %ProgramFiles(x86)%, the real Edge or Chrome hidden;
        `installed` names files to create under them, as (root key, path parts). Each call starts empty."""
        keys = ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)")
        saved = {k: os.environ.get(k) for k in keys}
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.update({k: v})
                                 for k, v in saved.items()])
        base = tempfile.mkdtemp(dir=self.home)
        os.environ.update({k: os.path.join(base, k) for k in keys})
        for key, parts in installed:
            path = os.path.join(base, key, *parts)
            os.makedirs(os.path.dirname(path))
            open(path, "w").close()

    @unittest.skipUnless(os.name == "nt", "Edge stands in for Chrome on Windows only")
    def test_edge_found_in_any_root(self):
        self.browser_roots()
        self.assertFalse(check.edge_installed())
        for key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            self.browser_roots((key, ("Microsoft", "Edge", "Application", "msedge.exe")))
            self.assertTrue(check.edge_installed(), key)
        self.assertFalse(check.chrome_installed())

    def browser_state(self, chrome, edge):
        """playwright_state with Chrome and Edge faked, in a checkout with no config and an empty cache."""
        saved = check.chrome_installed, check.edge_installed, check.pinned_chromium
        check.chrome_installed, check.edge_installed = (lambda: chrome), (lambda: edge)
        check.pinned_chromium = lambda cli: self.PINNED
        saved_env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(self.home, "ms-playwright")
        try:
            return check.playwright_state(self.saved_context("setup", root=self.home, home=self.home))
        finally:
            check.chrome_installed, check.edge_installed, check.pinned_chromium = saved
            os.environ.pop("PLAYWRIGHT_BROWSERS_PATH") if saved_env is None else os.environ.update(PLAYWRIGHT_BROWSERS_PATH=saved_env)

    def test_edge_without_chrome_is_the_browser(self):
        lines, machine, checkout, _ = self.browser_state(chrome=False, edge=True)
        self.assertIn("browser: ok (Edge)", lines)
        self.assertNotIn("browser", machine)
        self.assertIn("playwright-cli config: missing (this checkout; picks Edge when Chrome is missing)", lines)
        self.assertIn("config", checkout)   # install --skills writes `"channel": "msedge"` into it

    def test_chrome_wins_over_edge(self):
        lines, machine, checkout, _ = self.browser_state(chrome=True, edge=True)
        self.assertIn("browser: ok (Chrome)", lines)
        self.assertNotIn("config", checkout)

    def test_no_browser_runs_setup(self):
        lines, machine, _, _ = self.browser_state(chrome=False, edge=False)
        missing = [l for l in lines if l.startswith("browser: missing (no Chrome")]
        self.assertTrue(missing, lines)
        self.assertIn(", no Edge,", missing[0])
        self.assertIn("browser", machine)

    def cli_config(self, where, text):
        """A playwright-cli config in the checkout (`checkout`) or the scratch home (`global`)."""
        path = os.path.join(self.home, "root" if where == "checkout" else "", ".playwright", "cli.config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text if isinstance(text, str) else __import__("json").dumps(text))
        return os.path.normpath(path)

    PINNED = [["chromium-1200"], ["chromium_headless_shell-1200"]]

    def config_state(self, chrome=False, edge=False, chromium=False, folders=(), pinned=PINNED, cli=True):
        """playwright_state with Chrome and Edge faked, Playwright's cache a scratch folder holding
        `folders` (and with `chromium`, PINNED's two), the revisions playwright-cli pins faked as
        `pinned`, a playwright-cli found or not (`cli`), the checkout `root` and the global config
        under the scratch home."""
        cache = os.path.join(self.home, "ms-playwright")
        for folder in list(folders) + (["chromium-1200", "chromium_headless_shell-1200"] if chromium else []):
            os.makedirs(os.path.join(cache, folder))
            open(os.path.join(cache, folder, "INSTALLATION_COMPLETE"), "w").close()
        saved_env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = cache
        saved = check.chrome_installed, check.edge_installed, check.pinned_chromium
        check.chrome_installed, check.edge_installed = (lambda: chrome), (lambda: edge)
        check.pinned_chromium = lambda path: pinned
        which, found = check.which, cli
        check.which = lambda name, dirs: (("/fake/playwright-cli", True) if found else (None, False)) \
            if name == "playwright-cli" else which(name, dirs)
        try:
            return check.playwright_state(self.saved_context("setup", root=os.path.join(self.home, "root"), home=self.home))
        finally:
            check.chrome_installed, check.edge_installed, check.pinned_chromium = saved
            check.which = which
            os.environ.pop("PLAYWRIGHT_BROWSERS_PATH") if saved_env is None else os.environ.update(PLAYWRIGHT_BROWSERS_PATH=saved_env)

    def config_line(self, lines):
        found = [l for l in lines if l.startswith("playwright-cli config:")]
        return found[0] if found else None

    EDGE_CONFIG = {"browser": {"browserName": "chromium", "launchOptions": {"channel": "msedge"}}}
    CHROMIUM_CONFIG = {"browser": {"browserName": "chromium", "launchOptions": {}}}

    def test_no_config_with_chrome_prints_no_config_line(self):
        lines, _, checkout, _ = self.config_state(chrome=True)
        self.assertIsNone(self.config_line(lines))
        self.assertEqual(checkout, ["skill"])

    def test_checkout_config_naming_edge_with_edge(self):
        self.cli_config("checkout", self.EDGE_CONFIG)
        lines, _, checkout, _ = self.config_state(edge=True)
        self.assertEqual(self.config_line(lines), "playwright-cli config: ok (this checkout; Edge)")
        self.assertEqual(checkout, ["skill"])

    def test_checkout_config_naming_edge_without_edge(self):
        path = self.cli_config("checkout", self.EDGE_CONFIG)
        lines, _, checkout, _ = self.config_state(chrome=True)
        self.assertEqual(self.config_line(lines),
                         "playwright-cli config: browser missing (this checkout; names Edge, not installed)")
        (kind, fact, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertIn(path, fact)
        self.assertIn("delete it and run `playwright-cli install --skills`", question)
        self.assertIn("which then picks Chrome", question)
        self.assertIn("or to install Edge themselves", question)

    def test_config_with_no_channel_and_no_chromium(self):
        self.cli_config("checkout", self.CHROMIUM_CONFIG)
        lines, machine, checkout, _ = self.config_state(chrome=True)
        self.assertIn("browser: ok (Chrome)", lines)
        self.assertNotIn("browser", machine)
        self.assertTrue(self.config_line(lines).startswith(
            "playwright-cli config: browser missing (this checkout; names Chromium, not in %s" % os.path.join(self.home, "ms-playwright")))
        (_, _, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertIn("which downloads Chromium into Playwright's cache", question)
        self.assertEqual("(about 320 MB)" in question, check.WINDOWS)
        self.assertIn("delete it", question)   # Chrome is here: the config can go instead

    def test_config_with_no_channel_and_chromium(self):
        self.cli_config("checkout", self.CHROMIUM_CONFIG)
        lines, _, checkout, _ = self.config_state(chromium=True)
        self.assertEqual(self.config_line(lines), "playwright-cli config: ok (this checkout; Chromium)")
        self.assertEqual(checkout, ["skill"])

    def browser_line(self, lines):
        found = [l for l in lines if l.startswith("browser:")]
        return found[0] if found else None

    def test_pinned_chromium_is_the_browser(self):
        lines, machine, _, _ = self.config_state(chromium=True)
        self.assertEqual(self.browser_line(lines), "browser: ok (chromium-1200 and chromium_headless_shell-1200 in %s)"
                         % os.path.join(self.home, "ms-playwright"))
        self.assertNotIn("browser", machine)

    def test_stale_chromium_is_missing(self):
        """An old revision left after an update of playwright-cli is not what it launches (#228)."""
        self.cli_config("checkout", self.CHROMIUM_CONFIG)
        lines, machine, _, _ = self.config_state(folders=["chromium-1100", "chromium_headless_shell-1100"])
        line = self.browser_line(lines)
        self.assertTrue(line.startswith("browser: missing (no Chrome"), line)
        self.assertIn("no chromium-1200 and chromium_headless_shell-1200 in", line)
        self.assertIn("; found chromium-1100, chromium_headless_shell-1100, which this playwright-cli does not launch", line)
        self.assertIn("browser", machine)   # setup's install-browser downloads the pinned revision
        self.assertTrue(self.config_line(lines).startswith("playwright-cli config: browser missing (this checkout; names Chromium"))

    def test_chromium_without_its_headless_shell_is_missing(self):
        lines, machine, _, _ = self.config_state(folders=["chromium-1200"])
        line = self.browser_line(lines)
        self.assertTrue(line.startswith("browser: missing ("), line)
        self.assertIn("no chromium_headless_shell-1200 in", line)
        self.assertNotIn("chromium-1200", line)   # it is there; only what is missing is named
        self.assertNotIn("found", line)
        self.assertIn("browser", machine)

    def test_revision_override_folder_counts(self):
        pinned = [["chromium-1200", "chromium_mac14_special-1190"],
                  ["chromium_headless_shell-1200", "chromium_headless_shell_mac14_special-1190"]]
        lines, machine, _, _ = self.config_state(
            folders=["chromium_mac14_special-1190", "chromium_headless_shell_mac14_special-1190"], pinned=pinned)
        self.assertEqual(self.browser_line(lines), "browser: ok (chromium_mac14_special-1190 and"
                         " chromium_headless_shell_mac14_special-1190 in %s)" % os.path.join(self.home, "ms-playwright"))
        self.assertNotIn("browser", machine)

    def test_no_browsers_json_is_not_ok(self):
        """With no revision to compare with, a Chromium in the cache is printed without `ok`, and setup
        is not run for it."""
        self.cli_config("checkout", self.CHROMIUM_CONFIG)
        lines, machine, checkout, _ = self.config_state(folders=["chromium-1100"], pinned=None)
        cache = os.path.join(self.home, "ms-playwright")
        reason = "playwright-cli's playwright-core has no readable browsers.json to give the revision it launches"
        self.assertEqual(self.browser_line(lines), "browser: present (Chromium in %s; %s)" % (cache, reason))
        self.assertNotIn("browser", machine)
        self.assertEqual(self.config_line(lines), "playwright-cli config: present (this checkout; Chromium, in %s; %s)"
                         % (cache, reason))
        self.assertEqual(checkout, ["skill"])

    def test_chromium_with_no_playwright_cli_is_not_ok(self):
        lines, machine, _, _ = self.config_state(folders=["chromium-1100"], pinned=None, cli=False)
        self.assertEqual(self.browser_line(lines), "browser: present (Chromium in %s; its revision is checked once"
                         " playwright-cli is installed)" % os.path.join(self.home, "ms-playwright"))
        self.assertIn("playwright-cli", machine)
        self.assertNotIn("browser", machine)

    def test_no_browsers_json_and_no_chromium_is_missing(self):
        lines, machine, _, _ = self.config_state(pinned=None)
        self.assertTrue(self.browser_line(lines).startswith("browser: missing (no Chrome"), lines)
        self.assertIn("no Chromium in", self.browser_line(lines))
        self.assertIn("browser", machine)

    def fake_cli(self, browsers):
        """A playwright-cli in a scratch npm folder, with playwright-core's browsers.json holding
        `browsers` (a str is written as is; None writes no file). Returns the command's path."""
        npm = os.path.join(self.home, "npm")
        core = os.path.join(npm, "node_modules", "@playwright", "cli", "node_modules", "playwright-core")
        os.makedirs(core)
        open(os.path.join(core, "cli.js"), "w").close()
        if browsers is not None:
            with open(os.path.join(core, "browsers.json"), "w", encoding="utf-8") as f:
                f.write(browsers if isinstance(browsers, str) else __import__("json").dumps({"browsers": browsers}))
        cli = os.path.join(npm, "playwright-cli.cmd")
        open(cli, "w").close()
        return cli

    def test_pinned_chromium_reads_browsers_json(self):
        cli = self.fake_cli([{"name": "chromium", "revision": "1247"},
                             {"name": "chromium-headless-shell", "revision": "1247", "revisionOverrides": {"mac14": "1200"}},
                             {"name": "webkit", "revision": "2368"}])
        self.assertEqual(check.pinned_chromium(cli), [["chromium-1247"],
                         ["chromium_headless_shell-1247", "chromium_headless_shell_mac14_special-1200"]])

    def test_pinned_chromium_none_without_a_readable_browsers_json(self):
        self.assertIsNone(check.pinned_chromium(None))
        self.assertIsNone(check.pinned_chromium(self.fake_cli(None)))
        for browsers in ("{not json", "[]", [{"name": "chromium", "revision": "1247"}]):
            shutil.rmtree(os.path.join(self.home, "npm"))
            self.assertIsNone(check.pinned_chromium(self.fake_cli(browsers)), browsers)

    def test_macos_chrome_only_in_applications(self):
        """playwright-core's chrome channel looks in /Applications only, not in ~/Applications (#228)."""
        from unittest import mock
        app = "/Applications/Google Chrome.app"
        for exists, found in (({os.path.expanduser("~" + app)}, False), ({app}, True)):
            with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check.platform, "system", lambda: "Darwin"), \
                    mock.patch.object(check.os.path, "exists", lambda p, exists=exists: p in exists):
                self.assertEqual(check.chrome_installed(), found, exists)

    def test_macos_chrome_in_home_applications_runs_setup(self):
        """setup.sh counts only /Applications' Chrome, so it downloads Chromium for this one (#242)."""
        from unittest import mock
        app = os.path.join(self.home, "Applications", "Google Chrome.app")
        os.makedirs(app)
        with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check, "LINUX", False), \
                mock.patch.object(check.platform, "system", lambda: "Darwin"):
            lines, machine, _, _ = self.config_state()
        self.assertTrue(self.browser_line(lines).startswith(
            "browser: missing (Chrome is in %s, not in /Applications, where playwright-cli looks; no chromium-1200" % app), lines)
        self.assertIn("browser", machine)
        self.assertFalse([m for m in machine if m.startswith("user:")], machine)

    def test_macos_config_naming_chrome_in_home_applications(self):
        from unittest import mock
        app = os.path.join(self.home, "Applications", "Google Chrome.app")
        os.makedirs(app)
        self.cli_config("checkout", {"browser": {"browserName": "chromium", "launchOptions": {"channel": "chrome"}}})
        with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check, "LINUX", False), \
                mock.patch.object(check.platform, "system", lambda: "Darwin"):
            lines, machine, checkout, _ = self.config_state()
        self.assertEqual(self.config_line(lines), "playwright-cli config: browser missing (this checkout; names Chrome,"
                         " not in /Applications, where playwright-cli looks (it is in %s))" % app)
        (_, _, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertIn("move %s into /Applications" % app, question)
        self.assertNotIn("install Chrome themselves", question)
        self.assertNotIn("browser", machine)   # no Chromium download before the config line asks about the move
        self.assertFalse([m for m in machine if m.startswith("user:")], machine)

    def test_no_browser_offers_only_the_download(self):
        self.cli_config("checkout", self.CHROMIUM_CONFIG)
        _, _, checkout, _ = self.config_state()
        (_, _, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertNotIn("delete", question)

    def test_global_config_only_counts(self):
        path = self.cli_config("global", self.EDGE_CONFIG)
        lines, _, checkout, _ = self.config_state(edge=True)
        self.assertEqual(self.config_line(lines), "playwright-cli config: ok (global, %s; Edge)" % path)
        self.assertNotIn("config", checkout)

    def test_global_config_with_its_browser_missing_is_not_offered_for_deletion(self):
        self.cli_config("global", self.CHROMIUM_CONFIG)
        lines, _, checkout, _ = self.config_state(chrome=True)
        self.assertIn("browser missing (global, ", self.config_line(lines))
        (_, _, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertNotIn("delete", question)

    def test_checkout_config_over_global(self):
        self.cli_config("global", self.CHROMIUM_CONFIG)
        path = self.cli_config("checkout", self.EDGE_CONFIG)
        lines, _, _, _ = self.config_state(edge=True)
        self.assertEqual(self.config_line(lines), "playwright-cli config: ok (this checkout, over the global %s; Edge)"
                         % os.path.normpath(os.path.join(self.home, ".playwright", "cli.config.json")))

    def test_config_browser_merges_as_playwright_core(self):
        cb = check.config_browser
        self.assertEqual(cb([{}]), "Chrome")   # no browserName: playwright-core launches Chrome
        self.assertEqual(cb([{"browser": {"launchOptions": {"channel": "msedge"}}}]), "Chrome")
        self.assertEqual(cb([self.CHROMIUM_CONFIG]), "Chromium")
        self.assertEqual(cb([{"browser": {"browserName": "chromium", "launchOptions": {"channel": "chrome"}}}]), "Chrome")
        self.assertEqual(cb([self.CHROMIUM_CONFIG, self.EDGE_CONFIG]), "Edge")   # the checkout's over the global
        self.assertEqual(cb([self.EDGE_CONFIG, self.CHROMIUM_CONFIG]), "Edge")   # the global's channel stays
        # a global channel with no browserName is dropped before the checkout's browserName comes in
        self.assertEqual(cb([{"browser": {"launchOptions": {"channel": "msedge"}}}, self.CHROMIUM_CONFIG]), "Chromium")
        self.assertEqual(cb([{"browser": {"browserName": "firefox"}}]), 'browserName "firefox"')
        self.assertEqual(cb([{"browser": {"browserName": "chromium", "launchOptions": {"channel": "chrome-beta"}}}]),
                         'channel "chrome-beta"')
        self.assertEqual(cb([{"browser": {"launchOptions": {"executablePath": "/x/chrome"}}}]), "executablePath")
        self.assertEqual(cb([{"browser": {"cdpEndpoint": "http://localhost:9222"}}]), "cdpEndpoint")
        self.assertEqual(cb([{"browser": "x"}]), "Chrome")   # a browser that is no object is ignored

    def test_config_this_check_does_not_read_says_so(self):
        for text in ({"browser": {"browserName": "webkit"}}, "[browser]\nbrowserName = webkit\n"):
            self.cli_config("checkout", text)
            lines, _, checkout, _ = self.config_state(chrome=True)
            self.assertTrue(self.config_line(lines).startswith("playwright-cli config: present (this checkout; it sets "), lines)
            self.assertEqual(checkout, ["skill"])

    def test_config_with_a_bom_is_read(self):
        self.cli_config("checkout", "﻿" + __import__("json").dumps(self.EDGE_CONFIG))
        lines, _, _, _ = self.config_state(edge=True)
        self.assertEqual(self.config_line(lines), "playwright-cli config: ok (this checkout; Edge)")

    def test_unreadable_config_asks(self):
        path = self.cli_config("checkout", '{"browser": ')
        lines, _, checkout, _ = self.config_state(chrome=True)
        self.assertTrue(self.config_line(lines).startswith("playwright-cli config: unreadable (%s: " % path))
        (_, fact, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertIn("cannot start with its config", fact)
        self.assertIn("writes a new one", question)

    def test_unreadable_global_config_stays_the_users(self):
        self.cli_config("global", "{NaN")
        lines, _, checkout, _ = self.config_state(chrome=True)
        self.assertIn("unreadable (", self.config_line(lines))
        (_, _, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertIn("it is global", question)
        self.assertNotIn("delete", question)

    def test_json_javascript_rejects_is_unreadable(self):
        for text in ('{"browser": {"browserName": NaN}}', "null"):
            self.cli_config("checkout", text)
            lines, _, _, _ = self.config_state(chrome=True)
            self.assertIn("unreadable (", self.config_line(lines), text)

    def test_null_channel_overrides_the_global_one(self):
        self.assertEqual(check.config_browser(
            [self.EDGE_CONFIG, {"browser": {"browserName": "chromium", "launchOptions": {"channel": None}}}]), "Chromium")

    def test_browser_set_in_the_environment_is_not_judged(self):
        self.cli_config("checkout", self.EDGE_CONFIG)
        saved = os.environ.get("PLAYWRIGHT_MCP_BROWSER")
        os.environ["PLAYWRIGHT_MCP_BROWSER"] = "firefox"
        self.addCleanup(lambda: os.environ.pop("PLAYWRIGHT_MCP_BROWSER") if saved is None
                        else os.environ.update(PLAYWRIGHT_MCP_BROWSER=saved))
        lines, _, checkout, _ = self.config_state()
        self.assertEqual(self.config_line(lines),
                         "playwright-cli config: present (this checkout; PLAYWRIGHT_MCP_BROWSER is set, which this check does not look for)")
        self.assertEqual(checkout, ["skill"])

    def test_config_naming_chrome_with_no_browser_offers_the_delete(self):
        self.cli_config("checkout", {"browser": {"browserName": "chromium", "launchOptions": {"channel": "chrome"}}})
        _, _, checkout, _ = self.config_state()
        (_, _, question), = [c for c in checkout if isinstance(c, tuple)]
        self.assertIn("delete it and run `playwright-cli install --skills`", question)
        self.assertIn("which then downloads Chromium", question)
        self.assertIn("or to install Chrome themselves", question)

    def test_edge_found_at_playwright_core_paths_off_windows(self):
        """playwright-cli picks Edge at these paths on macOS and Linux too (#196)."""
        from unittest import mock
        edge = os.path.join(self.home, "msedge")
        for system in ("Darwin", "Linux"):
            with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check.platform, "system", lambda: system), \
                    mock.patch.dict(check.EDGE_PATHS, {system: [edge]}):
                self.assertFalse(check.edge_installed(), system)
                open(edge, "w").close()
                self.assertTrue(check.edge_installed(), system)
                os.remove(edge)
        self.assertEqual(check.EDGE_PATHS, {"Darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
                                            "Linux": ["/opt/microsoft/msedge/msedge"]})

    def test_linux_edge_skips_the_libraries_step(self):
        """Edge's package brings the libraries; Chromium's would only be asked for with no Chrome or Edge."""
        from unittest import mock
        node = os.path.join(self.home, "node")
        for folder in ("chromium-1200", "chromium_headless_shell-1200"):   # PINNED, so no browser step
            os.makedirs(os.path.join(self.home, "ms-playwright", folder))
            open(os.path.join(self.home, "ms-playwright", folder, "INSTALLATION_COMPLETE"), "w").close()
        for edge, asked in ((True, False), (False, True)):
            with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check, "LINUX", True), \
                    mock.patch.object(check, "missing_libraries", lambda home, pinned: True), \
                    mock.patch.object(check, "node_version", lambda n: (20, "v20.0.0")), \
                    mock.patch.object(check, "playwright_core_cli", lambda cli: "/fake/core/cli.js"), \
                    mock.patch.object(check, "which", lambda name, dirs: (node if name == "node" else "/fake/playwright-cli", True)):
                lines, machine, _, _ = self.browser_state(chrome=False, edge=edge)
            self.assertEqual(any(m.startswith("sudo:Chromium's system libraries:") for m in machine), asked, machine)
            self.assertEqual("browser libraries: missing (needs sudo)" in lines, asked, lines)

    def test_linux_libraries_without_playwright_core_download_no_browser(self):
        """With no playwright-core to run install-deps, the user reinstalls playwright-cli (#496): the old
        `install-browser --with-deps` fallback, run with sudo, downloaded browsers into root's cache."""
        from unittest import mock
        node = os.path.join(self.home, "node")
        for folder in ("chromium-1200", "chromium_headless_shell-1200"):
            os.makedirs(os.path.join(self.home, "ms-playwright", folder))
            open(os.path.join(self.home, "ms-playwright", folder, "INSTALLATION_COMPLETE"), "w").close()
        cli = os.path.join(self.home, "bin", "playwright-cli")
        for core, user in (("/fake/core/cli.js", False), (None, True)):
            with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check, "LINUX", True), \
                    mock.patch.object(check, "missing_libraries", lambda home, pinned: True), \
                    mock.patch.object(check, "node_version", lambda n: (20, "v20.0.0")), \
                    mock.patch.object(check, "playwright_core_cli", lambda c: core), \
                    mock.patch.object(check, "which", lambda name, dirs: (node if name == "node" else cli, True)):
                lines, machine, _, _ = self.browser_state(chrome=False, edge=False)
            libs = [m for m in machine if "Chromium's system libraries" in m]
            self.assertEqual(len(libs), 1, machine)
            self.assertFalse(any("install-browser" in m or "--with-deps" in m for m in machine), machine)
            if user:
                where = os.path.dirname(os.path.realpath(cli))
                self.assertIn("browser libraries: missing (playwright-core not found in %s)" % where, lines)
                self.assertEqual(libs[0], "user:Chromium's system libraries:reinstall playwright-cli with"
                                 " `npm install -g @playwright/cli@latest`, since playwright-core, whose"
                                 " install-deps installs them, is not in %s" % where)
            else:
                self.assertIn("browser libraries: missing (needs sudo)", lines)
                self.assertEqual(libs[0], "sudo:Chromium's system libraries:sudo %s /fake/core/cli.js install-deps"
                                 " chromium" % node)

    def test_linux_config_naming_chromium_checks_the_libraries_with_chrome_or_edge(self):
        """A config naming Chromium launches it even with Chrome or Edge installed (#255)."""
        from unittest import mock
        node = os.path.join(self.home, "node")
        cases = [(browser, config, chromium, config == self.CHROMIUM_CONFIG and chromium is not False)
                 for browser in ("chrome", "edge")
                 for config in (self.CHROMIUM_CONFIG, self.EDGE_CONFIG,
                                {"browser": {"browserName": "chromium", "launchOptions": {"channel": "chrome"}}}, None)
                 for chromium in (True, False, None)]   # None: a Chromium cached, its revision unknown
        for browser, config, chromium, asked in cases:
            shutil.rmtree(os.path.join(self.home, "ms-playwright"), ignore_errors=True)
            shutil.rmtree(os.path.join(self.home, "root", ".playwright"), ignore_errors=True)
            if config:
                self.cli_config("checkout", config)
            with mock.patch.object(check, "WINDOWS", False), mock.patch.object(check, "LINUX", True), \
                    mock.patch.object(check, "missing_libraries", lambda home, pinned: True), \
                    mock.patch.object(check, "node_version", lambda n: (20, "v20.0.0")), \
                    mock.patch.object(check, "playwright_core_cli", lambda cli: "/fake/core/cli.js"), \
                    mock.patch.object(check, "which", lambda name, dirs: (node, True)):
                lines, machine, _, _ = self.config_state(
                    chrome=browser == "chrome", edge=browser == "edge", chromium=chromium is True,
                    folders=["chromium-1200"] if chromium is None else (), pinned=None if chromium is None else self.PINNED)
            case = (browser, config, chromium)
            self.assertEqual(any(m.startswith("sudo:Chromium's system libraries:") for m in machine), asked, case)
            self.assertEqual("browser libraries: missing (needs sudo)" in lines, asked, (case, lines))

    def test_linux_config_naming_chromium_counts_only_when_it_loads(self):
        """A config this check cannot read, or a PLAYWRIGHT_MCP_* override, names no browser here."""
        configs = [("this checkout", self.cli_config("checkout", self.CHROMIUM_CONFIG))]
        self.assertTrue(check.config_names_chromium(configs))
        self.assertFalse(check.config_names_chromium([]))
        os.environ["PLAYWRIGHT_MCP_BROWSER"] = "chrome"
        try:
            self.assertFalse(check.config_names_chromium(configs))
        finally:
            del os.environ["PLAYWRIGHT_MCP_BROWSER"]
        self.cli_config("checkout", "{not json")
        self.assertFalse(check.config_names_chromium(configs))
        self.cli_config("global", self.CHROMIUM_CONFIG)
        self.cli_config("checkout", self.EDGE_CONFIG)   # the checkout's keys win over the global ones
        self.assertFalse(check.config_names_chromium(
            configs + [("global", os.path.join(self.home, ".playwright", "cli.config.json"))]))

    ASK = ("ask", "the playwright-cli config C names Chromium, which is not in X.", "Ask the user once whether to run Y.")

    def test_ask_is_a_question_with_no_install_of_its_own(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["playwright-cli config: browser missing"], [], [self.ASK], []))
        code, lines = self.run_check("fit")
        self.assertEqual(code, 0)
        asked = [l for l in lines if "names Chromium" in l]
        self.assertEqual(len(asked), 1)
        self.assertIn("Ask the user once whether to run Y. Do what they choose, then run this check again", asked[0])
        self.assertFalse(any("with no question" in l for l in lines))

    def test_skill_install_beside_an_ask_skips_the_download(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=([], [], ["skill", self.ASK], []))
        code, lines = self.run_check("fit")
        install = [l for l in lines if "with no question" in l]
        self.assertEqual(len(install), 1)
        self.assertIn("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", install[0])
        if check.WINDOWS:   # PowerShell keeps $env: set: the same command clears it
            self.assertIn("install --skills; Remove-Item Env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD`", install[0])
        self.state(playwright_cli=([], [], ["skill"], []))
        code, lines = self.run_check("fit")
        self.assertFalse(any("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD" in l for l in lines))

    def test_unattended_ask_asks_nothing(self):
        self.unattended()
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=([], [], [self.ASK], []))
        code, lines = self.run_check("fit")
        asked = [l for l in lines if "names Chromium" in l]
        self.assertEqual(len(asked), 1)
        self.assertIn("so it asks nothing", asked[0])
        self.assertNotIn("Ask the user", asked[0])

    def appdata(self, where, *parts):
        """A file under the fake real %APPDATA% (`real`) or a packaged app's store copy of it (`store`)."""
        base = (os.path.join(self.home, "Roaming") if where == "real" else
                os.path.join(self.home, "Local", "Packages", "Claude_x", "LocalCache", "Roaming"))
        path = os.path.join(base, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
        return os.path.dirname(path)

    def fake_profile(self):
        saved = {k: os.environ.get(k) for k in ("LOCALAPPDATA", "APPDATA", "PATH", "TINYTEX_BIN")}
        os.environ.update(LOCALAPPDATA=os.path.join(self.home, "Local"), APPDATA=os.path.join(self.home, "Roaming"), PATH="")
        os.environ.pop("TINYTEX_BIN", None)
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.update({k: v})
                                 for k, v in saved.items()])

    @unittest.skipUnless(os.name == "nt", "packaged apps' stores are Windows's")
    def test_playwright_cli_in_a_packaged_apps_store(self):
        store = self.appdata("store", "npm", "playwright-cli.cmd")
        self.fake_profile()
        self.assertEqual(check.which("playwright-cli", check.npm_bin_dirs(self.home)), (os.path.join(store, "playwright-cli.cmd"), False))
        self.appdata("real", "npm", "playwright-cli.cmd")
        self.assertEqual(os.path.dirname(check.which("playwright-cli", check.npm_bin_dirs(self.home))[0]), store)

    @unittest.skipUnless(os.name == "nt", "packaged apps' stores are Windows's")
    def test_tinytex_in_a_packaged_apps_store_or_the_real_appdata(self):
        resume = check.resume_module()
        self.fake_profile()
        real = self.appdata("real", "TinyTeX", "bin", "windows", "pdflatex.exe")
        self.assertEqual(os.path.normpath(resume.tex_bin("pdflatex")), os.path.join(real, "pdflatex.exe"))
        store = self.appdata("store", "TinyTeX", "bin", "windows", "pdflatex.exe")   # both: the store's, as setup.ps1 picks
        self.assertEqual(os.path.normpath(resume.tex_bin("pdflatex")), os.path.join(store, "pdflatex.exe"))

    @unittest.skipUnless(os.name == "nt", "Windows's error dialogs")
    def test_poppler_probe_starts_programs_with_no_error_dialog(self):
        # A child started with CREATE_DEFAULT_ERROR_MODE does not inherit this process's mode; it
        # probes a pdftotext that prints the error mode it inherited (#285)
        folder = os.path.join(self.home, "probe")
        os.makedirs(folder)
        self.write(folder, "pdftotext.bat", '@"%s" -c "import ctypes; print(ctypes.windll.kernel32.GetErrorMode())"\n'
                   % sys.executable)
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import resume, subprocess;"
                " print(subprocess.run([sys.argv[2], '-h'], capture_output=True, text=True).stdout.strip());"
                " resume._has_bbox_layout(sys.argv[2]);"
                " print(subprocess.run([sys.argv[2], '-h'], capture_output=True, text=True).stdout.strip())")
        run = subprocess.run([sys.executable, "-I", "-B", "-c", code, os.path.join(HERE, ".."),
                              os.path.join(folder, "pdftotext.bat")],
                             capture_output=True, text=True, creationflags=0x04000000)
        self.assertRegex(run.stdout, r"^\d+\s+\d+\s*$", run.stderr)
        before, after = (int(n) for n in run.stdout.split())
        self.assertEqual(before & 0x8003, 0, run.stderr)
        self.assertEqual(after & 0x8003, 0x8003, run.stderr)

    def test_drafts_of_one_name_build_in_their_own_dirs(self):
        resume = check.resume_module()
        a = os.path.join(self.home, ".build", "drafts", "a", "resume.tex")
        b = os.path.join(self.home, ".build", "drafts", "b", "resume.tex")
        c = os.path.join(self.home, "other", "a", "resume.tex")   # same folder name and stem as a
        dirs = [resume.default_outdir(p) for p in (a, b, c)]
        self.assertEqual(len(set(dirs)), 3)
        self.assertEqual(resume.default_outdir(a), dirs[0])   # a rebuild reuses its dir
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.home)   # relpath can't cross drives on Windows
        self.assertEqual(resume.default_outdir(os.path.relpath(a)), dirs[0])
        if os.name == "nt":   # one file, two spellings: one dir, as Windows folds case
            self.assertEqual(os.path.normcase(resume.default_outdir(a.upper().replace("\\", "/"))),
                             os.path.normcase(dirs[0]))
        self.assertTrue(os.path.basename(dirs[0]).startswith("a-resume-"))
        for d in dirs:
            self.assertEqual(os.path.dirname(d), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
                resume.__file__))), ".build", "resume"))   # the Log the script belongs to, without --root

    def fake_pdftotext(self, folder):
        """A pdftotext in `folder` that answers -h as poppler's does, with a pdftoppm beside it."""
        os.makedirs(folder, exist_ok=True)
        if os.name == "nt":
            self.write(folder, "pdftotext.bat", "@echo -bbox-layout\n")
            self.write(folder, "pdftoppm.exe", "")
            return os.path.join(folder, "pdftotext.bat")
        for name in ("pdftotext", "pdftoppm"):
            self.write(folder, name, "#!/bin/sh\necho -bbox-layout\n")
            os.chmod(os.path.join(folder, name), 0o755)
        return os.path.join(folder, "pdftotext")

    def poppler_lines(self):
        return check.tinytex_state(self.saved_context("setup", root=self.home, home=self.home))

    def test_poppler_from_setups_environment_or_the_users_own(self):
        resume = check.resume_module()
        self.fake_profile()
        if os.environ.get("POPPLER_BIN"):
            self.addCleanup(os.environ.__setitem__, "POPPLER_BIN", os.environ.pop("POPPLER_BIN"))
        if resume.poppler_bin("pdftotext", self.home):
            self.skipTest("this machine has a poppler in a folder tools/resume.py searches before PATH")
        lines, machine, _, _ = self.poppler_lines()
        self.assertIn("pdftotext: missing (poppler's, with -bbox-layout)", lines)
        self.assertIn("poppler", machine)   # setup installs it on every platform: no sudo or user piece
        self.assertFalse(any(m.startswith(("sudo:", "user:")) for m in machine))
        env = self.fake_pdftotext(resume.poppler_env_bin(self.home))
        self.assertEqual(resume.poppler_bin("pdftotext", self.home), env)
        self.assertEqual(os.path.dirname(resume.poppler_bin("pdftoppm", self.home)), os.path.dirname(env))
        lines, machine, _, _ = self.poppler_lines()
        self.assertIn("pdftotext: ok (%s; setup's micromamba environment; rerun setup to update it)" % env, lines)
        self.assertNotIn("poppler", machine)
        lonely = self.fake_pdftotext(os.path.join(self.home, "lonely"))   # no pdftoppm beside it: passed over
        os.remove(resume._sibling(lonely, "pdftoppm"))
        os.environ["PATH"] = os.path.dirname(lonely)
        self.assertEqual(resume.poppler_bin("pdftotext", self.home), env)
        own = self.fake_pdftotext(os.path.join(self.home, "own"))   # the user's own, on PATH, comes first
        os.environ["PATH"] = os.path.dirname(own)
        self.assertEqual(resume.poppler_bin("pdftotext", self.home), own)
        self.assertEqual(os.path.dirname(resume.poppler_bin("pdftoppm", self.home)), os.path.dirname(own))
        lines, _, _, _ = self.poppler_lines()
        self.assertTrue(any(l.startswith("pdftotext: ok (%s; the user's own install" % own) for l in lines), lines)

    def log_repo(self, name="log"):
        """A Log repo with one committed entry, one Engine file and an ignored inbox."""
        root = os.path.join(self.home, name)
        os.makedirs(os.path.join(root, "entries"))
        os.makedirs(os.path.join(root, "tools"))
        os.makedirs(os.path.join(root, "sources", "inbox"))
        self.write(root, ".gitignore", "sources/inbox/*\n")
        self.write(root, "entries/2024-01-a.md", "a\n")
        self.write(root, "entries/_template.md", "t\n")
        self.write(root, "tools/check.py", "x\n")
        shutil.copy(DEFAULTS, os.path.join(root, "config.toml"))
        for cmd in (["init", "-q"], ["add", "-A"],
                    ["-c", "user.email=t@example.invalid", "-c", "user.name=T", "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", root] + cmd, check=True, capture_output=True)
        return root

    def write(self, root, path, text):
        with open(os.path.join(root, path), "w", encoding="utf-8") as f:
            f.write(text)

    def uncommitted(self, root):
        return check.check_uncommitted(self.saved_context("log", root=root, home=self.home))

    def test_clean_log_prints_nothing(self):
        self.assertEqual(self.uncommitted(self.log_repo()), ([], [], False))

    def test_changed_and_new_log_files_are_listed(self):
        root = self.log_repo()
        self.write(root, "entries/2024-01-a.md", "b\n")
        self.write(root, "entries/2024-02-新.md", "new\n")
        self.write(root, "direction.md", "d\n")
        lines, nexts, stop = self.uncommitted(root)
        self.assertFalse(stop)
        self.assertEqual(lines[0], "log changes: uncommitted (3 file(s))")
        self.assertIn("log change: M entries/2024-01-a.md", lines)
        self.assertIn("log change: ?? entries/2024-02-新.md", lines)
        self.assertIn("log change: ?? direction.md", lines)
        self.assertEqual(len(nexts), 1)
        self.assertTrue(nexts[0].startswith("next: now, first:"))
        self.assertIn("an earlier session left", nexts[0])
        self.assertIn("settle commit -- <file>...", nexts[0])
        self.assertIn("settle discard -- <file>...", nexts[0])

    def test_stories_folder_is_listed(self):
        # stories/ (Talking points, wordings) is a Log folder in logfiles.LOG_FOLDERS
        root = self.log_repo()
        os.makedirs(os.path.join(root, "stories", "wordings"))
        self.write(root, "stories/wordings/why-us.md", "w\n")
        lines, _, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (1 file(s))",
                                 "log change: ?? stories/wordings/why-us.md"])

    def test_engine_template_and_inbox_are_not_listed(self):
        root = self.log_repo()
        self.write(root, "tools/check.py", "y\n")
        self.write(root, "entries/_template.md", "u\n")
        self.write(root, "sources/inbox/cv.txt", "cv\n")
        self.assertEqual(self.uncommitted(root), ([], [], False))

    def test_rename_lists_both_paths(self):
        root = self.log_repo()
        os.rename(os.path.join(root, "entries", "2024-01-a.md"), os.path.join(root, "entries", "2024-01-b.md"))
        subprocess.run(["git", "-C", root, "add", "-N", "entries/2024-01-b.md"], check=True)
        lines, _, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (1 file(s))",
                                 "log change: R entries/2024-01-b.md (from entries/2024-01-a.md)"])
        subprocess.run(["git", "-C", root, "add", "-A"], check=True)
        lines, _, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (1 file(s))",
                                 "log change: R entries/2024-01-b.md (from entries/2024-01-a.md)"])

    def test_script_prints_file_names_in_utf8(self):
        root = self.log_repo()
        tools = os.path.join(root, "tools")
        for name in SCRIPTS:
            shutil.copy(os.path.join(HERE, "..", name), tools)
        self.write(root, "entries/2024-02-新.md", "new\n")
        run = subprocess.run([sys.executable, "-I", os.path.join(tools, "check.py"), "log"], capture_output=True)
        self.assertIn("log change: ?? entries/2024-02-新.md", run.stdout.decode("utf-8").splitlines())

    def test_not_a_repo_prints_nothing(self):
        self.assertEqual(self.uncommitted(self.home), ([], [], False))

    # ---- a run still going in another session (#609) ----

    def live_marker(self, root, key, started_ago, touched_ago=0):
        """A run's live marker (scan.py run), started and last touched that many seconds ago."""
        path = os.path.join(root, ".build", "runs", key, "live")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        start = datetime.datetime.fromtimestamp(int(time.time() - started_ago)).astimezone()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"start": start.isoformat(), "mode": "write"}, f)
        os.utime(path, (time.time() - touched_ago,) * 2)

    def aged(self, root, path, text, ago):
        """Write a Log file whose time on disk is `ago` seconds back."""
        self.write(root, path, text)
        os.utime(os.path.join(root, path), (time.time() - ago,) * 2)

    def test_a_live_runs_files_print_as_its_own_with_no_settle(self):
        root = self.log_repo()
        self.live_marker(root, "2031-01-02-100000", started_ago=600)
        self.aged(root, "entries/2024-01-a.md", "a fact step 7 added\n", ago=60)
        self.aged(root, "profile.md", "p\n", ago=0)
        lines, nexts, stop = self.uncommitted(root)
        self.assertFalse(stop)
        self.assertEqual(lines, ["log changes: uncommitted (2 file(s), 2 of them a live run's)",
                                 "log change (live run 2031-01-02-100000): M entries/2024-01-a.md",
                                 "log change (live run 2031-01-02-100000): ?? profile.md"])
        self.assertEqual(len(nexts), 1)
        self.assertNotIn("settle", nexts[0].split("keep them as they are")[0])
        self.assertIn("another session", nexts[0])
        self.assertIn("scan.py\" end <key>", nexts[0])
        self.assertIn("(2031-01-02-100000)", nexts[0])

    def test_a_finished_sessions_leftover_is_offered_beside_a_live_run(self):
        root = self.log_repo()
        self.aged(root, "direction.md", "left by an earlier session\n", ago=3600)
        self.live_marker(root, "2031-01-02-100000", started_ago=600)
        self.aged(root, "entries/2024-01-a.md", "the live run's\n", ago=30)
        lines, nexts, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (2 file(s), 1 of them a live run's)",
                                 "log change: ?? direction.md",
                                 "log change (live run 2031-01-02-100000): M entries/2024-01-a.md"])
        self.assertEqual(len(nexts), 2)
        self.assertIn("an earlier session left", nexts[0])
        self.assertIn("settle discard -- <file>...", nexts[0])
        self.assertIn("still going in another session", nexts[1])

    def test_a_file_under_an_expired_marker_is_offered_as_today(self):
        root = self.log_repo()
        self.live_marker(root, "2031-01-02-100000", started_ago=4 * 3600, touched_ago=check.logfiles.LIVE_HOURS * 3600 + 60)
        self.aged(root, "entries/2024-01-a.md", "a crashed run's\n", ago=3 * 3600)
        lines, nexts, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (1 file(s))", "log change: M entries/2024-01-a.md"])
        self.assertEqual(len(nexts), 1)
        self.assertIn("an earlier session left", nexts[0])

    def test_an_ended_or_unreadable_marker_is_no_live_run(self):
        root = self.log_repo()
        os.makedirs(os.path.join(root, ".build", "runs", "2031-01-02-100000"))   # ended: its marker deleted
        bad = os.path.join(root, ".build", "runs", "2031-01-02-110000", "live")
        os.makedirs(os.path.dirname(bad))
        self.write(root, ".build/runs/2031-01-02-110000/live", "not json\n")
        self.write(root, "profile.md", "p\n")
        lines, _, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (1 file(s))", "log change: ?? profile.md"])

    def test_a_live_run_in_a_root_with_glob_characters(self):
        """#662 (B1): the marker is found in a Log root whose path holds `[`."""
        root = self.log_repo("log [1]")
        self.live_marker(root, "2031-01-02-100000", started_ago=600)
        self.aged(root, "profile.md", "p\n", ago=0)
        lines, _, _ = self.uncommitted(root)
        self.assertEqual(lines[1:],["log change (live run 2031-01-02-100000): ?? profile.md"])

    def test_a_marker_in_a_folder_named_as_no_run_key_is_no_live_run(self):
        """#662 (B1): only a folder `scan.py run` could have made holds a live run."""
        root = self.log_repo()
        self.live_marker(root, "notes", started_ago=600)
        self.aged(root, "profile.md", "p\n", ago=0)
        lines, _, _ = self.uncommitted(root)
        self.assertEqual(lines, ["log changes: uncommitted (1 file(s))", "log change: ?? profile.md"])

    def test_two_live_runs_each_take_the_files_since_their_start(self):
        root = self.log_repo()
        self.live_marker(root, "2031-01-02-100000", started_ago=1200)
        self.live_marker(root, "2031-01-02-101500", started_ago=300)
        self.aged(root, "entries/2024-01-a.md", "the first run's\n", ago=600)
        self.aged(root, "profile.md", "p\n", ago=60)
        lines, nexts, _ = self.uncommitted(root)
        self.assertIn("log change (live run 2031-01-02-100000): M entries/2024-01-a.md", lines)
        self.assertIn("log change (live run 2031-01-02-101500): ?? profile.md", lines)
        self.assertIn("(2031-01-02-100000, 2031-01-02-101500)", nexts[0])

    def test_uncommitted_line_comes_before_go_on(self):
        root = self.log_repo()
        self.write(root, "profile.md", "p\n")
        home = self.home
        check.Context = lambda mode, **_: self.saved_context(mode, root=root, home=home)
        code, lines = self.run_check("log")
        self.assertEqual(code, 0)
        self.assertTrue(any(l.startswith("next: now, first:") and "sync.py" in l and "status -- <file>" in l
                            for l in lines[:-1]), lines)
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_entry_over_threshold_is_listed_and_the_mode_goes_on(self):
        root = self.log_repo()
        self.write(root, "entries/2024-03-long.md", "x" * 40000)   # about 14,800 tokens
        self.write(root, "entries/_template.md", "x" * 40000)      # the template is not an entry
        home = self.home
        check.Context = lambda mode, **_: self.saved_context(mode, root=root, home=home)
        code, lines = self.run_check("log")
        self.assertEqual(code, 0)
        self.assertEqual([l for l in lines if l.startswith("entry ")],
                         ["entry over threshold: entries/2024-03-long.md 14815 tokens"])
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_no_entries_folder_prints_no_size_line(self):
        self.assertEqual(check.check_size(self.saved_context("log", root=self.home, home=self.home)), ([], [], False))

    def test_runs_as_a_script(self):
        root = self.log_repo()
        for name in SCRIPTS:
            shutil.copy(os.path.join(HERE, "..", name), os.path.join(root, "tools"))
        run = subprocess.run([sys.executable, "-I", os.path.join(root, "tools", "check.py"), "log"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines()[-1], "next: go on with the mode")


class GitStateTest(unittest.TestCase):
    """The root line, the read-only git lines (identity, default branch, ahead) and the pull step,
    on a Log cloned from a bare origin; and start.py through a skill link."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.saved_state = dict(check.STATE)
        self.addCleanup(lambda: check.STATE.update(self.saved_state))
        for tool in check.STATE:
            check.STATE[tool] = lambda ctx: OK
        self.saved_unattended = check.UNATTENDED
        self.addCleanup(lambda: setattr(check, "UNATTENDED", self.saved_unattended))
        check.UNATTENDED = False

    def git(self, root, *args):
        return subprocess.run(["git", "-C", root] + list(args), check=True, capture_output=True, text=True).stdout

    def commit(self, root, path, text):
        with open(os.path.join(root, path), "w", encoding="utf-8") as f:
            f.write(text)
        self.git(root, "add", "-A")
        self.git(root, "-c", "user.email=t@example.invalid", "-c", "user.name=T", "-c", "commit.gpgsign=false",
                 "commit", "-qm", "c")

    def log(self, origin=True, identity=True):
        """A Log with config.toml and README.md: a clone of a bare origin, or a repo with no remote."""
        root = os.path.join(self.tmp, "log")
        if origin:
            bare = os.path.join(self.tmp, "origin.git")
            subprocess.run(["git", "init", "-q", "--bare", "-b", "master", bare], check=True)
            seed = os.path.join(self.tmp, "seed")
            subprocess.run(["git", "init", "-q", "-b", "master", seed], check=True)
            shutil.copy(DEFAULTS, os.path.join(seed, "config.toml"))
            self.commit(seed, "README.md", "# Log\n")
            self.git(seed, "push", "-q", bare, "master")
            subprocess.run(["git", "clone", "-q", bare, root], check=True, capture_output=True)
        else:
            subprocess.run(["git", "init", "-q", "-b", "master", root], check=True)
            shutil.copy(DEFAULTS, os.path.join(root, "config.toml"))
            self.commit(root, "README.md", "# Log\n")
        if identity:
            self.git(root, "config", "user.email", "t@example.invalid")
        return root

    def run_main(self, args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check.main(args)
        return code, out.getvalue().splitlines()

    def run_check(self, root, mode="log"):
        home, saved = self.home, check.Context
        check.Context = lambda m, **_: saved(m, root=root, home=home)
        try:
            return self.run_main([mode])
        finally:
            check.Context = saved

    def nexts(self, lines):
        return [l for l in lines if l.startswith("next:")]

    def test_root_line_comes_first(self):
        root = self.log()
        code, lines = self.run_check(root)
        self.assertEqual(code, 0)
        self.assertEqual(lines[0], "root: %s" % root)
        self.assertTrue(lines[1].startswith("python: "), lines)

    def test_root_option(self):
        """--root names the Log; without it, the folder above the script's real path."""
        root, home, saved = self.log(), self.home, check.Context
        self.addCleanup(lambda: setattr(check, "Context", saved))
        check.Context = lambda m, root=None, **_: saved(m, root=root, home=home)   # --root's root, a scratch home
        code, lines = self.run_main(["--root", root, "log"])
        self.assertEqual(lines[0], "root: %s" % root)
        self.assertIn("identity: ok (t@example.invalid)", lines)
        code, lines = self.run_main(["--root"])
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("usage:"), lines)

    def test_root_line_before_too_old_python(self):
        saved = check.MIN_PYTHON
        self.addCleanup(lambda: setattr(check, "MIN_PYTHON", saved))
        check.MIN_PYTHON = (99, 0)
        code, lines = self.run_check(self.log())
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("root: "), lines)
        self.assertTrue(lines[1].startswith("python: too old"), lines)
        self.assertFalse(any("sync.py" in l for l in lines), lines)

    def test_clean_clone(self):
        root = self.log()
        code, lines = self.run_check(root)
        self.assertEqual(code, 0)
        for line in ("identity: ok (t@example.invalid)", "default branch: master", "ahead: 0"):
            self.assertIn(line, lines)
        nexts = self.nexts(lines)
        self.assertEqual(nexts[-1], "next: go on with the mode")
        self.assertTrue(nexts[-2].startswith("next: now, first: run `"), nexts)
        self.assertIn("sync.py\" pull` (another clone may have pushed)", nexts[-2])
        self.assertTrue(nexts[-2].endswith("go on once it ends with `sync: ok`, with no rerun of this check for the pull."), nexts)
        self.assertEqual(sum("pull" in n for n in nexts), 1, nexts)

    def test_no_identity_waits_for_a_commit(self):
        """A missing identity holds up a step that commits, not the mode (SETUP.md step 3)."""
        root = self.log(identity=False)
        code, lines = self.run_check(root, "fit")
        self.assertEqual(code, 0)
        self.assertIn("identity: missing (no repo-local user.email)", lines)
        self.assertTrue(any(n.startswith("next: when a step commits, first:") and "SETUP.md step 3" in n
                            for n in self.nexts(lines)), lines)
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_origin_head_unset(self):
        root = self.log()
        self.git(root, "remote", "set-head", "origin", "--delete")
        code, lines = self.run_check(root)
        self.assertEqual(code, 0)
        self.assertIn("default branch: unknown (origin/HEAD is not set)", lines)
        self.assertFalse(any(l.startswith("ahead:") for l in lines), lines)
        hint = [n for n in self.nexts(lines) if n.startswith("next: when a step names <default>, first:")]
        self.assertEqual(len(hint), 1, lines)
        self.assertIn("remote set-head origin --auto", hint[0])
        self.assertNotEqual(subprocess.run(["git", "-C", root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"],
                                           capture_output=True).returncode, 0)   # the check set nothing
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_ahead_is_told_with_no_step(self):
        """Commits not on origin are named; a sync.py commit that pushes takes them along, so no step pushes now,
        which could take a bulk change waiting for its yes along, or need an identity."""
        root = self.log(identity=False)
        self.commit(root, "profile.md", "p\n")
        self.commit(root, "direction.md", "d\n")
        with open(os.path.join(root, "README.md"), "a") as f:   # a bulk change waiting for its yes
            f.write("| row |\n")
        code, lines = self.run_check(root)
        self.assertEqual(code, 0)
        self.assertIn("ahead: 2 (not on origin yet; a sync.py commit that pushes takes them along, or, in a mode that"
                      " commits nothing, `sync.py push` at Next up)", lines)
        nexts = self.nexts(lines)
        self.assertFalse(any("README.md" in n or "origin/master..HEAD" in n for n in nexts), nexts)
        self.assertEqual(nexts[-1], "next: go on with the mode")
        self.assertEqual(self.git(root, "rev-list", "--count", "origin/master..HEAD").strip(), "2")   # nothing pushed

    def test_other_branch_has_no_ahead(self):
        """A scan draft branch, a worktree's own branch, a detached HEAD: commits go elsewhere."""
        root = self.log()
        self.git(root, "checkout", "-q", "-b", "scan/x")
        self.commit(root, "profile.md", "p\n")
        code, lines = self.run_check(root)
        self.assertIn("branch: scan/x (not master)", lines)
        self.assertFalse(any(l.startswith("ahead:") or "pull`" in l for l in lines), lines)   # no upstream yet
        self.git(root, "push", "-q", "-u", "origin", "scan/x")
        code, lines = self.run_check(root)
        self.assertEqual(sum("pull`" in l for l in lines), 1, lines)   # a pushed draft branch pulls
        self.git(root, "checkout", "-q", "--detach")
        code, lines = self.run_check(root)
        self.assertIn("branch: detached HEAD (not master)", lines)
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_default_branch_not_fetched(self):
        root = self.log()
        self.git(root, "update-ref", "-d", "refs/remotes/origin/master")
        self.git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/master")
        code, lines = self.run_check(root)
        self.assertIn("ahead: unknown", lines)

    def test_no_remote(self):
        root = self.log(origin=False)
        code, lines = self.run_check(root)
        self.assertEqual(code, 0)
        self.assertIn("default branch: none (no origin remote)", lines)
        self.assertFalse(any(l.startswith("ahead:") or "pull" in l for l in lines), lines)
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_not_a_repo(self):
        root = os.path.join(self.tmp, "plain")
        os.makedirs(root)
        shutil.copy(DEFAULTS, os.path.join(root, "config.toml"))
        code, lines = self.run_check(root)
        self.assertIn("git: not a repository (%s)" % root, lines)
        self.assertFalse(any(l.startswith(("identity:", "default branch:")) or "pull" in l for l in lines), lines)

    def test_log_change_points_at_sync_status(self):
        root = self.log()
        with open(os.path.join(root, "profile.md"), "w") as f:
            f.write("p\n")
        code, lines = self.run_check(root)
        self.assertIn("log change: ?? profile.md", lines)
        nexts = self.nexts(lines)
        settle = [n for n in nexts if "status -- <file>..." in n]
        self.assertEqual(len(settle), 1, nexts)
        self.assertIn("sync.py\" status -- <file>...`", settle[0])
        self.assertIn("sync.py\" settle commit -- <file>...`", settle[0])
        self.assertIn("sync.py\" settle discard -- <file>...`", settle[0])
        self.assertLess(nexts.index(settle[0]), next(i for i, n in enumerate(nexts) if "pull`" in n))
        self.assertEqual(nexts[-1], "next: go on with the mode")

    def test_stop_prints_no_pull(self):
        root = self.log()
        os.remove(os.path.join(root, "config.toml"))
        code, lines = self.run_check(root)
        self.assertEqual(code, 1)
        self.assertTrue(lines[-1].startswith("next: stop:"), lines)
        self.assertFalse(any("pull" in l for l in lines), lines)

    def test_setup_rerun_still_holds_go_on(self):
        """In setup, a step that runs the check again holds back the go-on line (#314); the pull line
        never asks for a rerun, so it does not."""
        root = self.log()
        check.STATE["tinytex"] = lambda ctx: (["x: missing"], ["x"], [], [])
        code, lines = self.run_check(root, "setup")
        self.assertEqual(code, 0)
        nexts = self.nexts(lines)
        self.assertTrue(any(n.startswith("next: now") and "run this check again" in n for n in nexts), nexts)
        self.assertNotIn("next: go on with the mode", nexts)
        pull = [n for n in nexts if "pull`" in n]
        self.assertEqual(len(pull), 1, nexts)
        self.assertNotIn("run this check again", pull[0])

    # ---- start.py ----

    def fake_log(self):
        """A Log on disk with the scripts check.py imports and the skill's start.py."""
        root = self.log()
        os.makedirs(os.path.join(root, "tools"))
        for name in SCRIPTS:
            shutil.copy(os.path.join(HERE, "..", name), os.path.join(root, "tools"))
        os.makedirs(os.path.join(root, "skills", "career-log"))
        shutil.copy(START, os.path.join(root, "skills", "career-log"))
        return root

    def start(self, folder, *args):
        env = dict(os.environ, HOME=self.home, USERPROFILE=self.home, CAREER_LOG_UNATTENDED="1",
                   CAREER_LOG_RELEASES_URL="http://127.0.0.1:9/none")
        return subprocess.run([sys.executable, "-I", os.path.join(folder, "start.py")] + list(args),
                              capture_output=True, text=True, cwd=self.home, env=env)

    def link(self, target):
        link = os.path.join(self.tmp, "agent", "skills", "career-log")
        os.makedirs(os.path.dirname(link))
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(target, link)
        else:
            os.symlink(target, link)
        return link

    def test_start_through_a_skill_link(self):
        """A Windows junction (SETUP.md step 4) or a POSIX symlink outside the Log: the root is the Log's."""
        root = self.fake_log()
        link = self.link(os.path.join(root, "skills", "career-log"))
        run = self.start(link, "log")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        out = run.stdout.splitlines()
        self.assertEqual(out[0], "root: %s" % root)
        self.assertIn("identity: ok (t@example.invalid)", out)
        self.assertEqual(out[-1], "next: go on with the mode")

    def test_start_without_a_mode_prints_the_root(self):
        root = self.fake_log()
        run = self.start(self.link(os.path.join(root, "skills", "career-log")))
        self.assertEqual((run.returncode, run.stdout), (0, "root: %s\n" % root), run.stderr)

    def test_start_without_the_tools_says_so(self):
        """A Python that does not resolve the link lands outside the Log, with no tools/check.py."""
        folder = os.path.join(self.tmp, "lone", "skills", "career-log")
        os.makedirs(folder)
        shutil.copy(START, folder)
        run = self.start(folder, "log")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertTrue(run.stdout.startswith("root: not found (no "), run.stdout)

    def test_start_passes_the_exit_code(self):
        root = self.fake_log()
        run = self.start(os.path.join(root, "skills", "career-log"), "deploy")
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertTrue(run.stdout.startswith("usage:"), run.stdout)


START = os.path.join(HERE, "..", "..", "skills", "career-log", "start.py")


class ConfigCheckTest(unittest.TestCase):
    """check_config: whether setup has run for this Log."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.saved = check.UNATTENDED
        self.addCleanup(lambda: setattr(check, "UNATTENDED", self.saved))
        check.UNATTENDED = False

    def config(self, mode, text=None):
        if text is not None:
            with open(os.path.join(self.root, "config.toml"), "w", encoding="utf-8") as f:
                f.write(text)
        return check.check_config(check.Context(mode, root=self.root, home=self.root))

    def test_missing_stops_every_mode_but_setup(self):
        for mode in (m for m in check.MODES if m != "setup"):
            lines, nexts, stop = self.config(mode)
            self.assertTrue(stop, mode)
            self.assertEqual(lines, ["config: missing (setup has not run for this Log)"])
            self.assertTrue(nexts[0].startswith("next: stop: setup has not run for this Log"))
            self.assertIn("setup mode", nexts[0])

    def test_missing_in_setup_goes_on(self):
        self.assertEqual(self.config("setup"), (["config: missing (setup writes it)"], [], False))

    def test_missing_unattended_asks_nothing(self):
        check.UNATTENDED = True
        lines, nexts, stop = self.config("fit")
        self.assertTrue(stop)
        self.assertIn("unattended", nexts[0])
        self.assertNotIn("on their yes", nexts[0])

    def test_unattended_setup_stops_too(self):
        check.UNATTENDED = True
        self.assertTrue(self.config("setup")[2])

    def test_values_and_defaults_are_printed(self):
        lines, nexts, stop = self.config("write", 'record_language = "Deutsch"\n')
        self.assertFalse(stop)
        self.assertEqual(nexts, [])
        self.assertEqual(lines, ["config record_language: Deutsch", "config interviewer_profiles: never (default)",
                                 "config front_page: full (default)", "config window: 7 (default)",
                                 "config scheduled_window: window (default)", "config screen_budget: 40 (default)",
                                 "config fit_budget: 15 (default)", "config n: 10 (default)", "config auto_write: off (default)", "config m: 5 (default)",
                                 "config update_check: on (default)", "config resume_max_pages: 1 (default)",
                                 "config plan_preview: ask (default)"])

    def test_unreadable_or_unknown_field_stops(self):
        for text in ("record_language = \n", 'colour = "blue"\n', 'front_page = "half"\n'):
            lines, nexts, stop = self.config("log", text)
            self.assertTrue(stop, text)
            self.assertTrue(lines[0].startswith("config: unreadable"), lines)
            self.assertTrue(nexts[0].startswith("next: stop: show the user the error"))

    def test_an_unreadable_defaults_file_stops(self):   # Finding 7: no traceback
        config_tool = check.tools_module("config")
        saved = config_tool.DEFAULTS_FILE
        self.addCleanup(lambda: setattr(config_tool, "DEFAULTS_FILE", saved))
        bad = os.path.join(self.root, "bad.toml")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("front_page = \n")
        for where in (os.path.join(self.root, "absent.toml"), bad, self.root):   # missing, no parse, a folder
            config_tool.DEFAULTS_FILE = where
            lines, nexts, stop = self.config("log", 'record_language = "English"\n')
            self.assertTrue(stop, where)
            self.assertTrue(lines[0].startswith("config: unreadable (%s cannot be read" % where), lines)
            self.assertIn("fix the file it names", nexts[0])

    def test_whole_run_stops_before_tools(self):
        out = io.StringIO()
        saved = check.Context
        self.addCleanup(lambda: setattr(check, "Context", saved))
        check.Context = lambda mode, **_: saved(mode, root=self.root, home=self.root)
        with redirect_stdout(out):
            code = check.main(["write"])
        self.assertEqual(code, 1)
        self.assertFalse(any("tinytex" in l for l in out.getvalue().splitlines()))


REPO = os.path.dirname(os.path.dirname(HERE))
README_HEAD = "# Log\n\n## Entries\n\n| Period | Entry | Type | Status |\n|---|---|---|---|\n"


class ModeStateTest(unittest.TestCase):
    """check_mode_state: the state lines a mode reads, in place of the skill's own checks (#297)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.home = os.path.join(self.root, "home")
        os.makedirs(self.home)
        shutil.copy(DEFAULTS, os.path.join(self.root, "config.toml"))
        shutil.copy(os.path.join(HERE, "..", "template", "direction.md"), os.path.join(self.root, "direction.md"))

    def write(self, name, text):
        with open(os.path.join(self.root, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def state(self, mode):
        return check.check_mode_state(check.Context(mode, root=self.root, home=self.home))

    def test_direction_items_in_every_mode(self):
        lines, nexts, stop = self.state("fit")
        items = [l for l in lines if l.startswith("direction ")]
        self.assertEqual(len(items), len(check.tools_module("config").DIRECTION_LINES))
        self.assertIn("direction target roles: empty", items)
        self.assertEqual((nexts, stop), ([], False))
        with open(os.path.join(self.root, "direction.md"), encoding="utf-8") as f:
            text = f.read()
        self.write("direction.md", text.replace("## Target roles, ranked\n", "## Target roles, ranked\n\n1. Backend engineer\n", 1))
        self.assertIn("direction target roles: set", self.state("fit")[0])
        os.remove(os.path.join(self.root, "direction.md"))
        line = [l for l in self.state("fit")[0] if l.startswith("direction target roles: ")]
        self.assertTrue(line[0].startswith("direction target roles: unreadable ("), line)

    def test_setup_front_page(self):
        shutil.copy(os.path.join(HERE, "..", "template", "README.md"), os.path.join(self.root, "README.md"))
        self.assertIn("front page: template", self.state("setup")[0])
        self.write("README.md", "# Mine\n\n## Entries\n")
        self.assertIn("front page: edited", self.state("setup")[0])
        self.assertFalse([l for l in self.state("fit")[0] if l.startswith("front page")])

    def test_setup_skill_links(self):
        skill = os.path.join(self.root, "skills", "career-log")
        os.makedirs(skill)
        other = os.path.join(self.root, "other")
        os.makedirs(other)
        try:
            os.makedirs(os.path.join(self.home, ".claude", "skills"))
            os.makedirs(os.path.join(self.home, ".agents", "skills"))
            for target, path in ((skill, os.path.join(self.home, ".claude", "skills", "career-log")),
                                 (other, os.path.join(self.home, ".agents", "skills", "career-log"))):
                if os.name == "nt":   # a junction, as SETUP.md step 4 makes on Windows
                    subprocess.run(["cmd", "/c", "mklink", "/J", path, target], capture_output=True, check=True)
                else:
                    os.symlink(target, path)
        except (OSError, subprocess.CalledProcessError) as e:
            self.skipTest("cannot make a link here: %s" % e)
        lines = self.state("setup")[0]
        self.assertIn("skill link claude: ok (%s)" % os.path.join(self.home, ".claude", "skills", "career-log"), lines)
        self.assertTrue(any(l.startswith("skill link codex: elsewhere (") for l in lines), lines)
        self.assertTrue(any(l.startswith("skill link antigravity-cli: missing (%s; only an agent the user runs needs it"
                                         % os.path.join(self.home, ".gemini", "antigravity-cli", "skills", "career-log"))
                            for l in lines), lines)

    def test_setup_eol(self):
        def git(*args):
            subprocess.run(["git", "-C", self.root, "-c", "core.autocrlf=false"] + list(args), capture_output=True, check=True)
        git("init", "-q")
        os.makedirs(os.path.join(self.root, "tools"))
        self.write(".gitattributes", "* text=auto eol=lf\n*.ps1 text eol=crlf\n")
        self.write("a.md", "lf\n")
        self.write("tools/setup.ps1", "crlf\r\n")
        self.write("empty.md", "")
        git("add", "-A")
        self.assertIn("eol: ok", self.state("setup")[0])
        self.write("a.md", "crlf\r\n")
        self.write("tools/setup.ps1", "lf\n")
        self.assertIn("eol: wrong (a.md w/crlf, tools/setup.ps1 w/lf; SETUP.md step 2)", self.state("setup")[0])
        os.remove(os.path.join(self.root, "a.md"))   # deleted from the working tree: nothing to judge
        self.assertIn("eol: wrong (tools/setup.ps1 w/lf; SETUP.md step 2)", self.state("setup")[0])

    def test_import_inbox_lines(self):
        self.write(".gitignore", ".build/\nsources/inbox/*\n!sources/inbox/.gitkeep\n")
        lines, nexts, stop = self.state("import")
        self.assertIn("gitignore inbox: ok", lines)
        self.assertEqual(nexts, [])
        self.write(".gitignore", ".build/\nsources/inbox/*\n")
        lines, nexts, stop = self.state("import")
        self.assertIn("gitignore inbox: missing (!sources/inbox/.gitkeep)", lines)
        self.assertEqual(len(nexts), 1)
        self.assertTrue(nexts[0].startswith("next: now, first: add the line(s) `!sources/inbox/.gitkeep`"), nexts)
        self.assertIn('commit "gitignore: sources/inbox" -- .gitignore', nexts[0])
        self.assertNotIn("run this check again", nexts[0])   # `go on with the mode` stays
        self.assertFalse([l for l in self.state("fit")[0] if l.startswith("gitignore")])

    def test_import_inbox_rule_in_other_words(self):
        """In a git repository, git's own answer decides: an equal rule counts, a missing exception does not."""
        subprocess.run(["git", "-C", self.root, "init", "-q"], check=True)
        self.write(".gitignore", "/sources/inbox/**\n!/sources/inbox/.gitkeep\n")
        self.assertIn("gitignore inbox: ok", self.state("import")[0])
        self.write(".gitignore", "sources/\n")
        self.assertIn("gitignore inbox: missing (!sources/inbox/.gitkeep)", self.state("import")[0])

    def test_scan_window(self):
        self.assertIn("scan window: 7 days (window); 7 days in an unattended run (scheduled_window)", self.state("scan")[0])
        self.write("config.toml", "window = 3\nscheduled_window = 2\n")
        self.assertIn("scan window: 3 days (window); 2 days in an unattended run (scheduled_window)", self.state("scan")[0])

    def test_interview_profile_step(self):
        nexts = self.state("interview")[1]
        self.assertEqual(len(nexts), 1)
        self.assertTrue(nexts[0].startswith(check.PROFILE_STEP + "keep to public pages"), nexts)
        self.assertIn('`interviewer_profiles = "never"`', nexts[0])
        self.write("config.toml", 'interviewer_profiles = "always"\n')
        nexts = self.state("interview")[1]
        self.assertTrue(nexts[0].startswith(check.PROFILE_STEP + "read it through the signed-in profile"), nexts)
        self.assertEqual(self.state("rank")[1], [])


class BrowserTargetTest(unittest.TestCase):
    """`check.py browser`: playwright-cli's state alone, browser.md's own check."""

    def test_browser_prints_playwright_cli_only(self):
        saved = dict(check.STATE)
        self.addCleanup(lambda: check.STATE.update(saved))
        check.STATE["playwright-cli"] = lambda ctx: (["playwright-cli skill: missing (this checkout)"], [], ["skill"], [])
        root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        out = io.StringIO()
        with redirect_stdout(out):
            code = check.main(["browser", "--root", root])
        lines = out.getvalue().splitlines()
        self.assertEqual(code, 0)
        self.assertFalse([l for l in lines if l.startswith(("config", "mode start", "git:", "direction", "tinytex"))], lines)
        self.assertTrue(any(l.startswith("next: now, first: from ") and "install --skills" in l for l in lines), lines)
        self.assertEqual(lines[-1], "next: go on with the mode")
        self.assertNotIn("browser", check.MODES)

    def test_unignored_playwright_files(self):
        root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        subprocess.run(["git", "-C", root, "init", "-q"], check=True)
        os.makedirs(os.path.join(root, ".playwright-cli"))
        with open(os.path.join(root, ".playwright-cli", "page.json"), "w") as f:
            f.write("{}")
        self.assertEqual(check.unignored_files(root), check.PLAYWRIGHT_FILES)   # no .gitignore: none ignored
        with open(os.path.join(root, ".gitignore"), "w") as f:
            f.write("# a note\n.claude/skills/playwright-cli/\n.agents/skills/playwright-cli/\n.playwright/\n")
        self.assertEqual(check.unignored_files(root), [".playwright-cli"])   # whether or not files exist yet
        with open(os.path.join(root, ".gitignore"), "a") as f:
            f.write(".playwright-cli/\n")
        self.assertEqual(check.unignored_files(root), [])   # an uncommitted .gitignore is no problem
        self.assertIsNone(check.unignored_files(os.path.join(root, "no-such-folder")))

    def test_unignored_files_ask_first_and_hold_the_install(self):
        saved = dict(check.STATE)
        self.addCleanup(lambda: check.STATE.update(saved))
        ask = ("ask-git", "git does not ignore what playwright-cli writes in this checkout (.playwright).",
               "Ask the user whether to add `.playwright/` to .gitignore.")
        check.STATE["playwright-cli"] = lambda ctx: (["playwright-cli files: not ignored by git (.playwright)"], [],
                                                    ["skill", ask], [])
        root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        out = io.StringIO()
        with redirect_stdout(out):
            check.main(["browser", "--root", root])
        nexts = [l for l in out.getvalue().splitlines() if l.startswith("next: now")]
        self.assertEqual(len(nexts), 1, nexts)
        self.assertIn("Ask the user whether to add `.playwright/`", nexts[0])
        self.assertNotIn("install --skills", nexts[0])


class SessionTest(unittest.TestCase):
    """Session hygiene: the mode start line and `done <mode>`, on a root with this repo's guide and SKILL.md."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.saved = check.UNATTENDED
        self.addCleanup(lambda: setattr(check, "UNATTENDED", self.saved))
        check.UNATTENDED = False
        for rel in ("docs/guide.md", "skills/career-log/SKILL.md"):
            os.makedirs(os.path.dirname(os.path.join(self.root, rel)), exist_ok=True)
            shutil.copy(os.path.join(REPO, rel), os.path.join(self.root, rel))
        shutil.copytree(os.path.join(REPO, "skills", "career-log", "modes"),
                        os.path.join(self.root, "skills", "career-log", "modes"))
        self.guide = check.Guide(self.root)

    def write(self, rel, text=""):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def entry(self, status):
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget\nperiod: 2031-01\nstatus: %s\n---\n\n# Widget\n" % status)
        self.write("README.md", README_HEAD + "| 2031-01 | [Widget](entries/2031-01-widget.md) | project | stub |\n")

    def git(self, *args, env=None):
        subprocess.run(["git", "-C", self.root] + list(args), check=True, capture_output=True,
                       env=dict(os.environ, **(env or {})))

    def head(self):
        return subprocess.run(["git", "-C", self.root, "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip()

    def repo(self):
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "T")
        self.git("config", "commit.gpgsign", "false")
        self.git("add", "-A")
        self.git("commit", "-qm", "seed")

    def done(self, *args):
        return check.done(list(args), root=self.root)

    def next_line(self, mode):
        return next((l for l in self.done(mode)[1] if l.startswith("Next:")), None)

    # ---- mode start ----

    def test_start_line_names_the_same_session_steps(self):
        _, nexts, stop = check.check_session(check.Context("scan", root=self.root))
        self.assertFalse(stop)
        self.assertEqual(len(nexts), 1)
        self.assertTrue(nexts[0].startswith("next: now, first: on any rerun of this check within this run of scan,"
                                            " skip this line: it is for the mode's first check. At the first check:"
                                            " if this session already ran a"
                                            " career-log mode before this run started, an earlier run of scan"
                                            " included,"), nexts[0])
        self.assertIn("Then wait for their answer: for a new session, stop here; if they stay, go on here.", nexts[0])
        self.assertTrue(nexts[0].endswith("Trigger check started, and scan, whose flow the guide goes on with in the"
                                          " same session."), nexts[0])
        _, nexts, _ = check.check_session(check.Context("write", root=self.root))
        self.assertTrue(nexts[0].endswith("Trigger check started."), nexts[0])

    def test_start_line_left_out_for_log_and_unattended(self):
        self.assertEqual(check.check_session(check.Context("log", root=self.root)), ([], [], False))
        check.UNATTENDED = True
        self.assertEqual(check.check_session(check.Context("write", root=self.root)), ([], [], False))

    def test_start_line_without_a_guide_still_suggests(self):
        os.remove(os.path.join(self.root, "docs", "guide.md"))
        _, nexts, _ = check.check_session(check.Context("scan", root=self.root))
        self.assertTrue(nexts[0].endswith("Trigger check started."), nexts[0])

    def test_mode_start_value_in_a_repo(self):
        self.repo()
        lines, _, _ = check.check_session(check.Context("fit", root=self.root))
        self.assertRegex(lines[0], r"^mode start: %s@\d+ \(Next up's --since; on a rerun of this mode's check,"
                                   r" keep the first one\)$" % self.head())

    # ---- done: the next step ----

    def test_one_next_per_mode_in_the_guide(self):
        nexts = {}
        for r in self.guide.flows:
            nexts.setdefault(r["mode"], set()).add((r["next"], r["session"]))
        self.assertEqual({m: n for m, n in nexts.items() if len(n) > 1}, {})

    def test_each_flow_step_gives_the_guide_next(self):
        """Every mode in a flow but log, in a state where no step past it is done yet."""
        for row in self.guide.flows:
            mode = row["mode"]
            if mode == "log":
                continue
            with self.subTest(mode=mode):
                shutil.rmtree(os.path.join(self.root, "entries"), ignore_errors=True)
                if mode != "setup":   # consolidate comes again while an entry is still imported
                    self.entry("consolidated" if mode == "consolidate" else "imported")
                line = self.next_line(mode)
                if row["next"] == "-" or mode not in check.NEEDS_TARGET.get(row["next"], (mode,)):
                    self.assertIsNone(line)   # the flow's last step, or a step with nothing to act on yet
                    continue
                self.assertTrue(line.startswith("Next: `%s`" % row["next"]), line)
                self.assertIn(row["why"].rstrip("."), line)

    def test_fit_with_no_posting_names_no_next_step(self):
        """A sponsorship question with no posting ("does <company> sponsor?") is no posting that fits (#284)."""
        self.entry("consolidated")
        self.assertIn("When a posting fits", self.next_line("fit"))
        code, lines = self.done("fit", "--no-posting")
        self.assertEqual(code, 0)
        self.assertNotIn("posting fits", "\n".join(lines))
        self.assertFalse(any(l.startswith("Next:") for l in lines), lines)
        self.assertEqual(self.done("write", "--no-posting")[0], 2)

    def test_setup_skips_steps_already_done(self):
        self.entry("imported")
        self.assertTrue(self.next_line("setup").startswith("Next: `consolidate`"))
        self.entry("consolidated")
        self.assertTrue(self.next_line("setup").startswith("Next: `stories`"))
        self.write("stories/conflict.md", "# Conflict\n")
        self.assertIsNone(self.next_line("setup"))   # fit needs a posting, which setup leaves none of
        self.write("sources/inbox/chatgpt-export.zip", "x")   # import-chats leaves raw exports here
        self.assertIsNone(self.next_line("setup"))

    def test_consolidate_again_while_an_entry_is_imported(self):
        self.entry("imported")
        self.assertEqual(self.next_line("consolidate"),
                         'Next: `consolidate` (say "consolidate the <project> entry"). 1 entry is still `stub` or'
                         ' `imported`: Widget (entries/2031-01-widget.md). They still have gaps and pending notes.')
        self.entry("consolidated (two gaps)")
        self.assertTrue(self.next_line("consolidate").startswith("Next: `stories`"))

    def test_finished_entry_is_not_named_while_others_wait(self):
        """A consolidate that finishes one entry while others are `stub` or `imported` names those
        others, never the one it finished; past NAMED it counts the rest (#607)."""
        self.entry("consolidated")   # the entry this run just finished
        for i, status in enumerate(["imported", "stub", "imported", "stub (two gaps)"], 2):
            self.write("entries/2031-0%d-part%d.md" % (i, i),
                       "---\ntitle: Part %d\nperiod: 2031-0%d\nstatus: %s\n---\n\n# Part %d\n" % (i, i, status, i))
        _, out = self.done("consolidate")
        line = next(l for l in out if l.startswith("Next:"))
        self.assertEqual(line, 'Next: `consolidate` (say "consolidate the <project> entry"). 4 entries are still'
                               ' `stub` or `imported`: Part 2 (entries/2031-02-part2.md), Part 3'
                               ' (entries/2031-03-part3.md), Part 4 (entries/2031-04-part4.md) and 1 more. They still'
                               ' have gaps and pending notes.')
        self.assertNotIn("Widget", "\n".join(out))
        self.assertIn(check.FRESH, out)
        self.assertNotIn(check.COMPLETE, out)
        self.assertFalse(any(l.startswith("Also available") for l in out), out)   # the Next line names them
        _, out = self.done("rank")   # no Next line: audit ranks the waiting entries
        self.assertIn('Also available: `audit` (say "audit my career log"): 4 entries are still `stub` or'
                      ' `imported`; it ranks which to consolidate first', out)
        self.assertIn(check.FRESH, out)
        self.assertNotIn(check.COMPLETE, out)

    def test_no_fitting_next_step_says_the_session_is_complete(self):
        """With nothing in the Log to act on, the block names no step and offers no mode: it says the
        run is complete and the session can end (#607)."""
        self.entry("consolidated")
        self.write("stories/conflict.md", "# Conflict\n")
        for mode in ("stories", "write", "interview", "audit", "rank"):
            with self.subTest(mode=mode):
                code, out = self.done(mode)
                self.assertEqual(code, 0)
                self.assertEqual(out[:2], ["Close-out", "Saved: not listed (no --since)"])
                self.assertEqual(out[2], check.COMPLETE)
                self.assertFalse(any(l.startswith(("Next:", "Also available")) for l in out), out)
                self.assertNotIn(check.FRESH, out)

    def test_import_answered_no_comes_again(self):
        """An import answered No leaves no entries, only its `.export-deny` commit: Next up suggests
        neither consolidate nor stories, which read the entries it discarded (#384)."""
        self.repo()
        start = "%s@%d" % (self.head(), int(time.time()) - 1)
        self.write(".export-deny", "widget\n")
        self.git("add", ".export-deny")
        self.git("commit", "-qm", "export-deny: widget")
        _, out = self.done("import", "--since", start)
        line = next(l for l in out if l.startswith("Next:"))
        self.assertTrue(line.startswith('Next: `import` (say "import my old resumes"). The Log has no entries yet'), line)
        self.assertFalse(any("`stories`" in l or "`consolidate`" in l for l in out), out)
        self.entry("imported")   # an import that kept its entries goes on to consolidate
        self.assertTrue(self.next_line("import").startswith("Next: `consolidate`"))

    def test_no_entries_suggests_no_step_that_reads_them(self):
        """On a Log with no entries, Next up names import, not a step that reads entries, whichever mode ran (#424)."""
        reads = ["`%s`" % m for m in check.READS_ENTRIES]
        for mode in ("consolidate", "setup", "import", "stories", "fit", "write", "scan-results"):
            with self.subTest(mode=mode):
                _, out = self.done(mode)
                line = next(l for l in out if l.startswith("Next:"))
                self.assertTrue(line.startswith('Next: `import` (say "import my old resumes").'), line)
                self.assertFalse(any(r in l for l in out for r in reads), out)
        self.assertIn("The Log has no entries yet, and the later steps read them", self.next_line("consolidate"))
        self.write("stories/conflict.md", "# Conflict\n")   # stories counts as done; fit still reads entries
        self.assertTrue(self.next_line("consolidate").startswith("Next: `import`"), self.next_line("consolidate"))
        self.entry("consolidated")   # with an entry, past stories comes fit, which needs a posting
        self.assertIsNone(self.next_line("consolidate"))

    def test_fit_next_reads_for_several_postings(self):
        """fit-several-postings ends with `done fit` too: its Next reads for a report on several postings,
        not for one posting that fits (#380's report)."""
        self.entry("consolidated")
        line = self.next_line("fit")
        self.assertTrue(line.startswith('Next: `write` (say "apply to <URL>"). When a posting fits,'), line)

    def test_next_carries_a_request_to_say(self):
        self.assertTrue(self.next_line("setup").startswith('Next: `import` (say "import my old resumes").'))

    def test_same_session_step_stays(self):
        _, out = self.done("scan")
        self.assertIn("Go on in this session: the guide runs `scan-results` right after `scan`, in the same session.", out)
        self.assertNotIn(check.FRESH, out)

    def test_fresh_session_line_and_its_block(self):
        self.entry("consolidated")
        code, out = self.done("fit")
        self.assertEqual(code, 0)
        self.assertEqual(out[0], "Close-out")
        self.assertEqual(out[1], "Saved: not listed (no --since)")
        self.assertTrue(out[2].startswith("Next: `write`"), out[2])
        self.assertEqual(out[3], check.FRESH)
        self.assertEqual(len(out), 5)   # no Also available: no mode outside the flows applies to this Log
        self.assertTrue(out[-1].startswith("next: end your last message with the block above"))
        self.assertIn("as SKILL.md › Next up says", out[-1])
        self.assertNotIn("line for line", out[-1])

    def test_also_available_only_when_the_log_calls_for_it(self):
        _, out = self.done("setup")   # no entries
        self.assertFalse(any(l.startswith("Also available") for l in out), out)
        self.entry("imported")
        _, out = self.done("fit")   # one entry left: consolidate needs no ranking
        self.assertFalse(any(l.startswith("Also available") for l in out), out)

    def test_mode_in_no_flow(self):
        self.entry("imported")
        self.write("entries/2031-02-gadget.md", "---\ntitle: Gadget\nperiod: 2031-02\nstatus: stub\n---\n\n# Gadget\n")
        _, out = self.done("audit")
        self.assertFalse(any(l.startswith("Next:") for l in out), out)   # no fixed step: no line for it
        self.assertFalse(any(l.startswith("Also available") for l in out), out)   # never audit after audit
        self.assertIn(check.COMPLETE, out)

    def test_setup_for_a_mode_goes_back_to_it(self):
        code, out = self.done("setup", "--for", "write")
        self.assertEqual(code, 0)
        self.assertIn("Next: go back to `write` in this session: setup ran for that request.", out)
        self.assertNotIn(check.FRESH, out)
        self.assertFalse(any(l.startswith("Also available") for l in out))
        self.assertTrue(out[-1].startswith("next: show the user the block above, then go on with"
                                           " write, starting with its Trigger check"), out[-1])

    # ---- a Target version's stale count reaching 3 (#612) ----

    def stale_log(self):
        """A repo with Target version `backend` saved: its provenance cites Widget, which then changes
        (stale count 1). Returns a function that adds and commits one entry, raising the count by 1."""
        self.entry("consolidated")
        self.write("outputs/resumes/backend.md", "# Backend\n\n| Bullet | Source |\n|---|---|\n"
                                                 "| Built it | entries/2031-01-widget.md |\n")
        self.write("outputs/resumes/backend.tex", "\\documentclass{article}\n")
        self.repo()   # its seed commit is the save
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget\nperiod: 2031-01\nstatus: consolidated\n---\n\n"
                                                "# Widget\n\nMore.\n")
        self.git("commit", "-qam", "log(widget): result")
        added = []

        def add():
            n = len(added) + 2
            self.write("entries/2032-0%d-part%d.md" % (n, n),
                       "---\ntitle: Part %d\nperiod: 2032-0%d\nstatus: consolidated\n---\n\n# Part %d\n" % (n, n, n))
            self.git("add", "-A")
            self.git("commit", "-qm", "log(part%d): start" % n)
            added.append(n)
        return add

    def stale_lines(self, mode, *args):
        return [l for l in self.done(mode, *args)[1] if "Target version" in l]

    def test_stale_count_two_says_nothing(self):
        add = self.stale_log()
        start = "%s@0" % self.head()
        add()   # this run: 1 -> 2
        self.assertEqual(self.stale_lines("consolidate", "--since", start), [])
        self.assertEqual(self.done("log"), (0, []))

    def test_stale_count_reaching_three_points_at_audit(self):
        add = self.stale_log()
        add()
        start = "%s@0" % self.head()
        add()   # this run: 2 -> 3
        line = ('Next: `audit` (say "audit my career log"). Target version `backend` has 3 entries behind its last'
                ' save: Widget (entries/2031-01-widget.md, changed), Part 2 (entries/2032-02-part2.md, new), Part 3'
                ' (entries/2032-03-part3.md, new). It decides whether to refresh the Target version')
        code, out = self.done("consolidate", "--since", start)
        self.assertEqual(code, 0, out)
        self.assertIn(line + ".", out)
        self.assertIn(check.FRESH, out)
        self.assertFalse(any(l.startswith("Also available: `audit`") for l in out), out)   # named once
        code, out = self.done("log")   # log's change is its last commit, step 4's
        self.assertEqual(code, 0)
        # no English request to copy (#624): the agent words it in the user's language
        self.assertEqual(out[0], line.replace(' (say "audit my career log")', "", 1) + ".")
        self.assertFalse(any("audit my career log" in l for l in out), out)
        self.assertTrue(out[-1].startswith("next: add it to the one-line report"), out)
        self.assertEqual(len(out), 2)

    def test_stale_count_four_says_nothing_again(self):
        add = self.stale_log()
        add()
        add()
        start = "%s@0" % self.head()
        add()   # this run: 3 -> 4
        self.assertEqual(self.stale_lines("consolidate", "--since", start), [])
        self.assertEqual(self.done("log"), (0, []))

    def test_stale_count_jumping_past_three_still_points_at_audit(self):
        add = self.stale_log()
        add()
        start = "%s@0" % self.head()
        add()
        add()   # this run: 2 -> 4
        lines = self.stale_lines("consolidate", "--since", start)
        self.assertEqual(len(lines), 1)
        self.assertIn("has 4 entries behind its last save", lines[0])

    def test_stale_count_crossed_by_a_cited_entry_edit(self):
        self.stale_log()
        part = "---\ntitle: Part %d\nperiod: 2032-0%d\nstatus: consolidated\n---\n\n# Part %d\n%s"
        for n in (2, 3):
            self.write("entries/2032-0%d-part%d.md" % (n, n), part % (n, n, n, ""))
        self.write("outputs/resumes/backend.md", "# Backend\n\n| Bullet | Source |\n|---|---|\n"
                                                 "| Built it | entries/2031-01-widget.md |\n"
                                                 "| Ran it | entries/2032-02-part2.md |\n"
                                                 "| Led it | entries/2032-03-part3.md |\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "write(backend): resume")   # a save citing all three: count 0
        for n in (2, 3):
            self.write("entries/2032-0%d-part%d.md" % (n, n), part % (n, n, n, "\nMore.\n"))
        self.git("commit", "-qam", "log: two results")   # count 2
        start = "%s@0" % self.head()
        self.write("entries/2031-01-widget.md", "---\ntitle: Widget\nperiod: 2031-01\nstatus: consolidated\n---\n\n"
                                                "# Widget\n\nEven more.\n")
        self.git("commit", "-qam", "consolidate(widget): sections")   # this run: 2 -> 3, by an edit
        lines = self.stale_lines("consolidate", "--since", start)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("Widget (entries/2031-01-widget.md, changed)", lines[0])

    def test_stale_count_left_out_without_since_and_for_other_modes(self):
        add = self.stale_log()
        add()
        start = "%s@0" % self.head()
        add()
        self.assertEqual(self.stale_lines("consolidate"), [])   # no --since: this run's change is unknown
        self.assertEqual(self.stale_lines("import", "--since", start), [])
        check.UNATTENDED = True
        self.assertEqual(self.done("log"), (0, []))

    # ---- a posting run's save feeds Target versions and Direction (#614) ----

    APP = "2032-05-01-acme-product-manager"
    TARGET_TEX = ("\\documentclass{article}\n\\begin{document}\n\\section{Experience}\n\\begin{itemize}\n"
                  "  \\item Cut quote API p95 latency from 820 ms to 210 ms with a Redis rate cache\n"
                  "\\end{itemize}\n\\end{document}\n")
    NEW_BULLET = "Ran weekly roadmap reviews with sales and support for three product lines"
    SWAP_BULLET = "Cut checkout API p95 latency from 820 ms to 210 ms with a Redis rate cache"

    def posting_save(self, roles=("Backend engineer",), targets=("backend",), start=None, bullets=(NEW_BULLET,),
                     archived=False, accept=False, record=None, quotes='""', then_reference=False):
        """A Log with these Target roles and Target versions; then this run: a posting run whose draft
        recorded `start` (from, family, tier; None: no start.txt), saved with `bullets` added to an
        entry's Past phrasings, each between `quotes`. Returns done write's Next and Not read lines.
        `accept`: the run is a scan accept, its start.txt in the scan's draft folder, which `scan.py
        draft` copies (#626). `record`: start.txt's text as written, in place of `start`'s.
        `then_reference`: the save is Archived, then set to Reference in the same run (#661)."""
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n"
                   + "".join("%d. %s (user, 2032-01-01)\n" % (i, r) for i, r in enumerate(roles, 1)))
        for t in targets:
            self.write("outputs/resumes/%s.tex" % t, self.TARGET_TEX)
            self.write("outputs/resumes/%s.md" % t, "# %s\n" % t)
        entry = "---\ntitle: Widget\nperiod: 2031-01\nstatus: consolidated\n---\n\n# Widget\n\n## Past phrasings\n%s"
        self.write("entries/2031-01-widget.md", entry % "")
        self.write("README.md", README_HEAD + "| 2031-01 | [Widget](entries/2031-01-widget.md) | project | done |\n")
        self.repo()
        since = "%s@0" % self.head()
        if start and accept:
            draft = ".build/scan/2032-05-01/drafts/" + self.APP
            self.write(draft + "/start.txt", "from: %s\nfamily: %s\ntier: %s\n" % start)
            self.write("outputs/reports/2032-05-01-scan.md", "# Scan 2032-05-01\n\n## Pending\n\n| URL | Company | Role"
                       " | Status | Draft | Fit map commit |\n|---|---|---|---|---|---|\n| https://acme.example/j/1 |"
                       " Acme | Product Manager | draft to review | %s/ | - |\n" % draft)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(check.tools_module("scan").main(["--root", self.root, "draft",
                                                                  "https://acme.example/j/1"]), 0)
            self.assertTrue(os.path.isfile(os.path.join(self.root, ".build/drafts", self.APP, "start.txt")))
        elif start:
            self.write(".build/drafts/%s/start.txt" % self.APP, "from: %s\nfamily: %s\ntier: %s\n" % start)
        if record is not None:
            self.write(".build/drafts/%s/start.txt" % self.APP, record)
        folder = "outputs/applications/" + self.APP
        self.write(folder + "/resume.tex", self.TARGET_TEX)
        self.write(folder + "/provenance.md", "# Provenance\n")
        if archived or then_reference:
            self.write(folder + "/archived.md", "Archived (user, 2032-05-01)\n")
        self.write("entries/2031-01-widget.md", entry % "".join(
            '- **backend:** %s%s%s (%s)\n' % (quotes[0], b, quotes[1], folder) for b in bullets))
        self.git("add", "-A")
        self.git("commit", "-qm", "write(acme): Product Manager")
        if then_reference:
            self.git("rm", "-q", folder + "/archived.md")
            self.git("commit", "-qm", "write(acme): Product Manager to Reference")
        return [l for l in self.done("write", "--since", since)[1] if l.startswith(("Next:", "Not read:"))]

    # ---- #661: the start record, the subject and the Past phrasings line as application.py reads them ----

    def test_a_record_lacking_a_line_says_so(self):
        nexts = self.posting_save(record="from: outputs/resumes/backend.tex\nfamily: backend\n")
        self.assertEqual(nexts, ["Not read: .build/drafts/%s/start.txt lacks tier: (application.py start --family"
                                 " --tier writes it), so outputs/applications/%s gets no Target version or Direction"
                                 " offer." % (self.APP, self.APP)])

    def test_the_role_leaves_out_a_level_change(self):
        nexts = self.posting_save(start=("outputs/resumes/backend.tex", "backend", "none"), bullets=(),
                                  then_reference=True)
        self.assertEqual(len(nexts), 1, nexts)
        self.assertTrue(nexts[0].startswith('Next: `setup` (say "add Product Manager to my target roles").'), nexts)

    def test_a_wording_in_corner_brackets_is_read_as_its_words(self):
        nexts = self.posting_save(start=("outputs/resumes/backend.tex", "backend", "1"), quotes="「」")
        self.assertEqual(len(nexts), 1, nexts)
        self.assertIn('Past phrasings: "%s" (Widget' % self.NEW_BULLET, nexts[0])

    def test_update_names_the_target_version_and_the_bullets(self):
        nexts = self.posting_save(start=("outputs/resumes/backend.tex", "backend", "1"),
                                  bullets=(self.NEW_BULLET, self.SWAP_BULLET))
        self.assertEqual(nexts, ['Next: `write` (say "update my backend resume with the new bullets"). Target version'
                                 ' `backend` lacks 1 bullet this save added to Past phrasings: "%s" (Widget,'
                                 ' entries/2031-01-widget.md). A target run for `backend` decides which to bring'
                                 ' in.' % self.NEW_BULLET])

    def test_update_left_out_when_no_bullet_was_added(self):
        for bullets in ((), (self.SWAP_BULLET,)):   # none, or only a swap of the posting's terms
            with self.subTest(bullets=bullets):
                self.setUp()
                self.assertEqual(self.posting_save(start=("outputs/resumes/backend.tex", "backend", "1"),
                                                   bullets=bullets), [])

    def test_create_from_the_fallback_seeded_from_the_approved_resume(self):
        nexts = self.posting_save(start=("sources/resumes/2030-01-01-main.tex", "pm", "1"), roles=("PM",))
        self.assertEqual(nexts, ['Next: `write` (say "make my first pm resume from the %s application"). No Target'
                                 ' version is close to this role (this run started from'
                                 ' sources/resumes/2030-01-01-main.tex): a target run creates `pm`, seeded from this'
                                 ' application\'s approved resume (outputs/applications/%s/resume.tex), which it'
                                 ' generalises (it drops the posting\'s own terms and company emphasis) and reviews'
                                 ' on its own.' % (self.APP, self.APP)])

    def test_create_from_another_role_familys_target_version(self):
        nexts = self.posting_save(start=("outputs/resumes/backend.tex", "pm", "2"), roles=("Backend", "PM"))
        self.assertEqual(len(nexts), 1, nexts)
        self.assertIn("a target run creates `pm`", nexts[0])
        self.assertIn("started from outputs/resumes/backend.tex", nexts[0])

    def test_create_is_general_only_while_target_roles_are_empty(self):
        nexts = self.posting_save(start=(check.tools_module("application").BLANK, "general", "none"), roles=(),
                                  targets=())
        self.assertEqual(len(nexts), 2, nexts)
        self.assertIn("a target run creates `general`", nexts[0])
        self.assertTrue(nexts[1].startswith('Next: `setup` (say "add Product Manager to my target roles")'), nexts)

    def test_a_family_with_a_target_version_gets_update_never_create(self):
        nexts = self.posting_save(start=("sources/resumes/2030-01-01-main.tex", "backend", "1"))   # user named a file
        self.assertEqual(len(nexts), 1, nexts)
        self.assertTrue(nexts[0].startswith('Next: `write` (say "update my backend resume'), nexts)
        self.setUp()
        self.assertEqual(self.posting_save(start=("sources/resumes/2030-01-01-main.tex", "backend", "1"),
                                           bullets=()), [])

    def test_direction_offered_only_for_a_role_outside_target_roles(self):
        nexts = self.posting_save(start=("outputs/resumes/backend.tex", "backend", "none"), bullets=())
        self.assertEqual(nexts, ['Next: `setup` (say "add Product Manager to my target roles"). Product Manager is'
                                 ' not among Direction\'s target roles, and `rank`, `scan` and `fit` order by that'
                                 ' list.'])

    def test_an_archived_save_gets_no_offer(self):
        self.assertEqual(self.posting_save(start=("sources/resumes/2030-01-01-main.tex", "pm", "none"),
                                           archived=True), [])

    def test_a_scan_accept_saved_at_reference_gets_the_posting_runs_offers(self):
        start = ("sources/resumes/2030-01-01-main.tex", "pm", "none")
        posting_run = self.posting_save(start=start, roles=("PM",))
        self.setUp()
        self.assertEqual(self.posting_save(start=start, roles=("PM",), accept=True), posting_run)
        self.assertEqual(len(posting_run), 2, posting_run)   # Create and Direction

    def test_a_scan_accept_saved_at_archived_gets_no_offer(self):
        self.assertEqual(self.posting_save(start=("sources/resumes/2030-01-01-main.tex", "pm", "none"),
                                           archived=True, accept=True), [])

    def test_no_offer_without_a_start_record_or_since(self):
        self.assertEqual(self.posting_save(start=None), [])
        self.setUp()
        self.posting_save(start=("sources/resumes/2030-01-01-main.tex", "pm", "none"))
        self.assertEqual(self.next_line("write"), None)   # no --since: this run's save is unknown

    def test_log_and_unattended_print_nothing(self):
        self.assertEqual(self.done("log"), (0, []))
        check.UNATTENDED = True
        self.assertEqual(self.done("write"), (0, []))

    # ---- done rank: the top target role's Target version (#615) ----

    def rank_nexts(self, roles, targets, *args):
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n"
                   + "".join("%d. %s\n" % (i, r) for i, r in enumerate(roles, 1)))
        for t in targets:
            self.write("outputs/resumes/%s.tex" % t, self.TARGET_TEX)
        code, out = self.done("rank", *args)
        self.assertEqual(code, 0, out)
        return [l for l in out if l.startswith("Next:")]

    RANK_LINE = ('Next: `write` (say "make a Backend engineer resume"). Your top target role, Backend engineer, has no'
                 ' Target version, and it is what you hand out where there is no posting, as at this ranking\'s'
                 ' event: a target run creates one.')

    def test_rank_offers_a_target_run_when_the_top_role_has_no_target_version(self):
        self.assertEqual(self.rank_nexts(("GAP: ask", "Backend engineer (user, 2032-01-01)", "PM"), ()),
                         [self.RANK_LINE])   # none at all; the role named without its citation
        self.assertEqual(self.rank_nexts(("Backend engineer", "PM"), ("pm",), "--family", "backend"), [self.RANK_LINE])

    def test_rank_says_nothing_when_the_top_role_has_one_or_roles_are_empty(self):
        self.assertEqual(self.rank_nexts(("Backend engineer",), ("backend",), "--family", "backend"), [])
        self.assertEqual(self.rank_nexts((), ("backend",)), [])
        self.assertEqual(self.rank_nexts((), ()), [])

    def test_rank_needs_family_while_a_target_version_exists(self):
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n1. Backend engineer\n")
        self.write("outputs/resumes/pm.tex", self.TARGET_TEX)
        for args in ([], ["--family"], ["--family", "Back End"]):
            code, out = self.done("rank", *args)
            self.assertEqual(code, 2, (args, out))
            self.assertTrue(out[0].startswith("usage:"), out)
        self.assertEqual(self.done("write", "--family", "pm")[0], 2)   # rank only
        check.UNATTENDED = True   # no block at all, so nothing to refuse
        self.assertEqual(self.done("rank"), (0, []))

    def test_bad_arguments(self):
        for args in (["deploy"], [], ["fit", "--since"], ["setup", "--for", "deploy"], ["fit", "--for", "write"]):
            code, out = self.done(*args)
            self.assertEqual(code, 2, args)
            self.assertTrue(out[0].startswith("usage:"), out)

    def test_main_runs_done(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check.main(["done", "log"])
        self.assertEqual((code, out.getvalue()), (0, ""))

    # ---- done: what was saved ----

    def test_uncommitted_log_change_holds_the_fresh_line(self):
        self.entry("consolidated")
        self.repo()
        self.write("entries/2031-01-widget.md", "changed\n")
        code, out = self.done("fit")
        self.assertEqual(code, 1)
        self.assertNotIn(check.FRESH, out)
        self.assertIn("Not saved yet: 1 Log file(s) not committed (M entries/2031-01-widget.md). Save it before"
                      " you leave this session.", out)
        self.assertTrue(out[-1].startswith("next: now, first: settle what is not saved"))

    def test_a_live_runs_files_are_not_unsaved(self):
        self.entry("consolidated")
        self.repo()
        live = os.path.join(self.root, ".build", "runs", "2031-01-02-100000", "live")
        os.makedirs(os.path.dirname(live))
        start = datetime.datetime.fromtimestamp(int(time.time() - 600)).astimezone()
        with open(live, "w", encoding="utf-8") as f:
            json.dump({"start": start.isoformat(), "mode": "write"}, f)
        self.write("entries/2031-01-widget.md", "another session's fact\n")
        code, out = self.done("fit")
        self.assertEqual(code, 0, out)
        self.assertFalse([l for l in out if l.startswith("Not saved yet")], out)
        os.remove(live)   # that run ended without saving: its file is this Log's to settle again
        code, out = self.done("fit")
        self.assertEqual(code, 1)
        self.assertIn("Not saved yet: 1 Log file(s) not committed (M entries/2031-01-widget.md). Save it before"
                      " you leave this session.", out)

    def test_uncommitted_talking_points_and_guard_files_count(self):
        self.entry("consolidated")
        self.repo()
        self.write("stories/conflict.md", "# Conflict\n")
        self.write(".export-deny", "acme\n")
        code, out = self.done("stories")
        self.assertEqual(code, 1)
        self.assertIn("Not saved yet: 2 Log file(s) not committed (?? stories/conflict.md, ?? .export-deny). Save it"
                      " before you leave this session.", out)

    def test_changed_talking_points_file_keeps_its_name(self):
        self.entry("consolidated")
        self.write("stories/team.md", "# Team\n")
        self.repo()
        self.write("stories/team.md", "# Team, changed\n")
        _, out = self.done("stories")
        self.assertIn("Not saved yet: 1 Log file(s) not committed (M stories/team.md). Save it before you leave"
                      " this session.", out)

    def test_commits_not_pushed_hold_the_fresh_line(self):
        self.entry("consolidated")
        self.repo()
        remote = os.path.join(self.root, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", remote], check=True, capture_output=True)
        self.write(".gitignore", "remote.git/\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "ignore")
        self.git("remote", "add", "origin", remote)
        self.git("push", "-q", "origin", "HEAD:refs/heads/main")
        self.git("remote", "set-head", "origin", "main")
        self.git("branch", "-m", "main")   # sync.py pushes from the default branch only
        self.assertEqual(self.done("fit")[0], 0)
        self.write("profile.md", "b\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "profile")
        code, out = self.done("fit")
        self.assertEqual(code, 1)
        self.assertIn("Not saved yet: 1 commit(s) not pushed (`sync.py push` pushes them). Save it before you leave this session.", out)
        self.assertIn("When it cannot be settled (a push that fails), say what failed and end your last message with"
                      " the block above", out[-1])
        push = '`%s -I "%s" push`' % (check.python_cmd(), os.path.join(self.root, "tools", "sync.py"))
        self.assertIn("(commits not pushed: %s; in the upgrade mode before its step 5" % push, out[-1])
        p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "..", "sync.py"), "--root", self.root, "push"],
                           capture_output=True, encoding="utf-8", env={k: v for k, v in os.environ.items()
                                                                        if k != "CAREER_LOG_UNATTENDED"})
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(subprocess.run(["git", "-C", self.root, "rev-list", "--count", "origin/main..HEAD"],
                                        capture_output=True, text=True).stdout.strip(), "0")
        self.assertEqual(self.done("fit")[0], 0)   # the one command above saved it
        self.write("profile.md", "c\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "profile again")
        self.assertIn("then go on with write", check.done(["setup", "--for", "write"], root=self.root)[1][-1])
        self.git("checkout", "-q", "-b", "topic")   # a branch's upstream wins over origin's default
        self.git("push", "-q", "-u", "origin", "topic")
        self.write("direction.md", "c\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "direction")
        out = self.done("fit")[1]   # sync.py push refuses here, so the block does not name it
        self.assertIn("Not saved yet: 1 commit(s) not pushed. Save it before you leave this session.", out)
        self.assertNotIn("sync.py", out[-1])
        self.git("push", "-q")
        self.assertEqual(self.done("fit")[0], 0)

    def test_since_lists_this_modes_commits_only(self):
        self.repo()
        start = self.head()
        self.write("stories.md", "a\n")   # a pulled commit: committed before the mode started
        self.git("add", "-A")
        self.git("commit", "-qm", "pulled: from another machine", env={"GIT_COMMITTER_DATE": "2000-01-01T00:00:00"})
        self.write("profile.md", "b\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "fit(åcme-dév): 2 gaps")
        _, out = self.done("fit", "--since", "%s@%d" % (start, 1000000000))
        self.assertEqual(out[1:3], ["Saved: 1 commit; its subject:", "  fit(åcme-dév): 2 gaps"])   # no hash
        self.write("direction.md", "c\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "direction: remote only")
        _, out = self.done("fit", "--since", "%s@%d" % (start, 1000000000))
        self.assertEqual(out[1:4], ["Saved: 2 commits; their subjects:", "  direction: remote only",
                                    "  fit(åcme-dév): 2 gaps"])
        _, out = self.done("fit", "--since", "%s@99999999999" % start)
        self.assertEqual(out[1], "Saved: no commit (this mode changed nothing in the Log)")
        _, out = self.done("fit", "--since", "nosuchsha@1")
        self.assertTrue(out[1].startswith("Saved: not listed (nosuchsha@1 is not"), out[1])


UPDATE_LINE = ('update: v0.3.0 available (you have v0.2.0): tell the user once this session, in passing, and go on;'
               ' only their request ("upgrade") starts the upgrade mode, and `update_check = "off"` in config.toml'
               ' stops this line (setup › Changes)')


class ReleaseTest(unittest.TestCase):
    """check_release: the `update:` line, against a fake Releases API on this machine."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.home, ignore_errors=True))
        self.root = os.path.join(self.home, "root")
        os.makedirs(os.path.join(self.root, "tools"))
        shutil.copy(DEFAULTS, os.path.join(self.root, "config.toml"))
        self.stamp("0.2.0")
        for name in ("UNATTENDED", "RELEASES_URL"):
            self.addCleanup(setattr, check, name, getattr(check, name))
        check.UNATTENDED = False
        self.requests, self.body, self.delay = [], b'{"tag_name": "v0.3.0"}', 0
        test = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                test.requests.append(dict(self.headers))
                time.sleep(test.delay)
                try:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(test.body)
                except OSError:   # the check gave up first
                    pass

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        check.RELEASES_URL = "http://127.0.0.1:%d/releases/latest" % server.server_address[1]

    def stamp(self, text):
        with open(os.path.join(self.root, "tools", "TEMPLATE_VERSION"), "w", encoding="utf-8") as f:
            f.write(text + "\nsource 0123abc\n")

    def release(self):
        return check.check_release(check.Context("log", root=self.root, home=self.home))

    def forget(self):
        shutil.rmtree(os.path.join(self.home, ".career-log"), ignore_errors=True)

    def cache(self):
        with open(os.path.join(self.home, ".career-log", "release.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_newer_release(self):
        self.assertEqual(self.release(), ([UPDATE_LINE], [], False))
        self.assertEqual(self.cache()["latest"], "0.3.0")
        self.assertNotIn("Authorization", self.requests[0])

    def test_same_or_older_release_is_silent(self):
        for tag in (b"v0.2.0", b"v0.1.9"):
            self.forget()
            self.body = b'{"tag_name": "%s"}' % tag
            self.assertEqual(self.release(), ([], [], False), tag)

    def test_asks_once_a_day(self):
        self.release()
        self.assertEqual(self.release()[0], [UPDATE_LINE])
        self.assertEqual(len(self.requests), 1)
        cache = self.cache()
        for checked in (cache["checked"] - check.RELEASE_EVERY - 1, cache["checked"] + 3600):   # a day old; ahead
            with open(os.path.join(self.home, ".career-log", "release.json"), "w", encoding="utf-8") as f:
                json.dump({"checked": checked, "latest": "0.3.0"}, f)
            self.release()
        self.assertEqual(len(self.requests), 3)
        with open(os.path.join(self.home, ".career-log", "release.json"), "w", encoding="utf-8") as f:
            f.write("{")   # cut short: ask again
        self.release()
        self.assertEqual(len(self.requests), 4)

    def test_offline_is_silent_and_waits_a_day(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        check.RELEASES_URL = "http://127.0.0.1:%d/" % sock.getsockname()[1]   # bound, never listening
        sock.close()
        self.assertEqual(self.release(), ([], [], False))
        self.assertIsNone(self.cache()["latest"])
        self.assertEqual(self.release(), ([], [], False))   # from the cache: no second try today

    def test_slow_server_is_cut_off(self):
        self.delay = check.RELEASE_TIMEOUT + 2
        start = time.monotonic()
        self.assertEqual(self.release(), ([], [], False))
        self.assertLess(time.monotonic() - start, check.RELEASE_TIMEOUT + 0.5)

    def test_bad_answers_are_silent(self):
        for body in (b"not json", b'{"message": "API rate limit exceeded"}', b'{"tag_name": "latest"}', b"[]"):
            self.forget()
            self.body = body
            self.assertEqual(self.release(), ([], [], False), body)

    def test_off_unattended_or_unreleased_never_asks(self):
        with open(os.path.join(self.root, "config.toml"), "a", encoding="utf-8") as f:
            f.write('update_check = "off"\n')
        self.assertEqual(self.release(), ([], [], False))
        shutil.copy(DEFAULTS, os.path.join(self.root, "config.toml"))
        check.UNATTENDED = True
        self.assertEqual(self.release(), ([], [], False))
        check.UNATTENDED = False
        self.stamp("next")
        self.assertEqual(self.release(), ([], [], False))
        os.remove(os.path.join(self.root, "tools", "TEMPLATE_VERSION"))
        self.assertEqual(self.release(), ([], [], False))
        self.assertEqual(self.requests, [])
        self.assertFalse(os.path.exists(os.path.join(self.home, ".career-log")))


if __name__ == "__main__":
    unittest.main()
