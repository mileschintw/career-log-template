#!/usr/bin/env python3
"""Tests for tools/entries.py, on small made-up Logs built in a temporary directory.

  python3 -I tools/tests/test_entries.py
"""
import datetime, importlib.util, io, os, re, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "entries.py")
spec = importlib.util.spec_from_file_location("entries", TOOL)
entries = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entries)

TODAY = "2031-06-15"


def entry(title="Widget Sorter", period="2031-01 – 2031-03", tags="[go, kafka]", series=None,
          one_line="Sorted widgets.", last_updated="2031-03-01", links="[]", type_="project", body=""):
    return ("---\ntitle: %s\ntype: %s\nperiod: %s\norg: personal\n%stags: %s\nlinks: %s\nlast_updated: %s\n---\n\n"
            "# %s\n\n## One line\n<!-- a comment -->\n%s\n\n## Context\n%s\n"
            % (title, type_, period, "series: %s\n" % series if series else "", tags, links, last_updated,
               title, one_line, body))


def row(path, title="Widget Sorter", period="2031-01 – 2031-03", tags="go, kafka", status="consolidated",
        type_="project"):
    return "| %s | [%s](%s) | %s | %s | %s |\n" % (period, title, path, type_, tags, status)


README_HEAD = "# Log\n\n## Entries\n\n| Period | Entry | Type | Tags | Status |\n|---|---|---|---|---|\n"


class Log(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "entries"))
        self.write("entries/_template.md", entry(title="", period="YYYY-MM – YYYY-MM"))

    def write(self, path, text, mode="w"):
        full = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if "b" in mode:
            with open(full, mode) as f:
                f.write(text)
        else:
            with open(full, mode, encoding="utf-8", newline="") as f:
                f.write(text)

    def run_tool(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = entries.main(list(args))
        return code, out.getvalue().splitlines()

    def check(self):
        return self.run_tool("check", "--root", self.root, "--today", TODAY)

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "-c", "commit.gpgsign=false"] + list(args), check=True, capture_output=True)


class ReadingTest(Log):
    def test_entry_paths(self):
        self.write("entries/2031-01-widget.md", entry())
        self.write("entries/notes.txt", "x")
        self.write("entries/old/2030-01-nested.md", entry())
        self.assertEqual(entries.entry_paths(self.root), ["entries/2031-01-widget.md"])
        self.assertEqual(entries.entry_paths(os.path.join(self.root, "missing")), [])

    def test_entry_path_pattern(self):
        for path in ("entries/2031-01-widget.md", "entries/_notes.md", "entries/2031-02-新.md"):
            self.assertTrue(entries.ENTRY_PATH.fullmatch(path), path)
        for path in ("entries/_template.md", "entries/a/b.md", "outputs/entries/x.md", "entries/x.txt"):
            self.assertFalse(entries.ENTRY_PATH.fullmatch(path), path)

    def test_front_matter_forms(self):
        text = ("﻿---\r\ntitle: \"Dual-Path Sorter\"   # quoted\r\nperiod: 2031-01 – ongoing  # or not\r\n"
                "tags: [go, 'rust']\r\nlinks:\r\n  - https://example.org/a#frag\r\n  - https://example.org/b  # b\r\n"
                "org:\r\n---\r\nbody\r\n")
        fields = entries.front_matter(text.lstrip("﻿"))
        self.assertEqual(fields["title"], "Dual-Path Sorter")
        self.assertEqual(fields["period"], "2031-01 – ongoing")
        self.assertEqual(fields["tags"], ["go", "rust"])
        self.assertEqual(fields["links"], ["https://example.org/a#frag", "https://example.org/b"])
        self.assertEqual(fields["org"], "")
        quoted = entries.front_matter('---\ntitle: "C# and F# # notes"  # a comment\ntags: [a, b]  # c\n---\n')
        self.assertEqual(quoted["title"], "C# and F# # notes")
        self.assertEqual(quoted["tags"], ["a", "b"])
        odd = entries.front_matter('---\ntitle: [WIP] Widget\ntags: [a, "b, c"]\n---\n')
        self.assertEqual(odd["title"], "[WIP] Widget")
        self.assertEqual(odd["tags"], ["a", "b, c"])
        self.write("entries/2031-01-bom.md", text)
        e = entries.Entry(self.root, "entries/2031-01-bom.md")
        self.assertTrue(e.ongoing)
        self.assertEqual(e.slug, "bom")

    def test_tokens(self):
        self.assertEqual(entries.tokens(""), 0)
        self.assertEqual(entries.tokens("a" * 27), 10)
        self.assertEqual(entries.tokens("中文字"), 4)
        self.assertEqual(entries.tokens("a" * 27 + "中文字"), 14)

    def test_periods(self):
        self.assertEqual(entries.parse_period("2031-01 – 2031-03"), ("2031-01", "2031-03"))
        self.assertEqual(entries.parse_period("2031-01-05 - ongoing"), ("2031-01-05", None))
        self.assertIsNone(entries.parse_period("2031-01-05 – 2031-01-04"))
        self.assertEqual(entries.parse_period("2031-01-05 – 2031-01"), ("2031-01-05", "2031-01"))
        self.assertEqual(entries.parse_period("2031-04"), ("2031-04", "2031-04"))
        self.assertIsNone(entries.parse_period("GAP: when?"))
        self.assertEqual(entries.parse_period("2031-01 – Ongoing"), ("2031-01", None))
        self.assertIsNone(entries.parse_period("2031-05 – 2031-01"))

    def test_links(self):
        text = ("[w](https://en.example.org/wiki/Foo_(bar)) and (see https://example.org/x). "
                "<https://example.org/y> [n](../sources/n.md) [a](#anchor) https://example.org/x")
        self.assertEqual(entries.links(text), ["https://en.example.org/wiki/Foo_(bar)", "https://example.org/x",
                                               "https://example.org/y", "../sources/n.md"])


class ListTest(Log):
    def setUp(self):
        super().setUp()
        self.write("entries/2031-01-widget.md", entry(series="widget", period="2031-01 – 2031-03"))
        self.write("entries/2031-04-widget-2.md", entry(series="widget", period="2031-04 – ongoing",
                                                        one_line="Sorted more widgets."))
        self.write("entries/2030-05-lamp.md", entry(title="Lamp Fixer", period="2030-05 – 2030-06"))
        self.write("README.md", README_HEAD + row("entries/2031-01-widget.md", status="imported (gaps)"))

    def test_list_lines(self):
        code, lines = self.run_tool("list", "--root", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].split(":")[0], "entries/2030-05-lamp.md")
        widget = lines[1]
        for part in ("slug widget;", "series widget;", "type project;", "org personal;",
                     "period 2031-01 – 2031-03;", "tags go, kafka;", "status imported (gaps);",
                     "one line: Sorted widgets."):
            self.assertIn(part, widget)
        self.assertIn("period 2031-04 – ongoing (ongoing);", lines[2])
        self.assertIn("status - (no README row);", lines[2])
        self.assertNotIn("over threshold", widget)

    def test_list_series(self):
        code, lines = self.run_tool("list", "--root", self.root, "--series", "widget")
        self.assertEqual([l.split(":")[0] for l in lines], ["entries/2031-01-widget.md", "entries/2031-04-widget-2.md",
                                                           "series widget"])

    def test_list_marks_over_threshold(self):
        self.write("entries/2030-05-lamp.md", entry(title="Lamp Fixer", body="x" * 40000))
        _, lines = self.run_tool("list", "--root", self.root)
        self.assertRegex(lines[0], r"tokens \d+ \(over threshold\);")


class CheckTest(Log):
    def clean(self):
        self.write("entries/2031-01-widget.md", entry(series="widget"))
        self.write("entries/2031-04-widget-2.md", entry(series="widget", period="2031-03 – ongoing",
                                                        last_updated="2031-05-01"))
        self.write("README.md", README_HEAD + row("entries/2031-01-widget.md")
                   + row("entries/2031-04-widget-2.md", period="2031-03 – ongoing"))

    def test_clean_log(self):
        self.clean()   # the parts share 2031-03: a split in that month, not an overlap
        self.assertEqual(self.check(), (0, ["OK: 2 entries, no findings"]))

    def test_empty_log(self):
        self.assertEqual(self.check(), (0, ["OK: 0 entries, no findings"]))

    def test_over_threshold(self):
        self.clean()
        self.write("entries/2031-01-widget.md", entry(series="widget", body="中" * 9400))
        code, lines = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["entry over threshold: entries/2031-01-widget.md %d tokens"
                                 % entries.tokens(entry(series="widget", body="中" * 9400))])

    def test_series_findings(self):
        self.clean()
        self.write("entries/2031-04-widget-2.md", entry(series="widget", period="2031-02 – ongoing", one_line=""))
        self.write("entries/2031-05-widget-3.md", entry(series="widget", period="2031-05 – ongoing"))
        self.write("entries/2031-06-gadget-2.md", entry(series="gadget", period="sometime"))
        self.write("README.md", README_HEAD + row("entries/2031-01-widget.md")
                   + row("entries/2031-04-widget-2.md", period="2031-02 – ongoing")
                   + row("entries/2031-05-widget-3.md", period="2031-05 – ongoing")
                   + row("entries/2031-06-gadget-2.md", period="sometime"))
        code, lines = self.check()
        self.assertEqual(code, 1)
        self.assertIn("series part with an unreadable period: entries/2031-06-gadget-2.md 'sometime'"
                      " (YYYY-MM – YYYY-MM or YYYY-MM – ongoing)", lines)
        self.assertIn("series names no entry: entries/2031-06-gadget-2.md series gadget", lines)
        self.assertIn("series part with an empty One line: entries/2031-04-widget-2.md", lines)
        self.assertIn("series widget has more than one ongoing part: entries/2031-04-widget-2.md,"
                      " entries/2031-05-widget-3.md", lines)
        overlaps = [l for l in lines if "overlapping" in l]
        self.assertEqual(len(overlaps), 2, lines)   # 01-03 with 02-ongoing; 02-ongoing with 05-ongoing
        self.assertIn("series widget has overlapping periods: entries/2031-01-widget.md (2031-01 – 2031-03),"
                      " entries/2031-04-widget-2.md (2031-02 – ongoing)", lines)

    def test_series_periods_with_days(self):
        # three parts within one month: by day they only meet, so no overlap
        self.write("entries/2031-01-widget.md", entry(series="widget", period="2031-01-12 – 2031-01-15"))
        self.write("entries/2031-01-widget-b.md", entry(series="widget", period="2031-01-16 – 2031-01-19"))
        self.write("entries/2031-01-widget-c.md", entry(series="widget", period="2031-01-19 – ongoing",
                                                        last_updated="2031-01-20"))
        self.write("README.md", README_HEAD
                   + row("entries/2031-01-widget.md", period="2031-01-12 – 2031-01-15")
                   + row("entries/2031-01-widget-b.md", period="2031-01-16 – 2031-01-19")
                   + row("entries/2031-01-widget-c.md", period="2031-01-19 – ongoing"))
        self.assertEqual(self.run_tool("check", "--root", self.root, "--today", "2031-01-20"), (0, ["OK: 3 entries, no findings"]))
        self.write("entries/2031-01-widget-b.md", entry(series="widget", period="2031-01-14 – 2031-01-19"))
        _, lines = self.run_tool("check", "--root", self.root, "--today", "2031-01-20")
        self.assertEqual([l for l in lines if "overlapping" in l],
                         ["series widget has overlapping periods: entries/2031-01-widget-b.md"
                          " (2031-01-14 – 2031-01-19), entries/2031-01-widget.md (2031-01-12 – 2031-01-15)"])
        # a period with days against one without is compared by month
        self.write("entries/2031-01-widget-b.md", entry(series="widget", period="2031-01 – 2031-01"))
        _, lines = self.run_tool("check", "--root", self.root, "--today", "2031-01-20")
        self.assertEqual(len([l for l in lines if "overlapping" in l]), 2, lines)

    def test_readme_findings(self):
        self.write("entries/2031-01-widget.md", entry())
        self.write("entries/2031-02-lamp.md", entry(title="Lamp Fixer"))
        self.write("entries/2031-03-gear.md", entry(title="Gear Cutter | v2"))
        self.write("README.md", README_HEAD
                   + row("entries/2031-01-widget.md", title="Widget Sorter (old)", period="2031-01 - 2031-04",
                         tags="go, redis", status="done", type_="work")
                   + row("entries/2031-09-gone.md")
                   + row("./entries/2031-03-gear.md#context", title="Gear Cutter \\| v2", tags="go"))
        code, lines = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(sorted(lines), sorted([
            "README row names a missing file: entries/2031-09-gone.md",
            "no README row: entries/2031-02-lamp.md",
            "README row differs: entries/2031-01-widget.md: title 'Widget Sorter (old)', front matter 'Widget Sorter'",
            "README row differs: entries/2031-01-widget.md: period '2031-01 - 2031-04', front matter '2031-01 – 2031-03'",
            "README row differs: entries/2031-01-widget.md: type 'work', front matter 'project'",
            "README row differs: entries/2031-01-widget.md: tags not in front matter: redis",
            "README row status unknown: entries/2031-01-widget.md 'done' (starts with stub, imported, consolidated)",
        ]))

    def test_stale_ongoing(self):
        self.write("entries/2031-01-widget.md", entry(period="2030-01 – ongoing", last_updated="2031-04-14"))
        self.write("entries/2031-02-lamp.md", entry(title="Lamp Fixer", period="2030-01 – ongoing",
                                                    last_updated="2031-04-15"))
        self.write("entries/2031-03-gear.md", entry(title="Gear Cutter", period="2030-01 – ongoing",
                                                    last_updated="YYYY-MM-DD"))
        self.write("entries/2031-04-old.md", entry(title="Old", period="2020-01 – 2020-02", last_updated="2020-02-01"))
        self.write("README.md", README_HEAD + "".join(
            row(p, title=t, period=pd) for p, t, pd in [
                ("entries/2031-01-widget.md", "Widget Sorter", "2030-01 – ongoing"),
                ("entries/2031-02-lamp.md", "Lamp Fixer", "2030-01 – ongoing"),
                ("entries/2031-03-gear.md", "Gear Cutter", "2030-01 – ongoing"),
                ("entries/2031-04-old.md", "Old", "2020-01 – 2020-02")]))
        code, lines = self.check()
        self.assertEqual(lines, [
            "ongoing entry not updated in over two months: entries/2031-01-widget.md last_updated 2031-04-14",
            "ongoing entry with no readable last_updated: entries/2031-03-gear.md 'YYYY-MM-DD'"])

    def test_months_before(self):
        self.assertEqual(entries.months_before(datetime.date(2031, 4, 30), 2), datetime.date(2031, 2, 28))
        self.assertEqual(entries.months_before(datetime.date(2031, 1, 10), 2), datetime.date(2030, 11, 10))

    def test_gap_ongoing_is_stale_too(self):
        """A stub log wrote with an unknown start month is ongoing for the staleness check."""
        self.write("entries/2031-01-widget.md", entry(period="GAP – ongoing", last_updated="2031-01-02"))
        self.write("README.md", README_HEAD + row("entries/2031-01-widget.md", period="GAP – ongoing"))
        self.assertEqual(self.check()[1], [
            "ongoing entry not updated in over two months: entries/2031-01-widget.md last_updated 2031-01-02"])
        _, lines = self.run_tool("list", "--root", self.root)
        self.assertNotIn("(ongoing)", lines[0])   # list's output, and so scan's Screen key, stay as they were


W_PATH = "entries/2031-01-widget.md"


class ShapeTest(Log):
    """The checks of an entry's shape: one entry with a README row, so every line is about its shape."""

    def shape(self, body="", **fields):
        self.write(W_PATH, entry(body=body, **fields))
        self.write("README.md", README_HEAD + row(W_PATH, period=fields.get("period", "2031-01 – 2031-03")))
        return self.check()

    def test_a_clean_entry(self):
        body = ("\n## Results and evidence\n| Metric | Value | How measured | Caveat | Source |\n|---|---|---|---|---|\n"
                "| p95 | 210 ms | load test | one run | sources/x.md |\n| errors | GAP: rate | GAP: how | GAP | GAP |\n"
                "\n## Past phrasings\n<!-- a comment -->\n- none yet\n"
                "\n## Conflicts\n- Open: \"a\" (x) vs \"b\" (y)\n"
                "- Settled: use \"820 ms\", not \"800 ms\" (the log says 820). (sources/x.md)\n"
                "- Settled: both \"A\" and \"B\" are right (both hold). (sources/x.md)\n"
                "- Settled: do not use \"beat Y\" (no run shows it). (sources/x.md)\n"
                "\n## Pending\n- 2031-06-01: a fact. https://example.org/pr/1\n")
        self.write("sources/x.md", "x")
        self.assertEqual(self.shape(body, last_updated="GAP: when"), (0, ["OK: 1 entries, no findings"]))

    def test_front_matter(self):
        code, lines = self.shape(type_="work | internship", period="2031-01 – 2031-03 (a note)",
                                 last_updated="2031-13-01")
        self.assertEqual(code, 1)
        self.assertIn("front matter: %s type 'work | internship' not allowed (%s)" % (W_PATH, " | ".join(entries.TYPES)),
                      lines)
        self.assertIn("front matter: %s last_updated '2031-13-01' not allowed (YYYY-MM-DD)" % W_PATH, lines)
        self.assertIn("front matter: %s period '2031-01 – 2031-03 (a note)' not allowed (YYYY-MM – YYYY-MM or"
                      " YYYY-MM – ongoing)" % W_PATH, lines)
        # GAP forms pass in every field, and a period may give GAP for one end
        for period in ("GAP", "GAP – 2031-03", "2031-01 – GAP", "GAP: when?"):
            self.write(W_PATH, entry(period=period, type_="GAP: which"))
            self.assertEqual([l for l in self.check()[1] if l.startswith("front matter")], [], period)
        self.write(W_PATH, entry().replace("org: personal", "visibility: secret  # a comment"))
        self.assertIn("front matter: %s visibility 'secret' not allowed (public | private | nda | GAP)" % W_PATH,
                      self.check()[1])

    def test_list_values(self):
        # a field that takes one value, given as a list (inline or block): a finding, no crash
        one = "YYYY-MM – YYYY-MM or YYYY-MM – ongoing"
        for field, text, value, allowed in [
                ("period", "[2031-01, 2031-02]", ["2031-01", "2031-02"], one),
                ("period", "\n  - 2031-01\n  - 2031-02", ["2031-01", "2031-02"], one),
                ("series", "[widget, lamp]", ["widget", "lamp"], "one slug"),
                ("series", "\n  - widget", ["widget"], "one slug"),
                ("last_updated", "[2031-03-01, 2031-04-01]", ["2031-03-01", "2031-04-01"], "YYYY-MM-DD"),
                ("last_updated", "\n  - 2031-03-01",["2031-03-01"], "YYYY-MM-DD")]:
            fields = {field: text}
            code, lines = self.shape(**fields)
            self.assertEqual(code, 1, (field, text))
            self.assertIn("front matter: %s %s %r not allowed (%s)" % (W_PATH, field, value, allowed), lines)
            code, lines = self.run_tool("list", "--root", self.root)
            self.assertEqual(code, 0)
            self.assertIn("series -;", lines[0])
            if field == "period":
                self.assertIn("period -;", lines[0])
        self.assertEqual(self.shape(series="[]"), (0, ["OK: 1 entries, no findings"]))
        # an ongoing entry's list last_updated is the staleness line's
        code, lines = self.shape(period="2031-01 – ongoing", last_updated="[2031-05-01]")
        self.assertIn("ongoing entry with no readable last_updated: %s ['2031-05-01']" % W_PATH, lines)
        self.assertFalse([l for l in lines if l.startswith("front matter")], lines)

    def test_links(self):
        links = ("[https://github.com/o/r, https://github.com/o/r/pull/3, https://gitlab.example.org/g/s/r/-/issues/2,"
                 " https://example.org/talk]")
        self.assertEqual(self.shape(links=links)[1], [
            "link not a repo root: %s https://github.com/o/r/pull/3; root https://github.com/o/r" % W_PATH,
            "link not a repo root: %s https://gitlab.example.org/g/s/r/-/issues/2; root https://gitlab.example.org/g/s/r,"
            " missing from links" % W_PATH])

    def test_old_section_and_pending(self):
        body = "\n## Log\n- 2020-01-01 an old line\n\n## Pending\n- 2031-04-14: old.\n- 2031-04-15: new.\n- no date\n"
        self.assertEqual(self.shape(body)[1], [
            "old section ## Log: %s (read `tools/entries.py --help` › Old sections before you edit it)" % W_PATH,
            "pending older than two months: %s:23: - 2031-04-14: old." % W_PATH,
            "pending line without a date: %s:25: - no date" % W_PATH])

    def test_conflicts(self):
        body = ("\n## Conflicts\n- Settled: use \"A\", not \"B\" (why).\n  - version 1 (src)\n"
                "- Title: \"A\" vs \"B\"\n- Settled: use the names (why). (src)\nnone\n")
        self.assertEqual(self.shape(body)[1], [
            "conflict line not Open or Settled: %s:21: - version 1 (src)" % W_PATH,
            "conflict line not Open or Settled: %s:22: - Title: \"A\" vs \"B\"" % W_PATH,
            "settled line not in a template form: %s:23: Settled: use the names (why). (src)" % W_PATH])
        # profile.md's ### Conflicts too
        self.write("profile.md", "# Profile\n\n### Conflicts\n- a line\n\n## Skills summary\n- not a conflict\n")
        self.write(W_PATH, entry())
        self.assertEqual(self.check()[1], ["conflict line not Open or Settled: profile.md:4: - a line"])

    def test_past_phrasings(self):
        os.makedirs(os.path.join(self.root, "outputs", "resumes"))
        self.write("outputs/resumes/backend.tex", "x")
        body = ("\n## Past phrasings\n- **backend:** \"Cut p95 to 210 ms\" (outputs/resumes/backend.tex, 2031-03-02)\n"
                "- **general:** \"**Queues:** Built a queue\" (sources/resumes/cv.tex)\n"
                "**backend:**\n- Built a cache (sources/resumes/cv.tex)\n"
                "- **frontend:** \"Drew a page\" (sources/resumes/cv.tex)\n"
                "- **general:** \"Sorted\" (sources/resumes/cv.tex; sent to Acme)\n"
                "- **general:** \"Sorted\" (sources/resumes/cv.tex) for Acme\n")
        self.write("sources/resumes/cv.tex", "x")
        self.assertEqual(self.shape(body)[1], [
            "past phrasing not in form: %s:22: **backend:**" % W_PATH,
            "past phrasing not in form: %s:23: - Built a cache (sources/resumes/cv.tex)" % W_PATH,
            "past phrasing angle unknown: %s:24 frontend (general, or a target in outputs/resumes/: backend)" % W_PATH,
            "past phrasing with more than one citation or a note: %s:25: (sources/resumes/cv.tex; sent to Acme)" % W_PATH,
            "past phrasing not in form: %s:26: - **general:** \"Sorted\" (sources/resumes/cv.tex) for Acme" % W_PATH])

    def test_results_rows(self):
        body = ("\n## Results and evidence\n| Metric | Value | How measured | Caveat | Source |\n|---|---|---|---|---|\n"
                "| p95 | 210 ms | load test |  | sources/x.md |\n| users | 40 | | | |\n")
        self.write("sources/x.md", "x")
        self.assertEqual(self.shape(body)[1], [
            "results row missing caveat: %s:22 p95" % W_PATH,
            "results row missing how measured, caveat, source: %s:23 users" % W_PATH])

    def test_citations_and_notes(self):
        """Output citations and record notes are lines to judge; neither is a finding."""
        body = ("\nIt held (outputs/resumes/backend.md). The old design was superseded.\n"
                "\n## Past phrasings\n- **general:** \"Sorted\" (outputs/resumes/backend.tex, 2031-03-02)\n")
        self.write("direction.md", "# Direction\n\nMoved to Berlin (outputs/reports/2031-01-01-x.md).\n")
        self.write("stories.md", "# Stories\n\n## Application questions\n| Q | A |\n|---|---|\n| why | [a](outputs/reports/a.md) |\n")
        code, lines = self.shape(body)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, [
            "check: output citation: %s:19: It held (outputs/resumes/backend.md). The old design was superseded." % W_PATH,
            "check: record note: %s:19: It held (outputs/resumes/backend.md). The old design was superseded." % W_PATH,
            "check: output citation: direction.md:3: Moved to Berlin (outputs/reports/2031-01-01-x.md).",
            "check: record note: direction.md:3: Moved to Berlin (outputs/reports/2031-01-01-x.md).",
            "OK: 1 entries, no findings"])

    def test_source_keys(self):
        self.write("sources/claude-code/2031-01-05-sorter.md", "# Claude Code session 2031-01-05: sorter\n\n## U1 — User\n")
        self.write("sources/chat/2031-01-01-threads.md", "# threads\n")
        self.write("sources/linkedin/page.md", "x")
        self.write("sources/keys.md", "| Key | Points at |\n|---|---|\n| `chat T<n>` | `sources/chat/2031-01-01-threads.md` |\n")
        self.write("sources/resumes/cv-2031.tex", "x")
        body = ("\nA (claude-code-2031-01-05-sorter U1). B (claude-code-2031-01-05-sorter U2, A1).\n"
                "C (claude-code-2031-01-09-gone U1). D (sources/resumes/cv-2031.tex; sources/resumes/cv-*.tex).\n"
                "E (sources/resumes/cv-2030.tex). F (sources/inbox/x.pdf).\n")
        self.assertEqual(self.shape(body)[1], [
            "source key unresolved: %s:19 claude-code-2031-01-05-sorter U2 (no ## U2 in"
            " sources/claude-code/2031-01-05-sorter.md)" % W_PATH,
            "source key unresolved: %s:19 claude-code-2031-01-05-sorter A1 (no ## A1 in"
            " sources/claude-code/2031-01-05-sorter.md)" % W_PATH,
            "source key unresolved: %s:20 claude-code-2031-01-09-gone U1 (no excerpt"
            " sources/claude-code/2031-01-09-gone.md)" % W_PATH,
            "source key unresolved: %s:21 sources/resumes/cv-2030.tex (no such file)" % W_PATH,
            "source folder not in keys.md: sources/linkedin/"])

    def test_consolidated(self):
        body = ("\n## My contribution\n- **I did:** the sorter\n- **I led, with help from:**\n"
                "\n## Pending\n- 2031-06-01: a fact.\n")
        self.write(W_PATH, entry(body=body))
        self.write("entries/2031-02-lamp.md", entry(title="Lamp Fixer", links="[https://github.com/o/r/pull/1]"))
        self.write("README.md", README_HEAD + row(W_PATH))
        code, lines = self.run_tool("check", "--root", self.root, "--today", TODAY, "--consolidated", W_PATH)
        self.assertEqual((code, lines), (1, [
            "pending not empty: %s" % W_PATH,
            "contribution category missing: %s I led, with help from:" % W_PATH,
            "contribution category missing: %s Others did; I can explain it:" % W_PATH]))
        # the other entry's findings show without --consolidated
        _, lines = self.check()
        self.assertIn("no README row: entries/2031-02-lamp.md", lines)
        self.assertEqual(self.run_tool("check", "--root", self.root, "--consolidated")[0], 2)
        self.assertEqual(self.run_tool("list", "--root", self.root, "--consolidated", W_PATH)[0], 2)


