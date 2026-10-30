#!/usr/bin/env python3
"""Print write step 10's checks on a saved output, before its commit (skills/career-log/modes/write.md),
and rank step 6's on a ranking (skills/career-log/modes/rank.md), then commit it on --commit; or
audit point 6's on every output (skills/career-log/modes/audit.md).

  python3 -I tools/check_save.py <saved>... [--humanizer <file> | --humanizer none] [--root <root>]
  python3 -I tools/check_save.py <saved> [--humanizer ...] --commit "<subject>" [--checked] [--root <root>]
  python3 -I tools/check_save.py --audit [--root <root>]

<root> is the Log's root (default: the folder above this script's). <saved> is a path in it, read
from <root> when relative: an application folder (outputs/applications/<folder>/, whose
provenance.md holds the provenance table), a target-run resume's outputs/resumes/<target>.md, a
report, outputs/reports/<YYYY-MM-DD>-<slug>.md, or a ranking, outputs/reports/<YYYY-MM-DD>-<event>-ranking.md.

Each line it prints is a check; a line that fails is followed by an indented `fix:` line saying what
to do. In order:
- Files (<saved>): what the output must hold, or `ok`:
  - an application folder: posting.md (with the posting's URL), resume.tex, resume.pdf and
    provenance.md; each heading of answers.md, when there is one, followed by a `Type: <question
    type>` line (only that the line is there: whether it names a stories.md row is not read); an
    archived.md, when there is one, of the one line `Archived (user, YYYY-MM-DD)`;
  - a target-run resume: <target>.tex and <target>.pdf beside <target>.md;
  - a resume (either): its .tex the same text as the draft's, .build/drafts/<name>/resume.tex
    (<name> the folder's name, or the target), and its .pdf the same file as the draft's resume.pdf,
    or the same words (read with pdftotext, as tools/resume.py --same-text reads them); with no
    draft, or no pdftotext for two PDFs whose bytes differ, a `note:` line says what was not
    compared, and it does not fail; and its .pdf's text layer with no `GAP:` for the email (the
    line tools/resume.py fails as `email: GAP (needs you)`), when pdftotext reads it;
  - a report: its file name `<YYYY-MM-DD>-<slug>.md`, a valid date; a `Kind: <kind>` line above its
    first table, <kind> one of KINDS (write step 1's kinds of output, or `other`); with `Kind:
    application answer`, each heading above the first table followed by a `Type:` line; a line there
    starting `Archived` in the form `Archived (user, YYYY-MM-DD)`, a real date (the marker of a
    `resume bullets` report saved Archived, write › Save levels; whether the save was Archived is
    the run's, and not read);
  - a ranking (named `-ranking.md`, with no `Kind:` line): applications.md's `## Events and contacts` table is one table (a row below a blank
    line, or any other line, is outside it and fails), each row with as many cells as its header,
    and a row there names the ranking's file name. A ranking has no Kind: line, provenance table,
    Lint at save or Humanizer after review line.
- Risks (<saved>): a resume's provenance file (an application's provenance.md, a target's .md),
  and a `resume bullets` report, has a `## Risks to handle in conversation` section after its
  provenance table.
- Provenance check (<file>): <n> rows; citing another output: <none, or each listed row>
  for each provenance file, <file> its path from the Log root and <n> its table's row count. A
  provenance table is one with an "entry" or "source" column; tables under `## Company context` and
  `## Risks...` are not read (tools/logfiles.py provenance_rows). A row is listed when:
  - its entry section (the first column whose header says "entry") names a `.md` file other than an
    entry, profile.md or direction.md (`stories.md`, `outputs/x.md`), source citations set aside; a
    path is read from the Log root, from entries/, or from the provenance file's folder (a link such
    as `../../entries/x.md`); a bare entry name with no `.md` (`2026-01-queue › What happened`) is
    read only when entries/<name>.md exists;
  - the section after a file's ` › ` (or a Markdown link's) is no heading in that file, compared
    without case and punctuation: the rest of the cell up to a `;`, else up to a ` (` (a note), else
    up to a `,`; each further ` › ` part too;
  - a column after the first cites another output: `outputs/`, `applications/`, `resumes/` or
    `reports/` outside a source citation (a `sources/` citation up to the next `;` or output path, a
    `<repo>@<sha>:<path>` key, or a URL; a URL into outputs/ still counts), `resume.tex`, or the word
    "provenance". The sponsorship records, `outputs/reports/sponsorship.jsonl`, are a source, not an
    output (a `none found` record cites them).
  A provenance file that is missing, not UTF-8, or has no provenance table prints a line saying so
  instead.
- Past phrasings (<entry>): +<added> -<removed>, then `ok` or each finding, for each entry whose
  `## Past phrasings` this save changed since git's HEAD (the save is not committed yet; which
  entries are this save's: --commit below), as write step 10's
  **Feed later runs** and write › Save levels say. It fails:
  - an added line not in the form entries/_template.md › Past phrasings gives (`- **<angle>:**
    "<wording>" (<citation>)`);
  - an added line whose wording is not, word for word, a bullet of a resume or `resume bullets`
    report among <saved> (LaTeX markup and case aside; an `\\item` under an Education or Skills
    heading is no bullet, as for application.py phrasings);
  - an added line whose citation is not the form for that output: `outputs/applications/<folder>`,
    `outputs/resumes/<target>.tex, YYYY-MM-DD`, or `outputs/reports/<YYYY-MM-DD>-<slug>.md`;
  - an added line citing an Archived output (a folder with archived.md, a report with the Archived
    line): an Archived save adds no line;
  - a removed line with an added one that differs from it only in words (a rewrite), and more lines
    removed than added (a drop happens only beside an addition, at the three-wording cap); a
    removed line citing an Archived output is the demote's (write › Save levels › To Archived) and is
    set aside.
  It lists, without failing, as `check:` lines: an added line that differs only in words from a line
  already there for its angle, or from another added line (SIMILAR, the ratio tools/entries.py
  uses), and each other removed line (check it is the cap's drop).
- Entries (<entry>): a line the save added to an entry outside `## Past phrasings` that names a path
  in outputs/ fails: the entries record nothing about where their material was used.
- Lint at save: tools/writing_lint.py's SKILL.md › Visibility lines (a link to anything a private or
  GAP entry links) and its --across lines (AI-tell check 9: one number in more than one artifact),
  run again on the saved text: the resume .tex, answers.md, or the report. Its `fix:` lines fail; its
  `check:` lines are calls to make. `Lint at save: ok` when it prints none.
- Humanizer after review: --humanizer, required for every employer-facing output: an application
  folder, a target-run resume, and a report of kind `resume bullets`, `cover letter` or
  `application answer`, or with a `Type:` line (a personal draft, such as a bio, had no review and
  needs none). `none` when the review's edits changed no text, else a UTF-8 file with one line per
  sentence or bullet the review's edits changed, `<the line as approved> -> <its Humanizer call:
  line, or: humanizer not available>` (`→` also read; the last arrow before the call line splits
  it). It prints one `Humanizer after review: <line> -> <call line>` line per line of the file, or
  `Humanizer after review: none`.

--audit reads every output instead (audit point 6), and prints a `finding:` line for: a folder in
outputs/applications/ with no provenance.md or a provenance.md with no provenance table (one an
`interview` recorded has a sent-version.md instead) or no resume.pdf (a finding only when the folder was sent: ask the user when nothing in the
log says), a report in outputs/reports/ with no provenance table (scan reports aside), anything at the
top of outputs/ besides applications/, resumes/, reports/, projects/ and dashboard/,
and each provenance row listed as above, in every application's, target's and report's provenance
file (scan reports aside). The last line is `check_save: ok` (exit 0, no finding), or `check_save:
<n> findings: report each` (exit 1).

For a save, the last line is `check_save: ok` (exit 0), or `check_save: fix the lines above, then run it
again` (exit 1). With --commit (one <saved>), it also checks the subject: an application folder's
`write(<company>): <role>`, whose company and role, as ASCII names (tools/logfiles.py ascii_slug),
are the folder's name after its date (the `commit:` line tools/application.py name printed); a target's `write(<target>): resume`; a report's `write(<slug>):
<kind>`, as its file name and Kind: line give them; a ranking's `rank(<event>): <n> employers`,
<event> as its file name has it. A subject that is none of these is a `Commit subject:` line that
fails. On `check_save: ok` it commits, printing `commit: <subject>`, then a `left: <path>: differs
from HEAD, not written by this save: not committed` line for each other path that differs from HEAD
(a bulk change waiting for its yes stays out), then tools/sync.py commit's lines, so it still ends
with `sync: ok` or a `next:` line; it exits with sync.py's code. It commits only the files this save wrote, told by what each
gained or lost since HEAD (new files included): <saved>, a target's .tex and .pdf with its .md; each
entry whose `## Past phrasings` gained or lost a line naming the output (its path from outputs/ on, or
a target's <target>.md, .tex or .pdf) or gained one holding its bullet; stories.md when a line it
gained names the output (answer-set's pointer); profile.md when its Interview prep list gained a
line; for an application folder each scan report whose gained lines name it (a scan accept's status
line), and then outputs/dashboard/; for a ranking applications.md when a line it gained names it.
A changed entry that is not this save's gets no Past phrasings check: when its section changed, a
`Past phrasings (<entry>): not this save's (...): not checked, not committed` line and a `check:`
line under it. An entry of this save's that also changed outside `## Past phrasings` gets a
`check:` line too: it is committed whole. While a `check:` line printed, it prints `held: not committed: ...` instead (exit 1):
act on each, then run it again with --checked. On exit 1 it commits nothing, so the same command,
run again after the fixes, is the commit. Exit 2, with one line saying why, for a <saved> path that is not a saved output in the Log,
a --humanizer file that cannot be read, or a git or writing.md read that fails: fix that path or
file, then run it again. Standard library only, Python 3.11+.
"""
import argparse, datetime, os, posixpath, re, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import logfiles
from entries import ENTRY_PATH, SCAN_REPORT, outputs   # what an entry's path is; the Log's outputs
from entries import PHRASING_PARTS, SIMILAR, phrasings, similar, words   # the Past phrasings parser
import writing_lint   # the Visibility and AI-tell check 9 lines, run again at save
import resume   # which pdftotext tools/resume.py uses

