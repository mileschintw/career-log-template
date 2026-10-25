#!/usr/bin/env python3
"""Check that .export-deny covers every employer and project name the Log records.

  python3 -I <root>/tools/deny_coverage.py [--root <root>]
  python3 -I <root>/tools/deny_coverage.py line [--root <root>] [--to <root>/.export-deny] [--commit] <name>...
  python3 -I <root>/tools/deny_coverage.py entry [--root <root>] [--to <root>/.export-deny] [--commit] <entry file>...
  python3 -I <root>/tools/deny_coverage.py clear [--root <root>] <name>

<root> is the Log's root, by default the folder above this script's.

tools/export-template.sh runs this before it builds the Template, in the Template's source only
(the repo with .export-allow): the export scan catches a Log name in an Engine file only when
.export-deny lists it, and the import, log and consolidate modes append names only as they meet
them.

Names are read from:
- the front matter of each entry (tools/entries.py says which files are entries): `org`; `title`:
  the part before ` — `, and a title with no ` — ` as one name, unsplit, only when `org` is
  missing or empty or each of its items is `personal` or a GAP with no name beside it (`none`
  and `n/a` do not count); each path segment of a GitHub or GitLab URL in `links` (owner, groups, repo) that has
  a letter or digit. Each value and each list item (inline `[a, "b, c"]` or `  - a`)
  is read as logfiles.front_matter reads it: a quoted one whole, `#` included (`"Acme #1 Labs"`),
  an unquoted one up to a ` #` comment;
- the Company, Employer, Event / company, Organisation and Institution columns (and their Chinese
  headers) of every table in applications.md, profile.md and outputs/reports/*-ranking.md;
- folder names under outputs/applications/, without the date.

A field holds free text, so it is split at commas, semicolons, parentheses and ` — `, except an
`org` value or list item written in quotes (`"Acme, Inc"`) and a title read whole, each one name.
These pieces are dropped: quoted text inside a field, a piece that says GAP, `personal`, `none`,
`n/a`, and a season and year (`Spring 2031`). In a table cell, prose (lowercase plain words, as in
`the open day`) is dropped too. A leading connector (`sponsored by`, `with`) is cut from a piece.

A name is covered when a .export-deny pattern matches it as the export scan does (whole words,
case-insensitive), or when it is a line of .export-cleared: names the maintainer has decided are
safe in the Template, matched exactly, ignoring case. Neither list is exported. A pattern that
matches only part of a name covers it: `Labs` covers `Acme Labs`.

Prints `OK: .export-deny covers <n> recorded names` (exit 0), or a `FAIL:` line, each name it does
not cover, indented, with the file it was found in and, when it differs from the name, the `deny:`
line for .export-deny: one that also matches the name with other ASCII separators, or none unless a
run is one character (`acme-co` and `acmeco` for `Acme & Co`); then a `run:` line, `line --commit`
with those names (one more for the names that are folders under outputs/applications/, whose
employer goes in its place), and how to clear a name (exit 1).
`line` prints the deny: line for each name given, one per line, even when it is the name itself. With
--to it also adds each one not already there to that file, in UTF-8 with LF line ends (exit 0;
exit 2 with no name, an empty one, or no such file, and for a name made only of quotes, brackets,
`*`, `@` and backticks, such as `@`, which leaves no line).
`entry` prints the deny: line for each name the given entry files record (as above) that the
.export-deny given by --to (or <root>'s) and the .export-cleared beside it do not cover; a relative
<entry file> such as `entries/2031-04-widget.md` that is not a file from the current folder is read
against <root>; with --to it also adds them, as `line` does. The log mode runs it on each entry it
creates, the import mode on each entry it creates or changes, and the consolidate mode on each entry
it creates or whose `org`, `title` or `links:` it changes. With nothing to add it prints `OK: ...`
(exit 0; exit 2 with no entry file, one that is not there, or one not in UTF-8).
--commit (`line`, `entry`): adds the lines to <root>'s .export-deny (--to may name only that file),
then commits that file alone and pushes it through tools/sync.py commit, whose lines it prints after
its own: subject `export-deny: names from <entry file names, comma-separated>` (`entry`) or
`export-deny: add <names>` (`line`), or `<n> entries` / `<n> names` for more than three. The last
line is sync.py's: `sync: ok` (exit 0) or a `next: stop:` line (exit 1). With nothing to add it
prints `OK: ...` and commits nothing.
`clear` moves a name the user cleared for export: it adds the name alone to .export-cleared and
commits and pushes that file (`export-cleared: <name>`), and only then takes out the .export-deny
lines that are the name or its deny: line and commits that file (`export-deny: clear <name>`), so
every commit pushed covers the name. A recorded name that only the removed line covered gets its own
deny: line in that commit (`kept covered: <line>`), or a `note:` to ask the user about clearing it
too when that line would match the cleared name. It prints sync.py's lines for each commit, and a
`note:` when another .export-deny line still matches the name; it ends as sync.py does (exit 0 or
1). Run again after it stopped, it commits and pushes what is left. When no line is the name or its
deny: line and the name is not in .export-cleared, it prints a `FAIL:` line naming the lines that
match it and changes nothing (exit 2), or, when no line matches it and the Log records it, only adds
it to .export-cleared and commits that; when the name is cleared already and nothing is left to commit
or push, `OK: ...` (exit 0).
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
import logfiles
# Moved to logfiles.py; kept here under their old names
from logfiles import URL_END, repo_segments

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
# grep -E bracket classes, in Python's syntax
POSIX = {"[:alpha:]": "a-zA-Z", "[:digit:]": "0-9", "[:alnum:]": "a-zA-Z0-9", "[:upper:]": "A-Z",
         "[:lower:]": "a-z", "[:space:]": r"\s", "[:blank:]": r" \t", "[:punct:]": r"!-/:-@\[-`{-~",
         "[:xdigit:]": "0-9A-Fa-f", "[:cntrl:]": r"\x00-\x1f\x7f", "[:graph:]": "!-~", "[:print:]": " -~"}
# GNU grep -E escapes Python reads the same way; \< and \> are word edges in grep
SAME_ESCAPES = set("wWsSbB")


class Unreadable(Exception):
    pass


def pieces(value, prose=False, whole=False):
    """The names in one field's text; prose=True also drops lowercase phrases (table cells), and
    whole=True reads the text as one name, unsplit (a quoted value)."""
    for piece in [value] if whole else SPLIT.split(QUOTED.sub("", value)):
        piece = piece.strip(" *`'\".:@[]")
        if (not re.search(r"[^\W_]", piece) or GAP.search(piece) or piece.lower() in PLACEHOLDERS
                or SEASON.fullmatch(piece) or (prose and PROSE.fullmatch(piece))):
            continue
        yield CONNECTOR.sub("", piece).lstrip("@")


def no_org(items):
    """Whether an entry's `org` items name no one: none at all, or each one `personal` or a GAP."""
    return all(value.strip(" *`'\"").lower() in ("", "personal")
               or (GAP.search(value) and not list(pieces(value, whole=quoted)))
               for key, value, quoted in items if key == "org")


