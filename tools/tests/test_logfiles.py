#!/usr/bin/env python3
"""Tests for tools/logfiles.py, the helpers the Log's tools share, on made-up text and small Logs
built in a temporary directory.

  python3 -I tools/tests/test_logfiles.py
"""
import ast, importlib.util, os, shutil, subprocess, sys, tempfile, unittest

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


if __name__ == "__main__":
    unittest.main()
