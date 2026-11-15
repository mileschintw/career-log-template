#!/usr/bin/env python3
"""Tests for tools/logfiles.py, the helpers the Log's tools share, on made-up text and small Logs
built in a temporary directory.

  python3 -I tools/tests/test_logfiles.py
"""
import ast, datetime, importlib.util, os, re, shutil, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "logfiles.py")
spec = importlib.util.spec_from_file_location("logfiles", TOOL)
logfiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logfiles)

HAS_GIT = shutil.which("git") is not None


class FrontMatter(unittest.TestCase):
    def test_lists_quotes_and_comments(self):
        text = ('---\norg: ["Acme, Inc", "Beta Labs"]   # two\ntitle: "Acme #1 Labs"\nnote: plain # cut\n'
                "tags: [go, kafka]\nlinks:\n  - https://github.com/a/b\n  - 'c # d'\nempty:\n---\n# Body\n")
        self.assertEqual(logfiles.front_matter(text), {
            "org": ["Acme, Inc", "Beta Labs"], "title": "Acme #1 Labs", "note": "plain",
            "tags": ["go", "kafka"], "links": ["https://github.com/a/b", "c # d"], "empty": ""})

    def test_quote_inside_a_quoted_value(self):
        text = "---\norg: 'Children's Hospital'\nname: 'O''Brien Co'   # x\nnote: \"a\" # c\n---\n"
        self.assertEqual(logfiles.front_matter(text),
                         {"org": "Children's Hospital", "name": "O'Brien Co", "note": "a"})

    def test_items_keep_every_line_of_a_repeated_key(self):
        text = "---\norg: Acme\norg:\n  - Beta\nseries:\norg: [Gamma]\n---\n"
        self.assertEqual(logfiles.front_matter(text)["org"], ["Gamma"])
        self.assertEqual(logfiles.front_matter_items(text),
                         [("org", "Acme", False), ("org", "Beta", False), ("org", "Gamma", False)])

    def test_items_say_which_were_quoted(self):
        text = "---\norg: [\"Acme, Inc\", Beta]\nname: 'O''Brien' # c\nnote: Acme, Inc\nlinks:\n  - \"x\"\n---\n"
        self.assertEqual(logfiles.front_matter_items(text), [
            ("org", "Acme, Inc", True), ("org", "Beta", False), ("name", "O'Brien", True),
            ("note", "Acme, Inc", False), ("links", "x", True)])

    def test_closing_line(self):
        unclosed = "---\norg: Acme\n\n# Body\nnote: x\n"
        self.assertEqual(logfiles.front_matter(unclosed), {"org": "Acme", "note": "x"})
        self.assertEqual(logfiles.front_matter(unclosed, closed=True), {})
        self.assertEqual(logfiles.front_matter("# No front matter\norg: x\n"), {})
        self.assertEqual(logfiles.split_front_matter("---\na: 1\n---\nbody\n"), (["a: 1"], 3))
        self.assertEqual(logfiles.split_front_matter("---\r\na: 1\r\n---\r\n"), (["a: 1"], 3))

    def test_as_list(self):
        self.assertEqual(logfiles.as_list("go, kafka ,"), ["go", "kafka"])
        self.assertEqual(logfiles.as_list(["x"]), ["x"])
        self.assertEqual(logfiles.as_list(None), [])


class Tables(unittest.TestCase):
    def test_escaped_pipe(self):
        self.assertEqual(logfiles.md_cells(r"| a \| b | c |"), ["a | b", "c"])
        self.assertEqual(logfiles.md_cells(r"a | b \|"), ["a", "b |"])
        self.assertEqual(logfiles.md_cells("|x||"), ["x", ""])

    def test_cell_spans(self):
        def cells(line):
            return [line[a:b] for a, b in logfiles.md_cell_spans(line)]
        self.assertEqual(cells("| a \\| b | |\r\n"), [" a \\| b ", " "])
        self.assertEqual(cells("  |x||\n"), ["x", ""])
        self.assertEqual(cells("| a | b  \n"), [" a ", " b"])   # no closing pipe
        self.assertEqual(cells("a | b |"), ["a ", " b "])        # no leading pipe

    def test_row_round_trip(self):
        cells = ["a | b", "two\nlines", 3]
        line = logfiles.md_row(cells)
        self.assertEqual(line, r"| a \| b | two lines | 3 |")
        self.assertEqual(logfiles.md_cells(line), ["a | b", "two lines", "3"])

    def test_tables_sections_and_rules(self):
        text = ("\ufeff| **Question type** | Stories |\n|:---|---:|\n| Bug | x |\n\n"
                "## Applications\n\n| Date | `Company` |\n|---|---|\n| 2031-01-01 | Acme \\| Co |\n| | |\n"
                "text\n| Late | table |\n")
        tables = logfiles.md_tables(text)
        self.assertEqual([(t.line, t.section, t.header) for t in tables],
                         [(1, None, ["question type", "stories"]), (7, "Applications", ["date", "company"]),
                          (12, "Applications", ["late", "table"])])
        self.assertEqual(tables[0].head, ["**Question type**", "Stories"])
        self.assertEqual(tables[1].rows, [(9, ["2031-01-01", "Acme | Co"])])
        self.assertEqual(tables[1].dicts(), [{"date": "2031-01-01", "company": "Acme | Co"}])
        self.assertEqual(tables[2].rows, [])
        self.assertEqual([t.end for t in tables], [3, 10, 12])   # #651 C2: the last line, an empty row too

    def test_provenance_rows(self):
        text = ("# Provenance\n\n| Claim | Entry › section | Source |\n|---|---|---|\n"
                "| a \\| b | entries/x.md › Context | sources/y |\n\n| Note | Other |\n|---|---|\n| n | o |\n\n"
                "## Company context\n\n| Fact | Source |\n|---|---|\n| f | https://x |\n\n"
                "## Risks to handle in conversation\n\n| Risk | Entry |\n|---|---|\n| r | e |\n\n"
                "## More\n\n| Claim | Source |\n|---|---|\n| m | s |\n")
        self.assertEqual(logfiles.provenance_rows(text), [
            (5, ["a | b", "entries/x.md › Context", "sources/y"], ["Claim", "Entry › section", "Source"]),
            (27, ["m", "s"], ["Claim", "Source"])])


