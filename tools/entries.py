#!/usr/bin/env python3
"""What an entry is, for every tool and mode that reads entries.

  python3 -I tools/entries.py list [<root>] [--series <slug>]
  python3 -I tools/entries.py check [<root>]
  python3 -I tools/entries.py refs <entry> [<root>]
  python3 -I tools/entries.py links-since <entry> [<root>]

(Windows: py -3 -I.) <root> is the Log's root, by default the folder above this script's. <entry>
is an entry's path, relative to <root> (`entries/2031-04-widget.md`) or to the current folder.

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
  then `one line:` and its text. `--series <slug>` lists that series' parts only. Exit 0.
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
    last_updated:`, from its `last_updated`.
  Exit 1 when it prints a finding, else `OK: <n> entries, no findings` and exit 0.
- `refs`: every line of the Log's other files (README, stories.md, profile, direction, applications,
  other entries, the Talking points files in stories/, outputs/, sources/ except the inbox) that
  names the entry's file, as `<file>:<line>: <text>`. It matches the file name without `.md` as a
  whole word, so plain text naming it and a line inside an HTML comment count too. Files that are not UTF-8 text are skipped. Exit 0.
- `links-since`: the links (URLs, and Markdown link targets) the entry has now that it did not
  have at its last commit whose subject is `consolidate(<slug>)` (or names the slug in a
  comma-separated list in the parentheses), uncommitted changes included: first a `since:` line
  naming the commit, or saying there is none (every link is then listed), then one `link: <link>`
  line each. Exit 0.

`--today YYYY-MM-DD` (check) sets the date the staleness check counts from, for tests.

Stories (the `stories` mode's checks, and `story-finish` for consolidate):

  python3 -I tools/entries.py story-coverage [<root>] [--type <question type>]...
  python3 -I tools/entries.py story-candidates <question type> [<root>]
  python3 -I tools/entries.py story-stale <talking points file> [<root>]
  python3 -I tools/entries.py story-wording-add <question type> <wording> [<root>]
  python3 -I tools/entries.py story-wordings [<root>] [--type <question type>]...
  python3 -I tools/entries.py story-finish <entry> [<root>]

They read three formats; the `stories` mode writes the first two as they are, and story-wording-add
writes the third:

- The Story index is the first table of stories.md, before any `## ` heading (the Application
  questions table is not read), with the header `| Question type | Stories |`. One row per question
  type, each type in one row only: `| <question type> | <story>; <story> |`, or, once the type has a
  Talking points file, `| [<question type>](stories/<slug>.md) | <story>; <story> |`. A question
  type holds no `|` and no `;`. A story is
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
  is optional (`YYYY-MM-DD` alone reads as 00:00), but the stories mode writes it at every save and
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
  is (exit 2 otherwise). A wording that starts with `-` goes after `--`. Prints `added:
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

Exit 2, with one line saying why, on a bad argument, a <root> with no entries/ folder, an <entry>
that is not an entry, a file it cannot read, or (links-since, story-stale) when git fails.
Standard library only, Python 3.11+.
"""
import datetime
import os
import posixpath
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ENTRY_PATH = re.compile(r"entries/(?!_template\.md$)[^/]+\.md")   # fullmatch, on a /-separated path
THRESHOLD = 12500
STATUSES = ("stub", "imported", "consolidated")
LOG_FILES = ["README.md", "README.zh-TW.md", "stories.md", "profile.md", "direction.md", "applications.md"]
LOG_FOLDERS = ["entries", "stories", "outputs", "sources"]
INBOX = "sources/inbox"
URL = re.compile(r"https?://[^\s<>\"'`\]|]+")
MD_TARGET = re.compile(r"\]\(([^)\s]+)\)")
PERIOD = re.compile(r"(\d{4}-\d{2}(?:-\d{2})?)(?: – (ongoing|\d{4}-\d{2}(?:-\d{2})?))?", re.I)
MAX_TYPES_PER_STORY = 3   # a Story (entry#anchor) under more types than this is told for too many questions
CORE_RANGE = (3, 5)       # how many core Stories (experiences marked core) a Log should have
MAX_PER_INTERVIEW = 1     # questions one Story (entry#anchor) may lead in one interview
WORDINGS = "stories/wordings"
UNFINISHED = ("raw", "pending")
STORY_SPLIT = re.compile(r";\s+(?=\*\(|\[)")
MARKER = re.compile(r"\*\(([^)*]+)\)\*\s*")
LINK = re.compile(r"\[((?:[^\]\\]|\\.)*)\]\(([^)\s]+)\)")


