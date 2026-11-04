#!/usr/bin/env python3
"""Which checks to run after an Engine change, from the paths it changed.

  python3 -I tools/checks_for.py <base>              (Windows: py -3 -I tools/checks_for.py ...)
  python3 -I tools/checks_for.py --paths <path>...
  python3 -I tools/checks_for.py --run <base>        (or --run --paths <path>...)

<base> is the commit the change started from (origin/<default> for a branch): the changed paths
are those `git diff <base>...HEAD` names, plus uncommitted and untracked ones. --paths takes
repo-relative paths instead. Both take --root <root>, the repo's root (default: the repo this
script is in).

It prints, in this order:
- one line per changed path: `engine: <path>` (an Engine path: the export's ALLOW list in
  tools/export-template.sh, its .export-* files, and, in the Template's source (a root with
  `maintainer/`), `.github/`, `maintainer/` and the maintainer docs; skills/career-log/engine-changes.md says how it lands), `guard: <path>`
  (.export-deny, .export-cleared) or `not engine: <path>`;
- `warn:` when only one of the Template's two front pages changed;
- the checks: each `run: <command>` line followed by a `check: <what passing looks like>` line,
  and each `do: <step>` line (one that needs a person or a platform: no single command), each
  command once, or `run: none` when no check covers the paths. `<scratch>` is a new folder in
  your scratchpad. The PowerShell parse of tools/setup.ps1 is a `run:` line for PowerShell.

With --run it prints the same path and warn: lines, then runs the `run:` checks of Python and sh
side by side (--jobs <n> at a time, default one per CPU; each with the command it prints, sh being
the one on PATH or else Git for Windows' own, `<scratch>` a temporary folder it removes), from the
repo's root. For each, in the order above: `ok:` or `FAIL:`, its seconds, its command and its last
line, an sh check's `note:` lines, its `check:` line when that asks for more than `OK`, and a
failure's last 40 lines. Then a `ran <n> checks` line with the wall time, and the PowerShell `run:`
and the `do:` lines, for you to run. When a check it ran failed, run that one alone before you fix
anything, since checks side by side may clash (a file lock on Windows).

The map is GROUPS below: each group's triggers (an exact path, or a folder ending in `/` for
everything under it) and the checks it runs. A group with a workflow is what that workflow in
this repo's .github/workflows/ runs, on the same `paths:`, the workflow's own file included; groups
that share a workflow are run together by it, on all their `paths:`. tools/tests/test_checks_for.py
fails when a workflow and its groups disagree. A new tool or test: add its group here, and in the
Template's source a workflow for it with the same `paths:` plus its own file, or name a workflow
whose `paths:` it mostly shares and add its paths and steps there. A check whose script is missing (maintainer/
in a Template) is left out, and so is a do: step that names a missing file (docs/upgrades/test-next.sh
until a Log format change writes it).

Exit 0 on success (with --run, when every check it ran exited 0), 1 when one of them failed, 2 on a
bad argument or a git error. Standard library only, Python 3.11+.
"""
import argparse, locale, os, re, shlex, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:   # -I leaves this folder off sys.path
    sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles
EXPORT = "tools/export-template.sh"
EXPORT_FILES = (".export-deny", ".export-allow", ".export-cleared")
GUARDS = (".export-deny", ".export-cleared")
# Engine only here, in the Template's source (AGENTS.md › Changes); the export leaves them out
SOURCE_ENGINE = (".export-allow", ".github/", "maintainer/", "docs/maintaining.md",
                 "docs/maintaining-tests.md", "docs/migrating.md", "docs/publishing.md",
                 ".claude/settings.json", "docs/agents/")
NEXT_TEST = "docs/upgrades/test-next.sh"   # a Log format change's scratch Log (docs/maintaining.md)
FRONT_PAGES = ("tools/template/README.md", "tools/template/README.zh-TW.md")
OK = "the last line is `OK`"


def py(script, check=OK):
    return ("py", script, check)


def sh(cmd, check):
    return ("sh", cmd, check)


def do(text, needs=None):
    """A step for a person; with needs, only when that file is in the repo."""
    return ("do", text, needs)


