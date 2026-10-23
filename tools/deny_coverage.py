#!/usr/bin/env python3
"""Check that .export-deny covers every employer and project name the Log records.

  python3 -I <root>/tools/deny_coverage.py [<root>]
  python3 -I <root>/tools/deny_coverage.py line [--to <root>/.export-deny] <name>...
  python3 -I <root>/tools/deny_coverage.py entry [--to <root>/.export-deny] <entry file>...

tools/export-template.sh runs this before it builds the Template, in the Template's source only
(the repo with .export-allow): the export scan catches a Log name in an Engine file only when
.export-deny lists it, and the import, log and consolidate modes append names only as they meet
them.

Names are read from:
- the front matter of each entry (tools/entries.py says which files are entries): `org`; the part
  of `title` before ` — `; each path segment of a GitHub or GitLab URL in `links` (owner, groups,
  repo) that has a letter or digit;
- the Company, Employer, Event / company, Organisation and Institution columns (and their Chinese
  headers) of every table in applications.md, profile.md and outputs/reports/*-ranking.md;
- folder names under outputs/applications/, without the date.

A field holds free text, so it is split at commas, semicolons, parentheses and ` — `, and these
pieces are dropped: quoted text, a piece that says GAP, `personal`, `none`, `n/a`, and a season and
year (`Spring 2031`). In a table cell, prose (lowercase plain words, as in `the open day`) is
dropped too. A leading connector (`sponsored by`, `with`) is cut from a piece.

A name is covered when a .export-deny pattern matches it as the export scan does (whole words,
case-insensitive), or when it is a line of .export-cleared: names the maintainer has decided are
safe in the Template, matched exactly, ignoring case. Neither list is exported. A pattern that
matches only part of a name covers it: `Labs` covers `Acme Labs`.

Prints `OK: .export-deny covers <n> recorded names` (exit 0), or each name it does not cover, with
the file it was found in and, when it differs from the name, the `deny:` line for .export-deny: one
that also matches the name with other ASCII separators, or none unless a run is one character
(`acme-co` and `acmeco` for `Acme & Co`) (exit 1).
`line` prints the deny: line for each name given, one per line, even when it is the name itself. With
--to it also adds each one not already there to that file, in UTF-8 with LF line ends (exit 0;
exit 2 with no name, an empty one, or no such file, and for a name made only of quotes, brackets,
`*`, `@` and backticks, such as `@`, which leaves no line).
`entry` prints the deny: line for each name the given entry files record (as above) that the
.export-deny given by --to (or this script's Log's) and the .export-cleared beside it do not cover;
with --to it also adds them, as `line` does. The log mode runs it on each entry it creates, the
import mode on each entry it creates or changes, and the consolidate mode on each entry it creates
or whose `org`, `title` or `links:` it changes. With nothing to add it prints `OK: ...` (exit 0;
exit 2 with no entry file, one that is not there, or one not in UTF-8).
Exit 2: no .export-deny, one that starts with a byte order mark, a pattern this script cannot read as
grep -E does, or a file not in UTF-8.
Every failure it checks for prints a line that starts with `FAIL:` and says what is wrong (exit 1
puts it above its list of names), except arguments in the wrong form, which print `usage: ...`
(exit 2).
Standard library only, Python 3.11+.
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import entries as entry_files

DENY = ".export-deny"
CLEARED = ".export-cleared"
COLUMNS = {"company", "employer", "event / company", "institution", "organisation",
           "organization", "公司", "雇主", "機構", "學校"}
TABLE_FILES = ("applications.md", "profile.md")
REPORTS = os.path.join("outputs", "reports")
APPLICATIONS = os.path.join("outputs", "applications")

SPLIT = re.compile(r"\s*(?:[,;()、，；（）]| — | – )\s*")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”|「[^」]*」')
PLACEHOLDERS = {"personal", "none", "n/a", "-", "?"}
GAP = re.compile(r"\bGAP\b")
SEASON = re.compile(r"(?i)(?:spring|summer|fall|autumn|winter) \d{4}")
PROSE = re.compile(r"[a-z0-9 '-]* [a-z0-9 '-]*")
CONNECTOR = re.compile(r"^(?:(?:the user was at|sponsored by|built for|with|for|at|on|by|via|from) )+(?=\S)")
URL = re.compile(r"https?://(?:www\.)?(?:github\.com|gitlab\.[^/\s]+)/([^\s,\]#?]+)")
URL_END = {"-", "tree", "blob", "issues", "pulls", "pull", "wiki", "releases", "commit", "commits",
           "tags", "actions", "compare"}
CELL = re.compile(r"(?<!\\)\|")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-")
# grep -E bracket classes, in Python's syntax
POSIX = {"[:alpha:]": "a-zA-Z", "[:digit:]": "0-9", "[:alnum:]": "a-zA-Z0-9", "[:upper:]": "A-Z",
         "[:lower:]": "a-z", "[:space:]": r"\s", "[:blank:]": r" \t", "[:punct:]": r"!-/:-@\[-`{-~",
         "[:xdigit:]": "0-9A-Fa-f", "[:cntrl:]": r"\x00-\x1f\x7f", "[:graph:]": "!-~", "[:print:]": " -~"}
# GNU grep -E escapes Python reads the same way; \< and \> are word edges in grep
SAME_ESCAPES = set("wWsSbB")


class Unreadable(Exception):
    pass


def pieces(value, prose=False):
    """The names in one field's text; prose=True also drops lowercase phrases (table cells)."""
    for piece in SPLIT.split(QUOTED.sub("", value)):
        piece = piece.strip(" *`'\".:@[]")
        if (not re.search(r"[^\W_]", piece) or GAP.search(piece) or piece.lower() in PLACEHOLDERS
                or SEASON.fullmatch(piece) or (prose and PROSE.fullmatch(piece))):
            continue
        yield CONNECTOR.sub("", piece).lstrip("@")


