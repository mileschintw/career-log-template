#!/usr/bin/env python3
"""Grade the mechanical checks of one clean-agent test run (docs/maintaining-tests.md in the
Template's source repo; the checks apply to any run of the skill, past-phrasings to a write save).

  python3 -I tools/check_run.py (--agent <id> | --transcript <run.jsonl>) [--copy <t>/log --base <sha>]

<run.jsonl> is the run's own transcript (Claude Code: `<session>/subagents/agent-<id>.jsonl` for a
run started as a subagent; `<session>.jsonl` in the project folder of the run's working directory,
under its CLAUDE_CONFIG_DIR's projects/, for a run started as its own `claude -p` process). The
subagents it started are read from its Agent tool calls, so their own transcripts are not needed.
--agent <id> finds it from the agent id the Agent tool's result gave: `agent-<id>.jsonl` in the
`subagents/` folder of any session in Claude Code's project folder for the working directory (as
tools/chat_export.py finds it, under CLAUDE_CONFIG_DIR or ~/.claude), so run it in the session
that started the run.
<t>/log is the run's scratch copy after the run. <sha> is the run's base: the parent of the run's
first commit (the head under test when the run committed on its branch), an ancestor of the copy's
HEAD. The save checks read the files added or changed between <sha> and HEAD (a file the save
deleted is not read). Without --copy, every check that reads the copy prints SKIP; when nothing
changed since <sha>, the save checks after commit-subject do.
--head <rev> names the head under test when it is not <sha>. With --copy, review.md, the
TYPED_MODES files and the files commit-subject reads are read at --head (else <sha>) and at the
copy's HEAD, the Engine an upgrade run installed: a text either gives passes. Without --copy,
review.md and the TYPED_MODES files are read as they are next to this script.

Prints `transcript: <path>`, the file it read, then one line per check,
`<PASS|NOTE|FAIL|SKIP> <check>: <evidence>`, in this order:
subagent-model, call-lines, reviewer-prompt, humanizer-after-review, map-count, outside-root,
save-branch, git-status, commit-subject, resume-identical, provenance, printed-lines,
past-phrasings; then `Grade: <FAIL | PASS with notes | PASS | none (every check skipped)> (...)`.
Exit 1 when a check fails. Exit 2, with one line saying why, when the transcript is missing or
holds no assistant message (often your own session's file instead of the run's), when --agent
finds no transcript, when <sha> is not a commit or not an ancestor of HEAD, or when git fails or
cannot run. A Log file that is not UTF-8 fails the check that reads it. Standard library only,
Python 3.11+.

Transcript checks:
- subagent-model: every subagent call names its model. Reviewer or humanizer without one: FAIL.
  Any other subagent (the company lookup) without one, a subagent on another model family than the
  run's own, or a subagent type other than Explore or Plan (the read-only types): NOTE. Another
  model family is no NOTE when the user's text before the call names that family (in the run's
  prompt, only the part after its `User message:` line; a relayed `User:` answer counts). The type
  is not graded when the prompt's first line matches one a TYPED_MODES file (scan.md) gives, since
  that mode names a type that writes files. Those first lines are the file's backticked
  `Read <root>/...` lines; each `<...>` matches a path, with no quote, no ". " and no second
  `/skills/career-log/` in it.
- call-lines: a `Reviewer call: model <m>, log root <path>` line before each reviewer call, a
  `Humanizer call: model <m>` line before each humanizer call. Missing, or written only inside a
  tool call (an `echo`): NOTE. A line naming another model family than the call's: FAIL. A line
  that starts with the label but does not parse: FAIL (read it, and grade it by its model).
- reviewer-prompt: each reviewer prompt's first line is review.md's pointer line (the backticked
  `Read <root>/...` line in its Dispatch), both `<root>`s replaced by the same path and nothing else
  changed (backslashes read as slashes). Otherwise FAIL. With --copy, a root that is not the copy's
  path: NOTE. Paths are compared with slashes, case and a trailing slash set aside, `/c/` read as
  `C:/`, and again after os.path.realpath, which resolves `..`, links and Windows short names of a
  path that exists; a NOTE left is another path, which may still be another spelling.
- humanizer-after-review: each reviewer call is followed by a humanizer call before the next
  reviewer call or the end of the run. Otherwise FAIL (grade by hand a review that changed no text,
  and a run where the humanizer skill was not available).
Calls are sorted in this order: a prompt whose first line names the humanizer is a humanizer call;
then a prompt that names modes/review.md, "Reviewer instructions" or "hiring-manager proxy", or a
description with the word "review" or "reviewer" (and not "humanizer"), is a reviewer call; then
any other prompt that names the humanizer is a humanizer call. A humanizer prompt that pastes
review.md's path past its first line counts as a reviewer: check a puzzling FAIL against the
call's description.
- map-count: the requirement map's count line (fit › Requirement map), `Map: <n> requirements and
  duties, <m> rows; no row: <none, or each>`, or `Map (<company>, <role>): ...` with several
  postings, as `tools/fit.py map` prints it: a shell call whose command runs fit.py's `map`, read
  from that call's output (its tool result; a command split over lines with a backslash or a backtick is
  read as one line). The last line each posting's label has across those outputs must say `no row:
  none` and have m >= n, and the output it is in must hold a line `map: ok` (a run that printed
  `bad:` lines has none). A map
  shown in the reply (a text message with a `Course work:` line and a table below it; the last such
  message counts, or the last message with a `Course work:` line when none has a table) must show
  above its table, in that message, a
  `Map:` line equal to the last one fit.py printed for its label, and its `Course work:` line must
  equal the last one fit.py printed. Otherwise FAIL. With no fit.py map output, a `Map:` line the
  run wrote itself (in a reply or an `echo`) or a map shown is a FAIL: the count is the tool's, not
  the agent's. Neither: SKIP. A run that built a map without showing it (interview, several
  postings) is graded by fit.py's lines alone.
map-count takes bold, italic and code marks out of a text before reading it.

With --copy (else SKIP): outside-root, from the transcript's write calls; save-branch, on the copy.
- outside-root: every file a Write, Edit, MultiEdit or NotebookEdit call wrote is under the copy
  (paths compared as reviewer-prompt compares them). One outside it: NOTE, naming each to delete.
  Files a shell command wrote are not read. No such call: SKIP.
- save-branch: the copy is on its default branch (origin/HEAD), every commit on HEAD is pushed
  (`origin/<default>..HEAD` counts 0), and the copy has one worktree. Otherwise, or with origin/HEAD
  unset: FAIL.

Save checks, on the changes between <sha> and the copy's HEAD:
- git-status: `git status --porcelain` prints nothing. Otherwise FAIL.
- commit-subject: each commit in <sha>..HEAD (merges set aside) has a subject the skill gives, or
  one a tool printed in the run as a `commit: <subject>` line (in the result of a shell call that
  runs a .py script). The subjects the skill gives are read from SKILL.md, every file in
  skills/career-log/modes/ and tools/sync.py, as they are at the head under test and at the copy's
  HEAD (an upgrade run commits by the mode of the release it installs): each quoted subject in a
  `sync.py commit "..."`, `sync.py settle commit --subject "..."` or `git commit -m "..."` command; each code span shaped
  `name(...): text` on a line that says commit; and each code span shaped `name: text` that follows
  "commit" or "subject" on its line with no other code span between, or right after "as" or
  "subject" (sync.py's own `commit:` and `committed:` lines set aside). In those, each `<...>` matches any text, `...` any text or none,
  `(s)`, `(es)` and `(y/ies)` after a letter the forms they spell (never the literal `(s)`), and
  anything else as written;
  one that starts with a `<...>` (`<the mode's message>`) names a tool's line, not a format, and is
  not read. A `consolidate(<slugs>)` subject
  must name, comma-separated, exactly the slugs of the entries its commit changes, and a
  `log(<slug>)` subject one entry the Log has at that commit (tools/entries.py `links-since` finds
  an entry's last consolidate by its slug). Otherwise FAIL. No commit: SKIP.
- resume-identical: every saved resume `.tex` under outputs/ is byte-identical to a `.tex` under
  the copy's .build/ (the drafts), or to a `.tex` under outputs/ at <sha> (an approved version saved
  unchanged). Otherwise FAIL.
- provenance: every application folder saved has a provenance.md, and every row of a provenance
  table in a saved provenance file (an application's provenance.md, outputs/resumes/*.md,
  outputs/reports/*.md) passes write step 10's rule, the one tools/check_save.py prints (its --help
  gives it): no entry section naming a file other than an entry, profile.md or direction.md, or a
  section that is no heading in it, and no column after the first citing another output. Otherwise
  FAIL. A provenance file with no
  provenance table: NOTE.
- printed-lines, only when a commit in <sha>..HEAD is a write save (SKIP otherwise): write step
  10's **Run the save check** lines, in the output of a tools/check_save.py run before the save's
  commit. A commit call is a shell (Bash, PowerShell) `git ... commit`, or a tools/sync.py `commit`
  or `settle commit`, whose `committed: [<branch> <sha>] <subject>` line counts as git's own. The
  save's commit is the commit call that made the
  first write commit touching a provenance file: its result names that commit's short sha, or else
  its command holds that commit's subject before a closing quote (a run may commit facts with
  `write(` earlier); else the first
  such call with `write(` in its command whose result is not a failure (an error starting `Exit
  code` with no `] write(` commit line in it), or else the last commit call; with none,
  the whole transcript. A check run is a shell call whose command runs check_save.py with python3, python
  or py, before that commit, or in the commit's own command ahead of the commit call
  (`check_save.py ... && git commit ...`); only its tool result is read, so a line the run wrote
  itself, echoed or read from a file does not count. The last check run must have exited 0 (its
  `check_save: ok` line). Each provenance file (as above) that a write commit touched needs a
  `Provenance check (<file>): <n> rows; citing another output: <...>` line, <file> its path or
  ending it after a `/` (a line with no `(<file>)` counts for the only file; a label that fits two
  files counts for neither). Its last such line must say `none` (as map-count reads it), count the
  rows the file has at the first write commit that touched it, and come after the run's last Write
  or Edit of that file. When the run made a reviewer call, the last check run that printed a
  `Humanizer after review:` line must print only lines in the form `Humanizer after review: <line>
  → <its Humanizer call: line, or humanizer not available>` (`->` also read), or `Humanizer after
  review: none`. Anything else, a missing line, or a check run only after the commit: FAIL. The
  <line> of each line that names a Humanizer call line must be in the prompt or the reply (its tool
  result) of a humanizer call made after the run's first reviewer call, with marks, outer quotes and
  extra spaces set aside. Found only once case, quotes and a trailing `...` are set aside too: NOTE.
  Found in neither: FAIL.
- past-phrasings, only when a commit in <sha>..HEAD is a write save (its subject starts with
  `write(`; SKIP otherwise, since other modes trim the section by their own steps): in each entry
  the save changed, the `## Past phrasings` lines are kept as they stand: no line removed and a
  similar one added (a rewrite), no more lines removed than added (a drop happens only beside an
  addition, at the three-wording cap), and no added line that differs only in its words from a line
  already there for the same angle. Otherwise FAIL. Any other removed line: NOTE, since a drop at
  the cap and a rewrite in new words both show as +1 -1. A line's angle is its own prefix in the
  format entries/_template.md gives, `- **ai-infra:** "..."`: a hyphen slug, then the wording in
  quotes (straight, curly or corner), so a bold label inside a wording (`- **Queues:** Designed...`)
  is no angle. Entries written before that format may group wordings under a label line
  (`**ai-infra**`, `- **ai-infra:**` with the wordings indented under it, `### ai-infra`), which
  sets the angle of the lines below it that have no prefix of their own; lines with no angle are
  compared with every line. Placeholder lines
  (`none yet`, `GAP:`) are not wordings. The evidence always gives each entry's `+added -removed`
  counts. A write save that adds no line: NOTE, to check the approved resume or bullets report has
  no new bullet (only those feed the section, write step 10). Two lines differ only in
  words when their word sequences, lowercased with the trailing (citation) stripped, have a difflib
  ratio of at least SIMILAR (0.85); two added lines are compared with each other too. Whether a
  claim reached the cap for its angle, and whether two wordings differ in meaning, stay with the
  judgement grader. Save levels (write › Save levels): a folder whose `archived.md` the range adds,
  or a report in outputs/reports/ whose `Archived (user, YYYY-MM-DD)` line the range adds (a
  bullets report), was saved Archived or demoted. A removed line citing that folder or report is the
  demote's and is set aside; an added line citing it: FAIL. When every write commit in the range
  adds an `archived.md` or such a line, adding no line is a PASS, not a NOTE. An Archived target-run
  resume has no marker, so it grades NOTE here and is passed by hand.
"""
import argparse, json, os, re, sys
from collections import Counter

