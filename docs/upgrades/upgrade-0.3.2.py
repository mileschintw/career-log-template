#!/usr/bin/env python3
"""Find what a Log still has in the formats of 0.3.1, and fix what is mechanical.

  python3 -I upgrade-0.3.2.py <root> [--apply]      (Windows: py -3 -I ...)

<root> is the Log's root. The guide that goes with this script, upgrade-0.3.2.md, says what to do
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
import os, sys

# Each check goes into this list itself: the export reads `CHECKS = []` as no change.
CHECKS = []
BLOCKING = ("apply", "migrate", "ask")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    apply = "--apply" in argv
    rest = [a for a in argv if a != "--apply"]
    if len(rest) != 1 or not os.path.isdir(os.path.join(rest[0], ".git")):
        print("usage: upgrade-0.3.2.py <root> [--apply], <root> a Log's git checkout")
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
