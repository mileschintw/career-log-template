#!/usr/bin/env python3
"""Check drafts against the fixed-string rules of skills/career-log/writing.md, before review.

  python3 -I tools/writing_lint.py <file>... [--across] [--posting <posting.md>] [--root <root>]
  (Windows: py -3 -I tools/writing_lint.py ...)

A <file> ending in `.tex` is a resume; any other is prose (form answers, a cover letter, a report),
read as Markdown: each heading starts an answer, and HTML comments, fenced code, tables, `Type:`
lines and the `## Company context` and `## Risks...` sections are skipped. <root> is the Log's root
(default: the folder above this script's); its skills/career-log/writing.md gives the word lists, so
a word added to a list there is checked with no change here.

What it checks, by writing.md rule:
- every file: AI-tell check 1 (the em dash; `---` and `\\textemdash` in a .tex), 2 and 6 (the quoted
  phrases), 3 (the stock AI words, with their inflections), and the Visibility rule of SKILL.md (a
  link to anything a `visibility: private` or `GAP` entry links: under a `links:` value, or a URL its
  text holds);
- prose: AI-tell check 5 (a `**Label:**` line or a bold mini-heading), and each answer's length;
- a resume: Format › Bullets (personal pronouns, a trailing period), Opening verbs (the weak and
  inflated ones; a first word repeated within a section), no references section, Content › metrics
  (a bullet that opens with its number), No test counts, and the Skills section (its title, an item
  written with `/`, operating systems, editors and proficiency labels, an item no bullet shows);
- --across: AI-tell check 9 over every file given, each answer its own artifact: a number (not a
  year or a single digit) that appears in more than one;
- --posting: Skills › Names follow postings: a Skills item the posting's text does not hold.

Output, one line each, file by file, the --across lines last:
  fix: <file>:<line>: <what>: <what to do> (<rule>)       break the rule as written: change the text
  check: <file>:<line>: <what>: <the call to make> (<rule>)   a call the rule leaves to judgement
  count: <file>:<line> "<heading>": <n> words, <n> characters[, limit <n> <unit>]   each answer
The last line is `OK: no fix lines` (exit 0; decide each check line), or `FAIL: <n> fix lines: fix
each, decide each check line, then run it again` (exit 1). Exit 2 with `FAIL: <why>` when a file
cannot be read or writing.md has lost a list this reads. Standard library only, Python 3.11+.
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
from entries import entry_paths

WRITING = "skills/career-log/writing.md"


class LintError(Exception):
    pass


# ---- writing.md's lists ----

def rule_line(text, heading, lead):
    """The line under writing.md's heading (`## ` or `### `) whose bold text starts with lead."""
    body = logfiles.section(text, heading) or logfiles.section(text, heading, 3) or ""
    for line in body.splitlines():
        if re.match(r"\s*(?:\d+\.|-)\s+\*\*" + re.escape(lead), line):
            return line
    raise LintError("%s has no line starting **%s under %s: update tools/writing_lint.py" % (WRITING, lead, heading))


def plain(items, lead):
    """items, each checked to be a plain word or name (`VS Code`, `worked on`), else LintError: a list
    reworded past what this reads fails here, not quietly."""
    for i in items:
        if not re.fullmatch(r"[^\W\d_][\w'’ +#-]*", i):
            raise LintError('%s: the **%s line lists "%s", not a plain word: update tools/writing_lint.py'
                            % (WRITING, lead, i))
    return items


def split_list(value):
    """Comma-separated items, a last `or` dropped and a parenthetical kept with its item."""
    items, depth, cur = [], 0, ""
    for c in value:
        depth += (c == "(") - (c == ")")
        if c == "," and depth == 0:
            items.append(cur)
            cur = ""
        else:
            cur += c
    items.append(cur)
    return [re.sub(r"^(?:or|and)\s+", "", i.strip()) for i in items if i.strip()]


