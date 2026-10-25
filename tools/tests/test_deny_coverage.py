#!/usr/bin/env python3
"""Tests for tools/deny_coverage.py, on small made-up Logs built in a temporary directory; the
--commit and clear ones in a clone of a bare origin, with git's global and system config left out,
as tools/tests/test_sync.py does.

  python3 -I tools/tests/test_deny_coverage.py
"""
import importlib.util, io, os, shlex, shutil, subprocess, sys, tempfile, unittest
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
        rc = deny_coverage.main(["deny_coverage.py", "--root", root])
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
        # A quoted org is one name; a title is still cut at ` — ` and split
        text = '---\ntitle: "Zentrovia — Dev"\norg: "Quillfeather, Inc."\n---\n'
        self.assertEqual(deny_coverage.entry_names(text), ["Zentrovia", "Quillfeather, Inc"])

    def test_unquoted_org_is_split(self):
        # Unquoted, a comma can list several employers on one line
        self.assertEqual(deny_coverage.entry_names("---\norg: Quillfeather, Inc.\n---\n"), ["Quillfeather", "Inc"])

    def test_quoted_list_and_hash(self):
        # A quoted list item and a quoted `#` are read whole, as logfiles.front_matter reads them
        self.assertEqual(deny_coverage.entry_names('---\norg: ["Acme, Inc", "Beta Labs"]\n---\n'),
                         ["Acme, Inc", "Beta Labs"])
        self.assertEqual(deny_coverage.entry_names('---\norg: ["GAP", "sponsored by Acme, Inc"]\n---\n'),
                         ["Acme, Inc"])   # the GAP and connector rules apply to the whole value
        self.assertEqual(deny_coverage.entry_names('---\norg: "Acme #1 Labs"   # the lab\n---\n'),
                         ["Acme #1 Labs"])
        self.assertEqual(deny_coverage.entry_names("---\norg:\n  - 'Acme #1 Labs'\n  - Beta # x\n---\n"),
                         ["Acme #1 Labs", "Beta"])
        # A quote inside quotes the same kind keeps the whole value (no one-letter `O` to deny)
        self.assertEqual(deny_coverage.entry_names("---\norg: 'O''Brien Co'\ntitle: 'Children's Ward — Dev'\n---\n"),
                         ["O'Brien Co", "Children's Ward"])

    def test_a_part_of_a_quoted_name_covers_it(self):
        # The export's grep -iwE matches whole words, so a deny line `Acme` covers `Acme, Inc`
        patterns = [deny_coverage.compile_pattern("Acme")]
        names = [(n, "e.md") for n in deny_coverage.entry_names('---\norg: ["Acme, Inc"]\n---\n')]
        self.assertEqual(names, [("Acme, Inc", "e.md")])
        self.assertEqual(deny_coverage.uncovered(names, patterns, []), [])

    def test_every_line_of_a_repeated_key(self):
        self.assertEqual(deny_coverage.entry_names("---\norg: Acme\norg: Beta\n---\n"), ["Acme", "Beta"])

    def test_title_with_no_dash_when_org_names_no_one(self):
        # With no ` — `, the whole title is a name only when `org` is missing, empty, `personal` or a GAP
        for org in ("", "org:\n", "org: []\n", "org: personal\n", "org: Personal\n", "org: GAP\n",
                    "org: GAP: which group ran it\n", "org: [personal, GAP]\n", 'org: "personal"\n',
                    'org: [""]\n'):
            self.assertEqual(deny_coverage.entry_names(f"---\ntitle: Brindlewood Kite Map\n{org}---\n"),
                             ["Brindlewood Kite Map"], org)
            self.assertEqual(deny_coverage.entry_names(f"---\ntitle: Brindlewood — Kite map\n{org}---\n"),
                             ["Brindlewood"], org)
        # An org that names someone: the title is read only up to ` — `, as before
        for org in ("org: Quillfeather Labs\n", "org: Quillfeather (GAP: which team)\n", "org: [personal, Zentrovia]\n"):
            names = deny_coverage.entry_names(f"---\ntitle: Brindlewood Kite Map\n{org}---\n")
            self.assertNotIn("Brindlewood Kite Map", names, org)
            names = deny_coverage.entry_names(f"---\ntitle: Brindlewood — Kite map\n{org}---\n")
            self.assertIn("Brindlewood", names, org)
            self.assertNotIn("Kite map", names, org)
        # A whole title is one name: not split at commas or parentheses, its quoted text kept
        for title in ("Notes, maps and kites", '"Kite, Map"', "Brindlewood (v2)", 'Rewrite of "Brindlewood"'):
            self.assertEqual(len(deny_coverage.entry_names(f"---\ntitle: {title}\norg: personal\n---\n")), 1, title)
        # `none` and `n/a` are not among the values that let a whole title be read
        self.assertEqual(deny_coverage.entry_names("---\ntitle: Brindlewood Kite Map\norg: none\n---\n"), [])
        # The org may come after the title
        self.assertEqual(deny_coverage.entry_names("---\ntitle: Brindlewood Kite Map\norg: GAP\n---\n"),
                         deny_coverage.entry_names("---\norg: GAP\ntitle: Brindlewood Kite Map\n---\n"))

    def test_unclosed_front_matter_names_nothing(self):
        self.assertEqual(deny_coverage.entry_names("---\ntitle: x\n\norg: Acme\n"), [])

    def test_root_is_given_with_the_flag(self):
        with tempfile.TemporaryDirectory() as root:
            make_log(root)
            for argv in ([root], ["--root"], ["--root", root, "--root", root], ["--root="]):
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(deny_coverage.main(["deny_coverage.py"] + argv), 2, argv)
                self.assertTrue(out.getvalue().startswith("usage:"), argv)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(deny_coverage.main(["deny_coverage.py", "--root=" + root]), 1)


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
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py", "entry", "--root", root, entry])
            with open(deny, "rb") as f:
                self.assertEqual(f.read(), before)
        self.assertEqual((rc, out.getvalue()), (0, "glintmoor\ncourse[^[:alnum:]]*group\nterm[^[:alnum:]]*two\n"
                                                   "widget[^[:alnum:]]*sorter[^[:alnum:]]*lab\n"))

    def test_entry_relative_to_root(self):
        # Run from another folder, a relative path is read against --root; one from the current folder wins
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as elsewhere:
            make_log(root)
            with open(os.path.join(root, "entries", "2026-08-kite.md"), "w", encoding="utf-8") as f:
                f.write("---\ntitle: Brindlewood Kite Map\norg: personal\n---\n")
            os.makedirs(os.path.join(elsewhere, "entries"))
            with open(os.path.join(elsewhere, "entries", "2026-01-widget-sorter.md"), "w", encoding="utf-8") as f:
                f.write("---\norg: Korvane\n---\n")
            saved = os.getcwd()
            try:
                os.chdir(elsewhere)
                outs = []
                for rel in ("entries/2026-01-widget-sorter.md", "entries/2026-08-kite.md", "entries/no.md"):
                    out = io.StringIO()
                    with redirect_stdout(out):
                        outs.append((deny_coverage.main(["deny_coverage.py", "entry", "--root", root, rel]),
                                     out.getvalue()))
            finally:
                os.chdir(saved)
        self.assertEqual(outs, [(0, "Korvane\n"),
                                (0, "Brindlewood[^[:alnum:]]*Kite[^[:alnum:]]*Map\n"),
                                (2, "FAIL: no entries/no.md\n")])

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
                     ["entry", "--help"], ["entry", "--commit", "--help"], ["clear", "--help"]):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = deny_coverage.main(["deny_coverage.py"] + args)
            self.assertEqual((rc, out.getvalue().splitlines()), (0, deny_coverage.__doc__.splitlines()), args)

    def test_empty_log_passes(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, ".export-deny"), "w", encoding="utf-8") as f:
                f.write("Someone\n")
            self.assertEqual(run(root), (0, "OK: .export-deny covers 0 recorded names\n"))


    def test_any_console_prints_names(self):
        # A console whose code page lacks a name's characters (cp1252) still gets the whole list.
        with tempfile.TemporaryDirectory() as root:
            make_log(root, deny=DENY_ALL + "\n", cleared="Career fair\npage\n")
            entry = os.path.join(root, "entries", "2026-07-kite.md")
            with open(entry, "w", encoding="utf-8") as f:
                f.write("---\norg: 風箏工作室\n---\n")
            stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
            saved, sys.stdout = sys.stdout, stream
            try:
                rc = deny_coverage.main(["deny_coverage.py", "--root", root])
                stream.flush()
            finally:
                sys.stdout = saved
        self.assertEqual(rc, 1)
        self.assertIn("  風箏工作室    (entries/2026-07-kite.md)", stream.buffer.getvalue().decode("utf-8"))


