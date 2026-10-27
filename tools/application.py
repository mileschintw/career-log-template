#!/usr/bin/env python3
"""The application folders and the other saved outputs of write (skills/career-log/modes/write.md):
their names, earlier contact with a company, the starting copy, the save, the level, sent versions,
risks and the Past phrasings a save feeds.

  python3 -I tools/application.py [--root <root>] <command> ...     (Windows: py -3 -I ...)

<root> is the Log's root (default: the folder above this script's). Paths are read from <root> when
relative. <saved> is a saved output: an application folder (outputs/applications/<folder>), a
target's outputs/resumes/<target>.md, or a report outputs/reports/<YYYY-MM-DD>-<slug>.md.

- `name --company <company> --role <role>` (a posting run), `name --target <target>` (a target run)
  or `name --report <slug> --kind <kind>` (any other output); each takes --today YYYY-MM-DD. Prints
  `name:`, `draft: .build/drafts/<name>/`, then `folder: outputs/applications/<name>/`, `resume:
  outputs/resumes/<target>.md` or `report: outputs/reports/<YYYY-MM-DD>-<slug>.md`, then `commit:
  <subject>`: `write(<company>): <role>`, `write(<target>): resume` or `write(<slug>): <kind>`.
  Names are ASCII slugs (tools/logfiles.py ascii_slug, as tools/scan.py names its draft folders),
  `<YYYY-MM-DD>-<company>-<role>` for a posting run; a name a saved folder or report already has
  takes the next free `-2`, `-3`. Drafts in .build/ do not count: a second call in the same run
  prints the same name.
- `prior <company>... [--type <question type>]`: for each company, `company: <company>`, then one
  `folder: <folder>/ | <date> | <Archived or Reference> | types: <its answers.md Type: lines, or
  none>` line per application folder whose name, less its date, starts with the company's words
  (newest first), and one `applications.md:<n>: <line>` per line of applications.md naming it as
  whole words; or `none: ...`. With --type, then one line per answer to that question type:
  `answer: <folder>/answers.md:<n> | <date> | Reference | <heading>` (a starting point, write-form-
  answers.md path 1), `untyped: ...` in the same form for each heading of a Reference folder saved
  before Type: lines (match its heading to the row yourself), and `sent before: ...` for an Archived
  folder's answer of that type or, saved before Type: lines, each of its headings; then, for each
  date of an `answer:` or `untyped:` line, `since <date>: <n> commits` and the `git log --since
  --oneline` lines for entries/, direction.md, stories.md and profile.md.
- `start [--name <name> --from <target or file>] [--replace]`: without --from, one `target: <name>
  | outputs/resumes/<name>.tex` per target (or `targets: none`), then `fallback:` the newest
  sources/resumes/*-main.tex, else the newest .tex there (newest by the YYYY-MM-DD its name starts
  with), `fallback: tie: <a>, <b>` when several share that date, or the blank layout
  skills/career-log/assets/resume-blank.tex. With --from, copies that target's .tex, or that file,
  to .build/drafts/<name>/resume.tex; it refuses the example resume, and a draft there with other
  text unless --replace.
- `save --application <name>` or `save --target <target>`: copies .build/drafts/<name>/resume.tex
  and resume.pdf to outputs/applications/<name>/ (with the draft's posting.md when the folder has
  none) or to outputs/resumes/<target>.tex and .pdf, printing a `copied:` line each. It refuses a
  draft without both files, and an application folder's committed resume.* with other content:
  that folder was sent and is frozen.
- `level <saved> archived|reference [--today YYYY-MM-DD]`, for an application folder or a `Kind:
  resume bullets` report (write › Save levels):
  - archived: writes the marker (archived.md, or the line under the report's `Kind:` line);
    deletes each ## Past phrasings line citing the output (`outputs/applications/<folder>` or the
    older `applications/<folder>`, likewise for a report), printing it; removes each stories.md
    pointer to a file under it, through tools/entries.py answer-set --remove, printing each.
  - reference: deletes the marker, then prints a `feed:` line naming the phrasings command for the
    bullets and one `answer: <type> | <path>` line per typed answer, for **Feed later runs**.
  Then `files:` (each file it wrote or deleted, for the commit) and `commit: <subject> to <level>`,
  the subject of the first `write(` commit that saved it (`write(<company>): <role>`), else
  `write(<folder>): application` or `write(<report name>): resume bullets`. It prints `unchanged:` for an output
  already at that level.
- `sent <target> [--before <YYYY-MM-DD[ HH:MM]>] [--record <folder>]`: the last commit of
  outputs/resumes/<target>.*, before that time with --before (a date alone: the end of that day),
  as `version: <hash>:outputs/resumes/<target>.tex` and the applications.md cell, `cell:
  [<target> @ <short>](https://github.com/<owner>/<repo>/blob/<hash>/outputs/resumes/<target>.pdf)`
  for a GitHub origin, else the bare short hash. With --before, also `changed that day: <n>
  commits`: for a date given alone, more than 0 means the user is asked which version went. Without --before it fails while
  the target's files have uncommitted changes (commit first). --record writes the version to
  <folder>/sent-version.md.
- `sent-show <ref> [--target <target>] [--out <file>] [--record <folder>]`: <ref> is an
  applications.md cell, its permalink, `<hash>:<path>`, a folder with sent-version.md, or a bare
  hash, alone or in the row's words (with --target). Prints `version: <hash>:<path>` (the path's .pdf read as .tex) and the file
  at that commit, or writes its bytes to --out; a bare hash whose path is not at that commit prints
  a `touched:` line per file it changed, and fails. --record as for sent.
- `risks <saved>`: `risks: <where>` and the `## Risks to handle in conversation` section saved with
  the output: an application folder's provenance.md; a folder with sent-version.md, the target's
  .md at that commit; a target's .md or a report; else `risks: none (saved before the section
  existed)`.
- `phrasings <saved, or a draft in .build/> --angle <angle> [<entry>...] [--today YYYY-MM-DD]`: the
  bullets of the resume (its .tex's `\\item`s, less those under an Education or Skills heading:
  tools/logfiles.py tex_bullets) or of the `resume bullets` report (its list items; a draft .md's), `bullet <n>: <wording>`, each followed, per
  entry, by `  <entry>: <ratio> <line>: <its closest wording for the angle>` (or `none for
  <angle>`), then one verdict line for the bullet:
  - `  same: <entry>:<line>: adds no line`: a wording an entry keeps for the angle at a ratio of
    tools/entries.py's SIMILAR or more;
  - else the bullet's entry is the one holding the largest share of its words (three letters or
    more, less a few such as `and`, `with`; the first entry given on a tie; a bullet merged from two
    claims goes to the one holding more), and the line is `  add: <entry>` (it differs from every
    wording kept for the angle, and goes in whole); `  none: ...` when the entries given hold less
    than half its words together (a line from profile.md, such as education); or `  older
    form: <entry>: ...` when that entry's ## Past phrasings has lines in neither the template's
    form nor its `none yet` or `GAP:` line (the older `**<label>**` form), which adds no line;
  then `cite: <citation>` (write step 10's form for that output), `entry: <entry>: <n> lines for
  <angle>`, and last `adds: <the --add flags for each add: bullet>` (or `adds: none`), the flags to
  run the same command with. An Archived output prints `archived: ... feeds nothing`.
  - `--add <n>=<entry>[,distinct|,replace=<line>]...` writes bullet <n> into the entry through
    tools/entries.py phrasing-add with that citation, and prints its lines.
  - `--cap <entry>=<line>,<line>,...` names the lines of one claim for the angle: keeps the two
    consolidate step 2 ranks first (from an output above imported, then newer above older) and
    deletes the rest, printing each.
  Both end with `line: <entry>:<n>: <line>` for each of the entry's lines for the angle as it now
  stands: the line numbers a later --replace or --cap takes.

Exit 0 on success, 1 when a command refuses or finds what the user must decide (a line saying so),
2 on a bad argument or a file it cannot read (a `FAIL:` line). Standard library only, Python 3.11+.
"""
import argparse, datetime, glob, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
import entries   # phrasing-add, answer-set, the Past phrasings and stories.md parsers
import check_save   # what a saved output is, its bullets, its Archived marker
import writing_lint   # tex_plain: a .tex fragment as the reader sees it

