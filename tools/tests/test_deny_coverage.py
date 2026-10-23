#!/usr/bin/env python3
"""Tests for tools/deny_coverage.py, on small made-up Logs built in a temporary directory.

  python3 -I tools/tests/test_deny_coverage.py
"""
import importlib.util, io, os, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "deny_coverage.py")
spec = importlib.util.spec_from_file_location("deny_coverage", TOOL)
deny_coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deny_coverage)

ENTRY = """---
title: Quillfeather Labs — Backend Developer (Associate)
type: work
period: 2020-01 – 2021-01
org: Quillfeather Labs Pte Ltd (Quillfeather), Ledger Team; sponsored by Zentrovia (with the Thrandlewick Council)
my_role: Developer at Hollowmere
collaborators: Orrin Vask
links: [https://github.com/quillfeather-dev/brindle-engine, https://example.org/brindle.pdf]
last_updated: 2021-01-01
---

# Quillfeather Labs

Hollowmere is named only in the body.
"""

# CRLF line ends, a byte order mark, a quoted value, block lists and a nested GitLab group
PROJECT = ("﻿---\n"
           'title: "Dual-Path Widget Sorter"\n'
           "type: project\n"
           "org:\n"
           "  - glintmoor\n"
           "links:\n"
           "  - https://gitlab.example.edu/course-group/term-two/widget-sorter-lab/-/tree/main\n"
           "---\n").replace("\n", "\r\n")

APPLICATIONS = """# Applications and contacts

## Applications

| Date | Company | Role | Answers / notes | Source |
|---|---|---|---|---|
| 2026-01-01 | Fizzlo.io | Intern | Why Fizzlo | src |
| 2026-01-02 | (company GAP) | (role GAP) | notes | src |
| 2026-01-03 | Q&R Partners | Intern | Pellquor is named only in the notes | src |
| 2026-01-04 | a \\| b | Intern | an escaped pipe | src |

## Events and contacts

| Date | **Event / company** | Who | What happened | Next step | Source |
|---|---|---|---|---|---|
| 2026-02-01 | Tarnwick summit, Spring 2031 (open day visit) | Vexlin Corp | met | | src |
| 2026-02-02 | Career fair (company GAP; page "Join the Glimmerfold mission") | A recruiter | | | src |
"""

RANKING = """# Ranking

| # | 公司 | 為什麼 |
|---|---|---|
| 1 | Korvane | 原因 |
"""

PROFILE = """# Profile

| Degree | Period | Institution | Notes |
|---|---|---|---|
| B.S. | 2015 – 2019 | Morrowfen Institute, Quistable | notes |
"""


def make_log(root, deny="", cleared=None):
    files = {
        "entries/2020-01-quillfeather.md": ENTRY,
        "entries/2026-01-widget-sorter.md": PROJECT,
        "entries/_template.md": "---\ntitle: <placeholder> — role\norg: Templatecorp\n---\n",
        "applications.md": APPLICATIONS,
        "profile.md": PROFILE,
        "outputs/reports/2026-03-01-fair-ranking.md": RANKING,
        "outputs/reports/2026-03-01-notes.md": RANKING.replace("Korvane", "Notacompany"),
        ".export-deny": "# comment\n\n" + deny,
    }
    if cleared is not None:
        files[".export-cleared"] = cleared
    for rel, text in files.items():
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    os.makedirs(os.path.join(root, "outputs", "applications", "2026-01-05-sablewood-data-engineer"))


def run(root):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = deny_coverage.main(["deny_coverage.py", root])
    return rc, out.getvalue()


ALL_NAMES = {
    "Quillfeather Labs": "entries/2020-01-quillfeather.md",
    "Quillfeather Labs Pte Ltd": "entries/2020-01-quillfeather.md",
    "Quillfeather": "entries/2020-01-quillfeather.md",
    "Ledger Team": "entries/2020-01-quillfeather.md",
    "Zentrovia": "entries/2020-01-quillfeather.md",
    "the Thrandlewick Council": "entries/2020-01-quillfeather.md",
    "quillfeather-dev": "entries/2020-01-quillfeather.md",
    "brindle-engine": "entries/2020-01-quillfeather.md",
    "glintmoor": "entries/2026-01-widget-sorter.md",
    "course-group": "entries/2026-01-widget-sorter.md",
    "term-two": "entries/2026-01-widget-sorter.md",
    "widget-sorter-lab": "entries/2026-01-widget-sorter.md",
    "Fizzlo.io": "applications.md",
    "Q&R Partners": "applications.md",
    "a | b": "applications.md",
    "Tarnwick summit": "applications.md",
    "Career fair": "applications.md",
    "page": "applications.md",
    "Morrowfen Institute": "profile.md",
    "Quistable": "profile.md",
    "Korvane": "outputs/reports/2026-03-01-fair-ranking.md",
    "sablewood-data-engineer": "outputs/applications/2026-01-05-sablewood-data-engineer",
}


