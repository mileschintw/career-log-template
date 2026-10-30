#!/usr/bin/env python3
"""Visa sponsorship records: which employers to look up, and the records found, kept and reused
(skills/career-log/modes/fit.md › Sponsorship lookup).

  python3 -I tools/sponsorship.py need [--kinds <kinds>] [--from <file.jsonl>] [--again <employer>]... [<employer>...]   (Windows: py -3 -I ...)
  python3 -I tools/sponsorship.py add <result file>
  python3 -I tools/sponsorship.py show [--kinds <kinds>] [--from <file.jsonl>] [<employer>...]
  python3 -I tools/sponsorship.py wording [--statuses <statuses>] <page file>...

Each takes --root <root>, the Log's root (default: the repo this script is in), anywhere on the line,
and --date YYYY-MM-DD, the day it counts from (default: today), for tests. A relative path argument
is read from the Log's root.

Kinds (KINDS): `lca`, an employer's H-1B LCA records, and `perm`, its PERM labor certification
filings, both from the US Department of Labor's public disclosure data or sites that republish it.
Which a Log looks up is direction.md's `**Visa sponsorship needed:**` line (tools/config.py's visa
sponsorship item): H-1B asks for lca, a green card for perm. --kinds (`lca`, `perm` or `lca,perm`)
takes them from the request instead, for a user who asks with no such line ("does <company>
sponsor?"). OPT and CPT on that line ask for no lookup: no filing says whether a posting takes a
student's work authorisation, so `wording` reads the posting instead.

Employers: two names are one employer when they fold to the same key: lower case, `&` as `and`,
punctuation as spaces, single letters run together (`L.L.C.` is `llc`), a leading `the` and trailing
legal forms (SUFFIXES: Inc, LLC, Ltd, Corp, Co, ...) left out, so `Example Robotics, Inc.` is
`Example Robotics`. Whether a record's filer is this company stays the agent's call (`certain`).

The records: outputs/reports/sponsorship.jsonl (RECORDS), committed with the Log, one JSON object per
line, per employer and kind: `employer` (the name it was looked up as), `kind`, `date` (YYYY-MM-DD,
the day it was looked up) and `records`: one object per record found, `url`, `filer` (the name the
record gives) and `certain` (true only when the filer is certainly this company; a similar name or a
parent company is false); [] is none found. Then these fields (OPTIONAL), which `add` checks and
lines kept before them lack:
  `sources`    the pages read, one object each: `url`, and `name`, the name the page was read for;
               at least one on an answered line, so that a none found still says where it looked
  `data_date`  how recent the source's data is, YYYY-MM or YYYY-MM-DD: the date the page says it was
               updated, else its newest record's; on every answered line
  `parent`     the parent company whose records these are, looked up because the employer's own
               name found none (so the line still says that none were under its own name); a
               line with a parent has records
  `unanswered` why no read answered the line (a page that would not load, or asked for a sign-in);
               its `records` is [], with no data_date or parent, and it is looked up again at the
               next `need`
A record is reused while it is less than REUSE_DAYS days old, then looked up again.

- `need`: the lookups to make for the employers given and those of --from (the `company` of each
  line of a JSONL file, as scan's fit.jsonl), each employer once (the first name given for it). With
  no kind to look up: `lookups: none (<why>)`. Else `lookups: <kinds>`, then for each employer and
  kind `lookup: <employer> | <kind>` (`lookup: <employer> | <kind> | unanswered <date> | <why>` after
  an unanswered line), or `reuse: <employer> | <kind> | <date>` for a record under REUSE_DAYS old,
  then `need: <n> to look up, <m> reused`. Last, while the line names OPT or CPT
  (not with --kinds), `wording: <statuses>`: run `wording` on each posting.
  --again <employer> (repeat it for each employer; it counts as an employer given) looks that
  employer up again, whatever its record's age, when its record is none found under its own name
  (records [], or a parent's records): `lookup: <employer> | <kind> | again <date>`, <date> the
  record's. It is for a legal name or website the user gives after such a none found: the name
  searched is a hint, not a new employer, so the result line's `employer` stays this employer's
  name (the name searched goes in `sources`' `name`), and `add` replaces the record. An --again
  employer whose record has records under its own name, is unanswered, or does not exist prints as
  it would without --again.
- `add`: reads a result file, one JSON object per line, per employer and kind, with these fields
  (each as the records above give it) and no `date`, which `add` sets (--date):
    `employer`   always: the name its `lookup:` line gives
    `kind`       always: `lca` or `perm`
    `records`    always: the records found, [] for none found or unanswered
    `sources`    on an answered line, at least one
    `data_date`  on an answered line
    `parent`     only when the records are a parent company's
    `unanswered` only when no read answered the line (records [], no data_date or parent)
  It checks every line (one `bad: line <n>: <why>` line each, exit 1, writing nothing), then writes
  each into the records dated --date, in place of the one its employer and kind had; an unanswered line
  leaves an answered one in place (`kept: <employer> | <kind> | <its date>, unanswered now`). It prints one
  `added: <employer> | <kind> | <n> record(s)` (or `none found`, or `unanswered`) line each, then `commit:
  sponsorship: <employers>` (the subject when the step commits RECORDS alone), unless every line was kept.
- `wording`: for a line naming OPT or CPT (or --statuses `OPT`, `CPT` or `OPT,CPT`, for a user who
  asks with no such line), the sentences of each page file (a posting's capture, or an employer's
  page saved as text) that may keep out a student on that work authorisation (WORDING): F-1 or J-1
  named as not eligible; unrestricted work authorisation; OPT, CPT or temporary work authorisation
  named as not accepted; authorisation or sponsorship asked for now and in the future. `wording:
  none (<why>)` when the line names neither; else `wording: <statuses>`, then for each file one
  `restricts: <file> | <sentence>` line per sentence found, in its order, or `restricts: <file> |
  none`. The patterns cover common phrasings only: a sentence they miss is still the agent's to read.
- `show`: the records, for the employers as need takes them and the kinds as need finds them:
  `lookups: none (<why>)`, or one line per record, `record: <employer> | <kind> | <date> | <url> |
  <filer> | certain|not certain`; `record: <employer> | <kind> | <date> | none found`; `record:
  <employer> | <kind> | <date> | unanswered | <why>`; or `record: <employer> | <kind> | not looked
  up`. A line with a parent starts with `record: <employer> | <kind> | <date> | none under its own
  name | parent: <parent>`. Each record and none found line ends with `| data: <data_date>` when the
  line has one, and a none found line then with `| <url>` for each source. It prints a record whatever its age (need decides what is
  looked up again).

In each line a `|` inside a name is written `\\|`. Exit 0 on success, 1 when a step refuses (a bad
result line; direction.md unreadable, or the visa sponsorship line's value unknown; RECORDS, --from
or a page file cannot be read, or RECORDS or --from does not parse; no direction.md, or no Constraints section, is no line), 2 on a bad argument. Standard library only, Python 3.11+.
"""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import config, logfiles

