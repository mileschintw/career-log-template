#!/usr/bin/env python3
"""The mechanical steps of the scan mode (skills/career-log/modes/scan.md).

  python3 -I tools/scan.py name [--screen-budget <s> --fit-budget <f>]   (Windows: py -3 -I tools/scan.py ...)
  python3 -I tools/scan.py sources
  python3 -I tools/scan.py prune [--dry-run]
  python3 -I tools/scan.py pending
  python3 -I tools/scan.py dedup <postings.jsonl> --out <kept.jsonl> [--window <days>]
  python3 -I tools/scan.py prefilter <dir>
  python3 -I tools/scan.py screen <dir> --screen-budget <s> --fit-budget <f> [--sort [--give-up]]
  python3 -I tools/scan.py screen --check <results.jsonl> [--batch <batch.todo>]
  python3 -I tools/scan.py fetch <capture path> <url>
  python3 -I tools/scan.py capture <capture path> <url> <page.json | text file> [--stand-in <API url>]
  python3 -I tools/scan.py fitmap <url> [--out <fit result>]
  python3 -I tools/scan.py rank <dir> --n <n> [--m <m>] [--give-up]
  python3 -I tools/scan.py report <rows.jsonl> [--name <name>] [--top <line>] [--drafting] [--screen <dir>] [--body <file>]
  python3 -I tools/scan.py summary <dir>
  python3 -I tools/scan.py status <url> <status> [--draft <cell>] [--reason <text>]
  python3 -I tools/scan.py cleanup [--dry-run]
  python3 -I tools/scan.py drafts <dir> --m <m>
  python3 -I tools/scan.py drafts --check <folder>
  python3 -I tools/scan.py drafts <dir> --save
  python3 -I tools/scan.py draft <url> [--out <dir>]

Each takes --root <root>, the Log's root (default: the repo this script is in), anywhere on the line,
and, before the command, --date YYYY-MM-DD, the day the run counts from (default: today), for tests.
A relative path argument is read from the Log's root. When `origin` exists, name, prune, report and cleanup first run `git fetch
--prune origin`, so a branch deleted from another clone counts as gone; a fetch that fails prints a
`fetch: failed` line and goes on with the branches as last fetched.

URLs: a posting's URL is kept as given (less trailing punctuation). Two URLs are the same posting when
their canonical forms (host without `www.`, port, path without its trailing slash, and the query less
TRACKING parameters; no scheme, no fragment) or their ATS job ids (`greenhouse:123`) match.

Files it reads and writes (skills/career-log/modes/scan.md › Files):
- a scan report, `outputs/reports/<YYYY-MM-DD>-scan[-<n>].md` (REPORT_NAME), `-<n>` from 2 on for a
  later run the same day. Its first line is `# Scan <name>`, the next paragraph its top line (sources
  skipped), then `## Pending`, a table with the columns of PENDING_COLUMNS, one row per posting. Then
  `report --screen` writes `## Ranking` (a table: RANKED_COLUMNS), `## Dropped at screen` (a table:
  URL, Company, Role, Reason, Screen key), `## Screened, not fully fitted` (a table: Company, Role,
  URL, Tier, Rough, Screen key), `## Sources` (one `- <source>: read: <how>` line per line of
  `read.jsonl`, `<how>` one of READS), `## Not fitted` (the counts dedup and the prefilter dropped, by
  reason, and the postings past the screen budget and the unreadable ones), `## Sponsorship records`
  (only while direction.md has a `**Visa sponsorship needed:**` line: a table of each fitted
  employer's records, once per employer, as tools/sponsorship.py keeps them) and `## Fit maps`: one
  `### <company> — <role>` heading per posting fitted, with a `URL: <url>` line, a `Screen: tier
  <t>, rough <touched>/<required>, key <key>` line, an `Entries commit: <sha>` line, then the map as
  tools/fit.py gives it (its `Recommendation:` line, the things to check, and a table whose rows keep
  their kind). An older report's Ranking and fit maps are the agent's, and its rows have no kind;
- `outputs/reports/scan-declined.jsonl`: one `{"url", "date", "reason"}` object per line, newest
  first;
- draft branches `scan/<YYYY-MM-DD>[-<n>]`, named as the report they belong to. A Draft cell names a
  draft as `scan/<name>:scan-drafts/<folder>`, `.build/scan/<name>/drafts/<folder>` (no remote), or the
  application folder it was saved as;
- `scan-sources.md`: one `## <source>` section per job source, with `- URL:`, `- Kind:`
  (KINDS), `- Read:` and `- Fields:` lines;
- a run's folder `.build/scan/<name>/` (`<dir>` below), never committed: `collected.jsonl`,
  `titles.jsonl` and `read.jsonl` (the agent's; `read.jsonl` holds one `{"source", "read"}` object
  per source read: its section name and how its postings were read, one of READS), `kept.jsonl`,
  `dedup-dropped.jsonl`, `prefiltered.jsonl`, `prefilter-dropped.jsonl`, `screen-list.jsonl`,
  `not-screened.jsonl`, `postings/<folder>.md` (the captures: the URL on the first line, a blank
  line, then the page's text), `fetched.jsonl` (fetch's), `screen/batch-<i>.todo` (capture paths, one per line), `screen/*.jsonl` (the Screen results), `fit.jsonl`,
  `screened.jsonl`, `dropped.jsonl`, `fit/<folder>.jsonl` (the fit results, in tools/fit.py's
  format), `unreadable.jsonl`, `ranked.jsonl` and `rows.jsonl`.

A Screen result is one JSON object per line: `url`, `gate` (`yes` or `no`), `reason` (on a no: the
constraint and the posting's words), `tier` (the role's rank in direction.md's Target roles: its
line's place, 1 the first, `GAP:` lines counted, never a `GAP:` line or past the last role; or
null for no tier, and null while the Target roles are empty), `rows` (one object per
requirement or duty: `requirement`, `kind` (`required`, `preferred` or `duty`), `entries` (the file
names that touch it, or [])), and an optional `check` (things to check, a list of strings). A
result reused from a report has `touched` and `required` in place of `rows`. Rough coverage is `<touched>/<required>`: the required and duty rows,
and of them the ones with an entry; when a posting marks no row required or duty, every row counts. The
Screen key is `<list>-<direction>`: the first 8 hex digits of the SHA-256 of `tools/entries.py list`'s
output (each line's `status` and `tokens` left out, so an edit that keeps the rest of an entry's line
keeps the key) and of direction.md's `## Constraints` and `## Target roles, ranked` sections. A result is reused while its
key is the current one.

- `name`: the next free report name today, as `name: <name>`, then `report:`, `branch:`
  (`scan/<name>`), `worktree:`, `drafts:` and `dir:` lines (the paths under `.build/`, `dir` the
  run's folder), and `remote: yes|no` (whether `origin` exists). A name is taken by a scan report, a
  `scan/*` branch, local or on origin, or a `.build/scan/` folder. With --screen-budget and
  --fit-budget, it first refuses as `screen` does when the screen budget is below the fit budget.
- `sources`: one `source: <name> | kind <kind> | url <url> | read set|GAP | fields set|GAP` line
  per section of scan-sources.md (a missing line reads `GAP`, a kind not in KINDS `unknown (<it>)`;
  `read` and `fields` are GAP while the line is missing or starts with `GAP`), a GitHub list's line
  ending in `| clone <folder>`, the folder to clone it into (`.build/scan-sources/<slug>`), and a
  public or signed-in job board's in `| session scan-<slug>`, its Browser session's name; the slug is
  the name's lowercase ASCII letters and digits joined by `-`, or with its hash when it has none or
  shares its slug with another source. Then `sources: <n>`; or `sources: none (<why>)` when the
  file is missing or has no section.
- `prune`: deletes the declined lines and the `scan/*` branches (their worktrees, the local branch
  and the one on `origin`) dated more than PRUNE_DAYS days before --date. One `pruned:` line each.
- `pending`: `report: <path>` for the newest scan report (or `report: none`), then one
  `pending: <url> | <company> | <role> | <status> | <draft> | fit map <state>` line per row whose
  status is in PENDING (a `|` in a cell as `\\|`; `<state>` the last line of `fitmap <url>` without
  its `fit map: `: `reuse`, `stale (<why>)` or `none`), and `count: <n> pending row(s)`; or
  `pending: none`.
- `dedup`: reads one posting per line (`url`, `company`, `role`, optional `location`, any other
  fields kept), and drops the applied, declined and repeated ones. Applied means its URL or ATS job
  id is in an `outputs/applications/*/posting.md` or on an `applications.md` line. Failing that, when
  the posting or the record has no job id: an application folder whose name, less its date, is the
  company and then the role (as words), and whose posting text, when it has one, holds the city (the
  location's first part, when given); or an `applications.md` table row with a cell equal to the
  company and one equal to the role. Declined means its URL is in scan-declined.jsonl. A kept posting
  gains `"seen"`: the date of the earliest scan report that lists its URL, or null. Writes the kept
  ones to --out, and the dropped ones to DEDUP_DROPPED beside it, each with its `drop` (its reason as
  `dropped by reason:` names it) and `why`; prints one `dropped: <url> (<why>)` line each, then a
  `kept:` line with the counts and a `dropped by reason:` line. With --window <days>, it first drops each posting whose `posted`
  starts with a date (YYYY-MM-DD) before --date less that many days; a `posted` with no such date
  (`2d ago`) is kept, with an `undated:` line.
- `prefilter`: reads `<dir>/kept.jsonl` and `<dir>/titles.jsonl`, the agent's judgement on each
  kept posting's list fields: one `{"url", "tier", "by", "drop"}` object per kept posting, `tier`
  the title's rank in direction.md's Target roles (its line's place, 1 the first, `GAP:` lines
  counted as tools/fit.py heatmap counts them; or null), `by` absent or `"content"`
  (the title is not a target's but close to one, the same kind of work under another name: `tier`
  is that target's rank, for the order alone, and Screen tiers it by its content), `drop` absent,
  `"role"` (the title plainly names work outside every target role) or `"constraint: <which>"` (it
  plainly breaks that hard constraint; `<which>` its bold label in direction.md's Constraints, as
  `constraint: Location`). It refuses, listing every problem (a kept posting with no line or two, a
  line for no kept posting, a tier past the last target role or on a `GAP:` line, a tier or a role
  drop while the Target roles are empty, a `by` other than `"content"`, or one with no tier or with
  a drop), and writes nothing. Else it writes the others to `prefiltered.jsonl` with their `tier`
  (and `by`), ordered by tier (null last; at one tier, a title `by` content after the target's own
  titles), then their source's place in scan-sources.md (a source it lacks last), then their order in
  kept.jsonl, and the dropped ones to `prefilter-dropped.jsonl` with their `drop`. It prints one
  `dropped: <url> (<drop>)` line each, one `close: <url> (tier <n>, by content: Screen tiers it)`
  line per title kept `by` content, `target roles: empty (...)` when they are, and a `prefilter:` line with the counts
  per drop.
- `screen`: refuses when --screen-budget is below --fit-budget. Without --sort, it takes the first
  --screen-budget postings of `<dir>/prefiltered.jsonl` into `screen-list.jsonl` (each with its
  `order`, its `folder`, `<YYYY-MM-DD>-<company>-<role>` from --date with `-2` and on for a repeat,
  and its `capture` path) and the rest into `not-screened.jsonl`; copies in a capture an earlier run
  left in `.build/scan/*/postings/` for the same URL; writes each result reused from a report to
  `screen/reused.jsonl`; and splits the others into `screen/batch-<i>.todo` files of up to BATCH
  capture paths. It prints a `key:` line, one `posting: <url> | capture <path> (have|copied|need) |
  screen (reused <report>|batch-<i>)` line each, and a `screen:` count line. With --sort, every
  posting of the list with a capture must have a result in `screen/*.jsonl` (else it refuses, naming
  the missing ones, or, with --give-up, moves each one's capture to `<capture>.unreadable`, where
  no later run copies it from, with a `gave up:` line); one with neither goes to `unreadable.jsonl`.
  It puts the gate's noes in
  `dropped.jsonl`, sorts the rest by tier (no tier last), then
  rough coverage (the share, highest first; 0/0 counts as 0), then their order in the list, and
  writes the first --fit-budget to `fit.jsonl` and the others to `screened.jsonl`, each posting with
  `tier`, `touched`, `required`, `rough`, `key`, `check` and its `capture`. It prints one `fit: <url>
  | capture <path> (have|need)` line each, then the counts.
  With --check (no <dir> or budgets), it checks a Screen results file as --sort does, every line,
  and with --batch, that it holds one line for each capture of the batch file that exists (by the
  URL on its first line) and none for another posting. `check: ok` lines, else exit 1 with one
  `bad:`, `missing:`, `extra:` or `repeated:` line per problem.
- `fetch`: the plain fetch of a posting's own page (browser.md › Fallback order item 1, for scan's
  captures): a GET of <url>, its HTML read as the text a reader sees (no script, style or template).
  It refuses a posting API or JSON endpoint (an `api.` host, an `/api/` path, Workday's `/wday/cxs/`,
  a `.json` file): the page's own URL is the read; and a record of one never counts for `capture`.
  It appends `{"url", "status", "chars", "capture"}` to the run folder's `fetched.jsonl` (`<dir>` for
  a capture path `<dir>/postings/<x>.md`, else the capture's own folder), then, given status 200 and
  at least 500 characters of text, writes the capture as `capture` does and prints `capture: <path>
  (<url>, fetch, <n> characters)` and a `next:` line (read the capture: one with no posting is read
  again with playwright-cli). Otherwise it writes no capture and refuses with `fetch: no capture
  from <url> (<why>)` and a `next:` line: a page built by script, a wall or an error status is read
  next with playwright-cli (a 404 or 410 may be a posting that is gone).
- `capture`: writes a posting's capture: the URL, a blank line, then the text of the page file
  (a `.json` file holding one JSON string, as `eval ... --filename` writes it, or a text file),
  with LF line ends. It refuses a URL with no `fetch` on record in `fetched.jsonl` (the page's own
  URL is read first, before playwright-cli or a posting API), and a page with no text, writing
  nothing. --stand-in names the API or JSON endpoint the page file came from (its text saved as a
  text file), and its line ends `, stand-in <API url>)`.
- `fitmap`: the newest `## Fit maps` subsection for the URL: `fit map: <report> (entries commit
  <sha>)`, then `fit map: reuse`, or `fit map: stale (<each entry changed since>)`; or `fit map: none`.
  The entries a map cites are the dated file names in its Entry cells, in any letters (tools/fit.py's
  ENTRY_NAME). With --out, on reuse it writes the map to that file as a fit result, its
  recommendation from its `Recommendation:` line (in an older report, from the posting's `## Ranking`
  line), with a `wrote:` line; a map with neither, or with no table, is `stale (...)` instead.
- `rank`: reads `<dir>/fit.jsonl` and the fit results in `<dir>/fit/`, checked as `tools/fit.py
  check` checks them. A posting with no result and no capture is unreadable; one with a capture but
  no result makes it refuse, or with --give-up is unreadable, its capture moved aside as `screen
  --give-up` does. It writes the unreadable ones into `unreadable.jsonl` with `"at": "fit"` (in place
  of the ones an earlier rank wrote), and ranks the rest: recommendation (apply, apply with caveats,
  skip), then tier (none last), then the share of required rows covered (tools/fit.py's coverage),
  then their order in the screen list. It writes them all to `ranked.jsonl`, and the first --n to
  `rows.jsonl` (`url`, `company`, `role`, `status` undecided, `draft` empty, `fit_commit`: a reused
  map's entries commit, else the last commit to `entries/`). It prints one `rank: <rank> | <company>
  | <role> | <recommendation> | <covered>/<required> | <url>` line for each of the top n, `only <x>
  found` when fewer were fitted, with --m one `draft: <url> | folder <folder> | capture <path>` line
  for each of the first m of the top n whose recommendation is not skip, and a `ranked:` count line.
- `report`: writes the report --name names (`2026-10-22-2`; default: the next free one, as `name`
  gives it) with its title, the --top line (default `All sources read.`) and the `## Pending`
  table: the rows given (each object has PENDING_COLUMNS' keys: url, company, role, status, draft,
  fit_commit), then the pending rows of the newest report whose URL they lack, carried over. A row
  given whose URL has a pending row with a draft there keeps that row's status, draft and fit map
  commit. A draft whose branch is gone reads `pruned (<branch>)`, and its status `undecided`.
  --drafting adds to the top line that the drafts are on this machine only, when there is no remote.
  With --screen, it refuses a `read.jsonl` line with no source or a `read` not in READS, and a
  source of `collected.jsonl` with no line there.
  With --screen <dir> and a `ranked.jsonl` there, it writes the sections after the table from the
  run's files, as the report's format above says; --body appends a file's sections after them. With
  no `ranked.jsonl`, --body's sections follow the table, with the two Screen sections and `## Sources`
  right after its `## Ranking`, and each `## Fit maps` subsection whose URL is in `fit.jsonl` gets its
  `Screen:` line.
  Then it regenerates the dashboard (tools/dashboard.py: its `wrote:` or `unchanged:` line and its
  `artifact:` line; when that fails, it deletes the report it wrote, so the same command runs again
  once the error is fixed) and prints `commit: scan(<name>): <x> postings`, `<x>` the number of rows
  given.
- `summary`: the run's counts, one line each (collected, then each file a collected posting can end
  in: dedup-dropped, prefilter-dropped, not-screened, dropped, screened, unreadable, ranked), and a
  `top:` line per row of `rows.jsonl`. It then checks that each posting of `collected.jsonl` is in
  exactly one of those files (by URL, each line once), and that the run's report has a fit map with a
  `Screen:` line for each ranked posting, and, while direction.md asks for sponsorship lookups, that
  each ranked posting's employer has a record of each kind under tools/sponsorship.py's REUSE_DAYS
  old (else `no sponsorship record:`) and answered (else `sponsorship unanswered: <employer> |
  <kind> | <why>`): `summary: ok, ...`, or exit 1 with one `missing:`, `repeated:`, `extra:`, `no
  report:`, `no Screen line:`, `no sponsorship record:`, `sponsorship unanswered:` or `sponsorship
  unreadable:` line each, then `summary: <n> finding(s)`.
- `status`: sets the status (one of STATUSES) of the URL's row in the newest report that lists it,
  and its Draft cell with --draft. `declined` also adds the URL to scan-declined.jsonl, with --reason,
  and for a URL in no Pending table (a posting screened, not fully fitted) does only that. Then it
  regenerates the dashboard, as `report` does, and prints the commit subject for what changed since
  HEAD: `commit: scan(<name>): <x> drafts` after `draft to review` (the report's rows set to it since
  HEAD), else `commit: scan(<name>): <x> accepted, <y> declined` (its rows set to accepted, and the
  URLs scan-declined.jsonl gained, since HEAD), `<name>` the report's.
- `cleanup`: deletes each `scan/*` branch (worktree, local, origin) whose report exists and whose
  every draft, by its row in the newest report that lists it, is accepted or declined. A branch no
  report's row has ever named (drafting stopped before its Draft cells) is kept for prune, and so is
  one git cannot remove (a worktree with uncommitted changes). Then it deletes each run's folder
  `.build/scan/<name>/` whose report's every row, by the newest row for its URL, is accepted or
  declined; a folder with no report yet is kept. One `deleted:` or `kept:` line each.
- `drafts <dir> --m <m>`: opens the run's draft folders (scan.md › Draft a posting). It picks the
  postings as `rank --m` does, from `rows.jsonl` and `ranked.jsonl`: the first m of the top n not
  recommended skip. With a remote it runs `git fetch`, then `git worktree add --no-track -b
  scan/<name> <worktree> origin/<default>` (the default branch from origin/HEAD), and each folder is
  `<worktree>/scan-drafts/<folder>`; with none, `<drafts>/<folder>` (the paths `name` prints). Into
  each it copies the capture as `posting.md` and writes the posting's `### ` section of the run's
  report's `## Fit maps` as `fit.md`. It prints `branch:` and `worktree:` (with a remote), one
  `draft: <url> | folder <folder path> | capture <capture path>` line each, and a `drafts:` count
  line. It refuses, writing nothing, when the branch exists (here or on origin), the worktree or a
  folder exists, a capture or a fit map is missing, or the report is not written yet.
- `drafts --check <folder>`: checks a draft folder's mechanical part: its files are exactly
  DRAFT_FILES, plus DRAFT_OPTIONAL (`answers.md`) when there were form questions, no PDF; decisions.md's
  first table has the header `| Decision | Chosen | Alternatives | Why |`, four cells a row, and a
  row whose Decision starts `needs you` reads `| needs you: <what> | GAP | - | <where> |`. `check:
  ok`, else exit 1 with one `missing:`, `extra:` or `bad:` line per problem and a `check: <n>
  problem(s)` line. What the files say is not checked.
- `drafts <dir> --save`: records the drafts once step 5.1 has committed and pushed them. A refusal ends
  with a `next:` line, the step to take. With a
  remote, it refuses, changing nothing, while the worktree has uncommitted changes or
  `origin/scan/<name>` lacks its HEAD (the push failed), with a `branch:` line, or when neither the
  worktree nor `origin/scan/<name>` is there (nothing drafted), and only uncommitted changes in
  `scan-drafts/` count (the rest is no draft's, and stays). The drafts are the
  folders of `origin/scan/<name>:scan-drafts/`; it checks each as --check does (the worktree's copy,
  or origin's once the worktree is gone) and that its posting has a row, refusing on a problem. Then
  it sets each posting's row, as `status` does, to `draft to review` with the Draft cell
  `scan/<name>:scan-drafts/<folder>`, and removes the worktree (`git worktree remove`, never forced;
  one git cannot remove stays, with a `kept:` line).
  With no remote the folders are those in `<drafts>/`, each cell `<drafts>/<folder>`. Then it
  regenerates the dashboard once, deletes `.playwright-cli/`, and prints `commit: scan(<name>): <x>
  drafts`. Run again after the worktree is gone, it sets the same cells again.
- `draft <url> [--out <dir>]`: copies the draft the URL's newest row names into --out (default
  `.build/drafts/<folder>/`): for a `scan/<name>:<path>` cell, after `git fetch`, the files of
  `origin/scan/<name>:<path>`; for a `.build/scan/...` cell, that folder on this machine. It prints
  `draft: <url> | <cell>`, `folder:`, `files:`, then one `needs you: <what> | <where>` line per
  `needs you` row of decisions.md, or `needs you: none`. It refuses, writing nothing, a row with no
  draft, a `pruned (...)` or accepted cell, a draft origin lacks, a draft folder not on this machine, and a --out folder
  that holds one of those files with other text (an earlier look's, accept's or build's copy, maybe
  edited; the same text, or a build's own files, are fine). A refusal ends with a `next:` line.

Exit 0 on success, 1 when a step refuses (a report name taken, a URL in no report, a file that does
not parse, no git), 2 on a bad argument. Standard library only, Python 3.11+.
"""
import argparse, datetime, glob, hashlib, html.parser, json, os, re, shutil, subprocess, sys
import http.client, urllib.error, urllib.request
from urllib.parse import parse_qsl, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
import config   # direction.md's target roles, as config.py's show reads them
import fit   # the map's format (fit results, map rows, a report's fit maps)
import sponsorship   # the visa sponsorship records a report shows for the employers fitted

