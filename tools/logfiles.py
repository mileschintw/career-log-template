"""The helpers the Log's tools share: reading and writing its files, front matter, Markdown tables
and sections, heading anchors, slugs, dated names, git, the Log's root and its own files, the
applications it records, the Target versions and the start record, a posting run's folder, a
session's record (its key, baseline and claims: ADR 0014) and the uncommitted Log files each session
claimed, the URLs in a text, an HTML page's text, a time in this machine's zone, and Claude Code's
project folder for a checkout.

A library, with no command line. A tool beside it imports it with
  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I leaves this folder off sys.path
  sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
  import logfiles

What an entry is (ENTRY_PATH, entry_paths, Entry, the Story model) stays in entries.py. It imports
no tool. Standard library only. It imports on any Python 3 (tools/check.py imports it before it says that
the Log needs 3.11+), so nothing here needs a newer one at import time.
"""
import bisect
import datetime
import glob
import hashlib
import html.parser
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import time


class LogError(Exception):
    """A Log file or a git call this cannot read; the tools print it as `FAIL: <why>`."""


# ---- Reading and writing ----

def read_text(path):
    """A file's text, UTF-8 with or without a byte order mark; UnicodeDecodeError for any other."""
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def write_text(path, text):
    """Write text as UTF-8 without a byte order mark, with LF line ends."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def utf8_stdout():
    """Print Log text in any language, whatever the console's code page: an unencodable character
    (a file name's surrogate escape on Linux) prints as a backslash escape, not a crash."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def python_cmd():
    """How a printed command starts Python here (SKILL.md › Platforms)."""
    return "py -3" if os.name == "nt" else "python3"


def shell_arg(text):
    """text quoted for a printed command that PowerShell, Git Bash, bash and zsh read alike: in single
    quotes, or in double quotes when it holds a single quote (PowerShell reads ‘ ’ ‚ ‛ as one too) and
    none of the characters either shell expands there. Text with both is quoted for the platform's
    shell (SKILL.md › Platforms): PowerShell's doubled quotes on Windows, sh's elsewhere."""
    if not re.search("['‘’‚‛]", text):
        return "'%s'" % text
    if not re.search(r'[$`"“”„\\!]', text):
        return '"%s"' % text
    if os.name == "nt":
        return "'%s'" % re.sub("(['‘’‚‛])", r"\1\1", text)
    return "'%s'" % text.replace("'", "'\\''")


# ---- The Log's root ----

def default_root(script):
    """The Log a tool belongs to: the folder above the tools/ folder that holds script."""
    return os.path.dirname(os.path.dirname(os.path.abspath(script)))


def find_log_root(path):
    """The nearest folder up from path (a file or a folder) that holds a .git, or None."""
    d = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path) or ".")
    while not os.path.exists(os.path.join(d, ".git")):
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up
    return d


def split_root(args, script):
    """(root, the other arguments) from `--root <root>` or `--root=<root>` anywhere before a `--`;
    root is default_root(script) without one. LogError for `--root` with no value, or given twice.
    Every tool takes its root this way, with no positional form."""
    root, rest, it = None, [], iter(args)
    for a in it:
        if a == "--":
            rest += [a] + list(it)
            break
        if a == "--root" or a.startswith("--root="):
            value = a[len("--root="):] if "=" in a else next(it, None)
            if not value or root is not None:
                raise LogError("--root takes one folder, the Log's root, once")
            root = value
        else:
            rest.append(a)
    return (root or default_root(script)), rest


def arg_path(root, arg, fits=os.path.isfile):
    """The absolute path a path argument names: arg as it is when absolute, else relative to root
    and then to the current folder, the first that fits (a file, by default); None when none does."""
    for base in ((None,) if os.path.isabs(arg) else (root, os.getcwd())):
        full = os.path.abspath(arg if base is None else os.path.join(base, arg))
        if fits(full):
            return full
    return None


def glob_under(folder, *pattern):
    """The paths under folder that match pattern (a glob, one argument per path segment), in no
    order: folder is read as it is written, whatever `[`, `]`, `*` or `?` its path holds. Every glob
    under a folder goes through here, in the Log or outside it (a home, LOCALAPPDATA, Playwright's
    cache): tools/tests/test_logfiles.py fails on one by hand that is not in its OUTSIDE_THE_LOG."""
    return glob.glob(os.path.join(glob.escape(folder), *pattern))


def add_root(parser, script):
    """The same --root on an argparse parser."""
    parser.add_argument("--root", default=default_root(script),
                        help="the Log's root (default: the folder above this script's)")


# The Log's own files (AGENTS.md › Changes), as paths relative to its root: everything else in it is
# the Engine. sources/inbox/ is the ignored inbox and entries/_template.md the Template's.
LOG_FILES = ["README.md", "README.zh-TW.md", "stories.md", "profile.md", "direction.md", "applications.md",
             "config.toml", "scan-sources.md"]
LOG_FOLDERS = ["entries", "stories", "outputs", "sources"]
NOT_LOG = ["entries/_template.md"]
INBOX = "sources/inbox"
# The same files as git pathspecs (`git status -- <LOG_PATHS>`)
LOG_PATHS = LOG_FOLDERS + [":(exclude)%s" % p for p in NOT_LOG] + LOG_FILES


