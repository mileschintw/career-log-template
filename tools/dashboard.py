#!/usr/bin/env python3
"""The scan dashboard: one read-only HTML page of the scan's results, regenerated from the Log.

  python3 -I tools/dashboard.py [--check]          (Windows: py -3 -I tools/dashboard.py ...)
  python3 -I tools/dashboard.py --artifact <url>

It takes --root <root>, the Log's root (default: the repo this script is in).

It writes OUT (`outputs/dashboard/dashboard.html`), a self-contained page (no script, no file it
loads) that a browser opens as a file and that an agent can publish as is. The page is a function of
the Log's files alone (no git history, no time; sorted listings, LF line endings), so two machines
with the same Log write the same bytes. Its sections, each from the Log files it names:
- the header: the list items of direction.md's `## Target roles, ranked` and `## Constraints`;
- Pending: the rows of the newest scan report's `## Pending` table still to decide (scan.PENDING);
- Ranking: the newest report's `## Ranking` section, as written;
- Screened, not fully fitted: the newest report's table of that name;
- Declined: `outputs/reports/scan-declined.jsonl`, newest first, with the company and role of the
  newest report row that lists the URL;
- Applications: the folders of `outputs/applications/`, newest first: date, name, Archived or
  Reference (`archived.md`), and the first URL in its `posting.md`;
- Scan history: one row per scan report, newest first: its name, top line, the Pending rows by
  status, the fit maps, and the postings dropped at screen and screened but not fully fitted.
Text from the Log is escaped, and only http and https URLs become links.

ARTIFACT (`outputs/dashboard/artifact.md`) records where the page is published: a line
`Artifact: <url>`.

Prints `wrote: <OUT>` (or `unchanged: <OUT>`), then `artifact: <url>`, or `artifact: none`. With
--check it writes nothing and prints `dashboard: up to date`, `dashboard: stale` or
`dashboard: missing`, with exit 1 for the last two. With --artifact <url> (an https URL) it writes
only ARTIFACT, as that one line: `wrote: <ARTIFACT>`, `artifact: <url>` and `commit: dashboard:
artifact`, or `unchanged: <ARTIFACT>` and `artifact: <url>`. tools/scan.py's report and status
regenerate the page themselves (write()).

Exit 0 on success, 1 on --check's stale or missing, or a file that does not parse, 2 on a bad
argument. Standard library only, Python 3.11+.
"""
import argparse, glob, html, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = "outputs/dashboard/dashboard.html"
ARTIFACT = "outputs/dashboard/artifact.md"
DIRECTION_SECTIONS = ("Target roles, ranked", "Constraints")

# scan.py owns the report format; load it from beside this script (`-I` leaves this folder off sys.path),
# or use the copy already running (scan.py regenerates this page), and leave no tools/__pycache__
sys.dont_write_bytecode = True
_path = os.path.join(HERE, "scan.py")
scan = sys.modules.get("scan")
if scan is None or not os.path.exists(getattr(scan, "__file__", None) or "") or not os.path.samefile(scan.__file__, _path):
    _spec = importlib.util.spec_from_file_location("scan", _path)
    scan = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(scan)


# ---- Markdown, the small part the Log's reports use ----

COMMENT = re.compile(r"<!--.*?-->", re.S)
INLINE = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)|`([^`\n]+)`|\*\*([^*\n]+)\*\*|(https?://[^\s<>()\[\]|\"'`]+)")


def esc(text):
    return html.escape(text or "", quote=True)


def link(url, label=None):
    url = scan.clean(url)
    if not re.match(r"https?://", url):
        return esc(label or url)
    return '<a href="%s" rel="noopener noreferrer">%s</a>' % (esc(url), esc(label or url))


def inline(text):
    """Escaped text with links, code and bold."""
    out, pos = [], 0
    for m in INLINE.finditer(text or ""):
        out.append(esc(text[pos:m.start()]))
        if m.group(1):
            out.append(link(m.group(2), m.group(1)))
        elif m.group(3):
            out.append("<code>%s</code>" % esc(m.group(3)))
        elif m.group(4):
            out.append("<strong>%s</strong>" % esc(m.group(4)))
        else:
            bare = m.group(5)
            url = scan.clean(bare)
            out.append(link(url) + esc(bare[len(url):]))
        pos = m.end()
    out.append(esc((text or "")[pos:]))
    return "".join(out)