class ShapeEdgeTest(Log):
    """Forms the first review found misread."""
    shape = ShapeTest.shape

    def test_consolidated_series_part(self):
        self.write("entries/2031-01-widget.md", entry(series="widget", period="2031-01 – 2031-06"))
        self.write("entries/2031-05-widget-2.md", entry(series="widget", period="2031-05 – 2031-09"))
        self.write("README.md", README_HEAD + row("entries/2031-01-widget.md", period="2031-01 – 2031-06")
                   + row("entries/2031-05-widget-2.md", period="2031-05 – 2031-09"))
        _, lines = self.run_tool("check", "--root", self.root, "--today", TODAY, "--consolidated",
                                 "entries/2031-05-widget-2.md")
        self.assertFalse([l for l in lines if "series names no entry" in l], lines)
        self.assertIn("series widget has overlapping periods: entries/2031-01-widget.md (2031-01 – 2031-06),"
                      " entries/2031-05-widget-2.md (2031-05 – 2031-09)", lines)

    def test_contribution_with_nested_lines(self):
        body = ("\n## My contribution\n- **I did:**\n  - the sorter\n  - its tests\n- **I led, with help from AI agents:** x\n"
                "- **Others did; I can explain it:**\n- a line that is not under it\n")
        self.write(W_PATH, entry(body=body))
        self.write("README.md", README_HEAD + row(W_PATH))
        self.assertEqual(self.run_tool("check", "--root", self.root, "--today", TODAY, "--consolidated", W_PATH)[1],
                         ["contribution category missing: %s Others did; I can explain it:" % W_PATH])

    def test_sources_not_utf8(self):
        self.write("sources/notes/old.md", "\xb4\xfa".encode("latin-1"), "wb")
        self.write("sources/claude-code/2031-01-05-x.md", b"\xb4\xfa", "wb")
        code, lines = self.shape("\nA (claude-code-2031-01-05-x U1).\n")
        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "source key unresolved: %s:19 claude-code-2031-01-05-x U1 (sources/claude-code/2031-01-05-x.md is not"
            " UTF-8 text)" % W_PATH,
            "source folder not in keys.md: sources/claude-code/", "source folder not in keys.md: sources/notes/"])

    def test_keys_md_not_utf8(self):
        self.write("sources/notes/a.md", "x")
        self.write("sources/keys.md", "\xb4\xfa".encode("latin-1"), "wb")
        self.assertEqual(self.shape()[1], ["source key unresolved: sources/keys.md is not UTF-8 text (save it as UTF-8,"
                                           " then run check again)"])

    def test_source_paths_that_are_not_paths(self):
        self.write("sources/resumes/cv.tex", "x")
        body = ("\nA https://github.com/o/r/blob/main/sources/x.md and o/r@ab12cd3:sources/y.md.\n"
                "B（sources/resumes/cv.tex）。C sources/resumes/cv.tex。\nD data sources/tools and sources/<origin>/.\n")
        self.assertEqual(self.shape(body), (0, ["OK: 1 entries, no findings"]))

    def test_bare_gap_lines(self):
        body = ("\n## Results and evidence\n| Metric | Value | How measured | Caveat | Source |\n|---|---|---|---|---|\n"
                "| GAP | | | | |\n\n## Past phrasings\n- GAP\n\n## Conflicts\nGAP (none known)\n\n## Pending\nGAP\n")
        self.assertEqual(self.shape(body), (0, ["OK: 1 entries, no findings"]))

    def test_second_review_forms(self):
        """A line that starts with the word gap is no GAP marker; a path right after CJK text is read;
        a glob with no extension is a path; `**I did not:**` is no `I did:` label."""
        body = ("\n見outputs/resumes/x.tex，來自claude-code-2031-01-05-x U9，見sources/gone/*\n"
                "\n## My contribution\n- **I did not:** the cluster\n"
                "\n## Pending\n- Gap in the docs, to ask the user\n")
        code, lines = self.shape(body)
        self.assertEqual(lines, [
            "pending line without a date: %s:25: - Gap in the docs, to ask the user" % W_PATH,
            "source key unresolved: %s:19 sources/gone/* (no such file)" % W_PATH,
            "source key unresolved: %s:19 claude-code-2031-01-05-x U9 (no excerpt sources/claude-code/2031-01-05-x.md)"
            % W_PATH,
            "check: output citation: %s:19: 見outputs/resumes/x.tex，來自claude-code-2031-01-05-x U9，見sources/gone/*" % W_PATH])
        _, lines = self.run_tool("check", "--root", self.root, "--today", TODAY, "--consolidated", W_PATH)
        self.assertIn("contribution category missing: %s I did:" % W_PATH, lines)

    def test_root_forms(self):
        self.write(W_PATH, entry())
        self.write("README.md", README_HEAD + row(W_PATH))
        for args in (["--root", self.root, "check"], ["check", "--root=%s" % self.root]):
            self.assertEqual(self.run_tool(*args, "--today", TODAY), (0, ["OK: 1 entries, no findings"]), args)
        for args in (["check", "--root"], ["check", "--root", self.root, "--root", self.root]):
            self.assertEqual(self.run_tool(*args)[0], 2, args)


class RulingsHitsTest(Log):
    maxDiff = None

    def setUp(self):
        super().setUp()
        conflicts = ("\n## Conflicts\n- Open: \"x\" vs \"y\"\n"
                     "- Settled: use \"2–10x faster\", not \"throughput\" (wall-clock runs, not \"rate\"). (src)\n"
                     "- Settled: use \"deadlock-free\" for resumes, \"deadlock-free but not starvation-free\" for"
                     " interviews (hot keys). (src)\n"
                     "- Settled: do not use \"820 ms\" (no run shows it). (src)\n")
        self.write(W_PATH, entry(title="Widget Sorter — a job", body=conflicts))
        self.write("entries/2031-02-lamp.md", entry(title="Lamp Fixer", body="\n## Conflicts\n"
                                                    "- Settled: both \"lamp\" and \"light\" are right (same). (src)\n"))
        self.write("profile.md", "# Profile\n\n### Conflicts\n- Settled: use \"Ann Lee\", not \"Anne\" (her name). (src)\n")

    def hits(self):
        code, lines = self.run_tool("rulings-hits", "--root", self.root)
        self.assertEqual(code, 0)
        return lines

    def test_pairs_and_hits(self):
        self.write("outputs/resumes/backend.md", "# Backend\n\n| Claim | Entry section | Source |\n|---|---|---|\n"
                   "| speed | Widget Sorter › Results | src |\n| name | profile | src |\n\n"
                   "## Risks to handle in conversation\n- Throughput was never measured.\n")
        self.write("outputs/resumes/backend.tex", "\\item Made it \\textbf{2-10x Faster} and deadlock-free but not"
                   "\n starvation-free; 820ms p95; Ann Lee\n")
        self.write("outputs/reports/2031-01-01-scan.md", "a scan report: never read\n")
        self.write("outputs/reports/2031-01-02-bio.md", "# Bio\nShe sorted widgets at 820 ms.\n")
        lines = self.hits()
        self.assertEqual(lines[:5], [
            "ruling: %s:21: Settled: use \"2–10x faster\", not \"throughput\" (wall-clock runs, not \"rate\"). (src)" % W_PATH,
            "ruling: %s:22: Settled: use \"deadlock-free\" for resumes, \"deadlock-free but not starvation-free\" for"
            " interviews (hot keys). (src)" % W_PATH,
            "ruling: %s:23: Settled: do not use \"820 ms\" (no run shows it). (src)" % W_PATH,
            "ruling: entries/2031-02-lamp.md:20: Settled: both \"lamp\" and \"light\" are right (same). (src)",
            "ruling: profile.md:4: Settled: use \"Ann Lee\", not \"Anne\" (her name). (src)"])
        self.assertEqual(lines[5:], [
            "check: outputs/resumes/backend against %s:21; hit right outputs/resumes/backend.tex:1 \"2–10x faster\"" % W_PATH,
            "check: outputs/resumes/backend against %s:22; hit context outputs/resumes/backend.tex:1 \"deadlock-free\";"
            " hit context outputs/resumes/backend.tex:1 \"deadlock-free but not starvation-free\"" % W_PATH,
            "check: outputs/resumes/backend against %s:23; hit do-not-use outputs/resumes/backend.tex:2 \"820 ms\"" % W_PATH,
            "check: outputs/resumes/backend against profile.md:4; hit right outputs/resumes/backend.tex:2 \"Ann Lee\"",
            "no provenance: outputs/reports/2031-01-02-bio.md",
            "check: outputs/reports/2031-01-02-bio.md against %s:23; hit do-not-use outputs/reports/2031-01-02-bio.md:2"
            " \"820 ms\"" % W_PATH,
            "check: outputs/reports/2031-01-02-bio.md against profile.md:4",
            "OK: 2 outputs, 5 rulings, 6 pairs, 6 hits"])   # the Risks section and the scan report are not read

    def test_wrong_context(self):
        """The issue's Done when: an output that uses a settled wording in the wrong context is listed."""
        self.write("outputs/applications/2031-02-01-acme-swe/provenance.md",
                   "| Claim | Entry | Source |\n|---|---|---|\n| locks | entries/2031-01-widget.md › How it works | src |\n")
        self.write("outputs/applications/2031-02-01-acme-swe/resume.tex", "\\item Locks are deadlock-free but not"
                   " starvation-free\n")
        self.write("outputs/applications/2031-02-01-acme-swe/posting.md", "Throughput matters.\n")
        lines = self.hits()
        self.assertIn("check: outputs/applications/2031-02-01-acme-swe/ against %s:22; hit context"
                      " outputs/applications/2031-02-01-acme-swe/resume.tex:1 \"deadlock-free\"; hit context"
                      " outputs/applications/2031-02-01-acme-swe/resume.tex:1 \"deadlock-free but not starvation-free\""
                      % W_PATH, lines)
        self.assertIn("check: outputs/applications/2031-02-01-acme-swe/ against %s:21" % W_PATH, lines)   # cited, no hit
        self.assertFalse([l for l in lines if "lamp.md" in l and l.startswith("check:")], lines)   # not cited
        # a wrong side inside a right side's match is not a hit; whole words only
        self.write("outputs/applications/2031-02-01-acme-swe/resume.tex", "\\item 2--10x faster; throughputs\n")
        lines = self.hits()
        self.assertIn("check: outputs/applications/2031-02-01-acme-swe/ against %s:21; hit right"
                      " outputs/applications/2031-02-01-acme-swe/resume.tex:1 \"2–10x faster\"" % W_PATH, lines)

    def test_ruling_with_a_parenthesis_inside(self):
        """Only the trailing (why) and (source) are cut off: a parenthesis before the wrong side keeps it."""
        self.assertEqual(entries.ruling_quotes('Settled: use "12 ms" (wall-clock), not "8 ms" (single run). (src)'),
                         [("right", "12 ms", "12ms"), ("wrong", "8 ms", "8ms")])
        self.assertEqual(entries.ruling_quotes('Settled: do not use "X beat Y" (no run, not "beat"). (src)'),
                         [("do-not-use", "X beat Y", "x beat y")])
        self.assertEqual([q[0] for q in entries.ruling_quotes('Settled: use "A1" for the 2031 (Q3) launch, "B1" for'
                                                              ' the rest (why). (src)')], ["context", "context"])

    def test_unresolved_rows(self):
        self.write("outputs/resumes/general.md", "| Claim | Entry section | Source |\n|---|---|---|\n"
                   "| a | Results (S1) | src |\n| b | [Lamp](../../entries/2031-02-lamp.md) › Context | src |\n"
                   "| c | Sorter › How it works | src |\n")
        self.write("outputs/resumes/two.md", "| Claim | Entry section | Source |\n|---|---|---|\n"
                   "| a | entries/2031-02-lamp.md › Context; Gizmo › People; Results | src |\n")
        self.write("outputs/resumes/two.tex", "\\item cut it to 820\\,ms\n")
        self.write("outputs/reports/2031-01-03-latin.md", "caf\xe9".encode("latin-1"), "wb")
        lines = self.hits()
        self.assertIn("unresolved: outputs/resumes/general.md:3: Results (S1)", lines)
        self.assertIn("unresolved: outputs/resumes/two.md:3: Gizmo › People", lines)   # a piece the row's others hide
        self.assertIn("check: outputs/resumes/two against %s:23; hit do-not-use outputs/resumes/two.tex:1 \"820 ms\""
                      % W_PATH, lines)   # not cited, but a hit
        self.assertIn("unreadable: outputs/reports/2031-01-03-latin.md (not UTF-8 text: read it yourself against every"
                      " ruling)", lines)
        self.assertIn("check: outputs/resumes/general against entries/2031-02-lamp.md:20; hit right"
                      " outputs/resumes/general.md:4 \"lamp\"", lines)
        self.assertIn("check: outputs/resumes/general against %s:21" % W_PATH, lines)   # "Sorter", a run of its title


class RefsTest(Log):
    def test_refs(self):
        self.write("entries/2031-01-widget.md", entry())
        self.write("entries/2031-04-widget-2.md", entry(body="See [part one](2031-01-widget.md#context)."))
        self.write("README.md", README_HEAD + row("entries/2031-01-widget.md") + row("entries/2031-04-widget-2.md"))
        self.write("stories.md", "| Hard bug | [Widget › Dead ends](entries/2031-01-widget.md#dead-ends) |\n")
        self.write("outputs/applications/2031-05-01-acme-dev/provenance.md", "| a | entries/2031-01-widget.md › Context | src |\n")
        self.write("sources/claude-code/2031-02-01-widget.md", "cites 2031-01-widget in passing\n")
        self.write("sources/inbox/raw.md", "entries/2031-01-widget.md\n")
        self.write("sources/resumes/old.pdf", b"%PDF \x00\xff entries/2031-01-widget.md", "wb")
        self.write("profile.md", "nothing here, and 2031-01-widgets is another name\n")
        self.write("stories/hard-bug.md", talking("Hard bug", "2031-06-01", "entries/2031-04-widget-2.md#context",
                                                  cue="entries/2031-01-widget.md")
                   + "<!-- old: entries/2031-01-widget.md -->\n")
        self.write("stories/other.md", talking("Other", "2031-06-01", "entries/2031-04-widget-2.md"))
        code, lines = self.run_tool("refs", "entries/2031-01-widget.md", "--root", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [
            "README.md:7: " + row("entries/2031-01-widget.md").strip(),
            "stories.md:1: | Hard bug | [Widget › Dead ends](entries/2031-01-widget.md#dead-ends) |",
            "entries/2031-04-widget-2.md:18: See [part one](2031-01-widget.md#context).",
            "stories/hard-bug.md:16: - the bug ([Context](../entries/2031-01-widget.md#context))",
            "stories/hard-bug.md:17: <!-- old: entries/2031-01-widget.md -->",
            "outputs/applications/2031-05-01-acme-dev/provenance.md:1: | a | entries/2031-01-widget.md › Context | src |",
            "sources/claude-code/2031-02-01-widget.md:1: cites 2031-01-widget in passing",
            "talking points: stories/hard-bug.md: type Hard bug",   # its cue line links the entry
        ])
        # a link to the entry's #pending is named; one inside an HTML comment does not count
        self.write("stories/other.md", talking("Other", "2031-06-01", "entries/2031-01-widget.md#pending"))
        self.write("stories/hard-bug.md", talking("Hard bug", "2031-06-01", "entries/2031-04-widget-2.md")
                   + "<!-- old: [x](../entries/2031-01-widget.md) -->\n")
        _, lines = self.run_tool("refs", "entries/2031-01-widget.md", "--root", self.root)
        self.assertEqual([l for l in lines if l.startswith("talking points: ")],
                         ["talking points: stories/other.md: type Other; links #pending"])

    def test_refs_reads_config_and_scan_sources(self):
        # config.toml and scan-sources.md are Log files (logfiles.LOG_FILES), so refs reads them too
        self.write("entries/2031-01-widget.md", entry())
        self.write("config.toml", "[scan]\nnote = \"see 2031-01-widget\"\n")
        self.write("scan-sources.md", "- boards picked for entries/2031-01-widget.md\n")
        code, lines = self.run_tool("refs", "entries/2031-01-widget.md", "--root", self.root)
        self.assertEqual((code, lines), (0, ["config.toml:2: note = \"see 2031-01-widget\"",
                                             "scan-sources.md:1: - boards picked for entries/2031-01-widget.md"]))

    def test_not_an_entry(self):
        self.write("README.md", README_HEAD)
        for arg in ("entries/_template.md", "README.md", "entries/2031-09-none.md"):
            code, lines = self.run_tool("refs", arg, "--root", self.root)
            self.assertEqual(code, 2, arg)
            self.assertTrue(lines[0].startswith("FAIL: not an entry"), lines)


class LinksSinceTest(Log):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.path = "entries/2031-01-widget.md"

    def commit(self, subject):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def test_no_consolidate_lists_every_link(self):
        self.write(self.path, entry(links="[https://example.org/widget]", body="Built it. ([notes](../sources/a.md))"))
        self.commit("log(widget): first")
        code, lines = self.run_tool("links-since", self.path, "--root", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["since: no consolidate(widget) commit touches entries/2031-01-widget.md;"
                                 " every link is listed",
                                 "link: https://example.org/widget", "link: ../sources/a.md"])

    def test_links_after_the_last_consolidate(self):
        self.write(self.path, entry(links="[https://example.org/widget]"))
        self.commit("consolidate(lamp, widget): both")
        self.write(self.path, entry(links="[https://example.org/widget]", body="- 2031-04-01: PR. https://example.org/pr/2."))
        self.commit("log(widget): a PR")
        self.write(self.path, entry(links="[https://example.org/widget, https://example.org/pr/3]",
                                    body="- 2031-04-01: PR. https://example.org/pr/2."))
        self.write("entries/2031-02-lamp.md", entry(title="Lamp Fixer"))
        self.commit("consolidate(lamp): only the lamp")
        _, lines = self.run_tool("links-since", self.path, "--root", self.root)
        self.assertTrue(lines[0].startswith("since: "), lines)
        self.assertTrue(lines[0].endswith(" consolidate(lamp, widget): both"), lines)
        self.assertEqual(lines[1:], ["link: https://example.org/pr/3", "link: https://example.org/pr/2"])
        # an uncommitted link counts too
        with open(os.path.join(self.root, self.path), "a", encoding="utf-8") as f:
            f.write("- 2031-05-01: more. https://example.org/pr/4\n")
        _, lines = self.run_tool("links-since", self.path, "--root", self.root)
        self.assertEqual(lines[-1], "link: https://example.org/pr/4")

    def test_section_links(self):
        """Every link in Pending, Past phrasings and Conflicts, consolidated or not, once."""
        self.write(self.path, entry(body="Built it, https://example.org/body.\n\n## Past phrasings\n"
                                         "- **general:** \"Sorted it\" (https://example.org/cv)\n\n## Conflicts\n"
                                         "- Open: [a](../sources/a.md) says 3 <!-- https://example.org/hidden -->\n\n"
                                         "## Pending\n- 2031-04-01: PR https://example.org/pr/2\n"))
        self.commit("consolidate(widget): first")
        with open(os.path.join(self.root, self.path), "a", encoding="utf-8") as f:
            f.write("- 2031-05-01: more https://example.org/pr/3, see https://example.org/cv\n")
        _, lines = self.run_tool("links-since", self.path, "--root", self.root)
        self.assertNotIn("link: https://example.org/hidden", lines)   # inside a comment
        self.assertEqual(lines[1:], ["section link: Pending: https://example.org/pr/2",
                                     "section link: Pending: https://example.org/pr/3",
                                     "section link: Pending: https://example.org/cv",
                                     "section link: Conflicts: ../sources/a.md"])

    def test_not_a_repo(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "entries"))
        with open(os.path.join(root, self.path), "w", encoding="utf-8") as f:
            f.write(entry())
        code, lines = self.run_tool("links-since", self.path, "--root", root)
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("FAIL: git log failed"), lines)