def log_files(root):
    """The Log's own files that exist under root, as /-separated paths: LOG_FILES, then each file in
    LOG_FOLDERS (sorted, hidden folders and the inbox skipped), less NOT_LOG."""
    out = [f for f in LOG_FILES if os.path.isfile(os.path.join(root, f))]
    for folder in LOG_FOLDERS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, folder)):
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            dirnames[:] = sorted(d for d in dirnames if (rel + "/" + d) != INBOX and not d.startswith("."))
            out += [rel + "/" + f for f in sorted(filenames)]
    return [p for p in out if p not in NOT_LOG]


# ---- Front matter ----

def unquote(value):
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def scalar(value):
    """A front matter value: a quoted one up to its closing quote, else up to a ` #` comment. When the
    same quotes wrap the whole value before a comment, it is read whole, a quote inside it included
    (`'Children's Hospital'`); in single quotes `''` is YAML's `'` (`'O''Brien'` is `O'Brien`)."""
    value = value.strip()
    bare = re.sub(r"(^|\s+)#.*$", "", value).strip()
    m = re.match(r"(\"[^\"]*\"|'[^']*')", value)
    if m and len(bare) > 1 and bare[0] == bare[-1] == m.group(1)[0] and len(bare) > len(m.group(1)):
        return bare[1:-1].replace("''", "'") if bare[0] == "'" else bare[1:-1]
    if m:
        return m.group(1)[1:-1]
    return bare


def split_front_matter(text, closed=False):
    """(the front matter's lines, the line index the body starts at): the lines between a first line
    `---` and the next `---`. Without a closing `---` the front matter runs to the end of the text, or
    with closed=True there is none. ([], 0) when the text does not start with `---`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], 0
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return lines[1:i], i + 1
    return ([], 0) if closed else (lines[1:], len(lines))


def _quoted(raw):
    """Whether a value or list item as written is a quoted string (`"a, b"`, `'a'`)."""
    raw = raw.strip()
    return len(raw) > 1 and raw[0] in "\"'" and raw.find(raw[0], 1) > 0


def _fields(text, closed):
    """[(key, is a list, [(value, quoted), ...])] in order, a repeated key once per line it is on."""
    out = []
    for line in split_front_matter(text, closed)[0]:
        m = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
        item = re.match(r"\s+- (.*)$", line)
        if m:
            value = m.group(2).strip()
            listed = re.sub(r"\]\s+#.*$", "]", value)
            if listed.startswith("[") and listed.endswith("]"):
                items = re.findall(r"\s*(?:\"[^\"]*\"|'[^']*'|[^,]+)", listed[1:-1])
                out.append((m.group(1), True, [(unquote(v), _quoted(v)) for v in items if v.strip()]))
            else:
                out.append((m.group(1), False, [(scalar(value), _quoted(value))]))
        elif item and out:
            key, listed, values = out[-1]
            raw = item.group(1)
            out[-1] = (key, True, (values if listed else []) + [(scalar(raw), _quoted(raw))])
    return out


def front_matter(text, closed=False):
    """{key: str or list}: inline lists `[a, b]` and block lists (`  - a`) become lists; a quoted
    value is read whole (`"Acme #1, Inc"`), an unquoted one up to a ` #` comment. A repeated key keeps
    its last value."""
    return {key: ([v for v, _ in values] if listed else values[0][0])
            for key, listed, values in _fields(text, closed)}


def front_matter_items(text, closed=False):
    """[(key, value, quoted)] for each scalar value and each list item, in order, every line of a
    repeated key included; an empty scalar is left out. quoted: it was written as a quoted string, so
    it is one value, its commas included (`"Acme, Inc"`)."""
    return [(key, v, q) for key, listed, values in _fields(text, closed) for v, q in values if listed or v]


def as_list(value):
    if isinstance(value, list):
        return value
    return [v.strip() for v in (value or "").split(",") if v.strip()]


# ---- Markdown ----

CELL = re.compile(r"(?<!\\)\|")


def md_cells(line):
    """A table row's cells, stripped, with `\\|` read as `|`. The row's outer pipes are optional."""
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return [c.strip().replace("\\|", "|") for c in CELL.split(s)]


def md_cell_spans(line):
    """(start, end) of each cell of a table row as written, between its pipes (`\\|` is no pipe),
    its spaces included; a row may leave off its last pipe."""
    bounds = [m.start() for m in CELL.finditer(line)]
    text_end = len(line.rstrip("\r\n"))
    if not bounds or line[:bounds[0]].strip():   # no leading pipe: the first cell starts the line
        bounds.insert(0, -1)
    if line[bounds[-1] + 1:text_end].strip():    # no closing pipe
        bounds.append(len(line[:text_end].rstrip()))
    return [(a + 1, b) for a, b in zip(bounds, bounds[1:])]


def md_cell(text):
    """Text as a table cell (or a piece of one): `|` written as `\\|`, line ends as spaces."""
    return str(text).replace("|", "\\|").replace("\r", "").replace("\n", " ")


def md_row(cells):
    """A table row from cells, each written as md_cell writes it."""
    return "| " + " | ".join(md_cell(c) for c in cells) + " |"


def is_rule(cells):
    """The `|---|:--:|` row under a table's header (an empty row reads as one too)."""
    return set("".join(cells)) <= set("-: ")


class Table:
    """A Markdown table: head (its header cells as written), header (the same, lowercased, without
    `*` and backticks), rows [(line number, cells)] (the rule row left out), line (the header's line
    number, from 1), end (its last line's number) and section (the last `## ` heading's text above
    it, heading_re's form, or None)."""

    def __init__(self, line, section, head):
        self.line, self.section, self.head, self.rows, self.end = line, section, head, [], line
        self.header = [h.strip("*` ").lower() for h in head]

    def dicts(self):
        """Each row as {lowercased header: cell}."""
        return [dict(zip(self.header, cells)) for _, cells in self.rows]


