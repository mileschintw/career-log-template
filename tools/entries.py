#!/usr/bin/env python3
"""What an entry is, for every tool and mode that reads entries.

  python3 -I tools/entries.py list [--series <slug> [--date YYYY-MM-DD]] [--window <years>] [--course-work]
  python3 -I tools/entries.py check [--consolidated <entry>...]
  python3 -I tools/entries.py refs <entry>
  python3 -I tools/entries.py links-since <entry>
  python3 -I tools/entries.py rulings-hits

(Windows: py -3 -I.) Every subcommand takes --root <root>, the Log's root, by default the folder
above this script's. <entry> is an entry's path, relative to <root> (`entries/2031-04-widget.md`)
or to the current folder.

An entry is a file `entries/<name>.md` other than `entries/_template.md` (ENTRY_PATH). Its slug is
the file name without `.md` and the leading `<YYYY-MM>-`. A series is a long experience split into
parts: every part, the first one included, has `series: <slug>` in its front matter, where <slug> is
the first part's slug (the first part keeps the original path).

Size: the estimated tokens of an entry are its ASCII characters / 2.7 plus 4/3 per other character,
a little above what Claude Code's Read counted on English and on Traditional Chinese Markdown. An
entry is over the threshold at more than THRESHOLD tokens, half of what Read returns in one call
(25,000).

- `list`: one line per entry: path, slug, series, type, org, period (and whether it is ongoing),
  tags, README status (`- (no README row)` without one), estimated tokens (and `over threshold`),
  then `one line:` and its text. `--series <slug>` lists that series' parts only, then
  `series <slug>: period <earliest start> – <latest end>`, the end `ongoing` when a part is, and
  either end `GAP` when a part's is GAP or does not read (`period -` for a series with no part). The flags below add lines after the entry lines, and without them the output is
  as above (scan.py hashes it):
  - `--date YYYY-MM-DD` (with `--series`): `part for <date>: <path>`, the finished part whose
    period holds the date, else the part still open (a period that reads, its end `ongoing` or `GAP`,
    its start not after the date), else the part that ends last; the first part when the date is
    before every part's start, followed by `before the first part:` and a `next:` line; when the
    date falls between two parts (no part covers it), `between parts:` and a `next:` line follow,
    as `period` prints them;
  - `--window <years>`: `outside window (ended <end>): <entry>` for each experience (an entry, or
    a whole series as `series <slug>: <its parts>`) that ended before the month <years> years ago
    (`--today` sets the day); an ongoing one, `GAP – ongoing` included, is inside;
    `window unknown (period <period>): <entry>` when an end is GAP or does not read;
  - `--course-work`: `course work: <paths> (by type or tag)`, each entry whose type is `course` or
    whose tags hold `coursework` (`none` without one).
  Exit 0.
- `check`: one line per finding, each starting with its kind:
  - `entry over threshold:` more than THRESHOLD estimated tokens;
  - `series names no entry:` no entry has the slug its `series` names;
  - `series part with an unreadable period:` not `YYYY-MM – YYYY-MM` or `YYYY-MM – ongoing` (a day
    may follow the month), or one that ends before it starts;
  - `series part with an empty One line:` its `## One line` holds nothing but comments;
  - `series <slug> has more than one ongoing part:`;
  - `series <slug> has overlapping periods:` two parts share more than the month where one ends and
    the next starts (the day, when both periods give days there);
  - `no README row:` no row of README.md links the entry;
  - `README row names a missing file:` a row links an entry file that does not exist;
  - `README row differs:` the row's title, period or type differs from the entry's front matter, or
    it lists a tag the front matter lacks (a row may list fewer tags);
  - `README row status unknown:` its status does not start with `stub`, `imported` or
    `consolidated` (SKILL.md › Layout);
  - `ongoing entry not updated in over two months:` or `ongoing entry with no readable
    last_updated:`, from its `last_updated` (a period `GAP – ongoing` is ongoing here too);
  then the shape entries/_template.md gives an entry, where a value or line that is `GAP` or
  starts with it (`GAP: <what>`, `GAP – ongoing`) is a gap and passes, and placeholder lines
  (`none`, `none yet`) and HTML comments are not read:
  - `front matter: <entry> <field> <value> not allowed (<what is>)`: `type` other than TYPES;
    `visibility` other than public, private, nda; `period` other than `YYYY-MM – YYYY-MM` or
    `YYYY-MM – ongoing` (a day may follow the month, either end may be GAP); `last_updated` not a
    `YYYY-MM-DD` date (an ongoing entry's is the staleness line's); a list in `period`,
    `last_updated` or `series` (shown as `one slug`), which each take one value: a list `period`
    or `series` is read as none, and `series: []` passes. A field it lacks is not read;
  - `link not a repo root: <entry> <url>; root <root>`: a GitHub or GitLab URL in `links:` that
    goes past the repo into a page (a PR, issue, commit: logfiles.URL_END), `, missing from links`
    added when no item of `links:` is that root;
  - `old section ## Log: <entry>`: *Old sections* below says what to do;
  - `pending line without a date: <entry>:<line>` (a `## Pending` line not `- YYYY-MM-DD: ...`)
    and `pending older than two months: <entry>:<line>`;
  - `conflict line not Open or Settled: <file>:<line>`: a line of an entry's `## Conflicts`, or of
    profile.md's `### Conflicts`, that past its `- ` starts with neither `Open:` nor `Settled:` (a
    version a settled conflict still lists, an open one without its marker);
  - `settled line not in a template form: <file>:<line>`: a `Settled:` line that does not go on
    with `use "`, `both "` or `do not use "` (or “, 「, 『) and end with its `(<source>)`;
  - `past phrasing not in form: <entry>:<line>`: a `## Past phrasings` line that is not
    `- **<angle>:** "<wording>" (<citation>)` with nothing after the citation (a label line over a
    group, an unquoted wording, a note after the citation); `past phrasing with more than one
    citation or a note: <entry>:<line>`: a `;` in the citation; `past phrasing angle unknown:
    <entry>:<line> <angle>`: neither `general` nor a target name (a `.tex` or `.md` in
    outputs/resumes/);
  - `results row missing <columns>: <entry>:<line> <metric>`: a `## Results and evidence` row whose
    How measured, Caveat or Source cell is empty;
  - `source key unresolved: <file>:<line> <key>`, in the files modes read for facts (the entries,
    profile.md, direction.md and stories.md, outside an entry's `## Past phrasings` and
    `## Conflicts`, profile.md's `### Conflicts` and stories.md's `## Application questions`): a
    `sources/...` path (one that ends in a file extension, a `/` or holds a `*`, read as a glob) that names
    no file or folder (the inbox aside), or a session key `<agent>-<YYYY-MM-DD>-<slug> U<k>` (A<k>,
    Q<k>) whose excerpt `sources/<agent>/<YYYY-MM-DD>-<slug>.md` is missing or has no `## U<k> `
    heading; and `source folder not in keys.md: sources/<folder>/`, a folder no line of
    sources/keys.md names, other than inbox/, resumes/ and the session excerpt folders (each of
    whose `.md` files starts `# <agent> session <YYYY-MM-DD>`).
  After the findings, lines for you to judge, which are not findings, from the same files and
  sections: `check: output citation: <file>:<line>: <text>`, a line naming a path in outputs/ (a
  fact citing an output is re-cited from that output's provenance table, SKILL.md › Provenance);
  and `check: record note: <file>:<line>: <text>`, a line that says `superseded` or `moved to` (a
  note about the record goes; a fact about the work, such as an earlier design, stays).
  `--consolidated <entry>...` (consolidate's Done when) reads only those entries: their findings
  above, the series and README findings that name them, and `pending not empty: <entry>` and
  `contribution category missing: <entry> <label>`, a label of `## My contribution` (CONTRIBUTION;
  words may follow it inside the bold, `**I led, with help from AI agents:**`) missing, or with
  nothing after it or indented under it.
  Exit 1 when it prints a finding, else `OK: <n> entries, no findings` and exit 0.
- `refs`: every line of the Log's other files (logfiles.LOG_FILES: README, stories.md, profile,
  direction, applications, config.toml, scan-sources.md; other entries, the Talking points files in
  stories/, outputs/, sources/ except the inbox) that names the entry's file, as `<file>:<line>: <text>`. It matches the file name without `.md` as a
  whole word, so plain text naming it and a line inside an HTML comment count too. Files that are not UTF-8 text are skipped.
  Then `talking points: <file>: type <type>[; links #pending]` for each Talking points file that
  links the entry outside an HTML comment, the last part when one of those links is to its
  `#pending`. Exit 0.
- `links-since`: the links to read at a consolidate. First a `since:` line naming the entry's last
  commit whose subject is `consolidate(<slug>)` (or names the slug in a comma-separated list in the
  parentheses), or saying there is none; then `section link: <section>: <link>` for each link in
  its `## Pending` (or an old `## Log`), `## Past phrasings` and `## Conflicts`; then `link: <link>`
  for each other link (URLs, and Markdown link targets) the entry has now, uncommitted changes
  included, that it did not have at that commit (every one, with none). Links inside HTML comments
  (the template's) are not read, and each link is printed once. Exit 0.
- `rulings-hits` (audit point 6): the outputs to read against the entries' current rulings. An
  output is an application folder (its resume.tex, answers.md and provenance.md), a target in
  outputs/resumes/ (its .md and .tex) or a report in outputs/reports/ (a scan report aside); its
  provenance table is the provenance.md, the target's .md or the report itself (logfiles.
  provenance_rows). A ruling is a `Settled:` line, of any form, in an entry's `## Conflicts` or
  profile.md's `### Conflicts`. Lines, in this order:
  - `ruling: <file>:<line>: <the line>`, each ruling once;
  - `no provenance: <output>`: an output with no provenance table; read it whole against every
    ruling;
  - `unreadable: <file> (...)`: an output's file that is not UTF-8 text; read it against every
    ruling;
  - `unresolved: <file>:<line>: <cell>`: a provenance row none of whose entry cells (every cell,
    in a table without an entry column) names an entry by its path, file name, slug or title (or
    a run of its title's words), profile or direction, or the piece of a cell (between `;`) that
    names something with `›` no entry matches; see which entry the row or piece means;
  - `check: <output> against <file>:<line>`: one per ruling of each entry its table names and of
    profile.md, and per ruling with a hit, followed by `; hit <side> <file>:<line> "<quote>"` for
    each quoted wording of the ruling (in "", “”, 「」 or 『』, its why and source left out) found
    in the output's files. <side> is `wrong` or `do-not-use` (a wording the ruling rules out),
    `context` (right only in the context the ruling names) or `right` (both sides of `both`); a
    `wrong` match inside a `right` one is left out. Matching ignores case, `*`, LaTeX markup,
    curly apostrophes, hyphens and dashes, runs of spaces and the space between a number and its
    unit; a `## Risks...` section is not read. Only quoted wordings are matched: a pair with no hit can
    still state the ruled-out claim in other words;
  - `OK: <n> outputs, <n> rulings, <n> pairs, <n> hits`. Exit 0.

Writes, and `state`, which reads what the modes decide on (each write edits in place and leaves
every other byte of the file as it was, its byte order mark and line ends included):

  python3 -I tools/entries.py new <slug> --month YYYY-MM --status stub|imported --field title=<title>
      --field period=<period> [--field <name>=<value>]... [--field-source <name>=<source>]...
  python3 -I tools/entries.py readme-row <entry> [--status <status>]
  python3 -I tools/entries.py readme-sort [--check]
  python3 -I tools/entries.py state [<entry>...]
  python3 -I tools/entries.py pending-add <entry> <text>
  python3 -I tools/entries.py period <entry> --cover YYYY-MM-DD | --ongoing
  python3 -I tools/entries.py set-visibility <entry> public|private|nda [--source <source>]
  python3 -I tools/entries.py phrasing-add <entry> --angle <angle> --source <citation>
      [--distinct | --replace <n>] <wording>
  python3 -I tools/entries.py split <entry> --phase <phase> --cut [<end>..]<start>:<part>:<phase>...
  python3 -I tools/entries.py split --undo <entry> <part>...
  python3 -I tools/entries.py diff <entry> [<part>...]
  python3 -I tools/entries.py drop <entry> --reason <reason>

A text or wording that starts with `-` goes after `--`, with every flag before the `--`.

- `new`: writes `entries/<YYYY-MM>-<slug>.md` from entries/_template.md, then its README row as
  `readme-row` does. <slug> is lowercase ASCII letters and digits joined by `-`; `--month` names
  the file (the mode says which month). `--field` sets a front matter field: title and period
  (required), type, org, my_role, collaborators, tags and links (comma-separated), visibility,
  series. An unknown start is `GAP – ongoing`, `GAP – YYYY-MM` or `GAP – GAP`. A field not given
  holds `GAP: <what>` (`my_role: GAP: role title`), tags and links `[]`, series nothing,
  visibility `GAP`, last_updated today. Each field keeps the template's comment, except one named by
  a `--field-source <name>=<source>` (org, my_role, collaborators, tags, visibility; the field given
  by `--field` too), whose comment becomes `# (<source>)`; a visibility other than GAP needs one
  (`--visibility-source <source>` is the same as `--field-source visibility=<source>`). In
  the body, `# <title>`, and `GAP:` in each of the ten prose sections (One line through Likely
  questions; after each of My contribution's labels), except the two tables, which stay as the
  template has them, as do Past phrasings, Conflicts and Pending. Prints `created: <path>` and the
  row's line. Exit 1, writing nothing, when the file exists (`exists: <path>`).
- `readme-row`: writes the entry's row of README.md's Entries table (the first table with an
  Entry column whose rows link an entry, else the first with Entry and Period columns, else the
  first with Entry) from its front matter: period, `[<title>](<path>)`, type, every tag, and
  `--status` (stub, imported or consolidated, a note in parentheses after it if any), or the row's
  status as it stands without `--status` (an entry with no row needs it). The row replaces the one
  that links the entry, or is added, and goes above the first entry row it sorts before (the
  order below). When the table was in that order, the rows of the entry's series move with it as
  one block, so the table stays in order.
  Prints `readme row <added|replaced|unchanged>: README.md:<n>: <row>`. Exit 0.
- `readme-sort`: sorts the Entries table's rows that link an entry, by their Period cells, top to
  bottom: rows whose period holds a `GAP` (or does not read), newest known date first; then the
  ongoing rows, newest start first; then the rest, newest end first, ties by newest start (a month
  without a day sorts below the days of that month). The rows of a series (entries with the same
  `series`) stay together, newest part first (an ongoing part, then by the newest date a part's
  period holds, then its oldest; a GAP is unknown, not first), and the block sorts by the whole
  series: with the GAP rows when a part's period holds a GAP or does not read, by the newest date
  any part sorts by; else with the ongoing rows when a part is ongoing, by its earliest start;
  else by its latest end, then its earliest start, newest first as above. Ties keep their order,
  and rows that link no entry keep their places. Prints `sorted: <n> entry rows, <m> moved`, or
  `OK: <n> entry rows in order`; exit 0. `--check` writes nothing: one `out of order: README.md:<n>: <entry>` per row
  that would move, and exit 1.
- `state`: lines for each entry given, or for every entry without one, in this order:
  - `state: <entry>: gaps <n>; gap sections <k> of 10; pending <p> (oldest <date>)`: <n> counts
    each `GAP` outside HTML comments, front matter included; a gap section is one of the ten prose
    sections holding nothing but `GAP:` lines, blanks, comments, a table's header and rule, or My
    contribution's labels (a missing one counts);
  - `gap sections: <entry>: <sections>`, when there are any;
  - `key section empty: <entry>: <section>` for One line, My contribution and Results and
    evidence;
  - `blocking gaps: <entry>: <section> (<n> GAP | empty), ...` for those of My contribution,
    Results and evidence and Likely questions (attribution, results, likely questions) that hold
    a GAP or nothing;
  - `suggest consolidate: <entry>: <reasons>`: PENDING_MANY pending lines or more, an oldest pending
    line over a month old, `mostly GAP` (MOSTLY_GAP gap sections or more: a stub), and each empty
    key section.
  Exit 0.
- `pending-add`: appends `- <today>: <text>` (whitespace runs made one space) to `## Pending`,
  after its last line, renaming an old `## Log` heading to `## Pending` (and adding the section at
  the end when there is neither), and sets last_updated to today. Prints `renamed: ...` when it
  renamed, `added: <entry>:<n>: <line>` and `last_updated: ...`. Exit 0. Exit 1, writing nothing,
  when the text starts with a date and a colon, after any leading list mark (`- `, `* `) or bold
  (`**2031-04-20**:` counts) (`leading date:`, then a `next:` line).
- `period`: `--cover <date>` extends the period's end to the date (at the end's precision) when
  the date is past it; `--ongoing` makes the end `ongoing`. Then it rewrites the README row as
  `readme-row` does, the status kept. `unchanged: ...` (exit 0) when the period covers the date
  already, is ongoing, or ends in GAP; exit 1, changing nothing, for a date before the start, a
  period that does not read, an entry with no README row, or a series part when another part
  ends later or its end is ongoing or GAP (`not the series' last part:`). When a `before the
  start:` or `not the series' last part:` refusal's date falls between two parts of the series
  (no part covers it), `between parts:` and a `next:` line follow. Every other refusal, and
  `unchanged:` for an end in GAP, ends with a `next:` line too.
- `set-visibility`: writes `visibility: <value>` with `# (<source>)` as the line's only comment;
  the source is `user, <today>` by default. Prints the line. Exit 0.
- `phrasing-add`: keeps a wording in `## Past phrasings` as `- **<angle>:** "<wording>"
  (<citation>)` (*Past phrasings* above): <angle> a target name or `general`, the citation free
  text with no `;` (a source file, `outputs/resumes/<target>.tex, YYYY-MM-DD`, a chat key). The
  wording is taken word for word, whitespace runs made one space, quotes around it dropped. Lines:
  - `added: <entry>:<n>: <line>`, after the section's last line;
  - `already kept: <entry>:<n>: <line>` or `recited: <entry>:<n>: <line>`: the same angle and
    wording is there already; its citation moves to the new one when that is newer: an output's
    citation (outputs/...) moves to no other, any other moves to an output's, else the new one
    moves in when its first YYYY-MM-DD is later;
  - `similar: <entry>:<n>: <line>`, then `not added: ...` and exit 1, writing nothing: a line of
    the same angle whose words are SIMILAR alike (`similar()`). Judge it: the same bullet in other
    words, `--replace <n>` (a line of the same angle) puts the new line in its place (exit 1, `kept:`, when that line cites an
    output and the new one does not); a different one, `--distinct` adds it anyway;
  - `replaced: <entry>:<n>: <line>`, with `--replace`.
  Exit 0 otherwise.
- `split` (consolidate step 4): makes the entry the first part of a series and writes the later
  parts, one per `--cut`: the date the part starts (YYYY-MM[-DD]), its short slug, its phase (a
  phase holds no `: `); `<end>..` before the start, when the work paused between the two parts,
  is the date the earlier part ends (not before its start, not after the cut, compared at the
  coarser of the two dates). The series slug is the entry's `series`, else its slug; the series
  title is its title (the part before the last `: `, when it is a part already). The entry keeps
  its path and gets `series: <slug>`, the title `<series title>: <--phase>` (its `# ` heading
  too, when that is `# <its title>`; else `heading not rewritten:` and a `next:` line) and the
  period from its start to the first cut (or its `<end>`). Each later part is
  `entries/<cut's YYYY-MM>-<series
  slug>-<part>.md`, written as `new` writes an entry, with `series`, the title `<series title>:
  <phase>`, the period from its cut to the next (or that cut's `<end>`; the last to the entry's
  end, or `ongoing`), and the entry's type, org, my_role, collaborators, tags, visibility and links
  lines as they stand (a block list's lines included). Then
  each part's README row, as `readme-row` writes it, a new part's status copied from the entry's
  row. Prints `kept: <entry>: <title>; period <period>`, `created: <part>: <title>; period
  <period>` per part, and the rows' lines. The facts stay in the entry: moving them is the mode's.
  Exit 2, writing nothing, when the title is a gap (`GAP`, `GAP: ...`), the period does not read
  (or holds a GAP), the entry has no README
  row, there is no entries/_template.md, a part's file exists or two cuts name one, a cut is not
  after the one before it (the first after the start) and before the end (two parts that start in
  the same month both give days), or an `<end>` is empty, before the earlier part's start or after
  its cut.
- `split --undo <entry> <part>...` (a rejected split): deletes each part's file and README row,
  `git rm --cached` first for one in the index (`diff` adds it), and gives the entry back its
  title, `# ` heading and series, and the period from the earliest start to the latest end of
  the entry and its parts (`period unchanged:` when one does not read), then rewrites its README
  row. The title: the series title as the draft has it, then HEAD's `: <phase>` when HEAD's entry
  is a part already (HEAD's title as it stands when it holds no `: `); else the title less the `: <phase>` split added (so a title the draft
  corrected stays corrected); the series: HEAD's, or none (no
  `series:` line when HEAD's has none). An entry not in HEAD (new since the last commit) whose
  series is its own slug, with no other part left, gets the title less the `: <phase>` and an
  empty `series:`; any other one keeps both as they stand (`not in HEAD:`, then a `next:` line).
  The heading is rewritten as `split` rewrites it. Move
  the parts' content back into the entry first: the files are gone after it. Prints `restored:
  <entry>: <title>; period <period>; series <slug or ->`, `deleted: <part>[; README row]` per
  part, then `still names <part>: <file>:<line>: <text>` for each line `refs` finds naming a part
  (point it back at the entry). Exit 2, writing nothing, when a part is named twice, is not
  another entry of the entry's series, or is in HEAD (an earlier split's part).
- `diff <entry> [<part>...]` (consolidate step 5): `git add -N` for each one not in the index
  (so a new part shows), then `git diff` of them, and with parts also of README.md, stories.md
  and profile.md, printed in a `diff` code fence longer than any run of backticks in it, to be
  pasted as printed. `no change: <files>` when the diff is empty. Exit 0.
- `drop <entry> --reason <reason>` (SKILL.md › Dropped experiences, on the user's word): deletes
  the entry's README row (`README row: <row>`, or `none`), each Story index item that links it
  (`story removed: <question type>: <item>`) and its file (`deleted: <entry>`; out of the index
  too when HEAD lacks it); appends a section `## <today> — Dropped: <title>` holding one line,
  `- Removed `<entry>` (<title>, <period>): <reason>`, to sources/import-log.md (`import log:
  ...`). When one part of its series is left, that part is a plain entry again: its title less the
  `: <phase>` (its heading too, as `split` rewrites it), an empty `series:` and its README row
  rewritten (`series folded: <part>: <title>; series -`), then a `next:` line and `old title:
  <file>:<line>: <text>` for each line outside outputs/ and sources/ that names the part and holds
  its old title. Else, when the entry was a series' first part, the earliest part left names the
  series: `series renamed: <part>: series <slug>` for each part. When a removed item was `core` and the
  series has parts left, a `next:` line. Last, a `next:` line and `still names: <file>:<line>:
  <text>` for each line `refs` finds naming the entry outside outputs/ and sources/ (frozen or
  historical, left as they are): take the entry out of it, or delete the line when it says
  nothing else. Exit 0.

`--today YYYY-MM-DD` (check, list --window, new, state, pending-add, set-visibility, split, drop) sets the day
they count from or write, for tests.

Old sections: an entry with a `## Log` section (an older Template's) treats it as `## Pending`, and
the next mode that edits the entry renames the heading. Its lines predate the Pending rules, so
their dates are event dates, and a line whose fact the body already holds is deleted, not placed
again. A line that only records an import or enrichment is deleted too, after any fact inside it is
placed and after one line for it is added to `sources/import-log.md` if that log lacks it. A line
that records an application, fair or contact moves to `applications.md`, unless it has a folder in
`outputs/applications/` (then it is deleted).

Past phrasings, as the tools read them (`phrasings()`, which tools/check_run.py imports): the
angle of a line is its own prefix in the template's form, `- **ai-infra:** "..."` (a hyphen slug,
then the wording in quotes: straight, curly or corner), so a bold label inside a wording is no
angle; a label line (`**ai-infra**`, `- **ai-infra:**` alone, `### ai-infra`) sets the angle of
the lines below it that have none (an older Template's form, which `check` reports as not in
form); `none yet` and `GAP:` lines are not wordings.

Stories (the Story index, Talking points and wordings files, and the Application questions table):

  python3 -I tools/entries.py story-coverage [--type <question type>]... [--talking-points]
      [--application-questions]
  python3 -I tools/entries.py story-candidates <question type>
  python3 -I tools/entries.py story-stale <talking points file>
  python3 -I tools/entries.py story-wording-add <question type> <wording>
  python3 -I tools/entries.py story-wordings [--type <question type>]...
  python3 -I tools/entries.py story-finish <entry>
  python3 -I tools/entries.py story-type-add <question type>
  python3 -I tools/entries.py story-add <question type> <target> [--marker raw|pending|core]...
      [--label <label>] [--summary <summary>]
  python3 -I tools/entries.py story-core <entry> on|off
  python3 -I tools/entries.py story-confirm <talking points file> [--type <question type>]
  python3 -I tools/entries.py answer-row <question type> [--angle <angle>]
  python3 -I tools/entries.py answer-row-add <question type> --scope shared|per-angle|per-company
  python3 -I tools/entries.py answer-set <question type> [--angle <angle>] [--remove] <path>

They read three formats, and write them as below: the Story index rows and items (story-type-add,
story-add, story-core, story-finish), a Talking points file's `confirmed:` line and its row's link
(story-confirm; the rest of the file is the `stories` mode's, as given here), and the wordings
files (story-wording-add):

- The Story index is the first table of stories.md, before any `## ` heading (not the Application
  questions table), with the header `| Question type | Stories |`. One row per question
  type, each type in one row only: `| <question type> | <story>; <story> |`, or, once the type has a
  Talking points file, `| [<question type>](stories/<slug>.md) | <story>; <story> |`. A question
  type holds no `|`, `;` or `]`. A story is
  `*(<marker>)* [<label>](entries/<file>.md#<section anchor>) — <one-line summary>`; the markers
  and the summary are optional, and stories are separated by `; `. Markers: `raw` (imported facts
  not consolidated yet), `pending` (facts still in the entry's `## Pending`), `core` (the entry is
  one of the user's core Stories; one item of the experience marked anywhere in the index is
  enough);
  others pass through;
  several go in one, comma-separated (`*(raw, pending)*`), and one written right after the link
  counts too. A story starts at the cell's start or at a `; ` followed by `*(` or `[`, so a summary
  may hold `;` but no `; [` or `; *(`. An item with no link, or one that links a file outside
  entries/, is kept but is not a Story. A Story is named by its key: `entries/<file>.md#<anchor>`,
  or the path alone when the link has no anchor: one point of an experience (GLOSSARY.md), and a
  long experience holds many. An experience is an entry, or a whole series (named by its first part).
  Core Stories and the type count per experience count by experience (its types are every type
  any of its keys is listed under); the other checks count by key. `log` indexes every pending
  Story of an entry as `entries/<file>.md#pending`, so that key names several Stories until
  `consolidate` gives each its own section; the two per-Story findings below skip it until then.
- A Talking points file is `stories/<slug>.md`, where <slug> is the question type lowercased with
  each run of characters other than letters and digits replaced by `-` (`Disagreement / conflict`:
  `disagreement-conflict`); the row's link, not the slug, says which file is the type's:

    ---
    type: <question type, as the index row writes it>
    confirmed: YYYY-MM-DD HH:MM
    order: chronological | result-first
    ---

    # <question type>

    ## Stories
    1. [<label>](../entries/<file>.md#<anchor>) — <when to lead with it>
    2. [<label>](../entries/<file>.md#<anchor>) — <when to lead with it>

    ## Opening
    <the one full sentence>

    ## Cue lines
    - <a few words> ([<section>](../entries/<file>.md#<anchor>))

    ## Follow-ups
    - [Likely questions](../entries/<file>.md#likely-questions)

  The tools read `type`, `confirmed`, the numbered `## Stories` list in order (the first is the
  lead Story) and every link to an entry anywhere in the file outside HTML comments (the entries
  it points at). `confirmed:` is the local date and time the user last confirmed the file; the time
  is optional (`YYYY-MM-DD` alone reads as 00:00), but story-confirm writes it at every save and
  reconfirm, so that the line changes even when the date does not.
- A wordings file is `stories/wordings/<slug>.md` (the slug as above, `-2`, `-3`, ... added when
  another type's file has it), one per question type, kept whether or not the type has Talking
  points; its `type:` line, not its name, says which type's it is:

    ---
    type: <question type, as the index row writes it>
    ---

    # <question type>

    - <a question the user brought, word for word, on one line>

  The tools read `type` and, after the front matter, every line that starts with `- ` outside
  HTML comments, in order.

In the output below, `-` stands for an empty field, a list of question types is separated by
` | `, and a line's last field is free text (it may hold `; `).

- `story-coverage`: first `core stories: <n>; <entry> (<k> types); ...`, the experiences marked
  `core`; then `types per entry: <entry> (<k> types); ...`, every experience the index lists, most
  types first (ties in index order); then, with `--type`, one `interview: <question type>: leads with
  <key>` line per question; then one line per finding, each starting with its kind:
  - `no story index:` no stories.md, or none of its tables has the index's header;
  - `duplicate question type:` two rows give the same type; every check uses the first, here
    and in story-candidates;
  - `type with no story:` its row holds no Story (`(items without an entry link: <n>)` follows
    when it holds other items);
  - `type with only raw or pending stories:` every Story in its row is marked `raw` or `pending`;
  - `index names a missing entry: <question type>: <path>`;
  - `story under too many types: <key> in <n> types (more than MAX_TYPES_PER_STORY): <types>` (a
    `#pending` key is skipped);
  - `core stories outside 3–5: <n>` (CORE_RANGE);
  - `row links a missing talking points file: <question type>: <path>`, `talking points file no
    row links: <path>`, `talking points type differs from its row: <path>: type <t>, row <t>`,
    `talking points with no readable confirmed date: <path> <value>`;
  - with `--type`: `interview type not in stories.md: <question type>`, `interview type with no
    story: <question type>`, and `story carries too many questions in one interview: <key> leads
    <n> (more than MAX_PER_INTERVIEW): <types>` (a `#pending` key is skipped).
  - with `--talking-points`, for each Talking points file: `talking points sections out of order:
    <file>: <its sections, as they come>` (Stories, Opening, Cue lines, Follow-ups is the order),
    and `talking points over MAX_CUE_LINES cue lines: <file>: <n>`;
  - with `--application-questions`, for each row of the Application questions table, `application
    question: <question type>: ` and one of: `no scope (shared, per-angle, per-company): <scope>`,
    `shared row with <n> pointers` (more than one), `per-company row with <n> pointers`,
    `per-angle pointer with no angle: <pointer>`, `per-angle row with <n> pointers for <angle>`.
  `--type` is given once per question of a pasted list for one interview: the question type the
  question maps to, written exactly as the index writes it, or `<question type>=<key>` when the
  user chose a Story other than the lead. The lead is the Talking points file's first Story, else
  the row's first Story. Exit 1 when it prints a finding, else `OK: <n> question types, no
  findings` and exit 0.
- `story-candidates <question type>` (matched exactly, case included), lines in this order:
  - `type: <question type>`, then `type not in stories.md: <question type> (...)` for a new type,
    whose candidates are then every entry;
  - `talking points: <file> confirmed <confirmed value>`, or `talking points: none; a new file is <path>`
    (the row's link when it names a missing file, else `stories/<slug>.md`);
  - `talking points <n>: <key>; label <label>; <text after the link>`: the file's Stories in order;
  - `indexed: <key>; markers <markers, comma-separated>; series <slug>; label <label>; summary:
    <summary>` (or `one line: <the entry's One line>` when the row gives no summary): the row's
    Stories in its order;
  - `indexed, not an entry: <the item as written>`: the row's other items;
  - `not yet indexed: <path>; series <slug>; indexed under <types>; [another part indexed here:
    <path>;] one line: <One line>`: each entry with no Story under this type, the bracketed field
    only when another part of its series has one;
  - `pending: <path>: <bullet>`: each `- ` line of each entry's `## Pending`, entry by entry, cut
    to 300 characters with ` ...` (read the entry for the rest).
  Exit 0.
- `story-stale <stories/<slug>.md>`: the changes, since the file was confirmed, to the entries it
  points at. First `since: <commit> <subject>`, the last commit that wrote the file's current
  `confirmed:` line, or, when no commit did, `since: <date> <time> (...)`; then `changed: <entry>
  <commit> <committer date> <subject>` for each later commit to one of them (from the confirmed
  date and time, in the second case), `uncommitted: <entry>`, and `missing entry: <entry>`. Exit 1
  when it prints one, else `OK: <n> entries unchanged since <since>` and exit 0. To show a change:
  `git -C <root> diff <since commit> -- <entry>`, or, with no since commit, from the parent of the
  oldest `changed:` commit (`<commit>^`). A reconfirm the same day clears the earlier changes only
  when it writes a new `confirmed:` value, which the time does.
- `story-wording-add <question type> <wording>`: keeps the wording, its whitespace runs made one
  space, in the type's wordings file, creating the file (and stories/wordings/) for a type that has
  none. The type must be a Story index row's, matched exactly, and one a `type:` line holds as it
  is (exit 2 otherwise). A wording that starts with `-` goes after `--`, with `--root` before the `--`. Prints `added:
  <file>: <wording>`, or `already kept: <file>: <wording>` when the file holds it already (case and
  whitespace aside), and exits 0.
- `story-wordings`: every type's wordings, the types in index order, then the files whose type
  the index lacks; with `--type` (once per type, matched exactly) only those types. Lines:
  `wording: <question type> | <wording>` per wording; `no wordings: <question type>` for a `--type`
  with none; `wordings type not in stories.md: <file>: <question type>`, before that file's
  wordings; `wordings file with no type: <file>`. Exit 0.
- `story-finish <entry>` (consolidate step 6): edits stories.md's Story index in place. Each item
  that links <entry> at a section the entry has (the anchor of one of its `## ` to `###### `
  headings, outside comments and fenced code, other than `pending`) loses the markers `raw` and
  `pending`, and the `*(…)*` itself when no marker is left; other markers, the link and the summary
  stay, and every other byte of the file stays as it was.
  One line per item edited: `dropped: <question type>: <markers dropped>: <the item as it now
  reads>`. Then one line per finding, each starting with its kind:
  - `no story index:` as in story-coverage;
  - `links no section: <question type>: <item>`: an item marked `raw` or `pending` that links
    <entry> with no anchor or one no heading of the entry has, or any item that links its
    `#pending`;
  - `raw source: <question type>: <source>: <item>`: an item marked `raw` that links a file in
    sources/ that <entry> names by its path (in a link or in plain text; a source cited only by its
    key is not matched).
  It edits no finding's item, and writes the other edits whatever it finds. Exit 1 when it prints
  a finding, else `OK: <n> items edited` and exit 0.

The writes below change one cell of stories.md, or add one row after a table's last, and leave
every other byte as it was. A question type is matched exactly, against the table's first row
that gives it.
- `story-type-add <question type>`: adds `| <question type> | |` to the Story index. The type is
  one line, holds no `|`, `;` or `]`, fits a `type:` line as written (no ` #`, quotes or brackets
  around it), and is no row's type yet, case aside (exit 2 otherwise). Prints `added:
  stories.md:<n>: <row>`.
- `story-add <question type> <target>`: adds a Story to the row's Stories cell, after `; ` when the
  cell holds items: `*(<markers>)* [<label>](<target>) — <summary>`, in the index format above.
  <target> is `entries/<file>.md#<anchor>` (or the entry alone), the anchor one of the entry's
  headings, `pending` included; or a file in sources/ (an import's raw link), which needs
  `--label`; a link with a space or parenthesis is refused (rename the file). The label is the
  entry's title, then ` › <the section's heading>` when the target has an anchor, with `|` and
  `]` written `\\|` and `\\]`; `--label` replaces it. `--marker` (once per marker) adds `raw`,
  `pending` or `core`; a `#pending` target always carries `pending`. `--summary` is one line,
  without `; [` or `; *(` (its `|` is written `\\|`). Prints `added: <question type>: <item>`, or
  `already linked: <question type>: <item>`, writing nothing, when the row has an item that
  links the same file and anchor (the anchor's case aside).
- `story-core <entry> on|off`: `on` adds `core` to one item of the experience (the first that
  links <entry>, else the first that links another part of its series): into its first `*(...)*`
  (`*(raw, core)*`), else as `*(core)* ` before it. Prints `core on: <question type>: <item>`;
  `already core: <question type>: <item>` for each item of the experience marked core already,
  writing nothing; or `not indexed: <entry> ...` and exit 1 when no item links the experience.
  `off` takes `core` from every item of every part (`core off: <question type>: <item>` each, or
  `not core: <entry>`).
- `story-confirm <stories/<slug>.md>`: writes `confirmed: <now>`, the local date and time
  `YYYY-MM-DD HH:MM`, in the file's front matter, and prints `confirmed: <file>: <now>`. With
  `--type <question type>`, it then links the row's type to the file (`[<question type>](<file>)`,
  `row linked: ...`, or `row already links: ...`). Exit 1, writing nothing, when the file's `type:`
  is not that type (`type differs: ...`) or the row links another file that exists (`row links
  another file: ...`).

The Application questions table is the first under `## Application questions` with a Question type
and a Scope column; Answer from, User's direction and Approved answer are read by name. The Approved
answer cell holds pointers separated by `; `: `<angle>: [<label>](<path>)` in a `per-angle` row,
<angle> a target name or `general` (Past phrasings' angles), and `[<label>](<path>)`, one at most,
in a `shared` row; a `per-company` row holds none. <path> is relative to the Log's root.
- `answer-row <question type>`: `row: <question type>; scope <scope>`, `answer from: <cell>`,
  `direction: <cell>`, then `pointer: <angle or ->: <path>; label <label>` per pointer: with
  `--angle` in a per-angle row, that angle's, then `general`'s; else all, in the cell's order. Then
  `pointer: none ...` when it printed none. For a type no row gives: `no row: <question type>`,
  then `row types: <type> | <type> ...`. Exit 0.
- `answer-row-add <question type> --scope <scope>`: adds the row, its other cells empty; the type
  as for story-type-add. Prints `added: stories.md:<n>: <row>`.
- `answer-set <question type> <path>`: writes the pointer `[answer](<path>)` (with `--angle
  <angle>: ` before it, needed, in a per-angle row) in place of the row's pointer for that angle
  (any one, in a shared row), the others staying where they are, or after them when there is none.
  A second pointer for that angle (in a shared row, any second) is taken out. Prints `replaced:
  <question type>: <old pointer>` for each it replaced, then `set: <question type>: <pointer>`; or
  `unchanged: ...` when the one pointer links <path> already. The file must exist. `--remove`
  takes out each pointer (of `--angle`'s, when given) that links <path>, or a file in the folder
  <path> names: `removed: ...` each, or `not linked: ...`. Exit 1, writing nothing, for a type no
  row gives (`no row:`), a row with no scope (`no scope:`), or a per-company row (`per-company row
  takes no pointer:`, exit 0 with `--remove`).

Exit 2, with one line saying why, on a bad argument (a root given as the last argument, the form
an older Template took, is named with the --root it needs), a <root> with no entries/ folder, an <entry>
that is not an entry, a file it cannot read, or (links-since, story-stale) when git fails.
Standard library only, Python 3.11+.
"""
import datetime
import difflib
import glob
import os
import posixpath
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
# Moved to logfiles.py; kept here under their old names for the tools and tests that use them
from logfiles import (INBOX, LOG_FILES, LOG_FOLDERS, as_list, front_matter, heading_anchors, log_files,
                      scalar, unquote)