class ScriptTest(Log):
    def test_bad_arguments(self):
        for args in ([], ["frob"], ["refs"], ["list", "a", "b"], ["check", "--today"], ["check", "--today", "soon"],
                     ["list", "--root", self.root, "--bogus"], ["check", "--root", self.root, "--series", "x"],
                     ["list", "--root", self.root, "--today", TODAY]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 2, args)

    def test_help(self):
        """-h or --help anywhere prints the docstring, which holds the formats the modes rely on."""
        for args in (["--help"], ["-h"], ["story-coverage", "--help"], ["list", "--root", self.root, "-h"]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 0, args)
            self.assertEqual(lines, entries.__doc__.splitlines(), args)

    def test_positional_root(self):
        """The root an older Template took as the last argument exits 2 with a line naming --root."""
        for args in (["check", self.root], ["list", self.root], ["refs", "entries/x.md", self.root],
                     ["story-wording-add", "Failure", "x", self.root]):
            code, lines = self.run_tool(*args)
            self.assertEqual((code, lines[0]), (2, "FAIL: give the Log's root as --root %s, not as an argument"
                                                % self.root), args)
        self.assertTrue(self.run_tool("check", "nowhere")[1][0].startswith("usage: "))

    def test_root_without_entries(self):
        missing = os.path.join(self.root, "nowhere")
        for args in (["check", "--root", missing], ["list", "--root", missing], ["refs", "entries/x.md", "--root", missing]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 2, args)
            self.assertTrue(lines[0].startswith("FAIL: no entries/ folder in "), lines)

    def test_runs_as_a_script_in_utf8(self):
        self.write("entries/2031-02-新.md", entry(title="新的", one_line="一句話"))
        run = subprocess.run([sys.executable, "-I", TOOL, "list", "--root", self.root], capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("entries/2031-02-新.md: slug 新;", run.stdout.decode("utf-8"))
        self.assertIn("one line: 一句話", run.stdout.decode("utf-8"))


W, G, P, S = ("entries/2031-01-widget.md", "entries/2031-04-gadget.md", "entries/2031-05-plinth.md",
              "entries/2031-06-widget-v2.md")
X = "entries/2031-07-xylophone.md"
FIVE = (W, G, P, S, X)


def index(*rows, tail=""):
    return ("# Story index\n\nIntro.\n\n| Question type | Stories |\n|---|---|\n%s\n## Application questions\n\n"
            "| Question type | Scope | Answer from |\n|---|---|---|\n| Disagreement / conflict | shared | |\n%s"
            % ("".join("| %s | %s |\n" % r for r in rows), tail))


def story(path, anchor="", label="Widget", summary="", marker=""):
    return "%s[%s](%s%s)%s" % ("*(%s)* " % marker if marker else "", label, path, "#" + anchor if anchor else "",
                                " — " + summary if summary else "")


def talking(type_, confirmed, *stories, cue=None):
    return ("---\ntype: %s\nconfirmed: %s\norder: chronological\n---\n\n# %s\n\n"
            "## Stories\n%s\n## Opening\nI sorted widgets.\n\n## Cue lines\n- the bug ([Context](../%s#context))\n"
            % (type_, confirmed, type_, "".join("%d. [S](../%s) — lead\n" % (n, s) for n, s in enumerate(stories, 1)),
               cue or stories[0]))


class StoryParseTest(Log):
    def test_index_items(self):
        cell = "; ".join([story(W, "dead-ends", "Widget › Dead ends", "a hunt; then a fix"),
                          story(G, marker="raw"), "*(raw)* a move abroad (no entry)",
                          story("direction.md", label="direction"), story(P, "lessons", marker="pending")])
        self.write("stories.md", index(("[Debugging](stories/debugging.md)", cell), ("Proudest project", "")))
        rows = entries.story_index(self.root)
        self.assertEqual([r.type for r in rows], ["Debugging", "Proudest project"])
        self.assertEqual(rows[0].talking, "stories/debugging.md")
        self.assertIsNone(rows[1].talking)
        items = rows[0].items
        self.assertEqual([i.kind for i in items], ["entry", "entry", "unlinked", "other", "entry"])
        self.assertEqual(items[0].key, W + "#dead-ends")
        self.assertEqual(items[0].summary, "a hunt; then a fix")
        self.assertEqual(items[1].markers, ["raw"])
        self.assertEqual(items[1].key, G)
        self.assertTrue(items[4].unfinished())
        self.assertEqual([s.key for s in rows[0].stories], [W + "#dead-ends", G, P + "#lessons"])

    def test_talking_points_file(self):
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01", W + "#dead-ends", G, cue=P))
        tp = entries.TalkingPoints(self.root, "stories/debugging.md")
        self.assertEqual((tp.type, tp.confirmed, tp.day), ("Debugging", "2031-06-01", datetime.date(2031, 6, 1)))
        self.assertEqual([s.key for s in tp.stories], [W + "#dead-ends", G])
        self.assertEqual(tp.entries, sorted([W, G, P]))

    def test_index_edges(self):
        cell = "*(raw)* a move abroad; %s *(raw, pending)* — late marker; %s" % (story(W, "a"), story(G))
        self.write("stories.md", "﻿" + index(("A \\| B", cell), ("[C](entries/x.md)", story(P)),
                                                 tail="\n## Old\n\n| Question type | Stories |\n|---|---|\n"
                                                      "| Hidden | %s |\n" % story(P)).replace("\n", "\r\n"))
        rows = entries.story_index(self.root)
        self.assertEqual([r.type for r in rows], ["A | B", "C"])
        self.assertIsNone(rows[1].talking)   # a type link outside stories/ is no Talking points file
        items = rows[0].items
        self.assertEqual([i.kind for i in items], ["unlinked", "entry", "entry"])
        self.assertEqual((items[1].markers, items[1].summary), (["raw", "pending"], "late marker"))
        self.assertTrue(items[1].unfinished())

    def test_talking_points_ignore_comments(self):
        self.write("stories/x.md", talking("X", "2031-06-01", W) + "<!-- e.g. [Y](../%s) -->\n" % G)
        self.assertEqual(entries.TalkingPoints(self.root, "stories/x.md").entries, [W])

    def test_slug(self):
        self.assertEqual(entries.story_slug("Disagreement / conflict"), "disagreement-conflict")
        self.assertEqual(entries.story_slug("Scope / prioritisation / tech debt"), "scope-prioritisation-tech-debt")
        self.assertEqual(entries.story_slug("衝突 與 分歧"), "衝突-與-分歧")


class StoryCoverageTest(Log):
    def setUp(self):
        super().setUp()
        for path in FIVE:
            self.write(path, entry())

    def coverage(self, *types):
        return self.run_tool("story-coverage", "--root", self.root, *[a for t in types for a in ("--type", t)])

    def five_core(self):
        """Five entries marked core, each under two types, no finding."""
        cells = [[(FIVE[i], "a", "core"), (FIVE[(i + 1) % 5], "b", "")] for i in range(5)]
        return [("T%d" % n, "; ".join(story(p, a, marker=m) for p, a, m in c)) for n, c in enumerate(cells)]

    def test_clean(self):
        self.write("stories.md", index(*self.five_core()))
        code, lines = self.coverage()
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "core stories: 5; " + "; ".join("%s (2 types)" % p for p in FIVE))
        self.assertEqual(lines[1], "types per entry: " + "; ".join("%s (2 types)" % p for p in FIVE))
        self.assertEqual(lines[-1], "OK: 5 question types, no findings")

    def test_type_with_no_story(self):
        self.write("stories.md", index(*self.five_core(), ("Leading a team", ""), ("Why us", "*(raw)* a move abroad"),
                                       ("Mentoring", story(G, "x", marker="raw") + "; " + story(P, "y", marker="pending"))))
        code, lines = self.coverage()
        self.assertEqual(code, 1)
        self.assertIn("type with no story: Leading a team", lines)
        self.assertIn("type with no story: Why us (items without an entry link: 1)", lines)
        self.assertIn("type with only raw or pending stories: Mentoring", lines)

    def test_sections_of_one_entry_count_as_one_story(self):
        self.write("stories.md", index(("A", story(W, "a") + "; " + story(W, "b")), ("B", story(W, "c"))))
        code, lines = self.coverage()
        self.assertEqual(lines[:2], ["core stories: 0", "types per entry: %s (2 types)" % W])   # unmarked: not core
        self.write("stories.md", index(("A", story(W, "a", marker="core") + "; " + story(W, "b")),
                                       ("B", story(W, "c"))))
        code, lines = self.coverage()
        self.assertEqual(lines[0], "core stories: 1; %s (2 types)" % W)
        self.write("stories.md", index(("A", story(W, "a") + " *(Core)*"), ("B", story(G, marker="raw, core")),
                                       ("A", story(P, marker="core"))))   # the duplicate row is ignored
        code, lines = self.coverage()
        self.assertEqual(lines[0], "core stories: 2; %s (1 types); %s (1 types)" % (W, G))

    def test_story_under_too_many_types(self):
        rows = self.five_core() + [("X%d" % n, story(G, "s") + "; " + story(W, "z%d" % n)) for n in range(4)]
        self.write("stories.md", index(*rows))
        code, lines = self.coverage()
        self.assertIn("story under too many types: %s#s in 4 types (more than 3): X0 | X1 | X2 | X3" % G, lines)
        self.assertFalse([l for l in lines if l.startswith("story under too many types: %s" % W)], lines)   # by key
        self.assertEqual(code, 1)

    def test_pending_stories_of_one_entry_are_not_one_story(self):
        """#232: every pending Story of an entry shares the key entries/<file>.md#pending."""
        rows = self.five_core() + [("X%d" % n, story(G, "pending", marker="pending")) for n in range(4)]
        self.write("stories.md", index(*rows))
        code, lines = self.coverage()
        self.assertFalse([l for l in lines if l.startswith("story under too many types")], lines)
        self.assertTrue(lines[1].startswith("types per entry: %s (6 types); " % G), lines)   # the entry still counts them
        code, lines = self.coverage("X0", "X1")
        self.assertIn("interview: X0: leads with %s#pending" % G, lines)
        self.assertIn("interview: X1: leads with %s#pending" % G, lines)
        self.assertFalse([l for l in lines if l.startswith("story carries")], lines)
        code, lines = self.coverage("X0", "T0=%s#pending" % G)   # a chosen Story
        self.assertFalse([l for l in lines if l.startswith("story carries")], lines)

    def test_a_series_is_one_experience(self):
        first, later = "entries/2031-01-shop.md", "entries/2032-01-shop-scale.md"
        self.write(first, entry(series="shop"))
        self.write(later, entry(series="shop", period="2032-01 – 2032-06"))
        self.write("stories.md", index(("A", story(first, "a")), ("B", story(later, "b", marker="core")),
                                       ("C", story(W))))
        code, lines = self.coverage()
        self.assertEqual(lines[:2], ["core stories: 1; %s (2 types)" % first,
                                     "types per entry: %s (2 types); %s (1 types)" % (first, W)])
        self.write(first, entry())   # a first part without its series: line still heads the series
        code, lines = self.coverage()
        self.assertEqual(lines[0], "core stories: 1; %s (2 types)" % first)

    def test_core_count_outside_range(self):
        self.write("stories.md", index(("A", story(W, "a", marker="core")), ("B", story(W, "b") + "; " + story(G))))
        code, lines = self.coverage()
        self.assertEqual(lines[0], "core stories: 1; %s (2 types)" % W)
        self.assertIn("core stories outside 3–5: 1", lines)
        rows = [("T0", "; ".join(story(p, marker="raw, core") for p in FIVE)),
                ("T1", story("entries/2031-07-more.md", marker="core"))]
        self.write("stories.md", index(*rows))
        code, lines = self.coverage()
        self.assertIn("core stories outside 3–5: 6", lines)
        self.assertIn("index names a missing entry: T1: entries/2031-07-more.md", lines)

    def test_pasted_list_overloads_one_story(self):
        rows = self.five_core() + [("Conflict", story(G, "c") + "; " + story(W, "a")),
                                   ("Failure", story(G, "c")), ("Deadline", story(G, "e"))]
        self.write("stories.md", index(*rows))
        code, lines = self.coverage("Deadline", "Failure", "T0", "Unknown type")   # two sections of one entry
        self.assertEqual(code, 1, lines)
        self.assertIn("interview: Failure: leads with %s#c" % G, lines)
        self.assertIn("interview type not in stories.md: Unknown type", lines)
        self.assertFalse([l for l in lines if l.startswith("story carries")], lines)
        code, lines = self.coverage("Conflict", "Failure", "Deadline")
        self.assertIn("story carries too many questions in one interview: %s#c leads 2 (more than 1):"
                      " Conflict | Failure" % G, lines)
        code, lines = self.coverage("Conflict=%s#a" % W, "Failure", "Deadline")
        self.assertIn("interview: Conflict: leads with %s#a" % W, lines)
        self.assertFalse([l for l in lines if l.startswith("story carries")], lines)

    def test_talking_points_lead_and_files(self):
        rows = self.five_core() + [("[Conflict](stories/conflict.md)", story(G, "c") + "; " + story(P, "d")),
                                   ("[Failure](stories/failure.md)", story(G, "c"))]
        self.write("stories.md", index(*rows))
        self.write("stories/conflict.md", talking("Conflict", "2031-06-01", P + "#d", G + "#c"))
        self.write("stories/stray.md", talking("Stray", "2031-06-01", G))
        self.write("stories/t0.md", talking("T0", "June", G))
        code, lines = self.coverage("Conflict")
        self.assertIn("interview: Conflict: leads with %s#d" % P, lines)
        self.assertIn("row links a missing talking points file: Failure: stories/failure.md", lines)
        self.assertIn("talking points file no row links: stories/stray.md", lines)
        self.assertIn("talking points file no row links: stories/t0.md", lines)
        self.write("stories.md", index(*rows[1:] + [("[T0](stories/t0.md)", rows[0][1]),
                                                    ("[Stray](stories/stray.md)", story(G))]))
        self.write("stories/stray.md", talking("Strays", "2031-06-01", G))
        code, lines = self.coverage()
        self.assertIn("talking points with no readable confirmed date: stories/t0.md June", lines)
        self.assertIn("talking points type differs from its row: stories/stray.md: type Strays, row Stray", lines)

    def test_no_stories_md(self):
        code, lines = self.coverage()
        self.assertEqual(lines[:2], ["core stories: 0", "types per entry: -"])
        self.assertEqual((code, lines[-1]), (1, "core stories outside 3–5: 0"))
        self.assertIn("no story index: no stories.md", lines)
        self.write("stories.md", "# Story index\n\n| Question type | Story |\n|---|---|\n| A | %s |\n" % story(W))
        code, lines = self.coverage()
        self.assertIn("no story index: stories.md has no table headed | Question type | Stories |", lines)

    def test_duplicate_type(self):
        self.write("stories.md", index(*self.five_core() + [("T0", story(P, "z"))]))
        code, lines = self.coverage("T0")
        self.assertIn("duplicate question type: T0", lines)
        self.assertIn("interview: T0: leads with %s#a" % W, lines)
        self.write("stories.md", index(*self.five_core() + [("T0", story(W, "z"))]))
        code, lines = self.coverage()
        self.assertEqual(lines[0].count("(2 types)"), 5, lines)   # the second T0 row adds no type
        self.assertEqual(lines[2:], ["duplicate question type: T0"])


class StoryCandidatesTest(Log):
    def setUp(self):
        Log.setUp(self)   # StoryLeadsTest borrows this setUp
        self.write(W, entry(one_line="Sorted widgets.", series="widget"))
        self.write(S, entry(title="Widget Sorter v2", period="2031-06 – 2031-08", one_line="Sorted faster.",
                            series="widget"))
        self.write(G, entry(title="Gadget", one_line="Built gadgets.", body="Text.\n\n## Pending\n<!-- c -->\n"
                            "- (2031-05-02) a gadget outage, fixed by a rollback (user, 2031-05-02)\n"))
        self.write(P, entry(title="Plinth", one_line="Poured plinths."))
        self.write("stories.md", index(("Debugging", story(W, "dead-ends", "Widget › Dead ends", "a hunt", "raw")
                                        + "; *(raw)* a move abroad"),
                                       ("Leading a team", story(P, "people"))))

    def candidates(self, question_type):
        code, lines = self.run_tool("story-candidates", question_type, "--root", self.root)
        self.assertEqual(code, 0, lines)
        return lines

    def test_from_index_row_unindexed_pending_and_series(self):
        lines = self.candidates("Debugging")
        self.assertEqual(lines[:2], ["type: Debugging", "talking points: none; a new file is stories/debugging.md"])
        self.assertIn("indexed: %s#dead-ends; markers raw; series widget; label Widget › Dead ends; summary: a hunt" % W, lines)
        self.assertIn("indexed, not an entry: *(raw)* a move abroad", lines)
        self.assertIn("not yet indexed: %s; series -; indexed under -; one line: Built gadgets." % G, lines)
        self.assertIn("not yet indexed: %s; series -; indexed under Leading a team; one line: Poured plinths." % P,
                      lines)
        self.assertIn("not yet indexed: %s; series widget; indexed under -; another part indexed here: %s;"
                      " one line: Sorted faster." % (S, W), lines)
        self.assertFalse([l for l in lines if l.startswith("not yet indexed: %s" % W)], lines)
        self.assertIn("pending: %s: (2031-05-02) a gadget outage, fixed by a rollback (user, 2031-05-02)" % G, lines)
        kinds = [l.split(":")[0] for l in lines]
        self.assertEqual(kinds, sorted(kinds, key=["type", "talking points", "indexed", "indexed, not an entry",
                                                   "not yet indexed", "pending"].index))

    def test_with_talking_points(self):
        self.write("stories.md", index(("[Debugging](stories/debugging.md)", story(W, "dead-ends"))))
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01", G + "#context", W + "#dead-ends"))
        lines = self.candidates("Debugging")
        self.assertEqual(lines[1], "talking points: stories/debugging.md confirmed 2031-06-01")
        self.assertEqual(lines[2], "talking points 1: %s#context; label S; lead" % G)
        self.assertIn("indexed: %s#dead-ends; markers -; series widget; label Widget; one line: Sorted widgets." % W,
                      lines)

    def test_new_type(self):
        lines = self.candidates("Raising a risk")
        self.assertEqual(lines[1], "type not in stories.md: Raising a risk (a new type; every entry is a candidate)")
        self.assertEqual(len([l for l in lines if l.startswith("not yet indexed: ")]), 4)

    def test_other_items_after_stories_and_a_missing_file(self):
        self.write("stories.md", index(("[Conflict](stories/conflict.md)", "*(raw)* a move abroad; " + story(P))))
        lines = self.candidates("Conflict")
        self.assertEqual(lines[1], "talking points: none; a new file is stories/conflict.md")
        self.assertEqual([l.split(":")[0] for l in lines[2:4]], ["indexed", "indexed, not an entry"])