def named_list(line, label, lead):
    """The items in `<label> (a, b, c)` on line."""
    m = re.search(re.escape(label) + r" \(([^)]*)\)", line)
    if not m or not split_list(m.group(1)):
        raise LintError("%s: the **%s line has no list after \"%s\": update tools/writing_lint.py"
                        % (WRITING, lead, label))
    return plain(split_list(m.group(1)), lead)


def quoted(line, lead):
    """The quoted phrases listed after the line's first ` no `, up to the first one not followed by
    `, "` (a quoted example later in the line is not in the list)."""
    m = re.search(r'\bno\b[^"]*("[^"]+"(?:,\s*(?:or\s+)?"[^"]+")*)', line.split("**", 2)[-1])
    found = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    if not found:
        raise LintError("%s: the **%s line has no quoted phrase: update tools/writing_lint.py" % (WRITING, lead))
    return found


def read_rules(root):
    """The word lists, read from the Log's writing.md."""
    path = os.path.join(root, *WRITING.split("/"))
    try:
        text = logfiles.read_text(path)
    except (OSError, UnicodeDecodeError) as e:
        raise LintError("cannot read %s: %s" % (WRITING, e))
    r = {}
    tells, fmt, skills = "AI-tell check", "Format", "Skills section"
    line = rule_line(text, tells, "Join clauses")
    m = re.search(r"em dash \((\S)\)", line)
    if not m:
        raise LintError("%s: the **Join clauses line has no `em dash (<char>)`: update tools/writing_lint.py" % WRITING)
    r["dash"] = m.group(1)
    r["phrases"] = quoted(rule_line(text, tells, "Say what happened"), "Say what happened")
    line = rule_line(text, tells, "Plain words")
    body = re.sub(r"\s*\([^()]*\)\s*$", "", line.split(":", 1)[-1].strip()).rstrip(". ")
    words = split_list(body)
    if not words:
        raise LintError("%s: the **Plain words line has no word list: update tools/writing_lint.py" % WRITING)
    r["stock"] = [(re.sub(r"\s*\(.*\)$", "", w), (re.search(r"\((.*)\)$", w) or [None, None])[1]) for w in words]
    plain([w for w, _ in r["stock"]], "Plain words")
    r["openers"] = quoted(rule_line(text, tells, "Start with the answer"), "Start with the answer")
    line = rule_line(text, fmt, "Bullets")
    r["pronouns"] = named_list(line, "personal pronouns", "Bullets")
    line = rule_line(text, fmt, "Opening verbs")
    r["weak"] = named_list(line, "not weak", "Opening verbs")
    r["inflated"] = named_list(line, "not inflated", "Opening verbs")
    line = rule_line(text, skills, 'Titled "')
    r["skills_title"] = re.search(r'\*\*Titled "([^"]+)"', line).group(1)
    r["os"] = named_list(line, "operating systems", 'Titled "')
    r["editors"] = named_list(line, "editors", 'Titled "')
    r["levels"] = named_list(line, "proficiency labels", 'Titled "')
    return r


# ---- Reading the files ----

def word_re(phrase):
    """A phrase as whole words, any case, a typographic apostrophe matching a plain one."""
    p = re.escape(phrase).replace("'", "['’]")
    return re.compile(r"(?<![\w-])%s(?![\w-])" % p, re.I)


def squash(name):
    """A name compared loosely: its parenthetical, case and spaces dropped (`Linux (Ubuntu)`, `VSCode`)."""
    return re.sub(r"\s+", "", re.sub(r"\s*\(.*\)\s*$", "", name)).lower()


def skill_re(item):
    """A Skills item, its parenthetical dropped, as a name: `C` not inside `C#`, and a name of three
    letters or fewer (`Go`) in its own case."""
    name = re.sub(r"\s*\(.*\)\s*$", "", item).strip()
    return re.compile(r"(?<![\w+#&-])%s(?![\w+#&-])" % re.escape(name), 0 if len(name) <= 3 else re.I)