READ_ONLY = ("Explore", "Plan")
TYPED_MODES = ("skills/career-log/modes/scan.md",)   # modes that name the type of each subagent they prompt
PLACEHOLDER = r'(?:(?!/skills/career-log/|\. )[^"])+?'   # a <...> in their prompts: no second pointer, sentence or quote
FAMILIES = ("haiku", "sonnet", "opus", "fable")
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from entries import ENTRY_PATH   # what an entry's path is
from entries import SIMILAR, phrasings, similar, words   # the Past phrasings parser (its docstring's *Past phrasings*)
import logfiles   # git with a timeout, UTF-8 reads
from logfiles import provenance_rows   # a provenance table's rows
from check_save import PROVENANCE_FILE, report_marks, row_problem   # write step 10's provenance rule; a report's Archived line


# ---------- transcript ----------

REMINDER = re.compile(r"<system-reminder>.*?(?:</system-reminder>|$)", re.S)   # the harness's text, not the user's

def events(path):
    """The run's blocks in order: ("text", text), ("tool", name, input, id) and, once per message,
    ("model", model id) from its assistant messages; ("result", text, tool id, failed) from the tool
    results in its user messages, failed when the result is an error that starts `Exit code`, and
    ("user", text) from the text the user (or the tester, as the user) sent, system reminders taken out."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                out.append(("user", REMINDER.sub("", msg["content"])))
                continue
            if not isinstance(msg.get("content"), list):
                continue
            if msg.get("role") == "user":
                for b in msg["content"]:
                    if isinstance(b, dict) and b.get("type") == "text":
                        out.append(("user", REMINDER.sub("", b.get("text", ""))))
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        body = b.get("content")
                        body = body if isinstance(body, str) else "\n".join(
                            c.get("text", "") for c in body or [] if isinstance(c, dict) and c.get("type") == "text")
                        out.append(("result", body, b.get("tool_use_id"),
                                    bool(b.get("is_error")) and body.startswith("Exit code")))
                continue
            if msg.get("role") != "assistant":
                continue
            if msg.get("model"):
                out.append(("model", msg["model"]))
            for b in msg["content"]:
                if b.get("type") == "text":
                    out.append(("text", b.get("text", "")))
                elif b.get("type") == "tool_use":
                    out.append(("tool", b.get("name", ""), b.get("input") or {}, b.get("id")))
    return out


def subagent_calls(evs):
    """(event index, kind, input) for each subagent call; kind is reviewer, humanizer or other."""
    calls = []
    for i, e in enumerate(evs):
        if e[0] == "tool" and e[1] in ("Agent", "Task"):
            prompt = (e[2].get("prompt") or "").replace("\\", "/")
            desc = (e[2].get("description") or "").lower()
            if "humanizer" in prompt.split("\n", 1)[0].lower():
                kind = "humanizer"
            elif (any(k in prompt for k in ("modes/review.md", "Reviewer instructions", "hiring-manager proxy"))
                  or (re.search(r"\breview(er)?\b", desc) and "humaniz" not in desc)):
                kind = "reviewer"
            elif "humanizer" in prompt.lower():
                kind = "humanizer"
            else:
                kind = "other"
            calls.append((i, kind, e[2]))
    return calls


def label(inp):
    return "%r (%s)" % (inp.get("description") or "no description", inp.get("subagent_type") or "no type")


def family(name):
    low = (name or "").lower()
    return next((f for f in FAMILIES if f in low), low.strip())


def mode_prompts(texts):
    """The first lines the TYPED_MODES texts give their subagents, as regexes: each `<...>` a path."""
    rxs = []
    for text in texts:
        for tmpl in re.findall(r"`(Read <root>/[^`]*)`", text):
            parts = re.split(r"<[^<>]+>", tmpl)
            rxs.append(re.compile("^" + PLACEHOLDER.join(re.escape(p) for p in parts) + "$"))
    return rxs


def asked(evs, upto, fam):
    """Whether the user's text before event upto names this model family (in the run's prompt, only
    the part after its `User message:` line)."""
    for e in evs[:upto]:
        if e[0] == "user":
            said = e[1].split("User message:", 1)[-1]
            if fam and re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(fam), said, re.I):
                return True
    return False


def check_models(calls, evs=(), typed=()):
    fails, notes, seen = [], [], []
    runs = {family(e[1]) for e in evs if e[0] == "model" and not e[1].startswith("<")}
    for i, kind, inp in calls:
        model = inp.get("model")
        seen.append("%s %s model=%s" % (kind, label(inp), model or "none"))
        if not model:
            (fails if kind in ("reviewer", "humanizer") else notes).append("%s %s has no model" % (kind, label(inp)))
        elif len(runs) == 1 and family(model) not in runs:
            if asked(evs, i, family(model)):
                seen[-1] += " (the user asked for %s)" % family(model)
            else:
                notes.append("%s %s runs on %s, the run on %s" % (kind, label(inp), model, next(iter(runs))))
        first = (inp.get("prompt") or "").split("\n", 1)[0].rstrip().replace("\\", "/")
        if inp.get("subagent_type") not in READ_ONLY and not any(rx.match(first) for rx in typed):
            notes.append("%s %s is not a read-only type" % (kind, label(inp)))
    if not calls:
        return "SKIP", "no subagent calls"
    if fails:
        return "FAIL", "; ".join(fails + ["calls: " + ", ".join(seen)])
    if notes:
        return "NOTE", "; ".join(notes + ["calls: " + ", ".join(seen)])
    return "PASS", "; ".join(seen)


M = r"[*_`]*"
LINE_RE = {"reviewer": re.compile(r"Reviewer call" + M + r":" + M + r"\s*model:?\s+([^,\n]+?)\s*,\s*log root:?\s+(\S[^\n]*)"),
           "humanizer": re.compile(r"Humanizer call" + M + r":" + M + r"\s*model:?\s+([^\n]+)")}
LABEL_START = {k: re.compile(r"^[\s>*_`-]*%s call\b" % k.capitalize(), re.M) for k in LINE_RE}


def strings(value):
    """Every string inside a tool input."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def check_call_lines(evs, calls):
    fails, notes, ok = [], [], []
    last = {"reviewer": -1, "humanizer": -1}
    for i, kind, inp in calls:
        if kind == "other":
            continue
        start, last[kind] = last[kind], i
        in_text, in_call, unparsed = None, None, None
        for e in evs[start + 1:i]:
            if e[0] not in ("text", "tool") or (e[0] == "tool" and e[1] in ("Agent", "Task")):
                continue
            for blob in ([e[1]] if e[0] == "text" else strings(e[2])):
                if LABEL_START[kind].search(blob) and not LINE_RE[kind].search(blob):
                    unparsed = blob[LABEL_START[kind].search(blob).start():].strip().split("\n", 1)[0]
                for m in LINE_RE[kind].finditer(blob):
                    if e[0] == "text":
                        in_text = m
                    else:
                        in_call = m
        found, in_tool = in_text or in_call, not in_text
        name = kind.capitalize()
        if not found and unparsed:
            fails.append("%s call line %r does not parse: read its model" % (name, unparsed[:80]))
            continue
        if not found:
            notes.append("no %s call line before %s" % (name, label(inp)))
            continue
        line = found.group(0).strip().strip("\"'`")
        named, model = found.group(1).strip().strip("\"'`*"), inp.get("model")
        if model and family(named) != family(model):
            fails.append("%s call line names %r, the call sets model=%s" % (name, named, model))
        elif in_tool:
            notes.append("%s call line %r written in a tool call, not in the conversation" % (name, line[:80]))
        else:
            ok.append("%s call line %r" % (name, line[:80]))
    if not any(k != "other" for _, k, _ in calls):
        return "SKIP", "no reviewer or humanizer call"
    if fails:
        return "FAIL", "; ".join(fails)
    if notes:
        return "NOTE", "; ".join(notes + ok)
    return "PASS", "; ".join(ok)