def front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return lines[1:i]
    return []


def unquote(value):
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def repo_segments(value):
    names = []
    for path in URL.findall(value):
        for i, seg in enumerate(path.split("/")):
            if i >= 2 and seg in URL_END:
                break
            seg = re.sub(r"\.git$", "", seg)
            if re.search(r"[^\W_]", seg):   # a segment with no letter or digit (`@`) names nothing
                names.append(seg)
    return names


def entry_names(text):
    names, key = [], None
    for line in front_matter(text):
        m = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2)
        elif re.match(r"\s+- ", line):
            value = line.strip()[2:]
        else:
            continue
        value = unquote(re.sub(r"\s+#.*$", "", value))
        if key == "org":
            names += pieces(value)
        elif key == "title" and " — " in value:
            names += pieces(value.split(" — ")[0])
        elif key == "links":
            names += repo_segments(value)
    return names


def table_names(text):
    """The names in a file's tables, and whether any table had a column this script reads."""
    names, header, read_any = [], None, False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in CELL.split(line.strip("|"))]
        if header is None:
            header = [c.strip("*` ").lower() for c in cells]
            read_any = read_any or any(h in COLUMNS for h in header)
        elif not set("".join(cells)) <= set("-: "):
            for i, h in enumerate(header):
                if h in COLUMNS and i < len(cells):
                    names += pieces(cells[i].replace("\\|", "|"), prose=True)
    return names, read_any


