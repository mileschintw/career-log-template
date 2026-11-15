#!/usr/bin/env python3
"""The application folders and the other saved outputs of write (skills/career-log/modes/write.md):
their names, earlier contact with a company, the starting copy, the save, the level, sent versions,
a target's staleness, risks and the Past phrasings a save feeds; and an interview's prep file, practice log
and recruiter mail.

  python3 -I tools/application.py [--root <root>] <command> ...     (Windows: py -3 -I ...)

<root> is the Log's root (default: the folder above this script's). Paths are read from <root> when
relative. <saved> is a saved output: an application folder (outputs/applications/<folder>), a
target's outputs/resumes/<target>.md, or a report outputs/reports/<YYYY-MM-DD>-<slug>.md.

- `name --company <company> --role <role>` (a posting run), `name --target <target>` (a target run)
  or `name --report <slug> --kind <kind>` (any other output); each takes --today YYYY-MM-DD. Prints
  `name:`, `draft: .build/drafts/<name>/`, then `folder: outputs/applications/<name>/`, `resume:
  outputs/resumes/<target>.md` or `report: outputs/reports/<YYYY-MM-DD>-<slug>.md`, then `commit:
  <subject>`: `write(<company>): <role>`, `write(<target>): resume` or `write(<slug>): <kind>`.
  Names are ASCII slugs (tools/logfiles.py ascii_slug; a company or role with no ASCII letter or
  digit is `posting`, as tools/scan.py names its draft folders: posting_slug),
  `<YYYY-MM-DD>-<company>-<role>` for a posting run; a name a saved folder or report already has
  takes the next free `-2`, `-3`. Drafts in .build/ do not count: a second call in the same run
  prints the same name.
- `prior <company>... [--type <question type>]`: for each company, `company: <company>`, then one
  `folder: <folder>/ | <date> | <Archived or Reference> | types: <its answers.md Type: lines, or
  none>` line per application folder whose name, less its date, starts with the company's words
  (newest first), and one `applications.md:<n>: <line>` per line of applications.md naming it as
  whole words; or `none: ...`. With --type, then one line per answer to that question type:
  `answer: <folder>/answers.md:<n> | <date> | Reference | <heading>` (a starting point, write-form-
  answers.md path 1), `untyped: ...` in the same form for each heading of a Reference folder saved
  before Type: lines (match its heading to the row yourself), and `sent before: ...` for an Archived
  folder's answer of that type or, saved before Type: lines, each of its headings; then, for each
  date of an `answer:` or `untyped:` line, `since <date>: <n> commit(s)` and the `git log --since
  --oneline` lines for entries/, direction.md, stories.md and profile.md.
- `start [--name <name> --from <target or file>] [--replace]`: without --from, one `target: <name>
  | outputs/resumes/<name>.tex` per target (or `targets: none`), then `fallback:` the newest
  sources/resumes/*-main.tex, else the newest .tex there (newest by the YYYY-MM-DD its name starts
  with), `fallback: tie: <a>, <b>` when several share that date, or the blank layout
  skills/career-log/assets/resume-blank.tex. With --from, copies that target's .tex, or that file,
  to .build/drafts/<name>/resume.tex; it refuses the example resume, and a draft there with other
  text unless --replace. A posting run adds `--family <target name> --tier <n>|none`: the target
  name of the posting's role family (`general` exactly when direction.md's Target roles are empty)
  and the role's place in those Target roles, `GAP:` lines counted as tools/fit.py ranks counts them
  (`none` when it is not among them); after copying, it
  writes them with --from's path to .build/drafts/<name>/start.txt (`from:`, `family:`, `tier:`
  lines, for tools/check.py done write) and prints `recorded: <that path>`.
- `save --application <name>` or `save --target <target>`: copies .build/drafts/<name>/resume.tex
  and resume.pdf to outputs/applications/<name>/ (with the draft's posting.md when the folder has
  none) or to outputs/resumes/<target>.tex and .pdf, printing a `copied:` line each. It refuses a
  draft without both files, and an application folder's committed resume.* with other content:
  that folder was sent and is frozen.
- `level <saved> archived|reference [--today YYYY-MM-DD]`, for an application folder or a `Kind:
  resume bullets` report (write › Save levels):
  - archived: writes the marker (archived.md, or the line under the report's `Kind:` line);
    deletes each ## Past phrasings line citing the output (`outputs/applications/<folder>` or the
    older `applications/<folder>`, likewise for a report), printing it; removes each stories.md
    pointer to a file under it, through tools/entries.py answer-set --remove, printing each.
  - reference: deletes the marker, then prints a `feed:` line naming the phrasings command for the
    bullets and one `answer: <type> | <path>` line per typed answer, for **Feed later runs**.
  Then `files:` (each file it wrote or deleted, for the commit) and `commit: <subject> to <level>`,
  the subject of the first `write(` commit that saved it (`write(<company>): <role>`), else
  `write(<folder>): application` or `write(<report name>): resume bullets`. For an output no
  commit has touched yet (an Archived save's marker, written before that save's commit), it
  prints `not committed: <saved> has no commit yet: ...` in their place. It prints `unchanged:` for an output
  already at that level, and refuses a folder holding the marker's name in another case (Archived.md).
- `sent <target> [--before <when>] [--record <folder>]`: the last commit of
  outputs/resumes/<target>.*, before that time with --before (a date alone: the end of that day;
  <when> is YYYY-MM-DD[ HH:MM] in this machine's time zone, or a time with its zone, such as an
  export's 2025-10-02T06:30:00Z, converted to it),
  as `version: <hash>:outputs/resumes/<target>.tex` and the applications.md cell, `cell:
  [<target> @ <short>](https://github.com/<owner>/<repo>/blob/<hash>/outputs/resumes/<target>.pdf)`
  for a GitHub origin, else the bare short hash. With --before, also `changed that day: 1 commit`
  (`<n> commits` otherwise): for a date given alone, more than 0 means the user is asked which
  version went. Without --before it fails while the target's files have uncommitted changes
  (commit first). --record writes the version to <folder>/sent-version.md.
- `sent-candidates --before <when> [--limit <n>]`: for a resume sent before the Log's targets.
  `before: <date>` (with `(<when> in this machine's time zone)` when <when> had a zone), `targets
  saved by <date>: <target> (<first save>), ...` or `targets: none saved by <date>`, then one
  `candidate: <hash>:sources/resumes/<file> | <date>` per file there whose name starts with a date
  on or before it (newest first, the newest <n>, default 5; `| uncommitted: commit it first` for one
  not committed as it is), `older: <n> more (--limit <all> shows them)`, then per consecutive pair,
  older first, `diff: <older> -> <newer>: <n> line(s) differ` and a `- `/`+ ` line per changed line
  (or `: identical`, `: not text`), and a `next:` line. `none: ...` and exit 1 when no file is that old.
- `sent-show <ref>... [--target <target>] [--out <file>] [--record <folder>] [--known <text>]
  [--today YYYY-MM-DD]`: <ref> is an applications.md cell, its permalink, `<hash>:<path>`, a folder
  with sent-version.md, or a bare hash, alone or in the row's words (with --target). Prints `version:
  <hash>:<path>` (the path's .pdf read as .tex) and the file at that commit, or writes its bytes to
  --out; a bare hash whose path is not at that commit prints a `touched:` line per file it changed,
  and fails. --record as for sent. Several refs (or a folder whose sent-version.md names several
  candidates): `candidates: <n>`, `known: <text>` (from the folder), each `version:` and its file,
  then per consecutive pair `differ: <a> -> <b>: ...` with the changed lines as sent-candidates
  prints them; --out refuses. --record with several takes --known, the user's statement of which
  went: sent-version.md gets one version per line, a blank line, `Known: <text> (user,
  <--today>)`, and the `Differ:` lines in a diff block. The same candidates again leave it
  `unchanged:`; another set is refused. The one-version form reads as before.
- `stale <target>`: how far a Target version has fallen behind the Log since its last save (the last
  `write(` commit of outputs/resumes/<target>.*, else its last commit); it judges nothing. `saved:
  <short> <date> <subject>`, then `cited changed: <n>` and one `  <entry>: <n> commit(s), last <date>
  <subject>` line (with `uncommitted changes`) per entry its provenance cites, by path or by name as
  tools/entries.py rulings-hits reads them, that changed since; `new entries: <n>` and one `
  <entry>: <title>` line (` (uncommitted)` when not yet committed) per entry added since, listed
  there and not as cited; `unresolved: <line>: <cell>` per provenance row that names no entry;
  `no provenance: ...` when the save's commit has no <target>.md, or its <target>.md is empty or
  names no entry; then last `verdict: stale` (an entry is on either list), `verdict: not compared`
  (both lists are empty and the provenance cites no entry) or `verdict: fresh` (both are empty and
  it cites one), the line audit and write read. Exit 0 on fresh, 1 otherwise, or with `none: ...`
  (no verdict line) when the target is not saved. `stale(root, target)` gives the same lists to
  another tool.
- `risks <saved>`: `risks: <where>` and the `## Risks to handle in conversation` section saved with
  the output: an application folder's provenance.md; a folder with sent-version.md, the target's
  .md at that commit (with several candidates, the first that has the section); a target's .md or
  a report; else `risks: none (saved before the section
  existed)`. With several candidates in sent-version.md (provenance.md or not), then `candidates: <n>: ...`, `known: <the Known: line>`,
  `version <i>: <hash>:<path>` per candidate in the file's order (followed by `missing: version
  <i>: ...` when the file is not at that commit, or `not text: version <i>: ...` for an imported
  .pdf, whose claims are read with sent-show --out), then `differ: <n> line(s) not in every version`
  (`differ: none: ...` when they hold the same lines; `differ: not compared: ...` with fewer than two
  text versions) and one `line (version <i>): <line>` or `line (versions <i>, <j>): <line>` per such
  line, in order of first appearance, naming each version that holds it; every version means every
  text version, and blank lines are left out.
- `phrasings <saved, or a draft in .build/> --angle <angle> [<entry>...] [--today YYYY-MM-DD]`: the
  bullets of the resume (its .tex's `\\item`s, less those under an Education or Skills heading:
  tools/logfiles.py tex_bullets) or of the `resume bullets` report (its list items; a draft .md's), `bullet <n>: <wording>`, each followed, per
  entry, by `  <entry>: <ratio> <line>: <its closest wording for the angle>` (or `none for
  <angle>`), then one verdict line for the bullet:
  - `  same: <entry>:<line>: adds no line`: a wording an entry keeps for the angle at a ratio of
    tools/entries.py's SIMILAR or more;
  - else the bullet's entry is the one holding the largest share of its words (three letters or
    more, less a few such as `and`, `with`; the first entry given on a tie; a bullet merged from two
    claims goes to the one holding more), and the line is `  add: <entry>` (it differs from every
    wording kept for the angle, and goes in whole); `  none: ...` when the entries given hold less
    than half its words together (a line from profile.md, such as education); or `  older
    form: <entry>: ...` when that entry's ## Past phrasings has lines in neither the template's
    form nor a placeholder such as `none yet` or `GAP:` (the older `**<label>**` form), which adds no line;
  after an `add:` line, `  at cap: <entry>: <line>,<line>: ...` when the entry already keeps two
  wordings (check_save.py PHRASING_CAP) for the angle within CLAIM of the bullet, taken for its
  claim: adding it makes a third, and --cap keeps two;
  then `cite: <citation>` (write step 10's form for that output), `entry: <entry>: <n> lines for
  <angle>`, and last `adds: <the --add flags for each add: bullet>` (or `adds: none`), the flags to
  run the same command with. An Archived output prints `archived: ... feeds nothing`.
  - `--add <n>=<entry>[,distinct|,replace=<line>]...` writes bullet <n> into the entry through
    tools/entries.py phrasing-add with that citation, and prints its lines.
  - `--cap <entry>=<line>,<line>,...` names the lines of one claim for the angle: keeps the two
    consolidate step 2 ranks first (from an output above imported, then newer above older) and
    deletes the rest, printing each.
  Both end with `line: <entry>:<n>: <line>` for each of the entry's lines for the angle as it now
  stands: the line numbers a later --replace or --cap takes.
- `prep-init <folder> --stage <stage> [--with talk,areas] [--date YYYY-MM-DD] [--mode-start <value>]`:
  writes <folder>/prep-<stage>.md, the prep file of one interview stage (<stage> a lowercase slug,
  as in interview-<stage>.md), and prints `wrote: <its path>`; it fails on a folder that does not
  exist and prints `refused: ...` for a prep file that does. It starts `## Decisions` with the
  statements SKILL.md's Direction upkeep saved for this application: each line of the folder's
  `notes.md` (written while it has no prep file) that is not blank, a `#` heading or a `---` rule,
  less a leading `- ` or `* `; then the value of each row of the Decisions of the folder's other
  prep files whose decision is `note` (any case) and whose value is not empty, those files in file
  name order; each text once (exact text), where it was first found. Each is a row `| <n> | note |
  <the text> | <file name>:<its line number> | |`, and it prints `carried: <count> lines of
  <folder>/notes.md into ## Decisions` and, per other prep file carried from, `carried: <count>
  note rows of <folder>/<its file name> into ## Decisions`. Its format, which an agent keeps up to
  date by hand:
  - a header: `# Prep: <stage>`, then `stage: <stage>`, `interview: <YYYY-MM-DD, or ?>` (--date),
    `mode start: <value, or ?>` (--mode-start: the interview mode's first `mode start:` value) and
    `practice log: practice-<stage>.md`;
  - `## Items`, `| item | phase | state | where |`, one row per piece of the prep, in phase order.
    phase: intake, research, align, pack, plan or practise. state: `open`, `done`, `user-only` (a
    fact or decision only the user can give) or `set aside`. where: empty or `-` until there is a
    file, else one or more paths relative to the folder, comma-separated, each optionally with a
    `#section`. prep-init writes the standard items, all `open`: recruiter-mail, posting,
    sent-version (intake); research, requirement-map, deep-dives (research); user-only-facts,
    behavioural-leads, areas (--with areas), talk (--with talk) (align); tell-me-about-yourself,
    why-this-company, awkward-questions (pack); logistics, effort, schedule (plan); practice, mock
    (practise). The agent adds a row for anything else the recruiter's mail asks for. The items'
    names are the practice log's items too.
  - `## Decisions`, `| # | decision | value | source | backup / note |`: one row per decision the
    user made, source `(user, YYYY-MM-DD)`. A statement that holds for the whole application, not
    this stage (SKILL.md's Direction upkeep), has the decision `note` and the statement as its
    value; a row prep-init carried has the source `<file name>:<its line number then>`.
  - `## Schedule`, `| date | commitments | plan | estimate |`: one row per day or block, its first
    cell starting with the date (`2026-03-10`, `2026-03-10 am`); commitments are the user's own, each
    with its clock time; estimate is the block's time, sized from the measured pace. A re-plan edits
    these rows in place, one table.
  - `## Pages`, `| page | built from | link | for |`: one row per page built for the run, added
    when it is built (skills/career-log/pages.md). page: the page's file, a path relative to the
    folder; built from: the one Log file it is built from, relative to the folder or, with a leading
    `/`, to the Log's root (`/stories.md`), or `-` when the page is its own source; link: where it
    is published; for: the device it is for.
  The file holds state, decisions, the schedule and links only; per-attempt practice results go in
  the practice log.
- `prep-status <folder> [--stage <stage>] [--today YYYY-MM-DD]`: reads <folder>/prep-<stage>.md
  (--stage may be left out when the folder has one prep file) and prints `prep: <its path>`,
  `today: <date>` (the machine's date in its time zone), `days left: <n>` to the interview date
  (`days left: unknown (interview: ?)`, or `days left: none (the interview was <date>)` after it),
  `schedule: <the row's cells>` for each Schedule row dated today (`schedule: nothing for
  today` with none), then one `<state>: <item>` line per item in file order, with ` (<where>)` when
  where is set; then, from the practice log's `## Attempts` table (none when the log or the table
  is missing), `retest: <item>` for each item whose latest attempt's verdict is shaky or again, in
  the order of those latest attempts, and `not practised: <item>` for each open or user-only practise-phase
  item with no attempt for it or a sub-item under it (any attempt counts for `practice`); then,
  while neither effort nor schedule is done, `not diagnosed: <area>` for each area with no
  `diagnostic` attempt for it or a sub-item under it: `behavioural answers` (with a
  behavioural-leads item; a `story/<key>` attempt counts), each `areas/<topic>` item (`areas`,
  with an areas item, while there is no `areas/<topic>` item), `talk` (with a talk item); an area
  is left out when its item is set aside or a Decisions row's decision is `diagnose: <area>` and
  its value starts with `set aside`; then, when `days left: 1` (the evening of the final review),
  `not reviewed: <item>` for each item on a `retest:` or `not practised:` line with no Decisions
  row whose decision is `final review: <item>` (the user's answer: do it tonight, or drop it),
  and for each practise-phase item set aside with no Decisions row naming it (its decision `<item>`
  or `<any>: <item>`); then `next:` lines: after the interview date, while <folder>/interview-<stage>-debrief.md does
  not exist, `next: close the loop (ask for the questions asked, round by round)`; `next: <item>
  (user-only)` for each user-only item, then `next: <item> (open, <phase>)` for the first open item
  of the earliest phase, or `next: nothing open` when there is none of these. It fails, with a
  `FAIL: <file>:<line>: ...` line per problem and nothing else, on an item row with an unknown
  state or phase or not four cells, a done row whose where names a path (the part before `#`) the
  folder lacks, a path outside it, or a `#section` alone, or an attempt row with an unknown verdict
  or not six cells; and on a page row not of four cells, or whose page or built-from names no
  file, a missing one, a `#section`, or one outside the folder (outside the Log, for a built-from
  with a leading `/`). The `stale:` lines come after the item lines and before the `retest:` lines:
  one `stale: <page> (built from <file>, changed since)` per page whose source changed after it: the
  source's last commit is one the page's last commit does not contain, or the source has uncommitted
  changes and the page none (no stale lines outside a git repository). Then, when the folder has
  `cue-card-<stage>.md` (this prep file's stage) and no `## Pages` row's built from names it (a
  row whose page is the card itself does not count), `no page: cue-card-<stage>.md (no ## Pages row
  built from it)`.
- `practice-add <folder> [--stage <stage>] --item <item> --verdict <verdict> [--kind <kind>]
  [--weak "<weak spots>"] [--heard <heard>] [--today YYYY-MM-DD]`: appends one attempt, dated
  today (the machine's date; --today for another), to the prep file's practice log (its header's
  `practice log:`, practice-<stage>.md in the folder), writing the log first when it does not
  exist, and prints `added: <the log's path>: <the row>`. --stage as for prep-status. The log is
  history: rows are added, never rewritten. Its format:
  - a header: `# Practice: <stage>`, then `prep: prep-<stage>.md`;
  - `## Attempts`, `| date | item | kind | verdict | weak spots | heard |`, one row per attempt in
    the order made. item: an item of the prep file, a sub-item under one (`areas/<topic>`,
    `talk/<part>`) or a told Story (`story/<key>`); kind: what the attempt was, in a word or two
    (`round` when --kind is left out; `diagnostic`, `mock`, `drill`); verdict: passed, near, shaky or again;
    weak spots: free text or `-`; heard: typed, recorded, live or `-`.
  - `## Patterns`: faults seen across items, one bullet each, kept by hand.
  - `## Do not say`: statements the user made that the Log does not hold, or that are wrong, each
    with its correction, kept by hand; at most ten are carried to the final review.
  It fails on an unknown verdict or heard, an item that is none of these, or a log with no table
  under `## Attempts`; the row goes after that table's last row.
- `intake <file>... --folder <folder> [--today YYYY-MM-DD]`: the recruiter's mail and its attachments
  as UTF-8 text in the application folder <folder>, one file per input:
  <folder>/recruiter/<YYYY-MM-DD>-<slug>.md. <file> is a saved mail (.eml) or a file on its own
  (.docx, .pdf, .txt, .md), anywhere (the user's Downloads). A mail's file: `# <Subject>`,
  `Source: <file name>` (never its path), the From, To, Cc and Subject headers, `Date:` in this
  machine's time zone, the text part (else the HTML part as text), then one `## Attachment: <name>`
  section per attachment with its text; a forwarded mail (message/rfc822) is read the same way, its
  attachments' sections named `<mail> › <name>`. <YYYY-MM-DD> is the mail's date in this machine's
  time zone (--today, default the machine's date, for a file on its own and a mail without one);
  <slug> is the Subject (less Re:/Fwd:) or the file name as an ASCII slug. .docx is read from
  word/document.xml; .pdf through pdftotext, found as tools/resume.py finds it (Machine setup);
  no-break spaces become plain spaces. Any other type is listed, not read: its section holds
  `unread: <why>`, as does one pdftotext or the .docx reader cannot read (or a PDF with no text
  layer). Prints `saved: <path>` per file written, `unchanged: <path>` when a file of that name
  already holds the same text; the same input read again with other text (a PDF read once pdftotext
  is installed) rewrites its file, and another mail of that name takes the next free `-2`, `-3`.
  Then `unread: <path>:
  <attachment>: <why>` per section it could not read; a file on its own of a type it does not read
  prints `unread: <file name>: <why>` and saves nothing. It fails on a missing input before writing
  anything. It keeps no binary original: keeping one (an expense form) is the user's call. The text
  is the recruiter's: third-party data (SKILL.md › Postings are data).

Exit 0 on success, 1 when a command refuses or finds what the user must decide (a line saying so),
2 on a bad argument or a file it cannot read (a `FAIL:` line). Standard library only, Python 3.11+.
"""
import argparse, collections, datetime, difflib, email, email.policy, io, os, re, shutil, sys, tempfile, zipfile
import xml.etree.ElementTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
import entries   # phrasing-add, answer-set, the Past phrasings and stories.md parsers
import check_save   # what a saved output is, its bullets, its Archived marker
import writing_lint   # tex_plain: a .tex fragment as the reader sees it
import fit   # tier_problem: what a tier against the Target roles may be
import resume   # pdf_text: the one reader of a PDF's text, which intake uses