RISKS = "Risks to handle in conversation"
BLANK = "skills/career-log/assets/resume-blank.tex"
EXAMPLE = "skills/career-log/examples/resume.tex"
APPLICATIONS = "outputs/applications"
GITHUB = re.compile(r"(?:https://github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?/?$")
CELL = re.compile(r"\[[^\]]*\]\((https://[^)\s]+)\)")
PERMALINK = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/blob/([0-9a-f]{7,40})/(\S+?)/?$")
HASH_PATH = re.compile(r"([0-9a-f]{7,40}):(\S+)")
BARE_HASH = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


class AppError(Exception):
    pass


def at(root, rel):
    return rel if os.path.isabs(rel) else os.path.join(root, rel)


def rel_of(root, path):
    """A path as the Log names it: relative to root, with /, no trailing /."""
    p = os.path.abspath(at(root, path))
    try:
        r = os.path.relpath(p, os.path.abspath(root)).replace(os.sep, "/")
    except ValueError:   # another drive
        r = ".."
    if r.startswith(".."):
        raise AppError("%s is not in the Log at %s" % (path, root))
    return r.rstrip("/")


def read(root, rel):
    try:
        return logfiles.read_text(at(root, rel))
    except (OSError, UnicodeDecodeError) as e:
        raise AppError("cannot read %s: %s" % (rel, e))


def git(root, *args):
    try:
        return logfiles.git(root, *args)
    except logfiles.LogError as e:
        raise AppError(str(e))


def today(value):
    if value is None:
        return datetime.date.today().isoformat()
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        raise AppError("--today takes YYYY-MM-DD: %s" % value)


def one_line(text):
    return " ".join((text or "").split())


# ---- name ----

def free_name(taken, base):
    name, n = base, 2
    while name in taken:
        name, n = "%s-%d" % (base, n), n + 1
    return name


