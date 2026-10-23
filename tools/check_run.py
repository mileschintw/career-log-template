#!/usr/bin/env python3
"""Grade the mechanical checks of one clean-agent test run (docs/maintaining-tests.md in the
Template's source repo; the checks apply to any run of the skill, past-phrasings to a write save).

  python3 -I tools/check_run.py --transcript <run.jsonl> [--copy <t>/log --base <sha>]

<run.jsonl> is the run's own transcript (Claude Code: `<session>/subagents/agent-<id>.jsonl`). The
subagents it started are read from its Agent tool calls, so their own transcripts are not needed.
<t>/log is the run's scratch copy after the run. <sha> is the run's base: the parent of the run's
first commit (the head under test when the run committed on its branch), an ancestor of the copy's
HEAD. The save checks read the files added or changed between <sha> and HEAD (a file the save
deleted is not read). Without --copy, or when nothing changed since <sha>, they print SKIP.
--head <rev> names the head under test when it is not <sha>; review.md and the TYPED_MODES files
are read as they are there (without --copy, as they are next to this script).

Prints one line per check, `<PASS|NOTE|FAIL|SKIP> <check>: <evidence>`, then a `Grade:` line.
Exit 1 when a check fails. Exit 2, with one line saying why, when the transcript is missing or
holds no assistant message (often your own session's file instead of the run's), when <sha> is not
a commit or not an ancestor of HEAD, or when git fails. Standard library only, Python 3.11+.

Transcript checks:
- subagent-model: every subagent call names its model. Reviewer or humanizer without one: FAIL.
  Any other subagent (the company lookup) without one, a subagent on another model family than the
  run's own, or a subagent type other than Explore or Plan (the read-only types): NOTE. The type
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
  path: NOTE. Pass --copy exactly as the run's prompt spelled the Log root to avoid a false NOTE.
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
  postings. The last line for each posting must say `no row: none` and have m >= n, and the first
  must come in the message that shows the map (its `Course work:` line), above the map's table,
  or in an earlier message. `none` may take a full stop or a note in parentheses, nothing else.
  Otherwise FAIL, as is a map shown with no count line, or a `Map:` label line that does not parse
  and no line that does. Lines only inside a shell tool call (an `echo`) are graded the same, and
  give NOTE where they would pass; other tool inputs (a written file, a subagent prompt) are not
  read. No count line and no map shown: SKIP (grade by hand a run that built a map
  without showing it: interview, or a several-postings run that printed no line). m is the run's
  own count: compare it with the rows of the map shown by hand.
map-count takes bold, italic and code marks out of a text before reading it.

Save checks, on the changes between <sha> and the copy's HEAD:
- git-status: `git status --porcelain` prints nothing. Otherwise FAIL.
- resume-identical: every saved resume `.tex` under outputs/ is byte-identical to a `.tex` under
  the copy's .build/ (the drafts), or to a `.tex` under outputs/ at <sha> (an approved version saved
  unchanged). Otherwise FAIL.
- provenance: every application folder saved has a provenance.md, and every row of a provenance
  table in a saved provenance file (an application's provenance.md, outputs/resumes/*.md,
  outputs/reports/*.md) passes write step 10's rule, the one tools/check_save.py prints (its --help
  gives it): no entry section naming a file other than an entry, profile.md or direction.md, and no
  column after the first citing another output. Otherwise FAIL. A provenance file with no
  provenance table: NOTE.
- printed-lines, only when a commit in <sha>..HEAD is a write save (SKIP otherwise): write step
  10's **Run the save check** lines, in the output of a tools/check_save.py run before the save's
  commit. The save's commit is the shell (Bash, PowerShell) `git ... commit` call that made the
  first write commit touching a provenance file: its result names that commit's short sha, or else
  its command holds that commit's subject before a closing quote (a run may commit facts with
  `write(` earlier); else the first
  such call with `write(` in its command whose result is not a failure (an error starting `Exit
  code` with no `] write(` commit line in it), or else the last `git ... commit` call; with none,
  the whole transcript. A check run is a shell call whose command runs check_save.py with python3, python
  or py, before that commit, or in the commit's own command ahead of `git ... commit`
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
  review: none`. Anything else, a missing line, or a check run only after the commit: FAIL.
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
  counts. A write save that adds no line: NOTE. Two lines differ only in
  words when their word sequences, lowercased with the trailing (citation) stripped, have a difflib
  ratio of at least SIMILAR (0.85); two added lines are compared with each other too. Whether a
  claim reached the cap for its angle, and whether two wordings differ in meaning, stay with the
  judgement grader. Save levels (write › Save levels): a folder whose `archived.md` the range adds
  was saved Archived or demoted. A removed line citing that folder is the demote's and is set
  aside; an added line citing it: FAIL. When every write commit in the range adds an `archived.md`,
  adding no line is a PASS, not a NOTE. An Archived target run has no marker, so it grades NOTE here
  and is passed by hand.
"""
import argparse, difflib, json, os, re, subprocess, sys
from collections import Counter