class Sections(unittest.TestCase):
    TEXT = ("# Title\n\n## One line\n<!-- c -->\nShort.\n### Sub\nkept\n## Context\n- a\n  - b\n-c\n"
            "```sh\n# a shell comment\n```\n- d\n## Last")

    def test_ends(self):
        self.assertEqual(logfiles.section(self.TEXT, "One line"), "<!-- c -->\nShort.\n### Sub\nkept\n")
        self.assertEqual(logfiles.section(self.TEXT, "Context"),
                         "- a\n  - b\n-c\n```sh\n# a shell comment\n```\n- d\n")
        self.assertEqual(logfiles.section(self.TEXT, "Last"), "")
        self.assertIsNone(logfiles.section(self.TEXT, "Missing"))
        self.assertEqual(logfiles.section(self.TEXT, "Sub", level=3), "kept\n")

    def test_bullets_and_comments(self):
        self.assertEqual(logfiles.bullets(logfiles.section(self.TEXT, "Context")), ["a", "b", "d"])
        self.assertEqual(logfiles.bullets("<!--\n- hidden\n-->\n- shown\n"), ["shown"])
        self.assertEqual(logfiles.strip_comments("a<!-- x\ny -->b"), "ab")

    def test_heading_anchors(self):
        text = ("# Title\n## Dead ends\n## Dead ends\n### C++ / Go!\n```\n## In code\n```\n<!-- ## Hidden -->\n"
                "## Done ##\n")
        self.assertEqual(logfiles.heading_anchors(text), {"dead-ends", "dead-ends-1", "c--go", "done"})
        self.assertEqual(logfiles.heading_names(text), {"dead-ends": "Dead ends", "dead-ends-1": "Dead ends",
                                                        "c--go": "C++ / Go!", "done": "Done"})
        self.assertEqual(logfiles.anchor("  What I Did  "), "what-i-did")

    def test_heading_forms_and_comments(self):
        """#651 C1: one rule for a section's heading: spaces or tabs around it, a CRLF line end, and
        no heading inside an HTML comment, as the Entries section reads it."""
        text = "# Log\n<!--\n## Entries\nold\n-->\n##  Entries \t\r\nrow\n<!-- ## Other -->\n# not an end\n## Next\n"
        self.assertEqual(logfiles.section(text, "Entries"), "row\n<!-- ## Other -->\n# not an end\n")
        self.assertEqual(logfiles.heading_re("Entries").search(logfiles.blank_comments(text)).group(0), "##  Entries \t\r")
        lines = text.splitlines(keepends=True)
        self.assertEqual(logfiles.section_lines(lines, "Entries"), (5, 9))
        self.assertEqual(logfiles.section_lines(lines, "Next"), (9, 10))
        self.assertEqual(logfiles.section_lines(["## Last"], "Last"), (0, 1))
        self.assertIsNone(logfiles.section_lines(lines, "Other"))

    def test_outside_code(self):
        """#651 C10: the fenced-code rule heading_names and entries.py diff share."""
        lines = ["a", "````md", "```", "# in code", "````", "~~~", "b", "~~~", "c", "```", "unclosed"]
        self.assertEqual(list(logfiles.outside_code(lines)), [(0, "a"), (8, "c")])


class Names(unittest.TestCase):
    def test_slugs(self):
        self.assertEqual(logfiles.entry_slug("entries/2031-04-widget-sorter.md"), "widget-sorter")
        self.assertEqual(logfiles.question_slug("Why this company?"), "why-this-company")
        self.assertEqual(logfiles.question_slug("為什麼 選我們"), "為什麼-選我們")
        self.assertEqual(logfiles.ascii_slug("Acme & Co. — Dev"), "acme-co-dev")
        self.assertEqual(logfiles.ascii_slug("職缺"), "")

    def test_split_dated(self):
        self.assertEqual(logfiles.split_dated("2031-05-01-acme-dev"), ("2031-05-01", "acme-dev"))
        self.assertEqual(logfiles.split_dated("acme-dev"), (None, "acme-dev"))
        self.assertEqual(logfiles.split_dated("2031-05-01-"), ("2031-05-01", ""))

    def test_repo_segments(self):
        value = ("https://github.com/acme-dev/widget.git https://gitlab.example.edu/group/sub/repo/-/tree/main "
                 "https://github.com/a/b/pull/7 https://github.com/@/x https://example.org/c")
        self.assertEqual(logfiles.repo_segments(value), ["acme-dev", "widget", "group", "sub", "repo", "a", "b", "x"])

    def test_tex_items(self):
        tex = ("\\usepackage{enumitem} % lists: itemize and \\item\n\\begin{itemize}\n"
               "  \\item Cut costs by \\textbf{30\\%}  across\n    three teams % a note\n"
               "  \\item[--] Second\n  % a comment-only line\n  continued\n\n  stray line\n\\end{itemize}\n"
               "\\item Last \\item Two on one line\n")
        self.assertEqual(logfiles.tex_items(tex), [
            (3, "Cut costs by \\textbf{30\\%} across three teams"), (5, "Second continued"),
            (11, "Last"), (11, "Two on one line")])

    def test_tex_bullets(self):
        """#524: items under an Education or Skills heading are no bullet; a bold label starts one."""
        tex = ("\\section*{Skills}\n\\begin{itemize}\n  \\item \\textbf{Languages:} Go, SQL\n\\end{itemize}\n"
               "\\section*{Work Experience}\n\\begin{itemize}\n  \\item \\textbf{Queue:} Built a job queue\n"
               "  \\item \\textbf{24x} less memory\n\\end{itemize}\n% \\section*{Education}\n"
               "\\section*{Education \\& Coursework}\n\\begin{itemize}\n"
               "  \\item {\\small \\textbf{Related Courses:} Distributed Systems}\n\\end{itemize}\n"
               "\\section{Research}\n\\begin{itemize}\n  \\item Measured cache hit rates\n\\end{itemize}\n")
        self.assertEqual(logfiles.tex_bullets(tex), [
            (7, "\\textbf{Queue:} Built a job queue"), (8, "\\textbf{24x} less memory"), (17, "Measured cache hit rates")])
        self.assertEqual(logfiles.tex_bullets("\\begin{itemize}\n  \\item No heading above\n\\end{itemize}\n"
                                              "\\section*{Projects \\& Skills}\n  \\item Built a cache\n"),
                         [(2, "No heading above"), (5, "Built a cache")])

    def test_tex_comments(self):
        """#651 C4: \\\\% is a line break, then a comment; a % in an \\href address is none."""
        tex = ("\\item See \\href{https://example.com/a%20b}{the demo} % a note\n"
               "\\item Line one\\\\% gone\n\\item Grew 40\\% a year\n")
        self.assertEqual(logfiles.tex_items(tex), [
            (1, "See \\href{https://example.com/a%20b}{the demo}"), (2, "Line one\\\\"), (3, "Grew 40\\% a year")])
        self.assertEqual(logfiles.tex_comment_at("\\url{x%y} 5% off"), 11)
        self.assertIsNone(logfiles.tex_comment_at("40\\% off"))

    def test_tex_sections(self):
        """#651 C5: a section is read in the body only, and one with bullets is no Skills section."""
        tex = ("\\newcommand{\\skills}{\\section*{Skills}}\n\\begin{document}\n"
               "\\begin{itemize}\n  \\item Built a cache\n\\end{itemize}\n"
               "\\section*{Experience and Skills}\n  \\item Ran the queue\n\n\\section{Technical Skills}\n"
               "  \\item \\textbf{Go:} yes\n")
        self.assertEqual(logfiles.tex_sections(tex), [(6, "Experience and Skills"), (9, "Technical Skills")])
        self.assertEqual(logfiles.tex_bullets(tex), [(4, "Built a cache"), (7, "Ran the queue")])
        self.assertEqual([logfiles.is_skills(t) for t in ("Experience and Skills", "Technical Skills", "Education")],
                         [False, True, False])

    def test_tex_line_break(self):
        """#651 C6: every form of a line break inside a source line."""
        self.assertEqual(logfiles.TEX_LINE_BREAK.split("a\\\\b\\\\*c\\\\[2pt]d\\\\ [2pt]e\\newline f\\newlines"),
                         ["a", "b", "c", "d", "e", " f\\newlines"])


