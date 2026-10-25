#!/usr/bin/env python3
"""Tests for tools/application.py, on small Logs built in a temporary git repository.

  python3 -I tools/tests/test_application.py
"""
import contextlib, importlib.util, io, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "application.py")
spec = importlib.util.spec_from_file_location("application", TOOL)
application = importlib.util.module_from_spec(spec)
spec.loader.exec_module(application)

RESUME = r"""\documentclass{article}
\begin{document}
\begin{itemize}
  \item Cut quote API p95 latency from 820 ms to 210 ms with a Redis rate cache
  \item \textbf{Queue:} Built a Go job queue on PostgreSQL for 40\% of traffic
\end{itemize}
\end{document}
"""

ENTRY = """---
title: Queue work
---
# Queue work

## Past phrasings
- **backend:** "Cut quote API p95 latency from 820 ms to 210 ms with a Redis cache" (sources/resumes/2025-09-draft.tex)
- **backend:** "Reduced p95 latency to 210 ms with a Redis cache" (outputs/applications/2026-01-05-acme-backend-engineer)
- **general:** "Built a job queue" (applications/2026-02-01-acme-platform-engineer)

## Conflicts
"""

STORIES = """# Stories

## Application questions

| Question type | Scope | Answer from | User's direction | Approved answer |
|---|---|---|---|---|
| Why this company | per-company | entries | - | |
| Biggest challenge | per-angle | entries | - | backend: [answer](outputs/applications/2026-02-01-acme-platform-engineer/answers.md); general: [answer](outputs/reports/2026-01-01-challenge.md) |
| About you | shared | profile | - | [answer](outputs/applications/2026-02-01-acme-platform-engineer/answers.md) |
"""

ANSWERS = """# Answers

## Why do you want to work here? (150 words)
Type: Why this company

Because.

## Your biggest challenge (200 words)
Type: Biggest challenge

The queue.
"""