SIMILAR = 0.85
READ_ONLY = ("Explore", "Plan")
TYPED_MODES = ("skills/career-log/modes/scan.md",)   # modes that name the type of each subagent they prompt
PLACEHOLDER = r'(?:(?!/skills/career-log/|\. )[^"])+?'   # a <...> in their prompts: no second pointer, sentence or quote
FAMILIES = ("haiku", "sonnet", "opus", "fable")
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from entries import ENTRY_PATH   # what an entry's path is
from check_save import PROVENANCE_FILE, provenance_rows, row_problem   # write step 10's provenance rule


# ---------- transcript ----------

def events(path):
    """The run's blocks in order: ("text", text), ("tool", name, input, id) and, once per message,
    ("model", model id) from its assistant messages; ("result", text, tool id, failed) from the tool
    results in its user messages, failed when the result is an error that starts `Exit code`."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            if not isinstance(msg.get("content"), list):
                continue
            if msg.get("role") == "user":
                for b in msg["content"]:
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


def check_models(calls, evs=(), typed=()):
    fails, notes, seen = [], [], []
    runs = {family(e[1]) for e in evs if e[0] == "model" and not e[1].startswith("<")}
    for _, kind, inp in calls:
        model = inp.get("model")
        seen.append("%s %s model=%s" % (kind, label(inp), model or "none"))
        if not model:
            (fails if kind in ("reviewer", "humanizer") else notes).append("%s %s has no model" % (kind, label(inp)))
        elif len(runs) == 1 and family(model) not in runs:
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
            if e[0] in ("model", "result") or (e[0] == "tool" and e[1] in ("Agent", "Task")):
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


def check_reviewer_prompt(calls, review_md, copy=None):
    revs = [inp for _, kind, inp in calls if kind == "reviewer"]
    if not revs:
        return "SKIP", "no reviewer call"
    tmpl, rx = pointer_line(review_md)
    if not rx:
        return "FAIL", "no `Read <root>/...` pointer line in modes/review.md"
    bad, notes, ok = [], [], []
    for inp in revs:
        first = (inp.get("prompt") or "").split("\n", 1)[0].rstrip().replace("\\", "/")
        m = rx.match(first)
        root = m.group("root") if m else (re.search(r"Read (.+?)/skills/career-log/modes/review\.md", first) or [None, None])[1]
        if not m:
            bad.append("%s first line %r does not match %r" % (label(inp), first, tmpl))
        if root and copy and norm(root) not in (norm(copy), norm(os.path.realpath(copy))):
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
        if e[0] in ("model", "result") or (e[0] == "tool" and e[1] not in SHELLS):
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
COURSE_WORK = re.compile(r"^[\s>|-]*Course work:", re.M)


def check_map_count(evs):
    lines, in_call, unparsed = printed(evs, MAP_LABEL, MAP_RE)
    shown = next(((i, m.start(), t) for i, e in enumerate(evs) if e[0] == "text"
                  for t in [EMPHASIS.sub("", e[1])] for m in [COURSE_WORK.search(t)] if m), None)
    notes = []
    if not lines and in_call:
        lines = in_call
        notes.append("Map line %r written only in a tool call" % in_call[-1][1].group(0).strip()[:120])
    if not lines:
        if unparsed:
            return "FAIL", "Map line %r does not parse" % unparsed[-1][1][:120]
        if shown:
            return "FAIL", "a map was shown (a Course work: line) with no Map: count line before it"
        return "SKIP", "no Map: line and no map shown (grade by hand if the run built a map)"
    last = {}
    for _, m in lines:
        last[(m.group(1) or "").strip()] = m
    bad, ok = [], []
    for m in last.values():
        n, rows = int(m.group(2)), int(m.group(3))
        line = m.group(0).strip()[:160]
        if not says_none(m.group(4)):
            bad.append("last Map line names requirements with no row: %r" % line)
        elif rows < n:
            bad.append("last Map line has fewer rows than requirements and duties, and names none missing: %r" % line)
        else:
            ok.append("%r" % line)
    if shown and lines[0][0][0] > shown[0]:
        bad.append("the first Map line comes in a later message than the map shown (its Course work: line)")
    elif shown and lines[0][0][0] == shown[0]:
        table = re.compile(r"^\s*\|", re.M).search(shown[2], shown[1])
        if table and lines[0][0][1] > table.start():
            bad.append("the first Map line comes after the map's table")
    if bad:
        return "FAIL", "; ".join(bad + notes + ok)
    return ("NOTE", "; ".join(notes + ok)) if notes else ("PASS", "; ".join(ok))


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
COMMIT = re.compile(r"\bgit\b(?:\s+(?:-[Cc]\s+(?:\"[^\"]*\"|'[^']*'|\S+)|--\S+))*\s+commit\b")
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
    files = {w: git(copy, "-c", "core.quotePath=off", "show", "--name-only", "--format=", w).splitlines() for w in writes}
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
    if any(k == "reviewer" for _, k, _ in calls):
        if not hum:
            bad.append("no Humanizer after review line in tools/check_save.py's output %s" % where)
        for _, m in hum:
            (ok if hum_ok(m) else bad).append(
                ("%r" if hum_ok(m) else "Humanizer after review line has no Humanizer call line for its changed text: %r")
                % m.group(0).strip()[:160])
    if bad:
        return "FAIL", "; ".join(bad + why + ["tool line not in the form step 10 gives: %r" % u[:120] for u in unparsed[-2:]] + ok)
    return "PASS", "; ".join(ok)


# ---------- scratch copy ----------

class GitError(Exception):
    pass


def git(copy, *args):
    p = subprocess.run(["git", "-C", copy, *args], capture_output=True)
    if p.returncode:
        raise GitError("git %s failed: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout.decode("utf-8", "replace")


def show(copy, rev, path):
    p = subprocess.run(["git", "-C", copy, "show", "%s:%s" % (rev, path)], capture_output=True)
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_status(copy):
    out = git(copy, "status", "--porcelain")
    return ("FAIL", "uncommitted: " + "; ".join(out.splitlines()[:10])) if out.strip() else ("PASS", "git status is clean")


def blob(copy, rev, path):
    p = subprocess.run(["git", "-C", copy, "show", "%s:%s" % (rev, path)], capture_output=True)
    return p.stdout if p.returncode == 0 else None


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
    for p in git(copy, "-c", "core.quotePath=off", "ls-tree", "-r", "-z", "--name-only", base, "--", "outputs").split("\0"):
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
        rows = provenance_rows(read(os.path.join(copy, p)))
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


LABEL = re.compile(r"\*\*([^*]+?):?\*\*:?")
ANGLE = re.compile(r"\*\*([a-z0-9][a-z0-9-]*):?\*\*:?\s*(?=[\"“「『])", re.I)


def phrasings(text):
    """(angle, wording) for each line under ## Past phrasings, the angle as the module docstring's
    past-phrasings rule gives it: the line's own prefix first, then the label line in force."""
    m = re.search(r"^## Past phrasings[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    out, angle = [], None
    for line in (m.group(1).splitlines() if m else []):
        s = line.strip()
        head = re.fullmatch(r"(?:-\s*)?" + LABEL.pattern, s) or re.fullmatch(r"###\s+(.+?):?", s)
        if head:
            angle = head.group(1).strip().lower()
        elif s.startswith("- ") and not re.match(r"(none yet|GAP:)", s[2:].strip(), re.I):
            body, own = s[2:].strip(), None
            inline = ANGLE.match(body)
            if inline:
                own, body = inline.group(1).strip().lower(), body[inline.end():].strip()
            out.append((own or angle, body))
    return out


def words(body):
    return re.findall(r"[\w.%+-]+", re.sub(r"\s*\([^()]*\)\s*$", "", body).lower())


def similar(a, b):
    if a[0] and b[0] and a[0] != b[0]:
        return 0.0
    return difflib.SequenceMatcher(None, words(a[1]), words(b[1]), autojunk=False).ratio()


def show_line(line):
    return "[%s] %r" % (line[0] or "no angle", line[1][:120])


def check_phrasings(copy, base, saved):
    entries = [p for p in saved if ENTRY_PATH.fullmatch(p)]
    subjects = git(copy, "log", "--format=%s", "%s..HEAD" % base).splitlines()
    if not any(t.startswith("write(") for t in subjects):
        return "SKIP", "no write save in %s..HEAD (another mode's Past phrasings changes are graded by hand)" % base
    none_added = "the write save added no Past phrasings line: check the approved text has no new wording"
    archived = sorted({p.split("/")[2] for p in saved if re.fullmatch(r"outputs/applications/[^/]+/archived\.md", p)})
    writes = git(copy, "log", "--format=%H %s", "%s..HEAD" % base).splitlines()
    only_archived = archived and all(
        any(re.fullmatch(r"outputs/applications/[^/]+/archived\.md", f)
            for f in git(copy, "show", "--name-only", "--diff-filter=A", "--format=", w.split()[0]).splitlines())
        for w in writes if w.split(" ", 1)[1].startswith("write("))
    level = "Archived save or demote (archived.md added in %s)" % ", ".join(archived) if archived else ""
    if not entries:
        return ("PASS", level + ": no Past phrasings line changed") if only_archived else ("NOTE", none_added)
    bad, ok, drops, demoted = [], [], [], []
    for p in entries:
        old = Counter(phrasings(show(copy, base, p)))
        new = Counter(phrasings(read(os.path.join(copy, p))) if os.path.isfile(os.path.join(copy, p)) else [])
        removed, added = list((old - new).elements()), list((new - old).elements())
        kept = list((old & new).elements())
        cites = lambda line: any(re.search(r"applications/%s(?![\w-])" % re.escape(f), line[1]) for f in archived)
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


# ---------- main ----------

def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcript", required=True, help="the run's transcript (.jsonl)")
    ap.add_argument("--copy", help="the run's scratch copy of the Log, after the run")
    ap.add_argument("--base", help="the run's base: the parent of its first commit (required with --copy)")
    ap.add_argument("--head", help="the head under test, when it is not --base")
    a = ap.parse_args(argv[1:])
    if a.copy and not a.base:
        ap.error("--copy needs --base")

    if not os.path.isfile(a.transcript):
        print("%s: no such file" % a.transcript)
        return 2
    evs = events(a.transcript)
    if not evs:
        print("%s holds no assistant message: is it the run's transcript?" % a.transcript)
        return 2
    try:
        if a.copy:
            for rev in [a.base] + ([a.head] if a.head else []):
                git(a.copy, "rev-parse", "--verify", "--quiet", rev + "^{commit}")
            if subprocess.run(["git", "-C", a.copy, "merge-base", "--is-ancestor", a.base, "HEAD"],
                              capture_output=True).returncode:
                print("%s is not an ancestor of the copy's HEAD: pass the parent of the run's first commit as --base"
                      % a.base)
                return 2
            review_md = show(a.copy, a.head or a.base, "skills/career-log/modes/review.md")
            typed = [show(a.copy, a.head or a.base, p) for p in TYPED_MODES]
            diff = git(a.copy, "-c", "core.quotePath=off", "diff", "--name-only", "-z", "--no-renames",
                       "--diff-filter=AM", a.base, "HEAD")
        else:
            review_md = read(os.path.join(HERE, "..", "skills", "career-log", "modes", "review.md"))
            typed = [read(os.path.join(HERE, "..", *p.split("/"))) for p in TYPED_MODES]
    except (GitError, OSError) as e:
        print(e)
        return 2
    calls = subagent_calls(evs)
    results = [("subagent-model", check_models(calls, evs, mode_prompts(typed))),
               ("call-lines", check_call_lines(evs, calls)),
               ("reviewer-prompt", check_reviewer_prompt(calls, review_md, a.copy)),
               ("humanizer-after-review", check_humanizer_after_review(calls)),
               ("map-count", check_map_count(evs))]
    save = ("git-status", "resume-identical", "provenance", "printed-lines", "past-phrasings")
    if a.copy:
        saved = [p for p in diff.split("\0") if p]
        results.append(("git-status", check_status(a.copy)))
        if saved:
            results += [("resume-identical", check_resume(a.copy, saved, a.base)),
                        ("provenance", check_provenance(a.copy, saved)),
                        ("printed-lines", check_printed_lines(evs, calls, a.copy, a.base, saved)),
                        ("past-phrasings", check_phrasings(a.copy, a.base, saved))]
        else:
            why = "no file added or changed between %s and HEAD: check --base, and where the save landed" % a.base
            results += [(name, ("SKIP", why)) for name in save[1:]]
    else:
        results += [(name, ("SKIP", "no --copy given")) for name in save]

    for name, (grade, evidence) in results:
        print("%s %s: %s" % (grade, name, evidence))
    grades = {g for _, (g, _) in results}
    overall = ("FAIL" if "FAIL" in grades else "PASS with notes" if "NOTE" in grades
               else "PASS" if "PASS" in grades else "none (every check skipped)")
    print("Grade: %s (mechanical checks only; judgement checks are graded by hand)" % overall)
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
