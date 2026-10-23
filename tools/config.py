#!/usr/bin/env python3
"""Read, check and change a Log's config.toml (Config, GLOSSARY.md); skills/career-log/modes/setup.md runs it.

  python3 -I tools/config.py fields                  (Windows: py -3 -I tools/config.py ...)
  python3 -I tools/config.py show
  python3 -I tools/config.py init
  python3 -I tools/config.py set <field> <value> [--dry-run]

Each takes --root <root>, the Log's root (default: the repo this script is in).

fields: every name setup can change, one per line: the Config fields as `config: <field> (<values>)`
and the Direction items as `direction: <item> (direction.md › <section>)`. A name outside this list
is not a field: a change request is mapped onto these names only.
show: `config.toml: missing` (setup has not run for this Log), or one `<field> = "<value>"` line per
field (a number without quotes), marked `(default)` when config.toml leaves it out.
init: writes config.toml from tools/config.default.toml, every field at its default; refuses when
config.toml exists.
set: checks the field's name and value, prints `before:` and `after:` lines, and writes the new
value in place, keeping the file's comments; --dry-run prints and writes nothing. It refuses a value
that would put fit_budget above screen_budget (ORDERED), naming the other field to change first.

Exit 0 on success, 1 when config.toml is missing (show, set), exists (init) or does not parse, or a
name or value is not allowed, 2 on a bad argument. Standard library only, Python 3.11+ (tomllib).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULTS_FILE = os.path.join(HERE, "config.default.toml")
NAME = "config.toml"



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
}
# Pairs of Count fields `set` keeps in order: (smaller, larger), the first never above the second.
ORDERED = [("fit_budget", "screen_budget")]
# Direction items setup asks about, and where each lives in direction.md. No defaults: an item with
# no line, or only a `GAP:` line, is empty.
DIRECTION = {
    "target roles": "Target roles, ranked",
    "sorting order": "Employer preferences, its `**Sorting order` line",
    "work authorisation": "Constraints",
    "other hard constraints": "Constraints",
    "what to emphasise": "What to emphasise, by target",
}


class ConfigError(Exception):
    pass


def defaults():
    import tomllib
    with open(DEFAULTS_FILE, "rb") as f:
        return tomllib.load(f)


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
    parse or holds a name or value it may not."""
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
    with open(DEFAULTS_FILE, encoding="utf-8") as f:
        text = f.read()
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
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
    if old == value and not was_default:
        return out + ["unchanged"]
    values = {f: v for f, (v, _) in config.items()} | {field: value}
    for small, large in ORDERED:
        if field in (small, large) and values[small] > values[large]:
            other = large if field == small else small
            raise ConfigError("%s = %s would put %s above %s (%s); change %s first" % (
                field, toml_value(value), small, large, values[large], other))
    if dry_run:
        return out + ["dry run: nothing written"]
    with open(path(root), encoding="utf-8-sig") as f:
        text = f.read()
    pattern = re.compile(r"^[ \t]*%s[ \t]*=.*$" % re.escape(field), re.M)
    if pattern.search(text):
        text = pattern.sub(lambda m: line, text, count=1)
    else:
        text = text + ("" if text.endswith("\n") or not text else "\n") + line + "\n"
    if parse(text, path(root)).get(field) != value:   # nothing is written that does not parse to the new value
        raise ConfigError("%s: could not place `%s` in it; edit the file by hand" % (path(root), line))
    with open(path(root), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
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
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    usage = "usage: config.py fields | show | init | set <field> <value> [--dry-run]  [--root <root>]"
    if not args or args[0] not in ("fields", "show", "init", "set"):
        print(usage)
        return 2
    try:
        if args[0] == "fields" and len(args) == 1:
            lines = field_lines()
        elif args[0] == "show" and len(args) == 1:
            config = load(root)
            for line in show_lines(config):
                print(line)
            return 0 if config is not None else 1
        elif args[0] == "init" and len(args) == 1:
            lines = init(root)
        elif args[0] == "set" and len(args) == 3:
            lines = set_field(root, args[1], args[2], dry_run)
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