if __name__ == "__main__":   # tools/dashboard.py, which this loads, then uses this module, not a second copy
    sys.modules.setdefault("scan", sys.modules[__name__])

ROOT = os.path.dirname(HERE)
REPORTS = "outputs/reports"
DECLINED = REPORTS + "/scan-declined.jsonl"
REPORT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-scan(?:-(\d+))?\.md$")
BRANCH_NAME = re.compile(r"^scan/(\d{4}-\d{2}-\d{2})(?:-(\d+))?$")
PRUNE_DAYS = 90
PENDING_COLUMNS = [("URL", "url"), ("Company", "company"), ("Role", "role"), ("Status", "status"),
                   ("Draft", "draft"), ("Fit map commit", "fit_commit")]
STATUSES = ("draft to review", "undecided", "accepted", "declined")
PENDING = ("draft to review", "undecided")
# Query parameters that track a click (where it came from), never which posting it is; canonical()
# drops them and every utm_ one, and every other parameter, an unknown ATS's own id included, stays.
TRACKING = {"ref", "refs", "referrer", "source", "src", "gh_src", "lever-source", "lever-origin", "trk",
            "trkinfo", "trackingid", "refid", "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "_hsenc",
            "_hsmi", "igshid", "campaign", "medium", "jobsource"}
BATCH = 10
DEDUP_DROPPED = "dedup-dropped.jsonl"   # beside dedup's --out
READ_FILE = "read.jsonl"   # how each source was read: the agent's, at collect
READS = ("API", "fetch", "browser", "file")
FETCHED = "fetched.jsonl"   # each posting page fetch tried: fetch's, read by capture
FETCH_MIN = 500   # fewer characters of text than this is no page: a shell built by script, a wall
FETCH_AGENT = "Mozilla/5.0 (compatible; career-log scan; plain fetch)"
SECTIONS = ("Constraints", "Target roles, ranked")


class ScanError(Exception):
    pass


# ---- URLs ----

clean = logfiles.clean_url   # a URL less the punctuation a sentence put after it
urls = logfiles.urls


def canonical(url):
    """The form two URLs of one posting share: host without `www.`, a port other than the scheme's
    own, the path without its trailing slash, the query less TRACKING parameters; no scheme, no
    fragment."""
    s = urlsplit(clean(url))
    host = (s.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    try:
        port = s.port
    except ValueError:
        port = None
    if port and port != {"http": 80, "https": 443}.get(s.scheme.lower()):
        host += ":%d" % port
    path = re.sub(r"/+$", "", s.path) or ""
    query = sorted((k.lower(), v) for k, v in parse_qsl(s.query, keep_blank_values=True)
                   if k.lower() not in TRACKING and not k.lower().startswith("utm_"))
    return host + path + ("?" + "&".join("%s=%s" % kv for kv in query) if query else "")


def job_id(url):
    """An ATS's own id for the posting (`greenhouse:123`), or None."""
    s = urlsplit(url.strip())
    host, path = (s.hostname or "").lower(), s.path
    params = {k.lower(): v for k, v in parse_qsl(s.query)}
    if "gh_jid" in params:
        return "greenhouse:" + params["gh_jid"]
    m = re.search(r"greenhouse\.io$", host) and re.search(r"/jobs/(\d+)", path)
    if m:
        return "greenhouse:" + m.group(1)
    m = re.search(r"(?:^|\.)(lever\.co|ashbyhq\.com)$", host) and re.search(r"/([0-9a-f]{8}-[0-9a-f-]{27,})", path, re.I)
    if m:
        return "%s:%s" % (host.split(".")[-2], m.group(1).lower())
    m = host.endswith("myworkdayjobs.com") and re.search(r"_([A-Z]*-?\d[\w-]*)$", path.rstrip("/"))
    if m:
        return "workday:%s:%s" % (host.split(".")[0], m.group(1))
    m = host.endswith("smartrecruiters.com") and re.search(r"/(\d{6,})", path)
    if m:
        return "smartrecruiters:" + m.group(1)
    return None


def keys(url):
    if not clean(url):
        return set()
    k = {canonical(url)}
    jid = job_id(url)
    if jid:
        k.add(jid)
    return k


norm = logfiles.norm


# ---- Reports ----

read = logfiles.read_text


def reports(root):
    """[(date, n, path)] of the scan reports, oldest first."""
    out = []
    for p in glob.glob(os.path.join(root, REPORTS, "*-scan*.md")):
        m = REPORT_NAME.match(os.path.basename(p))
        if m:
            out.append((m.group(1), int(m.group(2) or 1), p))
    return sorted(out)


cells = logfiles.md_cells   # `\|` in a cell is a `|` of its text


def pending_table(text):
    """(start, end, rows): the line range of the `## Pending` table and its rows as dicts."""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == "## Pending"), None)
    if start is None:
        return None, None, []
    i = start + 1
    while i < len(lines) and not lines[i].strip().startswith("|"):
        if lines[i].startswith("#"):
            return None, None, []
        i += 1
    first = i
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        c = cells(lines[i])
        if i >= first + 2 and len(c) == len(PENDING_COLUMNS):
            rows.append({key: value for (_, key), value in zip(PENDING_COLUMNS, c)} | {"_line": i})
        i += 1
    return first, i, rows


