#!/usr/bin/env python3
"""Find what a Log made before Template 0.1.0 still has in an old format, and fix what is mechanical.

  python3 -I upgrade-0.1.0.py [<root>] [--apply engine|log]      (Windows: py -3 -I ...)
  python3 -I upgrade-0.1.0.py [<root>] --old-lines
  python3 -I upgrade-0.1.0.py --poppler [<poppler bin folder>]  (macOS, Linux)

<root> is the Log's root (default: the current folder). The guide that goes with this script,
upgrade-0.1.0.md, says when to run it and what to do with each line. Without --apply it only reads
and prints. Each line starts with its kind:

  apply:   the script's --apply engine or --apply log (named on the line) changes it
  migrate: the agent changes it by hand as the guide says, with nothing to ask
  ask:     the user decides, in the guide's question round
  review:  show it to the user once in that round; keeping it as it is is an answer too
  later:   waits for a later mode (consolidate, export); nothing to do now
  done:    --apply changed it, in the working tree only (nothing is staged or committed)

--apply engine finishes the Engine replacement: it deletes the Engine files 0.1.0 removed and puts
the Log's own .gitignore lines back after 0.1.0's. --apply log makes the mechanical Log changes:
config.toml (through tools/config.py init), the Template text of direction.md, profile.md,
stories.md, applications.md and sources/keys.md, stories/.gitkeep, the outputs/ layout (with the
references to what it moves), an unedited front page, and the old Past phrasings form. It needs
Python 3.11+, as tools/config.py does. Every apply ends with a fresh check.

--old-lines lists, as <file>:<line>: <text>, the lines of an edited README.md or README.zh-TW.md,
outside its Entries section, that came from an old Template page and 0.1.0's page lacks.

--poppler installs poppler without Homebrew or sudo, for guide step 2: conda-forge's, through
micromamba, into ~/.career-log/poppler, with pdfinfo, pdftotext and pdftoppm in ~/.local/bin. It
installs nothing when a poppler is already on PATH or in Homebrew's folders, and a rerun updates
its own. Given a folder (a poppler the user built or installed elsewhere), or with POPPLER_BIN
naming one, it puts that poppler's tools in ~/.local/bin instead. It ends with `OK:` and exit 0, or
a `failed:` line and exit 1. On macOS the check without --apply prints a `migrate:` line while no
poppler is found.

Exit 0 with `OK: nothing left to migrate` when no apply, migrate or ask line is left, 1 otherwise, 2 on a
bad argument. Standard library only; runs on Python 3.9+.
"""

import hashlib
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys

ENGINE_VERSION = "e6a5565a4807db1ab30b0eb70f8c2fd1421ac4df"   # tools/TEMPLATE_VERSION in 0.1.0
REMOVED = ["skills/career-log/assets/fair-page/index.html", "skills/career-log/career-fair.md",
           "skills/career-log/modes/apply.md", "skills/career-log/modes/upskill.md"]

# Every line any pre-0.1.0 Template's .gitignore held: none of them is the Log's own.
OLD_GITIGNORE = {".DS_Store", ".build/", ".worktrees/", ".make_fixtures-*", ".claude/worktrees/",
                 "outputs/**/*.png", "!outputs/*-page/*.png", "!outputs/reports/*-page/*.png",
                 "__pycache__/", "*.pyc", "sources/inbox/*", "!sources/inbox/.gitkeep",
                 "# Raw chat exports stay local; only picked threads move to sources/<origin>/"}
OWN_GITIGNORE_HEADER = "# This Log's own lines"
# A line each of these 0.1.0 Engine files has and no older one had: a replacement left half done
# (tools/ copied, SETUP.md or .gitignore not) shows here.
ENGINE_MARKERS = [("SETUP.md", "## 5. Machine setup"), (".gitignore", ".claude/skills/playwright-cli/"),
                  ("AGENTS.md", "Machine setup"), ("skills/career-log/SKILL.md", "tools/check.py")]

# sha256 (first 16 hex digits) of every pre-0.1.0 Template front page, with the body of its
# entries section (`## Entries`, `## 條目`) emptied: a page that matches is the Template's, unedited.
OLD_PAGES = {
    "README.md": {"ac588e75a835c71b", "5aa2e48304e2ca0a", "2c3dc81159f228c7", "d283550663d19875",
                  "d06c05f255d0a560", "e525541d86994a88", "ec0987cc8dbd09ec", "cb262c1d86e3b2d6",
                  "5efb9eb8e31a78b6", "29d0129375fc5d15", "79807514f6344cf8"},
    "README.zh-TW.md": {"e3c7b2df2874ab44", "834f585f652d88f4", "20f617d0053eb04e",
                        "5ceb87ef585e01cc", "3bd1020801686b37", "774af1038724a1db",
                        "1048ad4ee53b7837", "e844dd24948ac42b"},
}
ENTRIES_HEADING = {"README.md": "Entries", "README.zh-TW.md": "條目"}
# Text only the old pages had: an edited page that still holds one describes the old Engine.
OLD_PAGE_TEXT = re.compile(r"Your settings|settings round|Bulk changes as pull requests|`data/` branch"
                           r"|大量變更走 pull request|設定相關的問題", re.I)

