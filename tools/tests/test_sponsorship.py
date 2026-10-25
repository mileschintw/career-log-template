#!/usr/bin/env python3
"""Tests for tools/sponsorship.py, on Logs made in a temporary directory, with made-up employers and
record URLs (no lookup reaches any site).

  python3 -I tools/tests/test_sponsorship.py
"""
import datetime, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True   # the tool loaded below leaves no tools/__pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "sponsorship.py")
spec = importlib.util.spec_from_file_location("sponsorship", TOOL)
sponsorship = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sponsorship)

TODAY = "2026-10-24"


def answered(item, data="2026-06"):
    """A result line with the sources and data_date `add` asks of an answered one."""
    return dict(item, sources=[{"url": "https://%s.example/search?em=%s" % (item["kind"], item["employer"].replace(" ", "+")),
                                "name": item["employer"]}], data_date=data)
LINE = "- **Visa sponsorship needed:** H-1B; green card (PERM) (user, 2026-10-01)\n"

# Saved postings for `wording`, made up around phrasings public postings use (#377), and the sentences
# it should find in each; the plain one holds the wording every posting has and finds nothing.
EEO = ("Example Robotics is an equal opportunity employer. We do not discriminate on the basis of race, religion,"
       " national origin or immigration status.")
POSTINGS = {
    "f1-j1": "https://jobs.example/1\n\nSoftware Engineer, Intern\n\nWhat you'll do\n- Build services in Go.\n\n"
             "This position is not eligible for F1 and J1 students. It is not available for any work sponsorship.\n\n" + EEO,
    "unrestricted": "https://jobs.example/2\n\nData Engineer\n\nRequirements\n- 2+ years of Python\n"
                    "- Candidates must have unrestricted work authorization now or in the future.\n\n" + EEO,
    "temporary": "https://jobs.example/3\n\nBackend Engineer\n\nWe are unable to consider candidates on temporary work"
                 " authorization, including F-1 OPT, STEM OPT and CPT. Remote in the US.\n\n" + EEO,
    "future": "https://jobs.example/4\n\nPlatform Engineer\n\nApplicants must be authorized to work in the United States"
              " without the need for current or future employer sponsorship.\n\n" + EEO,
    "plain": "https://jobs.example/5\n\nML Engineer\n\nRequirements\n- Report an F1 score and not just accuracy.\n"
             "- Must be legally authorized to work in the United States.\n- No relocation offered.\n\n" + EEO,
}
WANT = {
    "f1-j1": ["This position is not eligible for F1 and J1 students.",
              "It is not available for any work sponsorship."],
    "unrestricted": ["Candidates must have unrestricted work authorization now or in the future."],
    "temporary": ["We are unable to consider candidates on temporary work authorization, including F-1 OPT, STEM OPT and CPT."],
    "future": ["Applicants must be authorized to work in the United States without the need for current or future"
               " employer sponsorship."],
    "plain": ["none"],
}


class SponsorshipTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.direction(LINE)

    def direction(self, line):
        self.write("direction.md", "# Direction\n\n## Constraints\n- **Work authorisation:** Needs sponsorship"
                                   " (user, 2026-10-01)\n%s\n## What to emphasise, by target\n" % line)

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return p

    def jsonl(self, rel, items):
        return self.write(rel, "".join(json.dumps(i) + "\n" for i in items))

    def run_tool(self, *args, date=TODAY):
        out = io.StringIO()
        with redirect_stdout(out):
            code = sponsorship.main(list(args) + ["--root", self.root, "--date", date])
        return code, out.getvalue().splitlines()

    def records(self):
        with open(os.path.join(self.root, sponsorship.RECORDS), encoding="utf-8") as f:
            return [json.loads(l) for l in f]

    # ---- employers ----

    def test_employer_key_folds_legal_forms_and_punctuation(self):
        k = sponsorship.employer_key
        self.assertEqual(k("Example Robotics, Inc."), "example robotics")
        self.assertEqual(k("EXAMPLE ROBOTICS INC"), "example robotics")
        self.assertEqual(k("Example Robotics L.L.C."), "example robotics")
        self.assertEqual(k("The Sample Labs Corp."), "sample labs")
        self.assertEqual(k("Smith & Jones Co"), "smith and jones")
        self.assertEqual(k("Inc."), "inc")   # a name that is only a legal form keeps it
        self.assertEqual(k("Smith & Jones & Co."), "smith and jones")   # `& Co.`: its `and` goes with it
        self.assertEqual(k("Johnson and Johnson"), "johnson and johnson")
        self.assertNotEqual(k("Example Robotics"), k("Example Robotics Group"))   # the agent judges a parent

    # ---- need, add, reuse (Done when 1) ----

    def test_three_postings_two_employers_then_reuse_then_stale(self):
        fit = self.jsonl("fit.jsonl", [{"url": "https://jobs.example/1", "company": "Example Robotics Inc."},
                                       {"url": "https://jobs.example/2", "company": "Example Robotics"},
                                       {"url": "https://jobs.example/3", "company": "Sample Labs"}])
        code, lines = self.run_tool("need", "--from", fit)
        self.assertEqual((code, lines), (0, ["lookups: lca, perm",
                                             "lookup: Example Robotics Inc. | lca", "lookup: Example Robotics Inc. | perm",
                                             "lookup: Sample Labs | lca", "lookup: Sample Labs | perm",
                                             "need: 4 to look up, 0 reused"]))
        result = self.jsonl("result.jsonl", [answered(i) for i in [
            {"employer": "Example Robotics Inc.", "kind": "lca",
             "records": [{"url": "https://lca.example/er-1", "filer": "EXAMPLE ROBOTICS INC", "certain": True},
                         {"url": "https://lca.example/erg-1", "filer": "EXAMPLE ROBOTICS GROUP", "certain": False}]},
            {"employer": "Example Robotics Inc.", "kind": "perm", "records": []},
            {"employer": "Sample Labs", "kind": "lca", "records": []},
            {"employer": "Sample Labs", "kind": "perm",
             "records": [{"url": "https://perm.example/sl-1", "filer": "SAMPLE LABS LLC", "certain": True}]}]])
        code, lines = self.run_tool("add", result)
        self.assertEqual((code, lines), (0, ["added: Example Robotics Inc. | lca | 2 record(s)",
                                             "added: Example Robotics Inc. | perm | none found",
                                             "added: Sample Labs | lca | none found",
                                             "added: Sample Labs | perm | 1 record(s)",
                                             "commit: sponsorship: Example Robotics Inc., Sample Labs"]))
        self.assertEqual([(r["employer"], r["kind"], r["date"]) for r in self.records()],
                         [("Example Robotics Inc.", "lca", TODAY), ("Example Robotics Inc.", "perm", TODAY),
                          ("Sample Labs", "lca", TODAY), ("Sample Labs", "perm", TODAY)])
        # a second scan within the reuse age: every lookup reused, any spelling of the name
        code, lines = self.run_tool("need", "Example Robotics", "Sample Labs, Inc.", date="2026-12-01")
        self.assertEqual(lines, ["lookups: lca, perm",
                                 "reuse: Example Robotics | lca | %s" % TODAY, "reuse: Example Robotics | perm | %s" % TODAY,
                                 "reuse: Sample Labs, Inc. | lca | %s" % TODAY, "reuse: Sample Labs, Inc. | perm | %s" % TODAY,
                                 "need: 0 to look up, 4 reused"])
        # one day short of REUSE_DAYS: still reused; REUSE_DAYS later: looked up again
        almost = (datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=sponsorship.REUSE_DAYS - 1)).isoformat()
        self.assertEqual(self.run_tool("need", "Sample Labs", date=almost)[1][-1], "need: 0 to look up, 2 reused")
        later = (datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=sponsorship.REUSE_DAYS)).isoformat()
        self.assertEqual(self.run_tool("need", "Sample Labs", date=later)[1][-1], "need: 2 to look up, 0 reused")
        code, lines = self.run_tool("show", "Example Robotics", "Sample Labs", "Nobody Ltd")
        self.assertEqual(lines, [
            "record: Example Robotics | lca | %s | https://lca.example/er-1 | EXAMPLE ROBOTICS INC | certain"
            " | data: 2026-06" % TODAY,
            "record: Example Robotics | lca | %s | https://lca.example/erg-1 | EXAMPLE ROBOTICS GROUP | not certain"
            " | data: 2026-06" % TODAY,
            "record: Example Robotics | perm | %s | none found | data: 2026-06"
            " | https://perm.example/search?em=Example+Robotics+Inc." % TODAY,
            "record: Sample Labs | lca | %s | none found | data: 2026-06 | https://lca.example/search?em=Sample+Labs" % TODAY,
            "record: Sample Labs | perm | %s | https://perm.example/sl-1 | SAMPLE LABS LLC | certain | data: 2026-06" % TODAY,
            "record: Nobody Ltd | lca | not looked up", "record: Nobody Ltd | perm | not looked up"])
        # a later lookup replaces the employer's record of that kind only
        self.jsonl("again.jsonl", [answered({"employer": "Sample Labs Inc", "kind": "lca", "records": []})])
        self.assertEqual(self.run_tool("add", "again.jsonl", date=later)[0], 0)
        self.assertEqual([(r["employer"], r["kind"], r["date"]) for r in self.records()][2:],
                         [("Sample Labs Inc", "lca", later), ("Sample Labs", "perm", TODAY)])

    def test_only_the_kinds_the_line_names(self):
        self.direction("- **Visa sponsorship needed:** H-1B (user, 2026-10-01)\n")
        self.assertEqual(self.run_tool("need", "Sample Labs")[1],
                         ["lookups: lca", "lookup: Sample Labs | lca", "need: 1 to look up, 0 reused"])

    # ---- no line (Done when 2) ----

    def test_no_line_no_lookup_unless_asked(self):
        for line in ("", "- **Visa sponsorship needed:** none (user, 2026-10-01)\n",
                     "- **Visa sponsorship needed:** GAP: needs one?\n"):
            self.direction(line)
            code, lines = self.run_tool("need", "Sample Labs")
            self.assertEqual(code, 0)
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith("lookups: none ("), lines)
            self.assertTrue(self.run_tool("show", "Sample Labs")[1][0].startswith("lookups: none ("))
            self.assertEqual(sponsorship.unrecorded(self.root, ["Sample Labs"], datetime.date.today()), [])
        # the user asks ("does Sample Labs sponsor?"): --kinds stands in for the line
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "Sample Labs")[1],
                         ["lookups: lca", "lookup: Sample Labs | lca", "need: 1 to look up, 0 reused"])
        self.assertEqual(self.run_tool("need", "--kinds", "perm,lca", "Sample Labs")[1][0], "lookups: lca, perm")
        self.assertFalse(os.path.exists(os.path.join(self.root, sponsorship.RECORDS)))

    def test_an_unknown_line_value_is_refused(self):
        self.direction("- **Visa sponsorship needed:** O-1 (user, 2026-10-01)\n")
        code, lines = self.run_tool("need", "Sample Labs")
        self.assertEqual(code, 1)
        self.assertIn("O-1", lines[0])
        self.assertIn('direction set \\"visa sponsorship\\"', json.dumps(lines[0]))

    # ---- add refuses ----

    def test_add_checks_every_line_and_writes_nothing_on_a_problem(self):
        bad = self.write("bad.jsonl", "\n".join([
            json.dumps(answered({"employer": "A", "kind": "lca", "records": []})),
            "{not json",
            json.dumps({"employer": "B", "kind": "h1b", "records": []}),
            json.dumps({"employer": "C", "kind": "lca", "records": [{"url": "lca.example/1", "filer": "C", "certain": True}]}),
            json.dumps({"employer": "D", "kind": "lca", "records": [{"url": "https://lca.example/1", "filer": "D"}]}),
            json.dumps({"employer": "E", "kind": "lca", "records": [{"url": "https://x.example", "filer": "E", "certain": "yes"}]}),
            json.dumps({"employer": "A, Inc.", "kind": "lca", "records": []}),
            json.dumps({"employer": "F", "kind": "lca", "records": None}),
            json.dumps({"employer": "G", "kind": "lca", "records": [], "date": "2020-01-01"}),
            json.dumps({"employer": " ", "kind": "lca", "records": []}),
            json.dumps({"employer": "H", "kind": "lca", "records": [], "note": "x"}),
            # the fields of OPTIONAL (#284): an answered line names its sources and data date
            json.dumps({"employer": "I", "kind": "lca", "records": [], "data_date": "2026-06"}),
            json.dumps(dict(answered({"employer": "J", "kind": "lca", "records": []}), data_date=None)),
            json.dumps({k: v for k, v in answered({"employer": "K", "kind": "lca", "records": []}).items() if k != "data_date"}),
            json.dumps(answered({"employer": "L", "kind": "lca", "records": []}, data="2026-13")),
            json.dumps(dict(answered({"employer": "M", "kind": "lca", "records": []}), sources=[{"url": "https://x.example"}])),
            json.dumps({"employer": "N", "kind": "perm", "records": [], "unanswered": " "}),
            json.dumps({"employer": "O", "kind": "perm", "unanswered": "403", "records": [
                {"url": "https://x.example", "filer": "O", "certain": True}]}),
            json.dumps(dict(answered({"employer": "P", "kind": "lca", "records": []}), unanswered="403")),
            json.dumps(dict(answered({"employer": "Q", "kind": "lca", "records": []}), parent="")),
            json.dumps(dict(answered({"employer": "R", "kind": "lca", "records": []}), parent="R Group")),
        ]) + "\n")
        code, lines = self.run_tool("add", bad)
        self.assertEqual(code, 1)
        self.assertEqual([l.split(":")[0] + ":" + l.split(":")[1] for l in lines],
                         ["bad: line %d" % n for n in range(2, 22)])
        self.assertIn("bad: line 12: sources names the pages read", lines[10])
        self.assertIn("bad: line 14: data_date is how recent", lines[12])
        self.assertFalse(os.path.exists(os.path.join(self.root, sponsorship.RECORDS)))
        self.write("empty.jsonl", "\n")
        self.assertEqual(self.run_tool("add", "empty.jsonl"), (1, ["bad: empty.jsonl holds no result line"]))

    # ---- unanswered, a parent's records, and lines kept before them (#284) ----

    def test_an_unanswered_line_is_kept_shown_and_looked_up_again(self):
        self.jsonl("result.jsonl", [
            answered({"employer": "Sample Labs", "kind": "lca", "records": []}),
            {"employer": "Sample Labs", "kind": "perm", "records": [],
             "sources": [{"url": "https://perm.example/sample-labs", "name": "Sample Labs"}],
             "unanswered": "perm.example answered 403"}])
        self.assertEqual(self.run_tool("add", "result.jsonl")[1][:2],
                         ["added: Sample Labs | lca | none found", "added: Sample Labs | perm | unanswered"])
        self.assertEqual(self.run_tool("show", "Sample Labs")[1][1],
                         "record: Sample Labs | perm | %s | unanswered | perm.example answered 403" % TODAY)
        self.assertEqual(self.run_tool("need", "Sample Labs", date="2026-10-25")[1], [
            "lookups: lca, perm", "reuse: Sample Labs | lca | %s" % TODAY,
            "lookup: Sample Labs | perm | unanswered %s | perm.example answered 403" % TODAY,
            "need: 1 to look up, 1 reused"])
        # the lookup was made: scan's check finds no missing record; its report says unanswered
        self.assertEqual(sponsorship.unrecorded(self.root, ["Sample Labs"], datetime.date(2026, 10, 25)), [])
        self.assertIn("| Sample Labs | PERM | %s | - | unanswered: perm.example answered 403 | - | - |" % TODAY,
                      sponsorship.report_lines(self.root, ["Sample Labs"]))

    def test_an_unanswered_line_as_write_returns_it(self):
        """#437: the line write's company lookup now returns for a `lookup:` line no read answered,
        `"records": []` with `"unanswered"` and nothing else: add, show and scan's check take it."""
        self.assertEqual(self.run_tool("need", "Sample Labs")[1][1:3],
                         ["lookup: Sample Labs | lca", "lookup: Sample Labs | perm"])
        self.jsonl("result.jsonl", [
            answered({"employer": "Sample Labs", "kind": "lca", "records": []}),
            {"employer": "Sample Labs", "kind": "perm", "records": [], "unanswered": "perm.example asked for a sign-in"}])
        self.assertEqual(self.run_tool("add", "result.jsonl"), (0, [
            "added: Sample Labs | lca | none found", "added: Sample Labs | perm | unanswered",
            "commit: sponsorship: Sample Labs"]))
        self.assertEqual(self.run_tool("show", "Sample Labs")[1][1],
                         "record: Sample Labs | perm | %s | unanswered | perm.example asked for a sign-in" % TODAY)
        self.assertEqual(sponsorship.unanswered(self.root, ["Sample Labs"], datetime.date(2026, 10, 25)),
                         [("Sample Labs", "perm", "perm.example asked for a sign-in")])
        # past REUSE_DAYS it is unrecorded's, not unanswered's: one finding, not two
        later = datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=sponsorship.REUSE_DAYS)
        self.assertEqual(sponsorship.unanswered(self.root, ["Sample Labs"], later), [])
        self.assertIn(("Sample Labs", "perm"), sponsorship.unrecorded(self.root, ["Sample Labs"], later))

    def test_again_looks_up_a_fresh_none_found_under_a_legal_name(self):
        """#484: the user gives a legal name after a none found under the short name: `need --again`
        looks it up again however fresh the record, and the result, under the same employer, replaces it."""
        self.jsonl("result.jsonl", [answered({"employer": "Example", "kind": "lca", "records": []}),
                                    answered({"employer": "Example", "kind": "perm", "records": []}),
                                    answered({"employer": "Sample Labs", "kind": "lca", "records": []}),
                                    answered({"employer": "Other Co", "kind": "lca", "parent": "Parent Corp", "records": [
                                        {"url": "https://lca.example/p", "filer": "PARENT CORP", "certain": False}]}),
                                    answered({"employer": "Found Inc", "kind": "lca",
                                              "records": [{"url": "https://lca.example/f", "filer": "FOUND INC", "certain": True}]})])
        self.assertEqual(self.run_tool("add", "result.jsonl")[0], 0)
        later = "2026-10-30"
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "Sample Labs", "--again", "Example", date=later)[1], [
            "lookups: lca", "reuse: Sample Labs | lca | %s" % TODAY, "lookup: Example | lca | again %s" % TODAY,
            "need: 1 to look up, 1 reused"])
        # alone, with --from, with a comma in the name, `=` form; each kind of the line
        fit = self.jsonl("fit.jsonl", [{"company": "Sample Labs"}])
        self.assertEqual(self.run_tool("need", "--again=Example, Inc.", "--from", fit, date=later)[1], [
            "lookups: lca, perm", "lookup: Example, Inc. | lca | again %s" % TODAY,
            "lookup: Example, Inc. | perm | again %s" % TODAY, "reuse: Sample Labs | lca | %s" % TODAY,
            "lookup: Sample Labs | perm", "need: 3 to look up, 1 reused"])
        # none under its own name with a parent's records: looked up again; records under its own name: reused
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "--again", "Other Co", "--again", "Found Inc", date=later)[1], [
            "lookups: lca", "lookup: Other Co | lca | again %s" % TODAY, "reuse: Found Inc | lca | %s" % TODAY,
            "need: 1 to look up, 1 reused"])
        # past REUSE_DAYS a none found is still an `again` line; an unanswered one keeps its own line
        old = (datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=sponsorship.REUSE_DAYS)).isoformat()
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "--again", "Sample Labs", date=old)[1][1],
                         "lookup: Sample Labs | lca | again %s" % TODAY)
        self.jsonl("timeout.jsonl", [{"employer": "Gone Corp", "kind": "lca", "records": [], "unanswered": "timed out"}])
        self.run_tool("add", "timeout.jsonl")
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "--again", "Gone Corp", date=later)[1][1],
                         "lookup: Gone Corp | lca | unanswered %s | timed out" % TODAY)
        # an --again lookup no read answers keeps the none found, so --again asks for it once more
        self.jsonl("timeout.jsonl", [{"employer": "Sample Labs", "kind": "lca", "records": [], "unanswered": "timed out"}])
        self.assertEqual(self.run_tool("add", "timeout.jsonl", date=later)[1],
                         ["kept: Sample Labs | lca | %s, unanswered now" % TODAY])
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "--again", "Sample Labs", date=later)[1][1],
                         "lookup: Sample Labs | lca | again %s" % TODAY)
        # without --again, the same record is reused
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "Example", date=later)[1][1], "reuse: Example | lca | %s" % TODAY)
        self.jsonl("again.jsonl", [dict(answered({"employer": "Example", "kind": "lca",
                                                  "records": [{"url": "https://lca.example/el", "filer": "EXAMPLE LABS INC",
                                                               "certain": True}]}),
                                        sources=[{"url": "https://lca.example/search?em=Example+Labs+Inc", "name": "Example Labs Inc"}])])
        self.assertEqual(self.run_tool("add", "again.jsonl", date=later)[1][0], "added: Example | lca | 1 record(s)")
        mine = [r for r in self.records() if r["employer"] == "Example"]
        self.assertEqual([(r["kind"], r["date"], len(r["records"])) for r in mine], [("lca", later, 1), ("perm", TODAY, 0)])
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "--again", "Example", date=later)[1][1],
                         "reuse: Example | lca | %s" % later)
        for args in (("add", "again.jsonl", "--again", "Example"), ("show", "--again", "Example"),
                     ("wording", "a.md", "--again", "Example"), ("need", "--again"), ("need", "--again=", "A"),
                     ("need", "--again", " ")):
            self.assertEqual(self.run_tool(*args)[0], 2, args)

    def test_an_unanswered_line_leaves_an_answer_in_place(self):
        self.jsonl("result.jsonl", [answered({"employer": "Sample Labs", "kind": "lca", "records": []})])
        self.run_tool("add", "result.jsonl")
        later = "2027-03-01"
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "Sample Labs", date=later)[1][1], "lookup: Sample Labs | lca")
        self.jsonl("again.jsonl", [{"employer": "Sample Labs", "kind": "lca", "records": [], "unanswered": "timed out"}])
        self.assertEqual(self.run_tool("add", "again.jsonl", date=later),
                         (0, ["kept: Sample Labs | lca | %s, unanswered now" % TODAY]))
        self.assertEqual(self.records()[0]["date"], TODAY)
        self.assertNotIn("unanswered", self.records()[0])

    def test_a_parent_s_records_keep_none_under_its_own_name(self):
        self.jsonl("result.jsonl", [dict(answered({"employer": "Example Photos", "kind": "lca", "parent": "Example Group",
            "records": [{"url": "https://lca.example/search?em=Example+Group", "filer": "EXAMPLE GROUP INC",
                         "certain": False}]}), sources=[
            {"url": "https://lca.example/search?em=Example+Photos", "name": "Example Photos"},
            {"url": "https://lca.example/search?em=Example+Group", "name": "Example Group"}])])
        self.assertEqual(self.run_tool("add", "result.jsonl")[0], 0)
        self.assertEqual(self.run_tool("show", "--kinds", "lca", "Example Photos")[1], [
            "record: Example Photos | lca | %s | none under its own name | parent: Example Group" % TODAY,
            "record: Example Photos | lca | %s | https://lca.example/search?em=Example+Group | EXAMPLE GROUP INC"
            " | not certain | data: 2026-06" % TODAY])
        self.assertEqual(self.records()[0]["sources"][0]["name"], "Example Photos")
        self.assertIn("| Example Photos | H-1B LCA | %s | 2026-06 | none under its own name; parent: Example Group | - | - |" % TODAY,
                      sponsorship.report_lines(self.root, ["Example Photos"]))

    def test_lines_kept_before_the_new_fields_still_read(self):
        # outputs/reports/sponsorship.jsonl as the tool first wrote it (#369): no sources, data_date or unanswered
        self.jsonl(sponsorship.RECORDS, [
            {"employer": "Sample Labs", "kind": "lca", "date": TODAY,
             "records": [{"url": "https://lca.example/sl-1", "filer": "SAMPLE LABS INC", "certain": True}]},
            {"employer": "Sample Labs", "kind": "perm", "date": TODAY, "records": []}])
        self.assertEqual(self.run_tool("show", "Sample Labs")[1], [
            "record: Sample Labs | lca | %s | https://lca.example/sl-1 | SAMPLE LABS INC | certain" % TODAY,
            "record: Sample Labs | perm | %s | none found" % TODAY])
        self.assertEqual(self.run_tool("need", "Sample Labs")[1][-1], "need: 0 to look up, 2 reused")
        # a later add keeps them as they are
        self.jsonl("result.jsonl", [answered({"employer": "Example Robotics", "kind": "lca", "records": []})])
        self.assertEqual(self.run_tool("add", "result.jsonl")[0], 0)
        self.assertNotIn("sources", [r for r in self.records() if r["employer"] == "Sample Labs"][0])

    def test_a_damaged_records_file_is_reported(self):
        self.write(sponsorship.RECORDS, "{bad\n")
        code, lines = self.run_tool("need", "A")
        self.assertEqual(code, 1)
        self.assertIn("does not parse", lines[0])
        self.jsonl(sponsorship.RECORDS, [{"employer": "A", "kind": "lca", "date": "2026-02-30", "records": []}])
        code, lines = self.run_tool("need", "A")
        self.assertEqual((code, len(lines)), (1, 1))
        self.assertIn("date is not a YYYY-MM-DD day", lines[0])
        with self.assertRaises(sponsorship.SponsorshipError):
            sponsorship.unrecorded(self.root, ["A"], datetime.date(2026, 10, 24))

    def test_show_escapes_a_bar_and_options_take_an_equals_sign(self):
        self.jsonl(sponsorship.RECORDS, [{"employer": "A|B", "kind": "lca", "date": TODAY,
                                          "records": [{"url": "https://lca.example/a|b", "filer": "A|B", "certain": False}]}])
        code, lines = self.run_tool("show", "--kinds=lca", "A|B")
        self.assertEqual(lines, ["record: A\\|B | lca | %s | https://lca.example/a\\|b | A\\|B | not certain" % TODAY])
        fit = self.jsonl("fit.jsonl", [{"company": "A|B"}])
        self.assertEqual(self.run_tool("need", "--from=" + fit)[1][1], "reuse: A\\|B | lca | %s" % TODAY)

    # ---- OPT and CPT: the posting's wording (#377) ----

    def test_opt_and_cpt_ask_for_no_lookup_and_say_why(self):
        for line, kinds in (("OPT", ""), ("CPT; OPT", ""), ("OPT; H-1B", "lca")):
            self.direction("- **Visa sponsorship needed:** %s (user, 2026-10-01)\n" % line)
            code, lines = self.run_tool("need", "Sample Labs")
            self.assertEqual(code, 0)
            wording = "wording: OPT, CPT" if "CPT" in line else "wording: OPT"
            if kinds:
                self.assertEqual(lines, ["lookups: lca", "lookup: Sample Labs | lca", "need: 1 to look up, 0 reused", wording])
            else:
                self.assertEqual(len(lines), 2)
                self.assertTrue(lines[0].startswith("lookups: none (") and "names only OPT" in lines[0], lines)
                self.assertEqual(lines[1], wording)
        self.assertEqual(self.run_tool("need", "--kinds", "lca", "Sample Labs")[1][-1], "need: 1 to look up, 0 reused")
        self.assertEqual(self.run_tool("show", "Sample Labs")[1], ["record: Sample Labs | lca | not looked up"])

    def test_wording_finds_each_phrasing_and_not_a_plain_posting(self):
        self.direction("- **Visa sponsorship needed:** OPT (user, 2026-10-01)\n")
        files = [self.write("postings/%s.md" % name, text) for name, text in POSTINGS.items()]
        code, lines = self.run_tool("wording", *files)
        self.assertEqual(code, 0)
        self.assertEqual(lines[0], "wording: OPT")
        found = {}
        for l in lines[1:]:
            f, s = l[len("restricts: "):].split(" | ", 1)
            found.setdefault(os.path.basename(f)[:-3], []).append(s)
        self.assertEqual(found, WANT)

    def test_wording_sentences_found_and_not(self):
        for text in ("Must not require visa sponsorship, e.g. H-1B, now or in the future.",   # one sentence, e.g. kept
                     "You must be eligible to work now and at any time in the future without sponsorship.",
                     "Candidates need an unrestricted right to work in the US.",
                     "Sponsorship is not available for this role.", "We do not offer visa sponsorship.",
                     "No H1B, OPT, CPT or other temporary work authorization candidates will be considered."):
            self.assertEqual(sponsorship.restricting(text), [text])
        for text in ("You may opt out of self-identification; declining will not affect your application.",
                     "We sponsor visas and do not discriminate on any basis.",
                     "Visa sponsorship is available for candidates who do not yet have work authorization.",
                     "F-1 students on OPT are welcome to apply."):
            self.assertEqual(sponsorship.restricting(text), [], text)

    def test_wording_needs_opt_or_cpt(self):
        f = self.write("p.md", POSTINGS["f1-j1"])
        code, lines = self.run_tool("wording", f)   # H-1B; green card (PERM)
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("wording: none ("), lines)
        self.assertEqual(self.run_tool("wording", "--statuses", "cpt,opt", f)[1][:2],
                         ["wording: OPT, CPT", "restricts: %s | %s" % (f, WANT["f1-j1"][0])])
        self.direction("- **Visa sponsorship needed:** CPT (user, 2026-10-01)\n")
        self.assertEqual(self.run_tool("wording", f)[1][0], "wording: CPT")
        code, lines = self.run_tool("wording", "missing.md")
        self.assertEqual(code, 1)
        self.assertIn("missing.md cannot be read", lines[0])

    def test_bad_arguments(self):
        for args in ((), ("need",), ("add",), ("add", "a", "b"), ("need", "--kinds", "h1b", "A"), ("frob", "A"),
                     ("add", "x.jsonl", "--kinds", "lca"), ("need", "--frob", "A"), ("need", "--kinds=", "A"),
                     ("wording",), ("wording", "--statuses", "H-1B", "a.md"), ("wording", "--kinds", "lca", "a.md"),
                     ("need", "--statuses", "OPT", "A"), ("wording", "--statuses", "OPT,OPT", "a.md")):
            self.assertEqual(self.run_tool(*args)[0], 2, args)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(sponsorship.main(["--help"]), 0)
        self.assertIn("REUSE_DAYS", out.getvalue())

    def test_runs_as_a_script_and_leaves_no_pycache(self):
        tools = os.path.join(self.root, "tools")
        os.makedirs(tools)
        for name in ("sponsorship.py", "config.py", "logfiles.py", "config.default.toml"):
            shutil.copy(os.path.join(HERE, "..", name), tools)
        env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
        p = subprocess.run([sys.executable, "-I", os.path.join(tools, "sponsorship.py"), "--root", self.root, "need",
                            "Sample Labs"], capture_output=True, encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout.splitlines()[0], "lookups: lca, perm")
        self.assertFalse(os.path.exists(os.path.join(tools, "__pycache__")))


if __name__ == "__main__":
    unittest.main()