def table_lines(rows):
    out = ["| " + " | ".join(h for h, _ in PENDING_COLUMNS) + " |",
           "|" + "---|" * len(PENDING_COLUMNS)]
    for r in rows:
        out.append(logfiles.md_row(str(r.get(k) or "-") for _, k in PENDING_COLUMNS))
    return out


def newest_rows(root):
    """{canonical url: (report path, row)} from the newest report that lists each URL."""
    out = {}
    for _, _, p in reports(root):
        for r in pending_table(read(p))[2]:
            out[canonical(r["url"])] = (p, r)
    return out


# ---- git ----

def git(root, *args, check=False):
    """The finished git call (it never waits on a credential prompt); ScanError when git cannot start,
    gives no answer in 120 s, or, with check, exits non-zero."""
    try:
        p = logfiles.git_run(root, *args, timeout=120)
    except logfiles.LogError as e:
        raise ScanError("git %s: %s" % (" ".join(args), e))
    if check and p.returncode != 0:
        raise ScanError("git %s: %s" % (" ".join(args), p.stderr.strip()))
    return p


def has_remote(root):
    return git(root, "remote", "get-url", "origin").returncode == 0


def fetch(root):
    """`git fetch --prune origin` when origin exists: [] on success or with no remote, else the
    `fetch: failed` line."""
    if not has_remote(root):
        return []
    try:
        p = git(root, "fetch", "-q", "--prune", "origin")
    except ScanError as e:   # a timeout, or no git
        return ["fetch: failed (%s); origin's branches as last fetched" % e]
    if p.returncode == 0:
        return []
    err = (p.stderr.strip().splitlines() or ["exit %d" % p.returncode])[-1]
    return ["fetch: failed (%s); origin's branches as last fetched" % err]


def scan_branches(root):
    """{branch name: (local?, on origin?)} for the scan/* branches git knows."""
    out = {}
    p = git(root, "for-each-ref", "--format=%(refname)", "refs/heads/scan/", "refs/remotes/origin/scan/")
    for ref in p.stdout.split():
        if ref.startswith("refs/heads/"):
            name = ref[len("refs/heads/"):]
            out[name] = (True, out.get(name, (False, False))[1])
        else:
            name = ref[len("refs/remotes/origin/"):]
            out[name] = (out.get(name, (False, False))[0], True)
    return {b: v for b, v in out.items() if BRANCH_NAME.match(b)}


def delete_branch(root, branch, where, dry_run, force=False):
    """Remove the branch's worktree (with uncommitted changes only when force), the local branch and the
    one on origin; one line each."""
    local, remote = where
    out = []
    p = git(root, "worktree", "list", "--porcelain")
    path = None
    for line in p.stdout.split("\n"):
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.strip() == "branch refs/heads/" + branch and path:
            out.append("worktree %s" % path)
            if not dry_run:
                git(root, "worktree", "remove", *(["--force"] if force else []), path, check=True)
    if local:
        out.append("local branch")
        if not dry_run:
            git(root, "branch", "-D", branch, check=True)
    if remote:
        out.append("origin's branch")
        if not dry_run:
            p = git(root, "push", "-q", "origin", "--delete", branch)
            if p.returncode != 0:
                if "remote ref does not exist" not in p.stderr:
                    raise ScanError("git push origin --delete %s: %s" % (branch, p.stderr.strip()))
                git(root, "update-ref", "-d", "refs/remotes/origin/" + branch)   # deleted from another clone
    return out


# ---- Commands ----

def next_name(root, date):
    taken = {(d, n) for d, n, _ in reports(root)}
    for b in scan_branches(root):
        m = BRANCH_NAME.match(b)
        taken.add((m.group(1), int(m.group(2) or 1)))
    for d in glob.glob(os.path.join(root, ".build", "scan", "*")):
        m = BRANCH_NAME.match("scan/" + os.path.basename(d))
        if m and os.path.isdir(d):
            taken.add((m.group(1), int(m.group(2) or 1)))
    n = 1
    while (date, n) in taken:
        n += 1
    return date + ("" if n == 1 else "-%d" % n)


def check_budgets(screen_budget, fit_budget):
    if screen_budget < 1 or fit_budget < 1:
        raise ScanError("--screen-budget and --fit-budget must be 1 or more")
    if screen_budget < fit_budget:
        raise ScanError("screen_budget (%d) is below fit_budget (%d): the user picks which one to change"
                        % (screen_budget, fit_budget))


def run_paths(name):
    """{report, branch, worktree, drafts, dir} of the run named `name` (`2026-10-22-2`), relative to the
    Log's root, as `name` prints them."""
    return {"report": "%s/%s-scan%s.md" % (REPORTS, name[:10], name[10:]),
            "branch": "scan/" + name,
            "worktree": ".build/worktrees/scan-" + name,
            "drafts": ".build/scan/%s/drafts" % name,
            "dir": ".build/scan/%s" % name}


def cmd_name(root, date, screen_budget=None, fit_budget=None):
    if (screen_budget is None) != (fit_budget is None):
        raise ScanError("give --screen-budget and --fit-budget together")
    if screen_budget is not None:
        check_budgets(screen_budget, fit_budget)
    warn = fetch(root)
    name = next_name(root, date)
    paths = run_paths(name)
    return warn + ["name: " + name] + ["%s: %s" % (k, paths[k]) for k in ("report", "branch", "worktree", "drafts", "dir")] + \
        ["remote: " + ("yes" if has_remote(root) else "no")]


SOURCES = "scan-sources.md"
SOURCE_FIELDS = ("URL", "Kind", "Read", "Fields")
KINDS = ("signed-in job board", "public job board", "GitHub list")
CLONES = ".build/scan-sources"   # where a GitHub list source is cloned (cmd_sources)


def read_sources(root):
    """[(name, {field: value})] of scan-sources.md's `## <source>` sections, in order; [] when the
    file is missing."""
    path = os.path.join(root, SOURCES)
    if not os.path.exists(path):
        return []
    text = logfiles.strip_comments(read(path))
    out = []
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        name, _, body = part.partition("\n")
        fields = {}
        for b in logfiles.bullets(body):
            m = re.match(r"(\w+):\s*(.*)$", b)
            if m and m.group(1) in SOURCE_FIELDS:
                fields.setdefault(m.group(1), m.group(2).strip())
        out.append((name.strip(), fields))
    return out


def source_slugs(names):
    """{name: its slug}: the name's ASCII slug, or its short hash when it has none or another name in
    the list slugs the same (`Jobs list`, `jobs-list`); a name given twice gets one slug. A GitHub
    list's clone folder and a job board's Browser session are named from it (cmd_sources)."""
    slugs = {n: logfiles.ascii_slug(n) for n in names}
    taken = {}
    for n, s in slugs.items():
        taken.setdefault(s, set()).add(n)
    return {n: s if s and len(taken[s]) == 1 else (s + "-" if s else "") + short_hash(n)
            for n, s in slugs.items()}


def cmd_sources(root):
    found = read_sources(root)
    if not found:
        why = "no %s" % SOURCES if not os.path.exists(os.path.join(root, SOURCES)) else "no ## section"
        return ["sources: none (%s)" % why]
    slugs = source_slugs([name for name, _ in found])

    def state(v):
        return "GAP" if not v or v.startswith("GAP") else "set"
    out = []
    for name, f in found:
        kind = "GAP" if state(f.get("Kind")) == "GAP" else f["Kind"]
        if kind not in KINDS and kind != "GAP":
            kind = "unknown (%s)" % kind
        tail = (" | clone %s/%s" % (CLONES, slugs[name]) if kind == "GitHub list"
                else " | session scan-" + slugs[name] if kind in KINDS else "")
        out.append("source: %s | kind %s | url %s | read %s | fields %s%s"
                   % (name, kind, f.get("URL") or "GAP", state(f.get("Read")), state(f.get("Fields")), tail))
    out.append("sources: %d" % len(found))
    return out


def read_declined(root):
    p = os.path.join(root, DECLINED)
    if not os.path.exists(p):
        return []
    out = []
    for i, line in enumerate(read(p).split("\n"), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ScanError("%s line %d does not parse: %s" % (DECLINED, i, e))
    return out


def write_declined(root, items):
    p = os.path.join(root, DECLINED)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def cmd_prune(root, date, dry_run):
    cutoff = (datetime.date.fromisoformat(date) - datetime.timedelta(days=PRUNE_DAYS)).isoformat()
    warn = fetch(root)
    out = []
    items = read_declined(root)
    keep = [i for i in items if str(i.get("date", "")) >= cutoff]
    for i in items:
        if i not in keep:
            out.append("pruned: declined %s (%s)" % (i.get("url"), i.get("date")))
    if len(keep) != len(items) and not dry_run:
        write_declined(root, keep)
    for branch, where in sorted(scan_branches(root).items()):
        if BRANCH_NAME.match(branch).group(1) < cutoff:
            out.append("pruned: %s (%s)" % (branch, ", ".join(delete_branch(root, branch, where, dry_run, force=True))))
    out.append("prune: %d line(s) and branch(es) older than %s%s"
               % (len(out), cutoff, " (dry run: nothing deleted)" if dry_run else ""))
    return warn + out


def cmd_pending(root):
    rs = reports(root)
    if not rs:
        return ["report: none", "pending: none"]
    path = rs[-1][2]
    rows = [r for r in pending_table(read(path))[2] if r["status"] in PENDING]
    out = ["report: " + os.path.relpath(path, root).replace(os.sep, "/")]
    for r in rows:
        try:
            state = cmd_fitmap(root, r["url"])[-1][len("fit map: "):]
        except ScanError as e:   # no git: the rows still show
            state = "unknown (%s)" % e
        out.append("pending: " + " | ".join(str(c).replace("|", "\\|") for c in
                                            (r["url"], r["company"], r["role"], r["status"], r["draft"]))
                   + " | fit map " + state)
    out.append("count: %d pending row(s)" % len(rows) if rows else "pending: none")
    return out


def url_keys(text):
    """(keys, has a job id) of every URL in the text."""
    k, jid = set(), False
    for u in urls(text):
        k |= keys(u)
        jid = jid or job_id(u) is not None
    return k, jid


def applied_records(root):
    """[(keys, has a job id, match, where)] for each application record (logfiles.application_records):
    the keys of the URLs it holds, and match(company, role, city), the company-and-role fallback."""
    return [url_keys(text) + (match, where) for text, match, where in logfiles.application_records(root)]


def seen_dates(root):
    out = {}
    for date, _, p in reports(root):
        for u in urls(read(p)):
            out.setdefault(canonical(u), date)
    return out


def cmd_dedup(root, src, dst, date=None, window=None):
    cutoff = None
    if window is not None:
        if window < 0:
            raise ScanError("--window must be 0 or more days")
        cutoff = (datetime.date.fromisoformat(date) - datetime.timedelta(days=window)).isoformat()
    postings = []
    for i, line in enumerate(read(src).split("\n"), 1):
        if line.strip():
            try:
                postings.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ScanError("%s line %d does not parse: %s" % (src, i, e))
    applied = applied_records(root)
    declined = {}
    for item in read_declined(root):
        for k in keys(str(item.get("url", ""))):
            declined.setdefault(k, item.get("date"))
    seen = seen_dates(root)
    kept, dropped, out, batch, undated = [], [], [], set(), []
    reasons = {"before the window": 0, "applied": 0, "declined": 0, "repeated": 0}
    for p in postings:
        url = str(p.get("url") or "")
        if not url:
            raise ScanError("%s: a posting without a url: %s" % (src, json.dumps(p, ensure_ascii=False)))
        k = keys(url)
        why = undated_line = None
        if cutoff:
            posted = str(p.get("posted") or "").strip()
            m = re.match(r"(\d{4}-\d{2}-\d{2})(?:$|[T ])", posted)
            if not m:
                undated_line = 'undated: %s (posted "%s"): kept; write it as YYYY-MM-DD to window it' % (url, posted)
            elif m.group(1) < cutoff:
                why, kind = "posted %s, before the window (from %s)" % (m.group(1), cutoff), "before the window"
        for rk, _, _, where in ([] if why else applied):
            if k & rk:
                why, kind = "applied: %s" % where, "applied"
                break
        if not why:
            company, role = norm(p.get("company")), norm(p.get("role"))
            city = norm(str(p.get("location") or "").split(",")[0])
            has_id = job_id(url) is not None
            for _, rec_id, match, where in applied:
                if company.strip() and role.strip() and not (has_id and rec_id) and match(company, role, city):
                    why, kind = "applied: %s, by company and role" % where, "applied"
                    break
        if not why:
            hits = [declined[x] for x in k if x in declined]
            if hits:
                why, kind = "declined %s" % hits[0], "declined"
        if not why and k & batch:
            why, kind = "repeated in this batch", "repeated"
        if why:
            reasons[kind] += 1
            dropped.append(dict(p, drop=kind, why=why))
            out.append("dropped: %s (%s)" % (url, why))
            continue
        batch |= k
        if undated_line:
            undated.append(undated_line)
        p["seen"] = seen.get(canonical(url))
        kept.append(p)
    write_jsonl(dst, kept)
    write_jsonl(os.path.join(os.path.dirname(dst), DEDUP_DROPPED), dropped)
    listed = sum(1 for p in kept if p["seen"])
    out += undated
    out.append("kept: %d (%d new, %d listed before); dropped: %d; written to %s"
               % (len(kept), len(kept) - listed, listed, len(postings) - len(kept), dst))
    out.append("dropped by reason: " + ", ".join("%s %d" % kv for kv in reasons.items()))
    return out


# ---- Prefilter ----

def cmd_prefilter(root, d):
    d = at_root(root, d)
    kept = read_jsonl(os.path.join(d, "kept.jsonl"))
    marks = read_jsonl(os.path.join(d, "titles.jsonl"))
    tiers = fit.ranks(root)   # a tier is its line's place, `GAP:` lines counted, as fit.py heatmap reads it
    problems, by_posting = [], {}
    index = {}
    for i, p in enumerate(kept):
        for k in keys(str(p.get("url") or "")):
            index.setdefault(k, i)
    for n, m in enumerate(marks, 1):
        url = str(m.get("url") or "")
        i = next((index[k] for k in keys(url) if k in index), None)
        where = "titles.jsonl line %d (%s)" % (n, url or "no url")
        if i is None:
            problems.append("extra: %s: no posting of kept.jsonl has this url" % where)
            continue
        if i in by_posting:
            problems.append("repeated: %s: kept.jsonl's posting has a line already" % where)
            continue
        t, drop = m.get("tier"), m.get("drop")
        why = fit.tier_problem(t, tiers)
        if why:
            problems.append("bad: %s: tier %s" % (where, why))
        if drop not in (None, "") and not (drop == "role" or re.match(r"constraint: \S", str(drop))):
            problems.append('bad: %s: drop must be "role" or "constraint: <which>"' % where)
        elif drop == "role" and not tiers:
            problems.append("bad: %s: dropped for its role, but direction.md's Target roles are empty" % where)
        by = m.get("by")
        if by not in (None, "") and by != "content":
            problems.append('bad: %s: by must be "content"' % where)
        elif by and (t is None or drop):
            problems.append("bad: %s: by content needs the close target's tier, and no drop" % where)
        by_posting[i] = m
    for i, p in enumerate(kept):
        if i not in by_posting:
            problems.append("missing: %s has no line in titles.jsonl" % p.get("url"))
    if problems:
        raise ScanError("prefilter: %d problem(s); fix titles.jsonl and run it again\n%s"
                        % (len(problems), "\n".join(problems)))
    order = {name: i for i, (name, _) in enumerate(read_sources(root))}
    passed, dropped, counts, out = [], [], {}, []
    for i, p in enumerate(kept):
        m = by_posting[i]
        if m.get("drop"):
            dropped.append(dict(p, drop=m["drop"]))
            counts[m["drop"]] = counts.get(m["drop"], 0) + 1
            out.append("dropped: %s (%s)" % (p.get("url"), m["drop"]))
        else:
            passed.append((i, dict(p, tier=m.get("tier"), **({"by": "content"} if m.get("by") else {}))))
            if m.get("by"):
                out.append("close: %s (tier %d, by content: Screen tiers it)" % (p.get("url"), m["tier"]))
    passed.sort(key=lambda ip: (ip[1]["tier"] is None, ip[1]["tier"] or 0, "by" in ip[1],
                                order.get(str(ip[1].get("source") or ""), len(order)), ip[0]))
    write_jsonl(os.path.join(d, "prefiltered.jsonl"), [p for _, p in passed])
    write_jsonl(os.path.join(d, "prefilter-dropped.jsonl"), dropped)
    if not tiers:
        out.append("target roles: empty (no title was dropped for its role; the report says so)")
    unknown = sorted({str(p.get("source") or "") for _, p in passed} - set(order))
    if unknown:
        out.append("sources not in %s (ordered last): %s" % (SOURCES, ", ".join(unknown)))
    out.append("prefilter: %d kept, written to prefiltered.jsonl; %d dropped%s"
               % (len(passed), len(dropped),
                  " (%s)" % ", ".join("%s %d" % kv for kv in sorted(counts.items())) if counts else ""))
    return out


fit_maps = fit.fit_maps   # [(url, sha, body)] of a report's fit maps


def ranking_recommendation(text, url):
    """The recommendation a report's `## Ranking` line for the URL names (a report from before fit maps
    kept a `Recommendation:` line), or None."""
    body = logfiles.section(text, "Ranking") or ""
    for line in body.split("\n"):
        if any(keys(u) & keys(url) for u in urls(line)):
            low = line.lower()
            for r in sorted(fit.RECOMMENDATIONS, key=len, reverse=True):
                if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(r), low):
                    return r
    return None


