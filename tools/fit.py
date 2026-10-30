#!/usr/bin/env python3
"""The requirement map: a map file (a fit result), its checks, the lines it prints, and the fit maps a
scan report keeps (skills/career-log/modes/fit.md › Requirement map; scan.md step 7).

  python3 -I tools/fit.py name <company> <role> [--today YYYY-MM-DD]
  python3 -I tools/fit.py map <map file>... [--several] [--category <category>]... [--save-name] [--today YYYY-MM-DD]
  python3 -I tools/fit.py map <map file> --show
  python3 -I tools/fit.py heatmap <map file or Screen results file>...
  python3 -I tools/fit.py check <result.jsonl> [--capture <capture path>]
  (Windows: py -3 -I tools/fit.py ...)

It takes --root <root>, the Log's root (default: the repo this script is in), anywhere on the line.
A relative path argument is read from the Log's root.

A map file holds one JSON object on one line. A fit result is the map file a fit subagent writes
for scan (fit.md › Handed over by scan); it also has the posting fields. Its fields:
- `company`, `role`: the posting's company and role (`--several` and `--save-name` read them; give
  `name` the same two);
- `requirements`: the posting's requirements and duties, less the conditions Requirement map item 1
  takes out, each as one string in the posting's words;
- `course_work`: the course-work list of Requirement map item 2, as entry file names ([] for none);
- `rows`: one object per row of the map:
  - `requirement`: the row's skill or duty;
  - `of`: the number (from 1) of the `requirements` item the row maps; it may be left out when
    `requirement` is that item word for word;
  - `kind`: `required`, `preferred` or `duty`, as the posting gives it (KINDS);
  - `row_type`: `language or tool` (a row naming a language or a tool), `debugging` (a row for
    debugging or diagnosing), `understanding` (a requirement that asks only for understanding,
    knowledge, exposure or familiarity) or `other` (ROW_TYPES);
  - `written_by`: `coursework`, `collaborator`, `AI agent`, `unknown` or `user` (WRITERS); "" on a
    `gap` or `claimed, unbacked` row;
  - `own_work`: on an `AI agent` row, `none` or `<label>: <quote>`, the label `design`, `debugging`
    or `review`, the quote a line of the entry word for word; "" on every other row;
  - `category`: `covered`, `shallow`, `claimed, unbacked` or `gap` (CATEGORIES);
  - `entry`: the cited entry's file name, a section name in parentheses after it when the row cites
    one section ("2026-01-x.md (phase 3)"); "" on a `gap` or `claimed, unbacked` row;
  - `skill` (`heatmap` needs it; optional elsewhere): the skill's name in the heatmap, the same
    words on every row, in every map file, that asks for the same skill ("Go" on a "Golang" row).
- `capture` (`map` and `heatmap` need it): the path of the posting's capture (`scan.py capture`,
  `fetch` or an application's `posting.md`), relative to the Log's root or absolute.
A map file `heatmap` reads also has `tier`: the posting's role's place in direction.md's Target
roles (1 the first line, its `GAP:` lines counted), or null for a role on no tier; null on every map
file while they are empty.
A fit result also has
- `url`: the URL on the capture's first line;
- `recommendation`: `apply`, `apply with caveats` or `skip` (RECOMMENDATIONS);
- `check`: the things to check, a list of strings ([] for none);
- `notes`: the `Course work:` and `Map:` lines `map` prints for it, a list of two strings.
A result `scan.py fitmap --out` writes from an earlier report also has `fit_commit` (the map's
entries commit), `reused` (that report) and `text` (the map's lines below its header, as the report
holds them), and none of the map fields; a row of a report written before rows kept their kind has
`kind` null.

A scan report's `## Fit maps` holds one `### <company> — <role>` subsection per posting, with a
`URL:` line, a `Screen:` line, an `Entries commit:` line, a `Recommendation:` line, the things to
check, the notes, and the map as a table with the headers of COLUMNS. Required coverage is
`<covered>/<required>`: the rows of kind required or duty, and of them the `covered` ones; when no
row has one of those kinds (a map from before kinds were kept), every row counts.

- `name`: prints `map file: .build/fit/<YYYY-MM-DD>-<company>-<role>.jsonl`, the path to write the
  map file to, company and role as ASCII names (lowercase letters and digits, `-` between words; a
  name that holds a character outside ASCII, or no letter or digit, ends in the first 8 hex digits
  of its SHA-256).
- `map`: checks each map file and prints, per file:
  - `Course work: <the course_work file names, or none> (<n> entries listed)`, <n> the number of
    lines `tools/entries.py list` prints that start with `entries/`;
  - `Map: <n> requirements and duties, <m> rows; no row: <none, or each requirements item no row
    maps, joined by "; ">`; with --several, `Map (<company>, <role>): ...`;
  - the map as a table with the headers of COLUMNS, `-` in an empty cell; with --category (given
    once per category: `--category gap --category "claimed, unbacked"`), only the rows in those
    categories;
  then, with --save-name and no problem, for one map file with its company and role:
  `save: outputs/reports/<YYYY-MM-DD>-fit-posting-<company>-<role>.md` and
  `commit: fit(<company>-<role>): <n> gaps`, <n> the rows whose category is `gap`, named as `name`
  names them; then one `flag:` line per map file whose capture is closed, a stand-in's or of an
  unknown read, as scan.py's capture_state reads it (`scan.py state <capture path>` prints it):
  `flag: <map file> | capture <capture path> | <why>`, <why> `closed (<its why>)`,
  `read stand-in <API url>` or `read unknown (the capture has no read line)`, joined by "; "; a flag
  is no problem; then `map: ok`, or one `bad:` line per problem and exit 1.
  With --show (one map file; no --several, --category or --save-name), a `show:` line and one block
  to paste whole into a reply (write step 9) take the place of the two lines and the table: with
  no code fence, so the reply renders the table, the same `Course work:` and `Map:` lines, a blank
  line, and the map as a table with the headers of SHOW (COLUMNS less Own work), an `AI agent`
  row's Written by naming its own work's label (`AI agent (design)`, `AI agent (none)`). A cell's
  `|` is escaped, so a `|` or backticks in a cell stay in that cell.
  The checks, and the `flag:` (after an empty line below the table), `map: ok` or `bad:` lines,
  are the same.
  The problems:
  - a field above missing or not in its form, an `of` that is no `requirements` item's number;
    `company` or `role` that is not a string; with --several, two map files whose company and role
    give one name (as `name` makes it);
  - a cited entry with no file `entries/<name>`, a `course_work` name with none;
  - a `gap` or `claimed, unbacked` row with an entry, a written by or an own work; any other row
    without an entry or a written by;
  - a `coursework` row whose entry is not on `course_work`, or a row citing an entry on it that is
    not `coursework`;
  - own work on a row that is not `AI agent`, or none on one that is; own work that is neither
    `none` nor `<label>: <quote>`; a quote of fewer than three words, or one that is not in the
    cited entry's `## My contribution`, `## How it works` or a line holding `Settled:` (compared
    with bold, italic and code marks taken out, curly quote marks read as straight ones, each run
    of spaces and line breaks read as one space, and quote marks around the quote or around each
    part dropped; a `...` or `…` in the quote stands for words left out, and the parts, each whole
    words, must come in order in one of those places). The label may be in bold. A label other
    than the three is not a problem: it caps the row;
  - a `covered` row over its cap: `unknown`; `AI agent` with own work `none` or another label;
    `coursework` that is not `understanding`; `language or tool` with a `design` label; `debugging`
    with a label other than `debugging`;
  - a `requirements` item no row maps (the `Map:` line names it too);
  - no `capture`, or one that names no file.
- `heatmap`: runs `map --several`'s checks on the map files, and also that every row has a `skill`
  (a non-empty string) and every map file a `tier` (null, or the place of a line of Target roles
  that is no `GAP:` line). A Screen results file (a file in a scan run folder's `screen/` folder,
  when the run folder holds `screen-list.jsonl`; tools/scan.py --help gives the format) gets the
  checks of `scan.py screen --check`, and each of its gate yes results with `rows` is a rough
  posting, its company and role from the `screen-list.jsonl` line with its URL; a result with no
  such line, or a line with no company or role, is a problem. A rough posting whose URL a map
  file's `url` or an earlier rough posting has, or whose company and role a map file has (as `name`
  makes them one name), is left out: it is counted once, as mapped. No posting at all (only gate no
  results, say) is a problem too. On a problem it prints only the `bad:` lines and exits 1. Else it prints
  `Heatmap: <k> skills, <n> gaps; weights: <which>; <p> postings (<m> mapped, <r> rough) from <e>
  employers; flagged: <f> of <p>` (<which> `tiers`, or `every posting the same` when no posting
  has a tier; <e> the companies, ignoring case and runs of spaces; <f> the postings with a `flag:`
  line, mapped or rough), then, when one company holds more than half the
  postings, `skew: <company> holds <k> of the <p> postings` (named as its first posting names it),
  then a legend numbering the map files
  in the order given, then the rough postings, a Markdown list item each, `- #<i> <company>, <role>`,
  ` (rough)` after a rough one, between empty lines, then a table with the headers of HEATMAP, one
  row per skill (rows whose `skill` matches, ignoring case and runs of spaces, are one skill, named
  as the first of them is, each run of spaces one space), an empty line, the `flag:` lines `map`
  prints for the map files, then one `flag: <Screen results file> line <n> (rough) | capture
  <capture path> | <why>` line per rough posting whose capture (its `screen-list.jsonl` line's
  `capture`) is closed, a stand-in's or of an unknown read, <why> as `map` gives it (`read unknown
  (no file)` when the capture is gone), then `heatmap: ok`. A flagged rough posting stays in the
  heatmap, as a flagged map file does. A skill's cells:
  - Category: its weakest mapped row's, `gap` first, then `claimed, unbacked`, `shallow`, `covered`;
    `rough` when it has no mapped row (a rough row is never `covered`);
  - Postings: `<a> of <b>`, the postings with a row for it of all the postings;
  - Rough: `<r> (<t> touched)`, the rough postings of those and the ones whose rows for it name an
    entry; `-` for none;
  - Which: those postings' legend numbers, in order, joined by ", " (`#1, #3`);
  - Priority: `-` when Category is `covered`; else from its share: each posting weighs
    <the last target role's tier> + 1 - <tier> (1 when the tier is null; a `GAP:` line above a role
    keeps its place, as a role not yet named), and the share is the sum,
    over the postings where it has a row that is not covered (every rough row), of that weight
    times 2 when one of those rows is required or a duty (1 when they are all preferred),
    divided by twice the sum of all the postings' weights. `critical` from 0.6, `high` from 0.3,
    `medium` from 0.1, else `low`. The rows are ordered by priority, then share and the number
    of postings (each highest first), then skill.
  <n> is the rows whose Category is `gap`.
- `check`: checks a fit result file: one line, the fit result fields in their form, with --capture
  that its `url` is the one on the capture's first line, and, unless it is `reused`, everything
  `map` checks but `capture`, with its `notes` the two lines `map` prints for it (the bad line
  gives them).
  `check: ok`, else exit 1 with one `bad:` line per problem.

Exit 0 on success, 1 when a check fails or a file cannot be read, 2 on a bad argument. Standard
library only, Python 3.11+.
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
import config   # direction.md's target roles, as config.py's show reads them

KINDS = ("required", "preferred", "duty")
CATEGORIES = ("covered", "shallow", "claimed, unbacked", "gap")
RECOMMENDATIONS = ("apply", "apply with caveats", "skip")
ROW_TYPES = ("language or tool", "debugging", "understanding", "other")
WRITERS = ("coursework", "collaborator", "AI agent", "unknown", "user")
LABELS = ("design", "debugging", "review")
NO_ENTRY = ("claimed, unbacked", "gap")
HEATMAP = ("Priority", "Skill", "Category", "Postings", "Rough", "Which")
PRIORITIES = ((0.6, "critical"), (0.3, "high"), (0.1, "medium"), (0.0, "low"))
COLUMNS = [("Requirement", "requirement"), ("Kind", "kind"), ("Written by", "written_by"),
           ("Own work", "own_work"), ("Category", "category"), ("Entry", "entry")]
SHOW = [c for c in COLUMNS if c[1] != "own_work"]   # map --show's table
# An entry's file name as a map cites it: dated, any letters (an entry named in Chinese, say)
ENTRY_NAME = re.compile(r"(?<![0-9A-Za-z])(\d{4}-\d{2}-[^\s`|/\\()\[\]<>\"',;:!?]+?\.md)"
                        r"(?=\Z|[\s`|/\\()\[\]<>\"',;:!?]|\.(?!\w))")


class FitError(Exception):
    pass


# ---- The maps of a scan report ----

def fit_maps(text):
    """[(url, sha, body)] of the `### ` subsections under `## Fit maps`."""
    m = re.search(r"^## Fit maps[ \t]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    out = []
    for part in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
        u = re.search(r"^URL:(.*)$", part, re.M)
        s = re.search(r"^Entries commit:\s*`?([0-9a-f]{4,40})`?", part, re.M)
        found = logfiles.urls(u.group(1)) if u else []
        if found:
            out.append((found[0], s.group(1) if s else None, part))
    return out


def map_rows(body):
    """The rows of the map in a fit map subsection, as COLUMNS dicts (`kind` None when its table has
    no Kind column), or None when it holds no table with a Requirement column."""
    for t in logfiles.md_tables(body):
        if "requirement" not in t.header:
            continue
        rows = []
        for d in t.dicts():
            row = {key: d.get(head.lower(), "").strip("*` ") for head, key in COLUMNS}
            row["kind"] = row["kind"].lower() or None if "kind" in t.header else None
            row["category"] = row["category"].lower()
            rows.append(row)
        return rows
    return None


def recommendation(body):
    """The `Recommendation:` line's value, or None."""
    m = re.search(r"^Recommendation:\s*(.+?)\s*$", body, re.M)
    return m.group(1) if m else None