class StoryLeadsTest(Log):
    setUp, candidates = StoryCandidatesTest.setUp, StoryCandidatesTest.candidates

    def test_candidates_per_question_then_the_ask(self):
        code, lines = self.run_tool("story-leads", "--type", "Debugging", "--type", "Leading a team", "--root", self.root)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "question 1: Debugging")
        self.assertEqual(lines[1:lines.index("question 2: Leading a team")], self.candidates("Debugging"))
        rest = lines[lines.index("question 2: Leading a team") + 1:]
        self.assertEqual(rest[:-1], self.candidates("Leading a team"))
        self.assertTrue(rest[-1].startswith("next: now, show the user each question's proposed type"), rest[-1])
        self.assertIn("then end your turn", rest[-1])

    def leads(self, pack):
        self.write("outputs/applications/a/interview-screen.md", pack)
        return self.run_tool("story-leads", "--check", "outputs/applications/a/interview-screen.md", "--root", self.root)

    def test_check_passes_the_users_picks(self):
        code, lines = self.leads("# Pack\n\n## Stories\n\n### Tell me about a hard bug\nType: Debugging\n"
                                 "Lead: %s#dead-ends (user, 2031-06-02)\n\n### A team you led\n- **Type:** Leading a team\n"
                                 "- **Lead**: set aside (user, 2031-06-02).\n\n## Questions to ask\n- Lead: not a question\n" % W)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["lead: Tell me about a hard bug: %s#dead-ends (user, 2031-06-02)" % W,
                                 "lead: A team you led: set aside (user, 2031-06-02).", "leads: ok, 2 question(s)"])

    def test_check_fails_a_lead_the_user_did_not_pick(self):
        code, lines = self.leads("## Stories\n\n### Hard bug\nType: Debugging\nLead: %s#dead-ends (proposed)\n\n"
                                 "### Team\nLead: %s (user, 2031-06-02)\n\n### Conflict\nType: Conflict\n\n"
                                 "### Twice\nType: Debugging\nLead: x (user, 2031-06-02)\nLead: y (user, 2031-06-02)\n" % (W, P))
        self.assertEqual(code, 1, lines)
        self.assertEqual(lines[0], "lead: Team: %s (user, 2031-06-02)" % P)
        self.assertEqual(lines[1:-1], ["FAIL: lead not the user's pick: Hard bug: %s#dead-ends (proposed)" % W,
                                       "FAIL: no type: Team", "FAIL: no lead: Conflict", "FAIL: 2 leads: Twice"])
        self.assertTrue(lines[-1].startswith("next: fix a `no type` or `leads:` line"), lines[-1])
        lines = self.leads("# Pack\n\n## Likely questions\n- x\n")[1]
        self.assertEqual(lines[0], "FAIL: no ## Stories section: outputs/applications/a/interview-screen.md")
        self.assertTrue(lines[1].startswith("next: write the pack's ## Stories"), lines)
        self.assertEqual(self.leads("## Stories\n\nNone predicted.\n"), (0, ["leads: none predicted"]))
        self.assertEqual(self.leads("## Stories\n\nSome text.\n")[0], 1)

    def test_check_passes_a_lead_taken_from_confirmed_talking_points(self):
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01 13:00", W + "#dead-ends", P))
        pack = ("## Stories\n\n### Hard bug\nType: Debugging\nLead: %s (stories/debugging.md, confirmed %s)\n"
                "\n### Team\nType: Leading a team\nLead: %s#people (user, 2031-06-02)\n")
        code, lines = self.leads(pack % (P, "2031-06-01", P))
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["lead: Hard bug: %s (stories/debugging.md, confirmed 2031-06-01)" % P,
                                 "lead: Team: %s#people (user, 2031-06-02)" % P, "leads: ok, 2 question(s)"])
        lines = self.leads("## Stories\n\n### Hard bug\n- **Type:** Debugging\n- **Lead:** %s#dead-ends"
                           " (stories/debugging.md, confirmed 2031-06-01 13:00).\n" % W)[1]
        self.assertEqual(lines[-1], "leads: ok, 1 question(s)")
        bad = ((G, "2031-06-01", "not in the file's ## Stories"),)
        for key, day, why in bad:
            code, lines = self.leads(pack % (key, day, P))
            self.assertEqual(code, 1, lines)
            self.assertIn("FAIL: lead not in confirmed talking points: Hard bug: %s (stories/debugging.md, confirmed"
                          " %s): %s" % (key, day, why), lines)
        code, lines = self.leads(pack.replace("Type: Debugging", "Type: Leading a team") % (P, "2031-06-01", P))
        self.assertIn("FAIL: lead not in confirmed talking points: Hard bug: %s (stories/debugging.md, confirmed"
                      " 2031-06-01): the file's type is Debugging" % P, lines)
        code, lines = self.leads(pack.replace("debugging.md", "conflict.md") % (P, "2031-06-01", P))
        self.assertIn("FAIL: lead not in confirmed talking points: Hard bug: %s (stories/conflict.md, confirmed"
                      " 2031-06-01): no such file" % P, lines)
        self.assertTrue(lines[-1].startswith("next: fix a `no type` or `leads:` line"), lines[-1])

    def test_check_names_a_mis_shaped_taken_lead_a_format_error(self):
        """#530 (1): a value ending `(..., confirmed ...)` that misses the form is rewritten, not asked about."""
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01 13:00", W + "#dead-ends", P))
        for value in (P + r" (stories\debugging.md, confirmed 2031-06-01)",
                      P + " ([debugging](stories/debugging.md), confirmed 2031-06-01)",
                      P + " (../../../stories/debugging.md, confirmed 2031-06-01).",
                      P + " (stories/debugging.md confirmed 2031-06-01)"):
            code, lines = self.leads("## Stories\n\n### Hard bug\nType: Debugging\nLead: %s\n" % value)
            self.assertEqual(code, 1, lines)
            self.assertEqual(lines[0], "FAIL: taken lead not in the form: Hard bug: %s" % value)
            self.assertIn("rewrite each `taken lead not in the form` or `taken lead date out of date` Lead: without"
                          " asking the user, keeping its key", lines[-1])
        for value in (P + " (proposed)", "set aside (user confirmed, 2031-06-01)",
                      P + " (confirmed by the user, 2031-06-01)", P + " (stories/debugging.md, user confirmed)"):
            lines = self.leads("## Stories\n\n### Hard bug\nType: Debugging\nLead: %s\n" % value)[1]
            self.assertEqual(lines[0], "FAIL: lead not the user's pick: Hard bug: %s" % value)

    def test_check_names_a_date_a_reconfirm_left_behind(self):
        """#530 (2): the file was confirmed again with the Story still in it: rewrite the date, ask nobody."""
        self.write("stories/debugging.md", talking("Debugging", "2031-06-03 09:15", W + "#dead-ends", P))
        code, lines = self.leads("## Stories\n\n### Hard bug\nType: Debugging\n"
                                 "Lead: %s (stories/debugging.md, confirmed 2031-06-01 13:00)\n" % P)
        self.assertEqual(code, 1, lines)
        self.assertEqual(lines[0], "FAIL: taken lead date out of date: Hard bug: %s (stories/debugging.md, confirmed"
                                   " 2031-06-01 13:00): the file is confirmed 2031-06-03 09:15" % P)
        self.assertIn("without asking the user", lines[-1])
        code, lines = self.leads("## Stories\n\n### Hard bug\nType: Debugging\n"
                                 "Lead: %s (stories/debugging.md, confirmed 2031-06-03)\n" % P)
        self.assertEqual((code, lines[-1]), (0, "leads: ok, 1 question(s)"))
        self.write("stories/debugging.md", talking("Debugging", "someday", W + "#dead-ends", P))
        lines = self.leads("## Stories\n\n### Hard bug\nType: Debugging\n"
                           "Lead: %s (stories/debugging.md, confirmed 2031-06-01)\n" % P)[1]
        self.assertEqual(lines[0], "FAIL: lead not in confirmed talking points: Hard bug: %s (stories/debugging.md,"
                                   " confirmed 2031-06-01): the file is confirmed someday" % P)

    def test_usage(self):
        for args in (["story-leads"], ["story-leads", "pack.md"], ["story-leads", "--check"],
                     ["story-leads", "--check", "a.md", "--type", "Debugging"], ["story-leads", "--type", "Debugging", "x"]):
            self.assertEqual(self.run_tool(*args, "--root", self.root)[0], 2, args)


class StoryStaleTest(Log):
    def setUp(self):
        super().setUp()
        self.write(W, entry())
        self.write(G, entry(title="Gadget"))
        self.write(P, entry(title="Plinth"))
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01", W + "#dead-ends", cue=G))

    def commit(self, message, day, *paths):
        env = dict(os.environ, GIT_AUTHOR_DATE="%sT12:00:00" % day, GIT_COMMITTER_DATE="%sT12:00:00" % day)
        for args in (["add", "--"] + list(paths), ["commit", "-q", "-m", message]):
            subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@example.com",
                            "-c", "commit.gpgsign=false"] + args, check=True, capture_output=True, env=env)

    def stale(self, path="stories/debugging.md"):
        return self.run_tool("story-stale", path, "--root", self.root)

    def test_fresh_then_stale(self):
        self.git("init", "-q")
        self.commit("log(widget)", "2031-05-30", W, G, P)
        self.commit("stories(debugging): confirm", "2031-06-01", W, "stories/debugging.md")
        code, lines = self.stale()
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].startswith("since: ") and lines[0].endswith(" stories(debugging): confirm"), lines)
        self.assertTrue(lines[-1].startswith("OK: 2 entries unchanged since "), lines)
        self.write(P, "\nmore\n", "a")
        self.commit("log(plinth)", "2031-06-01", P)   # not pointed at
        self.write(W, "\nlater the same day\n", "a")
        self.commit("log(widget): fix", "2031-06-01", W)
        self.write(G, "\nuncommitted\n", "a")
        code, lines = self.stale()
        self.assertEqual(code, 1, lines)
        self.assertEqual(len(lines), 3, lines)
        self.assertRegex(lines[1], r"^changed: %s [0-9a-f]+ 2031-06-01 log\(widget\): fix$" % W)
        self.assertEqual(lines[2], "uncommitted: %s" % G)

    def test_reconfirmed_moves_the_baseline(self):
        self.git("init", "-q")
        self.commit("stories(debugging): confirm", "2031-06-01", W, G, "stories/debugging.md")
        self.write(W, "\nchange\n", "a")
        self.commit("log(widget)", "2031-06-10", W)
        self.write("stories/debugging.md", talking("Debugging", "2031-06-12", W + "#dead-ends", cue=G))
        self.commit("stories(debugging): reconfirm", "2031-06-12", "stories/debugging.md")
        code, lines = self.stale()
        self.assertEqual(code, 0, lines)

    def test_same_day_reconfirm_with_a_time(self):   # #230
        self.git("init", "-q")
        self.commit("stories(debugging): confirm", "2031-06-01", W, G, "stories/debugging.md")
        self.write(W, "\nchange\n", "a")
        self.commit("log(widget)", "2031-06-01", W)
        self.assertEqual(self.stale()[0], 1)
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01 14:30", W + "#dead-ends", cue=G))
        self.commit("stories(debugging): reconfirm", "2031-06-01", "stories/debugging.md")
        code, lines = self.stale()
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith(" stories(debugging): reconfirm"), lines)
        # a later save with the date alone, over the timed line, is found too
        self.write(W, "\nagain\n", "a")
        self.commit("log(widget): again", "2031-06-01", W)
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01", W + "#dead-ends", cue=G))
        self.commit("stories(debugging): revise", "2031-06-01", "stories/debugging.md")
        code, lines = self.stale()
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith(" stories(debugging): revise"), lines)
        # a commit that only adds trailing space or moves the line does not reconfirm
        self.write(W, "\nonce more\n", "a")
        self.commit("log(widget): once more", "2031-06-01", W)
        text = talking("Debugging", "2031-06-01", W + "#dead-ends", cue=G)
        self.write("stories/debugging.md", text.replace("confirmed: 2031-06-01\norder: chronological\n",
                                                        "order: chronological\nconfirmed: 2031-06-01  \n"))
        self.commit("stories(debugging): tidy", "2031-06-01", "stories/debugging.md")
        code, lines = self.stale()
        self.assertEqual(code, 1, lines)
        self.assertTrue(lines[0].endswith(" stories(debugging): revise"), lines)

    def test_confirmed_line_with_special_characters(self):
        self.git("init", "-q")
        self.commit("log(widget)", "2031-05-30", W, G)
        text = talking("Debugging", "2031-06-01", W + "#dead-ends", cue=G)
        self.write("stories/debugging.md", text.replace("confirmed: 2031-06-01",
                                                        'confirmed: "2031-06-01 14:30"   # re (x) [y] *+?'))
        self.commit("stories(debugging): confirm", "2031-06-01", "stories/debugging.md")
        code, lines = self.stale()
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].endswith(" stories(debugging): confirm"), lines)
        self.write("stories.md", index(("[Debugging](stories/debugging.md)", story(W, "dead-ends"))))
        code, lines = self.run_tool("story-coverage", "--root", self.root)
        self.assertFalse([l for l in lines if "confirmed date" in l], lines)

    def test_uncommitted_file_counts_from_the_time(self):
        self.git("init", "-q")
        self.commit("log(widget)", "2031-05-30", W, G)
        self.write(W, "\nmorning\n", "a")
        self.commit("log(widget): morning", "2031-06-01", W)   # 12:00
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01 13:00", W + "#dead-ends", cue=G))
        code, lines = self.stale()
        self.assertEqual(lines[0], "since: 2031-06-01 13:00 (no commit wrote stories/debugging.md's"
                                   " 'confirmed: 2031-06-01 13:00')")
        self.assertEqual(code, 0, lines)
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01 25:00", W + "#dead-ends", cue=G))
        code, lines = self.stale()
        self.assertEqual(code, 2, lines)

    def test_uncommitted_file_counts_from_the_day(self):
        self.git("init", "-q")
        self.commit("log(widget)", "2031-05-30", W, G)
        self.write(W, "\nmore\n", "a")
        self.commit("log(widget): more", "2031-06-01", W)
        code, lines = self.stale()
        self.assertEqual(lines[0], "since: 2031-06-01 00:00 (no commit wrote stories/debugging.md's"
                                   " 'confirmed: 2031-06-01')")
        self.assertRegex(lines[1], r"^changed: %s [0-9a-f]+ 2031-06-01 log\(widget\): more$" % W)
        self.assertEqual(code, 1)

    def test_missing_entry_and_errors(self):
        self.git("init", "-q")
        self.commit("log(widget)", "2031-05-30", W)
        self.write("stories/gone.md", talking("Gone", "2031-06-01", "entries/2031-09-gone.md"))
        self.write("stories/undated.md", talking("Undated", "soon", W))
        code, lines = self.stale("stories/gone.md")
        self.assertIn("missing entry: entries/2031-09-gone.md", lines)
        self.assertEqual(code, 1)
        for path in ("stories/undated.md", W, "stories/none.md"):
            code, lines = self.stale(path)
            self.assertEqual(code, 2, path)
            self.assertTrue(lines[0].startswith("FAIL: "), lines)

    def test_bad_arguments(self):
        for args in (["story-stale"], ["story-candidates"], ["story-coverage", "--type"],
                     ["list", "--type", "x"], ["story-coverage", "a", "b"]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 2, args)

    def test_not_a_repo(self):
        code, lines = self.stale()
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("FAIL: git log failed: "), lines)


class StoryWordingsTest(Log):
    def setUp(self):
        super().setUp()
        self.write(W, entry())
        self.write("stories.md", index(("[Conflict](stories/conflict.md)", story(W)),
                                       ("Disagreement / conflict", ""), ("Failure", "")))

    def add(self, qtype, wording):
        return self.run_tool("story-wording-add", qtype, wording, "--root", self.root)

    def listing(self, *types):
        return self.run_tool("story-wordings", "--root", self.root, *[a for t in types for a in ("--type", t)])

    def test_add_creates_the_file_then_appends_and_skips_a_repeat(self):
        self.assertEqual(self.add("Failure", "Tell me about  a\nfailure."),
                         (0, ["added: stories/wordings/failure.md: Tell me about a failure."]))
        self.assertEqual(self.add("Failure", "When did you fail?")[0], 0)
        self.assertEqual(self.add("Failure", " tell me ABOUT a failure. "),
                         (0, ["already kept: stories/wordings/failure.md: tell me ABOUT a failure."]))
        with open(os.path.join(self.root, "stories/wordings/failure.md"), encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), "---\ntype: Failure\n---\n\n# Failure\n\n- Tell me about a failure.\n"
                                       "- When did you fail?\n")
        self.assertEqual(self.listing(), (0, ["wording: Failure | Tell me about a failure.",
                                              "wording: Failure | When did you fail?"]))

    def test_kept_without_talking_points_and_unseen_by_coverage(self):
        """A type with no Talking points keeps its wordings; stories/wordings/ holds no Talking points file."""
        self.add("Failure", "Tell me about a failure.")
        code, lines = self.run_tool("story-coverage", "--root", self.root)
        self.assertFalse([l for l in lines if "wordings" in l], lines)
        self.assertEqual(entries.talking_points_files(self.root), [])

    def test_type_must_be_in_the_index(self):
        code, lines = self.add("Failures", "Tell me about a failure.")
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("FAIL: question type not in stories.md's Story index: Failures"), lines)
        self.assertFalse(os.path.exists(os.path.join(self.root, "stories/wordings")))
        self.assertEqual(self.add("Failure", "  ")[0], 2)

    def test_two_types_with_one_slug(self):
        self.write("stories/wordings/disagreement-conflict.md", "---\ntype: Disagreement, conflict\n---\n\n- Old.\n")
        self.assertEqual(self.add("Disagreement / conflict", "Tell me about a conflict.")[1],
                         ["added: stories/wordings/disagreement-conflict-2.md: Tell me about a conflict."])

    def test_appends_in_the_file_s_own_line_endings(self):
        self.write("stories/wordings/f.md", "﻿---\r\ntype: Failure\r\n---\r\n\r\n- One.")
        self.add("Failure", "Two.")
        with open(os.path.join(self.root, "stories/wordings/f.md"), "rb") as f:
            self.assertTrue(f.read().endswith(b"- One.\r\n- Two.\r\n"))
        self.assertEqual(self.listing("Failure")[1], ["wording: Failure | One.", "wording: Failure | Two."])

    def test_listing_order_filters_and_strays(self):
        self.write("stories/wordings/z.md", "---\ntype: Conflict\n---\n\n# Conflict\n\n- A clash?\n"
                                            "<!-- - not a wording -->\n<!--\n- nor this\n-->\n")
        self.write("stories/wordings/a.md", "---\ntype: Old type\n---\n\n- Gone?\n")
        self.write("stories/wordings/b.md", "# no front matter\n\n- Lost?\n")
        self.add("Failure", "Fail?")
        self.assertEqual(self.listing()[1], [
            "wording: Conflict | A clash?", "wording: Failure | Fail?",
            "wordings type not in stories.md: stories/wordings/a.md: Old type", "wording: Old type | Gone?",
            "wordings file with no type: stories/wordings/b.md"])
        self.assertEqual(self.listing("Failure", "Disagreement / conflict"),
                         (0, ["no wordings: Disagreement / conflict", "wording: Failure | Fail?"]))

    def test_types_a_type_line_cannot_hold(self):
        types = ["Project #1", '"Quoted" x', "[Draft] plan]"]
        self.write("stories.md", index(*[(t, "") for t in types]))
        for t in types:
            code, lines = self.add(t, "Tell me.")
            self.assertEqual(code, 2, t)
            self.assertTrue(lines[0].startswith("FAIL: a question type a type: line cannot hold"), lines)
        self.write("stories/wordings/x.md", "---\ntype: [a, b]\n---\n\n- Odd?\n")
        self.assertEqual(self.listing(), (0, ["wordings file with no type: stories/wordings/x.md"]))

    def test_a_wording_that_starts_with_a_dash_and_an_empty_file(self):
        self.write("stories/wordings/failure.md", "---\ntype: Failure\n---\n\n# Failure\n")
        self.assertEqual(self.listing("Failure")[1], ["no wordings: Failure"])
        self.assertEqual(self.run_tool("story-wording-add", "Failure", "--root", self.root, "--", "-h, really?", "x")[0], 2)
        self.assertEqual(self.run_tool("story-wording-add", "--root", self.root, "--", "Failure", "--why -h?"),
                         (0, ["added: stories/wordings/failure.md: --why -h?"]))
        self.assertEqual(self.listing("Failure")[1], ["wording: Failure | --why -h?"])

    def test_other_commands_take_no_double_dash(self):
        self.assertEqual(self.run_tool("list", "--", self.root)[0], 2)
        for args in (["check", "--", "-h"], ["story-coverage", "--type", "--", "-h"]):
            self.assertEqual(self.run_tool(*args), (0, entries.__doc__.splitlines()), args)

    def test_no_stories_md(self):
        os.remove(os.path.join(self.root, "stories.md"))
        self.assertEqual(self.add("Failure", "Tell me.")[0], 2)
        self.assertEqual(self.listing("Failure"), (0, ["no wordings: Failure"]))

    def test_arguments(self):
        for args in (["story-wording-add", "Failure"], ["story-wording-add", "Failure", "x", "--root", self.root, "y"],
                     ["story-wording-add", "Failure", "x", "--root", self.root, "--type", "x"],
                     ["story-wordings", "--root", self.root, "y"]):
            self.assertEqual(self.run_tool(*args)[0], 2, args)


class StoryFinishTest(Log):
    BODY = ("\n## How it works\nIt sorts.\n\n## Dead ends and mistakes\nA hunt (sources/resumes/cv-2031.pdf).\n"
            "\n## Pending\n")

    def setUp(self):
        super().setUp()
        self.write(W, entry() + self.BODY)
        self.write(G, entry(title="Gadget"))

    def finish(self, path=W):
        return self.run_tool("story-finish", path, "--root", self.root)

    def stories_md(self):
        with open(os.path.join(self.root, "stories.md"), encoding="utf-8", newline="") as f:
            return f.read()

    def test_drops_raw_and_pending_from_items_at_a_section(self):
        cell = "; ".join([story(W, "how-it-works", "Widget › How it works", "it sorts", "raw"),
                          story(W, "dead-ends-and-mistakes", marker="core, pending, raw"),
                          story(G, "context", marker="raw")])
        late = "[Widget](%s#how-it-works) *(raw, pending)* — late; %s *(pending)*" % (W, story(W, "context"))
        self.write("stories.md", index(("Debugging", cell), ("Proudest \\| best", late),
                                       ("Conflict", story(W, "how-it-works", marker="core"))))
        code, lines = self.finish()
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, [
            "dropped: Debugging: raw: [Widget › How it works](%s#how-it-works) — it sorts" % W,
            "dropped: Debugging: pending, raw: *(core)* [Widget](%s#dead-ends-and-mistakes)" % W,
            "dropped: Proudest | best: raw, pending: [Widget](%s#how-it-works) — late" % W,
            "dropped: Proudest | best: pending: [Widget](%s#context)" % W,
            "OK: 4 items edited"])
        text = self.stories_md()
        self.assertIn("| Debugging | [Widget › How it works](%s#how-it-works) — it sorts; *(core)* [Widget](%s"
                      "#dead-ends-and-mistakes); *(raw)* [Widget](%s#context) |\n" % (W, W, G), text)
        self.assertIn("| Proudest \\| best | [Widget](%s#how-it-works) — late; [Widget](%s#context) |\n" % (W, W), text)
        self.assertIn("| Conflict | *(core)* [Widget](%s#how-it-works) |\n" % W, text)
        self.assertIn("| Disagreement / conflict | shared | |", text)   # the second table is not read
        self.assertEqual(self.finish(), (0, ["OK: 0 items edited"]))

    def test_findings_are_left_as_they_are(self):
        cell = "; ".join([story(W, "pending", marker="pending"), story(W, marker="raw"), story(W, "gone", marker="raw"),
                          story(W, "pending"), story("sources/resumes/cv-2031.pdf", label="CV", marker="raw"),
                          story("sources/resumes/cv-2030.pdf", label="Old CV", marker="raw"),
                          story("sources/resumes/cv-2031.pdf", label="CV")])
        self.write("stories.md", index(("Debugging", cell)))
        before = self.stories_md()
        code, lines = self.finish()
        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "links no section: Debugging: *(pending)* [Widget](%s#pending)" % W,
            "links no section: Debugging: *(raw)* [Widget](%s)" % W,
            "links no section: Debugging: *(raw)* [Widget](%s#gone)" % W,
            "links no section: Debugging: [Widget](%s#pending)" % W,
            "raw source: Debugging: sources/resumes/cv-2031.pdf: *(raw)* [CV](sources/resumes/cv-2031.pdf)"])
        self.assertEqual(self.stories_md(), before)

    def test_keeps_bom_and_crlf(self):
        text = "﻿" + index(("Debugging", story(W, "how-it-works", marker="raw"))).replace("\n", "\r\n")
        self.write("stories.md", text)
        code, lines = self.finish()
        self.assertEqual(code, 0, lines)
        with open(os.path.join(self.root, "stories.md"), "rb") as f:
            self.assertEqual(f.read(), text.replace("*(raw)* ", "").encode("utf-8"))

    def test_no_index(self):
        self.assertEqual(self.finish(), (1, ["no story index: no stories.md"]))
        self.write("stories.md", "# Stories\n")
        code, lines = self.finish()
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("no story index: "), lines)
        self.assertEqual(self.run_tool("story-finish", "stories.md", "--root", self.root)[0], 2)

    def test_edits_and_findings_in_one_run(self):
        # a row with no closing |, an encoded and capitalised anchor, a marker written twice, a ../sources link
        self.write(W, entry() + self.BODY + "\n## 背景\nSee [the CV](../sources/resumes/cv-2032.md).\n"
                   "\n```\n## Fenced\n```\n")
        self.write("stories.md", "| Question type | Stories |\n|---|---|\n"
                   "| Debugging | %s |\n| Learning | %s |\n| Proudest | *(raw)* *(raw)* %s; %s; %s\n"
                   % (story(W, "Context", marker="raw"), story(W, "%E8%83%8C%E6%99%AF", marker="raw, pending"),
                      story(W, "how-it-works"), story(W, "fenced", marker="raw"),
                      story("sources/resumes/cv-2032.md", label="CV", marker="raw")))
        code, lines = self.finish()
        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "dropped: Debugging: raw: [Widget](%s#Context)" % W,
            "dropped: Learning: raw, pending: [Widget](%s#%%E8%%83%%8C%%E6%%99%%AF)" % W,
            "dropped: Proudest: raw: [Widget](%s#how-it-works)" % W,
            "links no section: Proudest: *(raw)* [Widget](%s#fenced)" % W,
            "raw source: Proudest: sources/resumes/cv-2032.md: *(raw)* [CV](sources/resumes/cv-2032.md)"])
        text = self.stories_md()
        self.assertIn("| Debugging | [Widget](%s#Context) |\n" % W, text)
        self.assertIn("| Proudest | [Widget](%s#how-it-works); *(raw)* [Widget](%s#fenced); *(raw)* [CV]" % (W, W), text)

    def test_heading_anchors(self):
        self.assertEqual(entries.heading_anchors("# A b\n## Lessons\n## Lessons\n### C/D: e?\n<!-- ## X -->\n"
                                                 "~~~md\n## Y\n~~~\n````\n```\n## Z\n````\n## A b\n```\n## Open\n"),
                         {"lessons", "lessons-1", "cd-e", "a-b-1"})


