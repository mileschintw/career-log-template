#!/usr/bin/env python3
"""Tests for tools/check.py: what it prints for each machine.toml choice and tool state.

  python3 -I tools/tests/test_check.py

The tool states are faked, so the tests pass on any machine whatever it has installed.
"""
import importlib.util, io, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "check.py")
spec = importlib.util.spec_from_file_location("check", TOOL)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

DEFAULTS = os.path.join(HERE, "..", "config.default.toml")
SCRIPTS = ("check.py", "resume.py", "entries.py", "config.py", "config.default.toml")

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
        check.Context = lambda mode: self.saved_context(mode, root=root, home=home)
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
        self.assertEqual([l for l in lines if l.startswith("next:")], ["next: go on with the mode"])

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

    def test_checkout_skill_installed_without_question(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["playwright-cli skill: missing"], [], ["skill"], []))
        code, lines = self.run_check("import")
        self.assertEqual(code, 0)
        self.assertTrue(any("install --skills" in l and "with no question" in l for l in lines))

    def test_off_path_prints_the_path_line(self):
        self.machine("playwright-cli = true\n")
        self.state(playwright_cli=(["node: ok but not on this shell's PATH"], [], [], ["/h/.nvm/versions/node/v22/bin"]))
        code, lines = self.run_check("rank")
        self.assertTrue(any("/h/.nvm/versions/node/v22/bin" in l for l in lines))

    def test_sudo_piece_prints_the_command_for_the_user(self):
        self.state(tinytex=(["pdftotext: missing"], ["sudo:poppler:sudo apt-get install poppler-utils"], [], []))
        code, lines = self.run_check("write")
        line = [l for l in lines if "sudo apt-get install poppler-utils" in l]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0].startswith(PDF + "stop: missing: poppler"))
        self.assertIn("in their own terminal", line[0])
        self.assertFalse(any("setup.sh" in l or "setup.ps1" in l for l in lines))

    def test_user_piece_is_told_not_installed(self):
        self.state(tinytex=(["pdftotext: missing"], ["user:poppler:install poppler yourself"], [], []))
        code, lines = self.run_check("write")
        self.assertTrue(any(l.startswith(PDF + "stop: missing: poppler") and "Tell the user to install poppler yourself" in l
                            for l in lines))

    def unattended(self):
        self.addCleanup(setattr, check, "UNATTENDED", check.UNATTENDED)
        check.UNATTENDED = True

    def test_unattended_run_installs_and_asks_nothing(self):
        self.unattended()
        self.machine("playwright-cli = true\n")
        self.state(tinytex=MISSING, playwright_cli=MISSING)
        for mode, prefix in (("write", PDF + "stop: setup is needed on this machine: x missing"),
                             ("rank", "next: when a page needs a Browser capture (item 2 of browser.md, Fallback order),"
                                      " first: setup is needed on this machine: x missing")):
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
        self.state(tinytex=(["pdftotext: missing"], ["sudo:poppler:sudo apt-get install poppler-utils"], [], []))
        code, lines = self.run_check("write")
        self.assertTrue(any(l.startswith(PDF + "stop: setup is needed on this machine: poppler missing") for l in lines))
        self.assertFalse(any("apt-get" in l for l in lines))

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
        self.assertIn("the links in %s" % os.path.join(self.home, ".local", "bin"), machine)
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
        self.assertEqual(machine.count("the links in %s" % local), 1, machine)

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
                    mock.patch.object(check, "playwright_core_cli", lambda cli: None), \
                    mock.patch.object(check, "which", lambda name, dirs: (node if name == "node" else "/fake/playwright-cli", True)):
                lines, machine, _, _ = self.browser_state(chrome=False, edge=edge)
            self.assertEqual(any(m.startswith("sudo:Chromium's system libraries:") for m in machine), asked, machine)
            self.assertEqual("browser libraries: missing (needs sudo)" in lines, asked, lines)

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
                    mock.patch.object(check, "playwright_core_cli", lambda cli: None), \
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

    def log_repo(self):
        """A Log repo with one committed entry, one Engine file and an ignored inbox."""
        root = os.path.join(self.home, "log")
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
        self.assertIn("Uncommitted Log changes", nexts[0])

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

    def test_uncommitted_line_comes_before_go_on(self):
        root = self.log_repo()
        self.write(root, "profile.md", "p\n")
        home = self.home
        check.Context = lambda mode: self.saved_context(mode, root=root, home=home)
        code, lines = self.run_check("log")
        self.assertEqual(code, 0)
        self.assertTrue(lines[-2].startswith("next: now, first:"))
        self.assertEqual(lines[-1], "next: go on with the mode")

    def test_entry_over_threshold_is_listed_and_the_mode_goes_on(self):
        root = self.log_repo()
        self.write(root, "entries/2024-03-long.md", "x" * 40000)   # about 14,800 tokens
        self.write(root, "entries/_template.md", "x" * 40000)      # the template is not an entry
        home = self.home
        check.Context = lambda mode: self.saved_context(mode, root=root, home=home)
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
                                 "config fit_budget: 15 (default)", "config n: 10 (default)", "config auto_write: off (default)", "config m: 5 (default)"])

    def test_unreadable_or_unknown_field_stops(self):
        for text in ("record_language = \n", 'colour = "blue"\n', 'front_page = "half"\n'):
            lines, nexts, stop = self.config("log", text)
            self.assertTrue(stop, text)
            self.assertTrue(lines[0].startswith("config: unreadable"), lines)
            self.assertTrue(nexts[0].startswith("next: stop: show the user the error"))

    def test_whole_run_stops_before_tools(self):
        out = io.StringIO()
        saved = check.Context
        self.addCleanup(lambda: setattr(check, "Context", saved))
        check.Context = lambda mode: saved(mode, root=self.root, home=self.root)
        with redirect_stdout(out):
            code = check.main(["write"])
        self.assertEqual(code, 1)
        self.assertFalse(any("tinytex" in l for l in out.getvalue().splitlines()))


if __name__ == "__main__":
    unittest.main()