def pointer_line(review_md):
    """review.md's pointer line, as a regex with both <root>s the same path."""
    m = re.search(r"`(Read <root>/[^`]*)`", review_md)
    if not m:
        return None, None
    tmpl = m.group(1)
    parts = [re.escape(p) for p in tmpl.split("<root>")]
    rx = parts[0] + r"(?P<root>.+?)" + parts[1] + "".join(r"(?P=root)" + p for p in parts[2:])
    return tmpl, re.compile("^" + rx + "$")


def norm(path):
    """A path for comparison: forward slashes, no trailing slash, /c/ as c:/, lowercase."""
    s = path.strip().replace("\\", "/").rstrip("/")
    m = re.match(r"^/([A-Za-z])/(.*)$", s)
    return ("%s:/%s" % (m.group(1), m.group(2)) if m else s).lower()


def real(path):
    """norm() of the path with its links and Windows short names resolved (os.path.realpath), for a
    path that exists; a relative path as norm() gives it."""
    s = path.strip().replace("\\", "/")
    m = re.match(r"^/([A-Za-z])/(.*)$", s)
    if m and os.name == "nt":
        s = "%s:/%s" % (m.group(1), m.group(2))
    return norm(os.path.realpath(s)) if os.path.isabs(s) else norm(s)


def same_path(a, b):
    return norm(a) == norm(b) or real(a) == real(b)


def inside(path, root):
    """Whether path is root or under it, in any spelling norm() or real() reads as the same."""
    return any(p == r or p.startswith(r.rstrip("/") + "/") for p in (norm(path), real(path)) for r in (norm(root), real(root)))