def cited_entries(body):
    """The entry file names the map cites: those of its Entry cells and any other its text names (an
    older map's column may have another name), so a change to any of them makes it stale."""
    rows = map_rows(body) or []
    return sorted(set(ENTRY_NAME.findall("\n".join(r["entry"] for r in rows) + "\n" + body)))


def coverage(rows):
    """(covered, required) of a map's rows, as the docstring says."""
    counted = [r for r in rows if r.get("kind") in ("required", "duty")] or rows
    return sum(1 for r in counted if r.get("category") == "covered"), len(counted)


def map_lines(result):
    """The lines of a fit map subsection below its `URL:` and `Entries commit:` lines: the
    recommendation, the things to check, the notes and the table; a reused map's own lines as the
    report held them."""
    out = ["Recommendation: %s" % result["recommendation"], ""]
    if result.get("text") is not None:
        return out + result["text"].strip("\n").split("\n")
    if result.get("check"):
        out += ["Things to check:", ""] + ["- %s" % c for c in result["check"]] + [""]
    if result.get("notes"):
        out += list(result["notes"]) + [""]
    return out + table(result["rows"])


def show_block(lines, rows):
    """`map --show`'s lines: a `show:` line, then the `Course work:` and `Map:` lines, a blank line and
    the map as a table with the headers of SHOW (an `AI agent` row's Written by naming its own work's
    label), with no code fence, so a reply renders it. A backslash before a `|` is doubled, so the
    `|` md_row escapes stays in its cell."""
    body = lines + ["", "| " + " | ".join(h for h, _ in SHOW) + " |", "|" + "---|" * len(SHOW)]
    for r in rows:
        cells = {k: r.get(k) for _, k in SHOW}
        if r.get("written_by") == "AI agent":
            own = split_own_work(r.get("own_work"))
            cells["written_by"] = "AI agent (%s)" % (own[0] if own else "none")
        body.append(logfiles.md_row("-" if cells[k] in (None, "") else re.sub(r"\\(?=\|)", r"\\\\", str(cells[k]))
                                    for _, k in SHOW))
    return ["show: paste the lines below, from `Course work:` to the table's last row, into your reply"
            " whole, as printed"] + body