HAS_GIT = shutil.which("git") is not None


@unittest.skipUnless(HAS_GIT, "needs git")
class Commits(unittest.TestCase):
    """--commit and clear, in a clone whose origin is a bare repo."""

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
        self.write(".export-deny", "# names\nSomeone\nWidget\n")
        self.write("entries/2026-02-kite.md", "---\ntitle: Kite\norg: Kestrelby\n---\n")
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

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as f:
            return f.read()

    def tool(self, *args, root=None):
        p = subprocess.run([sys.executable, "-I", TOOL, "--root", root or self.root] + list(args),
                           capture_output=True, encoding="utf-8", env=self.env)
        return p.returncode, p.stdout

    def log(self, n):
        """The last n commits: [(subject, [files])], newest first."""
        out = self.git(self.root, "log", "-n", str(n), "--format=@%s", "--name-only")
        commits = []
        for block in out.split("@")[1:]:
            subject, *files = [l for l in block.splitlines() if l]
            commits.append((subject, files))
        return commits

    def pushed(self):
        return self.git(self.root, "rev-list", "--count", "origin/master..HEAD").strip() == "0"

    def push_from_another_clone(self):
        other = self.clone("other")
        self.write("README.md", "# Log\n\nother\n", root=other)
        self.git(other, "commit", "-q", "-am", "other")
        self.git(other, "push", "-q", "origin", "master")

    def test_entry_commit_commits_only_the_deny_file(self):
        self.write("README.md", "# Log\n\nstaged\n")
        self.git(self.root, "add", "README.md")
        rc, out = self.tool("entry", "--commit", os.path.join(self.root, "entries", "2026-02-kite.md"))
        self.assertEqual(rc, 0, out)
        lines = out.splitlines()
        self.assertEqual(lines[0], "Kestrelby")
        self.assertRegex(lines[1], r"^committed: \[master [0-9a-f]+\] export-deny: names from 2026-02-kite\.md$")
        self.assertEqual(lines[-1], "sync: ok")
        self.assertEqual(self.log(1), [("export-deny: names from 2026-02-kite.md", [".export-deny"])])
        self.assertTrue(self.pushed())
        self.assertEqual(self.git(self.root, "status", "--short"), "M  README.md\n")
        self.assertTrue(self.read(".export-deny").endswith("Widget\nKestrelby\n"))

    def test_entry_commit_subject_for_many_entries(self):
        paths = []
        for i, org in enumerate(("Aldermoor", "Brackwater", "Cindervale", "Dunmerrow")):
            rel = "entries/2026-0%d-e%d.md" % (i + 3, i)
            self.write(rel, "---\norg: %s\n---\n" % org)
            paths.append(os.path.join(self.root, rel))
        rc, out = self.tool("entry", "--commit", *paths)
        self.assertEqual((rc, out.splitlines()[-1]), (0, "sync: ok"), out)
        self.assertEqual(self.log(1)[0][0], "export-deny: names from 4 entries")

    def test_entry_commit_with_nothing_to_add(self):
        self.write("entries/2026-02-kite.md", "---\norg: Widget\n---\n")
        before = self.git(self.root, "rev-parse", "HEAD")
        rc, out = self.tool("entry", "--to", os.path.join(self.root, ".export-deny"), "--commit",
                            os.path.join(self.root, "entries", "2026-02-kite.md"))
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("OK: "), out)
        self.assertNotIn("sync:", out)
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), before)

    def test_entry_commit_stops_as_sync_does(self):
        # No repo-local identity: sync.py refuses, and its next: stop: line is the last.
        bare = self.clone("noid", identity=False)
        rc, out = self.tool("entry", "--commit", os.path.join(bare, "entries", "2026-02-kite.md"), root=bare)
        self.assertEqual(rc, 1)
        self.assertTrue(out.splitlines()[-1].startswith("next: stop:"), out)
        # A push origin refuses: another clone pushed first.
        self.push_from_another_clone()
        rc, out = self.tool("entry", "--commit", os.path.join(self.root, "entries", "2026-02-kite.md"))
        self.assertEqual(rc, 1)
        self.assertIn("push: refused", out)
        self.assertTrue(out.splitlines()[-1].startswith("next: stop:"), out)

    def test_commit_needs_the_roots_deny_file(self):
        elsewhere = os.path.join(self.tmp, "deny")
        self.write("deny", "Someone\n", root=self.tmp)
        for args in (["entry", "--to", elsewhere, "--commit", os.path.join(self.root, "entries", "2026-02-kite.md")],
                     ["line", "--commit", "--to", elsewhere, "Kestrelby"]):
            rc, out = self.tool(*args)
            self.assertEqual(rc, 2, args)
            self.assertTrue(out.startswith("usage: "), out)

    def test_line_commit(self):
        rc, out = self.tool("line", "--commit", "Kestrelby", "Q&R Partners")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.splitlines()[:2], ["Kestrelby", "Q[^[:alnum:]]+R[^[:alnum:]]+Partners"])
        self.assertEqual(self.log(1), [("export-deny: add Kestrelby, Q&R Partners", [".export-deny"])])
        self.assertTrue(self.pushed())

    def test_clear_two_commits_cleared_first(self):
        self.write("entries/2026-02-kite.md", "---\norg: Widget\n---\n")
        self.git(self.root, "commit", "-q", "-am", "widget")
        self.git(self.root, "push", "-q", "origin", "master")
        rc, out = self.tool("clear", "Widget")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.splitlines()[-1], "sync: ok")
        self.assertEqual(self.log(2), [("export-deny: clear Widget", [".export-deny"]),
                                       ("export-cleared: Widget", [".export-cleared"])])
        self.assertTrue(self.pushed())
        self.assertEqual(self.read(".export-deny"), "# names\nSomeone\n")
        self.assertEqual(self.read(".export-cleared"), "Widget\n")
        self.assertEqual(self.tool(), (0, "OK: .export-deny covers 1 recorded names\n"))

    def test_clear_takes_the_deny_line_and_notes_another_match(self):
        self.write(".export-deny", "Kite[^[:alnum:]]*Works\nKite\n")
        self.write(".export-cleared", "# cleared\nSomething")   # no line end at the end
        self.git(self.root, "add", "-A")
        self.git(self.root, "commit", "-q", "-m", "lines")
        rc, out = self.tool("clear", "Kite Works")
        self.assertEqual(rc, 0, out)
        self.assertIn("note: .export-deny still has Kite, which the export's scan matches against 'Kite Works' too\n",
                      out)
        self.assertEqual(self.read(".export-deny"), "Kite\n")
        self.assertEqual(self.read(".export-cleared"), "# cleared\nSomething\nKite Works\n")

    def test_clear_a_name_with_no_line_changes_nothing(self):
        before = self.git(self.root, "rev-parse", "HEAD")
        rc, out = self.tool("clear", "Widget Labs")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "FAIL: no .export-deny line is 'Widget Labs' or its deny: line"
                              " 'Widget[^[:alnum:]]*Labs'; the lines that match it: Widget. Nothing was changed.\n")
        self.assertFalse(os.path.exists(os.path.join(self.root, ".export-cleared")))
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(self.tool("clear", "Kestrelbyy"),   # a typo: no line, and no such recorded name
                         (2, "FAIL: no .export-deny line is 'Kestrelbyy' or its deny: line 'Kestrelbyy', and the Log"
                             " records no such name. Nothing was changed.\n"))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".export-cleared")))
        for args in (["clear"], ["clear", "a", "b"], ["clear", "-x"], ["clear", " "]):
            self.assertEqual(self.tool(*args)[0], 2, args)

    def test_clear_leaves_the_deny_line_when_the_first_push_fails(self):
        self.push_from_another_clone()
        rc, out = self.tool("clear", "Widget")
        self.assertEqual(rc, 1)
        self.assertIn("push: refused", out)
        self.assertNotIn("export-deny: clear", out)
        self.assertEqual(self.read(".export-deny"), "# names\nSomeone\nWidget\n")
        self.assertEqual(self.log(1)[0], ("export-cleared: Widget", [".export-cleared"]))

    def test_fail_prints_run_lines_that_pass(self):
        self.write("entries/2026-02-kite.md", "---\norg: Kestrelby & Sons, Marrowgate\n---\n")
        os.makedirs(os.path.join(self.root, "outputs", "applications", "2026-03-01-tallowmere-analyst"))
        self.git(self.root, "commit", "-q", "-am", "names")
        self.git(self.root, "push", "-q", "origin", "master")
        rc, out = self.tool()
        self.assertEqual(rc, 1, out)
        runs = [l[len("run: "):] for l in out.splitlines() if l.startswith("run: ")]
        self.assertEqual(len(runs), 2, out)
        self.assertNotIn("tallowmere", runs[0])
        self.assertIn("'<employer>'   (for each folder: tallowmere-analyst)", runs[1])
        self.assertIn(" clear '<name>'", out)
        # Every line not about a name is unindented: the upgrade guide counts the indented ones.
        self.assertEqual(sum(l.startswith("  ") for l in out.splitlines()), 3)
        words = shlex.split(runs[0])
        words = [sys.executable] + words[words.index("-I"):]
        p = subprocess.run(words, capture_output=True, encoding="utf-8", env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(self.log(1), [("export-deny: add Kestrelby & Sons, Marrowgate", [".export-deny"])])
        self.assertEqual(self.tool("line", "--commit", "Tallowmere")[0], 0)
        self.assertEqual(self.tool(), (0, "OK: .export-deny covers 3 recorded names\n"))

    def test_clear_keeps_other_names_covered(self):
        # Kestrelby Labs was covered only by the Kestrelby line the user clears: it gets its own line.
        self.write(".export-deny", "Someone\nKestrelby\n")
        self.write("entries/2026-02-kite.md", "---\norg: Kestrelby, Kestrelby Labs\n---\n")
        self.git(self.root, "commit", "-q", "-am", "names")
        self.git(self.root, "push", "-q", "origin", "master")
        rc, out = self.tool("clear", "Kestrelby")
        self.assertEqual(rc, 0, out)
        self.assertIn("kept covered: Kestrelby[^[:alnum:]]*Labs\n", out)
        self.assertEqual(self.read(".export-deny"), "Someone\nKestrelby[^[:alnum:]]*Labs\n")
        self.assertEqual(self.tool(), (0, "OK: .export-deny covers 2 recorded names\n"))

    def test_clear_again_finishes_a_stopped_clear(self):
        # The .export-deny commit was made but its push refused: clear again pushes it.
        self.write("entries/2026-02-kite.md", "---\norg: Widget\n---\n")
        self.git(self.root, "commit", "-q", "-am", "widget")
        self.git(self.root, "push", "-q", "origin", "master")
        self.write(".export-cleared", "Widget\n")
        self.write(".export-deny", "# names\nSomeone\n")
        self.git(self.root, "add", "-A")
        self.git(self.root, "commit", "-q", "-m", "export-cleared: Widget")
        rc, out = self.tool("clear", "Widget")
        self.assertEqual(rc, 0, out)
        self.assertIn("commit: nothing to commit", out)
        self.assertEqual(out.splitlines()[-1], "sync: ok")
        self.assertTrue(self.pushed())

    def test_line_commit_with_nothing_new(self):
        before = self.git(self.root, "rev-parse", "HEAD")
        rc, out = self.tool("line", "--commit", "Widget")
        self.assertEqual((rc, out), (0, "Widget\nOK: .export-deny has every line already; nothing to commit\n"))
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(self.tool("line", "--to", "", "Widget")[0], 2)

    def test_run_line_quotes_apostrophes_for_every_shell(self):
        self.write("entries/2026-02-kite.md", "---\norg: Brannock's Mill, Ferrow’s Yard\n---\n")
        self.git(self.root, "commit", "-q", "-am", "names")
        self.git(self.root, "push", "-q", "origin", "master")
        rc, out = self.tool()
        self.assertEqual(rc, 1, out)
        run = [l[len("run: "):] for l in out.splitlines() if l.startswith("run: ")][0]
        self.assertTrue(run.endswith(''' line --commit "Brannock's Mill" "Ferrow’s Yard"'''), run)
        args = run.split(" line --commit ", 1)[1]
        shells = [[s, "-c", "echo " + args] for s in ("sh",) if shutil.which(s)]
        shells += [[s, "-NoProfile", "-Command", "[Console]::OutputEncoding = [Text.Encoding]::UTF8; echo " + args]
                   for s in ("pwsh", "powershell") if shutil.which(s)]
        for shell in shells:
            p = subprocess.run(shell, capture_output=True, encoding="utf-8", env=self.env)
            self.assertEqual(p.stdout.split(), ["Brannock's", "Mill", "Ferrow’s", "Yard"], (shell[0], p.stdout, p.stderr))
        self.assertEqual(self.tool("line", "--commit", "Brannock's Mill", "Ferrow’s Yard")[0], 0)
        self.assertEqual(self.tool(), (0, "OK: .export-deny covers 2 recorded names\n"))

    def test_clear_does_not_deny_the_name_again(self):
        # Widget! keeps its `!`, and its deny: line (Widget) would match the cleared name: a note, no line.
        self.write("entries/2026-02-kite.md", "---\norg: Widget!\n---\n")
        self.git(self.root, "commit", "-q", "-am", "widget")
        self.git(self.root, "push", "-q", "origin", "master")
        rc, out = self.tool("clear", "Widget")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("kept covered:", out)
        self.assertIn("note: 'Widget!' is no longer covered, and its deny: line would match 'Widget': ask the user"
                      " whether to clear it too (clear 'Widget!')\n", out)
        self.assertEqual(self.read(".export-deny"), "# names\nSomeone\n")
        rc, out = self.tool("clear", "Widget!")   # the note's command, on the user's yes
        self.assertEqual((rc, out.splitlines()[-1]), (0, "sync: ok"), out)
        self.assertEqual(self.log(1), [("export-cleared: Widget!", [".export-cleared"])])
        self.assertEqual(self.read(".export-cleared"), "Widget\nWidget!\n")
        self.assertEqual(self.tool(), (0, "OK: .export-deny covers 1 recorded names\n"))

    def test_clear_twice_changes_nothing(self):
        self.assertEqual(self.tool("clear", "Widget")[0], 0)
        head = self.git(self.root, "rev-parse", "HEAD")
        self.assertEqual(self.tool("clear", "Widget"),
                         (0, "OK: Widget is in .export-cleared and has no .export-deny line; nothing to commit\n"))
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), head)

if __name__ == "__main__":
    unittest.main()