ENTRY_PATH = re.compile(r"entries/(?!_template\.md$)[^/]+\.md")   # fullmatch, on a /-separated path
THRESHOLD = 12500
STATUSES = ("stub", "imported", "consolidated")
URL = re.compile(r"https?://[^\s<>\"'`\]|]+")
MD_TARGET = re.compile(r"\]\(([^)\s]+)\)")
PERIOD = re.compile(r"(\d{4}-\d{2}(?:-\d{2})?)(?: – (ongoing|\d{4}-\d{2}(?:-\d{2})?))?", re.I)
MAX_TYPES_PER_STORY = 3   # a Story (entry#anchor) under more types than this is told for too many questions
CORE_RANGE = (3, 5)       # how many core Stories (experiences marked core) a Log should have
MAX_PER_INTERVIEW = 1     # questions one Story (entry#anchor) may lead in one interview
WORDINGS = "stories/wordings"
UNFINISHED = ("raw", "pending")
MARKERS = ("raw", "pending", "core")   # the markers story-add writes
TALKING_SECTIONS = ("Stories", "Opening", "Cue lines", "Follow-ups")   # a Talking points file's, in order
MAX_CUE_LINES = 7         # a Talking points file's cue lines; detail beyond them goes to Likely questions
STORY_SPLIT = re.compile(r";\s+(?=\*\(|\[)")
MARKER = re.compile(r"\*\(([^)*]+)\)\*\s*")
LINK = re.compile(r"\[((?:[^\]\\]|\\.)*)\]\(([^)\s]+)\)")
# An entry's shape (entries/_template.md)
TYPES = ("work", "internship", "project", "research", "course", "leadership", "award", "other")
VISIBILITIES = ("public", "private", "nda")
CONTRIBUTION = ("I did:", "I led, with help from:", "Others did; I can explain it:")
DATE = r"\d{4}-\d{2}(?:-\d{2})?"
GAP_VALUE = re.compile(r"GAP(?![\w-])")   # at a value's start: GAP, GAP: <what>, GAP – ongoing
PLACEHOLDER = re.compile(r"(?:- )?(?:(?i:none(?: yet| open)?\.?)|GAP(?:[:\s(].*)?)")   # fullmatch
QUOTE = re.compile(r'"([^"]+)"|“([^”]+)”|「([^」]+)」|『([^』]+)』')
PHRASING_FORM = re.compile(r'- \*\*([a-z0-9][a-z0-9-]*):\*\* ["“「『].*["”」』] \(((?:[^()]|\([^()]*\))*)\)', re.I)
SETTLED_FORM = re.compile(r'Settled: (?:use|both|do not use) ["“「『].*\)\.?')
PENDING_LINE = re.compile(r"- (\d{4}-\d{2}-\d{2}):")
OUTPUT_PATH = re.compile(r"(?<![A-Za-z0-9_-])outputs/[\w.-]")   # CJK text may run into it
RECORD_NOTE = re.compile(r"\b(?:superseded|moved to)\b", re.I)
SOURCE_PATH = re.compile(r"(?<![A-Za-z0-9_-])sources/[^\s)`\"'<>\]|;,（）。，、；：「」『』]*")
SESSION_KEY = re.compile(r"(?<![A-Za-z0-9_-])([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*)-(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]*)"
                         r" ([UAQ]\d+)((?:, ?[UAQ]\d+)*)")
# Past phrasings as the tools read them (the docstring's *Past phrasings*)
SIMILAR = 0.85
PHRASING_LABEL = re.compile(r"\*\*([^*]+?):?\*\*:?")
PHRASING_ANGLE = re.compile(r"\*\*([a-z0-9][a-z0-9-]*):?\*\*:?\s*(?=[\"“「『])", re.I)


Error = logfiles.LogError   # what the subcommands raise for a file or git call they cannot read


# ---- Reading an entry ----

def entry_paths(root):
    """The entries under root, as sorted /-separated paths relative to it; [] without entries/."""
    folder = os.path.join(root, "entries")
    if not os.path.isdir(folder):
        return []
    return [p for p in ("entries/" + n for n in sorted(os.listdir(folder)))
            if ENTRY_PATH.fullmatch(p) and os.path.isfile(os.path.join(root, p))]


read = logfiles.read_text


def section(text, heading):
    """A `## <heading>` section's text, HTML comments and blank lines dropped, joined by spaces."""
    body = logfiles.strip_comments(logfiles.section(text, heading) or "")
    return " ".join(line.strip() for line in body.splitlines() if line.strip())