def md_tables(text):
    """Each table in the text, in order: a run of lines that start with `|` (after spaces), its first
    row the header. Only the row right under the header is read as the divider (is_rule), as GitHub
    reads a table: a later row of `-` cells is a data row. A row of empty cells is left out."""
    tables, current, section = [], None, None
    for n, line in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        h = re.match(r"##[ \t]+(.*)", line)   # heading_re's form
        if h:
            section = h.group(1).strip()
        if not line.strip().startswith("|"):
            current = None
            continue
        cells = md_cells(line)
        if current is None:
            current = Table(n, section, cells)
            tables.append(current)
        elif any(cells) and not (n == current.line + 1 and is_rule(cells)):
            current.rows.append((n, cells))
        current.end = n
    return tables


def strip_comments(text):
    """The text without its HTML comments."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def heading_re(heading, level=2):
    """The pattern of a `## <heading>` line (with level 2): spaces or tabs after the marks and at the
    end, and a CRLF line end, allowed; re.M, so search() finds it on any line."""
    return re.compile(r"^%s[ \t]+%s[ \t]*\r?$" % ("#" * level, re.escape(heading)), re.M)


def blank_comments(text):
    """The text with each HTML comment's characters as spaces, its line ends kept: every offset and
    line number holds."""
    return re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\r\n]", " ", m.group(0)), text, flags=re.S)


def section(text, heading, level=2):
    """The body of the first `## <heading>` (with level 2, heading_re()) in the text, up to the next
    heading of that level or a higher one other than `# ` (`### ` ends at `## ` or `### `), or the
    end; None when there is no such heading. The heading may be the text's last line. A `# ` line
    does not end it: in a code block it is a comment. A heading inside an HTML comment is none."""
    span = section_span(text, heading, level)
    return text[span[0]:span[1]] if span else None


def section_span(text, heading, level=2):
    """(start, end) of the body section() returns, as offsets into the text; None when there is no
    such heading. A tool that rewrites a section's lines splices them in here."""
    m = re.search(r"%s\n?(.*?)(?=^#{2,%d}[ \t]|\Z)" % (heading_re(heading, level).pattern, max(level, 2)),
                  blank_comments(text), re.M | re.S)
    return m.span(1) if m else None


def section_lines(lines, heading, level=2):
    """(the heading's index, the index after the section's last line) in lines, each with its line
    end (splitlines(keepends=True)), by section()'s rule; None without the heading."""
    span = section_span("".join(lines), heading, level)
    if span is None:
        return None
    ends = list(itertools.accumulate(len(line) for line in lines))   # each line's end offset
    at = bisect.bisect_right(ends, span[0] - 1)   # the heading's line ends just before its body
    return at, (bisect.bisect_right(ends, span[1] - 1) + 1 if span[1] > span[0] else at + 1)


def bullets(text):
    """The text of each `- ` line, HTML comments dropped."""
    return [line.strip()[2:].strip() for line in strip_comments(text).splitlines()
            if line.strip().startswith("- ")]


def anchor(heading):
    """GitHub's anchor for a heading's text, before any -1, -2 for a repeat."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def heading_anchors(text):
    """GitHub's anchors for a Markdown file's section headings, `## ` to `###### ` (a repeated one gets
    -1, -2, ..., counting the `# ` title too), outside HTML comments and fenced code (an unclosed
    fence runs to the end)."""
    return set(heading_names(text))


FENCE = re.compile(r"[ \t]*(`{3,}|~{3,})")


def outside_code(lines):
    """(index, line) of each of the lines outside fenced code, the fence lines left out: a fence of
    three or more backticks or tildes closes at a line of only the same mark, at least as long; an
    unclosed one runs to the end."""
    fence = None
    for k, line in enumerate(lines):
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip(" \t`~"):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        yield k, line


def heading_names(text):
    """{anchor: heading text} for the headings heading_anchors() reads."""
    out, seen = {}, {}
    for _, line in outside_code(strip_comments(text).splitlines()):
        h = re.match(r"(#{1,6})[ \t]+(.+?)[ \t#]*$", line)
        if not h:
            continue
        base = anchor(h.group(2))
        n = seen.get(base, 0)
        seen[base] = n + 1
        if len(h.group(1)) > 1:
            out[base if n == 0 else "%s-%d" % (base, n)] = h.group(2).strip()
    return out


# ---- Names ----

DATED = re.compile(r"(\d{4}-\d{2}-\d{2})-(.*)$", re.S)


def entry_slug(path):
    """An entry's slug: its file name without `.md` and the leading `<YYYY-MM>-`."""
    return re.sub(r"^\d{4}-\d{2}-", "", os.path.basename(path)[:-3])


def question_slug(question_type):
    """A question type as a file name: lowercase, each run of other characters one `-` (letters of
    any script kept)."""
    return re.sub(r"[\W_]+", "-", question_type.lower()).strip("-")


# A slug: lowercase ASCII letters and digits, with single hyphens between them (a Story's name, a stage, a
# --slug). Tools use this, never a copy of the pattern (tools/tests/test_logfiles.py fails on one).
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"


def is_slug(text):
    """Whether text is a slug (SLUG)."""
    return bool(re.fullmatch(SLUG, text or ""))