RISKS = "Risks to handle in conversation"
BLANK = "skills/career-log/assets/resume-blank.tex"
EXAMPLE = "skills/career-log/examples/resume.tex"
APPLICATIONS = "outputs/applications"
GITHUB = re.compile(r"(?:https://github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?/?$")
CELL = re.compile(r"\[[^\]]*\]\((https://[^)\s]+)\)")
PERMALINK = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/blob/([0-9a-f]{7,40})/(\S+?)/?$")
HASH_PATH = re.compile(r"([0-9a-f]{7,40}):(\S+)")
BARE_HASH = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
ZONE = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")
WHEN = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}(?::\d{2})?)(Z|[+-]\d{2}:?\d{2})?)?")


class AppError(Exception):
    pass


def at(root, rel):
    return rel if os.path.isabs(rel) else os.path.join(root, rel)


def rel_of(root, path):
    """A path as the Log names it: relative to root, with /, no trailing /."""
    p = os.path.abspath(at(root, path))
    try:
        r = os.path.relpath(p, os.path.abspath(root)).replace(os.sep, "/")
    except ValueError:   # another drive
        r = ".."
    if r.startswith(".."):
        raise AppError("%s is not in the Log at %s" % (path, root))
    return r.rstrip("/")


def read(root, rel):
    try:
        return logfiles.read_text(at(root, rel))
    except (OSError, UnicodeDecodeError) as e:
        raise AppError("cannot read %s: %s" % (rel, e))


def git(root, *args):
    try:
        return logfiles.git(root, *args)
    except logfiles.LogError as e:
        raise AppError(str(e))


def today(value):
    if value is None:
        return datetime.date.today().isoformat()
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        raise AppError("--today takes YYYY-MM-DD: %s" % value)


def one_line(text):
    return " ".join((text or "").split())


# ---- name ----

def free_name(taken, base):
    name, n = base, 2
    while name in taken:
        name, n = "%s-%d" % (base, n), n + 1
    return name


def cmd_name(root, company, role, target, report, kind, day):
    if sum(x is not None for x in (company or role, target, report)) != 1 or bool(company) != bool(role):
        raise AppError("name takes --company and --role, or --target, or --report with --kind")
    if company:
        c, r = logfiles.posting_slug(company), logfiles.posting_slug(role)
        apps = at(root, APPLICATIONS)
        name = free_name(set(os.listdir(apps)) if os.path.isdir(apps) else set(), "%s-%s-%s" % (day, c, r))
        lines = ["folder: %s/%s/" % (APPLICATIONS, name), "commit: " + check_save.write_subject(c, one_line(role))]
    elif target:
        name = logfiles.ascii_slug(target)
        if not name:
            raise AppError("--target needs letters or digits: %r" % target)
        lines = ["resume: outputs/resumes/%s.md" % name, "commit: " + check_save.write_subject(name, "resume")]
    else:
        if not kind:
            raise AppError("--report takes --kind <kind>, one of: %s" % ", ".join(check_save.KINDS))
        if kind.lower() not in check_save.KINDS:
            raise AppError("--kind is one of: %s" % ", ".join(check_save.KINDS))
        slug = logfiles.ascii_slug(report)
        if not slug:
            raise AppError("--report needs letters or digits: %r" % report)
        d = at(root, "outputs/reports")
        taken = {f[len(day) + 1:-3] for f in (os.listdir(d) if os.path.isdir(d) else [])
                 if f.startswith(day + "-") and f.endswith(".md")}
        name = free_name(taken, slug)
        lines = ["report: outputs/reports/%s-%s.md" % (day, name), "commit: " + check_save.write_subject(name, kind.lower())]
    return ["name: %s" % name, "draft: .build/drafts/%s/" % name] + lines


