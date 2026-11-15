#!/usr/bin/env python3
"""Tests for tools/application.py, on small Logs built in a temporary git repository.

  python3 -I tools/tests/test_application.py
"""
import contextlib, datetime, email, email.message, email.policy, importlib.util, io, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from unittest import mock

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
        self.assertIn("since 2025-10-01: 1 commit", out)   # an untyped candidate's date too
        self.assertFalse(any(l.startswith(("since 2025-11-03", "since 2025-09-01")) for l in out), out)
        since = out.index("since 2026-02-01: 1 commit")
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

    def test_fallback_in_a_root_with_glob_characters(self):
        root = os.path.join(self.tmp, "log [1]")
        os.makedirs(os.path.join(root, "sources", "resumes"))
        with open(os.path.join(root, "sources", "resumes", "2025-01-01-main.tex"), "w", encoding="utf-8") as f:
            f.write(RESUME)
        self.assertEqual(application.fallback(root), "sources/resumes/2025-01-01-main.tex")

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

    # ---- the starting point a posting run records, for Next up (#614) ----

    def roles(self, *roles):
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n"
                   + "".join("%d. %s (user, 2026-01-01)\n" % (i, r) for i, r in enumerate(roles, 1)))

    def test_records_the_start_family_and_tier(self):
        self.roles("Backend engineer", "Platform engineer")
        self.write("outputs/resumes/backend.tex", RESUME)
        code, out = self.run_tool("start", "--name", "n", "--from", "backend", "--family", "backend", "--tier", "1")
        self.assertEqual(code, 0, out)
        self.assertEqual(out[-1], "recorded: .build/drafts/n/start.txt")
        self.assertEqual(application.logfiles.start_record(self.root, "n"),
                         {"from": "outputs/resumes/backend.tex", "family": "backend", "tier": "1"})
        self.write("sources/resumes/2025-01-01-main.tex", RESUME)   # a role outside Direction, from the fallback
        code, out = self.run_tool("start", "--name", "m", "--from", "sources/resumes/2025-01-01-main.tex",
                                  "--family", "pm", "--tier", "none")
        self.assertEqual(code, 0, out)
        self.assertEqual(application.logfiles.start_record(self.root, "m"),
                         {"from": "sources/resumes/2025-01-01-main.tex", "family": "pm", "tier": "none"})

    def test_no_record_without_family(self):
        self.write("outputs/resumes/general.tex", RESUME)
        self.assertEqual(self.run_tool("start", "--name", "t", "--from", "general")[0], 0)
        self.assertIsNone(application.logfiles.start_record(self.root, "t"))

    def test_family_general_only_while_target_roles_are_empty(self):
        self.write("outputs/resumes/general.tex", RESUME)
        code, out = self.run_tool("start", "--name", "a", "--from", "general", "--family", "general", "--tier", "none")
        self.assertEqual(code, 0, out)   # no target roles: the one family is general
        for family, tier in (("backend", "none"), ("general", "1")):
            code, _ = self.run_tool("start", "--name", "b", "--from", "general", "--family", family, "--tier", tier)
            self.assertEqual(code, 2, (family, tier))
        self.roles("Backend engineer")
        for family, tier in (("general", "none"), ("backend", "2"), ("backend", "x"), ("Back End", "1")):
            code, _ = self.run_tool("start", "--name", "c", "--from", "general", "--family", family, "--tier", tier)
            self.assertEqual(code, 2, (family, tier))
        self.assertEqual(self.run_tool("start", "--name", "c", "--from", "general", "--family", "backend")[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build", "drafts", "c")))


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
        self.commit("write(2026-03-01-bullets): resume bullets")
        code, out = self.run_tool("level", rel, "archived", "--today", "2026-03-02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(rel).splitlines()[:2], ["Kind: resume bullets", "Archived (user, 2026-03-02)"])
        self.assertEqual(out[-1], "commit: write(2026-03-01-bullets): resume bullets to Archived")
        self.run_tool("level", rel, "reference")
        self.assertNotIn("Archived", self.read(rel))

    def test_archived_save_not_yet_committed(self):
        """An Archived save writes its marker before the save's own commit (write › Save levels):
        no files: or commit: line for a level commit, which would split the save in two."""
        rel = "outputs/reports/2026-03-01-bullets.md"
        self.write(rel, "Kind: resume bullets\n\n- Built a queue\n")
        code, out = self.run_tool("level", rel, "archived", "--today", "2026-03-02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(rel).splitlines()[:2], ["Kind: resume bullets", "Archived (user, 2026-03-02)"])
        self.assertEqual(out, ["wrote: %s: Archived (user, 2026-03-02)" % rel,
                               "not committed: %s has no commit yet: the save's own commit takes the marker"
                               " (write step 10's Save and commit)" % rel])
        rel = self.folder("2026-01-10-globex-sre")   # a new folder: archived.md beside its files
        code, out = self.run_tool("level", rel, "archived", "--today", "2026-03-02")
        self.assertEqual((code, out[0], out[-1].split(":")[0]), (0, "wrote: %s/archived.md" % rel, "not committed"), out)

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

    def test_before_one_commit_that_day(self):
        self.write("outputs/resumes/general.tex", RESUME + "% v3\n")
        self.commit("v3", date="2026-03-04T10:00:00")
        _, out = self.run_tool("sent", "general", "--before", "2026-03-04")
        self.assertIn("changed that day: 1 commit", out)

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


class SentCandidates(Base):
    """A resume sent before the Log had any target: two imported resumes in sources/resumes."""
    FOLDER = "outputs/applications/2025-10-15-acme-backend-engineer"

    def setUp(self):
        super().setUp()
        self.write("sources/resumes/2025-09-28-fair.tex", RESUME)
        self.write("sources/resumes/2025-10-02-online.tex", RESUME.replace("40\\%", "45\\%"))
        self.write("sources/resumes/2025-11-01-later.tex", RESUME + "% later\n")
        self.commit("import")
        self.imp = self.git("rev-parse", "HEAD").strip()
        self.write("outputs/resumes/backend-infra.tex", RESUME)
        self.commit("target", date="2025-10-20T09:00:00")
        self.fair = "%s:sources/resumes/2025-09-28-fair.tex" % self.imp
        self.online = "%s:sources/resumes/2025-10-02-online.tex" % self.imp

    def test_lists_both_newest_first_with_their_diff(self):
        code, out = self.run_tool("sent-candidates", "--before", "2025-10-15")
        self.assertEqual(code, 0, out)
        self.assertIn("targets: none saved by 2025-10-15", out)
        cands = [l for l in out if l.startswith("candidate: ")]
        self.assertEqual(cands, ["candidate: %s | 2025-10-02" % self.online, "candidate: %s | 2025-09-28" % self.fair])
        i = out.index("diff: sources/resumes/2025-09-28-fair.tex -> sources/resumes/2025-10-02-online.tex: 1 line differs")
        self.assertEqual(out[i + 1:i + 3], ["- " + RESUME.splitlines()[4],
                                             "+ " + RESUME.splitlines()[4].replace("40\\%", "45\\%")])
        self.assertEqual(out[-1].split(":")[0], "next")

    def test_a_target_saved_by_then_is_named(self):
        _, out = self.run_tool("sent-candidates", "--before", "2025-10-21")
        self.assertIn("targets saved by 2025-10-21: backend-infra (2025-10-20)", out)

    def test_none_and_uncommitted(self):
        code, out = self.run_tool("sent-candidates", "--before", "2025-01-01")
        self.assertEqual(code, 1)
        self.assertTrue(out[-1].startswith("none: no file in sources/resumes/ dated on or before 2025-01-01"), out)
        self.write("sources/resumes/2025-09-30-new.tex", RESUME)
        _, out = self.run_tool("sent-candidates", "--before", "2025-10-01")
        self.assertIn("candidate: sources/resumes/2025-09-30-new.tex | 2025-09-30 | uncommitted: commit it first", out)

    def test_limit(self):
        _, out = self.run_tool("sent-candidates", "--before", "2025-12-01", "--limit", "1")
        self.assertEqual([l for l in out if l.startswith("candidate: ")],
                         ["candidate: %s:sources/resumes/2025-11-01-later.tex | 2025-11-01" % self.imp])
        self.assertIn("older: 2 more (--limit 3 shows them)", out)

    def test_a_utc_time_takes_this_machines_date(self):
        stamp = "2025-10-02T06:30:00Z"   # an export's UTC timestamp
        local = application.datetime.datetime.fromisoformat("2025-10-02T06:30:00+00:00").astimezone().date().isoformat()
        _, out = self.run_tool("sent-candidates", "--before", stamp)
        self.assertEqual(out[0], "before: %s (%s in this machine's time zone)" % (local, stamp))
        self.assertEqual(any("2025-10-02-online" in l for l in out if l.startswith("candidate: ")), local >= "2025-10-02")

    def test_local_when(self):
        when = application.local_when
        self.assertEqual(when("2025-10-02"), ("2025-10-02", None))
        self.assertEqual(when("2025-10-02 9:05"), ("2025-10-02", "9:05"))
        for stamp, offset in (("2025-10-02T23:30:00-08:00", -8), ("2025-10-02 07:30+05:30", 5.5)):
            tz = application.datetime.timezone(application.datetime.timedelta(hours=offset))
            dt = application.datetime.datetime.fromisoformat(stamp.replace(" ", "T")).replace(tzinfo=tz).astimezone()
            self.assertEqual(when(stamp), (dt.date().isoformat(), dt.strftime("%H:%M:%S")), stamp)
        with self.assertRaises(application.AppError):
            when("Oct 2")

    def test_record_two_candidates_and_show_both(self):
        code, out = self.run_tool("sent-show", self.fair, self.online, "--record", self.FOLDER,
                                  "--known", "paper copy at the fair was the first; the online upload was one of the two",
                                  "--today", "2026-11-13")
        self.assertEqual(code, 0, out)
        text = self.read(self.FOLDER + "/sent-version.md")
        self.assertTrue(text.startswith("%s\n%s\n\nKnown: paper copy at the fair was the first; the online upload was"
                                        " one of the two (user, 2026-11-13)\n" % (self.fair, self.online)), text)
        self.assertIn("40\\%", text.split("Differ:", 1)[1])
        code, out = self.run_tool("sent-show", self.FOLDER)
        self.assertEqual(code, 0, out)
        self.assertEqual(out[0], "candidates: 2")
        self.assertTrue(out[1].startswith("known: paper copy"), out)
        self.assertIn("version: %s" % self.fair, out)
        self.assertIn("version: %s" % self.online, out)
        i = out.index("differ: sources/resumes/2025-09-28-fair.tex -> sources/resumes/2025-10-02-online.tex: 1 line differs")
        self.assertTrue(out[i + 1].startswith("- ") and "40\\%" in out[i + 1], out[i + 1])
        self.assertTrue(self.run_tool("risks", self.FOLDER)[1][0].startswith("risks: none"))
        # the same pair again keeps the file; another set is refused
        self.assertEqual(self.run_tool("sent-show", self.online, self.fair, "--record", self.FOLDER, "--known", "x")[0], 0)
        self.assertEqual(self.read(self.FOLDER + "/sent-version.md"), text)
        self.assertEqual(self.run_tool("sent-show", self.fair, "--record", self.FOLDER)[0], 1)

    def test_an_imported_pdf(self):
        self.write("sources/resumes/2025-09-29-handout.pdf", b"%PDF-1.5 handout", binary=True)
        self.commit("pdf")
        pdf = "%s:sources/resumes/2025-09-29-handout.pdf" % self.git("rev-parse", "HEAD").strip()
        _, out = self.run_tool("sent-candidates", "--before", "2025-09-30")
        self.assertIn("candidate: %s | 2025-09-29" % pdf, out)
        self.assertIn("diff: sources/resumes/2025-09-28-fair.tex -> sources/resumes/2025-09-29-handout.pdf: not text", out)
        code, out = self.run_tool("sent-show", pdf, self.fair, "--record", self.FOLDER, "--known", "one of these")
        self.assertEqual(code, 0, out)
        self.assertIn("binary: 16 bytes: open it with sent-show %s --out <file>" % pdf, out)
        self.assertTrue(self.run_tool("risks", self.FOLDER)[1][0].startswith("risks: none"))
        dest = os.path.join(self.tmp, "h.pdf")
        self.assertEqual(self.run_tool("sent-show", pdf, "--out", dest)[0], 0)

    def test_a_bad_time_fails_cleanly(self):
        for bad in ("2025-10-02T25:00Z", "2025-02-30", "2025-10-02 9:61"):
            code, out = self.run_tool("sent-candidates", "--before", bad)
            self.assertEqual(code, 2, (bad, out))
            self.assertTrue(out[0].startswith("FAIL: --before is not a real date and time"), out)

    def test_record_from_a_folder_keeps_what_is_known(self):
        self.run_tool("sent-show", self.fair, self.online, "--record", self.FOLDER, "--known", "one of the two",
                      "--today", "2026-11-13")
        other = "outputs/applications/2025-10-15-acme-platform-engineer"
        self.assertEqual(self.run_tool("sent-show", self.FOLDER, "--record", other)[0], 0)
        self.assertIn("Known: one of the two (user, 2026-11-13)\n", self.read(other + "/sent-version.md"))

    def test_several_need_known_and_no_out(self):
        self.assertEqual(self.run_tool("sent-show", self.fair, self.online, "--record", self.FOLDER)[0], 2)
        self.assertFalse(self.exists(self.FOLDER + "/sent-version.md"))
        self.assertEqual(self.run_tool("sent-show", self.fair, self.online, "--out", os.path.join(self.tmp, "x"))[0], 2)

    def test_one_version_folder_reads_as_before(self):
        self.write(self.FOLDER + "/sent-version.md", self.fair + "\n")
        code, out = self.run_tool("sent-show", self.FOLDER)
        self.assertEqual(out, ["version: %s" % self.fair] + RESUME.rstrip("\n").split("\n"))
        self.assertEqual(code, 0)


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

    def test_several_candidates_print_the_lines_where_they_differ(self):
        self.write("outputs/resumes/general.md", "# General\n\n" + PROVENANCE)
        self.write("outputs/resumes/general.tex", RESUME)
        self.commit("v1")
        a = self.git("rev-parse", "HEAD").strip()
        self.write("outputs/resumes/general.tex", RESUME.replace("820 ms to 210 ms", "800 ms to 200 ms")
                   .replace("40\\%", "half"))
        self.commit("v2")
        b = self.git("rev-parse", "HEAD").strip()
        folder = "outputs/applications/2026-03-05-acme-backend-engineer"
        va, vb = "%s:outputs/resumes/general.tex" % a, "%s:outputs/resumes/general.tex" % b
        self.write(folder + "/sent-version.md", "%s\n%s\n\nKnown: one of the two (user, 2026-03-05)\n" % (va, vb))
        code, out = self.run_tool("risks", folder)
        self.assertEqual(code, 0, out)
        self.assertEqual(out[:2], ["risks: %s:outputs/resumes/general.md" % a, "- The 820 ms baseline was a staging number."])
        self.assertEqual(out[2:], [
            "candidates: 2: the brief covers each `line` below, with the versions that hold it",
            "known: one of the two (user, 2026-03-05)",
            "version 1: %s" % va, "version 2: %s" % vb,
            "differ: 4 lines not in every version",
            "line (version 1):   \\item Cut quote API p95 latency from 820 ms to 210 ms with a Redis rate cache",
            "line (version 1):   \\item \\textbf{Queue:} Built a Go job queue on PostgreSQL for 40\\% of traffic",
            "line (version 2):   \\item Cut quote API p95 latency from 800 ms to 200 ms with a Redis rate cache",
            "line (version 2):   \\item \\textbf{Queue:} Built a Go job queue on PostgreSQL for half of traffic"])
        # three candidates: a line two of them hold names both
        self.write(folder + "/sent-version.md", "%s\n%s\n%s\n\nKnown: x (user, 2026-03-05)\n" % (va, vb, va))
        _, out = self.run_tool("risks", folder)
        self.assertIn("line (versions 1, 3):   \\item Cut quote API p95 latency from 820 ms to 210 ms with a Redis rate cache", out)
        self.assertIn("line (version 2):   \\item Cut quote API p95 latency from 800 ms to 200 ms with a Redis rate cache", out)
        # with no Risks section in any candidate, the lines still print; the same lines say so
        self.write("outputs/resumes/general.md", "# General\n")
        self.commit("v3")
        c = self.git("rev-parse", "HEAD").strip()
        vc = "%s:outputs/resumes/general.tex" % c
        self.write(folder + "/sent-version.md", "%s\n%s\n\nKnown: x (user, 2026-03-05)\n" % (vc, vc))
        _, out = self.run_tool("risks", folder)
        self.assertTrue(out[0].startswith("risks: none"), out)
        self.assertEqual(out[-1], "differ: none: the versions hold the same lines")
        # an imported .pdf is not compared, and says how to read it
        self.write("sources/resumes/2025-09-29-handout.pdf", b"%PDF-1.5 handout", binary=True)
        self.commit("pdf")
        pdf = "%s:sources/resumes/2025-09-29-handout.pdf" % self.git("rev-parse", "HEAD").strip()
        self.write(folder + "/sent-version.md", "%s\n%s\n\nKnown: x (user, 2026-03-05)\n" % (vc, pdf))
        _, out = self.run_tool("risks", folder)
        self.assertIn("not text: version 2: read its claims from sent-show %s --out <file>" % pdf, out)
        self.assertEqual(out[-1], "differ: not compared: fewer than two versions are text")


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
        self.assertEqual(out[2], "  same: entries/2025-06-queue.md:7: adds no line")
        self.assertEqual(out[3], "bullet 2: **Queue:** Built a Go job queue on PostgreSQL for 40% of traffic")
        self.assertIn("cite: %s" % self.FOLDER, out)
        self.assertEqual(out[-2:], ["entry: entries/2025-06-queue.md: 2 lines for backend", "adds: --add 2=entries/2025-06-queue.md"])
        _, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-06-queue.md", "--angle", "ml")
        self.assertEqual(out[1], "  entries/2025-06-queue.md: none for ml")

    def test_target_cite_and_draft(self):
        self.write("outputs/resumes/backend.md", "# Backend\n")
        self.write("outputs/resumes/backend.tex", RESUME)
        _, out = self.run_tool("phrasings", "outputs/resumes/backend.md", "--angle", "backend", "--today", "2026-03-02")
        self.assertIn("cite: outputs/resumes/backend.tex, 2026-03-02", out)
        self.write(".build/drafts/backend/resume.tex", RESUME)
        _, out = self.run_tool("phrasings", ".build/drafts/backend/resume.tex", "--angle", "backend")
        self.assertTrue(out[-2].startswith("cite: (the saved output"))
        self.write(".build/drafts/bullets/bullets.md", "- Built a queue\n- Ran it\n")
        _, out = self.run_tool("phrasings", ".build/drafts/bullets/bullets.md", "--angle", "backend")
        self.assertEqual([l for l in out if l.startswith("bullet")], ["bullet 1: Built a queue", "bullet 2: Ran it"])

    def test_verdicts_name_the_bullets_to_add(self):
        """#518 (4): which bullets differ from every wording kept for the angle, and their entry."""
        self.write("entries/2025-07-cache.md", "# Cache\n\n## What happened\nBuilt a PostgreSQL job queue in Go "
                   "that took 40% of traffic.\n\n## Past phrasings\n- none yet\n")
        self.write(self.FOLDER + "/resume.tex", RESUME.replace(r"\end{itemize}", r"  \item BSc in Computer Science, 2024" "\n"
                                                               r"\end{itemize}"))
        code, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-06-queue.md", "entries/2025-07-cache.md",
                                  "--angle", "backend")
        self.assertEqual(code, 0, out)
        verdicts = [l for l in out if l.startswith("  ") and not l.startswith("  entries/")]
        self.assertEqual(verdicts, ["  same: entries/2025-06-queue.md:7: adds no line",
                                    "  add: entries/2025-07-cache.md",
                                    "  none: the entries given hold less than half its words: adds no line"])
        self.assertEqual(out[-1], "adds: --add 2=entries/2025-07-cache.md")
        merged = RESUME.replace(r"\item Cut quote", r"\item Built a PostgreSQL job queue and cut quote")
        self.write(self.FOLDER + "/resume.tex", merged)
        self.write("entries/2025-08-api.md", "# API\n\n## What happened\nCut quote latency with a Redis rate cache.\n")
        _, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-07-cache.md", "entries/2025-08-api.md", "--angle", "backend")
        self.assertEqual(out[1:4], ["  entries/2025-07-cache.md: none for backend", "  entries/2025-08-api.md: none for backend",
                                    "  add: entries/2025-08-api.md"])   # a merged bullet goes in whole
        self.write("entries/2025-07-cache.md", self.read("entries/2025-07-cache.md").replace(
            "- none yet", "**backend**\n- Built a job queue (2025 resume)"))
        _, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-07-cache.md", "--angle", "backend")
        self.assertIn("  older form: entries/2025-07-cache.md: 2 Past phrasings lines in a form this command cannot read: "
                      "adds no line until they are in the template's form", out)
        self.assertEqual(out[-1], "adds: none")

    def test_education_items_are_no_bullets(self):
        """#524: a coursework line under the Education heading is listed as no bullet and gets no add:."""
        self.write(self.FOLDER + "/resume.tex", RESUME.replace(r"\end{document}", r"""\section*{Education}
\begin{itemize}
  \item {\small \textbf{Related Courses:} Go job queue on PostgreSQL, traffic}
\end{itemize}
\end{document}"""))
        code, out = self.run_tool("phrasings", self.FOLDER, "entries/2025-06-queue.md", "--angle", "backend")
        self.assertEqual(code, 0, out)
        self.assertEqual([l for l in out if l.startswith("bullet")], [
            "bullet 1: Cut quote API p95 latency from 820 ms to 210 ms with a Redis rate cache",
            "bullet 2: **Queue:** Built a Go job queue on PostgreSQL for 40% of traffic"])
        self.assertEqual(out[-1], "adds: --add 2=entries/2025-06-queue.md")
        code, out = self.run_tool("phrasings", self.FOLDER, "--angle", "backend", "--add", "3=entries/2025-06-queue.md")
        self.assertEqual(code, 2, out)
        self.assertIn("n from 1 to 2", out[0])

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
        self.assertEqual(out[:1] + out[-2:], ["bullet 1: Built a queue", "cite: %s" % rel, "adds: none"])
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


TARGET = """# Resume: general

## Provenance

| Claim | Entry section | Source |
|---|---|---|
| 820 ms | entries/2025-06-queue.md › Results | PR 1 |
| Teaching | Tutoring › What happened | user |
"""


class Stale(Base):
    def setUp(self):
        super().setUp()
        self.write("entries/2025-06-queue.md", ENTRY)
        self.write("entries/2024-01-tutoring.md", "---\ntitle: Tutoring — weekend classes\n---\n# Tutoring\n")
        self.write("entries/2023-01-other.md", "---\ntitle: Other work\n---\n# Other work\n")
        self.write("outputs/resumes/general.md", TARGET)
        self.write("outputs/resumes/general.tex", RESUME)
        self.commit("write(general): resume", date="2026-03-01T09:00:00")
        self.saved = self.git("rev-parse", "HEAD").strip()

    def test_fresh_when_nothing_changed(self):
        self.write("README.md", "# Log, edited\n")
        self.commit("other")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 0, out)
        self.assertEqual(out[0], "saved: %s 2026-03-01 write(general): resume" % self.saved[:7])
        self.assertIn("cited changed: 0", out)
        self.assertIn("new entries: 0", out)
        self.assertEqual(out[-1], "verdict: fresh")

    def test_cited_entry_changed(self):
        self.write("entries/2025-06-queue.md", ENTRY + "- one more\n")
        self.write("entries/2023-01-other.md", "---\ntitle: Other work\n---\n# Other work, edited\n")
        self.commit("log(queue): result", date="2026-03-04T10:00:00")
        self.write("entries/2024-01-tutoring.md", "---\ntitle: Tutoring — weekend classes\n---\n# Tutoring, edited\n")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 1, out)
        self.assertIn("cited changed: 2", out)
        self.assertIn("  entries/2025-06-queue.md: 1 commit, last 2026-03-04 log(queue): result", out)
        self.assertIn("  entries/2024-01-tutoring.md: uncommitted changes", out)
        self.assertFalse(any("2023-01-other" in l for l in out), out)   # not cited
        self.assertIn("new entries: 0", out)

    def test_new_entry(self):
        self.write("entries/2026-02-new.md", "---\ntitle: New project\n---\n# New project\n")
        self.commit("log(new): start")
        self.write("entries/2026-03-draft.md", "---\ntitle: Draft — not committed\n---\n")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 1, out)
        self.assertIn("cited changed: 0", out)
        self.assertIn("new entries: 2", out)
        self.assertIn("  entries/2026-02-new.md: New project", out)
        self.assertIn("  entries/2026-03-draft.md: Draft — not committed (uncommitted)", out)

    def test_a_new_entry_its_label_names_is_listed_once(self):
        self.write("entries/2026-02-tutoring-online.md", "---\ntitle: Tutoring — online\n---\n")
        self.commit("log(tutoring): online")
        res = application.stale(self.root, "general")
        self.assertEqual([c[0] for c in res["changed"]], [])
        self.assertEqual([n[0] for n in res["new"]], ["entries/2026-02-tutoring-online.md"])
        self.assertEqual(res["saved"][0], self.saved)

    def test_unresolved_cell(self):
        self.write("outputs/resumes/general.md", TARGET + "| Award | Nowhere › Results | user |\n")
        self.commit("write(general): resume")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 0, out)
        self.assertTrue(any(l.startswith("unresolved: ") and "Nowhere" in l for l in out), out)

    def test_no_saved_target(self):
        code, out = self.run_tool("stale", "backend")
        self.assertEqual(code, 1)
        self.assertEqual(out, ["none: no saved target backend (outputs/resumes/backend.* is missing or never committed)"])


    def test_an_upgrade_commit_is_no_save(self):
        self.write("entries/2025-06-queue.md", ENTRY + "- one more\n")
        self.commit("log(queue): result")
        self.write("outputs/resumes/general.md", TARGET + "\n")
        self.commit("upgrade 0.9.0: resume tables")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(out[0], "saved: %s 2026-03-01 write(general): resume" % self.saved[:7])
        self.assertIn("cited changed: 1", out)

    def test_entry_names_with_spaces_and_accents(self):
        self.write("entries/2024-02-café work.md", "---\ntitle: Café work\n---\n")
        self.commit("log(cafe): start")
        self.write("outputs/resumes/general.md", TARGET + "\n")
        self.commit("write(general): resume")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 0, out)
        self.assertIn("new entries: 0", out)

    def test_no_provenance_is_never_fresh(self):
        self.git("rm", "-q", "outputs/resumes/general.md")
        self.write("outputs/resumes/general.tex", RESUME + "% v2\n")
        self.commit("write(general): resume")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 1, out)
        self.assertTrue(out[-2].startswith("no provenance: "), out)
        self.assertEqual(out[-1], "verdict: not compared")

    def test_an_empty_provenance_is_never_fresh(self):
        self.write("outputs/resumes/general.md", "")
        self.commit("write(general): resume")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 1, out)
        self.assertEqual(out[-2:], ["no provenance: the save's outputs/resumes/general.md cites no entry,"
                                    " so no cited entry was checked", "verdict: not compared"])

    def test_a_provenance_citing_no_entry_is_never_fresh(self):
        self.write("outputs/resumes/general.md", TARGET.replace("entries/2025-06-queue.md", "Nowhere")
                   .replace("Tutoring", "Nobody"))
        self.commit("write(general): resume")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 1, out)
        self.assertEqual(len([l for l in out if l.startswith("unresolved: ")]), 2, out)
        self.assertTrue(out[-2].startswith("no provenance: "), out)
        self.assertEqual(out[-1], "verdict: not compared")

    def test_one_commit_is_singular(self):
        self.write("entries/2025-06-queue.md", ENTRY + "- one more\n")
        self.commit("log(queue): result", date="2026-03-04T09:00:00")
        _, out = self.run_tool("stale", "general")
        self.assertIn("  entries/2025-06-queue.md: 1 commit, last 2026-03-04 log(queue): result", out)
        self.write("entries/2025-06-queue.md", ENTRY + "- two more\n")
        self.commit("log(queue): again", date="2026-03-05T09:00:00")
        _, out = self.run_tool("stale", "general")
        self.assertIn("  entries/2025-06-queue.md: 2 commits, last 2026-03-05 log(queue): again", out)

    def test_a_deleted_target_is_not_saved(self):
        self.git("rm", "-q", "outputs/resumes/general.md", "outputs/resumes/general.tex")
        self.commit("remove general")
        code, out = self.run_tool("stale", "general")
        self.assertEqual(code, 1)
        self.assertTrue(out[0].startswith("none: "), out)


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
        self.assertIn("since 2026-02-01: 1 commit", out)