def table(rows):
    """The map's rows as a table with the headers of COLUMNS, `-` in an empty cell."""
    out = ["| " + " | ".join(h for h, _ in COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for r in rows:
        out.append(logfiles.md_row("-" if r.get(k) in (None, "") else str(r[k]) for _, k in COLUMNS))
    return out


def body_text(body):
    """A subsection's lines below its header lines (heading, URL:, Screen:, Entries commit:,
    Recommendation:), for a reused map."""
    lines = body.split("\n")[1:]
    head = re.compile(r"^(URL|Screen|Entries commit|Recommendation):")
    return "\n".join(l for l in lines if not head.match(l)).strip("\n")


# ---- A fit result ----

def problems(result, capture_url=None, posting=True):
    """What is wrong with a fit result's shape, as `bad:` lines' text; [] when nothing is. With
    posting False (a map file), `url`, `recommendation`, `check` and `notes` are not read. The map's
    own rules are map_problems'."""
    if not isinstance(result, dict):
        return ["the line is no JSON object"]
    out = []
    if posting:
        found = logfiles.urls(str(result.get("url") or ""))
        if not found:
            out.append("url: no URL")
        elif capture_url and logfiles.clean_url(capture_url) != found[0]:
            out.append("url: %s, but the capture's first line gives %s" % (found[0], capture_url))
        if result.get("recommendation") not in RECOMMENDATIONS:
            out.append("recommendation: %r is not one of %s" % (result.get("recommendation"), ", ".join(RECOMMENDATIONS)))
        for name in ("check", "notes"):
            v = result.get(name, [])
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                out.append("%s: must be a list of strings" % name)
    rows = result.get("rows")
    if not isinstance(rows, list) or not rows:
        return out + ["rows: must be a list with one object per row of the map"]
    reused = "reused" in result
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            out.append("rows[%d]: is no JSON object" % i)
            continue
        for _, key in COLUMNS:
            if not isinstance(r.get(key, ""), (str, type(None))):
                out.append("rows[%d].%s: must be a string" % (i, key))
        if not str(r.get("requirement") or "").strip():
            out.append("rows[%d].requirement: empty" % i)
        if r.get("kind") not in KINDS and not (reused and r.get("kind") is None):
            out.append("rows[%d].kind: %r is not one of %s" % (i, r.get("kind"), ", ".join(KINDS)))
        if r.get("category") not in CATEGORIES:
            out.append("rows[%d].category: %r is not one of %s" % (i, r.get("category"), ", ".join(CATEGORIES)))
        if not isinstance(r.get("skill", ""), str):
            out.append("rows[%d].skill: must be a string" % i)
    return out


# ---- The map's rules ----

MARKS = re.compile(r"[*_`]")
ELLIPSIS = re.compile(r"\.\.\.|…")
QUOTE_MARKS = "\"'“”‘’"


CURLY = str.maketrans("\u201c\u201d\u2018\u2019", "\"\"''")


def plain(text):
    """Text as a quote is compared: no bold, italic or code marks, curly quote marks straight, each run
    of white space one space."""
    return " ".join(MARKS.sub("", text).translate(CURLY).split())


def quote_sources(text):
    """The places of an entry an own work line may quote: `## My contribution`, `## How it works`,
    and each line holding `Settled:`."""
    found = [logfiles.section(text, h) or "" for h in ("My contribution", "How it works")]
    found += [l for l in text.split("\n") if "Settled:" in l]
    return [plain(t) for t in found if t.strip()]


def quoted(quote, sources):
    """Whether the quote's parts (split at `...` or an ellipsis) come, in order, in one of the sources."""
    parts = [p for p in (plain(x).strip(QUOTE_MARKS + " ") for x in ELLIPSIS.split(quote)) if p]
    if sum(len(p.split()) for p in parts) < 3:
        return False
    for src in sources:
        at = 0
        for p in parts:
            m = re.compile(r"(?<!\w)%s(?!\w)" % re.escape(p)).search(src, at)
            if not m:
                break
            at = m.end()
        else:
            return True
    return False


def split_own_work(value):
    """(label, quote) of an own work cell, ("none", "") for `none`, None when it is neither."""
    value = (value or "").strip()
    if value.lower() == "none":
        return "none", ""
    m = re.match(r"([^:\n]{1,40}?):(?:[*_]*)\s*(\S.*)\Z", value, re.S)
    return (MARKS.sub("", m.group(1)).strip().lower(), m.group(2)) if m else None


def entry_name(cell):
    found = ENTRY_NAME.findall(cell or "")
    return found[0] if found else None


def requirements(result):
    reqs = result.get("requirements")
    return reqs if isinstance(reqs, list) else []


def row_of(result, row):
    """The number (from 1) of the `requirements` item a row maps, or None."""
    reqs = requirements(result)
    n = row.get("of")
    if n is None:
        words = str(row.get("requirement") or "").strip()
        n = next((k for k, q in enumerate(reqs, 1) if isinstance(q, str) and q.strip() == words), None)
    return n if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(reqs) else None


def unmapped(result):
    """The `requirements` items no row maps."""
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    hit = {row_of(result, r) for r in rows if isinstance(r, dict)}
    return [str(q) for k, q in enumerate(requirements(result), 1) if k not in hit]


def map_problems(root, result):
    """What breaks the requirement map's rules (the docstring's list), as `bad:` lines' text."""
    out = []
    reqs = result.get("requirements")
    if not isinstance(reqs, list) or not reqs or not all(isinstance(q, str) and q.strip() for q in reqs):
        out.append("requirements: must be a list of the requirements and duties, one non-empty string each")
    for k in ("company", "role"):
        if result.get(k) is not None and not isinstance(result.get(k), str):
            out.append("%s: must be a string" % k)
    cw = result.get("course_work")
    if not isinstance(cw, list) or not all(isinstance(c, str) for c in cw):
        out.append("course_work: must be a list of entry file names ([] for none)")
        cw = []
    texts = {}

    def entry_text(name):
        if name not in texts:
            p = os.path.join(root, "entries", name)
            texts[name] = logfiles.read_text(p).replace("\r\n", "\n") if os.path.isfile(p) else None
        return texts[name]

    course = set()
    for c in cw:
        name = entry_name(c)
        if not name or entry_text(name) is None:
            out.append("course_work: %r is no file in entries/" % c)
        else:
            course.add(name)
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict) or not all(isinstance(r.get(k) or "", str) for _, k in COLUMNS):
            continue   # problems() names it
        at = "rows[%d]" % i
        if row_of(result, r) is None:
            if "of" in r:
                out.append("%s.of: %r is not the number of a requirements item (1 to %d)" % (at, r["of"], len(requirements(result))))
            else:
                out.append("%s: requirement %r is no requirements item word for word; give its of" % (at, r.get("requirement")))
        if r.get("row_type") not in ROW_TYPES:
            out.append("%s.row_type: %r is not one of %s" % (at, r.get("row_type"), ", ".join(ROW_TYPES)))
        cat, writer = r.get("category"), r.get("written_by") or ""
        own, cell = r.get("own_work") or "", r.get("entry") or ""
        if cat in NO_ENTRY:
            if cell or writer or own:
                out.append("%s: a %r row has no entry, written by or own work" % (at, cat))
            continue
        if writer not in WRITERS:
            out.append("%s.written_by: %r is not one of %s" % (at, writer, ", ".join(WRITERS)))
        name = entry_name(cell)
        if not name:
            out.append("%s.entry: %r names no entry file" % (at, cell))
        elif entry_text(name) is None:
            out.append("%s.entry: %s is no file in entries/" % (at, name))
        if writer == "coursework" and name and name not in course:
            out.append("%s: written by coursework, but %s is not on course_work" % (at, name))
        if writer != "coursework" and name in course:
            out.append("%s: %s is on course_work, so its written by is coursework" % (at, name))
        cap = None
        if writer == "AI agent":
            split = split_own_work(own)
            if not own:
                out.append("%s.own_work: empty on an AI agent row; give <label>: <quote> or none" % at)
            elif split is None:
                out.append("%s.own_work: %r is neither none nor <label>: <quote>" % (at, own))
            else:
                label, quote = split
                text = entry_text(name) if name else None
                if quote and len(plain(ELLIPSIS.sub(" ", quote)).strip(QUOTE_MARKS + " ").split()) < 3:
                    out.append("%s.own_work: the quote has fewer than three words; quote the line" % at)
                elif quote and text is not None and not quoted(quote, quote_sources(text)):
                    out.append("%s.own_work: the quote is not word for word in %s's ## My contribution, "
                               "## How it works or a Settled: line" % (at, name))
                if label == "none":
                    cap = "AI agent with own work none"
                elif label not in LABELS:
                    cap = "AI agent with the label %r (not design, debugging or review)" % label
                elif r.get("row_type") == "language or tool" and label == "design":
                    cap = "a language or tool row with a design label"
                elif r.get("row_type") == "debugging" and label != "debugging":
                    cap = "a debugging row with a %s label" % label
        elif own:
            out.append("%s.own_work: only an AI agent row has own work" % at)
        if writer == "unknown":
            cap = "written by unknown"
        elif writer == "coursework" and r.get("row_type") != "understanding":
            cap = "coursework on a row that is not understanding"
        if cap and cat == "covered":
            out.append("%s.category: covered, but %s; at most shallow" % (at, cap))
    for q in unmapped(result):
        out.append("requirements: no row maps %r" % q)
    return out


def listed_entries(root):
    """The number of lines `tools/entries.py list` prints that start with `entries/`."""
    p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "entries.py"), "list", "--root", root],
                       capture_output=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise FitError("tools/entries.py list: %s" % (p.stdout + p.stderr).strip())
    return sum(1 for l in p.stdout.split("\n") if l.startswith("entries/"))


