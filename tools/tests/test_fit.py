#!/usr/bin/env python3
"""Tests for tools/fit.py: the fit result's schema, a report's fit maps and their rows.

  python3 -I tools/tests/test_fit.py
"""
import importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True   # the tool loaded below leaves no tools/__pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "fit.py")
spec = importlib.util.spec_from_file_location("fit", TOOL)
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)

ROW = {"requirement": "Go", "kind": "required", "written_by": "user", "own_work": "", "category": "covered",
       "entry": "2025-01-widget.md", "row_type": "language or tool"}
GAP = dict(ROW, requirement="Mentor juniors", kind="duty", category="gap", entry="", written_by="", row_type="other")
MAP = {"company": "Example Corp", "role": "Software Engineer", "requirements": ["Go", "Mentor juniors"],
       "course_work": [], "rows": [ROW, GAP], "capture": "postings/m.md"}
# the capture MAP names: an open posting, read by scan.py fetch (#571)
CAPTURE = "https://a.com/1\nread: fetch, open\n\nWe build widgets in Go.\n"
NOTES = ["Course work: none (3 entries listed)", "Map: 2 requirements and duties, 2 rows; no row: none"]
RESULT = dict(MAP, url="https://a.com/1", recommendation="apply", check=["visa"], notes=NOTES)
# a fit result from before the map fields (#301): problems() still passes it
OLD_RESULT = {"url": "https://a.com/1", "recommendation": "apply", "check": ["visa"], "notes": NOTES[1:],
              "rows": [{k: v for k, v in r.items() if k != "row_type"} for r in (ROW, GAP)]}
ENTRIES = {
    "2025-01-widget.md": "# Widget\n\n## My contribution\n\nBuilt the widget in Go.\n",
    "2025-02-agent.md": ("# Agent\n\n## My contribution\n\n**I did:** traced the drift to a *stale* cache and had the agent\n"
                         "fix it.\n\n## How it works\n\nChose SQLite over Postgres for the queue.\n\n## Conflicts\n\n"
                         "- Settled: I read the agent's parser and corrected its retry logic.\n\n## Notes\n\n"
                         "Wrote the load tests by hand.\n"),
    "2024-09-course.md": "# Course\n\n## My contribution\n\nCompleted the distributed systems labs.\n",
}

REPORT = """# Scan 2026-10-22

## Pending

## Fit maps

### A — SWE

URL: https://a.com/1
Screen: tier 1, rough 1/2, key aaaaaaaa-bbbbbbbb
Entries commit: abc1234
{rest}

## Next
"""


class FitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        for name, text in ENTRIES.items():
            self.write("entries/" + name, text)
        self.write("postings/m.md", CAPTURE)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return p

    def run_tool(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = fit.main(["--root", self.tmp] + list(args))
        return code, out.getvalue().splitlines()

    def test_a_map_round_trips_with_its_kinds(self):
        text = REPORT.format(rest="\n".join(fit.map_lines(RESULT)))
        [(url, sha, body)] = fit.fit_maps(text)
        self.assertEqual((url, sha), ("https://a.com/1", "abc1234"))
        self.assertEqual(fit.recommendation(body), "apply")
        rows = fit.map_rows(body)
        self.assertEqual([(r["requirement"], r["kind"], r["category"]) for r in rows],
                         [("Go", "required", "covered"), ("Mentor juniors", "duty", "gap")])
        self.assertEqual(fit.coverage(rows), fit.coverage(RESULT["rows"]))
        self.assertEqual(fit.coverage(rows), (1, 2))
        self.assertIn("Things to check:\n\n- visa\n\nCourse work: none (3 entries listed)\nMap: 2 requirements", text)
        reused = dict(RESULT, text=fit.body_text(body), reused="r.md")
        self.assertEqual(fit.map_lines(reused), fit.map_lines(RESULT))   # a reused map keeps its own lines

    def test_an_old_map_has_no_kinds_and_counts_every_row(self):
        body = ("A — SWE\n\nURL: https://a.com/1\n\n| Requirement | Written by | Own work | Category | Entry |\n"
                "|---|---|---|---|---|\n| Go | user | | covered | `2025-01-widget.md` |\n| SQL | user | | shallow | - |\n")
        rows = fit.map_rows(body)
        self.assertEqual([r["kind"] for r in rows], [None, None])
        self.assertEqual(fit.coverage(rows), (1, 2))
        self.assertIsNone(fit.map_rows("no table here\n"))

    def test_preferred_rows_do_not_count_when_required_ones_exist(self):
        rows = [dict(ROW, kind="preferred"), dict(ROW, kind="required", category="shallow")]
        self.assertEqual(fit.coverage(rows), (0, 1))

    def test_cited_entries_any_letters(self):
        """Finding 5: an entry named in Chinese is cited too, from the Entry cells or the whole text."""
        body = ("| Requirement | Kind | Written by | Own work | Category | Entry |\n|---|---|---|---|---|---|\n"
                "| SQL | required | user | - | covered | `2024-02-新.md` (phase 3) |\n"
                "| Go | required | user | - | covered | entries/2025-01-widget.md |\n")
        self.assertEqual(fit.cited_entries(body), ["2024-02-新.md", "2025-01-widget.md"])
        self.assertEqual(fit.cited_entries("Built in 2024-02-新.md, see x2025-01-a.md.bak\n"), ["2024-02-新.md"])

    def test_check(self):
        good = self.write("fit/a.jsonl", json.dumps(RESULT) + "\n")
        cap = self.write("postings/a.md", "https://a.com/1\n\ntext\n")
        self.assertEqual(self.run_tool("check", "fit/a.jsonl", "--capture", "postings/a.md"), (0, ["check: ok"]))
        self.write("postings/b.md", "https://b.com/2\n\ntext\n")
        code, lines = self.run_tool("check", good, "--capture", "postings/b.md")
        self.assertEqual((code, lines), (1, ["bad: url: https://a.com/1, but the capture's first line gives https://b.com/2"]))
        bad = dict(RESULT, recommendation="maybe", check="visa",
                   rows=[dict(ROW, kind="must"), dict(ROW, category="partly", requirement=" ")])
        self.write("fit/b.jsonl", json.dumps(bad) + "\n")
        code, lines = self.run_tool("check", "fit/b.jsonl")
        self.assertEqual(code, 1)
        self.assertEqual(lines[:5], ["bad: recommendation: 'maybe' is not one of apply, apply with caveats, skip",
                                 "bad: check: must be a list of strings",
                                 "bad: rows[1].kind: 'must' is not one of required, preferred, duty",
                                 "bad: rows[2].requirement: empty",
                                 "bad: rows[2].category: 'partly' is not one of covered, shallow, claimed, unbacked, gap"])
        self.write("fit/c.jsonl", json.dumps(RESULT) + "\n" + json.dumps(RESULT) + "\n")
        self.assertIn("2 lines", self.run_tool("check", "fit/c.jsonl")[1][0])
        self.write("fit/d.jsonl", "{not json\n")
        self.assertIn("does not parse", self.run_tool("check", "fit/d.jsonl")[1][0])
        self.assertEqual(self.run_tool("check", "fit/missing.jsonl")[0], 1)
        self.assertEqual(self.run_tool("nothing")[0], 2)

    def test_a_reused_row_may_lack_its_kind(self):
        self.assertEqual(fit.problems(dict(RESULT, reused="r.md", rows=[dict(ROW, kind=None)])), [])
        self.assertTrue(fit.problems(dict(RESULT, rows=[dict(ROW, kind=None)])))

    def test_an_old_result_keeps_passing_problems(self):
        """scan.py's fitmap and rank call problems(): a result from before the map fields passes it, as
        does a reused one, and check does not hold a reused one to the map's rules."""
        self.assertEqual(fit.problems(OLD_RESULT), [])
        reused = dict(OLD_RESULT, reused="outputs/reports/r.md", fit_commit="abc1234", text="| Requirement |")
        self.assertEqual(fit.problems(reused), [])
        self.write("fit/r.jsonl", json.dumps(reused) + "\n")
        self.assertEqual(self.run_tool("check", "fit/r.jsonl"), (0, ["check: ok"]))
        self.write("fit/o.jsonl", json.dumps(OLD_RESULT) + "\n")
        code, lines = self.run_tool("check", "fit/o.jsonl")
        self.assertEqual(code, 1)
        self.assertIn("bad: requirements: must be a list of the requirements and duties, one non-empty string each", lines)

    def test_check_gives_the_notes(self):
        self.write("fit/n.jsonl", json.dumps(dict(RESULT, notes=["Map: 9 requirements"])) + "\n")
        code, lines = self.run_tool("check", "fit/n.jsonl")
        self.assertEqual((code, lines), (1, ["bad: notes: must be the lines map prints for it: " + json.dumps(NOTES)]))

    # ---- map ----

    def map_file(self, name="m.jsonl", **change):
        self.write("fit/" + name, json.dumps(dict(MAP, **change), ensure_ascii=False) + "\n")
        return "fit/" + name

    def bad(self, *rows, **change):
        """The bad: lines of map on a map file with these rows (each requirement its own item)."""
        reqs = list(dict.fromkeys(r["requirement"] for r in rows))
        code, lines = self.run_tool("map", self.map_file(rows=list(rows), requirements=reqs, **change))
        self.assertEqual(code, 1 if any(l.startswith("bad: ") for l in lines) else 0, lines)
        return [l[5:] for l in lines if l.startswith("bad: ")]

    AGENT = dict(ROW, requirement="Debug flaky services", row_type="debugging", written_by="AI agent",
                 entry="2025-02-agent.md", own_work="debugging: traced the drift to a stale cache and had the agent fix it.")

    def test_map_prints_its_lines_and_table(self):
        code, lines = self.run_tool("map", self.map_file())
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[:2], NOTES)
        self.assertEqual(lines[3:7], ["| Requirement | Kind | Written by | Own work | Category | Entry |",
                                      "|---|---|---|---|---|---|",
                                      "| Go | required | user | - | covered | 2025-01-widget.md |",
                                      "| Mentor juniors | duty | - | - | gap | - |"])
        self.assertEqual(lines[-1], "map: ok")

    def test_show_prints_one_block_to_paste(self):
        """#518 (3), #550: write step 9 pastes one block, not a table of its own, with no code fence."""
        agent = dict(self.AGENT, category="shallow")
        path = self.map_file(requirements=["Go", "Mentor juniors", "Debug flaky services"], rows=[ROW, GAP, agent])
        code, lines = self.run_tool("map", path, "--show")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, [
            "show: paste the lines below, from `Course work:` to the table's last row, into your reply whole, as printed",
            "Course work: none (3 entries listed)",
            "Map: 3 requirements and duties, 3 rows; no row: none",
            "",
            "| Requirement | Kind | Written by | Category | Entry |",
            "|---|---|---|---|---|",
            "| Go | required | user | covered | 2025-01-widget.md |",
            "| Mentor juniors | duty | - | gap | - |",
            "| Debug flaky services | required | AI agent (debugging) | shallow | 2025-02-agent.md |",
            "map: ok"])
        self.assertEqual(self.run_tool("map", path, "--show", "--several")[0], 1)

    def test_show_keeps_a_pipe_or_backticks_in_its_cell(self):
        r"""#550: with no fence to guard it, a `|`, a `\|` or backticks in a cell stay one cell."""
        entry = r"`2025-01-widget.md` (a ```b``` | c \| d\)"
        code, lines = self.run_tool("map", self.map_file(requirements=["Go"], rows=[dict(ROW, entry=entry)]), "--show")
        self.assertEqual(code, 0, lines)
        row = lines[lines.index("|---|---|---|---|---|") + 1]
        self.assertEqual(row, r"| Go | required | user | covered | `2025-01-widget.md` (a ```b``` \| c \\\| d\) |")
        self.assertEqual(len(re.findall(r"(?<!\\)(?:\\\\)*\|", row)), 6, row)   # 5 cells: 6 unescaped pipes

    def test_a_good_map_passes(self):
        course = dict(ROW, requirement="Distributed systems", row_type="understanding", written_by="coursework",
                      entry="2024-09-course.md")
        review = dict(self.AGENT, requirement="Python", row_type="language or tool",
                      own_work='review: "I read the agent\'s parser and corrected its retry logic."')
        design = dict(self.AGENT, requirement="System design", row_type="other",
                      own_work="design: Chose SQLite ... for the queue")
        section = dict(ROW, requirement="Go APIs", entry="`2025-01-widget.md` (phase 3)")
        self.assertEqual(self.bad(course, self.AGENT, review, design, section, GAP,
                                  course_work=["2024-09-course.md"]), [])

    def test_a_missing_row_is_named(self):
        code, lines = self.run_tool("map", self.map_file(requirements=["Go", "Mentor juniors", "On-call"]))
        self.assertEqual(code, 1)
        self.assertEqual(lines[1], "Map: 3 requirements and duties, 2 rows; no row: On-call")
        self.assertIn("bad: requirements: no row maps 'On-call'", lines)

    def test_split_rows_count_more_rows(self):
        rows = [dict(ROW, requirement="Go", of=1), dict(ROW, requirement="SQL", of=1, category="shallow"), dict(GAP, of=2)]
        code, lines = self.run_tool("map", self.map_file(requirements=["Go, SQL", "Mentor juniors"], rows=rows))
        self.assertEqual((code, lines[1]), (0, "Map: 2 requirements and duties, 3 rows; no row: none"))
        self.assertEqual(self.bad(dict(ROW, of=3)), ["rows[1].of: 3 is not the number of a requirements item (1 to 1)",
                                                  "requirements: no row maps 'Go'"])

    def test_several_postings_name_each_map(self):
        other = self.map_file("o.jsonl", company="Other Inc", role="SRE")
        code, lines = self.run_tool("map", self.map_file(), other, "--several")
        self.assertEqual(code, 0, lines)
        self.assertEqual([l for l in lines if l.startswith("Map")],
                         ["Map (Example Corp, Software Engineer): 2 requirements and duties, 2 rows; no row: none",
                          "Map (Other Inc, SRE): 2 requirements and duties, 2 rows; no row: none"])
        code, lines = self.run_tool("map", self.map_file("x.jsonl", company=""), "--several")
        self.assertIn("bad: company, role: --several needs both in the map file", lines)

    def test_course_work_line_counts_the_listed_entries(self):
        code, lines = self.run_tool("map", self.map_file(course_work=["2024-09-course.md"]))
        self.assertEqual(lines[0], "Course work: 2024-09-course.md (3 entries listed)")
        self.write("entries/_template.md", "# template\n")
        self.assertEqual(self.run_tool("map", self.map_file())[1][0], "Course work: none (3 entries listed)")

    def test_category_filter(self):
        rows = [ROW, GAP, dict(ROW, requirement="SQL", category="claimed, unbacked", entry="", written_by="")]
        code, lines = self.run_tool("map", self.map_file(requirements=["Go", "Mentor juniors", "SQL"], rows=rows),
                                    "--category", "gap", "--category", "claimed, unbacked")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[1], "Map: 3 requirements and duties, 3 rows; no row: none")
        self.assertEqual([l.split(" | ")[0] for l in lines if l.startswith("| ") and "---" not in l],
                         ["| Requirement", "| Mentor juniors", "| SQL"])
        self.assertEqual(self.run_tool("map", self.map_file(), "--category", "claimed")[0], 2)

    def test_save_name(self):
        gaps = [GAP, dict(GAP, requirement="On-call")]
        code, lines = self.run_tool("map", self.map_file(requirements=["Go", "Mentor juniors", "On-call"], rows=[ROW] + gaps,
                                                         role="Software Engineer (Infra)"),
                                    "--save-name", "--today", "2026-10-24")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[1], "Map: 3 requirements and duties, 3 rows; no row: none")
        self.assertEqual(lines[-3:], ["save: outputs/reports/2026-10-24-fit-posting-example-corp-software-engineer-infra.md",
                                      "commit: fit(example-corp-software-engineer-infra): 2 gaps", "map: ok"])
        self.assertEqual(fit.slug("Software Engineer (Infra)"), fit.logfiles.ascii_slug("Software Engineer (Infra)"))
        code, lines = self.run_tool("map", self.map_file(company=None), "--save-name")
        self.assertEqual(lines[-1], "bad: --save-name: give one map file, with its company and role")

    def test_name(self):
        self.assertEqual(self.run_tool("name", "Example Corp", "Software Engineer (Infra)", "--today", "2026-10-24"),
                         (0, ["map file: .build/fit/2026-10-24-example-corp-software-engineer-infra.jsonl"]))
        # names in other letters get distinct names, not one shared fallback
        a = self.run_tool("name", "甲公司", "軟體工程師", "--today", "2026-10-24")[1][0]
        b = self.run_tool("name", "乙公司", "韌體工程師", "--today", "2026-10-24")[1][0]
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^map file: \.build/fit/2026-10-24-[0-9a-f]{8}-[0-9a-f]{8}\.jsonl$")

    def test_names_with_some_other_letters_differ(self):
        a = self.run_tool("name", "後端 Inc", "工程師 (Go)", "--today", "2026-10-24")[1][0]
        b = self.run_tool("name", "前端 Inc", "工程師 (Go)", "--today", "2026-10-24")[1][0]
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^map file: \.build/fit/2026-10-24-inc-[0-9a-f]{8}-go-[0-9a-f]{8}\.jsonl$")

    def test_one_name_in_two_unicode_forms_is_one_file(self):
        self.assertEqual(fit.slug("Café"), fit.slug("Café"))

    def test_a_name_with_no_letter_gets_its_hash(self):
        a = self.run_tool("name", "!!!", "x", "--today", "2026-10-24")[1][0]
        b = self.run_tool("name", "???", "x", "--today", "2026-10-24")[1][0]
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^map file: \.build/fit/2026-10-24-[0-9a-f]{8}-x\.jsonl$")

    def test_a_malformed_map_file_gets_bad_lines(self):
        for change in ({"rows": 5}, {"rows": [dict(ROW, own_work=5)]}, {"requirements": "Go"}, {"course_work": 5},
                       {"company": ["a"]}):
            with self.subTest(change=change):
                code, lines = self.run_tool("map", self.map_file(**change))
                self.assertEqual(code, 1, lines)
                self.assertTrue(any(l.startswith("bad: ") for l in lines), lines)

    def test_several_without_company_says_so_once(self):
        files = [self.map_file("a.jsonl", company=None), self.map_file("b.jsonl", company=None)]
        code, lines = self.run_tool("map", *files, "--several")
        self.assertEqual(code, 1)
        self.assertEqual([l for l in lines if "same company" in l], [])

    def test_several_refuses_one_posting_twice(self):
        code, lines = self.run_tool("map", self.map_file(), self.map_file("b.jsonl"), "--several")
        self.assertEqual(code, 1)
        self.assertIn("bad: fit/b.jsonl: company, role: another map file of this run gives the same name "
                      "(example-corp-software-engineer)", lines)

    def test_a_row_names_its_requirements_item(self):
        code, lines = self.run_tool("map", self.map_file(requirements=["Golang", "Mentor juniors"]))
        self.assertEqual(code, 1)
        self.assertIn("bad: rows[1]: requirement 'Go' is no requirements item word for word; give its of", lines)

    # ---- the map's rules, one each ----

    def test_category_must_be_one_of_four(self):
        self.assertIn("rows[1].category: 'partly covered' is not one of covered, shallow, claimed, unbacked, gap",
                      self.bad(dict(ROW, category="partly covered")))

    def test_gap_row_has_no_entry(self):
        self.assertEqual(self.bad(dict(GAP, entry="2025-01-widget.md")), ["rows[1]: a 'gap' row has no entry, written by or own work"])
        self.assertEqual(self.bad(dict(GAP, category="claimed, unbacked", written_by="user")),
                         ["rows[1]: a 'claimed, unbacked' row has no entry, written by or own work"])

    def test_written_by_must_be_one_of_five(self):
        self.assertEqual(self.bad(dict(ROW, written_by="me")),
                         ["rows[1].written_by: 'me' is not one of coursework, collaborator, AI agent, unknown, user"])

    def test_coursework_must_be_on_the_list(self):
        self.assertEqual(self.bad(dict(ROW, written_by="coursework", row_type="understanding")),
                         ["rows[1]: written by coursework, but 2025-01-widget.md is not on course_work"])
        self.assertEqual(self.bad(ROW, course_work=["2025-01-widget.md"]),
                         ["rows[1]: 2025-01-widget.md is on course_work, so its written by is coursework"])
        self.assertEqual(self.bad(ROW, course_work=["2025-09-none.md"]), ["course_work: '2025-09-none.md' is no file in entries/"])

    def test_own_work_only_on_agent_rows(self):
        self.assertEqual(self.bad(dict(ROW, own_work="design: Built the widget in Go.")),
                         ["rows[1].own_work: only an AI agent row has own work"])
        self.assertEqual(self.bad(dict(self.AGENT, own_work="")),
                         ["rows[1].own_work: empty on an AI agent row; give <label>: <quote> or none"])
        self.assertEqual(self.bad(dict(self.AGENT, own_work="traced the drift", category="shallow")),
                         ["rows[1].own_work: 'traced the drift' is neither none nor <label>: <quote>"])

    def test_quote_must_be_in_the_three_places(self):
        wrong = ("rows[1].own_work: the quote is not word for word in 2025-02-agent.md's ## My contribution, "
                 "## How it works or a Settled: line")
        self.assertEqual(self.bad(dict(self.AGENT, own_work="debugging: traced the drift to a cold cache")), [wrong])
        # in another section of the entry: not counted
        self.assertEqual(self.bad(dict(self.AGENT, own_work="review: Wrote the load tests by hand.", row_type="other",
                                       category="shallow")), [wrong])
        # whole words only, and three of them at least
        self.assertEqual(self.bad(dict(self.AGENT, own_work="debugging: aced the drift to a stale")), [wrong])
        self.assertEqual(self.bad(dict(self.AGENT, own_work="debugging: the drift")),
                         ["rows[1].own_work: the quote has fewer than three words; quote the line"])
        # curly quotes, quoted parts around an ellipsis and a bold label read as written
        for own in ("**debugging:** “traced the drift” … “had the agent fix it”",
                    "review: I read the agent’s parser and corrected its retry logic"):
            with self.subTest(own=own):
                self.assertEqual(self.bad(dict(self.AGENT, own_work=own, row_type="other")), [])

    def test_caps_hold_covered_rows(self):
        cases = [
            (dict(ROW, written_by="unknown"), "written by unknown"),
            (dict(self.AGENT, own_work="none"), "AI agent with own work none"),
            (dict(ROW, written_by="coursework", entry="2024-09-course.md", row_type="other"),
             "coursework on a row that is not understanding"),
            (dict(self.AGENT, row_type="language or tool", own_work="design: Chose SQLite over Postgres for the queue."),
             "a language or tool row with a design label"),
            (dict(self.AGENT, own_work="review: I read the agent's parser and corrected its retry logic."),
             "a debugging row with a review label"),
        ]
        for row, why in cases:
            with self.subTest(why=why):
                self.assertEqual(self.bad(row, course_work=["2024-09-course.md"]),
                                 ["rows[1].category: covered, but %s; at most shallow" % why])
                self.assertEqual(self.bad(dict(row, category="shallow"), course_work=["2024-09-course.md"]), [])

    def test_another_label_is_not_refused_but_caps(self):
        row = dict(self.AGENT, row_type="other", own_work="testing: Chose SQLite over Postgres for the queue.")
        self.assertEqual(self.bad(dict(row, category="shallow")), [])
        self.assertEqual(self.bad(row), ["rows[1].category: covered, but AI agent with the label 'testing' "
                                         "(not design, debugging or review); at most shallow"])

    def test_cited_entry_must_exist(self):
        self.assertEqual(self.bad(dict(ROW, entry="2025-03-gone.md")), ["rows[1].entry: 2025-03-gone.md is no file in entries/"])
        self.assertEqual(self.bad(dict(ROW, entry="the widget")), ["rows[1].entry: 'the widget' names no entry file"])

    def test_row_type_must_be_one_of_four(self):
        self.assertEqual(self.bad(dict(ROW, row_type="skill")),
                         ["rows[1].row_type: 'skill' is not one of language or tool, debugging, understanding, other"])

    # ---- heatmap ----

    def posting(self, name, company, rows, tier=None):
        """A map file for heatmap: rows as (skill, requirement, kind, category) tuples."""
        out = []
        for skill, req, kind, cat in rows:
            base = GAP if cat in fit.NO_ENTRY else ROW
            out.append(dict(base, requirement=req, kind=kind, category=cat, skill=skill))
        reqs = list(dict.fromkeys(r["requirement"] for r in out))
        return self.map_file(name, company=company, role="SWE", tier=tier, requirements=reqs, rows=out)

    def roles(self, *names):
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n\n%s\n## Constraints\n\n- US only\n"
                   % "".join("%d. %s\n" % (i, n) for i, n in enumerate(names, 1)))

    def heatmap(self, *files):
        code, lines = self.run_tool("heatmap", *files)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[-1], "heatmap: ok")
        rows = [l for l in lines if l.startswith("| ") and not l.startswith("| Priority")]
        return lines[0], [[c.strip() for c in r.strip("|").split("|")] for r in rows]

    def test_heatmap_merges_skills_across_postings(self):
        """Rows naming one skill in other words merge under `skill`; the weakest category wins; the
        counts and posting lists come from the map files."""
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "covered"), ("Kubernetes", "K8s", "required", "gap")])
        b = self.posting("b.jsonl", "B", [("go", "Golang", "required", "shallow"),
                                          ("Kubernetes", "Kubernetes in production", "required", "gap")])
        c = self.posting("c.jsonl", "C", [("Go", "Go", "required", "covered"), ("SQL", "SQL", "preferred", "gap")])
        head, rows = self.heatmap(a, b, c)
        self.assertEqual(head, "Heatmap: 3 skills, 2 gaps; weights: every posting the same; "
                               "3 postings (3 mapped, 0 rough) from 3 employers; flagged: 0 of 3")
        self.assertEqual(rows, [["critical", "Kubernetes", "gap", "2 of 3", "-", "#1, #2"],
                                ["high", "Go", "shallow", "3 of 3", "-", "#1, #2, #3"],
                                ["medium", "SQL", "gap", "1 of 3", "-", "#3"]])

    def test_heatmap_legend_numbers_the_postings_in_order(self):
        """#557: a legend numbers the map files in the order given, between the Heatmap: line and the
        table; Which lists those numbers, in order."""
        b = self.posting("b.jsonl", "  Beta Corp ", [("SQL", "SQL", "required", "gap")])
        a = self.posting("a.jsonl", "Alpha", [("Go", "Go", "required", "gap"), ("SQL", "SQL", "required", "covered")])
        code, lines = self.run_tool("heatmap", b, a)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[1:6], ["", "- #1 Beta Corp, SWE", "- #2 Alpha, SWE", "",
                                      "| Priority | Skill | Category | Postings | Rough | Which |"])
        self.assertEqual([r[5] for r in self.heatmap(b, a)[1]], ["#1, #2", "#2"])

    def test_heatmap_counts_a_posting_once_and_covered_gets_no_priority(self):
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "covered"), ("Go", "Go services", "duty", "covered"),
                                          ("SQL", "SQL", "required", "gap")])
        b = self.posting("b.jsonl", "B", [("Go", "Go", "required", "covered")])
        head, rows = self.heatmap(a, b)
        self.assertEqual(rows, [["high", "SQL", "gap", "1 of 2", "-", "#1"], ["-", "Go", "covered", "2 of 2", "-", "#1, #2"]])
        self.assertEqual(head, "Heatmap: 2 skills, 1 gaps; weights: every posting the same; "
                               "2 postings (2 mapped, 0 rough) from 2 employers; flagged: 0 of 2")

    def test_heatmap_weighs_by_tier(self):
        """The same gap is critical in the tier-1 posting and medium in the tier-3 one."""
        self.roles("Backend", "Platform", "Data")
        a = self.posting("a.jsonl", "A", [("Rust", "Rust", "required", "gap"), ("Go", "Go", "required", "covered")], tier=1)
        b = self.posting("b.jsonl", "B", [("SQL", "SQL", "required", "gap"), ("Go", "Go", "required", "covered")], tier=3)
        head, rows = self.heatmap(a, b)
        self.assertIn("; weights: tiers; ", head)
        self.assertEqual([r[:2] for r in rows], [["critical", "Rust"], ["medium", "SQL"], ["-", "Go"]])

    def test_heatmap_preferred_weighs_half(self):
        a = self.posting("a.jsonl", "A", [("Rust", "Rust", "preferred", "gap")])
        b = self.posting("b.jsonl", "B", [("Go", "Go", "required", "covered")])
        self.assertEqual(self.heatmap(a, b)[1][0][:2], ["medium", "Rust"])   # 1 / (2 * 2) = 0.25

    def test_heatmap_needs_skill_and_tier(self):
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "gap")], tier=2)
        self.write("fit/b.jsonl", json.dumps(dict(MAP, company="B")) + "\n")
        code, lines = self.run_tool("heatmap", a, "fit/b.jsonl")
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["bad: fit/a.jsonl: tier: 2, but direction.md's Target roles are empty",
                                 "bad: fit/b.jsonl: rows[1].skill: heatmap needs the skill's name on every row",
                                 "bad: fit/b.jsonl: rows[2].skill: heatmap needs the skill's name on every row",
                                 "bad: fit/b.jsonl: tier: heatmap needs it, a whole number from 1 or null"])
        self.roles("Backend")
        code, lines = self.run_tool("heatmap", a)
        self.assertEqual(lines, ["bad: tier: 2, but direction.md lists 1 target role(s)"])

    def test_heatmap_shows_only_bad_lines_on_a_bad_map(self):
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "covered")])
        b = self.posting("b.jsonl", "", [("Go", "Go", "required", "gap")])
        code, lines = self.run_tool("heatmap", a, b)
        self.assertEqual((code, lines), (1, ["bad: fit/b.jsonl: company, role: --several needs both in the map file"]))

    def test_heatmap_skill_must_be_a_string_once(self):
        self.assertEqual(self.bad(dict(ROW, skill=3)), ["rows[1].skill: must be a string"])
        a = self.map_file("a.jsonl", tier=None, rows=[dict(ROW, skill=3), dict(GAP, skill="  Mentoring   juniors ")])
        self.assertEqual(self.run_tool("heatmap", a), (1, ["bad: rows[1].skill: must be a string"]))
        b = self.map_file("a.jsonl", tier=None, rows=[dict(ROW, skill="Go"), dict(GAP, skill="  Mentoring   juniors ")])
        self.assertEqual(self.heatmap(b)[1][0][1], "Mentoring juniors")

    def test_heatmap_tier_counts_gap_lines(self):
        """A tier is the role's place in the list, `GAP:` lines counted: tier 3 is Platform here,
        weighed as the last role; a tier on a `GAP:` line is refused."""
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n\n1. Backend\n2. GAP: a second role?\n"
                   "3. Platform\n4. GAP: more?\n\n## Constraints\n\n- US only\n")
        a = self.posting("a.jsonl", "A", [("Rust", "Rust", "required", "gap")], tier=1)
        b = self.posting("b.jsonl", "B", [("SQL", "SQL", "required", "gap")], tier=3)
        head, rows = self.heatmap(a, b)
        self.assertEqual([r[:2] for r in rows], [["critical", "Rust"], ["medium", "SQL"]])   # weights 3 and 1: 6/8, 2/8
        c = self.posting("c.jsonl", "C", [("SQL", "SQL", "required", "gap")], tier=2)
        code, lines = self.run_tool("heatmap", c)
        self.assertEqual((code, lines), (1, ["bad: tier: 2 is the `GAP:` line of direction.md's Target roles, no role"]))
        d = self.posting("d.jsonl", "D", [("SQL", "SQL", "required", "gap")], tier=4)
        self.assertEqual(self.run_tool("heatmap", d),
                         (1, ["bad: tier: 4, but direction.md's last target role is 3"]))

    def test_heatmap_medium_and_low_rows(self):
        """Medium from a share of 0.1, low below it (2/12 and 1/12): the table keeps both, with their
        priority; two rows of one posting on one skill count once, as the weakest."""
        files = [self.posting("a.jsonl", "A", [("Rust", "Rust", "preferred", "gap"), ("Go", "Go", "required", "covered")])]
        files += [self.posting("%s.jsonl" % n, n.upper(), [("Go", "Go", "required", "covered")]) for n in "bcde"]
        files.append(self.posting("f.jsonl", "F", [("SQL", "SQL", "required", "covered"),
                                                  ("SQL", "SQL schema design", "required", "shallow")]))
        head, rows = self.heatmap(*files)
        self.assertEqual(head, "Heatmap: 3 skills, 1 gaps; weights: every posting the same; "
                               "6 postings (6 mapped, 0 rough) from 6 employers; flagged: 0 of 6")
        self.assertEqual([r[:3] for r in rows], [["medium", "SQL", "shallow"], ["low", "Rust", "gap"], ["-", "Go", "covered"]])

    def test_heatmap_ranks_a_synthesised_row(self):
        """A step-4 item is one more row on the requirement it is drawn from (`of`), merged by its skill."""
        item = dict(GAP, requirement="payments domain", of=2, kind="duty", skill="[domain] Payments")
        a = self.map_file("a.jsonl", company="A", tier=None, rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring"), item])
        b = self.map_file("b.jsonl", company="B", tier=None, rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring"), item])
        head, rows = self.heatmap(a, b)
        self.assertIn(["critical", "[domain] Payments", "gap", "2 of 2", "-", "#1, #2"], rows)

    def test_heatmap_weights_say_the_same_when_no_tier_is_given(self):
        self.roles("Backend")
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "gap")])
        self.assertIn("; weights: every posting the same; ", self.heatmap(a)[0])

    # ---- the capture a map file names (#571) ----

    def test_a_map_needs_its_capture(self):
        """A map file with no `capture`, or one naming no file, fails map and heatmap."""
        no_field = {k: v for k, v in MAP.items() if k != "capture"}
        self.write("fit/n.jsonl", json.dumps(no_field) + "\n")
        want = "capture: missing; it must be the path of the posting's capture (scan.py capture)"
        code, lines = self.run_tool("map", "fit/n.jsonl")
        self.assertEqual(code, 1)
        self.assertIn("bad: " + want, lines)
        self.assertEqual(self.bad(ROW, capture=""), [want])
        self.assertEqual(self.bad(ROW, capture="postings/gone.md"), ["capture: postings/gone.md is no file"])
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "gap")])
        self.write("fit/b.jsonl", json.dumps(dict(no_field, company="B", tier=None,
                                                  rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])) + "\n")
        self.assertEqual(self.run_tool("heatmap", a, "fit/b.jsonl"), (1, ["bad: fit/b.jsonl: " + want]))

    def test_an_open_fetched_capture_prints_no_flag(self):
        for how in ("fetch", "browser", "pasted"):
            self.write("postings/m.md", "https://a.com/1\nread: %s, open\n\nWe build widgets in Go.\n" % how)
            code, lines = self.run_tool("map", self.map_file())
            self.assertEqual(code, 0, lines)
            self.assertFalse([l for l in lines if l.startswith("flag:")], lines)

    def test_a_closed_or_stand_in_capture_is_flagged(self):
        """One flag: line per map file, outside the table, before map: ok; the map still passes."""
        self.write("postings/c.md", 'https://a.com/1\nread: fetch, closed (the page says "position has been filled")\n\nx\n')
        self.write("postings/s.md", "https://a.com/1\nread: stand-in https://api.a.com/j/1, open\n\nx\n")
        self.write("postings/b.md", "https://a.com/1\nread: stand-in https://api.a.com/j/1, closed (status 410)\n\nx\n")
        self.write("postings/u.md", "https://a.com/1\n\nx\n")
        want = {"c": 'closed (the page says "position has been filled")', "s": "read stand-in https://api.a.com/j/1",
                "b": "closed (status 410); read stand-in https://api.a.com/j/1",
                "u": "read unknown (the capture has no read line)"}
        for k, why in want.items():
            code, lines = self.run_tool("map", self.map_file(capture="postings/%s.md" % k))
            self.assertEqual(code, 0, lines)
            self.assertEqual(lines[-2:], ["flag: fit/m.jsonl | capture postings/%s.md | %s" % (k, why), "map: ok"])
        code, lines = self.run_tool("map", self.map_file(capture="postings/c.md"), "--show")
        self.assertEqual(lines[-3:], ["", "flag: fit/m.jsonl | capture postings/c.md | " + want["c"], "map: ok"])

    def test_heatmap_counts_the_flagged_maps(self):
        self.write("postings/c.md", "https://a.com/1\nread: browser, closed (status 404)\n\nx\n")
        self.write("postings/s.md", "https://b.com/1\nread: stand-in https://api.b.com/1, open\n\nx\n")
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "gap")])
        b = self.map_file("b.jsonl", company="B", tier=None, capture="postings/c.md",
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        c = self.map_file("c.jsonl", company="C", tier=None, capture="postings/s.md",
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        code, lines = self.run_tool("heatmap", a, b, c)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "Heatmap: 2 skills, 2 gaps; weights: every posting the same; "
                                   "3 postings (3 mapped, 0 rough) from 3 employers; flagged: 2 of 3")
        self.assertEqual(lines[-4:], ["", "flag: fit/b.jsonl | capture postings/c.md | closed (status 404)",
                                      "flag: fit/c.jsonl | capture postings/s.md | read stand-in https://api.b.com/1",
                                      "heatmap: ok"])
        self.assertTrue(self.heatmap(a)[0].endswith("; flagged: 0 of 1"))

    # ---- heatmap with Screen results (#569) ----

    RUN = ".build/scan/q"

    def screened(self, listed, results, name="batch-1.jsonl"):
        """A run folder's screen-list.jsonl (listed: (url, company) pairs) and one Screen results
        file in its screen/ folder; rough rows as (skill, kind, entries) tuples."""
        self.write(self.RUN + "/screen-list.jsonl",
                   "".join(json.dumps({"url": u, "company": c, "role": "SWE"}) + "\n" for u, c in listed))
        lines = []
        for r in results:
            if "rows" in r:
                r = dict(r, rows=[{"requirement": s, "kind": k, "entries": e, "skill": s} for s, k, e in r["rows"]])
            lines.append(json.dumps(dict({"gate": "yes", "tier": None}, **r)) + "\n")
        self.write(self.RUN + "/screen/" + name, "".join(lines))
        return self.RUN + "/screen/" + name

    def test_heatmap_counts_rough_rows_and_never_covers_from_them(self):
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "covered"), ("SQL", "SQL", "required", "gap")])
        s = self.screened([("https://b.com/1", "B"), ("https://c.com/2", "C"), ("https://d.com/3", "D"), ("https://e.com/4", "E")], [
            {"url": "https://b.com/1", "rows": [("go", "required", ["2025-01-widget.md"]), ("Kafka", "required", [])]},
            {"url": "https://c.com/2", "rows": [("Kafka", "preferred", ["2025-01-widget.md"])]},
            {"url": "https://d.com/3", "gate": "no", "reason": "US only"},
            {"url": "https://e.com/4", "touched": 1, "required": 2, "reused": "outputs/reports/x.md"}])
        code, lines = self.run_tool("heatmap", a, s)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[:6], ["Heatmap: 3 skills, 1 gaps; weights: every posting the same; "
                                     "3 postings (1 mapped, 2 rough) from 3 employers; flagged: 0 of 3", "",
                                     "- #1 A, SWE", "- #2 B, SWE (rough)", "- #3 C, SWE (rough)", ""])
        head, rows = self.heatmap(a, s)
        self.assertEqual(lines[6], "| Priority | Skill | Category | Postings | Rough | Which |")
        # Kafka: rough alone, never covered: (2 + 1) / 6 = 0.5; SQL: 2 / 6; Go stays covered
        self.assertEqual(rows, [["high", "Kafka", "rough", "2 of 3", "2 (1 touched)", "#2, #3"],
                                ["high", "SQL", "gap", "1 of 3", "-", "#1"],
                                ["-", "Go", "covered", "2 of 3", "1 (1 touched)", "#1, #2"]])

    def test_heatmap_rough_rows_add_to_a_mapped_skills_share(self):
        """A rough row on a skill a map row holds shallow adds its posting's weight; the category stays the map's."""
        self.roles("Backend", "Data")
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "shallow"), ("SQL", "SQL", "required", "covered")], tier=2)
        s = self.screened([("https://b.com/1", "B")], [{"url": "https://b.com/1", "tier": 1, "rows": [("Go", "duty", [])]}])
        head, rows = self.heatmap(a, s)
        self.assertTrue(head.startswith("Heatmap: 2 skills, 0 gaps; weights: tiers; 2 postings"), head)
        self.assertEqual(rows[0], ["critical", "Go", "shallow", "2 of 2", "1 (0 touched)", "#1, #2"])   # (2 + 4) / 6

    def test_heatmap_counts_a_mapped_posting_once(self):
        """A posting with a Screen result and a full map is the map's: by its url, or by company and role."""
        a = self.map_file("a.jsonl", company="B", role="SWE", tier=None, url="https://b.com/1/",
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        b = self.map_file("c.jsonl", company=" c ", role="swe", tier=None,
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        s = self.screened([("https://www.b.com/1", "B"), ("https://c.com/2", "C"), ("https://d.com/3", "D")], [
            {"url": "https://www.b.com/1", "rows": [("Kafka", "required", [])]},
            {"url": "https://c.com/2", "rows": [("Kafka", "required", [])]},
            {"url": "https://d.com/3", "rows": [("Rust", "required", [])]}])
        t = self.screened([("https://www.b.com/1", "B"), ("https://c.com/2", "C"), ("https://d.com/3", "D")],
                          [{"url": "https://d.com/3", "rows": [("Rust", "required", [])]}], name="batch-2.jsonl")
        code, lines = self.run_tool("heatmap", a, b, s, t)
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith("; 3 postings (2 mapped, 1 rough) from 3 employers; flagged: 0 of 3"), lines[0])
        self.assertEqual([l for l in lines if "Kafka" in l], [])
        self.assertIn("- #3 D, SWE (rough)", lines)

    def test_heatmap_a_map_files_own_rough_field_keeps_it_mapped(self):
        """A fit result that copied fit.jsonl's `rough` share ("6/7") is still a mapped posting."""
        a = self.map_file("a.jsonl", company="A", role="SWE", tier=None, rough="6/7",
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        code, lines = self.run_tool("heatmap", a)
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith("; 1 postings (1 mapped, 0 rough) from 1 employers; flagged: 0 of 1"), lines[0])
        self.assertIn("- #1 A, SWE", lines)

    def test_heatmap_skew_line_when_one_employer_holds_more_than_half(self):
        a = self.posting("a.jsonl", "Acme", [("Go", "Go", "required", "gap")])
        b = self.map_file("b.jsonl", company="ACME ", role="SRE", tier=None,
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        s = self.screened([("https://b.com/1", "Beta"), ("https://a.com/9", "acme")],
                          [{"url": "https://b.com/1", "rows": [("Go", "required", [])]}])
        code, lines = self.run_tool("heatmap", a, b, s)   # Acme 2 of 3
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith("3 postings (2 mapped, 1 rough) from 2 employers; flagged: 0 of 3"), lines[0])
        self.assertEqual(lines[1:3], ["skew: Acme holds 2 of the 3 postings", ""])
        t = self.screened([("https://b.com/1", "Beta"), ("https://a.com/9", "acme")],
                          [{"url": "https://b.com/1", "rows": [("Go", "required", [])]},
                           {"url": "https://a.com/9", "rows": [("Go", "required", [])]}], name="batch-2.jsonl")
        code, lines = self.run_tool("heatmap", b, t)   # 2 of 3 again, named as the first posting names it
        self.assertEqual(lines[1], "skew: ACME holds 2 of the 3 postings")
        code, lines = self.run_tool("heatmap", b, s)   # half is no skew
        self.assertEqual((code, lines[1]), (0, ""))
        self.assertFalse(any(l.startswith("skew:") for l in lines))

    def test_heatmap_flags_a_closed_rough_posting(self):
        """A rough posting whose capture (its screen-list.jsonl line's) is closed, a stand-in's or of an
        unknown read gets a flag: line after the map files' ones and counts on the Heatmap: line (#589)."""
        self.write("postings/c.md", "https://a.com/1\nread: browser, closed (status 404)\n\nx\n")
        self.write(self.RUN + "/postings/b.md", 'https://b.com/1\nread: fetch, closed (the page says "no longer accepting applications")\n\nx\n')
        self.write(self.RUN + "/postings/c.md", "https://c.com/2\nread: stand-in https://api.c.com/2, open\n\nx\n")
        self.write(self.RUN + "/postings/d.md", "https://d.com/3\nread: fetch, open\n\nx\n")
        self.write(self.RUN + "/postings/e.md", "https://e.com/4\n\nx\n")
        a = self.map_file("a.jsonl", company="A", tier=None, capture="postings/c.md",
                          rows=[dict(ROW, skill="Go"), dict(GAP, skill="Mentoring")])
        s = self.screened([], [{"url": u, "rows": [("Go", "required", [])]}
                               for u in ("https://b.com/1", "https://c.com/2", "https://d.com/3", "https://e.com/4")])
        self.write(self.RUN + "/screen-list.jsonl", "".join(
            json.dumps({"url": u, "company": c, "role": "SWE", "capture": self.RUN + "/postings/%s.md" % k}) + "\n"
            for u, c, k in [("https://b.com/1", "B", "b"), ("https://c.com/2", "C", "c"),
                            ("https://d.com/3", "D", "d"), ("https://e.com/4", "E", "e")]))
        code, lines = self.run_tool("heatmap", a, s)
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith("; 5 postings (1 mapped, 4 rough) from 5 employers; flagged: 4 of 5"), lines[0])
        self.assertEqual(lines[-6:], [
            "",
            "flag: fit/a.jsonl | capture postings/c.md | closed (status 404)",
            'flag: %s line 1 (rough) | capture %s/postings/b.md | closed (the page says "no longer accepting applications")'
            % (s, self.RUN),
            "flag: %s line 2 (rough) | capture %s/postings/c.md | read stand-in https://api.c.com/2" % (s, self.RUN),
            "flag: %s line 4 (rough) | capture %s/postings/e.md | read unknown (the capture has no read line)" % (s, self.RUN),
            "heatmap: ok"])
        s = self.screened([], [{"url": "https://b.com/1", "rows": [("Go", "required", [])]}])
        self.write(self.RUN + "/screen-list.jsonl", json.dumps(
            {"url": "https://b.com/1", "company": "B", "role": "SWE", "capture": self.RUN + "/postings/gone.md"}) + "\n")
        code, lines = self.run_tool("heatmap", s)
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith("; flagged: 1 of 1"), lines[0])
        self.assertEqual(lines[-2], "flag: %s line 1 (rough) | capture %s/postings/gone.md | read unknown (no file)" % (s, self.RUN))

    def test_heatmap_checks_screen_results(self):
        a = self.posting("a.jsonl", "A", [("Go", "Go", "required", "gap")])
        s = self.screened([("https://b.com/1", "B")], [
            {"url": "https://b.com/1", "rows": [("Go", "required", [])]},
            {"url": "https://x.com/7", "rows": [("Go", "required", [])]}])
        self.write(self.RUN + "/screen/batch-1.jsonl", self.read_text(s).replace('"skill": "Go"', '"skill": ""', 1))
        code, lines = self.run_tool("heatmap", a, s)
        self.assertEqual((code, lines), (1, [
            "bad: %s: line 1: https://b.com/1: each row needs a skill, named as a map row's (tools/fit.py --help)" % s,
            "bad: %s: line 2: https://x.com/7 is on no line of the run's screen-list.jsonl, which gives its company and role"
            % s]))
        self.write(self.RUN + "/screen/reused.jsonl", "")   # an empty results file adds nothing
        self.assertEqual(self.run_tool("heatmap", a, self.RUN + "/screen/reused.jsonl")[0], 0)
        s = self.screened([("https://b.com/1", " ")], [{"url": "https://b.com/1", "rows": [("Go", "required", [])]},
                                                       {"url": "https://c.com/2", "gate": "no", "reason": "x"}])
        self.assertEqual(self.run_tool("heatmap", a, s), (1, [
            "bad: %s: line 1: https://b.com/1 has no company or role on its screen-list.jsonl line" % s]))
        s = self.screened([("https://c.com/2", "C")], [{"url": "https://c.com/2", "gate": "no", "reason": "x"}])
        self.assertEqual(self.run_tool("heatmap", s), (1, [
            "bad: no posting: give a map file, or a Screen result with a gate yes and its rows"]))

    def read_text(self, name):
        with open(os.path.join(self.tmp, name), encoding="utf-8") as f:
            return f.read()

    def test_runs_isolated(self):
        """`-I` leaves the script's folder off sys.path: the tool still finds logfiles.py."""
        p = subprocess.run([sys.executable, "-I", TOOL, "--root", self.tmp, "check", "none.jsonl"], capture_output=True,
                           encoding="utf-8")
        self.assertEqual(p.returncode, 1)
        self.assertTrue(p.stdout.startswith("fit: "), p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