def inflected_re(word):
    """A stock word and its inflections (leverage, leverages, leveraged, leveraging)."""
    stems = {re.escape(word)} | ({re.escape(word[:-1])} if word.endswith("e") else set())
    return re.compile(r"(?<![\w-])(?:%s)(?:s|es|d|ed|ing|ly)?(?![\w-])" % "|".join(sorted(stems)), re.I)


def blank_comments(text):
    """HTML comments replaced by their line breaks, so line numbers hold."""
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def tex_plain(text):
    """A .tex fragment as the reader sees it: commands and braces dropped, escapes undone."""
    text = re.sub(r"\\\\\*?(?:\[[^\]]*\])?", " ", text)   # a line break: \\, \\*, \\[2pt]
    text = re.sub(r"\\(?:href|[hv]space\*?)\{[^}]*\}", "", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"\\(?=\s|$)", " ", text)   # a control space, or a lone \ at the line's end
    text = re.sub(r"(?<!\\)\$", "", text)   # math mode: $\sim$40\% reads ~40%
    text = re.sub(r"\\([%&#$_{}])", r"\1", text).replace("~", " ").replace("{", "").replace("}", "")
    return " ".join(text.replace("---", "—").replace("--", "–").split())


class Prose:
    """A prose file: its lines to check and its answers, (line number, heading, [(n, text)])."""

    def __init__(self, text):
        self.lines, self.answers = [], []
        fence, skip, answer = None, 0, [0, "", []]
        self.answers.append(answer)
        for n, line in enumerate(blank_comments(text).splitlines(), 1):
            m = re.match(r"\s*(`{3,}|~{3,})", line)
            if fence or m:
                fence = None if fence and m and m.group(1)[0] == fence[0] else (fence or m.group(1))
                continue
            h = re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if h:
                level = len(h.group(1))
                if skip and level > skip:   # a heading inside a skipped section
                    continue
                skip = level if re.match(r"(Company context|Risks)", h.group(2)) else 0
                answer = [n, h.group(2), []]
                self.answers.append(answer)
                continue
            if skip or line.lstrip().startswith("|") or re.match(r"\s*Type:", line):
                continue
            if line.strip():
                self.lines.append((n, line))
            answer[2].append((n, line))
        for a in self.answers:
            while a[2] and not a[2][-1][1].strip():
                a[2].pop()
            while a[2] and not a[2][0][1].strip():
                a[2].pop(0)
        self.answers = [a for a in self.answers if a[2] or LIMIT.search(a[1])]


class Resume:
    """A .tex resume: its body lines, its sections, its bullets and its Skills lines."""

    def __init__(self, text):
        self.lines, self.sections = [], []
        body = not re.search(r"^[^%\n]*\\begin\{document\}", text, re.M)
        for n, raw in enumerate(text.splitlines(), 1):
            line = re.sub(r"(?<!\\)%.*$", "", raw)
            if "\\begin{document}" in line:
                body = True
                continue
            if not body or not line.strip():
                continue
            self.lines.append((n, line))
            m = re.search(r"\\section\*?\{([^}]*)\}", line)
            if m:
                self.sections.append((n, tex_plain(m.group(1))))
        self.items = []
        for n, item in logfiles.tex_items(text):
            title = ""
            for hn, h in self.sections:
                if hn <= n:
                    title = h
            self.items.append((n, tex_plain(item), title))

    def skill_lines(self, title):
        """(line number, label, [items]) for each line of the section named title."""
        out, inside = [], False
        for n, line in self.lines:
            m = re.search(r"\\section\*?\{([^}]*)\}", line)
            if m:
                inside = tex_plain(m.group(1)).lower() == title.lower()
                continue
            if inside and "\\item" not in line and not re.match(r"\s*\\(?:begin|end|vspace)", line):
                text = tex_plain(line)
                label, colon, rest = text.partition(":")
                label, rest = (label, rest) if colon else ("", label)
                items = split_list(rest)
                if items:
                    out.append((n, label.strip(), items))
        return out