class ArgPath(unittest.TestCase):
    def test_root_then_the_current_folder(self):
        """#651 C8: a relative path is read against root first, then the current folder."""
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as here:
            for folder, name in ((root, "both.md"), (here, "both.md"), (here, "here.md")):
                open(os.path.join(folder, name), "w").close()
            saved = os.getcwd()
            try:
                os.chdir(here)
                same = lambda p: os.path.normcase(os.path.realpath(p))
                self.assertEqual(same(logfiles.arg_path(root, "both.md")), same(os.path.join(root, "both.md")))
                self.assertEqual(same(logfiles.arg_path(root, "here.md")), same(os.path.join(here, "here.md")))
                self.assertIsNone(logfiles.arg_path(root, "none.md"))
                self.assertIsNone(logfiles.arg_path(root, "both.md", os.path.isdir))
                full = os.path.join(here, "here.md")
                self.assertEqual(logfiles.arg_path(root, full), full)
            finally:
                os.chdir(saved)


class Files(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, rel, text="x\n"):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_read_and_write(self):
        path = os.path.join(self.root, "a.md")
        with open(path, "wb") as f:
            f.write(b"\xef\xbb\xbfhello\r\n")
        self.assertEqual(logfiles.read_text(path), "hello\n")
        logfiles.write_text(path, "one\ntwo\n")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"one\ntwo\n")
        with open(path, "wb") as f:
            f.write(b"\xff\xfe")
        with self.assertRaises(UnicodeDecodeError):
            logfiles.read_text(path)

    def test_log_files(self):
        for rel in ("README.md", "config.toml", "scan-sources.md", "notes.md", "entries/_template.md",
                    "entries/2031-01-a.md", "stories/wordings/why.md", "sources/inbox/cv.txt",
                    "sources/resumes/cv.tex", "outputs/.hidden/x.md", "tools/check.py"):
            self.write(rel)
        self.assertEqual(logfiles.log_files(self.root), [
            "README.md", "config.toml", "scan-sources.md", "entries/2031-01-a.md", "stories/wordings/why.md",
            "sources/resumes/cv.tex"])
        self.assertEqual(logfiles.LOG_PATHS[:5], ["entries", "stories", "outputs", "sources",
                                                  ":(exclude)entries/_template.md"])
        self.assertEqual(set(logfiles.LOG_PATHS[5:]), set(logfiles.LOG_FILES))

    def test_roots(self):
        script = os.path.join(self.root, "tools", "x.py")
        self.assertEqual(logfiles.default_root(script), self.root)
        self.assertEqual(logfiles.split_root(["list", "--root", "/r", "a"], script), ("/r", ["list", "a"]))
        self.assertEqual(logfiles.split_root(["--root=/r"], script), ("/r", []))
        self.assertEqual(logfiles.split_root(["a", "--", "--root", "b"], script),
                         (self.root, ["a", "--", "--root", "b"]))
        for args in (["--root"], ["--root="], ["--root", "a", "--root", "b"]):
            with self.assertRaises(logfiles.LogError):
                logfiles.split_root(args, script)
        os.makedirs(os.path.join(self.root, ".git"))
        self.write("outputs/applications/x/provenance.md")
        self.assertEqual(logfiles.find_log_root(os.path.join(self.root, "outputs", "applications", "x",
                                                             "provenance.md")), self.root)
        self.assertEqual(logfiles.find_log_root(os.path.join(self.root, "outputs")), self.root)


@unittest.skipUnless(HAS_GIT, "no git on PATH")
class Git(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.run_git("init", "-q", "-b", "main")

    def run_git(self, *args, cwd=None):
        subprocess.run(["git", "-C", cwd or self.root] + list(args), check=True, capture_output=True)

    def test_git(self):
        self.assertEqual(logfiles.git(self.root, "rev-parse", "--is-inside-work-tree"), "true\n")
        with self.assertRaises(logfiles.LogError) as e:
            logfiles.git(self.root, "log")
        self.assertTrue(str(e.exception).startswith("git log failed: "))
        self.assertNotEqual(logfiles.git_run(self.root, "log").returncode, 0)

    def test_no_git(self):
        path = os.environ.get("PATH", "")
        os.environ["PATH"] = self.root
        try:
            with self.assertRaises(logfiles.LogError):
                logfiles.git(self.root, "status")
        finally:
            os.environ["PATH"] = path

    def test_git_blob_in_a_log_below_the_top(self):
        """#651 C9: a path is read from the Log's root, a folder below the git top level."""
        log = os.path.join(self.root, "log")
        os.makedirs(log)
        for folder, text in ((self.root, "top"), (log, "log")):
            with open(os.path.join(folder, "README.md"), "w") as f:
                f.write(text)
        self.run_git("add", "-A")
        self.run_git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "x")
        self.assertEqual(logfiles.git_blob(log, "HEAD", "README.md"), b"log")
        self.assertEqual(logfiles.git_blob(log, "", "./README.md"), b"log")   # the index
        self.assertEqual(logfiles.git_blob(self.root, "HEAD", "README.md"), b"top")
        self.assertIsNone(logfiles.git_blob(log, "HEAD", "log/README.md"))

    def test_local_identity(self):
        self.assertEqual(logfiles.local_identity(self.root), (None, None))
        self.run_git("config", "--local", "user.email", "me@example.com")
        self.assertEqual(logfiles.local_identity(self.root), (None, "me@example.com"))

    def test_checkouts(self):
        self.run_git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "x")
        tree = os.path.join(self.root, ".worktrees", "topic")
        self.run_git("worktree", "add", "-q", tree, "-b", "topic")
        real = lambda ps: [os.path.normcase(os.path.realpath(p)) for p in ps]
        self.assertEqual(real(logfiles.checkouts(tree)), real([self.root, tree]))   # main checkout first
        with self.assertRaises(logfiles.LogError):
            logfiles.checkouts(os.path.join(self.root, "no-such-folder"))

    def test_default_branch(self):
        self.assertIsNone(logfiles.default_branch(self.root))
        self.assertIsNone(logfiles.set_default_branch(self.root))   # no origin
        remote = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, remote, True)
        self.run_git("init", "-q", "--bare", "-b", "trunk", cwd=remote)
        self.run_git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty",
                     "-m", "x")
        self.run_git("remote", "add", "origin", remote)
        self.run_git("push", "-q", "origin", "main:trunk")
        self.assertIsNone(logfiles.default_branch(self.root))   # origin/HEAD not set yet: read-only
        self.assertEqual(logfiles.set_default_branch(self.root), "trunk")
        self.assertEqual(logfiles.default_branch(self.root), "trunk")


