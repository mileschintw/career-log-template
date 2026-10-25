#!/usr/bin/env python3
r"""Build a resume .tex locally and check its layout.

    python3 -I tools/resume.py <file.tex> [--out DIR] [--pages N] [--install-missing] [--no-png]
                               [--same-layout <start.tex>]
    python3 -I tools/resume.py --check <file.pdf> [--out DIR] [--pages N] [--no-png]
    python3 -I tools/resume.py <a.pdf> --same-text <b.pdf>
    python3 -I tools/resume.py --stale <folder>
    python3 -I tools/resume.py --baseline
(Windows: py -3 -I tools/resume.py ...) Each takes --root <root>, the Log's root (default: the folder
above this script's): its config.toml gives the page limit and its .build/ holds the scratch dirs. A
relative path is read from the current folder.

Build: first a scan of the .tex's document body, comments aside, with one `FAIL: source line <n>:`
line per hit: a `<...>` placeholder left; outside math, an \href or \url address, and for & a
tabular: an unescaped & # or _, a $ before a digit, or a % right after a digit (it starts a
comment, so the % and the rest of the line vanish); a Unicode en or em dash, written -- or ---
instead. Then pdflatex
in a scratch dir, and the PDF copied next to the .tex. The default dir is
<root>/.build/resume/<folder>-<stem>-<hash>/, named after the .tex's folder and stem plus a hash of
its full path, so drafts that share a name (every draft is resume.tex) each build in their own and
never read each other's PDF or log. With --install-missing, packages reported missing are installed
with tlmgr and the build is retried; each one installed that tools/tex-packages.txt does not list
prints `add to tools/tex-packages.txt: <package>` (an Engine change, so the next machine gets it).
--same-layout <start.tex> also fails, with one `FAIL: layout ...` line each, on a preamble line or a
spacing, font or geometry command (\setlength, \setlist, \linespread, \fontsize, \geometry,
\titleformat, \titlespacing and the like) that differs from the version the draft started from;
\vspace nudges do not count, nor does an added line that only loads packages, none of them a
layout or font one (geometry, parskip, setspace, microtype, a font family: LAYOUT_PACKAGES) or a
local file.

Check (always runs after a build), one `FAIL:` line each: more pages than the limit (resume_max_pages
in config.toml, default 1; --pages N for this run; the line names the limit and where it came from),
a bullet over 2 lines, a wrapped bullet whose last line fills under 60% of the width (a dangling
line), a line of the Skills section that wraps (its labels read from the .tex beside the PDF: a
line's first \textbf{} and each one right after a \\ on it, with no word before it, so a mark such
as \checkmark may come first; a row above every label fails as one with no label the check can
read), a log line over
1pt too wide (overfull box), no email address or garbage glyphs in the text layer. An email left
as a GAP (a line holding `GAP: email` or `Email: GAP`) fails as `email: GAP (needs you): <that
line>` instead, so a scan draft can tell it from a lost address. `note:` lines
give each page's bullets and bottom slack, dates in en dashes (some ATS imports drop them), the
page images (<stem>-<page>.png beside the PDF, unless --no-png) and the text layer in reading
order, the order an ATS reads it (<stem>.txt in the scratch dir; read it). Needs only the standard
library plus TinyTeX and poppler (tools/setup.sh or tools/setup.ps1 installs both: poppler only
when the user has none of their own).

Same text: exit 0 when two PDFs hold the same words in the same order (whitespace and line breaks
ignored, so a rebuild after a toolchain update still matches), 1 when they differ, with the first
difference shown, or when either has no text layer.

Stale: each <target>.tex in <folder> (outputs/resumes/) is copied to <root>/.build/audit/<target>/,
with the files beside it that it \input's or \include's, built there and compared with the <target>.pdf beside it, as --same-text does: one
`<target>: same text (<n> words)` or `FAIL: <target>: <why>` line each (a folder with no .tex: one
`note:` line; a .tex with no .pdf that another one there \input's or \include's: a `note:` line
saying it is part of that one). A build that stops on a file not found, with no such file beside the .tex, prints
`FAIL: <target>: this machine lacks <file>, so <target>.tex was not compared: <the command that
installs it>` in place of `does not build`. Audit uses it to catch a committed PDF built from something else.

Baseline: builds the example resume (skills/career-log/examples/resume.tex) in <root>/.build/verify/,
checks it, and compares its page with the one SETUP.md step 6 expects (bullets, text block, bottom
slack within 1pt); the last line is `baseline: OK` or `FAIL: baseline: <what differs>`, a failed pdflatex run included.

Exit 0 when every check passes, 1 when one fails, 2 when the build fails, pdftotext fails, TinyTeX
or poppler is not found, or an option is wrong.

Runs on macOS, Linux and Windows. Binaries are found in TINYTEX_BIN and POPPLER_BIN
first, then in the default install locations, then on PATH. PATH comes last because
on Windows it often holds copies setup did not install: Git for Windows ships xpdf's
pdftotext (no -bbox-layout), and an older TeX Live may sit ahead of TinyTeX. Setup's own
poppler (a micromamba environment in ~/.career-log/poppler) comes after PATH, so a poppler of the
user's own always wins. pdfinfo and pdftoppm come from the folder of the pdftotext found.
"""
import argparse
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles

