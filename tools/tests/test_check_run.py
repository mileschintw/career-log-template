#!/usr/bin/env python3
"""Tests for tools/check_run.py, on small transcripts and scratch copies built in a temporary directory.

  python3 -I tools/tests/test_check_run.py

Each check has a passing and a failing case. Needs git on the PATH.
"""
import contextlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "check_run.py")
spec = importlib.util.spec_from_file_location("check_run", TOOL)
check_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_run)

ROOT = "/tmp/t/log"
POINTER = ('Read %s/skills/career-log/modes/review.md whole, in one read, and follow its section '
           '"Reviewer instructions" for the log at %s.')
HUMANIZER = ("Call the Skill tool with the humanizer skill first, then run it on the text below. Keep every "
             "fact, its length and these AI-tell rules: 1 no em dashes. Edit no file. Reply with the edited "
             "text only.\nBuilt a queue.")
SCREEN = ('Read %s/skills/career-log/modes/fit.md whole and follow its section "Screen" for the captures listed '
          'in %s/.build/scan/2026-02-01/screen/batch-1.todo, writing %s/.build/scan/2026-02-01/screen/batch-1.jsonl.')
FIT = ('Read %s/skills/career-log/modes/fit.md whole and follow its "Handed over by scan" bullet for the capture at %s, '
       'writing %s.')
SCAN_MD = ("# Scan\n\n3. **Start one subagent per batch,** of a type that writes files. Its prompt's first line is `"
           + SCREEN % ("<root>", "<dir>", "<dir>") + "`; the rest is the Log root.\n"
           "3. Start one subagent per posting to fit, of the type step 6.3 names. Its prompt's first line is `"
           + FIT % ("<root>", "<capture path>", "<dir>/fit/<folder>.jsonl") + "`.\n")
REVIEW_MD = "# Review\n\n## Dispatch\n\nFirst line: `" + POINTER % ("<root>", "<root>") + "` Then the drafts.\n"
WRITE_MD = ("# Write\n\n10. Once the check has exited 0: `python3 -I <root>/tools/sync.py commit \"<subject>\" -- <file>...`, "
            "with the subject `write(<company>): <role>` for a posting run, `write(<slug>): <target>` otherwise.\n")
MODES_MD = {"log.md": "4. **Commit and push:** `python3 -I <root>/tools/sync.py commit \"log(<slug>): <milestone>\" -- <file>...`.\n",
            "consolidate.md": "7. **Commit and push**: `python3 -I <root>/tools/sync.py commit \"consolidate(<slugs>): <summary>\" -- <file>...`\n",
            "import.md": "7. Commit as *Bulk data changes* says: `import: <n> file(s), <m> entr(y/ies)`.\n",
            "scan.md": "9. `python3 -I <root>/tools/sync.py commit \"<the subject of its commit: line>\" -- <report>`.\n"}


def text(t):
    return {"type": "text", "text": t}


def agent(desc, prompt, model="sonnet", kind="Explore"):
    inp = {"description": desc, "subagent_type": kind, "prompt": prompt}
    if model:
        inp["model"] = model
    return {"type": "tool_use", "name": "Agent", "input": inp}


def bash(cmd):
    return {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}


def lookup(model="sonnet"):
    return agent("Company lookup", 'Read /log/skills/career-log/modes/write.md whole and follow its section "Company lookup".\n\n'
                 "Company: Example Corp. No H-1B LCA lookup requested.", model)


def reviewer(model="sonnet", first=None):
    return agent("Review drafts", (first or POINTER % (ROOT, ROOT)) + "\n<posting>...</posting>", model)


def humanizer(model="sonnet"):
    return agent("Humanizer pass", HUMANIZER, model)


REVIEWER_LINE = text("Reviewer call: model Sonnet 5.5, log root " + ROOT)
HUMANIZER_LINE = text("Humanizer call: model Sonnet 5.5")
HUMANIZER_AFTER = "Humanizer after review: Built a queue. → Humanizer call: model Sonnet 5.5"
PROVENANCE_LINE = ("Provenance check (%s/provenance.md): 2 rows; citing another output: none"
                   % "outputs/applications/2026-02-01-example-engineer")
COMMIT = bash("git -C /tmp/t/log commit -m 'write(example): Engineer' && git push")


def result(out, error=False):
    """The tool result of the tool call just before it: a user message, an error when error is set."""
    return {"type": "tool_result", "content": ("Exit code 1\n" if error else "") + out, "is_error": error}


def checked(*lines, ok=True, cmd="python3 -I tools/check_save.py outputs/applications/2026-02-01-example-engineer "
                                 "--humanizer .build/humanizer.txt"):
    """A tools/check_save.py call and its output: these lines, then its last line."""
    out = "\n".join(lines + ("check_save: ok" if ok else "check_save: fix the lines above, then run it again",))
    return [bash(cmd), result(out, error=not ok)]


GOOD_RUN = [lookup(), HUMANIZER_LINE, humanizer(), REVIEWER_LINE, reviewer(), HUMANIZER_LINE, humanizer(),
            *checked(PROVENANCE_LINE, HUMANIZER_AFTER), COMMIT, text("Saved.")]
MAP = "Map: 10 requirements and duties, 11 rows; no row: none"
COURSE = "Course work: none (4 entries listed)"
TABLE = "| Requirement | Kind | Written by | Own work | Category | Entry |\n|---|---|---|---|---|---|\n| Go | required | user | - | covered | 2025-01-widget.md |"


def fit_map(map_line=MAP, course=COURSE, cmd="py -3 -I tools/fit.py --root C:/t/log map .build/fit/2026-10-24-a-b.jsonl"):
    """A tools/fit.py map call and its output."""
    return [bash(cmd), result("%s\n%s\n\n%s\n\nmap: ok" % (course, map_line, TABLE), error="no row: none" not in map_line)]


SHOWN = text("Here is the map.\n\n%s\n%s\n\n%s" % (COURSE, MAP, TABLE))


def write_transcript(path, blocks, model=None):
    """A run made of these blocks: each tool_use gets an id, and each tool_result block goes in a user
    message answering the tool_use before it."""
    last = None
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "Apply to a posting"}}) + "\n")
        for n, b in enumerate(blocks):
            if b.get("type") == "tool_result":
                rec = {"type": "user", "message": {"role": "user", "content": [dict(b, tool_use_id=last)]}}
            else:
                if b.get("type") == "tool_use":
                    last = "toolu_%d" % n
                    b = dict(b, id=last)
                msg = {"role": "assistant", "content": [b]}
                if model:
                    msg["model"] = model
                rec = {"type": "assistant", "message": msg}
            f.write(json.dumps(rec) + "\n")


def transcript(tmp, blocks, model=None):
    """The events and subagent calls of a run made of these blocks."""
    path = os.path.join(tmp, "run.jsonl")
    write_transcript(path, blocks, model)
    evs = check_run.events(path)
    return evs, check_run.subagent_calls(evs)

ENTRY = """---
type: work
---
# Queue service

## What happened
Built a job queue. (user, 2026-01-02)

## Past phrasings
<!-- Reusable wordings. -->
- **backend:** "Built a job queue that retried failed tasks within one second." (sources/resumes/2026-01-old.tex)
- **general:** "Designed the retry policy for a job queue used by three teams." (sources/resumes/2026-01-old.tex)

## Conflicts
"""

PROVENANCE = """# Provenance

| Claim | Entry section | Source |
|---|---|---|
| Built a job queue | 2026-01-queue › What happened | (user, 2026-01-02) |
| Retry within one second | 2026-01-queue › Past phrasings | sources/resumes/2026-01-old.tex |

## Company context

| Fact | URL |
|---|---|
| Example Corp runs queues | https://example.com/outputs/blog |

## Risks to handle in conversation
- The one-second figure is from one run.
"""

TEX = "\\documentclass{article}\n\\begin{document}Resume\\end{document}\n"
FOLDER = "outputs/applications/2026-02-01-example-engineer"