# (name, workflow or None, triggers, checks). The export group's triggers are read from
# tools/export-template.sh (export_triggers).
GROUPS = [
    ("export", "template-scan.yml", None, [
        sh("sh tools/export-template.sh <scratch>/export",
           "the last line is `OK`, with no `note: uncommitted` line (it exports commits only: commit first)"),
    ]),
    ("chat export", "parser-tests.yml", [
        "tools/chat_export.py", "tools/tests/test_chat_export.py", "tools/tests/make_fixtures.py",
        "tools/tests/fixtures/", "tools/tests/expected/", "tools/logfiles.py",
    ], [
        py("tools/tests/test_chat_export.py"),
    ]),
    ("check run/save", "parser-tests.yml", [
        "tools/check_run.py", "tools/tests/test_check_run.py", "tools/check_save.py", "tools/tests/test_check_save.py",
        "tools/chat_export.py", "tools/entries.py", "tools/logfiles.py", "tools/writing_lint.py", "tools/resume.py",
        "tools/config.py", "tools/config.default.toml", "tools/fit.py", "tools/sponsorship.py", "tools/dashboard.py",
        "skills/career-log/writing.md", "skills/career-log/modes/review.md", "skills/career-log/modes/scan.md",
    ], [
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
    ("config", "machine-check.yml", [
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
    ]),
    ("setup scripts", "machine-check.yml", [
        "tools/setup.sh", "tools/setup.ps1",
    ], [
        sh("sh -n tools/setup.sh", "it prints nothing and exits 0"),
        ("ps", "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
               "(Resolve-Path tools/setup.ps1).Path, [ref]$null, [ref]$e); $e",
         "run in PowerShell 7 and in Windows PowerShell 5.1, where you have them, it prints nothing"),
    ]),
    ("setup by hand", None, [   # not on a change to machine-check.yml alone
        "tools/setup.sh", "tools/setup.ps1",
    ], [
        do("run SETUP.md step 5 with the tools the change touches, on each platform you can; "
           "step 5's check holds"),
    ]),
    ("resume", "parser-tests.yml", [
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
    ("dashboard", "scan-tests.yml", [
        "tools/dashboard.py", "tools/scan.py", "tools/fit.py", "tools/entries.py", "tools/logfiles.py",
        "tools/sponsorship.py", "tools/config.py", "tools/tests/test_dashboard.py",
    ], [
        py("tools/tests/test_dashboard.py"),
    ]),
    ("sponsorship", "scan-tests.yml", [
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
    ("upgrade next", None, [
        "docs/upgrades/upgrade-next.md", "docs/upgrades/upgrade-next.py", NEXT_TEST,
    ], [
        do("run %s, then upgrade the scratch Log it builds with docs/upgrades/upgrade-next.md through the "
           "upgrade mode; its header says how (docs/maintaining.md › Log format changes)" % NEXT_TEST, NEXT_TEST),
    ]),
    ("coord", "coord-tests.yml", [
        "maintainer/coord.py", "maintainer/tests/test_coord.py", "tools/export-template.sh", "tools/deny_coverage.py",
    ], [
        py("maintainer/tests/test_coord.py"),
    ]),
    ("closing refs", "coord-tests.yml", [
        ".github/workflows/closing_refs.py", "maintainer/tests/test_closing_refs.py",
    ], [
        py("maintainer/tests/test_closing_refs.py"),
    ]),
    ("harness", "harness-tests.yml", [
        "maintainer/harness.py", "maintainer/tests/test_harness.py", "tools/logfiles.py", "tools/config.py",
        "tools/config.default.toml",
    ], [
        py("maintainer/tests/test_harness.py"),
    ]),
    ("writing lint", "application-tests.yml", [
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
    if path in GUARDS:
        return "guard"
    engine = export_triggers(root)
    if os.path.isdir(os.path.join(root, "maintainer")):   # the Template's source
        engine += list(SOURCE_ENGINE)
    return "engine" if any(matches(path, t) for t in engine) else "not engine"


def present(check, root):
    """A check whose script is not in this repo (maintainer/ in a Template), or a do: step whose
    file is not (test-next.sh before a Log format change), is left out."""
    need = check[1] if check[0] == "py" else check[2] if check[0] == "do" else None
    return need is None or os.path.isfile(os.path.join(root, need))


def checks(paths, root):
    """The checks for the changed paths, each once, in GROUPS order."""
    out = []
    for group in GROUPS:
        if any(matches(p, t) for p in paths for t in triggers(group, root)):
            out += [c for c in group[3] if present(c, root) and c not in out]
    return out


def command(check):
    """A run: check's command, as printed and as --run runs it."""
    return "%s -I %s" % (logfiles.python_cmd(), check[1]) if check[0] == "py" else check[1]


def verdict(check):
    return check[2].format(python=logfiles.python_cmd())


def render(check):
    if check[0] == "do":
        return ["do: " + check[1]]
    return ["run: " + command(check), "check: " + verdict(check)]


def head(paths, root):
    """The engine:, guard:, not engine: and warn: lines."""
    lines = ["%s: %s" % (kind(p, root), p) for p in paths]
    changed = [f for f in FRONT_PAGES if f in paths]
    if len(changed) == 1:
        other = FRONT_PAGES[1 - FRONT_PAGES.index(changed[0])]
        lines.append("warn: %s changed but %s did not: make the same change there, in the same commit "
                     "(Entries-table rows live only in README.md)" % (changed[0], other))
    return lines


def report(paths, root):
    lines = head(paths, root)
    found = checks(paths, root)
    for c in found:
        lines += render(c)
    if not found:
        lines.append("run: none (no check covers these paths)")
    return lines


def find_sh():
    """[sh] and the env to run it with: the sh on PATH, else Git for Windows' own, with its folder (the
    grep and sed tools/export-template.sh calls) first on PATH; None when there is neither."""
    found = shutil.which("sh")
    if found:
        return found, None
    if os.name == "nt":
        try:
            p = subprocess.run(["git", "--exec-path"], capture_output=True, text=True)   # <Git>/mingw64/libexec/git-core
        except OSError:
            return None, None
        exe = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(p.stdout.strip()))), "usr", "bin", "sh.exe")
        if p.returncode == 0 and os.path.isfile(exe):
            return exe, dict(os.environ, PATH=os.path.dirname(exe) + os.pathsep + os.environ.get("PATH", ""))
    return None, None


def run_one(check, root, scratch, sh):
    """(ok, seconds, output) for a py or sh check, run from root; sh is find_sh()."""
    argv = [a.replace("<scratch>", scratch) for a in shlex.split(command(check))]
    env = None
    if check[0] == "sh":   # each sh check's command starts with `sh`
        if sh[0] is None:
            return False, 0.0, "no sh found (on Windows it comes with Git for Windows)"
        argv[0], env = sh
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL)
    except OSError as e:
        return False, time.monotonic() - start, "%s: %s" % (argv[0], e)
    try:
        out = p.stdout.decode("utf-8")
    except UnicodeDecodeError:   # a Windows child writes a pipe in the ANSI code page
        out = p.stdout.decode(locale.getpreferredencoding(False), "replace")
    return p.returncode == 0, time.monotonic() - start, out


def run(paths, root, jobs):
    """Print head(), run the py and sh checks side by side, print each one's result, then the
    render() of the ps and do: checks; 1 when a check failed, else 0."""
    print("\n".join(head(paths, root)), flush=True)
    found = checks(paths, root)
    mine = [c for c in found if c[0] in ("py", "sh")]
    if not found:
        print("run: none (no check covers these paths)")
        return 0
    scratch = tempfile.mkdtemp(prefix="checks_for-").replace("\\", "/")
    start, failed = time.monotonic(), 0
    sh = find_sh() if any(c[0] == "sh" for c in mine) else (None, None)
    try:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [(c, pool.submit(run_one, c, root, scratch, sh)) for c in mine]
            for c, f in futures:   # in GROUPS order; each line once its check is done
                ok, secs, out = f.result()
                lines = out.rstrip().splitlines() or ["(no output)"]
                print("%s %4.0fs %s: %s" % ("ok:  " if ok else "FAIL:", secs, command(c), lines[-1].strip()))
                if ok and c[0] == "sh":   # the export's `note: uncommitted` line, say
                    for l in lines[:-1]:
                        if l.startswith("note:"):
                            print("      " + l)
                if c[2] != OK:
                    print("      check: " + verdict(c))
                if not ok:
                    failed += 1
                    print("\n".join("      | " + l for l in lines[-40:]))
                sys.stdout.flush()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if mine:
        print("ran %d checks side by side in %.0fs: %s" % (len(mine), time.monotonic() - start,
              "%d failed (rerun each alone to tell a real failure from a clash)" % failed if failed else "all exited 0"))
    for c in found:
        if c not in mine:
            print("\n".join(render(c)))
    return 1 if failed else 0


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
    ap.add_argument("--run", action="store_true", help="run the py and sh checks side by side")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="checks at a time with --run (default: CPUs)")
    args = ap.parse_args(argv)
    if (args.base is None) == (args.paths is None):
        ap.print_usage(sys.stderr)
        print("checks_for.py: give either <base> or --paths", file=sys.stderr)
        return 2
    try:
        paths = sorted(set(relative(p, args.root) for p in args.paths)) if args.paths else changed(args.root, args.base)
        if args.run:
            return run(paths, args.root, max(1, args.jobs))
        lines = report(paths, args.root)
    except ChecksError as e:
        print("checks_for.py: %s" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
