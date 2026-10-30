#!/usr/bin/env python3
"""Find what a Log still has in the formats of 0.2.1, and fix what is mechanical.

  python3 -I upgrade-0.3.0.py <root> [--apply]      (Windows: py -3 -I ...)

<root> is the Log's root. The guide that goes with this script, upgrade-0.3.0.md, says what to do
with each line. Without --apply it only reads and prints. Each line starts with its kind:

  apply:   --apply changes it
  migrate: the agent changes it by hand as the guide says, with nothing to ask
  ask:     the user decides, in the guide's question round
  review:  show it to the user once in that round; keeping it as it is is an answer too
  later:   waits for a later mode; nothing to do now
  done:    --apply changed it, in the working tree only (nothing is staged or committed)

Each check in CHECKS is a function (log root, apply) returning (kind, text) pairs; a pull request
that changes a Log format adds its check here and its step to the guide.

Exit 0 with `OK: nothing left to migrate` when no apply, migrate or ask line is left, 1 otherwise,
2 on a bad argument. Standard library only, Python 3.11+.
"""
import os, re, subprocess, sys

STATUS = re.compile(r"(stub|imported|consolidated)( \(.+\))?")   # tools/entries.py's STATUS
ENTRY_LINK = re.compile(r"\]\(\.?/?(entries/[^)#\s]+)(?:#[^)]*)?\)")


def read_lines(path):
    """(whether it starts with a byte order mark, its lines with their line ends)."""
    with open(path, "rb") as f:
        raw = f.read()
    return raw.startswith(b"\xef\xbb\xbf"), raw.decode("utf-8-sig").splitlines(keepends=True)


def cells(line):
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def old_table(root):
    """[(line number, cells by lowercase header)] of the rows of README.md's Entries table as it stands:
    the first table with an Entry column, one in the `## Entries` section first, as
    `tools/entries.py readme` picks it; [] when there is none or README.md cannot be read."""
    try:
        _, lines = read_lines(os.path.join(root, "README.md"))
    except (OSError, UnicodeError):
        return []
    tables, section, header = [], None, None
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.strip().startswith("|"):
            header = None
            continue
        if header is None:
            header = [c.strip("*` ").lower() for c in cells(line)]
            if "entry" in header:
                tables.append((section != "Entries", len(tables), []))
            continue
        row = cells(line)
        if "entry" in header and not set("".join(row)) <= set("-: "):
            tables[-1][2].append((n, dict(zip(header, row))))
    return min(tables)[2] if tables else []


def front_matter_status(lines):
    """(index of the front matter's closing `---`, its `status:` value or None without the line);
    (None, None) for a file without front matter."""
    if not lines or lines[0].strip() != "---":
        return None, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            values = [re.sub(r"(^|\s)#.*$", "", m.group(1)).strip()
                      for m in (re.match(r"status:(.*)", line) for line in lines[1:i]) if m]
            return i, (values[0] if values else None)
    return None, None


def check_status(root, apply):
    """Each entry keeps its status in its front matter's `status:` (#573), read from there only
    (#574): an entry without one gets its README row's, when that row's status reads."""
    rows = {}
    for _, row in old_table(root):
        m = ENTRY_LINK.search(row.get("entry", ""))
        if m and "status" in row:
            rows.setdefault(m.group(1), row["status"])
    folder, out = os.path.join(root, "entries"), []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        rel = "entries/" + name
        if not name.endswith(".md") or name == "_template.md" or not os.path.isfile(os.path.join(root, rel)):
            continue
        try:
            bom, lines = read_lines(os.path.join(root, rel))
        except (OSError, UnicodeError):
            continue   # entries.py check names a file it cannot read
        close, status = front_matter_status(lines)
        if close is None or status:
            continue
        row = rows.get(rel)
        if row in (None, "-"):   # `-`: the generated table's cell for no status
            out.append(("ask", "%s: no status: its front matter has no `status:` and no README row gives one" % rel))
        elif not STATUS.fullmatch(row):
            out.append(("ask", "%s: no status: its README row's %r is not a status" % (rel, row)))
        elif apply:
            eol = lines[0][len(lines[0].rstrip("\r\n")):] or "\n"
            at = next((i for i in range(1, close) if lines[i].startswith("status:")), None)
            if at is None:
                lines.insert(close, "status: %s%s" % (row, eol))
            else:
                lines[at] = "status: %s%s" % (row, lines[at][len(lines[at].rstrip("\r\n")):] or eol)
            with open(os.path.join(root, rel), "wb") as f:
                f.write((b"\xef\xbb\xbf" if bom else b"") + "".join(lines).encode("utf-8"))
            out.append(("done", "%s: status: %s, from its README row" % (rel, row)))
        else:
            out.append(("apply", "%s: status: %s, from its README row" % (rel, row)))
    return out


def check_readme(root, apply):
    """README.md's Entries table is generated from the entries' front matter (#574): one row per plain
    entry and one per series, no Tags column; `tools/entries.py readme` writes it whole."""
    out = [("ask", "README.md:%d: %s: links no entry, and the generated table leaves it out"
            % (n, " | ".join(row.values()))) for n, row in old_table(root) if not ENTRY_LINK.search(row.get("entry", ""))]
    if out or check_status(root, False):
        return out   # the table waits for the answers and the statuses: writing it drops the old rows
    tool = os.path.join(root, "tools", "entries.py")
    p = subprocess.run([sys.executable, "-I", tool, "check", "--root", root], capture_output=True, encoding="utf-8",
                       errors="replace")
    found = [line for line in p.stdout.splitlines() if line.startswith("README table not generated: ")]
    if not found:
        return []
    if not found[0].startswith("README table not generated: README.md:"):
        return [("migrate", "README.md: %s" % found[0])]
    if not apply:
        return [("apply", "README.md: Entries table in the old layout, or not generated from the entries yet")]
    p = subprocess.run([sys.executable, "-I", tool, "readme", "--root", root], capture_output=True, encoding="utf-8",
                       errors="replace")
    said = (p.stdout.strip() or p.stderr.strip() or "no output").splitlines()[-1]
    return [("done" if p.returncode == 0 else "migrate", "README.md: %s" % said)]


# Each check goes into this list itself: the export reads `CHECKS = []` as no change.
CHECKS = [check_status, check_readme]
BLOCKING = ("apply", "migrate", "ask")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    apply = "--apply" in argv
    rest = [a for a in argv if a != "--apply"]
    if len(rest) != 1 or not os.path.isdir(os.path.join(rest[0], ".git")):
        print("usage: upgrade-0.3.0.py <root> [--apply], <root> a Log's git checkout")
        return 2
    lines = [line for check in CHECKS for line in check(rest[0], apply)]
    for kind, text in lines:
        print("%s: %s" % (kind, text))
    if apply:   # every apply ends with a fresh check
        lines = [line for check in CHECKS for line in check(rest[0], False)]
        for kind, text in lines:
            print("%s: %s" % (kind, text))
    if any(kind in BLOCKING for kind, _ in lines):
        return 1
    print("OK: nothing left to migrate")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