def count_lines(result, listed, label=None):
    """The `Course work:` and `Map:` lines of a map."""
    cw = [c for c in result.get("course_work") if isinstance(c, str)] if isinstance(result.get("course_work"), list) else []
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    return ["Course work: %s (%d entries listed)" % (", ".join(cw) or "none", listed),
            "Map%s: %d requirements and duties, %d rows; no row: %s"
            % (" (%s)" % label if label else "", len(requirements(result)), len(rows),
               "; ".join(unmapped(result)) or "none")]


def slug(text):
    """A company or role as a file name part: logfiles.ascii_slug (as scan.py names a posting), and,
    when the name holds a character outside ASCII or no letter or digit, the first 8 hex digits of its
    SHA-256 (of its NFC form) after it. Two names that differ only in ASCII punctuation or case
    (`C++ Dev`, `C# Dev`) still share one."""
    text = unicodedata.normalize("NFC", (text or "").strip())
    ascii = logfiles.ascii_slug(text)
    if ascii and text.isascii():
        return ascii
    return "-".join(p for p in (ascii, hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]) if p)


def posting_name(result):
    """`<company>-<role>` of a map file, or None when it lacks either."""
    c, r = (result.get(k) if isinstance(result.get(k), str) else "" for k in ("company", "role"))
    c, r = c.strip(), r.strip()
    return "%s-%s" % (slug(c), slug(r)) if c and r else None