def answers(*rows):
    """stories.md with a one-row Story index and an Application questions table of the given rows."""
    return ("# Story index\n\n| Question type | Stories |\n|---|---|\n| Debugging | |\n\n## Application questions\n"
            "<!-- the scopes -->\n\n| Question type | Scope | Answer from | User's direction | Approved answer |\n"
            "|---|---|---|---|---|\n%s" % "".join("| %s | %s | | | %s |\n" % r for r in rows))


class StoryWriteTest(Log):
    BODY = "\n## Dead ends and mistakes\nA hunt.\n\n## Pending\n- 2031-06-01: fixed it.\n"

    def setUp(self):
        super().setUp()
        self.write(W, entry(title="Widget | Sorter [v2]") + self.BODY)
        self.write(G, entry(title="Gadget", series="gadget") + self.BODY)
        self.write(S, entry(title="Gadget 2", series="gadget") + self.BODY)
        self.write("sources/resumes/cv-2031.pdf", "%PDF")

    def tool(self, *args):
        return self.run_tool(*(args[:1] + ("--root", self.root) + args[1:]))

    def read(self, path="stories.md"):
        with open(os.path.join(self.root, path), "rb") as f:
            return f.read()

    def test_story_add_writes_the_index_format(self):
        self.write("stories.md", index(("Debugging", "*(toy)* [X](entries/x.md) — a summary; a note"), ("Proudest", "")))
        code, lines = self.tool("story-add", "Debugging", W + "#dead-ends-and-mistakes", "--summary", "a | b; c")
        self.assertEqual(code, 0, lines)
        item = "[Widget \\| Sorter [v2\\] › Dead ends and mistakes](%s#dead-ends-and-mistakes) — a \\| b; c" % W
        self.assertEqual(lines, ["added: Debugging: " + item])
        self.assertIn("| Debugging | *(toy)* [X](entries/x.md) — a summary; a note; %s |\n" % item, self.read().decode())
        row = entries.story_index(self.root)[0]
        self.assertEqual((row.stories[-1].key, row.stories[-1].summary), (W + "#dead-ends-and-mistakes", "a | b; c"))
        self.assertEqual(row.stories[-1].label, "Widget | Sorter [v2\\] › Dead ends and mistakes")
        before = self.read()
        self.assertEqual(self.tool("story-add", "Debugging", W + "#Dead-ends-and-mistakes", "--marker", "core"),
                         (0, ["already linked: Debugging: " + item.replace("\\|", "|")]))
        self.assertEqual(self.read(), before)
        code, lines = self.tool("story-add", "Proudest", W + "#pending", "--summary", "fixed it")
        self.assertEqual(lines, ["added: Proudest: *(pending)* [Widget \\| Sorter [v2\\] › Pending](%s#pending)"
                                 " — fixed it" % W])
        self.assertIn(b"| Proudest | *(pending)* [", self.read())

    def test_story_add_markers_sources_and_refusals(self):
        self.write("stories.md", index(("Debugging", "")))
        code, lines = self.tool("story-add", "Debugging", "sources/resumes/cv-2031.pdf", "--marker", "raw",
                                "--marker", "core", "--label", "CV › the outage")
        self.assertEqual(lines, ["added: Debugging: *(raw, core)* [CV › the outage](sources/resumes/cv-2031.pdf)"])
        self.assertEqual(self.tool("story-add", "Debugging", G, "--marker", "raw")[1],
                         ["added: Debugging: *(raw)* [Gadget](%s)" % G])
        before = self.read()
        for args in [("Debugging", W + "#gone"), ("Debugging", "entries/2031-09-none.md"), ("Nope", W),
                     ("Debugging", "sources/resumes/cv-2031.pdf"), ("Debugging", "direction.md"),
                     ("Debugging", W, "--marker", "toy"), ("Debugging", W, "--summary", "a; [b](x)"),
                     ("Debugging", W, "--summary", "a; *(raw)* b"), ("Debugging", W, "--summary", "two\nlines"),
                     ("Debugging", "sources/resumes/My CV.pdf", "--label", "CV")]:
            code, lines = self.tool("story-add", *args)
            self.assertEqual(code, 2, (args, lines))
            self.assertTrue(lines[0].startswith("FAIL: "), lines)
        self.assertEqual(self.tool("story-add", "Debugging")[0], 2)
        self.assertEqual(self.read(), before)

    def test_story_add_keeps_bom_crlf_and_other_cells(self):
        text = "﻿" + index(("Debugging", story(G, marker="raw, pending")), ("Proudest", "")).replace("\n", "\r\n")
        self.write("stories.md", text)
        self.assertEqual(self.tool("story-add", "Debugging", W)[0], 0)
        expected = text.replace(story(G, marker="raw, pending") + " |",
                                story(G, marker="raw, pending") + "; [Widget \\| Sorter [v2\\]](%s) |" % W)
        self.assertEqual(self.read(), expected.encode("utf-8"))

    def test_story_add_to_a_row_with_no_closing_pipe(self):
        self.write("stories.md", "| Question type | Stories |\n|---|---|\n| Debugging | %s\n| Proudest |" % story(G))
        self.assertEqual(self.tool("story-add", "Debugging", S)[0], 0)
        self.assertEqual(self.tool("story-add", "Proudest", S)[0], 0)
        self.assertEqual(self.read().decode(), "| Question type | Stories |\n|---|---|\n| Debugging | %s; "
                         "[Gadget 2](%s)\n| Proudest | [Gadget 2](%s) |" % (story(G), S, S))

    def test_story_add_after_a_trailing_separator(self):
        self.write("stories.md", index(("Debugging", story(G) + ";")))
        self.assertEqual(self.tool("story-add", "Debugging", S)[0], 0)
        self.assertIn("| Debugging | %s; [Gadget 2](%s) |" % (story(G), S), self.read().decode())
        self.write("stories.md", index(("Debugging", story(G, summary="R&amp;"))))   # an entity's `;` stays
        self.assertEqual(self.tool("story-add", "Debugging", S)[0], 0)
        self.assertIn("| Debugging | %s; [Gadget 2](%s) |" % (story(G, summary="R&amp;"), S), self.read().decode())

    def test_story_type_add(self):
        self.write("stories.md", "﻿" + index(("Debugging", story(G))).replace("\n", "\r\n"))
        code, lines = self.tool("story-type-add", "Working with AI agents")
        self.assertEqual((code, lines), (0, ["added: stories.md:8: | Working with AI agents | |"]))
        self.assertIn("| Debugging | %s |\r\n| Working with AI agents | |\r\n\r\n## Application" % story(G),
                      self.read().decode("utf-8-sig"))
        self.assertEqual([r.type for r in entries.story_index(self.root)], ["Debugging", "Working with AI agents"])
        before = self.read()
        for bad in ("debugging", "A | B", "A; B", "Tell me [about] it", "", " padded", '"quoted"', "two\nlines"):
            code, lines = self.tool("story-type-add", bad)
            self.assertEqual(code, 2, (bad, lines))
        self.assertEqual(self.read(), before)

    def test_story_type_add_to_an_index_with_no_rows(self):
        self.write("stories.md", "| Question type | Stories |\n|---|---|")
        self.assertEqual(self.tool("story-type-add", "Debugging")[0], 0)
        self.assertEqual(self.read(), b"| Question type | Stories |\n|---|---|\n| Debugging | |")

    def test_story_core_on_and_off_across_a_series(self):
        self.write("stories.md", index(("A", story(W) + "; " + story(G, "context", marker="raw")),
                                       ("B", story(S, "pending", marker="pending")), ("C", "")))
        self.assertEqual(self.tool("story-core", S, "on"), (0, ["core on: B: *(pending, core)* [Widget](%s#pending)" % S]))
        before = self.read()
        self.assertEqual(self.tool("story-core", G, "on")[1], ["already core: B: *(pending, core)* [Widget](%s#pending)" % S])
        self.assertEqual(self.read(), before)
        self.assertEqual(self.tool("story-core", W, "on")[1], ["core on: A: *(core)* [Widget](%s)" % W])
        lines = self.run_tool("story-coverage", "--root", self.root)[1]
        self.assertEqual(lines[0], "core stories: 2; %s (1 types); %s (2 types)" % (W, G))
        # off takes core from every item of every part
        self.write("stories.md", index(("A", story(G, "context", marker="core, raw") + " *(core)*"),
                                       ("B", "[x](%s) *(core)* — y; %s" % (S, story(W, marker="core")))))
        code, lines = self.tool("story-core", S, "off")
        self.assertEqual(lines, ["core off: A: *(raw)* [Widget](%s#context)" % G, "core off: B: [x](%s) — y" % S])
        self.assertIn("| B | [x](%s) — y; %s |" % (S, story(W, marker="core")), self.read().decode())
        self.assertEqual(self.tool("story-core", G, "off"), (0, ["not core: %s" % G]))
        self.assertEqual(self.tool("story-core", "entries/2031-05-plinth.md", "on")[0], 2)   # no such entry
        self.write(P, entry())
        self.assertEqual(self.tool("story-core", P, "on"),
                         (1, ["not indexed: %s (index one of its Stories with story-add first)" % P]))
        self.assertEqual(self.tool("story-core", W, "maybe")[0], 2)

    def test_story_confirm(self):
        self.write("stories.md", "﻿" + index(("Debugging", story(W)), ("Old", "x")).replace("\n", "\r\n"))
        self.write("stories/debugging.md", talking("Debugging", "2031-01-01", W).replace("\n", "\r\n"))
        code, lines = self.tool("story-confirm", "stories/debugging.md", "--type", "Debugging")
        self.assertEqual(code, 0, lines)
        self.assertRegex(lines[0], r"^confirmed: stories/debugging\.md: \d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        self.assertEqual(lines[1], "row linked: Debugging: stories/debugging.md")
        tp = self.read("stories/debugging.md").decode()
        self.assertRegex(tp, r"\r\nconfirmed: \d{4}-\d{2}-\d{2} \d{2}:\d{2}\r\norder:")
        self.assertIn("| [Debugging](stories/debugging.md) | %s |\r\n" % story(W), self.read().decode("utf-8-sig"))
        self.assertTrue(self.read().startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("talking points", "\n".join(self.run_tool("story-coverage", "--root", self.root)[1]))
        code, lines = self.tool("story-confirm", "stories/debugging.md", "--type", "Debugging")
        self.assertEqual(lines[1], "row already links: Debugging: stories/debugging.md")
        # a reconfirm alone; a type that differs, or a row that links another file, writes nothing
        self.assertEqual(self.tool("story-confirm", "stories/debugging.md")[0], 0)
        self.write("stories/old.md", talking("Old", "2031-01-01", W))
        before = (self.read(), self.read("stories/old.md"))
        self.assertEqual(self.tool("story-confirm", "stories/old.md", "--type", "Debugging"),
                         (1, ["type differs: stories/old.md: type Old, --type Debugging (write the row's type in its"
                              " type: line)"]))
        self.write("stories/debugging-2.md", talking("Debugging", "2031-01-01", W))
        self.assertEqual(self.tool("story-confirm", "stories/debugging-2.md", "--type", "Debugging")[1],
                         ["row links another file: Debugging: stories/debugging.md"])
        self.assertEqual((self.read(), self.read("stories/old.md")), before)
        self.assertEqual(self.tool("story-confirm", "stories/old.md", "--type", "Old", "--type", "Old")[0], 2)
        self.assertEqual(self.tool("story-confirm", "stories/none.md")[0], 2)

    def test_story_confirm_adds_a_missing_line(self):
        self.write("stories.md", index(("Debugging", story(W))))
        self.write("stories/debugging.md", "---\ntype: Debugging\n---\n\n# Debugging\n")
        self.assertEqual(self.tool("story-confirm", "stories/debugging.md")[0], 0)
        self.assertRegex(self.read("stories/debugging.md").decode(), r"^---\ntype: Debugging\nconfirmed: \d{4}-[^\n]+\n---\n")
        self.write("stories/bare.md", "# Bare\n")
        self.assertEqual(self.tool("story-confirm", "stories/bare.md")[0], 2)


class AnswerRowTest(Log):
    ROWS = (("Why us", "per-company", ""), ("Pronunciation", "shared", "[answer](outputs/reports/a.md)"),
            ("Proudest", "per-angle", "ai-infra: [A](outputs/reports/a.md); general: [G](outputs/reports/g.md); "
                                      "backend: [B](outputs/reports/b.md)"),
            ("No scope", "", ""))

    def setUp(self):
        super().setUp()
        for name in ("a", "b", "g", "n"):
            self.write("outputs/reports/%s.md" % name, "x")
        self.write("outputs/applications/2031-06-01-acme/answers.md", "x")

    def tool(self, *args):
        return self.run_tool(*(args[:1] + ("--root", self.root) + args[1:]))

    def read(self):
        with open(os.path.join(self.root, "stories.md"), "rb") as f:
            return f.read()

    def test_answer_row(self):
        self.write("stories.md", answers(*self.ROWS))
        code, lines = self.tool("answer-row", "Proudest", "--angle", "backend")
        self.assertEqual((code, lines), (0, ["row: Proudest; scope per-angle", "answer from: -", "direction: -",
                                             "pointer: backend: outputs/reports/b.md; label B",
                                             "pointer: general: outputs/reports/g.md; label G"]))
        self.assertEqual(self.tool("answer-row", "Proudest", "--angle", "data")[1][3:],
                         ["pointer: general: outputs/reports/g.md; label G"])
        self.assertEqual(len(self.tool("answer-row", "Proudest")[1]), 6)
        self.assertEqual(self.tool("answer-row", "Pronunciation", "--angle", "x")[1][3:],
                         ["pointer: -: outputs/reports/a.md; label answer"])
        self.assertEqual(self.tool("answer-row", "Why us")[1][3:], ["pointer: none"])
        self.write("stories.md", answers(("Proudest", "per-angle", "ai-infra: [A](outputs/reports/a.md)")))
        self.assertEqual(self.tool("answer-row", "Proudest", "--angle", "general")[1][3:], ["pointer: none for general"])
        self.write("stories.md", answers(*self.ROWS))
        self.assertEqual(self.tool("answer-row", "Why them"),
                         (0, ["no row: Why them", "row types: Why us | Pronunciation | Proudest | No scope"]))
        self.write("stories.md", index(("Debugging", "")).split("## Application")[0])
        self.assertEqual(self.tool("answer-row", "Why us")[1],
                         ["no row: Why us (stories.md has no Application questions table)"])

    def test_answer_row_add(self):
        self.write("stories.md", answers(*self.ROWS).replace("\n", "\r\n"))
        code, lines = self.tool("answer-row-add", "Tell us about yourself", "--scope", "per-angle")
        self.assertEqual((code, lines), (0, ["added: stories.md:16: | Tell us about yourself | per-angle | | | |"]))
        self.assertTrue(self.read().endswith(b"|\r\n| Tell us about yourself | per-angle | | | |\r\n"))
        self.assertEqual(self.tool("answer-row", "Tell us about yourself")[1][0], "row: Tell us about yourself; scope per-angle")
        before = self.read()
        self.assertEqual(self.tool("answer-row-add", "why us", "--scope", "shared")[0], 2)
        self.assertEqual(self.tool("answer-row-add", "New", "--scope", "per-role")[0], 2)
        self.assertEqual(self.tool("answer-row-add", "New")[0], 2)
        self.assertEqual(self.read(), before)

    def test_answer_set_per_angle(self):
        text = answers(*self.ROWS)
        self.write("stories.md", text)
        code, lines = self.tool("answer-set", "Proudest", "--angle", "general", "outputs/reports/n.md")
        self.assertEqual(lines, ["replaced: Proudest: general: [G](outputs/reports/g.md)",
                                 "set: Proudest: general: [answer](outputs/reports/n.md)"])
        cell = "ai-infra: [A](outputs/reports/a.md); general: [answer](outputs/reports/n.md); backend: [B](outputs/reports/b.md)"
        self.assertEqual(self.read().decode(), text.replace(self.ROWS[2][2], cell))   # the order kept, one cell changed
        self.assertEqual(self.tool("answer-set", "Proudest", "--angle", "general", "./outputs/reports/n.md"),
                         (0, ["unchanged: Proudest: general: [answer](outputs/reports/n.md)"]))
        self.assertEqual(self.tool("answer-set", "Proudest", "--angle", "data", "outputs/reports/n.md")[1],
                         ["set: Proudest: data: [answer](outputs/reports/n.md)"])
        self.assertIn(cell + "; data: [answer](outputs/reports/n.md) |", self.read().decode())
        # two pointers for one angle become one, where the first was
        self.write("stories.md", answers(("Proudest", "per-angle", "x: [1](outputs/reports/a.md); y: [2](outputs/reports/b.md);"
                                                                   " x: [3](outputs/reports/g.md)")))
        self.tool("answer-set", "Proudest", "--angle", "x", "outputs/reports/n.md")
        self.assertIn("| x: [answer](outputs/reports/n.md); y: [2](outputs/reports/b.md) |", self.read().decode())
        self.assertEqual(self.tool("answer-set", "Proudest", "outputs/reports/n.md")[0], 2)   # no --angle
        self.assertEqual(self.tool("answer-set", "Proudest", "--angle", "x", "outputs/reports/none.md")[0], 2)
        self.assertEqual(self.tool("answer-set", "Proudest", "--angle", "X Y", "outputs/reports/n.md")[0], 2)

    def test_answer_set_shared_per_company_and_no_scope(self):
        self.write("stories.md", answers(*self.ROWS))
        code, lines = self.tool("answer-set", "Pronunciation", "--angle", "backend", "outputs/reports/n.md")
        self.assertEqual(lines, ["replaced: Pronunciation: [answer](outputs/reports/a.md)",
                                 "set: Pronunciation: [answer](outputs/reports/n.md)"])
        self.assertIn("| Pronunciation | shared | | | [answer](outputs/reports/n.md) |", self.read().decode())
        self.write("stories.md", answers(("Pronunciation", "shared", "[1](outputs/reports/a.md); [2](outputs/reports/b.md)")))
        self.tool("answer-set", "Pronunciation", "outputs/reports/n.md")
        self.assertIn("| Pronunciation | shared | | | [answer](outputs/reports/n.md) |", self.read().decode())
        self.write("stories.md", answers(("Pronunciation", "shared", "[1](outputs/reports/a.md); [1](outputs/reports/a.md)")))
        self.tool("answer-set", "Pronunciation", "outputs/reports/n.md")   # identical copies leave one pointer
        self.assertIn("| Pronunciation | shared | | | [answer](outputs/reports/n.md) |", self.read().decode())
        self.write("stories.md", answers(*self.ROWS))
        before = self.read()
        self.assertEqual(self.tool("answer-set", "Why us", "outputs/reports/n.md"),
                         (1, ["per-company row takes no pointer: Why us"]))
        self.assertEqual(self.tool("answer-set", "No scope", "outputs/reports/n.md"),
                         (1, ["no scope: No scope: - (one of shared, per-angle, per-company)"]))
        self.assertEqual(self.tool("answer-set", "Missing", "outputs/reports/n.md")[0], 1)
        self.assertEqual(self.read(), before)

    def test_answer_set_remove(self):
        self.write("stories.md", answers(*self.ROWS, ("Excites", "per-angle",
                                                      "x: [A](outputs/applications/2031-06-01-acme/answers.md); "
                                                      "y: [A](outputs/applications/2031-06-01-acme/answers.md)")))
        self.assertEqual(self.tool("answer-set", "Excites", "--angle", "x", "--remove", "outputs/applications/2031-06-01-acme")[1],
                         ["removed: Excites: x: [A](outputs/applications/2031-06-01-acme/answers.md)"])
        self.assertIn("| Excites | per-angle | | | y: [A](outputs/applications/2031-06-01-acme/answers.md) |", self.read().decode())
        self.assertEqual(self.tool("answer-set", "Proudest", "--angle", "backend", "--remove", "outputs/reports/a.md"),
                         (0, ["not linked: Proudest: outputs/reports/a.md"]))   # backend's pointer links b.md
        self.tool("answer-set", "Proudest", "--remove", "outputs/reports/a.md")   # any angle's, without --angle
        self.assertIn("| Proudest | per-angle | | | general: [G](outputs/reports/g.md); backend: [B](outputs/reports/b.md) |",
                      self.read().decode())
        self.tool("answer-set", "Pronunciation", "--remove", "outputs/reports/a.md")
        self.assertIn("| Pronunciation | shared | | | |", self.read().decode())

    def test_writes_keep_odd_cells_as_they_are(self):
        # a marker after the link, `*(raw, pending)*`, CRLF and BOM, a bare `;` in a summary, angles out of order
        odd = ("﻿# Story index\r\n\r\n| Question type | Stories |\r\n|---|---|\r\n"
               "| Debugging | [W](%s#context) *(raw, pending)* — a; b ;c |\r\n| Proudest |  *(core)*  [W](%s)  |\r\n"
               "\r\n## Application questions\r\n\r\n| Question type | Scope | Answer from | User's direction | Approved answer |\r\n"
               "|:--|--|--|--|--:|\r\n| Proudest | per-angle | [W](%s) |  | zeta: [z](outputs/reports/a.md);  alpha: [a](outputs/reports/b.md) |\r\n"
               "| Why us | per-company |  |  |  |\r\n" % (W, W, W))
        self.write(W, entry())
        self.write("stories.md", odd)
        self.assertEqual(self.tool("answer-set", "Proudest", "--angle", "mid", "outputs/reports/g.md")[0], 0)
        self.assertEqual(self.tool("story-type-add", "Leading a team")[0], 0)
        self.assertEqual(self.tool("story-add", "Debugging", W)[0], 0)
        self.assertEqual(self.tool("story-core", W, "off")[0], 0)
        new = self.read().decode("utf-8")
        old_lines, new_lines = odd.split("\r\n"), new.split("\r\n")
        changed = [(a, b) for a, b in zip(old_lines, new_lines[:6] + new_lines[7:]) if a != b]
        self.assertEqual(new_lines[6], "| Leading a team | |")
        self.assertEqual(changed, [
            (old_lines[4], "| Debugging | [W](%s#context) *(raw, pending)* — a; b ;c; [Widget Sorter](%s) |" % (W, W)),
            (old_lines[5], "| Proudest | [W](%s) |" % W),
            (old_lines[11], "| Proudest | per-angle | [W](%s) |  | zeta: [z](outputs/reports/a.md);  alpha: "
                            "[a](outputs/reports/b.md); mid: [answer](outputs/reports/g.md) |" % W)])

    def test_story_coverage_findings_behind_flags(self):
        for path in FIVE:
            self.write(path, entry())
        cells = [[(FIVE[i], "a", "core"), (FIVE[(i + 1) % 5], "b", "")] for i in range(5)]
        rows = [("T%d" % n, "; ".join(story(p, a, marker=m) for p, a, m in c)) for n, c in enumerate(cells)]
        stories_md = index(*rows).split("## Application")[0] + answers(
            ("A", "shared", "[1](outputs/reports/a.md); [2](outputs/reports/b.md)"), ("B", "per-company", "[1](outputs/reports/a.md)"),
            ("C", "per-angle", "x: [1](outputs/reports/a.md); x: [2](outputs/reports/b.md); [3](outputs/reports/g.md)"),
            ("D", "sometimes", ""), ("E", "per-angle", "x: [1](outputs/reports/a.md); y: [2](outputs/reports/b.md)"),
            ("F", "shared", "[1](outputs/reports/a.md)")).split("\n\n", 1)[1].split("| Debugging | |\n\n", 1)[1]
        self.write("stories.md", stories_md)
        self.write("stories/t0.md", "---\ntype: T0\nconfirmed: 2031-06-01\n---\n\n## Opening\nI.\n\n## Stories\n1. [S](../%s)\n\n"
                   "## Cue lines\n%s" % (W, "".join("- c%d\n" % n for n in range(8))))
        self.write("stories.md", stories_md.replace("| T0 |", "| [T0](stories/t0.md) |"))
        code, lines = self.run_tool("story-coverage", "--root", self.root)
        self.assertEqual((code, lines[-1]), (0, "OK: 5 question types, no findings"))
        code, lines = self.run_tool("story-coverage", "--root", self.root, "--application-questions")
        self.assertEqual(code, 1)
        self.assertEqual(lines[2:], [
            "application question: A: shared row with 2 pointers",
            "application question: B: per-company row with 1 pointers",
            "application question: C: per-angle pointer with no angle: [3](outputs/reports/g.md)",
            "application question: C: per-angle row with 2 pointers for x",
            "application question: D: no scope (shared, per-angle, per-company): sometimes"])
        code, lines = self.run_tool("story-coverage", "--root", self.root, "--talking-points")
        self.assertEqual(lines[2:], ["talking points sections out of order: stories/t0.md: Opening | Stories | Cue lines",
                                     "talking points over 7 cue lines: stories/t0.md: 8"])


TEMPLATE = os.path.join(HERE, "..", "..", "entries", "_template.md")
NEW_W = "entries/2031-04-widget.md"


class WriteLog(Log):
    """A Log with the real entries/_template.md and the Template's empty Entries table."""

    def setUp(self):
        super().setUp()
        shutil.copy(TEMPLATE, os.path.join(self.root, "entries", "_template.md"))
        self.write("README.md", "# Log\n\n## Entries\n\n| Period | Entry | Type | Tags | Status |\n|---|---|---|---|---|\n"
                   "\n## Upstream\n")

    def read(self, path):
        with open(os.path.join(self.root, path), encoding="utf-8", newline="") as f:
            return f.read()

    def tool(self, *args):
        return self.run_tool(*(args[:1] + ("--root", self.root) + args[1:]))

    def new(self, slug="widget", month="2031-04", period="2031-04 – ongoing", *more, status="stub"):
        return self.tool("new", slug, "--month", month, "--status", status, "--field", "title=Widget Sorter",
                         "--field", "period=%s" % period, "--today", "2031-04-20", *more)

    def rows(self):
        return [l for l in self.read("README.md").splitlines() if "](entries/" in l]


class NewTest(WriteLog):
    def test_writes_the_template_with_gaps_and_a_readme_row(self):
        code, lines = self.new("widget", "2031-04", "GAP – ongoing", "--field", "tags=go, kafka",
                               "--field", "org=personal")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["created: %s" % NEW_W, "readme row added: README.md:7: | GAP – ongoing | [Widget Sorter]"
                                 "(%s) | GAP: type | go, kafka | stub |" % NEW_W])
        text = self.read(NEW_W)
        e = entries.Entry(self.root, NEW_W)
        self.assertEqual((e.fields["title"], e.fields["org"], e.fields["my_role"], e.fields["visibility"],
                          e.tags, e.fields["links"], e.fields["series"], e.fields["last_updated"], e.period),
                         ("Widget Sorter", "personal", "GAP: role title", "GAP", ["go", "kafka"], [], "",
                          "2031-04-20", "GAP – ongoing"))
        self.assertIn("my_role: GAP: role title    # title, plus the role actually played\n", text)
        self.assertIn("visibility: GAP             # public | private | nda\n", text)
        self.assertIn("\n# Widget Sorter\n", text)
        self.assertIn("<!-- If you could say one sentence about this, what would it be? -->\nGAP:\n", text)
        self.assertIn("- **I did:** GAP:\n- **I led, with help from:** GAP:\n", text)
        # #271: the tables, Past phrasings, Conflicts and Pending stay as the template has them
        template = self.read("entries/_template.md")
        for heading in ("Decisions and trade-offs", "Results and evidence", "Past phrasings", "Conflicts", "Pending"):
            self.assertEqual(entries.logfiles.section(text, heading), entries.logfiles.section(template, heading), heading)
        self.assertEqual(text.count("GAP:\n"), 7 + 3)
        self.assertEqual(self.check(), (0, ["OK: 1 entries, no findings"]))

    def test_a_new_entry_is_mostly_gap_with_every_key_section_empty(self):
        self.new()
        code, lines = self.tool("state", NEW_W, "--today", "2031-04-20")
        self.assertEqual(code, 0)
        self.assertEqual(lines[0], "state: %s: gaps 15; gap sections 10 of 10; pending 0" % NEW_W)
        self.assertEqual(lines[2:5], ["key section empty: %s: %s" % (NEW_W, s) for s in entries.KEY_SECTIONS])
        self.assertEqual(lines[5], "blocking gaps: %s: My contribution (3 GAP), Results and evidence (empty),"
                                   " Likely questions (1 GAP)" % NEW_W)
        self.assertTrue(lines[6].startswith("suggest consolidate: %s: mostly GAP (10 of 10 sections); key section"
                                            " empty: One line" % NEW_W), lines[6])

    def test_refuses_an_existing_file(self):
        self.new()
        before = self.read(NEW_W)
        code, lines = self.new()
        self.assertEqual((code, lines), (1, ["exists: %s (nothing written; extend it, or pick another slug)" % NEW_W]))
        self.assertEqual(self.read(NEW_W), before)
        self.assertEqual(len(self.rows()), 1)

    def test_visibility_takes_its_source_as_the_only_comment(self):
        self.assertEqual(self.new("a", "2031-04", "2031-04 – ongoing", "--field", "visibility=public")[0], 2)
        self.new("a", "2031-04", "2031-04 – ongoing", "--field", "visibility=public",
                 "--visibility-source", "https://github.com/u/a")
        text = self.read("entries/2031-04-a.md")
        self.assertIn("visibility: public          # (https://github.com/u/a)\n", text)
        self.assertIn("period: 2031-04 – ongoing   # or", text)   # only visibility's comment changes

    def test_a_field_the_user_stated_cites_them(self):
        # #370: --field-source writes the source as the field's comment, and check reads the value without it
        code, lines = self.new("a", "2031-04", "2031-04 – ongoing", "--field", "my_role=Backend intern, led the queue",
                               "--field-source", "my_role=user, 2031-04-20", "--field", "tags=go, kafka",
                               "--field-source", "tags=user, 2031-04-20", "--field", "org=Acme #1, Inc",
                               "--field-source", "org=user, 2031-04-20", "--field", "visibility=nda",
                               "--field-source", "visibility=user, 2031-04-20")
        self.assertEqual(code, 0, lines)
        text = self.read("entries/2031-04-a.md")
        self.assertIn("my_role: Backend intern, led the queue  # (user, 2031-04-20)\n", text)
        self.assertIn("tags: [go, kafka]           # (user, 2031-04-20)\n", text)
        self.assertIn('org: "Acme #1, Inc"         # (user, 2031-04-20)\n', text)
        self.assertIn("visibility: nda             # (user, 2031-04-20)\n", text)
        self.assertIn("collaborators: GAP: collaborators  # name", text)   # a field with no source keeps the template's
        e = entries.Entry(self.root, "entries/2031-04-a.md")
        self.assertEqual((e.fields["my_role"], e.tags, e.fields["org"], e.fields["visibility"]),
                         ("Backend intern, led the queue", ["go", "kafka"], "Acme #1, Inc", "nda"))
        self.assertEqual(self.check(), (0, ["OK: 1 entries, no findings"]))
        for more in (["--field-source", "my_role=user, 2031-04-20"],   # no --field my_role
                     ["--field", "period=2031-04 – ongoing", "--field-source", "period=user, 2031-04-20"],
                     ["--field", "my_role=Lead", "--field-source", "my_role="],
                     ["--field", "my_role=Lead", "--field-source", "my_role=a", "--field-source", "my_role=b"],
                     ["--field", "visibility=nda", "--visibility-source", "a", "--field-source", "visibility=b"]):
            self.assertEqual(self.new("b", "2031-04", "2031-04 – ongoing", *more)[0], 2, more)
        self.assertFalse(os.path.exists(os.path.join(self.root, "entries", "2031-04-b.md")))

    def test_bad_arguments(self):
        for more in (["--field", "period=soon"], ["--field", "type=job"], ["--field", "colour=red"],
                     ["--field", "series=Not A Slug"], ["--field", "visibility=secret"]):
            self.assertEqual(self.new("a", "2031-04", "2031-04 – ongoing", *more)[0], 2, more)
        self.assertEqual(self.new("Bad Slug")[0], 2)
        self.assertEqual(self.new("a", "2031-13")[0], 2)
        self.assertEqual(self.new("a", status="consolidated")[0], 2)
        self.assertEqual(self.tool("new", "a", "--month", "2031-04", "--status", "stub", "--field", "period=2031-04")[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "entries", "2031-04-a.md")))

    def test_quotes_a_title_the_front_matter_would_cut(self):
        self.tool("new", "a", "--month", "2031-04", "--status", "stub", "--field", "title=Sorter #2 | fast",
                  "--field", "period=2031-04")
        e = entries.Entry(self.root, "entries/2031-04-a.md")
        self.assertEqual(e.fields["title"], "Sorter #2 | fast")
        self.assertEqual(self.check()[0], 0, self.check())