def cmd_fitmap(root, url, out=None):
    want = keys(url)
    found = None
    for _, _, p in reports(root):
        text = read(p)
        for u, sha, body in fit_maps(text):
            if keys(u) & want:
                found = (p, sha, body, text)
    if not found:
        return ["fit map: none"]
    p, sha, body, text = found
    rel = os.path.relpath(p, root).replace(os.sep, "/")
    lines = ["fit map: %s (entries commit %s)" % (rel, sha or "missing")]
    if not sha or git(root, "cat-file", "-e", sha + "^{commit}").returncode != 0:
        return lines + ["fit map: stale (its entries commit is missing or unknown)"]
    changed = []
    for name in fit.cited_entries(body):
        path = "entries/" + name
        p_ = git(root, "log", "--format=%h", sha + "..HEAD", "--", path)
        if p_.stdout.strip() or not os.path.exists(os.path.join(root, path)):
            changed.append(path)
    if changed:
        return lines + ["fit map: stale (%s)" % ", ".join(changed)]
    if out:
        rec = fit.recommendation(body) or ranking_recommendation(text, url)
        rows = fit.map_rows(body)
        if rec not in fit.RECOMMENDATIONS or not rows:
            return lines + ["fit map: stale (%s)" % ("its map has no table with a Requirement column" if not rows
                                                     else "no recommendation in the report")]
        result = {"url": clean(url), "recommendation": rec, "check": [], "notes": [], "rows": rows,
                  "fit_commit": sha, "reused": rel, "text": fit.body_text(body)}
        bad = fit.problems(result)
        if bad:   # a column or a value this format does not know: fitted again
            return lines + ["fit map: stale (its map's rows do not parse: %s)" % bad[0]]
        write_jsonl(at_root(root, out), [result])
        lines.append("wrote: %s" % os.path.relpath(at_root(root, out), root).replace(os.sep, "/"))
    return lines + ["fit map: reuse"]


# ---- Screen ----

DROPPED_COLUMNS = [("URL", "url"), ("Company", "company"), ("Role", "role"), ("Reason", "reason"), ("Screen key", "key")]
SCREENED_COLUMNS = [("Company", "company"), ("Role", "role"), ("URL", "url"), ("Tier", "tier"), ("Rough", "rough"),
                    ("Screen key", "key")]
SCREEN_LINE = re.compile(r"^Screen:\s*tier\s+(\S+),\s*rough\s+(\d+)/(\d+),\s*key\s+([0-9a-f]{8}-[0-9a-f]{8})\s*$", re.M)


def at_root(root, path):
    return path if os.path.isabs(path) else os.path.join(root, path)


def jsonl_lines(path):
    """[(line number, object or None, why None)] of a JSON Lines file, a line that does not parse or
    holds no JSON object with its why."""
    out = []
    for i, line in enumerate(read(path).split("\n"), 1):
        if line.strip():
            try:
                item = json.loads(line)
            except json.JSONDecodeError as e:
                out.append((i, None, "does not parse: %s" % e))
                continue
            out.append((i, item, None) if isinstance(item, dict) else (i, None, "is no JSON object"))
    return out


def read_jsonl(path):
    out = []
    for i, item, why in jsonl_lines(path):
        if why:
            raise ScanError("%s line %d %s" % (path, i, why))
        out.append(item)
    return out