def read_result(path):
    """The one fit result a file holds; FitError naming the problems when it holds none or more."""
    lines = [l for l in logfiles.read_text(path).split("\n") if l.strip()]
    if len(lines) != 1:
        raise FitError("%s: %d lines; a fit result is one JSON object on one line" % (path, len(lines)))
    try:
        return json.loads(lines[0])
    except json.JSONDecodeError as e:
        raise FitError("%s does not parse: %s" % (path, e))


def at_root(root, path):
    return path if os.path.isabs(path) else os.path.join(root, path)


def cmd_check(root, path, capture=None):
    path = at_root(root, path)
    want = None
    if capture:
        capture = at_root(root, capture)
        found = logfiles.urls("\n".join(logfiles.read_text(capture).split("\n")[:3]))
        if not found:
            raise FitError("%s: no URL in its first lines" % capture)
        want = found[0]
    try:
        result = read_result(path)
        bad = problems(result, want)
        if isinstance(result, dict) and "reused" not in result and isinstance(result.get("rows"), list):
            bad += map_problems(root, result)
            lines = count_lines(result, listed_entries(root))
            if result.get("notes") != lines:
                bad.append("notes: must be the lines map prints for it: %s" % json.dumps(lines, ensure_ascii=False))
    except FitError as e:
        bad = [str(e)]
    if bad:
        return 1, ["bad: %s" % b for b in bad]
    return 0, ["check: ok"]