def entry_names(text):
    items = logfiles.front_matter_items(text, closed=True)
    whole_title = no_org(items)
    names = []
    for key, value, quoted in items:
        if key == "org":
            names += pieces(value, whole=quoted)
        elif key == "title" and " — " in value:
            names += pieces(value.split(" — ")[0])
        elif key == "title" and whole_title:
            names += pieces(value, whole=True)
        elif key == "links":
            names += repo_segments(value)
    return names


def table_names(text):
    """The names in a file's tables, and whether any table had a column this script reads."""
    names, read_any = [], False
    for table in logfiles.md_tables(text):
        read_any = read_any or any(h in COLUMNS for h in table.header)
        for _, cells in table.rows:
            for i, h in enumerate(table.header):
                if h in COLUMNS and i < len(cells):
                    names += pieces(cells[i], prose=True)
    return names, read_any


def read(path):
    try:
        return logfiles.read_text(path)
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
        rest = logfiles.split_dated(name)[1]
        if os.path.isdir(os.path.join(apps, name)) and rest:
            add([rest], "outputs/applications/" + name)
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
    """Add each line the file lacks (ignoring case, as the scan does), as UTF-8 with LF line ends; the
    lines added."""
    with open(path, "rb") as f:
        if f.read(3) == b"\xef\xbb\xbf":
            raise Unreadable(f"{path} starts with a byte order mark; save it as UTF-8 without one")
    text = read(path)
    have = {l.strip().lower() for l in text.splitlines()}
    add = [l for l in dict.fromkeys(new) if l.lower() not in have]
    if add:
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(("\n" if text and not text.endswith("\n") else "") + "\n".join(add) + "\n")
    return add


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


def options(args):
    """(the --to file or None, whether --commit was given, the rest), from options before the rest."""
    to, commit = None, False
    while args[:1] == ["--commit"] or (args[:1] == ["--to"] and len(args) > 1 and args[1].strip() and to is None):
        if args[0] == "--commit":
            commit, args = True, args[1:]
        else:
            to, args = args[1], args[2:]
    return to, commit, args


def root_deny(deny, root):
    return os.path.normcase(os.path.abspath(deny)) == os.path.normcase(os.path.abspath(os.path.join(root, DENY)))


def listed(items, many):
    """Up to three items, comma-separated, or `<n> <many>`: a commit subject's tail."""
    return ", ".join(items) if len(items) <= 3 else f"{len(items)} {many}"


