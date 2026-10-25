#!/usr/bin/env python3
"""Which checks to run after an Engine change, from the paths it changed.

  python3 -I tools/checks_for.py <base>              (Windows: py -3 -I tools/checks_for.py ...)
  python3 -I tools/checks_for.py --paths <path>...

<base> is the commit the change started from (origin/<default> for a branch): the changed paths
are those `git diff <base>...HEAD` names, plus uncommitted and untracked ones. --paths takes
repo-relative paths instead. Both take --root <root>, the repo's root (default: the repo this
script is in).

It prints, in this order:
- one line per changed path: `engine: <path>` (an Engine path: the export's ALLOW list in
  tools/export-template.sh, its .export-* files, and, in the Template's source (a root with
  `maintainer/`), `.github/`, `maintainer/` and the maintainer docs; AGENTS.md › Changes says how it lands), `guard: <path>`
  (.export-deny, .export-cleared), `coordination: <path>` (docs/coordination/) or
  `not engine: <path>`;
- `warn:` when only one of the Template's two front pages changed;
- the checks: each `run: <command>` line followed by a `check: <what passing looks like>` line,
  and each `do: <step>` line (one that needs a person or a platform: no single command), each
  command once, or `run: none` when no check covers the paths. `<scratch>` is a new folder in
  your scratchpad. The PowerShell parse of tools/setup.ps1 is a `run:` line for PowerShell.

The map is GROUPS below: each group's triggers (an exact path, or a folder ending in `/` for
everything under it) and the checks it runs. A group with a workflow is what that workflow in
this repo's .github/workflows/ runs, on the same `paths:`, the workflow's own file included;
tools/tests/test_checks_for.py fails when the two disagree. A new tool or test: add its group here,
and in the Template's source its workflow with the same `paths:` plus its own file. A check whose script is missing (maintainer/
in a Template) is left out.

Exit 0 on success, 2 on a bad argument or a git error. Standard library only, Python 3.11+.
"""
import argparse, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
EXPORT = "tools/export-template.sh"
EXPORT_FILES = (".export-deny", ".export-allow", ".export-cleared")
GUARDS = (".export-deny", ".export-cleared")
COORDINATION = "docs/coordination/"
# Engine only here, in the Template's source (AGENTS.md › Changes); the export leaves them out
SOURCE_ENGINE = (".export-allow", ".github/", "maintainer/", "docs/maintaining.md",
                 "docs/maintaining-tests.md", "docs/migrating.md")
FRONT_PAGES = ("tools/template/README.md", "tools/template/README.zh-TW.md")
OK = "the last line is `OK`"


def py(script, check=OK):
    return ("py", script, check)


def sh(cmd, check):
    return ("sh", cmd, check)


def do(text):
    return ("do", text, None)