class Contract(Base):
    """The rows of #661 where application.py's copy behaved apart from the other tools'."""
    def roles(self, *roles):
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n"
                   + "".join("%d. %s\n" % (i, r) for i, r in enumerate(roles, 1)))

    def test_tier_counts_gap_lines_as_fit_and_scan_do(self):
        self.roles("Backend engineer", "GAP: a second role", "Infra engineer")
        self.write("outputs/resumes/backend.tex", RESUME)
        code, out = self.run_tool("start", "--name", "n", "--from", "backend", "--family", "infra", "--tier", "3")
        self.assertEqual(code, 0, out)
        code, out = self.run_tool("start", "--name", "m", "--from", "backend", "--family", "backend", "--tier", "2")
        self.assertEqual(code, 2, out)   # the GAP line is no role
        self.assertEqual(application.fit.ranks(self.root), {1: False, 2: True, 3: False})

    def test_start_lists_targets_in_a_root_with_glob_characters(self):
        root = os.path.join(self.tmp, "log [1]")
        os.makedirs(os.path.join(root, "outputs", "resumes"))
        with open(os.path.join(root, "outputs", "resumes", "backend.tex"), "w", encoding="utf-8") as f:
            f.write(RESUME)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            application.main(["--root", root, "start"])
        self.assertEqual(out.getvalue().splitlines()[0], "target: backend | outputs/resumes/backend.tex")

    def test_a_misnamed_marker_is_refused_with_its_rename(self):
        rel = self.folder("2026-01-10-globex-sre")
        self.write(rel + "/Archived.md", "Archived (user, 2026-01-01)\n")
        self.assertFalse(application.logfiles.is_archived_folder(self.root, rel))
        for level in ("archived", "reference"):
            code, out = self.run_tool("level", rel, level, "--today", "2026-02-01")
            self.assertEqual(code, 1, out)
            self.assertIn("`git mv %s/Archived.md %s/archived.md`" % (rel, rel), out[0])
        self.assertEqual(os.listdir(os.path.join(self.root, *rel.split("/"))).count("archived.md"), 0)

    def test_tier_zero_is_no_place(self):
        self.roles("Backend engineer")
        self.write("outputs/resumes/backend.tex", RESUME)
        code, out = self.run_tool("start", "--name", "n", "--from", "backend", "--family", "backend", "--tier", "0")
        self.assertEqual(code, 2, out)
        self.assertNotIn("null", out[0])

    def test_an_empty_target_name_is_refused(self):
        for args in (("sent", ""), ("stale", "")):
            code, out = self.run_tool(*args)
            self.assertEqual(code, 2, (args, out))
            self.assertIn("not a target name", out[0])

    def test_a_company_with_no_ascii_letter_is_named_posting(self):
        code, out = self.run_tool("name", "--company", "日本電気", "--role", "Backend", "--today", "2026-01-01")
        self.assertEqual(code, 0, out)
        self.assertEqual(out[0], "name: 2026-01-01-posting-backend")
        self.assertEqual(out[-1], "commit: write(posting): Backend")

    def test_a_placeholder_line_is_no_older_form(self):
        self.write("entries/2025-06-queue.md", "# Q\n\n## Past phrasings\n- none\n- GAP (ask the user)\n")
        self.assertEqual(application.older_lines(self.root, "entries/2025-06-queue.md"), 0)

    def test_entries_after_angle_on_every_python(self):
        self.write("entries/2025-06-queue.md", ENTRY)
        self.write(".build/drafts/n/resume.tex", RESUME)
        code, out = self.run_tool("phrasings", ".build/drafts/n/resume.tex", "--angle", "backend", "entries/2025-06-queue.md")
        self.assertEqual(code, 0, out)   # write steps 9 and 10 give this order; argparse before 3.12 left the entry over
        self.assertIn("entry: entries/2025-06-queue.md: 2 lines for backend", out)
        self.assertEqual(self.run_tool("phrasings", ".build/drafts/n/resume.tex", "--angle", "backend", "--bogus")[0], 2)

    def test_at_cap_names_the_claims_two_wordings(self):
        self.write("entries/2025-06-queue.md", """# Queue

## Past phrasings
- **backend:** "Reduced quote API p95 latency from 820 ms with a Redis cache" (outputs/applications/2026-01-05-a-b)
- **backend:** "Brought quote API p95 latency down to 210 ms with Redis caching" (outputs/applications/2026-01-06-a-b)
- **backend:** "Built a job queue on PostgreSQL" (outputs/applications/2026-01-07-a-b)
""")
        self.write(".build/drafts/n/resume.tex", RESUME)
        code, out = self.run_tool("phrasings", ".build/drafts/n/resume.tex", "--angle", "backend", "entries/2025-06-queue.md")
        self.assertEqual(code, 0, out)
        caps = [l for l in out if l.startswith("  at cap:")]
        self.assertEqual(len(caps), 1, out)   # bullet 1's claim; bullet 2's claim keeps one wording
        self.assertTrue(caps[0].startswith("  at cap: entries/2025-06-queue.md: 4,5: "), out)
        self.assertEqual(out[out.index(caps[0]) - 1], "  add: entries/2025-06-queue.md")