def ascii_slug(text):
    """Text as an ASCII name: lowercase letters and digits, each run of anything else one `-`, none
    at the ends; '' when nothing is left."""
    return "-".join(re.sub(r"[^0-9a-z]+", " ", (text or "").lower()).split())


def split_dated(name):
    """(date, rest) for a name `<YYYY-MM-DD>-<rest>`, else (None, name)."""
    m = DATED.match(name)
    return (m.group(1), m.group(2)) if m else (None, name)


def is_target_name(text):
    """Whether text is a target name (a Target version's, a role family's): a non-empty ascii_slug of
    itself."""
    return bool(text) and ascii_slug(text) == text


def posting_slug(text):
    """A company or role as a draft folder or application folder name has it: ascii_slug, or
    `posting` for a name with no ASCII letter or digit."""
    return ascii_slug(text) or "posting"


def plural(n, word):
    """`1 commit`, `2 commits`."""
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


# ---- Links ----

REPO_URL = re.compile(r"https?://(?:www\.)?(?:github\.com|gitlab\.[^/\s]+)/([^\s,\]#?]+)")
# A path segment after owner/repo that starts a page inside a repo, not a group or repo name
URL_END = {"-", "tree", "blob", "issues", "pulls", "pull", "wiki", "releases", "commit", "commits",
           "tags", "actions", "compare"}


def repo_segments(value):
    """The owner, group and repo names in each GitHub or GitLab URL in value, up to a URL_END segment;
    a segment with no letter or digit (`@`) names nothing."""
    names = []
    for path in REPO_URL.findall(value):
        for i, seg in enumerate(path.split("/")):
            if i >= 2 and seg in URL_END:
                break
            seg = re.sub(r"\.git$", "", seg)
            if re.search(r"[^\W_]", seg):
                names.append(seg)
    return names


# ---- Outputs ----

def provenance_rows(text):
    """(line number, cells, header cells) for each body row of a provenance table: a table with a
    column whose header says entry or source, outside `## Company context` and `## Risks...`."""
    rows = []
    for t in md_tables(text):
        if t.section and re.match(r"(Company context|Risks)", t.section):
            continue
        if any(re.search(r"entry|source", h, re.I) for h in t.head):
            rows += [(n, cells, t.head) for n, cells in t.rows]
    return rows


# ---- LaTeX ----

TEX_ADDRESS = re.compile(r"\\(href|url)\{[^}]*\}")
# A \\ line break (\\*, \\[2pt], \\ [2pt]) or a \newline inside a source line
TEX_LINE_BREAK = re.compile(r"\\\\\*?(?:\s*\[[^\]]*\])?|\\newline(?![A-Za-z])")


def tex_comment_at(line):
    """Where a .tex line's comment starts: the first % after an even number of backslashes (\\\\% is
    a line break, then a comment) and outside an \\href or \\url address, or None."""
    addresses = [m.span() for m in TEX_ADDRESS.finditer(line)]
    for m in re.finditer("%", line):
        run = len(line[:m.start()]) - len(line[:m.start()].rstrip("\\"))
        if run % 2 == 0 and not any(a <= m.start() < b for a, b in addresses):
            return m.start()
    return None


def tex_uncomment(line):
    """A .tex line without its comment (tex_comment_at)."""
    at = tex_comment_at(line)
    return line if at is None else line[:at]


def tex_body(text):
    """(line number, the line with its comment dropped, the raw line) of each line after
    \\begin{document}; the whole file when it has none."""
    lines = text.splitlines()
    start = next((i + 1 for i, l in enumerate(lines) if "\\begin{document}" in tex_uncomment(l)), 0)
    return [(n + 1, tex_uncomment(lines[n]), lines[n]) for n in range(start, len(lines))]


def tex_sections(text):
    """(line number, title as written) of each `\\section{...}` in the body (tex_body)."""
    out = []
    for n, code, _ in tex_body(text):
        m = re.search(r"\\section\*?\{([^}]*)\}", code)
        if m:
            out.append((n, m.group(1)))
    return out


NO_BULLETS = ("education", "skill")   # the resume skeleton's sections whose items are no bullet
BULLETS = ("experience", "project")


def has_bullets(title):
    """Whether a `\\section` title's items are bullets: it holds "experience" or "project", or neither
    "education" nor "skill" (`Experience and Skills` has bullets)."""
    title = title.lower()
    return any(w in title for w in BULLETS) or not any(w in title for w in NO_BULLETS)


def is_skills(title):
    """Whether a `\\section` title is the Skills section: it holds "skill" and has no bullets."""
    return "skill" in title.lower() and not has_bullets(title)


def tex_items(text):
    """(line number, text) of each `\\item` in a .tex file, comments dropped: the text after it (and
    its optional `[...]`) up to the next `\\item`, `\\begin`, `\\end` or an empty line, whitespace
    collapsed, LaTeX left as written."""
    out, current = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = tex_uncomment(raw)
        if current is not None and not raw.strip():   # a comment-only line is not a paragraph break
            current = None
            continue
        parts = re.split(r"(\\item\b(?:\[[^\]]*\])?|\\begin\{[^}]*\}|\\end\{[^}]*\})", line)
        for k, part in enumerate(parts):
            if k % 2:
                if part.startswith("\\item"):
                    current = [n, []]
                    out.append(current)
                else:
                    current = None
            elif current is not None:
                current[1].append(part)
    return [(n, " ".join(" ".join(chunks).split())) for n, chunks in out]


INPUT = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")