def commit(root, subject, path):
    """Commit and push the one file through sync.py, which prints its own lines; its exit code."""
    import sync
    return sync.main(["sync.py", "--root", root, "commit", subject, "--", path])


def entry_command(args, root):
    """`entry [--to <.export-deny>] [--commit] <entry file>...`: the deny: lines the entries' uncovered
    names need."""
    to, commit_too, files = options(args)
    if (not files or any(not f.strip() or f.startswith("-") for f in files)
            or (commit_too and to and not root_deny(to, root))):
        print("usage: deny_coverage.py entry [--root <root>] [--to <.export-deny>] [--commit] <entry file>..."
              "  (options first; --commit writes <root>'s .export-deny only)")
        return 2
    deny = to or os.path.join(root, DENY)
    # A relative path that is no file from the current folder is read against root, as entries.py does
    files = [f if os.path.isabs(f) or os.path.isfile(f) or not os.path.isfile(os.path.join(root, f))
             else os.path.join(root, f) for f in files]
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
        if (to or commit_too) and out:
            append_lines(deny, out)
    except Unreadable as e:
        print(f"FAIL: {e}")
        return 2
    if not out:
        print(f"OK: {DENY} and {CLEARED} cover the {len(names)} names these entries record")
    for line in out:
        print(line)
    if commit_too and out:
        names = [os.path.basename(f) for f in dict.fromkeys(files)]
        return commit(root, f"export-deny: names from {listed(names, 'entries')}", DENY)
    return 0


def line_command(args, root):
    """`line [--to <.export-deny>] [--commit] <name>...`: each name's deny: line."""
    to, commit_too, names = options(args)
    if (not names or any(not n.strip() or n.startswith("-") or re.search(r"[\x00-\x1f\x7f]", n) for n in names)
            or (commit_too and to and not root_deny(to, root))):
        print("usage: deny_coverage.py line [--root <root>] [--to <.export-deny>] [--commit] <name>...  (options"
              " first; --commit writes <root>'s .export-deny only; a name is not empty, does not start with -,"
              " and has no control character)")
        return 2
    deny = to or (os.path.join(root, DENY) if commit_too else None)
    if deny and not os.path.isfile(deny):
        print(f"FAIL: no {deny}")
        return 2
    out = [deny_line(n) for n in names]
    empty = [n for n, line in zip(names, out) if not line]
    if empty:
        print(f"FAIL: no deny: line for {', '.join(repr(n) for n in empty)}: a name made only of"
              f" quotes, brackets, `*`, `@` and backticks leaves none. Nothing was added.")
        return 2
    added = []
    if deny:
        try:
            added = append_lines(deny, out)
        except Unreadable as e:
            print(f"FAIL: {e}")
            return 2
    for line in out:
        print(line)
    if commit_too and not added:
        print(f"OK: {DENY} has every line already; nothing to commit")
    elif commit_too:
        return commit(root, f"export-deny: add {listed(list(dict.fromkeys(names)), 'names')}", DENY)
    return 0