class PrepBase(Base):
    FOLDER = "outputs/applications/2026-03-01-acme-backend-engineer"
    FILE = FOLDER + "/prep-final.md"

    def setUp(self):
        super().setUp()
        self.write(self.FOLDER + "/posting.md", "https://example.com/job\n")

    def init(self, *more):
        return self.run_tool("prep-init", self.FOLDER, "--stage", "final", *more)

    def status(self, *more):
        return self.run_tool("prep-status", self.FOLDER, "--today", "2026-03-10", *more)

    def items(self):
        return [l.split("|")[1].strip() for l in self.read(self.FILE).split("## Items")[1].split("## Decisions")[0].splitlines()[4:] if l.startswith("|")]

    def set_row(self, item, state, where=""):
        text = self.read(self.FILE)
        old = [l for l in text.splitlines() if l.startswith("| %s |" % item)][0]
        phase = old.split("|")[2].strip()
        self.write(self.FILE, text.replace(old, "| %s | %s | %s | %s |" % (item, phase, state, where)))


class Prep(PrepBase):

    def test_init_writes_the_standard_items_in_phase_order(self):
        code, out = self.init("--date", "2026-03-12", "--mode-start", "abc123")
        self.assertEqual((code, out), (0, ["wrote: %s" % self.FILE]))
        text = self.read(self.FILE)
        for line in ("# Prep: final", "stage: final", "interview: 2026-03-12", "mode start: abc123",
                     "practice log: practice-final.md", "| item | phase | state | where |",
                     "| # | decision | value | source | backup / note |", "| date | commitments | plan | estimate |",
                     "| page | built from | link | for |"):
            self.assertIn(line, text.splitlines())
        self.assertEqual(self.items(), ["recruiter-mail", "posting", "sent-version", "research", "requirement-map",
                                        "deep-dives", "user-only-facts", "behavioural-leads", "tell-me-about-yourself",
                                        "why-this-company", "awkward-questions", "logistics", "effort", "schedule",
                                        "practice", "mock"])
        phases = [l.split("|")[2].strip() for l in text.splitlines() if l.startswith("| ") and "| open |" in l]
        self.assertEqual(phases, sorted(phases, key=application.PHASES.index))

    def test_status_reads_a_short_divider_as_the_standard_one(self):
        self.init("--date", "2026-03-12")
        want = self.status()
        self.write(self.FILE, self.read(self.FILE).replace("|---|---|---|---|", "|-|-|-|-|", 1))
        self.assertIn("| item | phase | state | where |\n|-|-|-|-|\n", self.read(self.FILE))
        self.assertEqual(self.status(), want)

    def test_status_reads_a_divider_with_no_closing_pipe(self):
        self.init("--date", "2026-03-12")
        want = self.status()
        self.write(self.FILE, self.read(self.FILE).replace("|---|---|---|---|", "|---|---|---|---", 1))
        self.assertIn("| item | phase | state | where |\n|---|---|---|---\n", self.read(self.FILE))
        self.assertEqual(self.status(), want)

    def test_init_with_talk_and_areas(self):
        self.assertEqual(self.init("--with", "talk,areas")[0], 0)
        items = self.items()
        self.assertEqual(items[items.index("behavioural-leads") + 1:items.index("tell-me-about-yourself")], ["areas", "talk"])
        self.assertIn("interview: ?", self.read(self.FILE))

    def test_init_with_one(self):
        self.init("--with", "talk")
        self.assertIn("talk", self.items())
        self.assertNotIn("areas", self.items())

    def test_init_refusals(self):
        self.assertEqual(self.init("--with", "slides")[0], 2)
        self.assertEqual(self.run_tool("prep-init", self.FOLDER, "--stage", "Final Round")[0], 2)
        self.assertEqual(self.run_tool("prep-init", "outputs/applications/nope", "--stage", "final")[0], 2)
        self.assertFalse(self.exists(self.FILE))
        self.init()
        code, out = self.init()
        self.assertEqual(code, 1)
        self.assertTrue(out[0].startswith("refused: ") and "exists" in out[0], out)
        self.assertEqual(self.run_tool("prep-status", self.FOLDER, "--stage", "../x")[0], 2)

    def test_status_prints_every_item_then_next(self):
        self.init("--date", "2026-03-12")
        self.set_row("posting", "done", "posting.md")
        self.set_row("recruiter-mail", "set aside")
        self.set_row("sent-version", "done")
        self.set_row("logistics", "user-only")
        self.set_row("user-only-facts", "user-only", "deep-dive-x.md#questions")
        self.set_row("research", "done", "-")
        head = "| date | commitments | plan | estimate |\n|---|---|---|---|\n"
        text = self.read(self.FILE).replace(head, head + "| 2026-03-09 | - | read | 1 h |\n"
                                            "| 2026-03-10 | exam 16:30 | mock at 18:00 | 1 h |\n"
                                            "| 2026-03-10 pm | - | talk a\\|b | 30 min |\n")
        self.write(self.FILE, text)
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertEqual(out[:4], ["prep: " + self.FILE, "today: 2026-03-10", "days left: 2",
                                   "schedule: 2026-03-10 | exam 16:30 | mock at 18:00 | 1 h"])
        self.assertEqual(out[4], "schedule: 2026-03-10 pm | - | talk a|b | 30 min")
        self.assertEqual(out[5:8], ["set aside: recruiter-mail", "done: posting (posting.md)", "done: sent-version"])
        self.assertIn("user-only: user-only-facts (deep-dive-x.md#questions)", out)
        self.assertIn("done: research", out)
        self.assertEqual(len([l for l in out if not l.startswith(("prep:", "today:", "days left:", "schedule:", "not practised:", "not diagnosed:", "next:"))]), 16)
        self.assertEqual(out[-3:], ["next: user-only-facts (user-only)", "next: logistics (user-only)",
                                    "next: requirement-map (open, research)"])

    def test_next_takes_the_earliest_phase_not_the_first_row(self):
        self.init()
        text = self.read(self.FILE)
        self.write(self.FILE, text.replace("|---|---|---|---|\n", "|---|---|---|---|\n| bring-id | plan | open | |\n", 1))
        for item in ("recruiter-mail", "posting", "sent-version"):
            self.set_row(item, "done")
        _, out = self.status()
        self.assertEqual(out[-1], "next: research (open, research)")
        self.assertIn("open: bring-id", out)

    def test_nothing_open(self):
        self.init()
        for item in self.items():
            self.set_row(item, "set aside")
        _, out = self.status()
        self.assertEqual(out[-1], "next: nothing open")
        self.assertIn("days left: unknown (interview: ?)", out)
        self.assertIn("schedule: nothing for today", out)

    def test_after_the_interview(self):
        self.init("--date", "2026-03-09")
        self.assertIn("days left: none (the interview was 2026-03-09)", self.status()[1])
        self.assertIn("days left: 0", self.run_tool("prep-status", self.FOLDER, "--today", "2026-03-09")[1])

    def test_unknown_state_fails(self):
        self.init()
        self.set_row("research", "half done")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 1, out)
        self.assertTrue(out[0].startswith("FAIL: %s:" % self.FILE) and "research" in out[0] and "half done" in out[0], out)

    def test_done_with_a_missing_path_fails(self):
        self.init()
        self.set_row("deep-dives", "done", "deep-dive-queue.md, posting.md#Duties")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 1, out)
        self.assertIn("deep-dive-queue.md does not exist", out[0])
        self.write(self.FOLDER + "/deep-dive-queue.md", "# Notes\n")
        self.assertEqual(self.status()[0], 0)

    def test_done_where_outside_the_folder_or_section_alone_fails(self):
        self.init()
        self.set_row("research", "done", "../2026-01-01-other/posting.md")
        self.set_row("deep-dives", "done", "#notes")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 2, out)
        self.assertIn("not a path in the folder", out[0])
        self.assertIn("names no file", out[1])

    def test_a_missing_separator_row_does_not_hide_the_items(self):
        self.init()
        self.write(self.FILE, self.read(self.FILE).replace("| item | phase | state | where |\n|---|---|---|---|\n", ""))
        self.set_row("research", "half done")
        self.assertEqual(self.status()[0], 2)

    def test_an_open_row_may_name_a_missing_path(self):
        self.init()
        self.set_row("research", "open", "research.md")
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertIn("open: research (research.md)", out)

    def test_unknown_phase_and_short_row_fail(self):
        self.init()
        text = self.read(self.FILE).replace("| mock | practise | open | |", "| mock | rehearse | open | |\n| odd | plan | open |")
        self.write(self.FILE, text)
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 2, out)

    def decisions(self, path=None):
        return application.parse_prep(self.read(path or self.FILE))["tables"]["Decisions"]

    def test_init_carries_the_folders_notes_into_decisions(self):
        # Direction upkeep (SKILL.md) saves a statement for this application as a line of notes.md
        # when the folder has no prep file; the next interview run's prep file has to hold it.
        self.write(self.FOLDER + "/notes.md", "# Notes\n\n- Answer in English this round\n"
                   "回答順序：先結論 | 再細節\n\n* diagnose: talk set aside\n---\n## Later\n#1 priority: relocation\n")
        code, out = self.init("--with", "talk")
        self.assertEqual((code, out), (0, ["wrote: %s" % self.FILE, "carried: 4 lines of %s/notes.md into ## Decisions" % self.FOLDER]))
        self.assertEqual([cells for _, cells in self.decisions()],
                         [["1", "note", "Answer in English this round", "notes.md:3", ""],
                          ["2", "note", "回答順序：先結論 | 再細節", "notes.md:4", ""],
                          ["3", "note", "diagnose: talk set aside", "notes.md:6", ""],
                          ["4", "note", "#1 priority: relocation", "notes.md:9", ""]])
        # a carried note is a value under the fixed decision `note`, never a decision prep-status keys on
        self.assertIn("not diagnosed: talk", self.status()[1])

    def test_each_new_stage_carries_the_notes(self):
        self.write(self.FOLDER + "/notes.md", "Ask about the on-call rota\n")
        self.run_tool("prep-init", self.FOLDER, "--stage", "technical")
        self.init()
        for path in (self.FOLDER + "/prep-technical.md", self.FILE):
            self.assertEqual([cells[2:4] for _, cells in self.decisions(path)], [["Ask about the on-call rota", "notes.md:1"]])

    def test_init_carries_the_note_rows_of_the_folders_other_prep_files(self):
        # Direction upkeep (SKILL.md) saves a statement for this application as a Decisions row
        # `note` once the folder has a prep file; the next stage's prep file has to hold it.
        self.write(self.FOLDER + "/notes.md", "Ask about the on-call rota\n")
        self.run_tool("prep-init", self.FOLDER, "--stage", "screen")
        screen = self.FOLDER + "/prep-screen.md"
        carried = "| 1 | note | Ask about the on-call rota | notes.md:1 |  |\n"
        self.assertIn(carried, self.read(screen))
        self.write(screen, self.read(screen).replace(carried, carried +
                   "| 2 | answer order | STAR | (user, 2026-03-02) | |\n"
                   "| 3 | note | Tell them I would move to Berlin \\| not Munich | (user, 2026-03-03) | |\n"
                   "| 4 | note |\n"))
        code, out = self.init()
        self.assertEqual(code, 0, out)
        self.assertEqual(out[1:], ["carried: 1 lines of %s/notes.md into ## Decisions" % self.FOLDER,
                                   "carried: 1 note rows of %s into ## Decisions" % screen])
        row = [n for n, cells in self.decisions(screen) if cells[2:] and cells[2].startswith("Tell them")][0]
        self.assertEqual([cells for _, cells in self.decisions()],
                         [["1", "note", "Ask about the on-call rota", "notes.md:1", ""],
                          ["2", "note", "Tell them I would move to Berlin | not Munich", "prep-screen.md:%d" % row, ""]])

    def test_a_note_in_several_prep_files_is_carried_once(self):
        row = "| 1 | Note | Practise in English | (user, 2026-03-02) | |\n"
        header = "| # | decision | value | source | backup / note |\n|---|---|---|---|---|\n"
        for stage in ("screen", "technical"):
            self.run_tool("prep-init", self.FOLDER, "--stage", stage)
            other = "%s/prep-%s.md" % (self.FOLDER, stage)
            self.write(other, self.read(other).replace(header, header + row))
        code, out = self.init()
        self.assertEqual(out[1:], ["carried: 1 note rows of %s/prep-screen.md into ## Decisions" % self.FOLDER])
        self.assertEqual([cells[1:4] for _, cells in self.decisions()], [["note", "Practise in English", "prep-screen.md:%d" % (
            [n for n, cells in self.decisions(self.FOLDER + "/prep-screen.md")][0])]])

    def test_init_without_notes_carries_nothing(self):
        self.assertEqual(self.init(), (0, ["wrote: %s" % self.FILE]))
        self.assertEqual(self.decisions(), [])
        self.write(self.FOLDER + "/notes.md", "\n# Notes\n\n")
        self.assertEqual(self.run_tool("prep-init", self.FOLDER, "--stage", "technical")[1],
                         ["wrote: %s/prep-technical.md" % self.FOLDER])

    def test_stage_is_found_or_named(self):
        self.assertEqual(self.status()[0], 2)
        self.init()
        self.assertEqual(self.status()[0], 0)
        self.run_tool("prep-init", self.FOLDER, "--stage", "technical")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertIn("--stage", out[0])
        self.assertEqual(self.status("--stage", "technical")[1][0], "prep: %s/prep-technical.md" % self.FOLDER)

    def test_help_gives_the_format(self):
        for text in ("prep-init", "prep-status", "| item | phase | state | where |", "user-only", "set aside",
                     "| # | decision | value | source | backup / note |"):
            self.assertIn(text, application.__doc__)

    def test_parse_prep_reads_any_section(self):
        prep = application.parse_prep("# Prep: x\n\nstage: x\ninterview: ?\n\n## Pages\n\n| page | built from | link | for |\n"
                                      "|---|---|---|---|\n| card.html | card.md | https://e.x | tablet a\\|b |\n")
        self.assertEqual(prep["header"]["stage"], "x")
        self.assertEqual(application.parse_prep("## S\n\n| a | b |\n|:---|---:|\n| - | - |\n| | |\n")["tables"]["S"],
                         [(5, ["-", "-"])])   # a `-` row under the divider is data; an empty row is left out
        self.assertEqual(prep["tables"]["Pages"], [(10, ["card.html", "card.md", "https://e.x", "tablet a|b"])])