def local_inputs(tex):
    """The files beside tex, relative to its folder, that it (or one of them) \\input's or
    \\include's, the name as given or with .tex added; a name that is no file there (a
    package's own file), that leaves the folder or that is tex itself is not one."""
    folder = os.path.dirname(os.path.abspath(tex))
    own = os.path.normcase(os.path.basename(tex))
    found, todo = [], [tex]
    while todo:
        try:
            text = read_text(todo.pop())
        except (OSError, UnicodeDecodeError):
            continue
        text = "\n".join(map(tex_uncomment, text.split("\n")))   # a commented-out \input is not read
        for name in INPUT.findall(text):
            for cand in (name.strip(), name.strip() + ".tex"):
                if os.path.isabs(cand) or os.path.splitdrive(cand)[0]:
                    break
                path = os.path.normpath(os.path.join(folder, cand))
                rel = os.path.relpath(path, folder)
                if (os.path.isfile(path) and rel != os.pardir and not rel.startswith(os.pardir + os.sep)
                        and os.path.normcase(rel) != own and rel not in found):
                    found.append(rel)
                    todo.append(path)
                    break
    return found


def tex_bullets(text):
    """tex_items less the items under a body `\\section` (tex_sections) whose items are no bullets
    (has_bullets: a coursework line, a Skills row): an experience or project bullet, under any other
    heading, is what feeds Past phrasings. A bold label is no sign: `\\textbf{Topic:} Built ...`
    starts many a bullet."""
    sections = tex_sections(text)
    def heading(n):
        return next((title for at, title in reversed(sections) if at <= n), "")
    return [(n, item) for n, item in tex_items(text) if has_bullets(heading(n))]


# ---- git ----

def git_run(root, *args, timeout=60):
    """The finished `git -C <root> <args>` (stdout and stderr as text), whatever its exit code;
    LogError when git cannot start or gives no answer in time. It never waits on a credential
    prompt, and prints paths unquoted."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        return subprocess.run(["git", "-C", root, "-c", "core.quotepath=false"] + list(args),
                              capture_output=True, encoding="utf-8", errors="replace", env=env,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise LogError("git failed: %s" % e)


def git(root, *args, timeout=60):
    """The stdout of `git -C <root> <args>`; LogError when it cannot run or exits non-zero."""
    p = git_run(root, *args, timeout=timeout)
    if p.returncode != 0:
        raise LogError("git %s failed: %s" % (args[0], p.stderr.strip()))
    return p.stdout


def git_blob(root, rev, path, timeout=60):
    """The bytes of path, relative to root, at rev (`git show <rev>:./<path>`; rev "" is the index),
    or None when rev has no such file; LogError when git cannot start or gives no answer in time.
    The `./` reads path from root, not from the git top level, for a Log in a folder below it."""
    path = path if path.startswith("./") else "./" + path
    try:
        p = subprocess.run(["git", "-C", root, "show", "%s:%s" % (rev, path)], capture_output=True,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"), timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise LogError("git failed: %s" % e)
    return p.stdout if p.returncode == 0 else None


def checkouts(root):
    """The checkouts of root's repository, main checkout first, then each linked worktree, as absolute
    paths from `git worktree list`; LogError when git cannot list them (root is no git repository)."""
    out = [line[len("worktree "):] for line in git(root, "worktree", "list", "--porcelain").splitlines()
           if line.startswith("worktree ")]
    return [os.path.abspath(p) for p in out]


def default_branch(root):
    """The default branch's name, from origin/HEAD, or None when that is unset (no origin, or a clone
    that never set it). It only reads; set_default_branch() asks the remote."""
    p = git_run(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    name = p.stdout.strip()
    if p.returncode != 0 or not name:
        return None
    return name[len("origin/"):] if name.startswith("origin/") else name


def set_default_branch(root, timeout=120):
    """Set origin/HEAD from the remote (`git remote set-head origin --auto`) and return the default
    branch's name; None when the remote cannot say."""
    p = git_run(root, "remote", "set-head", "origin", "--auto", timeout=timeout)
    return default_branch(root) if p.returncode == 0 else None


def local_identity(root):
    """(user.name, user.email) from the repo's own git config (`config --local`), each None when unset:
    a commit uses this identity, never a global one that may belong to someone else."""
    def get(key):
        p = git_run(root, "config", "--local", "--get", key)
        return (p.stdout.strip() or None) if p.returncode == 0 else None
    return get("user.name"), get("user.email")


# ---- Applications ----

def norm(text):
    """Text as space-separated lowercase ASCII words, with a space at each end, for whole-word
    matching (`" acme ml engineer "`)."""
    return " " + " ".join(re.sub(r"[^0-9a-z]+", " ", (text or "").lower()).split()) + " "


def is_archived_folder(root, rel):
    """Whether the application folder rel (from root) holds archived.md, the name in that exact case on
    every OS: write › Save levels' Archived marker."""
    path = os.path.join(root, *rel.split("/"))
    return os.path.isdir(path) and "archived.md" in os.listdir(path)


def archived_misnamed(root, rel):
    """The files of the application folder rel named archived.md in another case (`Archived.md`): no
    marker, which is_archived_folder does not count."""
    path = os.path.join(root, *rel.split("/"))
    return [f for f in (os.listdir(path) if os.path.isdir(path) else []) if f.lower() == "archived.md" and f != "archived.md"]


