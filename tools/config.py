#!/usr/bin/env python3
"""Read, check and change a Log's config.toml (Config, GLOSSARY.md) and its Direction items; skills/career-log/modes/setup.md runs it.

  python3 -I tools/config.py fields                  (Windows: py -3 -I tools/config.py ...)
  python3 -I tools/config.py show
  python3 -I tools/config.py init
  python3 -I tools/config.py set <field> <value> [--dry-run]
  python3 -I tools/config.py direction set <item> <line>... [--target <target>] [--drop-indented] [--dry-run]

Each takes --root <root>, the Log's root (default: the repo this script is in).

fields: every name setup can change, one per line: the Config fields as `config: <field> (<values>)`
and the Direction items as `direction: <item> (direction.md › <section>)`. A name outside this list
is not a field: a change request is mapped onto these names only.
show: `config.toml: missing` (setup has not run for this Log), or one `<field> = "<value>"` line per
field (a number without quotes), marked `(default)` when config.toml leaves it out. Then, for each
Direction item, one `direction <item>: <line>` line per line of direction.md it holds (a list line's
text after its list mark, then its indented lines as they stand), or `direction <item>: empty` when
it holds no list line or only `GAP:` ones, or `direction <item>: unreadable (<why>)` when
direction.md or the item's section is missing.
init: writes config.toml from tools/config.default.toml, every field at its default; refuses when
config.toml exists.
set: checks the field's name and value, prints `before:` and `after:` lines, and writes the new
value in place, keeping the file's comments; --dry-run prints and writes nothing. A value equal to
the current one, a `(default)` one too, prints `unchanged` and writes nothing. It refuses a value
that would put fit_budget above screen_budget (ORDERED), naming the other field to change first.
  front_page trimmed: when README.md above `## Entries` is still the Template's page, it also
  replaces that part with the personal index (TRIMMED) and deletes README.zh-TW.md, saying so on a
  `front page:` line; refused when the page is neither the Template's nor that index (the user's
  own text would be lost).
  front_page full: refused until README.md above `## Entries` is the Template's page again
  (tools/template/README.md) and README.zh-TW.md exists; the user restores them by hand.
  interviewer_profiles always, with --dry-run: a `tell the user:` line, the risk to say with it.
direction set: writes one Direction item's whole new list in place of the lines it holds, each list
line its own argument (a line as show prints it, its source and label included, is read as the same
line); the other lines of its section stay. A line the item already holds, its source aside, keeps
that source; each other line gets `(user, <today>)`. A line left out is deleted: to add one, pass
the `before:` lines to keep with it. An argument that starts with a space or tab is an indented line
of the list line argument before it, in place of that line's own: one the item already holds, its
source aside, is written as it stands, its indentation too (show prints them so: passed back they
are the same lines); another is written as given, with the source. An unindented argument that is
one of the item's indented lines (its list mark aside) is left out. A list line given none keeps its own when it stays
as it is. Each of the item's indented lines the new lines no longer hold, under any line, is printed
as a `drops:` line after the `after:` lines; a change with any is written only with --drop-indented,
the user's yes to the dry run that showed them. A line given twice is refused.
  target roles: a numbered list, best first, one line per argument. It holds the section's numbered
  lines, and its bullets only when it has no numbered line (a note under the list stays a note).
  work authorisation, sorting order: one line, written `- **<label>:** <line>`.
  visa sponsorship: one line, written `- **Visa sponsorship needed:** <value>`, right after work
  authorisation: `H-1B`, `green card (PERM)`, `OPT` (STEM OPT too), `CPT`, several with `;` between
  them (written in that order: `H-1B; OPT`), or `none` (VISAS); any other value is refused (another
  visa goes in work authorisation's own words). tools/sponsorship.py reads it: H-1B asks for each
  employer's H-1B LCA records, a green card for its PERM filings, and OPT or CPT for no filing but the
  posting's wording (`sponsorship.py wording`).
  other hard constraints: one bullet per argument, replacing every Constraints bullet that no other
  item labels; `none` alone writes `- **Other hard constraints:** none`. A line with another item's
  label (`Work authorisation: …`) is refused: it is that item's.
  what to emphasise: one line, for the resume target --target names (`Backend`, or `**Backend:**`
  as show prints it), written `- **<target>:** <line>`; the other targets' lines stay.
It prints `before:` and `after:` lines in show's `direction` form, any `drops:` lines, then
`unchanged` (the same lines, sources aside: nothing written), `dry run: nothing written` or `written`.

Exit 0 on success, 1 when config.toml is missing (show, set), exists (init) or does not parse,
tools/config.default.toml cannot be read, direction.md or the item's section is missing (direction
set), or a name or value is not allowed, 2 on a bad argument. Standard library only, Python 3.11+
(tomllib).
"""
import datetime, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULTS_FILE = os.path.join(HERE, "config.default.toml")
NAME = "config.toml"
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles



