"""The Trigger check, run from the skill's folder (SKILL.md): this file's real path, a skill link
resolved, gives the Log's root, and <root>/tools/check.py <mode> runs there; its first line is
`root: <root>`. With no mode, it prints only that line (guide and upgrade have no check).

  python3 -I <this skill's base directory>/start.py [<mode>]     (Windows: py -3 -I ...)

Any Python 3 runs it, so an old one still gets as far as check.py saying it is too old; one that
cannot resolve the link (Windows before Python 3.8) finds no tools/check.py and says so. It exits
with check.py's exit code.
"""
import os, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):   # the root in any language, as check.py prints it
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
check = os.path.join(root, "tools", "check.py")
if not os.path.isfile(check):
    print("root: not found (no %s; this Python, %s, may not resolve the skill link: run this with"
          " Python 3.11+)" % (check, sys.version.split()[0]))
    sys.exit(1)
if len(sys.argv) < 2:
    print("root: " + root)
    sys.exit(0)
sys.exit(subprocess.call([sys.executable, "-I", check] + sys.argv[1:]))
