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
FIT = 'Read %s/skills/career-log/modes/fit.md whole and follow its "Handed over by scan" bullet for the capture at %s.'
SCAN_MD = ("# Scan\n\n3. **Start one subagent per batch,** of a type that writes files. Its prompt's first line is `"
           + SCREEN % ("<root>", "<dir>", "<dir>") + "`; the rest is the Log root.\n"
           "3. Start one subagent per posting to fit, of the type step 6.3 names. Its prompt's first line is `"
           + FIT % ("<root>", "<capture path>") + "`.\n")
REVIEW_MD = "# Review\n\n## Dispatch\n\nFirst line: `" + POINTER % ("<root>", "<root>") + "` Then the drafts.\n"


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
MAP_LINE = text("Map: 10 requirements and duties, 11 rows; no row: none")
COURSE_LINE = text("Course work: none (4 entry files searched)\n\n| Requirement | ... |")


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
        fit = FIT % (ROOT, ROOT + "/.build/scan/2026-02-01/postings/example.md")
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
        grade, ev = self.map_count([MAP_LINE, COURSE_LINE])
        self.assertEqual(grade, "PASS", ev)

    def test_map_count_reprinted_until_none_pass(self):
        first = text("**Map:** 10 requirements and duties, 9 rows; no row: mentoring junior engineers")
        self.assertEqual(self.map_count([first, MAP_LINE, COURSE_LINE])[0], "PASS")

    def test_map_count_naming_a_missing_row_fails(self):
        last = text("Map: 10 requirements and duties, 9 rows; no row: mentoring junior engineers")
        self.assertEqual(self.map_count([last, COURSE_LINE])[0], "FAIL")

    def test_map_count_fewer_rows_saying_none_fails(self):
        self.assertEqual(self.map_count([text("Map: 10 requirements and duties, 7 rows; no row: none")])[0], "FAIL")

    def test_map_count_reworded_fails(self):
        grade, ev = self.map_count([text("Map: partial, 7 rows"), COURSE_LINE])
        self.assertEqual(grade, "FAIL")
        self.assertIn("does not parse", ev)

    def test_map_shown_without_count_fails(self):
        self.assertEqual(self.map_count([COURSE_LINE])[0], "FAIL")

    def test_map_count_after_the_map_fails(self):
        self.assertEqual(self.map_count([COURSE_LINE, MAP_LINE])[0], "FAIL")

    def test_map_count_per_posting(self):
        a = "Map (Example Corp, Engineer): 10 requirements and duties, 10 rows; no row: none"
        b = "Map (Other Inc, SRE): 12 requirements and duties, 11 rows; no row: on-call"
        self.assertEqual(self.map_count([text(a + "\n" + b)])[0], "FAIL")
        fixed = b.replace("11 rows; no row: on-call", "12 rows; no row: none")
        self.assertEqual(self.map_count([text(a + "\n" + b), text(fixed)])[0], "PASS")

    def test_map_count_under_the_course_work_line_pass(self):
        shown = "Course work: none (4 entry files searched)\n" + MAP_LINE["text"] + "\n\n| Requirement | ... |"
        self.assertEqual(self.map_count([text(shown)])[0], "PASS")

    def test_map_count_bold_and_trailing_words_pass(self):
        line = text("**Map:** **10** requirements and duties, **11** rows; no row: none (all mapped)")
        self.assertEqual(self.map_count([line, COURSE_LINE])[0], "PASS")

    def test_map_count_role_with_parentheses_is_read(self):
        line = text("Map (Example Corp, Software Engineer (Infrastructure)): 10 requirements and duties, 9 rows; no row: none")
        self.assertEqual(self.map_count([line])[0], "FAIL")

    def test_map_count_after_the_table_in_one_message_fails(self):
        self.assertEqual(self.map_count([text(COURSE_LINE["text"] + "\n|---|\n" + MAP_LINE["text"])])[0], "FAIL")

    def test_map_line_only_in_a_written_file_is_missing(self):
        write = {"type": "tool_use", "name": "Write", "input": {"file_path": "x.md", "content": MAP_LINE["text"]}}
        self.assertEqual(self.map_count([write, COURSE_LINE])[0], "FAIL")

    def test_map_count_none_with_more_words_fails(self):
        self.assertEqual(self.map_count([text("Map: 10 requirements and duties, 11 rows; no row: none except on-call")])[0],
                         "FAIL")

    def test_map_count_only_in_a_tool_call_is_a_note(self):
        echo = bash("echo 'Map: 10 requirements and duties, 11 rows; no row: none'")
        self.assertEqual(self.map_count([echo, COURSE_LINE])[0], "NOTE")

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
                "| Queue design | 2026-01-queue › How it works | queue@abc1234:docs/reports/design.md:12 |\n")
        self.save(provenance=PROVENANCE.replace("\n## Company context", rows + "\n## Company context", 1))
        grade, ev = check_run.check_provenance(self.copy, self.saved())
        self.assertEqual(grade, "PASS", ev)

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
        self.assertIn("added no Past phrasings line", ev)

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

    def test_same_wording_for_another_angle_pass(self):
        self.save(entry=self.phrasings(add=[
            '- **general:** "Built a job queue that retried failed tasks within one second." (%s)' % FOLDER]))
        self.assertEqual(check_run.check_phrasings(self.copy, self.base, self.saved())[0], "PASS")


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

    def run_main(self, blocks=GOOD_RUN):
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

    def test_nothing_saved_skips(self):
        code, out = self.run_main()
        self.assertIn("SKIP provenance: no file added or changed", out)


if __name__ == "__main__":
    unittest.main()