def table_html(header, rows):
    out = ['<div class="scroll"><table>', "<thead><tr>"]
    out += ["<th>%s</th>" % inline(h) for h in header]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def markdown(text):
    """Paragraphs, `#` headings (shown two levels down), lists and tables, as HTML."""
    out, para, items, kind = [], [], [], None
    lines = COMMENT.sub("", text or "").split("\n")

    def flush():
        nonlocal para, items, kind
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
        if items:
            out.append("<%s>%s</%s>" % (kind, "".join("<li>%s</li>" % inline(i) for i in items), kind))
        para, items, kind = [], [], None

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("|"):
            flush()
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(scan.cells(lines[i]))
                i += 1
            body = [r for r in block[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            out.append(table_html(block[0], [[inline(c) for c in r] for r in body]))
            continue
        m = re.match(r"(#{1,6})\s+(.*)", s)
        lm = re.match(r"([-*]|\d+[.)])\s+(.*)", s)
        if not s:
            flush()
        elif m:
            flush()
            level = min(len(m.group(1)) + 2, 6)
            out.append("<h%d>%s</h%d>" % (level, inline(m.group(2)), level))
        elif lm:
            new = "ul" if lm.group(1) in "-*" else "ol"
            if para or (kind and kind != new):
                flush()
            kind = new
            items.append(lm.group(2))
        elif items and lines[i][:1] in " \t":
            items[-1] += " " + s
        else:
            if items:
                flush()
            para.append(s)
        i += 1
    flush()
    return "\n".join(out)


# ---- The Log ----

def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def section(text, heading, level="##"):
    m = re.search(r"^%s %s[ \t]*$(.*?)(?=^#{1,%d} |\Z)" % (level, re.escape(heading), len(level)),
                  text, re.M | re.S)
    return m.group(1).strip() if m else None


def top_line(text):
    """The paragraph between a report's title and its first `## `."""
    m = re.search(r"\A#[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return " ".join(m.group(1).split()) if m else ""


def direction(root):
    p = os.path.join(root, "direction.md")
    if not os.path.exists(p):
        return []
    text = scan.read(p)
    return [(name, list_items(section(text, name) or "")) for name in DIRECTION_SECTIONS]


def list_items(text):
    """A section's list items (with their indented continuation lines), less its guidance and comments."""
    out, inside = [], False
    for line in COMMENT.sub("", text).split("\n"):
        if re.match(r"\s*([-*]|\d+[.)])\s+", line):
            out.append(line)
            inside = True
        elif inside and line[:1] in " \t" and line.strip():
            out.append(line)
        else:
            inside = False
    return "\n".join(out)


def pending(text):
    return [[inline(r["company"]), inline(r["role"]), esc(r["status"]), inline(r["draft"]), inline(r["fit_commit"]),
             link(r["url"])] for r in scan.pending_table(text)[2] if r["status"] in scan.PENDING]


def declined(root):
    by_url = scan.newest_rows(root)
    out = []
    for item in scan.read_declined(root):
        item = {k: str(v) for k, v in item.items() if v is not None} if isinstance(item, dict) else {}
        try:
            _, row = by_url.get(scan.canonical(item.get("url", "")), (None, {}))
        except ValueError:   # a URL urlsplit cannot read: shown without its row
            row = {}
        out.append([esc(item.get("date") or ""), inline(row.get("company") or "-"), inline(row.get("role") or "-"),
                    inline(item.get("reason") or "-"), link(item.get("url") or "")])
    return out


def applications(root):
    out = []
    for d in sorted(glob.glob(os.path.join(root, "outputs", "applications", "*")), reverse=True):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.*)", name)
        date, rest = (m.group(1), m.group(2)) if m else ("", name)
        level = "Archived" if "archived.md" in os.listdir(d) else "Reference"   # exact case on every OS
        posting = os.path.join(d, "posting.md")
        found = scan.urls(scan.read(posting)) if os.path.exists(posting) else []
        out.append([esc(date), esc(rest), esc(level), link(found[0]) if found else "-"])
    return out


def history(root, paths):
    out = []
    for p in reversed(paths):
        text = scan.read(p)
        by_status = {}
        for r in scan.pending_table(text)[2]:
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        counts = ", ".join("%d %s" % (by_status[s], s) for s in sorted(by_status)) or "-"
        name = os.path.basename(p)[:-len(".md")]
        out.append([esc(name), inline(top_line(text)), esc(counts), str(len(scan.fit_maps(text))),
                    str(len(scan.section_table(text, "Dropped at screen"))),
                    str(len(scan.section_table(text, "Screened, not fully fitted")))])
    return out


# ---- The page ----

STYLE = """:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#5f6670;--line:#dcd8cf;--card:#ffffff;--accent:#1f5fa8;--head:#f1eee7}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16181c;--fg:#e6e6e3;--muted:#a3a8b0;--line:#33373e;--card:#1d2026;--accent:#7fb0ec;--head:#23272e}}
:root[data-theme="dark"]{--bg:#16181c;--fg:#e6e6e3;--muted:#a3a8b0;--line:#33373e;--card:#1d2026;--accent:#7fb0ec;--head:#23272e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.6rem;margin:0 0 4px}
h2{font-size:1.15rem;margin:32px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--line)}
h3,h4,h5,h6{font-size:1rem;margin:16px 0 4px}
.muted{color:var(--muted)}
a{color:var(--accent);overflow-wrap:anywhere}
code{font:0.9em ui-monospace,Consolas,monospace}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--card)}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;vertical-align:top;padding:6px 10px;border-bottom:1px solid var(--line)}
th{background:var(--head);font-weight:600;white-space:nowrap}
tr:last-child td{border-bottom:0}
.direction{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-top:12px}
.direction div{border:1px solid var(--line);border-radius:6px;background:var(--card);padding:4px 12px}
.direction h3{margin-top:8px}"""


def block(title, intro, header, rows, empty):
    out = ["<section>", "<h2>%s</h2>" % esc(title)]
    if intro:
        out.append('<p class="muted">%s</p>' % intro)
    out.append(table_html(header, rows) if rows else '<p class="muted">%s</p>' % esc(empty))
    out.append("</section>")
    return "\n".join(out)


def render(root):
    paths = [p for _, _, p in scan.reports(root)]
    newest = paths[-1] if paths else None
    text = scan.read(newest) if newest else ""
    parts = ["<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             "<title>Scan Dashboard</title>", "<style>", STYLE, "</style>", "</head>", "<body>", "<main>",
             "<h1>Scan Dashboard</h1>"]
    if newest:
        parts.append('<p class="muted">Newest scan: <code>%s</code>. %s</p>'
                     % (esc(rel(root, newest)), inline(top_line(text))))
    else:
        parts.append('<p class="muted">No scan report yet.</p>')
    parts.append('<p class="muted">Generated by <code>tools/dashboard.py</code> from the Log; '
                 'it changes only when regenerated.</p>')
    d = direction(root)
    if d:
        parts.append('<div class="direction">')
        for name, body in d:
            parts.append("<div><h3>%s</h3>\n%s</div>" % (esc(name), markdown(body) or '<p class="muted">-</p>'))
        parts.append("</div>")
    parts.append(block("Pending", "The newest report's postings still to decide.",
                       ["Company", "Role", "Status", "Draft", "Fit map commit", "URL"], pending(text) if newest else [],
                       "None pending."))
    ranking = section(text, "Ranking") if newest else None
    parts += ["<section>", "<h2>Ranking</h2>", markdown(ranking) if ranking else '<p class="muted">No ranking.</p>',
              "</section>"]
    screened = scan.section_table(text, "Screened, not fully fitted") if newest else []
    parts.append(block("Screened, not fully fitted", "Passed the gate, past the fit budget: no full fit yet.",
                       ["Company", "Role", "URL", "Tier", "Rough", "Screen key"],
                       [[inline(c) for c in r] for r in screened], "None."))
    parts.append(block("Declined", "Later scans drop these.", ["Date", "Company", "Role", "Reason", "URL"],
                       declined(root), "None declined."))
    parts.append(block("Applications", None, ["Date", "Folder", "Level", "Posting"], applications(root),
                       "No application folders."))
    parts.append(block("Scan history", None,
                       ["Report", "Top line", "Pending rows", "Fit maps", "Dropped at screen", "Screened, not fitted"],
                       history(root, paths), "No scan reports."))
    parts += ["</main>", "</body>", "</html>", ""]
    return "\n".join(parts)


def artifact_url(root):
    p = os.path.join(root, ARTIFACT)
    if not os.path.exists(p):
        return None
    m = re.search(r"^Artifact:[ \t]*(https://\S+)[ \t]*$", scan.read(p), re.M)
    return m.group(1) if m else None


def written(root):
    """The page as OUT holds it, or None."""
    out = os.path.join(root, OUT)
    if not os.path.exists(out):
        return None
    with open(out, encoding="utf-8", newline="") as f:
        return f.read()


def write(root, page=None):
    """Writes the page when it changed: `wrote: <OUT>` or `unchanged: <OUT>`."""
    page = render(root) if page is None else page
    if written(root) == page:
        return "unchanged: %s" % OUT
    out = os.path.join(root, OUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    return "wrote: %s" % OUT


def write_artifact(root, url):
    """ARTIFACT as the one line `Artifact: <url>`: `wrote:` or `unchanged:`, then the commit subject."""
    if not re.fullmatch(r"https://\S+", url):
        raise ValueError("--artifact takes the page's https:// URL")
    p = os.path.join(root, ARTIFACT)
    line = "Artifact: %s\n" % url
    if os.path.exists(p) and scan.read(p) == line:
        return ["unchanged: %s" % ARTIFACT, "artifact: %s" % url]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(line)
    return ["wrote: %s" % ARTIFACT, "artifact: %s" % url, "commit: dashboard: artifact"]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = argparse.ArgumentParser(prog="dashboard.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--artifact")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    if a.check and a.artifact:
        print("dashboard: --check and --artifact go alone")
        return 2
    root = a.root
    try:
        if a.artifact:
            for line in write_artifact(root, a.artifact):
                print(line)
            return 0
        page = render(root)
        if a.check:
            old = written(root)
            state = "missing" if old is None else "up to date" if old == page else "stale"
            print("dashboard: %s" % state)
            return 0 if state == "up to date" else 1
        print(write(root, page))
    except (scan.ScanError, OSError, ValueError) as e:
        print("dashboard: %s" % e)
        return 1
    print("artifact: %s" % (artifact_url(root) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