def check_reviewer_prompt(calls, review_md, copy=None):
    """review_md: review.md's text, or its texts at several revisions (a first line may match any)."""
    revs = [inp for _, kind, inp in calls if kind == "reviewer"]
    if not revs:
        return "SKIP", "no reviewer call"
    lines = [pl for pl in map(pointer_line, [review_md] if isinstance(review_md, str) else review_md) if pl[1]]
    if not lines:
        return "FAIL", "no `Read <root>/...` pointer line in modes/review.md"
    tmpl = " or ".join("%r" % t for t in dict.fromkeys(t for t, _ in lines))
    bad, notes, ok = [], [], []
    for inp in revs:
        first = (inp.get("prompt") or "").split("\n", 1)[0].rstrip().replace("\\", "/")
        m = next((m for _, rx in lines for m in [rx.match(first)] if m), None)
        root = m.group("root") if m else (re.search(r"Read (.+?)/skills/career-log/modes/review\.md", first) or [None, None])[1]
        if not m:
            bad.append("%s first line %r does not match %s" % (label(inp), first, tmpl))
        if root and copy and not same_path(root, copy):
            notes.append("%s root %s is not the copy %s" % (label(inp), root, copy))
        elif m:
            ok.append("%s root %s" % (label(inp), root))
    if bad:
        return "FAIL", "; ".join(bad + notes + ok)
    return ("NOTE", "; ".join(notes + ok)) if notes else ("PASS", "; ".join(ok))


def check_humanizer_after_review(calls):
    seq = [(i, kind, inp) for i, kind, inp in calls if kind != "other"]
    revs = [n for n, c in enumerate(seq) if c[1] == "reviewer"]
    if not revs:
        return "SKIP", "no reviewer call"
    bad, ok = [], []
    for n in revs:
        nxt = next((c for c in seq[n + 1:] if c[1] == "reviewer"), None)
        upto = seq.index(nxt) if nxt else len(seq)
        hum = [c for c in seq[n + 1:upto] if c[1] == "humanizer"]
        if hum:
            ok.append("%s, then humanizer %s" % (label(seq[n][2]), label(hum[0][2])))
        else:
            bad.append("no humanizer call after reviewer %s" % label(seq[n][2])
                       + (" before the next reviewer call" if nxt else " to the end of the run")
                       + " (grade by hand if that review changed no text)")
    return ("FAIL", "; ".join(bad)) if bad else ("PASS", "; ".join(ok))


EMPHASIS = re.compile(r"[*_`]")


def printed(evs, label_re, line_re, upto=None):
    """(lines in the conversation, lines only in tool calls, label lines that do not parse), each a
    list of ((event index, offset), match or text), for the events before index upto. A tool call
    counts only when it is a shell command (an `echo`). Bold, italic and code marks are taken out
    first, so `**Map:** **10** ...` reads as `Map: 10 ...`."""
    in_text, in_call, unparsed = [], [], []
    for i, e in enumerate(evs[:upto]):
        if e[0] not in ("text", "tool") or (e[0] == "tool" and e[1] not in SHELLS):
            continue
        for blob in ([e[1]] if e[0] == "text" else strings(e[2])):
            blob = EMPHASIS.sub("", blob)
            found = list(line_re.finditer(blob))
            (in_text if e[0] == "text" else in_call).extend(((i, m.start()), m) for m in found)
            if e[0] == "text":
                starts = [m.start() for m in found]
                unparsed += [((i, s.start()), blob[s.start():].lstrip().split("\n", 1)[0].strip()) for s in label_re.finditer(blob)
                             if not any(s.start() <= a < s.end() for a in starts)]
    return in_text, in_call, unparsed


def says_none(text):
    """`none` alone, or with a full stop or a note in parentheses after it (and an echo's quote)."""
    return bool(re.fullmatch(r"\s*none\s*(?:\.|\([^)]*\))?[\s\"']*", text, re.I))


MAP_LABEL = re.compile(r"^[\s>|-]*(Map(?:\s*\(.*?\))?:)", re.M)
MAP_RE = re.compile(r"Map(?:\s*\((.*?)\))?:\s*(\d+)\s+requirements? and dut(?:y|ies)\s*,\s*"
                    r"(\d+)\s+rows?\s*;\s*no row:?\s*([^\n]*)")
COURSE_WORK = re.compile(r"^[\s>|-]*(Course work:[^\n]*)", re.M)
# a shell command that runs tools/fit.py's map subcommand (--root may come before it)
FIT_MAP = re.compile(r"\bfit\.py[\"']?\s(?:[^;&|\n]*?\s)?map(?=\s|$)")


def one_line(text):
    return " ".join(EMPHASIS.sub("", text).split())


def fit_map_lines(evs):
    """([(Map line match, whether its output says `map: ok`)], last Course work line) in the outputs
    of the run's fit.py map calls."""
    results = {e[2]: e[1] for e in evs if e[0] == "result"}
    maps, course = [], None
    for e in evs:
        if FIT_MAP.search(re.sub(r"[\\`]\r?\n", " ", command(e))):
            out = results.get(e[3]) or ""
            ok = bool(re.search(r"^map: ok[ \t\r]*$", out, re.M))
            maps += [(m, ok) for m in MAP_RE.finditer(out)]
            found = COURSE_WORK.findall(out)
            course = one_line(found[-1]) if found else course
    return maps, course


def check_map_count(evs):
    tool, course = fit_map_lines(evs)
    lines, in_call, unparsed = printed(evs, MAP_LABEL, MAP_RE)
    shown = [(i, m.start(), t) for i, e in enumerate(evs) if e[0] == "text"
             for t in [EMPHASIS.sub("", e[1])] for m in [COURSE_WORK.search(t)] if m]
    shown = [s for s in shown if re.compile(r"^\s*\|", re.M).search(s[2], s[1])] or shown
    if not tool:
        if lines or in_call or unparsed:
            first = (lines or in_call)[-1][1].group(0) if lines or in_call else unparsed[-1][1]
            return "FAIL", "Map line %r with no tools/fit.py map output: run it and show its lines" % first.strip()[:120]
        if shown:
            return "FAIL", "a map was shown (a Course work: line) with no tools/fit.py map output"
        return "SKIP", "no tools/fit.py map run and no map shown"
    last, passed = {}, {}
    for m, done in tool:
        last[(m.group(1) or "").strip()] = m
        passed[(m.group(1) or "").strip()] = done
    bad, ok = [], []
    for label, m in last.items():
        n, rows = int(m.group(2)), int(m.group(3))
        line = m.group(0).strip()[:160]
        if not passed[label]:
            bad.append("fit.py's last map run for %r printed bad: lines, not map: ok" % line)
        elif not says_none(m.group(4)):
            bad.append("fit.py's last Map line names requirements with no row: %r" % line)
        elif rows < n:
            bad.append("fit.py's last Map line has fewer rows than requirements and duties: %r" % line)
        else:
            ok.append("%r" % line)
    if shown:
        i, at, text = shown[-1]
        table = re.compile(r"^\s*\|", re.M).search(text, at)
        above = [m for m in MAP_RE.finditer(text[:table.start() if table else len(text)])]
        if not above:
            bad.append("the map shown has no Map: line above its table")
        else:
            m = above[-1]
            want = last.get((m.group(1) or "").strip())
            if not want or one_line(m.group(0)) != one_line(want.group(0)):
                bad.append("the map shown says %r, fit.py printed %r" % (one_line(m.group(0))[:120],
                                                                          one_line(want.group(0))[:120] if want else None))
        cw = one_line(COURSE_WORK.search(text, at).group(1))
        if course and cw != course:
            bad.append("the map shown says %r, fit.py printed %r" % (cw[:120], course[:120]))
        if not bad:
            ok.append("shown as fit.py printed it")
    if bad:
        return "FAIL", "; ".join(bad + ok)
    return "PASS", "; ".join(ok)