OUTPUT_REF = re.compile(r"\b(?:outputs|applications|resumes|reports)/|\bresume\.tex\b|\bprovenance\b", re.I)
SOURCE_PATH = re.compile(r"\bsources/(?:[^;|\s]|\s+(?![^;|\s]*\b(?:outputs|applications|resumes|reports)/))*|[\w.-]+@[0-9a-f]{6,}:\S+|https?://(?![^\s]*/outputs/)\S+")
SPONSORSHIP_RECORDS = re.compile(r"(?<![\w./-])outputs/reports/sponsorship\.jsonl(?![\w./-])")   # a source, not an output
MD_FILE = re.compile(r"[\w./\\-]*\w\.md\b", re.I)
SECTION_REF = re.compile(r"(?:\[[^\]]*\]\(([^)\s]+)\)|([\w./\\-]*\w))\s+›\s+([^;|]+)")
PROVENANCE_FILE = re.compile(r"outputs/applications/[^/]+/provenance\.md$|outputs/(?:resumes|reports)/[^/]+\.md$")
APPLICATION = re.compile(r"outputs/applications/[^/]+$")
TARGET = re.compile(r"outputs/resumes/([^/]+)\.md$")
REPORT = re.compile(r"outputs/reports/[^/]+\.md$")
REPORT_NAME = re.compile(r"outputs/reports/(\d{4}-\d{2}-\d{2})-[^/\s]+\.md$")
RANKING = re.compile(r"outputs/reports/\d{4}-\d{2}-\d{2}-([^/\s]+)-ranking\.md$")   # rank step 6's report
EVENTS = "Events and contacts"
CHECK_LINE = re.compile(r"(?:^|\s|: )check: ")
ARCHIVED = re.compile(r"Archived \(user, (\d{4}-\d{2}-\d{2})\)")
KINDS = ("resume bullets", "cover letter", "bio", "elevator pitch", "application answer", "interview answer", "other")
EMPLOYER_KINDS = ("resume bullets", "cover letter", "application answer")
APPLICATION_FILES = ("posting.md", "resume.tex", "resume.pdf")   # provenance.md: its Provenance check line
OUTPUTS_TOP = ("applications", "resumes", "reports", "projects", "dashboard")
RISKS = "## Risks to handle in conversation"
HUMANIZER_CALL = re.compile(r"[*_`]*Humanizer call[*_`]*:[*_`]*\s*model:?\s+\S|humanizer not available", re.I)
HUMANIZER_LINE = re.compile(r"(.*\S)\s*(?:→|->)\s*((?:%s).*)$" % HUMANIZER_CALL.pattern, re.I)