class ReadmeTest(WriteLog):
    PERIODS = [("2031-04-a", "2031-04 – 2031-05"), ("2030-01-b", "2030-01 – ongoing"), ("2029-01-c", "GAP – 2029-06"),
               ("2031-01-d", "2031-01 – 2031-05"), ("2032-01-e", "2032-01 – ongoing"), ("2028-01-f", "2028-01 – 2028-02"),
               ("2031-05-g", "2031-05-14 – 2031-05-20")]
    ORDER = ["2029-01-c", "2032-01-e", "2030-01-b", "2031-05-g", "2031-04-a", "2031-01-d", "2028-01-f"]

    def test_row_order(self):
        periods = [p for _, p in self.PERIODS] + ["GAP – ongoing", "soon"]
        ordered = [p for _, p in entries.sort_rows([(p, p) for p in periods])]
        self.assertEqual(ordered, ["GAP – 2029-06", "GAP – ongoing", "soon", "2032-01 – ongoing", "2030-01 – ongoing",
                                   "2031-05-14 – 2031-05-20", "2031-04 – 2031-05", "2031-01 – 2031-05", "2028-01 – 2028-02"])

    SERIES = [("2029-01-y", "2029-01 – 2029-06", None), ("2028-01-big", "2028-01 – 2029-03", "big"),
              ("2031-01-x", "2031-01 – 2031-03", None), ("2026-01-run", "2026-01 – 2027-01", "run"),
              ("2027-05-gap-two", "2027-05 – 2027-09", "gap"), ("2029-03-big-two", "2029-03 – 2030-12", "big"),
              ("2028-01-z", "GAP – 2028-01", None), ("2027-01-run-two", "2027-01 – ongoing", "run"),
              ("2030-01-w", "2030-01 – ongoing", None), ("2027-05-gap", "GAP – 2027-05", "gap")]
    # each series in one block, newest part first: a GAP part puts it in the GAP group (by the newest
    # date a part sorts by), an ongoing part with the ongoing rows (by its earliest start), else by its latest end
    SERIES_ORDER = ["2028-01-z", "2027-05-gap-two", "2027-05-gap", "2030-01-w", "2027-01-run-two", "2026-01-run",
                    "2031-01-x", "2029-03-big-two", "2028-01-big", "2029-01-y"]

    def new_series(self):
        for name, period, series in self.SERIES:
            more = ("--field", "series=%s" % series) if series else ()
            self.assertEqual(self.new(name[8:], name[:7], period, *more)[0], 0)

    def test_sort_rows_keeps_a_series_together(self):
        rows = [(n, p, s) for n, p, s in self.SERIES]
        self.assertEqual([r[0] for r in entries.sort_rows(rows)], self.SERIES_ORDER)
        self.assertEqual([r[0] for r in entries.sort_rows(rows[::-1])], self.SERIES_ORDER)
        self.assertEqual(entries.block_order(["2028-01 – 2029-03", "2029-03 – 2030-12"]), (2, ("2030-12", "2028-01")))
        last_open = [("a", "2026-01 – 2027-05", "s"), ("b", "2027-05 – GAP", "s"), ("c", "2025-01 – 2025-06", None)]
        self.assertEqual([r[0] for r in entries.sort_rows(last_open)], ["b", "a", "c"])

    def test_a_series_with_one_row_or_a_missing_file_sorts_as_a_row(self):
        self.new("solo", "2029-01", "2029-01 – 2029-06", "--field", "series=solo")
        self.new("late", "2030-01", "2030-01 – 2030-02")
        self.new("old", "2028-01", "2028-01 – 2028-02", "--field", "series=late")
        os.remove(os.path.join(self.root, "entries/2030-01-late.md"))   # its row reads as no series
        self.assertIsNone(entries.row_series(self.root, "entries/2030-01-late.md"))
        self.assertEqual([re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()],
                         ["2030-01-late", "2029-01-solo", "2028-01-old"])
        self.assertEqual(self.tool("readme-sort"), (0, ["OK: 3 entry rows in order"]))

    def test_readme_row_moves_no_block_in_a_table_out_of_order(self):
        self.new("x", "2031-01", "2031-01 – 2031-03")
        self.new("big", "2028-01", "2028-01 – 2029-03", "--field", "series=big")
        self.new("y", "2029-01", "2029-01 – 2029-06")
        rows = self.rows()
        self.write("README.md", self.read("README.md").replace("\n".join(rows), "\n".join([rows[1], rows[0], rows[2]])))
        self.new("big-two", "2029-03", "2029-03 – 2030-12", "--field", "series=big")   # inserted only
        self.assertEqual([re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()],
                         ["2029-03-big-two", "2029-01-y", "2031-01-x", "2028-01-big"])

    def test_readme_row_moves_the_block_down_when_a_part_shrinks(self):
        self.new_series()
        path = "entries/2029-03-big-two.md"
        self.write(path, self.read(path).replace("2029-03 – 2030-12", "2029-03 – 2029-04"))
        self.assertEqual(self.tool("readme-row", path)[0], 0)
        names = [re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()]
        self.assertEqual(names[-3:], ["2029-01-y", "2029-03-big-two", "2028-01-big"])
        self.assertEqual(self.tool("readme-sort", "--check")[0], 0)

    def test_new_rows_keep_a_series_together(self):
        self.new_series()   # big-two's row moves big up with it
        self.assertEqual([re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()], self.SERIES_ORDER)
        self.assertEqual(self.tool("readme-sort", "--check"), (0, ["OK: 10 entry rows in order"]))

    def test_sort_keeps_a_series_together_and_is_idempotent(self):
        self.new_series()
        text = self.read("README.md")
        rows = self.rows()
        self.write("README.md", text.replace("\n".join(rows), "\n".join(rows[::-1])))
        self.assertEqual(self.tool("readme-sort", "--check")[0], 1)
        self.assertEqual(self.tool("readme-sort"), (0, ["sorted: 10 entry rows, 10 moved"]))
        after = self.read("README.md")
        self.assertEqual([re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()], self.SERIES_ORDER)
        self.assertEqual(self.tool("readme-sort"), (0, ["OK: 10 entry rows in order"]))
        self.assertEqual(self.read("README.md"), after)

    def test_new_rows_go_in_order(self):
        for name, period in self.PERIODS:
            self.new(name[8:], name[:7], period)
        self.assertEqual([re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()], self.ORDER)
        self.assertEqual(self.tool("readme-sort", "--check"), (0, ["OK: 7 entry rows in order"]))

    def test_sort_moves_entry_rows_only_and_is_idempotent(self):
        for name, period in self.PERIODS:
            self.new(name[8:], name[:7], period)
        text = self.read("README.md").replace("\n", "\r\n")
        head, rest = text.split("|---|---|---|---|---|\r\n")
        rows = rest.split("\r\n")[:7]
        shuffled = head + "|---|---|---|---|---|\r\n" + "\r\n".join(rows[::-1][:3] + ["| - | a note, no entry | | | |"]
                                                                 + rows[::-1][3:]) + "\r\n\r\n## Upstream\r\n"
        self.write("README.md", "﻿" + shuffled)
        code, lines = self.tool("readme-sort", "--check")
        self.assertEqual(code, 1)
        self.assertTrue(all(l.startswith("out of order: README.md:") for l in lines), lines)
        self.assertEqual(self.tool("readme-sort")[0], 0)
        after = self.read("README.md")
        self.assertTrue(after.startswith("﻿# Log\r\n"))
        self.assertEqual([re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()], self.ORDER)
        self.assertEqual(after.split("\r\n").index("| - | a note, no entry | | | |"), 9)   # the 4th row, as before
        self.assertEqual(self.tool("readme-sort"), (0, ["OK: 7 entry rows in order"]))
        self.assertEqual(self.read("README.md"), after)

    def test_readme_row_replaces_and_keeps_the_status(self):
        self.new()
        self.write(NEW_W, self.read(NEW_W).replace("tags: []", "tags: [go]").replace("title: Widget Sorter", "title: A | B"))
        self.write("README.md", self.read("README.md").replace("| stub |", "| stub (two gaps) |"))
        self.assertEqual(self.tool("readme-row", NEW_W), (0, ["readme row replaced: README.md:7: | 2031-04 – ongoing |"
                                                          " [A \\| B](%s) | GAP: type | go | stub (two gaps) |" % NEW_W]))
        self.assertEqual(self.tool("readme-row", NEW_W)[1][0][:22], "readme row unchanged: ")
        self.tool("readme-row", NEW_W, "--status", "consolidated (with gaps)")
        self.assertIn("| consolidated (with gaps) |", self.rows()[0])
        self.assertEqual(self.check(), (0, ["OK: 1 entries, no findings"]))
        self.assertEqual(self.tool("readme-row", NEW_W, "--status", "done")[0], 2)

    def test_readme_row_needs_a_status_and_a_table(self):
        self.new()
        self.write("README.md", "# Log\n")
        self.assertEqual(self.tool("readme-row", NEW_W, "--status", "stub")[0], 2)
        self.write("README.md", "| Period | Entry | Type | Tags | Status |\n|---|---|---|---|---|\n")
        self.assertEqual(self.tool("readme-row", NEW_W)[0], 2)
        self.assertEqual(self.tool("readme-row", NEW_W, "--status", "stub")[0], 0)


class StateTest(WriteLog):
    def test_pending_and_key_sections(self):
        self.write(NEW_W, entry(title="Widget", period="2031-01 – ongoing", one_line="GAP: one line",
                            body="Sorted.\n\n## My contribution\n- **I did:** the sorter\n\n## Results and evidence\n"
                                 "| Metric | Value | How measured | Caveat | Source |\n|---|---|---|---|---|\n"
                                 "| GAP: latency | | | | |\n\n## Pending\n- 2031-03-01: a\n- 2031-05-01: b\n"))
        _, lines = self.tool("state", NEW_W, "--today", "2031-04-15")
        self.assertEqual(lines[0], "state: %s: gaps 2; gap sections 8 of 10; pending 2 (oldest 2031-03-01)" % NEW_W)
        self.assertIn("key section empty: %s: One line" % NEW_W, lines)
        self.assertNotIn("key section empty: %s: My contribution" % NEW_W, lines)
        self.assertIn("key section empty: %s: Results and evidence" % NEW_W, lines)
        self.assertEqual(lines[-1], "suggest consolidate: %s: oldest pending line 2031-03-01, over a month old; mostly"
                                    " GAP (8 of 10 sections); key section empty: One line; key section empty: Results"
                                    " and evidence" % NEW_W)
        _, lines = self.tool("state", NEW_W, "--today", "2031-03-20")
        self.assertNotIn("over a month old", lines[-1])

    def test_threshold_and_many_pending(self):
        body = "".join("## %s\nSomething.\n\n" % h for h in entries.PROSE[:6])
        body += "## Pending\n" + "".join("- 2031-04-0%d: x\n" % d for d in range(1, 6))
        self.write(NEW_W, "---\ntitle: Widget\n---\n\n" + body)
        _, lines = self.tool("state", NEW_W, "--today", "2031-04-10")
        self.assertEqual(lines[-1], "suggest consolidate: %s: 5 pending lines; key section empty: Results and evidence"
                         % NEW_W)   # 4 gap sections: not a stub
        self.write(NEW_W, "---\ntitle: Widget\n---\n\n" + "".join("## %s\nSomething.\n\n" % h for h in entries.PROSE[:5]))
        _, lines = self.tool("state", NEW_W, "--today", "2031-04-10")
        self.assertEqual(lines[-1], "suggest consolidate: %s: mostly GAP (5 of 10 sections); key section empty:"
                         " Results and evidence" % NEW_W)

    def test_takes_entries_or_reads_every_one(self):
        self.new()
        self.new("lamp", "2030-01", "2030-01 – 2030-05")
        code, lines = self.tool("state", "--today", "2031-04-20")
        self.assertEqual(code, 0)
        self.assertEqual([l.split(":")[1].strip() for l in lines if l.startswith("state:")],
                         ["entries/2030-01-lamp.md", NEW_W])
        self.assertEqual(self.tool("state", "entries/none.md")[0], 2)
        self.assertEqual(self.tool("state", "entries/_template.md")[0], 2)