HUM_LABEL = re.compile(r"^[\s>|-]*Humanizer after review:", re.M)
HUM_RE = re.compile(r"Humanizer after review:\s*(?:(\S[^\n]*?)\s*(?:→|->)\s*(\S[^\n]*)"
                    r"|(none)[ \t]*(?:\.|\([^)\n]*\))?[ \t]*(?=\n|$))", re.I)
PROV_LABEL = re.compile(r"^[\s>|-]*Provenance check(?:\s*\(.*?\))?:", re.M)
PROV_RE = re.compile(r"Provenance check(?:\s*\((.*?)\))?:\s*(\d+)\s+rows?\s*;\s*citing another output:?\s*([^\n]*)")
# running it, not reading it: a command (`&` calls one in PowerShell) that starts with an
# interpreter, then its flags, then the script
CHECK_SAVE = re.compile(r"(?:^|[;&|(\n])\s*(?:\w+=\S+\s+)*(?:&\s*)?[\"']?(?:\"[^\"]*[\\/]|'[^']*[\\/]|[^\s\"';&|]*[\\/])?"
                        r"(?:python3?|py)(?:\.exe)?[\"']?(?:\s+-[XW]\s+[^\s-]\S*|\s+-\S+)*\s+"
                        r"[\"']?(?:\"[^\"]*[\\/]|'[^']*[\\/]|[^\s\"']*[\\/])?check_save\.py\b",
                        re.I)
EDITS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
# `git ... commit`, or tools/sync.py's commit or settle commit, which the modes run in its place
COMMIT = re.compile(r"\bgit\b(?:\s+(?:-[Cc]\s+(?:\"[^\"]*\"|'[^']*'|\S+)|--\S+))*\s+commit\b"
                    r"|\bsync\.py[\"']?(?:\s+--root(?:=|\s+)(?:\"[^\"]*\"|'[^']*'|\S+))?"
                    r"\s+(?:settle(?:\s+--root(?:=|\s+)(?:\"[^\"]*\"|'[^']*'|\S+))?\s+)?commit\b")
SHELLS = ("Bash", "PowerShell")


def hum_ok(m):
    """A Humanizer after review line in the given form: `none`, or each changed line → a call line."""
    if m.group(1) and m.group(1).startswith("not in the form"):
        return False
    return bool(m.group(3)) or bool(LINE_RE["humanizer"].search(m.group(2))
                                    or re.search(r"(?:→|->)\s*humanizer not available", m.group(0), re.I))


def table_lines(tables, lines, ambiguous):
    """Each table's last line among these, as (position, match): a label equal to its path, or its
    end after a `/` (`./` set aside); an unlabelled line counts for the only table; a label that fits
    two tables counts for neither and goes in ambiguous."""
    named = {}
    for pos, m in lines:
        label = (m.group(1) or "").strip().replace("\\", "/")
        label = label[2:] if label.startswith("./") else label
        match = [t for t in tables if label and (t == label or t.endswith("/" + label))]
        if len(match) > 1:
            ambiguous.add(label)
            continue
        for t in (match or ([tables[0]] if len(tables) == 1 and not label else [])):
            named[t] = (pos, m)
    return named


def command(e):
    return str(e[2].get("command") or "") if e[0] == "tool" and e[1] in SHELLS else ""


def check_printed_lines(evs, calls, copy, base, saved):
    subject = dict(w.split(" ", 1) for w in git(copy, "log", "--format=%H %s", "%s..HEAD" % base).splitlines()
                   if w.split(" ", 1)[1:] and w.split(" ", 1)[1].startswith("write("))
    writes = list(subject)
    if not writes:
        return "SKIP", "no write save in %s..HEAD" % base
    files = {w: git(copy, "show", "--name-only", "--format=", w).splitlines() for w in writes}
    tables = [p for p in saved if any(p in f for f in files.values()) and PROVENANCE_FILE.match(p)]
    results = {e[2]: e for e in evs if e[0] == "result"}
    out_of = lambda e: results.get(e[3], ("", "", "", False))
    # a commit call failed when its result is an error and shows no commit made (a push may fail after it)
    failed = lambda e: bool(out_of(e)[3]) and not re.search(r"\]\s+write\(", out_of(e)[1])
    commits = [i for i, e in enumerate(evs) if COMMIT.search(command(e))]
    # the save's commit: the call that made the first write commit touching a provenance file (a run
    # may commit facts with write( earlier): its result names its short sha, or its command its
    # subject; else the first write( commit call that did not fail
    first = [w for w in reversed(writes) if any(t in files[w] for t in tables)][:1]
    by_sha = [i for i in commits if first and re.search(r"\b%s" % first[0][:7], out_of(evs[i])[1])]
    by_subject = [i for i in commits if first and not failed(evs[i])
                  and re.search(re.escape(subject[first[0]]) + r"[\"']", command(evs[i]))]
    made = by_sha or by_subject
    save = made or [i for i in commits if "write(" in command(evs[i]) and not failed(evs[i])]
    upto = save[0] if save else commits[-1] if commits else len(evs)
    where = "before the save's git commit call" if commits else "in the run"
    chained = lambda i: i == upto and CHECK_SAVE.search(command(evs[i])).start() < COMMIT.search(command(evs[i])).start()
    runs = [i for i, e in enumerate(evs[:upto + 1]) if CHECK_SAVE.search(command(e)) and (i < upto or chained(i))]
    after = [i for i, e in enumerate(evs) if i > upto and CHECK_SAVE.search(command(e))]
    prov, hum, unparsed = [], [], []
    for i in runs:
        out = out_of(evs[i])[1]
        prov += [((i, m.start()), m) for m in PROV_RE.finditer(out)]
        found = [((i, m.start()), m) for m in HUM_RE.finditer(out)]
        if found or HUM_LABEL.search(out):
            hum = found
        unparsed += [l.strip() for l in out.splitlines() if l.strip().startswith(("Provenance check", "Humanizer after review"))
                     and not (PROV_RE.match(l.strip()) or HUM_RE.match(l.strip()))]
    why = []
    if not runs:
        why.append("tools/check_save.py ran only after the save's commit" if after
                   else "no tools/check_save.py run %s" % where)
        if printed(evs, PROV_LABEL, PROV_RE, upto)[0] or printed(evs, HUM_LABEL, HUM_RE, upto)[0]:
            why.append("the run wrote the lines itself: they count only as the tool's output")
    bad, ok = [], []
    if runs and not re.search(r"^check_save: ok\s*$", out_of(evs[runs[-1]])[1], re.M):   # printed on exit 0 only
        bad.append("the last tools/check_save.py run %s did not exit 0 (no `check_save: ok` line)" % where)
    ambiguous = set()
    named = table_lines(tables, prov, ambiguous)
    bad += ["Provenance check label %r fits more than one provenance file" % a for a in sorted(ambiguous)]
    for t in tables:
        if t not in named:
            bad.append("no Provenance check line for %s in tools/check_save.py's output %s" % (t, where))
            continue
        (i, _), m = named[t]
        line = m.group(0).strip()[:160]
        rows = len(provenance_rows(show(copy, next(w for w in reversed(writes) if t in files[w]), t)))
        edits = [e for e in evs[i + 1:upto] if e[0] == "tool" and e[1] in EDITS
                 and str(e[2].get("file_path") or e[2].get("notebook_path") or "").replace("\\", "/").endswith("/" + t)]
        if not says_none(m.group(3)):
            bad.append("last Provenance check line for %s does not say none: %r" % (t, line))
        elif int(m.group(2)) != rows:
            bad.append("last Provenance check line for %s counts %s rows, the committed file has %d: %r"
                       % (t, m.group(2), rows, line))
        elif edits:
            bad.append("%s was edited (%s) after its last Provenance check line" % (t, edits[-1][1]))
        else:
            ok.append("%r" % line)
    notes = []
    if any(k == "reviewer" for _, k, _ in calls):
        if not hum:
            bad.append("no Humanizer after review line in tools/check_save.py's output %s" % where)
        first = next(i for i, k, _ in calls if k == "reviewer")
        texts = [one_line(t) for i, k, inp in calls if k == "humanizer" and i > first
                 for t in (inp.get("prompt") or "", out_of(evs[i])[1])]
        for _, m in hum:
            line = m.group(0).strip()[:160]
            if not hum_ok(m):
                bad.append("Humanizer after review line has no Humanizer call line for its changed text: %r" % line)
            elif m.group(3) or not LINE_RE["humanizer"].search(m.group(2)):
                ok.append("%r" % line)
            else:
                found = humanized(m.group(1), texts)
                if found == "yes":
                    ok.append("%r" % line)
                elif found == "nearly":
                    notes.append("the text of %r is in a humanizer call's prompt or reply after the review only with other "
                                 "quotes, case or a cut: compare them" % line)
                else:
                    bad.append("the text of %r is in neither the prompt nor the reply of a humanizer call after the review"
                               % line)
    if bad:
        return "FAIL", "; ".join(bad + why + ["tool line not in the form step 10 gives: %r" % u[:120] for u in unparsed[-2:]] + notes + ok)
    if notes:
        return "NOTE", "; ".join(notes + ok)
    return "PASS", "; ".join(ok)