class Report:
    """What check() prints: each line, and each failing line's fix under it."""

    def __init__(self):
        self.lines, self.failed = [], False

    def ok(self, line):
        self.lines.append(line)

    def fail(self, line, fix):
        self.lines += [line, "  fix: " + fix]
        self.failed = True


class NotUTF8(UnicodeError):
    """A Log file that is not UTF-8, with its path."""


def read(root, rel):
    try:
        return logfiles.read_text(os.path.join(root, *rel.split("/")))
    except UnicodeDecodeError:
        raise NotUTF8(rel)


def exists(root, rel):
    return os.path.exists(os.path.join(root, *rel.split("/")))


# ---- Provenance ----

def entry_file(root, rel, name):
    """The path of a file named in an entry section of the provenance file rel, when it is an entry,
    profile.md or direction.md: read from the Log root, from entries/, or from rel's folder (a
    relative link); else None."""
    name = name.replace("\\", "/")
    for path in (name, "entries/" + name, posixpath.join(posixpath.dirname(rel), name)):
        path = posixpath.normpath(path)
        if path in ("profile.md", "direction.md"):
            return path
        if ENTRY_PATH.fullmatch(path) and exists(root, path):
            return path
    return None


def heading_names(root, path):
    """Each heading's text in a Log file, as section_name() reads it; None when it cannot be read."""
    try:
        text = read(root, path)
    except (OSError, UnicodeError):
        return None
    return {section_name(h) for h in re.findall(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", logfiles.strip_comments(text), re.M)}


def section_name(text):
    return logfiles.anchor(text.replace("*", "").replace("`", ""))


def missing_section(root, rel, cell):
    """`<file> › <section>` in an entry-section cell whose section is no heading in that file, or None."""
    for m in SECTION_REF.finditer(cell):
        shown = name = m.group(1) or m.group(2)
        if not name.lower().endswith(".md"):
            if not exists(root, "entries/%s.md" % name):
                continue
            name += ".md"
        path = entry_file(root, rel, name)
        names = heading_names(root, path) if path else None
        if names is None:
            continue
        # the whole rest of the cell, else up to ` (` (a note), else up to `,` (a list)
        rest = m.group(3).strip()
        tries = [rest, re.split(r"\s+\(", rest)[0], rest.split(",")[0]]
        gone = [[p.strip() for p in t.split(" › ") if section_name(p) not in names] for t in tries]
        if all(gone):
            return "%s › %s" % (shown, gone[1][0])
    return None


def row_problem(root, rel, cells, head):
    """Why a row of the provenance file rel cites something other than an entry section and its
    source, or None."""
    col = next((k for k, h in enumerate(head) if re.search(r"entry", h, re.I)), None)
    if col is not None and col < len(cells):
        cell = SOURCE_PATH.sub("", cells[col])
        other = [f for f in MD_FILE.findall(cell) if not entry_file(root, rel, f)]
        if other:
            return "entry section names %s" % other[0]
        gone = missing_section(root, rel, cell)
        if gone:
            return "entry section names %s, no heading there" % gone
    for c in cells[1:]:
        m = OUTPUT_REF.search(SPONSORSHIP_RECORDS.sub("", SOURCE_PATH.sub("", c)))
        if m:
            return "names another output (%s)" % m.group(0)
    return None


def check_file(root, rel):
    """(the Provenance check line, whether it passes) for one provenance file."""
    if not exists(root, rel):
        return "Provenance check (%s): missing: write the provenance table there" % rel, False
    try:
        rows = logfiles.provenance_rows(read(root, rel))
    except UnicodeError:
        return "Provenance check (%s): not UTF-8: save it as UTF-8" % rel, False
    if not rows:
        return ("Provenance check (%s): no provenance table (a table with an entry or source column)" % rel), False
    listed = []
    for n, cells, head in rows:
        why = row_problem(root, rel, cells, head)
        if why:
            listed.append("line %d, %s: %s" % (n, why, " | ".join(cells)[:200]))
    return ("Provenance check (%s): %d rows; citing another output: %s"
            % (rel, len(rows), "; ".join(listed) if listed else "none")), not listed


PROVENANCE_FIX = ("replace each listed row with rows citing the entry sections behind that claim (a section "
                  "of an entry, profile.md or direction.md, by a heading it has), each with its source; a "
                  "file with no table: write its provenance table")


# ---- The output's files ----

def above_table(text):
    """The lines above a text's first table row."""
    out = []
    for line in text.lstrip("﻿").splitlines():
        if line.strip().startswith("|"):
            break
        out.append(line)
    return out


def report_marks(text):
    """(kind or None, whether it holds the Archived line) from the lines above a report's first table."""
    lines = above_table(text)
    kind = next((m.group(1).strip().lower() for m in (re.match(r"\s*Kind:\s*(\S.*?)\s*$", l) for l in lines) if m), None)
    return kind, any(ARCHIVED.fullmatch(l.strip()) for l in lines)


def bad_marker(line):
    """Whether a line meant as the Archived marker is not `Archived (user, YYYY-MM-DD)` with a real date."""
    m = ARCHIVED.fullmatch(line.strip())
    try:
        return not m or not datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return True


def untyped_headings(lines):
    """Each question heading with no `Type:` line under it (the first line with text): the `## `
    headings and below, or the `# ` ones in a file with none; `## Company context` and `## Risks...`
    set aside."""
    heads = [(n, l) for n, l in enumerate(lines) if re.match(r"#{1,6}\s", l)]
    level = 2 if any(re.match(r"#{2,6}\s", l) for _, l in heads) else 1
    out = []
    for n, l in heads:
        if len(l) - len(l.lstrip("#")) < level or re.match(r"#+\s+(Company context|Risks)", l):
            continue
        nxt = next((x.strip() for x in lines[n + 1:] if x.strip() and not re.match(r"\s*Kind:", x)
                    and not ARCHIVED.fullmatch(x.strip())), "")
        if not re.match(r"Type:\s*\S", nxt):
            out.append(l.strip())
    return out


def pdf_words(pdf):
    """The words of a PDF's text layer, as tools/resume.py --same-text reads them; None with no
    pdftotext; [] when it cannot read the file."""
    exe = resume.poppler_bin("pdftotext")
    if not exe:
        return None
    resume.no_error_dialogs()
    run = subprocess.run([exe, "-enc", "UTF-8", pdf, "-"], capture_output=True, encoding="utf-8", errors="replace")
    return run.stdout.split() if run.returncode == 0 else []


def same_as_draft(root, rel, tex, pdf, name, out):
    """Check a saved resume's .tex and .pdf against the draft's, .build/drafts/<name>/resume.*."""
    draft = ".build/drafts/%s/" % name
    if not exists(root, draft + "resume.tex"):
        out.ok("Files (%s): note: no %sresume.tex, so %s and %s were not compared with a draft" % (rel, draft, tex, pdf))
        return
    with open(os.path.join(root, *(draft + "resume.tex").split("/")), "rb") as a, \
            open(os.path.join(root, *tex.split("/")), "rb") as b:
        if a.read().replace(b"\r\n", b"\n") != b.read().replace(b"\r\n", b"\n"):
            out.fail("Files (%s): %s differs from the approved draft %sresume.tex" % (rel, tex, draft),
                     "copy %sresume.tex over %s, and its built resume.pdf over %s" % (draft, tex, pdf))
            return
    if not exists(root, draft + "resume.pdf"):
        out.ok("Files (%s): note: no %sresume.pdf, so %s was not compared" % (rel, draft, pdf))
        return
    paths = [os.path.join(root, *p.split("/")) for p in (draft + "resume.pdf", pdf)]
    with open(paths[0], "rb") as a, open(paths[1], "rb") as b:
        if a.read() == b.read():
            return
    got = [pdf_words(p) for p in paths]
    if got[0] is None or got[1] is None:
        out.ok("Files (%s): note: %s and %sresume.pdf differ in bytes, and pdftotext (poppler) is not found to "
               "compare their words; not checked" % (rel, pdf, draft))
    elif not got[0] or got[0] != got[1]:
        out.fail("Files (%s): %s is not the PDF built from the approved draft (%sresume.pdf has other words)" % (rel, pdf, draft),
                 "build %sresume.tex with tools/resume.py, then copy its resume.pdf over %s" % (draft, pdf))


def email_gap(root, rel, pdf, out):
    """Fail a saved resume whose PDF still holds the email as a GAP; nothing when pdftotext cannot read it."""
    words = pdf_words(os.path.join(root, *pdf.split("/")))
    if words and (resume.email_fail([" ".join(words)]) or "").startswith("email: GAP"):
        out.fail("Files (%s): %s still has the email as a GAP" % (rel, pdf),
                 "ask the user for their email address, record it in profile.md, put it in the draft's header, "
                 "rebuild it with tools/resume.py and copy the .tex and .pdf over the saved ones")


def check_files(root, rel, out):
    """The Files lines for one <saved>; (the provenance file, whether it holds a resume or resume
    bullets, which carry the Risks section, whether --humanizer is required)."""
    before = len(out.lines)
    if APPLICATION.match(rel):
        missing = [f for f in APPLICATION_FILES if not exists(root, rel + "/" + f)]
        for f in missing:
            out.fail("Files (%s): no %s" % (rel, f), {
                "posting.md": "write the verbatim posting text and its URL to posting.md",
                "resume.tex": "copy the approved draft's resume.tex there",
                "resume.pdf": "copy the PDF built from the approved draft there"}[f])
        if "posting.md" not in missing and not re.search(r"https?://\S", read(root, rel + "/posting.md")):
            out.fail("Files (%s): posting.md has no URL" % rel, "add the posting's URL to posting.md")
        if exists(root, rel + "/answers.md"):
            for h in untyped_headings(read(root, rel + "/answers.md").splitlines()):
                out.fail("Files (%s): answers.md heading with no Type: line under it: %s" % (rel, h),
                         "write `Type: <question type>` under it, the type as its stories.md row's first column has it")
        if exists(root, rel + "/archived.md"):
            body = [l.strip() for l in read(root, rel + "/archived.md").splitlines() if l.strip()]
            if len(body) != 1 or bad_marker(body[0]):
                out.fail("Files (%s): archived.md is not the one line `Archived (user, YYYY-MM-DD)`" % rel,
                         "write that one line, with the date it was saved Archived")
        if not ({"resume.tex", "resume.pdf"} & set(missing)):
            same_as_draft(root, rel, rel + "/resume.tex", rel + "/resume.pdf", rel.split("/")[-1], out)
            email_gap(root, rel, rel + "/resume.pdf", out)
        found = rel + "/provenance.md", True, True
    elif TARGET.match(rel):
        target = TARGET.match(rel).group(1)
        tex, pdf = "outputs/resumes/%s.tex" % target, "outputs/resumes/%s.pdf" % target
        for f in (tex, pdf):
            if not exists(root, f):
                out.fail("Files (%s): no %s" % (rel, f), "copy the approved draft's resume.%s there as %s" % (f[-3:], f))
        if exists(root, tex) and exists(root, pdf):
            same_as_draft(root, rel, tex, pdf, target, out)
            email_gap(root, rel, pdf, out)
        found = rel, True, True
    elif is_ranking(root, rel):
        check_ranking(root, rel, out)
        found = None, False, False
    else:
        m = REPORT_NAME.match(rel)
        try:
            datetime.date.fromisoformat(m.group(1)) if m else None
        except ValueError:
            m = None
        if not m:
            out.fail("Files (%s): not named outputs/reports/<YYYY-MM-DD>-<slug>.md" % rel,
                     "rename it to today's date and a short lowercase slug")
        text = read(root, rel) if exists(root, rel) else ""
        kind, _ = report_marks(text)
        for l in above_table(text):
            if re.match(r"\s*Archived\b", l) and bad_marker(l):
                out.fail("Files (%s): an Archived line not in the form `Archived (user, YYYY-MM-DD)`: %s" % (rel, l.strip()),
                         "write it in that form, with the date it was saved Archived, on the line under `Kind:`")
        if kind is None:
            out.fail("Files (%s): no `Kind:` line above the first table" % rel,
                     "write `Kind: <kind>` on its own line above the approved text, <kind> one of: %s" % ", ".join(KINDS))
        elif kind not in KINDS:
            out.fail("Files (%s): Kind: %s is none of the kinds" % (rel, kind), "write one of: %s" % ", ".join(KINDS))
        typed = any(re.match(r"\s*Type:\s*\S", l) for l in above_table(text))
        if kind == "application answer":
            for h in untyped_headings(above_table(text)):
                out.fail("Files (%s): question heading with no Type: line under it: %s" % (rel, h),
                         "write `Type: <question type>` under it, the type as its stories.md row's first column has it")
        found = rel, kind == "resume bullets", kind in EMPLOYER_KINDS or typed
    if len(out.lines) == before:
        out.ok("Files (%s): ok" % rel)
    return found


def check_ranking(root, rel, out):
    """The Files lines for a ranking: applications.md › Events and contacts is one table, each row
    with the header's cells, and a row there names the report (rank step 6)."""
    name = rel.split("/")[-1]
    text = read(root, "applications.md") if exists(root, "applications.md") else None
    tables = [t for t in logfiles.md_tables(text) if t.section == EVENTS] if text is not None else []
    if not tables:
        out.fail("Files (%s): applications.md has no `## %s` table" % (rel, EVENTS),
                 "add the event's row to the table under `## %s` in applications.md" % EVENTS)
        return
    for t in tables[1:]:
        out.fail("Files (%s): applications.md:%d: a row outside the `## %s` table (a blank line or other "
                 "text above it ends the table)" % (rel, t.line, EVENTS),
                 "delete the lines between the table's last row and this one, so the row joins the table")
    head = tables[0]
    for n, cells in head.rows:
        if len(cells) != len(head.head):
            out.fail("Files (%s): applications.md:%d: %d cells, the table's header has %d" % (rel, n, len(cells), len(head.head)),
                     "give the row one cell per column, `|` between them, and `\\|` for a `|` inside a cell")
    if not any(name in " ".join(cells) for t in tables for cells in [t.head] + [c for _, c in t.rows]):
        out.fail("Files (%s): no row of applications.md › %s names %s" % (rel, EVENTS, name),
                 "add the event's row there, its Source cell a link to %s" % rel)


def check_risks(root, rel, prov, out):
    """A resume's provenance file, or a bullets report, has the Risks section after its provenance table."""
    try:
        text = read(root, prov)
    except (OSError, UnicodeError):
        return   # its Provenance check line says so
    rows = logfiles.provenance_rows(text)
    at = next((n for n, l in enumerate(text.lstrip("﻿").splitlines(), 1) if l.strip() == RISKS), None)
    if at is None or (rows and at < rows[-1][0]):
        out.fail("Risks (%s): no `%s` section after the provenance table in %s" % (rel, RISKS, prov),
                 "add it after the table, with the risks step 9 showed with the draft (attribution stretch, "
                 "caveats kept off the page, likely follow-up questions)")
    else:
        out.ok("Risks (%s): ok" % rel)


# ---- Past phrasings and the entries ----

def bullets_of(root, rel):
    """The approved bullets a saved output can feed into Past phrasings: [(words, citation pattern, the
    citation as write step 10 gives it)]."""
    if APPLICATION.match(rel):
        texs, cite = [rel + "/resume.tex"], (re.escape(rel) + r"/?", rel)
    elif TARGET.match(rel):
        tex = rel[:-3] + ".tex"
        texs, cite = [tex], (re.escape(tex) + r", \d{4}-\d{2}-\d{2}", tex + ", YYYY-MM-DD")
    else:
        text = read(root, rel) if exists(root, rel) else ""
        if report_marks(text)[0] != "resume bullets":
            return []
        items = [re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", l) for l in above_table(text)
                 if re.match(r"\s*(?:[-*+]|\d+\.)\s+\S", l)]
        return [(words(writing_lint.tex_plain(i)), re.escape(rel), rel) for i in items]
    out = []
    for tex in texs:
        if exists(root, tex):
            out += [(words(writing_lint.tex_plain(i)),) + cite for _, i in logfiles.tex_bullets(read(root, tex))]
    return out


def archived_outputs(root):
    """The outputs saved Archived, as a Past phrasings citation names them (`outputs/` left off, as
    older citations do): each application folder with an archived.md, and each report with the
    Archived line."""
    out = []
    apps = os.path.join(root, "outputs", "applications")
    for name in os.listdir(apps) if os.path.isdir(apps) else []:
        if os.path.isfile(os.path.join(apps, name, "archived.md")):
            out.append("applications/" + name)
    reports = os.path.join(root, "outputs", "reports")
    for name in os.listdir(reports) if os.path.isdir(reports) else []:
        try:
            if name.endswith(".md") and report_marks(read(root, "outputs/reports/" + name))[1]:
                out.append("reports/" + name)
        except (OSError, UnicodeError):
            pass
    return out


def changed_entries(root):
    """The entries that differ from git's HEAD (new ones included), as paths from the root."""
    return sorted(p for p in changed_paths(root, "entries/") if ENTRY_PATH.fullmatch(p) and exists(root, p))


def changed_paths(root, *spec):
    """The paths under spec (default: the whole Log) that differ from git's HEAD, new and deleted ones
    included, as paths from the root."""
    spec = spec or (".",)
    paths = logfiles.git(root, "diff", "HEAD", "--name-only", "--relative", "--", *spec).splitlines()
    paths += logfiles.git(root, "ls-files", "--others", "--exclude-standard", "--", *spec).splitlines()
    return sorted({p for p in paths if p})


def output_name(rel):
    """A pattern for the saved output as a Past phrasings citation, a stories.md pointer, a scan
    report's Draft cell or an applications.md row names it (`outputs/` optional, as older citations
    leave it off)."""
    if TARGET.match(rel):
        name = re.escape(rel[len("outputs/"):-len(".md")]) + r"\.(?:md|tex|pdf)"
    else:
        name = re.escape(rel[len("outputs/"):])
    return r"(?<![\w.-])" + name + r"(?![\w.-])"


def names_output(text, saved):
    return any(re.search(output_name(rel), text) for rel in saved)


def added_lines(root, rel, old=None):
    """The lines a file has that HEAD's version lacks (all of a new file's)."""
    new = read(root, rel) if exists(root, rel) else ""
    old = at_head(root, rel) if old is None else old
    return list((Counter(new.splitlines()) - Counter(old.splitlines())).elements())


def saves_entry(old, new, saved, approved):
    """Whether this save changed the entry: a line its `## Past phrasings` gained or lost names the
    saved output, or one it gained holds a bullet of it (a cap's drop lies beside such an addition)."""
    before, after = Counter(phrasings(old)), Counter(phrasings(new))
    moved = list(((after - before) + (before - after)).elements())
    said = [b[0] for b in approved]
    return any(names_output(l[1], saved) for l in moved) or any(
        (m := PHRASING_PARTS.fullmatch("- **%s:** %s" % l)) and words(writing_lint.tex_plain(m.group(2))) in said
        for l in (after - before).elements() if l[0])


def at_head(root, rel):
    p = logfiles.git_run(root, "show", "HEAD:./" + rel)
    return p.stdout if p.returncode == 0 else ""


def show_line(line):
    return "[%s] %r" % (line[0] or "no angle", line[1][:120])


def check_phrasings(root, entry, old, new, approved, archived, out):
    """The Past phrasings line for one changed entry."""
    before, after = Counter(phrasings(old)), Counter(phrasings(new))
    removed, added = list((before - after).elements()), list((after - before).elements())
    if not removed and not added:
        return
    kept = list((before & after).elements())
    raw = {l.strip().lower() for l in (logfiles.section(new, "Past phrasings") or "").splitlines()}
    cites = lambda line, paths: any(re.search(re.escape(p) + r"(?![\w.-])", line[1]) for p in paths)
    fails, checks = [], []
    demoted = [r for r in removed if cites(r, archived)]
    removed = [r for r in removed if r not in demoted]
    for n, a in enumerate(added):
        line = "- **%s:** %s" % (a[0], a[1])
        m = PHRASING_PARTS.fullmatch(line) if a[0] and line.lower() in raw else None
        if not m:
            fails.append("added %s: not in the form `- **<angle>:** \"<wording>\" (<citation>)`" % show_line(a))
            continue
        if cites(a, archived):
            fails.append("added %s cites an Archived output: an Archived save adds no line" % show_line(a))
            continue
        said = words(writing_lint.tex_plain(m.group(2)))
        forms = [(cite, shown) for got, cite, shown in approved if got == said]
        if not forms:
            fails.append("added %s: its wording is no bullet of the approved resume or bullets report, word for word"
                         % show_line(a))
        elif not any(re.fullmatch(cite, m.group(3).strip()) for cite, _ in forms):
            fails.append("added %s: cite it as (%s)" % (show_line(a), forms[0][1]))
        twin = max(kept + added[:n], key=lambda k: similar(a, k), default=None)
        if twin and similar(a, twin) >= SIMILAR:
            checks.append("added %s differs only in words from %r (%.2f): keep it only when its meaning differs"
                          % (show_line(a), twin[1][:120], similar(a, twin)))
    for r in removed:
        twin = max(added, key=lambda a: similar(r, a), default=None)
        if twin and similar(r, twin) >= SIMILAR:
            fails.append("rewritten %s -> %r: a line stays as written" % (show_line(r), twin[1][:120]))
        else:
            checks.append("removed %s: check it is the line consolidate step 2 ranks last, at the three-wording cap"
                          % show_line(r))
    if len(removed) > len(added):
        fails.append("%d line(s) removed, %d added: a drop happens only beside an addition" % (len(removed), len(added)))
    head = "Past phrasings (%s): +%d -%d" % (entry, len(added), len(removed) + len(demoted))
    if demoted:
        head += " (%d citing an Archived output: the demote's)" % len(demoted)
    if fails:
        out.fail("%s; %s" % (head, "; ".join(fails)),
                 "put back each line as it stood; add only bullets of the approved resume or bullets report, word "
                 "for word, in the template's form, citing the output as the finding says; none in an Archived save")
    else:
        out.ok(head + "; ok")
    out.lines += ["  check: " + c for c in checks]


def check_entries(root, saved, out):
    """The Past phrasings and Entries lines for the entries the save changed; the save's entries."""
    archived = archived_outputs(root)
    approved = [b for rel in saved for b in bullets_of(root, rel)]
    changed, mine = changed_entries(root), []
    if not changed:
        out.ok("Past phrasings: no entry changed")
    for entry in changed:
        new, old = read(root, entry), at_head(root, entry)
        strip = lambda t: re.sub(r"^## Past phrasings[^\n]*\n.*?(?=^## |\Z)", "", t, flags=re.M | re.S).splitlines()
        if saves_entry(old, new, saved, approved):
            mine.append(entry)
            check_phrasings(root, entry, old, new, approved, archived, out)
            if strip(old) != strip(new):
                out.lines.append("  check: %s also changed outside ## Past phrasings, and the save commits it whole: "
                                 "check that change is a fact this run recorded, not a bulk change waiting for its yes"
                                 % entry)
        elif Counter(phrasings(old)) != Counter(phrasings(new)):
            out.ok("Past phrasings (%s): not this save's (no line it gained or lost names the output or holds "
                   "its bullet): not checked, not committed" % entry)
            out.lines.append("  check: check it is a bulk change waiting for its yes; a line this save added "
                             "names the output in its citation and is a bullet of it, word for word")
        cited = [l.strip() for l in (Counter(strip(new)) - Counter(strip(old))).elements() if entries_output.search(l)]
        for l in cited:
            out.fail("Entries (%s): added a line naming an output: %s" % (entry, l[:160]),
                     "take it out: the provenance table already says where the material was used")
    return mine


entries_output = re.compile(r"(?<![\w-])outputs/[\w.-]")


# ---- Lint at save ----

def check_lint(root, saved, out):
    texts = []
    for rel in saved:
        if is_ranking(root, rel):
            continue   # the user's own list, never sent
        if APPLICATION.match(rel):
            texts += [rel + "/resume.tex", rel + "/answers.md"]
        elif TARGET.match(rel):
            texts.append(rel[:-3] + ".tex")
        else:
            texts.append(rel)
    lint = writing_lint.Lint(writing_lint.read_rules(root), writing_lint.private_links(root))
    artifacts = []
    for rel in texts:
        if not exists(root, rel):
            continue
        text = read(root, rel)
        artifacts += lint.resume(rel, text, None) if rel.endswith(".tex") else lint.prose(rel, text)
    lint.across(artifacts)
    kept = [l for l in lint.out if "(SKILL.md › Visibility)" in l or "(writing.md › AI-tell check: Spend the words)" in l]
    for l in kept:
        if l.startswith("fix:"):
            out.fail("Lint at save: " + l, "take the link out of the saved text and its draft, then run it again")
        else:
            out.ok("Lint at save: " + l)
    if not kept:
        out.ok("Lint at save: ok")


# ---- Humanizer ----

def humanizer_lines(arg):
    """(the Humanizer after review lines, whether they pass)."""
    if arg.strip().lower() == "none":
        return ["Humanizer after review: none"], True
    with open(arg, encoding="utf-8-sig") as f:
        given = [l.strip() for l in f.read().splitlines() if l.strip()]
    if not given:
        return ["Humanizer after review: %s is empty: pass --humanizer none when the review changed no text" % arg], False
    out, ok = [], True
    for l in given:
        m = HUMANIZER_LINE.match(l)
        if m:
            out.append("Humanizer after review: %s -> %s" % (m.group(1), m.group(2)))
        else:
            out.append("Humanizer after review: not in the form <changed line> -> <its Humanizer call: line, "
                       "or: humanizer not available>: %s" % l)
            ok = False
    return out, ok


HUMANIZER_FIX = ("for each such line: when it had its humanizer call after the review, write it in the form; "
                 "otherwise give it its humanizer pass (review.md › Apply the review) and its call line first")


# ---- Commit ----

def is_ranking(root, rel):
    """Whether a saved path is rank step 6's ranking: named `-ranking.md`, with no `Kind:` line (a
    write report may end its slug in `ranking`)."""
    return bool(RANKING.match(rel)) and (not exists(root, rel) or report_marks(read(root, rel))[0] is None)


def name_part(text, fallback=""):
    """A company, role or event as a file name has it: tools/logfiles.py ascii_slug (tools/scan.py
    names a name with no ASCII letter or digit `posting`)."""
    return logfiles.ascii_slug(text) or fallback


def subject_problem(root, rel, subject):
    """Why a --commit subject is not the one the save's mode gives for rel, or None."""
    if APPLICATION.match(rel):
        m = re.fullmatch(r"write\((.+?)\): (\S.*)", subject)
        folder = rel.split("/")[-1]
        names = {"%s-%s" % (name_part(m.group(1), c), name_part(m.group(2), r))
                 for c in ("", "posting") for r in ("", "posting")} if m else set()
        if any(re.fullmatch(r"\d{4}-\d{2}-\d{2}-%s(?:-\d+)?" % re.escape(n), folder) for n in names):
            return None
        return ("`write(<company>): <role>`, the `commit:` line tools/application.py name printed (a scan accept: "
                "company and role as the folder's name gives them after its date)")
    if TARGET.match(rel):
        want = "write(%s): resume" % TARGET.match(rel).group(1)
        return None if subject == want else "`%s`" % want
    if is_ranking(root, rel):
        event = RANKING.match(rel).group(1)
        m = re.fullmatch(r"rank\((.+?)\): \d+ employers", subject)
        if m and event in (logfiles.ascii_slug(m.group(1)), "-".join(m.group(1).lower().split())):
            return None
        return "`rank(<event>): <n> employers`, <event> the event the file is named for (%s)" % event
    slug = rel.split("/")[-1][len("YYYY-MM-DD-"):-len(".md")]
    kind = report_marks(read(root, rel))[0] if exists(root, rel) else None
    want = "write(%s): %s" % (slug, kind or "<its Kind: line's kind>")
    return None if subject == want else "`%s`" % want


def commit_paths(root, saved, entries):
    """The paths a save commits: each <saved> (a target's .tex and .pdf with its .md), then each Log
    file this save wrote, by what it gained since HEAD: <entries> (check_entries' list); stories.md
    when a line it gained names the output (answer-set's pointer); profile.md when its Interview prep
    list gained a line; for an application folder each scan report whose gained lines name it (a scan
    accept's status line) and then outputs/dashboard/; for a ranking applications.md when a line it
    gained names it."""
    paths = []
    for rel in saved:
        paths.append(rel)
        if TARGET.match(rel):
            paths += [p for p in (rel[:-3] + ".tex", rel[:-3] + ".pdf") if exists(root, p)]
    paths += entries
    if any(names_output(l, saved) for l in added_lines(root, "stories.md")):
        paths.append("stories.md")
    if exists(root, "profile.md"):
        prep = lambda t: logfiles.section(t, "Interview prep list") or ""
        if Counter(prep(read(root, "profile.md")).splitlines()) - Counter(prep(at_head(root, "profile.md")).splitlines()):
            paths.append("profile.md")
    if any(APPLICATION.match(rel) for rel in saved):
        scans = [p for p in changed_paths(root, "outputs/reports/") if SCAN_REPORT.fullmatch(p.split("/")[-1])
                 and exists(root, p) and any(names_output(l, saved) for l in added_lines(root, p))]
        if scans:
            paths += scans + changed_paths(root, "outputs/dashboard/")
    if any(is_ranking(root, rel) for rel in saved) and any(names_output(l, saved) for l in added_lines(root, "applications.md")):
        paths.append("applications.md")
    return list(dict.fromkeys(paths))


def left_paths(root, paths):
    """The paths that differ from HEAD and are not among the committed ones (nor in a committed folder)."""
    inside = lambda p: any(p == c or p.startswith(c.rstrip("/") + "/") for c in paths)
    return [p for p in changed_paths(root) if not inside(p)]


def commit(root, saved, subject, entries):
    """`commit: <subject>`, a `left:` line for each other path that differs from HEAD, then
    tools/sync.py commit's own lines; sync.py's exit code."""
    print("commit: %s" % subject)
    paths = commit_paths(root, saved, entries)
    for path in left_paths(root, paths):
        print("left: %s: differs from HEAD, not written by this save: not committed" % path)
    sys.stdout.flush()
    p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "sync.py"), "commit", "--root", root, subject, "--"]
                       + paths, capture_output=True, encoding="utf-8", errors="replace")
    sys.stdout.write(p.stdout + p.stderr)
    return p.returncode