def cmd_name(root, company, role, target, report, kind, day):
    if sum(x is not None for x in (company or role, target, report)) != 1 or bool(company) != bool(role):
        raise AppError("name takes --company and --role, or --target, or --report with --kind")
    if company:
        c, r = logfiles.ascii_slug(company), logfiles.ascii_slug(role)
        if not c or not r:
            raise AppError("--company and --role need letters or digits: %r, %r" % (company, role))
        apps = at(root, APPLICATIONS)
        name = free_name(set(os.listdir(apps)) if os.path.isdir(apps) else set(), "%s-%s-%s" % (day, c, r))
        lines = ["folder: %s/%s/" % (APPLICATIONS, name), "commit: write(%s): %s" % (c, one_line(role))]
    elif target:
        name = logfiles.ascii_slug(target)
        if not name:
            raise AppError("--target needs letters or digits: %r" % target)
        lines = ["resume: outputs/resumes/%s.md" % name, "commit: write(%s): resume" % name]
    else:
        if not kind:
            raise AppError("--report takes --kind <kind>, one of: %s" % ", ".join(check_save.KINDS))
        if kind.lower() not in check_save.KINDS:
            raise AppError("--kind is one of: %s" % ", ".join(check_save.KINDS))
        slug = logfiles.ascii_slug(report)
        if not slug:
            raise AppError("--report needs letters or digits: %r" % report)
        d = at(root, "outputs/reports")
        taken = {f[len(day) + 1:-3] for f in (os.listdir(d) if os.path.isdir(d) else [])
                 if f.startswith(day + "-") and f.endswith(".md")}
        name = free_name(taken, slug)
        lines = ["report: outputs/reports/%s-%s.md" % (day, name), "commit: write(%s): %s" % (name, kind.lower())]
    return ["name: %s" % name, "draft: .build/drafts/%s/" % name] + lines


# ---- prior ----

def folders(root):
    """[(folder rel path, name, date or None, Archived?)] for each application folder, newest first."""
    d = at(root, APPLICATIONS)
    out = []
    for name in sorted(os.listdir(d) if os.path.isdir(d) else [], reverse=True):
        if os.path.isdir(os.path.join(d, name)):
            out.append(("%s/%s" % (APPLICATIONS, name), name, logfiles.split_dated(name)[0],
                        "archived.md" in os.listdir(os.path.join(d, name))))   # exact case on every OS
    return out


def typed_answers(text):
    """[(line number, heading, its Type: value or None)] for each question heading of an answers.md:
    the `## ` headings and below, or the `# ` ones in a file with none (as check_save reads them);
    `Company context` and `Risks...` set aside."""
    out, lines = [], text.lstrip("\ufeff").splitlines()
    level = 2 if any(re.match(r"#{2,6}\s", l) for l in lines) else 1
    for i, line in enumerate(lines):
        h = re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not h or len(h.group(1)) < level or re.match(r"(Company context|Risks)", h.group(2)):
            continue
        nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
        t = re.match(r"Type:\s*(\S.*?)\s*$", nxt)
        out.append((i + 1, h.group(2), t.group(1) if t else None))
    return out


def since_lines(root, day):
    try:
        log = git(root, "log", "--since=%s 00:00:00" % day, "--oneline", "--", "entries/", "direction.md", "stories.md",
                  "profile.md").splitlines()
    except AppError as e:
        return ["since %s: unknown (%s)" % (day, e)]
    return ["since %s: %d commits" % (day, len(log))] + ["  " + l for l in log]


def cmd_prior(root, companies, qtype):
    out = []
    apps = os.path.join(root, "applications.md")
    app_lines = logfiles.read_text(apps).split("\n") if os.path.isfile(apps) else []
    for company in companies:
        want = logfiles.norm(company)
        if not want.strip():
            raise AppError("a company needs letters or digits: %r" % company)
        out.append("company: %s" % company)
        found, dates = False, []
        for rel, name, day, archived in folders(root):
            if not logfiles.norm(logfiles.split_dated(name)[1]).startswith(want):
                continue
            found = True
            ans = os.path.join(root, rel, "answers.md")
            heads = typed_answers(read(root, rel + "/answers.md")) if os.path.isfile(ans) else []
            types = sorted({t for _, _, t in heads if t})
            level = "Archived" if archived else "Reference"
            out.append("folder: %s/ | %s | %s | types: %s" % (rel, day or "-", level,
                                                             "; ".join(types) if types else "none"))
            if qtype is None:
                continue
            untyped = not types
            for n, head, t in heads:
                if untyped or (t or "").lower() == qtype.lower():
                    tag = "sent before" if archived else "untyped" if untyped else "answer"
                    out.append("%s: %s/answers.md:%d | %s | %s | %s" % (tag, rel, n, day or "-", level, head))
                    if tag != "sent before" and day and day not in dates:
                        dates.append(day)
        for n, line in enumerate(app_lines, 1):
            if want in logfiles.norm(line):
                found = True
                out.append("applications.md:%d: %s" % (n, line.strip()))
        if not found:
            out.append("none: no application folder or applications.md line names %s" % company)
        for day in dates:
            out += since_lines(root, day)
    return out


# ---- start ----

def targets(root):
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(root, "outputs", "resumes", "*.tex")))


def fallback(root):
    texs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "sources", "resumes", "*.tex")))
    pool = [t for t in texs if t[:-4].endswith("-main")] or texs
    if not pool:
        return BLANK
    dated = [t for t in pool if DAY.match(t)]
    if dated:
        newest = max(t[:10] for t in dated)
        pool = [t for t in dated if t[:10] == newest]
    if len(pool) > 1:
        return "tie: " + ", ".join("sources/resumes/" + t for t in pool)
    return "sources/resumes/" + pool[0]