class Recorded(unittest.TestCase):
    def test_names_and_where_found(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root)
            self.assertEqual(dict(deny_coverage.recorded(root)), ALL_NAMES)

    def test_left_out(self):
        # The body, other front matter fields, a title without ` — `, the entry template, a report
        # that is not a ranking, and the Who and notes columns are not read.
        with tempfile.TemporaryDirectory() as root:
            make_log(root)
            names = " ".join(n for n, _ in deny_coverage.recorded(root))
            for absent in ("Hollowmere", "Orrin", "Dual-Path", "Templatecorp", "Notacompany",
                           "Vexlin", "Pellquor", "Glimmerfold", "brindle.pdf", "tree", "main"):
                self.assertNotIn(absent, names)

    def test_note_for_unread_tables(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "profile.md"), "w", encoding="utf-8") as f:
                f.write("| Firm name | Notes |\n|---|---|\n| Korvane | x |\n")
            notes = []
            self.assertEqual(deny_coverage.recorded(root, notes), [])
            self.assertEqual(len(notes), 1)
            self.assertIn("no table in profile.md has a column", notes[0])

    def test_quoted_title_and_org(self):
        text = '---\ntitle: "Zentrovia — Dev"\norg: "Quillfeather, Inc."\n---\n'
        self.assertEqual(deny_coverage.entry_names(text), ["Zentrovia", "Quillfeather", "Inc"])


class Pieces(unittest.TestCase):
    def cases(self, value, prose=False):
        return list(deny_coverage.pieces(value, prose))

    def test_split(self):
        self.assertEqual(self.cases("Alpha Co (Alpha), Beta Unit; Gamma — Delta"),
                         ["Alpha Co", "Alpha", "Beta Unit", "Gamma", "Delta"])
        self.assertEqual(self.cases("Korvane（只收實習）、Pellbrook"), ["Korvane", "只收實習", "Pellbrook"])

    def test_dropped(self):
        for value in ("GAP", "(company GAP)", "companies GAP", "personal", "None", "n/a",
                      "Spring 2031", "winter 2032", '"Quoted Title"', "", "  ", ">", "|", "--"):
            self.assertEqual(self.cases(value), [], value)

    def test_prose_dropped_in_table_cells_only(self):
        for value in ("the open day", "summer job hunt", "12 booths",
                      "a storage-related role"):
            self.assertEqual(self.cases(value, prose=True), [], value)
        self.assertEqual(self.cases("glintmoor"), ["glintmoor"])
        self.assertEqual(self.cases("glintmoor", prose=True), ["glintmoor"])
        self.assertEqual(self.cases("three", prose=True), ["three"])
        self.assertEqual(self.cases("brindle labs"), ["brindle labs"])

    def test_connector_cut(self):
        self.assertEqual(self.cases("sponsored by Zentrovia"), ["Zentrovia"])
        self.assertEqual(self.cases("the user was at Tarnwick"), ["Tarnwick"])
        self.assertEqual(self.cases("zentrovia AI"), ["zentrovia AI"])
        self.assertEqual(self.cases("with @zentrovia"), ["zentrovia"])

    def test_lowercase_names_kept(self):
        self.assertEqual(self.cases("widget-sorter", prose=True), ["widget-sorter"])
        self.assertEqual(self.cases("fizzlo.io", prose=True), ["fizzlo.io"])