# ---- Audit ----

def audit(root):
    findings = []
    apps = os.path.join(root, "outputs", "applications")
    for name in sorted(os.listdir(apps)) if os.path.isdir(apps) else []:
        d = os.path.join(apps, name)
        if not os.path.isdir(d) or os.path.isfile(os.path.join(d, "sent-version.md")):
            continue
        if not os.path.isfile(os.path.join(d, "provenance.md")):
            findings.append("outputs/applications/%s: no provenance.md" % name)
        if not os.path.isfile(os.path.join(d, "resume.pdf")):
            findings.append("outputs/applications/%s: no resume.pdf: a finding when it was sent (ask the user "
                            "when nothing in the log says)" % name)
    top = os.path.join(root, "outputs")
    for name in sorted(os.listdir(top)) if os.path.isdir(top) else []:
        if name not in OUTPUTS_TOP and not name.startswith("."):
            findings.append("outputs/%s: at the top of outputs/, besides %s" % (name, ", ".join(t + "/" for t in OUTPUTS_TOP)))
    for _, prov, _ in outputs(root):
        if not prov or not exists(root, prov) or SCAN_REPORT.fullmatch(prov.split("/")[-1]):
            continue
        try:
            rows = logfiles.provenance_rows(read(root, prov))
        except UnicodeError:
            findings.append("%s: not UTF-8" % prov)
            continue
        if not rows and prov.startswith(("outputs/applications/", "outputs/reports/")):
            findings.append("%s: no provenance table (a table with an entry or source column)" % prov)
        for n, cells, head in rows:
            why = row_problem(root, prov, cells, head)
            if why:
                findings.append("%s:%d %s: %s" % (prov, n, why, " | ".join(cells)[:200]))
    for f in findings:
        print("finding: " + f)
    print("check_save: ok" if not findings else "check_save: %d findings: report each" % len(findings))
    return 1 if findings else 0