TEST_COUNT = re.compile(r"(?<![\w.])\d[\d,]*\+?\s+(?:(?:unit|integration|end-to-end|e2e|regression|"
                        r"automated|smoke|load|property-based|and|or|,)\s*)*tests?\b", re.I)
LIMIT = re.compile(r"(\d[\d,]*)[\s-]*(words?|characters?|chars?)\b", re.I)
URL = re.compile(r"(?:https?://|(?<![\w./])(?:www\.)?(?:github\.com|gitlab\.[a-z.]+)/)[^\s<>\"'`)\]}|\\]+", re.I)


def norm_url(url, cut=False):
    """A URL without scheme, `www.`, query, fragment or trailing `/`, host lowercased, and a GitHub or
    GitLab path lowercased without `.git`; with cut, such a URL ends before its first URL_END segment
    (the repo root)."""
    url = re.sub(r"^https?://", "", url.strip().rstrip(".,;:"), flags=re.I)
    url = re.split(r"[#?]", re.sub(r"^www\.", "", url, flags=re.I))[0].rstrip("/")
    host, _, path = url.partition("/")
    segs = [s for s in path.split("/") if s]
    if re.match(r"github\.com$|gitlab\.", host, re.I):
        segs = [re.sub(r"\.git$", "", s.lower()) for s in segs]
        for i, s in enumerate(segs):
            if cut and i >= 2 and s in logfiles.URL_END:
                segs = segs[:i]
                break
    return "/".join([host.lower()] + segs)


def private_links(root):
    """[(normalized URL, whether a link under it counts too, entry path, visibility)] for every entry
    whose visibility is not public or nda (private, GAP or unset)."""
    out = []
    for path in entry_paths(root):
        try:
            text = logfiles.read_text(os.path.join(root, path))
        except (OSError, UnicodeDecodeError) as e:
            raise LintError("cannot read %s: %s" % (path, e))
        fields = logfiles.front_matter(text)
        vis = (fields.get("visibility") or "GAP").strip()
        if vis.lower() in ("public", "nda"):
            continue
        links = fields.get("links")
        for url in URL.findall(", ".join(links) if isinstance(links, list) else links or ""):
            out.append((norm_url(url, cut=True), "link", path, vis))   # a value may carry a note: `<url> (mirror)`
        for url in URL.findall(text):
            out.append((norm_url(url), "body", path, vis))
    return out


def under(url, prefix):
    """Whether url is a page under prefix: for GitHub and GitLab only below an owner/repo, so a
    profile link (`github.com/<user>`) does not cover every repo."""
    if not url.startswith(prefix + "/"):
        return False
    return not re.match(r"github\.com$|gitlab\.", prefix.split("/")[0]) or prefix.count("/") >= 2


# ---- The checks ----