def capture_check(root, path, result):
    """(problem, flag) of the capture map file `path` names: the problem's text when `capture` is
    missing or names no file, else its `flag:` line when the capture is closed, a stand-in's or of an
    unknown read (each None when there is none)."""
    cap = result.get("capture")
    if not isinstance(cap, str) or not cap.strip():
        return "capture: missing; it must be the path of the posting's capture (scan.py capture)", None
    if not os.path.isfile(at_root(root, cap)):
        return "capture: %s is no file" % cap, None
    why = capture_why(root, cap)
    return None, ("flag: %s | capture %s | %s" % (path, cap, why) if why else None)


def capture_why(root, cap):
    """Why the capture at `cap` is flagged (closed, a stand-in's or of an unknown read), or None."""
    import scan   # scan.py imports this module, so not at the top
    st = scan.capture_state(at_root(root, cap))
    why = []
    if st["open"] is False:
        why.append("closed (%s)" % st["why"])
    if st["read"] == "stand-in":
        why.append("read stand-in %s" % st["stand_in"])
    elif st["read"] is None:
        why.append("read unknown (the capture has no read line)")
    return "; ".join(why) or None


def cmd_map(root, paths, several=False, categories=(), save_name=False, today=None, show=False):
    if show and (several or categories or save_name or len(paths) != 1):
        raise FitError("--show takes one map file, with no --several, --category or --save-name")
    listed = listed_entries(root)
    out, bad, results, flags = [], [], [], []
    for path in paths:
        where = "%s: " % path if len(paths) > 1 else ""
        try:
            result = read_result(at_root(root, path))
        except FitError as e:
            bad.append(str(e))
            continue
        shape = problems(result, posting=False)
        if not isinstance(result, dict):
            bad += [where + b for b in shape]
            continue
        rules = map_problems(root, result)
        problem, flag = capture_check(root, path, result)
        rules += [problem] if problem else []
        flags += [flag] if flag else []
        results.append(result)
        label = None
        if several:
            if posting_name(result) and posting_name(result) in [posting_name(r) for r in results[:-1]]:
                rules.append("company, role: another map file of this run gives the same name (%s)" % posting_name(result))
            if posting_name(result):
                label = "%s, %s" % (str(result["company"]).strip(), str(result["role"]).strip())
            else:
                rules.append("company, role: --several needs both in the map file")
        rows = [r for r in result.get("rows") if isinstance(r, dict)] if isinstance(result.get("rows"), list) else []
        if show:
            out += show_block(count_lines(result, listed), rows) + ([""] if flag else [])
        else:
            out += count_lines(result, listed, label) + [""]
            out += table([r for r in rows if not categories or r.get("category") in categories]) + [""]
        bad += [where + b for b in shape + rules]
    if save_name and not bad:
        name = posting_name(results[0]) if len(results) == 1 else None
        if not name:
            bad.append("--save-name: give one map file, with its company and role")
        else:
            day = today or datetime.date.today().isoformat()
            gaps = sum(1 for r in results[0]["rows"] if isinstance(r, dict) and r.get("category") == "gap")
            out += ["save: outputs/reports/%s-fit-posting-%s.md" % (day, name),
                    "commit: fit(%s): %d gaps" % (name, gaps)]
    if bad:
        return 1, out + flags + ["bad: %s" % b for b in bad]
    return 0, out + flags + ["map: ok"]


WEAKEST = ("gap", "claimed, unbacked", "shallow", "covered")


def skill_key(name):
    return " ".join(name.split()).casefold()