MAX_PAGES = 1           # the page limit when config.toml cannot give one
MAX_BULLET_LINES = 2
DANGLING_RATIO = 0.60   # last line of a wrapped bullet filling < 60% of the width
# A Skills row with no label wraps from the row above only if that row's gap to the right edge could
# not hold the row's first word plus this much (pt): ragged-right text may break early
SKILLS_REACH_MARGIN = 36
OVERFULL_PT = 1.0       # overfull \hbox warnings above this many points
BULLET = "•"
EXAMPLE = os.path.join("skills", "career-log", "examples", "resume.tex")
# What SETUP.md step 6 expects of the example's page: its bullets, the text block's left and right
# edges, and the bottom slack, within SLACK_PT.
BASELINE = {"bullets": 6, "left": 36, "right": 576, "slack": 321}
SLACK_PT = 1


WINDOWS = os.name == "nt"
SETUP_HINT = "Run tools\\setup.ps1 first." if WINDOWS else "Run tools/setup.sh first."
# A packaged app (the Claude desktop app) keeps a folder its processes create in %APPDATA% in its own
# store, where a process started outside the package (its PowerShell tool, the python3 alias) does not
# see it as %APPDATA%; the store path itself works from anywhere (#152). The glob matches every
# packaged app's store, so the Engine names no product.
APPDATA_STORE = "%LOCALAPPDATA%/Packages/*/LocalCache/Roaming/"


def _search(name, env_var, patterns, usable=lambda path: True, last=()):
    """$env_var, then each glob pattern, then PATH, then the folders in `last`; tries Windows
    extensions too."""
    names = [name + ext for ext in (".exe", ".bat", ".cmd")] if WINDOWS else [name]
    dirs = [os.environ[env_var]] if os.environ.get(env_var) else []
    for pattern in patterns:
        dirs += map(os.path.normpath, sorted(glob.glob(os.path.expandvars(os.path.expanduser(pattern)))))
    dirs += os.environ.get("PATH", "").split(os.pathsep)
    dirs += last
    for d in filter(None, dirs):
        for n in names:
            path = os.path.join(d, n)
            if os.path.isfile(path) and os.access(path, os.X_OK) and usable(path):
                return path
    return None


def no_error_dialogs():
    """On Windows, a program that cannot load a DLL (a poppler without the Visual C++ runtime) fails
    at once, with no dialog waiting for a click; the programs this process starts inherit the mode
    (#285). tools/setup.ps1 sets the same mode for itself."""
    if WINDOWS:
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x8003)