def clear_command(args, root):
    """`clear <name>`: the name moves from .export-deny to .export-cleared, one commit for each file."""
    if len(args) != 1 or not args[0].strip() or args[0].startswith("-") or re.search(r"[\x00-\x1f\x7f]", args[0]):
        print("usage: deny_coverage.py clear [--root <root>] <name>  (one name: not empty, does not start"
              " with -, and has no control character)")
        return 2
    name = args[0].strip()
    deny, cleared = os.path.join(root, DENY), os.path.join(root, CLEARED)
    if not os.path.isfile(deny):
        print(f"FAIL: no {DENY} in {root}")
        return 2
    try:
        patterns = deny_patterns(deny)
        text = read(deny)
        mine = {name.lower(), ere_escape(name).lower(), (deny_line(name) or name).lower()}
        keep = [l for l in text.splitlines(keepends=True) if l.strip().lower() not in mine]
        if len(keep) == len(text.splitlines(keepends=True)):
            if name.lower() in {c.lower() for c in lines(cleared)}:
                if not pending(root):
                    print(f"OK: {name} is in {CLEARED} and has no {DENY} line; nothing to commit")
                    return 0
                # cleared before, and its line already out: a commit or push that stopped then
                rc = commit(root, f"export-cleared: {name}", CLEARED)
                return rc if rc != 0 else commit(root, f"export-deny: clear {name}", DENY)
            matching = [p for p, c in zip(lines(deny), patterns) if c.search(name)]
            if not matching and name.lower() in {n.lower() for n, _ in recorded(root)}:
                # no line denies it: a spelling the clearing of another name left uncovered (`Yahoo!`)
                if os.path.isfile(cleared):
                    append_lines(cleared, [name])
                else:
                    logfiles.write_text(cleared, name + "\n")
                return commit(root, f"export-cleared: {name}", CLEARED)
            print(f"FAIL: no {DENY} line is {name!r} or its deny: line {deny_line(name)!r}"
                  + (f"; the lines that match it: {', '.join(matching)}" if matching else ", and the Log records"
                     " no such name") + ". Nothing was changed.")
            return 2
        # a name the removed line covered stays covered, by its own deny: line
        left = [compile_pattern(l.strip()) for l in keep if l.strip() and not l.strip().startswith("#")]
        was = {n.lower() for n, _ in uncovered(recorded(root), patterns, lines(cleared))}
        lost = [n for n, _ in uncovered(recorded(root), left, lines(cleared) + [name]) if n.lower() not in was]
        cover, also = [], []   # a line that matches the cleared name would deny it again
        for n in lost:
            line = deny_line(n)
            if line and line.lower() not in mine and not compile_pattern(line).search(name):
                cover.append(line)
            else:
                also.append(n)
        cover = list(dict.fromkeys(cover))
        if os.path.isfile(cleared):
            append_lines(cleared, [name])
        else:
            logfiles.write_text(cleared, name + "\n")
    except Unreadable as e:
        print(f"FAIL: {e}")
        return 2
    # .export-cleared first, so that every commit pushed covers the name
    rc = commit(root, f"export-cleared: {name}", CLEARED)
    if rc != 0:
        return rc
    body = "".join(keep)
    logfiles.write_text(deny, body + ("\n" if body and not body.endswith("\n") else "") + "".join(l + "\n" for l in cover))
    for line in cover:
        print(f"kept covered: {line}")
    for n in also:
        print(f"note: {n!r} is no longer covered, and its deny: line would match {name!r}: ask the user"
              f" whether to clear it too (clear {logfiles.shell_arg(n)})")
    still = [p for p, c in zip(lines(deny), deny_patterns(deny)) if c.search(name)]
    if still:
        print(f"note: {DENY} still has {', '.join(still)}, which the export's scan matches against {name!r} too")
    return commit(root, f"export-deny: clear {name}", DENY)


def pending(root):
    """Whether .export-deny or .export-cleared differs from HEAD, or HEAD is not on its upstream."""
    if logfiles.git_run(root, "status", "--porcelain", "--", DENY, CLEARED).stdout.strip():
        return True
    p = logfiles.git_run(root, "rev-list", "--count", "@{upstream}..HEAD")
    return p.returncode != 0 or p.stdout.strip() != "0"


def main(argv):
    logfiles.utf8_stdout()
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.rstrip())
        return 0
    try:
        root, argv = logfiles.split_root(argv[1:], __file__)
    except logfiles.LogError as e:
        print(f"usage: deny_coverage.py [--root <root>]: {e}")
        return 2
    argv = ["deny_coverage.py"] + argv
    commands = {"line": line_command, "entry": entry_command, "clear": clear_command}
    if len(argv) > 1 and argv[1] in commands:
        return commands[argv[1]](argv[2:], root)
    if len(argv) > 1:
        print("usage: deny_coverage.py [--root <root>] | line [--to <.export-deny>] [--commit] <name>... |"
              " entry [--to <.export-deny>] [--commit] <entry file>... | clear <name>  (each takes --root"
              " <root>; the Log's root is given with --root, not on its own)")
        return 2
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
    script = os.path.abspath(__file__).replace(os.sep, "/")
    run = f"{logfiles.python_cmd()} -I {logfiles.shell_arg(script)} --root {logfiles.shell_arg(os.path.abspath(root).replace(os.sep, '/'))}"
    folders = [n for n, where in missing if where.startswith(APPLICATIONS.replace(os.sep, "/") + "/")]
    print(f"FAIL: {DENY} does not cover {len(missing)} name(s) the Log records. Show the user the names"
          f" below, then run each run: line below, which adds the names' deny: lines to {DENY} and commits"
          f" and pushes it. Before running one, put the employer's own name in place of a name that is a"
          f" phrase naming an employer (its event, its recruiter)"
          + (", and add the employer's name for each folder under outputs/applications/." if folders else "."))
    for name, where in missing:
        line = deny_line(name)
        print(f"  {name}    ({where})" + (f"    deny: {line}" if line != name else ""))
    rest = [n for n, _ in missing if n not in folders]
    if rest:
        print(f"run: {run} line --commit {' '.join(logfiles.shell_arg(n) for n in rest)}")
    if folders:
        print(f"run: {run} line --commit '<employer>'   (for each folder: {', '.join(folders)})")
    print(f"When the export's scan then fails because a line added matches a common word or a tool's"
          f" name in Engine text, ask the user whether to clear that name; on a yes, run: {run} clear"
          f" '<name>', which moves it from {DENY} to {CLEARED} and commits each.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
