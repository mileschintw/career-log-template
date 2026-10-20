#!/usr/bin/env python3
"""Tests for tools/skill_lint.py, on small skill trees built in a temporary directory.

  python3 -I tools/tests/test_skill_lint.py
"""
import importlib.util, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "skill_lint.py")
spec = importlib.util.spec_from_file_location("skill_lint", TOOL)
skill_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill_lint)

SKILL_MD = """# Skill

## Settings

## Rules for every mode

- **Commits.** Commit often.
- **Subagents.** Brief them.

## Modes

| Mode | When | File |
|---|---|---|
| **log** | Something happened | [modes/log.md](modes/log.md) |
| **fit** | A posting | [modes/fit.md](modes/fit.md) |
"""

FIT_MD = """# Fit

1. **Read the posting.**
5. **Map each requirement** to an entry.
7. **Check the draft claim by claim** against the entries.

## Save
"""

TREE = {
    "skills/career-log/SKILL.md": SKILL_MD,
    "skills/career-log/modes/fit.md": FIT_MD,
    "skills/career-log/modes/log.md": "# Log\n\nOK.\n",
    "skills/career-log/modes/review.md": "# Review\n\n## Apply the review\n",
    "tools/template/direction.md": "# Direction\n\n## What to emphasise, by target\n\n## Constraints\n",
    "SETUP.md": "# Setup\n\n## 4. Skill link\n\n## How `tools/resume.py` finds its tools\n",
}


class SkillLint(unittest.TestCase):
    def lint(self, text, extra=None):
        """Problems after appending text to modes/log.md, as (line, message)."""
        with tempfile.TemporaryDirectory() as root:
            files = dict(TREE, **(extra or {}))
            files["skills/career-log/modes/log.md"] += text
            for rel, body in files.items():
                path = os.path.join(root, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(body)
            return [(n, msg) for _, n, msg in skill_lint.Linter(root).run()]

    def assertClean(self, text):
        self.assertEqual(self.lint(text), [])

    def assertProblem(self, text, fragment):
        problems = self.lint(text)
        self.assertTrue(any(fragment in msg for _, msg in problems), problems)

    # Passes
    def test_good_pointers_pass(self):
        self.assertClean(
            "See [SKILL.md › Commits](../SKILL.md#rules-for-every-mode) and [SKILL.md › Settings](../SKILL.md#settings).\n"
            "Map as [fit.md](fit.md) step 5 does; fit.md step 7 checks it ([fit.md](fit.md) › *Check the draft claim by claim*).\n"
            "Read `direction.md › What to emphasise` for this target and `direction.md › Constraints`.\n"
            "Follow SKILL.md › Subagents. The skill link (SETUP.md step 4), in the order SETUP.md › How `tools/resume.py` finds its tools gives.\n"
            "Then [review.md › Apply the review](review.md#apply-the-review), the `fit` mode and **log** mode.\n"
        )

    def test_code_block_is_skipped_for_links(self):
        self.assertClean("```\n[x](missing.md)\n```\nInline `[x](missing.md)` too.\n")

    def test_old_name_on_a_line_marked_old_passes(self):
        self.assertClean("Fit reports (and older upskill reports).\n")

    # Failures
    def test_missing_file(self):
        self.assertProblem("See [x](nowhere.md).\n", "link nowhere.md: no such file")

    def test_missing_anchor(self):
        self.assertProblem("See [SKILL.md › Subagents](../SKILL.md#subagents).\n", "no heading with that anchor")

    def test_missing_section_bare(self):
        self.assertProblem("Follow SKILL.md › Comits first.\n", "SKILL.md › Comits")

    def test_missing_section_in_backticks(self):
        self.assertProblem("Read `direction.md › Emphasis` first.\n", "direction.md › Emphasis: no such section")

    def test_missing_section_in_link_text(self):
        self.assertProblem("See [review.md › Timing](review.md#apply-the-review).\n", "review.md › Timing: no such section")

    def test_second_reference_on_a_line_is_checked(self):
        self.assertProblem("Read `direction.md › Constraints`, then SKILL.md › Comits.\n", "SKILL.md › Comits")
        self.assertProblem("Read SKILL.md › Settings, then `direction.md › Emphasis`.\n", "direction.md › Emphasis")

    def test_missing_section_file(self):
        self.assertProblem("See `nothing.md › Section`.\n", "nothing.md: no such file")

    def test_missing_step(self):
        self.assertProblem("As fit.md step 6 does.\n", "fit.md step 6: no such step")
        self.assertProblem("As [fit.md](fit.md) step 9 does.\n", "step 9: no such step")

    def test_retired_mode_anywhere(self):
        self.assertProblem("Run upskill on the postings.\n", "mode upskill")

    def test_unknown_mode_in_mode_context(self):
        self.assertProblem("Use the `apply` mode.\n", "mode apply")
        self.assertProblem("Use **apply** mode.\n", "mode apply")

    def test_ordinary_word_is_not_a_mode(self):
        self.assertClean("Apply the review, then apply to the posting.\n")

    def test_slug(self):
        self.assertEqual(skill_lint.slug("Perplexity (perplexity.ai)"), "perplexity-perplexityai")
        self.assertEqual(skill_lint.slug("How `tools/resume.py` finds its tools"), "how-toolsresumepy-finds-its-tools")
        self.assertEqual(skill_lint.slug("4. Skill link"), "4-skill-link")

    def test_repo_skill_passes(self):
        """The skill in this repo passes the lint as committed."""
        p = subprocess.run([sys.executable, "-I", TOOL], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