class Transcript(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def calls(self, blocks, model=None):
        return transcript(self.tmp, blocks, model)

    def test_kinds_by_first_line(self):
        _, calls = self.calls(GOOD_RUN)
        self.assertEqual([k for _, k, _ in calls], ["other", "humanizer", "reviewer", "humanizer"])

    def test_models_pass(self):
        self.assertEqual(check_run.check_models(self.calls(GOOD_RUN)[1])[0], "PASS")

    def test_reviewer_without_model_fails(self):
        grade, ev = check_run.check_models(self.calls([lookup(), reviewer(model=None), humanizer()])[1])
        self.assertEqual(grade, "FAIL")
        self.assertIn("reviewer", ev)

    def test_humanizer_without_model_fails(self):
        self.assertEqual(check_run.check_models(self.calls([reviewer(), humanizer(model=None)])[1])[0], "FAIL")

    def test_lookup_without_model_is_a_note(self):
        self.assertEqual(check_run.check_models(self.calls([lookup(model=None), reviewer(), humanizer()])[1])[0], "NOTE")

    def test_subagent_on_another_model_than_the_run_is_a_note(self):
        grade, ev = check_run.check_models(*reversed(self.calls(GOOD_RUN, model="claude-opus-5-5")))
        self.assertEqual(grade, "NOTE")
        self.assertIn("the run on opus", ev)
        self.assertEqual(check_run.check_models(*reversed(self.calls(GOOD_RUN, model="claude-sonnet-5-5")))[0], "PASS")

    def test_lookup_described_with_reviews_is_not_the_reviewer(self):
        _, calls = self.calls([agent("Look up Example Corp reviews", "Find employee reviews of Example Corp.")])
        self.assertEqual([k for _, k, _ in calls], ["other"])

    def test_type_not_read_only_is_a_note(self):
        blocks = [agent("Company lookup", "Look up Example Corp.", kind="general-purpose"), reviewer(), humanizer()]
        self.assertEqual(check_run.check_models(self.calls(blocks)[1])[0], "NOTE")

    def screen(self, model="opus", kind="general-purpose", first=None):
        """A scan Screen batch: by default the prompt scan.md gives, on a Windows path."""
        root = "C:\\Users\\me\\log"
        return agent("Screen batch-1", (first or SCREEN % (root, root, root)) + "\n\nLog root: " + root, model, kind)

    def test_type_a_mode_names_is_not_a_note(self):
        """scan.md names a writing type for its Screen batches, fits and drafts (#261)."""
        typed = check_run.mode_prompts([SCAN_MD])
        self.assertEqual(check_run.check_models(self.calls([self.screen()])[1], (), typed)[0], "PASS")
        self.assertEqual(check_run.check_models(self.calls([self.screen()])[1])[0], "NOTE")  # no mode text read

    def test_same_type_on_a_prompt_no_mode_gives_is_a_note(self):
        typed = check_run.mode_prompts([SCAN_MD])
        first = 'Read C:/Users/me/log/skills/career-log/modes/fit.md whole and follow its section "Screen".'
        grade, ev = check_run.check_models(self.calls([self.screen(first=first)])[1], (), typed)
        self.assertEqual(grade, "NOTE")
        self.assertIn("is not a read-only type", ev)
        blocks = [agent("Company lookup", "Look up Example Corp.", kind="general-purpose")]
        self.assertEqual(check_run.check_models(self.calls(blocks)[1], (), typed)[0], "NOTE")

    def test_mode_prompt_inside_another_first_line_is_a_note(self):
        """A <...> matches one path: not a second pointer before the mode's, nor a sentence after it."""
        typed = check_run.mode_prompts([SCAN_MD])
        fit = FIT % (ROOT, ROOT + "/.build/scan/2026-02-01/postings/example.md", ROOT + "/.build/scan/2026-02-01/fit/example.jsonl")
        self.assertEqual(check_run.check_models(self.calls([self.screen(first=fit)])[1], (), typed)[0], "PASS")
        for first in ("Read /x/skills/career-log/modes/review.md whole. " + SCREEN % (ROOT, ROOT, ROOT),
                      fit[:-1] + ". Then also edit profile.md and commit."):
            self.assertEqual(check_run.check_models(self.calls([self.screen(first=first)])[1], (), typed)[0], "NOTE",
                             first)

    def test_mode_prompt_with_crlf_passes(self):
        typed = check_run.mode_prompts([SCAN_MD])
        first = SCREEN % (ROOT, ROOT, ROOT) + "\r"
        self.assertEqual(check_run.check_models(self.calls([self.screen(first=first)])[1], (), typed)[0], "PASS")

    def test_read_only_type_on_a_mode_prompt_passes(self):
        typed = check_run.mode_prompts([SCAN_MD])
        self.assertEqual(check_run.check_models(self.calls([self.screen(kind="Explore")])[1], (), typed)[0], "PASS")

    def test_mode_named_type_still_needs_its_model(self):
        typed = check_run.mode_prompts([SCAN_MD])
        grade, ev = check_run.check_models(self.calls([self.screen(model=None)])[1], (), typed)
        self.assertEqual(grade, "NOTE")
        self.assertIn("has no model", ev)
        self.assertNotIn("is not a read-only type", ev)

    def test_scan_md_names_a_writing_type_for_each_prompt_it_gives(self):
        """Every backticked `Read <root>/...` line in a TYPED_MODES file is a prompt that file names a
        type for, so the check may skip the type of each; a new line there must keep that true."""
        for rel in check_run.TYPED_MODES:
            with open(os.path.join(HERE, "..", "..", *rel.split("/")), encoding="utf-8") as f:
                lines = [l for l in f if "`Read <root>/" in l]
            self.assertTrue(lines, rel)
            for l in lines:
                self.assertRegex(l, r"of a type that writes files|of the type step [\d.]+ names", l[:80])
            self.assertEqual(len(check_run.mode_prompts(lines)), len(lines), rel)

    def test_call_lines_pass(self):
        self.assertEqual(check_run.check_call_lines(*self.calls(GOOD_RUN))[0], "PASS")

    def test_missing_call_line_is_a_note(self):
        grade, ev = check_run.check_call_lines(*self.calls([lookup(), reviewer(), HUMANIZER_LINE, humanizer()]))
        self.assertEqual(grade, "NOTE")
        self.assertIn("no Reviewer call line", ev)

    def test_call_line_in_a_tool_call_is_a_note(self):
        blocks = [bash('echo "Reviewer call: model sonnet, log root %s"' % ROOT), reviewer(), HUMANIZER_LINE, humanizer()]
        grade, ev = check_run.check_call_lines(*self.calls(blocks))
        self.assertEqual(grade, "NOTE")
        self.assertIn("written in a tool call", ev)

    def test_call_line_naming_another_model_fails(self):
        blocks = [text("Reviewer call: model Opus 5.5, log root " + ROOT), reviewer(), HUMANIZER_LINE, humanizer()]
        self.assertEqual(check_run.check_call_lines(*self.calls(blocks))[0], "FAIL")

    def test_bold_call_line_is_read(self):
        blocks = [text("**Reviewer call:** model Opus 5.5, log root " + ROOT), reviewer(), HUMANIZER_LINE, humanizer()]
        self.assertEqual(check_run.check_call_lines(*self.calls(blocks))[0], "FAIL")

    def test_unparsed_call_line_fails(self):
        blocks = [text("Reviewer call: Opus, root " + ROOT), reviewer(), HUMANIZER_LINE, humanizer()]
        grade, ev = check_run.check_call_lines(*self.calls(blocks))
        self.assertEqual(grade, "FAIL")
        self.assertIn("does not parse", ev)

    def test_task_tool_name_counts(self):
        blocks = [dict(reviewer(), name="Task")]
        self.assertEqual([k for _, k, _ in self.calls(blocks)[1]], ["reviewer"])

    def test_humanizer_call_line_naming_another_model_fails(self):
        blocks = [REVIEWER_LINE, reviewer(), text("Humanizer call: model Haiku 5.5"), humanizer()]
        self.assertEqual(check_run.check_call_lines(*self.calls(blocks))[0], "FAIL")

    def test_call_line_in_conversation_then_echoed_pass(self):
        blocks = [REVIEWER_LINE, bash('echo "Reviewer call: model sonnet, log root %s"' % ROOT), reviewer(),
                  HUMANIZER_LINE, humanizer()]
        self.assertEqual(check_run.check_call_lines(*self.calls(blocks))[0], "PASS")

    def test_call_line_before_an_earlier_call_does_not_count(self):
        blocks = [REVIEWER_LINE, reviewer(), HUMANIZER_LINE, humanizer(), reviewer(), HUMANIZER_LINE, humanizer()]
        grade, ev = check_run.check_call_lines(*self.calls(blocks))
        self.assertEqual(grade, "NOTE")
        self.assertEqual(ev.count("no Reviewer call line"), 1)

    def test_reviewer_prompt_pass(self):
        self.assertEqual(check_run.check_reviewer_prompt(self.calls(GOOD_RUN)[1], REVIEW_MD)[0], "PASS")

    def test_reviewer_prompt_reworded_fails(self):
        first = (POINTER % (ROOT, ROOT)).replace("whole, in one read", "whole")
        self.assertEqual(check_run.check_reviewer_prompt(self.calls([reviewer(first=first)])[1], REVIEW_MD)[0], "FAIL")

    def test_reviewer_prompt_with_backslashes_pass(self):
        win = "C:\\t\\log"
        first = (POINTER % (win, win)).replace("/", "\\")
        self.assertEqual(check_run.check_reviewer_prompt(self.calls([reviewer(first=first)])[1], REVIEW_MD)[0], "PASS")

    def test_reviewer_prompt_two_roots_fails(self):
        first = POINTER % (ROOT, "/tmp/t2/log")
        self.assertEqual(check_run.check_reviewer_prompt(self.calls([reviewer(first=first)])[1], REVIEW_MD)[0], "FAIL")

    def test_reviewer_prompt_with_a_preface_line_fails(self):
        """A drifted first line still marks the call as the reviewer, so its checks still run."""
        first = "You are a hiring-manager proxy.\n" + POINTER % (ROOT, ROOT)
        evs, calls = self.calls([reviewer(model=None, first=first)])
        self.assertEqual([k for _, k, _ in calls], ["reviewer"])
        self.assertEqual(check_run.check_reviewer_prompt(calls, REVIEW_MD)[0], "FAIL")
        self.assertEqual(check_run.check_models(calls)[0], "FAIL")
        self.assertEqual(check_run.check_humanizer_after_review(calls)[0], "FAIL")

    def test_reviewer_without_the_pointer_is_a_reviewer(self):
        """An older reviewer prompt, with the instructions copied in, is still graded as the reviewer."""
        _, calls = self.calls([agent("Review drafts", "You are a hiring-manager proxy and a fact checker.", model=None)])
        self.assertEqual([k for _, k, _ in calls], ["reviewer"])
        self.assertEqual(check_run.check_models(calls)[0], "FAIL")

    def test_humanizer_described_by_the_review_is_a_humanizer(self):
        _, calls = self.calls([agent("Humanizer on review-changed text", HUMANIZER)])
        self.assertEqual([k for _, k, _ in calls], ["humanizer"])

    def test_humanizer_with_a_preface_line_is_a_humanizer(self):
        _, calls = self.calls([agent("Polish", "Polish this text.\n" + HUMANIZER, model=None)])
        self.assertEqual([k for _, k, _ in calls], ["humanizer"])
        self.assertEqual(check_run.check_models(calls)[0], "FAIL")

    def test_root_note_survives_a_failed_first_line(self):
        drifted = reviewer(first=(POINTER % ("/tmp/main/log", "/tmp/main/log")).replace("whole, in one read", "whole"))
        _, calls = self.calls([reviewer(), drifted])
        grade, ev = check_run.check_reviewer_prompt(calls, REVIEW_MD, ROOT)
        self.assertEqual(grade, "FAIL")
        self.assertIn("is not the copy", ev)

    def test_git_bash_root_matches(self):
        self.assertEqual(check_run.norm("/c/Users/t/log/"), check_run.norm("C:\\Users\\t\\log"))

    def test_reviewer_root_not_the_copy_is_a_note(self):
        _, calls = self.calls(GOOD_RUN)
        self.assertEqual(check_run.check_reviewer_prompt(calls, REVIEW_MD, ROOT + "/")[0], "PASS")
        self.assertEqual(check_run.check_reviewer_prompt(calls, REVIEW_MD, "/tmp/main/log")[0], "NOTE")

    def test_pointer_line_matches_the_skill(self):
        """The repo's own review.md still has the pointer line this script reads."""
        with open(os.path.join(HERE, "..", "..", "skills", "career-log", "modes", "review.md"), encoding="utf-8") as f:
            tmpl, rx = check_run.pointer_line(f.read())
        self.assertIsNotNone(rx)
        self.assertTrue(rx.match(tmpl.replace("<root>", ROOT)))

    def test_humanizer_after_review_pass(self):
        self.assertEqual(check_run.check_humanizer_after_review(self.calls(GOOD_RUN)[1])[0], "PASS")

    def test_humanizer_only_before_review_fails(self):
        blocks = [lookup(), humanizer(), reviewer(), text("Saved.")]
        self.assertEqual(check_run.check_humanizer_after_review(self.calls(blocks)[1])[0], "FAIL")

    def test_scoped_review_without_humanizer_fails(self):
        blocks = [reviewer(), humanizer(), reviewer(), text("Saved.")]
        grade, ev = check_run.check_humanizer_after_review(self.calls(blocks)[1])
        self.assertEqual(grade, "FAIL")
        self.assertIn("to the end of the run", ev)

    def test_no_reviewer_skips(self):
        self.assertEqual(check_run.check_humanizer_after_review(self.calls([lookup()])[1])[0], "SKIP")

    def map_count(self, blocks):
        return check_run.check_map_count(self.calls(blocks)[0])

    def test_map_count_pass(self):
        grade, ev = self.map_count([*fit_map(), SHOWN])
        self.assertEqual(grade, "PASS", ev)

    def test_map_count_rerun_until_none_pass(self):
        first = fit_map("Map: 10 requirements and duties, 9 rows; no row: mentoring junior engineers")
        self.assertEqual(self.map_count([*first, *fit_map(), SHOWN])[0], "PASS")

    def test_map_count_naming_a_missing_row_fails(self):
        grade, ev = self.map_count(fit_map("Map: 10 requirements and duties, 9 rows; no row: mentoring junior engineers"))
        self.assertEqual(grade, "FAIL")
        self.assertIn("names requirements with no row", ev)

    def test_map_count_fewer_rows_saying_none_fails(self):
        self.assertEqual(self.map_count(fit_map("Map: 10 requirements and duties, 7 rows; no row: none"))[0], "FAIL")

    def test_map_shown_unlike_the_tool_fails(self):
        typed = text(SHOWN["text"].replace("11 rows", "12 rows"))
        grade, ev = self.map_count([*fit_map(), typed])
        self.assertEqual(grade, "FAIL")
        self.assertIn("fit.py printed", ev)
        course = text(SHOWN["text"].replace("(4 entries", "(5 entries"))
        self.assertEqual(self.map_count([*fit_map(), course])[0], "FAIL")

    def test_map_shown_without_its_map_line_fails(self):
        grade, ev = self.map_count([*fit_map(), text(COURSE + "\n\n" + TABLE)])
        self.assertEqual(grade, "FAIL")
        self.assertIn("no Map: line above its table", ev)

    def test_map_table_shown_without_its_lines_fails(self):
        """#511: a Requirement table shown with neither the Course work: nor the Map: line; the heatmap is no map."""
        reworded = text("## Requirement map\nOf 11 rows, 1 is covered.\n\n| Requirement | Category | Entry |\n|---|---|---|\n| Go | covered | widget |")
        grade, ev = self.map_count([*fit_map(), reworded])
        self.assertEqual(grade, "FAIL")
        self.assertIn("no Map: line above its table; the map shown has no Course work: line", ev)
        interview = fit_map(cmd='py -3 -I tools/fit.py map m.jsonl --category gap --category "claimed, unbacked"')
        self.assertEqual(self.map_count([*interview, reworded])[0], "PASS")   # a map not to show: its rows may be quoted
        self.assertEqual(self.map_count([text("Here is the map.\n\n" + TABLE)])[0], "SKIP")   # no fit.py map run
        heatmap = text("| Priority | Skill | Category | Postings | Which |\n|---|---|---|---|---|\n| high | Go | covered | 2 | a, b |")
        self.assertEqual(self.map_count([*fit_map(), heatmap])[0], "PASS")

    def test_map_line_after_the_table_fails(self):
        self.assertEqual(self.map_count([*fit_map(), text(COURSE + "\n\n" + TABLE + "\n\n" + MAP)])[0], "FAIL")

    def test_map_line_with_no_tool_output_fails(self):
        grade, ev = self.map_count([text(MAP), SHOWN])
        self.assertEqual(grade, "FAIL")
        self.assertIn("no tools/fit.py map output", ev)
        echo = bash("echo '%s'" % MAP)
        self.assertEqual(self.map_count([echo])[0], "FAIL")
        self.assertEqual(self.map_count([text(COURSE + "\n\n" + TABLE)])[0], "FAIL")

    def test_map_not_shown_is_graded_by_the_tool(self):
        """interview: the map is built and not shown; fit.py's lines grade it."""
        cmd = 'python3 -I tools/fit.py map .build/fit/m.jsonl --category gap --category "claimed, unbacked"'
        grade, ev = self.map_count(fit_map(cmd=cmd))
        self.assertEqual(grade, "PASS", ev)

    def test_map_count_per_posting(self):
        a = "Map (Example Corp, Engineer): 10 requirements and duties, 10 rows; no row: none"
        b = "Map (Other Inc, SRE): 12 requirements and duties, 11 rows; no row: on-call"
        fixed = b.replace("11 rows; no row: on-call", "12 rows; no row: none")
        self.assertEqual(self.map_count([*fit_map(a), *fit_map(b)])[0], "FAIL")
        self.assertEqual(self.map_count([*fit_map(a), *fit_map(b), *fit_map(fixed)])[0], "PASS")

    def test_map_shown_bold_reads_the_same(self):
        bold = text("**Course work:** none (4 entries listed)\n**Map:** **10** requirements and duties, **11** rows; no row: none\n\n" + TABLE)
        self.assertEqual(self.map_count([*fit_map(), bold])[0], "PASS")

    def test_map_run_that_printed_bad_lines_fails(self):
        blocks = [bash("py -3 -I tools/fit.py map m.jsonl"),
                  result("%s\n%s\n\n%s\n\nbad: rows[1].category: covered, but written by unknown; at most shallow"
                         % (COURSE, MAP, TABLE), error=True), SHOWN]
        grade, ev = self.map_count(blocks)
        self.assertEqual(grade, "FAIL")
        self.assertIn("printed bad: lines", ev)

    def test_map_run_output_with_crlf_lines(self):
        """Windows: the tool's lines end in CRLF in the tool result."""
        out = "%s\n%s\n\n%s\n\nmap: ok\nexit 0" % (COURSE, MAP, TABLE)
        blocks = [bash("py -3 -I tools/fit.py map m.jsonl; echo \"exit $?\""), result(out.replace("\n", "\r\n")), SHOWN]
        grade, ev = self.map_count(blocks)
        self.assertEqual(grade, "PASS", ev)

    def test_a_later_course_work_mention_is_not_the_map(self):
        recap = text("Done.\n\nCourse work: none (4 entries listed)")
        self.assertEqual(self.map_count([*fit_map(), SHOWN, recap])[0], "PASS")

    def test_map_run_commands_other_shells(self):
        for cmd in ("& py -3 -I \"C:\\t\\log\\tools\\fit.py\" --root \"C:\\t\\log\" map .build/fit/m.jsonl",
                    "python3 -I tools/fit.py --root /t/log \\\n  map .build/fit/m.jsonl",
                    "py -3 -I tools/fit.py --root C:/t/log `\n  map .build/fit/m.jsonl"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.map_count([*fit_map(cmd=cmd), SHOWN])[0], "PASS")

    def test_role_with_parentheses_is_read(self):
        line = "Map (Example Corp, Software Engineer (Infrastructure)): 10 requirements and duties, 9 rows; no row: none"
        self.assertEqual(self.map_count(fit_map(line))[0], "FAIL")

    def test_fit_check_is_not_a_map_run(self):
        check = [bash("py -3 -I tools/fit.py check fit/a.jsonl --capture postings/map.md"), result("check: ok")]
        self.assertEqual(self.map_count([*check, SHOWN])[0], "FAIL")

    def test_no_map_skips(self):
        self.assertEqual(self.map_count(GOOD_RUN)[0], "SKIP")


class CopyBase(unittest.TestCase):
    """A scratch copy: a base commit holding one entry, then the run's save on top."""

    def setUp(self):
        self.copy = tempfile.mkdtemp()
        self.git("init", "-q")
        self.write(".gitignore", ".build/\n")
        self.write("entries/2026-01-queue.md", ENTRY)
        self.write("outputs/resumes/backend.tex", TEX)
        self.write("skills/career-log/modes/review.md", REVIEW_MD)
        self.write("skills/career-log/modes/write.md", WRITE_MD)
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        shutil.rmtree(self.copy, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))

    def git(self, *args):
        return subprocess.run(["git", "-C", self.copy, "-c", "user.email=test@example.invalid", "-c", "user.name=Test",
                               "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True).stdout

    def write(self, rel, body):
        path = os.path.join(self.copy, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)

    def commit(self, subject="write(example): Engineer"):
        self.git("add", "-A")
        self.git("commit", "-qm", subject)

    def save(self, provenance=PROVENANCE, tex=TEX, draft=TEX, entry=ENTRY):
        """A posting run's save: draft under .build, the application folder, the entry."""
        self.write(".build/drafts/2026-02-01-example-engineer/resume.tex", draft)
        self.write(FOLDER + "/posting.md", "Example Corp: Engineer\n")
        self.write(FOLDER + "/resume.tex", tex)
        if provenance is not None:
            self.write(FOLDER + "/provenance.md", provenance)
        self.write("entries/2026-01-queue.md", entry)
        self.commit()

    def saved(self):
        return [p for p in self.git("diff", "--name-only", "--diff-filter=AM", self.base, "HEAD").splitlines() if p]

    def publish(self):
        """Push HEAD to a bare origin as its default branch, the copy's own, as the harness's copy has it."""
        branch = self.git("branch", "--show-current").strip()
        remote = self.copy + "-remote.git"
        if not os.path.isdir(remote):
            subprocess.run(["git", "init", "-q", "--bare", "-b", branch, remote], check=True, capture_output=True)
            self.addCleanup(shutil.rmtree, remote, True)
            self.git("remote", "add", "origin", remote)
        self.git("push", "-q", "-f", "origin", "HEAD:" + branch)
        self.git("fetch", "-q", "origin")
        self.git("remote", "set-head", "origin", branch)

    def phrasings(self, add=(), drop=()):
        """The entry with the lines in add appended under Past phrasings and those in drop removed."""
        body = ENTRY
        for l in drop:
            body = body.replace(l + "\n", "")
        for l in add:
            body = body.replace("\n## Conflicts", l + "\n\n## Conflicts")
        return body



class Copy(CopyBase):
    def test_status_clean_pass(self):
        self.save()
        self.assertEqual(check_run.check_status(self.copy)[0], "PASS")

    def test_status_untracked_fails(self):
        self.save()
        self.write("outputs/reports/stray.md", "x\n")
        self.assertEqual(check_run.check_status(self.copy)[0], "FAIL")

    def test_resume_identical_pass(self):
        self.save()
        grade, ev = check_run.check_resume(self.copy, self.saved(), self.base)
        self.assertEqual(grade, "PASS")
        self.assertIn(".build/drafts/2026-02-01-example-engineer/resume.tex", ev)

    def test_resume_differs_from_draft_fails(self):
        self.save(tex=TEX.replace("Resume", "Resume edited after approval"))
        self.assertEqual(check_run.check_resume(self.copy, self.saved(), self.base)[0], "FAIL")

    def test_resume_saved_from_an_approved_target_pass(self):
        self.save(draft="a different draft\n")
        grade, ev = check_run.check_resume(self.copy, self.saved(), self.base)
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("outputs/resumes/backend.tex at", ev)

    def test_provenance_pass(self):
        self.save()
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("2 row(s)", ev)

    def test_provenance_row_pointing_at_another_output_fails(self):
        row = "| Skills line | backend target | backend provenance (../../resumes/backend.md) |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("Skills line", ev)

    def test_provenance_row_pointing_at_an_application_fails(self):
        row = "| Queue bullet | 2026-01-queue › What happened | outputs/applications/2025-12-01-other/provenance.md |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        self.assertEqual(check_run.check_provenance(self.copy, self.saved())[0], "FAIL")

    def test_provenance_url_and_other_tables_pass(self):
        row = "| Example Corp's queue | 2026-01-queue › What happened | https://example.com/reports/queues |\n"
        text = PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1)
        text += "\n## Approved text\n\n| Section | Text |\n|---|---|\n| Header | see outputs/resumes/backend.pdf |\n"
        self.save(provenance=text)
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("3 row(s)", ev)

    def test_provenance_direction_row_passes_and_an_output_row_still_fails(self):
        row = "| Work authorisation | direction.md › Constraints | (user, 2026-01-10) |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("3 row(s)", ev)
        bad = row + "| Skills line | backend target | outputs/resumes/backend.md |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", bad + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("Skills line", ev)
        self.assertNotIn("Work authorisation", ev)

    def test_provenance_url_into_outputs_fails(self):
        row = "| Skills line | backend target | https://example.com/blob/main/outputs/resumes/backend.md |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        self.assertEqual(check_run.check_provenance(self.copy, self.saved())[0], "FAIL")

    def test_provenance_without_a_provenance_table_is_a_note(self):
        self.save(provenance="# Provenance\n\nEvery claim comes from the backend target.\n")
        self.assertEqual(check_run.check_provenance(self.copy, self.saved())[0], "NOTE")

    def test_provenance_source_citations_pass(self):
        rows = ("| Degree | profile › Education | sources/resumes/2024-old.tex, 2026-new.tex; transcript |\n"
                "| Queue design | 2026-01-queue › What happened | queue@abc1234:docs/reports/design.md:12 |\n")
        self.save(provenance=PROVENANCE.replace("\n## Company context", rows + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)

    def test_provenance_section_missing_from_its_entry_fails(self):
        """Exception 5's section check, now the tool's: the section after ` › ` is a heading of that entry."""
        row = "| Queue design | 2026-01-queue › How it works | (user, 2026-01-02) |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("2026-01-queue › How it works, no heading there", ev)

    def test_provenance_example_entry_citation_passes(self):
        path = os.path.join(HERE, "..", "..", "skills", "career-log", "examples", "entries",
                            "2025-06-northwind-freight-internship.md")
        with open(path, encoding="utf-8") as f:
            line = next(l for l in f if l.startswith("| Invoices flagged by the reconciler |"))
        source = line.strip().strip("|").split("|")[-1].strip()
        row = "| Flagged invoices | 2025-06-northwind-freight-internship › Results and evidence | %s |\n" % source
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)

    def test_provenance_repo_key_into_reports_passes_and_a_reports_path_fails(self):
        row = "| Flagged invoices | 2025-06-internship › Results | `reconciler@3f9c2a1:reports/2025-08.md:14` |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)
        for cell in ("outputs/reports/x.md", "reports/x.md", "reconciler repo `reports/2025-08.md`"):
            row = "| Flagged invoices | 2025-06-internship › Results | %s |\n" % cell
            self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
            grade, ev = check_run.check_provenance(self.copy, self.saved())
            self.assertEqual(grade, "FAIL", cell)
            self.assertIn("Flagged invoices", ev)

    def test_provenance_source_then_output_in_one_cell_fails(self):
        row = "| Skills line | backend target | sources/resumes/old.tex, outputs/resumes/backend.md |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        self.assertEqual(check_run.check_provenance(self.copy, self.saved())[0], "FAIL")

    def test_provenance_entry_section_naming_another_file_fails(self):
        """The rule write step 10 runs through tools/check_save.py: an entry section is an entry's."""
        row = "| Queue answer | stories.md › Application questions | (user, 2026-01-02) |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("entry section names stories.md", ev)
        row = "| Queue bullet | 2026-01-queue.md › What happened | (user, 2026-01-02) |\n"
        self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        self.assertEqual(check_run.check_provenance(self.copy, self.saved())[0], "PASS")

    def test_application_without_provenance_fails(self):
        self.save(provenance=None)
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("has no provenance.md", ev)

    def printed(self, blocks):
        os.makedirs(os.path.join(self.copy, ".build"), exist_ok=True)
        evs, calls = transcript(os.path.join(self.copy, ".build"), blocks)
        return check_run.check_printed_lines(evs, calls, self.copy, self.base, self.saved())

    def test_printed_lines_pass(self):
        self.save()
        grade, ev = self.printed(GOOD_RUN)
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("provenance.md): 2 rows", ev)
        self.assertIn("Humanizer after review: Built a queue.", ev)

    def test_check_save_lines_around_the_two_it_grades_pass(self):
        """check_save's own Files, Risks, Past phrasings, Entries and Lint lines, and the `fix:` and
        `check:` lines under them, are not lines in another form."""
        self.save()
        lines = ("Files (%s): ok" % FOLDER, "Files (%s): note: no .build/drafts/x/resume.pdf, so y was not compared" % FOLDER,
                 "Risks (%s): ok" % FOLDER, PROVENANCE_LINE,
                 "Past phrasings (entries/2026-01-queue.md): +1 -1; ok",
                 "  check: removed [backend] '\"Built a queue\" (x)': check it is the line consolidate step 2 ranks last",
                 "Lint at save: check: %s/answers.md:3: 820 appears in 2 artifacts" % FOLDER, HUMANIZER_AFTER)
        grade, ev = self.printed([reviewer(), humanizer()] + checked(*lines) + [COMMIT])
        self.assertEqual(grade, "PASS", ev)
        bad = ("Provenance check (provenance.md): 3 rows; citing another output: line 7, entry section names "
               "2026-01-queue › Nowhere, no heading there: x",
               "  fix: replace each listed row with rows citing the entry sections behind that claim")
        grade, ev = self.printed([reviewer(), humanizer()] + checked(*bad, HUMANIZER_AFTER, ok=False) + [COMMIT])
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("does not say none", ev)
        self.assertNotIn("tool line not in the form", ev)

    def test_rerun_until_none_pass(self):
        self.save()
        first = checked("Provenance check (provenance.md): 3 rows; citing another output: line 7, names another "
                        "output (outputs/): x", HUMANIZER_AFTER, ok=False)
        grade, ev = self.printed([reviewer(), humanizer()] + first + checked(PROVENANCE_LINE, HUMANIZER_AFTER) + [COMMIT])
        self.assertEqual(grade, "PASS", ev)

    def test_lines_the_run_wrote_itself_fail(self):
        self.save()
        grade, ev = self.printed([reviewer(), humanizer(), text(HUMANIZER_AFTER), text(PROVENANCE_LINE), COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("no tools/check_save.py run before the save's git commit call", ev)
        self.assertIn("the run wrote the lines itself", ev)

    def test_echoed_or_read_lines_fail(self):
        self.save()
        for cmd in ("echo '%s'" % PROVENANCE_LINE, "cat %s/provenance.md" % FOLDER):
            grade, ev = self.printed([bash(cmd), result(PROVENANCE_LINE), COMMIT])
            self.assertEqual(grade, "FAIL", cmd)
            self.assertIn("no tools/check_save.py run", ev)

    def test_tool_line_for_a_file_with_no_table_fails(self):
        self.save()
        line = "Provenance check (%s/provenance.md): no provenance table (a table with an entry or source column)" % FOLDER
        grade, ev = self.printed(checked(line, ok=False) + [COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("not in the form", ev)

    def test_last_provenance_check_not_none_fails(self):
        self.save()
        line = "Provenance check: 2 rows; citing another output: line 7, names another output (outputs/): x"
        grade, ev = self.printed(checked(line, ok=False) + [COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("does not say none", ev)

    def test_missing_humanizer_after_review_fails(self):
        self.save()
        grade, ev = self.printed([reviewer(), humanizer()] + checked(PROVENANCE_LINE) + [COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("no Humanizer after review line", ev)

    def test_no_reviewer_needs_no_humanizer_line(self):
        self.save()
        self.assertEqual(self.printed(checked(PROVENANCE_LINE) + [COMMIT])[0], "PASS")

    def test_sync_commit_is_the_save_commit(self):
        self.save()
        sync = bash("py -3 -I /tmp/t/log/tools/sync.py commit 'write(example): Engineer' -- %s" % FOLDER)
        self.assertEqual(self.printed(checked(PROVENANCE_LINE) + [sync])[0], "PASS")
        grade, ev = self.printed([reviewer(), humanizer(), sync] + checked(PROVENANCE_LINE, HUMANIZER_AFTER))
        self.assertEqual(grade, "FAIL")
        self.assertIn("ran only after the save's commit", ev)

    def test_sync_commit_with_root_and_a_failed_push(self):
        self.save()
        sync = bash('python3 -I tools/sync.py --root "/tmp/t/log" commit "write(example): Engineer" -- %s' % FOLDER)
        pushed = result("committed: [master 1234567] write(example): Engineer\npush: refused (the commit is made,"
                        " not pushed)\nnext: stop: show the user git's message above", error=True)
        grade, ev = self.printed([reviewer(), humanizer(), sync, pushed] + checked(PROVENANCE_LINE, HUMANIZER_AFTER))
        self.assertEqual(grade, "FAIL")
        self.assertIn("ran only after the save's commit", ev)

    def test_check_only_after_the_commit_fails(self):
        self.save()
        grade, ev = self.printed([reviewer(), humanizer(), COMMIT] + checked(PROVENANCE_LINE, HUMANIZER_AFTER))
        self.assertEqual(grade, "FAIL")
        self.assertIn("ran only after the save's commit", ev)

    def test_a_table_with_no_line_fails(self):
        self.write("outputs/reports/2026-02-01-bio.md", PROVENANCE)
        self.save()
        grade, ev = self.printed(GOOD_RUN)
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("no Provenance check line for outputs/reports/2026-02-01-bio.md", ev)

    def test_one_line_per_table_pass(self):
        self.write("outputs/reports/2026-02-01-my_bio.md", PROVENANCE)
        self.save()
        bio = "Provenance check (outputs/reports/2026-02-01-my_bio.md): 2 rows; citing another output: none"
        self.assertEqual(self.printed(checked(PROVENANCE_LINE, bio) + [COMMIT])[0], "PASS")
        # or in two runs of the tool
        grade, ev = self.printed(checked(bio) + checked(PROVENANCE_LINE) + [COMMIT])
        self.assertEqual(grade, "PASS", ev)

    def test_unnamed_line_for_the_only_table_pass(self):
        self.save()
        self.assertEqual(self.printed(checked("Provenance check: 2 rows; citing another output: none") + [COMMIT])[0], "PASS")

    def test_ascii_arrow_and_review_with_no_change_pass(self):
        self.save()
        for hum in ("Humanizer after review: Built a queue. -> Humanizer call: model Sonnet 5.5",
                    "Humanizer after review: none"):
            grade, ev = self.printed([reviewer(), humanizer()] + checked(PROVENANCE_LINE, hum) + [COMMIT])
            self.assertEqual(grade, "PASS", (hum, ev))

    def test_humanizer_after_review_without_a_call_line_fails(self):
        self.save()
        for hum in ("Humanizer after review: Built a queue. -> none",
                    "Humanizer after review: Built a queue. -> no Humanizer call yet"):
            grade, ev = self.printed([reviewer(), humanizer()] + checked(PROVENANCE_LINE, HUMANIZER_AFTER, hum) + [COMMIT])
            self.assertEqual(grade, "FAIL", hum)

    def test_commit_named_in_a_prompt_or_rev_parse_is_no_commit(self):
        self.save()
        noise = [agent("Note", "then git commit the save"), bash("git rev-parse HEAD^{commit}")]
        grade, ev = self.printed(noise + checked(PROVENANCE_LINE) + [COMMIT])
        self.assertEqual(grade, "PASS", ev)

    def test_label_fitting_two_tables_fails(self):
        self.write("outputs/applications/2026-01-01-other-engineer/provenance.md", PROVENANCE)
        self.save()
        grade, ev = self.printed(checked("Provenance check (provenance.md): 2 rows; citing another output: none") + [COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("fits more than one provenance file", ev)

    def test_none_then_a_listed_row_fails(self):
        self.save()
        line = "Provenance check (provenance.md): 2 rows; citing another output: none, but row 2 cites outputs/x.md"
        self.assertEqual(self.printed(checked(line) + [COMMIT])[0], "FAIL")

    def test_commit_with_a_long_option_is_the_cutoff(self):
        self.save()
        late = bash("git --no-pager commit -m 'write(example): Engineer'")
        grade, ev = self.printed([late] + checked(PROVENANCE_LINE))
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("ran only after", ev)

    def test_a_failed_commit_is_not_the_cutoff(self):
        """A write( commit that exits non-zero (a hook, nothing staged) is not the save's commit."""
        self.save()
        blocks = [COMMIT, result("nothing added to commit", error=True)] + checked(PROVENANCE_LINE) + [COMMIT]
        grade, ev = self.printed(blocks)
        self.assertEqual(grade, "PASS", ev)

    def test_check_chained_before_the_commit_pass(self):
        self.save()
        cmd = ("py -3 -I tools/check_save.py %s && git add -A && git commit -m 'write(example): Engineer' && git push"
               % FOLDER)
        out = PROVENANCE_LINE + "\ncheck_save: ok\n[master 1a2b3c4] write(example): Engineer"
        grade, ev = self.printed([bash(cmd), result(out)])
        self.assertEqual(grade, "PASS", ev)
        # chained after the commit, it checks nothing before it
        cmd = "git commit -m 'write(example): Engineer' && py -3 -I tools/check_save.py %s" % FOLDER
        self.assertEqual(self.printed([bash(cmd), result(PROVENANCE_LINE + "\ncheck_save: ok")])[0], "FAIL")

    def test_check_save_commit_is_the_save_commit(self):
        """#518: check_save.py --commit checks, then commits; an earlier fact commit is not the cutoff."""
        self.save()
        early = bash("py -3 -I tools/sync.py commit 'log(example): a fact' -- entries/x.md")
        cmd = "py -3 -I tools/check_save.py %s --humanizer none --commit 'write(example): Engineer'" % FOLDER
        out = PROVENANCE_LINE + "\ncheck_save: ok\ncommit: write(example): Engineer\ncommitted: [master 1a2b3c4] write(example): Engineer"
        grade, ev = self.printed([early, result("committed: [master 0f0f0f0] log(example): a fact"), bash(cmd), result(out)])
        self.assertEqual(grade, "PASS", ev)

    def test_result_as_a_list_of_text_blocks_is_read(self):
        self.save()
        out = {"type": "tool_result", "content": [{"type": "text", "text": PROVENANCE_LINE + "\ncheck_save: ok"}]}
        grade, ev = self.printed([bash("python3 -I tools/check_save.py %s" % FOLDER), out, COMMIT])
        self.assertEqual(grade, "PASS", ev)

    def test_row_count_unlike_the_committed_file_fails(self):
        self.save()
        line = PROVENANCE_LINE.replace("2 rows", "3 rows")
        grade, ev = self.printed(checked(line) + [COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("the committed file has 2", ev)

    def test_file_edited_after_its_check_fails(self):
        self.save()
        edit = {"type": "tool_use", "name": "Edit",
                "input": {"file_path": "/tmp/t/log/" + FOLDER + "/provenance.md", "old_string": "a", "new_string": "b"}}
        grade, ev = self.printed(checked(PROVENANCE_LINE) + [edit, COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("edited (Edit) after its last Provenance check line", ev)
        # an edit to another file, or before the check, is fine
        other = dict(edit, input=dict(edit["input"], file_path="/tmp/t/log/" + FOLDER + "/answers.md"))
        self.assertEqual(self.printed([edit] + checked(PROVENANCE_LINE) + [other, COMMIT])[0], "PASS")

    def test_reading_the_tool_is_no_check_run(self):
        self.save()
        src = "print(\"Humanizer after review: %s -> %s\")\nProvenance check (provenance.md): 2 rows; citing another output: none"
        for cmd in ("cat tools/check_save.py", "grep -n python tools/check_save.py"):
            grade, ev = self.printed([bash(cmd), result(src), COMMIT])
            self.assertEqual(grade, "FAIL", cmd)
            self.assertIn("no tools/check_save.py run", ev)
        # nor after a real run
        self.assertEqual(self.printed(checked(PROVENANCE_LINE) + [bash("grep -n python tools/check_save.py"),
                                                                  result(src), COMMIT])[0], "PASS")
        # these run it
        for cmd in ('py -3 -I tools\\check_save.py %s' % FOLDER,
                    '& "C:\\Python311\\python.exe" -I "C:/log/tools/check_save.py" %s' % FOLDER,
                    '& "C:\\Program Files\\Python311\\python.exe" -I tools/check_save.py %s' % FOLDER,
                    'python3 -I "D:/My Repos/log/tools/check_save.py" %s' % FOLDER,
                    'PYTHONUTF8=1 python3 -X utf8 -I tools/check_save.py %s' % FOLDER,
                    'Set-Content x.txt $h | py -3 -I "$r/tools/check_save.py" %s' % FOLDER):
            grade, ev = self.printed([bash(cmd), result(PROVENANCE_LINE + "\ncheck_save: ok"), COMMIT])
            self.assertEqual(grade, "PASS", (cmd, ev))

    def test_run_pattern_on_long_commands(self):
        """No catastrophic backtracking on many flags; a test file of the same name is no run."""
        import time
        start = time.monotonic()
        self.assertIsNone(check_run.CHECK_SAVE.search("python " + "-X " * 5000 + "z"))
        self.assertLess(time.monotonic() - start, 1)
        self.assertIsNone(check_run.CHECK_SAVE.search("python -I tools/tests/test_check_save.py"))
        self.assertTrue(check_run.CHECK_SAVE.search("python3 -I check_save.py x"))

    def test_humanizer_line_with_an_arrow_of_its_own_pass(self):
        """The tool splits at the last arrow, and prints the line whole."""
        self.save()
        for hum in ("Humanizer after review: Cut 40ms -> 12ms -> humanizer not available",
                    "Humanizer after review: Cut 40ms -> 12ms -> humanizer not available (skill not installed)."):
            grade, ev = self.printed([reviewer(), humanizer()] + checked(PROVENANCE_LINE, hum) + [COMMIT])
            self.assertEqual(grade, "PASS", (hum, ev))

    def test_committed_file_with_a_bom_counts_its_rows(self):
        self.save(provenance="﻿" + PROVENANCE[PROVENANCE.index("|"):])
        self.assertEqual(self.printed(checked(PROVENANCE_LINE) + [COMMIT])[0], "PASS")

    def test_last_check_run_failing_fails(self):
        """Its lines may parse (a provenance line saying none beside a Humanizer line it rejected)."""
        self.save()
        bad = ("Humanizer after review: not in the form <changed line> -> <its Humanizer call: line, or: humanizer "
               "not available>: Cut 40ms -> 12ms -> Humanizer call: model Sonnet 5.5")
        grade, ev = self.printed([reviewer(), humanizer()] + checked(PROVENANCE_LINE, bad, ok=False) + [COMMIT])
        self.assertEqual(grade, "FAIL")
        self.assertIn("did not exit 0", ev)

    def test_rows_are_counted_at_the_save_commit(self):
        """A later write save may change the file; the cutoff is the first save's commit."""
        self.save()
        self.write(FOLDER + "/provenance.md", PROVENANCE.replace(
            "\n## Company context", "| Third | 2026-01-queue › What happened | (user, 2026-01-03) |\n\n## Company context", 1))
        self.commit("write(example): Engineer, one more row")
        grade, ev = self.printed(GOOD_RUN)
        self.assertEqual(grade, "PASS", ev)

    def test_an_earlier_write_commit_of_facts_is_not_the_cutoff(self):
        """A run may commit facts the user gave (write step 7) with a write( subject before its save."""
        self.write("entries/2026-01-queue.md", ENTRY + "\nA fact. (user, 2026-02-01)\n")
        self.commit("write(example): record a fact")
        facts = self.git("rev-parse", "--short", "HEAD").strip()
        self.save()
        sha = self.git("rev-parse", "--short", "HEAD").strip()
        blocks = ([bash("git commit -m 'write(example): record a fact'"), result("[master %s] write(example): record a fact" % facts)]
                  + checked(PROVENANCE_LINE) + [COMMIT, result("[master %s] write(example): Engineer" % sha)])
        grade, ev = self.printed(blocks)
        self.assertEqual(grade, "PASS", ev)
        # `git commit -q` prints nothing: the command's subject finds the save's commit
        quiet = [blocks[0], result("")] + checked(PROVENANCE_LINE) + [COMMIT, result("")]
        self.assertEqual(self.printed(quiet)[0], "PASS")
        # a check run only after the save's commit still fails
        blocks = blocks[:2] + [COMMIT, result("[master %s] write(example): Engineer" % sha)] + checked(PROVENANCE_LINE)
        self.assertEqual(self.printed(blocks)[0], "FAIL")

    def test_commit_made_but_push_failed_is_the_cutoff(self):
        self.save()
        out = "[master 1a2b3c4] write(example): Engineer\n 3 files changed\nerror: failed to push some refs"
        blocks = [COMMIT, result(out, error=True)] + checked(PROVENANCE_LINE) + [COMMIT]
        grade, ev = self.printed(blocks)
        self.assertEqual(grade, "FAIL")
        self.assertIn("ran only after", ev)

    def test_another_modes_report_needs_no_line(self):
        self.save()
        self.write("outputs/reports/2026-02-02-fit-posting-example-engineer.md", PROVENANCE)
        self.commit("fit(example-engineer): 2 gaps")
        self.assertEqual(self.printed(GOOD_RUN)[0], "PASS")

    def test_printed_lines_skip_without_a_write_save(self):
        self.write("entries/2026-01-queue.md", ENTRY + "x\n")
        self.commit("consolidate(queue): placed lines")
        self.assertEqual(self.printed(GOOD_RUN)[0], "SKIP")

    def test_write_save_adding_no_phrasing_is_a_note(self):
        self.save(entry=ENTRY.replace("Built a job queue. (user", "Built a job queue in Go. (user"))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "NOTE", ev)
        self.assertIn("the write save added no Past phrasings line: check the approved resume or bullets report", ev)

    def test_phrasing_added_pass(self):
        self.save(entry=self.phrasings(add=['- **backend:** "Cut queue latency by moving retries to a worker pool." (%s)' % FOLDER]))
        self.assertEqual(check_run.check_phrasings(self.copy, self.base, self.saved())[0], "PASS")

    def test_drop_beside_an_addition_is_a_note(self):
        added = '- **backend:** "Cut queue latency by moving retries to a worker pool." (%s)' % FOLDER
        dropped = '- **backend:** "Built a job queue that retried failed tasks within one second." (sources/resumes/2026-01-old.tex)'
        self.save(entry=self.phrasings(add=[added], drop=[dropped]))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "NOTE", ev)
        self.assertIn("+1 -1", ev)
        self.assertIn("retried failed tasks", ev)

    def test_phrasing_rewritten_fails(self):
        old = '- **backend:** "Built a job queue that retried failed tasks within one second." (sources/resumes/2026-01-old.tex)'
        new = '- **backend:** "Built a job queue that retried failed jobs within one second." (sources/resumes/2026-01-old.tex)'
        self.save(entry=ENTRY.replace(old, new))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("rewritten", ev)

    def test_phrasing_dropped_without_addition_fails(self):
        dropped = '- **general:** "Designed the retry policy for a job queue used by three teams." (sources/resumes/2026-01-old.tex)'
        self.save(entry=self.phrasings(drop=[dropped]))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("1 line(s) removed, 0 added", ev)

    def test_word_only_addition_fails(self):
        self.save(entry=self.phrasings(add=[
            '- **backend:** "Built a job queue in Java that retried failed tasks within one second." (%s)' % FOLDER]))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("word-only addition", ev)

    def test_two_word_only_additions_fail(self):
        self.save(entry=self.phrasings(add=[
            '- **backend:** "Moved queue retries to a worker pool, cutting latency." (%s)' % FOLDER,
            '- **backend:** "Moved queue retries to a worker pool, cutting the latency." (%s)' % FOLDER]))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("word-only addition", ev)

    def test_placeholder_replaced_pass(self):
        base = ENTRY.replace('- **general:** "Designed the retry policy for a job queue used by three teams." (sources/resumes/2026-01-old.tex)\n', "- None yet.\n")
        self.write("entries/2026-01-queue.md", base)
        self.commit("data: placeholder")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.save(entry=base.replace("- None yet.", '- **general:** "Designed the retry policy." (%s)' % FOLDER))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "PASS", ev)

    def test_other_mode_trim_skips(self):
        dropped = '- **general:** "Designed the retry policy for a job queue used by three teams." (sources/resumes/2026-01-old.tex)'
        self.write("entries/2026-01-queue.md", self.phrasings(drop=[dropped]))
        self.commit("consolidate(queue): trim Past phrasings")
        self.assertEqual(check_run.check_phrasings(self.copy, self.base, self.saved())[0], "SKIP")

    def test_fail_evidence_gives_counts(self):
        self.save(entry=self.phrasings(add=[
            '- **backend:** "Built a job queue in Java that retried failed tasks within one second." (%s)' % FOLDER]))
        self.assertIn("+1 -0", check_run.check_phrasings(self.copy, self.base, self.saved())[1])

    def test_write_save_with_no_entry_changed_is_a_note(self):
        self.save()
        self.assertEqual(check_run.check_phrasings(self.copy, self.base, ["outputs/x.md"])[0], "NOTE")

    def test_label_lines_set_the_angle(self):
        text = """## Past phrasings
- **backend:**
  - Built a job queue that retried failed tasks within one second. (a)
**general**
- Built a job queue that retried failed tasks within one second (b)
- **Queues:** Designed the retry policy. (c)

## Conflicts
"""
        self.assertEqual(check_run.phrasings(text), [
            ("backend", "Built a job queue that retried failed tasks within one second. (a)"),
            ("general", "Built a job queue that retried failed tasks within one second (b)"),
            ("general", "**Queues:** Designed the retry policy. (c)")])

    def test_own_prefix_sets_the_angle_only_for_a_quoted_wording(self):
        text = """## Past phrasings
- **ai-infra:** "**Queues:** Built a job queue." (a)
- **Queues:** Designed the retry policy. (b)
- **general:**"Designed the retry policy." (c)

## Conflicts
"""
        self.assertEqual(check_run.phrasings(text), [
            ("ai-infra", '"**Queues:** Built a job queue." (a)'),
            (None, "**Queues:** Designed the retry policy. (b)"),
            ("general", '"Designed the retry policy." (c)')])

    def test_own_prefix_wins_over_a_label_line(self):
        text = """## Past phrasings
**backend**
- **AI-Infra:** “Built a job queue.” (a)
- **ai-infra**: 「Built a job queue.」 (b)
- Built a job queue. (c)

## Conflicts
"""
        self.assertEqual([a for a, _ in check_run.phrasings(text)], ["ai-infra", "ai-infra", "backend"])

    def test_word_only_addition_under_a_label_line_fails(self):
        nested = ENTRY.replace('- **backend:** "Built a job queue', '- **backend:**\n  - "Built a job queue')
        self.write("entries/2026-01-queue.md", nested)
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        java = '  - "Built a job queue in Java that retried failed tasks within one second." (x)'
        self.save(entry=nested.replace('old.tex)\n- **general:**', 'old.tex)\n' + java + '\n- **general:**'))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("[backend]", ev)

    def test_archived_save_adding_no_phrasing_pass(self):
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-01)\n")
        self.save()
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("Archived save or demote", ev)

    def test_archived_save_adding_a_phrasing_fails(self):
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-01)\n")
        self.save(entry=self.phrasings(add=['- **backend:** "Cut queue latency by moving retries to a worker pool." (%s)' % FOLDER]))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("citing an Archived folder", ev)

    def demote_base(self):
        """A base whose entry holds a wording citing FOLDER, saved earlier at the Reference level."""
        cited = '- **backend:** "Cut queue latency by moving retries to a worker pool." (%s)' % FOLDER
        self.save(entry=self.phrasings(add=[cited]))
        self.base = self.git("rev-parse", "HEAD").strip()
        return cited

    def test_demote_removing_the_folders_lines_pass(self):
        self.demote_base()
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-03)\n")
        self.write("entries/2026-01-queue.md", ENTRY)
        self.commit("write(example): Engineer to Archived")
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("demoted", ev)

    def test_archived_folder_does_not_match_a_longer_name(self):
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-01)\n")
        self.save(entry=self.phrasings(add=['- **backend:** "Cut queue latency by moving retries to a worker pool." (%s-ii)' % FOLDER]))
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertNotIn("citing an Archived folder", ev)

    def test_demote_removing_another_line_fails(self):
        self.demote_base()
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-03)\n")
        self.write("entries/2026-01-queue.md", self.phrasings(add=[
            '- **backend:** "Cut queue latency by moving retries to a worker pool." (%s)' % FOLDER],
            drop=['- **general:** "Designed the retry policy for a job queue used by three teams." (sources/resumes/2026-01-old.tex)']))
        self.commit("write(example): Engineer to Archived")
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("1 line(s) removed, 0 added", ev)

    def test_demote_then_reference_save_adding_none_is_a_note(self):
        self.demote_base()
        self.write(FOLDER + "/archived.md", "Archived (user, 2026-02-03)\n")
        self.write("entries/2026-01-queue.md", ENTRY)
        self.commit("write(example): Engineer to Archived")
        self.write("outputs/applications/2026-02-04-other-engineer/posting.md", "Other: Engineer\n")
        self.commit("write(other): Engineer")
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "NOTE", ev)
        self.assertIn("added no Past phrasings line", ev)

    def test_bullets_report_demote_pass(self):
        """D8: a bullets report's lines cite its path; the Archived line added to it demotes them."""
        report = "outputs/reports/2026-02-01-backend-bullets.md"
        cited = '- **backend:** "Cut queue latency by moving retries to a worker pool." (%s)' % report
        self.write(report, "Kind: resume bullets\n\n- Cut queue latency by moving retries to a worker pool.\n\n" + PROVENANCE)
        self.write("entries/2026-01-queue.md", self.phrasings(add=[cited]))
        self.commit("write(backend-bullets): backend")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(report, "Kind: resume bullets\nArchived (user, 2026-02-03)\n\n- Cut queue latency by moving retries "
                           "to a worker pool.\n\n" + PROVENANCE)
        self.write("entries/2026-01-queue.md", ENTRY)
        self.commit("write(backend-bullets): backend to Archived")
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("demoted", ev)
        self.write("entries/2026-01-queue.md", self.phrasings(add=[cited.replace("backend:", "general:")]))
        self.commit("write(backend-bullets): backend again")
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL", ev)
        self.assertIn("citing an Archived folder", ev)

    def test_same_wording_for_another_angle_pass(self):
        self.save(entry=self.phrasings(add=[
            '- **general:** "Built a job queue that retried failed tasks within one second." (%s)' % FOLDER]))
        self.assertEqual(check_run.check_phrasings(self.copy, self.base, self.saved())[0], "PASS")


class Finding6(CopyBase):
    """A file that is not UTF-8, or git that cannot run, is graded or reported, not a traceback."""

    def write_bytes(self, rel, data):
        path = os.path.join(self.copy, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def test_provenance_not_utf8_fails(self):
        self.save()
        self.write_bytes(FOLDER + "/provenance.md", PROVENANCE.encode("utf-8") + b"\x93cp1252\x94\n")
        self.commit()
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("provenance.md is not UTF-8", ev)

    def test_entry_not_utf8_fails(self):
        self.save()
        self.write_bytes("entries/2026-01-queue.md", ENTRY.encode("utf-8") + b"\x93cp1252\x94\n")
        self.commit()
        grade, ev = check_run.check_phrasings(self.copy, self.base, self.saved())
        self.assertEqual(grade, "FAIL")
        self.assertIn("2026-01-queue.md is not UTF-8", ev)

    def test_git_that_cannot_run_exits_2(self):
        self.save()
        path = os.path.join(self.copy, ".build", "run.jsonl")
        write_transcript(path, GOOD_RUN)
        real = check_run.logfiles.subprocess.run

        def no_git(cmd, *a, **k):
            if cmd and cmd[0] == "git":
                raise FileNotFoundError("git")
            return real(cmd, *a, **k)
        out = io.StringIO()
        check_run.logfiles.subprocess.run = no_git
        try:
            with contextlib.redirect_stdout(out):
                code = check_run.main(["check_run.py", "--transcript", path, "--copy", self.copy, "--base", self.base])
        finally:
            check_run.logfiles.subprocess.run = real
        self.assertEqual(code, 2, out.getvalue())
        self.assertIn("git failed", out.getvalue())

    def test_git_failing_inside_a_check_exits_2(self):
        """origin/HEAD names a branch origin no longer has: save-branch's rev-list fails."""
        self.save()
        self.publish()
        self.git("update-ref", "refs/remotes/origin/HEAD", "HEAD")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/gone")
        path = os.path.join(self.copy, ".build", "run.jsonl")
        write_transcript(path, GOOD_RUN)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_run.main(["check_run.py", "--transcript", path, "--copy", self.copy, "--base", self.base])
        self.assertEqual(code, 2, out.getvalue())
        self.assertTrue(out.getvalue().startswith("git rev-list failed"), out.getvalue())

    def test_transcript_not_utf8_is_read(self):
        path = os.path.join(self.copy, ".build", "run.jsonl")
        os.makedirs(os.path.dirname(path))
        write_transcript(path, GOOD_RUN)
        with open(path, "ab") as f:
            f.write(b'{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "\x93ok\x94"}]}}\n')
        self.assertIn("text", [e[0] for e in check_run.events(path)])


class SaveBranch(CopyBase):
    def setUp(self):
        super().setUp()
        self.save()
        self.publish()

    def test_on_default_and_pushed_passes(self):
        grade, ev = check_run.check_branch(self.copy)
        self.assertEqual(grade, "PASS", ev)

    def test_unpushed_commit_fails(self):
        self.write("applications.md", "x\n")
        self.commit("applications(fair): sent")
        grade, ev = check_run.check_branch(self.copy)
        self.assertEqual(grade, "FAIL")
        self.assertIn("1 commit(s) on HEAD not pushed", ev)

    def test_other_branch_fails(self):
        self.git("checkout", "-q", "-b", "write/example")
        grade, ev = check_run.check_branch(self.copy)
        self.assertEqual(grade, "FAIL")
        self.assertIn("HEAD is branch write/example", ev)

    def test_second_worktree_fails(self):
        tree = self.copy + "-tree"
        self.git("worktree", "add", "-q", "-b", "side", tree)
        self.addCleanup(shutil.rmtree, tree, True)
        grade, ev = check_run.check_branch(self.copy)
        self.assertEqual(grade, "FAIL")
        self.assertIn("2 worktrees", ev)

    def test_no_origin_head_fails(self):
        self.git("remote", "set-head", "origin", "-d")
        grade, ev = check_run.check_branch(self.copy)
        self.assertEqual(grade, "FAIL")
        self.assertIn("no origin/HEAD", ev)


def edit(path):
    return {"type": "tool_use", "name": "Write", "input": {"file_path": path, "content": "x"}}


class OutsideRootAndPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "log")
        os.makedirs(os.path.join(self.root, "entries"))

    def tearDown(self):
        shutil.rmtree(self.tmp, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))

    def evs(self, blocks):
        return transcript(self.tmp, blocks)[0]

    def test_inside_passes(self):
        grade, ev = check_run.check_outside(self.evs([edit(self.root.replace("\\", "/") + "/.build/x/resume.tex")]), self.root)
        self.assertEqual(grade, "PASS", ev)

    def test_outside_is_a_note(self):
        stray = os.path.join(self.tmp, "notes.md")
        grade, ev = check_run.check_outside(self.evs([edit(os.path.join(self.root, "entries", "a.md")), edit(stray)]), self.root)
        self.assertEqual(grade, "NOTE")
        self.assertIn(stray, ev)
        self.assertNotIn("a.md", ev)

    def test_sibling_with_the_root_as_prefix_is_outside(self):
        self.assertEqual(check_run.check_outside(self.evs([edit(self.root + "-old/x.md")]), self.root)[0], "NOTE")

    def test_relative_copy_is_made_absolute(self):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@example.invalid", "-c", "user.name=T",
                        "commit", "-q", "--allow-empty", "-m", "base"], check=True)
        path = os.path.join(self.tmp, "run.jsonl")
        write_transcript(path, [edit(os.path.join(self.root, "b.txt"))])
        out, cwd = io.StringIO(), os.getcwd()
        os.chdir(self.tmp)
        try:
            with contextlib.redirect_stdout(out):
                check_run.main(["check_run.py", "--transcript", path, "--copy", "log", "--base", "HEAD"])
        finally:
            os.chdir(cwd)
        self.assertIn("PASS outside-root", out.getvalue())

    def test_no_edit_skips(self):
        self.assertEqual(check_run.check_outside(self.evs([text("Done.")]), self.root)[0], "SKIP")

    def test_another_spelling_of_the_root_is_the_same(self):
        """Exception 3: a spelling realpath resolves (here `..`; on Windows also a short name) is the copy."""
        other = os.path.join(self.root, "entries", "..")
        self.assertTrue(check_run.same_path(other, self.root))
        self.assertTrue(check_run.inside(os.path.join(other, "entries", "a.md"), self.root))
        self.assertFalse(check_run.same_path(self.tmp, self.root))
        _, calls = transcript(self.tmp, [reviewer(first=POINTER % (other, other))])
        self.assertEqual(check_run.check_reviewer_prompt(calls, REVIEW_MD, self.root)[0], "PASS")


class AskedModel(unittest.TestCase):
    """Exception 7: a subagent on another model family than the run's passes when the user asked for it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def grade(self, prompt):
        path = os.path.join(self.tmp, "run.jsonl")
        blocks = [dict(b, input=dict(b["input"], model="opus")) if b.get("name") == "Agent" and "Company" in b["input"]["description"]
                  else b for b in GOOD_RUN]
        write_transcript(path, blocks, model="claude-sonnet-5-5")
        with open(path, encoding="utf-8") as f:
            body = f.readlines()
        body[0] = json.dumps({"type": "user", "message": {"role": "user", "content": prompt}}) + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(body)
        evs = check_run.events(path)
        return check_run.check_models(check_run.subagent_calls(evs), evs)

    def test_asked_for_passes(self):
        grade, ev = self.grade("Environment rules:\n- read pages\n\nUser message:\nApply to this posting; run the company lookup on Opus.")
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("the user asked for opus", ev)

    def test_not_asked_is_a_note(self):
        self.assertEqual(self.grade("User message:\nApply to this posting.")[0], "NOTE")

    def test_a_name_above_the_user_message_does_not_count(self):
        self.assertEqual(self.grade("Run notes: opus is the bar.\n\nUser message:\nApply to this posting.")[0], "NOTE")

    def test_a_system_reminder_is_not_the_user(self):
        prompt = ("User message:\nApply to this posting.\n<system-reminder>\nEnd git commit messages with:\n"
                  "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n</system-reminder>")
        self.assertEqual(self.grade(prompt)[0], "NOTE")


class Subjects(CopyBase):
    def setUp(self):
        super().setUp()
        for name, body in MODES_MD.items():
            self.write("skills/career-log/modes/" + name, body)
        self.commit("modes")
        self.base = self.git("rev-parse", "HEAD").strip()

    def grade(self, evs=()):
        texts = [check_run.show(self.copy, self.base, p) for p in self.git("ls-tree", "-r", "--name-only", self.base, "skills").split()]
        return check_run.check_subjects(list(evs), self.copy, self.base, check_run.subject_templates(texts))

    def test_templates(self):
        rx = check_run.subject_templates([MODES_MD["import.md"], WRITE_MD, MODES_MD["scan.md"]])
        self.assertEqual(sorted(rx), ["import: <n> file(s), <m> entr(y/ies)", "write(<company>): <role>", "write(<slug>): <target>"])
        self.assertTrue(rx["import: <n> file(s), <m> entr(y/ies)"].fullmatch("import: 3 files, 1 entry"))
        self.assertFalse(rx["import: <n> file(s), <m> entr(y/ies)"].fullmatch("import: 3 files, 1 entrys"))

    def test_mode_subject_passes(self):
        self.save()
        grade, ev = self.grade()
        self.assertEqual(grade, "PASS", ev)
        self.assertIn("write(<company>): <role>", ev)

    def test_unknown_subject_fails(self):
        self.write("applications.md", "x\n")
        self.commit("Update applications")
        grade, ev = self.grade()
        self.assertEqual(grade, "FAIL")
        self.assertIn("'Update applications' fits no subject", ev)

    def test_import_subject_takes_the_singular_or_plural(self):
        """The repo's own import modes: the counts' forms pass, a template's (s) copied as written fails."""
        modes = os.path.join(HERE, "..", "..", "skills", "career-log", "modes")
        texts = []
        for name in ("import.md", "import-chats.md"):
            with open(os.path.join(modes, name), encoding="utf-8") as f:
                texts.append(f.read())
        rx = check_run.subject_templates(texts)
        for subject in ("import: 1 file, 0 entries", "import: 2 files, 1 entry", "import: 1 file, 3 entries (gemini)"):
            self.assertTrue(any(r.fullmatch(subject) for r in rx.values()), subject)
        for subject in ("import: 1 file(s), 0 entries", "import: 2 files, 1 entr(y/ies)"):
            self.assertFalse(any(r.fullmatch(subject) for r in rx.values()), subject)
        self.write("sources/import-log.md", "x\n")
        self.commit("import: 1 file(s), 0 entries")
        grade, ev = self.grade()
        self.assertEqual(grade, "FAIL")
        self.assertIn("copied as written: the mode asks for the singular or plural", ev)

    def test_upgrade_subject_from_the_release_it_installs(self):
        """#500: an upgrade run commits by the upgrade mode its own commit brings in (the base's
        Engine has none), as the repo's own upgrade.md writes it: read the subjects at HEAD too."""
        with open(os.path.join(HERE, "..", "..", "skills", "career-log", "modes", "upgrade.md"), encoding="utf-8") as f:
            upgrade = f.read()
        self.write("skills/career-log/modes/upgrade.md", upgrade)
        self.commit("upgrade: Template 0.2.0")
        os.makedirs(os.path.join(self.copy, ".build"), exist_ok=True)
        path = os.path.join(self.copy, ".build", "run.jsonl")
        write_transcript(path, GOOD_RUN)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            check_run.main(["check_run.py", "--transcript", path, "--copy", self.copy, "--base", self.base])
        self.assertIn("PASS commit-subject: ", out.getvalue())
        self.assertIn("'upgrade: Template 0.2.0' (`upgrade: Template <version>`)", out.getvalue())

    def test_deny_coverage_subjects(self):
        """#507: the commits the repo's own deny_coverage.py makes (`entry --commit`, `line --commit`)
        pass, read from the tool at the head under test; a near miss still fails."""
        with open(os.path.join(HERE, "..", "deny_coverage.py"), encoding="utf-8") as f:
            tool = f.read()
        rx = check_run.subject_templates([tool])
        for subject in ("export-cleared: Foo", "export-deny: clear Foo"):   # `clear`'s two commits
            self.assertTrue(any(r.fullmatch(subject) for r in rx.values()), subject)
        self.write("tools/deny_coverage.py", tool)
        self.commit("tools")
        self.base = self.git("rev-parse", "HEAD").strip()
        for n, subject in enumerate(("export-deny: names from 2026-01-a.md, 2026-02-b.md",
                                     "export-deny: names from 4 entries", "export-deny: add Foo, Bar")):
            self.write(".export-deny", "x%d\n" % n)
            self.commit(subject)
        os.makedirs(os.path.join(self.copy, ".build"), exist_ok=True)
        path = os.path.join(self.copy, ".build", "run.jsonl")
        write_transcript(path, GOOD_RUN)

        def graded():
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                check_run.main(["check_run.py", "--transcript", path, "--copy", self.copy, "--base", self.base])
            return next(l for l in out.getvalue().splitlines() if " commit-subject: " in l)
        line = graded()
        self.assertTrue(line.startswith("PASS "), line)
        self.assertIn("'export-deny: add Foo, Bar' (`export-deny: add <", line)
        self.write(".export-deny", "y\n")
        self.commit("export-deny: update")
        line = graded()
        self.assertTrue(line.startswith("FAIL "), line)
        self.assertIn("'export-deny: update' fits no subject", line)

    def test_tool_printed_subject_passes(self):
        self.write("outputs/reports/2026-02-01-scan-daily.md", "x\n")
        self.commit("scan(daily): 4 postings")
        self.assertEqual(self.grade()[0], "FAIL")
        evs = transcript(self.copy, [bash("python3 -I tools/scan.py report"), result("saved: x\ncommit: scan(daily): 4 postings")])[0]
        self.assertEqual(self.grade(evs)[0], "PASS")

    def test_subject_printed_in_a_subagent_passes(self):
        """#511: a subagent the run started printed the commit: line; one only another transcript there printed still fails."""
        session = os.path.join(self.copy, ".build", "session")
        os.makedirs(os.path.join(session, "subagents"))
        write_transcript(session + ".jsonl", [lookup(), result("Done.\nagentId: a1b2c3 (use SendMessage with to: 'a1b2c3')")])
        for agent_id, subject in (("a1b2c3", "sponsorship: Example Corp"), ("d4e5f6", "sponsorship: Other Inc")):
            write_transcript(os.path.join(session, "subagents", "agent-%s.jsonl" % agent_id),
                             [bash("py -3 -I tools/sponsorship.py --root . add .build/sponsorship.jsonl"),
                              result("added: 1\ncommit: %s" % subject)])

        def graded():
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                check_run.main(["check_run.py", "--transcript", session + ".jsonl", "--copy", self.copy, "--base", self.base])
            return next(l for l in out.getvalue().splitlines() if " commit-subject: " in l)
        self.write("outputs/reports/sponsorship.jsonl", "{}\n")
        self.commit("sponsorship: Example Corp")
        line = graded()
        self.assertTrue(line.startswith("PASS "), line)
        self.assertIn("'sponsorship: Example Corp' (a tool's commit: line)", line)
        self.write("outputs/reports/sponsorship.jsonl", "{}\n{}\n")
        self.commit("sponsorship: Other Inc")
        line = graded()
        self.assertTrue(line.startswith("FAIL "), line)
        self.assertIn("'sponsorship: Other Inc' fits no subject", line)

    def test_subagents_of_a_run_that_is_itself_a_subagent(self):
        """--agent: the run is <session>/subagents/agent-<id>.jsonl, and its subagents sit beside it."""
        folder = os.path.join(self.copy, ".build", "session", "subagents")
        os.makedirs(folder)
        run = os.path.join(folder, "agent-r1.jsonl")
        write_transcript(run, [lookup(), result("Done.\nagentId: s1"), lookup(), result("Done.\nagentId: gone")])
        write_transcript(os.path.join(folder, "agent-s1.jsonl"), [])
        write_transcript(os.path.join(folder, "agent-other.jsonl"), [])
        self.assertEqual(check_run.subagent_transcripts(run, check_run.events(run)), [os.path.join(folder, "agent-s1.jsonl")])

    def test_consolidate_slugs_are_the_entries_changed(self):
        self.write("entries/2026-01-queue.md", ENTRY + "x\n")
        self.commit("consolidate(queue): first pass")
        self.assertEqual(self.grade()[0], "PASS")
        self.write("entries/2026-01-queue.md", ENTRY + "y\n")
        self.commit("consolidate(queu): second pass")
        grade, ev = self.grade()
        self.assertEqual(grade, "FAIL")
        self.assertIn("names queu, the entries it changes are queue", ev)

    def test_log_slug_names_an_entry(self):
        self.write("stories.md", "x\n")
        self.commit("log(queue): index pending Story under Conflict")
        self.assertEqual(self.grade()[0], "PASS")
        self.write("stories.md", "y\n")
        self.commit("log(widget): index pending Story under Conflict")
        grade, ev = self.grade()
        self.assertEqual(grade, "FAIL")
        self.assertIn("names no one entry", ev)

    def test_no_commit_skips(self):
        self.assertEqual(self.grade()[0], "SKIP")

    def test_an_example_subject_is_literal_and_a_slugless_log_fails(self):
        rx = check_run.subject_templates(["the entry commits as `log(widget): ...`.\n"])
        self.assertTrue(rx["log(widget): ..."].fullmatch("log(widget): shipped"))
        self.assertFalse(rx["log(widget): ..."].fullmatch("log: shipped"))
        self.write("stories.md", "x\n")
        self.commit("log: shipped the queue")
        self.assertEqual(self.grade()[0], "FAIL")

    def test_tool_output_spans_are_no_subjects(self):
        text = ("It prints `committed: [<branch> <sha>] <subject>` and `series: <slug>` after a commit; the subject is "
                "a `commit: <subject>` line.\nCommit it as `upgrade: <what changed>`.\n"
                "settle commit: commits every Log change, with the subject\n`log: changes left uncommitted (<files>)`.\n")
        rx = check_run.subject_templates([text])
        self.assertEqual(sorted(rx), ["log: changes left uncommitted (<files>)", "upgrade: <what changed>"])
        self.assertTrue(rx["log: changes left uncommitted (<files>)"].fullmatch("log: changes left uncommitted (a.md, b.md)"))

    def test_a_commit_line_only_counts_from_a_tool(self):
        self.write("outputs/reports/x.md", "x\n")
        self.commit("scan(daily): 4 postings")
        evs = transcript(self.copy, [bash("cat notes.txt"), result("commit: scan(daily): 4 postings")])[0]
        self.assertEqual(self.grade(evs)[0], "FAIL")


class HumanizedLines(CopyBase):
    """Exception 10: each `Humanizer after review:` line's text is in a humanizer call made after the review."""

    def grade(self, after_line, reply=None):
        self.save()
        blocks = [lookup(), REVIEWER_LINE, reviewer(), HUMANIZER_LINE, humanizer()]
        if reply is not None:
            blocks.append(result(reply))
        blocks += [*checked(PROVENANCE_LINE, after_line), COMMIT]
        evs, calls = transcript(self.copy, blocks)
        return check_run.check_printed_lines(evs, calls, self.copy, self.base, self.saved())

    def test_line_in_the_prompt_passes(self):
        self.assertEqual(self.grade(HUMANIZER_AFTER)[0], "PASS")

    def test_line_in_the_reply_passes(self):
        line = "Humanizer after review: Built a retrying queue. → Humanizer call: model Sonnet 5.5"
        self.assertEqual(self.grade(line, reply="Built a retrying   queue.")[0], "PASS")

    def test_line_in_neither_fails(self):
        line = "Humanizer after review: Led a team of five. → Humanizer call: model Sonnet 5.5"
        grade, ev = self.grade(line)
        self.assertEqual(grade, "FAIL")
        self.assertIn("in neither the prompt nor the reply", ev)

    def test_near_match_is_a_note(self):
        line = "Humanizer after review: “built A QUEUE.” → Humanizer call: model Sonnet 5.5"
        grade, ev = self.grade(line)
        self.assertEqual(grade, "NOTE", ev)

    def test_humanizer_not_available_is_not_matched(self):
        line = "Humanizer after review: Led a team of five. → humanizer not available"
        self.assertEqual(self.grade(line)[0], "PASS")


class FindAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = self.tmp
        import chat_export
        self.folder = os.path.join(self.tmp, "projects", chat_export.claude_folder(os.getcwd()))

    def tearDown(self):
        if self.old is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self.old
        shutil.rmtree(self.tmp)

    def main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_run.main(["check_run.py", *args])
        return code, out.getvalue()

    def test_agent_id_finds_the_run_in_any_session(self):
        for session in ("older-session", "newer-session"):
            os.makedirs(os.path.join(self.folder, session, "subagents"))
        write_transcript(os.path.join(self.folder, "older-session", "subagents", "agent-a1b2.jsonl"), GOOD_RUN)
        write_transcript(os.path.join(self.folder, "newer-session", "subagents", "agent-other.jsonl"), [])
        code, out = self.main("--agent", "a1b2")
        self.assertEqual(code, 0, out)
        self.assertIn("Grade: PASS", out)
        self.assertTrue(out.startswith("transcript: " + os.path.join(self.folder, "older-session", "subagents", "agent-a1b2.jsonl")), out)

    def test_unknown_agent_exits_2(self):
        os.makedirs(os.path.join(self.folder, "s", "subagents"))
        code, out = self.main("--agent", "nope")
        self.assertEqual(code, 2)
        self.assertIn("no agent-nope.jsonl", out)

    def test_no_project_folder_exits_2(self):
        code, out = self.main("--agent", "a1b2")
        self.assertEqual(code, 2)
        self.assertIn("no Claude Code transcripts", out)

    def test_agent_and_transcript_are_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.main("--agent", "a1b2", "--transcript", "x.jsonl")


class Main(unittest.TestCase):
    def run_main(self, blocks, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            write_transcript(path, blocks)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = check_run.main(["check_run.py", "--transcript", path, *extra])
            return code, out.getvalue()

    def test_good_run_exits_0(self):
        code, out = self.run_main(GOOD_RUN)
        self.assertEqual(code, 0, out)
        self.assertIn("Grade: PASS", out)
        self.assertIn("SKIP provenance: no --copy given", out)

    def test_failing_run_exits_1(self):
        code, out = self.run_main([lookup(), REVIEWER_LINE, reviewer(model=None), HUMANIZER_LINE, humanizer()])
        self.assertEqual(code, 1)
        self.assertIn("FAIL subagent-model", out)
        self.assertIn("Grade: FAIL", out)

    def test_empty_transcript_exits_2(self):
        self.assertEqual(self.run_main([])[0], 2)

    def test_missing_transcript_exits_2(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_run.main(["check_run.py", "--transcript", os.path.join(HERE, "no-such.jsonl")]), 2)

    def test_copy_needs_base(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_main(GOOD_RUN, "--copy", HERE)

    def test_help_prints_the_docstring(self):
        """--help prints the docstring, which gives each check's rule, as written (#227)."""
        for flag in ("--help", "-h"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
                check_run.main(["check_run.py", flag])
            self.assertEqual(exit.exception.code, 0, flag)
            self.assertIn(check_run.__doc__.strip(), out.getvalue(), flag)


class MainWithCopy(CopyBase):
    """The whole script on a scratch copy, including how it lists the saved files."""

    def run_main(self, blocks=GOOD_RUN, publish=True):
        if publish and self.git("branch", "--show-current").strip():
            self.publish()
        path = os.path.join(self.copy, ".build", "run.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_transcript(path, blocks)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_run.main(["check_run.py", "--transcript", path, "--copy", self.copy, "--base", self.base])
        return code, out.getvalue()

    def test_non_ascii_folder_is_read(self):
        global FOLDER
        old, FOLDER = FOLDER, "outputs/applications/2026-02-01-\u7bc4\u4f8b-engineer"
        try:
            row = "| Skills line | backend target | outputs/resumes/backend.md |\n"
            self.save(provenance=PROVENANCE.replace("\n## Company context", row + "\n## Company context", 1))
        finally:
            FOLDER = old
        code, out = self.run_main()
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL provenance", out)
        self.assertIn("PASS resume-identical", out)

    def test_good_save_passes(self):
        self.save()
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        for check in ("git-status", "resume-identical", "provenance", "printed-lines"):
            self.assertIn("PASS " + check, out)
        self.assertIn("NOTE reviewer-prompt", out)  # the transcript's root is not this temporary copy

    def test_base_not_a_commit_exits_2(self):
        self.save()
        self.base = "0123456789abcdef0123456789abcdef01234567"
        code, out = self.run_main()
        self.assertEqual(code, 2, out)
        self.assertIn("rev-parse", out)

    def test_base_not_an_ancestor_exits_2(self):
        """A save committed on another line than the branch under test (the default branch)."""
        self.git("commit", "-q", "--allow-empty", "-m", "the branch moves on")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "HEAD~1")
        self.save()
        code, out = self.run_main()
        self.assertEqual(code, 2, out)
        self.assertIn("not an ancestor", out)

    def test_mode_prompts_are_read_from_the_copy(self):
        """scan.md's prompts are read at the base, as review.md is (#261)."""
        screen = agent("Screen batch-1", SCREEN % (ROOT, ROOT, ROOT), "opus", "general-purpose")
        self.assertIn("NOTE subagent-model", self.run_main([screen])[1])  # the base has no scan.md
        self.write("skills/career-log/modes/scan.md", SCAN_MD)
        self.commit("add scan")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.assertIn("PASS subagent-model", self.run_main([screen])[1])

    def test_upgrade_run_reads_review_md_and_typed_modes_at_head(self):
        """#503: an upgrade run's base is the older Engine; the prompts its review.md and scan.md give
        come with the upgrade commit, so they are read at HEAD too."""
        self.write("skills/career-log/modes/review.md", "# Review\n\nFirst line: `Read <root>/review-old.md`.\n")
        self.commit("the older Engine")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write("skills/career-log/modes/review.md", REVIEW_MD)
        self.write("skills/career-log/modes/scan.md", SCAN_MD)
        self.commit("upgrade: Template 0.2.0")
        screen = agent("Screen batch-1", SCREEN % (ROOT, ROOT, ROOT), "opus", "general-purpose")
        out = self.run_main(GOOD_RUN + [screen])[1]
        self.assertIn("NOTE reviewer-prompt", out)  # only the root differs from this temporary copy
        self.assertNotIn("does not match", out)
        self.assertIn("PASS subagent-model", out)  # scan.md at HEAD names the Screen prompt's type
        old = agent("Review drafts", "Read %s/review-old.md\n<posting>...</posting>" % ROOT)
        self.assertNotIn("does not match", self.run_main([REVIEWER_LINE, old])[1])  # the base's line passes too
        bad = self.run_main([REVIEWER_LINE, reviewer(first="Read the review file")])[1]
        self.assertIn("does not match %r or %r" % ("Read <root>/review-old.md", POINTER % ("<root>", "<root>")), bad)

    def test_nothing_saved_skips(self):
        code, out = self.run_main()
        self.assertIn("SKIP provenance: no file added or changed", out)


if __name__ == "__main__":
    unittest.main()