QUOTES = "\"'\u2018\u2019\u201c\u201d\u300c\u300d"


def humanized(line, texts):
    """yes: the line, its marks and outer quotes taken out and its spaces collapsed, is in one of
    the texts; nearly: it is once case, quotes and a trailing `...` cut are set aside; else no."""
    want = one_line(line).strip(QUOTES + " ")
    if not want:
        return "no"
    if any(want in t for t in texts):
        return "yes"
    loose = lambda t: re.sub("[%s]" % QUOTES, "", t).lower()
    cut = loose(re.sub(r"\s*(?:\.\.\.|…)$", "", want))
    return "nearly" if cut and any(cut in loose(t) for t in texts) else "no"


# ---------- scratch copy ----------

def git(copy, *args):
    """The stdout of `git -C <copy> <args>`; LogError when git cannot run, times out or fails."""
    return logfiles.git(copy, *args)


def show(copy, rev, path):
    """A file's text at rev ("" when rev has none), any byte that is not UTF-8 replaced."""
    data = logfiles.git_blob(copy, rev, path)
    return data.decode("utf-8", "replace") if data is not None else ""


def read(path):
    """A file's text; UnicodeDecodeError when it is not UTF-8 (the checks grade that)."""
    return logfiles.read_text(path)


def check_branch(copy):
    default = logfiles.default_branch(copy)
    if not default:
        return "FAIL", ("the copy has no origin/HEAD, so its default branch is unknown: a copy the harness built has both "
                        "(`git remote -v`; `git remote set-head origin <default>` sets a missing HEAD)")
    branch = git(copy, "branch", "--show-current").strip()
    ahead = git(copy, "rev-list", "--count", "origin/%s..HEAD" % default).strip()
    trees = logfiles.checkouts(copy)
    bad = []
    if branch != default:
        bad.append("HEAD is %s, not the default branch %s" % ("branch " + branch if branch else "detached", default))
    if ahead != "0":
        bad.append("%s commit(s) on HEAD not pushed to origin/%s" % (ahead, default))
    if len(trees) > 1:
        bad.append("the copy has %d worktrees (`git worktree prune` drops one whose folder is gone): %s"
                   % (len(trees), ", ".join(trees)))
    if bad:
        return "FAIL", "; ".join(bad)
    return "PASS", "on %s, pushed to origin/%s, one worktree" % (default, default)


def check_outside(evs, copy):
    written = []
    for e in evs:
        if e[0] == "tool" and e[1] in EDITS:
            path = str(e[2].get("file_path") or e[2].get("notebook_path") or "")
            if path and path not in written:
                written.append(path)
    if not written:
        return "SKIP", "no Write or Edit call"
    outside = [p for p in written if not inside(p, copy)]
    if outside:
        return "NOTE", ("written outside the Log root %s (delete each): %s; files a shell command wrote are not read"
                        % (copy, ", ".join(outside)))
    return "PASS", "%d file(s) written, all under %s; files a shell command wrote are not read" % (len(written), copy)


def check_status(copy):
    out = git(copy, "status", "--porcelain")
    return ("FAIL", "uncommitted: " + "; ".join(out.splitlines()[:10])) if out.strip() else ("PASS", "git status is clean")


def blob(copy, rev, path):
    return logfiles.git_blob(copy, rev, path)


def check_resume(copy, saved, base):
    texs = [p for p in saved if p.startswith("outputs/") and p.endswith(".tex")]
    if not texs:
        return "SKIP", "no resume .tex saved"
    drafts = {}
    for d, _, files in os.walk(os.path.join(copy, ".build")):
        for f in files:
            if f.endswith(".tex"):
                with open(os.path.join(d, f), "rb") as fh:
                    drafts[os.path.relpath(os.path.join(d, f), copy).replace("\\", "/")] = fh.read()
    for p in git(copy, "ls-tree", "-r", "-z", "--name-only", base, "--", "outputs").split("\0"):
        if p.endswith(".tex"):
            drafts["%s at %s" % (p, base[:12])] = blob(copy, base, p)
    bad, ok = [], []
    for t in texs:
        with open(os.path.join(copy, t), "rb") as f:
            body = f.read()
        same = [name for name, data in drafts.items() if data == body]
        (ok if same else bad).append("%s = %s" % (t, same[0]) if same
                                     else "%s matches no .tex under .build/ or outputs/ at the base" % t)
    return ("FAIL", "; ".join(bad)) if bad else ("PASS", "; ".join(ok))


def check_provenance(copy, saved):
    folders = sorted({"/".join(p.split("/")[:3]) for p in saved if p.startswith("outputs/applications/") and p.count("/") >= 3})
    files = [p for p in saved if PROVENANCE_FILE.match(p)]
    if not folders and not files:
        return "SKIP", "no output with a provenance table saved"
    bad = ["%s has no provenance.md" % d for d in folders if not os.path.isfile(os.path.join(copy, d, "provenance.md"))]
    count, empty = 0, []
    for p in files:
        try:
            rows = provenance_rows(read(os.path.join(copy, p)))
        except UnicodeDecodeError:
            bad.append("%s is not UTF-8" % p)
            continue
        if not rows:
            empty.append(p)
        for n, cells, head in rows:
            count += 1
            why = row_problem(copy, p, cells, head)
            if why:
                bad.append("%s:%d %s: %s" % (p, n, why, " | ".join(cells)[:200]))
    if bad:
        return "FAIL", "; ".join(bad)
    found = "%d row(s) in %s cite no other output" % (count, ", ".join(files))
    if empty:
        return "NOTE", found + "; no table with an entry or source column in " + ", ".join(empty)
    return "PASS", found