class Practice(PrepBase):
    LOG = PrepBase.FOLDER + "/practice-final.md"

    def add(self, item, verdict, *more, day="2026-03-10"):
        return self.run_tool("practice-add", self.FOLDER, "--item", item, "--verdict", verdict,
                             *(("--today", day) if day else ()), *more)

    def rows(self):
        text = self.read(self.LOG)
        return [l for l in text.split("## Attempts")[1].split("## Patterns")[0].splitlines()[4:] if l.startswith("|")]

    def test_add_writes_the_log_then_appends(self):
        self.init("--date", "2026-03-12", "--with", "areas")
        code, out = self.add("areas/caching", "shaky", "--weak", "no eviction a|b", "--heard", "recorded", "--kind", "drill")
        self.assertEqual((code, out), (0, ["added: %s: | 2026-03-10 | areas/caching | drill | shaky | no eviction a\\|b | recorded |" % self.LOG]))
        text = self.read(self.LOG)
        for line in ("# Practice: final", "| date | item | kind | verdict | weak spots | heard |", "## Patterns", "## Do not say"):
            self.assertIn(line, text.splitlines())
        self.write(self.LOG, text.replace("## Patterns\n", "## Patterns\n\n- rushes the numbers\n"))
        self.assertEqual(self.add("mock", "passed", day="2026-03-11")[0], 0)
        self.assertEqual(self.rows(), ["| 2026-03-10 | areas/caching | drill | shaky | no eviction a\\|b | recorded |",
                                       "| 2026-03-11 | mock | round | passed | - | - |"])
        self.assertIn("- rushes the numbers", self.read(self.LOG))
        self.write(self.LOG, self.read(self.LOG).replace("| recorded |" + chr(10), "| recorded |" + chr(10) * 2))   # a blank line inside the table
        self.add("practice", "near", day="2026-03-12")
        self.assertTrue(self.read(self.LOG).split("## Patterns")[0].rstrip().endswith("| 2026-03-12 | practice | round | near | - | - |"))

    def test_add_takes_the_machines_date(self):
        self.init()
        before = datetime.date.today().isoformat()
        self.add("practice", "near", day=None)
        self.assertIn(self.rows()[0].split("|")[1].strip(), (before, datetime.date.today().isoformat()))

    def test_add_refusals(self):
        self.init()
        code, out = self.add("practice", "good")
        self.assertEqual(code, 2)
        self.assertIn("passed, near, shaky, again", out[0])
        self.assertEqual(self.add("practice", "near", "--heard", "dreamt")[0], 2)
        self.assertEqual(self.add("no-such-item", "near")[0], 2)
        self.assertEqual(self.add("story/", "near")[0], 2)
        self.assertEqual(self.add("story", "near")[0], 2)
        self.assertFalse(self.exists(self.LOG))
        self.assertEqual(self.add("story/queue-outage", "near")[0], 0)
        self.write(self.LOG, "# Practice: final\n")
        code, out = self.add("practice", "near")
        self.assertEqual(code, 2)
        self.assertIn("## Attempts", out[0])

    def test_retest_until_a_later_pass(self):
        self.init("--date", "2026-03-12", "--with", "talk")
        self.add("talk/opening", "again", day="2026-03-09")
        self.add("story/queue-outage", "shaky", day="2026-03-09")
        self.add("practice", "near", day="2026-03-09")
        _, out = self.status()
        self.assertEqual([l for l in out if l.startswith("retest:")], ["retest: talk/opening", "retest: story/queue-outage"])
        self.assertLess(out.index("retest: story/queue-outage"), out.index("next: recruiter-mail (open, intake)"))
        self.assertGreater(out.index("retest: talk/opening"), out.index("open: mock"))
        self.add("talk/opening", "passed")
        _, out = self.status()
        self.assertEqual([l for l in out if l.startswith("retest:")], ["retest: story/queue-outage"])

    def test_not_practised(self):
        self.init("--date", "2026-03-12", "--with", "areas")
        text = self.read(self.FILE).replace("| mock | practise | open | |", "| mock | practise | open | |\n| whiteboard | practise | open | |")
        self.write(self.FILE, text)
        _, out = self.status()
        self.assertEqual([l for l in out if l.startswith("not practised:")],
                         ["not practised: practice", "not practised: mock", "not practised: whiteboard"])
        self.assertEqual(self.add("areas/x", "passed")[0], 0)   # any attempt counts for practice
        _, out = self.status()
        self.assertEqual([l for l in out if l.startswith("not practised:")], ["not practised: mock", "not practised: whiteboard"])
        self.add("whiteboard/cache", "near")
        self.set_row("mock", "set aside")
        _, out = self.status()
        self.assertEqual([l for l in out if l.startswith("not practised:")], [])

    def diagnosed(self):
        return [l for l in self.status()[1] if l.startswith("not diagnosed:")]

    def add_topics(self, *topics):
        text = self.read(self.FILE)
        rows = "".join("| areas/%s | practise | open | interview-final.md#technical-areas |\n" % t for t in topics)
        self.write(self.FILE, text.replace("| mock | practise | open | |\n", "| mock | practise | open | |\n" + rows))

    def test_not_diagnosed_per_area(self):
        self.init("--date", "2026-03-12", "--with", "areas,talk")
        self.assertEqual(self.diagnosed(), ["not diagnosed: behavioural answers", "not diagnosed: areas",
                                            "not diagnosed: talk"])
        self.add_topics("caching", "queues")
        _, out = self.status()
        lines = [l for l in out if l.startswith("not diagnosed:")]
        self.assertEqual(lines, ["not diagnosed: behavioural answers", "not diagnosed: areas/caching",
                                 "not diagnosed: areas/queues", "not diagnosed: talk"])
        self.assertLess(out.index(lines[-1]), out.index("next: recruiter-mail (open, intake)"))
        self.assertGreater(out.index(lines[0]), out.index("not practised: mock"))
        self.add("story/queue-outage", "shaky", "--kind", "diagnostic")
        self.add("areas/caching", "near", "--kind", "drill")   # not a diagnostic round
        self.add("talk/opening", "near", "--kind", "diagnostic")
        self.assertEqual(self.diagnosed(), ["not diagnosed: areas/caching", "not diagnosed: areas/queues"])
        self.add("areas/caching", "passed", "--kind", "diagnostic")
        self.add("areas/queues/fifo", "again", "--kind", "diagnostic")
        self.assertEqual(self.diagnosed(), [])

    def test_a_set_aside_area_is_not_diagnosed(self):
        self.init("--date", "2026-03-12", "--with", "areas,talk")
        self.add_topics("caching", "queues")
        self.set_row("areas/queues", "set aside")
        head = "| # | decision | value | source | backup / note |\n|---|---|---|---|---|\n"
        self.write(self.FILE, self.read(self.FILE).replace(head, head +
                   "| 1 | diagnose: Talk | Set aside: no time for a spoken round | (user, 2026-03-10) | |\n"
                   "| 2 | diagnose: areas/caching | a round tomorrow | (user, 2026-03-10) | |\n"))
        self.assertEqual(self.diagnosed(), ["not diagnosed: behavioural answers", "not diagnosed: areas/caching"])
        self.set_row("behavioural-leads", "set aside")
        self.assertEqual(self.diagnosed(), ["not diagnosed: areas/caching"])

    def test_no_area_lines_once_a_plan_item_is_done(self):
        self.init("--date", "2026-03-12", "--with", "areas,talk")
        self.set_row("logistics", "done")
        self.assertEqual(self.diagnosed(), ["not diagnosed: behavioural answers", "not diagnosed: areas",
                                            "not diagnosed: talk"])
        self.set_row("effort", "done", "prep-final.md#decisions")
        self.assertEqual(self.diagnosed(), [])
        self.set_row("effort", "open")
        self.set_row("schedule", "done", "prep-final.md#schedule")
        self.assertEqual(self.diagnosed(), [])

    def test_without_areas_or_talk_only_the_behavioural_answers(self):
        self.init("--date", "2026-03-12")
        self.assertEqual(self.diagnosed(), ["not diagnosed: behavioural answers"])
        self.add("behavioural-leads", "near", "--kind", "diagnostic")
        self.assertEqual(self.diagnosed(), [])

    def reviewed(self, today="2026-03-10"):
        return [l for l in self.run_tool("prep-status", self.FOLDER, "--today", today)[1] if l.startswith("not reviewed:")]

    def test_not_reviewed_on_the_evening_before(self):
        self.init("--date", "2026-03-11", "--with", "areas")
        self.add_topics("caching")
        self.add("story/queue-outage", "shaky")
        self.add("areas/caching", "passed")
        _, out = self.status()
        lines = [l for l in out if l.startswith("not reviewed:")]
        self.assertEqual(lines, ["not reviewed: story/queue-outage", "not reviewed: mock"])
        self.assertGreater(out.index(lines[0]), out.index("not practised: mock"))
        self.assertLess(out.index(lines[-1]), out.index("next: recruiter-mail (open, intake)"))
        self.assertEqual(self.reviewed("2026-03-09"), [])   # two days left: Final review has not started
        self.assertEqual(self.reviewed("2026-03-11"), [])   # the interview day skips step 1
        head = "| # | decision | value | source | backup / note |\n|---|---|---|---|---|\n"
        self.write(self.FILE, self.read(self.FILE).replace(head, head +
                   "| 1 | Final review: mock | drop: no time | (user, 2026-03-10) | |\n"))
        self.assertEqual(self.reviewed(), ["not reviewed: story/queue-outage"])
        self.write(self.FILE, self.read(self.FILE).replace(head, head +
                   "| 2 | final review: story/queue-outage | tonight | (user, 2026-03-10) | |\n"))
        self.assertEqual(self.reviewed(), [])

    def test_a_set_aside_item_with_no_decision_is_not_reviewed(self):
        self.init("--date", "2026-03-11", "--with", "areas")
        self.add_topics("caching", "queues")
        self.add("areas/caching", "passed")
        self.set_row("mock", "set aside")              # the run set it aside itself: no row names it
        self.set_row("areas/queues", "set aside")      # the Plan cut it, with the user's row
        head = "| # | decision | value | source | backup / note |\n|---|---|---|---|---|\n"
        self.write(self.FILE, self.read(self.FILE).replace(head, head +
                   "| 1 | Areas/queues | set aside: the Plan cut it | (user, 2026-03-08) | |\n"))
        self.assertEqual(self.reviewed(), ["not reviewed: mock"])
        self.write(self.FILE, self.read(self.FILE).replace(head, head +
                   "| 2 | final review: mock | drop | (user, 2026-03-10) | |\n"))
        self.assertEqual(self.reviewed(), [])

    def test_a_bad_practice_row_fails(self):
        self.init()
        self.add("practice", "near")
        self.write(self.LOG, self.read(self.LOG).replace("| near |", "| fine |"))
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 1, out)
        self.assertTrue(out[0].startswith("FAIL: %s:" % self.LOG) and "fine" in out[0], out)

    def test_close_the_loop_after_the_interview(self):
        close = "next: close the loop (ask for the questions asked, round by round)"
        self.init("--date", "2026-03-09")
        _, out = self.status()
        self.assertEqual([l for l in out if l.startswith("next:")][0], close)
        self.assertEqual(out[-1], "next: recruiter-mail (open, intake)")
        self.assertNotIn(close, self.run_tool("prep-status", self.FOLDER, "--today", "2026-03-09")[1])
        self.write(self.FOLDER + "/interview-final-debrief.md", "# Debrief\n")
        self.assertNotIn(close, self.status()[1])

    def test_help_gives_the_practice_format(self):
        for text in ("practice-add", "| date | item | kind | verdict | weak spots | heard |", "## Patterns",
                     "## Do not say", "retest:", "not practised:", "not diagnosed:", "diagnose: <area>", "not reviewed:", "final review: <item>", "close the loop"):
            self.assertIn(text, application.__doc__)