def heatmap_rows(results, last):
    """The heatmap's rows (the HEATMAP cells, in their order) of checked map files and screened
    postings (a `rough` one's rows have `entries`, no `category`), as the docstring says, `last` the
    tier of the last target role (ranks())."""
    weights = [last + 1 - r["tier"] if r.get("tier") is not None else 1 for r in results]
    skills = {}   # key -> {"name", "per": {posting index: [rows]}}
    for i, result in enumerate(results):
        for row in result["rows"]:
            s = skills.setdefault(skill_key(row["skill"]), {"name": " ".join(row["skill"].split()), "per": {}})
            s["per"].setdefault(i, []).append(row)
    total = 2 * sum(weights)
    out = []
    for s in skills.values():
        mapped = [r["category"] for i, rows in s["per"].items() if not results[i].get("rough") for r in rows]
        weakest = min(mapped, key=WEAKEST.index) if mapped else "rough"
        rough = [rows for i, rows in s["per"].items() if results[i].get("rough")]
        share = 0.0
        for i, rows in s["per"].items():
            short = [r for r in rows if r.get("category") != "covered"]   # a rough row is never covered
            if short:
                share += weights[i] * (2 if any(r["kind"] != "preferred" for r in short) else 1)
        share /= total
        priority = "-" if weakest == "covered" else next(p for at, p in PRIORITIES if share >= at)
        which = ", ".join("#%d" % (i + 1) for i in sorted(s["per"]))
        touched = sum(1 for rows in rough if any(e.strip() for r in rows for e in r["entries"] if isinstance(e, str)))
        out.append(((["critical", "high", "medium", "low", "-"].index(priority), -share, -len(s["per"]),
                     skill_key(s["name"])),
                    [priority, s["name"], weakest, "%d of %d" % (len(s["per"]), len(results)),
                     "%d (%d touched)" % (len(rough), touched) if rough else "-", which]))
    return [cells for _, cells in sorted(out)]


def ranks(root):
    """The tier of each line of direction.md's Target roles, in order: its place in the list, from 1,
    `GAP:` lines counted (the place a reader sees), mapped to whether the line is a `GAP:` one;
    {} when the roles are empty, as config.py's show reads them."""
    if not config.target_roles(root):
        return {}
    _, _, found = config.item_lines(config.direction_text(root), "target roles")
    return {n: config.is_gap(t) for n, (_, t) in enumerate(found, 1)}


def last_rank(tiers):
    """The tier of the last target role of ranks()'s map, 0 when it holds none."""
    return max((n for n, gap in tiers.items() if not gap), default=0)


def tier_problem(t, tiers):
    """What is wrong with a tier `t` against ranks()'s map, the text after "tier", or None when it is
    null or a target role's place; scan.py's prefilter and Screen result check and heatmap share it."""
    if t is None:
        return None
    last = last_rank(tiers)
    if isinstance(t, bool) or not isinstance(t, int) or t < 1:
        return "must be a whole number from 1, or null"
    if not tiers:
        return "%d, but direction.md's Target roles are empty" % t
    if t > last and len(tiers) == last:
        return "%d, but direction.md lists %d target role(s)" % (t, last)
    if t > last:
        return "%d, but direction.md's last target role is %d" % (t, last)
    if tiers[t]:
        return "%d is the `GAP:` line of direction.md's Target roles, no role" % t
    return None


def legend_line(n, result):
    """The heatmap legend's line for the posting numbered `n` (from 1: the map files in the order
    given, then the screened postings)."""
    return "- #%d %s, %s%s" % (n, result["company"].strip(), result["role"].strip(), " (rough)" if result.get("rough") else "")


def screen_list(path):
    """The run's screen-list.jsonl of a Screen results file (in the run folder's `screen/`), or None
    when the file is not one."""
    folder = os.path.dirname(os.path.abspath(path))
    listed = os.path.join(os.path.dirname(folder), "screen-list.jsonl")
    return listed if os.path.basename(folder) == "screen" and os.path.isfile(listed) else None


def screened_postings(root, paths, tiers, mapped):
    """(postings, bad lines, flag lines) of the Screen results files: each gate yes with rows, as
    `scan.py screen --check` checks it, with its company and role from the run's screen-list.jsonl
    and `rough` set; none whose URL a posting before it (`mapped`, or another result) has, nor whose
    company and role a map file has. A posting whose screen-list.jsonl line names a capture that is
    closed, a stand-in's, of an unknown read or no file gets a flag line."""
    import scan   # scan.py imports this module, so not at the top
    seen = {scan.canonical(r["url"]) for r in mapped if isinstance(r.get("url"), str) and r["url"].strip()}
    names = {posting_name(r) for r in mapped}
    out, bad, flags = [], [], []
    for path in paths:
        full = at_root(root, path)
        try:
            listed = {scan.canonical(p["url"]): p for p in scan.read_jsonl(screen_list(full)) if isinstance(p.get("url"), str)}
        except scan.ScanError as e:
            bad.append("bad: %s" % e)
            continue
        for n, r, why in scan.jsonl_lines(full):
            if why:
                bad.append("bad: %s: line %d %s" % (path, n, why))
                continue
            try:
                scan.check_result(r, "line %d" % n, tiers)
            except scan.ScanError as e:
                bad.append("bad: %s: %s" % (path, e))
                continue
            if r["gate"] != "yes" or not isinstance(r.get("rows"), list):
                continue   # dropped at screen, or reused from a report with no rows
            p = listed.get(scan.canonical(r["url"]))
            if not p:
                bad.append("bad: %s: line %d: %s is on no line of the run's screen-list.jsonl, which gives its "
                           "company and role" % (path, n, r["url"]))
                continue
            posting = {"company": p.get("company"), "role": p.get("role"), "tier": r.get("tier"), "rows": r["rows"], "rough": True}
            if not posting_name(posting):
                bad.append("bad: %s: line %d: %s has no company or role on its screen-list.jsonl line" % (path, n, r["url"]))
                continue
            if scan.canonical(r["url"]) in seen or posting_name(posting) in names:
                continue
            seen.add(scan.canonical(r["url"]))
            out.append(posting)
            cap = p.get("capture")
            if isinstance(cap, str) and cap.strip():
                why = capture_why(root, cap) if os.path.isfile(at_root(root, cap)) else "read unknown (no file)"
                if why:
                    flags.append("flag: %s line %d (rough) | capture %s | %s" % (path, n, cap, why))
    return out, bad, flags