def tokens(text):
    """Estimated tokens: ASCII characters / 2.7 plus 4/3 per other character, rounded up."""
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return -(-(ascii_chars * 40 + (len(text) - ascii_chars) * 144) // 108)


slug_of = logfiles.entry_slug


def norm_period(value):
    return re.sub(r"\s*[–—]\s*|\s+-\s+", " – ", (value or "").strip())


def before(a, b):
    """a is earlier than b, two YYYY-MM or YYYY-MM-DD dates compared at the coarser of the two."""
    n = min(len(a), len(b))
    return a[:n] < b[:n]


def parse_period(value):
    """(start, end) as YYYY-MM or YYYY-MM-DD strings, end None when ongoing; None when it does not
    parse."""
    m = PERIOD.fullmatch(norm_period(value))
    if not m:
        return None
    start, end = m.group(1), m.group(2)
    if end and end.lower() == "ongoing":
        return start, None
    end = end or start
    return None if before(end, start) else (start, end)


def one_value(value):
    """A field that takes one value: its text, or "" for a list (check's front matter line names it)."""
    return value if isinstance(value, str) else ""


class Entry:
    def __init__(self, root, path):
        self.path = path
        self.text = read(os.path.join(root, path))
        self.fields = front_matter(self.text)
        self.slug = slug_of(path)
        self.series = one_value(self.fields.get("series"))
        self.period = norm_period(one_value(self.fields.get("period")))
        span = parse_period(self.period)
        self.span = span
        self.ongoing = bool(span) and span[1] is None
        self.gap_ongoing = bool(re.fullmatch(r"GAP – ongoing", self.period, re.I))   # start month unknown
        self.tags = as_list(self.fields.get("tags"))
        self.one_line = section(self.text, "One line")
        self.tokens = tokens(self.text)
        self.over = self.tokens > THRESHOLD


def load(root):
    return [Entry(root, p) for p in entry_paths(root)]


def over_threshold(entries):
    """The `entry over threshold` line of each entry past THRESHOLD (tools/check.py prints them too)."""
    return ["entry over threshold: %s %d tokens" % (e.path, e.tokens) for e in entries if e.over]


# ---- README rows ----

def readme_rows(root):
    """{entry path: row cells by lowercase header} for README.md's rows that link an entry file,
    and the link targets that name no file."""
    path = os.path.join(root, "README.md")
    rows, missing = {}, []
    if not os.path.isfile(path):
        return rows, missing
    for table in logfiles.md_tables(read(path)):
        if "entry" not in table.header:
            continue
        for row in table.dicts():
            m = re.search(r"\[(.*)\]\(\.?/?(entries/[^)#\s]+)(?:#[^)]*)?\)", row.get("entry", ""))
            if not m:
                continue
            row["title"] = m.group(1)
            target = m.group(2)
            if os.path.isfile(os.path.join(root, target)):
                rows[target] = row
            else:
                missing.append(target)
    return rows, missing


# ---- Subcommands ----

def cmd_list(root, series=None):
    rows, _ = readme_rows(root)
    for e in load(root):
        if series and e.series != series:
            continue
        row = rows.get(e.path)
        status = row.get("status", "") if row else "- (no README row)"
        print("%s: slug %s; series %s; type %s; org %s; period %s%s; tags %s; status %s; tokens %d%s;"
              " one line: %s" % (e.path, e.slug, e.series or "-", e.fields.get("type") or "-",
                                 e.fields.get("org") or "-", e.period or "-", " (ongoing)" if e.ongoing else "",
                                 ", ".join(e.tags) or "-", status or "-", e.tokens,
                                 " (over threshold)" if e.over else "", e.one_line or "-"))
    return 0


def months_before(day, n):
    month = day.month - n
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    for d in (day.day, 30, 29, 28):
        try:
            return datetime.date(year, month, d)
        except ValueError:
            continue


def findings(root, today, entries=None):
    """[(the entry paths a finding names, its line)], and the `check:` lines; a finding that names
    no entry has ()."""
    entries = load(root) if entries is None else entries
    out = [((e.path,), line) for e, line in zip([e for e in entries if e.over], over_threshold(entries))]
    slugs = {e.slug for e in entries}
    series = {}
    for e in entries:
        if e.series:
            if not e.span:
                out.append(((e.path,), "series part with an unreadable period: %s %r (YYYY-MM – YYYY-MM or"
                                       " YYYY-MM – ongoing)" % (e.path, e.period)))
            series.setdefault(e.series, []).append(e)
            if e.series not in slugs:
                out.append(((e.path,), "series names no entry: %s series %s" % (e.path, e.series)))
            if not e.one_line:
                out.append(((e.path,), "series part with an empty One line: %s" % e.path))
    for name, parts in series.items():
        ongoing = [p.path for p in parts if p.ongoing]
        if len(ongoing) > 1:
            out.append((tuple(ongoing), "series %s has more than one ongoing part: %s" % (name, ", ".join(ongoing))))
        spans = [p for p in parts if p.span]
        for i, a in enumerate(spans):
            for b in spans[i + 1:]:
                a_end, b_end = a.span[1] or "9999-99-99", b.span[1] or "9999-99-99"
                same_start = not before(a.span[0], b.span[0]) and not before(b.span[0], a.span[0])
                if same_start or (before(a.span[0], b_end) and before(b.span[0], a_end)):
                    out.append(((a.path, b.path), "series %s has overlapping periods: %s (%s), %s (%s)"
                                % (name, a.path, a.period, b.path, b.period)))
    rows, missing = readme_rows(root)
    out += [((), "README row names a missing file: %s" % t) for t in missing]
    for e in entries:
        row = rows.get(e.path)
        if row is None:
            out.append(((e.path,), "no README row: %s" % e.path))
            continue
        differ = []
        if row["title"] != (e.fields.get("title") or ""):
            differ.append("title %r, front matter %r" % (row["title"], e.fields.get("title") or ""))
        if "period" in row and norm_period(row["period"]) != e.period:
            differ.append("period %r, front matter %r" % (row["period"], e.period))
        if "type" in row and row["type"] != (e.fields.get("type") or ""):
            differ.append("type %r, front matter %r" % (row["type"], e.fields.get("type") or ""))
        only_readme = sorted(set(as_list(row.get("tags"))) - set(e.tags))
        if only_readme:
            differ.append("tags not in front matter: %s" % ", ".join(only_readme))
        out += [((e.path,), "README row differs: %s: %s" % (e.path, d)) for d in differ]
        if "status" in row and not re.match(r"(%s)\b" % "|".join(STATUSES), row["status"]):
            out.append(((e.path,), "README row status unknown: %s %r (starts with %s)"
                        % (e.path, row["status"], ", ".join(STATUSES))))
    cutoff = months_before(today, 2)
    for e in entries:
        updated = e.fields.get("last_updated") or ""
        if not (e.ongoing or e.gap_ongoing):
            continue
        try:
            day = datetime.date.fromisoformat(updated)
        except (ValueError, TypeError):   # TypeError: a list
            out.append(((e.path,), "ongoing entry with no readable last_updated: %s %r" % (e.path, updated)))
            continue
        if day < cutoff:
            out.append(((e.path,), "ongoing entry not updated in over two months: %s last_updated %s"
                        % (e.path, updated)))
    targets = resume_targets(root)
    for e in entries:
        out += [((e.path,), line) for line in shape_findings(e, targets, cutoff)]
    notes = []
    for path, text, skip in read_files(root, entries):
        tag = (path,) if ENTRY_PATH.fullmatch(path) else ()
        found, checks = text_findings(root, path, text, skip)
        out += [(tag, line) for line in found]
        notes += [(tag, line) for line in checks]
    out += [((), line) for line in source_folder_findings(root)]
    return out, notes


def cmd_check(root, today, consolidated=None):
    entries = load(root)
    found, notes = findings(root, today, entries)   # every entry: a series part's findings need the others
    if consolidated is not None:
        entries = [e for e in entries if e.path in consolidated]
        found = [f for f in found if set(f[0]) & set(consolidated)]
        notes = [n for n in notes if set(n[0]) & set(consolidated)]
        for e in entries:
            found += [((e.path,), line) for line in consolidated_findings(e)]
    for _, line in found:
        print(line)
    for _, line in notes:
        print(line)
    if found:
        return 1
    print("OK: %d entries, no findings" % len(entries))
    return 0


# ---- An entry's shape ----

def lines_of(text):
    """The text's lines, numbered from 1, with HTML comments blanked (their line ends kept)."""
    bare = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return list(enumerate(bare.splitlines(), 1))


def section_numbered(text, heading, level=2):
    """[(line number, line)] of a `<level #> <heading>` section's lines, comments blanked, up to the
    next heading of that level or a higher one other than `# `; [] without the section."""
    out, inside = [], False
    for n, line in lines_of(text):
        h = re.match(r"(#{1,6})[ \t]", line)
        if inside:
            if h and 2 <= len(h.group(1)) <= max(level, 2):
                break
            out.append((n, line))
        elif re.fullmatch(r"#{%d}[ \t]+%s[ \t]*" % (level, re.escape(heading)), line):
            inside = True
    return out


def content(lines):
    """The lines that hold something other than a placeholder, stripped."""
    return [(n, line.strip()) for n, line in lines if line.strip() and not PLACEHOLDER.fullmatch(line.strip())]


def resume_targets(root):
    """The target names in outputs/resumes/: its .tex and .md files' names, lowercased."""
    folder = os.path.join(root, "outputs", "resumes")
    names = os.listdir(folder) if os.path.isdir(folder) else []
    return {n.rsplit(".", 1)[0].lower() for n in names if n.endswith((".tex", ".md"))}


def period_ok(value):
    return bool(parse_period(value) or re.fullmatch(r"%s – GAP\b.*" % DATE, value))


def date_ok(value):
    try:
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and bool(datetime.date.fromisoformat(value))
    except ValueError:
        return False


def front_matter_findings(e):
    out = []
    checks = [("type", lambda v: v in TYPES, " | ".join(TYPES)),
              ("visibility", lambda v: v in VISIBILITIES, " | ".join(VISIBILITIES + ("GAP",))),
              ("period", lambda v: period_ok(norm_period(v)), "YYYY-MM – YYYY-MM or YYYY-MM – ongoing"),
              ("series", lambda v: True, "one slug")]
    if not (e.ongoing or e.gap_ongoing):
        checks.append(("last_updated", date_ok, "YYYY-MM-DD"))
    for field, ok, allowed in checks:
        if field not in e.fields:
            continue
        value = e.fields[field]
        if field == "series" and value == []:   # read as no series, as it always was
            continue
        if isinstance(value, str) and (GAP_VALUE.match(value) or ok(value.strip())):
            continue
        out.append("front matter: %s %s %r not allowed (%s)" % (e.path, field, value, allowed))
    return out


def repo_root(url):
    """(the repo's root URL, whether url goes past it into a page), or None for a URL that names no
    GitHub or GitLab repo."""
    m = logfiles.REPO_URL.match(url)
    if not m:
        return None
    segments = m.group(1).rstrip("/").split("/")
    for i, seg in enumerate(segments):
        if i >= 2 and seg in logfiles.URL_END:
            return url[:m.start(1)] + "/".join(segments[:i]), True
    return url[:m.start(1)] + re.sub(r"\.git$", "", "/".join(segments)), False


def link_findings(e):
    items = e.fields.get("links")
    items = items if isinstance(items, list) else [items] if items else []
    urls = [u for item in items for u in URL.findall(item)]
    roots = {r[0].lower() for r in map(repo_root, urls) if r and not r[1]}
    out = []
    for url in urls:
        r = repo_root(url)
        if r and r[1]:
            out.append("link not a repo root: %s %s; root %s%s"
                       % (e.path, url, r[0], "" if r[0].lower() in roots else ", missing from links"))
    return out


def phrasing_findings(e, targets):
    out = []
    for n, s in content(section_numbered(e.text, "Past phrasings")):
        m = PHRASING_FORM.fullmatch(s)
        if not m:
            out.append("past phrasing not in form: %s:%d: %s" % (e.path, n, s[:100]))
            continue
        if ";" in m.group(2):
            out.append("past phrasing with more than one citation or a note: %s:%d: (%s)" % (e.path, n, m.group(2)))
        if m.group(1).lower() != "general" and m.group(1).lower() not in targets:
            out.append("past phrasing angle unknown: %s:%d %s (general, or a target in outputs/resumes/: %s)"
                       % (e.path, n, m.group(1), ", ".join(sorted(targets)) or "none"))
    return out


def conflict_findings(path, lines):
    out = []
    for n, s in content(lines):
        body = s[2:].strip() if s.startswith("- ") else s
        if s.startswith("#"):
            continue
        if body.startswith("Settled:"):
            if not SETTLED_FORM.fullmatch(body):
                out.append("settled line not in a template form: %s:%d: %s" % (path, n, body[:100]))
        elif not body.startswith("Open:"):
            out.append("conflict line not Open or Settled: %s:%d: %s" % (path, n, s[:100]))
    return out


def pending_findings(e, cutoff):
    out = []
    for n, s in content(section_numbered(e.text, "Pending")):
        m = PENDING_LINE.match(s)
        try:
            day = datetime.date.fromisoformat(m.group(1)) if m else None
        except ValueError:
            day = None
        if day is None:
            out.append("pending line without a date: %s:%d: %s" % (e.path, n, s[:100]))
        elif day < cutoff:
            out.append("pending older than two months: %s:%d: %s" % (e.path, n, s[:100]))
    return out


def results_findings(e):
    out, columns = [], None
    for n, line in section_numbered(e.text, "Results and evidence"):
        if not line.strip().startswith("|"):
            columns = None
            continue
        cells = logfiles.md_cells(line)
        if columns is None:
            head = [c.strip("*` ").lower() for c in cells]
            columns = [(i, h) for i, h in enumerate(head) if h in ("how measured", "caveat", "source")]
            continue
        if logfiles.is_rule(cells) or GAP_VALUE.match(cells[0]):   # a GAP row marks the gap itself
            continue
        empty = [h for i, h in columns if i >= len(cells) or not cells[i]]
        if empty:
            out.append("results row missing %s: %s:%d %s" % (", ".join(empty), e.path, n, cells[0][:60] or "-"))
    return out


def shape_findings(e, targets, cutoff):
    out = front_matter_findings(e) + link_findings(e)
    if any(re.fullmatch(r"## Log[ \t]*", line) for _, line in lines_of(e.text)):
        out.append("old section ## Log: %s (read `tools/entries.py --help` › Old sections before you edit it)" % e.path)
    out += pending_findings(e, cutoff)
    out += conflict_findings(e.path, section_numbered(e.text, "Conflicts"))
    out += phrasing_findings(e, targets)
    out += results_findings(e)
    return out


def consolidated_findings(e):
    out = ["pending not empty: %s" % e.path] if content(section_numbered(e.text, "Pending")) else []
    lines = [line for _, line in section_numbered(e.text, "My contribution")]
    for label in CONTRIBUTION:
        bold = re.compile(r"\*\*%s\b(?! not\b)[^*]*:\*\*" % re.escape(label[:-1]))   # `**I led, with help from AI agents:**` too
        at = next((i for i, l in enumerate(lines) if bold.search(l)), None)
        after = lines[at][bold.search(lines[at]).end():].strip() if at is not None else ""
        under = []   # the indented lines under the label, up to the next line that is not
        for l in lines[at + 1:] if at is not None else []:
            if l.strip() and not l[:1].isspace():
                break
            under.append(l.strip())
        if at is None or not (after or any(under)):
            out.append("contribution category missing: %s %s" % (e.path, label))
    return out


def read_files(root, entries):
    """(path, text, the sections not read) for each file modes read for facts: the entries,
    profile.md, direction.md and stories.md."""
    out = [(e.path, e.text, {(2, "Past phrasings"), (2, "Conflicts")}) for e in entries]
    for path, skip in (("profile.md", {(3, "Conflicts")}), ("direction.md", set()),
                       ("stories.md", {(2, "Application questions")})):
        if os.path.isfile(os.path.join(root, path)):
            out.append((path, read(os.path.join(root, path)), skip))
    return out


def text_findings(root, path, text, skip):
    """The output citation and source key findings of one file (and profile.md's Conflicts lines'),
    and its record notes."""
    out = conflict_findings(path, section_numbered(text, "Conflicts", 3)) if path == "profile.md" else []
    notes, headings = [], {}   # {level: the heading above at that level}
    body_start = logfiles.split_front_matter(text, True)[1]
    for n, line in lines_of(text):
        h = re.match(r"(#{2,6})[ \t]+(.+?)[ \t]*$", line)
        if h:
            headings = {k: v for k, v in headings.items() if k < len(h.group(1))}
            headings[len(h.group(1))] = h.group(2)
            continue
        if n <= body_start or not line.strip() or set(headings.items()) & skip:
            continue
        s = line.strip()
        if OUTPUT_PATH.search(s):
            notes.append("check: output citation: %s:%d: %s" % (path, n, s[:160]))
        if RECORD_NOTE.search(s):
            notes.append("check: record note: %s:%d: %s" % (path, n, s[:160]))
        out += ["source key unresolved: %s:%d %s" % (path, n, key) for key in unresolved_keys(root, s)]
    return out, notes


def unresolved_keys(root, line):
    out = []
    for m in SOURCE_PATH.finditer(line):
        token = re.split(r"[\s(\[<（「]", line[:m.start()])[-1]
        if "://" in token or "@" in token:   # inside a URL, or a repo key's path
            continue
        p = re.sub(r"(#.*|:\d+(?:-\d+)?)$", "", m.group(0).rstrip(".:"))
        if not (p.endswith("/") or "*" in p or re.search(r"\.[A-Za-z0-9]+$", p)):   # prose: `data sources/tools`
            continue
        if p.rstrip("/") == logfiles.INBOX or p.startswith(logfiles.INBOX + "/") or p == "sources/":
            continue
        full = os.path.join(root, *p.rstrip("/").split("/"))
        if not (glob.glob(full) if "*" in p else os.path.exists(full)):
            out.append("%s (no such file)" % p)
    for m in SESSION_KEY.finditer(line):
        agent, date, slug = m.group(1), m.group(2), m.group(3)
        key = "%s-%s-%s" % (agent, date, slug)
        path = os.path.join(root, "sources", agent, "%s-%s.md" % (date, slug))
        if not os.path.isfile(path):
            out.append("%s %s (no excerpt sources/%s/%s-%s.md)" % (key, m.group(4), agent, date, slug))
            continue
        try:
            heads = {h for h in re.findall(r"^## ([UAQ]\d+)\b", read(path), re.M)}
        except (OSError, UnicodeDecodeError):
            out.append("%s %s (sources/%s/%s-%s.md is not UTF-8 text)" % (key, m.group(4), agent, date, slug))
            continue
        for turn in [m.group(4)] + re.findall(r"[UAQ]\d+", m.group(5)):
            if turn not in heads:
                out.append("%s %s (no ## %s in sources/%s/%s-%s.md)" % (key, turn, turn, agent, date, slug))
    return out


def first_line(path):
    """A file's text from its first non-blank character, '' for one that is not UTF-8 text."""
    try:
        return read(path).lstrip()
    except (OSError, UnicodeDecodeError):
        return ""


def source_folder_findings(root):
    folder = os.path.join(root, "sources")
    if not os.path.isdir(folder):
        return []
    keys = os.path.join(folder, "keys.md")
    out = []
    if os.path.isfile(keys) and not first_line(keys) and os.path.getsize(keys):
        return ["source key unresolved: sources/keys.md is not UTF-8 text (save it as UTF-8, then run check again)"]
    keys = first_line(keys) if os.path.isfile(keys) else ""
    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if not os.path.isdir(full) or name.startswith(".") or name in ("inbox", "resumes"):
            continue
        mds = [f for f in os.listdir(full) if f.endswith(".md")]
        heads = [first_line(os.path.join(full, f)) for f in mds]
        heads = [h for h in heads if h]   # a file that is not UTF-8 is the key check's finding
        if heads and all(re.match(r"# .+ session \d{4}-\d{2}-\d{2}", h) for h in heads):
            continue   # session excerpts: their keys are SKILL.md › Source keys'
        if "sources/%s/" % name not in keys:
            out.append("source folder not in keys.md: sources/%s/" % name)
    return out


def entry_arg(root, arg):
    """The entry's /-separated path relative to root, from a path relative to root or the cwd."""
    for base in (root, os.getcwd()):
        full = os.path.abspath(os.path.join(base, arg))
        try:
            rel = os.path.relpath(full, os.path.abspath(root)).replace(os.sep, "/")
        except ValueError:   # another drive (Windows)
            continue
        if os.path.isfile(full) and ENTRY_PATH.fullmatch(rel):
            return rel
    raise Error("not an entry of %s: %s (an entry is entries/<name>.md, not _template.md)" % (root, arg))


def ref_lines(root, path):
    """(file, line number, line) for each line of the Log's other files that names the entry's file
    (refs)."""
    pattern = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(os.path.basename(path)[:-3]))
    for rel in log_files(root):
        if rel == path:
            continue
        try:
            text = read(os.path.join(root, rel))
        except (UnicodeDecodeError, OSError):
            continue
        if "\0" in text:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                line = line.strip()
                yield rel, n, line if len(line) <= 300 else line[:300] + " ..."


def cmd_refs(root, path):
    for rel, n, line in ref_lines(root, path):
        print("%s:%d: %s" % (rel, n, line))
    for rel in talking_points_files(root):
        try:
            tp = TalkingPoints(root, rel)
        except (UnicodeDecodeError, OSError):
            continue
        if path not in tp.entries:
            continue
        bare = re.sub(r"<!--.*?-->", "", tp.text, flags=re.S)
        pending = [t for _, t in LINK.findall(bare) if link_path("stories", t) == (path, "pending")]
        print("talking points: %s: type %s%s" % (rel, tp.type or "-", "; links #pending" if pending else ""))
    return 0


git = logfiles.git


def links(text):
    found = []
    for m in URL.finditer(text):
        url = m.group(0).rstrip(".,;:")
        while url.endswith(")") and url.count(")") > url.count("("):   # a link's or a sentence's close
            url = url[:-1].rstrip(".,;:")
        found.append(url)
    for m in MD_TARGET.finditer(text):
        target = m.group(1)
        if not target.startswith(("http://", "https://", "#", "mailto:")):
            found.append(target)
    return list(dict.fromkeys(found))


LINK_SECTIONS = ("Pending", "Log", "Past phrasings", "Conflicts")   # links-since's `section link:` lines; Log is an old Pending


def last_consolidate(root, path, slug):
    """(sha, subject) of the last commit touching path whose subject is consolidate(<slug>...)."""
    for line in git(root, "log", "--format=%H %s", "--", path).splitlines():
        sha, _, subject = line.partition(" ")
        m = re.match(r"consolidate\(([^)]*)\)", subject)
        if m and slug in [s.strip() for s in m.group(1).split(",")]:
            return sha, subject
    return None, None


def cmd_links_since(root, path):
    sha, subject = last_consolidate(root, path, slug_of(path))
    text = read(os.path.join(root, path))
    now = links(logfiles.strip_comments(text))
    if sha:
        before = set(links(logfiles.strip_comments(git(root, "show", "%s:./%s" % (sha, path)))))
        print("since: %s %s" % (sha[:12], subject))
    else:
        before = set()
        print("since: no consolidate(%s) commit touches %s; every link is listed" % (slug_of(path), path))
    shown = set()
    for heading in LINK_SECTIONS:
        for link in links("\n".join(line for _, line in section_numbered(text, heading))):
            if link not in shown:
                print("section link: %s: %s" % (heading, link))
                shown.add(link)
    for link in now:
        if link not in before and link not in shown:
            print("link: %s" % link)
    return 0