def cmd_start(root, name, source, replace):
    if source is None:
        if name:
            raise AppError("start --name takes --from <target or file>")
        ts = targets(root)
        out = ["target: %s | outputs/resumes/%s.tex" % (t, t) for t in ts] or ["targets: none"]
        return out + ["fallback: %s" % fallback(root)]
    if not name or not logfiles.ascii_slug(name) == name:
        raise AppError("start --from takes --name <name>, the name `name` printed")
    src = "outputs/resumes/%s.tex" % source if source in targets(root) else rel_of(root, source)
    if src == EXAMPLE:
        raise AppError("never copy the example resume (%s): copy a target, a source resume or %s" % (EXAMPLE, BLANK))
    text = read(root, src)
    dest = ".build/drafts/%s/resume.tex" % name
    if os.path.exists(at(root, dest)) and not replace and read(root, dest).replace("\r\n", "\n") != text.replace("\r\n", "\n"):
        return ["kept: %s holds another text (this run's edits?): nothing copied; --replace starts over from %s"
                % (dest, src)], 1
    os.makedirs(os.path.dirname(at(root, dest)), exist_ok=True)
    shutil.copyfile(at(root, src), at(root, dest))
    return ["copied: %s -> %s" % (src, dest)]


# ---- save ----

def committed_bytes(root, rel):
    p = subprocess.run(["git", "-C", root, "show", "HEAD:./%s" % rel], capture_output=True)   # ./: from root
    return p.stdout if p.returncode == 0 else None


def same_bytes(a, b):
    return a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n")


def cmd_save(root, application, target):
    if (application is None) == (target is None):
        raise AppError("save takes --application <name> or --target <target>")
    name = application or target
    if logfiles.ascii_slug(name) != name and not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[0-9a-z-]+", name):
        raise AppError("not a name `name` prints: %s" % name)
    draft = ".build/drafts/%s" % name
    missing = [f for f in ("resume.tex", "resume.pdf") if not os.path.isfile(at(root, draft + "/" + f))]
    if missing:
        return ["refused: %s has no %s: build it with tools/resume.py first" % (draft, " or ".join(missing))], 1
    if application:
        dest = "%s/%s" % (APPLICATIONS, name)
        pairs = [("resume.tex", dest + "/resume.tex"), ("resume.pdf", dest + "/resume.pdf")]
        if os.path.isfile(at(root, draft + "/posting.md")) and not os.path.exists(at(root, dest + "/posting.md")):
            pairs.append(("posting.md", dest + "/posting.md"))
        for f, to in pairs[:2]:
            old = committed_bytes(root, to)
            with open(at(root, draft + "/" + f), "rb") as fh:
                new = fh.read()
            if old is not None and not same_bytes(old, new):
                return ["refused: %s is committed with other content: the folder was sent and is frozen; a later"
                        " version is a new application (`name`) or a target" % to], 1
    else:
        pairs = [("resume.tex", "outputs/resumes/%s.tex" % name), ("resume.pdf", "outputs/resumes/%s.pdf" % name)]
    out = []
    for f, to in pairs:
        os.makedirs(os.path.dirname(at(root, to)), exist_ok=True)
        shutil.copyfile(at(root, draft + "/" + f), at(root, to))
        out.append("copied: %s/%s -> %s" % (draft, f, to))
    return out


# ---- level ----

def saved_kind(root, rel):
    """'application', 'target' or 'report' for a saved output's path; AppError for anything else."""
    if check_save.APPLICATION.match(rel):
        if not os.path.isdir(at(root, rel)):
            raise AppError("no such application folder: %s" % rel)
        return "application"
    if check_save.TARGET.match(rel):
        return "target"
    if check_save.REPORT_NAME.match(rel):
        return "report"
    raise AppError("not a saved output (outputs/applications/<folder>, outputs/resumes/<target>.md or"
                   " outputs/reports/<YYYY-MM-DD>-<slug>.md): %s" % rel)


def cites(citation, rel):
    """Whether a Past phrasings citation names the output rel (with or without `outputs/`)."""
    short = re.escape(rel[len("outputs/"):])
    return re.search(r"(?<![\w./-])(?:outputs/)?%s(?![\w.-])" % short, citation) is not None


def is_archived(root, rel, kind):
    if kind == "application":
        return os.path.isfile(at(root, rel + "/archived.md"))
    if kind == "report":
        return check_save.report_marks(read(root, rel))[1]
    return False


def first_subject(root, rel):
    try:
        subjects = git(root, "log", "--format=%s", "--", rel).splitlines()
    except AppError:
        return None
    for subject in reversed(subjects):   # oldest first
        m = re.match(r"(write\([^)]*\): .*?)(?: to (?:Reference|Archived))?$", subject)
        if m:
            return m.group(1)
    return None


def drop_phrasings(root, rel):
    """Delete each Past phrasings line citing rel, in every entry; (lines, files changed)."""
    out, changed = [], []
    for erel in entries.entry_paths(root):
        path = at(root, erel)
        bom, lines = entries.read_lines(path)
        bounds = entries.section_bounds(lines, "Past phrasings")
        if not bounds:
            continue
        bare = dict(entries.lines_of("".join(lines)))   # a line inside an HTML comment is no phrasing
        gone = [i for i in range(bounds[0] + 1, bounds[1])
                if (lambda m: m and cites(m.group(3), rel))(entries.PHRASING_PARTS.fullmatch(bare.get(i + 1, "").strip()))]
        if gone:
            for i in gone:
                out.append("removed: %s:%d: %s" % (erel, i + 1, lines[i].strip()))
            entries.write_lines(path, bom, [l for i, l in enumerate(lines) if i not in gone])
            changed.append(erel)
    return out, changed