def _has_bbox_layout(pdftotext):
    """poppler's pdftotext has -bbox-layout; xpdf's (Git for Windows ships one) does not."""
    no_error_dialogs()
    try:
        run = subprocess.run([pdftotext, "-h"], capture_output=True, text=True, errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "-bbox-layout" in run.stdout + run.stderr


def tex_bin(name):
    """The TeX binary tools/resume.py would use, or None."""
    return _search(name, "TINYTEX_BIN", [
        "~/Library/TinyTeX/bin/*/", "~/.TinyTeX/bin/*/",
        APPDATA_STORE + "TinyTeX/bin/windows/", "%APPDATA%/TinyTeX/bin/windows/", "%ProgramData%/TinyTeX/bin/windows/"])


def poppler_env(home=None):
    """The micromamba environment setup installs conda-forge's poppler into (#281)."""
    return os.path.join(home or os.path.expanduser("~"), ".career-log", "poppler")


def poppler_env_bin(home=None):
    return os.path.join(poppler_env(home), "Library", "bin") if WINDOWS else os.path.join(poppler_env(home), "bin")


def _sibling(path, name):
    """The program `name` in the folder of `path`, or None."""
    exts = (".exe", ".bat", ".cmd") if WINDOWS else ("",)
    return next((p for p in (os.path.join(os.path.dirname(path), name + ext) for ext in exts)
                 if os.path.isfile(p) and os.access(p, os.X_OK)), None)


def poppler_bin(name, home=None):
    """The poppler binary tools/resume.py would use, or None: pdftotext as found, and pdfinfo or
    pdftoppm from its folder, so they always come from one install. A pdftotext with no pdftoppm
    beside it (the check's page images need it) is passed over."""
    pdftotext = _search("pdftotext", "POPPLER_BIN", [
        "%LOCALAPPDATA%/Microsoft/WinGet/Packages/*Poppler*/*/Library/bin/",
        "%LOCALAPPDATA%/Microsoft/WinGet/Packages/*Poppler*/*/bin/",
        "~/scoop/apps/poppler/current/Library/bin/", "~/scoop/apps/poppler/current/bin/",
        "%ProgramData%/chocolatey/bin/",
        # Homebrew's: not on PATH in a shell that did not load Homebrew's shellenv
        "/opt/homebrew/bin/", "/usr/local/bin/"],
        lambda path: _sibling(path, "pdftoppm") and _has_bbox_layout(path), last=[poppler_env_bin(home)])
    if not pdftotext or name == "pdftotext":
        return pdftotext
    return _sibling(pdftotext, name)


def find_tex_bin(name):
    found = tex_bin(name)
    if not found:   # exit 2, not 1: 1 means a check failed
        print(f"{name} not found. {SETUP_HINT}", file=sys.stderr)
        sys.exit(2)
    return found


def find_poppler_bin(name):
    found = poppler_bin(name)
    if not found:
        print(f"{name} (poppler) not found. {SETUP_HINT}", file=sys.stderr)
        sys.exit(2)
    return found


def default_outdir(tex, root=None):
    """<root>/.build/resume/<folder>-<stem>-<hash>: one scratch dir per .tex, the same one on every rebuild."""
    path = os.path.abspath(tex)
    folder = os.path.basename(os.path.dirname(path))
    stem = os.path.splitext(os.path.basename(path))[0]
    # normcase: on Windows, two spellings of one path are one file, so they share one dir
    digest = hashlib.sha1(os.path.normcase(path).encode("utf-8")).hexdigest()[:8]
    return os.path.join(root or logfiles.default_root(__file__), ".build", "resume",
                        "-".join(p for p in (folder, stem, digest) if p))


def page_limit(root, pages=None):
    """(limit, where it came from): --pages, then the Log's config.toml (resume_max_pages)."""
    if pages is not None:
        return pages, "--pages"
    import config, tomllib
    try:
        loaded = config.load(root)
        if loaded is None:
            return config.defaults()["resume_max_pages"], "default"
        value, is_default = loaded["resume_max_pages"]
        return value, "default" if is_default else "config.toml"
    except config.ConfigError as e:
        problem = e
    try:   # another field's bad value leaves this one usable
        value = tomllib.loads(logfiles.read_text(config.path(root)))["resume_max_pages"]
        config.check_value("resume_max_pages", value)
        return value, "config.toml"
    except (OSError, ValueError, KeyError, config.ConfigError):   # ValueError: TOML or UTF-8
        print(f"warning: {problem}; using the default page limit")
        return MAX_PAGES, "default"


# ---- The source ----

def comment_at(line):
    """Where the line's comment starts: the first % after an even number of backslashes (\\\\% is a
    line break, then a comment) and outside an \\href or \\url address, or None."""
    addresses = [m.span() for m in ADDRESS.finditer(line)]
    for m in re.finditer("%", line):
        run = len(line[:m.start()]) - len(line[:m.start()].rstrip("\\"))
        if run % 2 == 0 and not any(a <= m.start() < b for a, b in addresses):
            return m.start()
    return None


def uncomment(line):
    at = comment_at(line)
    return line if at is None else line[:at]


ADDRESS = re.compile(r"\\(href|url)\{[^}]*\}")
TABULAR = re.compile(r"\\(begin|end)\{(tabular\*?|tabularx|array|align\*?)\}")
# The body's commands that set spacing, font or geometry; \vspace is not one
LAYOUT = re.compile(r"\\(setlength|addtolength|setlist|linespread|fontsize|selectfont|geometry|newgeometry|"
                    r"titleformat|titlespacing|renewcommand)\b")
# Packages (.sty names, lowercase) whose loading alone changes the page, the spacing, the line breaks
# or the font, so --same-layout fails an added \usepackage of one; any other package only brings in
# commands (amssymb, xcolor, tabularx). Never complete: the PNG read (latex.md) catches the rest.
LAYOUT_PACKAGES = {
    # page, spacing, paragraphs, line breaks, headers
    "geometry", "fullpage", "savetrees", "vmargin", "anysize", "typearea", "a4wide", "a4", "scrextend",
    "parskip", "setspace", "indentfirst", "microtype", "ragged2e", "hyphenat", "babel", "polyglossia",
    "fancyhdr", "sectsty", "nopageno", "ulem", "showframe", "lineno", "draftwatermark",
    # font selection and sizes
    "fontenc", "fontspec", "unicode-math", "mathspec", "xltxtra", "anyfontsize", "type1cm", "fix-cm",
    # font families
    "lmodern", "mlmodern", "cfr-lm", "xcharter", "charter", "libertine", "libertinus", "libertinust1math",
    "helvet", "times", "mathptmx", "mathpazo", "palatino", "courier", "avant", "bookman", "newcent",
    "chancery", "utopia", "fourier", "fouriernc", "erewhon", "heuristica", "kpfonts", "cmbright",
    "newtxtext", "newtxmath", "newpxtext", "newpxmath", "stix", "stix2", "ebgaramond", "garamondx",
    "cochineal", "crimson", "crimsonpro", "gentium", "baskervillef", "librebaskerville", "mathdesign",
    "bera", "beramono", "inconsolata", "sourcesanspro", "sourceserifpro", "sourcecodepro", "roboto",
    "lato", "opensans", "raleway", "montserrat", "merriweather", "firasans", "firamono", "plex-sans",
    "plex-serif", "plex-mono", "paratype", "ptsans", "ptserif", "dejavu", "dejavusans", "dejavuserif",
    "arev", "iwona", "kurier", "antpolt", "noto", "noto-sans", "noto-serif", "inter", "cabin",
    "carlito", "alegreya", "eulervm", "sfmath", "txfonts", "pxfonts", "newtx", "ccfonts", "fontsetup",
    "nimbussans", "nimbusserif", "nimbusmono",
    # CJK fonts and spacing
    "ctex", "xecjk", "cjkutf8", "cjk", "luatexja", "luatexja-fontspec",
}


def body(text):
    """(line number, the line with its comment dropped, the raw line) of each line after
    \\begin{document}; the whole file when it has none."""
    lines = text.splitlines()
    start = next((i + 1 for i, l in enumerate(lines) if "\\begin{document}" in uncomment(l)), 0)
    return [(n + 1, uncomment(lines[n]), lines[n]) for n in range(start, len(lines))]


def scan_source(text):
    """`source line <n>: ...` for each placeholder, unescaped special character or Unicode dash in
    the document body."""
    out, table = [], 0
    for n, code, raw in body(text):
        marks = [m.group(1) for m in TABULAR.finditer(code)]
        in_table = table > 0 or "begin" in marks   # & is a column break there
        table += marks.count("begin") - marks.count("end")
        for m in re.finditer(r"(?<!\w)(?<!::)<[A-Za-z][^<>]*>", code):   # not std::vector<int>, parse::<T>
            out.append(f"source line {n}: placeholder {m.group(0)} left; replace it with a fact from an entry")
        bare = ADDRESS.sub("", raw)
        at = comment_at(bare)
        if at and bare[at - 1].isdigit():
            out.append(f"source line {n}: {bare[max(0, at - 8):at + 1].strip()} starts a comment, so the "
                       "% and the rest of the line are dropped; write \\% for a percentage")
        # math holds a command, ^ or _, or no space ($\sim$, $10^6$, $>$); "$2M to $1M" is two dollar signs
        text_only = re.sub(r"(?<!\\)\$(?:[^$]*[\\^_][^$]*|[^$\s]+)(?<!\\)\$", "", ADDRESS.sub("", code))
        if re.search(r"(?<!\\)\$(?=\d)", text_only):
            out.append(f"source line {n}: unescaped $ before a number; write \\$")
        for ch in "#_" + ("" if in_table else "&"):
            if re.search(r"(?<!\\)" + re.escape(ch), text_only):
                out.append(f"source line {n}: unescaped {ch}; write \\{ch}")
        for dash, tex in (("–", "--"), ("—", "---")):
            if dash in code:
                out.append(f"source line {n}: Unicode {dash}; write {tex}, as every version does")
    return out


def plain(tex):
    """A short piece of LaTeX as its text: commands' braces dropped, escapes undone."""
    tex = re.sub(r"\\(textbf|textit|emph|underline)\{([^{}]*)\}", r"\2", tex)
    tex = re.sub(r"\\([&%$#_{}])", r"\1", tex).replace("---", "—").replace("--", "–")
    tex = re.sub(r"\\[A-Za-z]+\*?", "", tex)   # any other command: \textsc, \large
    return " ".join(tex.replace("{", "").replace("}", "").split())


# A \\ line break (\\*, \\[2pt]) or a \newline inside a source line
LINE_BREAK = re.compile(r"\\\\\*?(?:\s*\[[^\]]*\])?|\\newline(?![A-Za-z])")


def skills_of(text):
    """(the Skills heading, each Skills line's label, every section heading) from the .tex, or None
    when no section's title holds "skill". A label starts the source line or follows a \\\\ or a
    \\newline on it."""
    headings, title, labels, inside = [], None, [], False
    for _, code, _ in body(text):
        m = re.search(r"\\section\*?\{([^}]*)\}", code)
        if m:
            headings.append(plain(m.group(1)))
            inside = "skill" in m.group(1).lower() and title is None
            title = headings[-1] if inside else title
            continue
        for part in LINE_BREAK.split(code) if inside else ():   # several Skills lines on one source line
            label = re.match(r"\s*(?:\\item\s*)?([^,]*?)\\textbf\{([^{}]*)\}", part)
            if label and not re.search(r"\w", plain(label.group(1))):   # a mark before it: \checkmark\
                labels.append(plain(label.group(2)))
    return (title, labels, headings) if title else None


def layout_lines(text):
    """{normalized line: its line number} of the lines that set the layout: every preamble line,
    and the body's spacing, font and geometry commands."""
    out, in_body = {}, False
    for n, raw in enumerate(text.splitlines(), 1):
        code = " ".join(uncomment(raw).split())
        if "\\begin{document}" in code:
            in_body = True
            continue
        if code and (not in_body or LAYOUT.search(code)):
            out.setdefault(code, n)
    return out


def same_layout(tex_text, start_text, start_name):
    a, b = layout_lines(tex_text), layout_lines(start_text)

    def commands_only(line):
        """A bare \\usepackage line none of whose packages is in LAYOUT_PACKAGES, a TeX Gyre font
        (tg...) or a local file (a path: it can set anything), matched without case (Windows finds
        XCharter.sty for xcharter): not a layout change."""
        m = re.fullmatch(r"\\usepackage(?:\[[^\]]*\])?\{([^{}]*)\}", line)
        names = [p.strip().lower() for p in m.group(1).split(",")] if m else []
        return bool(m) and not any(p in LAYOUT_PACKAGES or p.startswith("tg") or "/" in p for p in names)
    return ([f"layout: line {n} is not in {start_name}: {line}" for line, n in a.items()
             if line not in b and not commands_only(line)]
            + [f"layout: line {n} of {start_name} is gone: {line}" for line, n in b.items() if line not in a])


# ---- Build ----

class BuildFailed(Exception):
    def __init__(self, tex, missing=None):
        super().__init__(tex)
        self.missing = missing   # the file pdflatex found missing (`File `<name>' not found`), if any


def listed_packages():
    try:
        text = logfiles.read_text(os.path.join(HERE, "tex-packages.txt"))
    except (OSError, UnicodeDecodeError):
        return set()
    return {l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")}


def build(tex, outdir, install_missing):
    """(the PDF next to the .tex, the log); prints the errors and raises BuildFailed when pdflatex fails."""
    pdflatex = find_tex_bin("pdflatex")
    # Another TeX can build the baseline to the same bottom slack, so the numbers alone do not show it
    chosen = os.environ.get("TINYTEX_BIN")
    on_purpose = chosen and os.path.normcase(os.path.dirname(os.path.abspath(pdflatex))) == \
        os.path.normcase(os.path.abspath(chosen))
    if not on_purpose and "tinytex" not in os.path.realpath(pdflatex).lower():
        print(f"warning: building with {pdflatex}, not TinyTeX. {SETUP_HINT}"
              " To use this TeX on purpose, set TINYTEX_BIN to its bin folder.")
    outdir = os.path.abspath(outdir)  # pdflatex runs from the .tex folder, so a relative path would point elsewhere
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(tex))[0]
    cmd = [pdflatex, "-interaction=nonstopmode", "-halt-on-error",
           f"-output-directory={outdir}", os.path.basename(tex)]
    installed = []
    for _ in range(10):
        run = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(tex)),
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        missing = re.search(r"File `([^']+)' not found", run.stdout)
        if run.returncode == 0 or not (missing and install_missing):
            break
        tlmgr = find_tex_bin("tlmgr")
        hit = subprocess.run([tlmgr, "search", "--global", "--file", "/" + missing.group(1)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        pkg = next((l.rstrip(":") for l in hit.splitlines()
                    if l and not l.startswith(("tlmgr", " ", "\t"))), None)
        if not pkg:
            print(f"tlmgr found no package providing {missing.group(1)}")
            break
        print(f"installing {pkg} for {missing.group(1)}")
        inst = subprocess.run([tlmgr, "install", pkg], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if inst.returncode != 0:
            print(f"tlmgr install {pkg} failed (exit {inst.returncode}): {(inst.stderr or inst.stdout).strip()[-500:]}")
            break
        installed.append(pkg)
    listed = listed_packages()
    for pkg in installed:
        if pkg not in listed:
            print(f"add to tools/tex-packages.txt: {pkg}")
    log_path = os.path.join(outdir, stem + ".log")
    if run.returncode != 0:
        errors = [l for l in run.stdout.splitlines() if l.startswith("!") or re.match(r"l\.\d+", l)]
        print("BUILD FAILED")
        print("\n".join(errors[:10]) or run.stdout[-2000:])
        if missing and not install_missing:
            print("Missing package file; rerun with --install-missing.")
        raise BuildFailed(tex, missing.group(1) if missing else None)
    pdf = os.path.join(outdir, stem + ".pdf")
    final = os.path.join(os.path.dirname(os.path.abspath(tex)), stem + ".pdf")
    shutil.copyfile(pdf, final)
    return final, log_path


# ---- Reading the PDF ----

def lines_of(pdf):
    run = subprocess.run([find_poppler_bin("pdftotext"), "-enc", "UTF-8", "-bbox-layout", pdf, "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if run.returncode != 0:   # a tool failure, not a layout failure: exit 2 like a failed build
        print(f"pdftotext failed (exit {run.returncode}): {run.stderr.strip()[:500]}")
        sys.exit(2)
    xml = run.stdout
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", xml).replace('xmlns="http://www.w3.org/1999/xhtml"', "")
    root = ET.fromstring(xml)
    pages = []
    for page in root.iter("page"):
        rows = []
        for ln in page.iter("line"):
            text = " ".join(w.text or "" for w in ln.iter("word"))
            rows.append({k: float(ln.get(k)) for k in ("xMin", "xMax", "yMin", "yMax")} | {"text": text})
        # pdftotext may split one visual line into several (a bullet glyph, a right-aligned
        # date); merge lines whose tops are within 2pt into one row
        merged = []
        for r in sorted(rows, key=lambda r: (r["yMin"], r["xMin"])):
            if merged and abs(r["yMin"] - merged[-1]["yMin"]) < 2:
                m = merged[-1]
                m["xMin"], m["xMax"] = min(m["xMin"], r["xMin"]), max(m["xMax"], r["xMax"])
                m["yMax"] = max(m["yMax"], r["yMax"])
                m["text"] = (m["text"] + " " + r["text"]) if r["xMin"] >= m["xMin"] else (r["text"] + " " + m["text"])
            else:
                merged.append(dict(r))
        pages.append({"w": float(page.get("width")), "h": float(page.get("height")), "lines": merged})
    return pages


def words_of(pdf):
    run = subprocess.run([find_poppler_bin("pdftotext"), "-enc", "UTF-8", pdf, "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if run.returncode != 0:
        print(f"pdftotext failed on {pdf} (exit {run.returncode}): {run.stderr.strip()[:500]}")
        sys.exit(2)
    return run.stdout.split()


def compare_text(a, b):
    """(same, what to say): the same words in the same order, as --same-text compares them."""
    wa, wb = words_of(a), words_of(b)
    blank = [p for p, w in ((a, wa), (b, wb)) if not w]
    if blank:  # two blank PDFs would otherwise "match"
        return False, "no text layer in " + ", ".join(blank)
    if wa == wb:
        return True, f"same text ({len(wa)} words)"
    i = next((i for i, (x, y) in enumerate(zip(wa, wb)) if x != y), min(len(wa), len(wb)))
    return False, f"text differs at word {i}: {' '.join(wa[i:i + 8])!r} vs {' '.join(wb[i:i + 8])!r}"


def same_text(a, b):
    same, said = compare_text(a, b)
    print(said if same else "FAIL: " + said)
    return same


# ---- The checks ----

def bullets_of(rows):
    """The page's bullets, each a list of its rows: a bullet line starts with "•"; continuation
    lines sit indented right of the bullet glyph and start before the next bullet or heading."""
    bullets, cur = [], None
    for r in sorted(rows, key=lambda r: (r["yMin"], r["xMin"])):
        if r["text"].startswith(BULLET):
            cur = [r]
            bullets.append(cur)
        elif cur and r["xMin"] > cur[0]["xMin"] + 4 and r["yMin"] - cur[-1]["yMin"] < 20:
            cur.append(r)
        else:
            cur = None
    return bullets


def summary(page):
    """(bullets, the text block's left and right edges, bottom slack in pt) of a page that has text."""
    rows = page["lines"]
    return (len(bullets_of(rows)), min(r["xMin"] for r in rows), max(r["xMax"] for r in rows),
            page["h"] - max(r["yMax"] for r in rows))


def label_at(item, labels):
    """The label a Skills row starts with, after at most a short mark (✓, –) and no word; else None."""
    for l in labels:
        i = item.find(l)
        if i >= 0 and len(item[:i].strip()) <= 3 and not re.search(r"\w", item[:i]):
            return l
    return None


def skills_wraps(pages, skills):
    """(fails, notes): a `Skills line wraps` fail for each row of the Skills section that starts
    with none of its labels and that the row above could have run on to; else a `no label` fail
    (above the first label, or out of the row above's reach), whose own rows then fail no more."""
    title, labels, headings = skills
    if not labels:
        return [], [f"no {title} line starts with a \\textbf{{<label>}}, so its lines were not checked"]
    # each row with its page and that page's right edge, its widest row (one text column assumed)
    rows = [(r, pno, max(x["xMax"] for x in p["lines"]))
            for pno, p in enumerate(pages) for r in sorted(p["lines"], key=lambda r: (r["yMin"], r["xMin"]))]
    folded = {h.casefold() for h in headings}   # a template may print headings in capitals
    start = next((i for i, (r, _, _) in enumerate(rows)
                  if " ".join(r["text"].split()).casefold() == title.casefold()), None)
    if start is None:
        return [], [f"no {title} heading in the text layer, so its lines were not checked"]
    fails, label, unlabelled = [], None, False
    for (prev, prev_page, right), (r, pno, _) in zip(rows[start:], rows[start + 1:]):
        text = " ".join(r["text"].split())
        item = text[len(BULLET):].lstrip() if text.startswith(BULLET) else text   # Skills lines in an itemize
        hit = label_at(item, labels)
        if text.casefold() in folded or (text.startswith(BULLET) and not hit):   # the next section
            break
        # the gap the row above left could not have held this row's first word (width by its share of letters)
        word = (item.split() or [""])[0]
        out_of_reach = (pno == prev_page and right - prev["xMax"]
                        > (r["xMax"] - r["xMin"]) * len(word) / max(len(item), 1) + SKILLS_REACH_MARGIN)
        if hit:
            label, unlabelled = hit, False
        elif label and not out_of_reach:
            if not unlabelled:   # else a row of the line with no label above, which already failed
                fails.append(f"{title} line wraps: {label} … {text[:40]}")
        else:
            fails.append(f"{title} line with no \\textbf{{<label>}} the check can read: {text[:40]}")
            unlabelled = True
    return fails, []


def email_fail(lines):
    """The email check's fail for a text layer's lines (tools/check_save.py runs it too), or None when
    they hold an address."""
    if re.search(r"[\w.+-]+@[\w-]+\.\w+", " ".join(lines)):
        return None
    gap = next((l for l in lines if re.search(r"\bGAP:\s*(?i:e-?mail)\b|\b(?i:e-?mail)\s*:\s*GAP\b", l)), None)
    return f"email: GAP (needs you): {gap}" if gap else "no email address in the text layer"


def layout(pages, limit=(MAX_PAGES, "default"), skills=None):
    """(fails, notes) for the rows lines_of reads: everything the check reads from the PDF alone.
    skills is what skills_of gives, or None to skip that check."""
    fails, notes = [], []
    if len(pages) > limit[0]:
        fails.append(f"pages: {len(pages)} (limit {limit[0]}, {limit[1]})")
    for pno, page in enumerate(pages, 1):
        rows = page["lines"]
        if not rows:
            continue
        right = max(r["xMax"] for r in rows)
        for b in bullets_of(rows):
            head = b[0]["text"][:60]
            if len(b) > MAX_BULLET_LINES:
                fails.append(f"p{pno} bullet has {len(b)} lines: {head}")
            if len(b) > 1:
                last = b[-1]
                width = right - last["xMin"]
                ratio = (last["xMax"] - last["xMin"]) / width if width else 1
                if ratio < DANGLING_RATIO:   # floored, so a fail never prints the threshold itself
                    fails.append(f"p{pno} dangling last line ({int(ratio * 100)}% of width, under "
                                 f"{DANGLING_RATIO:.0%}): {head} … {last['text']}")
        n, left, right, slack = summary(page)
        notes.append(f"p{pno}: {n} bullets, text block x {left:.0f}–{right:.0f}, bottom slack {slack:.0f}pt")
    if skills:
        more, said = skills_wraps(pages, skills)
        fails += more
        notes += said
    text = " ".join(r["text"] for p in pages for r in p["lines"])
    email = email_fail([r["text"] for p in pages for r in p["lines"]])
    if email:
        fails.append(email)
    if re.search(r"\(cid:\d+\)|�", text):
        fails.append("garbage glyphs in the text layer")
    if "–" in text:
        notes.append("dates use en dashes (–); some ATS imports (Workday) drop them")
    return fails, notes


def check(pdf, log_path=None, png=True, limit=(MAX_PAGES, "default"), outdir=None, fails=()):
    """Print the check of a PDF; True when it passes. `fails` come from before the build (the source
    scan, --same-layout); the text layer goes to <outdir>/<stem>.txt."""
    pages = lines_of(pdf)
    stem = os.path.splitext(pdf)[0]
    skills = None
    if os.path.isfile(stem + ".tex"):   # the Skills lines are read from the .tex beside the PDF
        try:
            skills = skills_of(logfiles.read_text(stem + ".tex"))
        except (OSError, UnicodeDecodeError):
            pass
    more, notes = layout(pages, limit, skills)
    fails = list(fails) + more

    if log_path and os.path.exists(log_path):
        log = open(log_path, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"Overfull \\hbox \(([\d.]+)pt too wide\)[^\n]*lines (\d+)", log):
            if float(m.group(1)) > OVERFULL_PT:
                fails.append(f"overfull box {m.group(1)}pt at source line {m.group(2)}")

    if outdir:
        os.makedirs(outdir, exist_ok=True)
        txt = os.path.join(os.path.abspath(outdir), os.path.basename(stem) + ".txt")
        if subprocess.run([find_poppler_bin("pdftotext"), "-enc", "UTF-8", pdf, txt],
                          capture_output=True).returncode == 0:
            notes.append(f"text layer: {txt} (read it: the order an ATS reads)")
    if png:
        subprocess.run([find_poppler_bin("pdftoppm"), "-png", "-r", "110", pdf, stem], check=True)
        notes.append("png: " + ", ".join(sorted(glob.glob(glob.escape(stem) + "-*.png"))))

    for n in notes:
        print("note:", n)
    for f in fails:
        print("FAIL:", f)
    print("OK" if not fails else f"{len(fails)} check(s) failed")
    return not fails


def read_tex(path):
    try:
        return logfiles.read_text(path)
    except (OSError, UnicodeDecodeError) as e:
        print(f"cannot read {path}: {e}")
        sys.exit(2)


def build_and_check(tex, root, outdir=None, limit=None, install_missing=False, png=True, start=None):
    """(passed, the PDF): the source scan, the build and the check; BuildFailed when the build fails."""
    text = read_tex(tex)
    fails = scan_source(text)
    if start:
        fails += same_layout(text, read_tex(start), os.path.basename(start))
    outdir = outdir or default_outdir(tex, root)
    try:
        pdf, log = build(tex, outdir, install_missing)
    except BuildFailed:
        for f in fails:   # a bare & or _ breaks the build: the scan names its line
            print("FAIL:", f)
        raise
    print("pdf:", pdf)
    return check(pdf, log, png, limit or page_limit(root), outdir, fails), pdf


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
            text = logfiles.read_text(todo.pop())
        except (OSError, UnicodeDecodeError):
            continue
        text = re.sub(r"(?<!\\)((?:\\\\)*)%.*", r"\1", text)   # a commented-out \input is not read; \% is no comment
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


def stale(folder, root):
    texs = sorted(glob.glob(os.path.join(glob.escape(folder), "*.tex")))
    if not texs:   # a Log with no target resume yet
        print(f"note: no .tex in {folder}, so nothing to compare")
        return True
    ok = True
    parts = {os.path.normcase(os.path.join(folder, rel)): os.path.basename(tex) for tex in texs for rel in local_inputs(tex)}
    for tex in texs:
        target = os.path.splitext(os.path.basename(tex))[0]
        if os.path.normcase(tex) in parts and not os.path.isfile(os.path.splitext(tex)[0] + ".pdf"):
            print(f"note: {target}.tex is part of {parts[os.path.normcase(tex)]}, not a resume of its own")
            continue
        pdf = os.path.splitext(tex)[0] + ".pdf"
        if not os.path.isfile(pdf):
            print(f"FAIL: {target}: no {target}.pdf beside its .tex")
            ok = False
            continue
        copy = os.path.join(root, ".build", "audit", target, target + ".tex")
        os.makedirs(os.path.dirname(copy), exist_ok=True)
        shutil.copyfile(tex, copy)
        for rel in local_inputs(tex):   # pdflatex looks for them beside the copy
            dest = os.path.join(os.path.dirname(copy), rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(os.path.join(folder, rel), dest)
        try:
            built, _ = build(copy, default_outdir(copy, root), False)
        except BuildFailed as e:
            # a file the .tex names that is not beside it is a package this machine lacks
            if e.missing and not os.path.exists(os.path.join(folder, e.missing)):
                print(f"FAIL: {target}: this machine lacks {e.missing}, so {target}.tex was not compared: "
                      f"python3 -I \"{os.path.join(HERE, 'resume.py')}\" \"{copy}\" --install-missing --root \"{root}\" "
                      "installs it")
            else:
                print(f"FAIL: {target}: {target}.tex does not build (the lines above say why)")
            ok = False
            continue
        same, said = compare_text(built, pdf)
        print(f"{target}: {said}" if same else f"FAIL: {target}: {said}; {target}.pdf is not the one its .tex builds")
        ok = ok and same
    return ok


def baseline(root):
    example = os.path.join(root, EXAMPLE)
    if not os.path.isfile(example):
        print(f"FAIL: baseline: no {example}")
        return False
    tex = os.path.join(root, ".build", "verify", "resume.tex")
    os.makedirs(os.path.dirname(tex), exist_ok=True)
    shutil.copyfile(example, tex)
    try:
        ok, pdf = build_and_check(tex, root, limit=(1, "the example"))
    except BuildFailed:
        print("FAIL: baseline: the example does not build (the lines above say why)")
        sys.exit(2)
    pages = lines_of(pdf)
    wrong = [] if len(pages) == 1 else [f"pages {len(pages)}, expected 1"]
    if pages and pages[0]["lines"]:
        got = dict(zip(("bullets", "left", "right", "slack"), summary(pages[0])))
        for k, want in BASELINE.items():
            off = abs(got[k] - want) > SLACK_PT if k == "slack" else round(got[k]) != want
            if off:
                wrong.append(f"{k} {got[k]:.0f}, expected {want}")
    print("baseline: OK" if ok and not wrong else
          "FAIL: baseline: " + ("; ".join(wrong) or "a check above failed"))
    return ok and not wrong


def main(argv=None):
    # Windows consoles default to a legacy code page; the report prints "•", "–" and "…"
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    no_error_dialogs()   # TeX and poppler too
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help=".tex to build and check, or .pdf with --check or --same-text")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="only check an existing PDF")
    mode.add_argument("--same-text", metavar="PDF", help="compare the words of the .pdf in path with this one")
    mode.add_argument("--stale", metavar="FOLDER", help="rebuild each .tex in FOLDER and compare it with its .pdf")
    mode.add_argument("--baseline", action="store_true", help="build and check the example resume (SETUP.md step 6)")
    logfiles.add_root(ap, __file__)
    ap.add_argument("--out", help="scratch build dir (default <root>/.build/resume/<folder>-<stem>-<hash>, "
                    "one per .tex)")
    ap.add_argument("--pages", type=int, help="the page limit for this run (default: resume_max_pages in config.toml)")
    ap.add_argument("--install-missing", action="store_true", help="tlmgr-install missing packages and retry")
    ap.add_argument("--no-png", action="store_true", help="skip page images")
    ap.add_argument("--same-layout", metavar="TEX", help="fail on layout settings that differ from this .tex")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    given = {"--" + k.replace("_", "-") for k in ("out", "pages", "install_missing", "no_png", "same_layout")
             if getattr(a, k) not in (None, False)}
    if a.check:
        extra = given - {"--out", "--pages", "--no-png"}
    elif a.same_text is not None or a.stale is not None or a.baseline:
        extra = given
    else:
        extra = set()
    if extra:
        ap.error(", ".join(sorted(extra)) + " do not apply with this mode")
    if (a.path is None) != (a.stale is not None or a.baseline):
        ap.error("--stale and --baseline take no path" if a.path else "give the path of a .tex, or of a .pdf")
    if a.pages is not None and a.pages < 1:
        ap.error("--pages takes a whole number from 1")
    if not os.path.isdir(root):
        ap.error(f"--root {a.root}: no such folder")
    if a.stale is not None and not os.path.isdir(a.stale):
        ap.error(f"--stale {a.stale}: no such folder")
    if a.same_text is not None:
        ok = same_text(a.path, a.same_text)
    elif a.stale is not None:
        ok = stale(a.stale, root)
    elif a.baseline:
        ok = baseline(root)
    elif a.check:
        ok = check(a.path, png=not a.no_png, limit=page_limit(root, a.pages),
                   outdir=a.out or default_outdir(a.path, root))
    else:
        try:
            ok, _ = build_and_check(a.path, root, a.out, page_limit(root, a.pages), a.install_missing,
                                    not a.no_png, a.same_layout)
        except BuildFailed:
            sys.exit(2)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
