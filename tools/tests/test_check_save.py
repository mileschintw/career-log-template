#!/usr/bin/env python3
"""Tests for tools/check_save.py, on small Logs built in a temporary directory.

  python3 -I tools/tests/test_check_save.py
"""
import contextlib, importlib.util, io, os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "check_save.py")
spec = importlib.util.spec_from_file_location("check_save", TOOL)
check_save = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_save)

FOLDER = "outputs/applications/2026-02-01-example-engineer"
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
        os.makedirs(os.path.join(self.root, ".git"))
        self.write("entries/2026-01-queue.md", "# Queue\n")
        self.write("profile.md", "# Profile\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rel, body):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)

    def run_tool(self, *args, cwd=None):
        out = io.StringIO()
        old = os.getcwd()
        os.chdir(cwd or self.root)
        try:
            with contextlib.redirect_stdout(out):
                code = check_save.main(["check_save.py", *args])
        finally:
            os.chdir(old)
        return code, out.getvalue()

    def test_clean_application_folder_passes(self):
        self.write(FOLDER + "/provenance.md", PROVENANCE)
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), [
            "Provenance check (%s/provenance.md): 3 rows; citing another output: none" % FOLDER,
            "Humanizer after review: none",
            "check_save: ok"])

    def test_path_from_outside_the_log_is_printed_from_its_root(self):
        self.write(FOLDER + "/provenance.md", PROVENANCE)
        code, out = self.run_tool(os.path.join(self.root, *FOLDER.split("/")) + os.sep, "--humanizer", "none",
                                  cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn("Provenance check (%s/provenance.md): 3 rows" % FOLDER, out)

    def test_row_citing_another_output_is_listed(self):
        for cell in ("outputs/resumes/backend.md", "backend provenance", "../../resumes/backend.md",
                     "sources/resumes/old.tex, outputs/resumes/backend.md",
                     "https://example.com/blob/main/outputs/resumes/backend.md"):
            self.write(FOLDER + "/provenance.md", with_row("| Skills line | backend target | %s |\n" % cell))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 1, cell)
            self.assertIn("4 rows; citing another output: line 8, names another output", out, cell)
            self.assertIn("Skills line", out, cell)
            self.assertTrue(out.endswith("check_save: fix the lines above, then run it again\n"), out)

    def test_source_citations_are_not_listed(self):
        rows = ("| Degree | profile.md › Education | sources/resumes/2024-old.tex, 2026-new.tex; transcript |\n"
                "| Queue design | 2026-01-queue › How it works | queue@abc1234:docs/reports/design.md:12 |\n"
                "| Queue blog | 2026-01-queue › How it works | https://example.com/reports/queues |\n")
        self.write(FOLDER + "/provenance.md", with_row(rows))
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("6 rows; citing another output: none", out)

    def test_entry_section_naming_another_file_is_listed(self):
        for section in ("stories.md › Application questions", "outputs/resumes/backend.md › Skills",
                        "entries/2026-02-missing.md › What happened", "entries/_template.md › Results",
                        "2026-02-missing.md › What happened"):
            self.write(FOLDER + "/provenance.md", with_row("| A claim | %s | (user, 2026-01-02) |\n" % section))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 1, section)
            self.assertIn("entry section names", out, section)

    def test_entry_section_naming_an_entry_or_profile_passes(self):
        for section in ("2026-01-queue.md › What happened", "./entries/2026-01-queue.md › What happened",
                        "profile.md › Skills", "2026-01-queue › CI/CD", "2026-01-queue › Node.js work",
                        "[Queue](../../../entries/2026-01-queue.md) › What happened",
                        "2026-01-queue › How it works (settings.toml layout)",
                        "2026-01-queue › Results; sources/notes/review.md"):
            self.write(FOLDER + "/provenance.md", with_row("| A claim | %s | (user, 2026-01-02) |\n" % section))
            code, out = self.run_tool(FOLDER, "--humanizer", "none")
            self.assertEqual(code, 0, (section, out))

    def test_report_linking_entries_from_its_folder_passes(self):
        """A report one folder down links entries as ../../entries/<x>.md."""
        rows = "| A claim | [Queue](../../entries/2026-01-queue.md) | (user, 2026-01-02) |\n"
        self.write("outputs/reports/2026-02-01-bio.md", with_row(rows))
        code, out = self.run_tool("outputs/reports/2026-02-01-bio.md")
        self.assertEqual(code, 0, out)
        self.write("outputs/reports/2026-02-01-bio.md", with_row(rows.replace("2026-01-queue", "2026-03-gone")))
        self.assertEqual(self.run_tool("outputs/reports/2026-02-01-bio.md")[0], 1)

    def test_missing_or_tableless_provenance_fails(self):
        os.makedirs(os.path.join(self.root, *FOLDER.split("/")))
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 1)
        self.assertIn("provenance.md): missing", out)
        self.write(FOLDER + "/provenance.md", "# Provenance\n\nEvery claim comes from the backend target.\n")
        code, out = self.run_tool(FOLDER, "--humanizer", "none")
        self.assertEqual(code, 1)
        self.assertIn("provenance.md): no provenance table", out)

    def test_provenance_file_with_a_bom_is_read_and_utf16_fails(self):
        path = os.path.join(self.root, *FOLDER.split("/"), "provenance.md")
        os.makedirs(os.path.dirname(path))
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
        self.write("outputs/resumes/backend.md", "# Backend\n\nApproved text.\n\n" + PROVENANCE)
        self.write("outputs/reports/2026-02-01-bio.md", PROVENANCE)
        code, out = self.run_tool("outputs/resumes/backend.md", "outputs/reports/2026-02-01-bio.md", "--humanizer", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("Provenance check (outputs/resumes/backend.md): 3 rows", out)
        self.assertIn("Provenance check (outputs/reports/2026-02-01-bio.md): 3 rows", out)
        # a report needs no --humanizer (a personal draft has no review); a resume does
        self.assertEqual(self.run_tool("outputs/reports/2026-02-01-bio.md")[0], 0)
        code, out = self.run_tool("outputs/resumes/backend.md")
        self.assertEqual(code, 1)
        self.assertIn("Humanizer after review: missing: pass --humanizer", out)

    def test_humanizer_file(self):
        self.write(FOLDER + "/provenance.md", PROVENANCE)
        self.write(".build/humanizer.txt", "Built a job queue in Go. → Humanizer call: model Opus 5.5\n\n"
                   "Led the retry design. -> humanizer not available\n")
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
        self.assertEqual(code, 0, out)
        self.assertIn("Humanizer after review: Built a job queue in Go. -> Humanizer call: model Opus 5.5\n", out)
        self.assertIn("Humanizer after review: Led the retry design. -> humanizer not available\n", out)

    def test_humanizer_line_with_its_own_arrow(self):
        """An approved line may hold an arrow of its own: the last arrow before the call line splits it."""
        self.write(FOLDER + "/provenance.md", PROVENANCE)
        self.write(".build/humanizer.txt", "Cut p99 latency 40 ms -> 12 ms with batching → Humanizer call: model Opus 5.5\n"
                   "Moved the queue A → B in one release -> humanizer not available\n")
        code, out = self.run_tool(FOLDER, "--humanizer", ".build/humanizer.txt")
        self.assertEqual(code, 0, out)
        self.assertIn("review: Cut p99 latency 40 ms -> 12 ms with batching -> Humanizer call: model Opus 5.5\n", out)
        self.assertIn("review: Moved the queue A → B in one release -> humanizer not available\n", out)

    def test_humanizer_file_with_a_bom_is_read_and_utf16_exits_2(self):
        self.write(FOLDER + "/provenance.md", PROVENANCE)
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
        self.write(FOLDER + "/provenance.md", PROVENANCE)
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
        self.write(FOLDER + "/provenance.md", PROVENANCE)
        code, out = self.run_tool(FOLDER)
        self.assertEqual(code, 1)
        self.assertIn("Humanizer after review: missing", out)

    def test_bad_paths_exit_2(self):
        self.write(FOLDER + "/answers.md", "# Answers\n")
        for p in (FOLDER + "/answers.md", "entries/2026-01-queue.md", "outputs", os.path.join(self.tmp, "x.md")):
            code, out = self.run_tool(p, "--humanizer", "none")
            self.assertEqual(code, 2, p)
            self.assertIn("not an application folder or a saved provenance file", out)
        self.write(FOLDER + "/provenance.md", PROVENANCE)
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
        import subprocess
        self.write(FOLDER + "/provenance.md", with_row("| 佇列 | stories.md › 問題 | (user, 2026-01-02) |\n"))
        p = subprocess.run([sys.executable, "-I", os.path.abspath(TOOL), FOLDER, "--humanizer", "none"],
                           cwd=self.root, capture_output=True)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("entry section names stories.md: 佇列 | stories.md › 問題", p.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