class Error(Exception):
    pass


# ---- Reading an entry ----

def entry_paths(root):
    """The entries under root, as sorted /-separated paths relative to it; [] without entries/."""
    folder = os.path.join(root, "entries")
    if not os.path.isdir(folder):
        return []
    return [p for p in ("entries/" + n for n in sorted(os.listdir(folder)))
            if ENTRY_PATH.fullmatch(p) and os.path.isfile(os.path.join(root, p))]


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def unquote(value):
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def scalar(value):
    """A front matter value: a quoted one up to its closing quote, else up to a ` #` comment."""
    value = value.strip()
    m = re.match(r"(\"[^\"]*\"|'[^']*')", value)
    if m:
        return m.group(1)[1:-1]
    return re.sub(r"(^|\s+)#.*$", "", value).strip()


def front_matter(text):
    """{key: str or list}: inline lists `[a, b]` and block lists (`  - a`) become lists."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
        item = re.match(r"\s+- (.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            listed = re.sub(r"\]\s+#.*$", "]", value)
            if listed.startswith("[") and listed.endswith("]"):
                items = re.findall(r"\s*(?:\"[^\"]*\"|'[^']*'|[^,]+)", listed[1:-1])
                fields[key] = [unquote(v) for v in items if v.strip()]
            else:
                fields[key] = scalar(value)
        elif item and key:
            if not isinstance(fields.get(key), list):
                fields[key] = []
            fields[key].append(scalar(item.group(1)))
    return fields


def as_list(value):
    if isinstance(value, list):
        return value
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def section(text, heading):
    """A `## <heading>` section's text, HTML comments and blank lines dropped, joined by spaces."""
    m = re.search(r"^## %s[ \t]*\n(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    if not m:
        return ""
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    return " ".join(line.strip() for line in body.splitlines() if line.strip())


def tokens(text):
    """Estimated tokens: ASCII characters / 2.7 plus 4/3 per other character, rounded up."""
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return -(-(ascii_chars * 40 + (len(text) - ascii_chars) * 144) // 108)


def slug_of(path):
    return re.sub(r"^\d{4}-\d{2}-", "", os.path.basename(path)[:-3])


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


class Entry:
    def __init__(self, root, path):
        self.path = path
        self.text = read(os.path.join(root, path))
        self.fields = front_matter(self.text)
        self.slug = slug_of(path)
        self.series = self.fields.get("series") or ""
        self.period = norm_period(self.fields.get("period"))
        span = parse_period(self.period)
        self.span = span
        self.ongoing = bool(span) and span[1] is None
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
    header = None
    for line in read(path).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip("|"))]
        if header is None:
            header = [c.strip("*` ").lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: ") or "entry" not in header:
            continue
        row = dict(zip(header, cells))
        m = re.search(r"\[(.*)\]\(\.?/?(entries/[^)#\s]+)(?:#[^)]*)?\)", row.get("entry", ""))
        if not m:
            continue
        row["title"] = m.group(1).replace("\\|", "|")
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


def findings(root, today):
    entries = load(root)
    out = over_threshold(entries)
    slugs = {e.slug for e in entries}
    series = {}
    for e in entries:
        if e.series:
            if not e.span:
                out.append("series part with an unreadable period: %s %r (YYYY-MM – YYYY-MM or YYYY-MM –"
                           " ongoing)" % (e.path, e.period))
            series.setdefault(e.series, []).append(e)
            if e.series not in slugs:
                out.append("series names no entry: %s series %s" % (e.path, e.series))
            if not e.one_line:
                out.append("series part with an empty One line: %s" % e.path)
    for name, parts in series.items():
        ongoing = [p.path for p in parts if p.ongoing]
        if len(ongoing) > 1:
            out.append("series %s has more than one ongoing part: %s" % (name, ", ".join(ongoing)))
        spans = [p for p in parts if p.span]
        for i, a in enumerate(spans):
            for b in spans[i + 1:]:
                a_end, b_end = a.span[1] or "9999-99-99", b.span[1] or "9999-99-99"
                same_start = not before(a.span[0], b.span[0]) and not before(b.span[0], a.span[0])
                if same_start or (before(a.span[0], b_end) and before(b.span[0], a_end)):
                    out.append("series %s has overlapping periods: %s (%s), %s (%s)"
                               % (name, a.path, a.period, b.path, b.period))
    rows, missing = readme_rows(root)
    out += ["README row names a missing file: %s" % t for t in missing]
    for e in entries:
        row = rows.get(e.path)
        if row is None:
            out.append("no README row: %s" % e.path)
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
        out += ["README row differs: %s: %s" % (e.path, d) for d in differ]
        if "status" in row and not re.match(r"(%s)\b" % "|".join(STATUSES), row["status"]):
            out.append("README row status unknown: %s %r (starts with %s)"
                       % (e.path, row["status"], ", ".join(STATUSES)))
    cutoff = months_before(today, 2)
    for e in entries:
        updated = e.fields.get("last_updated") or ""
        if not e.ongoing:
            continue
        try:
            day = datetime.date.fromisoformat(updated)
        except ValueError:
            out.append("ongoing entry with no readable last_updated: %s %r" % (e.path, updated))
            continue
        if day < cutoff:
            out.append("ongoing entry not updated in over two months: %s last_updated %s" % (e.path, updated))
    return out, len(entries)


def cmd_check(root, today):
    found, n = findings(root, today)
    for line in found:
        print(line)
    if found:
        return 1
    print("OK: %d entries, no findings" % n)
    return 0


def log_files(root):
    """The Log's text files other than the Engine's, as /-separated paths."""
    out = [f for f in LOG_FILES if os.path.isfile(os.path.join(root, f))]
    for folder in LOG_FOLDERS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, folder)):
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            dirnames[:] = sorted(d for d in dirnames if (rel + "/" + d) != INBOX and not d.startswith("."))
            out += [rel + "/" + f for f in sorted(filenames)]
    return [p for p in out if p != "entries/_template.md"]


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