RECORDS = "outputs/reports/sponsorship.jsonl"
REUSE_DAYS = 90   # LCA disclosure data is published quarterly
KINDS = {"lca": "H-1B LCA", "perm": "PERM"}
SUFFIXES = {"inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co", "company", "plc",
            "gmbh", "lp", "llp", "ag", "sa", "pbc", "pte", "pty", "bv", "nv"}
FIELDS = ("employer", "kind", "records")
OPTIONAL = ("sources", "data_date", "parent", "unanswered")
RECORD_FIELDS = ("url", "filer", "certain")
STATUSES = ("OPT", "CPT")
# Wording that may keep out a student on OPT or CPT, each found within one sentence. OPT and CPT are
# matched in capitals only, so that "opt out" is not one.
NOT = r"(?:\bnot?\b|\bineligible\b|\bunable\b|\bcannot\b|\bcan't\b|\bwon't\b|\bexclud\w*)"
WORDING = [
    re.compile(r"(?=.*\b[FJ]-?1\s+(?:\S+\s+){0,2}(?:students?|visas?|status|holders?|candidates?|OPT|CPT)\b)(?=.*%s)"
               % NOT, re.I),   # not eligible for F1 and J1 students (not an F1 score)
    re.compile(r"\bunrestricted\s+(?:\w+\s+){0,2}(?:authori[sz]ation|right\s+to\s+work)\b", re.I),
    re.compile(r"(?=.*(?:(?-i:\bOPT\b|\bCPT\b)|\btemporary\s+(?:\w+\s+)?authori[sz]ation\b))(?=.*%s)" % NOT, re.I),
    re.compile(r"(?=.*(?:sponsor|authori[sz]))(?=.*\b(?:now|current(?:ly)?|present(?:ly)?)\s+(?:and|or)\s+"
               r"(?:at\s+any\s+time\s+)?(?:in\s+the\s+)?future\b)", re.I),   # without sponsorship now or in the future
    # sponsorship refused: a negation a few words before it, or `is not available` after it
    re.compile(r"%s(?:\W+\w+){0,5}?\W+sponsor|\bsponsor\w*(?:\W+\w+){0,3}?\W+(?:is|are|will\s+be)\s+(?:not|unavailable)\b"
               % NOT, re.I),
]
# Where a page's text breaks into sentences: after . ! ? (not after e.g., i.e. or U.S.), at a blank
# line, and before a list item.
SENTENCE = re.compile(r"(?<!e\.g\.)(?<!i\.e\.)(?<!U\.S\.)(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])|\n\s*\n"
                      r"|\n(?=\s*(?:[-*•]|\d+[.)])\s)")