# (name, workflow or None, triggers, checks). The export group's triggers are read from
# tools/export-template.sh (export_triggers).
GROUPS = [
    ("export", "template-scan.yml", None, [
        sh("sh tools/export-template.sh <scratch>/export",
           "the last line is `OK`, with no `note: uncommitted` line (it exports commits only: commit first)"),
    ]),
    ("parser", "parser-tests.yml", [
        "tools/chat_export.py", "tools/tests/test_chat_export.py", "tools/tests/make_fixtures.py",
        "tools/tests/fixtures/", "tools/tests/expected/", "tools/check_run.py", "tools/entries.py",
        "tools/logfiles.py", "tools/tests/test_check_run.py", "tools/check_save.py", "tools/tests/test_check_save.py",
        "tools/writing_lint.py", "tools/resume.py", "tools/config.py", "tools/config.default.toml",
        "skills/career-log/writing.md", "skills/career-log/modes/review.md", "skills/career-log/modes/scan.md",
    ], [
        py("tools/tests/test_chat_export.py"),
        py("tools/tests/test_check_run.py"),
        py("tools/tests/test_check_save.py"),
    ]),
    ("deny coverage", "deny-coverage.yml", [
        "tools/deny_coverage.py", "tools/entries.py", "tools/logfiles.py", "tools/sync.py",
        "tools/tests/test_deny_coverage.py",
    ], [
        py("tools/tests/test_deny_coverage.py"),
    ]),
    ("entries", "entries-tests.yml", [
        "tools/entries.py", "tools/tests/test_entries.py", "tools/logfiles.py", "tools/tests/test_logfiles.py",
        "entries/_template.md",
    ], [
        py("tools/tests/test_logfiles.py"),
        py("tools/tests/test_entries.py"),
    ]),
    ("config", "config-tests.yml", [
        "tools/config.py", "tools/config.default.toml", "tools/logfiles.py", "tools/tests/test_config.py",
        "tools/template/README.md", "tools/template/README.zh-TW.md", "tools/template/direction.md",
    ], [
        py("tools/tests/test_config.py"),
        py("tools/tests/test_check.py"),
    ]),
    ("machine check", "machine-check.yml", [
        "tools/check.py", "tools/resume.py", "tools/entries.py", "tools/logfiles.py", "tools/upgrade.py",
        "tools/config.py", "tools/config.default.toml", "tools/tests/test_check.py",
        "tools/guide.py", "docs/guide.md", "skills/career-log/SKILL.md", "skills/career-log/start.py",
        "tools/setup.sh", "tools/setup.ps1",
    ], [
        py("tools/tests/test_check.py"),
        sh("sh -n tools/setup.sh", "it prints nothing and exits 0"),
        ("ps", "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
               "(Resolve-Path tools/setup.ps1).Path, [ref]$null, [ref]$e); $e",
         "run in PowerShell 7 and in Windows PowerShell 5.1, where you have them, it prints nothing"),
    ]),
    ("setup scripts", None, [
        "tools/setup.sh", "tools/setup.ps1",
    ], [
        do("run SETUP.md step 5 with the tools the change touches, on each platform you can; "
           "step 5's check holds"),
    ]),
    ("resume", "resume-tests.yml", [
        "tools/resume.py", "tools/tex-packages.txt", "tools/config.py", "tools/config.default.toml",
        "tools/logfiles.py", "tools/tests/test_resume.py", "skills/career-log/examples/resume.tex",
        "skills/career-log/assets/resume-blank.tex",
    ], [
        py("tools/tests/test_resume.py", "the last line is `OK (skipped=1)`, the one skipped being the lipsum "
           "install; more skipped means TinyTeX or poppler is not found and the build cases did not run: run it "
           "again on a machine with both (SETUP.md step 5), on every platform you use"),
    ]),
    ("skill lint", "skill-lint.yml", [
        "skills/", "tools/template/", "SETUP.md", "AGENTS.md", "CLAUDE.md", "GLOSSARY.md",
        "entries/_template.md", "docs/adr/", "docs/guide.md", "tools/guide.py", "tools/config.py",
        "tools/config.default.toml", "tools/logfiles.py", "tools/skill_lint.py", "tools/tests/test_guide.py",
        "tools/tests/test_skill_lint.py",
    ], [
        py("tools/tests/test_guide.py"),
        py("tools/tests/test_skill_lint.py"),
        py("tools/skill_lint.py", "it prints `skill lint: ok`; when it names a stale block of "
           "`docs/guide.md`, run `{python} -I tools/guide.py write`, commit, and run it again"),
    ]),
    ("scan", "scan-tests.yml", [
        "tools/scan.py", "tools/fit.py", "tools/entries.py", "tools/logfiles.py", "tools/dashboard.py",
        "tools/sponsorship.py", "tools/config.py", "tools/tests/test_scan.py", "tools/tests/test_fit.py",
    ], [
        py("tools/tests/test_scan.py"),
        py("tools/tests/test_fit.py"),
    ]),
    ("dashboard", "dashboard-tests.yml", [
        "tools/dashboard.py", "tools/scan.py", "tools/fit.py", "tools/entries.py", "tools/logfiles.py",
        "tools/sponsorship.py", "tools/config.py", "tools/tests/test_dashboard.py",
    ], [
        py("tools/tests/test_dashboard.py"),
    ]),
    ("sponsorship", "sponsorship-tests.yml", [
        "tools/sponsorship.py", "tools/config.py", "tools/logfiles.py", "tools/tests/test_sponsorship.py",
    ], [
        py("tools/tests/test_sponsorship.py"),
    ]),
    ("perplexity", "perplexity-tests.yml", [
        "tools/perplexity-list.js", "tools/perplexity-job.js", "tools/perplexity-extras.js", "tools/chat_export.py",
        "tools/logfiles.py",
        "tools/tests/test_perplexity.py", "tools/tests/perplexity_fake.js", "tools/tests/perplexity_harness.js",
    ], [
        py("tools/tests/test_perplexity.py", "the last line is `OK`; `OK (skipped=…)` means `node` is not on `PATH` "
           "and the scripts did not run: put Node on `PATH` and run it again"),
    ]),
    ("upgrade", "upgrade-tests.yml", [
        "tools/upgrade.py", "tools/tests/test_upgrade.py", "tools/export-template.sh", "docs/upgrades/",
        "tools/config.py", "tools/logfiles.py", "tools/sponsorship.py",
    ], [
        py("tools/tests/test_upgrade.py"),
    ]),
    ("readiness", "readiness-tests.yml", [
        "maintainer/readiness.py", "maintainer/coord.py", "maintainer/coordlib.py",
        "maintainer/tests/test_readiness.py", "maintainer/tests/test_coord.py", "tools/export-template.sh",
        ".github/workflows/closing_refs.py", "tools/deny_coverage.py",
    ], [
        py("maintainer/tests/test_readiness.py"),
        py("maintainer/tests/test_coord.py"),
    ]),
    ("harness", "harness-tests.yml", [
        "maintainer/harness.py", "maintainer/tests/test_harness.py", "tools/logfiles.py", "tools/config.py",
        "tools/config.default.toml",
    ], [
        py("maintainer/tests/test_harness.py"),
    ]),
    ("writing lint", "writing-lint-tests.yml", [
        "tools/writing_lint.py", "tools/entries.py", "tools/logfiles.py", "skills/career-log/writing.md",
        "tools/tests/test_writing_lint.py",
    ], [
        py("tools/tests/test_writing_lint.py"),
    ]),
    ("application", "application-tests.yml", [
        "tools/application.py", "tools/entries.py", "tools/logfiles.py", "tools/check_save.py",
        "tools/writing_lint.py", "tools/resume.py", "tools/tests/test_application.py",
    ], [
        py("tools/tests/test_application.py"),
    ]),
    ("sync", "sync-tests.yml", [
        "tools/sync.py", "tools/logfiles.py", "tools/tests/test_sync.py",
    ], [
        py("tools/tests/test_sync.py"),
    ]),
    ("checks_for", "checks-for-tests.yml", [
        "tools/checks_for.py", "tools/tests/test_checks_for.py", EXPORT, ".github/workflows/",
    ], [
        py("tools/tests/test_checks_for.py"),
    ]),
]