class Imports(unittest.TestCase):
    def test_imports_on_an_older_python(self):
        # tools/check.py imports it before it tells the user that the Log needs Python 3.11+
        with open(TOOL, encoding="utf-8") as f:
            source = f.read()
        ast.parse(source, TOOL, feature_version=(3, 8))
        self.assertNotIn("tomllib", source)



class ShellArg(unittest.TestCase):
    def test_quotes(self):
        self.assertEqual(logfiles.shell_arg("Q&R Partners"), "'Q&R Partners'")
        for text in ("O'Neil", "Ferrow’s", "a‚b", "a‛b"):
            self.assertEqual(logfiles.shell_arg(text), '"%s"' % text, text)
        both = logfiles.shell_arg("O'Neil $x")
        self.assertEqual(both, "'O''Neil $x'" if os.name == "nt" else "'O'\\''Neil $x'")


class TargetContract(unittest.TestCase):
    """The Target versions, target names and posting slugs every tool shares (#661)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, root, rel, text):
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_targets_in_a_root_with_glob_characters(self):
        root = os.path.join(self.tmp, "log [1]")
        self.write(root, "outputs/resumes/backend.tex", "x")
        self.assertEqual(logfiles.targets(root), ["backend"])

    def test_application_records_in_a_root_with_glob_characters(self):
        root = os.path.join(self.tmp, "log [1]")
        self.write(root, "outputs/applications/2026-09-01-acme-swe/posting.md", "https://acme.com/j/1\n")
        self.assertEqual([w for _, _, w in logfiles.application_records(root)], ["outputs/applications/2026-09-01-acme-swe"])

    def test_a_part_another_target_inputs_is_no_target(self):
        root = os.path.join(self.tmp, "log")
        self.write(root, "outputs/resumes/backend.tex", "\\input{header}\n")
        self.write(root, "outputs/resumes/header.tex", "% shared header\n")
        self.write(root, "outputs/resumes/pm.tex", "x")
        self.assertEqual(logfiles.targets(root), ["backend", "pm"])
        self.write(root, "outputs/resumes/header.pdf", "")   # built on its own: a resume after all
        self.assertEqual(logfiles.targets(root), ["backend", "header", "pm"])

    def test_target_names(self):
        for name, ok in (("backend", True), ("ml-infra", True), ("", False), ("Backend", False), ("a b", False)):
            self.assertEqual(logfiles.is_target_name(name), ok, name)

    def test_posting_slug(self):
        self.assertEqual(logfiles.posting_slug("Acme, Inc."), "acme-inc")
        self.assertEqual(logfiles.posting_slug("日本"), "posting")

    def test_start_record(self):
        text = logfiles.start_record_text("outputs/resumes/backend.tex", "backend", "1")
        self.assertEqual(text, "from: outputs/resumes/backend.tex\nfamily: backend\ntier: 1\n")
        self.assertEqual(logfiles.start_record_lacks(logfiles.parse_start_record(text)), [])
        self.assertEqual(logfiles.start_record_lacks(logfiles.parse_start_record("from: x\n")), ["family:", "tier:"])

    def test_plural(self):
        self.assertEqual([logfiles.plural(n, "commit") for n in (0, 1, 2)], ["0 commits", "1 commit", "2 commits"])


class RunFolder(unittest.TestCase):
    """A posting run's folder and key, and the session it recorded, as scan.py writes them (#662, ADR 0014)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_run_key_and_folder(self):
        self.assertEqual(logfiles.run_key("2026-10-22", "041500"), "2026-10-22-041500")
        self.assertEqual(logfiles.run_key("2026-10-22", "041500", 3), "2026-10-22-041500-3")
        m = logfiles.RUN_KEY.match("2026-10-22-041500-3")
        self.assertEqual(m.group("date", "hh", "mm", "ss", "n"), ("2026-10-22", "04", "15", "00", "3"))
        for bad in ("2026-10-22", "2026-10-22-0415", "notes", "2026-10-22-041500-"):
            self.assertIsNone(logfiles.RUN_KEY.match(bad), bad)
        self.assertEqual(logfiles.run_folder("2026-10-22-041500"), ".build/runs/2026-10-22-041500")

    def test_run_session(self):
        root = os.path.join(self.tmp, "log [1]")
        folder = os.path.join(root, *logfiles.run_folder("2026-10-22-041500").split("/"))
        os.makedirs(folder)
        self.assertIsNone(logfiles.run_session(root, "2026-10-22-041500"))   # a run started with no --session
        logfiles.write_text(os.path.join(folder, logfiles.RUN_SESSION), "2026-10-22-040000\n")
        self.assertEqual(logfiles.run_session(root, "2026-10-22-041500"), "2026-10-22-040000")
        logfiles.write_text(os.path.join(folder, logfiles.RUN_SESSION), "../x\n")
        self.assertIsNone(logfiles.run_session(root, "2026-10-22-041500"))
        self.assertIsNone(logfiles.run_session(root, "../x"))


