"""The helpers the Log's tools share: reading and writing its files, front matter, Markdown tables
and sections, heading anchors, slugs, dated names, git, the Log's root and its own files, the
applications it records, the URLs in a text, and Claude Code's project folder for a checkout.

A library, with no command line. A tool beside it imports it with
  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I leaves this folder off sys.path
  sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
  import logfiles

What an entry is (ENTRY_PATH, entry_paths, Entry, the Story model) stays in entries.py.
Standard library only. It imports on any Python 3 (tools/check.py imports it before it says that
the Log needs 3.11+), so nothing here needs a newer one at import time.
"""
import glob
import os
import re
import subprocess
import sys


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


def md_row(cells):
    """A table row from cells, with `|` written as `\\|` and line ends as spaces."""
    return "| " + " | ".join(str(c).replace("|", "\\|").replace("\r", "").replace("\n", " ")
                             for c in cells) + " |"


def is_rule(cells):
    """The `|---|:--:|` row under a table's header (an empty row reads as one too)."""
    return set("".join(cells)) <= set("-: ")


class Table:
    """A Markdown table: head (its header cells as written), header (the same, lowercased, without
    `*` and backticks), rows [(line number, cells)] (the rule row left out), line (the header's line
    number, from 1) and section (the last `## ` heading's text above it, or None)."""

    def __init__(self, line, section, head):
        self.line, self.section, self.head, self.rows = line, section, head, []
        self.header = [h.strip("*` ").lower() for h in head]

    def dicts(self):
        """Each row as {lowercased header: cell}."""
        return [dict(zip(self.header, cells)) for _, cells in self.rows]


def md_tables(text):
    """Each table in the text, in order: a run of lines that start with `|` (after spaces), its first
    row the header."""
    tables, current, section = [], None, None
    for n, line in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.strip().startswith("|"):
            current = None
            continue
        cells = md_cells(line)
        if current is None:
            current = Table(n, section, cells)
            tables.append(current)
        elif not is_rule(cells):
            current.rows.append((n, cells))
    return tables


def strip_comments(text):
    """The text without its HTML comments."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def section(text, heading, level=2):
    """The body of the first `## <heading>` (with level 2) heading in the text, up to the next heading
    of that level or a higher one other than `# ` (`### ` ends at `## ` or `### `), or the end; None
    when there is no such heading. The heading may be the text's last line. A `# ` line does not end
    it: in a code block it is a comment."""
    span = section_span(text, heading, level)
    return text[span[0]:span[1]] if span else None


def section_span(text, heading, level=2):
    """(start, end) of the body section() returns, as offsets into the text; None when there is no
    such heading. A tool that rewrites a section's lines splices them in here."""
    marks = "#" * level
    m = re.search(r"^%s %s[ \t]*$\n?(.*?)(?=^#{2,%d} |\Z)" % (marks, re.escape(heading), max(level, 2)),
                  text, re.M | re.S)
    return m.span(1) if m else None


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


def heading_names(text):
    """{anchor: heading text} for the headings heading_anchors() reads."""
    out, seen, fence = {}, {}, None
    for line in strip_comments(text).splitlines():
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


def ascii_slug(text):
    """Text as an ASCII name: lowercase letters and digits, each run of anything else one `-`, none
    at the ends; '' when nothing is left."""
    return "-".join(re.sub(r"[^0-9a-z]+", " ", (text or "").lower()).split())


def split_dated(name):
    """(date, rest) for a name `<YYYY-MM-DD>-<rest>`, else (None, name)."""
    m = DATED.match(name)
    return (m.group(1), m.group(2)) if m else (None, name)


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


def tex_items(text):
    """(line number, text) of each `\\item` in a .tex file, comments dropped: the text after it (and
    its optional `[...]`) up to the next `\\item`, `\\begin`, `\\end` or an empty line, whitespace
    collapsed, LaTeX left as written."""
    out, current = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"(?<!\\)%.*$", "", raw)
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


NO_BULLETS = ("education", "skill")   # the resume skeleton's sections whose items are no bullet
BULLETS = ("experience", "project")


def tex_bullets(text):
    """tex_items less the items under a `\\section` whose title holds "education" or "skill" (a
    coursework line, a Skills row) and neither "experience" nor "project" (`Experience and Skills`
    keeps its bullets): an experience or project bullet, under any other heading, is what feeds
    Past phrasings. A bold label is no sign: `\\textbf{Topic:} Built ...` starts many a bullet."""
    sections = []
    for n, raw in enumerate(text.splitlines(), 1):
        m = re.search(r"\\section\*?\{([^}]*)\}", re.sub(r"(?<!\\)%.*$", "", raw))
        if m:
            sections.append((n, m.group(1).lower()))
    def heading(n):
        return next((title for at, title in reversed(sections) if at <= n), "")
    def kept(title):
        return any(w in title for w in BULLETS) or not any(w in title for w in NO_BULLETS)
    return [(n, item) for n, item in tex_items(text) if kept(heading(n))]


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
    """The bytes of path at rev (`git show <rev>:<path>`), or None when rev has no such file;
    LogError when git cannot start or gives no answer in time."""
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


def application_records(root):
    """[(text, match, where)] for each `outputs/applications/*/` folder and each `applications.md`
    line: text is the folder's `posting.md` (or '') or the line, and match(company, role, city), on
    norm() text, is whether the record names that company and role. A folder matches when its name,
    less its date, is the company and then the role, and its posting text, when it has one, holds
    the city (when given); an applications.md table row when a cell equals the company and one the
    role."""
    out = []
    for d in sorted(glob.glob(os.path.join(root, "outputs", "applications", "*"))):
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


# ---- URLs ----

URL = re.compile(r"https?://[^\s<>()\[\]|\"'`]+")
URL_TRAILING = ".,;:!?*_~"


def clean_url(url):
    """A URL as found in text, less the punctuation a sentence or Markdown put after it."""
    return url.strip().rstrip(URL_TRAILING)


def urls(text):
    """The URLs in the text, in order, each as clean_url() gives it."""
    return [clean_url(u) for u in URL.findall(text)]


# ---- Claude Code's project folders ----

def projects_dir(given=None):
    """Claude Code's projects folder: given, else CLAUDE_CONFIG_DIR's or ~/.claude's `projects`."""
    if given:
        return given
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def fold(name):
    return name.lower() if os.name == "nt" else name  # a Windows drive letter's case varies


def claude_folder(path):
    """Claude Code's project folder name for a working directory: every character outside [A-Za-z0-9]
    becomes '-' (`/Users/me/Repos/career-log` -> `-Users-me-Repos-career-log`). The one copy of the rule."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path))


def folder_of(name, slug):
    """Whether a project folder is the one for the path with this slug; a long name is cut and given a suffix."""
    return fold(name) == fold(slug) or (len(slug) > 200 and fold(name).startswith(fold(slug[:200])))


def find_project_folder(projects, path):
    """The folder under projects that Claude Code keeps for a working directory (an exact name first,
    then, for a path over 200 characters, the first folder its cut name starts), or None."""
    slug = claude_folder(path)
    names = sorted(os.listdir(projects)) if os.path.isdir(projects) else []
    exact = [n for n in names if fold(n) == fold(slug)]
    near = [n for n in names if len(slug) > 200 and fold(n).startswith(fold(slug[:200]))]
    found = (exact or near)[:1]
    return os.path.join(projects, found[0]) if found else None