def show_line(line):
    return "[%s] %r" % (line[0] or "no angle", line[1][:120])


def check_phrasings(copy, base, saved):
    entries = [p for p in saved if ENTRY_PATH.fullmatch(p)]
    subjects = git(copy, "log", "--format=%s", "%s..HEAD" % base).splitlines()
    if not any(t.startswith("write(") for t in subjects):
        return "SKIP", "no write save in %s..HEAD (another mode's Past phrasings changes are graded by hand)" % base
    none_added = "the write save added no Past phrasings line: check the approved resume or bullets report has no new bullet"
    marked = lambda rev, p: report_marks(show(copy, rev, p))[1]   # a report's Archived line at rev
    reports = [p for p in saved if re.fullmatch(r"outputs/reports/[^/]+\.md", p)]
    archived = sorted({"applications/" + p.split("/")[2] for p in saved
                       if re.fullmatch(r"outputs/applications/[^/]+/archived\.md", p)}
                      | {p[len("outputs/"):] for p in reports if marked("HEAD", p) and not marked(base, p)})
    writes = git(copy, "log", "--format=%H %s", "%s..HEAD" % base).splitlines()
    only_archived = archived and all(
        any(re.fullmatch(r"outputs/applications/[^/]+/archived\.md", f)
            for f in git(copy, "show", "--name-only", "--diff-filter=A", "--format=", w.split()[0]).splitlines())
        or any(re.fullmatch(r"outputs/reports/[^/]+\.md", f) and marked(w.split()[0], f)
               and not marked(w.split()[0] + "^", f)
               for f in git(copy, "show", "--name-only", "--format=", w.split()[0]).splitlines())
        for w in writes if w.split(" ", 1)[1].startswith("write("))
    level = "Archived save or demote (archived.md or the Archived line added in %s)" % ", ".join(archived) if archived else ""
    if not entries:
        return ("PASS", level + ": no Past phrasings line changed") if only_archived else ("NOTE", none_added)
    bad, ok, drops, demoted = [], [], [], []
    for p in entries:
        old = Counter(phrasings(show(copy, base, p)))
        try:
            new = Counter(phrasings(read(os.path.join(copy, p))) if os.path.isfile(os.path.join(copy, p)) else [])
        except UnicodeDecodeError:
            bad.append("%s is not UTF-8" % p)
            continue
        removed, added = list((old - new).elements()), list((new - old).elements())
        kept = list((old & new).elements())
        cites = lambda line: any(re.search(r"%s(?![\w-])" % re.escape(f), line[1]) for f in archived)
        demoted += ["%s: demoted %s" % (p, show_line(r)) for r in removed if cites(r)]
        removed = [r for r in removed if not cites(r)]
        bad += ["%s: added %s, citing an Archived folder" % (p, show_line(a)) for a in added if cites(a)]
        for r in removed:
            twin = max(added, key=lambda a: similar(r, a), default=None)
            if twin and similar(r, twin) >= SIMILAR:
                bad.append("%s: rewritten %s -> %r" % (p, show_line(r), twin[1][:120]))
        if len(removed) > len(added):
            bad.append("%s: %d line(s) removed, %d added (a drop happens only beside an addition): %s"
                       % (p, len(removed), len(added), "; ".join(show_line(r) for r in removed)))
        for n, a in enumerate(added):
            twin = max(kept + added[:n], key=lambda k: similar(a, k), default=None)
            if twin and similar(a, twin) >= SIMILAR:
                bad.append("%s: word-only addition %s (%.2f like %r)" % (p, show_line(a), similar(a, twin), twin[1][:120]))
        if added or removed:
            ok.append("%s: +%d -%d" % (p, len(added), len(removed)))
        drops += ["%s: removed %s" % (p, show_line(r)) for r in removed]
    ok += demoted
    if bad:
        return "FAIL", "; ".join(ok + bad)
    if not any(re.search(r": \+[1-9]", o) for o in ok):
        if only_archived and not drops:
            return "PASS", "; ".join([level] + ok)
        return "NOTE", "; ".join(ok + drops + [none_added])
    if drops:
        return "NOTE", "; ".join(ok + drops) + " (check each removed line is the cap's drop)"
    return "PASS", "; ".join(ok) if ok else "no Past phrasings line changed"


SUBJECT_FILES = ("skills/career-log/SKILL.md", "tools/sync.py")   # and every file in skills/career-log/modes/
# a subject in a commit command: sync.py's commit or settle commit (--subject), or git commit -m
SUBJECT_CMD = re.compile(r'(?:sync\.py(?:\s+--[\w-]+)*\s+(?:settle\s+)?commit(?:\s+--[\w-]+)*\s+(?:--subject\s+)?'
                         r'|\bgit\b[^`\n]*?\scommit\s+(?:-\S+\s+)*?-m\s+)"([^"`\n]+)"')
# a subject-shaped code span: `name(...): text` on a line that says commit, or `name: text` after
# "commit" or "subject" with no other code span between
SUBJECT_SPAN = re.compile(r"`([a-z][a-z-]*\([^`()]*\): [^`]+)`")
SUBJECT_AFTER = re.compile(r"(?:\bcommit|\bsubject)[^`\n]*`([a-z][a-z-]*: [^`]+)`", re.I)
SUBJECT_AS = re.compile(r"(?:\bas|\bsubject)\s+`([a-z][a-z-]*: [^`]+)`")   # "commit it as `...`", "with the subject `...`"
TOOL_LINES = ("commit:", "committed:")   # sync.py's own output lines, not subjects
SUBJECT_PART = re.compile(r"(<[^<>]+>|\.\.\.|\u2026|(?<=[a-z])\((?:s|es|y/ies)\))")
SLUGGED = re.compile(r"^(log|consolidate)\(([^)]*)\)")


def subject_templates(texts):
    """{template: regex} for the commit subjects these texts give: each `<...>` and `...` matches any
    text, `(s)` and `(y/ies)` the forms they spell. A template that starts with a placeholder (`<the
    mode's message>`, `<the subject of its commit: line>`) is a tool's line, not a format: skipped."""
    out = {}
    for text in texts:
        found = SUBJECT_CMD.findall(text) + SUBJECT_AS.findall(text)
        for line in text.splitlines():
            if "commit" in line.lower():
                found += SUBJECT_SPAN.findall(line)
            found += SUBJECT_AFTER.findall(line)
        for tmpl in found:
            if not re.match(r"[a-z]", tmpl) or tmpl.startswith(TOOL_LINES):
                continue
            rx = ""
            for n, part in enumerate(SUBJECT_PART.split(tmpl)):
                if n % 2 == 0:
                    rx += re.escape(part)
                elif part.startswith("<") or part in ("...", "\u2026"):
                    rx += ".+" if part.startswith("<") else ".*"
                else:
                    forms = part[1:-1].split("/")
                    rx += "(?:%s)%s" % ("|".join(map(re.escape, forms)), "?" if len(forms) == 1 else "")
            out[tmpl] = re.compile(rx)
    return out