# ---- prior ----

def folders(root):
    """[(folder rel path, name, date or None, Archived?)] for each application folder, newest first."""
    d = at(root, APPLICATIONS)
    out = []
    for name in sorted(os.listdir(d) if os.path.isdir(d) else [], reverse=True):
        if os.path.isdir(os.path.join(d, name)):
            out.append(("%s/%s" % (APPLICATIONS, name), name, logfiles.split_dated(name)[0],
                        logfiles.is_archived_folder(root, "%s/%s" % (APPLICATIONS, name))))
    return out


def typed_answers(text):
    """[(line number, heading, its Type: value or None)] for each question heading of an answers.md:
    the `## ` headings and below, or the `# ` ones in a file with none (as check_save reads them);
    `Company context` and `Risks...` set aside."""
    out, lines = [], text.lstrip("\ufeff").splitlines()
    level = 2 if any(re.match(r"#{2,6}\s", l) for l in lines) else 1
    for i, line in enumerate(lines):
        h = re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not h or len(h.group(1)) < level or re.match(r"(Company context|Risks)", h.group(2)):
            continue
        nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
        t = re.match(r"Type:\s*(\S.*?)\s*$", nxt)
        out.append((i + 1, h.group(2), t.group(1) if t else None))
    return out


def since_lines(root, day):
    try:
        log = git(root, "log", "--since=%s 00:00:00" % day, "--oneline", "--", "entries/", "direction.md", "stories.md",
                  "profile.md").splitlines()
    except AppError as e:
        return ["since %s: unknown (%s)" % (day, e)]
    return ["since %s: %s" % (day, logfiles.plural(len(log), "commit"))] + ["  " + l for l in log]


def cmd_prior(root, companies, qtype):
    out = []
    apps = os.path.join(root, "applications.md")
    app_lines = logfiles.read_text(apps).split("\n") if os.path.isfile(apps) else []
    for company in companies:
        want = logfiles.norm(company)
        if not want.strip():
            raise AppError("a company needs letters or digits: %r" % company)
        out.append("company: %s" % company)
        found, dates = False, []
        for rel, name, day, archived in folders(root):
            if not logfiles.norm(logfiles.split_dated(name)[1]).startswith(want):
                continue
            found = True
            ans = os.path.join(root, rel, "answers.md")
            heads = typed_answers(read(root, rel + "/answers.md")) if os.path.isfile(ans) else []
            types = sorted({t for _, _, t in heads if t})
            level = "Archived" if archived else "Reference"
            out.append("folder: %s/ | %s | %s | types: %s" % (rel, day or "-", level,
                                                             "; ".join(types) if types else "none"))
            if qtype is None:
                continue
            untyped = not types
            for n, head, t in heads:
                if untyped or (t or "").lower() == qtype.lower():
                    tag = "sent before" if archived else "untyped" if untyped else "answer"
                    out.append("%s: %s/answers.md:%d | %s | %s | %s" % (tag, rel, n, day or "-", level, head))
                    if tag != "sent before" and day and day not in dates:
                        dates.append(day)
        for n, line in enumerate(app_lines, 1):
            if want in logfiles.norm(line):
                found = True
                out.append("applications.md:%d: %s" % (n, line.strip()))
        if not found:
            out.append("none: no application folder or applications.md line names %s" % company)
        for day in dates:
            out += since_lines(root, day)
    return out


# ---- start ----

def fallback(root):
    texs = sorted(os.path.basename(p) for p in logfiles.glob_under(os.path.join(root, "sources", "resumes"), "*.tex"))
    pool = [t for t in texs if t[:-4].endswith("-main")] or texs
    if not pool:
        return BLANK
    dated = [t for t in pool if DAY.match(t)]
    if dated:
        newest = max(t[:10] for t in dated)
        pool = [t for t in dated if t[:10] == newest]
    if len(pool) > 1:
        return "tie: " + ", ".join("sources/resumes/" + t for t in pool)
    return "sources/resumes/" + pool[0]


def family_problem(root, family, tier):
    """Why --family and --tier do not fit direction.md's Target roles, or None."""
    if (family is None) != (tier is None):
        return "start takes --family and --tier together"
    tiers = fit.ranks(root)
    if not logfiles.is_target_name(family):
        return "--family is a target name, lowercase: %r" % family
    if not tiers and (family != "general" or tier != "none"):
        return "direction.md's Target roles are empty: --family general --tier none"
    if tiers and family == "general":
        return "--family general is only for a Log with no Target roles: name the posting's role family"
    if tier == "none":
        return None
    problem = fit.tier_problem(int(tier), tiers) if tier.isdigit() and int(tier) else "must be a whole number from 1"
    return problem and "--tier is the role's place in direction.md's Target roles, or none: %s" % problem


def cmd_start(root, name, source, replace, family=None, tier=None):
    if source is None:
        if name or family or tier:
            raise AppError("start --name, --family and --tier take --from <target or file>")
        ts = logfiles.targets(root)
        out = ["target: %s | outputs/resumes/%s.tex" % (t, t) for t in ts] or ["targets: none"]
        return out + ["fallback: %s" % fallback(root)]
    if not logfiles.is_target_name(name):
        raise AppError("start --from takes --name <name>, the name `name` printed")
    if family is not None or tier is not None:
        problem = family_problem(root, family, tier)
        if problem:
            raise AppError(problem)
    src = "outputs/resumes/%s.tex" % source if source in logfiles.targets(root) else rel_of(root, source)
    if src == EXAMPLE:
        raise AppError("never copy the example resume (%s): copy a target, a source resume or %s" % (EXAMPLE, BLANK))
    text = read(root, src)
    dest = ".build/drafts/%s/resume.tex" % name
    if os.path.exists(at(root, dest)) and not replace and read(root, dest).replace("\r\n", "\n") != text.replace("\r\n", "\n"):
        return ["kept: %s holds another text (this run's edits?): nothing copied; --replace starts over from %s"
                % (dest, src)], 1
    os.makedirs(os.path.dirname(at(root, dest)), exist_ok=True)
    shutil.copyfile(at(root, src), at(root, dest))
    out = ["copied: %s -> %s" % (src, dest)]
    if family is not None:
        logfiles.write_text(at(root, logfiles.START_RECORD % name), logfiles.start_record_text(src, family, tier))
        out.append("recorded: " + logfiles.START_RECORD % name)
    return out


# ---- save ----

def committed_bytes(root, rel):
    return logfiles.git_blob(root, "HEAD", rel)


def same_bytes(a, b):
    return a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n")


def cmd_save(root, application, target):
    if (application is None) == (target is None):
        raise AppError("save takes --application <name> or --target <target>")
    name = application or target
    if logfiles.ascii_slug(name) != name and not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[0-9a-z-]+", name):
        raise AppError("not a name `name` prints: %s" % name)
    draft = ".build/drafts/%s" % name
    missing = [f for f in ("resume.tex", "resume.pdf") if not os.path.isfile(at(root, draft + "/" + f))]
    if missing:
        return ["refused: %s has no %s: build it with tools/resume.py first" % (draft, " or ".join(missing))], 1
    if application:
        dest = "%s/%s" % (APPLICATIONS, name)
        pairs = [("resume.tex", dest + "/resume.tex"), ("resume.pdf", dest + "/resume.pdf")]
        if os.path.isfile(at(root, draft + "/posting.md")) and not os.path.exists(at(root, dest + "/posting.md")):
            pairs.append(("posting.md", dest + "/posting.md"))
        for f, to in pairs[:2]:
            old = committed_bytes(root, to)
            with open(at(root, draft + "/" + f), "rb") as fh:
                new = fh.read()
            if old is not None and not same_bytes(old, new):
                return ["refused: %s is committed with other content: the folder was sent and is frozen; a later"
                        " version is a new application (`name`) or a target" % to], 1
    else:
        pairs = [("resume.tex", "outputs/resumes/%s.tex" % name), ("resume.pdf", "outputs/resumes/%s.pdf" % name)]
    out = []
    for f, to in pairs:
        os.makedirs(os.path.dirname(at(root, to)), exist_ok=True)
        shutil.copyfile(at(root, draft + "/" + f), at(root, to))
        out.append("copied: %s/%s -> %s" % (draft, f, to))
    return out


# ---- level ----

def saved_kind(root, rel):
    """'application', 'target' or 'report' for a saved output's path; AppError for anything else."""
    if check_save.APPLICATION.match(rel):
        if not os.path.isdir(at(root, rel)):
            raise AppError("no such application folder: %s" % rel)
        return "application"
    if check_save.TARGET.match(rel):
        return "target"
    if check_save.REPORT_NAME.match(rel):
        return "report"
    raise AppError("not a saved output (outputs/applications/<folder>, outputs/resumes/<target>.md or"
                   " outputs/reports/<YYYY-MM-DD>-<slug>.md): %s" % rel)


def is_archived(root, rel, kind):
    if kind == "application":
        return logfiles.is_archived_folder(root, rel)
    if kind == "report":
        return check_save.report_marks(read(root, rel))[1]
    return False


def committed(root, rel):
    """Whether any commit touched rel (False outside a git repository)."""
    try:
        return bool(git(root, "log", "-1", "--format=%h", "--", rel).strip())
    except AppError:
        return False


def first_subject(root, rel):
    try:
        subjects = git(root, "log", "--format=%s", "--", rel).splitlines()
    except AppError:
        return None
    for subject in reversed(subjects):   # oldest first
        m = check_save.parse_write_subject(subject)
        if m:
            return check_save.write_subject(*m)
    return None


def drop_phrasings(root, rel):
    """Delete each Past phrasings line citing rel, in every entry; (lines, files changed)."""
    out, changed = [], []
    for erel in entries.entry_paths(root):
        path = at(root, erel)
        bom, lines = entries.read_lines(path)
        bounds = entries.section_bounds(lines, "Past phrasings")
        if not bounds:
            continue
        bare = dict(entries.lines_of("".join(lines)))   # a line inside an HTML comment is no phrasing
        gone = [i for i in range(bounds[0] + 1, bounds[1])
                if (lambda m: m and check_save.cites(m.group(3), rel))(entries.PHRASING_PARTS.fullmatch(bare.get(i + 1, "").strip()))]
        if gone:
            for i in gone:
                out.append("removed: %s:%d: %s" % (erel, i + 1, lines[i].strip()))
            entries.write_lines(path, bom, [l for i, l in enumerate(lines) if i not in gone])
            changed.append(erel)
    return out, changed