PROVENANCE = """# Provenance

| Claim | Entry section | Source |
|---|---|---|
| 820 ms | entries/2025-06-queue.md › Results | PR 1 |

## Risks to handle in conversation
- The 820 ms baseline was a staging number.
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "log")
        os.makedirs(self.root)
        self.git("init", "-q")
        self.write("README.md", "# Log\n")
        self.commit("base")

    def tearDown(self):
        shutil.rmtree(self.tmp, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))   # git's read-only objects

    def git(self, *args):
        return subprocess.run(["git", "-C", self.root] + list(args), check=True, capture_output=True,
                              encoding="utf-8").stdout

    def commit(self, message, date=None):
        env = dict(os.environ)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self.git("add", "-A")
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit",
                        "-q", "-m", message], check=True, capture_output=True, env=env)

    def write(self, rel, body, binary=False):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if binary:
            with open(path, "wb") as f:
                f.write(body)
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
        return path

    def read(self, rel):
        with open(os.path.join(self.root, *rel.split("/")), encoding="utf-8") as f:
            return f.read()

    def exists(self, rel):
        return os.path.exists(os.path.join(self.root, *rel.split("/")))

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = application.main(["--root", self.root] + list(args))
        return code, out.getvalue().splitlines()

    def folder(self, name, archived=False, answers=ANSWERS):
        rel = "outputs/applications/" + name
        self.write(rel + "/posting.md", "https://example.com/job\n")
        self.write(rel + "/resume.tex", RESUME)
        if answers:
            self.write(rel + "/answers.md", answers)
        self.write(rel + "/provenance.md", PROVENANCE)
        if archived:
            self.write(rel + "/archived.md", "Archived (user, 2026-01-01)\n")
        return rel


class Name(Base):
    def test_posting_run(self):
        code, out = self.run_tool("name", "--company", "Acme & Co.", "--role", "Backend  Engineer", "--today", "2026-03-02")
        self.assertEqual(code, 0)
        self.assertEqual(out, ["name: 2026-03-02-acme-co-backend-engineer",
                               "draft: .build/drafts/2026-03-02-acme-co-backend-engineer/",
                               "folder: outputs/applications/2026-03-02-acme-co-backend-engineer/",
                               "commit: write(acme-co): Backend Engineer"])

    def test_saved_folder_takes_the_next_suffix_and_drafts_do_not(self):
        self.folder("2026-03-02-acme-backend-engineer")
        self.write(".build/drafts/2026-03-02-acme-backend-engineer-2/resume.tex", RESUME)
        _, out = self.run_tool("name", "--company", "Acme", "--role", "Backend Engineer", "--today", "2026-03-02")
        self.assertIn("folder: outputs/applications/2026-03-02-acme-backend-engineer-2/", out)
        _, again = self.run_tool("name", "--company", "Acme", "--role", "Backend Engineer", "--today", "2026-03-02")
        self.assertEqual(out, again)

    def test_target_run(self):
        _, out = self.run_tool("name", "--target", "AI Infra")
        self.assertEqual(out, ["name: ai-infra", "draft: .build/drafts/ai-infra/", "resume: outputs/resumes/ai-infra.md",
                               "commit: write(ai-infra): resume"])

    def test_report(self):
        self.write("outputs/reports/2026-03-02-bio.md", "x\n")
        _, out = self.run_tool("name", "--report", "Bio", "--kind", "bio", "--today", "2026-03-02")
        self.assertEqual(out, ["name: bio-2", "draft: .build/drafts/bio-2/", "report: outputs/reports/2026-03-02-bio-2.md",
                               "commit: write(bio-2): bio"])

    def test_bad_arguments(self):
        self.assertEqual(self.run_tool("name", "--company", "Acme")[0], 2)
        self.assertEqual(self.run_tool("name", "--report", "bio", "--kind", "poem")[0], 2)
        self.assertEqual(self.run_tool("name", "--target", "x", "--company", "a", "--role", "b")[0], 2)


class Prior(Base):
    def setUp(self):
        super().setUp()
        self.folder("2026-02-01-acme-platform-engineer")
        self.folder("2025-11-03-acme-backend-engineer", archived=True)
        self.folder("2025-10-01-acme-data-engineer", answers="# Answers\n\n## Why us?\nBecause.\n")
        self.folder("2025-09-01-acme-sre", archived=True, answers="# Answers\n\n## Why Acme?\nBecause.\n")
        self.folder("2026-01-01-acmeco-intern")
        self.write("applications.md", "# Applications\n\n| Event | Company |\n|---|---|\n| Fair 2026 | Acme |\n| Fair | Acmeco |\n")
        self.commit("save", date="2026-02-01T12:00:00")
        self.write("entries/x.md", "x\n")
        self.commit("entry", date="2026-02-10T12:00:00")

    def test_folders_and_lines(self):
        code, out = self.run_tool("prior", "Acme")
        self.assertEqual(code, 0)
        self.assertEqual(out, [
            "company: Acme",
            "folder: outputs/applications/2026-02-01-acme-platform-engineer/ | 2026-02-01 | Reference | types: Biggest challenge; Why this company",
            "folder: outputs/applications/2025-11-03-acme-backend-engineer/ | 2025-11-03 | Archived | types: Biggest challenge; Why this company",
            "folder: outputs/applications/2025-10-01-acme-data-engineer/ | 2025-10-01 | Reference | types: none",
            "folder: outputs/applications/2025-09-01-acme-sre/ | 2025-09-01 | Archived | types: none",
            "applications.md:5: | Fair 2026 | Acme |"])

    def test_type_answers_and_what_changed_since(self):
        _, out = self.run_tool("prior", "acme", "--type", "why this company")
        self.assertIn("answer: outputs/applications/2026-02-01-acme-platform-engineer/answers.md:3 | 2026-02-01 | Reference"
                      " | Why do you want to work here? (150 words)", out)
        self.assertIn("sent before: outputs/applications/2025-11-03-acme-backend-engineer/answers.md:3 | 2025-11-03 |"
                      " Archived | Why do you want to work here? (150 words)", out)
        self.assertIn("untyped: outputs/applications/2025-10-01-acme-data-engineer/answers.md:3 | 2025-10-01 | Reference"
                      " | Why us?", out)
        self.assertIn("sent before: outputs/applications/2025-09-01-acme-sre/answers.md:3 | 2025-09-01 | Archived | Why Acme?", out)
        self.assertIn("since 2025-10-01: 1 commits", out)   # an untyped candidate's date too
        self.assertFalse(any(l.startswith(("since 2025-11-03", "since 2025-09-01")) for l in out), out)
        since = out.index("since 2026-02-01: 1 commits")
        self.assertTrue(out[since + 1].strip().endswith("entry"), out)

    def test_several_names_and_none(self):
        _, out = self.run_tool("prior", "Globex", "Acmeco")
        self.assertEqual(out[:2], ["company: Globex", "none: no application folder or applications.md line names Globex"])
        self.assertIn("folder: outputs/applications/2026-01-01-acmeco-intern/ | 2026-01-01 | Reference | types: "
                      "Biggest challenge; Why this company", out)
        self.assertIn("applications.md:6: | Fair | Acmeco |", out)


class Start(Base):
    def test_targets_and_newest_main(self):
        self.write("outputs/resumes/general.tex", RESUME)
        self.write("sources/resumes/2024-05-01-main.tex", RESUME)
        self.write("sources/resumes/2025-01-01-main.tex", RESUME)
        self.write("sources/resumes/2026-01-01-other.tex", RESUME)
        _, out = self.run_tool("start")
        self.assertEqual(out, ["target: general | outputs/resumes/general.tex",
                               "fallback: sources/resumes/2025-01-01-main.tex"])

    def test_newest_tex_tie_and_blank(self):
        _, out = self.run_tool("start")
        self.assertEqual(out, ["targets: none", "fallback: skills/career-log/assets/resume-blank.tex"])
        self.write("sources/resumes/2025-01-01-a.tex", RESUME)
        self.write("sources/resumes/2025-01-01-b.tex", RESUME)
        _, out = self.run_tool("start")
        self.assertEqual(out[-1], "fallback: tie: sources/resumes/2025-01-01-a.tex, sources/resumes/2025-01-01-b.tex")

    def test_copy_and_refusals(self):
        self.write("outputs/resumes/general.tex", RESUME)
        code, out = self.run_tool("start", "--name", "backend", "--from", "general")
        self.assertEqual((code, out), (0, ["copied: outputs/resumes/general.tex -> .build/drafts/backend/resume.tex"]))
        self.write(".build/drafts/backend/resume.tex", RESUME + "% edited\n")
        code, out = self.run_tool("start", "--name", "backend", "--from", "general")
        self.assertEqual(code, 1)
        self.assertTrue(out[0].startswith("kept:"))
        self.assertEqual(self.run_tool("start", "--name", "backend", "--from", "general", "--replace")[0], 0)
        self.write("skills/career-log/examples/resume.tex", RESUME)
        self.assertEqual(self.run_tool("start", "--name", "x", "--from", "skills/career-log/examples/resume.tex")[0], 2)


class Save(Base):
    NAME = "2026-03-02-acme-backend-engineer"

    def draft(self, tex=RESUME, pdf=b"%PDF-1.4 one"):
        self.write(".build/drafts/%s/resume.tex" % self.NAME, tex)
        self.write(".build/drafts/%s/resume.pdf" % self.NAME, pdf, binary=True)
        self.write(".build/drafts/%s/posting.md" % self.NAME, "https://example.com/job\n")

    def test_application(self):
        self.draft()
        code, out = self.run_tool("save", "--application", self.NAME)
        self.assertEqual(code, 0, out)
        folder = "outputs/applications/" + self.NAME
        self.assertEqual(out[-1], "copied: .build/drafts/%s/posting.md -> %s/posting.md" % (self.NAME, folder))
        self.assertEqual(self.read(folder + "/resume.tex"), RESUME)

    def test_sent_folder_is_frozen(self):
        self.draft()
        self.run_tool("save", "--application", self.NAME)
        self.commit("save")
        self.assertEqual(self.run_tool("save", "--application", self.NAME)[0], 0)   # the same content again
        self.draft(tex=RESUME + "% later\n")
        code, out = self.run_tool("save", "--application", self.NAME)
        self.assertEqual(code, 1)
        self.assertIn("frozen", out[0])

    def test_target_overwrites_and_missing_pdf(self):
        self.write(".build/drafts/backend/resume.tex", RESUME)
        code, out = self.run_tool("save", "--target", "backend")
        self.assertEqual(code, 1)
        self.assertIn("no resume.pdf", out[0])
        self.write(".build/drafts/backend/resume.pdf", b"%PDF", binary=True)
        self.write("outputs/resumes/backend.tex", "old\n")
        self.commit("old")
        self.assertEqual(self.run_tool("save", "--target", "backend")[0], 0)
        self.assertEqual(self.read("outputs/resumes/backend.tex"), RESUME)


class Level(Base):
    FOLDER = "outputs/applications/2026-02-01-acme-platform-engineer"

    def setUp(self):
        super().setUp()
        self.folder("2026-02-01-acme-platform-engineer")
        self.write("entries/2025-06-queue.md", ENTRY.replace(
            "(applications/2026-02-01-acme-platform-engineer)\n",
            "(outputs/applications/2026-02-01-acme-platform-engineer)\n"
            "- **general:** \"Built a job queue in Go\" (applications/2026-02-01-acme-platform-engineer)\n"
            "- **general:** \"Built a job queue in Rust\" (applications/2026-02-01-acme-platform-engineer-2)\n"))
        self.write("stories.md", STORIES)
        self.commit("write(acme): Platform Engineer")

    def test_to_archived(self):
        code, out = self.run_tool("level", self.FOLDER, "archived", "--today", "2026-03-02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(self.FOLDER + "/archived.md"), "Archived (user, 2026-03-02)\n")
        entry = self.read("entries/2025-06-queue.md")
        self.assertNotIn("platform-engineer)", entry)
        self.assertIn("platform-engineer-2)", entry)   # another folder whose name starts the same
        self.assertIn("2026-01-05-acme-backend-engineer", entry)
        self.assertEqual(sum(l.startswith("removed: entries/") for l in out), 2)
        stories = self.read("stories.md")
        self.assertIn("| Biggest challenge | per-angle | entries | - | general: [answer](outputs/reports/2026-01-01-challenge.md) |",
                      stories)
        self.assertIn("| About you | shared | profile | - | |", stories)
        self.assertEqual(out[-2], "files: %s/archived.md entries/2025-06-queue.md stories.md" % self.FOLDER)
        self.assertEqual(out[-1], "commit: write(acme): Platform Engineer to Archived")
        self.assertEqual(self.run_tool("level", self.FOLDER, "archived")[1],
                         ["unchanged: %s is already Archived" % self.FOLDER])

    def test_to_reference(self):
        self.run_tool("level", self.FOLDER, "archived", "--today", "2026-03-02")
        self.commit("write(acme): Platform Engineer to Archived")
        code, out = self.run_tool("level", self.FOLDER + "/", "reference")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.exists(self.FOLDER + "/archived.md"))
        self.assertTrue(out[1].startswith("feed: "), out)
        self.assertIn("answer: Biggest challenge | %s/answers.md" % self.FOLDER, out)
        self.assertEqual(out[-1], "commit: write(acme): Platform Engineer to Reference")

    def test_bullets_report(self):
        rel = "outputs/reports/2026-03-01-bullets.md"
        self.write(rel, "Kind: resume bullets\n\n- Built a queue\n\n| Claim | Entry section | Source |\n|---|---|---|\n")
        code, out = self.run_tool("level", rel, "archived", "--today", "2026-03-02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(rel).splitlines()[:2], ["Kind: resume bullets", "Archived (user, 2026-03-02)"])
        self.assertEqual(out[-1], "commit: write(2026-03-01-bullets): resume bullets to Archived")
        self.run_tool("level", rel, "reference")
        self.assertNotIn("Archived", self.read(rel))

    def test_subject_from_the_first_write_commit_else_the_folder(self):
        rel = self.folder("2026-01-10-globex-sre")
        self.commit("scan(2026-01-09): accepted")
        self.assertEqual(self.run_tool("level", rel, "archived")[1][-1], "commit: write(2026-01-10-globex-sre): application to Archived")
        self.git("reset", "-q", "--hard")
        self.git("clean", "-fdq")
        self.write(rel + "/answers.md", ANSWERS + "\n")
        self.commit("write(globex): SRE")
        self.assertEqual(self.run_tool("level", rel, "archived")[1][-1], "commit: write(globex): SRE to Archived")

    def test_not_a_bullets_report(self):
        rel = "outputs/reports/2026-03-01-bio.md"
        self.write(rel, "Kind: bio\n\nText\n")
        self.assertEqual(self.run_tool("level", rel, "archived")[0], 2)


class Sent(Base):
    def setUp(self):
        super().setUp()
        self.write("outputs/resumes/general.tex", RESUME)
        self.write("outputs/resumes/general.pdf", b"%PDF one", binary=True)
        self.commit("v1", date="2026-03-01T09:00:00")
        self.v1 = self.git("rev-parse", "HEAD").strip()
        self.write("outputs/resumes/general.tex", RESUME + "% v2\n")
        self.commit("v2", date="2026-03-01T15:00:00")
        self.v2 = self.git("rev-parse", "HEAD").strip()

    def test_cell_github_and_bare(self):
        _, out = self.run_tool("sent", "general")
        self.assertEqual(out, ["version: %s:outputs/resumes/general.tex" % self.v2, "cell: %s" % self.v2[:7]])
        self.git("remote", "add", "origin", "git@github.com:someone/log.git")
        _, out = self.run_tool("sent", "general")
        self.assertEqual(out[1], "cell: [general @ %s](https://github.com/someone/log/blob/%s/outputs/resumes/general.pdf)"
                         % (self.v2[:7], self.v2))

    def test_uncommitted_changes_refuse(self):
        self.write("outputs/resumes/general.tex", "edited\n")
        code, out = self.run_tool("sent", "general")
        self.assertEqual(code, 1)
        self.assertIn("uncommitted", out[0])

    def test_before_and_the_same_day(self):
        _, out = self.run_tool("sent", "general", "--before", "2026-03-01 12:00")
        self.assertEqual(out[0], "version: %s:outputs/resumes/general.tex" % self.v1)
        self.assertIn("changed that day: 2 commits", out)
        _, out = self.run_tool("sent", "general", "--before", "2026-03-02")
        self.assertEqual(out[0], "version: %s:outputs/resumes/general.tex" % self.v2)
        self.assertIn("changed that day: 0 commits", out)

    def test_record(self):
        folder = "outputs/applications/2026-03-05-acme-backend-engineer"
        code, out = self.run_tool("sent", "general", "--record", folder)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(folder + "/sent-version.md"), "%s:outputs/resumes/general.tex\n" % self.v2)
        code, _ = self.run_tool("sent", "general", "--before", "2026-03-01 12:00", "--record", folder)
        self.assertEqual(code, 1)


class SentShow(Sent):
    def test_forms(self):
        cell = "[general @ %s](https://github.com/someone/log/blob/%s/outputs/resumes/general.pdf)" % (self.v1[:7], self.v1)
        for ref in (cell, "https://github.com/someone/log/blob/%s/outputs/resumes/general.pdf" % self.v1,
                    "%s:outputs/resumes/general.tex" % self.v1):
            code, out = self.run_tool("sent-show", ref)
            self.assertEqual((code, out[0]), (0, "version: %s:outputs/resumes/general.tex" % self.v1), ref)
            self.assertNotIn("% v2", "\n".join(out))
        code, out = self.run_tool("sent-show", self.v2[:7], "--target", "general")
        self.assertIn("% v2", "\n".join(out))
        self.assertEqual(self.run_tool("sent-show", self.v2[:7])[0], 2)
        _, out = self.run_tool("sent-show", "Gave them the resume, sent %s" % self.v1[:7], "--target", "general")
        self.assertEqual(out[0], "version: %s:outputs/resumes/general.tex" % self.v1)   # a row written in words
        _, out = self.run_tool("sent-show", "Req 4512398, sent %s" % self.v1[:7], "--target", "general")
        self.assertEqual(out[0], "version: %s:outputs/resumes/general.tex" % self.v1)   # another number first

    def test_out_bytes_and_folder(self):
        dest = os.path.join(self.tmp, "sent.tex")
        folder = "outputs/applications/2026-03-05-acme-backend-engineer"
        self.run_tool("sent", "general", "--before", "2026-03-01 12:00", "--record", folder)
        code, out = self.run_tool("sent-show", folder, "--out", dest)
        self.assertEqual(code, 0, out)
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), RESUME.encode())

    def test_missing_path_lists_what_it_touched(self):
        self.git("mv", "outputs/resumes/general.tex", "outputs/resumes/backend.tex")
        self.commit("rename")
        h = self.git("rev-parse", "HEAD").strip()
        code, out = self.run_tool("sent-show", h[:7], "--target", "general")
        self.assertEqual(code, 1)
        self.assertIn("touched: outputs/resumes/backend.tex", out)


class Risks(Base):
    def test_where_the_section_is(self):
        rel = self.folder("2026-02-01-acme-platform-engineer")
        _, out = self.run_tool("risks", rel)
        self.assertEqual(out, ["risks: %s/provenance.md" % rel, "- The 820 ms baseline was a staging number."])
        report = "outputs/reports/2026-03-01-bullets.md"
        self.write(report, "Kind: resume bullets\n\n- x\n\n| a | entry |\n|---|---|\n\n## Risks to handle in conversation\n- One run.\n")
        self.assertEqual(self.run_tool("risks", report)[1], ["risks: %s" % report, "- One run."])
        self.write("outputs/resumes/general.md", "# General\n")
        self.assertTrue(self.run_tool("risks", "outputs/resumes/general.md")[1][0].startswith("risks: none"))

    def test_sent_version_folder(self):
        self.write("outputs/resumes/general.md", "# General\n\n" + PROVENANCE)
        self.write("outputs/resumes/general.tex", RESUME)
        self.commit("v1")
        h = self.git("rev-parse", "HEAD").strip()
        self.write("outputs/resumes/general.md", "# General\n")
        self.commit("v2")
        folder = "outputs/applications/2026-03-05-acme-backend-engineer"
        self.write(folder + "/sent-version.md", "%s:outputs/resumes/general.tex\n" % h)
        _, out = self.run_tool("risks", folder)
        self.assertEqual(out, ["risks: %s:outputs/resumes/general.md" % h, "- The 820 ms baseline was a staging number."])


class Phrasings(Base):
    FOLDER = "outputs/applications/2026-03-02-acme-backend-engineer"

    def setUp(self):
        super().setUp()
        self.folder("2026-03-02-acme-backend-engineer")
        self.write("entries/2025-06-queue.md", ENTRY)

    def test_preview(self):
        code, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-06-queue.md", "--angle", "backend")
        self.assertEqual(code, 0, out)
        self.assertEqual(out[0], "bullet 1: Cut quote API p95 latency from 820 ms to 210 ms with a Redis rate cache")
        self.assertTrue(out[1].startswith("  entries/2025-06-queue.md: 0."), out)
        self.assertEqual(out[2], "bullet 2: **Queue:** Built a Go job queue on PostgreSQL for 40% of traffic")
        self.assertIn("cite: %s" % self.FOLDER, out)
        self.assertEqual(out[-1], "entry: entries/2025-06-queue.md: 2 lines for backend")
        _, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-06-queue.md", "--angle", "ml")
        self.assertEqual(out[1], "  entries/2025-06-queue.md: none for ml")

    def test_target_cite_and_draft(self):
        self.write("outputs/resumes/backend.md", "# Backend\n")
        self.write("outputs/resumes/backend.tex", RESUME)
        _, out = self.run_tool("phrasings", "outputs/resumes/backend.md", "--angle", "backend", "--today", "2026-03-02")
        self.assertIn("cite: outputs/resumes/backend.tex, 2026-03-02", out)
        self.write(".build/drafts/backend/resume.tex", RESUME)
        _, out = self.run_tool("phrasings", ".build/drafts/backend/resume.tex", "--angle", "backend")
        self.assertTrue(out[-1].startswith("cite: (the saved output"))
        self.write(".build/drafts/bullets/bullets.md", "- Built a queue\n- Ran it\n")
        _, out = self.run_tool("phrasings", ".build/drafts/bullets/bullets.md", "--angle", "backend")
        self.assertEqual(out[:2], ["bullet 1: Built a queue", "bullet 2: Ran it"])

    def test_add_through_phrasing_add(self):
        code, out = self.run_tool("phrasings", self.FOLDER, "--angle", "backend", "--add", "2=entries/2025-06-queue.md")
        self.assertEqual(code, 0, out)
        self.assertEqual(out[-1], 'line: entries/2025-06-queue.md:10: - **backend:** "**Queue:** Built a Go job queue on'
                         ' PostgreSQL for 40% of traffic" (' + self.FOLDER + ')')
        self.assertIn('- **backend:** "**Queue:** Built a Go job queue on PostgreSQL for 40% of traffic" (' + self.FOLDER + ')',
                      self.read("entries/2025-06-queue.md"))
        code, out = self.run_tool("phrasings", self.FOLDER, "--angle", "backend", "--add", "1=entries/2025-06-queue.md")
        self.assertEqual(code, 1, out)   # phrasing-add: near an existing wording, the agent decides
        self.assertTrue(any(l.startswith("similar:") for l in out), out)
        code, out = self.run_tool("phrasings", self.FOLDER, "--angle", "backend", "--add", "1=entries/2025-06-queue.md,distinct")
        self.assertEqual(code, 0, out)

    def test_archived_and_bullets_report(self):
        self.write(self.FOLDER + "/archived.md", "Archived (user, 2026-03-02)\n")
        _, out = self.run_tool("phrasings", self.FOLDER, "--angle", "backend")
        self.assertTrue(out[0].startswith("archived:"))
        rel = "outputs/reports/2026-03-01-bullets.md"
        self.write(rel, "Kind: resume bullets\n\n- Built a queue\n\n| Claim | Entry section | Source |\n|---|---|---|\n")
        _, out = self.run_tool("phrasings", rel, "--angle", "general")
        self.assertEqual(out[:1] + out[-1:], ["bullet 1: Built a queue", "cite: %s" % rel])
        self.write("outputs/reports/2026-03-01-bio.md", "Kind: bio\n\nText\n")
        self.assertEqual(self.run_tool("phrasings", "outputs/reports/2026-03-01-bio.md", "--angle", "general")[0], 2)

    def test_cap_keeps_the_two_ranked_first(self):
        self.run_tool("phrasings", self.FOLDER, "--angle", "backend", "--add", "1=entries/2025-06-queue.md,distinct")
        lines = self.read("entries/2025-06-queue.md").splitlines()
        n = [i for i, l in enumerate(lines, 1) if l.startswith("- **backend:**")]
        self.assertEqual(len(n), 3)
        code, out = self.run_tool("phrasings", "--angle", "backend", "--cap", "entries/2025-06-queue.md=" + ",".join(map(str, n)))
        self.assertEqual(code, 0, out)
        self.assertEqual([l for l in out if not l.startswith("line: ")], [out[0]])
        self.assertTrue(out[0].startswith("dropped: "), out)
        self.assertIn("sources/resumes/2025-09-draft.tex", out[0])   # the imported one goes first
        self.assertEqual(len([l for l in out if l.startswith("line: entries/2025-06-queue.md:")]), 2)   # renumbered
        text = self.read("entries/2025-06-queue.md")
        self.assertNotIn("2025-09-draft", text)
        self.assertIn("2026-01-05-acme-backend-engineer", text)
        self.assertEqual(self.run_tool("phrasings", "--angle", "backend", "--cap", "entries/2025-06-queue.md=1,2")[0], 2)



class BelowTheTopLevel(Base):
    """A Log in a folder of a bigger repository: git paths are read from the Log's root."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "repo")
        self.root = os.path.join(self.repo, "career")
        os.makedirs(self.root)
        subprocess.run(["git", "-C", self.repo, "init", "-q"], check=True, capture_output=True)
        self.write("outputs/resumes/general.tex", RESUME)
        self.write("outputs/resumes/general.md", "# General\n\n" + PROVENANCE)
        self.write("outputs/resumes/general.pdf", b"%PDF", binary=True)
        self.commit("v1")
        self.v1 = self.git("rev-parse", "HEAD").strip()

    def test_sent_show_risks_and_cell(self):
        folder = "outputs/applications/2026-03-05-acme-backend-engineer"
        self.assertEqual(self.run_tool("sent", "general", "--record", folder)[0], 0)
        code, out = self.run_tool("sent-show", folder)
        self.assertEqual(code, 0, out)
        self.assertIn(r"\begin{itemize}", "\n".join(out))
        self.assertEqual(self.run_tool("risks", folder)[1][1], "- The 820 ms baseline was a staging number.")
        self.git("remote", "add", "origin", "https://github.com/someone/log.git")
        cell = self.run_tool("sent", "general")[1][1][len("cell: "):]
        self.assertIn("/blob/%s/career/outputs/resumes/general.pdf" % self.v1, cell)
        code, out = self.run_tool("sent-show", cell)   # the cell sent wrote reads back
        self.assertEqual((code, out[0]), (0, "version: %s:outputs/resumes/general.tex" % self.v1), out)

    def test_save_keeps_a_sent_folder_frozen(self):
        name = "2026-03-02-acme-backend-engineer"
        self.write(".build/drafts/%s/resume.tex" % name, RESUME)
        self.write(".build/drafts/%s/resume.pdf" % name, b"%PDF", binary=True)
        self.run_tool("save", "--application", name)
        self.commit("save")
        self.write(".build/drafts/%s/resume.tex" % name, RESUME + "% later\n")
        self.assertEqual(self.run_tool("save", "--application", name)[0], 1)