DIRECTION_GAPS = {   # the Template's question lines, with or without a `(skipped, ...)` note
    "Target roles, ranked": "- **Target roles:** GAP: which roles are you aiming for, best first"
                            " (for example backend engineer, then platform engineer)?",
    "Employer preferences": "- **Sorting order for ranking employers:** GAP: after your hard constraints,"
                            " what decides which employers come first (domain fit, size, pay, location, ...)?",
    "Constraints": "- **Work authorisation:** GAP: does any role need sponsorship, a citizenship or a"
                   " clearance you lack? Which visa, if any, must an employer sponsor?",
}
DIRECTION_COMMENTS = {   # 0.1.0's text under these headings, from tools/template/direction.md
    "Target roles, ranked": "<!-- A numbered list, best first. Setup fills it; empty until then. -->",
    "Employer preferences": "<!-- The sorting order for ranking employers, on a line `- **Sorting order:** …`"
                            " (after your hard constraints: domain fit, size, pay, location, ...), and any"
                            " other preference about employers. -->",
    "Constraints": "Hard constraints: a role or employer that breaks one is out. One bullet each, work"
                   " authorisation first (`- **Work authorisation:** …`), each followed by its source,"
                   " `(user, YYYY-MM-DD)`. \"None\" is an answer too. Change one by saying so: setup shows"
                   " it before and after and writes it on your yes.",
    "What to emphasise, by target": "<!-- One line per resume target (`general` included): the entries to"
                                    " lead with and what to leave out. Experience that ended more than about"
                                    " five years ago stays off resumes by default (writing.md › Recency); a"
                                    " line here changes that window for one target or for all of them, for"
                                    " example \"Recency: ten years, every target\" or \"Backend: keep <entry>"
                                    " despite its age\". -->",
    "Writing preferences for applications": "<!-- The record language is in config.toml. -->",
}
OLD_CONSTRAINTS = ("Hard constraints: a role or employer that breaks one is out. A line still marked `GAP:`"
                   " has no answer yet; answer it in chat, or replace the whole `GAP: …` text here,"
                   " including any `(skipped, …)` note, with your answer followed by `(user, YYYY-MM-DD)`."
                   " \"None\" is an answer too.")
DEFAULT_LANGUAGES = "- **Languages:** record language English. (default; change it here)"

OLD_APPLICATION_QUESTIONS = {
    "<!-- Recurring application question types → the approved answer in outputs/. -->",
    "<!-- Recurring application question types → the approved answer in outputs/reports/ or an application folder. -->",
}

TEXT_UPDATES = [   # (file, a line only an old Template had, 0.1.0's line)
    ("applications.md",
     "Applications this repo prepared materials for, plus career fairs and recruiter contacts, newest last. `rank`, `apply` and `interview` read it to reuse what a company has already seen. Citation keys are defined in [sources/keys.md](sources/keys.md).",
     None),
    ("applications.md",
     "Applications this repo prepared materials for, plus career fairs and recruiter contacts, newest last. `rank`, `write` and `interview` read it to reuse what a company has already seen. Citation keys are defined in [sources/keys.md](sources/keys.md).",
     "Career fairs, recruiter contacts, resume versions sent outside an application, and applications that have no folder in `outputs/applications/`, newest last. A folder there is its own index entry and gets no row here. `rank`, `write` and `interview` search this file for a company or event to reuse what it has already seen; none of them reads it whole. Citation keys are defined in [sources/keys.md](sources/keys.md)."),
    ("profile.md",
     "<!-- Facts that differ between sources (dates, titles), and which one to use for which kind of application. -->",
     "<!-- Facts that differ between sources (dates, titles), in the forms entries/_template.md › Conflicts gives: an `Open:` line, or a `Settled:` line such as `Settled: use \"<A>\" for <application type>, \"<B>\" for <application type> (<why>). (<source>)`. -->"),
    ("profile.md",
     "<!-- Skills and claims on approved resumes that rest on thin evidence; review before an interview that touches them. -->",
     "<!-- Skills and claims on approved resumes that rest on thin evidence, and known bugs or negative results behind a resume claim (kept off the page, writing.md › Principles); review before an interview that touches them. -->"),
    ("profile.md", "- **Work authorisation:** GAP",
     "- **Work authorisation:** kept in [direction.md › Constraints](direction.md#constraints), with the roles it rules out."),
    ("sources/keys.md",
     "Short citations for material imported into this log. The generic forms (`sources/resumes/<file>`, `<repo>@<sha>:<path>:<line>`) are in [SKILL.md › Source keys](../skills/career-log/SKILL.md#source-keys). Add a row whenever a new source folder appears.",
     None),
    ("sources/keys.md",
     "Short citations for material imported into this log. The generic forms (`sources/resumes/<file>`, `<repo>@<sha>:<path>:<line>`) are in [SKILL.md › Source keys](../skills/career-log/SKILL.md#source-keys). Add a row whenever a new source folder or a new chat extract appears.",
     "Short citations for material imported into this log. The generic forms (`sources/resumes/<file>`, `<repo>@<sha>:<path>:<line>`) are in [SKILL.md › Source keys](../skills/career-log/SKILL.md#source-keys). Add a row whenever a new source folder or a new chat extract appears; session excerpts in `sources/<agent>/` need none."),
    ("stories.md",
     "Behavioural question types → where the story lives. A row with no entry is a missing story. Rows marked *(raw)* point at imported facts that still need consolidating into a story.",
     "Behavioural question types → where the story lives. A row with no entry is a missing story. Stories marked *(raw)* point at imported facts that still need consolidating into a story, *(pending)* at facts still in an entry's pending notes, and *(core)* at one of your 3–5 core stories (one marked item per entry is enough). Once you confirm Talking points for a type (the `stories` mode), its name links the file in `stories/`."),
]
for i, (f, old, new) in enumerate(TEXT_UPDATES):   # a None takes the next row's new line
    if new is None:
        TEXT_UPDATES[i] = (f, old, TEXT_UPDATES[i + 1][2])

OLD_PHRASING = re.compile(r'^- (["“].*["”]) \(([A-Za-z0-9][A-Za-z0-9-]*); (.+)\)\s*$')
NEW_PHRASING = re.compile(r'^- \*\*[a-z0-9][a-z0-9-]*:\*\* ["“「『]', re.I)
DEEP_LINK = re.compile(r"/(pull|pulls|issues|commit|commits|merge_requests|compare|blob|tree)/")
OUTPUT_DIRS = {"applications", "resumes", "reports", "dashboard", ".gitkeep"}


