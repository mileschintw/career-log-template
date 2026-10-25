#!/usr/bin/env python3
"""Tests for tools/check_save.py, on small Logs built in a temporary directory.

  python3 -I tools/tests/test_check_save.py
"""
import contextlib, importlib.util, io, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "check_save.py")
spec = importlib.util.spec_from_file_location("check_save", TOOL)
check_save = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_save)

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FOLDER = "outputs/applications/2026-02-01-example-engineer"
DRAFT = ".build/drafts/2026-02-01-example-engineer"
ENTRY = """---
visibility: public
---
# Queue

## What happened
Built a job queue.

## How it works
Retries.

## Results
One second.

## CI/CD
## Node.js work

## Past phrasings
- **backend:** "Built a job queue in Go" (sources/resumes/2026-01-old.tex)

## Conflicts
"""
TEX = r"""\begin{document}
\begin{itemize}
  \item Built a job queue in Go
  \item Cut retry latency to \textbf{one second} with backoff
\end{itemize}
\end{document}
"""
POSTING = "# Engineer at Example\n\nhttps://example.com/jobs/1\n\nBuild queues.\n"
PROVENANCE = """# Provenance

| Claim | Entry section | Source |
|---|---|---|
| Built a job queue | 2026-01-queue › What happened | (user, 2026-01-02) |
| Retry within one second | entries/2026-01-queue.md › Past phrasings | sources/resumes/2026-01-old.tex |
| Work authorisation | direction.md › Constraints | (user, 2026-01-10) |

## Company context

| Fact | URL |
|---|---|
| Example Corp runs queues | https://example.com/outputs/blog |

## Risks to handle in conversation
- The one-second figure is from one run.
"""


def with_row(row, text=PROVENANCE):
    return text.replace("\n## Company context", row + "\n## Company context", 1)