class Coverage(unittest.TestCase):
    def covered(self, pattern, name):
        p = deny_coverage.compile_pattern(pattern)
        return not deny_coverage.uncovered([(name, "x")], [p], [])

    def test_whole_word_ignoring_case(self):
        self.assertTrue(self.covered("Zentrovia", "sponsored ZENTROVIA team"))
        self.assertTrue(self.covered("Quillfeather", "Quillfeather Labs Pte Ltd"))
        self.assertTrue(self.covered("widget-sorter", "widget-sorter-lab"))
        self.assertFalse(self.covered("Zentro", "Zentrovia"))
        self.assertFalse(self.covered("Fizzlo", "Fizzlo_io"))

    def test_regex_and_posix_classes(self):
        self.assertTrue(self.covered("Q&R[- ]?Partners", "Q&R Partners"))
        self.assertTrue(self.covered("Fizzlo\\.io", "Fizzlo.io"))
        self.assertFalse(self.covered("Fizzlo\\.io", "Fizzloxio"))
        self.assertTrue(self.covered("Thrandlewick[[:space:]]Council", "Thrandlewick Council"))
        self.assertTrue(self.covered("Korv[[:xdigit:]]ne", "Korvane"))
        self.assertTrue(self.covered("\\<Korvane\\>", "Korvane"))

    def test_patterns_grep_reads_otherwise(self):
        self.assertTrue(self.covered("Korvane \\(?Labs\\)?", "Korvane (Labs)"))
        for pat in ("Korvane\\d+", "(?i)Korvane", "Kor(?=vane)", "Korv[[:foo:]]ne", "Quill(feather"):
            with self.assertRaises(Exception, msg=pat):
                deny_coverage.compile_pattern(pat)

    def test_cleared_exact_ignoring_case(self):
        names = [("Career fair", "a"), ("Career fair day", "b")]
        self.assertEqual(deny_coverage.uncovered(names, [], ["career FAIR"]), [("Career fair day", "b")])

    def test_deny_line_matches_slugs(self):
        self.assertEqual(deny_coverage.deny_line("Korvane"), "Korvane")
        line = deny_coverage.deny_line("Q&R Partners")
        self.assertEqual(line, "Q[^[:alnum:]]+R[^[:alnum:]]+Partners")
        for text in ("Q&R Partners", "rank-q-r-partners"):
            self.assertTrue(self.covered(line, text), text)
        self.assertEqual(deny_coverage.deny_line("Ledger Team"), "Ledger[^[:alnum:]]*Team")
        self.assertTrue(self.covered("Ledger[^[:alnum:]]*Team", "ledgerteam"))
        self.assertTrue(self.covered(deny_coverage.deny_line("Fizzlo.io"), "fizzlo-io"))
        line = deny_coverage.deny_line("Q&R")
        self.assertEqual(line, "Q[^[:alnum:]]+R")
        self.assertTrue(self.covered(line, "rank-q-r"))
        self.assertFalse(self.covered(line, "qr"))

    def test_deny_line_covers_its_name(self):
        for name in list(ALL_NAMES) + ["Q & R Partners", "Q&R  Partners", "A.B. Labs", "Neo42",
                                       "C++", "C#", "Yahoo!", ".NET", "X", "a\\b (c)"]:
            self.assertTrue(self.covered(deny_coverage.deny_line(name), name), name)

    def test_deny_line_one_run(self):
        self.assertEqual(deny_coverage.deny_line("C++"), "C\\+\\+")
        self.assertEqual(deny_coverage.deny_line("C#"), "C#")
        self.assertFalse(self.covered("C\\+\\+", "plain C code"))
        self.assertEqual(deny_coverage.deny_line("Yahoo!"), "Yahoo")
        self.assertTrue(self.covered("Yahoo", "rank-yahoo"))
        self.assertEqual(deny_coverage.deny_line(" .NET "), "\\.NET")
        self.assertFalse(self.covered("\\.NET", "net income"))
        self.assertEqual(deny_coverage.deny_line("Go!"), "Go!")
        for name in ("[Korvane]", "@korvane", "#korvane", "`Korvane`", "\"Korvane\""):
            self.assertEqual(deny_coverage.deny_line(name).lower(), "korvane", name)

    def test_deny_line_keeps_word_characters_at_the_edges(self):
        self.assertEqual(deny_coverage.deny_line("_site_"), "_site_")
        self.assertTrue(self.covered("_site_", "_site_"))
        line = deny_coverage.deny_line("widget_engine_")
        self.assertEqual(line, "_*widget[^[:alnum:]]*engine_*")
        for text in ("widget_engine_", "widget-engine", "WidgetEngine", "_widget_engine_"):
            self.assertTrue(self.covered(line, text), text)

    def test_deny_line_possessive(self):
        line = deny_coverage.deny_line("Pellquor's")
        self.assertEqual(line, "Pellquor[^[:alnum:]]*s")
        for text in ("Pellquor's", "rank-pellquors", "pellquor-s"):
            self.assertTrue(self.covered(line, text), text)
        self.assertEqual(deny_coverage.ere_escape("a-b & c.(d)"), "a-b & c\\.\\(d\\)")

    def test_deny_line_slugs_and_joined(self):
        line = deny_coverage.deny_line("Brindle Works")
        for text in ("Brindle Works", "rank-brindle-works", "BrindleWorks", "brindle_works"):
            self.assertTrue(self.covered(line, text), text)
        self.assertTrue(self.covered(deny_coverage.deny_line("Acme & Co"), "rank-acme-co"))

    def test_commit_links(self):
        self.assertEqual(deny_coverage.repo_segments("https://github.com/zent-org/brindle/commit/abc123"),
                         ["zent-org", "brindle"])
        self.assertEqual(deny_coverage.repo_segments("https://github.com/zent-org/actions"), ["zent-org", "actions"])