# ---- intake: recruiter mail and its attachments as text (fixtures made up: example.com, Acme) ----

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx_bytes(*paragraphs):
    """A minimal .docx: word/document.xml with one w:p per paragraph, a w:tab for each tab."""
    def para(text):
        runs = "<w:r><w:tab/></w:r>".join('<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % t for t in text.split("\t"))
        return "<w:p>%s</w:p>" % runs
    xml = '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="%s"><w:body>%s</w:body></w:document>' % (
        W_NS, "".join(para(p) for p in paragraphs))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", xml.encode("utf-8"))
    return buf.getvalue()


def pdf_bytes(text):
    """A one-page PDF whose text layer is text (ASCII), with a correct xref table."""
    stream = "BT /F1 12 Tf 20 100 Td (%s) Tj ET" % text
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            "<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for n, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (n, obj)).encode("latin-1")
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    out += b"".join(("%010d 00000 n \n" % o).encode() for o in offsets)
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)).encode()
    return out


def multipart_mail(extra=()):
    """A recruiter's mail with a presentation prompt (.docx) and a study guide (.pdf)."""
    m = email.message.EmailMessage()
    m["From"] = "Rae Recruiter <rae@example.com>"
    m["To"] = "candidate@example.com"
    m["Cc"] = "coordinator@example.com"
    m["Subject"] = "Final interview – next steps"
    m["Date"] = "Thu, 05 Mar 2026 18:30:00 +0000"
    m.set_content("Hi,\n\nYour final loop is on March 12. The prompt and the guide are attached.\n\nRae\n")
    m.add_alternative("<html><body><p>Hi,</p><p>HTML copy, not this one.</p></body></html>", subtype="html")
    m.add_attachment(docx_bytes("Presentation prompt", "Speak for 10 minutes.\tPrinted notes are welcome."),
                     maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                     filename="Presentation Prompt.docx")
    m.add_attachment(pdf_bytes("Study guide: leadership principles"), maintype="application", subtype="pdf",
                     filename="Study Guide.pdf")
    for name, data in extra:
        m.add_attachment(data, maintype="application", subtype="octet-stream", filename=name)
    return m.as_bytes()