# ---- Past phrasings ----

def phrasings(text):
    """(angle, wording) for each line under ## Past phrasings, the angle as the docstring's *Past
    phrasings* gives it: the line's own prefix first, then the label line in force."""
    m = re.search(r"^## Past phrasings[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    out, angle = [], None
    for line in (m.group(1).splitlines() if m else []):
        s = line.strip()
        head = re.fullmatch(r"(?:-\s*)?" + PHRASING_LABEL.pattern, s) or re.fullmatch(r"###\s+(.+?):?", s)
        if head:
            angle = head.group(1).strip().lower()
        elif s.startswith("- ") and not re.match(r"(none yet|GAP:)", s[2:].strip(), re.I):
            body, own = s[2:].strip(), None
            inline = PHRASING_ANGLE.match(body)
            if inline:
                own, body = inline.group(1).strip().lower(), body[inline.end():].strip()
            out.append((own or angle, body))
    return out


def words(body):
    return re.findall(r"[\w.%+-]+", re.sub(r"\s*\([^()]*\)\s*$", "", body).lower())


def similar(a, b):
    """The difflib ratio of two (angle, wording) lines' words, lowercased, the trailing (citation)
    dropped; 0 for two different angles."""
    if a[0] and b[0] and a[0] != b[0]:
        return 0.0
    return difflib.SequenceMatcher(None, words(a[1]), words(b[1]), autojunk=False).ratio()


# ---- Rulings against outputs ----

SCAN_REPORT = re.compile(r"\d{4}-\d{2}-\d{2}-scan(?:-\d+)?\.md")


def outputs(root):
    """[(output, its provenance file, its files)], as rulings-hits' docstring says."""
    out = []
    apps = os.path.join(root, "outputs", "applications")
    for name in sorted(os.listdir(apps)) if os.path.isdir(apps) else []:
        base = "outputs/applications/%s/" % name
        if os.path.isdir(os.path.join(apps, name)):
            files = [base + f for f in ("resume.tex", "answers.md", "provenance.md") if os.path.isfile(os.path.join(apps, name, f))]
            out.append((base, base + "provenance.md", files))
    resumes = os.path.join(root, "outputs", "resumes")
    for target in sorted(resume_targets(root)) if os.path.isdir(resumes) else []:
        names = {n.lower(): n for n in os.listdir(resumes)}
        files = ["outputs/resumes/" + names[target + ext] for ext in (".md", ".tex") if target + ext in names]
        md = [f for f in files if f.endswith(".md")]
        out.append(("outputs/resumes/%s" % target, md[0] if md else None, files))
    reports = os.path.join(root, "outputs", "reports")
    for name in sorted(os.listdir(reports)) if os.path.isdir(reports) else []:
        if name.endswith(".md") and not SCAN_REPORT.fullmatch(name) and os.path.isfile(os.path.join(reports, name)):
            path = "outputs/reports/" + name
            out.append((path, path, [path]))
    return out


def plain(text, tex=False):
    """Text as rulings-hits matches it: LaTeX markup dropped (tex), lowercase, without `*`, curly
    apostrophes straight, each run of
    hyphens, dashes and spaces one space, and no space between a number and its unit."""
    if tex:
        text = re.sub(r"(?<!\\)%.*$", "", text, flags=re.M)
        text = re.sub(r"\\[,;:! ]", " ", text)
        text = re.sub(r"\\([%&$#_{}])", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text).replace("{", "").replace("}", "").replace("~", " ")
    text = text.replace("*", "").replace("`", "").replace("’", "'").replace("‘", "'").casefold()
    text = re.sub(r"[\s\-‐‑‒–—]+", " ", text)
    return re.sub(r"(\d) (?=[^\W\d_]|%)", r"\1", text)


def output_text(root, path):
    """(the file's plain text, joined by spaces, and each line's start offset in it), a `## Risks...`
    section left out."""
    try:
        text = read(os.path.join(root, path))
    except (OSError, UnicodeDecodeError):
        return None, []
    joined, starts, risks = "", [], False
    for line in text.splitlines():
        if line.startswith("## "):
            risks = line.startswith("## Risks")
        starts.append(len(joined))
        joined += (plain(line, path.endswith(".tex")).strip() if not risks else "") + " "
    return joined, starts


def rulings(root, entries):
    """[(file, line number, the Settled line)] of each entry, then profile.md."""
    out = []
    files = [(e.path, e.text, 2) for e in entries]
    if os.path.isfile(os.path.join(root, "profile.md")):
        files.append(("profile.md", read(os.path.join(root, "profile.md")), 3))
    for path, text, level in files:
        for n, s in content(section_numbered(text, "Conflicts", level)):
            body = s[2:].strip() if s.startswith("- ") else s
            if body.startswith("Settled:"):
                out.append((path, n, body))
    return out


def cited_entries(entries, provenance_text):
    """(the entries the provenance rows name, [(line, the cell or piece that names none)]), as
    rulings-hits' docstring says."""
    keys = []
    for e in entries:
        title = plain(" ".join(as_list(e.fields.get("title"))))
        head = re.split(r" (?:—|–|-|\() |: ", title)[0].strip()
        keys.append((e, {plain(e.slug), plain(os.path.basename(e.path)[:-3])}, title, head))
    words_re = r"(?<![\w-])%s(?![\w-])"

    def names(piece):
        """The entries a piece of a cell names, or None when it names nothing (profile and direction
        name no entry, but are named)."""
        found = {e.path for p in re.findall(r"entries/([^\s)#|]+?)\.md", piece)
                 for e, *_ in keys if os.path.basename(e.path)[:-3] == os.path.basename(p)}
        name = plain(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", piece).split("›")[0])
        name = re.sub(r"\(.*$", "", name).strip(" :")
        for part in [name] + [p.strip() for p in name.split(":") if p.strip()]:
            if len(part) < 2:
                continue
            for e, stems, title, title_head in keys:
                if part in stems or re.search(words_re % re.escape(part), title) or (
                        len(title_head) >= 3 and re.search(words_re % re.escape(title_head), part)):
                    found.add(e.path)
        if found or re.search(r"\b(?:profile|direction)\b", piece, re.I):
            return found
        return None

    named, unresolved = set(), []
    for n, cells, head in logfiles.provenance_rows(provenance_text):
        cols = [i for i, h in enumerate(head) if re.search("entry", h, re.I)] or range(len(cells))
        pieces = [p.strip() for i in cols if i < len(cells) for p in cells[i].split(";") if p.strip()]
        results = [(p, names(p)) for p in pieces]
        if all(r is None for _, r in results):
            unresolved.append((n, " | ".join(cells[i] for i in cols if i < len(cells))[:120]))
            continue
        for p, r in results:
            if r is None and "›" in p:   # it names an entry, one no entry matches; a bare section is the row's
                unresolved.append((n, p[:120]))
            named |= r or set()
    return named, unresolved


def ruling_quotes(line):
    """[(side, quoted wording, the wording as matched)] of a Settled line's ruling, its (why) and (source) left out: side is
    `right` or `wrong` (`use "A", not "B"`, `both`), `do-not-use`, or `context` (`use "A" for ...`)."""
    ruling = line[len("Settled:"):].strip()
    for _ in range(2):   # the trailing (<why>). (<source>), so a parenthesis inside the ruling stays
        tail = ruling.rstrip(" .")
        if not tail.endswith(")"):
            break
        depth = 0
        for i in range(len(tail) - 1, -1, -1):
            depth += {")": 1, "(": -1}.get(tail[i], 0)
            if depth == 0:
                ruling = tail[:i].rstrip()
                break
        else:
            break
    wrong_from = re.search(r"(?:^|[,;] )not ", re.sub(r"[\"“「『][^\"”」』]*[\"”」』]", lambda m: "x" * len(m.group(0)), ruling))
    out = []
    for m in QUOTE.finditer(ruling):
        text = next(g for g in m.groups() if g)
        if ruling.startswith("do not use"):
            side = "do-not-use"
        elif ruling.startswith("both"):
            side = "right"
        elif wrong_from:
            side = "wrong" if m.start() > wrong_from.start() else "right"
        else:
            side = "context"
        out.append((side, text, plain(text).strip()))
    return out


def quote_pattern(q):
    """A wording as a regex on plain text: whole words where it starts or ends with a letter or digit."""
    edge = lambda c: c.isascii() and c.isalnum()
    body = r" +".join(re.escape(w) for w in q.split(" "))   # an empty line between two words of it adds a space
    return (r"(?<![a-z0-9])" if edge(q[0]) else "") + body + (r"(?![a-z0-9])" if edge(q[-1]) else "")


def cmd_rulings_hits(root):
    entries = load(root)
    found = rulings(root, entries)
    for path, n, line in found:
        print("ruling: %s:%d: %s" % (path, n, line))
    quotes = [ruling_quotes(line) for _, _, line in found]
    pairs = hits = 0
    outs = outputs(root)
    for name, prov, files in outs:
        texts = {f: output_text(root, f) for f in files}
        for f in [f for f, t in texts.items() if t[0] is None]:
            print("unreadable: %s (not UTF-8 text: read it yourself against every ruling)" % f)
            del texts[f]
        named, unresolved = set(), []
        prov_text = None
        if prov and os.path.isfile(os.path.join(root, prov)):
            try:
                prov_text = read(os.path.join(root, prov))
            except (OSError, UnicodeDecodeError):
                prov_text = None
        if prov_text is not None and logfiles.provenance_rows(prov_text):
            named, unresolved = cited_entries(entries, prov_text)
        else:
            print("no provenance: %s" % name)
        for n, cell in unresolved:
            print("unresolved: %s:%d: %s" % (prov, n, cell))
        for k, (path, n, _) in enumerate(found):
            found_hits = []
            spans = {f: [] for f in texts}   # the right side's matches, which hold a wrong side's text
            for side, raw, q in sorted(quotes[k], key=lambda t: t[0] != "right"):
                if len(q) < 2:
                    continue
                for f, (joined, starts) in texts.items():
                    matches = list(re.finditer(quote_pattern(q), joined))
                    if side == "right":
                        spans[f] += [m.span() for m in matches]
                    else:
                        matches = [m for m in matches if not any(a <= m.start() and m.end() <= b for a, b in spans[f])]
                    if matches:
                        line = max(i for i, s in enumerate(starts, 1) if s <= matches[0].start())
                        found_hits.append('hit %s %s:%d "%s"' % (side, f, line, raw))
            if path in named or path == "profile.md" or found_hits:
                pairs += 1
                hits += len(found_hits)
                print("check: %s against %s:%d%s" % (name, path, n, "".join("; " + h for h in found_hits)))
    print("OK: %d outputs, %d rulings, %d pairs, %d hits" % (len(outs), len(found), pairs, hits))
    return 0


# ---- Stories ----

story_slug = logfiles.question_slug


def link_path(base, target):
    """A link target as a /-separated path relative to the Log's root, and its anchor ('' without);
    base is the /-separated folder of the file that holds the link."""
    path, _, anchor = target.partition("#")
    if not path or path.startswith(("http://", "https://", "mailto:")):
        return None, anchor
    return posixpath.normpath(posixpath.join(base, path)), anchor


class Story:
    """One item of an index cell or a Talking points file: kind `entry`, `other` (links a file
    outside entries/) or `unlinked`."""
    def __init__(self, text, base):
        self.text = text.strip()
        rest = self.text
        self.markers = []
        while MARKER.match(rest):
            m = MARKER.match(rest)
            self.markers += [v.strip() for v in m.group(1).split(",") if v.strip()]
            rest = rest[m.end():]
        m = LINK.match(rest)
        self.label, self.path, self.anchor, self.summary = "", None, "", rest
        if m:
            self.label = m.group(1).replace("\\|", "|")
            self.path, self.anchor = link_path(base, m.group(2))
            rest = rest[m.end():].lstrip()
            while MARKER.match(rest):   # a marker written after the link
                n = MARKER.match(rest)
                self.markers += [v.strip() for v in n.group(1).split(",") if v.strip()]
                rest = rest[n.end():]
            self.summary = re.sub(r"^\s*[—–-]+\s*", "", rest).strip()
        self.kind = ("entry" if self.path and ENTRY_PATH.fullmatch(self.path)
                     else "other" if self.path else "unlinked")
        self.key = (self.path + ("#" + self.anchor if self.anchor else "")) if self.path else self.text

    def unfinished(self):
        return any(m.lower() in UNFINISHED for m in self.markers)


class Row:
    def __init__(self, type_cell, stories_cell):
        m = re.fullmatch(LINK.pattern, type_cell.strip())
        self.type = (m.group(1) if m else type_cell).replace("\\|", "|").strip()
        target = link_path("", m.group(2))[0] if m else None
        self.talking = target if target and re.fullmatch(r"stories/[^/]+\.md", target) else None
        items = [s for s in STORY_SPLIT.split(stories_cell.replace("\\|", "|")) if s.strip(" ;")]
        self.items = [Story(s.strip().rstrip(";"), "") for s in items]
        self.stories = [s for s in self.items if s.kind == "entry"]


def story_index(root):
    """The rows of stories.md's Story index (the first table before any `## ` heading); None when
    stories.md is missing or holds no table with the header `| Question type | Stories |`."""
    path = os.path.join(root, "stories.md")
    if not os.path.isfile(path):
        return None
    found = False
    for table in logfiles.md_tables(read(path)):
        if table.section is not None or table.header[:2] != ["question type", "stories"]:
            continue
        found = True
        if table.rows:
            return [Row(cells[0], cells[1] if len(cells) > 1 else "") for _, cells in table.rows]
    return [] if found else None


def first_rows(rows):
    """{question type: its first row}, in index order: a later row with the same type is ignored."""
    out = {}
    for row in rows:
        out.setdefault(row.type, row)
    return out


class TalkingPoints:
    def __init__(self, root, path):
        self.path = path
        self.text = read(os.path.join(root, path))
        fields = front_matter(self.text)
        self.type = fields.get("type") or ""
        self.confirmed = fields.get("confirmed") or ""
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?", self.confirmed)
        self.day, self.time = None, (m and m.group(2)) or "00:00"
        try:
            if m:
                datetime.time.fromisoformat(self.time)
                self.day = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            pass
        m = re.search(r"^confirmed:.*$", self.text, re.M)
        self.confirmed_line = m.group(0).rstrip("\r") if m else ""
        base = posixpath.dirname(path)
        stories = logfiles.section(self.text, "Stories")
        listed = re.findall(r"^\s*\d+\.\s+(.*\S)", logfiles.strip_comments(stories), re.M) if stories else []
        self.stories = [s for s in (Story(t, base) for t in listed) if s.kind == "entry"]
        bare = re.sub(r"<!--.*?-->", "", self.text, flags=re.S)
        self.entries = sorted({p for p in (link_path(base, t)[0] for _, t in LINK.findall(bare))
                               if p and ENTRY_PATH.fullmatch(p)})


def talking_points_files(root):
    folder = os.path.join(root, "stories")
    if not os.path.isdir(folder):
        return []
    return ["stories/" + n for n in sorted(os.listdir(folder))
            if n.endswith(".md") and os.path.isfile(os.path.join(folder, n))]


def pending_key(key):
    """True for a key that links an entry's `## Pending` section, shared by all its pending Stories."""
    return key.partition("#")[2] == "pending"


def lead_story(root, row):
    if row.talking and os.path.isfile(os.path.join(root, row.talking)):
        stories = TalkingPoints(root, row.talking).stories
        if stories:
            return stories[0].key
    return row.stories[0].key if row.stories else None


def experiences(root):
    """{entry path: the path that names its experience}: a series part maps to its first part (the
    entry whose slug the series names, series field or not, else the earliest part); any other
    entry is left out."""
    entries = load(root)
    by_slug = {e.slug: e.path for e in entries}
    parts = {}
    for e in entries:
        if e.series:
            parts.setdefault(e.series, []).append(e.path)
    out = {}
    for slug, paths in parts.items():
        first = by_slug.get(slug, min(paths))
        out.update((p, first) for p in paths + [first])
    return out


def cmd_story_coverage(root, questions, talking=False, applications=False):
    rows = story_index(root)
    out = []
    if rows is None:
        out.append("no story index: %s" % ("stories.md has no table headed | Question type | Stories |"
                                           if os.path.isfile(os.path.join(root, "stories.md")) else "no stories.md"))
        rows = []
    out += ["duplicate question type: %s" % r.type for r in rows if r is not first_rows(rows)[r.type]]
    rows = list(first_rows(rows).values())
    exp = experiences(root)
    types_of, key_types, core = {}, {}, set()
    for row in rows:
        for path in dict.fromkeys(exp.get(s.path, s.path) for s in row.stories):
            types_of.setdefault(path, []).append(row.type)
        for key in dict.fromkeys(s.key for s in row.stories if not pending_key(s.key)):
            key_types.setdefault(key, []).append(row.type)
        core.update(exp.get(s.path, s.path) for s in row.stories if "core" in (m.lower() for m in s.markers))
    core = [p for p in types_of if p in core]
    print("core stories: %d%s" % (len(core), "".join("; %s (%d types)" % (p, len(types_of[p])) for p in core)))
    print("types per entry: %s" % ("; ".join("%s (%d types)" % (p, len(t)) for p, t in
                                            sorted(types_of.items(), key=lambda i: -len(i[1]))) or "-"))
    for row in rows:
        if not row.stories:
            others = len(row.items)
            out.append("type with no story: %s%s" % (row.type, " (items without an entry link: %d)" % others
                                                     if others else ""))
        elif all(s.unfinished() for s in row.stories):
            out.append("type with only raw or pending stories: %s" % row.type)
        for s in row.stories:
            if not os.path.isfile(os.path.join(root, s.path)):
                out.append("index names a missing entry: %s: %s" % (row.type, s.path))
    for key, types in key_types.items():
        if len(types) > MAX_TYPES_PER_STORY:
            out.append("story under too many types: %s in %d types (more than %d): %s"
                       % (key, len(types), MAX_TYPES_PER_STORY, " | ".join(types)))
    if not CORE_RANGE[0] <= len(core) <= CORE_RANGE[1]:
        out.append("core stories outside %d–%d: %d" % (CORE_RANGE[0], CORE_RANGE[1], len(core)))
    linked = {}
    for row in rows:
        if not row.talking:
            continue
        linked[row.talking] = row
        if not os.path.isfile(os.path.join(root, row.talking)):
            out.append("row links a missing talking points file: %s: %s" % (row.type, row.talking))
    for path in talking_points_files(root):
        if path not in linked:
            out.append("talking points file no row links: %s" % path)
            continue
        tp = TalkingPoints(root, path)
        if tp.type != linked[path].type:
            out.append("talking points type differs from its row: %s: type %s, row %s"
                       % (path, tp.type, linked[path].type))
        if not tp.day:
            out.append("talking points with no readable confirmed date: %s %s" % (path, tp.confirmed or "-"))
    by_type = {row.type: row for row in rows}
    leads = {}
    for q in questions:
        m = re.fullmatch(r"(.*?)=(entries/\S+)", q)
        qtype, chosen = (m.group(1).strip(), m.group(2)) if m else (q.strip(), None)
        row = by_type.get(qtype)
        if row is None:
            out.append("interview type not in stories.md: %s" % qtype)
            continue
        key = chosen or lead_story(root, row)
        if key is None:
            out.append("interview type with no story: %s" % qtype)
            continue
        print("interview: %s: leads with %s" % (qtype, key))
        if not pending_key(key):
            leads.setdefault(key, []).append(qtype)
    for key, types in leads.items():
        if len(types) > MAX_PER_INTERVIEW:
            out.append("story carries too many questions in one interview: %s leads %d (more than %d): %s"
                       % (key, len(types), MAX_PER_INTERVIEW, " | ".join(types)))
    if talking:
        out += talking_points_findings(root)
    if applications:
        out += application_findings(root)
    for line in out:
        print(line)
    if out:
        return 1
    print("OK: %d question types, no findings" % len(rows))
    return 0


def section_lines(text, heading):
    """A `## <heading>` section's `- ` bullets, HTML comments dropped."""
    return logfiles.bullets(logfiles.section(text, heading) or "")


def cmd_story_candidates(root, question_type):
    rows = list(first_rows(story_index(root) or []).values())
    row = next((r for r in rows if r.type == question_type), None)
    entries = {e.path: e for e in load(root)}
    print("type: %s" % question_type)
    if row is None:
        print("type not in stories.md: %s (a new type; every entry is a candidate)" % question_type)
    talking = row.talking if row else None
    if talking and os.path.isfile(os.path.join(root, talking)):
        tp = TalkingPoints(root, talking)
        print("talking points: %s confirmed %s" % (talking, tp.confirmed or "-"))
        for n, s in enumerate(tp.stories, 1):
            print("talking points %d: %s; label %s; %s" % (n, s.key, s.label or "-", s.summary or "-"))
    else:
        print("talking points: none; a new file is %s" % (talking or "stories/%s.md" % story_slug(question_type)))

    def series_of(path):
        e = entries.get(path)
        return e.series if e else ""

    indexed = set()
    for s in row.stories if row else []:
        indexed.add(s.path)
        e = entries.get(s.path)
        print("indexed: %s; markers %s; series %s; label %s; %s"
              % (s.key, ", ".join(s.markers) or "-", series_of(s.path) or "-", s.label or "-",
                 "summary: %s" % s.summary if s.summary
                 else "one line: %s" % (e.one_line if e and e.one_line else "-")))
    for s in row.items if row else []:
        if s.kind != "entry":
            print("indexed, not an entry: %s" % s.text)
    indexed_series = {series_of(p): p for p in indexed if series_of(p)}
    types_of = {}
    for r in rows:
        for s in r.stories:
            types_of.setdefault(s.path, []).append(r.type)
    for path, e in entries.items():
        if path in indexed:
            continue
        part = indexed_series.get(e.series) if e.series else None
        print("not yet indexed: %s; series %s; indexed under %s;%s one line: %s"
              % (path, e.series or "-", " | ".join(dict.fromkeys(types_of.get(path, []))) or "-",
                 " another part indexed here: %s;" % part if part else "", e.one_line or "-"))
    for path, e in entries.items():
        for line in section_lines(e.text, "Pending"):
            print("pending: %s: %s" % (path, line if len(line) <= 300 else line[:300] + " ..."))
    return 0


def talking_points_arg(root, arg):
    for base in (root, os.getcwd()):
        full = os.path.abspath(os.path.join(base, arg))
        try:
            rel = os.path.relpath(full, os.path.abspath(root)).replace(os.sep, "/")
        except ValueError:   # another drive (Windows)
            continue
        if os.path.isfile(full) and re.fullmatch(r"stories/[^/]+\.md", rel):
            return rel
    raise Error("not a Talking points file of %s: %s (one is stories/<slug>.md)" % (root, arg))


def cmd_story_stale(root, path):
    tp = TalkingPoints(root, path)
    if not tp.day:
        raise Error("%s has no readable confirmed: date (YYYY-MM-DD, or YYYY-MM-DD HH:MM): %r"
                    % (path, tp.confirmed))
    # Counts whole lines: a plain -S would miss `confirmed: D` written over `confirmed: D HH:MM`, and -G
    # would take a commit that only changed the line's trailing space or line ending, or moved it.
    exact = "^%s[[:space:]]*$" % re.sub(r"([.\[\]()*+?{}|^$\\])", r"\\\1", tp.confirmed_line.rstrip())
    sha = git(root, "log", "-1", "--format=%H %s", "--pickaxe-regex", "-S" + exact, "--", path).strip()
    if sha:
        sha, _, subject = sha.partition(" ")
        since = sha[:12]
        print("since: %s %s" % (since, subject))
        span = ["%s..HEAD" % sha]
    else:
        since = "%s %s" % (tp.day.isoformat(), tp.time)
        print("since: %s (no commit wrote %s's %r)" % (since, path, tp.confirmed_line))
        span = ["--since=%s:00" % since]
    out = []
    for entry in tp.entries:
        if not os.path.isfile(os.path.join(root, entry)):
            out.append("missing entry: %s" % entry)
            continue
        for line in git(root, "log", "--format=%h %cd %s", "--date=short", *span, "--", entry).splitlines():
            out.append("changed: %s %s" % (entry, line))
        if git(root, "status", "--porcelain", "--", entry).strip():
            out.append("uncommitted: %s" % entry)
    for line in out:
        print(line)
    if out:
        return 1
    print("OK: %d entries unchanged since %s" % (len(tp.entries), since))
    return 0


def wordings_files(root):
    """[(path, question type, [wording, ...])] for each file in stories/wordings/, by path."""
    folder = os.path.join(root, *WORDINGS.split("/"))
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        path = WORDINGS + "/" + name
        if not name.endswith(".md") or not os.path.isfile(os.path.join(root, path)):
            continue
        text = read(os.path.join(root, path))
        body = logfiles.strip_comments("\n".join(text.splitlines()[logfiles.split_front_matter(text, True)[1]:]))
        lines = [line[2:].strip() for line in body.splitlines() if line.startswith("- ")]
        qtype = front_matter(text).get("type")
        out.append((path, qtype if isinstance(qtype, str) else "", [w for w in lines if w]))
    return out


def one_line(wording):
    return " ".join(wording.split())


def cmd_story_wording_add(root, question_type, wording):
    wording = one_line(wording)
    if not wording:
        raise Error("an empty wording")
    if front_matter("---\ntype: %s\n---" % question_type).get("type") != question_type:
        raise Error("a question type a type: line cannot hold as it is (a ` #`, quotes or brackets"
                    " around it), so neither a wordings file nor a Talking points file can name it: %s;"
                    " a renamed row needs its Talking points file's type: renamed too" % question_type)
    if question_type not in first_rows(story_index(root) or []):
        raise Error("question type not in stories.md's Story index: %s (add its row first, written as"
                    " the index writes it)" % question_type)
    files = wordings_files(root)
    found = next((f for f in files if f[1] == question_type), None)
    if found:
        path, _, kept = found
        if any(one_line(w).casefold() == wording.casefold() for w in kept):
            print("already kept: %s: %s" % (path, wording))
            return 0
        full = os.path.join(root, path)
        with open(full, "rb") as f:
            raw = f.read()
        eol = b"\r\n" if b"\r\n" in raw else b"\n"
        with open(full, "ab") as f:
            f.write((b"" if not raw or raw.endswith(b"\n") else eol) + ("- " + wording).encode("utf-8") + eol)
    else:
        taken = {f[0] for f in files}
        slug = story_slug(question_type) or "type"
        path = next(p for p in ("%s/%s%s.md" % (WORDINGS, slug, "-%d" % n if n > 1 else "") for n in range(1, 1000))
                    if p not in taken and not os.path.exists(os.path.join(root, p)))
        os.makedirs(os.path.join(root, *WORDINGS.split("/")), exist_ok=True)
        with open(os.path.join(root, path), "w", encoding="utf-8", newline="\n") as f:
            f.write("---\ntype: %s\n---\n\n# %s\n\n- %s\n" % (question_type, question_type, wording))
    print("added: %s: %s" % (path, wording))
    return 0


def cmd_story_wordings(root, types):
    index = list(first_rows(story_index(root) or []))
    files = wordings_files(root)
    rank = {t: n for n, t in enumerate(index)}
    files.sort(key=lambda f: (rank.get(f[1], len(rank)), f[0]))
    for t in types:
        if not any(f[1] == t and f[2] for f in files):
            print("no wordings: %s" % t)
    for path, qtype, kept in files:
        if types and qtype not in types:
            continue
        if not qtype:
            print("wordings file with no type: %s" % path)
            continue
        if qtype not in rank:
            print("wordings type not in stories.md: %s: %s" % (path, qtype))
        for w in kept:
            print("wording: %s | %s" % (qtype, w))
    return 0


def drop_unfinished(item, names=UNFINISHED):
    """The item with `raw` and `pending` (or the markers names gives) taken out of its markers
    (before the link and right after it), and the markers dropped, in their order."""
    dropped, parts, pos = [], [], 0

    def strip(m):
        keep = []
        for v in (v.strip() for v in m.group(1).split(",")):
            if v and v.lower() in names:
                if v.lower() not in (d.lower() for d in dropped):
                    dropped.append(v)
            elif v:
                keep.append(v)
        space = m.group(0)[len(m.group(0).rstrip()):]
        return "*(%s)*%s" % (", ".join(keep), space) if keep else ""

    while MARKER.match(item, pos):
        m = MARKER.match(item, pos)
        parts.append(strip(m))
        pos = m.end()
    link = LINK.match(item, pos)
    if link:
        parts.append(item[pos:link.end()])
        pos = link.end()
        space = re.match(r"\s*", item[pos:]).group(0)
        if MARKER.match(item, pos + len(space)):
            parts.append(space)
            pos += len(space)
            while MARKER.match(item, pos):
                m = MARKER.match(item, pos)
                parts.append(strip(m))
                pos = m.end()
    out = "".join(parts) + item[pos:]
    if not item[pos:]:   # a marker the item ended with: no space left before the cell's end
        out = out.rstrip() + item[len(item.rstrip()):]
    return out, dropped


def cmd_story_finish(root, path):
    stories_md = os.path.join(root, "stories.md")
    entry_text = read(os.path.join(root, path))
    anchors = heading_anchors(entry_text) - {"pending"}
    out, edited = [], 0
    if not os.path.isfile(stories_md):
        out.append("no story index: no stories.md")
    else:
        with open(stories_md, "rb") as f:
            raw = f.read()
        bom = raw.startswith(b"\xef\xbb\xbf")
        lines = raw.decode("utf-8-sig").splitlines(keepends=True)
        header, found, in_rows = None, False, False
        for i, full in enumerate(lines):
            line = full.rstrip("\r\n")
            if line.startswith("## "):
                break
            if not line.strip().startswith("|"):
                if found and in_rows:
                    break
                header = None
                continue
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if header is None:
                header = [c.strip("*` ").lower() for c in cells]
                found = found or header[:2] == ["question type", "stories"]
                continue
            if set("".join(cells)) <= set("-: ") or header[:2] != ["question type", "stories"]:
                continue
            in_rows = True
            bounds = [m.start() for m in re.finditer(r"(?<!\\)\|", line)]
            if len(bounds) < 2:
                continue
            row = Row(cells[0], "")
            start = bounds[1] + 1
            end = bounds[2] if len(bounds) > 2 else len(line.rstrip())   # a row may leave off its last |
            cell = line[start:end]
            pieces = re.split(r"(;\s+(?=\*\(|\[))", cell)
            for n in range(0, len(pieces), 2):
                text = pieces[n]
                lead = text[:len(text) - len(text.lstrip())]
                s = Story(text.strip().rstrip(";"), "")
                if s.kind == "other" and s.path.startswith("sources/") and any(
                        m.lower() == "raw" for m in s.markers) and re.search(
                        r"(?<![\w-])%s(?![\w.-])" % re.escape(s.path), entry_text):
                    out.append("raw source: %s: %s: %s" % (row.type, s.path, s.text))
                anchor = urllib.parse.unquote(s.anchor).lower()
                if s.path != path or not (s.unfinished() or anchor == "pending"):
                    continue
                if anchor not in anchors:
                    out.append("links no section: %s: %s" % (row.type, s.text))
                    continue
                new, dropped = drop_unfinished(text.lstrip())
                pieces[n] = lead + new
                edited += 1
                print("dropped: %s: %s: %s" % (row.type, ", ".join(dropped), new.strip()))
            lines[i] = line[:start] + "".join(pieces) + line[end:] + full[len(line):]
        if not found:
            out.append("no story index: stories.md has no table headed | Question type | Stories |")
        elif edited:
            with open(stories_md, "wb") as f:
                f.write((b"\xef\xbb\xbf" if bom else b"") + "".join(lines).encode("utf-8"))
    for line in out:
        print(line)
    if out:
        return 1
    print("OK: %d items edited" % edited)
    return 0


class StoriesFile:
    """stories.md as lines, for edits in place: each write changes one cell, or adds one row, and
    leaves every other byte as it was (a byte order mark and the line ends included)."""

    def __init__(self, root):
        self.path = os.path.join(root, "stories.md")
        if not os.path.isfile(self.path):
            raise Error("no stories.md in %s" % root)
        self.bom, self.lines = read_lines(self.path)
        self.tables = logfiles.md_tables("".join(self.lines))

    def index(self):
        """The Story index table, as story_index() picks it, or None."""
        found = [t for t in self.tables if t.section is None and t.header[:2] == ["question type", "stories"]]
        return next((t for t in found if t.rows), found[0] if found else None)

    def answers(self):
        """The Application questions table: the first under `## Application questions` with a Question
        type and a Scope column, or None."""
        return next((t for t in self.tables if (t.section or "").lower() == "application questions"
                     and t.header[:1] == ["question type"] and "scope" in t.header), None)

    def cell(self, n, col):
        """Row line n's col-th cell as written, stripped ('' for a row short of it)."""
        spans = logfiles.md_cell_spans(self.lines[n - 1])
        return self.lines[n - 1][spans[col][0]:spans[col][1]].strip() if col < len(spans) else ""

    def set_cell(self, n, col, text):
        """Write row line n's col-th cell as ` <text> ` (` ` when empty), adding cells a short row lacks."""
        line = self.lines[n - 1]
        spans = logfiles.md_cell_spans(line)
        if col < len(spans):
            a, b = spans[col]
            new = " %s" % text if text else ""
            self.lines[n - 1] = line[:a] + (new + " " if line[b:b + 1] == "|" else new or " ") + line[b:]
            return
        body = line.rstrip("\r\n").rstrip()
        if not body.endswith("|") or body.endswith("\\|"):
            body += " |"
        self.lines[n - 1] = body + " |" * (col - len(spans)) + (" %s |" % text if text else " |") + ends(line)

    def add_row(self, table, cells):
        """Add `| <cell> | ... |` after the table's last row; its line number."""
        at = table.rows[-1][0] if table.rows else table.line + 1
        eol = line_end(self.lines)
        if not ends(self.lines[at - 1]):
            self.lines[at - 1] += eol
            eol = ""
        self.lines.insert(at, "|" + "|".join(" %s " % c if c else " " for c in cells) + "|" + eol)
        return at + 1

    def save(self):
        write_lines(self.path, self.bom, self.lines)


def index_row(sf, question_type):
    """(line number, Row) of the type's first row in the Story index; Error when it has none."""
    table = sf.index()
    if table is None:
        raise Error("stories.md has no table headed | Question type | Stories | (the Story index)")
    for n, cells in table.rows:
        if Row(cells[0], "").type == question_type:
            return n, Row(cells[0], cells[1] if len(cells) > 1 else "")
    raise Error("question type not in stories.md's Story index: %s (matched exactly; a new type gets its"
                " row from story-type-add)" % question_type)


def same_link(path, anchor, s):
    return s.path == path and urllib.parse.unquote(s.anchor).lower() == urllib.parse.unquote(anchor).lower()


def question_type_ok(question_type, taken):
    """Error unless question_type can name a new row: one line, no `|`, `;` or `]`, one a `type:` line
    holds as it is, and no row's type already (case aside)."""
    if not question_type.strip() or question_type != one_line(question_type):
        raise Error("a question type is one line, with no leading, trailing or repeated spaces: %r" % question_type)
    if any(c in question_type for c in "|;]"):   # `]` would be escaped in its row's Talking points link
        raise Error("a question type holds no |, ; or ]: %s" % question_type)
    if front_matter("---\ntype: %s\n---" % question_type).get("type") != question_type:
        raise Error("a question type a type: line cannot hold as it is (a ` #`, quotes or brackets around"
                    " it): %s" % question_type)
    same = [t for t in taken if t.casefold() == question_type.casefold()]
    if same:
        raise Error("stories.md has this question type already: %s" % same[0])


def cmd_story_type_add(root, question_type):
    sf = StoriesFile(root)
    table = sf.index()
    if table is None:
        raise Error("stories.md has no table headed | Question type | Stories | (the Story index)")
    question_type_ok(question_type, [Row(cells[0], "").type for _, cells in table.rows])
    n = sf.add_row(table, [question_type, ""])
    sf.save()
    print("added: stories.md:%d: %s" % (n, sf.lines[n - 1].rstrip("\r\n")))
    return 0


def story_item(root, target, markers, label, summary):
    """(path, anchor, the index item to write) for a Story that links target; Error on a bad one."""
    path, anchor = link_path("", target)
    if path is None or path.startswith(".."):
        raise Error("a Story links a file of the Log: %s" % target)
    if re.search(r"[\s()]", target):
        raise Error("a Story's link holds no spaces or parentheses (the index could not read it): %s" % target)
    full = os.path.join(root, path)
    if ENTRY_PATH.fullmatch(path):
        if not os.path.isfile(full):
            raise Error("no such entry: %s" % path)
        text = read(full)
        names = logfiles.heading_names(text)
        key = urllib.parse.unquote(anchor).lower()
        if anchor and key not in names:
            raise Error("%s has no section with the anchor #%s (its anchors: %s)"
                        % (path, anchor, ", ".join(sorted(names)) or "none"))
        if not label:
            title = front_matter(text).get("title")
            label = (title if isinstance(title, str) and title else logfiles.entry_slug(path)) + (
                " › " + names[key] if anchor else "")
        if key == "pending" and "pending" not in markers:
            markers = markers + ["pending"]
    elif path.startswith("sources/"):
        if not os.path.exists(full):
            raise Error("no such source: %s" % path)
        if not label:
            raise Error("a Story that links a source needs --label <label>")
    else:
        raise Error("a Story links an entry (entries/<file>.md#<anchor>) or a source (sources/...): %s" % target)
    if summary and (summary != one_line(summary) or STORY_SPLIT.search(summary)):
        raise Error("a summary is one line, with no `; [` or `; *(` (they start the next Story): %r" % summary)
    label = re.sub(r"([\]|])", r"\\\1", one_line(label).replace("\\", ""))
    item = "%s[%s](%s)%s" % ("*(%s)* " % ", ".join(markers) if markers else "", label,
                             path + ("#" + anchor if anchor else ""),
                             " — " + summary.replace("|", "\\|") if summary else "")
    return path, anchor, item


def cmd_story_add(root, question_type, target, markers, label, summary):
    for m in markers:
        if m not in MARKERS:
            raise Error("--marker takes raw, pending or core: %s" % m)
    path, anchor, item = story_item(root, target, list(dict.fromkeys(markers)), label, summary)
    sf = StoriesFile(root)
    n, row = index_row(sf, question_type)
    for s in row.items:
        if same_link(path, anchor, s):
            print("already linked: %s: %s" % (row.type, s.text))
            return 0
    cell = re.sub(r"(?<=[)\s]);\s*$", "", sf.cell(n, 1)).rstrip()   # a stray separator, not an entity's `;`
    sf.set_cell(n, 1, cell + "; " + item if cell else item)
    sf.save()
    print("added: %s: %s" % (row.type, item))
    return 0


def index_pieces(sf):
    """[(line number, Row, the Stories cell as written split into items and separators)] for each row
    of the Story index, for edits in place."""
    table = sf.index()
    if table is None:
        raise Error("stories.md has no table headed | Question type | Stories | (the Story index)")
    return [(n, Row(cells[0], ""), re.split("(%s)" % STORY_SPLIT.pattern, sf.cell(n, 1))) for n, cells in table.rows]


def add_core(item):
    """The item with `core` added to its first marker group, or a new `*(core)* ` before it."""
    m = re.match(r"\*\(([^)*]+)\)\*", item)
    return "*(%s, core)*%s" % (m.group(1).strip(), item[m.end():]) if m else "*(core)* " + item


def cmd_story_core(root, path, on):
    exp = experiences(root)
    first = exp.get(path, path)
    parts = {p for p, f in exp.items() if f == first} | {path}
    sf = StoriesFile(root)
    rows = index_pieces(sf)
    linked = [(n, row, pieces, k) for n, row, pieces in rows for k in range(0, len(pieces), 2)
              if Story(pieces[k].strip().rstrip(";"), "").path in parts]
    core = [(row, pieces[k].strip()) for n, row, pieces, k in linked
            if "core" in (m.lower() for m in Story(pieces[k].strip().rstrip(";"), "").markers)]
    if on:
        if core:
            for row, text in core:
                print("already core: %s: %s" % (row.type, text))
            return 0
        own = [x for x in linked if Story(x[2][x[3]].strip().rstrip(";"), "").path == path]
        if not (own or linked):
            print("not indexed: %s (index one of its Stories with story-add first)" % path)
            return 1
        n, row, pieces, k = (own or linked)[0]
        text = pieces[k]
        lead = text[:len(text) - len(text.lstrip())]
        pieces[k] = lead + add_core(text.lstrip())
        sf.set_cell(n, 1, "".join(pieces).strip())
        sf.save()
        print("core on: %s: %s" % (row.type, pieces[k].strip()))
        return 0
    if not core:
        print("not core: %s" % path)
        return 0
    for n, row, pieces, k in linked:
        text = pieces[k]
        if "core" not in (m.lower() for m in Story(text.strip().rstrip(";"), "").markers):
            continue
        lead = text[:len(text) - len(text.lstrip())]
        new, _ = drop_unfinished(text.lstrip(), ("core",))
        pieces[k] = lead + new
        sf.set_cell(n, 1, "".join(pieces).strip())
        print("core off: %s: %s" % (row.type, new.strip()))
    sf.save()
    return 0


def cmd_story_confirm(root, path, question_type, now):
    tp = TalkingPoints(root, path)
    full = os.path.join(root, path)
    bom, lines = read_lines(full)
    if not front_matter_span(lines)[1]:
        raise Error("%s has no front matter (--- lines) to hold confirmed:" % path)
    sf = None
    if question_type is not None:
        if tp.type != question_type:
            print("type differs: %s: type %s, --type %s (write the row's type in its type: line)"
                  % (path, tp.type or "-", question_type))
            return 1
        sf = StoriesFile(root)
        n, row = index_row(sf, question_type)
        if row.talking and row.talking != path and os.path.isfile(os.path.join(root, row.talking)):
            print("row links another file: %s: %s" % (question_type, row.talking))
            return 1
    set_field(lines, "confirmed", now)
    write_lines(full, bom, lines)
    print("confirmed: %s: %s" % (path, now))
    if sf is not None:
        if row.talking == path:
            print("row already links: %s: %s" % (question_type, path))
        else:
            sf.set_cell(n, 0, "[%s](%s)" % (re.sub(r"([\]|])", r"\\\1", question_type), path))
            sf.save()
            print("row linked: %s: %s" % (question_type, path))
    return 0


SCOPES = ("shared", "per-angle", "per-company")
POINTER_SPLIT = re.compile(r";\s+(?=(?:[a-z0-9][a-z0-9-]*:\s*)?\[)", re.I)
POINTER = re.compile(r"(?:([a-z0-9][a-z0-9-]*):\s*)?\[((?:[^\]\\]|\\.)*)\]\(([^)\s]+)\)\s*", re.I)


class AnswerRow:
    """A row of stories.md's Application questions table: type, scope, its cells by column name, and
    pointers [(angle or '', label, path, the text as written)] (text that is no link left out)."""

    def __init__(self, table, cells):
        get = dict(zip(table.header, cells))
        self.type = cells[0]
        self.scope = get.get("scope", "").strip("` ").lower()
        self.answer_from = get.get("answer from", "")
        self.direction = next((v for k, v in get.items() if "direction" in k), "")
        self.col = pointer_column(table)
        self.pointers = [p for p in (pointer(t) for t in POINTER_SPLIT.split(cells[self.col] if self.col < len(cells)
                                                                             else "")) if p]


def pointer_column(table):
    """The Application questions column that holds the pointers: Approved answer, else the last."""
    return table.header.index("approved answer") if "approved answer" in table.header else len(table.header) - 1


def pointer(text):
    m = POINTER.fullmatch(text.strip())
    return (m.group(1) or "", m.group(2).replace("\\]", "]"), m.group(3), text.strip()) if m else None


def answer_rows(sf):
    table = sf.answers()
    return table, ([] if table is None else [(n, AnswerRow(table, cells)) for n, cells in table.rows])


def cmd_answer_row(root, question_type, angle):
    table, rows = answer_rows(StoriesFile(root))
    row = next((r for _, r in rows if r.type == question_type), None)
    if row is None:
        print("no row: %s%s" % (question_type, "" if table else " (stories.md has no Application questions table)"))
        if rows:
            print("row types: %s" % " | ".join(r.type for _, r in rows))
        return 0
    print("row: %s; scope %s" % (row.type, row.scope or "-"))
    print("answer from: %s" % (row.answer_from or "-"))
    print("direction: %s" % (row.direction or "-"))
    shown = row.pointers
    if row.scope == "per-angle" and angle:
        shown = ([p for p in row.pointers if p[0].lower() == angle.lower()]
                 + [p for p in row.pointers if p[0].lower() == "general" != angle.lower()])
    for a, label, path, _ in shown:
        print("pointer: %s: %s; label %s" % (a or "-", path, label or "-"))
    if not shown:
        print("pointer: none%s" % (" for %s" % " or ".join([angle] + (["general"] if angle.lower() != "general" else []))
                                    if row.scope == "per-angle" and angle else ""))
    return 0


def cmd_answer_row_add(root, question_type, scope):
    sf = StoriesFile(root)
    table, rows = answer_rows(sf)
    if table is None:
        raise Error("stories.md has no Application questions table (a `## Application questions` section"
                    " with a | Question type | Scope | ... | table)")
    question_type_ok(question_type, [r.type for _, r in rows])
    n = sf.add_row(table, [question_type, scope] + [""] * (len(table.header) - 2))
    sf.save()
    print("added: stories.md:%d: %s" % (n, sf.lines[n - 1].rstrip("\r\n")))
    return 0


def under(path, target):
    """True when path is target, or a file in the folder target names."""
    path, target = path.partition("#")[0], target.partition("#")[0].rstrip("/")
    return path == target or path.startswith(target + "/")


def cmd_answer_set(root, question_type, angle, target, remove):
    sf = StoriesFile(root)
    table, rows = answer_rows(sf)
    found = next(((n, r) for n, r in rows if r.type == question_type), None)
    if found is None:
        print("no row: %s (add it with answer-row-add once the user confirms its scope)" % question_type)
        return 1
    n, row = found
    if row.scope not in SCOPES:
        print("no scope: %s: %s (one of %s)" % (row.type, row.scope or "-", ", ".join(SCOPES)))
        return 1
    if row.scope == "per-company":
        print("per-company row takes no pointer: %s" % row.type)
        return 1 if not remove else 0
    if row.scope == "per-angle" and not angle and not remove:
        raise Error("a per-angle row's pointer needs --angle <angle>")
    target = posixpath.normpath(target.replace("\\", "/"))
    if target.startswith(("../", "/")) or target in ("..", "."):
        raise Error("a pointer links a file of the Log, relative to its root: %s" % target)
    if not remove and not os.path.exists(os.path.join(root, target.partition("#")[0])):
        raise Error("no such answer file: %s" % target)
    parts = re.split("(%s)" % POINTER_SPLIT.pattern, sf.cell(n, row.col))
    items = [("" if k == 0 else parts[k - 1], parts[k]) for k in range(0, len(parts), 2) if parts[k].strip()]

    def mine(text):
        p = pointer(text)
        return p and (row.scope == "shared" or not angle or p[0].lower() == angle.lower())

    if remove:
        gone = [t for _, t in items if mine(t) and under(pointer(t)[2], target)]
        if not gone:
            print("not linked: %s: %s" % (row.type, target))
            return 0
        kept = [(s, t) for s, t in items if t not in gone]
        for t in gone:
            print("removed: %s: %s" % (row.type, t.strip()))
    else:
        new = ("%s: " % angle if row.scope == "per-angle" else "") + "[answer](%s)" % target
        old = [t for _, t in items if mine(t)]
        if len(old) == 1 and pointer(old[0])[2] == target:
            print("unchanged: %s: %s" % (row.type, old[0].strip()))
            return 0
        if old:
            first = next(k for k, (_, t) in enumerate(items) if t == old[0])
            kept = [(s, new) if k == first else (s, t) for k, (s, t) in enumerate(items) if k == first or t not in old]
        else:
            kept = items + [("; ", new)]
        for t in old:
            print("replaced: %s: %s" % (row.type, t.strip()))
        print("set: %s: %s" % (row.type, new))
    text = "".join((s if k else "") + t.strip() for k, (s, t) in enumerate(kept))
    sf.set_cell(n, row.col, text)
    sf.save()
    return 0


def application_findings(root):
    """`application question:` findings for stories.md's Application questions table."""
    if not os.path.isfile(os.path.join(root, "stories.md")):
        return []
    out = []
    for _, row in answer_rows(StoriesFile(root))[1]:
        pre = "application question: %s: " % row.type
        if row.scope not in SCOPES:
            out.append(pre + "no scope (%s): %s" % (", ".join(SCOPES), row.scope or "-"))
        elif row.scope == "shared" and len(row.pointers) > 1:
            out.append(pre + "shared row with %d pointers" % len(row.pointers))
        elif row.scope == "per-company" and row.pointers:
            out.append(pre + "per-company row with %d pointers" % len(row.pointers))
        elif row.scope == "per-angle":
            counts = {}
            for a, _, _, text in row.pointers:
                if not a:
                    out.append(pre + "per-angle pointer with no angle: %s" % text)
                else:
                    counts[a.lower()] = counts.get(a.lower(), 0) + 1
            out += [pre + "per-angle row with %d pointers for %s" % (c, a) for a, c in counts.items() if c > 1]
    return out


def talking_points_findings(root):
    """`talking points sections out of order:` and `talking points over <n> cue lines:` findings."""
    out = []
    for path in talking_points_files(root):
        text = logfiles.strip_comments(read(os.path.join(root, path)))
        found = [h for h in re.findall(r"^## (.+?)[ \t]*$", text, re.M) if h in TALKING_SECTIONS]
        if found != sorted(found, key=TALKING_SECTIONS.index):
            out.append("talking points sections out of order: %s: %s" % (path, " | ".join(found)))
        cues = section_lines(text, "Cue lines")
        if len(cues) > MAX_CUE_LINES:
            out.append("talking points over %d cue lines: %s: %d" % (MAX_CUE_LINES, path, len(cues)))
    return out


# ---- Writing entries and the README table ----

PROSE = ("One line", "Context", "My contribution", "How it works", "Decisions and trade-offs",
         "Dead ends and mistakes", "Results and evidence", "People", "Lessons", "Likely questions")
KEY_SECTIONS = ("One line", "My contribution", "Results and evidence")   # empty: a reason to consolidate
BLOCKING = ("My contribution", "Results and evidence", "Likely questions")   # what common outputs need
MOSTLY_GAP = 5            # of the ten PROSE sections: an entry is mostly GAP (a stub) at this many empty
PENDING_MANY = 5          # pending lines that make log suggest consolidate
NEW_FIELDS = {"title": None, "type": "GAP: type", "period": None, "org": "GAP: organisation",
              "my_role": "GAP: role title", "collaborators": "GAP: collaborators", "tags": [],
              "visibility": "GAP", "links": [], "series": ""}   # None: new requires it
SOURCED = ("org", "my_role", "collaborators", "tags", "visibility")   # the fields new's --field-source cites
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ANGLE = re.compile(r"[a-z0-9][a-z0-9-]*")
NEW_PERIOD = re.compile(r"(GAP|%s) – (GAP|ongoing|%s)|%s" % (DATE, DATE, DATE), re.I)
GAP_WORD = re.compile(r"(?<![\w-])GAP(?![\w-])")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
PHRASING_PARTS = re.compile(r'- \*\*([a-z0-9][a-z0-9-]*):\*\* ["“「『](.*)["”」』] \(((?:[^()]|\([^()]*\))*)\)', re.I)
ENTRY_LINK = re.compile(r"\]\(\.?/?(entries/[^)#\s]+)(?:#[^)]*)?\)")


def read_lines(path):
    """(whether it starts with a byte order mark, its lines with their line ends)."""
    with open(path, "rb") as f:
        raw = f.read()
    return raw.startswith(b"\xef\xbb\xbf"), raw.decode("utf-8-sig").splitlines(keepends=True)


def write_lines(path, bom, lines):
    with open(path, "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + "".join(lines).encode("utf-8"))


def line_end(lines):
    """The line end the file uses: its first line's, LF for a file without one."""
    for line in lines:
        if line.endswith(("\r\n", "\n")):
            return "\r\n" if line.endswith("\r\n") else "\n"
    return "\n"


def ends(line):
    return line[len(line.rstrip("\r\n")):]


def mend_ends(lines, eol, last):
    """After lines moved or were inserted: every line but the last ends with a line end (eol when it
    has none), and the last ends as the file's last line did before (last)."""
    for i in range(len(lines) - 1):
        if not ends(lines[i]):
            lines[i] += eol
    if lines:
        lines[-1] = lines[-1].rstrip("\r\n") + last


def yaml_value(value):
    """A front matter value as written: quoted when the tools would misread it bare."""
    if isinstance(value, list):
        return "[%s]" % ", ".join(yaml_value(v) if not re.search(r"[,\[\]]", v) else '"%s"' % v for v in value)
    if value and (" #" in value or value[0] in "\"'[{" or value.startswith("#")):
        return '"%s"' % value if '"' not in value else "'%s'" % value.replace("'", "''")
    return value


def front_matter_span(lines):
    """(first, end): the indexes of the front matter's lines, lines[first:end]; (0, 0) without one."""
    if not lines or lines[0].strip() != "---":
        return 0, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return 1, i
    return 0, 0


def comment_at(rest):
    """Where a front matter value's ` # comment` starts in the text after `key:`, or None."""
    m = re.match(r"\s*(\"[^\"]*\"|'(?:[^']|'')*')", rest)
    start = m.end() if m else 0
    c = re.search(r"(?:^|\s)#", rest[start:])
    return None if c is None else start + c.start() + (len(c.group(0)) - 1)


def field_line(line, key, value, comment=None):
    """The line `key: <value>`, the old line's comment kept at its column (comment=None) or replaced."""
    rest = line.rstrip("\r\n")[len(key) + 1:]
    at = comment_at(rest)
    if comment is None:
        comment = rest[at:] if at is not None else ""
    col = len(key) + 1 + at if at is not None else 0
    head = ("%s: %s" % (key, yaml_value(value))).rstrip()
    if comment:
        head = head.ljust(col) if len(head) < col - 1 else head + "  "
        head += comment
    return head + ends(line)


def set_field(lines, key, value, comment=None):
    """Write key's value in the front matter in place (comment as field_line takes it), adding the
    line before the closing `---` when the field is missing. False without front matter."""
    first, end = front_matter_span(lines)
    if not end:
        return False
    for i in range(first, end):
        if re.match(r"%s:" % re.escape(key), lines[i]):
            lines[i] = field_line(lines[i], key, value, comment)
            return True
    eol = line_end(lines)
    lines.insert(end, ("%s: %s" % (key, yaml_value(value))).rstrip() + ("  " + comment if comment else "") + eol)
    return True


def section_bounds(lines, heading):
    """(index of the `## <heading>` line, index after its last line) in raw lines, or None; the
    section runs to the next `# ` or `## ` heading outside comments."""
    bare = [line for _, line in lines_of("".join(lines))]
    start = next((i for i, line in enumerate(bare) if re.fullmatch(r"## %s[ \t]*" % re.escape(heading), line)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(bare)) if re.match(r"#{1,2}[ \t]", bare[i])), len(lines))
    return start, end


def append_in_section(lines, bounds, new):
    """Insert the line `new` after the section's last non-blank line; its index."""
    start, end = bounds
    at = max([i for i in range(start, end) if lines[i].strip()] or [start]) + 1
    eol = line_end(lines)
    if not lines[at - 1].endswith(("\n", "\r")):
        lines[at - 1] += eol
    lines.insert(at, new + eol)
    return at


# ---- README.md's Entries table ----

class ReadmeTable:
    """README.md's Entries table: the first table whose header has an Entry column and whose rows link
    an entry (else the first with Entry and Period columns, else the first with Entry), as raw lines: header (its cells,
    lowercased), rule (the index of its rule row) and rows (the indexes of the rows under it)."""

    def __init__(self, root):
        self.path = os.path.join(root, "README.md")
        if not os.path.isfile(self.path):
            raise Error("no README.md in %s" % root)
        self.bom, self.lines = read_lines(self.path)
        tables, i = [], 0
        while i < len(self.lines):
            if self.lines[i].strip().startswith("|"):
                head = [c.strip("*` ").lower() for c in logfiles.md_cells(self.lines[i])]
                j = i + 1
                while j < len(self.lines) and self.lines[j].strip().startswith("|"):
                    j += 1
                if "entry" in head and j > i + 1 and logfiles.is_rule(logfiles.md_cells(self.lines[i + 1])):
                    tables.append((head, i + 1, list(range(i + 2, j))))
                i = j
            else:
                i += 1
        for self.header, self.rule, self.rows in tables:   # the first that links an entry, else the first
            if any(self.entry_of(r) for r in self.rows):
                return
        if tables:
            self.header, self.rule, self.rows = next((t for t in tables if "period" in t[0]), tables[0])
            return
        raise Error("README.md has no table with an Entry column (| Period | Entry | Type | Tags | Status |)")

    def cells(self, i):
        return dict(zip(self.header, logfiles.md_cells(self.lines[i])))

    def entry_of(self, i):
        """The entries/ path the row's Entry cell links, or None."""
        m = ENTRY_LINK.search(self.cells(i).get("entry", ""))
        return m.group(1) if m else None

    def save(self):
        write_lines(self.path, self.bom, self.lines)


def date_key(value):
    return value if value and re.fullmatch(DATE, value) else ""


def row_order(period):
    """(group, newest-first keys) for a README row's period: GAP rows first (either end GAP, or a
    period the tools cannot read), then ongoing rows by start, then the rest by end, then start."""
    p = norm_period(period)
    m = re.fullmatch(r"(%s) – (ongoing|%s)" % (DATE, DATE), p, re.I) or re.fullmatch(r"(%s)()" % DATE, p)
    if not m or not parse_period(p):
        known = [d for d in re.findall(DATE, p)]
        return 0, (known[-1] if known else "", "")
    start, end = m.group(1), m.group(2) or m.group(1)
    if end.lower() == "ongoing":
        return 1, (start, "")
    return 2, (end, start)


def block_order(periods):
    """row_order for a block of rows: one row, or a series' rows. A series sorts by its whole
    period: with a GAP (or unreadable) part, in the GAP group by the newest date any part sorts
    by; else, with an ongoing part, by its earliest start; else by its latest end, then its
    earliest start. For one row it is that row's row_order."""
    keys = [row_order(p) for p in periods]
    if len(keys) == 1:
        return keys[0]
    starts = [k[0] if g == 1 else k[1] for g, k in keys if g]
    if any(g == 0 for g, _ in keys):
        return 0, (max(k[0] for _, k in keys), "")
    if any(g == 1 for g, _ in keys):
        return 1, (min(starts), "")
    return 2, (max(k[0] for _, k in keys), min(starts))


def part_order(period):
    """A series part's newest-first key inside its block: ongoing parts first, then by the newest
    date the period holds, then its oldest (a GAP end or start counts as unknown, not first)."""
    p = norm_period(period)
    dates = re.findall(DATE, p)
    return bool(re.search(r"ongoing", p, re.I)), max(dates, default=""), min(dates, default="")


def sort_rows(rows):
    """[(row line, period[, series])] in the README order: each series' rows in one block, placed
    by block_order and newest part first inside it (part_order); ties in their current order."""
    blocks, at = [], {}
    for r in rows:
        series = r[2] if len(r) > 2 else None
        if not series:
            blocks.append([r])
            continue
        if series not in at:
            at[series] = len(blocks)
            blocks.append([])
        blocks[at[series]].append(r)
    keyed = []
    for b in blocks:
        if len(b) > 1:
            b = sorted(b, key=lambda r: part_order(r[1]), reverse=True)   # stable, so ties keep their order
        keyed.append((block_order([r[1] for r in b]), b))
    keyed = sorted(keyed, key=lambda kb: kb[0][1], reverse=True)
    return [r for _, b in sorted(keyed, key=lambda kb: kb[0][0]) for r in b]


def row_series(root, path):
    """The `series` of the entry a README row links, or None (no series, or no file to read)."""
    try:
        return one_value(front_matter(read(os.path.join(root, path))).get("series")) or None
    except (OSError, UnicodeError, ValueError):
        return None


def entry_rows(root, table):
    """(slots, [(row line, period, series)]) for the table's rows that link an entry."""
    slots = [i for i in table.rows if table.entry_of(i)]
    return slots, [(table.lines[i], table.cells(i).get("period", ""), row_series(root, table.entry_of(i)))
                   for i in slots]


def readme_row(root, e, status=None):
    """Write e's README row from its front matter: replace the row that links it, or add one; place
    it above the first entry row it sorts before (sort_rows), and when the table was in order, move
    its series' rows with it as one block. Prints `<added|replaced|unchanged>: README.md:<n>: <row>`."""
    table = ReadmeTable(root)
    at = next((i for i in table.rows if table.entry_of(i) == e.path), None)
    old = table.cells(at) if at is not None else {}
    if status is None:
        if at is None:
            raise Error("%s has no README row yet: give its --status (%s)" % (e.path, " | ".join(STATUSES)))
        status = old.get("status", "")
    values = {"period": e.period, "entry": "[%s](%s)" % (e.fields.get("title") or "", e.path),
              "type": e.fields.get("type") or "", "tags": ", ".join(e.tags), "status": status}
    eol, last = line_end(table.lines), ends(table.lines[-1])
    new = logfiles.md_row([values[h] if h in values else old.get(h, "") for h in table.header]) + eol
    before_lines = list(table.lines)
    current = entry_rows(root, table)[1]
    in_order = sort_rows(current) == current   # as it stood: a part's old row still holds its series' place
    rows = table.rows
    if at is not None:
        del table.lines[at]
        rows = [i if i < at else i - 1 for i in rows if i != at]
    table.rows = rows
    slots, others = entry_rows(root, table)
    row = (new, values["period"], e.series or None)
    ordered = sort_rows(others + [row])
    after = ordered[ordered.index(row) + 1:]
    place = next((i for i, r in zip(slots, others) if r in after), (rows[-1] + 1) if rows else table.rule + 1)
    table.lines.insert(place, new)
    if in_order:   # a table in order stays in order: the row's series may move as one block
        table.rows = [i if i < place else i + 1 for i in rows] + [place]
        table.rows.sort()
        slots, current = entry_rows(root, table)
        for i, (line, _, _) in zip(slots, sort_rows(current)):
            table.lines[i] = line
        place = table.lines.index(new, table.rule + 1)
    mend_ends(table.lines, eol, last)
    kind = "added" if at is None else "unchanged" if table.lines == before_lines else "replaced"
    if kind != "unchanged":
        table.save()
    print("readme row %s: README.md:%d: %s" % (kind, place + 1, table.lines[place].rstrip("\r\n")))


def cmd_readme_row(root, path, status):
    readme_row(root, Entry(root, path), status)
    return 0


def cmd_readme_sort(root, check_only):
    table = ReadmeTable(root)
    slots, rows = entry_rows(root, table)
    ordered = sort_rows(rows)
    moved = sum(1 for a, b in zip(rows, ordered) if a[0] != b[0])
    if not moved:
        print("OK: %d entry rows in order" % len(rows))
        return 0
    if check_only:
        for i, (a, b) in zip(slots, zip(rows, ordered)):
            if a[0] != b[0]:
                print("out of order: README.md:%d: %s" % (i + 1, table.entry_of(i)))
        return 1
    eol, last = line_end(table.lines), ends(table.lines[-1])
    for i, (line, _, _) in zip(slots, ordered):
        table.lines[i] = line
    mend_ends(table.lines, eol, last)
    table.save()
    print("sorted: %d entry rows, %d moved" % (len(rows), moved))
    return 0


# ---- new, pending-add, period, set-visibility ----

def from_template(root, values, today, sources=None):
    """(byte order mark, lines) of a new entry from entries/_template.md, as `new` writes it: the
    front matter from values (NEW_FIELDS' keys), a field in sources with `# (<its source>)` as its
    comment, the title heading, and `GAP:` in each prose section."""
    sources = sources or {}
    template = os.path.join(root, "entries", "_template.md")
    if not os.path.isfile(template):
        raise Error("no entries/_template.md in %s" % root)
    bom, lines = read_lines(template)
    first, end = front_matter_span(lines)
    for i in range(first, end):
        m = re.match(r"([A-Za-z_]+):", lines[i])
        if not m:
            continue
        key = m.group(1)
        if key == "last_updated":
            lines[i] = field_line(lines[i], key, today.isoformat())
        elif key in sources:
            lines[i] = field_line(lines[i], key, values[key], "# (%s)" % sources[key])
        elif key == "type":   # the template's value is the list of types, not a comment
            lines[i] = ("type: %s" % yaml_value(values[key])) + ends(lines[i])
        elif key in values:
            lines[i] = field_line(lines[i], key, values[key])
    out, heading = [], None
    bare = dict(lines_of("".join(lines)))
    for n, line in enumerate(lines, 1):
        text = bare.get(n, "")
        if heading is None and n > end + 1 and re.match(r"# ", text):
            line = "# %s%s" % (values["title"], ends(line))
            heading = ""
        elif re.match(r"## ", text):
            heading = text[3:].strip()
        if heading in PROSE and re.fullmatch(r"\s*- \*\*[^*]+:\*\*\s*", text):   # My contribution's labels
            line = line.rstrip("\r\n").rstrip() + " GAP:" + ends(line)
        out.append(line)
    for heading in PROSE:   # a section that holds nothing but its comment gets `GAP:`; tables stay as they are
        bounds = section_bounds(out, heading)
        if bounds and not any(text.strip() for n, text in lines_of("".join(out)) if bounds[0] + 1 < n <= bounds[1]):
            append_in_section(out, bounds, "GAP:")
    return bom, out


def cmd_new(root, slug, month, status, fields, sources, today):
    path = "entries/%s-%s.md" % (month, slug)
    full = os.path.join(root, path)
    if os.path.exists(full):
        print("exists: %s (nothing written; extend it, or pick another slug)" % path)
        return 1
    ReadmeTable(root)   # refuse before writing when the row cannot be written
    bom, out = from_template(root, dict(NEW_FIELDS, **fields), today, sources)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    write_lines(full, bom, out)
    print("created: %s" % path)
    readme_row(root, Entry(root, path), status)
    return 0


# ---- split, diff, drop ----

SPLIT_COPY = ("type", "org", "my_role", "collaborators", "tags", "visibility", "links")   # each part's, as the entry has them


def cut_arg(value):
    """(the earlier part's end or None, the date the part starts, part slug, phase) from split's
    `--cut [YYYY-MM[-DD]..]YYYY-MM[-DD]:<part>:<phase>`; Error on a bad one."""
    dates, _, rest = value.partition(":")
    part, _, phase = rest.partition(":")
    pause, two, date = dates.rpartition("..")
    if two and not pause:
        raise Error("--cut %r: an empty <end> before `..`" % value)
    if not all(date_ok(d) or re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", d) for d in [date] + ([pause] if pause else [])):
        raise Error("--cut %r: [<the earlier part's end>..]<start>:<part>:<phase>, each date YYYY-MM[-DD]" % value)
    if not SLUG.fullmatch(part):
        raise Error("--cut %r: <part> is lowercase ASCII letters and digits, joined by -" % value)
    return pause or None, date, part, phase_arg(phase)


def phase_arg(phase):
    phase = phase.strip()
    if not phase or len(phase.splitlines()) > 1 or ": " in phase:
        raise Error("a phase is one line of text without `: ` (the title is `<series title>: <phase>`): %r" % phase)
    return phase


def series_title(e):
    """The series title: the entry's title, the part before its last `: ` when it is already a part."""
    title = e.fields.get("title") or ""
    return title.rpartition(": ")[0] or title if e.series else title


def field_block(lines, key):
    """The front matter lines of key: its `key:` line and the indented or `- ` lines under it (a block
    list); [] when the field is missing."""
    first, end = front_matter_span(lines)
    for i in range(first, end):
        if re.match(r"%s:" % re.escape(key), lines[i]):
            j = i + 1
            while j < end and re.match(r"[ \t]|-[ \t]", lines[j]):
                j += 1
            return lines[i:j]
    return []


def set_heading(lines, old, new, path):
    """Rewrite the entry's `# <old>` title heading, the first after the front matter, as `# <new>`;
    without one, print `heading not rewritten:` and a `next:` line."""
    end = front_matter_span(lines)[1]
    for i in range(end + 1, len(lines)):
        if lines[i].rstrip("\r\n").rstrip() == "# %s" % old:
            lines[i] = "# %s%s" % (new, ends(lines[i]))
            return
    if old != new:
        print("heading not rewritten: %s: no `# %s` heading after the front matter" % (path, old))
        print("next: make its title heading `# %s`" % new)


def fold(root, path):
    """Make path, a series' only part left, a plain entry again: its title less the `: <phase>`, its
    heading too, an empty `series:`, and its README row; then the lines outside outputs/ and sources/
    that still hold the old title."""
    e = Entry(root, path)
    old, title = e.fields.get("title") or "", series_title(e)
    bom, lines = read_lines(os.path.join(root, path))
    set_heading(lines, old, title, path)
    set_field(lines, "title", title)
    set_field(lines, "series", "")
    write_lines(os.path.join(root, path), bom, lines)
    print("series folded: %s: %s; series -" % (path, title))
    readme_row(root, Entry(root, path))
    stale = [ref for ref in ref_lines(root, path) if old in ref[2] and not ref[0].startswith(FROZEN)]
    if stale:
        print("next: write its title %r in place of %r in each line below" % (title, old))
    for rel, n, text in stale:
        print("old title: %s:%d: %s" % (rel, n, text))


def cmd_split(root, path, phase, cuts, today):
    e = Entry(root, path)
    span = parse_period(e.period)
    if not span:
        raise Error("%s: period %r does not read; split takes YYYY-MM – YYYY-MM or YYYY-MM – ongoing (a day may"
                    " follow the month)" % (path, e.period))
    start, end = span
    dates = [start] + [c[1] for c in cuts]
    for a, b in zip(dates, dates[1:]):
        if not before(a, b):
            raise Error("cut %s is not after %s: cuts go in order, inside the period, and two parts that start in"
                        " the same month both give days" % (b, a))
    if end and not before(dates[-1], end):
        raise Error("cut %s is not before the period's end %s" % (dates[-1], end))
    ends_ = [c[0] or c[1] for c in cuts] + [end or "ongoing"]   # each part's end: a pause's start, else the next cut
    for a, (pause, b, _, _) in zip(dates, cuts):
        if pause and (before(pause, a) or before(b, pause)):
            raise Error("%s..%s: the earlier part's end goes after its start %s and not after %s" % (pause, b, a, b))
    if re.fullmatch(r"GAP(?::.*)?", e.fields.get("title") or "GAP"):   # `GAP` or `GAP: <what>`, not "Gap year"
        raise Error("%s: its title is a gap (%r): give the entry its title before a split" % (path, e.fields.get("title")))
    slug = e.series or e.slug
    title = series_title(e)
    parts = ["entries/%s-%s-%s.md" % (c[1][:7], slug, c[2]) for c in cuts]
    if len(set(parts)) < len(parts):
        raise Error("two cuts name the same file: give each part its own slug")
    for p in parts:
        if os.path.exists(os.path.join(root, p)):
            raise Error("%s exists: pick another <part> slug" % p)
    table = ReadmeTable(root)
    at = next((i for i in table.rows if table.entry_of(i) == path), None)
    if at is None:
        raise Error("%s has no README row: give it one with readme-row --status first" % path)
    status = table.cells(at).get("status", "")
    periods = ["%s – %s" % (a, b) for a, b in zip(dates, ends_)]
    bom, lines = read_lines(os.path.join(root, path))
    written = []   # every file is built before the first is written
    for p, (_, _, _, part_phase), period in zip(parts, cuts, periods[1:]):
        values = dict(NEW_FIELDS, title="%s: %s" % (title, part_phase), period=period, series=slug)
        pbom, plines = from_template(root, values, today)
        for key in SPLIT_COPY:
            block, mine = field_block(lines, key), field_block(plines, key)
            if block and mine:
                k = plines.index(mine[0])
                plines[k:k + len(mine)] = [l.rstrip("\r\n") + ends(mine[0]) for l in block]
        written.append((p, pbom, plines, "created: %s: %s: %s; period %s" % (p, title, part_phase, period)))
    set_heading(lines, e.fields.get("title") or "", "%s: %s" % (title, phase), path)
    for key, value in (("title", "%s: %s" % (title, phase)), ("period", periods[0]), ("series", slug)):
        set_field(lines, key, value)
    write_lines(os.path.join(root, path), bom, lines)
    print("kept: %s: %s: %s; period %s" % (path, title, phase, periods[0]))
    for p, pbom, plines, line in written:
        write_lines(os.path.join(root, p), pbom, plines)
        print(line)
    readme_row(root, Entry(root, path))
    for p in parts:
        readme_row(root, Entry(root, p), status)
    return 0


def drop_row(root, path):
    """Delete the README row that links path; the row, or None when it has none (or no README.md)."""
    if not os.path.isfile(os.path.join(root, "README.md")):
        return None
    table = ReadmeTable(root)
    at = next((i for i in table.rows if table.entry_of(i) == path), None)
    if at is None:
        return None
    line = table.lines.pop(at)
    if at == len(table.lines) and table.lines:   # the last line: it now ends as the deleted one did
        table.lines[-1] = table.lines[-1].rstrip("\r\n") + ends(line)
    table.save()
    return line.rstrip("\r\n")


def unindex(root, path):
    """`git rm --cached` path when the index holds it but HEAD does not (an entry `diff` added with -N)."""
    if git_run(root, "ls-files", "--error-unmatch", "--", path).returncode == 0 and \
            logfiles.git_blob(root, "HEAD", path) is None:
        git(root, "rm", "-q", "--cached", "--", path)


git_run = logfiles.git_run


def cmd_split_undo(root, path, parts):
    e = Entry(root, path)
    slug = e.series or e.slug
    if len(set(parts)) < len(parts):
        raise Error("a part is named twice")
    for p in parts:
        if p == path or Entry(root, p).series != slug:
            raise Error("%s is not a later part of series %s" % (p, slug))
        if logfiles.git_blob(root, "HEAD", p) is not None:
            raise Error("%s is in HEAD: a part an earlier split made, not this one's" % p)
    head = logfiles.git_blob(root, "HEAD", path)
    bom, lines = read_lines(os.path.join(root, path))
    title = e.fields.get("title") or ""
    others = [x for x in entry_paths(root) if x != path and x not in parts and Entry(root, x).series == slug]
    if head is None and e.series == e.slug and not others:   # a new entry the split made a series' first part
        restored_title = title.rpartition(": ")[0] or title
        set_field(lines, "series", "")
        set_field(lines, "title", restored_title)
        set_heading(lines, title, restored_title, path)
    elif head is None:
        print("not in HEAD: %s: title and series left as they are (its series has other parts)" % path)
        print("next: when the split changed the title's `: <phase>`, write back the phase it had, in its title"
              " heading too")
    else:
        old_lines = head.decode("utf-8-sig").splitlines(keepends=True)
        old = front_matter("".join(old_lines))
        if one_value(old.get("series")):   # a part already: HEAD's phase after the draft's series title
            old_title = one_value(old.get("title")) or ""
            restored_title = ("%s: %s" % (title.rpartition(": ")[0] or title, old_title.rpartition(": ")[2])
                              if ": " in old_title else old_title)
            set_field(lines, "series", one_value(old.get("series")))
        else:   # the split's title less its `: <phase>`, a title the draft corrected kept
            restored_title = title.rpartition(": ")[0] or title
            series = field_block(lines, "series")
            if field_block(old_lines, "series"):
                set_field(lines, "series", "")
            elif series:
                del lines[lines.index(series[0])]
        set_field(lines, "title", restored_title)
        set_heading(lines, title, restored_title, path)
    spans = [parse_period(x.period) for x in [e] + [Entry(root, p) for p in parts]]
    if all(spans):
        first = min((s for s, _ in spans), key=lambda d: (d[:7], d))
        ends_ = [t for _, t in spans]
        last = None if None in ends_ else max(ends_, key=lambda d: (d[:7], d))
        set_field(lines, "period", "%s – %s" % (first, last or "ongoing"))
    else:
        print("period unchanged: a part's period does not read; set %s's by hand" % path)
    write_lines(os.path.join(root, path), bom, lines)
    restored = Entry(root, path)
    print("restored: %s: %s; period %s; series %s" % (path, restored.fields.get("title") or "", restored.period,
                                                      restored.series or "-"))
    for p in parts:
        unindex(root, p)
        os.remove(os.path.join(root, p))
        row = drop_row(root, p)
        print("deleted: %s%s" % (p, "; README row" if row else ""))
    readme_row(root, restored)
    for p in parts:
        for rel, n, line in ref_lines(root, p):
            print("still names %s: %s:%d: %s" % (p, rel, n, line))
    return 0


def fence(text):
    """A code fence longer than any run of backticks in text, at least three."""
    return "`" * max([3] + [len(run) + 1 for run in re.findall(r"`+", text)])


def cmd_diff(root, paths):
    files = list(paths) + ([f for f in ("README.md", "stories.md", "profile.md") if os.path.isfile(os.path.join(root, f))]
                           if len(paths) > 1 else [])
    tracked = set(git(root, "ls-files", "--", *paths).splitlines())
    new = [p for p in paths if p not in tracked]
    if new:
        git(root, "add", "-N", "--", *new)
    out = git(root, "diff", "--no-color", "--no-ext-diff", "--", *files)
    if not out.strip():
        print("no change: %s" % " ".join(files))
        return 0
    f = fence(out)
    print("%sdiff\n%s\n%s" % (f, out.rstrip("\r\n"), f))
    return 0


FROZEN = ("outputs/", "sources/")   # drop leaves their lines as they are: frozen or historical


def cmd_drop(root, path, reason, today):
    e = Entry(root, path)
    title = e.fields.get("title") or ""
    parts = [p for p in entry_paths(root) if p != path and e.series and Entry(root, p).series == e.series]
    row = drop_row(root, path)
    print("README row: %s" % (row or "none"))
    core = False
    if story_index(root) is not None:
        sf = StoriesFile(root)
        changed = False
        for n, row_, pieces in index_pieces(sf):
            items, seps = pieces[0::2], pieces[1::2]
            keep = [k for k, item in enumerate(items) if Story(item.strip().rstrip(";"), "").path != path]
            if len(keep) == len(items):
                continue
            for k, item in enumerate(items):
                if k not in keep:
                    print("story removed: %s: %s" % (row_.type, item.strip()))
                    core = core or "core" in (m.lower() for m in Story(item.strip().rstrip(";"), "").markers)
            cell = "".join((seps[k - 1] if j else "") + items[k] for j, k in enumerate(keep))
            sf.set_cell(n, 1, cell.strip())
            changed = True
        if changed:
            sf.save()
    try:
        unindex(root, path)
    except Error:
        pass   # a Log that is no git repository
    os.remove(os.path.join(root, path))
    print("deleted: %s" % path)
    left = [ref for ref in ref_lines(root, path) if not ref[0].startswith(FROZEN)]   # before the import log names it
    log = os.path.join(root, "sources", "import-log.md")
    if os.path.isfile(log):
        bom, lines = read_lines(log)
    else:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        bom, lines = False, ["# Import log\n"]
    eol = line_end(lines)
    if lines and not ends(lines[-1]):
        lines[-1] += eol
    line = "- Removed `%s` (%s, %s): %s" % (path, title, e.period, " ".join(reason.split()))
    lines += ([eol] if lines and lines[-1].strip() else []) + ["## %s — Dropped: %s%s" % (today.isoformat(), title, eol),
                                                              eol, line + eol]
    write_lines(log, bom, lines)
    print("import log: sources/import-log.md: %s" % line)
    if len(parts) == 1:   # one part left: a plain entry again
        fold(root, parts[0])
    elif parts and e.series == e.slug:   # the series' first part: the earliest part left names the series now
        first = min(parts, key=lambda p: (parse_period(Entry(root, p).period) or ("9999",))[0][:7] + p)
        for p in parts:
            plines = read_lines(os.path.join(root, p))
            set_field(plines[1], "series", slug_of(first))
            write_lines(os.path.join(root, p), *plines)
            print("series renamed: %s: series %s" % (p, slug_of(first)))
    if core and parts:
        print("next: core went with it; the experience has parts left: python3 -I <root>/tools/entries.py story-core"
              " <part> on --root <root>, on the user's word")
    if left:
        print("next: take the entry out of each line below, or delete a line that says nothing else")
    for rel, n, text in left:
        print("still names: %s:%d: %s" % (rel, n, text))
    return 0


def pending_bounds(lines):
    """The `## Pending` section's bounds, renaming an old `## Log` heading to it; (bounds, renamed)."""
    bounds = section_bounds(lines, "Pending")
    if bounds:
        return bounds, False
    bounds = section_bounds(lines, "Log")
    if bounds:
        lines[bounds[0]] = "## Pending" + ends(lines[bounds[0]])
        return bounds, True
    eol = line_end(lines)
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += eol
    lines += [eol, "## Pending" + eol]
    return (len(lines) - 1, len(lines)), False


def cmd_pending_add(root, path, text, today):
    lead = re.match(r"\s*(?:[-*]\s+)?\**\s*(%s)\**\s*:" % DATE, text)
    if lead:
        print("leading date: %s: the text starts with %s:, and pending-add writes the day recorded itself"
              " (nothing changed)" % (path, lead.group(1)))
        print("next: run it again with the text starting at what happened: drop the date when it is the day recorded;"
              " a date the evidence gives for the event goes inside the sentence (\"merged 2031-04-20\")")
        return 1
    full = os.path.join(root, path)
    bom, lines = read_lines(full)
    bounds, renamed = pending_bounds(lines)
    line = "- %s: %s" % (today.isoformat(), " ".join(text.split()))
    at = append_in_section(lines, bounds, line)
    set_field(lines, "last_updated", today.isoformat())
    write_lines(full, bom, lines)
    if renamed:
        print("renamed: %s: ## Log to ## Pending" % path)
    print("added: %s:%d: %s" % (path, at + 1, line))
    print("last_updated: %s: %s" % (path, today.isoformat()))
    return 0


LEAVE_PERIOD = ("leave %s: the pending line holds the milestone's date, and consolidate sets"
                " the period from it")


def series_gap(root, series, date, keep, entries=None):
    """The `between parts:` and `next:` lines when date falls between two parts of the series (no part
    covers it, one ends before it and one starts after it), keep the part to log to without an answer;
    else [], also when a part's start or end is GAP or does not read."""
    parts = [(p, period_ends(p)) for p in (entries if entries is not None else load(root)) if p.series == series]
    ended = [(end, p) for p, (start, end) in parts if end not in (None, "ongoing") and before(end, date)]
    later = [(start, p) for p, (start, end) in parts if start and before(date, start)]
    covers = any(start and not before(date, start) and (end == "ongoing" or end and not before(end, date))
                 for _, (start, end) in parts)
    if covers or not ended or not later or any(None in ends for _, ends in parts):
        return []
    end, prev = max(ended, key=lambda t: t[0])
    start, nxt = min(later, key=lambda t: t[0])
    return ["between parts: %s falls after %s (ends %s) and before %s (starts %s)" % (date, prev.path, end, nxt.path, start),
            "next: ask the user once which of the two parts the milestone belongs to (no answer: keep %s);"
            " that part is the entry from here on (its pending line and its commit), and both periods stay as"
            " they are (consolidate places the line's event date)" % keep]


def cmd_period(root, path, cover, ongoing):
    e = Entry(root, path)
    m = re.fullmatch(r"(GAP|%s) – (GAP|ongoing|%s)" % (DATE, DATE), e.period, re.I) or \
        re.fullmatch(r"(%s)()" % DATE, e.period)
    if not m:
        print("period unreadable: %s %r (YYYY-MM – YYYY-MM, YYYY-MM – ongoing; either end may be GAP)" % (path, e.period))
        print("next: " + LEAVE_PERIOD % "the period as it is")
        return 1
    start, end = m.group(1), m.group(2) or m.group(1)
    if e.series:
        mine = period_ends(e)[1]
        later = []
        for p in load(root):
            if p.series == e.series and p.path != path:
                theirs = period_ends(p)[1]
                if theirs in (None, "ongoing") or (mine not in (None, "ongoing") and before(mine, theirs)):
                    later.append(p.path)
        if later:
            print("not the series' last part: %s; %s ends later, or its end is ongoing or GAP (only the part"
                  " that ends last is extended)" % (path, ", ".join(later)))
            gap = series_gap(root, e.series, cover, path) if cover else []
            for line in gap or ["next: " + LEAVE_PERIOD % "the periods as they are"]:
                print(line)
            return 1
    try:   # the row is rewritten after the period: refuse before writing when it cannot be
        table = ReadmeTable(root)
    except Error as err:
        print("readme row not writable: %s (nothing changed)" % err)
        print("next: " + LEAVE_PERIOD % "the period as it is")
        return 1
    if not any(table.entry_of(i) == path for i in table.rows):
        print("no README row: %s (nothing changed)" % path)
        print("next: python3 -I <root>/tools/entries.py readme-row %s --status <its status> --root <root>, then"
              " this period command again" % path)
        return 1
    new = None
    if end.lower() == "ongoing":
        pass
    elif ongoing:
        new = "%s – ongoing" % start
    elif end.upper() == "GAP":
        print("unchanged: %s period %s: its end is GAP" % (path, e.period))
        print("next: when the work goes on, run it again with --ongoing; else %s" % (LEAVE_PERIOD % "the period as it is"))
        return 0
    elif start.upper() != "GAP" and before(cover, start):
        print("before the start: %s period %s, date %s (nothing changed)" % (path, e.period, cover))
        gap = series_gap(root, e.series, cover, path) if e.series else []
        for line in gap or ["next: " + LEAVE_PERIOD % "the period as it is"]:
            print(line)
        return 1
    elif before(end, cover):
        new = "%s – %s" % (start, cover[:len(end)])
    if new is None:
        print("unchanged: %s period %s covers %s" % (path, e.period, "ongoing" if ongoing else cover))
        return 0
    full = os.path.join(root, path)
    bom, lines = read_lines(full)
    set_field(lines, "period", new)
    write_lines(full, bom, lines)
    print("period: %s: %s to %s" % (path, e.period, new))
    readme_row(root, Entry(root, path))
    return 0


def cmd_set_visibility(root, path, value, source):
    full = os.path.join(root, path)
    bom, lines = read_lines(full)
    if not set_field(lines, "visibility", value, "# (%s)" % source):
        raise Error("%s has no front matter" % path)
    write_lines(full, bom, lines)
    print("visibility: %s: %s  # (%s)" % (path, value, source))
    return 0


# ---- state ----

def section_empty(text, heading):
    """(whether a `## <heading>` section holds nothing but GAP lines, blanks, comments, a table's header
    and rule, or My contribution's labels; its GAP markers). A missing section is empty."""
    empty, in_table = True, False
    lines = section_numbered(text, heading)
    for _, line in lines:
        s = line.strip()
        if s.startswith("|"):
            cells = logfiles.md_cells(s)
            header, in_table = not in_table, True
            if header or logfiles.is_rule(cells) or GAP_VALUE.match(cells[0]) or not any(cells):
                continue
            empty = False
            continue
        in_table = False
        s = re.sub(r"^- ", "", s)
        s = re.sub(r"^\*\*[^*]+:\*\*", "", s).strip()
        if s and not GAP_VALUE.match(s):
            empty = False
    return empty, sum(len(GAP_WORD.findall(line)) for _, line in lines)


def entry_state(e, today):
    """The `state` lines of one entry."""
    path, text = e.path, e.text
    gaps = len(GAP_WORD.findall(logfiles.strip_comments(text)))
    empty = {h: section_empty(text, h) for h in PROSE}
    blank = [h for h in PROSE if empty[h][0]]
    pending = content(section_numbered(text, "Pending") or section_numbered(text, "Log"))
    dates = sorted(m.group(1) for m in (PENDING_LINE.match(s) for _, s in pending) if m)
    out = ["state: %s: gaps %d; gap sections %d of %d; pending %d%s"
           % (path, gaps, len(blank), len(PROSE), len(pending), " (oldest %s)" % dates[0] if dates else "")]
    if blank:
        out.append("gap sections: %s: %s" % (path, ", ".join(blank)))
    keys = [h for h in KEY_SECTIONS if h in blank]
    out += ["key section empty: %s: %s" % (path, h) for h in keys]
    block = ["%s (%s)" % (h, "%d GAP" % empty[h][1] if empty[h][1] else "empty") for h in BLOCKING
             if empty[h][0] or empty[h][1]]
    if block:
        out.append("blocking gaps: %s: %s" % (path, ", ".join(block)))
    reasons = []
    if len(pending) >= PENDING_MANY:
        reasons.append("%d pending lines" % len(pending))
    if dates and dates[0] < months_before(today, 1).isoformat():
        reasons.append("oldest pending line %s, over a month old" % dates[0])
    if len(blank) >= MOSTLY_GAP:
        reasons.append("mostly GAP (%d of %d sections)" % (len(blank), len(PROSE)))
    reasons += ["key section empty: %s" % h for h in keys]
    if reasons:
        out.append("suggest consolidate: %s: %s" % (path, "; ".join(reasons)))
    return out


def cmd_state(root, paths, today):
    for path in paths or entry_paths(root):
        for line in entry_state(Entry(root, path), today):
            print(line)
    return 0


# ---- phrasing-add ----

def newer_citation(new, old):
    """A repeated wording's citation moves to the new one: never from an output (outputs/...) to
    anything else; to an output from anything else; else when the new one's first YYYY-MM-DD is later."""
    new_out, old_out = OUTPUT_PATH.search(new), OUTPUT_PATH.search(old)
    if old_out and not new_out:
        return False
    if new_out and not old_out:
        return True
    a, b = DAY.search(new), DAY.search(old)
    return bool(a and b and a.group(0) > b.group(0))


def cmd_phrasing_add(root, path, wording, angle, citation, distinct, replace):
    wording = " ".join(wording.split())
    if len(wording) > 1 and wording[0] + wording[-1] in ('""', "“”", "「」", "『』"):
        wording = wording[1:-1]
    angle = angle.lower()
    line = '- **%s:** "%s" (%s)' % (angle, wording, " ".join(citation.split()))
    if not ANGLE.fullmatch(angle) or not PHRASING_FORM.fullmatch(line) or ";" in citation:
        print("FAIL: not a Past phrasings line: %s (an angle like `general`, a citation with no `;`)" % line)
        return 2
    full = os.path.join(root, path)
    bom, lines = read_lines(full)
    bounds = section_bounds(lines, "Past phrasings")
    if not bounds:
        print("FAIL: %s has no ## Past phrasings section" % path)
        return 2
    bare = dict(lines_of("".join(lines)))
    kept = []   # (index, angle, wording, citation)
    for i in range(bounds[0] + 1, bounds[1]):
        m = PHRASING_PARTS.fullmatch(bare.get(i + 1, "").strip())
        if m:
            kept.append((i, m.group(1).lower(), m.group(2), m.group(3)))
    eol = ends(lines[bounds[0]]) or line_end(lines)
    if replace is not None:
        old = next((k for k in kept if k[0] + 1 == replace), None)
        if old is None or old[1] != angle:
            print("FAIL: %s:%d is not a Past phrasings line in form with the angle %s" % (path, replace, angle))
            return 2
        if OUTPUT_PATH.search(old[3]) and not OUTPUT_PATH.search(citation):
            print("kept: %s:%d cites an output, which a wording from elsewhere does not replace" % (path, replace))
            return 1
        lines[old[0]] = re.match(r"\s*", lines[old[0]]).group(0) + line + (ends(lines[old[0]]) or eol)
        write_lines(full, bom, lines)
        print("replaced: %s:%d: %s" % (path, replace, line))
        return 0
    for i, a, w, c in kept:
        if a == angle and " ".join(w.split()) == wording:
            if newer_citation(citation, c):
                cut = lines[i].rfind("(%s)" % c)
                lines[i] = lines[i][:cut] + "(%s)" % " ".join(citation.split()) + lines[i][cut + len(c) + 2:]
                write_lines(full, bom, lines)
                print("recited: %s:%d: %s" % (path, i + 1, lines[i].strip()))
            else:
                print("already kept: %s:%d: %s" % (path, i + 1, lines[i].strip()))
            return 0
    near = [(i, lines[i].strip()) for i, a, w, c in kept if similar((a, w), (angle, wording)) >= SIMILAR]
    if near and not distinct:
        for i, text in near:
            print("similar: %s:%d: %s" % (path, i + 1, text))
        print("not added: %s (the same bullet: --replace <line> with the newer version's wording; another"
              " claim or wording: --distinct)" % line)
        return 1
    at = append_in_section(lines, bounds, line)
    write_lines(full, bom, lines)
    print("added: %s:%d: %s" % (path, at + 1, line))
    return 0


# ---- list's opt-in lines ----

def period_ends(e):
    """(start, end) of an entry's period as written: start a date or None (GAP), end a date,
    "ongoing" or None (GAP); (None, None) for a period that does not read or ends before it starts."""
    m = re.fullmatch(r"(GAP|%s) – (GAP|ongoing|%s)" % (DATE, DATE), e.period, re.I) or \
        re.fullmatch(r"(%s)()" % DATE, e.period)
    if not m:
        return None, None
    start = None if m.group(1).upper() == "GAP" else m.group(1)
    end = m.group(2) or m.group(1)
    end = "ongoing" if end.lower() == "ongoing" else None if end.upper() == "GAP" else end
    if start and end not in (None, "ongoing") and before(end, start):
        return None, None
    return start, end


def experience_end(parts):
    """The latest end of the parts' periods: a date, None when one is ongoing, or False when one
    part's end is GAP or does not read (the end is unknown)."""
    ends = [period_ends(p)[1] for p in parts]
    if "ongoing" in ends:
        return None
    if not ends or None in ends:
        return False
    return max(ends)


def list_extras(entries, series, date, window, course_work, today):
    out = []
    if series:
        parts = [e for e in entries if e.series == series]
        starts = [period_ends(p)[0] for p in parts]
        if parts:
            end = experience_end(parts)
            start = "GAP" if None in starts else min(starts)
            out.append("series %s: period %s – %s" % (series, start, "GAP" if end is False else end or "ongoing"))
        else:
            out.append("series %s: period -" % series)
        if date:
            ends = {p.path: period_ends(p) for p in parts}
            done = [p for p in parts if ends[p.path][0] and ends[p.path][1] not in (None, "ongoing")
                    and not before(date, ends[p.path][0]) and not before(ends[p.path][1], date)]
            reads = {p.path: ends[p.path] != (None, None) or re.fullmatch(r"GAP – GAP", p.period, re.I) for p in parts}
            live = [p for p in parts if reads[p.path] and ends[p.path][1] in (None, "ongoing")
                    and not (ends[p.path][0] and before(date, ends[p.path][0]))]   # ongoing, or its end not known yet
            last = sorted((p for p in parts if ends[p.path][1] not in (None, "ongoing")), key=lambda p: ends[p.path][1])
            starts = [ends[p.path][0] for p in parts]
            first = None   # the first part, when the date is before every part
            if parts and None not in starts and all(before(date, d) for d in starts):
                first = min(parts, key=lambda p: (ends[p.path][0][:7], ends[p.path][0]))
            pick = ([first] if first else done or live or last[-1:] or [None])[0]
            out.append("part for %s: %s" % (date, pick.path if pick else "-"))
            if first:
                out.append("before the first part: %s starts %s" % (first.path, ends[first.path][0]))
                out.append("next: the milestone goes to %s; %s" % (first.path, LEAVE_PERIOD % "the period as it is"))
            elif pick:
                out += series_gap(None, series, date, pick.path, parts)
    if window is not None:
        cutoff = "%04d-%02d" % (today.year - window, today.month)
        groups = {}
        for e in entries:
            groups.setdefault(e.series or e.path, []).append(e)
        for name, parts in groups.items():
            end = experience_end(parts)
            label = "series %s: %s" % (name, ", ".join(p.path for p in parts)) if parts[0].series else name
            if end is False:
                out.append("window unknown (period %s): %s" % ("; ".join(p.period or "-" for p in parts), label))
            elif end and end[:7] < cutoff:
                out.append("outside window (ended %s): %s" % (end, label))
    if course_work:
        hits = [e.path for e in entries if e.fields.get("type") == "course" or "coursework" in e.tags]
        out.append("course work: %s (by type or tag)" % (", ".join(hits) or "none"))
    return out


VALUE_FLAGS = ("--series", "--today", "--type", "--month", "--status", "--field", "--field-source",
               "--visibility-source", "--angle",
               "--source", "--replace", "--cover", "--date", "--window", "--marker", "--label", "--summary", "--scope",
               "--phase", "--cut", "--reason")
SWITCHES = ("--consolidated", "--check", "--distinct", "--ongoing", "--course-work", "--remove", "--talking-points",
            "--application-questions", "--undo")
REPEATED = ("--type", "--field", "--field-source", "--marker", "--cut")
FLAGS = {   # each subcommand's flags; --root is every one's
    "list": {"--series", "--date", "--window", "--course-work", "--today"}, "check": {"--consolidated", "--today"},
    "story-coverage": {"--type", "--talking-points", "--application-questions"}, "story-wordings": {"--type"},
    "story-add": {"--marker", "--label", "--summary"}, "story-confirm": {"--type"}, "answer-row": {"--angle"},
    "answer-row-add": {"--scope"}, "answer-set": {"--angle", "--remove"},
    "new": {"--month", "--status", "--field", "--field-source", "--visibility-source", "--today"}, "readme-row": {"--status"},
    "readme-sort": {"--check"}, "state": {"--today"}, "pending-add": {"--today"}, "period": {"--cover", "--ongoing"},
    "set-visibility": {"--source", "--today"}, "phrasing-add": {"--angle", "--source", "--distinct", "--replace"},
    "split": {"--phase", "--cut", "--undo", "--today"}, "drop": {"--reason", "--today"}}
TAKES = {"list": 0, "rulings-hits": 0, "story-coverage": 0, "story-wordings": 0, "readme-sort": 0, "refs": 1,
         "links-since": 1, "story-candidates": 1, "story-stale": 1, "story-finish": 1, "new": 1, "readme-row": 1,
         "period": 1, "story-wording-add": 2, "phrasing-add": 2, "pending-add": 2, "set-visibility": 2,
         "story-type-add": 1, "story-add": 2, "story-core": 2, "story-confirm": 1, "answer-row": 1,
         "answer-row-add": 1, "answer-set": 2, "drop": 1,
         "check": None, "state": None, "split": None, "diff": None}
# None: check takes entries with --consolidated only, state any number, split and diff one or more
FREE_TEXT = ("story-wording-add", "phrasing-add", "pending-add")   # their text may follow `--`


def new_fields(values):
    """{field: value} from new's `--field <name>=<value>` values; Error on a bad one."""
    out = {}
    for v in values:
        name, eq, value = v.partition("=")
        name = name.strip().replace("-", "_")
        if not eq or name not in NEW_FIELDS:
            raise Error("--field takes <name>=<value>, <name> one of %s: %s" % (", ".join(NEW_FIELDS), v))
        value = value.strip()
        if len(value.splitlines()) > 1:
            raise Error("--field %s: one line, no line break" % name)
        out[name] = as_list(value.strip("[]")) if name in ("tags", "links") else value
    for name in ("title", "period"):
        if not out.get(name):
            raise Error("new needs --field %s=<value>" % name)
    if not NEW_PERIOD.fullmatch(norm_period(out["period"])) or (
            re.fullmatch(r"%s – %s" % (DATE, DATE), norm_period(out["period"])) and not parse_period(out["period"])):
        raise Error("period %r: YYYY-MM – YYYY-MM or YYYY-MM – ongoing (a day may follow the month); an unknown"
                    " start is GAP – ongoing, GAP – YYYY-MM or GAP – GAP" % out["period"])
    out["period"] = norm_period(out["period"])
    if out.get("type") and out["type"] not in TYPES:
        raise Error("type %r: one of %s" % (out["type"], " | ".join(TYPES)))
    if out.get("visibility") and out["visibility"] not in VISIBILITIES + ("GAP",):
        raise Error("visibility %r: one of %s" % (out["visibility"], " | ".join(VISIBILITIES + ("GAP",))))
    for name, value in out.items():
        if isinstance(value, str) and logfiles.scalar(yaml_value(value)) != value:
            raise Error("%s %r: front matter cannot hold it as written (a quote of each kind with ` #`)" % (name, value))
    if out.get("series") and not SLUG.fullmatch(out["series"]):
        raise Error("series %r: the first part's slug" % out["series"])
    return out


def field_sources(values, visibility_source, fields):
    """{field: source} from new's `--field-source <name>=<source>` values (and --visibility-source, the
    same as `--field-source visibility=<source>`); Error on a bad one."""
    out = {}
    for v in values + (["visibility=%s" % visibility_source] if visibility_source else []):
        name, eq, source = v.partition("=")
        name, source = name.strip().replace("-", "_"), " ".join(source.split())
        if not eq or name not in SOURCED or not source:
            raise Error("--field-source takes <name>=<source>, <name> one of %s: %s" % (", ".join(SOURCED), v))
        if name not in fields or (name == "visibility" and fields[name] == "GAP"):
            raise Error("--field-source %s: give its value with --field %s=<value> too" % (name, name))
        if name in out:
            raise Error("--field-source %s: one source per field" % name)
        out[name] = source
    return out


def main(argv):
    logfiles.utf8_stdout()
    usage = ("usage: %s -I tools/entries.py [--root <root>] list [--series <slug> [--date YYYY-MM-DD]]"
             " [--window <years>] [--course-work] |"
             " check [--consolidated <entry>...] | refs <entry> | links-since <entry> | rulings-hits |"
             " new <slug> --month YYYY-MM --status stub|imported --field title=<title> --field period=<period>"
             " [--field <name>=<value>]... [--field-source <name>=<source>]... | readme-row <entry> [--status <status>] |"
             " readme-sort [--check] | state [<entry>...] | pending-add <entry> <text> |"
             " period <entry> --cover YYYY-MM-DD|--ongoing | set-visibility <entry> public|private|nda [--source <source>] |"
             " phrasing-add <entry> --angle <angle> --source <citation> [--distinct|--replace <n>] <wording> |"
             " story-coverage [--type <question type>]... | story-candidates <question type> |"
             " story-stale <talking points file> | story-finish <entry> |"
             " story-wording-add <question type> <wording> | story-wordings [--type <question type>]... |"
             " story-type-add <question type> | story-add <question type> <target> [--marker raw|pending|core]..."
             " [--label <label>] [--summary <summary>] | story-core <entry> on|off |"
             " story-confirm <talking points file> [--type <question type>] |"
             " answer-row <question type> [--angle <angle>] |"
             " answer-row-add <question type> --scope shared|per-angle|per-company |"
             " answer-set <question type> [--angle <angle>] [--remove] <path> |"
             " split <entry> --phase <phase> --cut [<end>..]<start>:<part>:<phase>... | split --undo <entry> <part>... |"
             " diff <entry> [<part>...] | drop <entry> --reason <reason>"
             % ("py -3" if os.name == "nt" else "python3"))
    try:
        root, argv = logfiles.split_root(argv, __file__)
    except logfiles.LogError as e:
        print("%s\n%s" % (e, usage))
        return 2
    passthrough = bool(argv[:1]) and argv[0] in FREE_TEXT and "--" in argv   # only they take free text
    flags = argv[:argv.index("--")] if passthrough else argv
    if "-h" in flags or "--help" in flags:
        print(__doc__.rstrip())
        return 0
    args, opts = [], {}
    it = iter(argv)
    for a in it:
        if a in SWITCHES:
            opts[a] = True
        elif a in VALUE_FLAGS:
            value = next(it, None)
            if a in REPEATED and value is not None:
                opts.setdefault(a, []).append(value)
            else:
                opts[a] = value
            if value is None:
                print(usage)
                return 2
        elif a == "--" and passthrough:   # the rest are arguments, a text that starts with `-` included
            args += list(it)
        elif a.startswith("--"):
            print(usage)
            return 2
        else:
            args.append(a)
    if not args or args[0] not in TAKES:
        print(usage)
        return 2
    cmd, rest = args[0], args[1:]
    def bad_usage(extra):
        """Exit 2 with the usage, after a line naming --root when an extra argument is a Log's root (an
        older Template took the root as its last argument)."""
        roots = [a for a in extra if os.path.isdir(os.path.join(a, "entries"))]
        if roots:
            print("FAIL: give the Log's root as --root %s, not as an argument" % roots[-1])
        print(usage)
        return 2

    consolidated = "--consolidated" in opts
    takes = TAKES[cmd]
    if set(opts) - FLAGS.get(cmd, set()) or (cmd == "list" and "--today" in opts and "--window" not in opts):
        return bad_usage([] if takes == 2 or consolidated else rest[takes or 0:])
    if takes is None:
        if cmd == "check" and bool(rest) != consolidated or cmd in ("split", "diff") and not rest:
            return bad_usage([] if consolidated else rest)
    elif len(rest) != takes:
        return bad_usage(rest[takes:])
    try:
        today = datetime.date.fromisoformat(opts["--today"]) if "--today" in opts else datetime.date.today()
    except ValueError:
        print("--today takes YYYY-MM-DD")
        return 2
    if not os.path.isdir(os.path.join(root, "entries")):
        print("FAIL: no entries/ folder in %s; give the Log's root with --root" % root)
        return 2

    def bad(message):
        print("FAIL: %s" % message)
        return 2

    if "--date" in opts and ("--series" not in opts or not date_ok(opts["--date"])):
        return bad("--date takes YYYY-MM-DD, with --series")
    if "--window" in opts and not opts["--window"].isdigit():
        return bad("--window takes a whole number of years")
    if "--cover" in opts and not date_ok(opts["--cover"]):
        return bad("--cover takes YYYY-MM-DD")
    if cmd == "period" and ("--cover" in opts) == ("--ongoing" in opts):
        return bad("period takes --cover YYYY-MM-DD or --ongoing")
    if "--replace" in opts and (not opts["--replace"].isdigit() or "--distinct" in opts):
        return bad("--replace takes a line number, without --distinct")
    try:
        if cmd == "list":
            code = cmd_list(root, opts.get("--series"))
            for line in list_extras(load(root), opts.get("--series"), opts.get("--date"),
                                    int(opts["--window"]) if "--window" in opts else None,
                                    "--course-work" in opts, today):
                print(line)
            return code
        if cmd == "check":
            return cmd_check(root, today, [entry_arg(root, a) for a in rest] if consolidated else None)
        if cmd == "rulings-hits":
            return cmd_rulings_hits(root)
        if cmd == "story-coverage":
            return cmd_story_coverage(root, opts.get("--type", []), "--talking-points" in opts,
                                      "--application-questions" in opts)
        if cmd == "story-type-add":
            return cmd_story_type_add(root, rest[0])
        if cmd == "story-add":
            return cmd_story_add(root, rest[0], rest[1], opts.get("--marker", []), opts.get("--label"),
                                 opts.get("--summary"))
        if cmd == "story-core":
            if rest[1] not in ("on", "off"):
                return bad("story-core takes <entry> on or <entry> off")
            return cmd_story_core(root, entry_arg(root, rest[0]), rest[1] == "on")
        if cmd == "story-confirm":
            if len(opts.get("--type", [])) > 1:
                return bad("story-confirm takes one --type")
            return cmd_story_confirm(root, talking_points_arg(root, rest[0]), (opts.get("--type") or [None])[0],
                                     datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        if cmd == "answer-row":
            return cmd_answer_row(root, rest[0], opts.get("--angle"))
        if cmd == "answer-row-add":
            if opts.get("--scope") not in SCOPES:
                return bad("answer-row-add takes --scope %s" % "|".join(SCOPES))
            return cmd_answer_row_add(root, rest[0], opts["--scope"])
        if cmd == "answer-set":
            if opts.get("--angle") and not ANGLE.fullmatch(opts["--angle"]):
                return bad("--angle %r: a target name (lowercase letters, digits and -) or general" % opts["--angle"])
            return cmd_answer_set(root, rest[0], opts.get("--angle"), rest[1], "--remove" in opts)
        if cmd == "story-candidates":
            return cmd_story_candidates(root, rest[0])
        if cmd == "story-stale":
            return cmd_story_stale(root, talking_points_arg(root, rest[0]))
        if cmd == "story-wording-add":
            return cmd_story_wording_add(root, *rest)
        if cmd == "story-wordings":
            return cmd_story_wordings(root, opts.get("--type", []))
        if cmd == "readme-sort":
            return cmd_readme_sort(root, "--check" in opts)
        if cmd == "new":
            month, status = opts.get("--month") or "", opts.get("--status")
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
                return bad("new takes --month YYYY-MM: the month that names the file")
            if not SLUG.fullmatch(rest[0]):
                return bad("slug %r: lowercase ASCII letters and digits, joined by -" % rest[0])
            if status not in ("stub", "imported"):
                return bad("new takes --status stub or --status imported")
            fields = new_fields(opts.get("--field", []))
            sources = field_sources(opts.get("--field-source", []), opts.get("--visibility-source"), fields)
            if fields.get("visibility", "GAP") != "GAP" and "visibility" not in sources:
                return bad("a visibility other than GAP needs its source: --field-source visibility=<source>"
                           " (user, YYYY-MM-DD; a repo URL)")
            return cmd_new(root, rest[0], month, status, fields, sources, today)
        if cmd == "state":
            return cmd_state(root, [entry_arg(root, a) for a in rest], today)
        if cmd == "diff":
            return cmd_diff(root, [entry_arg(root, a) for a in rest])
        if cmd == "split":
            paths = [entry_arg(root, a) for a in rest]
            if "--undo" in opts:
                if len(paths) < 2 or "--phase" in opts or "--cut" in opts:
                    return bad("split --undo takes the entry, then each later part, and no --phase or --cut")
                return cmd_split_undo(root, paths[0], paths[1:])
            if len(paths) > 1 or not opts.get("--phase") or not opts.get("--cut"):
                return bad("split takes one entry, --phase <its phase> and a --cut YYYY-MM[-DD]:<part>:<phase>"
                           " per later part")
            return cmd_split(root, paths[0], phase_arg(opts["--phase"]), [cut_arg(c) for c in opts["--cut"]], today)
        path = entry_arg(root, rest[0])
        if cmd == "story-finish":
            return cmd_story_finish(root, path)
        if cmd == "drop":
            if not (opts.get("--reason") or "").strip() or len(opts["--reason"].splitlines()) > 1:
                return bad("drop takes --reason <one line: what the user said, and when>")
            return cmd_drop(root, path, opts["--reason"], today)
        if cmd == "readme-row":
            status = opts.get("--status")
            if status is not None and not re.match(r"(%s)\b" % "|".join(STATUSES), status):
                return bad("--status starts with %s" % ", ".join(STATUSES))
            return cmd_readme_row(root, path, status)
        if cmd == "pending-add":
            return cmd_pending_add(root, path, rest[1], today)
        if cmd == "period":
            return cmd_period(root, path, opts.get("--cover"), "--ongoing" in opts)
        if cmd == "set-visibility":
            if rest[1] not in VISIBILITIES:
                return bad("visibility %r: one of %s" % (rest[1], " | ".join(VISIBILITIES)))
            return cmd_set_visibility(root, path, rest[1], opts.get("--source") or "user, %s" % today.isoformat())
        if cmd == "phrasing-add":
            if not opts.get("--angle") or not opts.get("--source"):
                return bad("phrasing-add takes --angle <angle> and --source <citation>")
            return cmd_phrasing_add(root, path, rest[1], opts["--angle"], opts["--source"], "--distinct" in opts,
                                    int(opts["--replace"]) if "--replace" in opts else None)
        return cmd_refs(root, path) if cmd == "refs" else cmd_links_since(root, path)
    except (Error, OSError, UnicodeDecodeError) as e:
        print("FAIL: %s" % e)
        return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
