#!/usr/bin/env python3
"""Tests for tools/logfiles.py, the helpers the Log's tools share, on made-up text and small Logs
built in a temporary directory.

  python3 -I tools/tests/test_logfiles.py
"""
import ast, datetime, importlib.util, os, shutil, subprocess, sys, tempfile, time, unittest

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
    """A posting run's folder, key and live marker, as scan.py writes them and check.py reads them (#662)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def marker(self, root, key, ago=0):
        path = os.path.join(root, *logfiles.run_folder(key).split("/"), logfiles.LIVE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logfiles.write_live(path, datetime.datetime.now().astimezone().isoformat(timespec="seconds"), None)
        os.utime(path, (time.time() - ago,) * 2)
        return path

    def test_run_key_and_folder(self):
        self.assertEqual(logfiles.run_key("2026-10-22", "041500"), "2026-10-22-041500")
        self.assertEqual(logfiles.run_key("2026-10-22", "041500", 3), "2026-10-22-041500-3")
        m = logfiles.RUN_KEY.match("2026-10-22-041500-3")
        self.assertEqual(m.group("date", "hh", "mm", "ss", "n"), ("2026-10-22", "04", "15", "00", "3"))
        for bad in ("2026-10-22", "2026-10-22-0415", "notes", "2026-10-22-041500-"):
            self.assertIsNone(logfiles.RUN_KEY.match(bad), bad)
        self.assertEqual(logfiles.run_folder("2026-10-22-041500"), ".build/runs/2026-10-22-041500")

    def test_live_runs_in_a_root_with_glob_characters(self):
        root = os.path.join(self.tmp, "log [1]")
        self.marker(root, "2026-10-22-041500")
        self.assertEqual([k for _, k in logfiles.live_runs(root)], ["2026-10-22-041500"])

    def test_a_folder_named_as_no_run_key_holds_no_live_run(self):
        root = os.path.join(self.tmp, "log")
        self.marker(root, "notes")
        self.marker(root, "2026-10-22-041500")
        self.assertEqual([k for _, k in logfiles.live_runs(root)], ["2026-10-22-041500"])

    def test_an_expired_or_unreadable_marker_is_no_live_run(self):
        root = os.path.join(self.tmp, "log")
        old = self.marker(root, "2026-10-22-041500", ago=logfiles.LIVE_HOURS * 3600 + 60)
        self.assertIsNone(logfiles.read_live(old))
        bad = self.marker(root, "2026-10-22-051500")
        logfiles.write_text(bad, "not json\n")
        self.assertIsNone(logfiles.read_live(bad))
        self.assertEqual(logfiles.live_runs(root), [])


if __name__ == "__main__":
    unittest.main()