class Log:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.lines = []

    def out(self, kind, text):
        if kind == "migrate" and "(--apply " in text:   # a change the script itself makes
            kind = "apply"
        self.lines.append("%s: %s" % (kind, text))

    def path(self, rel):
        return os.path.join(self.root, *rel.split("/"))

    def read(self, rel):
        try:
            with open(self.path(rel), "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return None
        return raw.decode("utf-8-sig").replace("\r\n", "\n")

    def write(self, rel, text):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def git(self, *args):
        p = subprocess.run(["git", "-C", self.root, "-c", "core.quotepath=false"] + list(args),
                           capture_output=True, encoding="utf-8", errors="replace")
        return p.stdout if p.returncode == 0 else None

    def tool(self, *args):
        return subprocess.run([sys.executable, "-I", self.path("tools/" + args[0])] + list(args[1:]),
                              capture_output=True, encoding="utf-8", errors="replace", cwd=self.root)


def sections(text):
    """[(heading or None, start, end)] for each `## ` section, by line index."""
    lines = text.split("\n")
    heads = [i for i, l in enumerate(lines) if l.startswith("## ")]
    out = [(None, 0, heads[0] if heads else len(lines))]
    for n, i in enumerate(heads):
        out.append((lines[i][3:].strip(), i, heads[n + 1] if n + 1 < len(heads) else len(lines)))
    return lines, out


def template_section(log, rel, heading):
    """The body of `## <heading>` in one of 0.1.0's Template files, without its trailing blank lines."""
    lines, secs = sections(log.read(rel) or "")
    body = next((lines[a + 1:b] for h, a, b in secs if h == heading), [])
    while body and not body[-1].strip():
        body.pop()
    return body


def page_hash(text, heading):
    text = re.sub(r"(?ms)^## %s\n.*?(?=^## |\Z)" % re.escape(heading), "## %s\n" % heading, text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---- Engine ----

def check_engine(log, apply):
    version = (log.read("tools/TEMPLATE_VERSION") or "").strip()
    if version != ENGINE_VERSION and os.path.isfile(log.path("tools/config.py")):
        log.out("migrate", "engine: tools/TEMPLATE_VERSION is %s, not 0.1.0's: if this Log's Engine is a"
                " later Template's, follow that release's guide instead; otherwise replace it (guide step 1)"
                % (version or "missing"))
        return False
    if version != ENGINE_VERSION:
        log.out("migrate", "engine: this Log's Engine is not 0.1.0's (tools/TEMPLATE_VERSION %s): replace it"
                " first (guide step 1); nothing else is checked until then" % (version or "missing"))
        return False
    partial = [rel for rel, text in ENGINE_MARKERS if text not in (log.read(rel) or "")]
    if partial:
        log.out("migrate", "engine: only part of it is 0.1.0's (%s still old): replace it whole (guide"
                " step 1)" % ", ".join(partial))
        return False
    for rel in REMOVED:
        if os.path.exists(log.path(rel)):
            if apply == "engine":
                os.remove(log.path(rel))
                log.out("done", "deleted %s (an Engine file 0.1.0 removed)" % rel)
            else:
                log.out("migrate", "engine file 0.1.0 removed is still here: %s (--apply engine)" % rel)
    folder = log.path("skills/career-log/assets/fair-page")
    if apply == "engine" and os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)
    own = own_gitignore_lines(log)
    if own and apply == "engine":
        text = log.read(".gitignore") or ""
        log.write(".gitignore", text.rstrip("\n") + "\n\n" + OWN_GITIGNORE_HEADER + "\n" + "\n".join(own) + "\n")
        log.out("done", ".gitignore: put back this Log's own lines: %s" % ", ".join(own))
    elif own:
        log.out("migrate", ".gitignore lacks this Log's own lines: %s (--apply engine)" % ", ".join(own))
    return True


def own_gitignore_lines(log):
    """Lines a committed .gitignore held that no Template had and the current file lacks."""
    current = set(l.strip() for l in (log.read(".gitignore") or "").split("\n"))
    shas = (log.git("log", "--format=%H", "--", ".gitignore") or "").split()
    seen, own = set(), []
    for sha in shas:
        for line in (log.git("show", "%s:.gitignore" % sha) or "").replace("\r\n", "\n").split("\n"):
            s = line.strip()
            if s and s not in seen and s not in OLD_GITIGNORE and s not in current:
                seen.add(s)
                own.append(s)
    return own


# ---- Config and direction.md ----

def check_config(log, apply):
    if os.path.isfile(log.path("config.toml")):
        return
    if apply == "log":
        p = log.tool("config.py", "init", "--root", log.root)
        if p.returncode == 0:
            log.out("done", "config.toml written by tools/config.py init, every field at its default")
            return
        log.out("migrate", "config.toml: tools/config.py init failed: %s" % (p.stdout + p.stderr).strip())
        return
    log.out("migrate", "config.toml missing (--apply log writes it)")


def check_direction(log, apply):
    text = log.read("direction.md")
    if text is None:
        log.out("migrate", "direction.md missing: copy tools/template/direction.md")
        return
    lines, secs = sections(text)
    drop, notes = set(), []
    for heading, start, end in secs:
        body = lines[start + 1:end]
        if heading in ("Repo workflow", "First-session setup"):
            drop.update(range(start, end))
            notes.append(("fix", "direction.md: delete ## %s (0.1.0 has no such setting)" % heading))
        elif heading == "Career-fair tactics":
            if all(not l.strip() or l.strip().startswith("<!--") for l in body):
                drop.update(range(start, end))
                notes.append(("fix", "direction.md: delete the empty ## Career-fair tactics"))
            else:
                notes.append(("migrate", "direction.md › Career-fair tactics has lines: move each under"
                              " ## Employer preferences, as one line starting `At a career fair:`, then"
                              " delete the section"))
    new = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        heading = None
        for h, start, end in secs:
            if start < i < end:
                heading = h
        s = line.strip()
        gap = DIRECTION_GAPS.get(heading)
        if gap and s == gap:
            notes.append(("fix", "direction.md › %s: delete the Template's GAP question line" % heading))
            continue
        if gap and s.startswith(gap + " (skipped") and s.endswith(")"):
            notes.append(("fix", "direction.md › %s: delete the Template's GAP question line and its"
                          " (skipped, ...) note: 0.1.0 keeps no skip, and setup (guide step 4) shows the"
                          " item empty" % heading))
            continue
        if heading == "Constraints" and s == OLD_CONSTRAINTS:
            notes.append(("fix", "direction.md › Constraints: put in 0.1.0's intro paragraph"))
            new.append(DIRECTION_COMMENTS["Constraints"])
            continue
        if s == DEFAULT_LANGUAGES:
            notes.append(("fix", "direction.md: delete the default Languages line (the record language"
                          " is now config.toml's record_language, English by default)"))
            continue
        if s.startswith("- **Sorting order for ranking employers:**"):
            line = line.replace("**Sorting order for ranking employers:**", "**Sorting order:**", 1)
            notes.append(("fix", "direction.md: rename the Sorting order line's label"))
        if re.search(r"\(skipped, user, [0-9-]+\)", line) and "GAP:" in line:
            line = re.sub(r"\s*\(skipped, user, [0-9-]+\)", "", line)
            notes.append(("fix", "direction.md: delete a (skipped, ...) note (0.1.0 has no skipped state)"))
        new.append(line)
        h = line[3:].strip() if line.startswith("## ") else None
        if h == "Writing preferences for applications":
            continue   # 0.1.0's comment goes under the section's first paragraph, below
        if line.startswith("The rules every user shares are in [writing.md]"):
            h = "Writing preferences for applications"
        if h in DIRECTION_COMMENTS:
            body = next(lines[a + 1:b] for hh, a, b in secs if hh == h)
            if not any(l.strip() == DIRECTION_COMMENTS[h] or (h == "Constraints" and l.strip() == OLD_CONSTRAINTS)
                       for l in body):
                new.append(DIRECTION_COMMENTS[h])
                notes.append(("fix", "direction.md › %s: add 0.1.0's comment" % h))
    result = "\n".join(new)
    result = re.sub(r"\n{3,}", "\n\n", result)
    for kind, msg in notes:
        if kind == "fix":
            if apply == "log":
                log.out("done", msg)
            else:
                log.out("migrate", "%s (--apply log)" % msg)
        else:
            log.out(kind, msg)
    if apply == "log" and result != text:
        log.write("direction.md", result)
    text = result if apply == "log" else text
    for line in text.split("\n"):
        s = line.strip()
        if s != DEFAULT_LANGUAGES and re.match(r"- \*\*Languages:\*\*.*record language", s, re.I):
            log.out("migrate", "direction.md: the old Languages line `%s`: set its record language with"
                    " tools/config.py set record_language, keep any output-language part as a writing"
                    " preference, and delete the rest" % s)
        elif s.startswith("- **Target roles:**") and not s[len("- **Target roles:**"):].strip().startswith("GAP:"):
            log.out("migrate", "direction.md: `%s`: rewrite as a numbered list, best first, each role"
                    " with its source" % s)
        if "GAP: confirm:" in s:
            log.out("ask", "direction.md: confirm or drop `%s`" % s)


def check_profile(log):
    text = log.read("profile.md") or ""
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("- **Work authorisation:**") and "direction.md" not in s and s != "- **Work authorisation:** GAP":
            log.out("migrate", "profile.md: `%s`: move it to direction.md › Constraints as its"
                    " `- **Work authorisation:**` line (unless one is there), then put 0.1.0's pointer"
                    " line here" % s)


def check_text_updates(log, apply):
    files = {}
    for rel, old, new in TEXT_UPDATES:
        text = files.get(rel, log.read(rel))
        if text is None:
            continue
        lines = text.split("\n")
        if old in (l.rstrip() for l in lines):
            lines = [new if l.rstrip() == old else l for l in lines]
            files[rel] = "\n".join(lines)
            if apply == "log":
                log.out("done", "%s: the Template text `%s…` updated to 0.1.0's" % (rel, old[:40]))
            else:
                log.out("migrate", "%s: Template text `%s…` is pre-0.1.0 (--apply log updates it)" % (rel, old[:40]))
    if apply == "log":
        for rel, text in files.items():
            log.write(rel, text)


def check_stories(log, apply):
    text = log.read("stories.md")
    if text is not None:
        lines, secs = sections(text)
        for heading, start, end in secs:
            if heading != "Application questions":
                continue
            body = [l for l in lines[start + 1:end] if l.strip()]
            if any(l.startswith("| Question type | Scope") for l in body):
                break
            if all(l.strip() in OLD_APPLICATION_QUESTIONS for l in body):
                if apply == "log":
                    lines[start + 1:end] = template_section(log, "tools/template/stories.md", heading) + [""]
                    log.write("stories.md", "\n".join(lines))
                    log.out("done", "stories.md › Application questions: 0.1.0's comment and table")
                else:
                    log.out("migrate", "stories.md › Application questions: pre-0.1.0 (--apply log puts"
                            " 0.1.0's comment and table there)")
            else:
                log.out("ask", "stories.md › Application questions has rows without a Scope column:"
                        " give each row a scope (shared, per-angle or per-company), the user confirms")
    if not os.path.isfile(log.path("stories/.gitkeep")):
        if apply == "log":
            log.write("stories/.gitkeep", "")
            log.out("done", "created stories/.gitkeep")
        else:
            log.out("migrate", "stories/.gitkeep missing (--apply log creates it)")
    if os.path.isfile(log.path("tools/entries.py")):
        p = log.tool("entries.py", "story-coverage")   # its own Log, the one it runs in
        if p.returncode not in (0, 1):
            log.out("migrate", "tools/entries.py story-coverage cannot read stories.md: %s"
                    % ((p.stdout + p.stderr).strip().splitlines() or [""])[-1])


# ---- outputs/ ----

def check_outputs(log, apply):
    top = log.path("outputs")
    if not os.path.isdir(top):
        return
    moves = []
    for name in sorted(os.listdir(top)):
        full = os.path.join(top, name)
        if name in OUTPUT_DIRS:
            continue
        if os.path.isdir(full) and re.match(r"\d{4}-\d{2}-\d{2}-.+-page$", name):
            moves.append((name, "reports"))
        elif os.path.isdir(full) and re.match(r"\d{4}-\d{2}-\d{2}-", name):
            moves.append((name, "applications"))
        elif os.path.isfile(full) and re.match(r"\d{4}-\d{2}-\d{2}-.+\.md$", name):
            moves.append((name, "reports"))
        else:
            log.out("review", "outputs/%s: not in 0.1.0's layout (outputs/applications/, resumes/, reports/):"
                    " ask the user where it goes" % name)
    for name, sub in list(moves):
        if os.path.exists(os.path.join(top, sub, name)):
            moves.remove((name, sub))
            log.out("review", "outputs/%s and outputs/%s/%s both exist: ask the user which to keep, and"
                    " move or delete the other by hand" % (name, sub, name))
    if not moves:
        for sub in ("applications", "reports", "resumes"):
            if not os.path.isdir(os.path.join(top, sub)):
                if apply == "log":
                    log.write("outputs/%s/.gitkeep" % sub, "")
                    log.out("done", "created outputs/%s/.gitkeep" % sub)
                else:
                    log.out("migrate", "outputs/%s/ missing (--apply log creates it)" % sub)
        if os.path.isfile(os.path.join(top, ".gitkeep")) and all(
                os.path.isdir(os.path.join(top, s)) for s in ("applications", "reports", "resumes")):
            if apply == "log":
                os.remove(os.path.join(top, ".gitkeep"))
                log.out("done", "deleted outputs/.gitkeep (0.1.0 keeps one in each subfolder)")
            else:
                log.out("migrate", "outputs/.gitkeep is pre-0.1.0 (--apply log deletes it)")
        return
    if apply != "log":
        for name, sub in moves:
            log.out("migrate", "outputs/%s belongs in outputs/%s/ (--apply log moves it and the references"
                    " to it)" % (name, sub))
        return
    pattern = re.compile(r"outputs/(%s)(?=[/)\s`'\"#,;:]|$)" % "|".join(re.escape(n) for n, _ in moves))
    target = dict(moves)
    for rel in markdown_files(log):   # references first, so a failure here leaves nothing moved
        if rel.startswith(("outputs/", "sources/")):
            continue   # sent folders are frozen and sources/ is verbatim: their text stays as it was
        try:
            text = log.read(rel)
        except UnicodeDecodeError:
            log.out("review", "%s is not UTF-8, so its references to outputs/ were left as they were" % rel)
            continue
        new = pattern.sub(lambda m: "outputs/%s/%s" % (target[m.group(1)], m.group(1)), text)
        if new != text:
            log.write(rel, new)
            log.out("done", "%s: references to the moved outputs updated" % rel)
    for name, sub in moves:
        os.makedirs(os.path.join(top, sub), exist_ok=True)
        os.rename(os.path.join(top, name), os.path.join(top, sub, name))
        log.out("done", "moved outputs/%s to outputs/%s/%s" % (name, sub, name))
    check_outputs(log, apply)


def markdown_files(log):
    out = []
    for dirpath, dirs, files in os.walk(log.root):
        rel_dir = os.path.relpath(dirpath, log.root).replace(os.sep, "/")
        if rel_dir == ".":
            dirs[:] = [d for d in dirs if d not in (".git", ".build", "skills", "tools", "docs", ".github",
                                                    ".worktrees", ".claude", ".agents")]
        if rel_dir == "sources" or rel_dir.startswith("sources/inbox"):
            dirs[:] = [d for d in dirs if d != "inbox"]
        for f in files:
            if f.endswith(".md"):
                rel = f if rel_dir == "." else rel_dir + "/" + f
                if rel not in ("AGENTS.md", "CLAUDE.md", "GLOSSARY.md", "SETUP.md", "entries/_template.md"):
                    out.append(rel)
    return sorted(out)


# ---- Front page ----

def check_pages(log, apply):
    root_sha = ((log.git("rev-list", "--max-parents=0", "HEAD") or "").split() or [None])[-1]
    readme_template = False
    for rel in ("README.md", "README.zh-TW.md"):
        heading = ENTRIES_HEADING[rel]
        text = log.read(rel)
        new_page = log.read("tools/template/" + rel)
        if new_page is None:
            continue
        if text is None:
            if rel == "README.zh-TW.md" and readme_template:
                if apply == "log":
                    log.write(rel, new_page)
                    log.out("done", "README.zh-TW.md: 0.1.0's page (the old Template had none)")
                else:
                    log.out("migrate", "README.zh-TW.md missing beside an unedited front page (--apply log"
                            " copies 0.1.0's)")
            continue
        h = page_hash(text, heading)
        if h == page_hash(new_page, heading):
            readme_template = readme_template or rel == "README.md"
            continue
        full = (log.git("rev-parse", "--is-shallow-repository") or "").strip() == "false"
        first = log.git("show", "%s:%s" % (root_sha, rel)) if root_sha and full else None
        unedited = h in OLD_PAGES[rel] or (first is not None and h == page_hash(first.replace("\r\n", "\n"), heading))
        if unedited:
            if rel == "README.md":
                readme_template = True
            if apply == "log":
                log.write(rel, keep_entries(new_page, text, heading))
                log.out("done", "%s: the old Template page, unedited, replaced with 0.1.0's; its ## %s"
                        " section kept as it was" % (rel, heading))
            else:
                log.out("migrate", "%s is an unedited pre-0.1.0 Template page (--apply log replaces it with"
                        " 0.1.0's, keeping ## %s)" % (rel, heading))
        else:
            hits = [l for _, l in old_template_lines(log, rel)]
            if hits:
                log.out("review", "%s is edited and still has %d lines of the old Template page that 0.1.0's"
                        " lacks (`--old-lines` lists them; first: `%s`): replace it with 0.1.0's page"
                        " keeping ## %s, or cut those lines" % (rel, len(hits), hits[0].strip()[:80], heading))


def old_template_lines(log, rel):
    """[(line number, line)] of the page, outside its Entries section, that an unedited old Template page
    in the Log's history held (one of OLD_PAGES) and 0.1.0's page lacks: the Template's text, not the
    user's. With no such page in the history, the lines that name an old setting (OLD_PAGE_TEXT).
    Lines that are only markup (`>`, `---`, a table's separator row) are left out."""
    heading = ENTRIES_HEADING[rel]
    text, new_page = log.read(rel), log.read("tools/template/" + rel)
    if text is None or new_page is None:
        return []
    old = set()
    for sha in (log.git("log", "--format=%H", "--", rel) or "").split():
        page = (log.git("show", "%s:%s" % (sha, rel)) or "").replace("\r\n", "\n")
        if page_hash(page, heading) in OLD_PAGES[rel]:
            old.update(page.split("\n"))
    new = set(new_page.split("\n"))
    out, entries = [], False
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            entries = line[3:].strip() == heading
        if entries or line in new or re.fullmatch(r"[\s>|:-]*", line):
            continue
        if (line in old) if old else OLD_PAGE_TEXT.search(line):
            out.append((n, line))
    return out


def keep_entries(new_page, old_page, heading):
    m = re.search(r"(?ms)^## %s\n.*?(?=^## |\Z)" % re.escape(heading), old_page)
    if not m:
        return new_page
    return re.sub(r"(?ms)^## %s\n.*?(?=^## |\Z)" % re.escape(heading), lambda _: m.group(0), new_page, count=1)


# ---- Entries ----

def entry_files(log):
    folder = log.path("entries")
    if not os.path.isdir(folder):
        return []
    return ["entries/" + f for f in sorted(os.listdir(folder)) if f.endswith(".md") and f != "_template.md"]


def check_entries(log, apply):
    public = []
    for rel in entry_files(log):
        text = log.read(rel)
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        front = m.group(1) if m else ""
        vis = re.search(r"^visibility:[ \t]*([^\n#]*?)[ \t]*(#.*)?$", front, re.M)
        if not vis:
            log.out("migrate", "%s: no visibility line: add `visibility: GAP` to its front matter" % rel)
        elif vis.group(1) == "public" and not (vis.group(2) or "").strip("# ").startswith("(user,"):
            public.append(rel)
        links = re.search(r"^links:[ \t]*(.*)$", front, re.M)
        deep = DEEP_LINK.findall(links.group(1)) if links else []
        if deep:
            log.out("later", "%s: links: holds PR, issue or commit links; the next consolidate moves them"
                    " into the body as citations" % rel)
        if re.search(r"^## Log\s*$", text, re.M):
            log.out("later", "%s: has a ## Log section; the next mode that edits the entry renames it"
                    " ## Pending (SKILL.md › Entry sections renamed)" % rel)
        new_text, converted, other = convert_phrasings(text)
        if converted:
            if apply == "log":
                log.write(rel, new_text)
                log.out("done", "%s: %d Past phrasings lines in 0.1.0's form" % (rel, converted))
            else:
                log.out("migrate", "%s: %d Past phrasings lines in the old `\"...\" (angle; source)` form"
                        " (--apply log converts them)" % (rel, converted))
        if other:
            log.out("later", "%s: %d Past phrasings lines in neither form; still read, and the next"
                    " consolidate rewrites them" % (rel, other))
    if public:
        log.out("ask", "visibility: public in %d entries the user never confirmed (before 0.1.0 public was"
                " the default): %s. Ask public, private or nda for each, in one numbered list" %
                (len(public), ", ".join(public)))


def convert_phrasings(text):
    m = re.search(r"(?ms)^## Past phrasings[^\n]*\n(.*?)(?=^## |\Z)", text)
    if not m:
        return text, 0, 0
    converted, other, out = 0, 0, []
    for line in m.group(1).split("\n"):
        old = OLD_PHRASING.match(line.strip())
        if old:
            out.append('- **%s:** %s (%s)' % (old.group(2), old.group(1), old.group(3)))
            converted += 1
            continue
        s = line.strip()
        if s.startswith("- ") and not NEW_PHRASING.match(s) and not re.match(r"- (none yet|GAP:)", s, re.I):
            other += 1
        out.append(line)
    return text[:m.start(1)] + "\n".join(out) + text[m.end(1):], converted, other


def check_tools(log):
    p = log.tool("entries.py", "check")   # its own Log
    for line in p.stdout.splitlines():
        if line.startswith("OK:") or not line.strip():
            continue
        kind = "migrate" if line.startswith(("no README row", "README row")) else "later"
        log.out(kind, "tools/entries.py check: %s" % line)
    if p.returncode not in (0, 1):
        log.out("migrate", "tools/entries.py check failed: %s" % (p.stdout + p.stderr).strip())
    if os.path.isfile(log.path(".export-deny")):
        p = log.tool("deny_coverage.py")   # its own Log, the one it runs in
        names = [l for l in p.stdout.splitlines() if l.startswith("  ")]   # one indented line per name
        if names:
            log.out("later", ".export-deny: tools/deny_coverage.py names %d recorded names it does not cover;"
                    " this matters only if this Log exports a Template (AGENTS.md › Sharing)" % len(names))


def check_branches(log):
    out = log.git("branch", "-a", "--format=%(refname:short)", "--list", "data/*", "origin/data/*") or ""
    for name in out.split():
        log.out("ask", "branch %s is left from the old bulk-change pull requests: merge it (through its pull"
                " request, if it has one) or close it, then delete the branch (0.1.0 no longer reads it)" % name)


# ---- poppler without Homebrew (macOS, Linux) ----

MAMBA_VERSION = "2.9.0-0"   # micromamba's release; the download is checked against the release's .sha256
POPPLER_TOOLS = ("pdfinfo", "pdftotext", "pdftoppm")
WRAPPER_MARK = "# upgrade-0.1.0.py --poppler"


def has_bbox_layout(pdftotext):
    """poppler's pdftotext, the one tools/resume.py takes: it has -bbox-layout."""
    try:
        run = subprocess.run([pdftotext, "-h"], capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "-bbox-layout" in run.stdout + run.stderr


def own_wrapper(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return WRAPPER_MARK in f.read(4096)
    except OSError:
        return False


def poppler_folder(d):
    """d when it holds poppler's pdfinfo, pdftoppm and a pdftotext with -bbox-layout, else None."""
    ok = all(os.path.isfile(os.path.join(d, n)) and os.access(os.path.join(d, n), os.X_OK) for n in POPPLER_TOOLS)
    return d if ok and has_bbox_layout(os.path.join(d, "pdftotext")) else None


def found_poppler():
    """(folder, how): a poppler 0.1.0's tools/resume.py finds in every shell (on PATH, or in Homebrew's
    folders, which it searches by name), or one only POPPLER_BIN names, which a new shell does not see."""
    # ~/.local/bin too: a poppler built with --prefix ~/.local (install_poppler puts that folder on PATH)
    local_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    for d in os.environ.get("PATH", "").split(os.pathsep) + ["/opt/homebrew/bin", "/usr/local/bin", local_bin]:
        if d and not own_wrapper(os.path.join(d, "pdftotext")) and poppler_folder(d):
            return d, "found"
    if os.environ.get("POPPLER_BIN") and poppler_folder(os.environ["POPPLER_BIN"]):
        return os.environ["POPPLER_BIN"], "POPPLER_BIN"
    return None, None


def install_poppler(given=None):
    """conda-forge's poppler through micromamba into ~/.career-log/poppler, or the user's own poppler
    in `given` (or POPPLER_BIN), run from ~/.local/bin, where 0.1.0's tools/resume.py finds it on PATH."""
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin" and machine == "x86_64" and subprocess.run(   # an x86_64 Python under Rosetta
            ["sysctl", "-n", "sysctl.proc_translated"], capture_output=True, text=True).stdout.strip() == "1":
        machine = "arm64"
    subdir = {("Darwin", "arm64"): "osx-arm64", ("Darwin", "x86_64"): "osx-64",
              ("Linux", "x86_64"): "linux-64", ("Linux", "aarch64"): "linux-aarch64",
              ("Linux", "arm64"): "linux-aarch64"}.get((system, machine))
    if system not in ("Darwin", "Linux"):
        print("usage: --poppler is for macOS and Linux; on Windows 0.1.0's setup installs winget's poppler")
        return 2
    home = os.path.expanduser("~")
    env = os.path.join(home, ".career-log", "poppler")
    mamba_root = os.path.join(home, ".career-log", "micromamba")
    mamba = os.path.join(mamba_root, "micromamba")
    if given:
        given = os.path.abspath(os.path.expanduser(given))
        if not poppler_folder(given):
            print("failed: %s lacks poppler's pdfinfo, pdftoppm or a pdftotext with -bbox-layout" % given)
            return 1
        if own_wrapper(os.path.join(given, "pdftotext")):
            print("failed: %s holds this script's own scripts; give the folder poppler itself is in" % given)
            return 1
        return link_poppler(home, given)
    folder, how = found_poppler()
    if how == "found":
        if folder == os.path.join(home, ".local", "bin"):
            add_login_path(home)
        print("OK: poppler is already here (%s): nothing to install" % os.path.join(folder, "pdftotext"))
        return 0
    if how == "POPPLER_BIN" and not own_wrapper(os.path.join(folder, "pdftotext")):
        return link_poppler(home, folder)
    if subdir is None:
        print("failed: micromamba has no build for %s %s: install poppler yourself" % (system, machine))
        return 1
    if not shutil.which("curl"):
        print("failed: curl is missing (SETUP.md step 1)")
        return 1
    if not os.access(mamba, os.X_OK):
        url = "https://github.com/mamba-org/micromamba-releases/releases/download/%s/micromamba-%s" % (MAMBA_VERSION, subdir)
        print("Downloading micromamba %s (about 15-20 MB) into %s" % (MAMBA_VERSION, mamba_root), flush=True)
        os.makedirs(mamba_root, exist_ok=True)
        part = mamba + ".part"
        got = subprocess.run(["curl", "-fsSL", "--retry", "5", "-o", part, url])
        want = subprocess.run(["curl", "-fsSL", "--retry", "5", url + ".sha256"], capture_output=True, text=True)
        if got.returncode or want.returncode or not want.stdout.split():
            print("failed: micromamba did not download (offline, or behind a proxy: set HTTPS_PROXY); run this again")
            return 1
        with open(part, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != want.stdout.split()[0].lower():
            os.remove(part)
            print("failed: the micromamba download does not match its checksum; run this again")
            return 1
        os.chmod(part, 0o755)
        os.replace(part, mamba)
    # conda-forge only, whatever a .condarc of the user's says
    base = [mamba, "-y", "--no-rc", "-r", mamba_root]
    if os.path.isfile(os.path.join(env, "bin", "pdftotext")) and os.path.isdir(os.path.join(env, "conda-meta")):
        print("Updating poppler in %s (micromamba, conda-forge)" % env, flush=True)
        created = False
        run = subprocess.run(base + ["update", "-p", env, "--override-channels", "-c", "conda-forge", "--all"])
    else:
        shutil.rmtree(env, ignore_errors=True)   # what an interrupted run left
        created = True
        print("Installing poppler into %s (micromamba, conda-forge; 45 to 60 MB to download, about"
              " 230 MB on disk)" % env, flush=True)
        run = subprocess.run(base + ["create", "-p", env, "--override-channels", "-c", "conda-forge", "poppler"])
    shutil.rmtree(os.path.join(mamba_root, "pkgs"), ignore_errors=True)   # the downloaded packages
    works = has_bbox_layout(os.path.join(env, "bin", "pdftotext"))
    if run.returncode and works and not created:
        print("poppler: the update failed (its error is above); the installed poppler still works")
    elif run.returncode or not works:
        shutil.rmtree(env, ignore_errors=True)   # so that the next run makes it afresh
        print("failed: micromamba could not install poppler (its error is above); run this again")
        return 1
    print("done: poppler in %s" % env)
    return link_poppler(home, os.path.join(env, "bin"))


def link_poppler(home, folder):
    """pdfinfo, pdftotext and pdftoppm in ~/.local/bin, each a two-line script running the one in
    `folder` (not a link: each binary then finds its libraries from its own folder), and ~/.local/bin
    on the login shell's PATH."""
    local_bin = os.path.join(home, ".local", "bin")
    os.makedirs(local_bin, exist_ok=True)
    taken = [p for p in (os.path.join(local_bin, n) for n in POPPLER_TOOLS) if os.path.exists(p) and not own_wrapper(p)]
    if taken:
        print("failed: %s exists and is not this script's; move it away, then run this again" % taken[0])
        return 1
    for name in POPPLER_TOOLS:
        target = os.path.join(local_bin, name)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write('#!/bin/sh\n%s\nexec %s "$@"\n' % (WRAPPER_MARK, shlex.quote(os.path.join(folder, name))))
        os.chmod(target, 0o755)
    print("done: %s in %s, each running the one in %s" % (", ".join(POPPLER_TOOLS), local_bin, folder))
    add_login_path(home)
    print('OK: poppler in place; in a shell opened before this, run commands after export PATH="$HOME/.local/bin:$PATH"')
    return 0


def add_login_path(home):
    """~/.local/bin on PATH in the files login_profiles names."""
    for profile in login_profiles(home):
        line = 'export PATH="$HOME/.local/bin:$PATH"'
        try:
            with open(profile, encoding="utf-8", errors="replace") as f:
                if line in f.read():
                    continue
        except FileNotFoundError:
            pass
        with open(profile, "a", encoding="utf-8") as f:
            f.write("\n" + line + "\n")
        print("done: added to %s: %s" % (profile, line))


def check_poppler(log):
    """macOS: 0.1.0's setup would install Homebrew for a missing poppler, and build it from source
    where Homebrew has no packages for the macOS version."""
    if platform.system() != "Darwin":
        return
    if found_poppler()[0] or poppler_folder(os.path.join(os.path.expanduser("~"), ".local", "bin")):
        return
    log.out("migrate", "poppler: none on this Mac: install it with this script's --poppler before"
            " setup runs, as guide step 2 item 1 says (setup would install Homebrew for it)")


def login_profiles(home):
    """The files a shell reads, as 0.1.0's tools/setup.sh picks them, and ~/.zshrc too: zsh's
    ~/.zprofile and ~/.zshrc when the user's shell is zsh (a shell that reads only one of them finds
    poppler all the same), and the first of bash's login files that exists."""
    zsh = os.environ.get("SHELL", "").endswith("/zsh")
    out = [os.path.join(home, ".zprofile"), os.path.join(home, ".zshrc")] if zsh else []
    bash = next((os.path.join(home, p) for p in (".bash_profile", ".bash_login", ".profile")
                 if os.path.isfile(os.path.join(home, p))), os.path.join(home, ".profile"))
    return out + [bash]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if "-h" in argv or "--help" in argv:
        print(__doc__.rstrip())
        return 0
    if "--old-lines" in argv:
        rest = [a for a in argv if a != "--old-lines"]
        if len(rest) > 1:
            print("usage: upgrade-0.1.0.py [<root>] --old-lines")
            return 2
        log = Log(rest[0] if rest else ".")
        if log.git("rev-parse", "--git-dir") is None:
            print("usage: %s is not a git checkout of a Log" % log.root)
            return 2
        for rel in ("README.md", "README.zh-TW.md"):
            for n, line in old_template_lines(log, rel):
                print("%s:%d: %s" % (rel, n, line))
        return 0
    if "--poppler" in argv:
        if argv[0] != "--poppler" or len(argv) > 2:
            print("usage: upgrade-0.1.0.py --poppler [<poppler bin folder>]")
            return 2
        return install_poppler(argv[1] if len(argv) > 1 else None)
    apply, rest = None, []
    it = iter(argv)
    for a in it:
        if a == "--apply":
            apply = next(it, None)
            if apply not in ("engine", "log"):
                print("usage: --apply takes engine or log")
                return 2
        else:
            rest.append(a)
    if len(rest) > 1:
        print("usage: upgrade-0.1.0.py [<root>] [--apply engine|log]")
        return 2
    log = Log(rest[0] if rest else ".")
    if not os.path.isdir(os.path.join(log.root, ".git")) and log.git("rev-parse", "--git-dir") is None:
        print("usage: %s is not a git checkout of a Log" % log.root)
        return 2
    if apply == "log" and sys.version_info < (3, 11):
        print("migrate: Python %d.%d: --apply log needs 3.11+ (tools/config.py); run machine setup first"
              " (guide step 2)" % sys.version_info[:2])
        return 1
    check_branches(log)   # git refs only: settled in guide step 0, whatever the Engine
    check_poppler(log)   # this machine, whatever the Engine: guide step 2
    if check_engine(log, apply):
        check_config(log, apply)
        check_direction(log, apply)
        check_profile(log)
        check_text_updates(log, apply)
        check_stories(log, apply)
        check_outputs(log, apply)
        check_pages(log, apply)
        check_entries(log, apply)
        if os.path.isfile(log.path("tools/entries.py")):
            check_tools(log)
    if apply:   # what it changed, then a fresh check of what is left
        for line in log.lines:
            if line.startswith("done:"):
                print(line)
        return main(rest)
    for line in log.lines:
        print(line)
    left = [l for l in log.lines if l.startswith(("apply:", "migrate:", "ask:"))]
    if not left:
        print("OK: nothing left to migrate")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
