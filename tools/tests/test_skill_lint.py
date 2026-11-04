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

    def test_template_readme_links_resolve_as_exported(self):
        """tools/template/README.md is served at the root: its links resolve from there, a skeleton
        file it names (LICENSE, both.md) from tools/template/ first."""
        readme = ("[license](LICENSE) [skill](skills/career-log/SKILL.md#modes) [setup](SETUP.md)"
                  " [gone](missing.md) [here](#entries) [both](both.md#skeleton)\n\n## Entries\n")
        problems = self.lint("", {"tools/template/README.md": readme, "tools/template/LICENSE": "MIT\n",
                                  "tools/template/both.md": "## Skeleton\n", "both.md": "## Root\n"})
        self.assertEqual(problems, [(1, "link missing.md: no such file")])

    def test_check_mode_lists_match_the_skill(self):
        """check.py's MODES is the modes table but NO_CHECK, and NEEDS's playwright-cli modes are the
        modes whose files link browser.md, a modes/<mode>-<part>.md counting for <mode> (Finding 13)."""
        links = "Read [browser.md](../browser.md).\n"
        check_py = ('MODES = ["log", "fit"%s]\nNEEDS = {"fit": [("playwright-cli", "soft")]%s,'
                    ' "setup": [("playwright-cli", "soft")], "browser": [("playwright-cli", "soft")]}\n')
        tree = {"skills/career-log/modes/fit-several.md": links, "skills/career-log/browser.md": "# Browser\n",
                "tools/check.py": check_py % ("", "")}
        self.assertEqual(self.lint("", tree), [])
        problems = self.lint("", dict(tree, **{"tools/check.py": check_py % (', "deploy"', "")}))
        self.assertTrue(any("MODES differs" in m and "deploy" in m for _, m in problems), problems)
        problems = self.lint(links, tree)   # log links browser.md, but NEEDS has no log
        self.assertTrue(any("['log'] only linking" in m for _, m in problems), problems)
        problems = self.lint("", dict(tree, **{"tools/check.py": check_py % ("", ', "log": [("playwright-cli", "soft")]')}))
        self.assertTrue(any("['log'] only in NEEDS" in m for _, m in problems), problems)

    # Printed lines: a `x:` line a mode says a tool prints is a literal in the tool's source
    PRINTS = ('"""Prints `leads: ok` and `gone: <x>`."""\nimport helper\n'
              'def run(n, kind, x):\n    """Prints `ghost: <x>`."""\n'
              '    print("leads: ok, %d question(s)" % n)\n    print("readme %s: README.md:%d" % (kind, n))\n'
              '    print(f"cite: {x} (entry)")\n    tag = "sent before"\n    print("%s: %s" % (tag, x))\n    print("entries: ok")\n')
    TOOLS = {"tools/entries.py": PRINTS, "tools/other.py": "from helper import x\n",
             "tools/helper.py": 'print("similar: %s" % 1)\nprint("rate: 5%%s" % 1)\n',
             "tools/check.py": 'MODES = ["log", "fit"]\nNEEDS = {}\nprint("next: go on with the mode")\n'}

    def test_printed_line_found_in_the_tool(self):
        """A literal, one with a placeholder in it (%-format or f-string), a tag the tool formats
        into a label, and a line from a tool it imports all count; so do a tool named earlier on
        the line, a `<alias>` a skill file defines, and a label that names its tool."""
        self.assertEqual(self.lint(
            "Run `python3 -I <root>/tools/entries.py story-leads` until it prints `leads: ok`.\n"
            "`entries.py readme` printed `readme written:`; it then prints a `cite: <x> (entry)` line.\n"
            "It prints `sent before: <x>` lines. When it prints `similar:` lines, read them.\n"
            "`other.py x` prints `similar:` lines and `rate: 5%`.\n"
            "Run `check.py log`. On this line it printed `next: go on with the mode`.\n"
            "`<ent>` is `python3 -I <root>/tools/entries.py`. `<ent> x` prints `leads: ok, <n> question(s)`.\n"
            "Then `sync.py commit` prints `entries: ok`.\n", self.TOOLS), [])

    def test_printed_line_missing_from_the_tool(self):
        """D1 of #651: a mode waited for a line the tool never prints. A docstring is not output."""
        problems = self.lint("Run `entries.py story-leads` until it prints `leads: none predicted`.\n"
                             "`entries.py x` prints `gone: <x>` and `ghost:` lines.\n", self.TOOLS)
        self.assertEqual(problems, [(4, "prints `leads: none predicted`: not in tools/entries.py"),
                                    (5, "prints `gone: <x>`: not in tools/entries.py"),
                                    (5, "prints `ghost:`: not in tools/entries.py")])

    def test_printed_line_needs_a_print_verb_and_a_tool(self):
        """A file's line, a commit subject or a line far from the verb is not a printed line, and a
        line naming no tool has none to check."""
        self.assertEqual(self.lint(
            "Run `entries.py x`. Write the `Lead: none` line, then the `missing: x` line; the entry keeps its"
            " `Type: x` line, and git prints nothing.\nThe check prints `missing: x`.\n", self.TOOLS), [])

    def test_repo_skill_passes(self):
        """The skill in this repo passes the lint as committed."""
        p = subprocess.run([sys.executable, "-I", TOOL], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_help(self):
        for flag in ("--help", "-h"):
            p = subprocess.run([sys.executable, "-I", TOOL, flag], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, flag)
            self.assertEqual(p.stdout.splitlines(), skill_lint.__doc__.splitlines(), flag)


if __name__ == "__main__":
    unittest.main()