class ReviewFixesTest(WriteLog):
    """The review's findings on the writes (#292)."""

    def series(self, last_period):
        self.new("big", "2015-01", "2015-01 – 2016-06", "--field", "series=big")
        self.new("big-two", "2016-07", last_period, "--field", "series=big")

    def test_a_series_part_ending_in_gap_or_gap_ongoing_counts_as_later(self):
        for last in ("2016-07 – GAP", "GAP – ongoing"):
            with self.subTest(last=last):
                self.setUp()
                self.series(last)
                before = self.read("entries/2015-01-big.md")
                code, lines = self.tool("period", "entries/2015-01-big.md", "--cover", "2016-09-01")
                self.assertEqual(code, 1, lines)
                self.assertTrue(lines[0].startswith("not the series' last part: "), lines)
                self.assertEqual(self.read("entries/2015-01-big.md"), before)

    def test_list_reads_gap_ends_in_a_series(self):
        self.series("GAP – ongoing")
        _, lines = self.tool("list", "--series", "big", "--date", "2026-10-01")
        self.assertEqual(lines[2:], ["series big: period GAP – ongoing", "part for 2026-10-01: entries/2016-07-big-two.md"])
        self.setUp()
        self.series("2016-07 – GAP")
        _, lines = self.tool("list", "--series", "big", "--window", "5", "--today", "2026-10-01")
        self.assertEqual(lines[2:], ["series big: period 2015-01 – GAP",
                                     "window unknown (period 2015-01 – 2016-06; 2016-07 – GAP): series big: "
                                     "entries/2015-01-big.md, entries/2016-07-big-two.md"])

    def test_a_readme_whose_last_line_has_no_line_end(self):
        self.new()
        self.write("README.md", self.read("README.md").replace("\n\n## Upstream\n", "").replace("\n", "\r\n").rstrip())
        before = self.read("README.md")
        self.assertEqual(self.tool("readme-row", NEW_W)[1][0][:22], "readme row unchanged: ")
        self.assertEqual(self.read("README.md"), before)
        self.new("lamp", "2030-01", "2030-01 – 2030-05")
        text = self.read("README.md")
        self.assertNotIn("\n", text.replace("\r\n", ""))   # no bare LF
        self.assertFalse(text.endswith("\n"))
        self.write("README.md", text.replace(self.rows()[0] + "\r\n", "") + "\r\n" + self.rows()[0])
        self.assertEqual(self.tool("readme-sort")[0], 0)
        self.assertFalse(self.read("README.md").endswith("\n"))
        self.assertNotIn("\n", self.read("README.md").replace("\r\n", ""))

    def test_new_and_period_write_nothing_without_a_table(self):
        os.remove(os.path.join(self.root, "README.md"))
        self.assertEqual(self.new()[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, NEW_W)))
        self.write(NEW_W, entry(period="2031-01 – 2031-03"))
        before = self.read(NEW_W)
        self.assertEqual(self.tool("period", NEW_W, "--cover", "2031-06-01")[0], 1)
        self.write("README.md", "| Period | Entry | Type | Tags | Status |\n|---|---|---|---|---|\n")
        self.assertEqual(self.tool("period", NEW_W, "--cover", "2031-06-01")[0], 1)   # no row yet
        self.assertEqual(self.read(NEW_W), before)

    def test_new_refuses_a_reversed_period_and_a_title_it_cannot_hold(self):
        self.assertEqual(self.new("a", "2023-05", "2023-05 – 2023-01")[0], 2)
        self.assertEqual(self.tool("new", "a", "--month", "2023-05", "--status", "stub", "--field",
                                   "title=It's \"Big\" #1", "--field", "period=2023-05")[0], 2)
        self.assertEqual(entries.row_order("2023-05 – 2023-01")[0], 0)   # an unreadable period sorts with GAP

    def test_the_entries_table_is_the_one_that_links_entries(self):
        self.write("README.md", "| Name | Entry |\n|---|---|\n| a | b |\n\n" + self.read("README.md"))
        self.new()
        self.assertIn("](%s)" % NEW_W, self.read("README.md").split("## Entries")[1])
        self.assertEqual(self.tool("readme-row", NEW_W)[0], 0)
        self.assertEqual(self.tool("readme-sort"), (0, ["OK: 1 entry rows in order"]))

    def test_date_picks_a_part_still_open(self):
        for last in ("2031-04 – GAP", "GAP – GAP"):
            with self.subTest(last=last):
                self.setUp()
                self.new("big", "2031-01", "2031-01 – 2031-03", "--field", "series=big")
                self.new("big-two", "2031-04", last, "--field", "series=big")
                _, lines = self.tool("list", "--series", "big", "--date", "2031-08-01")
                self.assertEqual(lines[-1], "part for 2031-08-01: entries/2031-04-big-two.md")
                _, lines = self.tool("list", "--series", "big", "--date", "2031-02-01")
                self.assertEqual(lines[-1], "part for 2031-02-01: entries/2031-01-big.md")
        self.write("entries/2031-04-big-two.md", self.read("entries/2031-04-big-two.md").replace("period: GAP – GAP", "period: soon"))
        _, lines = self.tool("list", "--series", "big", "--date", "2031-08-01")
        self.assertEqual(lines[-1], "part for 2031-08-01: entries/2031-01-big.md")   # an unreadable period is no open part

    def test_a_field_with_a_line_break(self):
        for value in ("a\nb", "a\rb", "a\u2028b"):
            self.assertEqual(self.tool("new", "a", "--month", "2031-04", "--status", "stub", "--field",
                                       "title=" + value, "--field", "period=2031-04")[0], 2, repr(value))
        self.assertFalse(os.path.exists(os.path.join(self.root, "entries", "2031-04-a.md")))

    def test_replace_keeps_the_angle(self):
        self.new()
        self.tool("phrasing-add", NEW_W, "--angle", "general", "--source", "x", "--", "Built a fast widget sorter in Go")
        n = [i for i, l in enumerate(self.read(NEW_W).splitlines(), 1) if l.startswith("- **general:**")][0]
        self.assertEqual(self.tool("phrasing-add", NEW_W, "--angle", "backend", "--source", "y", "--replace", str(n),
                                   "--", "Built the widget sorter")[0], 2)


class EntryEditTest(WriteLog):
    def test_pending_add_appends_newest_last_and_renames_log(self):
        self.new()
        self.tool("pending-add", NEW_W, "--today", "2031-04-21", "Merged   it.\nhttps://x/pr/1")
        code, lines = self.tool("pending-add", NEW_W, "--today", "2031-04-22", "--", "-1 bug left")
        self.assertEqual(code, 0)
        text = self.read(NEW_W)
        self.assertTrue(text.endswith("links -->\n- 2031-04-21: Merged it. https://x/pr/1\n- 2031-04-22: -1 bug left\n"))
        self.assertIn("last_updated: 2031-04-22\n", text)
        self.write(NEW_W, text.replace("## Pending", "## Log"))
        _, lines = self.tool("pending-add", NEW_W, "--today", "2031-04-23", "c")
        self.assertEqual(lines[0], "renamed: %s: ## Log to ## Pending" % NEW_W)
        self.assertIn("## Pending\n", self.read(NEW_W))
        self.assertEqual(self.check()[1], ["OK: 1 entries, no findings"])

    def test_pending_add_refuses_a_leading_date(self):
        self.new()
        before = self.read(NEW_W)
        for text in ("2031-04-22: Merged it.", " 2031-04-20 : Merged it.", "2031-04: Merged it.",
                     "- 2031-04-20: Merged it.", "**2031-04-20**: Merged it."):
            code, lines = self.tool("pending-add", NEW_W, "--today", "2031-04-22", "--", text)
            self.assertEqual(code, 1, text)
            self.assertTrue(lines[0].startswith("leading date: %s: " % NEW_W) and lines[1].startswith("next: "), lines)
            self.assertEqual(self.read(NEW_W), before)
        self.assertEqual(self.tool("pending-add", NEW_W, "--today", "2031-04-22", "Merged 2031-04-20.")[0], 0)
        self.assertIn("\n- 2031-04-22: Merged 2031-04-20.\n", self.read(NEW_W))

    def test_pending_add_adds_the_section(self):
        self.write(NEW_W, entry())
        self.tool("pending-add", NEW_W, "--today", "2031-04-23", "c")
        self.assertTrue(self.read(NEW_W).endswith("\n\n## Pending\n- 2031-04-23: c\n"))

    def test_period(self):
        self.new(period="2031-01 – 2031-03")
        self.assertEqual(self.tool("period", NEW_W, "--cover", "2031-02-10")[1], ["unchanged: %s period 2031-01 – 2031-03"
                                                                            " covers 2031-02-10" % NEW_W])
        code, lines = self.tool("period", NEW_W, "--cover", "2031-05-02")
        self.assertEqual((code, lines[0]), (0, "period: %s: 2031-01 – 2031-03 to 2031-01 – 2031-05" % NEW_W))
        self.assertIn("| 2031-01 – 2031-05 |", self.rows()[0])
        self.assertIn("period: 2031-01 – 2031-05   # or", self.read(NEW_W))
        self.assertEqual(self.tool("period", NEW_W, "--cover", "2030-12-01")[0], 1)
        self.tool("period", NEW_W, "--ongoing")
        self.assertIn("| 2031-01 – ongoing |", self.rows()[0])
        self.assertEqual(self.check()[0], 0)
        for args in ([], ["--cover", "soon"], ["--cover", "2031-01-01", "--ongoing"]):
            self.assertEqual(self.tool("period", NEW_W, *args)[0], 2, args)

    def test_period_extends_only_a_series_last_part(self):
        self.new("widget", "2031-01", "2031-01 – 2031-03", "--field", "series=widget")
        self.new("widget-2", "2031-04", "2031-04-01 – 2031-05-01", "--field", "series=widget")
        code, lines = self.tool("period", NEW_W.replace("04", "01"), "--cover", "2031-06-01")
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("not the series' last part: entries/2031-01-widget.md;"), lines)
        self.assertEqual(self.tool("period", "entries/2031-04-widget-2.md", "--cover", "2031-06-01")[0], 0)
        self.assertIn("period: 2031-04-01 – 2031-06-01", self.read("entries/2031-04-widget-2.md"))

    def test_period_names_a_date_between_two_parts(self):
        gap = ["between parts: 2031-05-10 falls after entries/2031-01-widget.md (ends 2031-03) and before"
               " entries/2031-06-widget-2.md (starts 2031-06)"]
        for last, refused, named in (("2031-06 – 2031-08", "before the start: ", "entries/2031-06-widget-2.md"),
                                     ("2031-06 – ongoing", "not the series' last part: ", "entries/2031-01-widget.md")):
            with self.subTest(last=last):
                self.setUp()
                self.new("widget", "2031-01", "2031-01 – 2031-03", "--field", "series=widget")
                self.new("widget-2", "2031-06", last, "--field", "series=widget")
                listed = self.tool("list", "--series", "widget", "--date", "2031-05-10")[1][-3:]
                self.assertEqual(listed[0], "part for 2031-05-10: %s" % named)
                # #385: list says the date falls between parts before step 1 picks the entry
                self.assertEqual(listed[1:2], gap)
                self.assertTrue(listed[2].startswith("next: ask the user once") and "(no answer: keep %s)" % named
                                in listed[2], listed)
                before = (self.read("entries/2031-01-widget.md"), self.read("entries/2031-06-widget-2.md"),
                          self.read("README.md"))
                code, lines = self.tool("period", named, "--cover", "2031-05-10")
                self.assertEqual(code, 1, lines)
                self.assertTrue(lines[0].startswith(refused), lines)
                self.assertEqual(lines[1:2], gap)
                self.assertTrue(lines[2].startswith("next: ask the user once which of the two parts") and
                                "(no answer: keep %s)" % named in lines[2], lines)
                self.assertEqual((self.read("entries/2031-01-widget.md"), self.read("entries/2031-06-widget-2.md"),
                                  self.read("README.md")), before)
        # with three parts, the two on either side of the date; a date on a part's last day is covered
        self.new("widget-3", "2031-10", "2031-10-01 – ongoing", "--field", "series=widget")
        self.write("entries/2031-06-widget-2.md", self.read("entries/2031-06-widget-2.md").replace(
            "2031-06 – ongoing", "2031-06-01 – 2031-08-31"))
        code, lines = self.tool("period", "entries/2031-06-widget-2.md", "--cover", "2031-09-10")
        self.assertEqual(lines[1], "between parts: 2031-09-10 falls after entries/2031-06-widget-2.md (ends 2031-08-31)"
                                   " and before entries/2031-10-widget-3.md (starts 2031-10-01)")
        self.assertIn("(no answer: keep entries/2031-06-widget-2.md)", lines[2])
        leave = "next: leave %s: the pending line holds the milestone's date, and consolidate sets the period from it"
        self.assertEqual(self.tool("period", "entries/2031-06-widget-2.md", "--cover", "2031-08-31")[1][1:],
                         [leave % "the periods as they are"])
        # a date before the first part, or a part's end in GAP, is no gap between parts: #385's next line
        code, lines = self.tool("period", "entries/2031-01-widget.md", "--cover", "2030-12-01")
        self.assertEqual((code, lines[0].split(":")[0], lines[1:]),
                         (1, "not the series' last part", [leave % "the periods as they are"]))
        self.setUp()
        self.new("widget", "2031-01", "2031-01 – GAP", "--field", "series=widget")
        self.new("widget-2", "2031-06", "2031-06 – 2031-08", "--field", "series=widget")
        code, lines = self.tool("period", "entries/2031-06-widget-2.md", "--cover", "2031-05-10")
        self.assertEqual((code, lines[0].split(":")[0], lines[1:]),
                         (1, "not the series' last part", [leave % "the periods as they are"]))
        code, lines = self.tool("period", "entries/2031-01-widget.md", "--cover", "2031-09-01")
        self.assertEqual((code, lines[0].split(":")[0]), (0, "unchanged"))   # its own end in GAP
        self.assertTrue(lines[1].startswith("next: when the work goes on, run it again with --ongoing; else leave"), lines)
        _, lines = self.tool("list", "--series", "widget", "--date", "2031-05-10")
        self.assertEqual(lines[-1], "part for 2031-05-10: entries/2031-01-widget.md")   # a part's end in GAP: no gap line
        # an entry in no series: a date before its start, and an end in GAP
        self.new("lamp", "2031-03", "2031-03 – 2031-05")
        code, lines = self.tool("period", "entries/2031-03-lamp.md", "--cover", "2031-01-10")
        self.assertEqual((code, lines[0].split(":")[0], lines[1:]), (1, "before the start", [leave % "the period as it is"]))
        self.new("bulb", "2031-03", "2031-03 – GAP")
        code, lines = self.tool("period", "entries/2031-03-bulb.md", "--cover", "2031-07-10")
        self.assertEqual((code, lines[1]), (0, "next: when the work goes on, run it again with --ongoing; else leave the"
                                               " period as it is: the pending line holds the milestone's date, and"
                                               " consolidate sets the period from it"))

    def test_set_visibility(self):
        self.new()
        self.assertEqual(self.tool("set-visibility", NEW_W, "nda", "--today", "2031-04-22"),
                         (0, ["visibility: %s: nda  # (user, 2031-04-22)" % NEW_W]))
        self.assertIn("visibility: nda             # (user, 2031-04-22)\n", self.read(NEW_W))
        self.tool("set-visibility", NEW_W, "public", "--source", "https://github.com/u/w")
        self.assertIn("visibility: public          # (https://github.com/u/w)\n", self.read(NEW_W))
        self.assertEqual(self.tool("set-visibility", NEW_W, "secret")[0], 2)


class PhrasingAddTest(WriteLog):
    def add(self, wording, source, *more, angle="general"):
        return self.tool("phrasing-add", NEW_W, "--angle", angle, "--source", source, *more, "--", wording)

    def lines(self):
        return [l for l in self.read(NEW_W).splitlines() if l.startswith("- **") and '"' in l]

    def test_add_repeat_and_newer_citation(self):
        self.new()
        self.assertEqual(self.add("Built a widget sorter in Go", "sources/resumes/2030-05-01-cv.pdf")[1][0][:7], "added: ")
        self.assertEqual(self.add('"Built a widget  sorter in Go"', "sources/resumes/2029-01-01-cv.pdf")[1][0][:14],
                         "already kept: ")
        self.assertEqual(self.add("Built a widget sorter in Go", "sources/resumes/2031-01-01-cv.pdf")[1][0][:9], "recited: ")
        self.assertEqual(self.lines(), ['- **general:** "Built a widget sorter in Go" (sources/resumes/2031-01-01-cv.pdf)'])
        self.add("Built a widget sorter in Go", "outputs/resumes/backend.tex, 2031-02-01")
        self.add("Built a widget sorter in Go", "chatgpt-2031-06-01 T1.U2")   # no import citation replaces an output's
        self.assertEqual(self.lines(), ['- **general:** "Built a widget sorter in Go" (outputs/resumes/backend.tex, 2031-02-01)'])
        self.add("Built a widget sorter in Go", "sources/resumes/2031-01-01-cv.pdf", angle="backend")
        self.assertEqual(len(self.lines()), 2)
        self.assertEqual(self.check()[0], 1)   # `backend` is no target in outputs/resumes/: check's finding, not the tool's

    def test_similar_waits_for_a_judgement(self):
        self.new()
        self.add("Built a fast widget sorter in Go with Kafka", "sources/resumes/2030-05-01-cv.pdf")
        before = self.read(NEW_W)
        code, lines = self.add("Built a fast widget sorter in Go on Kafka", "sources/resumes/2031-05-01-cv.pdf")
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("similar: %s:" % NEW_W) and lines[1].startswith("not added: "), lines)
        self.assertEqual(self.read(NEW_W), before)
        n = int(lines[0].split(":")[2])
        self.assertEqual(self.add("Built a fast widget sorter in Go on Kafka", "sources/resumes/2031-05-01-cv.pdf",
                                  "--replace", str(n))[0], 0)
        self.assertEqual(self.lines(), ['- **general:** "Built a fast widget sorter in Go on Kafka" (sources/resumes/'
                                        '2031-05-01-cv.pdf)'])
        self.assertEqual(self.add("Built a fast widget sorter in Go with Kafka", "x", "--distinct")[0], 0)
        self.assertEqual(len(self.lines()), 2)

    def test_bad_lines(self):
        self.new()
        self.assertEqual(self.add("x", "a; b")[0], 2)
        self.assertEqual(self.add("x", "a", angle="Not An Angle")[0], 2)
        self.assertEqual(self.add("x", "a", "--replace", "3")[0], 2)
        self.assertEqual(self.add("x", "a", "--replace", "3", "--distinct")[0], 2)


class ListFlagsTest(Log):
    def setUp(self):
        super().setUp()
        self.write("entries/2024-01-widget.md", entry(series="widget", period="2024-01 – 2025-03"))
        self.write("entries/2025-04-widget-2.md", entry(series="widget", period="2025-04 – 2026-02"))
        self.write("entries/2020-05-lamp.md", entry(title="Lamp", period="2020-05 – 2021-06", type_="course"))
        self.write("entries/2022-05-tree.md", entry(title="Tree", period="2022-05 – 2023-06", tags="[coursework]"))
        self.write("entries/2030-01-gap.md", entry(title="Gap", period="GAP – ongoing"))

    def test_default_output_is_unchanged(self):
        _, plain = self.run_tool("list", "--root", self.root)
        self.assertEqual(len(plain), 5)
        _, flagged = self.run_tool("list", "--root", self.root, "--window", "5", "--course-work", "--today", "2031-06-15")
        self.assertEqual(flagged[:5], plain)

    def test_series_period_and_part_for_a_date(self):
        def part(date):
            return self.run_tool("list", "--root", self.root, "--series", "widget", "--date", date)[1][2:]
        self.assertEqual(part("2025-04-10"), ["series widget: period 2024-01 – 2026-02",
                                              "part for 2025-04-10: entries/2025-04-widget-2.md"])
        # #385: a date before every part goes to the first one, and says so
        self.assertEqual(part("2023-01-01")[1:], [
            "part for 2023-01-01: entries/2024-01-widget.md", "before the first part: entries/2024-01-widget.md starts 2024-01",
            "next: the milestone goes to entries/2024-01-widget.md; leave the period as it is: the pending line holds the"
            " milestone's date, and consolidate sets the period from it"])
        self.assertEqual(part("2026-05-01")[1:], ["part for 2026-05-01: entries/2025-04-widget-2.md"])   # after the last
        self.assertEqual(self.run_tool("list", "--root", self.root, "--date", "2025-04-10")[0], 2)

    def test_window_and_course_work(self):
        _, lines = self.run_tool("list", "--root", self.root, "--window", "5", "--course-work", "--today", "2028-03-15")
        self.assertEqual(lines[5:], ["outside window (ended 2021-06): entries/2020-05-lamp.md",
                                     "course work: entries/2020-05-lamp.md, entries/2022-05-tree.md (by type or tag)"])
        _, lines = self.run_tool("list", "--root", self.root, "--window", "2", "--today", "2028-03-15")
        self.assertEqual(lines[5:], ["outside window (ended 2021-06): entries/2020-05-lamp.md",
                                     "outside window (ended 2023-06): entries/2022-05-tree.md",
                                     "outside window (ended 2026-02): series widget: entries/2024-01-widget.md,"
                                     " entries/2025-04-widget-2.md"])

BIG = "entries/2028-01-big.md"