def write_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def short_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def screen_key(root):
    """`<list>-<direction>`, as the docstring says."""
    tool = os.path.join(HERE, "entries.py")
    p = subprocess.run([sys.executable, "-I", tool, "list", "--root", root], capture_output=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        raise ScanError("tools/entries.py list: %s" % (p.stdout + p.stderr).strip())
    listing = "\n".join(re.sub(r"; status [^;]*; tokens \d+(?: \(over threshold\))?;", ";", line)
                        for line in p.stdout.splitlines())
    direction = os.path.join(root, "direction.md")
    text = read(direction).replace("\r\n", "\n") if os.path.exists(direction) else ""
    parts = []
    for name in SECTIONS:
        m = re.search(r"^## %s[ \t]*$(.*?)(?=^## |\Z)" % re.escape(name), text, re.M | re.S)
        parts.append(m.group(1).strip() if m else "")
    return short_hash(listing) + "-" + short_hash("\n\n".join(parts))


def section_table(text, heading):
    """The rows of the first table under `## <heading>`, as lists of cells."""
    m = re.search(r"^## %s[ \t]*$(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    if not m:
        return []
    rows = [cells(l) for l in m.group(1).split("\n") if l.strip().startswith("|")]
    return rows[2:]


def tier_value(cell):
    cell = str(cell).strip()
    return int(cell) if re.fullmatch(r"\d+", cell) else None


def report_screens(root):
    """{canonical url: (report, result)}: the newest Screen result each report records for a URL."""
    out = {}
    for _, _, p in reports(root):
        text = read(p)
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        found = []
        for c in section_table(text, "Dropped at screen"):
            if len(c) == len(DROPPED_COLUMNS):
                found.append({"url": clean(c[0]), "gate": "no", "reason": c[3], "tier": None, "touched": 0,
                              "required": 0, "key": c[4]})
        for c in section_table(text, "Screened, not fully fitted"):
            m = re.fullmatch(r"(\d+)/(\d+)", c[4]) if len(c) == len(SCREENED_COLUMNS) else None
            if m:
                found.append({"url": clean(c[2]), "gate": "yes", "tier": tier_value(c[3]), "touched": int(m.group(1)),
                              "required": int(m.group(2)), "key": c[5]})
        for u, _, body in fit_maps(text):
            m = SCREEN_LINE.search(body)
            if m:
                found.append({"url": u, "gate": "yes", "tier": tier_value(m.group(1)), "touched": int(m.group(2)),
                              "required": int(m.group(3)), "key": m.group(4)})
        for r in found:
            out[canonical(r["url"])] = (rel, r)
    return out


def slug(text):
    return logfiles.ascii_slug(text) or "posting"


def capture_url(path):
    """The first URL in a capture's first three lines, or None."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            head = "".join(f.readline() for _ in range(3))
    except OSError:
        return None
    found = urls(head)
    return found[0] if found else None


def earlier_captures(root, here):
    """{key: path} of the captures other runs left in .build/scan/*/postings/."""
    out = {}
    for p in sorted(glob.glob(os.path.join(root, ".build", "scan", "*", "postings", "*.md"))):
        if os.path.dirname(os.path.dirname(os.path.abspath(p))) == os.path.abspath(here):
            continue
        u = capture_url(p)
        for k in keys(u) if u else ():
            out[k] = p
    return out


def rough(touched, required):
    return "%d/%d" % (touched, required)


def tally(result):
    """(touched, required) of a Screen result, as the docstring says."""
    if "rows" not in result:
        return int(result.get("touched") or 0), int(result.get("required") or 0)
    rows = result["rows"]
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ScanError("%s: rows must be a list of objects" % result.get("url"))
    counted = [r for r in rows if r.get("kind") in ("required", "duty")] or rows
    return sum(1 for r in counted if any(isinstance(e, str) and e.strip() for e in r.get("entries") or [])), len(counted)


def check_result(r, where, tiers):
    """A Screen result's problem as a ScanError; `tiers` is fit.ranks()'s map, which its tier must fit."""
    found = urls(str(r.get("url") or ""))   # a subagent may copy the capture's whole first line
    if not found:
        raise ScanError("%s: a result without a url: %s" % (where, json.dumps(r, ensure_ascii=False)))
    r["url"] = found[0]
    for row in r.get("rows") or []:
        if not isinstance(row, dict) or row.get("kind") not in ("required", "preferred", "duty") \
                or not isinstance(row.get("entries"), list):
            raise ScanError("%s: %s: each row needs a kind (required, preferred or duty) and an entries list"
                            % (where, r["url"]))
    if r.get("gate") not in ("yes", "no"):
        raise ScanError("%s: %s: gate must be yes or no" % (where, r.get("url")))
    if r["gate"] == "no" and not str(r.get("reason") or "").strip():
        raise ScanError("%s: %s: a gate no needs its reason" % (where, r.get("url")))
    why = fit.tier_problem(r.get("tier"), tiers)
    if why:
        raise ScanError("%s: %s: tier %s" % (where, r.get("url"), why))
    if r["gate"] == "yes" and "rows" not in r and "touched" not in r:
        raise ScanError("%s: %s: a gate yes needs its rows" % (where, r.get("url")))


def cmd_screen(root, date, d, screen_budget, fit_budget, sort, give_up=False):
    check_budgets(screen_budget, fit_budget)
    d = at_root(root, d)
    if sort:
        return screen_sort(root, date, d, fit_budget, give_up)
    return screen_prepare(root, date, d, screen_budget)


def cmd_screen_check(root, results, batch=None):
    """Each line of a Screen results file checked as --sort checks it, and, with a batch, one line
    for each capture of the batch that has a file and none for another posting."""
    results = at_root(root, results)
    problems, found = [], []
    tiers = fit.ranks(root)
    for n, r, why in jsonl_lines(results):
        if why:
            problems.append("bad: line %d %s" % (n, why))
            continue
        try:
            check_result(r, "line %d" % n, tiers)
        except ScanError as e:
            problems.append("bad: %s" % e)
            continue
        found.append((n, r["url"]))
    if batch:
        batch = at_root(root, batch)
        want = []
        for line in read(batch).split("\n"):
            cap = line.strip()
            if cap and os.path.exists(at_root(root, cap)):
                u = capture_url(at_root(root, cap))
                if not u:
                    problems.append("bad: %s: no URL in its first lines" % cap)
                else:
                    want.append((cap, u))
        hit = {}
        for n, u in found:
            match = [i for i, (_, w) in enumerate(want) if keys(w) & keys(u)]
            i = next((i for i in match if i not in hit), None)
            if not match:
                problems.append("extra: line %d: %s is no capture of the batch" % (n, u))
            elif i is None:
                problems.append("repeated: line %d: %s has line %d already" % (n, u, hit[match[0]]))
            else:
                hit[i] = n
        problems += ["missing: %s (%s) has no line" % (cap, u) for i, (cap, u) in enumerate(want) if i not in hit]
    if problems:
        raise ScanError("screen --check: %d problem(s) in %s\n%s" % (len(problems), results, "\n".join(problems)))
    return ["check: ok, %d result(s)%s" % (len(found), ", one per capture of the batch" if batch else "")]


def screen_prepare(root, date, d, budget):
    postings = read_jsonl(os.path.join(d, "prefiltered.jsonl"))
    key = screen_key(root)
    earlier = earlier_captures(root, d)
    stored = report_screens(root)
    folders, listed = set(), []
    for i, p in enumerate(postings[:budget]):
        if not p.get("url"):
            raise ScanError("prefiltered.jsonl: a posting without a url: %s" % json.dumps(p, ensure_ascii=False))
        base = "%s-%s-%s" % (date, slug(p.get("company")), slug(p.get("role")))
        folder, n = base, 2
        while folder in folders:
            folder, n = "%s-%d" % (base, n), n + 1
        folders.add(folder)
        listed.append(dict(p, order=i + 1, folder=folder,
                           capture=os.path.join(d, "postings", folder + ".md").replace(os.sep, "/")))
    write_jsonl(os.path.join(d, "screen-list.jsonl"), listed)
    write_jsonl(os.path.join(d, "not-screened.jsonl"), postings[budget:])
    sdir = os.path.join(d, "screen")
    os.makedirs(sdir, exist_ok=True)
    for old in glob.glob(os.path.join(sdir, "*.todo")) + glob.glob(os.path.join(sdir, "*.jsonl")):
        os.remove(old)   # results of an earlier prepare may have another key
    with open(os.path.join(sdir, "key"), "w", encoding="utf-8", newline="\n") as f:
        f.write(key + "\n")
    reused, todo, out = [], [], ["key: " + key]
    for p in listed:
        cap = os.path.join(root, p["capture"]) if not os.path.isabs(p["capture"]) else p["capture"]
        state = "have"
        held = keys(capture_url(cap) or "") if os.path.exists(cap) else set()
        if held and not held & keys(p["url"]) and any(held & keys(o["url"]) for o in listed if o is not p):
            os.replace(cap, cap + ".stale")   # another posting's capture, from before the list's order changed
        if not os.path.exists(cap):
            hit = next((earlier[k] for k in keys(p["url"]) if k in earlier), None)
            if hit:
                os.makedirs(os.path.dirname(cap), exist_ok=True)
                shutil.copyfile(hit, cap)
                state = "copied"
            else:
                state = "need"
        s = next((stored[k] for k in [canonical(p["url"])] if k in stored), None)
        if s and s[1]["key"] == key:
            reused.append(dict(s[1], url=p["url"], reused=s[0]))
            how = "reused " + s[0]
        else:
            todo.append(p)
            how = None
        p["_line"] = "posting: %s | capture %s (%s) | screen " % (p["url"], p["capture"], state)
        p["_how"] = how
    write_jsonl(os.path.join(sdir, "reused.jsonl"), reused)
    for b in range(0, len(todo), BATCH):
        name = "batch-%d" % (b // BATCH + 1)
        with open(os.path.join(sdir, name + ".todo"), "w", encoding="utf-8", newline="\n") as f:
            for p in todo[b:b + BATCH]:
                f.write(p["capture"] + "\n")
                p["_how"] = name
    out += [p["_line"] + p["_how"] for p in listed]
    out.append("screen: %d posting(s) listed, %d reused, %d in %d batch(es); %d not screened (past the budget)"
               % (len(listed), len(reused), len(todo), -(-len(todo) // BATCH), len(postings) - len(listed)))
    return out


def screen_sort(root, date, d, budget, give_up=False):
    listed = read_jsonl(os.path.join(d, "screen-list.jsonl"))
    key = screen_key(root)
    kfile = os.path.join(d, "screen", "key")
    if not os.path.exists(kfile) or read(kfile).strip() != key:
        raise ScanError("the entry list or direction.md changed since `screen` without --sort ran (key %s):"
                        " run it again, then screen the batches it prints" % key)
    results, tiers = {}, fit.ranks(root)
    for path in sorted(glob.glob(os.path.join(d, "screen", "*.jsonl"))):
        for r in read_jsonl(path):
            check_result(r, os.path.basename(path), tiers)
            for k in keys(str(r.get("url") or "")):
                results[k] = r
    missing, unreadable, passed, dropped = [], [], [], []
    for p in listed:
        r = next((results[k] for k in keys(p["url"]) if k in results), None)
        if r is None:   # a subagent may give the URL its capture holds
            cap_url = capture_url(at_root(root, p["capture"]))
            r = next((results[k] for k in keys(cap_url or "") if k in results), None)
        if r is None:
            (missing if os.path.exists(at_root(root, p["capture"])) else unreadable).append(p)
            continue
        touched, required = tally(r)
        item = dict(p, gate=r["gate"], reason=r.get("reason") or "", tier=r.get("tier"), touched=touched,
                    required=required, rough=rough(touched, required), key=r.get("key") or key,
                    check=r.get("check") or [], reused=r.get("reused"))
        (passed if r["gate"] == "yes" else dropped).append(item)
    gave_up = []
    if missing and not give_up:
        raise ScanError("no Screen result yet for %d posting(s): %s" % (len(missing), ", ".join(p["url"] for p in missing)))
    for p in missing:   # --give-up: unreadable, its capture moved aside so no later run reuses it
        cap = at_root(root, p["capture"])
        os.replace(cap, cap + ".unreadable")
        unreadable.append(p)
        gave_up.append("gave up: %s (capture moved to %s.unreadable)" % (p["url"], p["capture"]))

    def order(p):
        share = p["touched"] / p["required"] if p["required"] else 0.0
        return (p["tier"] is None, p["tier"] or 0, -share, p["order"])
    passed.sort(key=order)
    to_fit, rest = passed[:budget], passed[budget:]
    write_jsonl(os.path.join(d, "fit.jsonl"), to_fit)
    write_jsonl(os.path.join(d, "screened.jsonl"), rest)
    write_jsonl(os.path.join(d, "dropped.jsonl"), dropped)
    write_jsonl(os.path.join(d, "unreadable.jsonl"), unreadable)
    out = gave_up + ["fit: %s | capture %s (%s)" % (p["url"], p["capture"],
                                          "have" if os.path.exists(at_root(root, p["capture"])) else "need")
           for p in to_fit]
    out.append("screen: %d to fit, %d screened, not fully fitted, %d dropped at screen, %d unreadable (no capture)"
               % (len(to_fit), len(rest), len(dropped), len(unreadable)))
    return out


class PageText(html.parser.HTMLParser):
    """The text a reader sees on an HTML page: no script, style or template, a line per block."""
    SKIP = {"script", "style", "noscript", "template", "svg", "title"}
    BLOCK = {"p", "div", "li", "ul", "ol", "br", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6",
             "section", "article", "main", "header", "footer", "table", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self):
        lines = (re.sub(r"[ \t ]+", " ", l).strip() for l in "".join(self.parts).split("\n"))
        return "\n".join(l for l in lines if l)


def page_text(body, content_type):
    if "html" not in content_type.lower() and not re.match(r"\s*<", body):
        return body.strip()
    p = PageText()
    p.feed(body)
    p.close()
    return p.text()


def http_get(url):
    """(status, content type, body) of a plain GET; the tests replace it."""
    req = urllib.request.Request(url, headers={"User-Agent": FETCH_AGENT, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(4_000_000)
            ctype = r.headers.get("Content-Type", "")
            charset = r.headers.get_content_charset() or meta_charset(raw) or "utf-8"
            try:
                return r.status, ctype, raw.decode(charset, "replace")
            except LookupError:   # a charset Python does not know
                return r.status, ctype, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, "", ""


def meta_charset(raw):
    """The charset a page's own <meta> names in its first 4 KB, or None."""
    m = re.search(rb"""<meta[^>]+charset=["']?([\w-]+)""", raw[:4096], re.I)
    return m.group(1).decode("ascii") if m else None


def is_api(url):
    """Whether the URL is a job board's posting API or another JSON endpoint, not a posting's page."""
    s = urlsplit(url)
    host, path = (s.hostname or "").lower(), s.path.lower()
    return (host.startswith("api.") or "-api." in host or host.startswith("api-") or "/api/" in path
            or re.match(r"/api(/|$)", path) or "/wday/cxs/" in path or path.endswith(".json"))


def fetch_log(root, path):
    """The run folder's FETCHED file for a capture path: <dir>/fetched.jsonl for <dir>/postings/<x>.md."""
    d = os.path.dirname(os.path.abspath(at_root(root, path)))
    if os.path.basename(d) == "postings":
        d = os.path.dirname(d)
    return os.path.join(d, FETCHED)


def fetched(root, path, url):
    """The fetch record of url in path's run folder, or None."""
    log = fetch_log(root, path)
    if not os.path.exists(log):
        return None
    want = keys(url)
    hit = None
    for _, item, _ in jsonl_lines(log):   # an API shares the posting's id: a fetch of it is no read of the page
        if item and not is_api(str(item.get("url") or "")) and keys(str(item.get("url") or "")) & want:
            hit = item
    return hit


def cmd_fetch(root, path, url):
    found = urls(url)
    if not found:
        raise ScanError("%s is not a URL" % url)
    url = found[0]
    if is_api(url):
        raise ScanError("fetch: %s is an API or JSON endpoint, not the posting's page\nnext: fetch the posting's own"
                        " URL, the one its list gave" % url)
    try:
        status, ctype, body = http_get(url)
        why = None if 200 <= status < 300 else "status %d" % status
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        status, ctype, body, why = 0, "", "", "no answer: %s" % getattr(e, "reason", e)
    text = page_text(body, ctype) if why is None else ""
    if why is None and len(text) < FETCH_MIN:
        why = "%d characters of text, a page built by script or a wall" % len(text)
    log = fetch_log(root, path)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"url": url, "status": status, "chars": len(text), "capture": why is None}) + "\n")
    if why:
        raise ScanError("fetch: no capture from %s (%s)\nnext: %sread the page with playwright-cli (browser.md ›"
                        " Fallback order item 2) and run capture with the file it wrote; when that read"
                        " gives no posting too, or on a machine without playwright-cli, a posting API may stand in"
                        " (capture --stand-in), else leave it unwritten"
                        % (url, why, "status %d: the posting may be gone; " % status if status in (404, 410) else ""))
    dst = at_root(root, path)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    logfiles.write_text(dst, url + "\n\n" + text + "\n")
    return ["capture: %s (%s, fetch, %d characters)" % (path, url, len(text)),
            "next: read the capture's first 30 lines; when they hold no posting (only navigation, a sign-in page),"
            " read the page with playwright-cli and run capture with the file it wrote"]


def cmd_capture(root, path, url, source, stand_in=None):
    found = urls(url)
    if not found:
        raise ScanError("%s is not a URL" % url)
    if fetched(root, path, found[0]) is None:
        raise ScanError("capture: refused: no fetch of %s on record, so its own page was never read\nnext: run"
                        " fetch %s %s first; when it gives no capture, read the page with playwright-cli; a"
                        " posting API stands in only when that read gives no posting too, or on a machine"
                        " without playwright-cli" % (found[0], path, found[0]))
    if stand_in is not None and not urls(stand_in):
        raise ScanError("--stand-in %s is not a URL" % stand_in)
    src = at_root(root, source)
    text = read(src)
    if src.lower().endswith(".json"):
        try:
            text = json.loads(text)
        except json.JSONDecodeError as e:
            raise ScanError("%s does not parse: %s" % (source, e))
        if not isinstance(text, str):
            raise ScanError("%s holds no text (an eval of `() => document.body.innerText` writes one JSON string)"
                            % source)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text.strip():
        raise ScanError("%s holds no text: leave the capture unwritten" % source)
    dst = at_root(root, path)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    logfiles.write_text(dst, found[0] + "\n\n" + text + "\n")
    via = ", stand-in %s" % urls(stand_in)[0] if stand_in else ""
    return ["capture: %s (%s, %d characters%s)" % (path, found[0], len(text), via)]


def md_table(columns, rows):
    out = ["| " + " | ".join(h for h, _ in columns) + " |", "|" + "---|" * len(columns)]
    for r in rows:
        out.append(logfiles.md_row("-" if r.get(k) in (None, "") else str(r.get(k)) for _, k in columns))
    return out


def screen_sections(root, d):
    d = at_root(root, d)
    dropped = read_jsonl(os.path.join(d, "dropped.jsonl")) if os.path.exists(os.path.join(d, "dropped.jsonl")) else []
    screened = read_jsonl(os.path.join(d, "screened.jsonl")) if os.path.exists(os.path.join(d, "screened.jsonl")) else []
    out = ["## Dropped at screen", ""]
    out += md_table(DROPPED_COLUMNS, dropped) if dropped else ["None."]
    out += ["", "## Screened, not fully fitted", "",
            "Matched against the entry list (`tools/entries.py list`), not the entries' full text. Saying"
            " \"look at\" one of these runs a full fit on it.", ""]
    out += md_table(SCREENED_COLUMNS, screened) if screened else ["None."]
    return out


def add_screen_lines(body, fitted):
    """The body with this run's `Screen:` line after the `URL:` line of each fit map in fitted, in place
    of any `Screen:` line a reused map brought."""
    by_key = {}
    for p in fitted:
        for k in keys(p["url"]):
            by_key[k] = p
    m = re.search(r"^## Fit maps[ \t]*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not m:
        return body
    parts = re.split(r"(?=^### )", m.group(1), flags=re.M)
    for i, part in enumerate(parts):
        u = re.search(r"^URL:(.*)$", part, re.M)
        found = urls(u.group(1)) if u else []
        if not found:
            continue
        p = next((by_key[k] for k in keys(found[0]) if k in by_key), None)
        if p:
            part = re.sub(SCREEN_LINE.pattern + r"\n?", "", part, flags=re.M)
            u = re.search(r"^URL:(.*)$", part, re.M)
            line = "Screen: tier %s, rough %s, key %s" % (p["tier"] if p["tier"] is not None else "-", p["rough"], p["key"])
            parts[i] = part[:u.end()] + "\n" + line + part[u.end():]
    return body[:m.start(1)] + "".join(parts) + body[m.end(1):]


# ---- Rank, the report's own sections, summary ----

RANKED_COLUMNS = [("Rank", "rank"), ("Company", "company"), ("Role", "role"), ("URL", "url"),
                  ("Recommendation", "recommendation"), ("Tier", "tier"), ("Required covered", "covered_share"),
                  ("Rough", "rough"), ("Source", "source"), ("Listed before", "seen")]
LISTED_COLUMNS = [("Company", "company"), ("Role", "role"), ("URL", "url")]


def run_file(d, name):
    """The objects of a run's JSON Lines file, or [] when it is missing."""
    p = os.path.join(d, name)
    return read_jsonl(p) if os.path.exists(p) else []


def fit_results(root, d):
    """{key: (file, result)} of the fit results in `<dir>/fit/`; ScanError listing every problem."""
    out, bad = {}, []
    for path in sorted(glob.glob(os.path.join(d, "fit", "*.jsonl"))):
        name = "fit/" + os.path.basename(path)
        try:
            r = fit.read_result(path)
        except fit.FitError as e:
            bad.append("bad: %s" % e)
            continue
        wrong = fit.problems(r)
        if wrong:
            bad += ["bad: %s: %s" % (name, w) for w in wrong]
            continue
        r["url"] = urls(r["url"])[0]
        other = next((out[k][0] for k in keys(r["url"]) if k in out), None)
        if other:
            bad.append("bad: %s: %s has a result in %s already" % (name, r["url"], other))
            continue
        for k in keys(r["url"]):
            out[k] = (name, r)
    if bad:
        raise ScanError("%d problem(s) in the fit results; run tools/fit.py check on each\n%s" % (len(bad), "\n".join(bad)))
    return out


def entries_commit(root):
    return git(root, "log", "-1", "--format=%h", "--", "entries").stdout.strip()


def draft_picks(head, m):
    """The postings to draft: the first m of the top n (`head`, in rank order) not recommended skip."""
    return [p for p in head if p["recommendation"] != "skip"][:m]


def cmd_rank(root, d, n, m=None, give_up=False):
    if n < 1 or (m is not None and m < 0):
        raise ScanError("--n must be 1 or more, and --m 0 or more")
    d = at_root(root, d)
    postings = read_jsonl(os.path.join(d, "fit.jsonl"))
    results = fit_results(root, d)
    sha = entries_commit(root)
    fitted, missing, unreadable = [], [], []
    for p in postings:
        hit = next((results[k] for k in keys(p["url"]) if k in results), None)
        if hit is None:   # a subagent may give the URL its capture holds
            cap_url = capture_url(at_root(root, p["capture"]))
            hit = next((results[k] for k in keys(cap_url or "") if k in results), None)
        if hit is None:
            (missing if os.path.exists(at_root(root, p["capture"])) else unreadable).append(p)
            continue
        r = hit[1]
        covered, required = fit.coverage(r["rows"])
        fitted.append(dict(p, recommendation=r["recommendation"], covered=covered, required_rows=required,
                           covered_share="%d/%d" % (covered, required),
                           fit_commit=r.get("fit_commit") or sha, result=r))
    if missing and not give_up:
        raise ScanError("no fit result yet for %d posting(s): %s" % (len(missing), ", ".join(p["url"] for p in missing)))
    out = []
    for p in missing:   # --give-up: unreadable, its capture moved aside so no later run reuses it
        cap = at_root(root, p["capture"])
        os.replace(cap, cap + ".unreadable")
        unreadable.append(p)
        out.append("gave up: %s (capture moved to %s.unreadable)" % (p["url"], p["capture"]))
    # unreadable.jsonl: screen --sort's lines, then this step's (rewritten, so a rerun adds none twice)
    kept = [u for u in run_file(d, "unreadable.jsonl") if u.get("at") != "fit"]
    write_jsonl(os.path.join(d, "unreadable.jsonl"), kept + [dict(p, at="fit") for p in unreadable])

    def order(p):
        share = p["covered"] / p["required_rows"] if p["required_rows"] else 0.0
        return (fit.RECOMMENDATIONS.index(p["recommendation"]), p["tier"] is None, p["tier"] or 0, -share, p["order"])
    fitted.sort(key=order)
    for i, p in enumerate(fitted, 1):
        p["rank"] = i
    head = fitted[:n]
    write_jsonl(os.path.join(d, "ranked.jsonl"), fitted)
    write_jsonl(os.path.join(d, "rows.jsonl"), [{"url": p["url"], "company": p.get("company") or "", "role": p.get("role") or "",
                                                 "status": "undecided", "draft": "", "fit_commit": p["fit_commit"]}
                                                for p in head])
    out += ["rank: %d | %s | %s | %s | %s | %s" % (p["rank"], p.get("company"), p.get("role"), p["recommendation"],
                                                   p["covered_share"], p["url"]) for p in head]
    if len(fitted) < n:
        out.append("only %d found" % len(fitted))
    if m is not None:
        out += ["draft: %s | folder %s | capture %s" % (p["url"], p["folder"], p["capture"]) for p in draft_picks(head, m)]
    out.append("ranked: %d fitted, the top %d written to rows.jsonl; %d unreadable at fit"
               % (len(fitted), len(head), len(unreadable)))
    return out


def counts_text(items, field):
    counts = {}
    for i in items:
        counts[str(i.get(field))] = counts.get(str(i.get(field)), 0) + 1
    return ", ".join("%s %d" % kv for kv in sorted(counts.items()))


def read_lines(d):
    """The report's `## Sources`: one `- <source>: read: <how>` line per line of the run's read.jsonl,
    or [] when the run has neither it nor a posting collected; ScanError on a line without a source or
    with a `read` not in READS, or when a source of collected.jsonl has no line."""
    items = run_file(d, READ_FILE)
    out, have = ["## Sources", ""], set()
    for i, r in enumerate(items, 1):
        name = str(r.get("source") or "").strip()
        if not name:
            raise ScanError("%s line %d: a line without a source" % (READ_FILE, i))
        if r.get("read") not in READS:
            raise ScanError("%s line %d: read must be one of %s" % (READ_FILE, i, ", ".join(READS)))
        out.append("- %s: read: %s" % (name, r["read"]))
        have.add(name)
    lacking = [s for s in dict.fromkeys(str(p.get("source") or "").strip() for p in run_file(d, "collected.jsonl"))
               if s and s not in have]
    if lacking:
        raise ScanError("%s has no line for %s: add how each was read (scan.md step 3), then run report again"
                        % (READ_FILE, ", ".join(lacking)))
    return out + [""] if items else []


def run_sections(root, d):
    """The report's `## Ranking`, `## Sources`, `## Not fitted` and `## Fit maps`, from the run's files;
    the Screen sections go after the Ranking."""
    ranked = run_file(d, "ranked.jsonl")
    out = ["## Ranking", ""]
    out += md_table(RANKED_COLUMNS, ranked) if ranked else ["None fitted."]
    out += [""] + screen_sections(root, d) + [""] + read_lines(d) + ["## Not fitted", ""]
    dedup = run_file(d, DEDUP_DROPPED)
    pre = run_file(d, "prefilter-dropped.jsonl")
    out.append("- Dropped by dedup: %d%s" % (len(dedup), " (%s)" % counts_text(dedup, "drop") if dedup else ""))
    out.append("- Dropped by the prefilter: %d%s" % (len(pre), " (%s)" % counts_text(pre, "drop") if pre else ""))
    if not config.target_roles(root):
        out.append("- direction.md's Target roles are empty: no title was dropped for its role, and no posting has a tier.")
    for label, name in (("Past the screen budget", "not-screened.jsonl"), ("Unreadable", "unreadable.jsonl")):
        items = run_file(d, name)
        out.append("- %s: %d" % (label, len(items)))
        if items:
            out += [""] + md_table(LISTED_COLUMNS, items) + [""]
    out += [""] + sponsorship.report_lines(root, [p.get("company") or "" for p in ranked])
    out += ["## Fit maps", ""]
    for p in ranked:
        out += ["### %s — %s" % (p.get("company") or "-", p.get("role") or "-"), "",
                "URL: %s" % p["url"], "Entries commit: %s" % (p["fit_commit"] or "-")]
        out += fit.map_lines(p["result"]) + [""]
    if not ranked:
        out += ["None fitted.", ""]
    return "\n".join(out).rstrip("\n")


def report_name(path):
    m = REPORT_NAME.match(os.path.basename(path))
    return m.group(1) + ("-" + m.group(2) if m.group(2) else "")


def regenerate_dashboard(root):
    """tools/dashboard.py's page, written: its `wrote:` or `unchanged:` line and its `artifact:` line.
    Loaded here, not at the top (it loads this module)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("dashboard", os.path.join(HERE, "dashboard.py"))
    dashboard = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(dashboard)
        return [dashboard.write(root), "artifact: %s" % (dashboard.artifact_url(root) or "none")]
    except Exception as e:
        # by name: loaded under another name (a test), this module's dashboard uses its own copy's ScanError
        if type(e).__name__ in ("ScanError", "LogError") or isinstance(e, (OSError, ValueError)):
            raise ScanError("dashboard: %s" % e)
        raise


def cmd_summary(root, d, date):
    d = os.path.normpath(at_root(root, d))
    collected = read_jsonl(os.path.join(d, "collected.jsonl"))
    buckets = [("dropped by dedup", DEDUP_DROPPED), ("dropped by the prefilter", "prefilter-dropped.jsonl"),
               ("past the screen budget", "not-screened.jsonl"), ("dropped at screen", "dropped.jsonl"),
               ("screened, not fully fitted", "screened.jsonl"), ("unreadable", "unreadable.jsonl"),
               ("fitted and ranked", "ranked.jsonl")]
    owner = [None] * len(collected)
    ckeys = [keys(str(p.get("url") or "")) for p in collected]
    out, findings = ["collected: %d" % len(collected)], []
    for label, name in buckets:
        items = run_file(d, name)
        out.append("%s: %d" % (label, len(items)))
        for item in items:
            k = keys(str(item.get("url") or ""))
            match = [i for i, c in enumerate(ckeys) if c & k]
            free = next((i for i in match if owner[i] is None), None)
            if free is not None:
                owner[free] = name
            elif match:
                findings.append("repeated: %s (in %s and %s)" % (item.get("url"), owner[match[0]], name))
            else:
                findings.append("extra: %s in %s (not in collected.jsonl)" % (item.get("url"), name))
    findings += ["missing: %s (collected, in none of the run's files)" % p.get("url")
                 for p, o in zip(collected, owner) if o is None]
    report = os.path.join(root, REPORTS, "%s-scan%s.md" % (os.path.basename(d)[:10], os.path.basename(d)[10:]))
    ranked = run_file(d, "ranked.jsonl")
    if not os.path.exists(report):
        findings.append("no report: %s" % os.path.relpath(report, root).replace(os.sep, "/"))
    else:
        maps = {canonical(u): body for u, _, body in fit_maps(read(report))}
        for p in ranked:
            body = maps.get(canonical(p["url"]))
            if body is None or not SCREEN_LINE.search(body):
                findings.append("no Screen line: %s's fit map in %s" % (p["url"], os.path.basename(report)))
    names, day = [p.get("company") or "" for p in ranked], datetime.date.fromisoformat(date)
    try:
        findings += ["no sponsorship record: %s | %s" % (n, k) for n, k in sponsorship.unrecorded(root, names, day)]
        findings += ["sponsorship unanswered: %s | %s | %s" % (n, k, why) for n, k, why in sponsorship.unanswered(root, names, day)]
    except sponsorship.SponsorshipError as e:
        findings.append("sponsorship unreadable: %s" % e)
    head = run_file(d, "rows.jsonl")
    by_url = {canonical(p["url"]): p for p in ranked}
    for r in head:
        p = by_url.get(canonical(r["url"]), {})
        out.append("top: %s | %s | %s | %s | %s" % (p.get("rank", "-"), r.get("company"), r.get("role"),
                                                   p.get("recommendation", "-"), r["url"]))
    if findings:
        return 1, out + findings + ["summary: %d finding(s)" % len(findings)]
    return 0, out + ["summary: ok, every posting collected is in one of the run's files"]


def cmd_report(root, date, src, top, name=None, body=None, screen=None, drafting=False):
    warn = fetch(root)
    rows = []
    for i, r in enumerate(read_jsonl(at_root(root, src)), 1):
        if r.get("status") not in STATUSES:
            raise ScanError("%s line %d: status must be one of %s" % (src, i, ", ".join(STATUSES)))
        r["url"] = clean(str(r.get("url") or ""))
        if not r["url"]:
            raise ScanError("%s line %d: a row without a url" % (src, i))
        rows.append(r)
    rs = reports(root)
    old = [r for r in pending_table(read(rs[-1][2]))[2] if r["status"] in PENDING] if rs else []
    branches = scan_branches(root) if old else {}

    def pruned(r):   # only when origin's branches are known: after a fetch that worked, or with no remote
        m = re.match(r"^(scan/[^:\s]+):", r["draft"])
        if m and not warn and m.group(1) not in branches:
            r["draft"], r["status"] = "pruned (%s)" % m.group(1), "undecided"
        return r
    for r in rows:   # a posting listed again keeps the draft an earlier scan made for it
        prev = next((o for o in old if keys(o["url"]) & keys(r["url"])), None)
        if prev and prev["draft"] not in ("", "-") and not r.get("draft"):
            r["status"], r["draft"], r["fit_commit"] = prev["status"], prev["draft"], prev["fit_commit"]
            pruned(r)
    have = set()
    for r in rows:
        have |= keys(r["url"])
    carried = [pruned(r) for r in old if not keys(r["url"]) & have]
    name = name or next_name(root, date)
    m = re.match(r"^(\d{4}-\d{2}-\d{2})((?:-\d+)?)$", name)
    if not m:
        raise ScanError("--name must be YYYY-MM-DD or YYYY-MM-DD-<n>, as `name` prints it")
    path = os.path.join(root, REPORTS, "%s-scan%s.md" % m.groups())
    if os.path.exists(path):
        raise ScanError("%s exists" % path)
    if drafting and not has_remote(root):
        top = top.rstrip() + " The drafts are on this machine only (no remote)."
    lines = ["# Scan %s" % name, "", top, "", "## Pending", ""] + table_lines(rows + carried)
    text = read(at_root(root, body)).replace("\r\n", "\n").strip("\n") if body else ""
    if screen and os.path.exists(os.path.join(at_root(root, screen), "ranked.jsonl")):
        d = at_root(root, screen)
        text = (add_screen_lines(run_sections(root, d), run_file(d, "ranked.jsonl")) + "\n\n" + text).strip("\n")
    elif screen:   # a body the agent wrote: the Screen sections go after its Ranking
        d = at_root(root, screen)
        text = add_screen_lines(text, run_file(d, "fit.jsonl"))
        ranking = re.search(r"^## Ranking[ \t]*$.*?(?=^## |\Z)", text, re.M | re.S)
        cut = ranking.end() if ranking else 0
        block = "\n".join(screen_sections(root, screen) + [""] + read_lines(d)).rstrip("\n")
        text = (text[:cut].rstrip("\n") + "\n\n" + block + "\n\n" + text[cut:].lstrip("\n")).strip("\n")
    if text:
        lines += [""] + text.split("\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    out = warn + ["wrote %s: %d row(s), %d carried over" % (os.path.relpath(path, root).replace(os.sep, "/"),
                                                           len(rows) + len(carried), len(carried))]
    try:
        out += regenerate_dashboard(root)
    except ScanError as e:   # so that the same report command runs again once it is fixed
        os.remove(path)
        raise ScanError("%s; the report is not written: fix that, then run report again" % e)
    return out + ["commit: scan(%s): %d postings" % (name, len(rows))]


def committed_text(root, path):
    """The file as HEAD has it, or None."""
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    p = git(root, "show", "HEAD:" + rel)
    return p.stdout if p.returncode == 0 else None


def status_subject(root, report, status):
    """The commit subject for the statuses set since HEAD: `scan(<name>): <x> drafts` after a draft to
    review, else `scan(<name>): <x> accepted, <y> declined`."""
    before = committed_text(root, report)
    was = {canonical(r["url"]): r for r in pending_table(before or "")[2]}
    changed = [r for r in pending_table(read(report))[2]
               if (was.get(canonical(r["url"])) or {}).get("status") != r["status"]
               or (was.get(canonical(r["url"])) or {}).get("draft") != r["draft"]]
    name = report_name(report)
    if status == "draft to review":
        return "scan(%s): %d drafts" % (name, sum(1 for r in changed if r["status"] == "draft to review"))
    old = committed_text(root, os.path.join(root, DECLINED)) or ""
    had = set()
    for line in old.split("\n"):
        try:
            had |= keys(str(json.loads(line).get("url") or "")) if line.strip() else set()
        except (json.JSONDecodeError, AttributeError):
            continue
    declined = sum(1 for i in read_declined(root) if not keys(str(i.get("url") or "")) & had)
    return "scan(%s): %d accepted, %d declined" % (name, sum(1 for r in changed if r["status"] == "accepted"), declined)


def cmd_status(root, date, url, status, draft, reason):
    out, report = set_status(root, date, url, status, draft, reason)
    out += regenerate_dashboard(root)
    return out + (["commit: " + status_subject(root, report, status)] if report else [])


def set_status(root, date, url, status, draft, reason):
    """(lines, report): sets the row's status and Draft cell, as `status` does, without the dashboard
    or the subject; `report` the file changed (for a declined URL in no Pending table, the newest
    report, or None)."""
    if status not in STATUSES:
        raise ScanError("status must be one of %s" % ", ".join(STATUSES))
    want = keys(url)
    hit = None
    for _, _, p in reports(root):
        for r in pending_table(read(p))[2]:
            if keys(r["url"]) & want:
                hit = (p, r)
    if not hit and status == "declined":   # a posting the scan screened but never ranked
        items = [i for i in read_declined(root) if not keys(str(i.get("url", ""))) & want]
        write_declined(root, [{"url": clean(url), "date": date, "reason": reason or ""}] + items)
        rs = reports(root)
        return ["%s: in no Pending table" % clean(url), "%s: added %s" % (DECLINED, clean(url))], (rs[-1][2] if rs else None)
    if not hit:
        raise ScanError("%s is in no scan report's Pending table" % url)
    p, r = hit
    lines = read(p).split("\n")
    old = dict(r)
    r["status"] = status
    if draft:
        r["draft"] = draft
    lines[r["_line"]] = table_lines([r])[2]
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    rel = os.path.relpath(p, root).replace(os.sep, "/")
    out = ["%s: %s: %s -> %s%s" % (rel, r["url"], old["status"], status,
                                   "; draft %s -> %s" % (old["draft"], draft) if draft else "")]
    if status == "declined":
        items = [i for i in read_declined(root) if not keys(str(i.get("url", ""))) & want]
        write_declined(root, [{"url": r["url"], "date": date, "reason": reason or ""}] + items)
        out.append("%s: added %s" % (DECLINED, r["url"]))
    return out, p


def cmd_cleanup(root, dry_run):
    warn = fetch(root)
    rows = newest_rows(root)
    names = {os.path.basename(p) for _, _, p in reports(root)}
    out = []
    for branch, where in sorted(scan_branches(root).items()):
        m = BRANCH_NAME.match(branch)
        report = "%s-scan%s.md" % (m.group(1), "-" + m.group(2) if m.group(2) else "")
        if report not in names:
            out.append("kept: %s (no report %s yet)" % (branch, report))
            continue
        # named by a row of any report (an accepted row's newest cell names its application folder instead)
        urls_named = {canonical(r["url"]) for _, _, p in reports(root) for r in pending_table(read(p))[2]
                      if r["draft"].startswith(branch + ":")}
        named = bool(urls_named)
        # pending: the newest row of each posting the branch drafted, whatever its Draft cell says now
        # (`pruned (...)` after another clone missed the push, say)
        pending = [rows[u][1] for u in urls_named if u in rows and rows[u][1]["status"] not in ("accepted", "declined")]
        if not named:   # drafting has not set its Draft cells yet, or stopped before it did
            out.append("kept: %s (no Draft cell names it; prune deletes it after %d days)" % (branch, PRUNE_DAYS))
        elif pending:
            out.append("kept: %s (%d pending)" % (branch, len(pending)))
        else:
            try:
                done = delete_branch(root, branch, where, dry_run)
            except ScanError as e:   # a worktree with uncommitted changes, say: keep it for the user
                out.append("kept: %s (%s)" % (branch, e))
                continue
            out.append("deleted: %s (%s)%s" % (branch, ", ".join(done), " (dry run: nothing deleted)" if dry_run else ""))
    for d in sorted(glob.glob(os.path.join(root, ".build", "scan", "*"))):
        m = BRANCH_NAME.match("scan/" + os.path.basename(d))
        if not (m and os.path.isdir(d)):
            continue
        rel = ".build/scan/%s/" % os.path.basename(d)
        report = os.path.join(root, REPORTS, "%s-scan%s.md" % (m.group(1), "-" + m.group(2) if m.group(2) else ""))
        if not os.path.exists(report):
            out.append("kept: %s (no report yet)" % rel)
            continue
        # each posting's newest row decides, so a row carried into a later report keeps the folder
        pending = [r for r in pending_table(read(report))[2]
                   if rows.get(canonical(r["url"]), (None, r))[1]["status"] not in ("accepted", "declined")]
        if pending:
            out.append("kept: %s (%d pending)" % (rel, len(pending)))
            continue
        if not dry_run:
            shutil.rmtree(d)
        out.append("deleted: %s%s" % (rel, " (dry run: nothing deleted)" if dry_run else ""))
    return warn + (out or ["cleanup: no scan branches or run folders"])


# ---- Drafts ----

DRAFT_FILES = ("posting.md", "fit.md", "resume.tex", "company.md", "decisions.md", "handoff.md")
DRAFT_OPTIONAL = ("answers.md",)
DECISIONS_HEADER = ["Decision", "Chosen", "Alternatives", "Why"]
NEEDS_YOU = re.compile(r"^needs you:\s*\S")
PLAYWRIGHT = ".playwright-cli"
NO_DRAFT = ("\nnext: treat it as a posting with no draft (scan-results.md › Look at a posting with no draft;"
            " an accept is an ordinary write posting run)")


def rel_path(root, path):
    """The path from the Log's root, or as given when it is on another drive (Windows)."""
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return path


def tree_files(root, ref, path):
    """{name: text} of the files (blobs; no subfolder) of `<ref>:<path>`, or None when git has no such folder."""
    p = git(root, "ls-tree", "-z", "%s:%s" % (ref, path))
    if p.returncode != 0:
        return None
    out = {}
    for item in p.stdout.split("\0"):
        meta, _, name = item.partition("\t")
        if name and meta.split(" ")[1:2] == ["blob"]:
            out[name] = git(root, "show", "%s:%s/%s" % (ref, path, name), check=True).stdout
    return out


def run_name(d):
    """The run's name from its folder `.build/scan/<name>`."""
    name = os.path.basename(os.path.normpath(d))
    if not BRANCH_NAME.match("scan/" + name):
        raise ScanError("%s is no run folder (.build/scan/<name>, as `name` prints it)" % d)
    return name


def cmd_drafts(root, d, m):
    if m < 0:
        raise ScanError("--m must be 0 or more")
    d = os.path.normpath(at_root(root, d))
    paths = run_paths(run_name(d))
    if not os.path.exists(os.path.join(d, "rows.jsonl")):
        raise ScanError("no rows.jsonl in %s: run rank first" % rel_path(root, d))
    ranked = {canonical(p["url"]): p for p in run_file(d, "ranked.jsonl")}
    head = [ranked[canonical(r["url"])] for r in run_file(d, "rows.jsonl") if canonical(r["url"]) in ranked]
    picks = draft_picks(head, m)
    if not picks:
        return ["drafts: none (no posting of rows.jsonl is recommended above skip, or --m is 0)"]
    report = os.path.join(root, paths["report"])
    if not os.path.exists(report):
        raise ScanError("no report %s yet: write it (step 9) first" % paths["report"])
    maps = {}
    for u, _, body in fit_maps(read(report)):
        for k in keys(u):
            maps[k] = body
    remote = has_remote(root)
    warn = fetch(root) if remote else []
    base = paths["worktree"] + "/scan-drafts" if remote else paths["drafts"]
    problems, todo = [], []
    if remote and paths["branch"] in scan_branches(root):
        problems.append("exists: the branch %s (a draft run of this name started already)" % paths["branch"])
    if remote and os.path.exists(at_root(root, paths["worktree"])):
        problems.append("exists: %s" % paths["worktree"])
    for p in picks:
        body = next((maps[k] for k in keys(p["url"]) if k in maps), None)
        folder = "%s/%s" % (base, p["folder"])
        if body is None:
            problems.append("no fit map: %s has no `### ` section under %s's `## Fit maps`" % (p["url"], paths["report"]))
        if not os.path.isfile(at_root(root, p["capture"])):
            problems.append("no capture: %s (%s)" % (p["capture"], p["url"]))
        if not remote and os.path.exists(at_root(root, folder)):
            problems.append("exists: %s" % folder)
        todo.append((p, folder, body))
    if problems:
        raise ScanError("drafts: %d problem(s); nothing written\n%s" % (len(problems), "\n".join(problems)))
    out = list(warn)
    if remote:
        default = logfiles.default_branch(root) or logfiles.set_default_branch(root)
        if not default:
            raise ScanError("drafts: origin names no default branch (git remote set-head origin --auto failed); nothing written")
        git(root, "worktree", "add", "-q", "--no-track", "-b", paths["branch"], at_root(root, paths["worktree"]),
            "origin/" + default, check=True)
        out += ["branch: %s (from origin/%s)" % (paths["branch"], default), "worktree: " + paths["worktree"]]
    made = []
    try:
        for p, folder, body in todo:
            target = at_root(root, folder)
            os.makedirs(target)
            made.append(target)
            shutil.copyfile(at_root(root, p["capture"]), os.path.join(target, "posting.md"))
            logfiles.write_text(os.path.join(target, "fit.md"), "### " + body.strip("\n") + "\n")
            out.append("draft: %s | folder %s | capture %s" % (p["url"], folder, p["capture"]))
    except OSError:   # leave nothing: the same command runs again once it is fixed
        if remote:
            git(root, "worktree", "remove", "--force", at_root(root, paths["worktree"]))
            git(root, "branch", "-D", paths["branch"])
        for target in made:
            shutil.rmtree(target, ignore_errors=True)
        raise
    return out + ["drafts: %d folder(s), each with posting.md and fit.md" % len(todo)]


def needs_you_rows(text):
    """[(what, where)] of the `needs you` rows of decisions.md's table."""
    tables = logfiles.md_tables(text)
    if not tables:
        return []
    out = []
    for _, c in tables[0].rows:
        if c and c[0].lower().startswith("needs you"):
            out.append((c[0].split(":", 1)[-1].strip(), c[3] if len(c) > 3 else ""))
    return out


def draft_problems(path):
    """One line per way the draft folder differs from scan.md's step 4: its files, its decisions table."""
    if not os.path.isdir(path):
        return ["missing: the folder %s" % path]
    names = sorted(os.listdir(path))
    decisions = read(os.path.join(path, "decisions.md")) if "decisions.md" in names else None
    return draft_file_problems(names, decisions)


def draft_file_problems(names, decisions):
    """draft_problems() of a folder holding the files `names`, decisions.md's text `decisions`."""
    problems = ["missing: %s" % n for n in DRAFT_FILES if n not in names]
    for n in names:
        if n.lower().endswith(".pdf"):
            problems.append("extra: %s (a draft folder holds no PDF: the accept builds it)" % n)
        elif n not in DRAFT_FILES + DRAFT_OPTIONAL:
            problems.append("extra: %s (a draft folder holds only %s, and answers.md for form questions)"
                            % (n, ", ".join(DRAFT_FILES)))
    if decisions is None:
        return problems
    tables = logfiles.md_tables(decisions)
    if not tables or tables[0].head != DECISIONS_HEADER:
        return problems + ["bad: decisions.md: its table's header must be | %s |" % " | ".join(DECISIONS_HEADER)]
    for n, c in tables[0].rows:
        if len(c) != len(DECISIONS_HEADER):
            problems.append("bad: decisions.md line %d: %d cells, not %d" % (n, len(c), len(DECISIONS_HEADER)))
        elif c[0].lower().startswith("needs you") and not (NEEDS_YOU.match(c[0]) and c[1] == "GAP" and c[2] == "-" and c[3]):
            problems.append("bad: decisions.md line %d: a needs-you row is | needs you: <what> | GAP | - | <where it appears> |" % n)
    return problems


def cmd_drafts_check(root, folder):
    problems = draft_problems(at_root(root, folder))
    return (1, problems + ["check: %d problem(s)" % len(problems)]) if problems else (0, ["check: ok"])


def cmd_drafts_save(root, date, d):
    d = os.path.normpath(at_root(root, d))
    paths = run_paths(run_name(d))
    ranked = {p.get("folder"): p for p in run_file(d, "ranked.jsonl")}
    out, remote = [], has_remote(root)
    if remote:
        branch, wt = paths["branch"], at_root(root, paths["worktree"])
        ref = "refs/remotes/origin/" + branch
        on_origin = git(root, "rev-parse", "--verify", "-q", ref).returncode == 0
        if os.path.isdir(wt):
            head = git(wt, "rev-parse", "HEAD", check=True).stdout.strip()
            if git(wt, "status", "--porcelain", "--", "scan-drafts").stdout.strip():
                raise ScanError("save: refused: %s has uncommitted changes in scan-drafts/; nothing changed\nbranch: %s\n"
                                "next: run step 5.1's sync.py commit again, then this" % (paths["worktree"], branch))
            if not on_origin or git(root, "merge-base", "--is-ancestor", head, ref).returncode != 0:
                raise ScanError("save: refused: the branch is not pushed (origin/%s lacks the worktree's HEAD %s);"
                                " nothing changed\nbranch: %s\nnext: run step 5.1's sync.py commit again (it retries"
                                " the push), then this; when its push is refused again, stop drafting here"
                                % (branch, head[:7], branch))
        elif not on_origin:
            raise ScanError("save: refused: no worktree %s and no origin/%s: nothing drafted to save\n"
                            "next: stop drafting here" % (paths["worktree"], branch))
        p = git(root, "ls-tree", "--name-only", ref + ":scan-drafts")
        folders = sorted(p.stdout.split()) if p.returncode == 0 else []
        where = lambda f: os.path.join(wt, "scan-drafts", f)
        cell = lambda f: "%s:scan-drafts/%s" % (branch, f)
    else:
        top = at_root(root, paths["drafts"])
        folders = sorted(f for f in os.listdir(top) if os.path.isdir(os.path.join(top, f))) if os.path.isdir(top) else []
        where = lambda f: os.path.join(top, f)
        cell = lambda f: "%s/%s" % (paths["drafts"], f)
    if not folders:
        raise ScanError("save: refused: no draft folder in %s\nnext: stop drafting here"
                        % ("origin/%s:scan-drafts" % paths["branch"] if remote else paths["drafts"]))
    listed = set()
    for _, _, p in reports(root):
        for r in pending_table(read(p))[2]:
            listed |= keys(r["url"])
    problems = []
    for f in folders:
        if f not in ranked:
            problems.append("no posting: %s is no folder of ranked.jsonl" % f)
        elif not keys(ranked[f]["url"]) & listed:
            problems.append("no row: %s (%s) is in no report's Pending table" % (ranked[f]["url"], f))
        if os.path.isdir(where(f)):
            found = draft_problems(where(f))
        else:   # an earlier --save removed the worktree, or a file: the drafts as origin has them
            files = tree_files(root, ref, "scan-drafts/" + f) if remote else None
            found = draft_file_problems(sorted(files), files.get("decisions.md")) if files is not None \
                else ["not a folder (a draft is a folder)"]
        problems += ["%s: %s" % (f, x) for x in found]
    if problems:
        first = ("git -C <root> worktree add %s %s, then " % (paths["worktree"], branch)
                 if remote and not os.path.isdir(wt) else "")
        raise ScanError("save: refused: %d problem(s); nothing changed\n%s\nnext: %sfix each one named as scan.md ›"
                        " Draft a posting step 4 says, or delete it to leave its posting undrafted (in %s), then"
                        " run step 5.1 again (with a remote) and this" % (len(problems), "\n".join(problems), first,
                                                                        paths["worktree"] + "/scan-drafts" if remote
                                                                        else paths["drafts"]))
    report = None
    for f in folders:
        lines, report = set_status(root, date, ranked[f]["url"], "draft to review", cell(f), None)
        out += lines
    if remote and os.path.isdir(wt):
        p = git(root, "worktree", "remove", wt)
        out.append("removed: the worktree %s (origin/%s keeps the drafts)" % (paths["worktree"], paths["branch"])
                   if p.returncode == 0 else "kept: the worktree %s (git could not remove it: %s; cleanup removes it"
                   " once its drafts are decided)" % (paths["worktree"], (p.stderr.strip().splitlines() or ["?"])[-1]))
    out += regenerate_dashboard(root)
    if os.path.isdir(os.path.join(root, PLAYWRIGHT)):
        shutil.rmtree(os.path.join(root, PLAYWRIGHT))
        out.append("deleted: %s/" % PLAYWRIGHT)
    return out + ["commit: " + status_subject(root, report, "draft to review")]


def cmd_draft(root, url, out=None):
    want, hit = keys(url), None
    for _, _, p in reports(root):
        for r in pending_table(read(p))[2]:
            if keys(r["url"]) & want:
                hit = r
    if not hit:
        raise ScanError("%s is in no scan report's Pending table" % url)
    c = hit["draft"]
    m = re.match(r"^(scan/[^:\s]+):(.+)$", c)
    warn, files = [], {}
    if c in ("", "-"):
        raise ScanError("%s has no draft%s" % (hit["url"], NO_DRAFT))
    if c.startswith("pruned"):
        raise ScanError("%s's draft is gone, its branch deleted (%s)%s" % (hit["url"], c, NO_DRAFT))
    if m:
        branch, path = m.group(1), m.group(2).strip("/")
        warn = fetch(root)
        files = tree_files(root, "refs/remotes/origin/" + branch, path)
        if files is None:
            raise ScanError("origin has no %s:%s (its branch deleted, or the draft never pushed)%s" % (branch, path, NO_DRAFT))
    elif c.startswith(".build/"):
        path = c.rstrip("/")
        src = at_root(root, path)
        if not os.path.isdir(src):
            raise ScanError("%s is not on this machine: the drafts of a scan with no remote stay where it ran\nnext:"
                            " tell the user the draft is on the machine that ran the scan, to look at or accept it there;"
                            " here, treat it as a posting with no draft (scan-results.md › Look at a posting with no"
                            " draft; an accept is an ordinary write posting run)" % path)
        for name in sorted(os.listdir(src)):
            if os.path.isfile(os.path.join(src, name)):
                files[name] = read(os.path.join(src, name))
    else:
        raise ScanError("%s is %s, not a draft: its Draft cell names %s\nnext: show the user its row (status and"
                        " Draft cell): it holds no draft to copy" % (hit["url"], hit["status"], c))
    dest = at_root(root, out or ".build/drafts/" + os.path.basename(path))
    files = {n: text.replace("\r\n", "\n") for n, text in files.items()}
    differ = [n for n, text in files.items() if os.path.exists(os.path.join(dest, n))
              and read(os.path.join(dest, n)).replace("\r\n", "\n") != text]
    if differ:
        raise ScanError("%s holds a different %s; nothing written\nnext: it is this draft from an earlier look,"
                        " accept or build: use the draft there as it is (or give --out <another folder> for the draft"
                        " as it was saved)" % (rel_path(root, dest), ", ".join(sorted(differ))))
    os.makedirs(dest, exist_ok=True)
    for n, text in files.items():
        logfiles.write_text(os.path.join(dest, n), text)
    lines = warn + ["draft: %s | %s" % (hit["url"], c), "folder: %s/" % rel_path(root, dest),
                    "files: " + ", ".join(sorted(files))]
    rows = needs_you_rows(files.get("decisions.md", ""))
    return lines + (["needs you: %s | %s" % row for row in rows] if rows else ["needs you: none"])


def main(argv):
    logfiles.utf8_stdout()
    ap = argparse.ArgumentParser(prog="scan.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("name")
    sp.add_argument("--screen-budget", type=int)
    sp.add_argument("--fit-budget", type=int)
    sub.add_parser("sources")
    sp = sub.add_parser("prune")
    sp.add_argument("--dry-run", action="store_true")
    sub.add_parser("pending")
    sp = sub.add_parser("dedup")
    sp.add_argument("postings")
    sp.add_argument("--out", required=True)
    sp.add_argument("--window", type=int)
    sp = sub.add_parser("prefilter")
    sp.add_argument("dir")
    sp = sub.add_parser("screen")
    sp.add_argument("dir", nargs="?")
    sp.add_argument("--screen-budget", type=int)
    sp.add_argument("--fit-budget", type=int)
    sp.add_argument("--sort", action="store_true")
    sp.add_argument("--give-up", action="store_true")
    sp.add_argument("--check")
    sp.add_argument("--batch")
    sp = sub.add_parser("fetch")
    sp.add_argument("path")
    sp.add_argument("url")
    sp = sub.add_parser("capture")
    sp.add_argument("path")
    sp.add_argument("url")
    sp.add_argument("source")
    sp.add_argument("--stand-in")
    sp = sub.add_parser("fitmap")
    sp.add_argument("url")
    sp.add_argument("--out")
    sp = sub.add_parser("rank")
    sp.add_argument("dir")
    sp.add_argument("--n", type=int, required=True)
    sp.add_argument("--m", type=int)
    sp.add_argument("--give-up", action="store_true")
    sp = sub.add_parser("report")
    sp.add_argument("rows")
    sp.add_argument("--top", default="All sources read.")
    sp.add_argument("--name")
    sp.add_argument("--body")
    sp.add_argument("--screen")
    sp.add_argument("--drafting", action="store_true")
    sp = sub.add_parser("summary")
    sp.add_argument("dir")
    sp = sub.add_parser("status")
    sp.add_argument("url")
    sp.add_argument("status")
    sp.add_argument("--draft")
    sp.add_argument("--reason")
    sp = sub.add_parser("cleanup")
    sp.add_argument("--dry-run", action="store_true")
    sp = sub.add_parser("drafts")
    sp.add_argument("dir", nargs="?")
    sp.add_argument("--m", type=int)
    sp.add_argument("--check")
    sp.add_argument("--save", action="store_true")
    sp = sub.add_parser("draft")
    sp.add_argument("url")
    sp.add_argument("--out")
    try:
        root, argv = logfiles.split_root(argv, __file__)
        a = ap.parse_args(argv)
        datetime.date.fromisoformat(a.date)
    except logfiles.LogError as e:
        print("scan: %s" % e)
        return 2
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    except ValueError:
        print("scan: --date must be YYYY-MM-DD")
        return 2
    root = os.path.abspath(root)   # a relative --root is not joined to the paths built from it twice
    if a.cmd == "name" and (a.screen_budget is None) != (a.fit_budget is None):
        print("scan: give --screen-budget and --fit-budget together")
        return 2
    if a.cmd == "screen":
        bad = None
        if a.check:
            if a.dir or a.sort or a.give_up or a.screen_budget is not None or a.fit_budget is not None:
                bad = "screen --check <results> [--batch <todo>] takes nothing else"
        elif a.batch:
            bad = "--batch goes with --check"
        elif not a.dir or a.screen_budget is None or a.fit_budget is None:
            bad = "screen needs <dir>, --screen-budget and --fit-budget (or --check <results>)"
        elif a.give_up and not a.sort:
            bad = "--give-up goes with --sort"
        if bad:
            print("scan: %s" % bad)
            return 2
    if a.cmd == "drafts":
        if a.check:
            bad = "drafts --check <folder> takes nothing else" if a.dir or a.m is not None or a.save else None
        elif not a.dir or (a.m is None) == (not a.save):
            bad = "drafts needs <dir> and one of --m <m> or --save (or --check <folder>)"
        else:
            bad = None
        if bad:
            print("scan: %s" % bad)
            return 2
    code = 0
    try:
        if a.cmd == "name":
            lines = cmd_name(root, a.date, a.screen_budget, a.fit_budget)
        elif a.cmd == "sources":
            lines = cmd_sources(root)
        elif a.cmd == "prune":
            lines = cmd_prune(root, a.date, a.dry_run)
        elif a.cmd == "pending":
            lines = cmd_pending(root)
        elif a.cmd == "dedup":
            lines = cmd_dedup(root, at_root(root, a.postings), at_root(root, a.out), a.date, a.window)
        elif a.cmd == "prefilter":
            lines = cmd_prefilter(root, a.dir)
        elif a.cmd == "screen" and a.check:
            lines = cmd_screen_check(root, a.check, a.batch)
        elif a.cmd == "screen":
            lines = cmd_screen(root, a.date, a.dir, a.screen_budget, a.fit_budget, a.sort, a.give_up)
        elif a.cmd == "fetch":
            lines = cmd_fetch(root, a.path, a.url)
        elif a.cmd == "capture":
            lines = cmd_capture(root, a.path, a.url, a.source, a.stand_in)
        elif a.cmd == "fitmap":
            lines = cmd_fitmap(root, a.url, a.out)
        elif a.cmd == "rank":
            lines = cmd_rank(root, a.dir, a.n, a.m, a.give_up)
        elif a.cmd == "report":
            lines = cmd_report(root, a.date, a.rows, a.top, a.name, a.body, a.screen, a.drafting)
        elif a.cmd == "summary":
            code, lines = cmd_summary(root, a.dir, a.date)
        elif a.cmd == "status":
            lines = cmd_status(root, a.date, a.url, a.status, a.draft, a.reason)
        elif a.cmd == "drafts" and a.check:
            code, lines = cmd_drafts_check(root, a.check)
        elif a.cmd == "drafts" and a.save:
            lines = cmd_drafts_save(root, a.date, a.dir)
        elif a.cmd == "drafts":
            lines = cmd_drafts(root, a.dir, a.m)
        elif a.cmd == "draft":
            lines = cmd_draft(root, a.url, a.out)
        else:
            lines = cmd_cleanup(root, a.dry_run)
    except (ScanError, logfiles.LogError, OSError, UnicodeDecodeError) as e:
        print("scan: %s" % e)
        return 1
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