def captured(fn, *args):
    """fn's return value and the lines it printed."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, [l for l in buf.getvalue().splitlines() if l.strip()]


def drop_pointers(root, rel):
    if not os.path.isfile(os.path.join(root, "stories.md")):
        return [], []
    _, rows = entries.answer_rows(entries.StoriesFile(root))
    out = []
    for _, row in rows:
        if any(entries.under(p[2], rel) for p in row.pointers):
            out += [l for l in captured(entries.cmd_answer_set, root, row.type, None, rel, True)[1]
                    if l.startswith("removed:")]   # a per-company row keeps none, and says so
    return out, (["stories.md"] if out else [])


def cmd_level(root, saved, level, day):
    rel = rel_of(root, saved)
    kind = saved_kind(root, rel)
    if kind == "target":
        raise AppError("a target has no level: it is overwritten in place (write › Save levels)")
    if kind == "report" and check_save.report_marks(read(root, rel))[0] != "resume bullets":
        raise AppError("only a `Kind: resume bullets` report has a level: %s" % rel)
    want = level == "archived"
    if is_archived(root, rel, kind) == want:
        return ["unchanged: %s is already %s" % (rel, "Archived" if want else "Reference")]
    marker = "Archived (user, %s)" % day
    out, files = [], []
    if kind == "application":
        path = at(root, rel + "/archived.md")
        if want:
            logfiles.write_text(path, marker + "\n")
        else:
            os.remove(path)
        out.append("%s: %s/archived.md" % ("wrote" if want else "deleted", rel))
        files.append(rel + "/archived.md")
    else:
        bom, lines = entries.read_lines(at(root, rel))
        if want:
            k = next(i for i, l in enumerate(lines) if re.match(r"\s*Kind:", l))
            lines.insert(k + 1, marker + (entries.ends(lines[k]) or entries.line_end(lines)))
        else:
            lines = [l for l in lines if not check_save.ARCHIVED.fullmatch(l.strip())]
        entries.write_lines(at(root, rel), bom, lines)
        out.append("%s: %s: %s" % ("wrote" if want else "deleted", rel, marker if want else "the Archived line"))
        files.append(rel)
    if want:
        gone, changed = drop_phrasings(root, rel)
        ptrs, stories = drop_pointers(root, rel)
        out += gone + ptrs
        files += changed + stories
    else:
        out.append("feed: %s -I %s phrasings %s --angle <angle> <entry>... --root %s"
                   " (the angle step 5 picks for its role; then --add as write step 10's Feed later runs says)"
                   % (logfiles.python_cmd(), logfiles.shell_arg(os.path.abspath(__file__)), rel, logfiles.shell_arg(root)))
        ans = rel + "/answers.md" if kind == "application" else rel
        if os.path.isfile(at(root, ans)):
            for n, head, t in typed_answers(read(root, ans)):
                if t:
                    out.append("answer: %s | %s" % (t, ans))
    subject = first_subject(root, rel) or ("write(%s): resume bullets" % os.path.basename(rel)[:-3] if kind == "report"
                                           else "write(%s): application" % os.path.basename(rel))
    return out + ["files: %s" % " ".join(files), "commit: %s to %s" % (subject, "Archived" if want else "Reference")]


# ---- sent ----

def owner_repo(root):
    p = logfiles.git_run(root, "remote", "get-url", "origin")
    m = GITHUB.match(p.stdout.strip()) if p.returncode == 0 else None
    return m.group(1) if m else None


def cell(root, target, full):
    repo = owner_repo(root)
    if not repo:
        return full[:7]
    prefix = git(root, "rev-parse", "--show-prefix").strip()   # the Log's folder in the repo, when it is below its top
    return "[%s @ %s](https://github.com/%s/blob/%s/%soutputs/resumes/%s.pdf)" % (target, full[:7], repo, full, prefix, target)


def record(root, folder, version):
    rel = rel_of(root, folder)
    if not check_save.APPLICATION.match(rel):
        raise AppError("--record takes an application folder, outputs/applications/<folder>: %s" % folder)
    path = at(root, rel + "/sent-version.md")
    if os.path.exists(path) and read(root, rel + "/sent-version.md").strip() != version:
        return ["refused: %s/sent-version.md names another version: %s" % (rel, read(root, rel + "/sent-version.md").strip())], 1
    os.makedirs(at(root, rel), exist_ok=True)
    logfiles.write_text(path, version + "\n")
    return ["recorded: %s/sent-version.md: %s" % (rel, version)]


def cmd_sent(root, target, before, folder):
    if logfiles.ascii_slug(target) != target:
        raise AppError("not a target name: %s" % target)
    spec = "outputs/resumes/%s.*" % target
    out = []
    if before is None:
        dirty = git(root, "status", "--porcelain", "--", spec).strip()
        if dirty:
            return ["refused: %s has uncommitted changes: commit them first (write step 10), then run it again" % spec], 1
        full = git(root, "log", "-1", "--format=%H", "--", spec).strip()
    else:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}(?::\d{2})?))?", before.strip())
        if not m:
            raise AppError("--before takes YYYY-MM-DD or YYYY-MM-DD HH:MM: %s" % before)
        until = "%s %s" % (m.group(1), m.group(2) or "23:59:59")
        full = git(root, "log", "-1", "--format=%H", "--before=%s" % until, "--", spec).strip()
        that_day = git(root, "log", "--format=%H", "--since=%s 00:00:00" % m.group(1),
                       "--until=%s 23:59:59" % m.group(1), "--", spec).split()
        out.append("changed that day: %d commits" % len(that_day))
    if not full:
        return out + ["none: no commit touched %s%s" % (spec, " before %s" % before if before else "")], 1
    version = "%s:outputs/resumes/%s.tex" % (full, target)
    out = ["version: %s" % version, "cell: %s" % cell(root, target, full)] + out
    if folder:
        res = record(root, folder, version)
        if isinstance(res, tuple):
            return out + res[0], 1
        out += res
    return out


def resolve(root, ref, target):
    """(full hash, path) a sent-version reference names; path None for a bare hash with no target."""
    ref = ref.strip()
    if os.path.isdir(at(root, ref)) and os.path.isfile(at(root, ref) + "/sent-version.md"):
        ref = read(root, rel_of(root, ref) + "/sent-version.md").strip()
    m = CELL.search(ref)
    url = m.group(1) if m else ref
    link, m = PERMALINK.match(url), HASH_PATH.fullmatch(ref)
    if link or m:
        hashes, path = [(link or m).group(1)], (link or m).group(2)
        if link:   # a permalink's path is from the repository's top level, which may sit above the Log
            prefix = git(root, "rev-parse", "--show-prefix").strip()
            path = path[len(prefix):] if prefix and path.startswith(prefix) else path
    elif BARE_HASH.search(ref):   # a bare hash, alone or in a row's words (among other numbers)
        hashes, path = [h.group(0) for h in BARE_HASH.finditer(ref)], ("outputs/resumes/%s.tex" % target if target else None)
        if path is None:
            raise AppError("a bare hash names no file: add --target <target>")
    else:
        raise AppError("not a sent version (a cell, a permalink, <hash>:<path>, a folder with sent-version.md,"
                       " or a hash with --target): %s" % ref)
    for h in hashes:
        p = logfiles.git_run(root, "rev-parse", "--verify", "--quiet", h + "^{commit}")
        if p.returncode == 0 and p.stdout.strip():
            full = p.stdout.strip()
            break
    else:
        raise AppError("no such commit in this clone: %s (git fetch, then run it again)" % ", ".join(hashes))
    return full, re.sub(r"\.pdf$", ".tex", path)


def cmd_sent_show(root, ref, target, dest, folder):
    full, path = resolve(root, ref, target)
    p = subprocess.run(["git", "-C", root, "show", "%s:./%s" % (full, path)], capture_output=True)
    if p.returncode != 0:
        touched = git(root, "show", "--stat", "--name-only", "--format=", full).split()
        return ["missing: %s at %s" % (path, full[:7])] + ["touched: %s" % t for t in touched], 1
    out = ["version: %s:%s" % (full, path)]
    if dest:
        try:
            with open(dest, "wb") as f:
                f.write(p.stdout)
        except OSError as e:
            raise AppError("cannot write %s: %s" % (dest, e))
        out.append("wrote: %s" % dest)
    else:
        out.append(p.stdout.decode("utf-8", "replace").rstrip("\n"))
    if folder:
        res = record(root, folder, "%s:%s" % (full, path))
        if isinstance(res, tuple):
            return out + res[0], 1
        out += res
    return out


# ---- risks ----

def cmd_risks(root, saved):
    rel = rel_of(root, saved)
    kind = saved_kind(root, rel)
    if kind == "application":
        if os.path.isfile(at(root, rel + "/provenance.md")):
            where, text = rel + "/provenance.md", read(root, rel + "/provenance.md")
        elif os.path.isfile(at(root, rel + "/sent-version.md")):
            full, path = resolve(root, rel, None)
            where = "%s:%s" % (full, path[:-4] + ".md")
            p = subprocess.run(["git", "-C", root, "show", "%s:./%s" % (full, path[:-4] + ".md")], capture_output=True)
            text = p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""
        else:
            where, text = rel, ""
    else:
        where, text = rel, read(root, rel)
    body = logfiles.section(text, RISKS)
    if body is None or not body.strip():
        return ["risks: none (saved before the section existed): find the risks from its claims (%s)" % where]
    return ["risks: %s" % where, body.strip("\n")]


# ---- phrasings ----

def wording(item):
    """A .tex bullet as a Past phrasings wording: bold kept as **x**, the rest as the reader sees it."""
    return writing_lint.tex_plain(re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", item))


def list_items(text):
    """The list items above a Markdown text's first table, as bullets (check_save reads the same)."""
    return [one_line(re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", l)) for l in check_save.above_table(text)
            if re.match(r"\s*(?:[-*+]|\d+\.)\s+\S", l)]


def approved_bullets(root, rel, day):
    """([wording], citation or None, Archived?) for a saved output or a draft .tex."""
    if rel.endswith(".tex"):
        items = [i for _, i in logfiles.tex_bullets(read(root, rel))]
        return [wording(i) for i in items], None, False
    if rel.startswith(".build/") and rel.endswith(".md"):   # a bullets draft, before its Kind: line
        return list_items(read(root, rel)), None, False
    kind = saved_kind(root, rel)
    if kind == "application":
        tex, cite = rel + "/resume.tex", rel
    elif kind == "target":
        tex, cite = rel[:-3] + ".tex", "%s, %s" % (rel[:-3] + ".tex", day)
    else:
        text = read(root, rel)
        mark = check_save.report_marks(text)
        if mark[0] != "resume bullets":
            raise AppError("%s is no `Kind: resume bullets` report: only those feed Past phrasings" % rel)
        return list_items(text), rel, mark[1]
    items = [i for _, i in logfiles.tex_bullets(read(root, tex))] if os.path.isfile(at(root, tex)) else []
    return [wording(i) for i in items], cite, is_archived(root, rel, kind)


def entry_lines(root, erel, angle):
    """[(line number, wording, citation, the line)] of an entry's Past phrasings for the angle."""
    path = at(root, erel)
    if not os.path.isfile(path):
        raise AppError("no such entry: %s" % erel)
    _, lines = entries.read_lines(path)
    bounds = entries.section_bounds(lines, "Past phrasings")
    out, bare = [], dict(entries.lines_of("".join(lines)))   # a line inside an HTML comment is no phrasing
    for i in range(bounds[0] + 1, bounds[1]) if bounds else []:
        m = entries.PHRASING_PARTS.fullmatch(bare.get(i + 1, "").strip())
        if m and m.group(1).lower() == angle:
            out.append((i + 1, m.group(2), m.group(3), lines[i].strip()))
    return out


def rank_key(line):
    """consolidate step 2's order, best first: a wording from an output above an imported one, then
    the newer above the older (the first YYYY-MM-DD in its citation)."""
    _, _, citation, _ = line
    d = DAY.search(citation)
    return (bool(entries.OUTPUT_PATH.search(citation) or re.match(r"(applications|resumes|reports)/", citation)),
            d.group(0) if d else "")


def cmd_phrasings(root, saved, angle, names, adds, caps, day):
    angle = angle.lower()
    if not entries.ANGLE.fullmatch(angle):
        raise AppError("--angle is a target name like `general`: %s" % angle)
    erels = [rel_of(root, e) for e in names]
    if caps:
        return cap(root, angle, caps)
    rel = rel_of(root, saved)
    bullets, cite, archived = approved_bullets(root, rel, day)
    if archived:
        return ["archived: %s is saved Archived and feeds nothing (write › Save levels)" % rel]
    if adds:
        if cite is None:
            raise AppError("--add takes the saved output, not a draft: its citation names the save")
        out, worst = [], 0
        for a in adds:
            m = re.fullmatch(r"(\d+)=([^,]+)(?:,(distinct|replace=(\d+)))?", a)
            if not m or not 1 <= int(m.group(1)) <= len(bullets):
                raise AppError("--add takes <bullet n>=<entry>[,distinct|,replace=<line>], n from 1 to %d: %s"
                               % (len(bullets), a))
            code, lines = captured(entries.cmd_phrasing_add, root, rel_of(root, m.group(2)), bullets[int(m.group(1)) - 1],
                                   angle, cite, m.group(3) == "distinct", int(m.group(4)) if m.group(4) else None)
            out += lines
            worst = max(worst, code)
        out += now_lines(root, sorted({rel_of(root, re.match(r"\d+=([^,]+)", a).group(1)) for a in adds}), angle)
        return (out, worst) if worst else out
    out, add = [], []
    kept = {e: entry_lines(root, e, angle) for e in erels}
    held = {e: content_words(read(root, e)) for e in erels}
    older = {e: older_lines(root, e) for e in erels}
    for n, b in enumerate(bullets, 1):
        out.append("bullet %d: %s" % (n, b))
        same = None
        for e in erels:
            best = max(kept[e], key=lambda k: entries.similar((angle, k[1]), (angle, b)), default=None)
            if best is None:
                out.append("  %s: none for %s" % (e, angle))
            else:
                ratio = entries.similar((angle, best[1]), (angle, b))
                out.append("  %s: %.2f %d: %s" % (e, ratio, best[0], best[3]))
                if ratio >= entries.SIMILAR and (same is None or ratio > same[0]):
                    same = ratio, e, best[0]
        own = content_words(b)
        share = {e: len(own & held[e]) / len(own) for e in erels} if own else {}
        owner = max(erels, key=lambda e: share[e], default=None) if share else None
        if same:
            out.append("  same: %s:%d: adds no line" % same[1:])
        elif owner is None or len(own & set().union(*held.values())) / len(own) < OWNS:
            out.append("  none: the entries given hold less than half its words: adds no line")
        elif older[owner]:
            out.append("  older form: %s: %d Past phrasings lines in a form this command cannot read: adds no line "
                       "until they are in the template's form" % (owner, older[owner]))
        else:
            out.append("  add: %s" % owner)
            add.append("--add %d=%s" % (n, owner))
    out.append("cite: %s" % (cite or "(the saved output: run this on it after the save)"))
    out += ["entry: %s: %d lines for %s" % (e, len(kept[e]), angle) for e in erels]
    return out + ["adds: %s" % (" ".join(add) or "none")]


OWNS = 0.5   # the share of a bullet's words the entries given must hold for it to be theirs
STOP = {"and", "the", "for", "with", "from", "into", "that", "this", "its", "our", "their", "via", "per", "over",
        "under", "across", "using", "used", "was", "were", "are", "has", "had", "have", "than", "then", "each"}


def content_words(text):
    """The words of a text that name something: three letters or more, not a STOP word."""
    return {w.strip(".") for w in entries.words(text) if len(w.strip(".")) >= 3 and w.strip(".") not in STOP}


def older_lines(root, erel):
    """The lines under an entry's ## Past phrasings that are neither in the template's form, nor its
    `none yet` or `GAP:` line: the older `**<label>**` form, which entry_lines cannot read."""
    _, lines = entries.read_lines(at(root, erel))
    bounds = entries.section_bounds(lines, "Past phrasings")
    bare = dict(entries.lines_of("".join(lines)))
    n = 0
    for i in range(bounds[0] + 1, bounds[1]) if bounds else []:
        line = bare.get(i + 1, "").strip()
        if line and not entries.PHRASING_PARTS.fullmatch(line) and not re.match(r"(?:-\s*)?(?:none yet|GAP:)", line, re.I):
            n += 1
    return n


def cap(root, angle, caps):
    out = []
    for c in caps:
        m = re.fullmatch(r"([^=]+)=(\d+(?:,\d+)+)", c)
        if not m:
            raise AppError("--cap takes <entry>=<line>,<line>,...: %s" % c)
        erel, want = rel_of(root, m.group(1)), [int(x) for x in m.group(2).split(",")]
        if len(set(want)) != len(want):
            raise AppError("--cap names a line twice: %s" % c)
        lines = {l[0]: l for l in entry_lines(root, erel, angle)}
        bad = [n for n in want if n not in lines]
        if bad:
            raise AppError("%s:%s is no Past phrasings line for %s" % (erel, ",".join(map(str, bad)), angle))
        if len(want) <= 2:
            out.append("kept: %s: %d wordings, within the two per claim" % (erel, len(want)))
            continue
        ranked = sorted((lines[n] for n in want), key=rank_key, reverse=True)
        gone = {l[0] for l in ranked[2:]}
        path = at(root, erel)
        bom, raw = entries.read_lines(path)
        for n in sorted(gone):
            out.append("dropped: %s:%d: %s" % (erel, n, raw[n - 1].strip()))
        entries.write_lines(path, bom, [l for i, l in enumerate(raw, 1) if i not in gone])
    return out + now_lines(root, sorted({rel_of(root, c.split("=")[0]) for c in caps}), angle)


def now_lines(root, erels, angle):
    return ["line: %s:%d: %s" % (e, n, line) for e in erels for n, _, _, line in entry_lines(root, e, angle)]


# ---- main ----

ROOT_HELP = "Every command takes --root <root>, the Log's root (default: the folder above this script's), anywhere on the line."


def parser():
    p = argparse.ArgumentParser(prog="application.py", description=__doc__, epilog=ROOT_HELP,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("name", epilog=ROOT_HELP)
    s.add_argument("--company"); s.add_argument("--role"); s.add_argument("--target")
    s.add_argument("--report"); s.add_argument("--kind"); s.add_argument("--today")
    s = sub.add_parser("prior", epilog=ROOT_HELP)
    s.add_argument("companies", nargs="+"); s.add_argument("--type")
    s = sub.add_parser("start", epilog=ROOT_HELP)
    s.add_argument("--name"); s.add_argument("--from", dest="source"); s.add_argument("--replace", action="store_true")
    s = sub.add_parser("save", epilog=ROOT_HELP)
    s.add_argument("--application"); s.add_argument("--target")
    s = sub.add_parser("level", epilog=ROOT_HELP)
    s.add_argument("saved"); s.add_argument("level", choices=("archived", "reference")); s.add_argument("--today")
    s = sub.add_parser("sent", epilog=ROOT_HELP)
    s.add_argument("target"); s.add_argument("--before"); s.add_argument("--record")
    s = sub.add_parser("sent-show", epilog=ROOT_HELP)
    s.add_argument("ref"); s.add_argument("--target"); s.add_argument("--out"); s.add_argument("--record")
    s = sub.add_parser("risks", epilog=ROOT_HELP)
    s.add_argument("saved")
    s = sub.add_parser("phrasings", epilog=ROOT_HELP)
    s.add_argument("saved", nargs="?"); s.add_argument("entries", nargs="*"); s.add_argument("--angle", required=True)
    s.add_argument("--add", action="append", default=[]); s.add_argument("--cap", action="append", default=[])
    s.add_argument("--today")
    return p


def run(root, a):
    if a.cmd == "name":
        return cmd_name(root, a.company, a.role, a.target, a.report, a.kind, today(a.today))
    if a.cmd == "prior":
        return cmd_prior(root, a.companies, a.type)
    if a.cmd == "start":
        return cmd_start(root, a.name, a.source, a.replace)
    if a.cmd == "save":
        return cmd_save(root, a.application, a.target)
    if a.cmd == "level":
        return cmd_level(root, a.saved, a.level, today(a.today))
    if a.cmd == "sent":
        return cmd_sent(root, a.target, a.before, a.record)
    if a.cmd == "sent-show":
        return cmd_sent_show(root, a.ref, a.target, a.out, a.record)
    if a.cmd == "risks":
        return cmd_risks(root, a.saved)
    if a.cmd == "phrasings":
        if a.cap:
            return cmd_phrasings(root, None, a.angle, [], [], a.cap, today(a.today))
        if not a.saved:
            raise AppError("phrasings takes <saved> (or --cap)")
        return cmd_phrasings(root, a.saved, a.angle, a.entries, a.add, [], today(a.today))


def main(argv):
    logfiles.utf8_stdout()
    try:
        root, rest = logfiles.split_root(argv, __file__)
    except logfiles.LogError as e:
        print("FAIL: %s" % e)
        return 2
    try:
        a = parser().parse_args(rest)
    except SystemExit as e:
        if e.code:
            print("FAIL: bad arguments; see `application.py --help`")
        return 2 if e.code else 0
    root = os.path.abspath(root)
    try:
        res = run(root, a)
    except (AppError, entries.Error, logfiles.LogError) as e:
        print("FAIL: %s" % e)
        return 2
    lines, code = res if isinstance(res, tuple) else (res, 0)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