def application_records(root):
    """[(text, match, where)] for each `outputs/applications/*/` folder and each `applications.md`
    line: text is the folder's `posting.md` (or '') or the line, and match(company, role, city), on
    norm() text, is whether the record names that company and role. A folder matches when its name,
    less its date, is the company and then the role, and its posting text, when it has one, holds
    the city (when given); an applications.md table row when a cell equals the company and one the
    role."""
    out = []
    for d in sorted(glob_under(os.path.join(root, "outputs", "applications"), "*")):
        if not os.path.isdir(d):
            continue
        posting = os.path.join(d, "posting.md")
        raw = read_text(posting) if os.path.exists(posting) else ""
        name = norm(split_dated(os.path.basename(d))[1])

        def match(company, role, city, name=name, text=norm(raw) if raw else ""):
            return name == company + role.lstrip() and (not text or not city.strip() or city in text)
        out.append((raw, match, "outputs/applications/" + os.path.basename(d)))
    apps = os.path.join(root, "applications.md")
    if os.path.exists(apps):
        for i, line in enumerate(read_text(apps).split("\n"), 1):
            row = {norm(c) for c in md_cells(line)} if line.strip().startswith("|") else set()

            def match(company, role, city, row=row):
                return company in row and role in row
            out.append((line, match, "applications.md:%d" % i))
    return out


# ---- Target versions and the start record ----

RESUMES = "outputs/resumes"
START_RECORD = ".build/drafts/%s/start.txt"   # what `application.py start --family --tier` wrote, by draft name
START_KEYS = ("from", "family", "tier")


def targets(root):
    """The Target versions: the name of each outputs/resumes/<target>.tex, sorted, less a part (a .tex
    another one there \\input's or \\include's, with no .pdf beside it), as tools/resume.py --stale
    reads them."""
    folder = os.path.join(root, *RESUMES.split("/"))
    texs = sorted(glob_under(folder, "*.tex"))
    parts = {os.path.normcase(os.path.join(folder, rel)) for tex in texs for rel in local_inputs(tex)}
    return [os.path.basename(t)[:-4] for t in texs
            if os.path.normcase(t) not in parts or os.path.isfile(t[:-4] + ".pdf")]


def start_record_text(source, family, tier):
    """A start record's text: one `key: value` line per START_KEYS key."""
    return "".join("%s: %s\n" % kv for kv in zip(START_KEYS, (source, family, tier)))


def parse_start_record(text):
    """{key: value} for each `key: value` line of a start record."""
    pairs = (l.partition(":") for l in text.splitlines())
    return {k.strip(): v.strip() for k, sep, v in pairs if sep}


def start_record(root, name):
    """The draft <name>'s start record as parse_start_record reads it, or None when it has none."""
    path = os.path.join(root, *(START_RECORD % name).split("/"))
    return parse_start_record(read_text(path)) if os.path.isfile(path) else None


def start_record_lacks(record):
    """The `key:` lines START_KEYS names that a parsed start record lacks."""
    return [k + ":" for k in START_KEYS if k not in record]


# ---- A posting run's folder ----

RUNS = ".build/runs"   # one folder per posting run, named by its key (tools/scan.py run makes it)
RUN_KEY = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<hh>\d{2})(?P<mm>\d{2})(?P<ss>\d{2})(?:-(?P<n>\d+))?$")
RUN_SESSION = "session"   # in a run's folder: the key of the session that started it (scan.py run --session)


def run_key(date, clock, n=1):
    """A run's key: `<date>-<clock>`, then `-<n>` from 2 on (the second run started that second)."""
    return "%s-%s" % (date, clock) + ("-%d" % n if n > 1 else "")


def run_folder(key):
    """A run's folder, relative to the Log root."""
    return "%s/%s" % (RUNS, key)


def run_session(root, key):
    """The session key a run recorded (scan.py run --session), or None: no such run, or it recorded none."""
    if not RUN_KEY.match(key or ""):
        return None
    try:
        found = read_text(os.path.join(root, *run_folder(key).split("/"), RUN_SESSION)).strip()
    except (OSError, UnicodeError):
        return None
    return found if SESSION_KEY.match(found) else None


def commit_session(root, session, run):
    """The session a commit runs under: --session's, or for one release the session --run's run recorded (scan.py
    run --session); None for neither."""
    return session or (run_session(root, run) if run else None)


# ---- A session's record: its key, baseline and claims (ADR 0014) ----

SESSIONS = ".build/sessions"   # one folder per agent session, named by its key (tools/check.py makes it)
SESSION_KEY = RUN_KEY   # `<YYYY-MM-DD>-<HHMMSS>[-<n>]`, the time of the session's first check
SESSION_FILE = "session.json"   # {"start", "baseline": {path: hash}, "claims": [path]}
SESSION_KEEP_DAYS = 7   # a session holding no claim whose key is older than this is deleted (new_session)
GONE = "-"   # a baseline hash: the file is deleted
LOCK = ".lock"   # in SESSIONS: held while one tool changes records another session may read or change
LOCK_TRIES, LOCK_WAIT, LOCK_STALE = 100, 0.1, 60   # seconds; a lock older than LOCK_STALE is a crashed tool's


def session_path(root, key):
    return os.path.join(root, *SESSIONS.split("/"), key, SESSION_FILE)


def read_session(root, key):
    """A session's record {"start", "baseline", "claims"}, or None when it has none or it does not parse."""
    if not SESSION_KEY.match(key or ""):
        return None
    try:
        data = json.loads(read_text(session_path(root, key)))
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    baseline, claims = data.get("baseline"), data.get("claims")
    return {"start": data.get("start"),
            "baseline": {p: h for p, h in baseline.items() if isinstance(p, str) and isinstance(h, str)}
            if isinstance(baseline, dict) else {},
            "claims": [p for p in claims if isinstance(p, str)] if isinstance(claims, list) else []}