class Edges(Base):
    def test_commented_line_and_per_company_pointer(self):
        rel = self.folder("2026-02-01-acme-platform-engineer")
        self.write("entries/2025-06-queue.md", ENTRY.replace("## Past phrasings\n", "## Past phrasings\n<!--\n"
                   '- **backend:** "An example" (outputs/applications/2026-02-01-acme-platform-engineer)\n-->\n'))
        self.write("stories.md", STORIES.replace("| Why this company | per-company | entries | - | |",
                   "| Why this company | per-company | entries | - | [answer](%s/answers.md) |" % rel))
        self.commit("write(acme): Platform Engineer")
        _, out = self.run_tool("level", rel, "archived")
        self.assertIn("An example", self.read("entries/2025-06-queue.md"))
        self.assertFalse(any("per-company" in l for l in out), out)
        self.assertEqual(len([l for l in out if l.startswith("removed: entries/")]), 1)

    def test_cap_names_a_line_twice(self):
        self.write("entries/2025-06-queue.md", ENTRY)
        self.assertEqual(self.run_tool("phrasings", "--angle", "backend", "--cap", "entries/2025-06-queue.md=7,7,8")[0], 2)
        self.assertEqual(self.read("entries/2025-06-queue.md"), ENTRY)

    def test_since_counts_the_whole_day(self):
        self.folder("2026-02-01-acme-platform-engineer")
        self.commit("save", date="2026-01-20T12:00:00")
        self.write("entries/x.md", "x\n")
        self.commit("early", date="2026-02-01T00:30:00")
        _, out = self.run_tool("prior", "acme", "--type", "Why this company")
        self.assertIn("since 2026-02-01: 1 commits", out)


if __name__ == "__main__":
    unittest.main()