class SessionRecord(unittest.TestCase):
    """A session's key, baseline and claims (ADR 0014), as check.py and sync.py write and read them."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = os.path.join(self.tmp, "log [1]")   # a glob character in the path, as #662 B1
        os.makedirs(self.root)

    def test_new_session_keys_and_record(self):
        a = logfiles.new_session(self.root, {"profile.md": "abc"})
        b = logfiles.new_session(self.root, {})
        self.assertTrue(logfiles.SESSION_KEY.match(a) and logfiles.SESSION_KEY.match(b))
        self.assertNotEqual(a, b)   # two in one second get -2
        record = logfiles.read_session(self.root, a)
        self.assertEqual((record["baseline"], record["claims"]), ({"profile.md": "abc"}, []))
        self.assertIsNotNone(datetime.datetime.fromisoformat(record["start"]).tzinfo)
        self.assertEqual(sorted(logfiles.sessions(self.root)), sorted([a, b]))
        self.assertIsNone(logfiles.read_session(self.root, "notes"))
        self.assertIsNone(logfiles.read_session(self.root, "2026-10-22-041500"))

    def test_an_unreadable_record_is_no_session(self):
        key = logfiles.new_session(self.root, {})
        logfiles.write_text(logfiles.session_path(self.root, key), "not json\n")
        self.assertIsNone(logfiles.read_session(self.root, key))
        self.assertEqual(logfiles.sessions(self.root), {})

    def test_an_old_session_with_no_claim_is_deleted_and_one_with_claims_kept(self):
        old_date = (datetime.date.today() - datetime.timedelta(days=logfiles.SESSION_KEEP_DAYS + 1)).isoformat()
        idle, holding = old_date + "-100000", old_date + "-110000"
        logfiles.write_session(self.root, idle, {"start": None, "baseline": {}, "claims": []})
        logfiles.write_session(self.root, holding, {"start": None, "baseline": {}, "claims": ["profile.md"]})
        key = logfiles.new_session(self.root, {})
        self.assertEqual(sorted(logfiles.sessions(self.root)), sorted([holding, key]))   # time never releases a claim

    def test_holder_and_release(self):
        a = logfiles.new_session(self.root, {})
        b = logfiles.new_session(self.root, {})
        logfiles.write_session(self.root, a, {"start": None, "baseline": {}, "claims": ["entries/", "profile.md"]})
        records = logfiles.sessions(self.root)
        self.assertEqual(logfiles.holder(records, "entries/2024-01-a.md"), a)   # under a claimed folder
        self.assertEqual(logfiles.holder(records, "entries"), a)
        self.assertIsNone(logfiles.holder(records, "profile.md", but=a))
        self.assertIsNone(logfiles.holder(records, "stories.md"))
        self.assertEqual(logfiles.release_claims(self.root, a, ["profile.md", "stories.md"]), ["profile.md"])
        self.assertEqual(logfiles.release_claims(self.root, a), ["entries/"])
        self.assertEqual(logfiles.read_session(self.root, a)["claims"], [])   # the record stays: idle, with its key
        self.assertEqual(logfiles.release_claims(self.root, "2026-01-01-000000"), [])
        self.assertIn(b, logfiles.sessions(self.root))

    def test_the_lock_is_taken_over_once_stale(self):
        lock = os.path.join(self.root, *logfiles.SESSIONS.split("/"), logfiles.LOCK)
        os.makedirs(os.path.dirname(lock))
        open(lock, "w").close()
        os.utime(lock, (time.time() - logfiles.LOCK_STALE - 5,) * 2)
        with logfiles.session_lock(self.root):
            self.assertTrue(os.path.exists(lock))
        self.assertFalse(os.path.exists(lock))

    def test_file_hash_and_log_paths(self):
        logfiles.write_text(os.path.join(self.root, "profile.md"), "p\n")
        self.assertEqual(len(logfiles.file_hash(self.root, "profile.md")), 64)
        self.assertEqual(logfiles.file_hash(self.root, "gone.md"), logfiles.GONE)
        for path in ("profile.md", "entries/2024-01-a.md", "entries/", "outputs/applications/x/cover.md"):
            self.assertTrue(logfiles.is_log_path(path), path)
        for path in ("tools/check.py", "entries/_template.md", "sources/inbox/cv.txt", ".build/x", "SETUP.md"):
            self.assertFalse(logfiles.is_log_path(path), path)


REPO = os.path.join(HERE, "..", "..")
# The glob calls that stay by hand, each as its source text, by file, with why: glob_under cannot
# take their shape (#773). Any other glob, under a folder of the Log or not (a home, LOCALAPPDATA,
# Playwright's cache), calls logfiles.glob_under, which escapes the folder (#671, #712, #747).
OUTSIDE_THE_LOG = {
    # resume.APPDATA_STORE is one pattern string with the %LOCALAPPDATA% token in it, not path segments
    "tools/check.py": ["glob.glob(resume_module().APPDATA_STORE.replace('%LOCALAPPDATA%', glob.escape(local)) + 'npm')"],
    # a written pattern with ~ or a $VAR or %VAR% anywhere in it: _expand escapes each value in place
    "tools/resume.py": ["glob.glob(_expand(pattern))"],
}


def glob_under_shape(text):
    """True when a glob call's source text is glob_under's body copied: glob.glob or glob.iglob of
    os.path.join with glob.escape(folder) first, the call to make logfiles.glob_under(folder, ...)."""
    call = ast.parse(text, mode="eval").body
    join = call.args[0] if isinstance(call, ast.Call) and call.args else None
    return (isinstance(join, ast.Call) and ast.unparse(join.func) == "os.path.join" and bool(join.args)
            and isinstance(join.args[0], ast.Call) and ast.unparse(join.args[0].func) == "glob.escape")


def tool_sources():
    """[(repo-relative path, source)] of each tool a guard test scans: the .py files of tools/ and
    skills/career-log/."""
    rels = ["%s/%s" % (folder, name) for folder in ("tools", "skills/career-log")
            for name in sorted(os.listdir(os.path.join(REPO, *folder.split("/")))) if name.endswith(".py")]
    return [(rel, logfiles.read_text(os.path.join(REPO, *rel.split("/")))) for rel in rels]


def hand_globs(source):
    """[(line, source text)] of each glob.glob() or glob.iglob() call in a Python source, and of
    each `from glob import` that would hide one, in line order."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module == "glob":
            found.append((node.lineno, ast.unparse(node)))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr in ("glob", "iglob")
              and isinstance(node.func.value, ast.Name) and node.func.value.id == "glob"):
            found.append((node.lineno, ast.unparse(node)))
    return sorted(found)


class ProjectFolder(unittest.TestCase):
    """find_project_folder: Claude Code's folder for a working directory."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.projects = os.path.join(self.tmp, "projects")

    def test_a_folder_named_from_the_path_as_given(self):
        folder = os.path.join(self.projects, logfiles.claude_folder(os.path.join(self.tmp, "log")))
        os.makedirs(folder)
        self.assertEqual(logfiles.find_project_folder(self.projects, os.path.join(self.tmp, "log")), folder)
        self.assertIsNone(logfiles.find_project_folder(self.projects, os.path.join(self.tmp, "other")))

    @unittest.skipIf(os.name == "nt", "a symlink needs extra rights on Windows")
    def test_a_checkout_reached_through_a_symlink_is_found_by_its_real_path(self):
        # #768: Claude Code names the folder from its resolved working directory (macOS's /var is /private/var)
        real = os.path.join(self.tmp, "real")
        os.makedirs(os.path.join(real, "log"))
        link = os.path.join(self.tmp, "link")
        os.symlink(real, link)
        folder = os.path.join(self.projects, logfiles.claude_folder(os.path.realpath(os.path.join(real, "log"))))
        os.makedirs(folder)
        self.assertEqual(logfiles.find_project_folder(self.projects, os.path.join(link, "log")), folder)


class ClaudeFolder(unittest.TestCase):
    """claude_folder: the name Claude Code gives a working directory's project folder (#788)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    @unittest.skipIf(os.name == "nt", "a symlink needs extra rights on Windows")
    def test_a_path_through_a_symlink_gets_the_resolved_paths_name(self):
        # Claude Code names the folder from its resolved working directory (macOS's /tmp is /private/tmp)
        real = os.path.join(self.tmp, "real")
        os.makedirs(os.path.join(real, "log"))
        link = os.path.join(self.tmp, "link")
        os.symlink(real, link)
        self.assertEqual(logfiles.claude_folder(os.path.join(link, "log")),
                         logfiles.claude_folder(os.path.realpath(os.path.join(real, "log"))))

    @unittest.skipUnless(os.name == "nt", "the Windows rule")
    def test_on_windows_the_path_is_named_as_given(self):
        # unchanged by #788: realpath there can swap a subst or mapped drive for its target
        path = os.path.join(self.tmp, "a_b c.d")
        self.assertEqual(logfiles.claude_folder(path), re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path)))

    def test_every_character_outside_letters_and_digits_becomes_a_dash(self):
        name = logfiles.claude_folder(os.path.join(self.tmp, "a_b c.d"))
        self.assertTrue(name.endswith("a-b-c-d"))
        self.assertRegex(name, r"^[A-Za-z0-9-]+$")