def write_session(root, key, record):
    """Write a session's record whole (a temporary file, then a rename: a reader never sees half of it)."""
    path = session_path(root, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    write_text(tmp, json.dumps({"start": record.get("start"), "baseline": dict(sorted(record["baseline"].items())),
                                "claims": sorted(set(record["claims"]))}, indent=1) + "\n")
    os.replace(tmp, path)


def sessions(root):
    """{key: record} of every session of this Log whose record reads."""
    folder = os.path.join(root, *SESSIONS.split("/"))
    out = {}
    for key in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        record = read_session(root, key)
        if record is not None:
            out[key] = record
    return out


class session_lock:
    """Held while a tool reads and changes session records (a claim, a release, a baseline that lapses), so two
    sessions never claim one file at once: a file made with O_EXCL, waited for, and taken over once stale."""

    def __init__(self, root):
        self.path = os.path.join(root, *SESSIONS.split("/"), LOCK)

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        for _ in range(LOCK_TRIES):
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > LOCK_STALE:
                        os.remove(self.path)
                        continue
                except OSError:
                    continue
                time.sleep(LOCK_WAIT)
        raise LogError("%s/%s is held by another tool; if no other session is running one, delete it"
                       % (SESSIONS, LOCK))

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except OSError:
            pass


def file_hash(root, path):
    """The hash a baseline keeps for a Log file (path relative to the root): its bytes', or GONE."""
    try:
        with open(os.path.join(root, path), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return GONE


def make_keyed_folder(parent, key_of):
    """Make parent if it is missing, then the folder parent/key_of(n) for the first n from 1 that is not there
    yet; its key. A record kept one folder per key (a run, a session) gets its folder here: the copied loop
    is what tools/tests/test_logfiles.py fails on."""
    os.makedirs(parent, exist_ok=True)
    n = 1
    while True:   # mkdir makes the folder or fails, so two records started the same second never share one
        key = key_of(n)
        try:
            os.mkdir(os.path.join(parent, key))
            return key
        except FileExistsError:
            n += 1


def new_session(root, baseline):
    """Make a session's folder and record with this baseline {path: hash}; its key, the time now. Deletes each
    session that holds no claim and whose key's date is more than SESSION_KEEP_DAYS before today."""
    now = datetime.datetime.now()
    parent = os.path.join(root, *SESSIONS.split("/"))
    os.makedirs(parent, exist_ok=True)
    oldest = (now.date() - datetime.timedelta(days=SESSION_KEEP_DAYS)).isoformat()
    for key, record in sessions(root).items():
        if not record["claims"] and SESSION_KEY.match(key).group("date") < oldest:
            shutil.rmtree(os.path.join(parent, key), ignore_errors=True)
    key = make_keyed_folder(parent, lambda n: run_key(now.strftime("%Y-%m-%d"), now.strftime("%H%M%S"), n))
    write_session(root, key, {"start": now.astimezone().isoformat(timespec="seconds"), "baseline": baseline,
                              "claims": []})
    return key


def under(path, named):
    """Whether path is the named path, or under it when it names a folder."""
    named = named.rstrip("/")
    return path == named or path.startswith(named + "/")


def holder(records, path, but=None):
    """The key of the session (other than but) whose claims cover path or a path under it, or None."""
    for key, record in records.items():
        if key != but and any(under(path, c) or under(c, path) for c in record["claims"]):
            return key
    return None


def lapse(root, changed):
    """Drop, from every session's baseline, each file that matches HEAD now (not in changed, the paths git lists
    as changed or new): an entry lapses once its file is settled, and never comes back."""
    with session_lock(root):
        for key, record in sessions(root).items():
            kept = {p: h for p, h in record["baseline"].items() if p in changed}
            if len(kept) != len(record["baseline"]):
                record["baseline"] = kept
                write_session(root, key, record)


def release_claims(root, key, paths=None):
    """Release the session's claims on paths (None: every claim; Next up, or its end); the released paths. Its
    record stays: an idle session keeps its key."""
    with session_lock(root):
        record = read_session(root, key)
        if record is None:
            return []
        gone = list(record["claims"]) if paths is None else [p for p in paths if p in record["claims"]]
        record["claims"] = [p for p in record["claims"] if p not in gone]
        write_session(root, key, record)
    return gone


def is_log_path(path):
    """Whether a path (relative to the root, / separators) is one of the Log's own files or folders (LOG_PATHS)."""
    path = path.rstrip("/")
    return ((path in LOG_FILES or path.split("/")[0] in LOG_FOLDERS)
            and path not in NOT_LOG and not under(path, INBOX))


def uncommitted(root):
    """[(status, path, old path or None, claiming session key or None)] of the Log's own files (LOG_PATHS)
    that git shows as changed or new, each with the session whose claims cover it (holder); None when git
    fails. Each baseline entry whose file matches HEAD again lapses here (lapse)."""
    try:
        p = git_run(root, "status", "--porcelain", "-z", "--untracked-files=all", "--", *LOG_PATHS, timeout=30)
    except LogError:
        return None
    if p.returncode != 0:
        return None
    found, entries = [], iter(p.stdout.split("\0"))
    for entry in entries:
        if len(entry) > 3:
            status, path = entry[:2], entry[3:]
            old = next(entries, "?") if "R" in status or "C" in status else None   # a rename's -z entry is followed by its old path
            found.append((status.strip(), path, old))
    if os.path.isdir(os.path.join(root, *SESSIONS.split("/"))):
        lapse(root, {p for _, p, _ in found} | {o for _, _, o in found if o})
    records = sessions(root)
    return [(status, path, old, holder(records, path)) for status, path, old in found]


# ---- URLs ----

URL = re.compile(r"https?://[^\s<>()\[\]|\"'`]+")
URL_TRAILING = ".,;:!?*_~"


def clean_url(url):
    """A URL as found in text, less the punctuation a sentence or Markdown put after it."""
    return url.strip().rstrip(URL_TRAILING)


def urls(text):
    """The URLs in the text, in order, each as clean_url() gives it."""
    return [clean_url(u) for u in URL.findall(text)]


# ---- An HTML page's text, and a time in this machine's zone (#791) ----

HTML_HIDDEN = {"script", "style", "noscript", "template", "svg", "title"}
HTML_BLOCKS = {"address", "article", "blockquote", "br", "dd", "div", "dl", "dt", "footer", "h1", "h2", "h3", "h4",
               "h5", "h6", "header", "hr", "li", "main", "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul"}


class HtmlText(html.parser.HTMLParser):
    """An HTML page as its reader sees it: a line per block, nothing from HTML_HIDDEN (or the caller's
    extra hidden tags), the spaces and line breaks in the markup's text read as one space, as a browser
    does, except inside <pre>. With marks, a list item starts with `- ` and a table's cells on one row
    are joined by tabs."""
    def __init__(self, hide=(), marks=False):
        super().__init__(convert_charrefs=True)
        self.hiding, self.marks = HTML_HIDDEN | set(hide), marks
        self.parts, self.hidden, self.pre = [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.pre += 1
        if tag in self.hiding:
            self.hidden += 1
        elif self.marks and tag == "li":
            self.parts.append("\n- ")
        elif self.marks and tag in ("td", "th"):
            self.parts.append("\t")
        elif tag in HTML_BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "pre":
            self.pre = max(0, self.pre - 1)
        if tag in self.hiding:
            self.hidden = max(0, self.hidden - 1)
        elif self.marks and tag in ("li", "td", "th"):   # the next item's `- ` or cell's tab follows on
            pass
        elif tag in HTML_BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data.replace("\r\n", "\n") if self.pre else re.sub(r"[ \t\r\n\f]+", " ", data))


def html_text(markup, hide=(), marks=False):
    """The text of an HTML page or mail part (HtmlText), each line stripped of spaces; blank lines kept,
    for the caller to drop or squeeze."""
    p = HtmlText(hide, marks)
    p.feed(markup)
    p.close()
    return "\n".join(line.strip(" ") for line in "".join(p.parts).split("\n"))


def local_time(when):
    """A timestamp as an aware datetime in this machine's time zone. `when` is an ISO 8601 string or
    a datetime: one with a zone (`Z`, `+05:30`, `-0800`) is converted; one without is taken as this
    machine's time already. A citation's `(user, YYYY-MM-DD)` is this time's date (SKILL.md)."""
    return (datetime.datetime.fromisoformat(when) if isinstance(when, str) else when).astimezone()


# ---- Claude Code's project folders ----

def projects_dir(given=None):
    """Claude Code's projects folder: given, else CLAUDE_CONFIG_DIR's or ~/.claude's `projects`."""
    if given:
        return given
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def fold(name):
    return name.lower() if os.name == "nt" else name  # a Windows drive letter's case varies


def folder_name(path):
    """A project folder name for an absolute path: every character outside [A-Za-z0-9] becomes '-'
    (`/Users/me/Repos/career-log` -> `-Users-me-Repos-career-log`). The one copy of the rule."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def claude_folder(path):
    """Claude Code's project folder name for a working directory. On macOS and Linux, Claude Code
    names it from its resolved working directory, so the path is resolved first (os.path.realpath:
    a checkout reached through a symlink, or macOS's /tmp, which is /private/tmp, gets the name of
    its real path; #788). Whether Claude Code resolves on Windows is not verified, so there the path
    is named as given (os.path.abspath), as before #788: realpath there can swap a subst or mapped
    drive for its target, or a short 8.3 name for the long one, and find_project_folder tries the
    resolved name as well."""
    return folder_name(os.path.abspath(path) if os.name == "nt" else os.path.realpath(path))


def folder_of(name, slug):
    """Whether a project folder is the one for the path with this slug; a long name is cut and given a suffix."""
    return fold(name) == fold(slug) or (len(slug) > 200 and fold(name).startswith(fold(slug[:200])))


def find_project_folder(projects, path):
    """The folder under projects that Claude Code keeps for a working directory (an exact name first,
    then, for a path over 200 characters, the first folder its cut name starts), or None. Claude Code
    names it from its resolved working directory, so a path reached through a symlink (macOS's /var is
    /private/var) is tried as given, then resolved (#768): a folder an older tool named from the path as
    given is still found first."""
    names = sorted(os.listdir(projects)) if os.path.isdir(projects) else []
    for slug in dict.fromkeys((folder_name(os.path.abspath(path)), folder_name(os.path.realpath(path)))):
        exact = [n for n in names if fold(n) == fold(slug)]
        near = [n for n in names if len(slug) > 200 and fold(n).startswith(fold(slug[:200]))]
        found = (exact or near)[:1]
        if found:
            return os.path.join(projects, found[0])
    return None
