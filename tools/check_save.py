#!/usr/bin/env python3
"""Print write step 10's checks on a saved output, before its commit (skills/career-log/modes/write.md).

  python3 -I tools/check_save.py <saved> ... [--humanizer <file> | --humanizer none]

<saved> is an application folder (outputs/applications/<folder>/, whose provenance.md is read) or a
saved provenance file (outputs/resumes/<target>.md, outputs/reports/<file>.md), inside a Log.

For each provenance file it prints
  Provenance check (<file>): <n> rows; citing another output: <none, or each such row>
with <file> its path from the Log root and <n> its table's row count. A provenance table is one with
an "entry" or "source" column; tables under `## Company context` and `## Risks...` are not read.
A row is listed when:
- its entry section (the first column whose header says "entry") names a `.md` file other than an
  entry, profile.md or direction.md (`stories.md`, `outputs/x.md`), source citations set aside; a
  path is read from the Log root, from entries/, or from the provenance file's folder (a link such
  as `../../entries/x.md`); a bare entry name with no `.md` (`2026-01-queue › What happened`) is
  not read;
- a column after the first cites another output: `outputs/`, `applications/`, `resumes/` or
  `reports/` outside a source citation (a `sources/` citation up to the next `;` or output path, a
  `<repo>@<sha>:<path>` key, or a URL; a URL into outputs/ still counts), `resume.tex`, or the word
  "provenance".
A provenance file that is missing, not UTF-8, or has no provenance table prints a line saying so
instead.

--humanizer is for every employer-facing output (without it, an application folder or a resume
fails): `none` when the review's edits changed no text, else a UTF-8 file with one line per
sentence or bullet the review's edits changed, `<the line as approved> -> <its Humanizer call:
line, or: humanizer not available>` (`→` also read; the last arrow before the call line splits it).
It prints one `Humanizer after review: <line> -> <call line>` line per line of the file, or
`Humanizer after review: none`.

The last line is `check_save: ok` (exit 0), or `check_save: fix the lines above, then run it again`
(exit 1). Exit 2, with one line saying why, for a <saved> path that is not a saved output in a Log,
or a --humanizer file that cannot be read: fix that path or file, then run it again. Standard
library only, Python 3.11+.
"""
import argparse, os, posixpath, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from entries import ENTRY_PATH   # what an entry's path is

OUTPUT_REF = re.compile(r"\b(?:outputs|applications|resumes|reports)/|\bresume\.tex\b|\bprovenance\b", re.I)
SOURCE_PATH = re.compile(r"\bsources/(?:[^;|\s]|\s+(?![^;|\s]*\b(?:outputs|applications|resumes|reports)/))*|[\w.-]+@[0-9a-f]{6,}:\S+|https?://(?![^\s]*/outputs/)\S+")
MD_FILE = re.compile(r"[\w./\\-]*\w\.md\b", re.I)
PROVENANCE_FILE = re.compile(r"outputs/applications/[^/]+/provenance\.md$|outputs/(?:resumes|reports)/[^/]+\.md$")
APPLICATION = re.compile(r"outputs/applications/[^/]+$")
HUMANIZER_CALL = re.compile(r"[*_`]*Humanizer call[*_`]*:[*_`]*\s*model:?\s+\S|humanizer not available", re.I)
HUMANIZER_LINE = re.compile(r"(.*\S)\s*(?:→|->)\s*((?:%s).*)$" % HUMANIZER_CALL.pattern, re.I)


def provenance_rows(text):
    """(line number, cells, header) for each body row of a table with an entry or source column,
    outside Company context and Risks."""
    rows, skip, header, head, wanted = [], False, True, [], False
    for n, line in enumerate(text.lstrip("﻿").splitlines(), 1):
        if line.startswith("## "):
            skip = bool(re.match(r"## (Company context|Risks)", line))
        s = line.strip()
        if not s.startswith("|"):
            header = True
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        if header:
            header, head = False, cells
            wanted = any(re.search(r"entry|source", c, re.I) for c in cells)
            continue
        if wanted and not skip:
            rows.append((n, cells, head))
    return rows


def entry_file(root, rel, name):
    """Whether a file name in an entry section of the provenance file rel is an entry, profile.md or
    direction.md: read from the Log root, from entries/, or from rel's folder (a relative link)."""
    name = name.replace("\\", "/")
    for path in (name, "entries/" + name, posixpath.join(posixpath.dirname(rel), name)):
        path = posixpath.normpath(path)
        if path in ("profile.md", "direction.md"):
            return True
        if ENTRY_PATH.fullmatch(path) and os.path.isfile(os.path.join(root, *path.split("/"))):
            return True
    return False


def row_problem(root, rel, cells, head):
    """Why a row of the provenance file rel cites something other than an entry section and its
    source, or None."""
    col = next((k for k, h in enumerate(head) if re.search(r"entry", h, re.I)), None)
    if col is not None and col < len(cells):
        other = [f for f in MD_FILE.findall(SOURCE_PATH.sub("", cells[col])) if not entry_file(root, rel, f)]
        if other:
            return "entry section names %s" % other[0]
    for c in cells[1:]:
        m = OUTPUT_REF.search(SOURCE_PATH.sub("", c))
        if m:
            return "names another output (%s)" % m.group(0)
    return None


def log_root(path):
    """The Log root holding path: the nearest folder up from it with a .git."""
    d = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path) or ".")
    while not os.path.exists(os.path.join(d, ".git")):
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up
    return d


def check_file(root, rel):
    """(the Provenance check line, whether it passes) for one provenance file."""
    path = os.path.join(root, *rel.split("/"))
    if not os.path.isfile(path):
        return "Provenance check (%s): missing: write the provenance table there" % rel, False
    try:
        with open(path, encoding="utf-8-sig") as f:
            rows = provenance_rows(f.read())
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


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("saved", nargs="+", help="an application folder or a saved provenance file")
    ap.add_argument("--humanizer", help="`none`, or a file of `<changed line> -> <Humanizer call: line>` lines")
    a = ap.parse_args(argv[1:])

    files = []
    for p in a.saved:
        root = log_root(p)
        rel = os.path.relpath(os.path.abspath(p), root).replace("\\", "/").rstrip("/") if root else None
        if rel and APPLICATION.match(rel) and os.path.isdir(p):
            files.append((root, rel + "/provenance.md"))
        elif rel and PROVENANCE_FILE.match(rel) and not os.path.isdir(p):
            files.append((root, rel))
        else:
            print("%s: not an application folder or a saved provenance file (outputs/resumes/<target>.md, "
                  "outputs/reports/<file>.md) in a Log" % p)
            return 2

    lines, ok = [], True
    for root, rel in files:
        line, good = check_file(root, rel)
        lines.append(line)
        ok = ok and good
    if a.humanizer is not None:
        try:
            hum, good = humanizer_lines(a.humanizer)
        except (OSError, UnicodeError) as e:
            print("--humanizer %s: %s" % (a.humanizer, getattr(e, "strerror", None) or e))
            return 2
        lines += hum
        ok = ok and good
    elif any(rel.startswith(("outputs/applications/", "outputs/resumes/")) for _, rel in files):
        lines.append("Humanizer after review: missing: pass --humanizer <file>, or --humanizer none "
                     "when the review changed no text")
        ok = False
    for line in lines:
        print(line)
    print("check_save: ok" if ok else "check_save: fix the lines above, then run it again")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