def sample_lines(results):
    """The `Heatmap:` line's sample and the `skew:` line (or none) of the postings."""
    employers = {}
    for r in results:
        employers.setdefault(skill_key(r["company"]), [r["company"].strip(), 0])[1] += 1
    rough = sum(1 for r in results if r.get("rough"))
    sample = "%d postings (%d mapped, %d rough) from %d employers" % (len(results), len(results) - rough, rough, len(employers))
    top = max(employers.values(), key=lambda e: e[1], default=None)
    skew = ["skew: %s holds %d of the %d postings" % (top[0], top[1], len(results))] if top and 2 * top[1] > len(results) else []
    return sample, skew


def cmd_heatmap(root, paths):
    screens = [p for p in paths if screen_list(at_root(root, p))]
    paths = [p for p in paths if p not in screens]
    code, lines = cmd_map(root, paths, several=True) if paths else (0, [])
    bad = [l for l in lines if l.startswith("bad: ")]
    tiers = ranks(root)
    last = last_rank(tiers)
    results = []
    for path in paths:
        try:
            result = read_result(at_root(root, path))
        except FitError:
            continue   # cmd_map's bad: line names it
        if not isinstance(result, dict):
            continue
        result = {k: v for k, v in result.items() if k != "rough"}   # a fit result may copy fit.jsonl's rough share
        results.append(result)
        where = "%s: " % path if len(paths) > 1 else ""
        rows = result.get("rows") if isinstance(result.get("rows"), list) else []
        for i, r in enumerate(rows, 1):
            if isinstance(r, dict) and not isinstance(r.get("skill", ""), str):
                continue   # problems() names it
            if isinstance(r, dict) and not str(r.get("skill") or "").strip():
                bad.append("bad: %srows[%d].skill: heatmap needs the skill's name on every row" % (where, i))
        if "tier" not in result:
            bad.append("bad: %stier: heatmap needs it, a whole number from 1 or null" % where)
            continue
        why = tier_problem(result["tier"], tiers)
        if why:
            bad.append("bad: %stier: %s" % (where, why))
    rough, why, rough_flags = screened_postings(root, screens, tiers, results)
    bad += why
    if bad:
        return 1, bad
    results += rough
    if not results:
        return 1, ["bad: no posting: give a map file, or a Screen result with a gate yes and its rows"]
    rows = heatmap_rows(results, last)
    gaps = sum(1 for r in rows if r[2] == "gap")
    sample, skew = sample_lines(results)
    flags = [l for l in lines if l.startswith("flag: ")] + rough_flags
    out = ["Heatmap: %d skills, %d gaps; weights: %s; %s; flagged: %d of %d" % (len(rows), gaps, "tiers" if any(r.get("tier") is not None for r in results) else "every posting the same", sample, len(flags), len(results))]
    out += skew + [""] + [legend_line(n, r) for n, r in enumerate(results, 1)] + ["", "| " + " | ".join(HEATMAP) + " |", "|" + "---|" * len(HEATMAP)]
    return 0, out + [logfiles.md_row(r) for r in rows] + [""] + flags + ["heatmap: ok"]


def cmd_name(company, role, today=None):
    day = today or datetime.date.today().isoformat()
    return 0, ["map file: .build/fit/%s-%s-%s.jsonl" % (day, slug(company), slug(role))]


def date_arg(value):
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("not a date YYYY-MM-DD: %r" % value)
    return value


def main(argv):
    logfiles.utf8_stdout()
    ap = argparse.ArgumentParser(prog="fit.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("check")
    sp.add_argument("result")
    sp.add_argument("--capture")
    sp = sub.add_parser("map")
    sp.add_argument("files", nargs="+")
    sp.add_argument("--several", action="store_true")
    sp.add_argument("--category", action="append", choices=CATEGORIES, default=[])
    sp.add_argument("--save-name", action="store_true")
    sp.add_argument("--show", action="store_true")
    sp.add_argument("--today", type=date_arg)
    sp = sub.add_parser("heatmap")
    sp.add_argument("files", nargs="+")
    sp = sub.add_parser("name")
    sp.add_argument("company")
    sp.add_argument("role")
    sp.add_argument("--today", type=date_arg)
    try:
        root, argv = logfiles.split_root(argv, __file__)
        a = ap.parse_args(argv)
    except logfiles.LogError as e:
        print("fit: %s" % e)
        return 2
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    root = os.path.abspath(root)
    try:
        if a.cmd == "check":
            code, lines = cmd_check(root, a.result, a.capture)
        elif a.cmd == "map":
            code, lines = cmd_map(root, a.files, a.several, a.category, a.save_name, a.today, a.show)
        elif a.cmd == "heatmap":
            code, lines = cmd_heatmap(root, a.files)
        else:
            code, lines = cmd_name(a.company, a.role, a.today)
    except (FitError, logfiles.LogError, OSError, UnicodeDecodeError) as e:
        print("fit: %s" % e)
        return 1
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
