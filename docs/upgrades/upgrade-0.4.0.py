#!/usr/bin/env python3
"""Find what a Log still has in the formats of 0.3.2, and fix what is mechanical.

  python3 -I upgrade-0.4.0.py <root> [--apply]      (Windows: py -3 -I ...)

<root> is the Log's root. The guide that goes with this script, upgrade-0.4.0.md, says what to do
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
import importlib.util, os, sys


def log_tool(root, name):
    """The Log's own tools/<name>.py as a module: the Engine this guide runs on."""
    spec = importlib.util.spec_from_file_location("log_" + name, os.path.join(root, "tools", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_story_names(root, apply):
    """#695: a Story's key may carry a name. One review: line per key with no name that two or more
    Story index rows list (a #pending key aside): the rows may hold different Stories of one section."""
    entries = log_tool(root, "entries")
    rows = list(entries.first_rows(entries.story_index(root) or []).values())
    types = {}
    for row in rows:
        for key in dict.fromkeys(s.key for s in row.stories):
            if not entries.split_key(key)[2] and not entries.pending_key(key):
                types.setdefault(key, []).append(row.type)
    for key, listed in types.items():
        if len(listed) > 1:
            yield "review", "stories.md: %s: no name, in %d rows: %s" % (key, len(listed), " | ".join(listed))


# Each check goes into this list itself: the export reads `CHECKS = []` as no change.
CHECKS = [check_story_names]
BLOCKING = ("apply", "migrate", "ask")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    apply = "--apply" in argv
    rest = [a for a in argv if a != "--apply"]
    if len(rest) != 1 or not os.path.isdir(os.path.join(rest[0], ".git")):
        print("usage: upgrade-0.4.0.py <root> [--apply], <root> a Log's git checkout")
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