class ConsolidateHelpersTest(WriteLog):
    """split, split --undo, diff and drop (consolidate steps 4-6, SKILL.md › Dropped experiences)."""

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.new("big", "2028-01", "2028-01 – 2030-06", "--field", "tags=go, kafka", "--field", "org=Acme",
                 "--field", "visibility=public", "--visibility-source", "https://github.com/u/big",
                 "--field", "links=https://github.com/u/big", status="imported")
        self.new("solo", "2029-06", "2029-06 – 2029-08")
        self.commit("import")

    def commit(self, subject):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def names(self):
        return [re.search(r"entries/(.*)\.md", r).group(1) for r in self.rows()]

    def split(self, *more):
        return self.tool("split", BIG, "--phase", "Prototype", "--cut", "2029-03:scale:Scale-up", "--today",
                         "2031-04-20", *more)

    def test_split_writes_the_parts_and_their_rows(self):
        code, lines = self.split("--cut", "2030-01-15:launch:Launch")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[:3], ["kept: %s: Widget Sorter: Prototype; period 2028-01 – 2029-03" % BIG,
                                     "created: entries/2029-03-big-scale.md: Widget Sorter: Scale-up; period"
                                     " 2029-03 – 2030-01-15",
                                     "created: entries/2030-01-big-launch.md: Widget Sorter: Launch; period"
                                     " 2030-01-15 – 2030-06"])
        e = entries.Entry(self.root, BIG)
        self.assertEqual((e.fields["title"], e.series, e.period), ("Widget Sorter: Prototype", "big", "2028-01 – 2029-03"))
        part = entries.Entry(self.root, "entries/2029-03-big-scale.md")
        self.assertEqual((part.fields["title"], part.series, part.period, part.fields["org"], part.tags,
                          part.fields["links"], part.fields["last_updated"]),
                         ("Widget Sorter: Scale-up", "big", "2029-03 – 2030-01-15", "Acme", ["go", "kafka"],
                          ["https://github.com/u/big"], "2031-04-20"))
        self.assertIn("visibility: public          # (https://github.com/u/big)\n", part.text)
        self.assertIn("\n# Widget Sorter: Scale-up\n", part.text)
        self.assertIn("- **I did:** GAP:\n", part.text)
        # a row for each part, the status copied, the series in one block, newest part first
        self.assertEqual(self.names(), ["2030-01-big-launch", "2029-03-big-scale", "2028-01-big", "2029-06-solo"])
        self.assertTrue(all(r.endswith(" | imported |") for r in self.rows()[:3]), self.rows())
        self.assertEqual(self.tool("readme-sort", "--check")[0], 0)
        self.assertEqual([l for l in self.check()[1] if "series" in l or "README" in l], [])

    def test_split_with_a_pause(self):
        """`<end>..<start>`: the earlier part ends where a pause began, not at the cut."""
        code, lines = self.tool("split", BIG, "--phase", "Prototype", "--cut", "2029-01..2029-03:scale:Scale-up")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "kept: %s: Widget Sorter: Prototype; period 2028-01 – 2029-01" % BIG)
        self.assertEqual(entries.Entry(self.root, "entries/2029-03-big-scale.md").period, "2029-03 – 2030-06")
        self.assertEqual([l for l in self.check()[1] if "series" in l], [])
        for cut in ("2028-01..2029-03:a:A", "2029-04..2029-03:a:A", "soon..2029-03:a:A", "..2029-03:a:A"):
            self.assertEqual(self.tool("split", "entries/2029-03-big-scale.md", "--phase", "P", "--cut", cut)[0], 2, cut)

    def test_a_pause_after_a_one_month_part(self):
        """An end in the earlier part's start month, or in the cut's month when the cut gives a day."""
        code, lines = self.tool("split", BIG, "--phase", "P", "--cut", "2028-01..2028-05:b:B",
                                "--cut", "2029-03..2029-03-10:c:C")
        self.assertEqual(code, 0, lines)
        self.assertEqual([entries.Entry(self.root, p).period for p in
                          (BIG, "entries/2028-05-big-b.md", "entries/2029-03-big-c.md")],
                         ["2028-01 – 2028-01", "2028-05 – 2029-03", "2029-03-10 – 2030-06"])
        self.assertEqual([l for l in self.check()[1] if "series" in l], [])

    def test_split_an_ongoing_part_again(self):
        self.write(BIG, self.read(BIG).replace("2028-01 – 2030-06", "2028-01 – ongoing"))
        self.tool("readme-row", BIG)
        self.split()
        part = "entries/2029-03-big-scale.md"
        self.assertEqual(entries.Entry(self.root, part).period, "2029-03 – ongoing")
        code, lines = self.tool("split", part, "--phase", "Scale-up", "--cut", "2030-02:launch:Launch")
        self.assertEqual(code, 0, lines)
        launch = entries.Entry(self.root, "entries/2030-02-big-launch.md")   # the series slug, not the part's
        self.assertEqual((launch.fields["title"], launch.series, launch.period),
                         ("Widget Sorter: Launch", "big", "2030-02 – ongoing"))
        self.assertEqual(entries.Entry(self.root, part).fields["title"], "Widget Sorter: Scale-up")

    def test_split_refuses_before_writing(self):
        before = (self.read(BIG), self.read("README.md"))
        for cuts in (["2027-12:a:A"], ["2028-01:a:A"], ["2030-06:a:A"], ["2029-03:a:A", "2029-03-10:b:B"],
                     ["2029-03:a:A", "2029-02:b:B"], ["2029-03:a:A", "2029-03-20:a:B"], ["2029-03:Bad:A"], ["2029-03:a:"],
                     ["soon:a:A"]):
            args = ["split", BIG, "--phase", "P"] + [x for c in cuts for x in ("--cut", c)]
            self.assertEqual(self.tool(*args)[0], 2, cuts)
        self.write("entries/2029-03-big-a.md", "taken")
        self.assertEqual(self.tool("split", BIG, "--phase", "P", "--cut", "2029-03:a:A")[0], 2)
        self.assertEqual(self.tool("split", BIG, "--cut", "2029-03:b:B")[0], 2)   # no --phase
        self.assertEqual((self.read(BIG), self.read("README.md")), before)
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "entries"))),
                         ["2028-01-big.md", "2029-03-big-a.md", "2029-06-solo.md", "_template.md"])

    def test_diff_prints_a_fenced_block(self):
        self.assertEqual(self.tool("diff", BIG), (0, ["no change: %s" % BIG]))
        self.write(BIG, self.read(BIG).replace("GAP:\n", "Sorted widgets with ```` fences.\n", 1))
        code, lines = self.tool("diff", BIG)
        self.assertEqual((code, lines[0], lines[-1]), (0, "`````diff", "`````"))
        self.assertIn("+Sorted widgets with ```` fences.", lines)
        self.split()
        code, lines = self.tool("diff", BIG, "entries/2029-03-big-scale.md")
        self.assertEqual((lines[0], lines[-1]), ("`````diff", "`````"))
        heads = [l for l in lines if l.startswith("diff --git")]
        self.assertEqual(heads, ["diff --git a/%s b/%s" % (p, p) for p in ("README.md", BIG, "entries/2029-03-big-scale.md")])
        self.assertIn("+title: Widget Sorter: Scale-up", lines)

    def test_diff_cuts_the_unchanged_words_of_a_long_line(self):
        para = " ".join("word%d" % k for k in range(500))   # one ~4,400-character line
        self.write(BIG, self.read(BIG).replace("GAP:\n", "%s\n\nOld line to delete.\n" % para, 1))
        self.commit("long line")
        edited = para.replace("word200 ", "word200 CHANGED ").replace("word300 word301 word302 ", "")
        self.write(BIG, self.read(BIG).replace(para, edited.replace("word0 ", "word0  "))
                   .replace("Old line to delete.\n", "A new line, added whole.\n"))
        code, lines = self.tool("diff", BIG)
        self.assertEqual(code, 0, lines)
        self.assertLess(sum(map(len, lines)), 1500)
        self.assertEqual(lines[1], "# [… N words unchanged …]: N unchanged words this diff leaves out;"
                                   " it shows every added and deleted word")
        self.assertEqual([l for l in lines if l.startswith("@@")], ["@@ -17,9 +17,9 @@ ## One line"])   # the change's section
        old, new = [l for l in lines if l.startswith("-word0")], [l for l in lines if l.startswith("+word0")]
        self.assertEqual(len(old), 1, lines)
        self.assertEqual(len(new), 1, lines)
        # the whitespace change, the inserted word and the deleted words, each with 8 words beside it
        self.assertTrue(new[0].startswith("+word0  word1 word2 word3 word4 word5 word6 word7 word8 [… 184 words unchanged …] word193"), new)
        self.assertIn("word193 word194 word195 word196 word197 word198 word199 word200 CHANGED word201 "
                      "word202 word203 word204 word205 word206 word207 word208 [… 83 words unchanged …] word292", new[0])
        self.assertIn("word299 word300 word301 word302 word303", old[0])
        self.assertIn("word299 word303", new[0])
        self.assertTrue(old[0].endswith("word310 [… 189 words unchanged …]"), old)
        self.assertIn("-Old line to delete.", lines)
        self.assertIn("+A new line, added whole.", lines)
        # a line added whole is printed in full, however long
        self.write(BIG, self.read(BIG) + "\n%s\n" % para.replace("word", "fresh"))
        code, lines = self.tool("diff", BIG)
        self.assertIn("+" + para.replace("word", "fresh"), lines)

    def test_diff_names_the_section_and_pairs_a_last_line(self):
        para = " ".join("word%d" % k for k in range(300))
        text = self.read(BIG).rstrip("\n") + "\n\n## Notes\n```sh\n# not a heading\n```\n\n" + para   # no newline at the end
        self.write(BIG, text)
        self.commit("fence")
        self.write(BIG, text.replace("word150 ", "word150 CHANGED "))
        code, lines = self.tool("diff", BIG)
        self.assertEqual(code, 0, lines)
        self.assertEqual([l for l in lines if l.startswith("@@")][-1][-len(" @@ ## Notes"):], " @@ ## Notes")
        changed = [l for l in lines if l[:1] in "-+" and "word150" in l]
        self.assertEqual(len(changed), 2, lines)
        self.assertTrue(all(len(l) < 300 for l in changed), changed)
        self.assertEqual([lines[k - 1][:1] for k, l in enumerate(lines) if l == "\\ No newline at end of file"],
                         ["-", "+"])   # each mark after the line it is about

    def test_undo_a_split(self):
        # the draft extended the period before the split: undo keeps the draft's, from the parts' span
        self.write(BIG, self.read(BIG).replace("2028-01 – 2030-06", "2028-01 – 2030-09").replace("GAP:\n", "Draft.\n", 1))
        self.tool("readme-row", BIG)
        self.write("stories.md", index(("Debugging", story("entries/2029-03-big-scale.md", "context"))))
        self.split("--cut", "2030-01:launch:Launch")
        self.tool("diff", BIG, "entries/2029-03-big-scale.md", "entries/2030-01-big-launch.md")   # adds them -N
        parts = ["entries/2029-03-big-scale.md", "entries/2030-01-big-launch.md"]
        self.assertEqual(self.tool("split", "--undo", BIG)[0], 2)   # names its parts
        self.assertEqual(self.tool("split", "--undo", BIG, "entries/2029-06-solo.md")[0], 2)
        code, lines = self.tool("split", "--undo", BIG, *parts)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "restored: %s: Widget Sorter; period 2028-01 – 2030-09; series -" % BIG)
        self.assertEqual(lines[1:3], ["deleted: %s; README row" % p for p in parts])
        self.assertEqual(lines[-1], "still names entries/2029-03-big-scale.md: stories.md:7: | Debugging | "
                                    "[Widget](entries/2029-03-big-scale.md#context) |")
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "entries"))),
                         ["2028-01-big.md", "2029-06-solo.md", "_template.md"])
        self.assertIn("Draft.\n", self.read(BIG))
        self.assertIn("\nseries:                     # a part", self.read(BIG))
        self.assertEqual(self.names(), ["2028-01-big", "2029-06-solo"])
        self.assertEqual(self.rows()[0], "| 2028-01 – 2030-09 | [Widget Sorter](%s) | GAP: type | go, kafka | imported |" % BIG)
        status = subprocess.run(["git", "-C", self.root, "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(sorted(l[3:] for l in status.splitlines()), ["README.md", BIG, "stories.md"])

    def test_drop(self):
        self.split()
        scale = "entries/2029-03-big-scale.md"
        self.write("stories.md", index(
            ("Debugging", "; ".join([story(BIG, "context", marker="core"), story("entries/2029-06-solo.md")])),
            ("Proudest project", story(BIG, "", summary="all of it; more"))))
        self.write("stories/debugging.md", talking("Debugging", "2031-06-01", BIG + "#context"))
        self.write("profile.md", "Led [Widget](entries/2028-01-big.md).\n")
        self.write("sources/import-log.md", "# Import log\n\nOne section per import run.\n")
        code, lines = self.tool("drop", BIG, "--reason", "user, 2031-06-02: a class demo, not a project", "--today",
                                "2031-06-02")
        self.assertEqual(code, 0, lines)
        self.assertFalse(os.path.exists(os.path.join(self.root, BIG)))
        self.assertEqual(self.names(), ["2029-03-big-scale", "2029-06-solo"])
        self.assertEqual(lines[1:4], ["story removed: Debugging: *(core)* [Widget](%s#context)" % BIG,
                                      "story removed: Proudest project: [Widget](%s) — all of it; more" % BIG,
                                      "deleted: %s" % BIG])
        self.assertIn("| Debugging | [Widget](entries/2029-06-solo.md) |\n", self.read("stories.md"))
        self.assertIn("| Proudest project | |\n", self.read("stories.md"))
        self.assertEqual(self.read("sources/import-log.md"),
                         "# Import log\n\nOne section per import run.\n\n## 2031-06-02 — Dropped: Widget Sorter: Prototype\n\n"
                         "- Removed `%s` (Widget Sorter: Prototype, 2028-01 – 2029-03): user, 2031-06-02: a class demo,"
                         " not a project\n" % BIG)
        # #421: one part left is a plain entry again, and core went with the dropped part
        self.assertIn("series folded: %s: Widget Sorter; series -" % scale, lines)
        e = entries.Entry(self.root, scale)
        self.assertEqual((e.series, e.fields["title"]), ("", "Widget Sorter"))
        self.assertIn("\n# Widget Sorter\n", e.text)
        self.assertIn("[Widget Sorter](%s)" % scale, self.read("README.md"))
        self.assertTrue(any(l.startswith("next: core went with it") for l in lines), lines)
        self.assertEqual(self.check()[0], 0, self.check())
        self.assertEqual([l for l in lines if l.startswith("still names")],
                         ["still names: profile.md:1: Led [Widget](entries/2028-01-big.md).",
                          "still names: stories/debugging.md:10: 1. [S](../%s#context) — lead" % BIG,
                          "still names: stories/debugging.md:16: - the bug ([Context](../%s#context#context))" % BIG])
        self.assertEqual(self.tool("drop", "entries/2029-06-solo.md")[0], 2)   # no --reason

    def test_drop_renames_or_folds_the_series(self):
        # three parts, the first dropped: the earliest part left names the series
        self.split("--cut", "2030-01:launch:Launch")
        scale, launch = "entries/2029-03-big-scale.md", "entries/2030-01-big-launch.md"
        self.write("stories.md", index(("Debugging", story(scale, "context", label="Widget Sorter: Scale-up › Context"))))
        code, lines = self.tool("drop", BIG, "--reason", "user, 2031-06-02: never happened", "--today", "2031-06-02")
        self.assertEqual(code, 0, lines)
        self.assertEqual([l for l in lines if l.startswith("series ")],
                         ["series renamed: %s: series big-scale" % p for p in (scale, launch)])
        self.assertEqual([entries.Entry(self.root, p).series for p in (scale, launch)], ["big-scale", "big-scale"])
        # the last part of two dropped: the first part left is a plain entry, and a line naming its old title says so
        code, lines = self.tool("drop", launch, "--reason", "user, 2031-06-02: never happened", "--today", "2031-06-02")
        self.assertEqual(code, 0, lines)
        self.assertIn("series folded: %s: Widget Sorter; series -" % scale, lines)
        self.assertEqual(lines[-2:], ["next: write its title 'Widget Sorter' in place of 'Widget Sorter: Scale-up' in each"
                                      " line below", "old title: stories.md:%d: %s" % (
                                          self.read("stories.md").splitlines().index(
                                              [l for l in self.read("stories.md").splitlines() if scale in l][0]) + 1,
                                          [l for l in self.read("stories.md").splitlines() if scale in l][0])])
        self.assertEqual(entries.Entry(self.root, scale).series, "")

    def test_drop_in_a_bare_log(self):
        """No README.md, stories.md or import log; an entry diff added with -N leaves the index;
        lines in outputs/ and sources/ are frozen, so not listed."""
        os.remove(os.path.join(self.root, "README.md"))
        self.write("entries/2030-01-x.md", entry(title="X", period="2030-01 – 2030-02"))
        self.git("add", "-N", "entries/2030-01-x.md")
        self.write("outputs/reports/r.md", "cites entries/2030-01-x.md\n")
        self.write("direction.md", "- like [X](entries/2030-01-x.md)\n")
        code, lines = self.tool("drop", "entries/2030-01-x.md", "--reason", "never happened", "--today", "2031-06-02")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "README row: none")
        self.assertEqual(lines[-2:], ["next: take the entry out of each line below, or delete a line that says nothing"
                                      " else", "still names: direction.md:1: - like [X](entries/2030-01-x.md)"])
        self.assertEqual(self.read("sources/import-log.md"), "# Import log\n\n## 2031-06-02 — Dropped: X\n\n"
                         "- Removed `entries/2030-01-x.md` (X, 2030-01 – 2030-02): never happened\n")
        status = subprocess.run(["git", "-C", self.root, "status", "--porcelain", "--", "entries"], capture_output=True,
                                text=True).stdout
        self.assertEqual(status, "")

    def test_split_copies_block_lists_and_the_heading(self):
        self.write(BIG, self.read(BIG).replace("tags: [go, kafka]", "tags:\n  - go\n  - kafka")
                   .replace("links: [https://github.com/u/big]", "links:\n  - https://github.com/u/big"))
        self.assertEqual(self.split()[0], 0)
        part = entries.Entry(self.root, "entries/2029-03-big-scale.md")
        self.assertEqual((part.tags, part.fields["links"]), (["go", "kafka"], ["https://github.com/u/big"]))
        self.assertIn("\ntags:\n  - go\n  - kafka   ", part.text)   # the lines as they stand, their comment too
        self.assertIn("\n# Widget Sorter: Prototype\n", self.read(BIG))

    def test_split_refuses_a_gap_period_a_phase_with_a_colon_and_no_template(self):
        before = self.read(BIG)
        self.assertEqual(self.tool("split", BIG, "--phase", "A: b", "--cut", "2029-03:a:A")[0], 2)
        self.assertEqual(self.tool("split", BIG, "--phase", "A", "--cut", "2029-03:a:B: c")[0], 2)
        os.remove(os.path.join(self.root, "entries", "_template.md"))
        self.assertEqual(self.split()[0], 2)
        self.assertEqual(self.read(BIG), before)   # nothing written
        self.write(BIG, before.replace("2028-01 – 2030-06", "GAP – 2030-06"))
        self.assertEqual(self.split()[0], 2)

    def test_split_refuses_a_gap_title_and_names_a_heading_it_leaves(self):
        before = self.read(BIG)
        for gap in ("GAP: title", "GAP"):
            self.write(BIG, before.replace("title: Widget Sorter", "title: " + gap))
            self.assertEqual(self.split()[0], 2, gap)
            self.assertFalse(os.path.exists(os.path.join(self.root, "entries", "2029-03-big-scale.md")))
        self.write(BIG, before.replace("Widget Sorter", "Gap year sorter"))   # a title that only starts with the word
        self.assertEqual(self.split()[0], 0)
        self.git("checkout", "--", BIG, "README.md")
        os.remove(os.path.join(self.root, "entries", "2029-03-big-scale.md"))
        self.write(BIG, before.replace("\n# Widget Sorter\n", "\n# The Widget Sorter\n"))
        code, lines = self.split()
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[:2], ["heading not rewritten: %s: no `# Widget Sorter` heading after the front matter" % BIG,
                                     "next: make its title heading `# Widget Sorter: Prototype`"])
        self.assertIn("\n# The Widget Sorter\n", self.read(BIG))

    def test_undo_refuses_an_earlier_part_and_a_repeat(self):
        self.split()
        self.commit("consolidate(big): split")
        scale = "entries/2029-03-big-scale.md"
        self.write(scale, self.read(scale).replace("Widget Sorter: Scale-up", "Widget Sorter Pro: Scale-up"))   # the draft's
        code, lines = self.tool("split", "entries/2029-03-big-scale.md", "--phase", "Ramp",
                                "--cut", "2030-01:launch:Launch")
        self.assertEqual(code, 0, lines)
        launch = "entries/2030-01-big-launch.md"
        for parts in (["entries/2029-03-big-scale.md"], [launch, launch]):
            self.assertEqual(self.tool("split", "--undo", BIG, *parts)[0], 2, parts)
        code, lines = self.tool("split", "--undo", "entries/2029-03-big-scale.md", launch)
        self.assertEqual(code, 0, lines)
        e = entries.Entry(self.root, scale)   # a part already: the draft's series title, HEAD's phase and series
        self.assertEqual((e.fields["title"], e.series, e.period), ("Widget Sorter Pro: Scale-up", "big", "2029-03 – 2030-06"))
        # a part whose title in HEAD holds no `: ` gets that title back as it stands
        self.git("checkout", "--", scale)
        self.write(scale, self.read(scale).replace("Widget Sorter: Scale-up", "Scale-up work"))
        self.commit("retitled")
        self.tool("split", scale, "--phase", "Ramp", "--cut", "2030-01:launch:Launch")
        self.tool("split", "--undo", scale, launch)
        self.assertEqual(entries.Entry(self.root, scale).fields["title"], "Scale-up work")

    def test_undo_of_an_entry_not_in_head_and_one_whose_title_changed(self):
        self.write("entries/2030-01-new.md", entry(title="New Thing", period="2030-01 – 2030-12"))
        self.tool("readme-row", "entries/2030-01-new.md", "--status", "stub")
        self.tool("split", "entries/2030-01-new.md", "--phase", "A", "--cut", "2030-06:b:B")
        code, lines = self.tool("split", "--undo", "entries/2030-01-new.md", "entries/2030-06-new-b.md")
        # #421: a new entry the split made a first part is a plain entry again
        self.assertEqual(lines[0], "restored: entries/2030-01-new.md: New Thing; period 2030-01 – 2030-12; series -")
        self.assertIn("\n# New Thing\n", self.read("entries/2030-01-new.md"))
        # a new entry that was a later part already keeps its title and series, and says so
        self.write("entries/2030-01-new.md", entry(title="Big: Later", period="2030-01 – 2030-12", series="big"))
        self.tool("readme-row", "entries/2030-01-new.md", "--status", "stub")
        self.tool("split", "entries/2030-01-new.md", "--phase", "A", "--cut", "2030-06:b:B")
        code, lines = self.tool("split", "--undo", "entries/2030-01-new.md", "entries/2030-06-big-b.md")
        self.assertEqual(lines[:2], ["not in HEAD: entries/2030-01-new.md: title and series left as they are (its series"
                                     " has other parts)", "next: when the split changed the title's `: <phase>`, write"
                                     " back the phase it had, in its title heading too"])
        self.assertEqual(entries.Entry(self.root, "entries/2030-01-new.md").fields["title"], "Big: A")
        os.remove(os.path.join(self.root, "entries", "2030-01-new.md"))
        # a title the draft corrected stays; HEAD had a series: line, so it stays, empty
        self.write(BIG, self.read(BIG).replace("Widget Sorter", "Widget Sorter Pro"))
        self.split()
        code, lines = self.tool("split", "--undo", BIG, "entries/2029-03-big-scale.md")
        self.assertEqual(lines[0], "restored: %s: Widget Sorter Pro; period 2028-01 – 2030-06; series -" % BIG)
        self.assertIn("\n# Widget Sorter Pro\n", self.read(BIG))
        self.git("checkout", "--", BIG)
        text = self.read(BIG).replace("series:                     # a part of a split experience only: the earliest"
                                      " part's slug\n", "")
        self.write(BIG, text)
        self.commit("no series line")
        self.split()
        self.tool("split", "--undo", BIG, "entries/2029-03-big-scale.md")
        self.assertEqual(self.read(BIG), text)   # the split's series: line goes again

    def test_a_period_change_re_places_the_row(self):
        """consolidate step 6: readme-row moves an entry whose period changed past its neighbours."""
        self.assertEqual(self.names(), ["2028-01-big", "2029-06-solo"])
        self.write(BIG, self.read(BIG).replace("2028-01 – 2030-06", "2028-01 – 2029-07"))
        code, lines = self.tool("readme-row", BIG, "--status", "consolidated")
        self.assertEqual(code, 0)
        self.assertEqual(self.names(), ["2029-06-solo", "2028-01-big"])
        self.assertEqual(self.tool("readme-sort", "--check")[0], 0)

if __name__ == "__main__":
    unittest.main()