class ChecksError(Exception):
    pass


def allow(root):
    """The export's ALLOW list, from tools/export-template.sh."""
    try:
        with open(os.path.join(root, EXPORT), encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise ChecksError("cannot read %s: %s" % (EXPORT, e))
    m = re.search(r'^ALLOW="([^"]*)"', text, re.M)
    if not m:
        raise ChecksError("no ALLOW=\"...\" line in %s" % EXPORT)
    return m.group(1).split()


def export_triggers(root):
    """ALLOW as triggers (a folder ends in /), then the .export-* files."""
    return [p + "/" if os.path.isdir(os.path.join(root, p)) else p for p in allow(root)] + list(EXPORT_FILES)


def triggers(group, root):
    """A group's triggers, its own workflow file included, as that workflow's paths: has it."""
    own = [".github/workflows/" + group[1]] if group[1] else []
    return (export_triggers(root) if group[2] is None else group[2]) + own


def matches(path, trigger):
    return path.startswith(trigger) if trigger.endswith("/") else path == trigger


def kind(path, root):
    if path.startswith(COORDINATION):
        return "coordination"
    if path in GUARDS:
        return "guard"
    engine = export_triggers(root)
    if os.path.isdir(os.path.join(root, "maintainer")):   # the Template's source
        engine += list(SOURCE_ENGINE)
    return "engine" if any(matches(path, t) for t in engine) else "not engine"


def present(check, root):
    """A check whose script is not in this repo (maintainer/ in a Template) is left out."""
    return check[0] != "py" or os.path.isfile(os.path.join(root, check[1]))


def checks(paths, root):
    """The checks for the changed paths, each once, in GROUPS order."""
    out = []
    for group in GROUPS:
        if any(matches(p, t) for p in paths for t in triggers(group, root)):
            out += [c for c in group[3] if present(c, root) and c not in out]
    return out


def render(check):
    k, text, verdict = check
    python = logfiles.python_cmd()
    if k == "do":
        return ["do: " + text]
    cmd = "%s -I %s" % (python, text) if k == "py" else text
    return ["run: " + cmd, "check: " + verdict.format(python=python)]


def report(paths, root):
    lines = ["%s: %s" % (kind(p, root), p) for p in paths]
    changed = [f for f in FRONT_PAGES if f in paths]
    if len(changed) == 1:
        other = FRONT_PAGES[1 - FRONT_PAGES.index(changed[0])]
        lines.append("warn: %s changed but %s did not: make the same change there, in the same commit "
                     "(Entries-table rows live only in README.md)" % (changed[0], other))
    found = checks(paths, root)
    for c in found:
        lines += render(c)
    if not found:
        lines.append("run: none (no check covers these paths)")
    return lines


def git(root, *args):
    p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        raise ChecksError("git %s: %s" % (" ".join(args), (p.stderr or p.stdout).strip()))
    return p.stdout


def changed(root, base):
    """Paths changed since base: committed (base...HEAD), staged, unstaged and untracked."""
    paths = set(git(root, "diff", "--name-only", "--no-renames", "-z", base + "...HEAD").split("\0"))
    for entry in git(root, "status", "--porcelain", "--no-renames", "-uall", "-z").split("\0"):
        if len(entry) > 3:
            paths.add(entry[3:])
    paths.discard("")
    return sorted(paths)


def relative(path, root):
    """A path as the map has it: repo-relative, with forward slashes."""
    path = path.replace("\\", "/")
    if os.path.isabs(path):
        try:
            rel = os.path.relpath(path, root).replace("\\", "/")
        except ValueError:   # another drive
            rel = ".."
        if rel == ".." or rel.startswith("../"):
            raise ChecksError("%s is outside %s" % (path, root))
        return rel
    return re.sub(r"^(\./)+", "", path)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):   # a path may hold any character; a Windows pipe is not UTF-8
        stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", nargs="?", help="the commit the change started from")
    ap.add_argument("--paths", nargs="+", metavar="PATH", help="repo-relative paths instead of a base")
    ap.add_argument("--root", default=ROOT)
    args = ap.parse_args(argv)
    if (args.base is None) == (args.paths is None):
        ap.print_usage(sys.stderr)
        print("checks_for.py: give either <base> or --paths", file=sys.stderr)
        return 2
    try:
        paths = sorted(set(relative(p, args.root) for p in args.paths)) if args.paths else changed(args.root, args.base)
        lines = report(paths, args.root)
    except ChecksError as e:
        print("checks_for.py: %s" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