def read(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise Unreadable(f"{path} is not UTF-8 ({e})")


def recorded(root, notes=None):
    """(name, the file it was first found in), each name once, in the order found."""
    found = {}

    def add(names, where):
        for n in names:
            found.setdefault(n.lower(), (n, where))

    for path in entry_files.entry_paths(root):
        add(entry_names(read(os.path.join(root, path))), path)
    reports = os.path.join(root, REPORTS)
    tables = list(TABLE_FILES)
    if os.path.isdir(reports):
        tables += [os.path.join(REPORTS, n) for n in sorted(os.listdir(reports)) if n.endswith("-ranking.md")]
    for rel in tables:
        if os.path.isfile(os.path.join(root, rel)):
            names, read_any = table_names(read(os.path.join(root, rel)))
            add(names, rel.replace(os.sep, "/"))
            if not read_any and notes is not None:
                notes.append(f"note: no table in {rel.replace(os.sep, '/')} has a column this check reads"
                             f" ({', '.join(sorted(COLUMNS))})")
    apps = os.path.join(root, APPLICATIONS)
    for name in sorted(os.listdir(apps)) if os.path.isdir(apps) else []:
        if os.path.isdir(os.path.join(apps, name)) and DATED.sub("", name):
            add([DATED.sub("", name)], "outputs/applications/" + name)
    return list(found.values())


def lines(path):
    if not os.path.isfile(path):
        return []
    out = []
    for line in read(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def compile_pattern(pat):
    """A .export-deny line as the export's `grep -iwE` reads it; re.error for one this cannot match alike."""
    if re.search(r"(?<!\\)\(\?", pat):
        raise re.error("(? is not grep -E syntax")
    for m in re.finditer(r"\\(.)", pat):
        if m.group(1).isalnum() and m.group(1) not in SAME_ESCAPES:
            raise re.error(f"\\{m.group(1)} means something else in grep -E")
    for cls in re.findall(r"\[:[a-z]+:\]", pat):
        if cls not in POSIX:
            raise re.error(f"unknown class {cls}")
    for posix, py in POSIX.items():
        pat = pat.replace(posix, py)
    pat = pat.replace("\\<", r"\b").replace("\\>", r"\b")
    return re.compile(r"(?<!\w)(?:" + pat + r")(?!\w)", re.I)


def uncovered(names, patterns, cleared):
    cleared = {c.lower() for c in cleared}
    return [(n, where) for n, where in names
            if n.lower() not in cleared and not any(p.search(n) for p in patterns)]


def ere_escape(text):
    """The text as a grep -E literal: only its metacharacters escaped, since grep warns on a stray
    backslash (before `-`, `&` or a space)."""
    return re.sub(r"([][\\.(){}*+?|^$])", lambda m: "\\" + m.group(1), text)


def deny_line(name):
    """A .export-deny line for the name: its alphanumeric runs, with any ASCII separator between them
    (or none). Next to a run one character long (`Q&R`), one or more separators, so it does not match
    a plain word (`qr`); after an apostrophe, none needed (`McDonald's`, `mcdonalds`). Wrapping
    quotes, brackets, `*`, `@` and backticks are cut first, as `pieces` cuts them; other punctuation
    before the first run or after the last is dropped (`Yahoo!`, `Yahoo`). A name of one run stays a
    literal when the run is one or two characters (`C++`, `Go!`) or starts with a dot (`.NET`), so it
    is not a common word. `_` is a word character to the scan, so a name with one at an edge gets
    `_*` around a line of two or more runs (`foo_bar_`), and the name itself, escaped, otherwise
    (`_site_`, which `site` would miss)."""
    name = name.strip().strip(" *`'\"@[]()").strip()
    parts = re.split(r"([^\W_]+)", name)   # separator, run, separator, run, ..., separator
    runs, seps = parts[1::2], parts[2:-1:2]
    if len(runs) == 1 and (len(runs[0]) <= 2 or name.startswith(".")):
        return ere_escape(name)
    line = runs[0] if runs else ere_escape(name)
    for prev, sep, run in zip(runs, seps, runs[1:]):
        if sep in ("'", "’"):
            line += "[^[:alnum:]]*"
        else:
            line += "[^[:alnum:]]+" if len(prev) == 1 or len(run) == 1 else "[^[:alnum:]]*"
        line += run
    if not compile_pattern(line).search(name):
        return "_*" + line + "_*" if len(runs) > 1 else ere_escape(name)
    return line


def append_lines(path, new):
    """Add each line the file lacks (ignoring case, as the scan does), as UTF-8 with LF line ends."""
    with open(path, "rb") as f:
        if f.read(3) == b"\xef\xbb\xbf":
            raise Unreadable(f"{path} starts with a byte order mark; save it as UTF-8 without one")
    text = read(path)
    have = {l.strip().lower() for l in text.splitlines()}
    add = [l for l in dict.fromkeys(new) if l.lower() not in have]
    if add:
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(("\n" if text and not text.endswith("\n") else "") + "\n".join(add) + "\n")


def deny_patterns(deny):
    """The lines of a .export-deny, compiled; Unreadable for a file that starts with a byte order mark
    or a line this cannot read as grep -E does."""
    with open(deny, "rb") as f:
        if f.read(3) == b"\xef\xbb\xbf":
            raise Unreadable(f"{DENY} starts with a byte order mark, so the export's scan misreads its"
                             f" first line; save it as UTF-8 without one")
    patterns = []
    for pat in lines(deny):
        try:
            patterns.append(compile_pattern(pat))
        except re.error as e:
            raise Unreadable(f"cannot read the {DENY} pattern {pat!r} as grep -E does ({e})")
    return patterns


def entry_command(args):
    """`entry [--to <.export-deny>] <entry file>...`: the deny: lines the entries' uncovered names need."""
    to = args[1] if args[:1] == ["--to"] and len(args) > 1 else None
    files = args[2:] if to else args
    if not files or any(not f.strip() or f.startswith("-") for f in files):
        print("usage: deny_coverage.py entry [--to <.export-deny>] <entry file>...  (--to first)")
        return 2
    deny = to or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", DENY))
    for path in [deny] + files:
        if not os.path.isfile(path):
            print(f"FAIL: no {path}")
            return 2
    try:
        patterns = deny_patterns(deny)
        cleared = lines(os.path.join(os.path.dirname(os.path.abspath(deny)), CLEARED))
        names = {}
        for path in files:
            for n in entry_names(read(path)):
                names.setdefault(n.lower(), (n, path))
        out, seen = [], set()   # one line per spelling, as the scan ignores case
        for n, _ in uncovered(names.values(), patterns, cleared):
            line = deny_line(n)
            if line and line.lower() not in seen:
                seen.add(line.lower())
                out.append(line)
        if to and out:
            append_lines(to, out)
    except Unreadable as e:
        print(f"FAIL: {e}")
        return 2
    if not out:
        print(f"OK: {DENY} and {CLEARED} cover the {len(names)} names these entries record")
    for line in out:
        print(line)
    return 0


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.rstrip())
        return 0
    if len(argv) > 1 and argv[1] == "line":
        to = argv[3] if argv[2:3] == ["--to"] and len(argv) > 3 else None
        names = argv[4:] if to else argv[2:]
        if not names or any(not n.strip() or n.startswith("-") or re.search(r"[\x00-\x1f\x7f]", n)
                            for n in names):
            print("usage: deny_coverage.py line [--to <.export-deny>] <name>...  (--to first; a name is"
                  " not empty, does not start with -, and has no control character)")
            return 2
        if to and not os.path.isfile(to):
            print(f"FAIL: no {to}")
            return 2
        out = [deny_line(n) for n in names]
        empty = [n for n, line in zip(names, out) if not line]
        if empty:
            print(f"FAIL: no deny: line for {', '.join(repr(n) for n in empty)}: a name made only of"
                  f" quotes, brackets, `*`, `@` and backticks leaves none. Nothing was added.")
            return 2
        if to:
            try:
                append_lines(to, out)
            except Unreadable as e:
                print(f"FAIL: {e}")
                return 2
        for line in out:
            print(line)
        return 0
    if len(argv) > 1 and argv[1] == "entry":
        return entry_command(argv[2:])
    root = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    deny = os.path.join(root, DENY)
    if not os.path.isfile(deny):
        print(f"FAIL: no {DENY} in {root}")
        return 2
    try:
        patterns = deny_patterns(deny)
        notes = []
        names = recorded(root, notes)
        cleared = lines(os.path.join(root, CLEARED))
    except Unreadable as e:
        print(f"FAIL: {e}")
        return 2
    for note in notes:
        print(note)
    missing = uncovered(names, patterns, cleared)
    if not missing:
        print(f"OK: {DENY} covers {len(names)} recorded names")
        return 0
    print(f"FAIL: {DENY} does not cover {len(missing)} name(s) the Log records. Show the user the names."
          f" Add each one's deny: text (the name itself when none is shown) to {DENY} as a new line; for"
          f" a folder under outputs/applications/, or a phrase that names an employer (its event, its"
          f" recruiter), add the employer's name instead. Commit {DENY} on its own straight to the"
          f" default branch and push (AGENTS.md › Sharing). When the export's scan then fails because a"
          f" line you added matches a common word or a tool's name in Engine text, ask the user whether"
          f" to clear that name; on a yes, take its line out of {DENY}, add the name alone to {CLEARED},"
          f" and commit and push both the same way:")
    for name, where in missing:
        line = deny_line(name)
        print(f"  {name}    ({where})" + (f"    deny: {line}" if line != name else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