class Lint:
    def __init__(self, rules, privates):
        self.r, self.privates = rules, privates
        self.out, self.fixes = [], 0

    def fix(self, where, what):
        line = "fix: %s: %s" % (where, what)
        if line not in self.out:
            self.out.append(line)
            self.fixes += 1

    def check(self, where, what):
        line = "check: %s: %s" % (where, what)
        if line not in self.out:
            self.out.append(line)

    def common(self, where, line, tex):
        r = self.r
        dashes = [r["dash"]] + (["---", "\\textemdash"] if tex else [])
        if any(d in line for d in dashes):
            self.fix(where, "em dash: join the clauses with a comma, a colon, parentheses or two sentences "
                            "(writing.md › AI-tell check: Join clauses)")
        text = tex_plain(line) if tex else line
        for p in r["phrases"]:
            if word_re(p).search(text):
                self.fix(where, '"%s": say what happened, at its real size (writing.md › AI-tell check: Say what happened)' % p)
        for w, note in r["stock"]:
            m = inflected_re(w).search(text)
            if m and note:
                self.check(where, '"%s": a stock AI word %s; when it is, use a plain word '
                                  '(writing.md › AI-tell check: Plain words)' % (m.group(0), note))
            elif m:
                self.fix(where, '"%s": a stock AI word: use a plain word (writing.md › AI-tell check: Plain words)' % m.group(0))
        for p in r["openers"]:
            if word_re(p).search(text):
                self.fix(where, '"%s": a chatbot opener or closer: start with the answer and stop when it is '
                                'given (writing.md › AI-tell check: Start with the answer)' % p)
        done = set()
        for url in URL.findall(line):
            u = norm_url(url)
            if u in done:   # \href{<url>}{<the same, as shown>}
                continue
            done.add(u)
            hits = [(kind, entry, vis) for p, kind, entry, vis in self.privates
                    if u == p or (kind == "link" and under(u, p))]
            link = next((h for h in hits if h[0] == "link"), None)
            if link:
                self.fix(where, "links %s, under a link of %s (visibility: %s): an output links nothing from a "
                                "private or GAP entry; take the link out (SKILL.md › Visibility)"
                         % (url.rstrip(".,;:"), link[1], link[2]))
            elif hits:
                self.check(where, "links %s, which %s (visibility: %s) cites: when it is that entry's own repo, "
                                  "document or PR, take the link out; a public source it cites may stay "
                                  "(SKILL.md › Visibility)" % (url.rstrip(".,;:"), hits[0][1], hits[0][2]))

    def prose(self, name, text):
        doc = Prose(text)
        for n, line in doc.lines:
            where = "%s:%d" % (name, n)
            self.common(where, line, False)
            if re.match(r"\s*(?:[-*+]\s+|\d+\.\s+)?\*\*[^*]+?(?::\*\*|\*\*:)", line):
                self.check(where, "a **Label:** line: write it as a sentence where a sentence would do "
                                  "(writing.md › AI-tell check: Sentences in prose answers)")
            elif re.fullmatch(r"\s*\*\*[^*]+\*\*\s*", line):
                self.check(where, "a bold mini-heading: write it as a sentence where a sentence would do "
                                  "(writing.md › AI-tell check: Sentences in prose answers)")
        for n, heading, lines in doc.answers:
            body = "\n".join(l.strip() for _, l in lines)
            words, chars = len(body.split()), len(body)
            line = '%s:%d "%s": %d words, %d characters' % (name, n or lines[0][0], heading, words, chars)
            limits = list(LIMIT.finditer(heading))
            stated = [l for l in limits if re.search(r"(?:\(|\b(?:in|max|maximum|up to|under|limit|no more than)\s*)$",
                                                      heading[:l.start()], re.I)]
            m = (stated or limits or [None])[-1]   # "Name 3 words ... (50 words)", "In 50 words, name 3 words ..."
            if m:
                limit, unit = int(m.group(1).replace(",", "")), ("words" if m.group(2)[0] in "wW" else "characters")
                line += ", limit %d %s" % (limit, unit)
                if (words if unit == "words" else chars) > limit:
                    self.fix("%s:%d" % (name, n), "the answer is over its limit of %d %s: cut it to the limit "
                                                  "(write.md step 6)" % (limit, unit))
            self.out.append("count: " + line)
        return [("%s › %s" % (name, h) if h else name, lines) for n, h, lines in doc.answers]

    def resume(self, name, text, posting):
        r, doc = self.r, Resume(text)
        for n, line in doc.lines:
            self.common("%s:%d" % (name, n), line, True)
        for n, title in doc.sections:
            where = "%s:%d" % (name, n)
            if re.search(r"\breferences?\b", title, re.I):
                self.fix(where, 'a "%s" section: a resume has no references section; take it out '
                                "(writing.md › Format: Dates)" % title)
            elif re.search(r"skill", title, re.I) and title.lower() != r["skills_title"].lower():
                self.fix(where, 'the skills section is titled "%s": title it "%s" (writing.md › Skills section)'
                         % (title, r["skills_title"]))
        if not doc.items and doc.lines:
            self.check(name, "no \\item bullets found, so the bullet checks did not run: check the bullets against "
                             "writing.md › Format and Content by reading them")
        pronouns = [re.compile(r"(?<![\w/-])(?:%s|%s)(?![\w/-])" % (re.escape(p), re.escape(p[:1].upper() + p[1:])))
                    for p in r["pronouns"]]
        firsts = {}
        for n, item, section in doc.items:
            where = "%s:%d" % (name, n)
            for p, rx in zip(r["pronouns"], pronouns):
                if rx.search(item):
                    self.fix(where, 'personal pronoun "%s": write the bullet without it (writing.md › Format: Bullets)' % p)
            if re.search(r"\b(?:Inc|Co|Ltd|Corp|etc)\.$", item.rstrip()):
                self.check(where, "ends in an abbreviation's period: when the abbreviation can go, end the bullet "
                                  "without a period (writing.md › Format: Bullets)")
            elif item.rstrip().endswith("."):
                self.fix(where, "trailing period: end the bullet without one (writing.md › Format: Bullets)")
            for kind, verbs in (("weak", r["weak"]), ("inflated", r["inflated"])):
                for v in verbs:
                    if re.match(re.escape(v) + r"\b", item, re.I):
                        self.fix(where, 'opens with the %s verb "%s": open with a strong past-tense verb '
                                        "(writing.md › Format: Opening verbs)" % (kind, v))
            if re.match(r"[~$<>≈]?\d", item):
                self.fix(where, "opens with its number: lead with the action, the metric right after it or at "
                                "the end (writing.md › Content: Keep measured metrics)")
            m = TEST_COUNT.search(item)
            if m:
                self.fix(where, '"%s": a test count is not resume content; take it out (writing.md › Content: '
                                "No test counts)" % m.group(0))
            first = re.match(r"[A-Za-z][\w-]*", item)
            if first:
                firsts.setdefault((section, first.group(0).lower()), []).append(n)
        for (section, verb), lines in firsts.items():
            if len(lines) > 1:
                self.check("%s:%d" % (name, lines[1]), '"%s" opens %d bullets in %s (lines %s): vary the opening '
                                                       "verbs within a section (writing.md › Format: Opening verbs)"
                           % (verb, len(lines), section or "the resume", ", ".join(map(str, lines))))
        bullet_text = " ".join(item for _, item, _ in doc.items)
        posting_text = posting or ""
        for n, label, items in doc.skill_lines(r["skills_title"]):
            where = "%s:%d" % (name, n)
            if re.search(r"\b(?:soft|interpersonal)\b", label, re.I):
                self.check(where, 'the "%s" line: no soft skills in Skills (writing.md › Skills section)' % label)
            for w in r["levels"]:
                if word_re(w).search(label):
                    self.fix(where, '"%s": a proficiency label; group the line by category instead '
                                    "(writing.md › Skills section)" % label)
            unshown, unposted = [], []
            for item in items:
                if "/" in item:
                    self.check(where, '"%s": write each name on its own, comma-separated ("C, C++"), unless the '
                                      "slash is part of the tool's own name (writing.md › Skills section)" % item)
                for kind, words in (("an operating system", r["os"]), ("an editor", r["editors"])):
                    if any(squash(item) == squash(w) for w in words):
                        self.fix(where, '"%s" is %s: take it out of Skills (writing.md › Skills section)' % (item, kind))
                for w in r["levels"]:
                    if word_re(w).search(item):
                        self.fix(where, '"%s": a proficiency label; take it out (writing.md › Skills section)' % w)
                if not skill_re(item).search(bullet_text):
                    unshown.append(item)
                if posting is not None and not skill_re(item).search(posting_text):
                    near = sorted({w for w in re.findall(r"[\w.+#-]+", posting_text)
                                   if min(len(item), len(w)) >= 5 and w.lower() != item.lower()
                                   and (w.lower().startswith(item.lower()[:5]) or item.lower().startswith(w.lower()[:5]))})
                    unposted.append('"%s"%s' % (item, " (the posting writes %s)" % ", ".join(near[:3]) if near else ""))
            if unposted:
                self.check(where, "%s: not in the posting; write each the way the posting does, or keep it only as a "
                                  "tool the posting's role uses (writing.md › Skills: Names follow postings)"
                           % ", ".join(unposted))
            if unshown:
                self.check(where, "%s: in no bullet; show each in one where the log has a use of it, or, when none "
                                  "can, keep it as thin evidence (writing.md › Skills section)"
                           % ", ".join('"%s"' % i for i in unshown))
        return [(name, [(n, item) for n, item, _ in doc.items] +
                 [(n, ", ".join(items)) for n, _, items in doc.skill_lines(r["skills_title"])])]

    def across(self, artifacts):
        seen = {}
        for art, lines in artifacts:
            for n, line in lines:
                line = re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?\b", " ", line)   # a date's parts are not numbers
                for m in re.finditer(r"(?<![\w./+#])(\d{1,3}(?:,\d{3})+(?!\d)|\d+(?:\.\d+)?)", line):
                    num = m.group(1).replace(",", "")
                    if re.fullmatch(r"(19|20)\d\d|\d", num):   # a year, or a count too small to be evidence
                        continue
                    seen.setdefault(num, {}).setdefault(art, n)
        for num, arts in seen.items():
            if len(arts) > 1:
                self.check("%s:%d" % next((a.split(" › ")[0], n) for a, n in arts.items()),
                           "%s appears in %d artifacts (%s): when it is the same evidence, keep it in one "
                           "artifact and give the others their own (writing.md › AI-tell check: Spend the words)"
                           % (num, len(arts), "; ".join("%s:%d" % (a, n) for a, n in arts.items())))