class CheckSave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "log")
        os.makedirs(self.root)
        self.write("entries/2026-01-queue.md", ENTRY)
        self.write("profile.md", "# Profile\n\n## Skills\nGo.\n\n## Education\nBSc.\n")
        os.makedirs(os.path.join(self.root, "skills", "career-log"))
        shutil.copy(os.path.join(REPO, "skills", "career-log", "writing.md"),
                    os.path.join(self.root, "skills", "career-log", "writing.md"))
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "base")

    def tearDown(self):
        shutil.rmtree(self.tmp, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))   # git's read-only objects

    def write(self, rel, body):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)

    def git(self, *args):
        subprocess.run(["git", "-C", self.root] + list(args), check=True, capture_output=True)

    def app(self, provenance=PROVENANCE, folder=FOLDER):
        """A posting run's folder as write step 10 saves it, and its draft."""
        draft = ".build/drafts/" + folder.split("/")[-1]
        for rel in (folder, draft):
            self.write(rel + "/resume.tex", TEX)
            self.write(rel + "/resume.pdf", "%PDF-1.5 example")
        self.write(folder + "/posting.md", POSTING)
        self.write(folder + "/provenance.md", provenance)

    def target(self, name="backend", body=None):
        self.write("outputs/resumes/%s.md" % name, body or "# Backend\n\nApproved text.\n\n" + PROVENANCE)
        self.write("outputs/resumes/%s.tex" % name, TEX)
        self.write("outputs/resumes/%s.pdf" % name, "%PDF-1.5 example")
        self.write(".build/drafts/%s/resume.tex" % name, TEX)
        self.write(".build/drafts/%s/resume.pdf" % name, "%PDF-1.5 example")

    def run_tool(self, *args, cwd=None):
        out = io.StringIO()
        old = os.getcwd()
        os.chdir(cwd or self.root)
        try:
            with contextlib.redirect_stdout(out):
                code = check_save.main(["check_save.py", *args, "--root", self.root])
        finally:
            os.chdir(old)
        return code, out.getvalue()

    def test_clean_application_folder_passes(self):
        self.app(PROVENANCE)
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), [
            "Files (%s): ok" % FOLDER,
            "Risks (%s): ok" % FOLDER,
            "Provenance check (%s/provenance.md): 3 rows; citing another output: none" % FOLDER,
            "Past phrasings: no entry changed",
            "Lint at save: ok",
            "Humanizer after review: none",
            "check_save: ok"])

    def test_path_from_outside_the_log_is_printed_from_its_root(self):
        self.app(PROVENANCE)
        code, out = self.run_tool(os.path.join(self.root, *FOLDER.split("/")) + os.sep, "--humanizer", "none",
                                  cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn("Provenance check (%s/provenance.md): 3 rows" % FOLDER, out)

    def test_row_citing_another_output_is_listed(self):
        for cell in ("outputs/resumes/backend.md", "backend provenance", "../../resumes/backend.md",
                     "sources/resumes/old.tex, outputs/resumes/backend.md",
                     "https://example.com/blob/main/outputs/resumes/backend.md"):
            self.app(with_row("| Skills line | backend target | %s |\n" % cell))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 1, cell)
            self.assertIn("4 rows; citing another output: line 8, names another output", out, cell)
            self.assertIn("Skills line", out, cell)
            self.assertTrue(out.endswith("check_save: fix the lines above, then run it again\n"), out)

    def test_source_citations_are_not_listed(self):
        rows = ("| Degree | profile.md › Education | sources/resumes/2024-old.tex, 2026-new.tex; transcript |\n"
                "| Queue design | 2026-01-queue › How it works | queue@abc1234:docs/reports/design.md:12 |\n"
                "| Queue blog | 2026-01-queue › How it works | https://example.com/reports/queues |\n")
        self.app(with_row(rows))
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("6 rows; citing another output: none", out)

    def test_entry_section_naming_another_file_is_listed(self):
        for section in ("stories.md › Application questions", "outputs/resumes/backend.md › Skills",
                        "entries/2026-02-missing.md › What happened", "entries/_template.md › Results",
                        "2026-02-missing.md › What happened"):
            self.app(with_row("| A claim | %s | (user, 2026-01-02) |\n" % section))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 1, section)
            self.assertIn("entry section names", out, section)

    def test_entry_section_naming_an_entry_or_profile_passes(self):
        for section in ("2026-01-queue.md › What happened", "./entries/2026-01-queue.md › What happened",
                        "profile.md › Skills", "2026-01-queue › CI/CD", "2026-01-queue › Node.js work",
                        "[Queue](../../../entries/2026-01-queue.md) › What happened",
                        "2026-01-queue › How it works (settings.toml layout)",
                        "2026-01-queue › Results; sources/notes/review.md"):
            self.app(with_row("| A claim | %s | (user, 2026-01-02) |\n" % section))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 0, (section, out))

    def test_report_linking_entries_from_its_folder_passes(self):
        """A report one folder down links entries as ../../entries/<x>.md."""
        rows = "| A claim | [Queue](../../entries/2026-01-queue.md) | (user, 2026-01-02) |\n"
        self.write("outputs/reports/2026-02-01-bio.md", "Kind: bio\n\n" + with_row(rows))
        code, out = self.run_tool("outputs/reports/2026-02-01-bio.md")
        self.assertEqual(code, 0, out)
        self.write("outputs/reports/2026-02-01-bio.md", "Kind: bio\n\n" + with_row(rows.replace("2026-01-queue", "2026-03-gone")))
        self.assertEqual(self.run_tool("outputs/reports/2026-02-01-bio.md")[0], 1)

    def test_missing_or_tableless_provenance_fails(self):
        os.makedirs(os.path.join(self.root, *FOLDER.split("/")))
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 1)
        self.assertIn("provenance.md): missing", out)
        self.app("# Provenance\n\nEvery claim comes from the backend target.\n")
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 1)
        self.assertIn("provenance.md): no provenance table", out)

    def test_provenance_file_with_a_bom_is_read_and_utf16_fails(self):
        path = os.path.join(self.root, *FOLDER.split("/"), "provenance.md")
        self.app()
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(PROVENANCE[PROVENANCE.index("|"):])
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("3 rows; citing another output: none", out)
        with open(path, "w", encoding="utf-16") as f:
            f.write(PROVENANCE)
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 1)
        self.assertIn("provenance.md): not UTF-8", out)

    def test_target_resume_and_report(self):
        self.target()
        self.write("outputs/reports/2026-02-01-bio.md", "Kind: bio\n\n" + PROVENANCE)
        code, out = self.run_tool("outputs/resumes/backend.md", "outputs/reports/2026-02-01-bio.md", "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("Provenance check (outputs/resumes/backend.md): 3 rows", out)
        self.assertIn("Provenance check (outputs/reports/2026-02-01-bio.md): 3 rows", out)
        # a report needs no --humanizer (a personal draft has no review); a resume does
        self.assertEqual(self.run_tool("outputs/reports/2026-02-01-bio.md")[0], 0)
        code, out = self.run_tool("outputs/resumes/backend.md")
        self.assertEqual(code, 1)
        self.assertIn("Humanizer after review: missing\n  fix: pass --humanizer", out)

    def test_humanizer_file(self):
        self.app(PROVENANCE)
        self.write(".build/humanizer.txt", "Built a job queue in Go. → Humanizer call: model Opus 5.5\n\n"
                   "Led the retry design. -> humanizer not available\n")
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
        self.assertEqual(code, 0, out)
        self.assertIn("Humanizer after review: Built a job queue in Go. -> Humanizer call: model Opus 5.5\n", out)
        self.assertIn("Humanizer after review: Led the retry design. -> humanizer not available\n", out)

    def test_humanizer_line_with_its_own_arrow(self):
        """An approved line may hold an arrow of its own: the last arrow before the call line splits it."""
        self.app(PROVENANCE)
        self.write(".build/humanizer.txt", "Cut p99 latency 40 ms -> 12 ms with batching → Humanizer call: model Opus 5.5\n"
                   "Moved the queue A → B in one release -> humanizer not available\n")
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
        self.assertEqual(code, 0, out)
        self.assertIn("review: Cut p99 latency 40 ms -> 12 ms with batching -> Humanizer call: model Opus 5.5\n", out)
        self.assertIn("review: Moved the queue A → B in one release -> humanizer not available\n", out)

    def test_humanizer_file_with_a_bom_is_read_and_utf16_exits_2(self):
        self.app(PROVENANCE)
        path = os.path.join(self.root, ".build", "humanizer.txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("Built a job queue. -> Humanizer call: model Opus 5.5\n")
        self.assertEqual(self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")[0], 0)
        with open(path, "w", encoding="utf-16") as f:
            f.write("Built a job queue. -> Humanizer call: model Opus 5.5\n")
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
        self.assertEqual(code, 2, out)
        self.assertIn("--humanizer .build/humanizer.txt", out)

    def test_humanizer_line_without_a_call_line_fails(self):
        self.app(PROVENANCE)
        for line in ("Built a job queue in Go.", "Built a job queue in Go. -> none", "-> Humanizer call: model Opus 5.5"):
            self.write(".build/humanizer.txt", line + "\n")
            code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
            self.assertEqual(code, 1, line)
            self.assertIn("Humanizer after review: not in the form", out, line)
        self.write(".build/humanizer.txt", "\n")
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
        self.assertEqual(code, 1)
        self.assertIn("is empty", out)

    def test_application_needs_humanizer(self):
        self.app(PROVENANCE)
        code, out = self.run_tool(FOLDER)
        self.assertEqual(code, 1)
        self.assertIn("Humanizer after review: missing", out)

    def test_bad_paths_exit_2(self):
        self.write(FOLDER + "/answers.md", "# Answers\n")
        for p in (FOLDER + "/answers.md", "entries/2026-01-queue.md", "outputs", os.path.join(self.tmp, "x.md")):
            code, out = self.run_tool(p, "--humanizer", "none")
            self.assertEqual(code, 2, p)
            self.assertIn("not an application folder or a saved provenance file", out)
        self.app(PROVENANCE)
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/no-such.txt")
        self.assertEqual(code, 2)
        self.assertIn("--humanizer .build/no-such.txt", out)

    def test_help_prints_the_docstring(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            check_save.main(["check_save.py", "--help"])
        self.assertEqual(exit.exception.code, 0)
        self.assertIn(check_save.__doc__.strip(), out.getvalue())

    def test_command_line_prints_utf8(self):
        """Run as a program, as write step 10 does: rows hold `›` and CJK, on a Windows console too."""
        self.app(with_row("| 佇列 | stories.md › 問題 | (user, 2026-01-02) |\n"))
        p = subprocess.run([sys.executable, "-I", os.path.abspath(TOOL), FOLDER, "--humanizer", "none", "--root", self.root],
                           cwd=self.root, capture_output=True)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("entry section names stories.md: 佇列 | stories.md › 問題", p.stdout.decode("utf-8"))

    # ---- the output's files (write step 10) ----

    def failing(self, *args, says):
        code, out = self.run_tool(*args)
        self.assertEqual(code, 1, out)
        self.assertIn(says, out)
        self.assertIn("\n  fix: ", out[out.index(says):])   # each failing line has its fix under it
        return out

    def test_application_folder_missing_files_or_url(self):
        self.app()
        os.remove(os.path.join(self.root, *FOLDER.split("/"), "resume.pdf"))
        out = self.failing(FOLDER, "--humanizer", "none", says="Files (%s): no resume.pdf\n  fix: copy the PDF" % FOLDER)
        self.app()
        self.write(FOLDER + "/posting.md", "# Engineer\n\nBuild queues.\n")
        self.failing(FOLDER, "--humanizer", "none", says="posting.md has no URL\n  fix: ")
        os.remove(os.path.join(self.root, *FOLDER.split("/"), "posting.md"))
        self.failing(FOLDER, "--humanizer", "none", says="Files (%s): no posting.md" % FOLDER)

    def test_resume_differs_from_the_draft(self):
        self.app()
        self.write(FOLDER + "/resume.tex", TEX.replace("Go", "Rust"))
        self.failing(FOLDER, "--humanizer", "none", says="resume.tex differs from the approved draft")
        self.app()
        self.write(DRAFT + "/resume.tex", TEX.replace("\n", "\r\n"))   # line ends aside
        self.assertEqual(self.run_tool(FOLDER, "--humanizer", "none")[0], 0)
        shutil.rmtree(os.path.join(self.root, ".build"))
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("note: no %s/resume.tex" % DRAFT, out)

    def test_pdf_compared_by_its_words_when_the_bytes_differ(self):
        """pdftotext stubbed: the bytes of two builds always differ, so the words decide."""
        self.app()
        self.write(DRAFT + "/resume.pdf", "%PDF-1.5 rebuilt")
        real = check_save.pdf_words
        try:
            check_save.pdf_words = lambda pdf: ["Built", "a", "queue"]
            self.assertEqual(self.run_tool(FOLDER, "--humanizer", "none")[0], 0)
            check_save.pdf_words = lambda pdf: ["Built", "a", "queue"] if "drafts" in pdf else ["Built", "a", "cache"]
            self.failing(FOLDER, "--humanizer", "none", says="resume.pdf is not the PDF built from the approved draft")
            check_save.pdf_words = lambda pdf: None
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 0, out)
            self.assertIn("pdftotext (poppler) is not found", out)
        finally:
            check_save.pdf_words = real

    def test_resume_with_the_email_as_a_gap_fails(self):
        """#410: pdftotext stubbed; a saved resume must not still hold `GAP: email`."""
        self.app()
        real = check_save.pdf_words
        try:
            check_save.pdf_words = lambda pdf: "Ada | GAP: email | github.com/x".split()
            self.failing(FOLDER, "--humanizer", "none", says="resume.pdf still has the email as a GAP")
            check_save.pdf_words = lambda pdf: "Ada | ada@example.com | GAP: email".split()   # an address wins
            self.assertEqual(self.run_tool(FOLDER, "--humanizer", "none")[0], 0)
            self.target("general")
            check_save.pdf_words = lambda pdf: "Ada | Email: GAP".split()
            self.failing("outputs/resumes/general.md", "--humanizer", "none",
                         says="outputs/resumes/general.pdf still has the email as a GAP")
        finally:
            check_save.pdf_words = real

    def test_answers_need_type_lines(self):
        self.app()
        self.write(FOLDER + "/answers.md", "# Answers\n\n## Why us?\nType: why-company\n\nBecause queues.\n\n"
                                           "## A hard bug\n\nThe retry storm.\n")
        out = self.failing(FOLDER, "--humanizer", "none", says="answers.md heading with no Type: line under it: ## A hard bug")
        self.assertNotIn("Why us", out)
        self.write(FOLDER + "/answers.md", "## A hard bug\nType: hard-bug\n\nThe retry storm.\n")
        self.assertEqual(self.run_tool(FOLDER, "--humanizer", "none")[0], 0)

    def test_archived_marker_format(self):
        self.app()
        self.write(FOLDER + "/archived.md", "Archived 2026-02-01\n")
        self.failing(FOLDER, "--humanizer", "none", says="archived.md is not the one line")
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-01)\n")
        self.assertEqual(self.run_tool(FOLDER, "--humanizer", "none")[0], 0)

    def test_target_needs_its_tex_pdf_and_risks(self):
        self.target()
        os.remove(os.path.join(self.root, "outputs", "resumes", "backend.pdf"))
        self.failing("outputs/resumes/backend.md", "--humanizer", "none", says="no outputs/resumes/backend.pdf")
        self.target(body="# Backend\n\n" + PROVENANCE[:PROVENANCE.index("## Company")])
        self.failing("outputs/resumes/backend.md", "--humanizer", "none",
                     says="Risks (outputs/resumes/backend.md): no `## Risks to handle in conversation` section")
        self.target(body="# Backend\n\n## Risks to handle in conversation\n- One run.\n\n## Provenance\n\n"
                         + PROVENANCE[PROVENANCE.index("|"):PROVENANCE.index("## Company")])
        self.failing("outputs/resumes/backend.md", "--humanizer", "none", says="after the provenance table")
        self.target(body="# Backend\n\n" + PROVENANCE.replace("|---|---|---|\n", "|---|---|---|\n| A \\| B claim | 2026-01-queue › Results | (user, 2026-01-02) |\n", 1))
        code, out = self.run_tool("outputs/resumes/backend.md", "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("4 rows; citing another output: none", out)   # `\|` is a pipe inside a cell

    def test_report_name_and_kind(self):
        body = PROVENANCE[PROVENANCE.index("|"):]
        self.write("outputs/reports/bio.md", "Kind: bio\n\n" + body)
        self.failing("outputs/reports/bio.md", says="not named outputs/reports/<YYYY-MM-DD>-<slug>.md")
        self.write("outputs/reports/2026-02-30-bio.md", "Kind: bio\n\n" + body)
        self.failing("outputs/reports/2026-02-30-bio.md", says="not named")
        self.write("outputs/reports/2026-02-01-bio.md", "A bio.\n\n" + body)
        self.failing("outputs/reports/2026-02-01-bio.md", says="no `Kind:` line above the first table")
        self.write("outputs/reports/2026-02-01-bio.md", "Kind: memoir\n\n" + body)
        self.failing("outputs/reports/2026-02-01-bio.md", says="Kind: memoir is none of the kinds")
        self.write("outputs/reports/2026-02-01-why.md", "Kind: application answer\n\n## Why us?\n\nQueues.\n\n" + body)
        self.failing("outputs/reports/2026-02-01-why.md", "--humanizer", "none", says="question heading with no Type: line under it: ## Why us?")

    def test_employer_facing_report_needs_humanizer(self):
        """Finding 15: a cover letter, an answer or bullets in outputs/reports/ had a review; a bio did not."""
        body = PROVENANCE[PROVENANCE.index("|"):]
        for kind in ("cover letter", "resume bullets", "application answer"):
            self.write("outputs/reports/2026-02-01-x.md", "Kind: %s\n\nText.\n\n%s" % (kind, body))
            self.failing("outputs/reports/2026-02-01-x.md", says="Humanizer after review: missing")
            self.assertEqual(self.run_tool("outputs/reports/2026-02-01-x.md", "--humanizer", "none")[0], 0, kind)
        self.write("outputs/reports/2026-02-01-x.md", "Kind: other\n\n## Why us?\nType: why-company\n\nQueues.\n\n" + body)
        self.failing("outputs/reports/2026-02-01-x.md", says="Humanizer after review: missing")
        for kind in ("bio", "elevator pitch", "other"):
            self.write("outputs/reports/2026-02-01-x.md", "Kind: %s\n\nText.\n\n%s" % (kind, body))
            self.assertEqual(self.run_tool("outputs/reports/2026-02-01-x.md")[0], 0, kind)

    def test_bullets_report_needs_risks(self):
        """A resume bullets report carries the caveats behind its bullets, as a resume does; a bio does not."""
        body = PROVENANCE[PROVENANCE.index("|"):PROVENANCE.index("## Risks")]
        self.write("outputs/reports/2026-02-01-x.md", "Kind: resume bullets\n\n- Built a queue\n\n" + body)
        self.failing("outputs/reports/2026-02-01-x.md", "--humanizer", "none",
                     says="Risks (outputs/reports/2026-02-01-x.md): no `## Risks to handle in conversation` section"
                          " after the provenance table in outputs/reports/2026-02-01-x.md")
        self.write("outputs/reports/2026-02-01-x.md", "Kind: bio\n\nText.\n\n" + body)
        self.assertEqual(self.run_tool("outputs/reports/2026-02-01-x.md")[0], 0)

    def test_missing_section_after_the_arrow_is_listed(self):
        for section in ("2026-01-queue › Nowhere", "entries/2026-01-queue.md › Results › Latency", "profile.md › Hobbies"):
            self.app(with_row("| A claim | %s | (user, 2026-01-02) |\n" % section))
            out = self.failing(FOLDER, "--humanizer", "none", says="no heading there")
            self.assertIn(section.split(" › ")[-1], out, section)

    def test_relative_saved_path_is_read_from_the_root(self):
        self.app()
        code, out = self.run_tool(FOLDER, "--humanizer", "none", cwd=self.tmp)
        self.assertEqual(code, 0, out)

    # ---- Past phrasings and the entries ----

    def entry(self, phrasings, extra=""):
        self.write("entries/2026-01-queue.md", ENTRY.replace(
            '- **backend:** "Built a job queue in Go" (sources/resumes/2026-01-old.tex)\n', phrasings).replace(
            "## How it works\n", "## How it works\n" + extra))

    OLD = '- **backend:** "Built a job queue in Go" (sources/resumes/2026-01-old.tex)\n'
    NEW = '- **backend:** "Cut retry latency to one second with backoff" (%s)\n' % FOLDER

    def test_past_phrasings_addition_of_an_approved_bullet_passes(self):
        self.app()
        self.entry(self.OLD + self.NEW)
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("Past phrasings (entries/2026-01-queue.md): +1 -0; ok", out)

    def test_past_phrasings_findings(self):
        self.app()
        cases = [
            (self.NEW, "removed [backend]"),   # a removal beside an addition is listed, not failed
            ('- **backend:** "Built a job queue in Go" (%s)\n' % FOLDER, "rewritten"),
            ("", "1 line(s) removed, 0 added"),
            (self.OLD + self.NEW.replace(FOLDER, FOLDER + ", 2026-02-01"), "cite it as (%s)" % FOLDER),
            (self.OLD + '- **backend:** "Led the queue team" (%s)\n' % FOLDER, "no bullet of the approved resume"),
            (self.OLD + '- "Cut retry latency to one second with backoff" (%s)\n' % FOLDER, "not in the form"),
        ]
        for phrasings, says in cases:
            self.entry(phrasings)
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertIn(says, out, phrasings)
            self.assertEqual(code, 0 if says.startswith("removed") else 1, out)

    def test_word_only_addition_is_listed_not_failed(self):
        self.app()
        self.entry(self.OLD + '- **backend:** "Built a job queue in Go" (%s)\n' % FOLDER)
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("  check: added [backend]", out)
        self.assertIn("differs only in words", out)

    def test_archived_save_adds_no_line(self):
        self.app()
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-01)\n")
        self.entry(self.OLD + self.NEW)
        self.failing(FOLDER, "--humanizer", "none", says="cites an Archived output")
        # a demote: the line citing the folder, from an earlier Reference save, goes
        self.write("entries/2026-01-queue.md", ENTRY.replace(self.OLD, self.NEW))
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "reference save")
        self.write("entries/2026-01-queue.md", ENTRY.replace(self.OLD, ""))
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("+0 -1 (1 citing an Archived output: the demote's); ok", out)

    def test_entry_line_naming_an_output_fails(self):
        self.app()
        self.entry(self.OLD, extra="Used in %s.\n" % FOLDER)
        self.failing(FOLDER, "--humanizer", "none", says="Entries (entries/2026-01-queue.md): added a line naming an output")

    def test_bullets_report_feeds_and_its_demote(self):
        """D8: a resume bullets report feeds Past phrasings, cited by its path; archived, those lines go."""
        rel = "outputs/reports/2026-02-01-backend-bullets.md"
        body = PROVENANCE[PROVENANCE.index("|"):]
        self.write(rel, "Kind: resume bullets\n\n- Cut retry latency to **one second** with backoff\n\n" + body)
        line = '- **backend:** "Cut retry latency to one second with backoff" (%s)\n' % rel
        self.entry(self.OLD + line)
        code, out = self.run_tool(rel, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("+1 -0; ok", out)
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "reference save")
        self.write(rel, "Kind: resume bullets\nArchived (user, 2026-02-02)\n\n- Cut retry latency to one second with backoff\n\n" + body)
        self.entry(self.OLD)
        code, out = self.run_tool(rel, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("the demote's", out)
        self.entry(self.OLD + line)   # an Archived report feeds nothing
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "x")
        self.write("entries/2026-01-queue.md", ENTRY.replace(self.OLD, self.OLD + line.replace("backend:", "general:")))
        self.failing(rel, "--humanizer", "none", says="cites an Archived output")
        # a bio's text feeds nothing
        self.write("outputs/reports/2026-02-01-bio.md", "Kind: bio\n\n- Cut retry latency to one second with backoff\n\n" + body)
        self.write("entries/2026-01-queue.md", ENTRY.replace(self.OLD, self.OLD + line + line.replace(
            rel, "outputs/reports/2026-02-01-bio.md").replace("backend:", "general:")))
        self.failing("outputs/reports/2026-02-01-bio.md", says="no bullet of the approved resume or bullets report")

    def test_uppercase_angle_is_the_form(self):
        self.app()
        self.entry(self.OLD + self.NEW.replace("**backend:**", "**Backend:**"))
        self.assertEqual(self.run_tool(FOLDER, "--humanizer", "none")[0], 0)

    def test_log_below_the_git_top_level(self):
        """--root names a folder inside a bigger repo: git's paths are read from the root."""
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        sub = os.path.join(repo, "log")
        shutil.move(self.root, sub)
        shutil.move(os.path.join(sub, ".git"), os.path.join(repo, ".git"))
        self.root = sub
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "moved")
        self.app()
        self.entry(self.OLD + '- **backend:** "Led the queue team" (%s)\n' % FOLDER)
        self.failing(FOLDER, "--humanizer", "none", says="no bullet of the approved resume")

    # ---- review fixes: headings, links, markers, paths ----

    def test_section_with_a_note_a_list_or_parentheses(self):
        self.write("entries/2026-01-queue.md", ENTRY.replace("## Results\n", "## Results (2026)\n## Results\n"))
        for section in ("2026-01-queue › Results (2026)", "2026-01-queue › What happened, profile.md › Skills",
                        "2026-01-queue › Results (the second run)"):
            self.app(with_row("| A claim | %s | (user, 2026-01-02) |\n" % section))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 0, (section, out))
        self.app(with_row("| A claim | [Queue](../../../entries/2026-01-queue.md) › Nowhere | (user, 2026-01-02) |\n"))
        self.failing(FOLDER, "--humanizer", "none", says="› Nowhere, no heading there")

    def test_report_question_heading_above_its_kind_line(self):
        body = PROVENANCE[PROVENANCE.index("|"):]
        self.write("outputs/reports/2026-02-01-why.md", "# Why Example?\nKind: application answer\nType: motivation\n\n"
                                                        "Queues.\n\n" + body)
        self.assertEqual(self.run_tool("outputs/reports/2026-02-01-why.md", "--humanizer", "none")[0], 0)

    def test_malformed_archived_marker_fails(self):
        body = PROVENANCE[PROVENANCE.index("|"):]
        self.write("outputs/reports/2026-02-01-b.md", "Kind: resume bullets\nArchived (user, 2026-2-3)\n\n- A bullet\n\n" + body)
        self.failing("outputs/reports/2026-02-01-b.md", "--humanizer", "none", says="an Archived line not in the form")
        self.app()
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-13-45)\n")
        self.failing(FOLDER, "--humanizer", "none", says="archived.md is not the one line")

    def test_missing_saved_file_and_non_utf8_exit_2(self):
        for p in ("outputs/reports/2026-02-01-nothere.md", "outputs/resumes/nothere.md"):
            code, out = self.run_tool(p)
            self.assertEqual(code, 2, (p, out))
        self.app()
        with open(os.path.join(self.root, *FOLDER.split("/"), "posting.md"), "wb") as f:
            f.write(b"\xff\xfe bad https://example.com")
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 2, out)
        self.assertIn("cannot read %s/posting.md: not UTF-8" % FOLDER, out)

    # ---- lint at save ----

    def test_lint_at_save_private_link_and_repeated_number(self):
        self.write("entries/2026-02-secret.md", "---\nvisibility: private\nlinks: https://github.com/acme/secret\n---\n# Secret\n")
        self.app()
        self.write(FOLDER + "/resume.tex", TEX.replace("with backoff", "with backoff, 820 ms before"))
        self.write(DRAFT + "/resume.tex", TEX.replace("with backoff", "with backoff, 820 ms before"))
        self.write(FOLDER + "/answers.md", "## A hard bug\nType: hard-bug\n\nIt was 820 ms.\n")
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("Lint at save: check: ", out)
        self.assertIn("820 appears in 2 artifacts", out)
        self.write(FOLDER + "/answers.md", "## A hard bug\nType: hard-bug\n\nSee https://github.com/acme/secret/pull/3.\n")
        self.failing(FOLDER, "--humanizer", "none", says="Lint at save: fix: ")

    # ---- --audit ----

    def test_audit(self):
        self.app()
        self.assertEqual(self.run_tool("--audit"), (0, "check_save: ok\n"))
        self.write("outputs/applications/2026-01-05-acme-dev/posting.md", POSTING)
        self.write("outputs/applications/2026-01-06-acme-interview/sent-version.md", "abc1234\n")
        self.write("outputs/notes.md", "x\n")
        self.write("outputs/applications/2026-01-07-acme-ops/provenance.md", "# Provenance\n\nFrom the backend target.\n")
        self.write("outputs/applications/2026-01-07-acme-ops/resume.pdf", "%PDF")
        self.write("outputs/reports/2026-02-01-scan.md", "| Posting | Source |\n|---|---|\n| x | outputs/y |\n")
        self.write("outputs/reports/2026-02-01-bio.md", "Kind: bio\n\n" + with_row("| x | stories.md › Q | (user, 2026-01-02) |\n"))
        code, out = self.run_tool("--audit")
        self.assertEqual(code, 1, out)
        self.assertIn("finding: outputs/applications/2026-01-05-acme-dev: no provenance.md", out)
        self.assertIn("finding: outputs/applications/2026-01-05-acme-dev: no resume.pdf: a finding when it was sent", out)
        self.assertIn("finding: outputs/notes.md: at the top of outputs/", out)
        self.assertIn("finding: outputs/applications/2026-01-07-acme-ops/provenance.md: no provenance table", out)
        self.assertIn("finding: outputs/reports/2026-02-01-bio.md:10 entry section names stories.md", out)
        self.assertNotIn("interview", out)
        self.assertNotIn("scan.md", out)
        self.assertTrue(out.endswith("check_save: 5 findings: report each\n"), out)
        self.assertEqual(self.run_tool("--audit", FOLDER)[0], 2)

    def test_audit_report_with_no_table(self):
        """#481: every saved report holds a provenance table, as an application folder does."""
        self.write("outputs/reports/2026-02-02-pitch.md", "Kind: pitch\n\nA pitch with no table.\n")
        code, out = self.run_tool("--audit")
        self.assertEqual(code, 1, out)
        self.assertIn("finding: outputs/reports/2026-02-02-pitch.md: no provenance table", out)
        self.assertTrue(out.endswith("check_save: 1 findings: report each\n"), out)


if __name__ == "__main__":
    unittest.main()
