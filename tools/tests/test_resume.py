#!/usr/bin/env python3
"""Tests for tools/resume.py.

  python3 -I tools/tests/test_resume.py              (Windows: py -3 -I tools/tests/test_resume.py)

The checks that read pdftotext's lines, the source scan, the page limit and the options run on
made-up input and need no TeX. The build cases (SETUP.md step 7's, and one per check that needs a
real PDF) build copies of the example resume in a temporary Log and are skipped, as `OK (skipped=…)`,
when tools/resume.py finds no TinyTeX or no poppler. With RESUME_TEST_INSTALL=1 the missing-package
case also installs lipsum with tlmgr into the TeX tools/resume.py uses, and removes it afterwards.
"""
import contextlib, importlib.util, io, os, re, shutil, subprocess, sys, tempfile, types, unittest, unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
TOOL = os.path.join(TOOLS, "resume.py")
EXAMPLE = os.path.join(REPO, "skills", "career-log", "examples", "resume.tex")
BLANK = os.path.join(REPO, "skills", "career-log", "assets", "resume-blank.tex")
spec = importlib.util.spec_from_file_location("resume", TOOL)
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)

HAVE_TEX = bool(resume.tex_bin("pdflatex") and resume.poppler_bin("pdftotext") and resume.poppler_bin("pdftoppm"))
NO_TEX = "no TinyTeX or poppler found: run this on a machine with both (SETUP.md step 5)"


def row(x0, x1, y, text):
    return {"xMin": x0, "xMax": x1, "yMin": y, "yMax": y + 10, "text": text}


def page(*rows):
    return {"w": 612, "h": 792, "lines": list(rows)}


def wrapped(ratio, y=100):
    """A two-line bullet whose last line fills `ratio` of the 500pt from its start to the right edge."""
    return [row(36, 548, y, "• Built a thing that does a lot"), row(48, 48 + 500 * ratio, y + 12, "and the rest")]