class Count:
    """A whole number from lo to hi, written without quotes."""
    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi

    def __contains__(self, value):
        return isinstance(value, int) and not isinstance(value, bool) and self.lo <= value <= self.hi

    def __str__(self):
        return "a whole number from %d to %d" % (self.lo, self.hi)


# Each Config field: its allowed values (strings, and a Count for a number), or None for free text on
# one line (a language's name).
FIELDS = {
    "record_language": None,
    "interviewer_profiles": ("never", "always"),
    "front_page": ("full", "trimmed"),
    "window": (Count(1, 90),),
    "scheduled_window": ("window", Count(1, 90)),
    "screen_budget": (Count(1, 100),),
    "fit_budget": (Count(1, 50),),
    "n": (Count(1, 50),),
    "auto_write": ("off", "on"),
    "m": (Count(1, 20),),
    "update_check": ("on", "off"),
    "resume_max_pages": (Count(1, 3),),
}
# Pairs of Count fields `set` keeps in order: (smaller, larger), the first never above the second.
ORDERED = [("fit_budget", "screen_budget")]
# Direction items setup asks about, and where each lives in direction.md. No defaults: an item with
# no line, or only a `GAP:` line, is empty.
DIRECTION = {
    "target roles": "Target roles, ranked",
    "sorting order": "Employer preferences, its `**Sorting order` line",
    "work authorisation": "Constraints",
    "visa sponsorship": "Constraints",
    "other hard constraints": "Constraints",
    "what to emphasise": "What to emphasise, by target",
}
# How `show` and `direction set` find each Direction item's lines: its section's heading, and which
# list lines of that section are the item's: NUMBERED every one; a label, the bullet `- **<label>…:**`;
# OTHERS every bullet that no labelled item of the section claims; BY_TARGET one `- **<target>:**`
# bullet per resume target. A new item adds its line here and in DIRECTION.
NUMBERED, OTHERS, BY_TARGET = "(numbered)", "(others)", "(by target)"
DIRECTION_LINES = {
    "target roles": ("Target roles, ranked", NUMBERED),
    "sorting order": ("Employer preferences", "Sorting order"),
    "work authorisation": ("Constraints", "Work authorisation"),
    "visa sponsorship": ("Constraints", "Visa sponsorship needed"),
    "other hard constraints": ("Constraints", OTHERS),
    "what to emphasise": ("What to emphasise, by target", BY_TARGET),
}
# The visa sponsorship item's values: each part (`;` between two) as the user may write it -> as it is
# written, and the lookup it asks for (tools/sponsorship.py): an H-1B LCA, a green card PERM filing, or
# None for a student's work authorisation (OPT, CPT), which no filing answers: the posting's wording does.
VISAS = {"h-1b": ("H-1B", "lca"), "h1b": ("H-1B", "lca"),
         "green card (perm)": ("green card (PERM)", "perm"), "green card": ("green card (PERM)", "perm"),
         "perm": ("green card (PERM)", "perm"), "opt": ("OPT", None), "stem opt": ("OPT", None),
         "cpt": ("CPT", None)}