def check_subjects(evs, copy, base, templates):
    commits = [w.split(" ", 1) for w in git(copy, "log", "--no-merges", "--format=%H %s", "%s..HEAD" % base).splitlines()]
    if not commits:
        return "SKIP", "no commit in %s..HEAD" % base
    scripts = {e[3] for e in evs if re.search(r"\.py\b", command(e))}
    printed = {l[len("commit: "):].strip() for e in evs if e[0] == "result" and e[2] in scripts
               for l in e[1].splitlines() if l.startswith("commit: ")}
    bad, ok = [], []
    for sha, subject in reversed(commits):
        fits = [t for t, rx in templates.items() if rx.fullmatch(subject)]
        if not fits and subject not in printed:
            copied = " (a template's (s), (es) or (y/ies) copied as written: the mode asks for the singular or plural)" \
                if re.search(r"[A-Za-z]\((?:s|es|y/ies)\)", subject) else ""
            bad.append("%s %r fits no subject a mode gives, and no tool printed it as a commit: line%s" % (sha[:7], subject, copied))
            continue
        why = "a tool's commit: line" if subject in printed and not fits else "`%s`" % fits[0]
        m = SLUGGED.match(subject)
        if m:
            slugs = [x.strip() for x in m.group(2).split(",") if x.strip()]
            if m.group(1) == "consolidate":
                changed = sorted({logfiles.entry_slug(f) for f in git(copy, "show", "--name-only", "--format=", sha).splitlines()
                                  if ENTRY_PATH.fullmatch(f)})
                if sorted(set(slugs)) != changed:
                    bad.append("%s %r names %s, the entries it changes are %s" % (sha[:7], subject, ", ".join(slugs) or "none",
                                                                                ", ".join(changed) or "none"))
                    continue
            else:
                known = {logfiles.entry_slug(f) for f in git(copy, "ls-tree", "-r", "--name-only", sha, "--", "entries").splitlines()
                         if ENTRY_PATH.fullmatch(f)}
                if slugs != [s for s in slugs if s in known] or len(slugs) != 1:
                    bad.append("%s %r names no one entry the Log has at that commit" % (sha[:7], subject))
                    continue
        ok.append("%s %r (%s)" % (sha[:7], subject, why))
    return ("FAIL", "; ".join(bad + ok)) if bad else ("PASS", "; ".join(ok))


# ---------- main ----------

def find_agent(agent_id):
    """(the transcript of the subagent with this id, None) or (None, why): `agent-<id>.jsonl` in a
    `subagents/` folder of any session in Claude Code's project folder for the working directory."""
    import chat_export   # its project folder rule, Claude Code's own
    agent_id = agent_id[len("agent-"):] if agent_id.startswith("agent-") else agent_id
    try:
        folder = chat_export.project_folder(chat_export.projects_dir(None), os.getcwd())
    except SystemExit as e:
        return None, str(e.code)
    hits = [os.path.join(folder, d, "subagents", "agent-%s.jsonl" % agent_id) for d in os.listdir(folder)]
    hits = sorted((p for p in hits if os.path.isfile(p)), key=os.path.getmtime)
    if not hits:
        return None, "no agent-%s.jsonl in %s/<session>/subagents/: run this in the session that started the run, or pass --transcript" % (agent_id, folder)
    return hits[-1], None


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--transcript", help="the run's transcript (.jsonl)")
    which.add_argument("--agent", help="the run's agent id (the Agent tool's result), to find its transcript")
    ap.add_argument("--copy", help="the run's scratch copy of the Log, after the run")
    ap.add_argument("--base", help="the run's base: the parent of its first commit (required with --copy)")
    ap.add_argument("--head", help="the head under test, when it is not --base")
    a = ap.parse_args(argv[1:])
    if a.copy and not a.base:
        ap.error("--copy needs --base")
    if a.copy:
        a.copy = os.path.abspath(a.copy)

    if a.agent:
        a.transcript, why = find_agent(a.agent)
        if not a.transcript:
            print(why)
            return 2
    if not os.path.isfile(a.transcript):
        print("%s: no such file" % a.transcript)
        return 2
    evs = events(a.transcript)
    if not any(e[0] in ("text", "tool", "model") for e in evs):
        print("%s holds no assistant message: is it the run's transcript?" % a.transcript)
        return 2
    try:
        if a.copy:
            for rev in [a.base] + ([a.head] if a.head else []):
                git(a.copy, "rev-parse", "--verify", "--quiet", rev + "^{commit}")
            if logfiles.git_run(a.copy, "merge-base", "--is-ancestor", a.base, "HEAD").returncode:
                print("%s is not an ancestor of the copy's HEAD: pass the parent of the run's first commit as --base"
                      % a.base)
                return 2
            revs = list(dict.fromkeys((a.head or a.base, "HEAD")))   # HEAD: the Engine an upgrade run installed
            review_md = [show(a.copy, rev, "skills/career-log/modes/review.md") for rev in revs]
            typed = [show(a.copy, rev, p) for rev in revs for p in TYPED_MODES]
            subject_texts = []
            for rev in revs:
                modes = git(a.copy, "ls-tree", "--name-only", rev, "skills/career-log/modes/").splitlines()
                subject_texts += [show(a.copy, rev, p) for p in list(SUBJECT_FILES) + modes if p.endswith((".md", ".py"))]
            diff = git(a.copy, "diff", "--name-only", "-z", "--no-renames",
                       "--diff-filter=AM", a.base, "HEAD")
        else:
            review_md = [read(os.path.join(HERE, "..", "skills", "career-log", "modes", "review.md"))]
            typed = [read(os.path.join(HERE, "..", *p.split("/"))) for p in TYPED_MODES]
    except (logfiles.LogError, OSError, UnicodeDecodeError) as e:
        print(e)
        return 2
    try:
        results = grade_all(a, evs, review_md, typed, subject_texts if a.copy else [], diff if a.copy else "")
    except logfiles.LogError as e:
        print(e)
        return 2
    print("transcript: %s" % a.transcript)
    for name, (grade, evidence) in results:
        print("%s %s: %s" % (grade, name, evidence))
    grades = {g for _, (g, _) in results}
    overall = ("FAIL" if "FAIL" in grades else "PASS with notes" if "NOTE" in grades
               else "PASS" if "PASS" in grades else "none (every check skipped)")
    print("Grade: %s (mechanical checks only; judgement checks are graded by hand)" % overall)
    return 1 if overall == "FAIL" else 0


def grade_all(a, evs, review_md, typed, subject_texts, diff):
    """[(check, (grade, evidence))] in the order --help gives; LogError when git fails."""
    calls = subagent_calls(evs)
    results = [("subagent-model", check_models(calls, evs, mode_prompts(typed))),
               ("call-lines", check_call_lines(evs, calls)),
               ("reviewer-prompt", check_reviewer_prompt(calls, review_md, a.copy)),
               ("humanizer-after-review", check_humanizer_after_review(calls)),
               ("map-count", check_map_count(evs))]
    save = ("git-status", "commit-subject", "resume-identical", "provenance", "printed-lines", "past-phrasings")
    if a.copy:
        saved = [p for p in diff.split("\0") if p]
        results += [("outside-root", check_outside(evs, a.copy)),
                    ("save-branch", check_branch(a.copy)),
                    ("git-status", check_status(a.copy)),
                    ("commit-subject", check_subjects(evs, a.copy, a.base, subject_templates(subject_texts)))]
        if saved:
            results += [("resume-identical", check_resume(a.copy, saved, a.base)),
                        ("provenance", check_provenance(a.copy, saved)),
                        ("printed-lines", check_printed_lines(evs, calls, a.copy, a.base, saved)),
                        ("past-phrasings", check_phrasings(a.copy, a.base, saved))]
        else:
            why = "no file added or changed between %s and HEAD: check --base, and where the save landed" % a.base
            results += [(name, ("SKIP", why)) for name in save[2:]]
    else:
        results += [(name, ("SKIP", "no --copy given")) for name in ("outside-root", "save-branch") + save]
    return results


if __name__ == "__main__":
    sys.exit(main(sys.argv))