class GlobUnder(unittest.TestCase):
    """glob_under, the one place a tool globs under a folder read as written, in the Log or outside
    it, and the guard that keeps it the one (#683, #773; #671 was a copy without glob.escape)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_a_folder_with_glob_characters(self):
        folder = os.path.join(self.tmp, "log [1]", "a[b]")
        os.makedirs(os.path.join(folder, "sub"))
        for rel in ("x.md", "y.txt", "sub/z.md"):
            logfiles.write_text(os.path.join(folder, *rel.split("/")), "")
        self.assertEqual(logfiles.glob_under(folder, "*.md"), [os.path.join(folder, "x.md")])
        self.assertEqual(logfiles.glob_under(folder, "*", "*.md"), [os.path.join(folder, "sub", "z.md")])
        self.assertEqual(logfiles.glob_under(os.path.join(self.tmp, "none"), "*"), [])

    def test_the_guard_reads_each_way_to_glob_by_hand(self):
        self.assertEqual([line for line, _ in hand_globs(
            "import glob, os\n"
            "a = glob.glob(os.path.join(glob.escape(root), '*.md'))\n"   # the copied pattern
            "b = sorted(glob.glob(\n    os.path.join(root, '*')))\n"      # #671: no escape
            "c = glob.iglob(root + '/*')\n"
            "from glob import glob as g\n"
            "# glob.glob( in a comment\n"
            "d = logfiles.glob_under(root, glob.escape(name) + '-*.png')\n")], [2, 3, 5, 6])

    def test_the_list_holds_no_call_glob_under_takes(self):
        self.assertTrue(glob_under_shape("glob.glob(os.path.join(glob.escape(cache), f, 'chrome-*', 'chrome'))"))
        self.assertTrue(glob_under_shape("glob.iglob(os.path.join(glob.escape(home), '.nvm'))"))
        self.assertFalse(glob_under_shape("glob.glob(os.path.join(root, '*'))"))   # #671: a bug, not this shape
        self.assertFalse(glob_under_shape("glob.glob(_expand(pattern))"))
        self.assertFalse(glob_under_shape("glob.glob(STORE.replace('%L%', glob.escape(local)) + 'npm')"))
        self.assertEqual([(rel, text) for rel, texts in OUTSIDE_THE_LOG.items() for text in texts
                          if glob_under_shape(text)], [], "call logfiles.glob_under for these instead")

    def test_no_tool_globs_by_hand(self):
        fails = []
        for rel, source in tool_sources():
            found = hand_globs(source)
            if rel == "tools/logfiles.py":
                self.assertEqual(len(found), 1, "tools/logfiles.py globs once, in glob_under")
                continue
            allowed = list(OUTSIDE_THE_LOG.get(rel, []))
            for line, text in found:
                if text in allowed:
                    allowed.remove(text)
                else:
                    fails.append("%s:%d: glob by hand: %s" % (rel, line, text))
            fails += ["%s: OUTSIDE_THE_LOG lists %s, and it has no such call" % (rel, text) for text in allowed]
        fails += ["%s: OUTSIDE_THE_LOG lists a file that is not there" % rel
                  for rel in OUTSIDE_THE_LOG if not os.path.isfile(os.path.join(REPO, *rel.split("/")))]
        self.assertEqual(fails, [], "\n" + "\n".join(fails) + "\nCall logfiles.glob_under(folder, pattern) "
                         "for a glob under any folder, in the Log or outside it (a home, LOCALAPPDATA): it "
                         "escapes the folder. Only a call glob_under cannot take (a pattern written as one "
                         "string with the folder in it) is listed in OUTSIDE_THE_LOG, with the reason.")


# ---- One reader each for a PDF's text, an HTML page's text and a local time (#791) ----

# The pdftotext calls that stay by hand, each as its source text, by file, with why: resume.pdf_text
# reads a PDF's plain text to stdout, and these ask pdftotext for something else.
PDFTOTEXT_BY_HAND = {
    "tools/resume.py": [
        # the layout check reads each line's box (-bbox-layout XML), not the plain text
        "subprocess.run([find_poppler_bin('pdftotext'), '-enc', 'UTF-8', '-bbox-layout', pdf, '-'], "
        "capture_output=True, text=True, encoding='utf-8', errors='replace')",
        # --outdir writes the text layer to a file beside the PDF for the agent to read
        "subprocess.run([find_poppler_bin('pdftotext'), '-enc', 'UTF-8', pdf, txt], capture_output=True)",
    ],
}


def hand_pdftotext(source):
    """[(line, source text)] of each call that passes pdftotext's `-enc` (a pdftotext run), in line order."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and any(
                isinstance(a, (ast.List, ast.Tuple)) and any(isinstance(e, ast.Constant) and e.value == "-enc" for e in a.elts)
                for a in node.args):
            found.append((node.lineno, ast.unparse(node)))
    return sorted(found)


