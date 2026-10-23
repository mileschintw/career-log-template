#!/usr/bin/env python3
"""Tests for tools/entries.py, on small made-up Logs built in a temporary directory.

  python3 -I tools/tests/test_entries.py
"""
import datetime, importlib.util, io, os, shutil, subprocess, sys, tempfile, unittest
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
        return self.run_tool("check", self.root, "--today", TODAY)

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
        code, lines = self.run_tool("list", self.root)
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
        code, lines = self.run_tool("list", self.root, "--series", "widget")
        self.assertEqual([l.split(":")[0] for l in lines], ["entries/2031-01-widget.md", "entries/2031-04-widget-2.md"])

    def test_list_marks_over_threshold(self):
        self.write("entries/2030-05-lamp.md", entry(title="Lamp Fixer", body="x" * 40000))
        _, lines = self.run_tool("list", self.root)
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
        self.assertEqual(self.run_tool("check", self.root, "--today", "2031-01-20"), (0, ["OK: 3 entries, no findings"]))
        self.write("entries/2031-01-widget-b.md", entry(series="widget", period="2031-01-14 – 2031-01-19"))
        _, lines = self.run_tool("check", self.root, "--today", "2031-01-20")
        self.assertEqual([l for l in lines if "overlapping" in l],
                         ["series widget has overlapping periods: entries/2031-01-widget-b.md"
                          " (2031-01-14 – 2031-01-19), entries/2031-01-widget.md (2031-01-12 – 2031-01-15)"])
        # a period with days against one without is compared by month
        self.write("entries/2031-01-widget-b.md", entry(series="widget", period="2031-01 – 2031-01"))
        _, lines = self.run_tool("check", self.root, "--today", "2031-01-20")
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
        code, lines = self.run_tool("refs", "entries/2031-01-widget.md", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [
            "README.md:7: " + row("entries/2031-01-widget.md").strip(),
            "stories.md:1: | Hard bug | [Widget › Dead ends](entries/2031-01-widget.md#dead-ends) |",
            "entries/2031-04-widget-2.md:18: See [part one](2031-01-widget.md#context).",
            "stories/hard-bug.md:16: - the bug ([Context](../entries/2031-01-widget.md#context))",
            "stories/hard-bug.md:17: <!-- old: entries/2031-01-widget.md -->",
            "outputs/applications/2031-05-01-acme-dev/provenance.md:1: | a | entries/2031-01-widget.md › Context | src |",
            "sources/claude-code/2031-02-01-widget.md:1: cites 2031-01-widget in passing",
        ])

    def test_not_an_entry(self):
        self.write("README.md", README_HEAD)
        for arg in ("entries/_template.md", "README.md", "entries/2031-09-none.md"):
            code, lines = self.run_tool("refs", arg, self.root)
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
        code, lines = self.run_tool("links-since", self.path, self.root)
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
        _, lines = self.run_tool("links-since", self.path, self.root)
        self.assertTrue(lines[0].startswith("since: "), lines)
        self.assertTrue(lines[0].endswith(" consolidate(lamp, widget): both"), lines)
        self.assertEqual(lines[1:], ["link: https://example.org/pr/3", "link: https://example.org/pr/2"])
        # an uncommitted link counts too
        with open(os.path.join(self.root, self.path), "a", encoding="utf-8") as f:
            f.write("- 2031-05-01: more. https://example.org/pr/4\n")
        _, lines = self.run_tool("links-since", self.path, self.root)
        self.assertEqual(lines[-1], "link: https://example.org/pr/4")

    def test_not_a_repo(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "entries"))
        with open(os.path.join(root, self.path), "w", encoding="utf-8") as f:
            f.write(entry())
        code, lines = self.run_tool("links-since", self.path, root)
        self.assertEqual(code, 2)
        self.assertTrue(lines[0].startswith("FAIL: git log failed"), lines)


class ScriptTest(Log):
    def test_bad_arguments(self):
        for args in ([], ["frob"], ["refs"], ["list", "a", "b"], ["check", "--today"], ["check", "--today", "soon"],
                     ["list", self.root, "--bogus"], ["check", self.root, "--series", "x"],
                     ["list", self.root, "--today", TODAY]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 2, args)

    def test_help(self):
        """-h or --help anywhere prints the docstring, which holds the formats the modes rely on."""
        for args in (["--help"], ["-h"], ["story-coverage", "--help"], ["list", self.root, "-h"]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 0, args)
            self.assertEqual(lines, entries.__doc__.splitlines(), args)

    def test_root_without_entries(self):
        missing = os.path.join(self.root, "nowhere")
        for args in (["check", missing], ["list", missing], ["refs", "entries/x.md", missing]):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 2, args)
            self.assertTrue(lines[0].startswith("FAIL: no entries/ folder in "), lines)

    def test_runs_as_a_script_in_utf8(self):
        self.write("entries/2031-02-新.md", entry(title="新的", one_line="一句話"))
        run = subprocess.run([sys.executable, "-I", TOOL, "list", self.root], capture_output=True)
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
        return self.run_tool("story-coverage", self.root, *[a for t in types for a in ("--type", t)])

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
        super().setUp()
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
        code, lines = self.run_tool("story-candidates", question_type, self.root)
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
        return self.run_tool("story-stale", path, self.root)

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
        code, lines = self.run_tool("story-coverage", self.root)
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
        return self.run_tool("story-wording-add", qtype, wording, self.root)

    def listing(self, *types):
        return self.run_tool("story-wordings", self.root, *[a for t in types for a in ("--type", t)])

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
        code, lines = self.run_tool("story-coverage", self.root)
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
        self.assertEqual(self.run_tool("story-wording-add", "Failure", self.root, "--", "-h, really?")[0], 2)
        self.assertEqual(self.run_tool("story-wording-add", "--", "Failure", "--why -h?", self.root),
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
        for args in (["story-wording-add", "Failure"], ["story-wording-add", "Failure", "x", self.root, "y"],
                     ["story-wording-add", "Failure", "x", self.root, "--type", "x"],
                     ["story-wordings", self.root, "y"]):
            self.assertEqual(self.run_tool(*args)[0], 2, args)


class StoryFinishTest(Log):
    BODY = ("\n## How it works\nIt sorts.\n\n## Dead ends and mistakes\nA hunt (sources/resumes/cv-2031.pdf).\n"
            "\n## Pending\n")

    def setUp(self):
        super().setUp()
        self.write(W, entry() + self.BODY)
        self.write(G, entry(title="Gadget"))

    def finish(self, path=W):
        return self.run_tool("story-finish", path, self.root)

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
        self.assertEqual(self.run_tool("story-finish", "stories.md", self.root)[0], 2)

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


if __name__ == "__main__":
    unittest.main()