DENY_ALL = "\n".join(["Quillfeather", "Ledger Team", "Zentrovia", "Thrandlewick", "brindle-engine",
                      "glintmoor", "course-group", "term-two", "widget-sorter", "Fizzlo\\.io", "Q&R",
                      "a \\| b", "Tarnwick", "Morrowfen", "Quistable", "Korvane", "Sablewood"]) + "\n"


class Main(unittest.TestCase):
    def test_missing_names_fail(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny="Quillfeather\nZentrovia\n")
            rc, out = run(root)
        self.assertEqual(rc, 1)
        self.assertIn("does not cover 17 name(s)", out)
        self.assertIn("  Korvane    (outputs/reports/2026-03-01-fair-ranking.md)\n", out)
        self.assertIn("  Fizzlo.io    (applications.md)    deny: Fizzlo[^[:alnum:]]*io\n", out)
        self.assertNotIn("Zentrovia    (", out)

    def test_all_covered_pass(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny=DENY_ALL, cleared="# cleared\nCareer fair\npage\n")
            rc, out = run(root)
        self.assertEqual((rc, out), (0, f"OK: .export-deny covers {len(ALL_NAMES)} recorded names\n"))

    def test_cleared_name_not_reported(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny=DENY_ALL, cleared="")
            rc, out = run(root)
            self.assertEqual(rc, 1)
            self.assertIn("  Career fair    (applications.md)    deny: Career[^[:alnum:]]*fair\n", out)
            with open(os.path.join(root, ".export-cleared"), "w", encoding="utf-8") as f:
                f.write("career fair\nPAGE\n")
            self.assertEqual(run(root)[0], 0)

    def test_bad_pattern(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny="Quill(feather\n")
            rc, out = run(root)
        self.assertEqual(rc, 2)
        self.assertIn("cannot read the .export-deny pattern 'Quill(feather'", out)

    def test_not_utf8(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny=DENY_ALL)
            with open(os.path.join(root, "profile.md"), "wb") as f:
                f.write(b"| Institution |\n|---|\n| \xff\xfe |\n")
            rc, out = run(root)
        self.assertEqual(rc, 2)
        self.assertIn("profile.md is not UTF-8", out)

    def test_deny_file_with_bom(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root)
            with open(os.path.join(root, ".export-deny"), "w", encoding="utf-8-sig") as f:
                f.write(DENY_ALL)
            rc, out = run(root)
        self.assertEqual(rc, 2)
        self.assertIn("byte order mark", out)

    def test_no_deny_file(self):
        with tempfile.TemporaryDirectory() as root:
            rc, out = run(root)
        self.assertEqual(rc, 2)
        self.assertIn("FAIL: no .export-deny", out)

    def test_line_prints_each_name(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = deny_coverage.main(["deny_coverage.py", "line", "Brindle Works", "Korvane", "C++"])
        self.assertEqual((rc, out.getvalue()), (0, "Brindle[^[:alnum:]]*Works\nKorvane\nC\\+\\+\n"))

    def test_line_needs_a_name(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = deny_coverage.main(["deny_coverage.py", "line"])
        self.assertEqual(rc, 2)
        self.assertIn("usage:", out.getvalue())
        for argv in (["line", ""], ["line", "  "], ["line", "--to"], ["line", "--to", "x"],
                     ["line", "Korvane", "--to", "x"], ["line", "--to=x", "Korvane"], ["line", "-x"],
                     ["line", "Go\n!"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(deny_coverage.main(["deny_coverage.py"] + argv), 2, argv)

    def test_line_refuses_a_name_with_no_line(self):
        # A name the edge cuts leave empty would be an empty .export-deny line: refused, nothing added.
        for names in (["@"], ["()"], ["` * `"], ["Korvane", "'@'"]):
            with tempfile.TemporaryDirectory() as root:
                deny = os.path.join(root, ".export-deny")
                with open(deny, "wb") as f:
                    f.write(b"Brindle\n")
                for to in ([], ["--to", deny]):
                    out = io.StringIO()
                    with redirect_stdout(out):
                        rc = deny_coverage.main(["deny_coverage.py", "line"] + to + names)
                    self.assertEqual(rc, 2, (names, to))
                    self.assertTrue(out.getvalue().startswith("FAIL: no deny: line for "), out.getvalue())
                    self.assertEqual(out.getvalue().count("\n"), 1, out.getvalue())   # no line printed
                with open(deny, "rb") as f:
                    self.assertEqual(f.read(), b"Brindle\n")

    def test_line_to_appends_new_lines(self):
        with tempfile.TemporaryDirectory() as root:
            deny = os.path.join(root, ".export-deny")
            with open(deny, "w", encoding="utf-8", newline="") as f:
                f.write("# comment\r\nKorvane")
            with redirect_stdout(io.StringIO()):
                rc = deny_coverage.main(["deny_coverage.py", "line", "--to", deny,
                                         "KORVANE", "Brindle Works", "Brindle Works", "Café Noir"])
            with open(deny, "rb") as f:
                data = f.read()
        self.assertEqual(rc, 0)
        self.assertEqual(data, ("# comment\r\nKorvane\nBrindle[^[:alnum:]]*Works\n"
                                "Café[^[:alnum:]]*Noir\n").encode("utf-8"))

    def test_line_to_refuses_unreadable_files(self):
        for data, said in ((b"\xef\xbb\xbfKorvane\n", "byte order mark"), (b"\xff\xfe\n", "not UTF-8")):
            with tempfile.TemporaryDirectory() as root:
                deny = os.path.join(root, ".export-deny")
                with open(deny, "wb") as f:
                    f.write(data)
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = deny_coverage.main(["deny_coverage.py", "line", "--to", deny, "Brindle Works"])
                with open(deny, "rb") as f:
                    self.assertEqual(f.read(), data)
            self.assertEqual(rc, 2)
            self.assertIn(said, out.getvalue())

    def test_line_to_needs_the_file(self):
        with tempfile.TemporaryDirectory() as root:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py", "line", "--to", os.path.join(root, "no"), "Korvane"])
        self.assertEqual(rc, 2)
        self.assertIn("FAIL: no ", out.getvalue())

    def test_entry_to_adds_what_the_check_needs(self):
        # An org whose repo owner differs from its name: the owner and repo are recorded names too.
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny=DENY_ALL, cleared="Career fair\npage\n")
            entry = os.path.join(root, "entries", "2026-04-recon.md")
            with open(entry, "w", encoding="utf-8") as f:
                f.write("---\ntitle: Pellbrook Brothers' Foundry — Analyst\norg: Pellbrook Brothers' Foundry\n"
                        "links: [https://github.com/pb-foundry/recon-reports/pull/7]\n---\n")
            self.assertEqual(run(root)[0], 1)
            argv = ["deny_coverage.py", "entry", "--to", os.path.join(root, ".export-deny"), entry]
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(argv)
            self.assertEqual((rc, out.getvalue()),
                             (0, "Pellbrook[^[:alnum:]]*Brothers[^[:alnum:]]*Foundry\n"
                                 "pb[^[:alnum:]]*foundry\nrecon[^[:alnum:]]*reports\n"))
            self.assertEqual(run(root), (0, f"OK: .export-deny covers {len(ALL_NAMES) + 3} recorded names\n"))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(deny_coverage.main(argv), 0)
            self.assertEqual(out.getvalue(),
                             "OK: .export-deny and .export-cleared cover the 3 names these entries record\n")

    def test_entry_one_line_per_spelling(self):
        with tempfile.TemporaryDirectory() as root:
            deny = os.path.join(root, ".export-deny")
            make_log(root, deny="Someone\n")
            entry = os.path.join(root, "entries", "2026-06-brindle.md")
            with open(entry, "w", encoding="utf-8") as f:
                f.write("---\norg: Brindle & Co\nlinks: [https://github.com/brindle-co/x-y]\n---\n")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py", "entry", "--to", deny, entry])
        self.assertEqual((rc, out.getvalue()), (0, "Brindle[^[:alnum:]]*Co\nx[^[:alnum:]]+y\n"))

    def test_entry_skips_covered_and_cleared_names(self):
        # Quillfeather covers Quillfeather Labs; the cleared name stays out of .export-deny.
        with tempfile.TemporaryDirectory() as root:
            deny = os.path.join(root, ".export-deny")
            make_log(root, deny="Quillfeather\nbrindle-engine\n", cleared="ledger team\n")
            entry = os.path.join(root, "entries", "2020-01-quillfeather.md")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py", "entry", "--to", deny, entry])
            with open(deny, encoding="utf-8") as f:
                text = f.read()
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "Zentrovia\nthe[^[:alnum:]]*Thrandlewick[^[:alnum:]]*Council\n")
        self.assertTrue(text.endswith("brindle-engine\nZentrovia\nthe[^[:alnum:]]*Thrandlewick[^[:alnum:]]*Council\n"))
        self.assertNotIn("Ledger", text)

    def test_entry_without_to_only_prints(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root)
            entry = os.path.join(root, "entries", "2026-01-widget-sorter.md")
            deny = os.path.join(root, ".export-deny")
            with open(deny, "rb") as f:
                before = f.read()
            here = deny_coverage.__file__
            try:
                deny_coverage.__file__ = os.path.join(root, "tools", "deny_coverage.py")
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = deny_coverage.main(["deny_coverage.py", "entry", entry])
            finally:
                deny_coverage.__file__ = here
            with open(deny, "rb") as f:
                self.assertEqual(f.read(), before)
        self.assertEqual((rc, out.getvalue()), (0, "glintmoor\ncourse[^[:alnum:]]*group\nterm[^[:alnum:]]*two\n"
                                                   "widget[^[:alnum:]]*sorter[^[:alnum:]]*lab\n"))

    def test_entry_not_utf8(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root)
            entry = os.path.join(root, "entries", "2026-05-bad.md")
            with open(entry, "wb") as f:
                f.write(b"---\norg: \xff\xfe\n---\n")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py", "entry", "--to", os.path.join(root, ".export-deny"), entry])
        self.assertEqual(rc, 2)
        self.assertIn("is not UTF-8", out.getvalue())

    def test_entry_skips_url_segments_with_no_name(self):
        # A links: segment with no letter or digit (`@`, `*`) is not a name, so no empty line is added.
        with tempfile.TemporaryDirectory() as root:
            deny = os.path.join(root, ".export-deny")
            entry = os.path.join(root, "entry.md")
            with open(deny, "wb") as f:
                f.write(b"Brindle\nKorvane\n")
            with open(entry, "w", encoding="utf-8") as f:
                f.write("---\ntitle: Sync\norg: Brindle\nlinks:\n  - https://github.com/@/brindle\n"
                        "  - https://github.com/korvane/*\n---\n")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py", "entry", "--to", deny, entry])
            with open(deny, "rb") as f:
                data = f.read()
        self.assertEqual(rc, 0)
        self.assertTrue(out.getvalue().startswith("OK: "), out.getvalue())
        self.assertEqual(data, b"Brindle\nKorvane\n")

    def test_entry_bad_arguments(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny="Quill(feather\n")
            deny = os.path.join(root, ".export-deny")
            entry = os.path.join(root, "entries", "2020-01-quillfeather.md")
            for argv, said in ((["entry"], "usage:"), (["entry", "--to", deny], "usage:"), (["entry", ""], "usage:"),
                               (["entry", entry, "--to", deny], "usage:"),
                               (["entry", "--to", os.path.join(root, "no"), entry], "FAIL: no "),
                               (["entry", "--to", deny, os.path.join(root, "no.md")], "FAIL: no "),
                               (["entry", "--to", deny, entry], "cannot read the .export-deny pattern")):
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(deny_coverage.main(["deny_coverage.py"] + argv), 2, argv)
                self.assertIn(said, out.getvalue(), argv)

    def test_help(self):
        for args in (["--help"], ["-h"], [".", "--help"], ["line", "-h"], ["line", "Korvane", "--help"],
                     ["entry", "--help"]):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py"] + args)
            self.assertEqual((rc, out.getvalue().splitlines()), (0, deny_coverage.__doc__.splitlines()), args)

    def test_empty_log_passes(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, ".export-deny"), "w", encoding="utf-8") as f:
                f.write("Someone\n")
            self.assertEqual(run(root), (0, "OK: .export-deny covers 0 recorded names\n"))


if __name__ == "__main__":
    unittest.main()