DIRECTION_FILE = "direction.md"
ITEM = re.compile(r"^(?:\d+[.)]|[-*])[ \t]+(.*)$")   # a top-level list line
NUMBER = re.compile(r"^\d+[.)][ \t]")
LABEL = re.compile(r"^(?:\*\*([^*\n]+?)\*\*|([^*:\n]+):)")   # a line's `**Label:**`, or a plain `Label:`
SOURCE = re.compile(r"[ \t]*\([^()]*\d{4}-\d{2}-\d{2}[^()]*\)[ \t]*$")   # a line's trailing `(user, YYYY-MM-DD)`
# The front page setup trims to: README.md above `## Entries` becomes these lines.
TRIMMED = ("# career-log\n\nRaw records of my past work, projects and achievements, and the resumes and"
           " answers derived from them.\n\nHow to use it: [docs/guide.md](docs/guide.md).\n\n")
ENTRIES = re.compile(r"^## Entries[ \t]*$", re.M)
# Said with a change, on its --dry-run: (field, value) -> the line.
NOTICES = {("interviewer_profiles", "always"):
           "tell the user: the site may show each interviewer the visit unless the user's account browses"
           " privately, and its terms may limit automated reading"}


class ConfigError(Exception):
    pass


def defaults():
    """tools/config.default.toml's fields; ConfigError when it cannot be read or lacks one."""
    import tomllib
    try:
        with open(DEFAULTS_FILE, "rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError) as e:   # ValueError: TOMLDecodeError, or text that is not UTF-8
        raise ConfigError("%s cannot be read (%s); it is an Engine file: restore it from git or the Template"
                          % (DEFAULTS_FILE, e))
    missing = [f for f in FIELDS if f not in data]
    if missing:
        raise ConfigError("%s has no %s; it is an Engine file: restore it from git or the Template"
                          % (DEFAULTS_FILE, ", ".join(missing)))
    return data


def path(root):
    return os.path.join(root, NAME)


def check_value(field, value):
    """Raise ConfigError unless field is a Config field and value one it allows."""
    if field not in FIELDS:
        raise ConfigError("%s is not a Config field; the fields are %s (Direction items live in"
                          " direction.md: `config.py fields` lists both)" % (field, ", ".join(FIELDS)))
    allowed = FIELDS[field]
    if allowed is None:
        if not isinstance(value, str):
            raise ConfigError("%s must be a string in quotes" % field)
        if not value.strip() or re.search(r'["\\\r\n]', value):
            raise ConfigError("%s must be one line of text, without quotes or backslashes" % field)
    elif not any(value in a if isinstance(a, Count) else (isinstance(value, str) and value == a) for a in allowed):
        raise ConfigError("%s must be %s, not %s" % (field, allowed_text(allowed), toml_value(value)))


def allowed_text(allowed):
    return " or ".join(str(a) if isinstance(a, Count) else '"%s"' % a for a in allowed)


def toml_value(value):
    """A value as config.toml writes it: a number bare, text in quotes."""
    return '"%s"' % value if isinstance(value, str) else str(value)


def from_argument(field, value):
    """The command line's text as the field's value: a number for a field that takes one."""
    allowed = FIELDS.get(field) or ()
    if any(isinstance(a, Count) for a in allowed) and re.fullmatch(r"\d+", value.strip()):
        return int(value.strip())
    return value


def load(root):
    """{field: (value, is_default)}; None when config.toml is missing. ConfigError when it does not
    parse or holds a name or value it may not, or when tools/config.default.toml cannot be read."""
    p = path(root)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8-sig") as f:   # an editor may have added a BOM
            data = parse(f.read(), p)
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError("%s cannot be read: %s" % (p, e))
    base = defaults()
    return {f: (data[f], False) if f in data else (base[f], True) for f in FIELDS}


def parse(text, where):
    """The fields of a config.toml's text, each checked; ConfigError when it does not parse."""
    import tomllib
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError("%s does not parse: %s" % (where, e))
    for field, value in data.items():
        check_value(field, value)
    return data


def show_lines(config):
    if config is None:
        return ["%s: missing (setup has not run for this Log)" % NAME]
    return ["%s = %s%s" % (f, toml_value(v), " (default)" if d else "") for f, (v, d) in config.items()]


def field_lines():
    out = []
    for f, allowed in FIELDS.items():
        out.append("config: %s (%s)" % (f, allowed_text(allowed) if allowed else "one line of text"))
    for item, section in DIRECTION.items():
        out.append("direction: %s (direction.md › %s)" % (item, section))
    return out


def init(root):
    p = path(root)
    if os.path.exists(p):
        raise ConfigError("%s exists; change a field with `config.py set`" % p)
    defaults()   # an unreadable defaults file is refused before anything is written
    logfiles.write_text(p, logfiles.read_text(DEFAULTS_FILE))
    return ["wrote %s, every field at its default" % p] + show_lines(load(root))


def set_field(root, field, value, dry_run=False):
    value = from_argument(field, value)
    check_value(field, value)
    config = load(root)
    if config is None:
        raise ConfigError("%s is missing: setup runs `config.py init` first" % path(root))
    old, was_default = config[field]
    line = "%s = %s" % (field, toml_value(value))
    out = ["before: %s = %s%s" % (field, toml_value(old), " (default)" if was_default else ""), "after: " + line]
    if old == value:
        return out + ["unchanged"]
    values = {f: v for f, (v, _) in config.items()} | {field: value}
    for small, large in ORDERED:
        if field in (small, large) and values[small] > values[large]:
            other = large if field == small else small
            raise ConfigError("%s = %s would put %s above %s (%s); change %s first" % (
                field, toml_value(value), small, large, values[large], other))
    trim = field == "front_page" and front_page_change(root, value, out)
    if dry_run:
        return out + ([NOTICES[field, value]] if (field, value) in NOTICES else []) + ["dry run: nothing written"]
    with open(path(root), encoding="utf-8-sig") as f:
        text = f.read()
    pattern = re.compile(r"^[ \t]*%s[ \t]*=.*$" % re.escape(field), re.M)
    if pattern.search(text):
        text = pattern.sub(lambda m: line, text, count=1)
    else:
        text = text + ("" if text.endswith("\n") or not text else "\n") + line + "\n"
    if parse(text, path(root)).get(field) != value:   # nothing is written that does not parse to the new value
        raise ConfigError("%s: could not place `%s` in it; edit the file by hand" % (path(root), line))
    if trim:
        readme = os.path.join(root, "README.md")
        page = logfiles.read_text(readme)
        logfiles.write_text(readme, TRIMMED + page[ENTRIES.search(page).start():])
        if os.path.exists(os.path.join(root, "README.zh-TW.md")):
            os.remove(os.path.join(root, "README.zh-TW.md"))
    with open(path(root), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return out + ["written"]


# ---- The front page ----

def front_page_state(root):
    """What README.md above its `## Entries` line is: "template" (the same as
    tools/template/README.md's), "trimmed" (setup's personal index, TRIMMED), "edited" (anything
    else, or no `## Entries` line), or "missing" (no README.md). ConfigError when the Template's page
    or README.md cannot be read."""
    def head(p):
        text = logfiles.read_text(p)
        m = ENTRIES.search(text)
        return text[:m.start()] if m else None
    try:
        template = head(os.path.join(HERE, "template", "README.md"))
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError("tools/template/README.md cannot be read (%s); it is an Engine file" % e)
    readme = os.path.join(root, "README.md")
    if not os.path.exists(readme):
        return "missing"
    try:
        mine = head(readme)
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError("%s cannot be read: %s" % (readme, e))
    if mine is not None and mine == template:
        return "template"
    return "trimmed" if mine == TRIMMED else "edited"


def front_page_change(root, value, out):
    """Check a change of front_page against the page itself, adding a `front page:` line to out;
    True when the page is to be trimmed."""
    state = front_page_state(root)
    if value == "full":
        if state != "template" or not os.path.exists(os.path.join(root, "README.zh-TW.md")):
            raise ConfigError("front_page stays \"trimmed\" until the front page is the Template's again: the user"
                              " restores README.md above `## Entries` and README.zh-TW.md by hand, from"
                              " tools/template/ (git history may hold an older release's page; README.md is %s now)"
                              % state)
        return False
    if state == "template":
        out.append("front page: README.md above `## Entries` becomes the personal index, and README.zh-TW.md is deleted")
        return True
    if state != "trimmed":
        raise ConfigError("README.md above `## Entries` is %s, neither the Template's page nor the trimmed index, so"
                          " trimming would replace the user's own text: front_page stays \"full\"; the user edits the"
                          " page by hand" % state)
    return False


# ---- Direction ----

def direction_text(root):
    p = os.path.join(root, DIRECTION_FILE)
    if not os.path.exists(p):
        raise ConfigError("%s is missing" % DIRECTION_FILE)
    try:
        return logfiles.read_text(p)
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError("%s cannot be read: %s" % (DIRECTION_FILE, e))


def list_lines(lines):
    """[((first, end), text)] for each top-level list line of a section's lines outside HTML comments:
    its line range, indented continuation lines included, and its text after the list mark."""
    out, comment = [], False
    for i, line in enumerate(lines):
        if comment or line.lstrip().startswith("<!--"):
            comment = "-->" not in line
            continue
        m = ITEM.match(line)
        if m:
            out.append([[i, i + 1], m.group(1).strip()])
        elif out and out[-1][0][1] == i and line[:1] in " \t" and line.strip():
            out[-1][0][1] = i + 1
    return [(tuple(r), t) for r, t in out]


def label(text):
    m = LABEL.match(text)
    return (m.group(1) or m.group(2)).strip().rstrip(":").strip() if m else None


def claims(item, text, target=None, numbered=True):
    """Whether a list line of the item's section is one of the item's lines; numbered: whether it is
    a numbered line (a NUMBERED item takes bullets only from a section with no numbered line)."""
    heading, kind = DIRECTION_LINES[item]
    name = (label(text) or "").lower()
    if kind == NUMBERED:
        return numbered
    if kind == BY_TARGET:
        return target is None or norm(name) == norm(target.strip())
    if kind == OTHERS:
        return not any(claims(other, text) for other, (h, k) in DIRECTION_LINES.items()
                       if h == heading and k not in (NUMBERED, OTHERS, BY_TARGET))
    return norm(name).startswith(norm(kind))


def key(text):
    """A line's text for telling whether a kept line is the same line: its source left out, and its
    label (`**Label:**` or plain `Label:`) folded."""
    text = SOURCE.sub("", text)
    m = LABEL.match(text)
    return (norm(label(text)), text[m.end():].lstrip(" :").strip()) if m else (None, text.strip())


def norm(name):
    """A label for matching: lower case, -ize spelt -ise (a `**Work authorization:**` line too)."""
    return name.lower().replace("iz", "is")


def is_gap(text):
    m = LABEL.match(text)
    return text.startswith("GAP") or bool(m) and text[m.end():].lstrip(" :").startswith("GAP")


def item_lines(text, item, target=None):
    """(span of the item's section body in the text, the body's lines, the item's [((first, end), text)])."""
    heading = DIRECTION_LINES[item][0]
    span = logfiles.section_span(text, heading)
    if span is None:
        raise ConfigError("%s has no `## %s` section" % (DIRECTION_FILE, heading))
    lines = text[span[0]:span[1]].split("\n")
    found = list_lines(lines)
    numbered = [bool(NUMBER.match(lines[r[0]])) for r, _ in found]
    if not any(numbered):   # a list written as bullets: its bullets are the list
        numbered = [True] * len(found)
    return span, lines, [(r, t) for (r, t), n in zip(found, numbered) if claims(item, t, target, n)]


def shown(lines, found):
    """The item's lines as show prints them: each list line's text after its list mark, then its
    indented lines as they stand."""
    return [x for (first, end), t in found for x in [t] + [l.rstrip() for l in lines[first + 1:end]]]


def direction_lines(root):
    """show's `direction <item>:` lines."""
    try:
        text = direction_text(root)
    except ConfigError as e:
        return ["direction %s: unreadable (%s)" % (item, e) for item in DIRECTION_LINES]
    out = []
    for item in DIRECTION_LINES:
        try:
            _, lines, found = item_lines(text, item)
        except ConfigError as e:
            out.append("direction %s: unreadable (%s)" % (item, e))
            continue
        if all(is_gap(t) for _, t in found):
            out.append("direction %s: empty" % item)
        else:
            out += ["direction %s: %s" % (item, x) for x in shown(lines, found)]
    return out


def target_roles(root):
    """The target roles, best first, as show reads them (tools/scan.py reads them here too): each
    line's text after its list mark, `GAP:` lines left out; [] when direction.md or its section is
    missing."""
    try:
        _, _, found = item_lines(direction_text(root), "target roles")
    except ConfigError:
        return []
    return [t for _, t in found if not is_gap(t)]


def visa_value(text):
    """The visa sponsorship line's value as it is written (`H-1B; OPT`, `none`), the lookups it asks for
    and the student statuses it names (OPT, CPT), each in VISAS order; ConfigError for a value outside VISAS."""
    parts = [p.strip().rstrip(".").strip() for p in text.split(";")]
    if [p.lower() for p in parts] == ["none"]:
        return "none", (), ()
    found = [VISAS.get(re.sub(r"\s+", " ", p.lower())) for p in parts]
    if not parts or None in found:
        raise ConfigError("visa sponsorship is `H-1B`, `green card (PERM)`, `OPT` or `CPT`, several with `;` between"
                          " them (`H-1B; OPT`), or `none`, not `%s`; another visa (O-1, TN, another country's) goes in"
                          " work authorisation" % text.strip())
    order = list(dict.fromkeys(v for v in VISAS.values()))
    chosen = sorted(set(found), key=order.index)
    return ("; ".join(t for t, _ in chosen), tuple(k for _, k in chosen if k),
            tuple(t for t, k in chosen if not k))


def visa_line(root):
    """direction.md's `**Visa sponsorship needed:**` line as visa_value reads it: (written, lookups,
    statuses), or None with no such line (no direction.md or Constraints section either) or a `GAP:`
    one. ConfigError when direction.md cannot be read or the line's value is outside VISAS."""
    if not os.path.exists(os.path.join(root, DIRECTION_FILE)):
        return None
    text = direction_text(root)
    if logfiles.section_span(text, DIRECTION_LINES["visa sponsorship"][0]) is None:
        return None
    _, _, found = item_lines(text, "visa sponsorship")
    found = [t for _, t in found if not is_gap(t)]
    if not found:
        return None
    text = SOURCE.sub("", found[0])
    m = LABEL.match(text)
    try:
        return visa_value(text[m.end():].lstrip(" :") if m else text)
    except ConfigError as e:
        raise ConfigError("%s's `%s` line: %s; write it with `config.py direction set \"visa sponsorship\" <value>`"
                          % (DIRECTION_FILE, found[0], e))


def visa_lookups(root):
    """The lookups the visa sponsorship line asks for: () with no line, a `GAP:` or `none` one, or one
    that names only OPT or CPT, else ("lca",), ("perm",) or ("lca", "perm"). ConfigError as visa_line."""
    line = visa_line(root)
    return line[1] if line else ()


def visa_statuses(root):
    """The student statuses the visa sponsorship line names, ("OPT",), ("CPT",) or ("OPT", "CPT"), whose
    check is each posting's wording (tools/sponsorship.py wording); () for none. ConfigError as visa_line."""
    line = visa_line(root)
    return line[2] if line else ()


def direction_set(root, item, texts, target=None, dry_run=False, drop_indented=False):
    if item not in DIRECTION_LINES:
        raise ConfigError("%s is not a Direction item; the items are %s (`config.py fields` lists them)"
                          % (item, ", ".join(DIRECTION_LINES)))
    heading, kind = DIRECTION_LINES[item]
    if (kind == BY_TARGET) != (target is not None):
        raise ConfigError("%s needs --target <resume target>" % item if kind == BY_TARGET
                          else "--target is for what to emphasise only")
    if target is not None:   # a target as show prints its line, `**Backend:**`, is the target Backend
        target = label(target.strip() + ("" if target.strip().endswith(":") else ":")) or target.strip()
    if any(not SOURCE.sub("", t).strip() or re.search(r"[\r\n]", t) for t in texts) or (target is not None and not target.strip()):
        raise ConfigError("each line is one line of text, without its source")
    source = " (user, %s)" % datetime.date.today().isoformat()
    text = direction_text(root)
    span, lines, found = item_lines(text, item, target)
    # An argument that starts with a space or tab is an indented line of the list line before it, written
    # as given; one the item already holds, its source aside, is that line as it stands. A list line given
    # no indented lines keeps its own when it stays as it is. An unindented argument that is one of the
    # item's indented lines (with or without its list mark) is dropped: it is not a list line.
    old_sub = [(key(t), SOURCE.sub("", l.strip()), l.rstrip()) for (first, end), t in found for l in lines[first + 1:end]]
    indented = {k for _, k, _ in old_sub} | {SOURCE.sub("", (ITEM.match(k) or [None, k])[1]) for _, k, _ in old_sub}
    args, texts, subs = texts, [], []
    for t in args:
        if t[:1] in " \t":
            if not texts:
                raise ConfigError("`%s` is an indented line: give it after the list line it goes under" % t.strip())
            if any(SOURCE.sub("", l.strip()) == SOURCE.sub("", t.strip()) for l in subs[-1] or []):
                raise ConfigError("a line is given twice")
            subs[-1] = (subs[-1] or []) + [t.rstrip()]
        elif SOURCE.sub("", t.strip()) not in indented:   # a line copied from show comes with its source
            texts.append(SOURCE.sub("", t.strip()))
            subs.append(None)
    if not texts or kind not in (NUMBERED, OTHERS) and len(texts) != 1:
        raise ConfigError("%s takes one line" % item if kind not in (NUMBERED, OTHERS) else "%s takes a line or more" % item)
    if kind in (NUMBERED, OTHERS):
        bodies = (["**Other hard constraints:** none"] if kind == OTHERS and [t.lower().rstrip(".") for t in texts] == ["none"]
                  else texts)
        if bodies != texts and subs[0]:
            raise ConfigError("`none` takes no indented lines")
    else:
        name = label(found[0][1]) if found else target if kind == BY_TARGET else kind
        m = LABEL.match(texts[0])
        line = texts[0][m.end():].lstrip(" :") if m and norm(label(texts[0])) == norm(name) else texts[0]   # and its label
        if item == "visa sponsorship":
            line = visa_value(line)[0]
        bodies = [("**%s:** %s" % (name, line)).rstrip()]
    if len({key(b) for b in bodies}) < len(bodies):   # the same line, in two label forms too
        raise ConfigError("a line is given twice")
    if kind == OTHERS:
        for b in bodies:
            owner = next((i for i, (h, k) in DIRECTION_LINES.items() if h == heading and i != item and claims(i, b)), None)
            if owner:
                raise ConfigError("`%s` is a %s line: write it with `direction set \"%s\"`" % (b, owner, owner))
    kept = {key(t): t for _, t in found}
    # Which of the item's indented lines each new line holds: a kept line given none, its own; an argument
    # the item holds, its copy under the same list line first, else another copy. The rest go.
    used = {i for i, (parent, _, _) in enumerate(old_sub) for b, s in zip(bodies, subs)
            if s is None and key(b) in kept and parent == key(b)}
    pick = {}   # (new line, argument) -> the copy it is; first the copies under the same list line, for every line
    for same in (True, False):
        for j, (b, s) in enumerate(zip(bodies, subs)):
            for n, t in enumerate(s or []):
                k = SOURCE.sub("", t.strip())
                i = next((i for i, (parent, x, _) in enumerate(old_sub)
                          if x == k and i not in used and (parent == key(b)) == same), None)
                if (j, n) not in pick and i is not None:
                    pick[j, n] = i
                    used.add(i)
    now = [(kept.get(key(b), b + source),
            [l for parent, _, l in old_sub if parent == key(b)] if s is None and key(b) in kept else
            [old_sub[pick[j, n]][2] if (j, n) in pick else SOURCE.sub("", t) + source for n, t in enumerate(s or [])])
           for j, (b, s) in enumerate(zip(bodies, subs))]
    new = [x for i, (t, rest) in enumerate(now) for x in ["%d. %s" % (i + 1, t) if kind == NUMBERED else "- " + t] + rest]
    old = shown(lines, found)
    after = [x for t, rest in now for x in [t] + [l.rstrip() for l in rest]]
    out = (["before: direction %s: %s" % (item, x) for x in old] or ["before: direction %s: empty" % item]) + \
          ["after: direction %s: %s" % (item, x) for x in after]
    if [SOURCE.sub("", x) for x in old] == [SOURCE.sub("", x) for x in after]:
        return out + ["unchanged"]
    # The item's indented lines the new lines no longer hold: written only with --drop-indented, the
    # user's yes to the dry run that named them.
    drops = ["drops: direction %s: %s" % (item, l) for i, (_, _, l) in enumerate(old_sub) if i not in used]
    if drops and not dry_run and not drop_indented:
        raise ConfigError("this change deletes the indented lines its --dry-run prints as `drops:` lines: show the user"
                          " that dry run, and run it again with --drop-indented once they agree")
    out += drops
    if dry_run:
        return out + ["dry run: nothing written"]
    for (first, end), _ in reversed(found):
        del lines[first:end]
    items = list_lines(lines)
    if found and kind == OTHERS and items:   # after the section's labelled lines: work authorisation stays first
        at = max(found[0][0][0], items[-1][0][1])   # the lines left are the labelled ones
    elif found:
        at = found[0][0][0]
    elif items and kind not in (NUMBERED, OTHERS, BY_TARGET):
        # a labelled line leads its section, after the labelled items DIRECTION_LINES lists before it
        before = list(DIRECTION_LINES)[:list(DIRECTION_LINES).index(item)]
        ends = [r[1] for r, t in items if any(DIRECTION_LINES[i][0] == heading and DIRECTION_LINES[i][1] not in
                                              (NUMBERED, OTHERS, BY_TARGET) and claims(i, t) for i in before)]
        at = max(ends) if ends else items[0][0][0]
    elif items:
        at = items[-1][0][1]
    else:
        at = max([i + 1 for i, line in enumerate(lines) if line.strip()] or [0])
        if at and not lines[at - 1].rstrip().endswith("-->"):   # a list after a paragraph: a blank line between
            new = [""] + new
    lines[at:at] = new
    body = "\n".join(lines)
    if span[0] == len(text) and not text.endswith("\n"):   # the heading was the file's last line
        body = "\n" + body
    if not body.endswith("\n"):
        body += "\n"
    logfiles.write_text(os.path.join(root, DIRECTION_FILE), text[:span[0]] + body + text[span[1]:])
    return out + ["written"]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = list(argv)
    if "-h" in args or "--help" in args:
        print(__doc__.rstrip())
        return 0
    root = ROOT
    if "--root" in args:
        i = args.index("--root")
        if i + 1 >= len(args):
            print("usage: --root needs a path")
            return 2
        root = args[i + 1]
        del args[i:i + 2]
    target = None
    if "--target" in args:
        i = args.index("--target")
        if i + 1 >= len(args):
            print("usage: --target needs a resume target")
            return 2
        target = args[i + 1]
        del args[i:i + 2]
    dry_run, drop_indented = "--dry-run" in args, "--drop-indented" in args
    args = [a for a in args if a not in ("--dry-run", "--drop-indented")]
    usage = ("usage: config.py fields | show | init | set <field> <value> [--dry-run]"
             " | direction set <item> <line>... [--target <target>] [--drop-indented] [--dry-run]  [--root <root>]")
    if not args or args[0] not in ("fields", "show", "init", "set", "direction"):
        print(usage)
        return 2
    try:
        if args[0] == "fields" and len(args) == 1:
            lines = field_lines()
        elif args[0] == "show" and len(args) == 1:
            try:
                config = load(root)
                lines, code = show_lines(config), 0 if config is not None else 1
            except ConfigError as e:
                lines, code = ["config: %s" % e], 1
            for line in lines + direction_lines(root):   # Direction too: it needs no config.toml
                print(line)
            return code
        elif args[0] == "init" and len(args) == 1:
            lines = init(root)
        elif args[0] == "set" and len(args) == 3 and target is None:
            lines = set_field(root, args[1], args[2], dry_run)
        elif args[0] == "direction" and len(args) >= 4 and args[1] == "set":
            lines = direction_set(root, args[2], args[3:], target, dry_run, drop_indented)
        else:
            print(usage)
            return 2
    except ConfigError as e:
        print("config: %s" % e)
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