# ---- main ----

def saved_rel(root, p):
    """A <saved> path as a path from the root, or None when it is not a saved output in the Log."""
    path = os.path.abspath(p if os.path.isabs(p) else os.path.join(root, p))
    try:
        rel = os.path.relpath(path, root).replace("\\", "/").rstrip("/")
    except ValueError:   # another drive
        return None
    if rel.startswith("../") or rel == "..":
        return None
    if rel.endswith("/provenance.md") and APPLICATION.match(rel[:-len("/provenance.md")]):
        rel, path = rel[:-len("/provenance.md")], os.path.dirname(path)
    if APPLICATION.match(rel) and os.path.isdir(path):
        return rel
    if PROVENANCE_FILE.match(rel) and os.path.isfile(path) and not rel.startswith("outputs/applications/"):
        return rel
    return None


def main(argv):
    logfiles.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("saved", nargs="*", help="an application folder, a target's .md, or a report")
    ap.add_argument("--humanizer", help="`none`, or a file of `<changed line> -> <Humanizer call: line>` lines")
    ap.add_argument("--audit", action="store_true", help="audit point 6's checks on every output")
    ap.add_argument("--commit", metavar="SUBJECT", help="on exit 0, commit the save with this subject (tools/sync.py commit)")
    ap.add_argument("--checked", action="store_true", help="with --commit: each `check:` line was acted on")
    logfiles.add_root(ap, __file__)
    a = ap.parse_args(argv[1:])
    root = os.path.abspath(a.root)
    if a.audit:
        if a.saved or a.commit:
            print("--audit reads every output: give it no <saved> and no --commit")
            return 2
        return audit(root)
    if a.checked and not a.commit:
        print("--checked goes with --commit")
        return 2
    if a.commit is not None and len(a.saved) != 1:
        print("--commit takes one saved output: the one this save wrote")
        return 2
    if not a.saved:
        print("give a saved output (an application folder, outputs/resumes/<target>.md, outputs/reports/<file>.md), or --audit")
        return 2

    saved = []
    for p in a.saved:
        rel = saved_rel(root, p)
        if not rel:
            print("%s: not an application folder or a saved provenance file (outputs/resumes/<target>.md, "
                  "outputs/reports/<file>.md) in the Log at %s" % (p, root))
            return 2
        saved.append(rel)

    out, needs_humanizer = Report(), False
    try:
        for rel in saved:
            prov, holds_resume, employer = check_files(root, rel, out)
            needs_humanizer = needs_humanizer or employer
            if holds_resume:
                check_risks(root, rel, prov, out)
            if prov is None:   # a ranking: its sources are URLs, with no provenance table
                continue
            line, good = check_file(root, prov)
            if good:
                out.ok(line)
            else:
                out.fail(line, PROVENANCE_FIX)
        entries = check_entries(root, saved, out)
        check_lint(root, saved, out)
        if a.commit is not None:
            want = subject_problem(root, saved[0], a.commit)
            if want:
                out.fail("Commit subject: %r is not this save's" % a.commit, "pass --commit with " + want)
    except (logfiles.LogError, writing_lint.LintError) as e:
        print(e)
        return 2
    except NotUTF8 as e:
        print("cannot read %s: not UTF-8: save it as UTF-8" % e)
        return 2
    except (OSError, UnicodeError) as e:
        print("cannot read %s: %s" % (getattr(e, "filename", None) or "a saved file", getattr(e, "strerror", None) or e))
        return 2
    if a.humanizer is not None:
        try:
            hum, good = humanizer_lines(a.humanizer)
        except (OSError, UnicodeError) as e:
            print("--humanizer %s: %s" % (a.humanizer, getattr(e, "strerror", None) or e))
            return 2
        out.lines += hum
        if not good:
            out.lines.append("  fix: " + HUMANIZER_FIX)
            out.failed = True
    elif needs_humanizer:
        out.fail("Humanizer after review: missing",
                 "pass --humanizer <file>, or --humanizer none when the review changed no text")
    for line in out.lines:
        print(line)
    print("check_save: fix the lines above, then run it again" if out.failed else "check_save: ok")
    if out.failed:
        return 1
    if a.commit is None:
        return 0
    if not a.checked and any(CHECK_LINE.search(l) for l in out.lines):
        print("held: not committed: act on each `check:` line above, then run this again with --checked added")
        return 1
    try:
        return commit(root, saved, a.commit, entries)
    except logfiles.LogError as e:
        print(e)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