def hand_html_parsers(source):
    """[(line, source text)] of each html.parser.HTMLParser subclass, and of each `from html.parser
    import` that would hide one, in line order."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module == "html.parser":
            found.append((node.lineno, ast.unparse(node)))
        elif isinstance(node, ast.ClassDef) and any(ast.unparse(b).split(".")[-1] == "HTMLParser"
                                                    for b in node.bases):   # html.parser.HTMLParser, hp.HTMLParser
            found.append((node.lineno, "class %s(%s)" % (node.name, ", ".join(ast.unparse(b) for b in node.bases))))
    return sorted(found)


class TextReaders(unittest.TestCase):
    """logfiles.html_text and logfiles.local_time, and resume.pdf_text: one reader each, and the
    guards that keep them one (#791: application.py had added a second or third copy of each)."""
    def test_html_text(self):
        page = ("<html><head><title>T</title><meta charset=utf-8><body><script>x()</script>"
                "<h1>Role</h1><p>Two\n  words&nbsp;here</p><ul><li>One</li><li>Two</li></ul>"
                "<table><tr><td>Location</td><td>Remote</td></tr></table><svg><text>logo</text></svg>")
        lines = [l for l in logfiles.html_text(page).split("\n") if l]
        self.assertEqual(lines, ["Role", "Two words\xa0here", "One", "Two", "Location", "Remote"])
        mail = page.replace("<body>", "</head><body>")   # mail hides head, so its body comes after a </head>
        marked = [l for l in logfiles.html_text(mail, hide=("head",), marks=True).split("\n") if l]
        self.assertEqual(marked, ["Role", "Two words\xa0here", "- One", "- Two", "\tLocation\tRemote"])
        self.assertEqual(logfiles.html_text("<div>Line one\nline two</div><pre>x\n  y</pre>").split("\n"),
                         ["", "Line one line two", "", "x", "y", ""])   # only <pre> keeps its breaks
        # no </head>: a page's body is still read unless the caller hides head
        self.assertEqual([l for l in logfiles.html_text("<head><title>T</title><body><p>Duties").split("\n") if l],
                         ["Duties"])

    def test_local_time(self):
        utc = datetime.datetime(2025, 10, 2, 6, 30, tzinfo=datetime.timezone.utc)
        local = utc.astimezone()
        self.assertEqual(logfiles.local_time("2025-10-02T06:30:00Z"), local)
        self.assertEqual(logfiles.local_time("2025-10-02T12:00:00+05:30"), local)
        self.assertEqual(logfiles.local_time("2025-10-01T22:30:00-0800"), local)
        self.assertEqual(logfiles.local_time(utc), local)
        naive = logfiles.local_time("2025-10-02T06:30:00")   # no zone: this machine's time already
        self.assertEqual((naive.replace(tzinfo=None), naive.utcoffset()),
                         (datetime.datetime(2025, 10, 2, 6, 30), datetime.datetime(2025, 10, 2, 6, 30).astimezone().utcoffset()))

    def test_the_guards_read_each_copied_form(self):
        self.assertEqual([line for line, _ in hand_pdftotext(
            "import subprocess\n"
            "a = subprocess.run([exe, '-enc', 'UTF-8', pdf, '-'], capture_output=True)\n"
            "b = subprocess.check_output((find('pdftotext'), '-enc', 'UTF-8', p, '-'))\n"
            "c = subprocess.run([exe, '-h'])\n"
            "# subprocess.run([exe, '-enc', ...]) in a comment\n")], [2, 3])
        self.assertEqual([line for line, _ in hand_html_parsers(
            "import html.parser\n"
            "class A(html.parser.HTMLParser):\n    pass\n"
            "from html.parser import HTMLParser\n"
            "class B(HTMLParser):\n    pass\n"
            "class C(object):\n    pass\n"
            "import html.parser as hp\n"
            "class D(hp.HTMLParser):\n    pass\n")], [2, 4, 5, 10])

    def test_no_tool_reads_a_pdf_or_html_by_hand(self):
        fails = []
        for rel, source in tool_sources():
            allowed = list(PDFTOTEXT_BY_HAND.get(rel, []))
            found = hand_pdftotext(source)
            if rel == "tools/resume.py":   # the helper's own call: one, in pdf_text
                helper = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "pdf_text")
                inside = [f for f in found if helper.lineno <= f[0] <= helper.end_lineno]
                if len(inside) != 1:
                    fails.append("tools/resume.py: pdf_text runs pdftotext once, found %d" % len(inside))
                found = [f for f in found if f not in inside]
            for line, text in found:
                if text in allowed:
                    allowed.remove(text)
                else:
                    fails.append("%s:%d: pdftotext by hand: %s" % (rel, line, text))
            fails += ["%s: PDFTOTEXT_BY_HAND lists %s, and it has no such call" % (rel, text) for text in allowed]
            parsers = hand_html_parsers(source)
            if rel == "tools/logfiles.py":
                if [t for _, t in parsers] != ["class HtmlText(html.parser.HTMLParser)"]:
                    fails.append("tools/logfiles.py: one HTMLParser subclass, HtmlText, expected: %s" % parsers)
                continue
            fails += ["%s:%d: HTML read by hand: %s" % (rel, line, text) for line, text in parsers]
        fails += ["%s: PDFTOTEXT_BY_HAND lists a file that is not there" % rel
                  for rel in PDFTOTEXT_BY_HAND if not os.path.isfile(os.path.join(REPO, *rel.split("/")))]
        self.assertEqual(fails, [], "\n" + "\n".join(fails) + "\nRead a PDF's text with resume.pdf_text(path) "
                         "and an HTML page's with logfiles.html_text(markup): one reader each, so every tool "
                         "reads the same text. Only a pdftotext call for something else (a layout, a file "
                         "written) is listed in PDFTOTEXT_BY_HAND, with the reason.")


# The copied forms of logfiles' Markdown table helpers (#783), each with the helper to call instead.
TABLE_COPIES = (
    (re.compile(r"\(\?<!\\+\)\\+\|"), "a cell-splitting regex: call logfiles.md_cells (or md_cell_spans, md_tables)"),
    (re.compile(r"""replace\(\s*["']\|["']\s*,"""), "`|` escaped by hand: call logfiles.md_cell (or md_row)"),
    (re.compile(r""":\?-[+{*]|-\{3|set\(\s*["']-: ?["']\s*\)"""), "a divider check by hand: call logfiles.is_rule (or md_tables)"),
)
# A copy that rightly stays by hand, by its source line (stripped), with the reason: none yet.
TABLE_BY_HAND = {}


def table_copies(text):
    """[(line number, what, line)] for each line of the source that holds a copied table form."""
    return [(n, what, line.strip()) for n, line in enumerate(text.splitlines(), 1)
            for pattern, what in TABLE_COPIES if pattern.search(line)]