class SponsorshipError(Exception):
    pass


def employer_key(name):
    """An employer's name folded for matching (see the module's text)."""
    words = re.sub(r"[^\w\s]", " ", name.lower().replace("&", " and ")).split()
    merged = []
    for w in words:   # L.L.C. -> llc
        if len(w) == 1 and merged and merged[-1][1]:
            merged[-1] = (merged[-1][0] + w, True)
        else:
            merged.append((w, len(w) == 1))
    words = [w for w, _ in merged]
    if len(words) > 1 and words[0] == "the":
        words = words[1:]
    while len(words) > 1 and (words[-1] in SUFFIXES or words[-1] == "and"):   # `& Co.`: its `and` goes too
        words.pop()
    return " ".join(words)


def cell(text):
    return str(text).replace("|", "\\|")


def kinds_for(root, given=None):
    """(the kinds to look up, why there are none): --kinds when given, else direction.md's line."""
    if given is not None:
        return given, None
    try:
        kinds = config.visa_lookups(root)
    except config.ConfigError as e:
        raise SponsorshipError(str(e))
    if kinds:
        return kinds, None
    students, _ = statuses_for(root)
    if students:
        return kinds, ("direction.md's `**Visa sponsorship needed:**` line names only %s, which no filing answers"
                       % " and ".join(students))
    return kinds, "direction.md has no `**Visa sponsorship needed:**` line, or it says none"


def statuses_for(root, given=None):
    """(the statuses whose wording to read, why there are none): --statuses when given, else the line's."""
    if given is not None:
        return given, None
    try:
        found = config.visa_statuses(root)
    except config.ConfigError as e:
        raise SponsorshipError(str(e))
    return found, None if found else "direction.md's `**Visa sponsorship needed:**` line names no OPT or CPT, or there is none"


def parse_statuses(text):
    found = tuple(s.strip().upper() for s in text.split(",") if s.strip())
    if not found or any(s not in STATUSES for s in found) or len(set(found)) < len(found):
        raise ValueError("--statuses is OPT, CPT or OPT,CPT")
    return tuple(s for s in STATUSES if s in found)