def cmd_refs(root, path):
    stem = re.escape(os.path.basename(path)[:-3])
    pattern = re.compile(r"(?<![\w-])%s(?![\w-])" % stem)
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
                print("%s:%d: %s" % (rel, n, line if len(line) <= 300 else line[:300] + " ..."))
    return 0


def git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, "-c", "core.quotepath=false"] + list(args),
                           capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Error("git failed: %s" % e)
    if p.returncode != 0:
        raise Error("git %s failed: %s" % (args[0], p.stderr.strip()))
    return p.stdout


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
    now = links(read(os.path.join(root, path)))
    if sha:
        before = set(links(git(root, "show", "%s:./%s" % (sha, path))))
        print("since: %s %s" % (sha[:12], subject))
    else:
        before = set()
        print("since: no consolidate(%s) commit touches %s; every link is listed" % (slug_of(path), path))
    for link in now:
        if link not in before:
            print("link: %s" % link)
    return 0


# ---- Stories ----

def story_slug(question_type):
    return re.sub(r"[\W_]+", "-", question_type.lower()).strip("-")


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
    rows, header, found = [], None, False
    for line in read(path).splitlines():
        if line.startswith("## "):
            break
        line = line.strip()
        if not line.startswith("|"):
            if rows:
                break
            header = None
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip("|"))]
        if header is None:
            header = [c.strip("*` ").lower() for c in cells]
            found = found or header[:2] == ["question type", "stories"]
            continue
        if set("".join(cells)) <= set("-: ") or header[:2] != ["question type", "stories"]:
            continue
        rows.append(Row(cells[0], cells[1] if len(cells) > 1 else ""))
    return rows if found else None


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
        m = re.search(r"^## Stories[ \t]*\n(.*?)(?=^## |\Z)", self.text, re.M | re.S)
        listed = re.findall(r"^\s*\d+\.\s+(.*\S)", re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S),
                            re.M) if m else []
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


def cmd_story_coverage(root, questions):
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
    for line in out:
        print(line)
    if out:
        return 1
    print("OK: %d question types, no findings" % len(rows))
    return 0