# An HTML-only mail as Outlook sends it: quoted-printable, a no-break space in the text (=C2=A0, &nbsp;).
NBSP_MAIL = b"""From: Rae Recruiter <rae@example.com>
To: candidate@example.com
Subject: =?utf-8?q?Arrival_time_=E2=80=93_updated?=
Date: Mon, 09 Mar 2026 16:05:00 -0700
MIME-Version: 1.0
Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: quoted-printable

<html><head><style>p {margin:0}</style></head><body><p>Please arrive at 9:30=C2=A0am,=
 not 10:00&nbsp;am.</p><ul><li>Bring photo ID</li><li>Lunch is provided</li></ul></body></html>
"""


def local(when):
    return datetime.datetime.fromisoformat(when).astimezone()


class Intake(Base):
    FOLDER = "outputs/applications/2026-03-01-acme-solutions-architect"

    def setUp(self):
        super().setUp()
        self.write(self.FOLDER + "/posting.md", "https://example.com/job\n")
        self.inbox = os.path.join(self.tmp, "Downloads")
        os.makedirs(self.inbox)

    def drop(self, name, data):
        path = os.path.join(self.inbox, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def intake(self, *files, today="2026-03-10"):
        return self.run_tool("intake", *files, "--folder", self.FOLDER, "--today", today)

    def no_pdftotext(self):
        return mock.patch.object(application.resume, "poppler_bin", return_value=None)

    def test_multipart_mail_with_docx_and_pdf(self):
        day = local("2026-03-05T18:30:00+00:00")
        name = "%s/recruiter/%s-final-interview-next-steps.md" % (self.FOLDER, day.date().isoformat())
        with self.no_pdftotext():
            code, out = self.intake(self.drop("final.eml", multipart_mail()))
        self.assertEqual(code, 0)
        self.assertEqual(out, ["saved: " + name,
                               "unread: %s: Study Guide.pdf: no pdftotext (Machine setup installs poppler)" % name])
        text = self.read(name)
        self.assertTrue(text.startswith("# Final interview – next steps\n"), text)
        for line in ("From: Rae Recruiter <rae@example.com>", "To: candidate@example.com", "Cc: coordinator@example.com",
                     "Date: %s" % day.strftime("%Y-%m-%d %H:%M"), "Source: final.eml",
                     "Your final loop is on March 12.", "## Attachment: Presentation Prompt.docx",
                     "Presentation prompt\nSpeak for 10 minutes.\tPrinted notes are welcome.",
                     "## Attachment: Study Guide.pdf", "unread: no pdftotext (Machine setup installs poppler)"):
            self.assertIn(line, text)
        self.assertNotIn("HTML copy", text)   # the text part wins
        self.assertNotIn(self.inbox, text)   # the user's own path stays out of the Log

    @unittest.skipUnless(application.resume.poppler_bin("pdftotext"), "no pdftotext on this machine")
    def test_pdf_read_with_pdftotext(self):
        code, out = self.intake(self.drop("final.eml", multipart_mail()))
        self.assertEqual(code, 0)
        self.assertEqual(len(out), 1, out)
        self.assertIn("Study guide: leadership principles", self.read(out[0][len("saved: "):]))

    def test_pdf_pdftotext_cannot_read_is_unread(self):
        with mock.patch.object(application.resume, "poppler_bin", return_value=sys.executable):   # rejects -enc
            code, out = self.intake(self.drop("guide.pdf", b"%PDF-1.4 not really"))
        self.assertEqual(code, 0)
        self.assertEqual(len(out), 2, out)
        self.assertEqual(out[0], "saved: %s/recruiter/2026-03-10-guide.md" % self.FOLDER)
        self.assertTrue(out[1].startswith("unread: %s/recruiter/2026-03-10-guide.md: guide.pdf: pdftotext failed" % self.FOLDER), out)

    def test_html_only_mail_with_no_break_spaces(self):
        day = local("2026-03-09T16:05:00-07:00")
        code, out = self.intake(self.drop("arrival.eml", NBSP_MAIL))
        self.assertEqual(code, 0)
        name = "%s/recruiter/%s-arrival-time-updated.md" % (self.FOLDER, day.date().isoformat())
        self.assertEqual(out, ["saved: " + name])
        text = self.read(name)
        self.assertIn("# Arrival time – updated", text)
        self.assertIn("Please arrive at 9:30 am, not 10:00 am.", text)
        self.assertIn("- Bring photo ID\n- Lunch is provided", text)
        self.assertNotIn("\xa0", text)
        self.assertNotIn("margin", text)   # <style> is not text
        self.assertIn("Date: " + day.strftime("%Y-%m-%d %H:%M"), text)

    def test_prints_on_a_cp950_console(self):
        """-I ignores PYTHONIOENCODING: a Windows console with a CJK code page takes cp950 output."""
        mail = multipart_mail(extra=[("費用表 ✅\xa0.xlsx", b"PK\x03\x04 not read")])
        path = self.drop("final.eml", mail)
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp950", errors="strict")
        saved = sys.stdout
        sys.stdout = console
        try:
            with self.no_pdftotext():
                code = application.main(["--root", self.root, "intake", path, "--folder", self.FOLDER])
            console.flush()
        finally:
            sys.stdout = saved
        self.assertEqual(code, 0)
        printed = raw.getvalue().decode("utf-8")
        self.assertIn("費用表 ✅ .xlsx: not read", printed)   # a name is one line, its spaces plain

    def test_other_types_are_listed_not_read(self):
        with self.no_pdftotext():
            code, out = self.intake(self.drop("final.eml", multipart_mail(extra=[("Expense Form.xlsx", b"PK\x03\x04")])))
        self.assertEqual(code, 0)
        name = out[0][len("saved: "):]
        self.assertIn("unread: %s: Expense Form.xlsx: not read (.xlsx files are listed, not read)" % name, out)
        self.assertIn("## Attachment: Expense Form.xlsx\n\nunread: not read (.xlsx files are listed, not read)", self.read(name))

    def test_a_broken_docx_is_unread(self):
        code, out = self.intake(self.drop("prompt.docx", b"not a zip"))
        self.assertEqual(code, 0)
        self.assertEqual(out[0], "saved: %s/recruiter/2026-03-10-prompt.md" % self.FOLDER)
        self.assertTrue(out[1].startswith("unread: %s/recruiter/2026-03-10-prompt.md: prompt.docx: not a readable .docx" % self.FOLDER), out)

    def test_a_file_on_its_own(self):
        code, out = self.intake(self.drop("Presentation Prompt.docx", docx_bytes("Prompt", "Ten minutes.")))
        self.assertEqual((code, out), (0, ["saved: %s/recruiter/2026-03-10-presentation-prompt.md" % self.FOLDER]))
        text = self.read(self.FOLDER + "/recruiter/2026-03-10-presentation-prompt.md")
        self.assertTrue(text.startswith("# Presentation Prompt.docx\n"), text)
        self.assertIn("Source: Presentation Prompt.docx", text)
        self.assertIn("Prompt\nTen minutes.", text)
        self.assertEqual(self.intake(self.drop("notes.txt", "Ask about\xa0parking\n".encode("utf-8")))[1],
                         ["saved: %s/recruiter/2026-03-10-notes.md" % self.FOLDER])
        self.assertIn("Ask about parking", self.read(self.FOLDER + "/recruiter/2026-03-10-notes.md"))
        code, out = self.intake(self.drop("form.xlsx", b"PK"))
        self.assertEqual((code, out), (0, ["unread: form.xlsx: not read (.xlsx files are listed, not read)"]))
        self.assertFalse(self.exists(self.FOLDER + "/recruiter/2026-03-10-form.md"))

    def test_same_mail_again_is_unchanged_and_another_takes_the_next_name(self):
        path = self.drop("arrival.eml", NBSP_MAIL)
        saved = self.intake(path)[1][0][len("saved: "):]
        self.assertEqual(self.intake(path)[1], ["unchanged: " + saved])
        later = self.drop("arrival2.eml", NBSP_MAIL.replace(b"9:30", b"9:45"))
        self.assertEqual(self.intake(later)[1], ["saved: " + saved[:-len(".md")] + "-2.md"])
        self.assertEqual(self.intake(later)[1], ["unchanged: " + saved[:-len(".md")] + "-2.md"])

    def test_the_same_mail_read_again_rewrites_its_file(self):
        path = self.drop("final.eml", multipart_mail())
        with self.no_pdftotext():
            first = self.intake(path)[1]
        name = first[0][len("saved: "):]
        self.assertIn("unread: no pdftotext", self.read(name))
        with mock.patch.object(application, "pdf_text", return_value=("Study guide text\fPage two", None)):
            self.assertEqual(self.intake(path)[1], ["saved: " + name])   # once pdftotext is installed: no -2
        text = self.read(name)
        self.assertIn("Study guide text\nPage two", text)   # pdftotext's page break as a line break
        self.assertNotIn("unread:", text)
        self.assertFalse(self.exists(name[:-len(".md")] + "-2.md"))

    def test_slug_drops_reply_prefixes_only(self):
        self.assertEqual(application.slug("RE: Fwd: AW: Final round", "mail"), "final-round")
        self.assertEqual(application.slug("Re：面試", "mail"), "mail")
        self.assertEqual(application.slug("Re-entry program interview", "mail"), "re-entry-program-interview")

    def test_a_forwarded_mail_is_read_with_its_attachments(self):
        outer = email.message.EmailMessage()
        outer["From"] = "Sam Coordinator <sam@example.com>"
        outer["To"] = "candidate@example.com"
        outer["Subject"] = "Fwd: Final interview"
        outer["Date"] = "Fri, 06 Mar 2026 12:00:00 +0000"
        outer.set_content("Forwarding Rae's mail.\n")
        outer.add_attachment(email.message_from_bytes(multipart_mail(), policy=email.policy.default))
        with self.no_pdftotext():
            code, out = self.intake(self.drop("fwd.eml", outer.as_bytes()))
        self.assertEqual(code, 0)
        name = out[0][len("saved: "):]
        inner = "Final interview – next steps.eml"
        self.assertIn("unread: %s: %s › Study Guide.pdf: no pdftotext (Machine setup installs poppler)" % (name, inner), out)
        text = self.read(name)
        for line in ("Forwarding Rae's mail.", "## Attachment: " + inner,
                     "From: Rae Recruiter <rae@example.com>", "Your final loop is on March 12.",
                     "## Attachment: %s › Presentation Prompt.docx" % inner, "Printed notes are welcome."):
            self.assertIn(line, text)

    def test_refuses_a_missing_file_or_folder_and_writes_nothing(self):
        good = self.drop("arrival.eml", NBSP_MAIL)
        code, out = self.intake(good, os.path.join(self.inbox, "gone.eml"))
        self.assertEqual(code, 2)
        self.assertTrue(out[0].startswith("FAIL: cannot read"), out)
        self.assertFalse(self.exists(self.FOLDER + "/recruiter"))
        code, out = self.run_tool("intake", good, "--folder", "outputs/applications/nope")
        self.assertEqual(code, 2)

    def test_help_gives_intake(self):
        for text in ("intake <file>...", "recruiter/<YYYY-MM-DD>-<slug>.md", "unread:", "pdftotext"):
            self.assertIn(text, application.__doc__)


class Pages(PrepBase):
    HEADER = "| page | built from | link | for |\n|---|---|---|---|\n"
    STALE = "stale: pages/card.html (built from card.md, changed since)"

    def setUp(self):
        super().setUp()
        self.init()
        self.write(self.FOLDER + "/card.md", "# Card\n")
        self.write(self.FOLDER + "/pages/card.html", "<p>Card</p>\n")
        self.add_page("pages/card.html", "card.md")
        self.commit("built the card")

    def add_row(self, row):
        self.write(self.FILE, self.read(self.FILE).replace(self.HEADER, self.HEADER + row + "\n"))

    def add_page(self, page, source):
        self.add_row("| %s | %s | https://e.x/%s | tablet |" % (page, source, page))

    def test_a_source_committed_after_its_page_is_stale(self):
        self.write(self.FOLDER + "/card.md", "# Card\n\nA new line.\n")
        self.commit("card edited")
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertIn(self.STALE, out)
        self.assertLess(out.index("open: mock"), out.index(self.STALE))
        self.assertLess(out.index(self.STALE), min(i for i, l in enumerate(out) if l.startswith("next:")))

    def test_a_page_built_in_the_same_commit_or_later_is_not_stale(self):
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertFalse([l for l in out if l.startswith("stale:")], out)
        self.write(self.FOLDER + "/card.md", "# Card\n\nA new line.\n")
        self.commit("card edited")
        self.write(self.FOLDER + "/pages/card.html", "<p>Card</p>\n<p>A new line.</p>\n")
        self.commit("card rebuilt")
        self.assertFalse([l for l in self.status()[1] if l.startswith("stale:")])

    def test_an_uncommitted_source_edit_is_stale_until_the_page_changes_too(self):
        self.write(self.FOLDER + "/card.md", "# Card\n\nA new line.\n")
        self.assertIn(self.STALE, self.status()[1])
        self.write(self.FOLDER + "/pages/card.html", "<p>Card</p>\n<p>A new line.</p>\n")
        self.assertNotIn(self.STALE, self.status()[1])

    def test_a_page_that_is_its_own_source_is_never_stale(self):
        self.write(self.FOLDER + "/drill.html", "<p>Drill</p>\n")
        self.add_page("drill.html", "-")
        self.commit("drill page")
        self.write(self.FOLDER + "/drill.html", "<p>Drill 2</p>\n")
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertFalse([l for l in out if l.startswith("stale:")], out)

    def test_a_cue_card_with_no_page_row(self):
        self.write(self.FOLDER + "/cue-card-final.md", "# Cue card\n")
        code, out = self.status()
        self.assertEqual(code, 0, out)
        line = "no page: cue-card-final.md (no ## Pages row built from it)"
        self.assertIn(line, out)
        self.assertLess(out.index("open: mock"), out.index(line))
        self.assertLess(out.index(line), min(i for i, l in enumerate(out) if l.startswith("next:")))
        self.write(self.FOLDER + "/cue-card-final.html", "<p>Card</p>\n")
        self.add_page("cue-card-final.html", "cue-card-final.md")
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertFalse([l for l in out if l.startswith("no page:")], out)

    def test_a_page_row_naming_the_card_another_way_counts(self):
        self.write(self.FOLDER + "/cue-card-final.md", "# Cue card\n")
        self.write(self.FOLDER + "/cue-card-final.html", "<p>Card</p>\n")
        self.add_page("cue-card-final.html", "./cue-card-final.md")
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertFalse([l for l in out if l.startswith("no page:")], out)

    def test_another_stages_cue_card_needs_no_page_here(self):
        self.write(self.FOLDER + "/cue-card-screen.md", "# Cue card\n")
        self.assertFalse([l for l in self.status()[1] if l.startswith("no page:")])

    def test_a_source_at_the_log_root(self):
        self.write("stories.md", "# Stories\n")
        self.write(self.FOLDER + "/stories.html", "<p>Stories</p>\n")
        self.add_page("stories.html", "/stories.md")
        self.commit("stories page")
        self.assertFalse([l for l in self.status()[1] if l.startswith("stale:")])
        self.write("stories.md", "# Stories\n\nOne more.\n")
        self.commit("stories edited")
        self.assertIn("stale: stories.html (built from /stories.md, changed since)", self.status()[1])

    def test_a_missing_page_or_source_or_a_short_row_fails(self):
        self.add_page("gone.html", "card.md")
        self.add_page("pages/card.html", "gone.md")
        self.add_row("| odd.html | card.md |")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 3, out)
        self.assertTrue(all(l.startswith("FAIL: %s:" % self.FILE) for l in out), out)
        self.assertTrue(any("gone.html does not exist" in l for l in out), out)
        self.assertTrue(any("gone.md does not exist" in l for l in out), out)

    def test_a_page_path_outside_the_folder_or_a_source_outside_the_log_fails(self):
        self.add_page("../other/card.html", "card.md")
        self.add_page("pages/card.html", "/../card.md")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 2, out)
        self.assertIn("not a path in the Log", out[0])
        self.assertIn("not a path in the folder", out[1])

    def test_a_section_a_bare_slash_or_a_folder_names_no_page_file(self):
        self.add_page("pages/card.html", "card.md#intro")
        self.add_page("pages/card.html", "/")
        self.add_page("pages", "card.md")
        code, out = self.status()
        self.assertEqual(code, 2)
        self.assertEqual(len(out), 3, out)
        self.assertIn("pages does not exist", out[0])
        self.assertIn("'' names no file", out[1])
        self.assertIn("'card.md#intro' names no file", out[2])

    def test_outside_a_git_repository_there_is_no_stale_check(self):
        shutil.rmtree(os.path.join(self.root, ".git"), onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))
        code, out = self.status()
        self.assertEqual(code, 0, out)
        self.assertFalse([l for l in out if l.startswith("stale:")], out)

    def test_help_gives_the_stale_line_and_the_reference(self):
        for text in ("stale: <page> (built from <file>, changed since)", "skills/career-log/pages.md"):
            self.assertIn(text, application.__doc__)


if __name__ == "__main__":
    unittest.main()