class TableHelpers(unittest.TestCase):
    """logfiles' Markdown table helpers are the one place a tool splits a row, escapes a cell or tells
    the divider row, and the guard that keeps them the one (#783: application.py's copy read a
    `|-|-|` divider as a row)."""

    def test_only_the_row_under_the_header_is_the_divider(self):
        table = logfiles.md_tables("| a | b |\n|-|-|\n| - | - |\n| | |\n| x | y |\n")[0]
        self.assertEqual(table.rows, [(3, ["-", "-"]), (5, ["x", "y"])])   # an empty row is left out (#289)
        for rule in ("|---|---|", "|-|-|", "|:--|--:|", "|---|---"):
            self.assertEqual(logfiles.md_tables("| a | b |\n%s\n| x | y |\n" % rule)[0].rows, [(3, ["x", "y"])], rule)

    def test_md_cell(self):
        self.assertEqual(logfiles.md_cell("a|b\r\nc"), "a\\|b c")
        self.assertEqual(logfiles.md_row(["a|b", 1]), "| a\\|b | 1 |")

    def test_the_guard_reads_each_copied_form(self):
        found = table_copies(
            'CELL_SPLIT = re.compile(r"(?<!\\\\)\\|")\n'                 # 1: #687's split
            'parts = re.split("(?<!\\\\\\\\)\\\\|", line)\n'           # 2: the same, not raw
            'row = " | ".join(c.replace("|", "\\\\|") for c in cells)\n'   # 3: #705's writer
            "x = s.replace('|', '\\\\|')\n"                             # 4
            'RULE = re.compile(r"\\|(\\s*:?-{3,}:?\\s*\\|)+$")\n'       # 5: #687's divider
            'if all(re.fullmatch(r":?-+:?", c) for c in r): pass\n'    # 6: dashboard.py's
            "if set(''.join(cells)) <= set('-: '): pass\n"            # 7: entries.py's
            'out += ["|" + "---|" * 4]\n'                              # writing a divider is no copy
            'cells = logfiles.md_cells(line)\n')
        self.assertEqual(sorted({n for n, _, _ in found}), [1, 2, 3, 4, 5, 6, 7])

    def test_no_tool_reads_or_writes_a_table_by_hand(self):
        paths = sorted(rel for folder in ("tools", "maintainer", "skills/career-log")
                       for rel in (folder + "/" + name for name in os.listdir(os.path.join(REPO, *folder.split("/"))))
                       if rel.endswith(".py"))
        fails, listed = [], {rel: list(lines) for rel, lines in TABLE_BY_HAND.items()}
        for rel in paths:
            found = table_copies(logfiles.read_text(os.path.join(REPO, *rel.split("/"))))
            if rel == "tools/logfiles.py":   # the helpers themselves: CELL, md_cell, is_rule
                self.assertEqual(len(found), 3, found)
                continue
            for n, what, line in found:
                if line in listed.get(rel, []):
                    listed[rel].remove(line)
                else:
                    fails.append("%s:%d: %s: %s" % (rel, n, what, line))
        fails += ["%s: TABLE_BY_HAND lists %s, and it has no such line" % (rel, line)
                  for rel, lines in listed.items() for line in lines]
        self.assertEqual(fails, [], "\n" + "\n".join(fails) + "\nRead and write Markdown tables with "
                         "tools/logfiles.py's helpers (md_tables, md_cells, md_cell_spans, is_rule, md_cell, "
                         "md_row). Only a line that rightly stays by hand is listed in TABLE_BY_HAND, with the reason.")


def slug_copies(source):
    """[line] of each line of a Python source that writes out logfiles.SLUG's pattern."""
    return [n for n, line in enumerate(source.splitlines(), 1) if logfiles.SLUG in line]


class Slug(unittest.TestCase):
    """logfiles.SLUG, the one slug pattern, and the guard that keeps it the one (#784)."""
    def test_is_slug(self):
        for text in ("api-retry-design", "a", "2026", "v2-final"):
            self.assertTrue(logfiles.is_slug(text), text)
        for text in ("", None, "-a", "a-", "a--b", "A-b", "a_b", "a b", "café", "a\n"):
            self.assertFalse(logfiles.is_slug(text), text)

    def test_the_guard_reads_a_copy(self):
        self.assertEqual(slug_copies(
            "import re\n"
            'SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"\n'                 # the copied pattern
            "STAGE = re.compile(logfiles.SLUG + '$')\n"
            "ok = re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', s)\n"), [2, 4])   # and inline

    def test_no_tool_copies_the_slug_pattern(self):
        fails = ["%s:%d: the slug pattern written out" % (rel, line) for rel, source in tool_sources()
                 if rel != "tools/logfiles.py" for line in slug_copies(source)]
        self.assertEqual(fails, [], "\n" + "\n".join(fails) + "\nUse logfiles.SLUG (re.compile(logfiles.SLUG), "
                         "SLUG + '$') or logfiles.is_slug(text).")


def keyed_mkdirs(source):
    """[line] of each try, inside a loop, whose body calls os.mkdir or os.makedirs (which raises it too)
    and that catches FileExistsError: the loop that makes a keyed folder, in a Python source."""
    def catches(handler):
        names = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        return any(isinstance(n, ast.Name) and n.id == "FileExistsError" for n in names)
    found = set()
    for loop in ast.walk(ast.parse(source)):
        if not isinstance(loop, (ast.While, ast.For)):
            continue
        for node in ast.walk(loop):
            if (isinstance(node, ast.Try) and any(catches(h) for h in node.handlers if h.type)
                    and any(isinstance(c, ast.Call) and ast.unparse(c.func) in ("os.mkdir", "os.makedirs")
                            for b in node.body for c in ast.walk(b))):
                found.add(node.lineno)
    return sorted(found)


class KeyedFolder(unittest.TestCase):
    """make_keyed_folder, the one loop that makes a run's or a session's folder, and the guard that
    keeps it the one (#793)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_the_next_key_when_one_is_taken(self):
        parent = os.path.join(self.tmp, "a", "runs")   # made when missing
        key_of = lambda n: "2026-11-14-120000" + ("-%d" % n if n > 1 else "")
        self.assertEqual(logfiles.make_keyed_folder(parent, key_of), "2026-11-14-120000")
        self.assertEqual(logfiles.make_keyed_folder(parent, key_of), "2026-11-14-120000-2")
        self.assertEqual(sorted(os.listdir(parent)), ["2026-11-14-120000", "2026-11-14-120000-2"])

    def test_the_guard_reads_the_copied_loop(self):
        self.assertEqual(keyed_mkdirs(
            "n = 1\n"
            "while True:\n"
            "    key = run_key(date, now, n)\n"
            "    try:\n"                                    # line 4: the copied loop
            "        os.mkdir(os.path.join(parent, key))\n"
            "        break\n"
            "    except FileExistsError:\n"
            "        n += 1\n"
            "for n in itertools.count(1):\n"
            "    try:\n"                                    # line 10: with os.makedirs
            "        os.makedirs(os.path.join(parent, key_of(n)))\n"
            "        break\n"
            "    except (FileExistsError, PermissionError):\n"
            "        continue\n"
            "for p in paths:\n"
            "    try:\n"                                    # a loop with no mkdir
            "        os.remove(p)\n"
            "    except FileExistsError:\n"
            "        pass\n"
            "try:\n"                                        # a mkdir in no loop
            "    os.mkdir(d)\n"
            "except (OSError, FileExistsError):\n"
            "    pass\n"), [4, 10])

    def test_no_tool_makes_a_keyed_folder_by_hand(self):
        fails = []
        for rel, source in tool_sources():
            found = keyed_mkdirs(source)
            if rel == "tools/logfiles.py":
                self.assertEqual(len(found), 1, "tools/logfiles.py makes a keyed folder once, in make_keyed_folder")
                continue
            fails += ["%s:%d: a keyed folder made by hand" % (rel, line) for line in found]
        self.assertEqual(fails, [], "\n" + "\n".join(fails) + "\nCall logfiles.make_keyed_folder(parent, key_of): "
                         "it makes the folder of the first key not taken yet.")


if __name__ == "__main__":
    unittest.main()