def section_lines(text, heading):
    """A `## <heading>` section's `- ` bullets, HTML comments dropped."""
    m = re.search(r"^## %s[ \t]*\n(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    if not m:
        return []
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    return [line.strip()[2:].strip() for line in body.splitlines() if line.strip().startswith("- ")]


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
        body = re.sub(r"<!--.*?-->", "", re.sub(r"\A---\n.*?^---[ \t]*$", "", text.replace("\r\n", "\n"),
                                                  count=1, flags=re.M | re.S), flags=re.S)
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


def heading_anchors(text):
    """GitHub's anchors for a Markdown file's section headings, `## ` to `###### ` (a repeated one gets
    -1, -2, ..., counting the `# ` title too), outside HTML comments and fenced code (an unclosed
    fence runs to the end)."""
    out, seen, fence = set(), {}, None
    for line in re.sub(r"<!--.*?-->", "", text, flags=re.S).splitlines():
        m = re.match(r"[ \t]*(`{3,}|~{3,})", line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip(" \t`~"):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        h = re.match(r"(#{1,6})[ \t]+(.+?)[ \t#]*$", line)
        if not h:
            continue
        base = re.sub(r"[^\w\- ]", "", h.group(2).strip().lower()).replace(" ", "-")
        n = seen.get(base, 0)
        seen[base] = n + 1
        if len(h.group(1)) > 1:
            out.add(base if n == 0 else "%s-%d" % (base, n))
    return out


def drop_unfinished(item):
    """The item with `raw` and `pending` taken out of its markers (before the link and right after
    it), and the markers dropped, in their order."""
    dropped, parts, pos = [], [], 0

    def strip(m):
        keep = []
        for v in (v.strip() for v in m.group(1).split(",")):
            if v and v.lower() in UNFINISHED:
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


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):   # Log text in any language, whatever the code page
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    usage = ("usage: %s -I tools/entries.py list [<root>] [--series <slug>] | check [<root>] |"
             " refs <entry> [<root>] | links-since <entry> [<root>] |"
             " story-coverage [<root>] [--type <question type>]... | story-candidates <question type> [<root>] |"
             " story-stale <talking points file> [<root>] | story-finish <entry> [<root>] |"
             " story-wording-add <question type> <wording> [<root>] | story-wordings [<root>] [--type <question type>]..."
             % ("py -3" if os.name == "nt" else "python3"))
    passthrough = argv[:1] == ["story-wording-add"] and "--" in argv   # only it takes free text
    flags = argv[:argv.index("--")] if passthrough else argv
    if "-h" in flags or "--help" in flags:
        print(__doc__.rstrip())
        return 0
    args, opts = [], {}
    it = iter(argv)
    for a in it:
        if a in ("--series", "--today", "--type"):
            value = next(it, None)
            if a == "--type" and value is not None:
                opts.setdefault(a, []).append(value)
            else:
                opts[a] = value
            if value is None:
                print(usage)
                return 2
        elif a == "--" and passthrough:   # the rest are arguments, a wording that starts with `-` included
            args += list(it)
        elif a.startswith("--"):
            print(usage)
            return 2
        else:
            args.append(a)
    if not args or args[0] not in ("list", "check", "refs", "links-since", "story-coverage",
                                   "story-candidates", "story-stale", "story-finish", "story-wording-add",
                                   "story-wordings"):
        print(usage)
        return 2
    cmd, rest = args[0], args[1:]
    needs_entry = cmd in ("refs", "links-since", "story-candidates", "story-stale", "story-finish")
    if cmd == "story-wording-add":   # two arguments before <root>
        if not 2 <= len(rest) <= 3:
            print(usage)
            return 2
        rest = [rest[:2]] + rest[2:]
    takes_arg = needs_entry or cmd == "story-wording-add"
    if (len(rest) > (2 if takes_arg else 1) or (needs_entry and not rest)
            or ("--series" in opts and cmd != "list") or ("--today" in opts and cmd != "check")
            or ("--type" in opts and cmd not in ("story-coverage", "story-wordings"))):
        print(usage)
        return 2
    root = (rest[1] if len(rest) > 1 else ROOT) if takes_arg else (rest[0] if rest else ROOT)
    try:
        today = datetime.date.fromisoformat(opts["--today"]) if "--today" in opts else datetime.date.today()
    except ValueError:
        print("--today takes YYYY-MM-DD")
        return 2
    if not os.path.isdir(os.path.join(root, "entries")):
        print("FAIL: no entries/ folder in %s; give the Log's root" % root)
        return 2
    try:
        if cmd == "list":
            return cmd_list(root, opts.get("--series"))
        if cmd == "check":
            return cmd_check(root, today)
        if cmd == "story-coverage":
            return cmd_story_coverage(root, opts.get("--type", []))
        if cmd == "story-candidates":
            return cmd_story_candidates(root, rest[0])
        if cmd == "story-stale":
            return cmd_story_stale(root, talking_points_arg(root, rest[0]))
        if cmd == "story-wording-add":
            return cmd_story_wording_add(root, *rest[0])
        if cmd == "story-wordings":
            return cmd_story_wordings(root, opts.get("--type", []))
        path = entry_arg(root, rest[0])
        if cmd == "story-finish":
            return cmd_story_finish(root, path)
        return cmd_refs(root, path) if cmd == "refs" else cmd_links_since(root, path)
    except (Error, OSError, UnicodeDecodeError) as e:
        print("FAIL: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