def restricting(text):
    """The sentences and list items of a page's text that WORDING finds, in order, each on one line."""
    parts = (re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", " ".join(p.split())) for p in SENTENCE.split(text))
    return [p for p in parts if p and any(w.search(p) for w in WORDING)]


def cmd_wording(root, files, given):
    found, why = statuses_for(root, given)
    if not found:
        return ["wording: none (%s)" % why]
    out = ["wording: %s" % ", ".join(found)]
    for f in files:
        try:
            text = logfiles.read_text(os.path.join(root, f))
        except (OSError, UnicodeDecodeError) as e:
            raise SponsorshipError("%s cannot be read: %s" % (f, e))
        out += ["restricts: %s | %s" % (cell(f), cell(s)) for s in restricting(text)] or ["restricts: %s | none" % cell(f)]
    return out


def parse_kinds(text):
    kinds = tuple(k.strip() for k in text.split(",") if k.strip())
    if not kinds or any(k not in KINDS for k in kinds) or len(set(kinds)) < len(kinds):
        raise ValueError("--kinds is lca, perm or lca,perm")
    return tuple(k for k in KINDS if k in kinds)


def employers(root, names, src=None):
    """The employers, each once, in order: the names given, then --from's `company` fields."""
    names = list(names)
    if src:
        path = os.path.join(root, src)
        try:
            text = logfiles.read_text(path)
        except (OSError, UnicodeDecodeError) as e:
            raise SponsorshipError("%s cannot be read: %s" % (src, e))
        for i, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except ValueError as e:
                raise SponsorshipError("%s line %d does not parse: %s" % (src, i, e))
            if isinstance(item, dict) and isinstance(item.get("company"), str) and item["company"].strip():
                names.append(item["company"].strip())
    out, seen = [], set()
    for n in names:
        k = employer_key(n)
        if k and k not in seen:
            seen.add(k)
            out.append(n)
    return out


def load(root):
    """{(employer key, kind): record object} from RECORDS ({} when it does not exist)."""
    path = os.path.join(root, RECORDS)
    if not os.path.exists(path):
        return {}
    try:
        text = logfiles.read_text(path)
    except (OSError, UnicodeDecodeError) as e:
        raise SponsorshipError("%s cannot be read: %s" % (RECORDS, e))
    out = {}
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError as e:
            raise SponsorshipError("%s line %d does not parse: %s; fix it from git history" % (RECORDS, i, e))
        why = problem(item) or (None if valid_date(item.get("date")) else "date is not a YYYY-MM-DD day")
        if why:
            raise SponsorshipError("%s line %d: %s; fix it from git history" % (RECORDS, i, why))
        out[employer_key(item["employer"]), item["kind"]] = item
    return out


def valid_date(text):
    try:
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", text)) and bool(datetime.date.fromisoformat(text))
    except (TypeError, ValueError):
        return False


def problem(item):
    """Why a result line is not one, or None."""
    if not isinstance(item, dict):
        return "not a JSON object"
    extra = sorted(set(item) - set(FIELDS) - set(OPTIONAL) - {"date"})
    if extra:
        return "unknown field %s" % ", ".join(extra)
    if not isinstance(item.get("employer"), str) or not employer_key(item["employer"]):
        return "employer is the employer's name"
    if item.get("kind") not in KINDS:
        return "kind is %s" % " or ".join(KINDS)
    if not isinstance(item.get("records"), list):
        return "records is a list ([] for none found)"
    for n, r in enumerate(item["records"], 1):
        if not isinstance(r, dict) or set(r) != set(RECORD_FIELDS):
            return "record %d has exactly %s" % (n, ", ".join(RECORD_FIELDS))
        if not isinstance(r["url"], str) or not re.match(r"^https?://\S+$", r["url"]):
            return "record %d's url is the record's http(s) URL" % n
        if not isinstance(r["filer"], str) or not r["filer"].strip():
            return "record %d's filer is the name the record gives" % n
        if not isinstance(r["certain"], bool):
            return "record %d's certain is true or false" % n
    sources = item.get("sources", [])
    if not isinstance(sources, list):
        return "sources is a list of the pages read"
    for n, src in enumerate(sources, 1):
        if not isinstance(src, dict) or set(src) != {"url", "name"} or not isinstance(src["url"], str) \
                or not re.match(r"^https?://\S+$", src["url"]) or not isinstance(src["name"], str) or not src["name"].strip():
            return "source %d has exactly url (the page's http(s) URL) and name (the name it was read for)" % n
    if "data_date" in item and not (isinstance(item["data_date"], str) and (
            valid_date(item["data_date"]) or re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", item["data_date"]))):
        return "data_date is YYYY-MM or YYYY-MM-DD"
    if "parent" in item and (not isinstance(item["parent"], str) or not employer_key(item["parent"])):
        return "parent is the parent company's name"
    if "parent" in item and not item["records"] and "unanswered" not in item:
        return "a line with a parent holds the parent's records (with none found under either, leave parent out)"
    if "unanswered" in item:
        if not isinstance(item["unanswered"], str) or not item["unanswered"].strip():
            return "unanswered says why no read answered the line"
        if item["records"] or "data_date" in item or "parent" in item:
            return "an unanswered line has records [], and no data_date or parent"
    return None


def missing(item):
    """What `add` asks of a result line beyond problem(): an answered line's sources and data_date."""
    if "unanswered" in item:
        return None
    if not item.get("sources"):
        return "sources names the pages read (a none found's too), or the line is unanswered"
    if "data_date" not in item:
        return "data_date is how recent the source's data is (YYYY-MM or YYYY-MM-DD)"
    return None


def age(record, date):
    return (date - datetime.date.fromisoformat(record["date"])).days


def cmd_need(root, date, names, src, given, again=()):
    kinds, why = kinds_for(root, given)
    wording = [] if given is not None else ["wording: %s" % ", ".join(s) for s in [statuses_for(root)[0]] if s]
    if not kinds:
        return ["lookups: none (%s)" % why] + wording
    have, out, todo, reused = load(root), ["lookups: %s" % ", ".join(kinds)], 0, 0
    redo = {employer_key(n) for n in again}
    for name in employers(root, list(names) + list(again), src):
        for kind in kinds:
            r = have.get((employer_key(name), kind))
            if r and "unanswered" in r:
                out.append("lookup: %s | %s | unanswered %s | %s" % (cell(name), kind, r["date"], cell(r["unanswered"])))
                todo += 1
            elif r and employer_key(name) in redo and (not r["records"] or "parent" in r):
                out.append("lookup: %s | %s | again %s" % (cell(name), kind, r["date"]))
                todo += 1
            elif r and age(r, date) < REUSE_DAYS:
                out.append("reuse: %s | %s | %s" % (cell(name), kind, r["date"]))
                reused += 1
            else:
                out.append("lookup: %s | %s" % (cell(name), kind))
                todo += 1
    return out + ["need: %d to look up, %d reused" % (todo, reused)] + wording


def cmd_add(root, date, src):
    try:
        text = logfiles.read_text(os.path.join(root, src))
    except (OSError, UnicodeDecodeError) as e:
        raise SponsorshipError("%s cannot be read: %s" % (src, e))
    items, bad, seen = [], [], set()
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError as e:
            bad.append("bad: line %d: does not parse: %s" % (i, e))
            continue
        why = problem(item) or missing(item)
        if not why and "date" in item:
            why = 'remove "date": add sets it (--date, default today)'
        if not why and (employer_key(item["employer"]), item["kind"]) in seen:
            why = "%s | %s is on an earlier line" % (item["employer"], item["kind"])
        if why:
            bad.append("bad: line %d: %s" % (i, why))
            continue
        seen.add((employer_key(item["employer"]), item["kind"]))
        items.append(item)
    if bad or not items:
        return 1, bad or ["bad: %s holds no result line" % src]
    have = load(root)
    out, names = [], []
    for item in items:
        k = employer_key(item["employer"])
        old = have.get((k, item["kind"]))
        if "unanswered" in item and old and "unanswered" not in old:   # an answer, however old, beats none
            out.append("kept: %s | %s | %s, unanswered now" % (cell(item["employer"].strip()), item["kind"], old["date"]))
            continue
        have[k, item["kind"]] = dict({"employer": item["employer"].strip(), "kind": item["kind"],
                                      "date": date.isoformat(), "records": item["records"]},
                                     **{f: item[f] for f in OPTIONAL if f in item})
        n = len(item["records"])
        out.append("added: %s | %s | %s" % (cell(item["employer"].strip()), item["kind"], "unanswered" if "unanswered" in item
                                            else "%d record(s)" % n if n else "none found"))
        if item["employer"].strip() not in names:
            names.append(item["employer"].strip())
    if not names:
        return 0, out   # nothing changed: nothing to commit
    lines = [json.dumps(have[k], ensure_ascii=False) for k in sorted(have, key=lambda k: (k[0], list(KINDS).index(k[1])))]
    path = os.path.join(root, RECORDS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logfiles.write_text(path, "\n".join(lines) + "\n")
    subject = ", ".join(names[:3]) + (" and %d more" % (len(names) - 3) if len(names) > 3 else "")
    return 0, out + ["commit: sponsorship: %s" % subject]


def records(root, names, src=None, given=None):
    """(kinds, why none, [(employer, kind, record object or None)])."""
    kinds, why = kinds_for(root, given)
    if not kinds:
        return kinds, why, []
    have = load(root)
    return kinds, None, [(n, k, have.get((employer_key(n), k))) for n in employers(root, names, src) for k in kinds]


def cmd_show(root, names, src, given):
    kinds, why, found = records(root, names, src, given)
    if not kinds:
        return ["lookups: none (%s)" % why]
    out = []
    for name, kind, r in found:
        head = "record: %s | %s" % (cell(name), kind)
        if r is None:
            out.append(head + " | not looked up")
            continue
        if "unanswered" in r:
            out.append(head + " | %s | unanswered | %s" % (r["date"], cell(r["unanswered"])))
            continue
        data = " | data: %s" % r["data_date"] if "data_date" in r else ""
        if "parent" in r:
            out.append(head + " | %s | none under its own name | parent: %s" % (r["date"], cell(r["parent"])))
        if not r["records"]:
            out.append(head + " | %s | none found%s%s" % (r["date"], data,
                                                        "".join(" | " + cell(s["url"]) for s in r.get("sources", []))))
        for x in r["records"]:
            out.append(head + " | %s | %s | %s | %s%s" % (r["date"], cell(x["url"]), cell(x["filer"]),
                                                          "certain" if x["certain"] else "not certain", data))
    return out


def report_lines(root, names):
    """A scan report's `## Sponsorship records` section for the employers fitted, each once; [] when
    direction.md asks for no lookup."""
    try:
        kinds, _, found = records(root, names)
    except SponsorshipError as e:
        return ["## Sponsorship records", "", "Not read: %s." % str(e).rstrip("."), ""]
    if not kinds:
        return []
    out = ["## Sponsorship records", "",
           "%s for each employer fitted: something to check, never a gate; no filings is no proof either way."
           % " and ".join(KINDS[k] for k in kinds), "",
           "| Employer | Kind | Looked up | Data as of | Record | Filer | Filer certain |", "|---|---|---|---|---|---|---|"]
    for name, kind, r in found:
        if r is None:
            out.append("| %s | %s | - | - | not looked up | - | - |" % (cell(name), KINDS[kind]))
            continue
        head = "| %s | %s | %s | %s" % (cell(name), KINDS[kind], r["date"], r.get("data_date", "-"))
        if "unanswered" in r:
            out.append(head + " | unanswered: %s | - | - |" % cell(r["unanswered"]))
        elif "parent" in r:
            out.append(head + " | none under its own name; parent: %s | - | - |" % cell(r["parent"]))
        elif not r["records"]:
            out.append(head + " | none found | - | - |")
        for x in r["records"]:
            out.append(head + " | %s | %s | %s |" % (cell(x["url"]), cell(x["filer"]), "yes" if x["certain"] else "no"))
    return out + [""]


def unrecorded(root, names, date):
    """[(employer, kind)] with no record under REUSE_DAYS old, for the kinds direction.md asks for (an
    unanswered line is one: it says the lookup was made)."""
    if not names:
        return []
    _, _, found = records(root, names)
    return [(n, k) for n, k, r in found if r is None or age(r, date) >= REUSE_DAYS]


def unanswered(root, names, date):
    """[(employer, kind, why)] whose record under REUSE_DAYS old is unanswered (an older one is
    unrecorded's), for the kinds direction.md asks for."""
    if not names:
        return []
    _, _, found = records(root, names)
    return [(n, k, r["unanswered"]) for n, k, r in found if r and "unanswered" in r and age(r, date) < REUSE_DAYS]


def main(argv):
    logfiles.utf8_stdout()
    usage = ("usage: sponsorship.py need [--kinds <kinds>] [--from <file>] [--again <employer>]... [<employer>...] | add <result file>"
             " | show [--kinds <kinds>] [--from <file>] [<employer>...] | wording [--statuses <statuses>] <page file>..."
             "  [--root <root>] [--date YYYY-MM-DD]")
    if "-h" in argv or "--help" in argv:
        print(__doc__.rstrip())
        return 0
    try:
        root, args = logfiles.split_root(argv, __file__)
    except logfiles.LogError as e:
        print("sponsorship: %s" % e)
        return 2
    opts, again = {}, []
    rest = []
    it = iter(args)
    for a in it:
        name, eq, value = a.partition("=")
        if name == "--again":   # once per employer: a name may hold a comma
            value = value if eq else next(it, None)
            if not value or not value.strip() or not eq and value.startswith("--"):
                print(usage)
                return 2
            again.append(value.strip())
        elif name in ("--kinds", "--from", "--date", "--statuses"):
            value = value if eq else next(it, None)
            if not value or name in opts:
                print(usage)
                return 2
            opts[name] = value
        elif a.startswith("--"):
            print(usage)
            return 2
        else:
            rest.append(a)
    try:
        date = datetime.date.fromisoformat(opts["--date"]) if "--date" in opts else datetime.date.today()
        given = parse_kinds(opts["--kinds"]) if "--kinds" in opts else None
        statuses = parse_statuses(opts["--statuses"]) if "--statuses" in opts else None
    except ValueError as e:
        print("sponsorship: %s" % e)
        return 2
    if not rest or rest[0] not in ("need", "add", "show", "wording") \
            or (rest[0] == "add" and (len(rest) != 2 or opts.keys() - {"--date"})) \
            or (rest[0] == "wording" and (len(rest) == 1 or opts.keys() - {"--date", "--statuses"})) \
            or (rest[0] != "need" and again)             or (rest[0] in ("need", "show") and ("--statuses" in opts or len(rest) == 1 and "--from" not in opts and not again)):
        print(usage)
        return 2
    root = os.path.abspath(root)
    try:
        if rest[0] == "need":
            code, lines = 0, cmd_need(root, date, rest[1:], opts.get("--from"), given, again)
        elif rest[0] == "wording":
            code, lines = 0, cmd_wording(root, rest[1:], statuses)
        elif rest[0] == "show":
            code, lines = 0, cmd_show(root, rest[1:], opts.get("--from"), given)
        else:
            code, lines = cmd_add(root, date, rest[1])
    except SponsorshipError as e:
        print("sponsorship: %s" % e)
        return 1
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
