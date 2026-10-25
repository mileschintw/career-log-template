#!/usr/bin/env python3
"""Tests for tools/config.py, on config.toml files written in a temporary directory.

  python3 -I tools/tests/test_config.py
"""
import datetime, importlib.util, io, os, shutil, subprocess, sys, tempfile, tomllib, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "config.py")
TEMPLATE = os.path.join(HERE, "..", "template")
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
        code, lines = self.run_tool("show")
        self.assertEqual((code, lines[0]), (1, "config.toml: missing (setup has not run for this Log)"))
        self.assertEqual(lines[1:], ["direction %s: unreadable (direction.md is missing)" % i for i in config.DIRECTION])

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
        self.assertEqual(lines[:len(config.FIELDS)], ['record_language = "English" (default)', 'interviewer_profiles = "never" (default)',
                                 'front_page = "trimmed"', 'window = 7 (default)', 'scheduled_window = "window" (default)',
                                 'screen_budget = 40 (default)', 'fit_budget = 15 (default)', 'n = 10 (default)', 'auto_write = "off" (default)',
                                 'm = 5 (default)', 'update_check = "on" (default)',
                                 'resume_max_pages = 1 (default)'])

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

    def test_interviewer_profiles_notice(self):
        self.write('record_language = "English"\n')
        code, lines = self.run_tool("set", "interviewer_profiles", "always", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(lines[-2:], [config.NOTICES["interviewer_profiles", "always"], "dry run: nothing written"])
        self.assertTrue(lines[-2].startswith("tell the user: the site may show each interviewer the visit"))
        self.assertNotIn("tell the user", " ".join(self.run_tool("set", "update_check", "off", "--dry-run")[1]))

    def test_dry_run_writes_nothing(self):
        self.run_tool("init")
        self.copy_front_page()
        before = self.read(), self.page()
        code, lines = self.run_tool("set", "front_page", "trimmed", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(lines[-1], "dry run: nothing written")
        self.assertTrue(lines[-2].startswith("front page: README.md above `## Entries` becomes the personal index"))
        self.assertEqual((self.read(), self.page()), before)
        self.assertTrue(os.path.exists(os.path.join(self.root, "README.zh-TW.md")))

    # ---- The front page ----

    def copy_front_page(self):
        for name in ("README.md", "README.zh-TW.md"):
            shutil.copy(os.path.join(TEMPLATE, name), os.path.join(self.root, name))
        with open(os.path.join(self.root, "README.md"), "a", encoding="utf-8") as f:
            f.write("| 2024 | [x](entries/x.md) | job | a | stub |\n")   # a row of the Log's own

    def page(self):
        with open(os.path.join(self.root, "README.md"), encoding="utf-8") as f:
            return f.read()

    def test_trim_writes_the_personal_index(self):
        self.run_tool("init")
        self.copy_front_page()
        self.assertEqual(config.front_page_state(self.root), "template")
        tail = self.page()[self.page().index("## Entries"):]
        code, lines = self.run_tool("set", "front_page", "trimmed")
        self.assertEqual((code, lines[-1]), (0, "written"))
        self.assertEqual(self.page(), "# career-log\n\nRaw records of my past work, projects and achievements, and the"
                         " resumes and answers derived from them.\n\nHow to use it: [docs/guide.md](docs/guide.md).\n\n" + tail)
        self.assertFalse(os.path.exists(os.path.join(self.root, "README.zh-TW.md")))
        self.assertIn('front_page = "trimmed"', self.read())
        self.assertEqual(config.front_page_state(self.root), "trimmed")

    def test_full_is_refused_until_the_page_is_restored(self):
        self.run_tool("init")
        self.copy_front_page()
        self.run_tool("set", "front_page", "trimmed")
        before = self.read()
        code, lines = self.run_tool("set", "front_page", "full")
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith('config: front_page stays "trimmed" until the front page is the Template'), lines)
        self.assertIn("README.md is trimmed now", lines[0])
        self.assertEqual(self.read(), before)
        self.copy_front_page()   # the user restores README.md, not yet README.zh-TW.md
        os.remove(os.path.join(self.root, "README.zh-TW.md"))
        self.assertEqual(self.run_tool("set", "front_page", "full")[0], 1)
        self.copy_front_page()
        code, lines = self.run_tool("set", "front_page", "full")
        self.assertEqual((code, lines[-1]), (0, "written"))

    def test_an_edited_page_is_left_as_it_is(self):
        self.run_tool("init")
        with open(os.path.join(self.root, "README.md"), "w", encoding="utf-8") as f:
            f.write("# My own page\n\n## Entries\n")
        self.assertEqual(config.front_page_state(self.root), "edited")
        before = self.read()
        code, lines = self.run_tool("set", "front_page", "trimmed")
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("config: README.md above `## Entries` is edited, neither"), lines)
        self.assertEqual((self.page(), self.read()), ("# My own page\n\n## Entries\n", before))
        os.remove(os.path.join(self.root, "README.md"))
        self.assertEqual(config.front_page_state(self.root), "missing")
        self.assertEqual(self.run_tool("set", "front_page", "trimmed")[0], 1)
        with open(os.path.join(self.root, "README.md"), "w", encoding="utf-8") as f:
            f.write(config.TRIMMED + "## Entries\n")   # trimmed by hand: the field follows
        self.assertEqual(self.run_tool("set", "front_page", "trimmed")[1][-1], "written")

    # ---- Direction ----

    def direction(self, text=None):
        p = os.path.join(self.root, "direction.md")
        if text is not None:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        with open(p, encoding="utf-8") as f:
            return f.read()

    def show_direction(self):
        return [l for l in self.run_tool("show")[1] if l.startswith("direction ")]

    def test_show_prints_each_direction_item(self):
        self.run_tool("init")
        self.direction("## Target roles, ranked\n<!-- 1. not a role -->\n1. Backend (user, 2026-01-01)\n2. Platform (user, 2026-01-01)\n\n"
                       "## Employer preferences\n- Small teams. (user, 2026-01-01)\n\n"
                       "## Constraints\nHard constraints: one bullet each.\n\n- **Work authorisation:** GAP: sponsorship?\n"
                       "- Remote only. (user, 2026-01-01)\n  - (and no travel)\n- **Visa:** no (user, 2026-01-01)\n")
        code, lines = self.run_tool("show")
        self.assertEqual(code, 0)
        self.assertEqual([l for l in lines if l.startswith("direction ")], [
            "direction target roles: Backend (user, 2026-01-01)",
            "direction target roles: Platform (user, 2026-01-01)",
            "direction sorting order: empty",                     # its section holds other lines only
            "direction work authorisation: empty",                # only a GAP: line
            "direction visa sponsorship: empty",
            "direction other hard constraints: Remote only. (user, 2026-01-01)",
            "direction other hard constraints:   - (and no travel)",   # an indented line, as it stands
            "direction other hard constraints: **Visa:** no (user, 2026-01-01)",
            "direction what to emphasise: unreadable (direction.md has no `## What to emphasise, by target` section)",
        ])
        self.direction("## Target roles, ranked\n- GAP: which roles?\n")
        self.assertEqual(self.show_direction()[0], "direction target roles: empty")

    def test_the_template_direction_is_all_empty(self):
        shutil.copy(os.path.join(TEMPLATE, "direction.md"), os.path.join(self.root, "direction.md"))
        self.assertEqual(self.show_direction(), ["direction %s: empty" % i for i in config.DIRECTION])

    def test_direction_items_match_direction(self):
        self.assertEqual(list(config.DIRECTION_LINES), list(config.DIRECTION))
        for item, (heading, _) in config.DIRECTION_LINES.items():
            self.assertTrue(config.DIRECTION[item] == heading or config.DIRECTION[item].startswith(heading + ","), item)

    def test_direction_set_writes_dated_lines_in_place(self):
        shutil.copy(os.path.join(TEMPLATE, "direction.md"), os.path.join(self.root, "direction.md"))
        before = self.direction()
        today = datetime.date.today().isoformat()
        code, lines = self.run_tool("direction", "set", "target roles", "Backend engineer", "Platform engineer")
        self.assertEqual((code, lines), (0, ["before: direction target roles: empty",
                                             "after: direction target roles: Backend engineer (user, %s)" % today,
                                             "after: direction target roles: Platform engineer (user, %s)" % today, "written"]))
        self.run_tool("direction", "set", "other hard constraints", "No relocation")
        self.run_tool("direction", "set", "work authorisation", "Citizen, no sponsorship needed")
        self.run_tool("direction", "set", "sorting order", "domain fit, then pay")
        self.run_tool("direction", "set", "what to emphasise", "the search project first", "--target", "Backend")
        after = self.direction()
        self.assertIn("<!-- A numbered list, best first. Setup fills it; empty until then. -->\n"
                      "1. Backend engineer (user, %s)\n2. Platform engineer (user, %s)\n\n## Employer" % (today, today), after)
        self.assertIn("- **Sorting order:** domain fit, then pay (user, %s)\n\n## Tools" % today, after)
        self.assertIn("F-1 or J-1 students.\n\n- **Work authorisation:** Citizen, no sponsorship needed (user, %s)\n"
                      "- No relocation (user, %s)\n\n## What" % (today, today), after)   # work authorisation first
        self.assertIn("- **Backend:** the search project first (user, %s)\n\n## Self" % today, after)
        self.assertEqual(after.count("\n"), before.count("\n") + 7)   # 7 new lines (one blank), nothing else moved

    def test_direction_set_replaces_only_its_own_lines(self):
        self.direction("## Target roles, ranked\n- Data engineer (user, 2025-01-01)\n\n"
                       "## Employer preferences\n- Small teams. (user, 2025-01-01)\n"
                       "- **Sorting order for ranking employers:** size. (user, 2025-01-01)\n\n"
                       "## Constraints\n- **Work authorisation:** none (user, 2025-01-01)\n- Remote only. (user, 2025-01-01)\n"
                       "- Start after June. (user, 2025-01-01)\n\n"
                       "## What to emphasise, by target\n- **Backend:** x (user, 2025-01-01)\n- **general:** y (user, 2025-01-01)\n")
        today = datetime.date.today().isoformat()
        self.run_tool("direction", "set", "target roles", "Backend")
        self.run_tool("direction", "set", "sorting order", "pay")
        code, lines = self.run_tool("direction", "set", "other hard constraints", "none")
        self.assertEqual(lines, ["before: direction other hard constraints: Remote only. (user, 2025-01-01)",
                                 "before: direction other hard constraints: Start after June. (user, 2025-01-01)",
                                 "after: direction other hard constraints: **Other hard constraints:** none (user, %s)" % today,
                                 "written"])
        self.run_tool("direction", "set", "what to emphasise", "z", "--target", "general")
        self.assertEqual(self.direction(), (
            "## Target roles, ranked\n1. Backend (user, %s)\n\n"
            "## Employer preferences\n- Small teams. (user, 2025-01-01)\n"
            "- **Sorting order for ranking employers:** pay (user, %s)\n\n"
            "## Constraints\n- **Work authorisation:** none (user, 2025-01-01)\n- **Other hard constraints:** none (user, %s)\n\n"
            "## What to emphasise, by target\n- **Backend:** x (user, 2025-01-01)\n- **general:** z (user, %s)\n") % ((today,) * 4))

    def test_direction_set_keeps_the_source_of_a_kept_line(self):
        self.direction("## Target roles, ranked\n1. Backend (user, 2025-01-01)\n2. Platform (cv, 2024-05-01)\n\n"
                       "## Constraints\n- **Work authorisation:** none (user, 2025-01-01)\n- Remote only. (user, 2025-01-01)\n")
        today = datetime.date.today().isoformat()
        code, lines = self.run_tool("direction", "set", "target roles", "Data", "Backend", "Platform")
        self.assertEqual(lines[-4:], ["after: direction target roles: Data (user, %s)" % today,
                                      "after: direction target roles: Backend (user, 2025-01-01)",
                                      "after: direction target roles: Platform (cv, 2024-05-01)", "written"])
        self.run_tool("direction", "set", "other hard constraints", "Remote only. (user, 2025-01-01)", "No relocation")
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "**Work authorisation:** none (user, 2025-01-01)")[1][-1],
                         "unchanged")   # a line copied from show, label and source included
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. Data (user, %s)\n2. Backend (user, 2025-01-01)\n"
                         "3. Platform (cv, 2024-05-01)\n\n## Constraints\n- **Work authorisation:** none (user, 2025-01-01)\n"
                         "- Remote only. (user, 2025-01-01)\n- No relocation (user, %s)\n" % (today, today))

    def test_notes_and_indented_lines_stay(self):
        self.direction("## Target roles, ranked\n1. Backend (user, 2025-01-01)\n2. Platform (user, 2025-01-01)\n"
                       "- Product roles: considered, not a target. (user, 2025-01-01)\n\n"
                       "## Constraints\n- **Work authorisation:**\n  - Visa A until 2027. (user, 2025-01-01)\n"
                       "  - No visa B. (user, 2025-01-01)\n")
        self.assertEqual(self.show_direction()[:2], ["direction target roles: Backend (user, 2025-01-01)",
                                                     "direction target roles: Platform (user, 2025-01-01)"])   # the note is no role
        self.assertEqual(self.show_direction()[3:6], ["direction work authorisation: **Work authorisation:**",
                                                      "direction work authorisation:   - Visa A until 2027. (user, 2025-01-01)",
                                                      "direction work authorisation:   - No visa B. (user, 2025-01-01)"])
        today = datetime.date.today().isoformat()
        self.run_tool("direction", "set", "target roles", "Platform", "Backend")
        code, lines = self.run_tool("direction", "set", "work authorisation", "Citizen", "--dry-run")
        self.assertEqual((code, lines[-3:]), (0, ["drops: direction work authorisation:   - Visa A until 2027. (user, 2025-01-01)",
                                                  "drops: direction work authorisation:   - No visa B. (user, 2025-01-01)",
                                                  "dry run: nothing written"]))
        code, lines = self.run_tool("direction", "set", "work authorisation", "Citizen")
        self.assertEqual(code, 1)   # deleting indented lines needs the user's yes to that dry run
        self.assertTrue(lines[0].startswith("config: this change deletes the indented lines"), lines)
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "**Work authorisation:**")[1][-1], "unchanged")
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. Platform (user, 2025-01-01)\n2. Backend (user, 2025-01-01)\n"
                         "- Product roles: considered, not a target. (user, 2025-01-01)\n\n"
                         "## Constraints\n- **Work authorisation:**\n  - Visa A until 2027. (user, 2025-01-01)\n"
                         "  - No visa B. (user, 2025-01-01)\n")
        show = [l.split(": ", 1)[1] for l in self.show_direction()[3:6]]   # show's lines passed back as they are
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", *show)[1][-1], "unchanged")
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "Visa A until 2027.")[0], 1)
        self.assertIn("--drop-indented", lines[0])
        constraints = self.direction()[self.direction().index("## Constraints"):]
        code, lines = self.run_tool("direction", "set", "work authorisation", "Citizen", "--drop-indented", "--dry-run")
        self.assertEqual((code, lines[-4]), (0, "after: direction work authorisation: **Work authorisation:** Citizen (user, %s)" % today))
        self.assertIn(constraints, self.direction())
        self.assertEqual(self.run_tool("direction", "set", "target roles", "Data", "Backend")[1][-1], "written")   # no indented lines
        self.assertIn("1. Data (user, %s)\n2. Backend (user, 2025-01-01)\n" % today, self.direction())

    def test_labels_and_targets_as_show_prints_them(self):
        self.direction("## Constraints\n- Remote only. (user, 2025-01-01)\n- **Work authorization:** citizen (user, 2025-01-01)\n"
                       "- No defense. (user, 2025-01-01)\n\n## What to emphasise, by target\n- **Backend:** x (user, 2025-01-01)\n")
        today = datetime.date.today().isoformat()
        self.run_tool("direction", "set", "work authorisation", "**Work authorisation:** green card")
        self.run_tool("direction", "set", "other hard constraints", "Remote only.", "No relocation")
        self.run_tool("direction", "set", "what to emphasise", "**Backend:** y", "--target", "**Backend:**")
        self.assertEqual(self.direction(), "## Constraints\n- **Work authorization:** green card (user, %s)\n"
                         "- Remote only. (user, 2025-01-01)\n- No relocation (user, %s)\n\n"
                         "## What to emphasise, by target\n- **Backend:** y (user, %s)\n" % ((today,) * 3))
        self.assertEqual(self.run_tool("direction", "set", "target roles", "A", "A")[0], 1)   # a line given twice
        self.assertEqual(self.run_tool("direction", "set", "target roles", "Backend: Go", "backend: Go")[0], 1)   # in two forms

    def test_plain_labels_are_kept_and_owned(self):
        self.direction("## Constraints\n- Work authorisation: citizen (user, 2024-01-01)\n\n"
                       "## What to emphasise, by target\n- Optimisation: keep X (user, 2024-01-01)\n  - a note\n")
        before = self.direction()
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "Work authorisation: citizen (user, 2024-01-01)")[1][-1],
                         "unchanged")
        self.assertEqual(self.run_tool("direction", "set", "what to emphasise", "keep X", "--target", "Optimization")[1][-1],
                         "unchanged")   # a plain label, -ize folded, its indented line kept
        code, lines = self.run_tool("direction", "set", "other hard constraints", "Work authorization: no clearance jobs", "No relocation")
        self.assertEqual((code, lines), (1, ["config: `Work authorization: no clearance jobs` is a work authorisation line:"
                                             ' write it with `direction set "work authorisation"`']))
        self.assertEqual(self.direction(), before)

    def test_indented_lines_passed_back_stay_put(self):
        self.direction("## Target roles, ranked\n1. Backend, payments\n   or fintech infra (user, 2025-01-01)\n"
                       "   - focus: reliability (user, 2025-01-01)\n2. SRE (user, 2025-01-01)\n")
        back = [l.split(": ", 1)[1] for l in self.show_direction()[:4]]
        self.assertEqual(self.run_tool("direction", "set", "target roles", *back, "--dry-run")[1][-1], "unchanged")
        before = self.direction()
        self.run_tool("direction", "set", "target roles", "Staff", *back)
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. Staff (user, %s)\n2. Backend, payments\n"
                         "   or fintech infra (user, 2025-01-01)\n   - focus: reliability (user, 2025-01-01)\n"
                         "3. SRE (user, 2025-01-01)\n" % datetime.date.today().isoformat())
        self.assertNotEqual(before, self.direction())

    def test_indented_lines_kept_or_rewritten_with_their_line(self):
        self.direction("## Constraints\n- **Work authorisation:**\n  - Visa A until 2027. (user, 2025-01-01)\n"
                       "  - No visa B. (user, 2025-01-01)\n")
        today = datetime.date.today().isoformat()
        before = self.direction()
        code, lines = self.run_tool("direction", "set", "work authorisation", "Visa A",
                                    "  - Visa A until 2027. (user, 2025-01-01)", "  - Visa B from 2027.", "--dry-run")
        self.assertEqual((code, lines[-5:]), (0, ["after: direction work authorisation: **Work authorisation:** Visa A (user, %s)" % today,
                                                  "after: direction work authorisation:   - Visa A until 2027. (user, 2025-01-01)",
                                                  "after: direction work authorisation:   - Visa B from 2027. (user, %s)" % today,
                                                  "drops: direction work authorisation:   - No visa B. (user, 2025-01-01)",
                                                  "dry run: nothing written"]))
        self.assertEqual(self.direction(), before)
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "Visa A",
                                       "  - Visa A until 2027.", "  - Visa B from 2027.")[0], 1)   # No visa B goes: not without a yes
        self.assertEqual(self.direction(), before)
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "Visa A",
                                       "  - Visa A until 2027.", "  - Visa B from 2027.", "--drop-indented")[1][-1], "written")
        self.assertEqual(self.direction(), "## Constraints\n- **Work authorisation:** Visa A (user, %s)\n"
                         "  - Visa A until 2027. (user, 2025-01-01)\n  - Visa B from 2027. (user, %s)\n" % (today, today))
        self.assertEqual(self.run_tool("direction", "set", "work authorisation", "  - Visa A until 2027.")[0], 1)   # no list line first

    def test_a_list_line_renamed_carries_its_indented_lines(self):
        self.direction("## Target roles, ranked\n1. Backend (user, 2025-01-01)\n   - payments (user, 2025-01-01)\n"
                       "   - fintech (user, 2025-01-01)\n2. SRE (user, 2025-01-01)\n   - on call ok (user, 2025-01-01)\n"
                       "3. Data (user, 2025-01-01)\n")
        today = datetime.date.today().isoformat()
        before = self.direction()
        for args in (["Backend platform", "Data"],   # a rename and a delete
                     ["SRE", "ML", "   - new note", "Data"],   # a delete beside an unrelated new line's own note
                     ["Backend", "   - payments", "SRE", "Data"]):   # a kept line given part of its indented lines
            code, lines = self.run_tool("direction", "set", "target roles", *args)
            self.assertEqual(code, 1, args)
            self.assertIn("--drop-indented", lines[0])
            dry = self.run_tool("direction", "set", "target roles", *args, "--dry-run")[1]
            self.assertTrue(any(l.startswith("drops: direction target roles:    - ") for l in dry), args)
        self.assertEqual(self.direction(), before)
        self.run_tool("direction", "set", "target roles", "Backend platform", "   - payments (user, 2025-01-01)",
                      "   - fintech", "SRE", "Data")   # SRE kept as it is: its indented line moves with it
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. Backend platform (user, %s)\n"
                         "   - payments (user, 2025-01-01)\n   - fintech (user, 2025-01-01)\n2. SRE (user, 2025-01-01)\n"
                         "   - on call ok (user, 2025-01-01)\n3. Data (user, 2025-01-01)\n" % today)
        self.assertEqual(self.run_tool("direction", "set", "target roles", "SRE", "   - payments", "   - fintech",
                                       "   - on call ok", "Data")[1][-1], "written")   # moved under a line that stays
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. SRE (user, 2025-01-01)\n   - payments (user, 2025-01-01)\n"
                         "   - fintech (user, 2025-01-01)\n   - on call ok (user, 2025-01-01)\n2. Data (user, 2025-01-01)\n")
        self.run_tool("direction", "set", "target roles", "Data", "--drop-indented")
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. Data (user, 2025-01-01)\n")

    def test_two_indented_lines_with_the_same_text(self):
        self.direction("## Target roles, ranked\n1. Backend (user, 2025-01-01)\n   - remote ok (user, 2025-01-01)\n"
                       "2. SRE (user, 2025-01-01)\n   - remote ok (user, 2025-02-02)\n")
        before = self.direction()
        code, lines = self.run_tool("direction", "set", "target roles", "Backend", "SRE platform", "--dry-run")
        self.assertEqual(lines[-2:], ["drops: direction target roles:    - remote ok (user, 2025-02-02)", "dry run: nothing written"])
        self.assertEqual(self.run_tool("direction", "set", "target roles", "Backend", "SRE platform")[0], 1)
        self.assertEqual(self.run_tool("direction", "set", "target roles", "Backend", "SRE", "   - remote ok",
                                       "   - remote ok")[0], 1)   # given twice under one line
        for line in ("(user, 2025-01-01)", "   (user, 2025-01-01)"):   # a source alone is no line
            self.assertEqual(self.run_tool("direction", "set", "target roles", "Backend", "SRE", line)[0], 1, line)
        self.assertEqual(self.direction(), before)
        self.run_tool("direction", "set", "target roles", "Backend", "   - remote ok", "SRE", "   - remote ok")
        self.assertEqual(self.direction(), before)   # each copy keeps its own source
        lines = self.run_tool("direction", "set", "target roles", "Backend", "   - z", "SRE", "--dry-run")[1]
        self.assertIn("after: direction target roles:    - remote ok (user, 2025-02-02)", lines)   # SRE's own, kept
        self.assertEqual(lines[-2], "drops: direction target roles:    - remote ok (user, 2025-01-01)")   # the copy that goes
        self.assertEqual(self.run_tool("direction", "set", "target roles", "SRE", "   - remote ok", "Backend")[1][-1], "written")
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. SRE (user, 2025-01-01)\n   - remote ok (user, 2025-02-02)\n"
                         "2. Backend (user, 2025-01-01)\n   - remote ok (user, 2025-01-01)\n")   # each its own copy
        self.direction("## Target roles, ranked\n1. A (user, 2025-01-01)\n2. B (user, 2025-01-01)\n   - x (cv, 2025-02-02)\n")
        self.run_tool("direction", "set", "target roles", "A", "   - x", "B", "   - x")   # B's copy stays B's
        self.assertEqual(self.direction(), "## Target roles, ranked\n1. A (user, 2025-01-01)\n   - x (user, %s)\n"
                         "2. B (user, 2025-01-01)\n   - x (cv, 2025-02-02)\n" % datetime.date.today().isoformat())
        self.direction("## Constraints\n- Remote only. (user, 2025-01-01)\n")
        self.assertEqual(self.run_tool("direction", "set", "other hard constraints", "none", "  - but X")[0], 1)

    def test_the_us_spelling_is_work_authorisation(self):
        self.direction("## Constraints\n- **Work authorization:** EU (user, 2025-01-01)\n- Remote only. (user, 2025-01-01)\n")
        self.assertEqual(self.show_direction()[2:5], ["direction work authorisation: **Work authorization:** EU (user, 2025-01-01)",
                                                      "direction visa sponsorship: empty",
                                                      "direction other hard constraints: Remote only. (user, 2025-01-01)"])
        self.run_tool("direction", "set", "other hard constraints", "none")
        self.run_tool("direction", "set", "work authorisation", "EU citizen")
        self.assertEqual(self.direction(), "## Constraints\n- **Work authorization:** EU citizen (user, %s)\n"
                         "- **Other hard constraints:** none (user, %s)\n" % ((datetime.date.today().isoformat(),) * 2))

    # ---- Visa sponsorship needed (#284) ----

    def test_visa_sponsorship_values_and_place(self):
        self.direction("## Constraints\nHard constraints.\n\n- **Work authorisation:** Needs H-1B sponsorship (user, 2025-01-01)\n"
                       "- Remote only. (user, 2025-01-01)\n\n## What to emphasise, by target\n")
        today = datetime.date.today().isoformat()
        self.assertEqual(config.visa_lookups(self.root), ())   # no line
        code, lines = self.run_tool("direction", "set", "visa sponsorship", "h1b")
        self.assertEqual((code, lines), (0, ["before: direction visa sponsorship: empty",
                                             "after: direction visa sponsorship: **Visa sponsorship needed:** H-1B (user, %s)" % today,
                                             "written"]))
        self.assertEqual(config.visa_lookups(self.root), ("lca",))
        code, lines = self.run_tool("direction", "set", "visa sponsorship", "Visa sponsorship needed: green card; H-1B")
        self.assertEqual(lines[1], "after: direction visa sponsorship: **Visa sponsorship needed:** H-1B; green card (PERM)"
                                   " (user, %s)" % today)
        self.assertEqual(config.visa_lookups(self.root), ("lca", "perm"))
        # right after work authorisation, which stays as the user said it; the other constraints keep their lines
        self.assertIn("- **Work authorisation:** Needs H-1B sponsorship (user, 2025-01-01)\n"
                      "- **Visa sponsorship needed:** H-1B; green card (PERM) (user, %s)\n- Remote only." % today, self.direction())
        self.assertEqual(self.show_direction()[2:5], [
            "direction work authorisation: **Work authorisation:** Needs H-1B sponsorship (user, 2025-01-01)",
            "direction visa sponsorship: **Visa sponsorship needed:** H-1B; green card (PERM) (user, %s)" % today,
            "direction other hard constraints: Remote only. (user, 2025-01-01)"])
        self.run_tool("direction", "set", "visa sponsorship", "green card (PERM)")
        self.assertEqual(config.visa_lookups(self.root), ("perm",))
        self.run_tool("direction", "set", "visa sponsorship", "none")
        self.assertEqual(config.visa_lookups(self.root), ())
        before = self.direction()
        for value in ("O-1", "H-1B; TN", "", "H-1B, green card"):
            code, lines = self.run_tool("direction", "set", "visa sponsorship", value)
            self.assertEqual(code, 1, value)
            self.assertTrue(lines[0].startswith("config: "), lines)
        # its label belongs to it, not to the other hard constraints
        code, lines = self.run_tool("direction", "set", "other hard constraints", "**Visa sponsorship needed:** H-1B")
        self.assertEqual((code, lines), (1, ["config: `**Visa sponsorship needed:** H-1B` is a visa sponsorship line:"
                                             " write it with `direction set \"visa sponsorship\"`"]))
        self.assertEqual(self.direction(), before)

    def test_visa_sponsorship_place_with_and_without_work_authorisation(self):
        today = datetime.date.today().isoformat()
        self.direction("## Constraints\n- Remote only. (user, 2025-01-01)\n")
        self.run_tool("direction", "set", "visa sponsorship", "H-1B")   # no work authorisation: it leads the section
        self.assertEqual(self.direction(), "## Constraints\n- **Visa sponsorship needed:** H-1B (user, %s)\n"
                                           "- Remote only. (user, 2025-01-01)\n" % today)
        self.run_tool("direction", "set", "work authorisation", "F-1 OPT")   # work authorisation still goes first
        self.assertEqual(self.direction(), "## Constraints\n- **Work authorisation:** F-1 OPT (user, %s)\n"
                                           "- **Visa sponsorship needed:** H-1B (user, %s)\n"
                                           "- Remote only. (user, 2025-01-01)\n" % (today, today))
        self.run_tool("direction", "set", "visa sponsorship", "H-1B; green card")   # changed in place
        self.assertEqual(self.direction().splitlines()[2], "- **Visa sponsorship needed:** H-1B; green card (PERM) (user, %s)" % today)

    def test_visa_sponsorship_opt_and_cpt(self):
        """#377: OPT and CPT ask for no lookup; their check is the posting's wording."""
        self.direction("## Constraints\n- **Work authorisation:** F-1 OPT (user, 2025-01-01)\n")
        today = datetime.date.today().isoformat()
        for value, written, kinds, statuses in (("opt", "OPT", (), ("OPT",)), ("CPT.", "CPT", (), ("CPT",)), ("STEM OPT", "OPT", (), ("OPT",)),
                                                ("cpt; OPT", "OPT; CPT", (), ("OPT", "CPT")),
                                                ("OPT; green card; h1b", "H-1B; green card (PERM); OPT", ("lca", "perm"), ("OPT",))):
            code, lines = self.run_tool("direction", "set", "visa sponsorship", value)
            self.assertEqual((code, lines[1]), (0, "after: direction visa sponsorship: **Visa sponsorship needed:** %s"
                                                   " (user, %s)" % (written, today)), value)
            self.assertEqual((config.visa_lookups(self.root), config.visa_statuses(self.root)), (kinds, statuses), value)
        for value in ("OPT; none", "F-1", "J-1"):
            self.assertEqual(self.run_tool("direction", "set", "visa sponsorship", value)[0], 1, value)
        self.run_tool("direction", "set", "visa sponsorship", "none")
        self.assertEqual(config.visa_statuses(self.root), ())

    def test_visa_lookups_reads_the_line(self):
        for line, kinds in (("- **Visa sponsorship needed:** GAP: does the user need one?\n", ()),
                            ("- **Visa sponsorship needed:** H-1B; green card (PERM) (user, 2025-01-01)\n", ("lca", "perm")),
                            ("- **Visa sponsorship needed:** none (user, 2025-01-01)\n", ()),
                            ("- **Visa:** H-1B (user, 2025-01-01)\n", ())):   # another label is another constraint
            self.direction("## Constraints\n" + line)
            self.assertEqual(config.visa_lookups(self.root), kinds, line)
        self.direction("## Constraints\n- **Visa sponsorship needed:** O-1 (user, 2025-01-01)\n")
        with self.assertRaisesRegex(config.ConfigError, "O-1.*direction set"):
            config.visa_lookups(self.root)
        self.direction("## Target roles, ranked\n")
        self.assertEqual(config.visa_lookups(self.root), ())   # no Constraints section, or no direction.md: nothing asked
        os.remove(os.path.join(self.root, "direction.md"))
        self.assertEqual(config.visa_lookups(self.root), ())

    def test_direction_set_twice_is_unchanged_and_dry_run_writes_nothing(self):
        shutil.copy(os.path.join(TEMPLATE, "direction.md"), os.path.join(self.root, "direction.md"))
        code, lines = self.run_tool("direction", "set", "target roles", "Backend", "--dry-run")
        self.assertEqual((code, lines[-1]), (0, "dry run: nothing written"))
        with open(os.path.join(TEMPLATE, "direction.md"), encoding="utf-8") as f:
            self.assertEqual(self.direction(), f.read())
        self.run_tool("direction", "set", "target roles", "Backend")
        self.assertEqual(self.run_tool("direction", "set", "target roles", "Backend")[1][-1], "unchanged")
        written = self.direction()
        self.direction(written.replace(datetime.date.today().isoformat(), "2020-01-01"))   # an older answer, same words
        code, lines = self.run_tool("direction", "set", "target roles", "Backend")
        self.assertEqual((code, lines[-1]), (0, "unchanged"))
        self.assertIn("1. Backend (user, 2020-01-01)", self.direction())

    def test_direction_set_refuses(self):
        shutil.copy(os.path.join(TEMPLATE, "direction.md"), os.path.join(self.root, "direction.md"))
        before = self.direction()
        for args in (("target role", "x"), ("what to emphasise", "x"), ("target roles", "x", "--target", "Backend"),
                     ("work authorisation", "a", "b"), ("target roles", " "), ("target roles", "a\nb")):
            code, lines = self.run_tool("direction", "set", *args)
            self.assertEqual(code, 1, args)
            self.assertTrue(lines[0].startswith("config: "), lines)
        self.assertEqual(self.direction(), before)
        self.assertEqual(self.run_tool("direction", "set", "target roles")[0], 2)
        self.assertEqual(self.run_tool("direction", "add", "target roles", "x")[0], 2)
        os.remove(os.path.join(self.root, "direction.md"))
        self.assertEqual(self.run_tool("direction", "set", "target roles", "x"), (1, ["config: direction.md is missing"]))
        self.direction("## Target roles\n1. x\n")
        self.assertEqual(self.run_tool("direction", "set", "target roles", "x"),
                         (1, ["config: direction.md has no `## Target roles, ranked` section"]))

    # ---- An unreadable defaults file (Finding 7) ----

    def test_an_unreadable_defaults_file_is_reported(self):
        saved = config.DEFAULTS_FILE
        self.addCleanup(lambda: setattr(config, "DEFAULTS_FILE", saved))
        bad = os.path.join(self.root, "bad.toml")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("front_page = \n")
        partial = os.path.join(self.root, "partial.toml")
        with open(partial, "w", encoding="utf-8") as f:
            f.write('front_page = "full"\n')
        for where in (os.path.join(self.root, "absent.toml"), bad, partial, self.root):   # missing, no parse, short, a folder
            config.DEFAULTS_FILE = where
            for args in (("show",), ("init",)):
                if os.path.exists(os.path.join(self.root, "config.toml")):
                    os.remove(os.path.join(self.root, "config.toml"))
                if args == ("show",):
                    self.write('record_language = "English"\n')
                code, lines = self.run_tool(*args)
                self.assertEqual(code, 1, (where, args))
                self.assertTrue(lines[0].startswith("config: %s " % where), lines)
                self.assertIn("Engine file", lines[0])
            self.assertFalse(os.path.exists(os.path.join(self.root, "config.toml")))   # init wrote nothing

    def test_unchanged_value(self):
        self.write('front_page = "full"\n')
        self.assertEqual(self.run_tool("set", "front_page", "full")[1][-1], "unchanged")

    def test_a_default_set_to_itself_is_unchanged(self):   # Finding 8
        self.write('record_language = "English"\n')
        for field, value in (("front_page", "full"), ("m", "5"), ("interviewer_profiles", "never")):
            code, lines = self.run_tool("set", field, value)
            self.assertEqual((code, lines[-1]), (0, "unchanged"), field)
            self.assertTrue(lines[0].endswith("(default)"), lines)
        self.assertEqual(self.read(), 'record_language = "English"\n')
        self.assertEqual(self.run_tool("set", "m", "6")[1][-1], "written")   # another value still is written
        self.assertEqual(self.read(), 'record_language = "English"\nm = 6\n')

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
            f.write('update_check = "off"\n')
        self.assertEqual(self.run_tool("show")[0], 0)
        self.assertEqual(self.run_tool("set", "update_check", "on")[1][-1], "written")

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
        self.assertEqual(len(lines), len(config.FIELDS) + len(config.DIRECTION))

    def test_bad_arguments(self):
        self.assertEqual(self.run_tool()[0], 2)
        self.assertEqual(self.run_tool("set", "front_page")[0], 2)
        self.assertEqual(self.run_tool("delete")[0], 2)
        self.assertEqual(self.run_tool("set", "front_page", "full", "--target", "x")[0], 2)
        self.assertEqual(self.run_tool("direction", "set", "what to emphasise", "x", "--target")[0], 2)

    def test_runs_as_a_script(self):
        run = subprocess.run([sys.executable, "-I", TOOL, "init", "--root", self.root], capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        run = subprocess.run([sys.executable, "-I", TOOL, "set", "record_language", "日本語", "--root", self.root],
                             capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertIn('after: record_language = "日本語"', run.stdout.decode("utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
