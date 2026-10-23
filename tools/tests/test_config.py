#!/usr/bin/env python3
"""Tests for tools/config.py, on config.toml files written in a temporary directory.

  python3 -I tools/tests/test_config.py
"""
import importlib.util, io, os, shutil, subprocess, sys, tempfile, tomllib, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "config.py")
spec = importlib.util.spec_from_file_location("config", TOOL)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    def run_tool(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = config.main(list(args) + ["--root", self.root])
        return code, out.getvalue().splitlines()

    def write(self, text):
        with open(os.path.join(self.root, "config.toml"), "w", encoding="utf-8") as f:
            f.write(text)

    def read(self):
        with open(os.path.join(self.root, "config.toml"), encoding="utf-8") as f:
            return f.read()

    def test_help(self):
        for args in (["--help"], ["set", "-h"]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 0, args)
            self.assertEqual(lines, config.__doc__.splitlines(), args)

    def test_defaults_file_holds_every_field_with_an_allowed_value(self):
        base = config.defaults()
        self.assertEqual(sorted(base), sorted(config.FIELDS))
        for field, value in base.items():
            config.check_value(field, value)

    def test_show_missing(self):
        self.assertEqual(self.run_tool("show"), (1, ["config.toml: missing (setup has not run for this Log)"]))

    def test_init_writes_defaults_and_refuses_twice(self):
        code, lines = self.run_tool("init")
        self.assertEqual(code, 0)
        self.assertIn('record_language = "English"', lines)
        self.assertIn("# How the Engine runs", self.read())
        self.assertEqual(self.run_tool("init")[0], 1)

    def test_missing_field_takes_its_default(self):
        self.write('front_page = "trimmed"\n')
        code, lines = self.run_tool("show")
        self.assertEqual(code, 0)
        self.assertEqual(lines, ['record_language = "English" (default)', 'interviewer_profiles = "never" (default)',
                                 'front_page = "trimmed"', 'window = 7 (default)', 'scheduled_window = "window" (default)',
                                 'screen_budget = 40 (default)', 'fit_budget = 15 (default)', 'n = 10 (default)', 'auto_write = "off" (default)',
                                 'm = 5 (default)'])

    def test_numbers_are_written_without_quotes(self):
        self.run_tool("init")
        code, lines = self.run_tool("set", "m", "20")
        self.assertEqual(lines, ["before: m = 5", "after: m = 20", "written"])
        self.assertIn("\nm = 20\n", self.read())
        code, lines = self.run_tool("set", "scheduled_window", "1")
        self.assertEqual(lines, ['before: scheduled_window = "window"', "after: scheduled_window = 1", "written"])
        self.assertEqual(self.run_tool("set", "scheduled_window", "window")[1][-1], "written")
        self.assertEqual(self.run_tool("set", "window", "7")[1][-1], "unchanged")
        with open(os.path.join(self.root, "config.toml"), "rb") as f:
            data = tomllib.load(f)
        self.assertEqual((data["m"], data["scheduled_window"], data["window"]), (20, "window", 7))

    def test_numbers_out_of_range_are_refused(self):
        self.run_tool("init")
        before = self.read()
        for args in (("m", "21"), ("m", "0"), ("window", "91"), ("window", "seven"), ("fit_budget", "-1"),
                     ("n", "1.5"), ("auto_write", "yes"), ("scheduled_window", "0")):
            code, lines = self.run_tool("set", *args)
            self.assertEqual(code, 1, args)
            self.assertTrue(lines[0].startswith("config: "), lines)
        self.assertEqual(self.read(), before)
        for text in ('m = "5"\n', "m = true\n", "window = 7.0\n", 'record_language = 3\n'):
            self.write(text)
            self.assertEqual(self.run_tool("show")[0], 1, text)

    def test_fit_budget_never_above_screen_budget(self):
        self.run_tool("init")
        before = self.read()
        code, lines = self.run_tool("set", "fit_budget", "50")
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["config: fit_budget = 50 would put fit_budget above screen_budget (40); change screen_budget first"])
        code, lines = self.run_tool("set", "screen_budget", "10")
        self.assertEqual(lines, ["config: screen_budget = 10 would put fit_budget above screen_budget (10); change fit_budget first"])
        self.assertEqual(self.run_tool("set", "fit_budget", "50", "--dry-run")[0], 1)   # setup's dry run refuses too
        self.assertEqual(self.read(), before)
        self.assertEqual(self.run_tool("set", "screen_budget", "15")[1][-1], "written")   # equal is allowed
        self.assertEqual(self.run_tool("set", "screen_budget", "101")[0], 1)
        self.write("screen_budget = 5\nfit_budget = 15\n")   # a hand edit still loads: scan refuses at run time
        self.assertEqual(self.run_tool("show")[0], 0)

    def test_set_changes_one_line_and_keeps_comments(self):
        self.run_tool("init")
        before = self.read()
        code, lines = self.run_tool("set", "record_language", "繁體中文")
        self.assertEqual(code, 0)
        self.assertEqual(lines, ['before: record_language = "English"', 'after: record_language = "繁體中文"', "written"])
        after = self.read()
        self.assertEqual(after, before.replace('record_language = "English"', 'record_language = "繁體中文"'))
        with open(os.path.join(self.root, "config.toml"), "rb") as f:
            self.assertEqual(tomllib.load(f)["record_language"], "繁體中文")

    def test_set_appends_a_field_left_out(self):
        self.write('record_language = "English"\n')
        code, lines = self.run_tool("set", "interviewer_profiles", "always")
        self.assertEqual(lines[0], 'before: interviewer_profiles = "never" (default)')
        self.assertEqual(self.read(), 'record_language = "English"\ninterviewer_profiles = "always"\n')

    def test_dry_run_writes_nothing(self):
        self.run_tool("init")
        before = self.read()
        code, lines = self.run_tool("set", "front_page", "trimmed", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(lines[-1], "dry run: nothing written")
        self.assertEqual(self.read(), before)

    def test_unchanged_value(self):
        self.write('front_page = "full"\n')
        self.assertEqual(self.run_tool("set", "front_page", "full")[1][-1], "unchanged")

    def test_set_refuses_unknown_names_and_values(self):
        self.run_tool("init")
        before = self.read()
        for args in (("language", "English"), ("target roles", "backend"), ("front_page", "half"),
                     ("interviewer_profiles", "ask"), ("record_language", 'say "hi"'), ("record_language", " ")):
            code, lines = self.run_tool("set", *args)
            self.assertEqual(code, 1, args)
            self.assertTrue(lines[0].startswith("config: "), lines)
        self.assertEqual(self.read(), before)

    def test_set_never_writes_a_file_that_does_not_parse(self):
        self.write('"record_language" = "English"\n')   # a quoted key: valid, but the line is not found
        code, lines = self.run_tool("set", "record_language", "Deutsch")
        self.assertEqual(code, 1)
        self.assertEqual(self.read(), '"record_language" = "English"\n')

    def test_a_bom_is_read(self):
        with open(os.path.join(self.root, "config.toml"), "w", encoding="utf-8-sig") as f:
            f.write('front_page = "trimmed"\n')
        self.assertEqual(self.run_tool("show")[0], 0)
        self.assertEqual(self.run_tool("set", "front_page", "full")[1][-1], "written")

    def test_set_without_config_refuses(self):
        code, lines = self.run_tool("set", "front_page", "trimmed")
        self.assertEqual(code, 1)
        self.assertIn("config.py init", lines[0])

    def test_bad_files_are_reported(self):
        for text in ("record_language = \n", 'colour = "blue"\n', "front_page = 3\n"):
            self.write(text)
            code, lines = self.run_tool("show")
            self.assertEqual(code, 1, text)
            self.assertTrue(lines[0].startswith("config: "), lines)

    def test_fields_lists_config_and_direction(self):
        code, lines = self.run_tool("fields")
        self.assertEqual(code, 0)
        self.assertIn('config: interviewer_profiles ("never" or "always")', lines)
        self.assertIn("config: m (a whole number from 1 to 20)", lines)
        self.assertIn('config: scheduled_window ("window" or a whole number from 1 to 90)', lines)
        self.assertIn("direction: work authorisation (direction.md › Constraints)", lines)

    def test_bad_arguments(self):
        self.assertEqual(self.run_tool()[0], 2)
        self.assertEqual(self.run_tool("set", "front_page")[0], 2)
        self.assertEqual(self.run_tool("delete")[0], 2)

    def test_runs_as_a_script(self):
        run = subprocess.run([sys.executable, "-I", TOOL, "init", "--root", self.root], capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        run = subprocess.run([sys.executable, "-I", TOOL, "set", "record_language", "日本語", "--root", self.root],
                             capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertIn('after: record_language = "日本語"', run.stdout.decode("utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