def text_of(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_tool(*args, env=None):
    run = subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", env=env)
    return run.returncode, run.stdout + run.stderr


class LayoutTest(unittest.TestCase):
    def fails(self, *rows, limit=(1, "default"), skills=None, pages=None):
        fails, _ = resume.layout(pages or [page(*rows, row(36, 200, 700, "a@b.co"))], limit, skills)
        return fails

    def test_dangling_threshold_is_60_percent(self):
        self.assertEqual(resume.DANGLING_RATIO, 0.60)
        fails = self.fails(*wrapped(0.59))
        self.assertEqual(len(fails), 1)
        self.assertRegex(fails[0], r"^p1 dangling last line \(59% of width, under 60%\): • Built")
        self.assertEqual(self.fails(*wrapped(0.60)), [])

    def test_a_fail_never_prints_the_threshold_itself(self):
        self.assertRegex(self.fails(*wrapped(0.5999))[0], r"\(59% of width")

    def test_a_one_line_bullet_is_never_dangling(self):
        self.assertEqual(self.fails(row(36, 548, 100, "• Short"), row(36, 548, 112, "Heading")), [])

    def test_three_lines(self):
        rows = wrapped(0.9) + [row(48, 500, 124, "third line")]
        self.assertEqual(self.fails(*rows), ["p1 bullet has 3 lines: • Built a thing that does a lot"])

    def test_page_limit_names_where_it_came_from(self):
        two = [page(row(36, 200, 100, "a@b.co")), page(row(36, 200, 100, "more"))]
        self.assertEqual(self.fails(pages=two), ["pages: 2 (limit 1, default)"])
        self.assertEqual(self.fails(pages=two, limit=(2, "config.toml")), [])
        self.assertEqual(self.fails(pages=two * 2, limit=(3, "--pages")), ["pages: 4 (limit 3, --pages)"])
        self.assertEqual(self.fails(pages=two[:1], limit=(2, "config.toml")), [])   # fewer is fine

    def test_skills_line_that_wraps(self):
        skills = ("Skills", ["Languages:", "Backend & Data:"], ["Skills", "Experience"])
        rows = [row(36, 80, 50, "Skills"), row(36, 548, 62, "Languages: Go, Python, SQL, Rust, Java"),
                row(36, 100, 74, "Kotlin, Scala"), row(36, 300, 86, "Backend & Data: PostgreSQL"),
                row(36, 120, 100, "Experience"), row(36, 548, 112, "Kotlin, a line outside Skills")]
        self.assertEqual(self.fails(*rows, skills=skills), ["Skills line wraps: Languages: … Kotlin, Scala"])
        self.assertEqual(self.fails(*rows[:2], *rows[3:], skills=skills), [])

    def test_skills_without_labels_or_with_marked_up_headings(self):
        rows = [row(36, 80, 50, "Skills"), row(36, 548, 62, "Go, Python, SQL"), row(36, 120, 74, "Experience"),
                row(36, 548, 86, "• Built a thing"), row(36, 300, 98, "Projects")]
        fails, notes = resume.layout([page(*rows, row(36, 200, 700, "a@b.co"))], skills=("Skills", [], ["Skills"]))
        self.assertEqual(fails, [])
        self.assertTrue(any("lines were not checked" in n for n in notes), notes)
        text = ("\\begin{document}\n\\section*{\\textsc{Skills}}\n\\item \\textbf{Languages:} Go\n"
                "\\section*{\\textsc{Experience}}\n")
        self.assertEqual(resume.skills_of(text), ("Skills", ["Languages:"], ["Skills", "Experience"]))
        rows[1]["text"] = "Languages: Go"
        del rows[2]   # no heading it knows after Skills: it stops at the first bullet
        self.assertEqual(self.fails(*rows, skills=("Skills", ["Languages:"], ["Skills"])), [])

    def test_skills_in_an_itemize_and_headings_in_capitals(self):
        skills = ("Skills", ["Languages:", "Data:"], ["Skills", "Experience"])
        rows = [row(36, 80, 50, "SKILLS"), row(36, 548, 62, "• Languages: Go, Python, SQL, Rust"),
                row(48, 100, 74, "Kotlin"), row(36, 300, 86, "• Data: PostgreSQL"), row(36, 120, 100, "EXPERIENCE"),
                row(36, 548, 112, "Engineer, Example Co")]
        fails = self.fails(*rows, skills=skills)
        self.assertIn("Skills line wraps: Languages: … Kotlin", fails)
        self.assertEqual([f for f in fails if "Skills" in f], ["Skills line wraps: Languages: … Kotlin"])

    def test_skills_line_with_a_mark_before_its_label(self):
        """#386: a mark before the bold label (\\checkmark\\ ) still gives the line its label."""
        text = ("\\begin{document}\n\\section*{Skills}\n\\checkmark\\ \\textbf{Languages:} Go, Python, SQL\n"
                "\\item $\\bullet$~\\textbf{Data:} PostgreSQL\nGo, \\textbf{Python} and more\n"
                "\\section*{Experience}\n")
        skills = resume.skills_of(text)
        self.assertEqual(skills, ("Skills", ["Languages:", "Data:"], ["Skills", "Experience"]))
        rows = [row(36, 80, 50, "Skills"), row(36, 300, 62, "✓ Languages: Go, Python, SQL"),
                row(36, 300, 74, "• Data: PostgreSQL"), row(36, 120, 86, "Experience")]
        self.assertEqual(self.fails(*rows, skills=skills), [])   # one row each: no wrap
        rows[1:2] = [row(36, 548, 62, "✓ Languages: Go, Python, SQL, Rust, Java"), row(36, 100, 68, "Kotlin, Scala")]
        self.assertEqual(self.fails(*rows, skills=skills), ["Skills line wraps: Languages: … Kotlin, Scala"])
        rows[2] = row(36, 100, 68, "Kotlin, Languages: Scala")   # a label after a word is not a line's start
        self.assertEqual(self.fails(*rows, skills=skills), ["Skills line wraps: Languages: … Kotlin, Languages: Scala"])

    def test_skills_lines_sharing_one_source_line(self):
        """#423: every label on a source line is read, each at its start or right after a \\\\."""
        text = ("\\begin{document}\n\\section*{Skills}\n"
                "\\textbf{Languages}{: Go, Python} \\\\ \\textbf{Frameworks}{: Flask}\n"
                "\\textbf{Data:} PostgreSQL \\\\ [2pt] \\checkmark\\ \\textbf{Cloud:} AWS \\\\*\\textbf{Tools:} Git\n"
                "\\textbf{Testing:} pytest \\\\ Go, \\textbf{Python} and more\n"
                "\\section*{Experience}\n\\textbf{Engineer} \\\\ \\textbf{Example Co}\n")
        skills = resume.skills_of(text)
        self.assertEqual(skills, ("Skills", ["Languages", "Frameworks", "Data:", "Cloud:", "Tools:", "Testing:"],
                                  ["Skills", "Experience"]))
        rows = [row(36, 80, 50, "Skills"), row(36, 200, 62, "Languages: Go, Python"), row(36, 150, 74, "Frameworks: Flask"),
                row(36, 200, 86, "Data: PostgreSQL"), row(36, 150, 98, "✓ Cloud: AWS"), row(36, 150, 110, "Tools: Git"),
                row(36, 120, 122, "Experience")]
        self.assertEqual(self.fails(*rows, skills=skills), [])   # one row each: no wrap
        rows[1:2] = [row(36, 548, 62, "Languages: Go, Python, Rust, Java"), row(36, 100, 68, "Kotlin, Scala")]
        self.assertEqual(self.fails(*rows, skills=skills), ["Skills line wraps: Languages … Kotlin, Scala"])

    def test_skills_row_above_every_label_names_the_missing_label(self):
        skills = ("Skills", ["Data:"], ["Skills", "Experience"])
        rows = [row(36, 80, 50, "Skills"), row(36, 300, 62, "Go, Python, SQL"), row(36, 300, 74, "Data: PostgreSQL"),
                row(36, 120, 86, "Experience")]
        self.assertEqual(self.fails(*rows, skills=skills),
                         ["Skills line with no \\textbf{<label>} the check can read: Go, Python, SQL"])

    def test_skills_line_with_no_label_below_a_labelled_one(self):
        """#441: a row the row above could not have run on to is a line of its own, not a wrap."""
        skills = ("Skills", ["Languages:", "Data:"], ["Skills", "Experience"])
        rows = [row(36, 80, 50, "Skills"), row(36, 300, 62, "Languages: Go, Python, SQL"),
                row(36, 200, 74, "Kafka, Redis, Spark"), row(36, 300, 86, "Data: PostgreSQL"),
                row(36, 548, 98, "Experience")]
        self.assertEqual(self.fails(*rows, skills=skills),
                         ["Skills line with no \\textbf{<label>} the check can read: Kafka, Redis, Spark"])
        # that line wraps too: its second row is part of the same fail, not a wrap of Languages:
        rows[2:3] = [row(36, 548, 74, "Kafka, Redis, Spark, Flink, Airflow, Beam"), row(36, 100, 86, "dbt")]
        self.assertEqual(self.fails(*rows, skills=skills),
                         ["Skills line with no \\textbf{<label>} the check can read: Kafka, Redis, Spark, Flink, Airflow, Bea"])

    def test_skills_reach_margin(self):
        """A gap that holds the first word ("Kafka," 6 of 12 letters: 30pt) plus the 36pt margin is a wrap."""
        self.assertEqual(resume.SKILLS_REACH_MARGIN, 36)
        skills = ("Skills", ["Languages:"], ["Skills"])
        for gap, said in ((66, "Skills line wraps: Languages: … Kafka, Redis"),
                          (67, "Skills line with no \\textbf{<label>} the check can read: Kafka, Redis")):
            rows = [row(36, 80, 50, "Skills"), row(36, 548 - gap, 62, "Languages: Go"), row(36, 96, 74, "Kafka, Redis")]
            self.assertEqual(self.fails(*rows, row(36, 548, 86, "• Built a thing"), skills=skills), [said], gap)

    def test_skills_rows_across_a_page_break_wrap(self):
        skills = ("Skills", ["Languages:"], ["Skills"])
        pages = [page(row(36, 200, 100, "a@b.co"), row(36, 80, 700, "Skills"), row(36, 300, 712, "Languages: Go")),
                 page(row(36, 100, 50, "Kotlin, Scala"), row(36, 548, 62, "• Built a thing"))]
        self.assertEqual(self.fails(pages=pages, limit=(2, "default"), skills=skills),
                         ["Skills line wraps: Languages: … Kotlin, Scala"])

    def test_skills_lines_split_by_newline(self):
        """#441: \\newline breaks a source line as \\\\ does."""
        text = ("\\begin{document}\n\\section*{Skills}\n"
                "\\textbf{Languages:} Go \\newline \\textbf{Data:} SQL\\newline\\textbf{Cloud:} AWS\n"
                "\\textbf{Tools:} Git \\newlines \\textbf{Ops:} k8s\n\\section*{Experience}\n")
        self.assertEqual(resume.skills_of(text), ("Skills", ["Languages:", "Data:", "Cloud:", "Tools:"],
                                                  ["Skills", "Experience"]))

    def test_skills_heading_missing_is_a_note(self):
        fails, notes = resume.layout([page(row(36, 200, 100, "a@b.co"))], skills=("Skills", ["Languages:"], ["Skills"]))
        self.assertEqual(fails, [])
        self.assertIn("no Skills heading in the text layer, so its lines were not checked", notes)

    def test_text_layer(self):
        fails, notes = resume.layout([page(row(36, 200, 100, "Jan 2025 – May 2025 (cid:12)"))])
        self.assertEqual(fails, ["no email address in the text layer", "garbage glyphs in the text layer"])
        self.assertIn("dates use en dashes (–); some ATS imports (Workday) drop them", notes)

    def test_email_gap_is_its_own_line(self):
        fails, _ = resume.layout([page(row(36, 200, 100, "Springfield | GAP: email | github.com/x"))])
        self.assertEqual(fails, ["email: GAP (needs you): Springfield | GAP: email | github.com/x"])
        fails, _ = resume.layout([page(row(36, 200, 100, "E-mail: GAP | github.com/x"))])
        self.assertEqual(fails, ["email: GAP (needs you): E-mail: GAP | github.com/x"])
        for line in ("Springfield | GAP: phone", "Cut GAP: emails sent per day by 30%"):   # not the email field
            fails, _ = resume.layout([page(row(36, 200, 100, line))])
            self.assertEqual(fails, ["no email address in the text layer"])
        fails, _ = resume.layout([page(row(36, 200, 100, "a@b.co"), row(36, 200, 120, "GAP: email"))])
        self.assertEqual(fails, [])   # an address found: no email failure at all


class SourceTest(unittest.TestCase):
    def scan(self, *lines):
        return resume.scan_source("\\documentclass{article}\n$\\vcenter{}$ & # _\n\\begin{document}\n"
                                  + "\n".join(lines) + "\n\\end{document}\n")

    def test_preamble_is_not_scanned(self):
        self.assertEqual(self.scan("Plain text"), [])

    def test_placeholders_on_any_line(self):
        self.assertEqual(self.scan("\\centerline{\\Huge <Full Name>}", "% <a comment>"),
                         ["source line 4: placeholder <Full Name> left; replace it with a fact from an entry"])
        found = resume.scan_source(text_of(BLANK))
        self.assertTrue(any("<Full Name>" in f for f in found))
        self.assertTrue(any("<Category>" in f for f in found))   # the Skills lines, not just \item
        self.assertTrue(any("<Past-tense verb>" in f for f in found))

    def test_unescaped_characters(self):
        self.assertEqual(self.scan("R&D in C# with snake_case and $5M"), [
            "source line 4: unescaped $ before a number; write \\$",
            "source line 4: unescaped #; write \\#", "source line 4: unescaped _; write \\_",
            "source line 4: unescaped &; write \\&"])
        self.assertEqual(self.scan("R\\&D in C\\# with snake\\_case, \\$5M and 3\\%"), [])

    def test_percent_after_a_number_starts_a_comment(self):
        said = "starts a comment, so the % and the rest of the line are dropped; write \\% for a percentage"
        self.assertEqual(self.scan("cut cost 30% by caching"), ["source line 4: cost 30% " + said])
        end = self.scan("  \\item cutting job loss by 35%")   # at the line's end, where a result's number sits
        self.assertEqual(len(end), 1)
        self.assertRegex(end[0], r"^source line 4: .*35% starts a comment")
        self.assertEqual(self.scan("\\vspace{-9pt} % a comment with 50% in it"), [])

    def test_review_false_positives(self):
        self.assertEqual(self.scan("Served $\\sim$40k users and $10^6$ jobs", "\\href{https://x.io/a_b%20c}{x.io}",
                                   "\\\\% a comment after a line break: R&D 50%z",
                                   "A std::vector<int> pool, Map<K, V> and parse::<String>()",
                                   "achieving $>$95\\% accuracy, latency $<$10ms, from $3$ to $5$ nodes"), [])
        self.assertEqual(self.scan("cost $5M"), ["source line 4: unescaped $ before a number; write \\$"])
        self.assertEqual(self.scan("Cut costs from $2M to $1M"), ["source line 4: unescaped $ before a number; write \\$"])
        self.assertEqual(self.scan("\\href{mailto:<email>}{<email>}"),
                         ["source line 4: placeholder <email> left; replace it with a fact from an entry"] * 2)

    def test_addresses_math_tables_and_comments_are_left_alone(self):
        self.assertEqual(self.scan("\\href{https://x.io/a_b#c}{x.io} \\url{https://x.io/d_e}",
                                   "$\\sim$", "% R&D in C#", "\\begin{tabular}{ll} a & b \\end{tabular}"), [])

    def test_unicode_dashes(self):
        self.assertEqual(self.scan("Jan 2025 – May 2025 — now", "% Jan – May"), [
            "source line 4: Unicode –; write --, as every version does",
            "source line 4: Unicode —; write ---, as every version does"])

    def test_the_example_is_clean(self):
        self.assertEqual(resume.scan_source(text_of(EXAMPLE)), [])

    def test_skills_of_the_example(self):
        self.assertEqual(resume.skills_of(text_of(EXAMPLE)),
                         ("Skills", ["Languages:", "Backend & Data:"], ["Skills", "Experience", "Projects", "Education"]))
        self.assertIsNone(resume.skills_of("\\begin{document}\n\\section*{Experience}\n"))


class SameLayoutTest(unittest.TestCase):
    def setUp(self):
        self.start = text_of(EXAMPLE)

    def test_itemsep_change_fails(self):
        changed = self.start.replace("itemsep=-2pt", "itemsep=-4pt")
        self.assertEqual(resume.same_layout(changed, self.start, "start.tex"), [
            "layout: line 31 is not in start.tex: \\setlist[itemize]{itemsep=-2pt, leftmargin=12pt}".replace("-2pt", "-4pt"),
            "layout: line 31 of start.tex is gone: \\setlist[itemize]{itemsep=-2pt, leftmargin=12pt}"])

    def add(self, line, start=None):
        start = start or self.start
        return resume.same_layout(start.replace("\\usepackage{titlesec}", "\\usepackage{titlesec}\n" + line),
                                  start, "start.tex")

    def test_a_package_that_only_brings_commands_passes(self):
        # TinyTeX's base set has these, so --install-missing never names them (#379 case 3)
        for line in ("\\usepackage{amssymb}", "\\usepackage{xcolor}", "\\usepackage{tabularx}",
                     "\\usepackage{multicol}", "\\usepackage[table]{xcolor}", "\\usepackage{amssymb, multicol}",
                     "\\usepackage{lipsum}", "\\usepackage{xkeyval}"):
            self.assertEqual(self.add(line), [], line)

    def test_a_layout_package_fails_even_once_recorded(self):
        # --install-missing names parskip and the agent lists it: still a layout change (#379 case 1)
        with unittest.mock.patch.object(resume, "listed_packages", return_value={"parskip", "xcharter"}):
            for line in ("\\usepackage{parskip}", "\\usepackage{setspace}", "\\usepackage[margin=1in]{geometry}",
                         "\\usepackage{microtype}", "\\usepackage{amssymb,parskip}", "\\usepackage{lmodern}",
                         "\\usepackage{tgheros}", "\\usepackage{txfonts}", "\\usepackage{newtx}",
                         "\\usepackage{xeCJK}", "\\usepackage{./mystyle}",
                         "\\usepackage{xkeyval}\\setlength{\\parskip}{0pt}",
                         "\\RequirePackage{amssymb}"):
                self.assertEqual(len(self.add(line)), 1, line)

    def test_a_font_package_fails_in_any_case(self):
        # Windows finds XCharter.sty for \usepackage{xcharter}, which swaps the font (#379 case 2)
        start = self.start.replace("\\usepackage{XCharter}", "")
        for line in ("\\usepackage{xcharter}", "\\usepackage{XCharter}", "\\usepackage{LModern}"):
            self.assertEqual(len(self.add(line, start)), 1, line)

    def test_a_swapped_font_fails_twice(self):
        swapped = self.start.replace("\\usepackage{XCharter}", "\\usepackage{lmodern}")
        self.assertEqual(len(resume.same_layout(swapped, self.start, "start.tex")), 2)   # lmodern in, XCharter gone

    def test_body_layout_command_fails(self):
        changed = self.start.replace("% name\n", "% name\n\\setlength{\\parskip}{2pt}\n")
        self.assertEqual(len(resume.same_layout(changed, self.start, "start.tex")), 1)

    def test_vspace_words_and_comments_pass(self):
        changed = (self.start.replace("\\vspace{-18.5pt}", "\\vspace{-17pt}")
                   .replace("Cut shipment-quote", "Reduced shipment-quote")
                   .replace("% set font", "% the font"))
        self.assertEqual(resume.same_layout(changed, self.start, "start.tex"), [])


class PageLimitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def config(self, text):
        with open(os.path.join(self.root, "config.toml"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_default_without_config(self):
        self.assertEqual(resume.page_limit(self.root), (1, "default"))

    def test_config_and_pages(self):
        self.config("resume_max_pages = 2\n")
        self.assertEqual(resume.page_limit(self.root), (2, "config.toml"))
        self.assertEqual(resume.page_limit(self.root, 1), (1, "--pages"))
        self.config('window = 7\n')
        self.assertEqual(resume.page_limit(self.root), (1, "default"))

    def test_another_fields_bad_value_keeps_this_one(self):
        self.config('resume_max_pages = 2\nwindow = 999\n')
        self.assertEqual(resume.page_limit(self.root), (2, "config.toml"))

    def test_stale_with_no_tex_is_a_note(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertTrue(resume.stale(self.root, self.root))
        self.assertIn("note: no .tex in", out.getvalue())

    def stale_failing(self, missing):
        """--stale on one target whose build fails with `missing` as the file not found."""
        folder = os.path.join(self.root, "outputs", "resumes")
        os.makedirs(folder, exist_ok=True)
        for name in ("backend.tex", "backend.pdf"):
            open(os.path.join(folder, name), "w").close()

        def build(tex, outdir, install_missing):
            raise resume.BuildFailed(tex, missing)
        out = io.StringIO()
        with unittest.mock.patch.object(resume, "build", build), contextlib.redirect_stdout(out):
            self.assertFalse(resume.stale(folder, self.root))
        return folder, out.getvalue()

    def test_stale_tells_a_missing_package_from_a_broken_tex(self):   # #482
        _, out = self.stale_failing("careerlognosuchpkg.sty")
        self.assertRegex(out, r"(?m)^FAIL: backend: this machine lacks careerlognosuchpkg\.sty, so backend\.tex "
                              r"was not compared: python3 -I \".*resume\.py\" \".*backend\.tex\" --install-missing --root \"")
        self.assertNotIn("does not build", out)
        _, out = self.stale_failing(None)
        self.assertIn("FAIL: backend: backend.tex does not build (the lines above say why)", out)

    def test_stale_copies_the_local_files_a_tex_inputs(self):   # #504
        folder = os.path.join(self.root, "outputs", "resumes")
        os.makedirs(os.path.join(folder, "parts"))
        files = {"backend.tex": "\\input{header}\n\\include{parts/body}\n% \\input{commented}\n\\usepackage{x}\\input{x.sty}\n"
                                "\\input{../outside}\n",
                 "backend.pdf": "", "header.tex": "\\input{parts/contact.tex}\n", "parts/body.tex": "",
                 "parts/contact.tex": "", "commented.tex": "", "unused.tex": ""}
        for rel, body in files.items():
            with open(os.path.join(folder, *rel.split("/")), "w", encoding="utf-8") as f:
                f.write(body)
        with open(os.path.join(self.root, "outputs", "outside.tex"), "w") as f:
            f.write("")
        self.assertEqual(sorted(p.replace(os.sep, "/") for p in resume.local_inputs(os.path.join(folder, "backend.tex"))),
                         ["header.tex", "parts/body.tex", "parts/contact.tex"])
        seen = []

        def build(tex, outdir, install_missing):
            here = os.path.dirname(tex)
            seen.extend(sorted(os.path.relpath(os.path.join(d, f), here).replace(os.sep, "/")
                               for d, _, fs in os.walk(here) for f in fs))
            raise resume.BuildFailed(tex, None)
        with unittest.mock.patch.object(resume, "build", build), contextlib.redirect_stdout(io.StringIO()):
            resume.stale(folder, self.root)
        self.assertEqual(seen, ["backend.tex", "header.tex", "parts/body.tex", "parts/contact.tex"])

    def test_local_inputs_cycles_comments_and_parts_with_a_pdf(self):   # #504 review
        folder = os.path.join(self.root, "outputs", "resumes")
        os.makedirs(folder)
        files = {"a.tex": "\\input{b}\n", "b.tex": "\\input{a}\n", "self.tex": "\\input{self}\n",
                 "pct.tex": "50\\% \\input{c}\nline\\\\% \\input{d}\n", "c.tex": "", "d.tex": "",
                 "a.pdf": "", "b.pdf": ""}
        for rel, body in files.items():
            with open(os.path.join(folder, rel), "w", encoding="utf-8") as f:
                f.write(body)
        inputs = lambda name: resume.local_inputs(os.path.join(folder, name))
        self.assertEqual(inputs("a.tex"), ["b.tex"])
        self.assertEqual(inputs("self.tex"), [])
        self.assertEqual(inputs("pct.tex"), ["c.tex"])
        out = io.StringIO()

        def build(tex, outdir, install_missing):
            raise resume.BuildFailed(tex, None)
        with unittest.mock.patch.object(resume, "build", build), contextlib.redirect_stdout(out):
            self.assertFalse(resume.stale(folder, self.root))
        for target in ("a", "b"):   # each has its own .pdf: a resume, though the other \input's it
            self.assertIn("FAIL: %s: %s.tex does not build" % (target, target), out.getvalue())
        self.assertIn("note: c.tex is part of pct.tex", out.getvalue())
        self.assertIn("FAIL: d: no d.pdf beside its .tex", out.getvalue())

    def test_stale_a_local_file_left_behind_is_no_package(self):   # one the .tex names in no \input or \include
        folder = os.path.join(self.root, "outputs", "resumes")
        os.makedirs(folder)
        open(os.path.join(folder, "header.tex"), "w").close()
        _, out = self.stale_failing("header.tex")
        self.assertIn("FAIL: backend: backend.tex does not build", out)
        self.assertNotIn("lacks", out)

    def test_bad_config_warns_and_takes_the_default(self):
        self.config("resume_max_pages = 9\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(resume.page_limit(self.root), (1, "default"))
        self.assertIn("resume_max_pages must be a whole number from 1 to 3", out.getvalue())

    def test_default_build_dir_is_under_root(self):
        d = resume.default_outdir(os.path.join(self.root, "x", "resume.tex"), self.root)
        self.assertEqual(os.path.dirname(d), os.path.join(self.root, ".build", "resume"))


class OptionsTest(unittest.TestCase):
    def test_wrong_combinations_exit_2(self):
        for args in (["--baseline", "x.tex"], ["--stale", HERE, "--pages", "2"], ["x.pdf", "--same-text", "y.pdf", "--no-png"],
                     ["--check", "x.pdf", "--install-missing"], [], ["x.tex", "--pages", "0"], ["--baseline", "--out", "d"],
                     ["x.tex", "--root", os.path.join(HERE, "no-such-folder")], ["--stale", os.path.join(HERE, "no-such")]):
            code, out = run_tool(*args)
            self.assertEqual(code, 2, (args, out))
            self.assertIn("error:", out, args)   # argparse refused it, not a missing file further on

    def test_help_says_email_not_contact_details(self):
        self.assertIn("no email address", resume.__doc__)
        self.assertNotIn("contact details", resume.__doc__)

    def test_a_missing_tool_exits_2_not_1(self):
        saved = resume.tex_bin
        resume.tex_bin = lambda name: None
        try:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
                resume.find_tex_bin("pdflatex")
        finally:
            resume.tex_bin = saved
        self.assertEqual(e.exception.code, 2)


class FakeTlmgrTest(unittest.TestCase):
    """--install-missing with made-up pdflatex and tlmgr: what it prints after an install."""
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.tex = os.path.join(self.root, "d", "resume.tex")
        os.makedirs(os.path.dirname(self.tex))
        open(self.tex, "w").close()
        self.saved = resume.find_tex_bin, resume.subprocess.run
        self.addCleanup(lambda: (setattr(resume, "find_tex_bin", self.saved[0]),
                                 setattr(resume.subprocess, "run", self.saved[1])))
        resume.find_tex_bin = lambda name: name

    def build(self, pkg):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd[:2])
            if cmd[0] == "pdflatex":
                if calls.count(["pdflatex", "-interaction=nonstopmode"]) == 1:
                    return types.SimpleNamespace(returncode=1, stdout="! LaTeX Error: File `%s.sty' not found." % pkg, stderr="")
                out = next(c for c in cmd if c.startswith("-output-directory="))[len("-output-directory="):]
                open(os.path.join(out, "resume.pdf"), "w").close()
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            if cmd[1] == "search":
                return types.SimpleNamespace(returncode=0, stdout="%s:\n\ttexmf-dist/tex/latex/%s/%s.sty\n" % (pkg, pkg, pkg), stderr="")
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        resume.subprocess.run = run
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            resume.build(self.tex, os.path.join(self.root, "build"), True)
        return out.getvalue().splitlines()

    def test_prints_the_package_to_add(self):
        lines = self.build("fakepkg")
        self.assertIn("installing fakepkg for fakepkg.sty", lines)
        self.assertIn("add to tools/tex-packages.txt: fakepkg", lines)

    def test_says_nothing_when_listed(self):   # tools/tex-packages.txt beside the script lists it
        lines = self.build("xcharter")
        self.assertIn("installing xcharter for xcharter.sty", lines)
        self.assertFalse([l for l in lines if l.startswith("add to")])


@unittest.skipUnless(HAVE_TEX, NO_TEX)
class BuildTest(unittest.TestCase):
    """SETUP.md step 7's cases and the checks that need a real PDF, on copies of the example."""
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.example = text_of(EXAMPLE)

    def write(self, rel, text):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def item(self, n, more):
        """The example with `more` added to the end of its n-th \\item."""
        lines, seen = self.example.splitlines(True), 0
        for i, l in enumerate(lines):
            if l.lstrip().startswith("\\item"):
                seen += 1
                if seen == n:
                    lines[i] = l.rstrip("\n") + more + "\n"
        return "".join(lines)

    def build(self, text, *args, name="case/resume.tex"):
        return run_tool(self.write(name, text), "--root", self.root, "--no-png", *args)

    def test_the_example_passes(self):
        code, out = run_tool(self.write("case/resume.tex", self.example), "--root", self.root)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.rstrip().endswith("OK"), out)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "case", "resume-1.png")))
        txt = re.search(r"^note: text layer: (.+?) \(read it", out, re.M).group(1)
        self.assertTrue(txt.startswith(os.path.join(self.root, ".build", "resume")), txt)
        words = text_of(txt)
        self.assertLess(words.index("Skills"), words.index("Experience"))
        self.assertLess(words.index("Experience"), words.index("Projects"))
        self.assertLess(words.index("Projects"), words.index("Education"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "case", "resume.txt")))   # not beside the draft

    def test_too_long(self):   # SETUP.md step 7
        code, out = self.build(self.item(2, " that the finance team had run by hand every Friday afternoon for years "
                                            "before this consumer replaced it"))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL: p1 bullet has 3 lines")

    def test_dangling_line(self):   # SETUP.md step 7
        code, out = self.build(self.item(6, " during chaos testing"))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL: p1 dangling last line \(\d+% of width, under 60%\)")

    def test_skills_line_wraps(self):
        code, out = self.build(self.example.replace(
            "Go, Python, SQL \\\\", "Go, Python, SQL, TypeScript, JavaScript, Kotlin, Scala, Rust, Haskell, Elixir, "
                                   "Erlang, Clojure, OCaml, Fortran, COBOL \\\\"))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL: Skills line wraps: Languages:", out)

    def test_skills_lines_on_one_source_line(self):   # #423
        text = self.example.replace("Go, Python, SQL \\\\\n", "Go, Python, SQL \\\\ ")
        self.assertNotEqual(text, self.example)
        code, out = self.build(text)
        self.assertNotIn("Skills line", out)
        self.assertEqual(code, 0, out)
        code, out = self.build(text.replace("Go, Python, SQL \\\\", "Go, Python, SQL, TypeScript, JavaScript, Kotlin, "
                                            "Scala, Rust, Haskell, Elixir, Erlang, Clojure, OCaml, Fortran, COBOL \\\\"))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL: Skills line wraps: Languages:", out)
        self.assertNotIn("Backend", out)

    def test_skills_line_with_no_label(self):   # #441
        code, out = self.build(self.example.replace("Go, Python, SQL \\\\\n", "Go, Python, SQL \\\\\nDocker, Terraform \\\\\n"))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL: Skills line with no \\textbf{<label>} the check can read: Docker, Terraform", out)
        self.assertNotIn("line wraps", out)
        code, out = self.build(self.example.replace("Go, Python, SQL \\\\\n", "Go, Python, SQL \\newline "))
        self.assertNotIn("Skills line", out)
        self.assertEqual(code, 0, out)

    def test_broken_source(self):   # SETUP.md step 7
        code, out = self.build(self.example.replace("\\end{itemize}", "", 1))
        self.assertEqual(code, 2, out)
        self.assertIn("BUILD FAILED", out)
        self.assertRegex(out, r"(?m)^!")

    def test_scan_lines_come_with_a_failed_build(self):
        code, out = self.build(self.item(1, " for R&D"))
        self.assertEqual(code, 2, out)
        self.assertIn("BUILD FAILED", out)
        self.assertRegex(out, r"FAIL: source line \d+: unescaped &; write \\&")

    def test_missing_package(self):   # SETUP.md step 7, with a package no TeX has
        text = self.example.replace("\\usepackage{titlesec}", "\\usepackage{titlesec}\n\\usepackage{careerlognosuchpkg}")
        code, out = self.build(text)
        self.assertEqual(code, 2, out)
        self.assertIn("BUILD FAILED", out)
        self.assertIn("Missing package file; rerun with --install-missing.", out)
        code, out = self.build(text, "--install-missing")
        self.assertEqual(code, 2, out)
        self.assertIn("tlmgr found no package providing careerlognosuchpkg.sty", out)

    @unittest.skipUnless(os.environ.get("RESUME_TEST_INSTALL") == "1", "set RESUME_TEST_INSTALL=1 to install lipsum")
    def test_missing_package_installs(self):   # SETUP.md step 7 as it was: installs lipsum, then removes it
        tlmgr = resume.find_tex_bin("tlmgr")
        self.addCleanup(subprocess.run, [tlmgr, "remove", "lipsum"], capture_output=True)
        text = self.example.replace("\\usepackage{titlesec}", "\\usepackage{titlesec}\n\\usepackage{lipsum}")
        code, out = self.build(text)
        if code == 0:
            self.skipTest("lipsum is installed already; remove it and run this again")
        self.assertEqual(code, 2, out)
        code, out = self.build(text, "--install-missing")
        self.assertEqual(code, 0, out)
        self.assertIn("installing lipsum", out)
        self.assertIn("add to tools/tex-packages.txt: lipsum", out)

    def test_page_limit_from_config_and_pages(self):
        two = self.example.replace("% education section", "\\newpage\n% education section")
        code, out = self.build(two)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL: pages: 2 (limit 1, default)", out)
        self.write("config.toml", "resume_max_pages = 2\n")
        code, out = self.build(two)
        self.assertEqual(code, 0, out)
        code, out = self.build(two, "--pages", "1")
        self.assertIn("FAIL: pages: 2 (limit 1, --pages)", out)
        pdf = os.path.join(self.root, "case", "resume.pdf")
        other = tempfile.mkdtemp()   # --root names another Log: its config.toml, not this one
        self.addCleanup(shutil.rmtree, other, True)
        code, out = run_tool("--check", pdf, "--root", other, "--no-png")
        self.assertIn("FAIL: pages: 2 (limit 1, default)", out)

    def test_same_layout(self):
        start = self.write("start/resume.tex", self.example)
        code, out = self.build(self.example.replace("itemsep=-2pt", "itemsep=-3pt"), "--same-layout", start)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL: layout: line 31 is not in resume.tex", out)
        code, out = self.build(self.example.replace("\\vspace{5pt}", "\\vspace{4pt}"), "--same-layout", start)
        self.assertEqual(code, 0, out)
        # a package TinyTeX already has reaches exit 0 with tools/tex-packages.txt as it is (#379)
        code, out = self.build(self.example.replace("\\usepackage{titlesec}", "\\usepackage{titlesec}\n\\usepackage{amssymb}"),
                               "--same-layout", start)
        self.assertEqual(code, 0, out)

    def test_stale(self):
        same = self.write("outputs/resumes/backend.tex", self.example)
        self.assertEqual(run_tool(same, "--root", self.root, "--no-png")[0], 0)
        shutil.copy(same[:-4] + ".pdf", os.path.join(self.root, "outputs", "resumes", "platform.pdf"))
        self.write("outputs/resumes/platform.tex", self.example.replace("Cut shipment-quote", "Reduced shipment-quote"))
        for f in os.listdir(os.path.join(self.root, "outputs", "resumes")):
            if f.endswith(".png"):
                os.remove(os.path.join(self.root, "outputs", "resumes", f))
        code, out = run_tool("--stale", os.path.join(self.root, "outputs", "resumes"), "--root", self.root)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^backend: same text \(\d+ words\)$")
        self.assertRegex(out, r"(?m)^FAIL: platform: text differs at word \d+: .*platform.pdf is not the one its .tex builds$")
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".build", "audit", "platform", "platform.pdf")))
        # a package this machine lacks is no broken .tex (#482)
        shutil.copy(same[:-4] + ".pdf", os.path.join(self.root, "outputs", "resumes", "infra.pdf"))
        self.write("outputs/resumes/infra.tex", self.example.replace(
            "\\usepackage{titlesec}", "\\usepackage{titlesec}\n\\usepackage{careerlognosuchpkg}"))
        code, out = run_tool("--stale", os.path.join(self.root, "outputs", "resumes"), "--root", self.root)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL: infra: this machine lacks careerlognosuchpkg\.sty, so infra\.tex was not compared: ")
        self.assertNotIn("infra.tex does not build", out)
        self.assertRegex(out, r"(?m)^backend: same text")
        # a local file the .tex \input's is built with it (#504)
        os.remove(os.path.join(self.root, "outputs", "resumes", "infra.tex"))
        shutil.copy(same[:-4] + ".pdf", os.path.join(self.root, "outputs", "resumes", "split.pdf"))
        self.write("outputs/resumes/split-preamble.tex", "\\usepackage{titlesec}\n")
        self.write("outputs/resumes/split.tex", self.example.replace("\\usepackage{titlesec}", "\\input{split-preamble}"))
        code, out = run_tool("--stale", os.path.join(self.root, "outputs", "resumes"), "--root", self.root)
        self.assertRegex(out, r"(?m)^split: same text \(\d+ words\)$")
        self.assertRegex(out, r"(?m)^note: split-preamble\.tex is part of split\.tex, not a resume of its own$")
        self.assertEqual(code, 1, out)   # platform still differs

    def test_baseline(self):
        self.write("skills/career-log/examples/resume.tex", self.example)
        code, out = run_tool("--baseline", "--root", self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.rstrip().splitlines()[-1], "baseline: OK")
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".build", "verify", "resume-1.png")))
        self.write("skills/career-log/examples/resume.tex", self.example.replace("\\vspace{5pt}", "\\vspace{9pt}"))
        code, out = run_tool("--baseline", "--root", self.root)
        self.assertEqual(code, 1, out)
        self.assertRegex(out.rstrip().splitlines()[-1], r"^FAIL: baseline: slack \d+, expected 321$")


if __name__ == "__main__":
    unittest.main()