def main(argv):
    logfiles.utf8_stdout()
    try:
        root, rest = logfiles.split_root(argv, __file__)
    except logfiles.LogError as e:
        print("FAIL: %s" % e)
        return 2
    p = argparse.ArgumentParser(description="Check drafts against writing.md's fixed-string rules.")
    p.add_argument("files", nargs="+")
    p.add_argument("--across", action="store_true", help="AI-tell check 9 over every file given")
    p.add_argument("--posting", help="the posting's text, for Skills › Names follow postings")
    try:
        args = p.parse_args(rest)
    except SystemExit as e:
        if e.code:
            print("FAIL: bad arguments; see `writing_lint.py --help`")
        return 2 if e.code else 0
    try:
        rules = read_rules(root)
        lint = Lint(rules, private_links(root))
        posting = None
        if args.posting:
            try:
                posting = logfiles.read_text(args.posting)
            except (OSError, UnicodeDecodeError) as e:
                raise LintError("cannot read the posting %s: %s" % (args.posting, e))
        artifacts = []
        for f in args.files:
            try:
                text = logfiles.read_text(f)
            except (OSError, UnicodeDecodeError) as e:
                raise LintError("cannot read %s: %s" % (f, e))
            if f.lower().endswith(".tex"):
                artifacts += lint.resume(f, text, posting)
            else:
                artifacts += lint.prose(f, text)
        if args.across:
            lint.across(artifacts)
    except LintError as e:
        print("FAIL: %s" % e)
        return 2
    for line in lint.out:
        print(line)
    if lint.fixes:
        print("FAIL: %d fix lines: fix each, decide each check line, then run it again" % lint.fixes)
        return 1
    print("OK: no fix lines")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
