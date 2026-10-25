#!/usr/bin/env python3
"""Tests for tools/writing_lint.py, on small Logs built in a temporary directory with this repo's
writing.md.

  python3 -I tools/tests/test_writing_lint.py
"""
import contextlib, importlib.util, io, os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TOOL = os.path.join(HERE, "..", "writing_lint.py")
spec = importlib.util.spec_from_file_location("writing_lint", TOOL)
writing_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writing_lint)

WRITING = os.path.join(REPO, "skills", "career-log", "writing.md")

RESUME = r"""\documentclass{article}
%% a comment with a word like robust and an em dash --- is not read
\begin{document}
\section*{Skills}
\textbf{Languages:} Go, Python \\
\textbf{Data:} PostgreSQL, Redis
\section*{Experience}
\textbf{Engineer,} Example Corp -- City \hfill Jan 2025 -- May 2025 \\
\begin{itemize}
  \item Built a Go job queue on PostgreSQL that cut p95 queue wait from 820 ms to 210 ms
  \item Designed a Redis rate cache in Python refreshed every five minutes for four regions
\end{itemize}
\end{document}
"""


class WritingLint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "log")
        os.makedirs(os.path.join(self.root, "skills", "career-log"))
        shutil.copy(WRITING, os.path.join(self.root, "skills", "career-log", "writing.md"))
        os.makedirs(os.path.join(self.root, "entries"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rel, body):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        return path

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = writing_lint.main(["--root", self.root] + list(args))
        return code, out.getvalue().splitlines()

    def resume(self, old=None, new=None, name="resume.tex"):
        text = RESUME if old is None else RESUME.replace(old, new, 1)
        self.assertTrue(old is None or old in RESUME, old)
        return self.write(".build/drafts/x/" + name, text)

    def lines_of(self, kind, out):
        return [l for l in out if l.startswith(kind + ": ")]

    def assert_one(self, out, kind, *words):
        hits = [l for l in self.lines_of(kind, out) if all(w in l for w in words)]
        self.assertEqual(len(hits), 1, "\n".join(out))
        return hits[0]

    # ---- clean ----

    def test_clean_resume_and_answers(self):
        a = self.write(".build/drafts/x/answers.md", "# Answers\n\n## Why this team? (100 words)\n\nType: why-us\n\n"
                       "The team runs the queues I have built for two years, and I want to work on them at a larger scale.\n")
        code, out = self.run_tool(self.resume(), a, "--across")
        self.assertEqual(code, 0, "\n".join(out))
        self.assertEqual(self.lines_of("fix", out) + self.lines_of("check", out), [])
        self.assertEqual(out[-1], "OK: no fix lines")
        self.assert_one(out, "count", "Why this team? (100 words)", "22 words", "limit 100 words")

    def test_real_writing_md_has_every_list(self):
        rules = writing_lint.read_rules(REPO)
        for key in ("dash", "phrases", "stock", "openers", "pronouns", "weak", "inflated", "skills_title",
                    "os", "editors", "levels"):
            self.assertTrue(rules[key], key)
        self.assertIn(("leverage", 'as a verb for "use"'), rules["stock"])

    # ---- AI-tell check ----

    def test_em_dash(self):
        a = self.write("a.md", "I built the queue — it worked.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 1)
        self.assert_one(out, "fix", "a.md:1", "em dash")
        code, out = self.run_tool(self.resume("820 ms to 210 ms", "820 ms to 210 ms---a win"))
        self.assert_one(out, "fix", "resume.tex:10", "em dash")
        code, out = self.run_tool(self.resume("820 ms to 210 ms", r"820 ms to 210 ms\textemdash a win"))
        self.assert_one(out, "fix", "resume.tex:10", "em dash")

    def test_en_dash_and_comment_are_clean(self):
        code, out = self.run_tool(self.resume())
        self.assertEqual(self.lines_of("fix", out), [], "\n".join(out))

    def test_phrases_and_openers(self):
        a = self.write("a.md", "## Q\n\nGreat question. This was pivotal for the team.\nIn today’s fast-paced world it matters.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 1)
        self.assert_one(out, "fix", "a.md:3", '"pivotal"', "Say what happened")
        self.assert_one(out, "fix", "a.md:3", '"Great question"', "Start with the answer")
        self.assert_one(out, "fix", "a.md:4", "fast-paced world", "Say what happened")

    def test_stock_words_and_inflections(self):
        a = self.write("a.md", "We built robust tools.\nI showcased the work.\nThe team leveraged the cache.\n")
        code, out = self.run_tool(a)
        self.assert_one(out, "fix", "a.md:1", '"robust"', "Plain words")
        self.assert_one(out, "fix", "a.md:2", '"showcased"')
        hit = self.assert_one(out, "check", "a.md:3", '"leveraged"')
        self.assertIn('as a verb for "use"', hit)

    def test_bold_labels_in_prose(self):
        a = self.write("a.md", "## Q\n\n**Impact:** the queue got faster.\n\n**What I learned**\n\nMore text here.\n")
        code, out = self.run_tool(a)
        self.assert_one(out, "check", "a.md:3", "Label:")
        self.assert_one(out, "check", "a.md:5", "mini-heading")

    def test_skipped_parts_of_prose(self):
        a = self.write("a.md", "## Q\n\nPlain answer.\n\n<!-- robust -->\n| Claim | Entry | Source |\n|---|---|---|\n"
                       "| robust | e › x | y |\n\n```\nrobust\n```\n\n## Risks to handle in conversation\n- robust\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 0, "\n".join(out))

    # ---- word limits ----

    def test_word_and_character_limits(self):
        a = self.write("a.md", "## Why us? (5 words)\n\nOne two three four five six.\n\n"
                       "## Tell us more (max 20 characters)\n\nThis answer is longer than twenty.\n\n"
                       "## No limit here\n\nFine.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 1)
        self.assert_one(out, "fix", "a.md:1", "limit of 5 words")
        self.assert_one(out, "fix", "a.md:5", "limit of 20 characters")
        self.assert_one(out, "count", "No limit here", "1 words")

    # ---- resume bullets ----

    def test_pronouns(self):
        code, out = self.run_tool(self.resume("Built a Go job queue", "Built our Go job queue"))
        self.assert_one(out, "fix", "resume.tex:10", 'pronoun "our"')
        code, out = self.run_tool(self.resume("Built a Go job queue", "Built a Go I/O queue for US clients"))
        self.assertEqual(self.lines_of("fix", out), [], "\n".join(out))

    def test_trailing_period(self):
        code, out = self.run_tool(self.resume("820 ms to 210 ms", "820 ms to 210 ms."))
        self.assert_one(out, "fix", "resume.tex:10", "trailing period")

    def test_weak_and_inflated_openers(self):
        code, out = self.run_tool(self.resume("Built a Go", "Helped build a Go"))
        self.assert_one(out, "fix", "resume.tex:10", 'weak verb "helped"')
        code, out = self.run_tool(self.resume("Designed a Redis", "Spearheaded a Redis"))
        self.assert_one(out, "fix", "resume.tex:11", 'inflated verb "spearheaded"')

    def test_repeated_opening_verb(self):
        code, out = self.run_tool(self.resume("Designed a Redis", "Built a Redis"))
        self.assert_one(out, "check", '"built" opens 2 bullets in Experience')

    def test_metric_first_and_test_counts(self):
        code, out = self.run_tool(self.resume("Built a Go job queue", "40\\% faster Go job queue built"))
        self.assert_one(out, "fix", "resume.tex:10", "opens with its number")
        code, out = self.run_tool(self.resume("for four regions", "with 1,200 unit tests"))
        self.assert_one(out, "fix", "resume.tex:11", "1,200 unit tests")

    def test_references_and_skills_title(self):
        code, out = self.run_tool(self.resume(r"\section*{Skills}", r"\section*{Technical Skills}"))
        self.assert_one(out, "fix", "resume.tex:4", 'titled "Technical Skills"')
        code, out = self.run_tool(self.resume(r"\end{document}", "\\section*{References}\nOn request\n\\end{document}"))
        self.assert_one(out, "fix", "references section")

    def test_skills_items(self):
        code, out = self.run_tool(self.resume("Go, Python", "Go, Python, C/C++, Linux, VS Code, Proficient Rust"))
        self.assert_one(out, "check", '"C/C++"', "comma-separated")
        self.assert_one(out, "fix", '"Linux" is an operating system')
        self.assert_one(out, "fix", '"VS Code" is an editor')
        self.assert_one(out, "fix", '"proficient"')
        hit = self.assert_one(out, "check", '"Proficient Rust"', "in no bullet")
        self.assertNotIn('"Go"', hit)
        self.assertNotIn('"Python"', hit)

    def test_skills_parentheses_labels_and_short_names(self):
        code, out = self.run_tool(self.resume("Go, Python", "Go, Python, C, AWS (EC2, S3)"))
        hit = self.assert_one(out, "check", "in no bullet")
        self.assertIn('"C", "AWS (EC2, S3)"', hit)
        code, out = self.run_tool(self.resume(r"\textbf{Languages:}", r"\textbf{Proficient:}"))
        self.assert_one(out, "fix", '"Proficient": a proficiency label')
        code, out = self.run_tool(self.resume(r"\section*{Skills}", r"\section*{SKILLS}"))
        self.assertEqual(self.lines_of("fix", out), [], "\n".join(out))

    def test_posting_names(self):
        posting = self.write("posting.md", "We use Go, Postgres and Redis.\n")
        code, out = self.run_tool(self.resume(), "--posting", posting)
        self.assert_one(out, "check", '"PostgreSQL" (the posting writes Postgres): not in the posting')
        hit = self.assert_one(out, "check", '"Python": not in the posting')
        self.assertNotIn('"Go"', hit)
        self.assertFalse([l for l in out if '"Redis"' in l])

    def test_skills_line_break_forms(self):
        posting = self.write("posting.md", "We use Python, Go, PostgreSQL and Redis.\n")
        for end in (r"\\", r"\\*", r"\\[2pt]", r"\\ \vspace{2pt}", r"\newline", "\\"):
            with self.subTest(end=end):
                code, out = self.run_tool(self.resume(r"Go, Python \\", "Python, Go " + end), "--posting", posting)
                self.assertEqual(self.lines_of("check", out), [], "\n".join(out))

    # ---- rule 9 ----

    def test_across(self):
        a = self.write(".build/drafts/x/answers.md", "## First\n\nIt cut wait to 210 ms in 2025.\n\n"
                       "## Second\n\nIt also cut wait to 210 ms.\n")
        code, out = self.run_tool(self.resume(), a, "--across")
        hit = self.assert_one(out, "check", "210 appears in 3 artifacts")
        self.assertIn("answers.md › First:3", hit)
        self.assertFalse([l for l in out if "2025 appears" in l or "820 appears" in l])
        code, out = self.run_tool(self.resume(), a)
        self.assertFalse([l for l in out if "appears in" in l])

    # ---- private links ----

    def test_private_links(self):
        self.write("entries/2025-01-private.md", "---\ntitle: P\nvisibility: private\nlinks: [https://github.com/me/secret]\n"
                   "---\n\n## Context\nSee https://docs.example.com/plan.\n")
        self.write("entries/2025-02-public.md", "---\ntitle: Q\nvisibility: public\nlinks: [https://github.com/me/open]\n---\n")
        self.write("entries/2025-03-gap.md", "---\ntitle: G\nvisibility: GAP\nlinks: [https://gitlab.com/grp/sub/proj]\n---\n")
        a = self.write("a.md", "See https://github.com/me/secret/pull/4 and https://github.com/me/open.\n"
                       "Also https://docs.example.com/plan and https://github.com/me/secretive.\n"
                       "And gitlab.com/grp/sub/proj/-/issues/2\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 1)
        self.assert_one(out, "fix", "a.md:1", "github.com/me/secret/pull/4", "2025-01-private.md", "private")
        self.assert_one(out, "check", "a.md:2", "docs.example.com/plan", "a public source it cites may stay")
        self.assert_one(out, "fix", "a.md:3", "2025-03-gap.md", "GAP")
        self.assertFalse([l for l in out if "me/open" in l or "secretive" in l], "\n".join(out))
        code, out = self.run_tool(self.resume(r"\hfill Jan", r"\href{https://github.com/me/secret}{github.com/me/secret} \hfill Jan"))
        self.assert_one(out, "fix", "resume.tex:8", "2025-01-private.md")

    def test_private_link_variants(self):
        self.write("entries/2025-01-private.md", "---\ntitle: P\nvisibility: private\nlinks: [https://github.com/alexdoe/secret]\n---\n")
        a = self.write("a.md", "One https://github.com/alexdoe/secret?tab=readme\nTwo http://GitHub.com/AlexDoe/Secret\n"
                       "Three https://github.com/alexdoe/secret.git\n")
        code, out = self.run_tool(a)
        for n in (1, 2, 3):
            self.assert_one(out, "fix", "a.md:%d" % n, "2025-01-private.md")

    # ---- review regressions ----

    def test_limit_forms_and_unanswered(self):
        a = self.write("a.md", "## Tell us about a project (100-word limit)\n\n" + "word " * 120 + "\n\n"
                       "## Anything else? (max 50 words)\n\n## Two paragraphs (max 9 characters)\n\nabcd\n\nefgh\n")
        code, out = self.run_tool(a)
        self.assert_one(out, "fix", "a.md:1", "limit of 100 words")
        self.assert_one(out, "count", "Anything else?", "0 words")
        self.assert_one(out, "fix", "a.md:7", "limit of 9 characters")

    def test_test_count_forms(self):
        code, out = self.run_tool(self.resume("for four regions", "with 200+ unit and integration tests"))
        self.assert_one(out, "fix", "200+ unit and integration tests")
        code, out = self.run_tool(self.resume("for four regions", "cutting flaky failures from 12 per week to 0 by isolating tests"))
        self.assertFalse([l for l in out if "test count" in l], "\n".join(out))

    def test_math_mode_number_first(self):
        code, out = self.run_tool(self.resume("Built a Go job queue", r"$\sim$40\% faster Go job queue built"))
        self.assert_one(out, "fix", "opens with its number")

    def test_heading_inside_risks_stays_skipped(self):
        a = self.write("a.md", "## Q\n\nPlain.\n\n## Risks to handle in conversation\n\n### The number\n\nIt was pivotal.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 0, "\n".join(out))

    def test_begin_document_in_a_comment(self):
        text = RESUME.replace("\\begin{document}", "% paste this after \\begin{document}\n\\begin{document}", 1)
        p = self.write("c.tex", text.replace("820 ms to 210 ms", "820 ms to 210 ms with a robust cache"))
        code, out = self.run_tool(p)
        self.assert_one(out, "fix", '"robust"')

    def test_annotated_and_profile_links(self):
        self.write("entries/2025-01-private.md", "---\ntitle: P\nvisibility: private\nlinks: [https://github.com/Me/Lab-26 "
                   "(private; mirror, same SHAs), https://gitlab.com/grp/lab (original)]\n---\n")
        self.write("entries/2025-02-gap.md", "---\ntitle: G\nlinks: [https://github.com/me]\n---\n")
        a = self.write("a.md", "One https://github.com/me/lab-26/tree/main/labs\nTwo https://gitlab.com/grp/lab/-/blob/main/x\n"
                       "Three https://github.com/me/public-thing\n")
        code, out = self.run_tool(a)
        self.assert_one(out, "fix", "a.md:1", "2025-01-private.md")
        self.assert_one(out, "fix", "a.md:2", "2025-01-private.md")
        self.assertFalse([l for l in out if "a.md:3" in l and "links" in l], "\n".join(out))

    def test_limit_is_the_last_number(self):
        a = self.write("a.md", "## Name 3 words that describe you (50 words)\n\nCurious, careful and kind, with more words here too.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 0, "\n".join(out))
        self.assert_one(out, "count", "limit 50 words")
        a = self.write("b.md", "## In 50 words, name 3 words that describe you\n\nCurious, careful and kind.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 0, "\n".join(out))
        self.assert_one(out, "count", "limit 50 words")

    def test_skills_label_and_soft(self):
        code, out = self.run_tool(self.resume(r"\textbf{Data:} PostgreSQL, Redis",
                                              r"\textbf{Software Tools:} PostgreSQL, Redis, CI/CD: GitHub Actions"))
        self.assertFalse([l for l in out if "soft skills" in l], "\n".join(out))
        self.assert_one(out, "check", '"CI/CD: GitHub Actions"', "comma-separated")
        code, out = self.run_tool(self.resume("Go, Python", "Go, Python, Linux (Ubuntu), VSCode"))
        self.assert_one(out, "fix", '"Linux (Ubuntu)" is an operating system')
        self.assert_one(out, "fix", '"VSCode" is an editor')

    def test_qualified_and_technical_words(self):
        a = self.write("a.md", "I grew up as a foster child.\nWe measured robustness.\n")
        code, out = self.run_tool(a)
        self.assertEqual(code, 0, "\n".join(out))
        self.assert_one(out, "check", '"foster"', "as a verb")

    def test_bullet_edge_cases(self):
        code, out = self.run_tool(self.resume("for four regions", "for Example Co."))
        self.assertEqual(self.lines_of("fix", out), [], "\n".join(out))
        self.assert_one(out, "check", "abbreviation")
        code, out = self.run_tool(self.resume("for four regions", "from I-V sweeps"))
        self.assertEqual(self.lines_of("fix", out), [], "\n".join(out))
        p = self.write("r.tex", "\\begin{document}\n\\resumeItem{I built a queue in Go.}\n\\end{document}\n")
        code, out = self.run_tool(p)
        self.assert_one(out, "check", "no \\item bullets found")

    def test_dates_are_not_numbers(self):
        a = self.write("a.md", "## A\n\nShipped on 2026-10-18.\n\n## B\n\nUpdated 2025-10-18.\n")
        code, out = self.run_tool(a, "--across")
        self.assertFalse([l for l in out if "appears in" in l], "\n".join(out))

    def test_quoted_example_is_not_listed(self):
        self.reworded('("Great question", "I hope this helps", "In conclusion")',
                      '("Great question", "I hope this helps", "In conclusion"); write "It was the point" instead')
        code, out = self.run_tool(self.write("b.md", "It was the point.\n"))
        self.assertEqual(code, 0, "\n".join(out))

    def test_help(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = writing_lint.main(["--help"])
        self.assertEqual(code, 0)
        self.assertNotIn("FAIL", out.getvalue())

    # ---- writing.md is the one source ----

    def reworded(self, old, new):
        path = os.path.join(self.root, "skills", "career-log", "writing.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace(old, new, 1))
        return self.run_tool(self.write("a.md", "Fine.\n"))

    def test_rewordings_fail_loudly(self):
        for old, new in (("3. **Plain words**", "3. **Use plain words**"),
                         ("tapestry, landscape.", "tapestry, landscape. Prefer short words."),
                         ("delve, leverage", '"delve", "leverage"'),
                         ("not weak (helped", "not weak (e.g. helped")):
            self.tearDown()
            self.setUp()
            code, out = self.reworded(old, new)
            self.assertEqual(code, 2, (old, out))
            self.assertTrue(out[-1].startswith("FAIL: "), out)

    def test_word_added_to_writing_md_is_caught(self):
        path = os.path.join(self.root, "skills", "career-log", "writing.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("tapestry, landscape.", text)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("tapestry, landscape.", "tapestry, landscape, synergy."))
        a = self.write("a.md", "The synergy was clear.\n")
        code, out = self.run_tool(a)
        self.assert_one(out, "fix", '"synergy"')

    def test_lost_list_fails_loudly(self):
        path = os.path.join(self.root, "skills", "career-log", "writing.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("No personal pronouns (I, me, my, we, us, our)", "No personal pronouns"))
        code, out = self.run_tool(self.write("a.md", "Fine.\n"))
        self.assertEqual(code, 2)
        self.assertTrue(out[-1].startswith("FAIL: ") and "personal pronouns" in out[-1], out)

    def test_unreadable_file(self):
        code, out = self.run_tool(os.path.join(self.root, "missing.md"))
        self.assertEqual(code, 2)
        self.assertTrue(out[-1].startswith("FAIL: cannot read"), out)


if __name__ == "__main__":
    unittest.main()