def captured(fn, *args):
    """fn's return value and the lines it printed."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, [l for l in buf.getvalue().splitlines() if l.strip()]


def drop_pointers(root, rel):
    if not os.path.isfile(os.path.join(root, "stories.md")):
        return [], []
    _, rows = entries.answer_rows(entries.StoriesFile(root))
    out = []
    for _, row in rows:
        if any(entries.under(p[2], rel) for p in row.pointers):
            out += [l for l in captured(entries.cmd_answer_set, root, row.type, None, rel, True)[1]
                    if l.startswith("removed:")]   # a per-company row keeps none, and says so
    return out, (["stories.md"] if out else [])


def misnamed_fix(rel, name):
    return "rename it with `git mv %s/%s %s/archived.md`, or delete it when archived.md is there too" % (rel, name, rel)


def cmd_level(root, saved, level, day):
    rel = rel_of(root, saved)
    kind = saved_kind(root, rel)
    if kind == "target":
        raise AppError("a target has no level: it is overwritten in place (write › Save levels)")
    if kind == "report" and check_save.report_marks(read(root, rel))[0] != "resume bullets":
        raise AppError("only a `Kind: resume bullets` report has a level: %s" % rel)
    want = level == "archived"
    misnamed = logfiles.archived_misnamed(root, rel) if kind == "application" else []
    if misnamed:   # a case-insensitive disk would keep that name for a new archived.md, and git too
        return ["refused: %s/%s is no Archived marker (its name is archived.md): %s, then run this again"
                % (rel, misnamed[0], misnamed_fix(rel, misnamed[0]))], 1
    if is_archived(root, rel, kind) == want:
        return ["unchanged: %s is already %s" % (rel, "Archived" if want else "Reference")]
    marker = "Archived (user, %s)" % day
    out, files = [], []
    if kind == "application":
        path = at(root, rel + "/archived.md")
        if want:
            logfiles.write_text(path, marker + "\n")
        else:
            os.remove(path)
        out.append("%s: %s/archived.md" % ("wrote" if want else "deleted", rel))
        files.append(rel + "/archived.md")
    else:
        bom, lines = entries.read_lines(at(root, rel))
        if want:
            k = next(i for i, l in enumerate(lines) if re.match(r"\s*Kind:", l))
            lines.insert(k + 1, marker + (entries.ends(lines[k]) or entries.line_end(lines)))
        else:
            lines = [l for l in lines if not check_save.ARCHIVED.fullmatch(l.strip())]
        entries.write_lines(at(root, rel), bom, lines)
        out.append("%s: %s: %s" % ("wrote" if want else "deleted", rel, marker if want else "the Archived line"))
        files.append(rel)
    if want:
        gone, changed = drop_phrasings(root, rel)
        ptrs, stories = drop_pointers(root, rel)
        out += gone + ptrs
        files += changed + stories
    else:
        out.append("feed: %s -I %s phrasings %s --angle <angle> <entry>... --root %s"
                   " (the angle step 5 picks for its role; then --add as write step 10's Feed later runs says)"
                   % (logfiles.python_cmd(), logfiles.shell_arg(os.path.abspath(__file__)), rel, logfiles.shell_arg(root)))
        ans = rel + "/answers.md" if kind == "application" else rel
        if os.path.isfile(at(root, ans)):
            for n, head, t in typed_answers(read(root, ans)):
                if t:
                    out.append("answer: %s | %s" % (t, ans))
    if not committed(root, rel):   # an Archived save's marker, before the save's own commit
        return out + ["not committed: %s has no commit yet: the save's own commit takes the marker"
                      " (write step 10's Save and commit)" % rel]
    subject = first_subject(root, rel) or check_save.write_subject(*(
        (os.path.basename(rel)[:-3], "resume bullets") if kind == "report"
        else (os.path.basename(rel), "application")))
    return out + ["files: %s" % " ".join(files), "commit: %s to %s" % (subject, "Archived" if want else "Reference")]


# ---- sent ----

def owner_repo(root):
    p = logfiles.git_run(root, "remote", "get-url", "origin")
    m = GITHUB.match(p.stdout.strip()) if p.returncode == 0 else None
    return m.group(1) if m else None


def cell(root, target, full):
    repo = owner_repo(root)
    if not repo:
        return full[:7]
    prefix = git(root, "rev-parse", "--show-prefix").strip()   # the Log's folder in the repo, when it is below its top
    return "[%s @ %s](https://github.com/%s/blob/%s/%soutputs/resumes/%s.pdf)" % (target, full[:7], repo, full, prefix, target)


def local_when(text):
    """(YYYY-MM-DD, time or None) of a --before value in this machine's time zone. A value with a zone
    (`Z`, `+05:30`, `-0800`: an export's timestamp) is converted, its time given as HH:MM:SS; one
    without is taken as local already."""
    m = WHEN.fullmatch(text.strip())
    if not m:
        raise AppError("--before takes YYYY-MM-DD, YYYY-MM-DD HH:MM, or a time with its zone"
                       " (2025-10-02T06:30:00Z, ...+05:30): %s" % text)
    day, time, zone = m.groups()
    h, mi, sec = ([int(x) for x in time.split(":")] + [0])[:3] if time else (0, 0, 0)
    try:
        dt = datetime.datetime.fromisoformat(day).replace(hour=h, minute=mi, second=sec)
        if zone:
            dt = logfiles.local_time("%sT%02d:%02d:%02d%s" % (day, h, mi, sec, zone))
    except ValueError as e:
        raise AppError("--before is not a real date and time: %s (%s)" % (text, e))
    if not zone:
        return day, time
    return dt.date().isoformat(), dt.strftime("%H:%M:%S")


def is_binary(blob):
    """An imported .pdf or .docx, which sent-show and the diffs do not print."""
    return b"\0" in blob or blob.startswith((b"%PDF", b"PK\x03\x04"))


def line_diff(root, a, b, label=""):
    """`<a> -> <b>: <n> line(s) differ`, then `- <line>` / `+ <line>` per changed line, for two
    versions (`<hash>:<path>`) or two working-tree files; a non-text file gives one line."""
    def text(ref):
        m = HASH_PATH.fullmatch(ref)
        if m:
            blob = logfiles.git_blob(root, m.group(1), m.group(2))
        else:
            with open(at(root, ref), "rb") as f:
                blob = f.read()
        return None if blob is None or is_binary(blob) else blob.decode("utf-8", "replace").splitlines()
    path_of = lambda ref: HASH_PATH.fullmatch(ref).group(2) if HASH_PATH.fullmatch(ref) else ref
    head = "%s%s -> %s" % (label, path_of(a), path_of(b))
    old, new = text(a), text(b)
    if old is None or new is None:
        return ["%s: not text" % head]
    changed, n = [], 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag != "equal":
            n += max(i2 - i1, j2 - j1)
            changed += ["- " + x for x in old[i1:i2]] + ["+ " + x for x in new[j1:j2]]
    if not n:
        return ["%s: identical" % head]
    return ["%s: %s %s" % (head, logfiles.plural(n, "line"), "differs" if n == 1 else "differ")] + changed


def cmd_sent_candidates(root, before, limit):
    day, _ = local_when(before)
    out = ["before: %s" % day + (" (%s in this machine's time zone)" % before.strip() if ZONE.search(before.strip()) else "")]
    firsts = {}
    saved_on = None
    for line in git(root, "log", "--before=%s 23:59:59" % day, "--format=@%cd", "--date=format-local:%Y-%m-%d",
                    "--name-only", "--", "outputs/resumes/*.tex").splitlines():
        if line.startswith("@"):
            saved_on = line[1:]
        elif line.strip():
            target = os.path.basename(line.strip())[:-4]
            if logfiles.is_target_name(target):
                firsts[target] = saved_on   # newest first: the last one seen is the first save
    out.append("targets saved by %s: %s" % (day, ", ".join("%s (%s)" % kv for kv in sorted(firsts.items())))
               if firsts else "targets: none saved by %s" % day)
    files = []
    for path in logfiles.glob_under(os.path.join(root, "sources", "resumes"), "*"):
        base = os.path.basename(path)
        m = DAY.match(base)
        if os.path.isfile(path) and m and m.group(0) <= day:
            files.append((m.group(0), base))
    files.sort(reverse=True)
    if not files:
        return out + ["none: no file in sources/resumes/ dated on or before %s: ask the user which file went, or"
                      " import it first (import mode)" % day], 1
    shown, refs = files[:max(limit, 1)], []
    for date, base in shown:
        rel = "sources/resumes/" + base
        full = git(root, "log", "-1", "--format=%H", "--", rel).strip()
        if not full or git(root, "status", "--porcelain", "--", rel).strip():
            out.append("candidate: %s | %s | uncommitted: commit it first" % (rel, date))
            refs.append(rel)
        else:
            out.append("candidate: %s:%s | %s" % (full, rel, date))
            refs.append("%s:%s" % (full, rel))
    if len(files) > len(shown):
        out.append("older: %d more (--limit %d shows them)" % (len(files) - len(shown), len(files)))
    for newer, older in zip(refs, refs[1:]):
        out += line_diff(root, older, newer, "diff: ")
    out.append("next: show the user each candidate and diff, and ask which went (an imported file may be an"
               " older copy than they recall); sure of one: sent-show <its version> --record <folder>; one of"
               " several: sent-show <version> <version>... --record <folder> --known \"<what the user knows>\"")
    return out


def sent_file(root, rel):
    """(versions, known) of a sent-version.md naming several candidates; None for the one-version form."""
    lines = read(root, rel + "/sent-version.md").splitlines()
    versions = []
    for line in lines:
        if not HASH_PATH.fullmatch(line.strip()):
            break
        versions.append(line.strip())
    if len(versions) < 2:
        return None
    known = next((l[len("Known: "):].strip() for l in lines if l.startswith("Known: ")), None)
    return versions, known


def record(root, folder, version, known=None, day=None):
    """Write <folder>/sent-version.md: one version, or (several, with known) the candidates."""
    rel = rel_of(root, folder)
    if not check_save.APPLICATION.match(rel):
        raise AppError("--record takes an application folder, outputs/applications/<folder>: %s" % folder)
    path = at(root, rel + "/sent-version.md")
    several = isinstance(version, list)
    if os.path.exists(path):
        have = sent_file(root, rel)
        same = sorted(have[0]) == sorted(version) if several and have else read(root, rel + "/sent-version.md").strip() == version
        if not same:
            return ["refused: %s/sent-version.md names another version: %s"
                    % (rel, " ".join(have[0]) if have else read(root, rel + "/sent-version.md").strip())], 1
        if several:
            return ["unchanged: %s/sent-version.md names these candidates; its Known: line stays: %s" % (rel, have[1])]
    os.makedirs(at(root, rel), exist_ok=True)
    if not several:
        logfiles.write_text(path, version + "\n")
        return ["recorded: %s/sent-version.md: %s" % (rel, version)]
    known = one_line(known)
    if not re.search(r"\(user, \d{4}-\d{2}-\d{2}\)$", known):
        known += " (user, %s)" % day
    diffs = []
    for a, b in zip(version, version[1:]):
        diffs += line_diff(root, a, b)   # no label: the file's `Differ:` heading names them
    logfiles.write_text(path, "\n".join(version) + "\n\nKnown: %s\n\nDiffer:\n```diff\n%s\n```\n" % (known, "\n".join(diffs)))
    return ["recorded: %s/sent-version.md: %d candidates" % (rel, len(version))]


def cmd_sent(root, target, before, folder):
    if not logfiles.is_target_name(target):
        raise AppError("not a target name: %r" % target)
    spec = "outputs/resumes/%s.*" % target
    out = []
    if before is None:
        dirty = git(root, "status", "--porcelain", "--", spec).strip()
        if dirty:
            return ["refused: %s has uncommitted changes: commit them first (write step 10), then run it again" % spec], 1
        full = git(root, "log", "-1", "--format=%H", "--", spec).strip()
    else:
        day, time = local_when(before)
        until = "%s %s" % (day, time or "23:59:59")
        full = git(root, "log", "-1", "--format=%H", "--before=%s" % until, "--", spec).strip()
        that_day = git(root, "log", "--format=%H", "--since=%s 00:00:00" % day,
                       "--until=%s 23:59:59" % day, "--", spec).split()
        out.append("changed that day: %s" % logfiles.plural(len(that_day), "commit"))
    if not full:
        return out + ["none: no commit touched %s%s" % (spec, " before %s" % before if before else "")], 1
    version = "%s:outputs/resumes/%s.tex" % (full, target)
    out = ["version: %s" % version, "cell: %s" % cell(root, target, full)] + out
    if folder:
        res = record(root, folder, version)
        if isinstance(res, tuple):
            return out + res[0], 1
        out += res
    return out


def resolve(root, ref, target):
    """(full hash, path) a sent-version reference names; path None for a bare hash with no target."""
    ref = ref.strip()
    if os.path.isdir(at(root, ref)) and os.path.isfile(at(root, ref) + "/sent-version.md"):
        ref = read(root, rel_of(root, ref) + "/sent-version.md").strip()
    m = CELL.search(ref)
    url = m.group(1) if m else ref
    link, m = PERMALINK.match(url), HASH_PATH.fullmatch(ref)
    if link or m:
        hashes, path = [(link or m).group(1)], (link or m).group(2)
        if link:   # a permalink's path is from the repository's top level, which may sit above the Log
            prefix = git(root, "rev-parse", "--show-prefix").strip()
            path = path[len(prefix):] if prefix and path.startswith(prefix) else path
    elif BARE_HASH.search(ref):   # a bare hash, alone or in a row's words (among other numbers)
        hashes, path = [h.group(0) for h in BARE_HASH.finditer(ref)], ("outputs/resumes/%s.tex" % target if target else None)
        if path is None:
            raise AppError("a bare hash names no file: add --target <target>")
    else:
        raise AppError("not a sent version (a cell, a permalink, <hash>:<path>, a folder with sent-version.md,"
                       " or a hash with --target): %s" % ref)
    for h in hashes:
        p = logfiles.git_run(root, "rev-parse", "--verify", "--quiet", h + "^{commit}")
        if p.returncode == 0 and p.stdout.strip():
            full = p.stdout.strip()
            break
    else:
        raise AppError("no such commit in this clone: %s (git fetch, then run it again)" % ", ".join(hashes))
    if not path.startswith("outputs/"):   # an imported resume (sources/resumes/) has only the file it was imported as
        return full, path
    return full, re.sub(r"\.pdf$", ".tex", path)


def shown(blob, version):
    """A version's text as sent-show prints it; a binary file (an imported .pdf) as one line."""
    if is_binary(blob):
        return "binary: %d bytes: open it with sent-show %s --out <file>" % (len(blob), version)
    return blob.decode("utf-8", "replace").rstrip("\n")


def cmd_sent_show(root, refs, target, dest, folder, known, day):
    known_line = None
    if len(refs) == 1 and os.path.isdir(at(root, refs[0])) and os.path.isfile(at(root, refs[0]) + "/sent-version.md"):
        several = sent_file(root, rel_of(root, refs[0]))
        if several:
            refs, known_line = several
    if len(refs) == 1:
        return sent_show_one(root, refs[0], target, dest, folder)
    if dest:
        raise AppError("--out takes one version; give one ref")
    if folder and not known_line and not one_line(known):
        raise AppError("--record with several versions takes --known \"<what the user knows of which went>\"")
    versions = []
    for ref in refs:
        full, path = resolve(root, ref, target)
        versions.append("%s:%s" % (full, path))
    out = ["candidates: %d" % len(versions)] + (["known: %s" % known_line] if known_line else [])
    for v in versions:
        full, path = v.split(":", 1)
        blob = logfiles.git_blob(root, full, path)
        if blob is None:
            return out + ["missing: %s at %s" % (path, full[:7])], 1
        out += ["version: %s" % v, shown(blob, v)]
    for a, b in zip(versions, versions[1:]):
        out += line_diff(root, a, b, "differ: ")
    if folder:
        res = record(root, folder, versions, one_line(known) or known_line, day)
        if isinstance(res, tuple):
            return out + res[0], 1
        out += res
    return out


def sent_show_one(root, ref, target, dest, folder):
    full, path = resolve(root, ref, target)
    blob = logfiles.git_blob(root, full, path)
    if blob is None:
        touched = git(root, "show", "--stat", "--name-only", "--format=", full).split()
        return ["missing: %s at %s" % (path, full[:7])] + ["touched: %s" % t for t in touched], 1
    out = ["version: %s:%s" % (full, path)]
    if dest:
        try:
            with open(dest, "wb") as f:
                f.write(blob)
        except OSError as e:
            raise AppError("cannot write %s: %s" % (dest, e))
        out.append("wrote: %s" % dest)
    else:
        out.append(shown(blob, "%s:%s" % (full, path)))
    if folder:
        res = record(root, folder, "%s:%s" % (full, path))
        if isinstance(res, tuple):
            return out + res[0], 1
        out += res
    return out


# ---- stale ----

def stale(root, target):
    """How far a Target version has fallen behind the Log since its last save, as two lists; it
    judges nothing. The save is the last `write(` commit of outputs/resumes/<target>.* (else its last
    commit: an upgrade's rewrite saves nothing). A dict: `saved` (full hash, date, subject),
    `changed` [(entry, [(short hash, date, subject)] since the save, uncommitted)] for each entry its
    provenance cites (entries.cited_entries) that changed, `new` [(entry, title, uncommitted)] for
    each entry the save's commit did not hold, `unresolved` [(line, cell)] for each provenance row
    naming no entry, `provenance` False when the save's commit has no <target>.md to read, and
    `cites` False when that <target>.md is empty or none of its rows names an entry. None when the
    target is not saved (no commit touched it, or its files are gone)."""
    if not logfiles.is_target_name(target):
        raise AppError("not a target name: %r" % target)
    if not any(os.path.isfile(at(root, "outputs/resumes/%s.%s" % (target, x))) for x in ("md", "tex")):
        return None
    saves = [l.split("|", 2) for l in git(root, "log", "--format=%H|%cd|%s", "--date=short", "--",
                                          "outputs/resumes/%s.*" % target).splitlines() if l]
    if not saves:
        return None
    full, day, subject = next((s for s in saves if s[2].startswith("write(")), saves[0])
    blob = logfiles.git_blob(root, full, "outputs/resumes/%s.md" % target)
    log = entries.load(root)
    def paths(cmd, *args):   # -z: each name as it is, spaces and non-ASCII letters included
        return set(git(root, cmd, "-z", *args, "--", "entries/").split("\0")) - {""}
    held, tracked = paths("ls-tree", "-r", "--name-only", full), paths("ls-files")
    new = [(e.path, one_line(entries.one_value(e.fields.get("title"))) or e.slug, e.path not in tracked)
           for e in log if e.path not in held]
    cited, unresolved = entries.cited_entries(log, blob.decode("utf-8", "replace")) if blob else (set(), [])
    changed = []
    for path in sorted(cited - {n[0] for n in new}):
        try:
            commits, edited = entries.entry_changes(root, path, ["%s..HEAD" % full]) or ([], False)
        except logfiles.LogError as e:
            raise AppError(str(e))
        if commits or edited:
            changed.append((path, commits, edited))
    return {"saved": (full, day, subject), "changed": changed, "new": new, "unresolved": unresolved,
            "provenance": blob is not None, "cites": bool(cited)}


def cmd_stale(root, target):
    res = stale(root, target)
    if res is None:
        return ["none: no saved target %s (outputs/resumes/%s.* is missing or never committed)" % (target, target)], 1
    full, day, subject = res["saved"]
    out = ["saved: %s %s %s" % (full[:7], day, subject), "cited changed: %d" % len(res["changed"])]
    for path, log, dirty in res["changed"]:
        what = ["%s, last %s %s" % (logfiles.plural(len(log), "commit"), log[0][1], log[0][2])] if log else []
        out.append("  %s: %s" % (path, ", ".join(what + (["uncommitted changes"] if dirty else []))))
    out.append("new entries: %d" % len(res["new"]))
    out += ["  %s: %s%s" % (path, title, " (uncommitted)" if untracked else "") for path, title, untracked in res["new"]]
    out += ["unresolved: %s: %s" % (n, cell) for n, cell in res["unresolved"]]
    if not res["provenance"]:
        out.append("no provenance: the save's commit has no outputs/resumes/%s.md, so no cited entry was checked" % target)
    elif not res["cites"]:
        out.append("no provenance: the save's outputs/resumes/%s.md cites no entry, so no cited entry was checked" % target)
    verdict = stale_verdict(res)
    return out + ["verdict: %s" % verdict], 0 if verdict == "fresh" else 1


def stale_verdict(res):
    """stale()'s lists as one word: `stale` when an entry it cites changed or one was added since,
    else `not compared` when its provenance cites no entry, else `fresh`."""
    if res["changed"] or res["new"]:
        return "stale"
    return "fresh" if res["cites"] else "not compared"


# ---- risks ----

def cmd_risks(root, saved):
    rel = rel_of(root, saved)
    kind = saved_kind(root, rel)
    sent = kind == "application" and os.path.isfile(at(root, rel + "/sent-version.md"))
    several = sent_file(root, rel) if sent else None   # (versions, known) when it names several candidates
    if kind == "application":
        if os.path.isfile(at(root, rel + "/provenance.md")):
            where, text = rel + "/provenance.md", read(root, rel + "/provenance.md")
        elif sent:
            refs = several[0] if several else [rel]
            where, text = rel + "/sent-version.md", ""
            for ref in refs:   # the first candidate with the section (an imported resume has none)
                full, path = resolve(root, ref, None)
                found = (logfiles.git_blob(root, full, os.path.splitext(path)[0] + ".md") or b"").decode("utf-8", "replace")
                if (logfiles.section(found, RISKS) or "").strip():
                    where, text = "%s:%s" % (full, os.path.splitext(path)[0] + ".md"), found
                    break
                if not several:
                    where = "%s:%s" % (full, os.path.splitext(path)[0] + ".md")
        else:
            where, text = rel, ""
    else:
        where, text = rel, read(root, rel)
    body = logfiles.section(text, RISKS)
    if body is None or not body.strip():
        out = ["risks: none (saved before the section existed): find the risks from its claims (%s)" % where]
    else:
        out = ["risks: %s" % where, body.strip("\n")]
    return out + (candidate_lines(root, *several) if several else [])


def candidate_lines(root, versions, known):
    """Each line that is not in every one of several sent candidates, with the versions that hold it."""
    out = ["candidates: %d: the brief covers each `line` below, with the versions that hold it" % len(versions)]
    out += ["known: %s" % known] if known else []
    texts = {}
    for n, ref in enumerate(versions, 1):
        full, path = resolve(root, ref, None)
        version = "%s:%s" % (full, path)
        out.append("version %d: %s" % (n, version))
        blob = logfiles.git_blob(root, full, path)
        if blob is None:
            out.append("missing: version %d: %s at %s" % (n, path, full[:7]))
        elif is_binary(blob):
            out.append("not text: version %d: read its claims from sent-show %s --out <file>" % (n, version))
        else:
            texts[n] = blob.decode("utf-8", "replace").splitlines()
    if len(texts) < 2:
        return out + ["differ: not compared: fewer than two versions are text"]
    held, order = {}, []
    for n, lines in texts.items():
        for line in lines:
            if line.strip() and n not in held.setdefault(line, []):
                order += [line] if not held[line] else []
                held[line].append(n)
    differ = [l for l in order if len(held[l]) < len(texts)]
    out.append("differ: %s not in every version" % logfiles.plural(len(differ), "line") if differ
               else "differ: none: the versions hold the same lines")
    return out + ["line (%s %s): %s" % ("version" if len(held[l]) == 1 else "versions",
                                         ", ".join(map(str, held[l])), l) for l in differ]


# ---- phrasings ----

def wording(item):
    """A .tex bullet as a Past phrasings wording: bold kept as **x**, the rest as the reader sees it."""
    return writing_lint.tex_plain(re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", item))


def list_items(text):
    """The list items above a Markdown text's first table, as bullets (check_save reads the same)."""
    return [one_line(re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", l)) for l in check_save.above_table(text)
            if re.match(r"\s*(?:[-*+]|\d+\.)\s+\S", l)]


def approved_bullets(root, rel, day):
    """([wording], citation or None, Archived?) for a saved output or a draft .tex."""
    if rel.endswith(".tex"):
        items = [i for _, i in logfiles.tex_bullets(read(root, rel))]
        return [wording(i) for i in items], None, False
    if rel.startswith(".build/") and rel.endswith(".md"):   # a bullets draft, before its Kind: line
        return list_items(read(root, rel)), None, False
    kind = saved_kind(root, rel)
    if kind == "application":
        tex, cite = rel + "/resume.tex", rel
    elif kind == "target":
        tex, cite = rel[:-3] + ".tex", "%s, %s" % (rel[:-3] + ".tex", day)
    else:
        text = read(root, rel)
        mark = check_save.report_marks(text)
        if mark[0] != "resume bullets":
            raise AppError("%s is no `Kind: resume bullets` report: only those feed Past phrasings" % rel)
        return list_items(text), rel, mark[1]
    items = [i for _, i in logfiles.tex_bullets(read(root, tex))] if os.path.isfile(at(root, tex)) else []
    return [wording(i) for i in items], cite, is_archived(root, rel, kind)


def entry_lines(root, erel, angle):
    """[(line number, wording, citation, the line)] of an entry's Past phrasings for the angle."""
    path = at(root, erel)
    if not os.path.isfile(path):
        raise AppError("no such entry: %s" % erel)
    _, lines = entries.read_lines(path)
    bounds = entries.section_bounds(lines, "Past phrasings")
    out, bare = [], dict(entries.lines_of("".join(lines)))   # a line inside an HTML comment is no phrasing
    for i in range(bounds[0] + 1, bounds[1]) if bounds else []:
        m = entries.PHRASING_PARTS.fullmatch(bare.get(i + 1, "").strip())
        if m and m.group(1).lower() == angle:
            out.append((i + 1, m.group(2), m.group(3), lines[i].strip()))
    return out


def rank_key(line):
    """consolidate step 2's order, best first: a wording from an output above an imported one, then
    the newer above the older (the first YYYY-MM-DD in its citation)."""
    _, _, citation, _ = line
    d = DAY.search(citation)
    return (bool(entries.OUTPUT_PATH.search(citation) or re.match(r"(applications|resumes|reports)/", citation)),
            d.group(0) if d else "")


def cmd_phrasings(root, saved, angle, names, adds, caps, day):
    angle = angle.lower()
    if not entries.ANGLE.fullmatch(angle):
        raise AppError("--angle is a target name like `general`: %s" % angle)
    erels = [rel_of(root, e) for e in names]
    if caps:
        return cap(root, angle, caps)
    rel = rel_of(root, saved)
    bullets, cite, archived = approved_bullets(root, rel, day)
    if archived:
        return ["archived: %s is saved Archived and feeds nothing (write › Save levels)" % rel]
    if adds:
        if cite is None:
            raise AppError("--add takes the saved output, not a draft: its citation names the save")
        out, worst = [], 0
        for a in adds:
            m = re.fullmatch(r"(\d+)=([^,]+)(?:,(distinct|replace=(\d+)))?", a)
            if not m or not 1 <= int(m.group(1)) <= len(bullets):
                raise AppError("--add takes <bullet n>=<entry>[,distinct|,replace=<line>], n from 1 to %d: %s"
                               % (len(bullets), a))
            code, lines = captured(entries.cmd_phrasing_add, root, rel_of(root, m.group(2)), bullets[int(m.group(1)) - 1],
                                   angle, cite, m.group(3) == "distinct", int(m.group(4)) if m.group(4) else None)
            out += lines
            worst = max(worst, code)
        out += now_lines(root, sorted({rel_of(root, re.match(r"\d+=([^,]+)", a).group(1)) for a in adds}), angle)
        return (out, worst) if worst else out
    out, add = [], []
    kept = {e: entry_lines(root, e, angle) for e in erels}
    held = {e: content_words(read(root, e)) for e in erels}
    older = {e: older_lines(root, e) for e in erels}
    for n, b in enumerate(bullets, 1):
        out.append("bullet %d: %s" % (n, b))
        same = None
        for e in erels:
            best = max(kept[e], key=lambda k: entries.similar((angle, k[1]), (angle, b)), default=None)
            if best is None:
                out.append("  %s: none for %s" % (e, angle))
            else:
                ratio = entries.similar((angle, best[1]), (angle, b))
                out.append("  %s: %.2f %d: %s" % (e, ratio, best[0], best[3]))
                if ratio >= entries.SIMILAR and (same is None or ratio > same[0]):
                    same = ratio, e, best[0]
        own = content_words(b)
        share = {e: len(own & held[e]) / len(own) for e in erels} if own else {}
        owner = max(erels, key=lambda e: share[e], default=None) if share else None
        if same:
            out.append("  same: %s:%d: adds no line" % same[1:])
        elif owner is None or len(own & set().union(*held.values())) / len(own) < OWNS:
            out.append("  none: the entries given hold less than half its words: adds no line")
        elif older[owner]:
            out.append("  older form: %s: %d Past phrasings lines in a form this command cannot read: adds no line "
                       "until they are in the template's form" % (owner, older[owner]))
        else:
            out.append("  add: %s" % owner)
            add.append("--add %d=%s" % (n, owner))
            claim = [k[0] for k in kept[owner] if entries.similar((angle, k[1]), (angle, b)) >= CLAIM]
            if len(claim) >= check_save.PHRASING_CAP:
                out.append("  at cap: %s: %s: this claim keeps %d wordings for %s; adding this one drops one at the cap"
                           % (owner, ",".join(map(str, claim)), check_save.PHRASING_CAP, angle))
    out.append("cite: %s" % (cite or "(the saved output: run this on it after the save)"))
    out += ["entry: %s: %d lines for %s" % (e, len(kept[e]), angle) for e in erels]
    return out + ["adds: %s" % (" ".join(add) or "none")]


OWNS = 0.5   # the share of a bullet's words the entries given must hold for it to be theirs
CLAIM = 0.6   # a kept wording this close to a bullet (entries.similar) or closer is taken for the same claim
STOP = {"and", "the", "for", "with", "from", "into", "that", "this", "its", "our", "their", "via", "per", "over",
        "under", "across", "using", "used", "was", "were", "are", "has", "had", "have", "than", "then", "each"}


def content_words(text):
    """The words of a text that name something: three letters or more, not a STOP word."""
    return {w.strip(".") for w in entries.words(text) if len(w.strip(".")) >= 3 and w.strip(".") not in STOP}


def older_lines(root, erel):
    """The lines under an entry's ## Past phrasings that are neither in the template's form, nor a
    placeholder (entries.py PLACEHOLDER: `none yet`, `GAP: ...`): the older `**<label>**` form, which
    entry_lines cannot read."""
    _, lines = entries.read_lines(at(root, erel))
    bounds = entries.section_bounds(lines, "Past phrasings")
    bare = dict(entries.lines_of("".join(lines)))
    n = 0
    for i in range(bounds[0] + 1, bounds[1]) if bounds else []:
        line = bare.get(i + 1, "").strip()
        if line and not entries.PHRASING_PARTS.fullmatch(line) and not entries.PLACEHOLDER.fullmatch(line):
            n += 1
    return n


def cap(root, angle, caps):
    out = []
    for c in caps:
        m = re.fullmatch(r"([^=]+)=(\d+(?:,\d+)+)", c)
        if not m:
            raise AppError("--cap takes <entry>=<line>,<line>,...: %s" % c)
        erel, want = rel_of(root, m.group(1)), [int(x) for x in m.group(2).split(",")]
        if len(set(want)) != len(want):
            raise AppError("--cap names a line twice: %s" % c)
        lines = {l[0]: l for l in entry_lines(root, erel, angle)}
        bad = [n for n in want if n not in lines]
        if bad:
            raise AppError("%s:%s is no Past phrasings line for %s" % (erel, ",".join(map(str, bad)), angle))
        if len(want) <= check_save.PHRASING_CAP:
            out.append("kept: %s: %d wordings, within the %d per claim" % (erel, len(want), check_save.PHRASING_CAP))
            continue
        ranked = sorted((lines[n] for n in want), key=rank_key, reverse=True)
        gone = {l[0] for l in ranked[check_save.PHRASING_CAP:]}
        path = at(root, erel)
        bom, raw = entries.read_lines(path)
        for n in sorted(gone):
            out.append("dropped: %s:%d: %s" % (erel, n, raw[n - 1].strip()))
        entries.write_lines(path, bom, [l for i, l in enumerate(raw, 1) if i not in gone])
    return out + now_lines(root, sorted({rel_of(root, c.split("=")[0]) for c in caps}), angle)


def now_lines(root, erels, angle):
    return ["line: %s:%d: %s" % (e, n, line) for e in erels for n, _, _, line in entry_lines(root, e, angle)]


# ---- prep ----

PHASES = ("intake", "research", "align", "pack", "plan", "practise")
STATES = ("done", "open", "user-only", "set aside")
ITEMS = (   # (item, phase, the --with value it needs or None), in phase order
    ("recruiter-mail", "intake", None), ("posting", "intake", None), ("sent-version", "intake", None),
    ("research", "research", None), ("requirement-map", "research", None), ("deep-dives", "research", None),
    ("user-only-facts", "align", None), ("behavioural-leads", "align", None), ("areas", "align", "areas"),
    ("talk", "align", "talk"),
    ("tell-me-about-yourself", "pack", None), ("why-this-company", "pack", None), ("awkward-questions", "pack", None),
    ("logistics", "plan", None), ("effort", "plan", None), ("schedule", "plan", None),
    ("practice", "practise", None), ("mock", "practise", None))
WITH = tuple(need for _, _, need in ITEMS if need)
SLUG = logfiles.SLUG
STAGE = re.compile(SLUG + "$")
PREP = re.compile(r"prep-%s\.md$" % SLUG)
NOTES = "notes.md"   # the folder's statements for this application (SKILL.md › Direction upkeep)
NOTE = "note"   # the Decisions decision of a statement for the whole application
NOT_A_NOTE =re.compile(r"#+(\s|$)|([-*_]\s*){3,}$")   # a notes.md line that is a heading or a rule
PRACTICE = re.compile(r"practice-%s\.md$" % SLUG)
VERDICTS = ("passed", "near", "shaky", "again")
RETEST = ("shaky", "again")
HEARD = ("typed", "recorded", "live")
ATTEMPT = "| date | item | kind | verdict | weak spots | heard |"
TABLES = (   # (section, header row), in file order
    ("Items", "| item | phase | state | where |"),
    ("Decisions", "| # | decision | value | source | backup / note |"),
    ("Schedule", "| date | commitments | plan | estimate |"),
    ("Pages", "| page | built from | link | for |"))


def app_folder(root, folder):
    rel = rel_of(root, folder)
    if not os.path.isdir(at(root, rel)):
        raise AppError("no folder %s" % rel)
    return rel


def cmd_prep_init(root, folder, stage, with_, date, mode_start):
    rel = app_folder(root, folder)
    if not STAGE.match(stage or ""):
        raise AppError("--stage takes a lowercase slug (final, technical-1): %s" % stage)
    extra = [w.strip() for w in (with_ or "").split(",") if w.strip()]
    for w in extra:
        if w not in WITH:
            raise AppError("--with takes %s: %s" % (", ".join(WITH), w))
    try:
        day = "?" if date is None else datetime.date.fromisoformat(date).isoformat()
    except ValueError:
        raise AppError("--date takes YYYY-MM-DD: %s" % date)
    path = "%s/prep-%s.md" % (rel, stage)
    if os.path.exists(at(root, path)):
        return ["refused: %s exists; edit it instead" % path], 1
    out = ["# Prep: %s" % stage, "", "stage: %s" % stage, "interview: %s" % day,
           "mode start: %s" % one_line(mode_start or "?"), "practice log: practice-%s.md" % stage]
    carried = carried_notes(root, rel)   # [(the file carried from, its line, the note)]
    for section, header in TABLES:
        out += ["", "## " + section, "", header, "|" + "---|" * (header.count("|") - 1)]
        if section == "Items":
            out += ["| %s | %s | open | |" % (item, phase) for item, phase, need in ITEMS if need is None or need in extra]
        if section == "Decisions":
            out += [logfiles.md_row([i, NOTE, text, "%s:%d" % (name, line), ""]) for i, (name, line, text) in enumerate(carried, 1)]
    with open(at(root, path), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    counts = collections.Counter(name for name, _, _ in carried)   # in the order first carried
    return ["wrote: %s" % path] + ["carried: %d %s of %s/%s into ## Decisions" % (
        count, "lines" if name == NOTES else "note rows", rel, name) for name, count in counts.items()]


def carried_notes(root, rel):
    """The statements for this application a new prep file starts with, as [(file name, line, text)]:
    the lines of the folder's notes.md, then each `note` row of the folder's prep files' Decisions
    (SKILL.md's Direction upkeep writes it there once the folder has one), in file name order, each
    text once."""
    carried = [(NOTES, n, text) for n, text in folder_notes(root, rel)]
    for name in sorted(n for n in os.listdir(at(root, rel)) if PREP.match(n)):
        for n, cells in parse_prep(read(root, "%s/%s" % (rel, name)))["tables"].get("Decisions", []):
            if len(cells) > 2 and cells[1].lower() == NOTE and cells[2]:
                carried.append((name, n, cells[2]))
    first = {}   # each text -> where it was first found
    for name, n, text in carried:
        first.setdefault(text, (name, n, text))
    return list(first.values())


def folder_notes(root, rel):
    """The statements in <folder>/notes.md (SKILL.md's Direction upkeep writes them there when the
    folder has no prep file) as [(line number, text)]: each line that is not blank, a `#` heading or
    a `---` rule, less a leading `- ` or `* `."""
    path = "%s/%s" % (rel, NOTES)
    if not os.path.isfile(at(root, path)):
        return []
    notes = []
    for n, line in enumerate(read(root, path).splitlines(), 1):
        text = one_line(re.sub(r"^\s*[-*]\s+", "", line))
        if text and not NOT_A_NOTE.match(text):
            notes.append((n, text))
    return notes


def prep_path(root, rel, stage):
    if stage is not None and not STAGE.match(stage):
        raise AppError("--stage takes a lowercase slug (final, technical-1): %s" % stage)
    if stage:
        path = "%s/prep-%s.md" % (rel, stage)
        if not os.path.isfile(at(root, path)):
            raise AppError("no %s (prep-init writes it)" % path)
        return path
    found = sorted(n for n in os.listdir(at(root, rel)) if PREP.match(n))
    if len(found) != 1:
        raise AppError("%s has %s; name one with --stage" % (
            rel, "no prep-<stage>.md (prep-init writes it)" if not found else "several prep files: " + ", ".join(found)))
    return "%s/%s" % (rel, found[0])


def parse_prep(text):
    """A prep file as {"header": {key: value}, "tables": {section: [(line number, [cells])]}}: the
    `key: value` lines above the first `## `, and the rows of each `## <section>`'s table, less its
    header row and divider row, as logfiles.md_tables reads them (cells stripped, `\\|` read as `|`).
    A command that reads another section of the prep file reads it here."""
    header, tables = {}, {}
    for line in text.lstrip("﻿").splitlines():
        h = re.match(r"##[ \t]+(.*)", line)   # logfiles.md_tables' heading form
        if h:
            tables.setdefault(h.group(1).strip(), [])
        elif not tables:
            k, sep, v = line.strip().partition(":")
            if sep and k and not k.startswith("#"):
                header.setdefault(k.strip().lower(), v.strip())
    for table in logfiles.md_tables(text):
        if table.section is not None:
            tables[table.section] += table.rows
    return {"header": header, "tables": tables}


def where_problems(root, rel, where):
    """Why a done row's where fails: a path (the part before #) the folder lacks or that is not in it."""
    out = []
    for part in (p.strip() for p in where.split(",")):
        p = part.split("#", 1)[0].strip()
        if part in ("", "-"):
            continue
        if not p:
            out.append("%s names no file" % part)
        elif os.path.isabs(p) or ".." in p.replace("\\", "/").split("/"):
            out.append("%s is not a path in the folder" % p)
        elif not os.path.exists(at(root, rel + "/" + p)):
            out.append("%s/%s does not exist" % (rel, p))
    return out


def log_file(root, base, cell, within):
    """(the Log path of the file a Pages cell names, relative to base; None and why it fails): a
    path, without `#section`, to a file inside base (the folder, or "" for the Log's root)."""
    norm = cell.replace("\\", "/")
    if not norm or norm == "-" or "#" in norm:
        return None, "%r names no file" % cell
    if os.path.isabs(cell) or norm.startswith("/") or ".." in norm.split("/"):
        return None, "%s is not a path in %s" % (cell, within)
    rel_path = base + "/" + norm if base else norm
    if not os.path.isfile(at(root, rel_path)):
        return None, "%s does not exist" % rel_path
    return rel_path, None


def page_stale(root, page, source):
    """Whether source changed after page was built: source has uncommitted changes and page none, or
    source's last commit is one page's last commit does not contain. False outside a git repository
    or when git cannot tell."""
    try:
        dirty = [bool(git(root, "status", "--porcelain", "--", f).strip()) for f in (source, page)]
        if dirty[0] or dirty[1]:
            return dirty[0] and not dirty[1]
        source_commit, page_commit = (git(root, "log", "-1", "--format=%H", "--", f).strip() for f in (source, page))
        if not source_commit or not page_commit or source_commit == page_commit:
            return False
        return logfiles.git_run(root, "merge-base", "--is-ancestor", source_commit, page_commit).returncode == 1
    except (AppError, logfiles.LogError):
        return False


def stage_of(path):
    return os.path.basename(path)[len("prep-"):-len(".md")]


def after_interview(header, day):
    try:
        return datetime.date.fromisoformat(day) > datetime.date.fromisoformat(header.get("interview", "?"))
    except ValueError:
        return False


def days_left(header, day):
    """Days from <day> to the header's interview date, or None when either is not a date."""
    try:
        return (datetime.date.fromisoformat(header.get("interview", "?")) - datetime.date.fromisoformat(day)).days
    except ValueError:
        return None


def prep_date_lines(header, day):
    lines = ["today: %s" % day]
    raw = header.get("interview", "?")
    left = days_left(header, day)
    if left is None:
        return lines + ["days left: unknown (interview: %s)" % (raw or "?")]
    return lines + ["days left: %d" % left if left >= 0 else "days left: none (the interview was %s)" % raw]


def practice_path(rel, path, prep):
    """The prep file's practice log: its header's `practice log:` file, else practice-<stage>.md."""
    name = prep["header"].get("practice log", "")
    if not PRACTICE.match(name):
        name = "practice-%s.md" % stage_of(path)
    return "%s/%s" % (rel, name)


def practice_rows(root, log):
    """The practice log's attempts as [(line number, [cells])], and a FAIL line per bad row."""
    if not os.path.isfile(at(root, log)):
        return [], []
    rows, problems = parse_prep(read(root, log))["tables"].get("Attempts", []), []
    for n, cells in rows:
        if len(cells) != 6:
            problems.append("FAIL: %s:%d: an attempt row has 6 cells (%s): %d here" % (log, n, ATTEMPT[2:-2].replace(" | ", ", "), len(cells)))
        elif cells[3] not in VERDICTS:
            problems.append("FAIL: %s:%d: %s: unknown verdict %r (%s)" % (log, n, cells[1], cells[3], ", ".join(VERDICTS)))
    return [(n, cells) for n, cells in rows if len(cells) == 6], problems


def cmd_practice_add(root, folder, stage, item, verdict, kind, weak, heard, day):
    rel = app_folder(root, folder)
    path = prep_path(root, rel, stage)
    prep = parse_prep(read(root, path))
    if verdict not in VERDICTS:
        raise AppError("--verdict takes %s: %s" % (", ".join(VERDICTS), verdict))
    if heard is not None and heard not in HEARD:
        raise AppError("--heard takes %s: %s" % (", ".join(HEARD), heard))
    names = {cells[0] for _, cells in prep["tables"].get("Items", []) if cells} | {"story"}
    top, slash, sub = item.partition("/")
    if top not in names or (slash or top == "story") and not sub.strip() or "|" in item:
        raise AppError("--item takes an item of %s, `story/<key>` or `<item>/<sub-item>`: %s" % (path, item))
    log = practice_path(rel, path, prep)
    cells = [day, item, one_line(kind) or "round", verdict, one_line(weak) or "-", heard or "-"]
    row = logfiles.md_row(cells)
    if os.path.exists(at(root, log)):
        lines = read(root, log).splitlines()
        heads = [i for i, l in enumerate(lines) if re.match(r"##[ \t]+", l)]   # parse_prep's heading form
        start = next((i for i in heads if lines[i][2:].strip() == "Attempts"), None)
        end = next((i for i in heads if start is not None and i > start), len(lines))
        rows = [i for i in range(end) if start is not None and i > start and lines[i].strip().startswith("|")]
        if not rows:
            raise AppError("%s has no `## Attempts` table (%s); add it" % (log, ATTEMPT))
        lines.insert(rows[-1] + 1, row)   # after the table's last row, blank lines inside it included
    else:
        lines = ["# Practice: %s" % stage_of(path), "",
                 "prep: %s" % os.path.basename(path), "", "## Attempts", "", ATTEMPT,
                 "|" + "---|" * 6, row, "", "## Patterns", "", "## Do not say"]
    with open(at(root, log), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return ["added: %s: %s" % (log, row)]


def practice_items(items, attempts):
    """(the retest items in the order of each item's latest attempt, the not-practised items in item order)."""
    latest = {}
    for _, cells in attempts:
        latest.pop(cells[1], None)   # a later attempt moves the item to its place in the file
        latest[cells[1]] = cells[3]
    retest = [item for item, verdict in latest.items() if verdict in RETEST]
    untried = []
    for item, phase, state, _ in items:
        tried = any(t == item or t.startswith(item + "/") for t in latest) or (item == "practice" and latest)
        if phase == "practise" and state in ("open", "user-only") and not tried:
            untried.append(item)
    return retest, untried


def practice_lines(retest, untried):
    return ["retest: %s" % item for item in retest] + ["not practised: %s" % item for item in untried]


PLAN_AFTER_DIAGNOSE = ("effort", "schedule")   # the plan items Diagnose's rounds size


def diagnose_lines(prep, items, attempts):
    """not diagnosed: lines, one per area with no diagnostic attempt and nothing setting it aside,
    while neither plan item sized from the rounds is done: behavioural answers, each areas/<topic>
    row (the areas item while it has none), the talk."""
    states = {item: state for item, _, state, _ in items}
    if any(states.get(item) == "done" for item in PLAN_AFTER_DIAGNOSE):
        return []
    tried = [cells[1] for _, cells in attempts if cells[2].lower() == "diagnostic"]

    def has(*tops):
        return any(t == top or t.startswith(top + "/") for t in tried for top in tops)
    areas = []   # (the area as printed, its item, whether a diagnostic round covers it)
    if "behavioural-leads" in states:
        areas.append(("behavioural answers", "behavioural-leads", has("story", "behavioural-leads")))
    topics = [item for item, _, _, _ in items if item.startswith("areas/")]
    areas += [(t, t, has(t)) for t in topics] or ([("areas", "areas", has("areas"))] if "areas" in states else [])
    if "talk" in states:
        areas.append(("talk", "talk", has("talk")))
    aside = {cells[1].partition(":")[2].strip().lower() for _, cells in prep["tables"].get("Decisions", [])
             if len(cells) > 2 and cells[1].lower().startswith("diagnose:") and cells[2].lower().startswith("set aside")}
    return ["not diagnosed: %s" % area for area, item, covered in areas
            if not covered and states.get(item) != "set aside" and area.lower() not in aside]


def review_lines(prep, items, retest, untried, day):
    """not reviewed: lines on the evening before the interview (days left: 1): each retest or
    not-practised item with no Decisions row `final review: <item>` (the user's keep or drop), then
    each practise-phase item set aside with no Decisions row naming it (`<item>` or `<any>: <item>`)."""
    if days_left(prep["header"], day) != 1:
        return []
    named = {}   # each Decisions row's decision, lowercased -> the item it names after its prefix
    for _, cells in prep["tables"].get("Decisions", []):
        if len(cells) > 1:
            decision = cells[1].strip().lower()
            named[decision] = decision.partition(":")[2].strip() if ":" in decision else decision
    asked = {item for decision, item in named.items() if decision.startswith("final review:")}
    lines = [item for item in dict.fromkeys(retest + untried) if item.lower() not in asked]
    lines += [item for item, phase, state, _ in items if phase == "practise" and state == "set aside"
              and item.lower() not in named.values() and item not in lines]
    return ["not reviewed: %s" % item for item in lines]


def cmd_prep_status(root, folder, stage, day):
    rel = app_folder(root, folder)
    path = prep_path(root, rel, stage)
    prep = parse_prep(read(root, path))
    attempts, bad_rows = practice_rows(root, practice_path(rel, path, prep))
    items, problems = [], []
    for n, cells in prep["tables"].get("Items", []):
        if len(cells) != 4:
            problems.append("FAIL: %s:%d: an item row has 4 cells (item | phase | state | where): %d here" % (path, n, len(cells)))
            continue
        item, phase, state, where = cells
        if state not in STATES:
            problems.append("FAIL: %s:%d: %s: unknown state %r (%s)" % (path, n, item, state, ", ".join(STATES)))
        if phase not in PHASES:
            problems.append("FAIL: %s:%d: %s: unknown phase %r (%s)" % (path, n, item, phase, ", ".join(PHASES)))
        if state == "done":
            problems += ["FAIL: %s:%d: %s is done but %s" % (path, n, item, why) for why in where_problems(root, rel, where)]
        items.append((item, phase, state, where))
    pages = []
    for n, cells in prep["tables"].get("Pages", []):
        if len(cells) != 4:
            problems.append("FAIL: %s:%d: a page row has 4 cells (page | built from | link | for): %d here" % (path, n, len(cells)))
            continue
        page, source = cells[0], cells[1]
        page_path, why = log_file(root, rel, page, "the folder")
        whys = [why] if why else []
        source_path = None
        if source not in ("", "-"):   # else the page is its own source
            source_path, why = (log_file(root, "", source[1:], "the Log") if source.startswith("/")
                                else log_file(root, rel, source, "the folder"))
            whys += [why] if why else []
        problems += ["FAIL: %s:%d: page %s: %s" % (path, n, page, why) for why in whys]
        pages.append((page, source, page_path, source_path))
    problems += bad_rows
    if problems:
        return problems, 2
    lines = ["prep: %s" % path] + prep_date_lines(prep["header"], day)
    rows = [cells for _, cells in prep["tables"].get("Schedule", []) if cells and cells[0].startswith(day)]
    lines += ["schedule: %s" % " | ".join(cells) for cells in rows] or ["schedule: nothing for today"]
    lines += ["%s: %s%s" % (state, item, " (%s)" % where if where not in ("", "-") else "") for item, _, state, where in items]
    lines += ["stale: %s (built from %s, changed since)" % (page, source) for page, source, page_path, source_path in pages
              if source_path and page_stale(root, page_path, source_path)]
    card = "cue-card-%s.md" % stage_of(path)
    same = lambda p: os.path.normcase(os.path.normpath(at(root, p)))
    if os.path.isfile(at(root, "%s/%s" % (rel, card))) and same("%s/%s" % (rel, card)) not in {same(s) for _, _, _, s in pages if s}:
        lines.append("no page: %s (no ## Pages row built from it)" % card)
    retest, untried = practice_items(items, attempts)
    lines += practice_lines(retest, untried)
    lines += diagnose_lines(prep, items, attempts)
    lines += review_lines(prep, items, retest, untried, day)
    # A later status line goes here, after the stale and retest lines and before the next: lines; a
    # next: line that outranks the user-only ones goes first in nexts.
    nexts = []
    if after_interview(prep["header"], day) and not os.path.exists(at(root, "%s/interview-%s-debrief.md" % (rel, stage_of(path)))):
        nexts.append("next: close the loop (ask for the questions asked, round by round)")
    nexts += ["next: %s (user-only)" % item for item, _, state, _ in items if state == "user-only"]
    open_ = [(PHASES.index(phase), i, item, phase) for i, (item, phase, state, _) in enumerate(items) if state == "open"]
    if open_:
        _, _, item, phase = min(open_)
        nexts.append("next: %s (open, %s)" % (item, phase))
    return lines + (nexts or ["next: nothing open"])


# ---- intake ----

RECRUITER = "recruiter"
FILE_TYPES = (".docx", ".pdf", ".txt", ".md")   # what file_text reads; any other type is listed, not read
REPLY = re.compile(r"^\s*(?:(?:re|fw|fwd|aw|wg|sv|tr|vs)\s*[:：]\s*)+", re.I)   # Re:, Fwd:, AW:, RE： name no mail
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SPACES = str.maketrans({"\xa0": " ", " ": " ", " ": " ", "​": ""})   # no-break and zero-width spaces
BY_TYPE = {"application/pdf": ".pdf", "message/rfc822": ".eml", "text/plain": ".txt", "text/html": ".html",
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"}


def html_text(markup):
    """An HTML mail part as its reader sees it: logfiles.html_text with head hidden, `- ` per list
    item and a row's cells joined by tabs."""
    return logfiles.html_text(markup, hide=("head",), marks=True)


def tidy(text):
    """Text as saved: UTF-8 with \\n, no-break spaces as spaces, no trailing spaces, at most one blank line in a row."""
    text = text.translate(SPACES).replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")   # \f: pdftotext's page break
    lines = [line.rstrip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")


def docx_text(data):
    """(text, None) from word/document.xml, a line per paragraph, or (None, why not)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            tree = xml.etree.ElementTree.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, xml.etree.ElementTree.ParseError, OSError) as e:
        return None, "not a readable .docx (%s)" % one_line(str(e) or type(e).__name__)
    paras = []
    for p in tree.iter(WORD + "p"):
        buf = []
        for el in p.iter():
            if el.tag == WORD + "t":
                buf.append(el.text or "")
            elif el.tag == WORD + "tab":
                buf.append("\t")
            elif el.tag in (WORD + "br", WORD + "cr"):
                buf.append("\n")
        paras.append("".join(buf))
    return "\n".join(paras), None


def pdf_text(data):
    """(text, None) through resume.pdf_text, Machine setup's pdftotext, or (None, why not)."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        text, why = resume.pdf_text(path)
    except OSError as e:
        return None, "pdftotext failed: %s" % one_line(str(e))
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    if text is None:
        return None, why
    if not text.strip():
        return None, "no text layer (a scanned PDF?): ask the user for the text"
    return text, None


def file_text(name, data):
    """(text, None) for a file intake reads (.docx, .pdf, .txt, .md), or (None, why not)."""
    ext = os.path.splitext(name)[1].lower()
    if ext == ".docx":
        return docx_text(data)
    if ext == ".pdf":
        return pdf_text(data)
    if ext in (".txt", ".md"):
        try:
            return data.decode("utf-8-sig"), None
        except UnicodeDecodeError:
            return None, "not UTF-8 text"
    return None, "not read (%s files are listed, not read)" % (ext or "extensionless")


def mail_date(msg):
    """The mail's Date in this machine's time zone, as a datetime; None without a readable one."""
    try:
        when = msg["Date"].datetime if msg["Date"] is not None else None
    except (AttributeError, TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:   # -0000: UTC, zone unknown
        when = when.replace(tzinfo=datetime.timezone.utc)
    return logfiles.local_time(when)


def header(msg, name):
    try:
        return one_line(str(msg.get(name, "") or ""))
    except (TypeError, ValueError):
        return one_line(str(msg.get_all(name, [""])[0]))


def part_text(part):
    try:
        text = part.get_content()
    except (LookupError, ValueError):
        text = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
    return html_text(text) if part.get_content_subtype() == "html" else text


def mail_sections(msg, prefix, unread):
    """A mail as lines: its headers, its body (the text part, else the HTML part as text), then each
    attachment as a `## Attachment: <prefix><name>` section, a forwarded mail's read the same way."""
    when = mail_date(msg)
    out = []
    for name in ("From", "To", "Cc", "Subject"):
        if header(msg, name):
            out.append("%s: %s" % (name, header(msg, name)))
    out.append("Date: %s" % (when.strftime("%Y-%m-%d %H:%M") + " (this machine's time zone)" if when
                             else header(msg, "Date") or "unknown"))
    body = msg.get_body(preferencelist=("plain", "html"))
    out += ["", tidy(part_text(body)) if body is not None else "(no text part)"]
    for n, part in enumerate(msg.iter_attachments(), 1):
        ctype = part.get_content_type()
        inner = part.get_content() if ctype == "message/rfc822" else None
        if isinstance(inner, list):   # a message/rfc822 part holds its message as a one-item list in some forms
            inner = inner[0] if inner else None
        name = part.get_filename() or (header(inner, "Subject") if inner is not None else "") or "attachment-%d" % n
        name = one_line(name)
        if inner is not None and not os.path.splitext(name)[1]:
            name += ".eml"
        elif not os.path.splitext(name)[1]:
            name += BY_TYPE.get(ctype, "")
        label = prefix + name
        out += ["", "## Attachment: " + label, ""]
        if inner is not None:
            out += mail_sections(inner, label + " › ", unread)
            continue
        if ctype.startswith("text/") and os.path.splitext(name)[1].lower() in (".txt", ".md", ".html", ".htm", ""):
            text, why = part_text(part), None
        else:
            text, why = file_text(name, part.get_payload(decode=True) or b"")
        if text is None:
            out.append("unread: " + why)
            unread.append((label, why))
        else:
            out.append(tidy(text) or "(empty)")
    return out


def intake_one(path, day, unread):
    """(base name, text) of the saved file for one input, or (None, None) for a file intake does not read."""
    with open(path, "rb") as f:
        data = f.read()
    source = os.path.basename(path)
    stem, ext = os.path.splitext(source)
    if ext.lower() == ".eml":
        msg = email.message_from_bytes(data, policy=email.policy.default)
        when = mail_date(msg)
        title = header(msg, "Subject") or "(no subject)"
        base = "%s-%s" % (when.date().isoformat() if when else day, slug(header(msg, "Subject"), "mail"))
        lines = ["# " + title, "", "Source: " + source] + mail_sections(msg, "", unread)
        return base, "\n".join(lines)
    text, why = file_text(source, data)
    if ext.lower() not in FILE_TYPES:
        unread.append((None, why))
        return None, None
    body = "unread: " + why if text is None else tidy(text) or "(empty)"
    if text is None:
        unread.append((source, why))
    return "%s-%s" % (day, slug(stem, "file")), "\n".join(["# " + one_line(source), "", "Source: " + source, "", body])


def slug(text, fallback):
    s = logfiles.ascii_slug(REPLY.sub("", text or ""))
    if len(s) > 60:
        s = s[:60].rsplit("-", 1)[0]
    return s or fallback


def save_text(root, rel, base, text):
    """Write text to <rel>/<base>.md, or <base>-2.md ... when a file of that name holds another mail;
    (path, True) when written, (path, False) when a file there already held that text. A file with
    the same head (its title, Source: and header lines: the text above its second blank line) holds
    the same input read again, and is rewritten: a PDF read once pdftotext is installed, say."""
    body = text.rstrip("\n") + "\n"
    head = "\n\n".join(body.split("\n\n")[:2])
    name, n = base, 2
    while True:
        path = "%s/%s.md" % (rel, name)
        full = at(root, path)
        if not os.path.exists(full):
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
            return path, True
        with open(full, encoding="utf-8", errors="replace") as f:
            old = f.read()
        if old == body:
            return path, False
        if "\n\n".join(old.split("\n\n")[:2]) == head:
            with open(full, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
            return path, True
        name, n = "%s-%d" % (base, n), n + 1


def cmd_intake(root, files, folder, day):
    rel = app_folder(root, folder) + "/" + RECRUITER
    for path in files:
        if not os.path.isfile(path):
            raise AppError("cannot read %s: no such file" % path)
    out = []
    for path in files:
        unread = []
        try:
            base, text = intake_one(path, day, unread)
        except OSError as e:
            raise AppError("cannot read %s: %s" % (path, e))
        if base is None:
            out += ["unread: %s: %s" % (os.path.basename(path), why) for _, why in unread]
            continue
        saved, wrote = save_text(root, rel, base, text)
        out.append(("saved: " if wrote else "unchanged: ") + saved)
        out += ["unread: %s: %s: %s" % (saved, label, why) for label, why in unread]
    return out


# ---- main ----

ROOT_HELP = "Every command takes --root <root>, the Log's root (default: the folder above this script's), anywhere on the line."


def parser():
    p = argparse.ArgumentParser(prog="application.py", description=__doc__, epilog=ROOT_HELP,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("name", epilog=ROOT_HELP)
    s.add_argument("--company"); s.add_argument("--role"); s.add_argument("--target")
    s.add_argument("--report"); s.add_argument("--kind"); s.add_argument("--today")
    s = sub.add_parser("prior", epilog=ROOT_HELP)
    s.add_argument("companies", nargs="+"); s.add_argument("--type")
    s = sub.add_parser("start", epilog=ROOT_HELP)
    s.add_argument("--name"); s.add_argument("--from", dest="source"); s.add_argument("--replace", action="store_true")
    s.add_argument("--family"); s.add_argument("--tier")
    s = sub.add_parser("save", epilog=ROOT_HELP)
    s.add_argument("--application"); s.add_argument("--target")
    s = sub.add_parser("level", epilog=ROOT_HELP)
    s.add_argument("saved"); s.add_argument("level", choices=("archived", "reference")); s.add_argument("--today")
    s = sub.add_parser("sent", epilog=ROOT_HELP)
    s.add_argument("target"); s.add_argument("--before"); s.add_argument("--record")
    s = sub.add_parser("sent-candidates", epilog=ROOT_HELP)
    s.add_argument("--before", required=True); s.add_argument("--limit", type=int, default=5)
    s = sub.add_parser("sent-show", epilog=ROOT_HELP)
    s.add_argument("refs", nargs="+"); s.add_argument("--target"); s.add_argument("--out"); s.add_argument("--record")
    s.add_argument("--known"); s.add_argument("--today")
    s = sub.add_parser("stale", epilog=ROOT_HELP)
    s.add_argument("target")
    s = sub.add_parser("risks", epilog=ROOT_HELP)
    s.add_argument("saved")
    s = sub.add_parser("phrasings", epilog=ROOT_HELP)
    s.add_argument("saved", nargs="?"); s.add_argument("entries", nargs="*"); s.add_argument("--angle", required=True)
    s.add_argument("--add", action="append", default=[]); s.add_argument("--cap", action="append", default=[])
    s.add_argument("--today")
    s = sub.add_parser("prep-init", epilog=ROOT_HELP)
    s.add_argument("folder"); s.add_argument("--stage", required=True); s.add_argument("--with", dest="with_")
    s.add_argument("--date"); s.add_argument("--mode-start")
    s = sub.add_parser("prep-status", epilog=ROOT_HELP)
    s.add_argument("folder"); s.add_argument("--stage"); s.add_argument("--today")
    s = sub.add_parser("practice-add", epilog=ROOT_HELP)
    s.add_argument("folder"); s.add_argument("--stage"); s.add_argument("--item", required=True)
    s.add_argument("--verdict", required=True); s.add_argument("--kind"); s.add_argument("--weak")
    s.add_argument("--heard"); s.add_argument("--today")
    s = sub.add_parser("intake", epilog=ROOT_HELP)
    s.add_argument("files", nargs="+"); s.add_argument("--folder", required=True); s.add_argument("--today")
    return p


def run(root, a):
    if a.cmd == "name":
        return cmd_name(root, a.company, a.role, a.target, a.report, a.kind, today(a.today))
    if a.cmd == "prior":
        return cmd_prior(root, a.companies, a.type)
    if a.cmd == "start":
        return cmd_start(root, a.name, a.source, a.replace, a.family, a.tier)
    if a.cmd == "save":
        return cmd_save(root, a.application, a.target)
    if a.cmd == "level":
        return cmd_level(root, a.saved, a.level, today(a.today))
    if a.cmd == "sent":
        return cmd_sent(root, a.target, a.before, a.record)
    if a.cmd == "sent-show":
        return cmd_sent_show(root, a.refs, a.target, a.out, a.record, a.known, today(a.today))
    if a.cmd == "sent-candidates":
        return cmd_sent_candidates(root, a.before, a.limit)
    if a.cmd == "stale":
        return cmd_stale(root, a.target)
    if a.cmd == "risks":
        return cmd_risks(root, a.saved)
    if a.cmd == "phrasings":
        if a.cap:
            return cmd_phrasings(root, None, a.angle, [], [], a.cap, today(a.today))
        if not a.saved:
            raise AppError("phrasings takes <saved> (or --cap)")
        return cmd_phrasings(root, a.saved, a.angle, a.entries, a.add, [], today(a.today))
    if a.cmd == "prep-init":
        return cmd_prep_init(root, a.folder, a.stage, a.with_, a.date, a.mode_start)
    if a.cmd == "prep-status":
        return cmd_prep_status(root, a.folder, a.stage, today(a.today))
    if a.cmd == "practice-add":
        return cmd_practice_add(root, a.folder, a.stage, a.item, a.verdict, a.kind, a.weak, a.heard, today(a.today))
    if a.cmd == "intake":
        return cmd_intake(root, a.files, a.folder, today(a.today))


def main(argv):
    logfiles.utf8_stdout()
    try:
        root, rest = logfiles.split_root(argv, __file__)
    except logfiles.LogError as e:
        print("FAIL: %s" % e)
        return 2
    try:
        p = parser()
        a, extra = p.parse_known_args(rest)
        if a.cmd == "phrasings" and not any(x.startswith("-") for x in extra):
            a.entries += extra   # entries after an option (write steps 9 and 10's order): argparse leaves them over before 3.12, and on any Python when some come before it
        elif extra:
            p.parse_args(rest)   # the usual error, and exit 2
    except SystemExit as e:
        if e.code:
            print("FAIL: bad arguments; see `application.py --help`")
        return 2 if e.code else 0
    root = os.path.abspath(root)
    try:
        res = run(root, a)
    except (AppError, entries.Error, logfiles.LogError) as e:
        print("FAIL: %s" % e)
        return 2
    lines, code = res if isinstance(res, tuple) else (res, 0)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
