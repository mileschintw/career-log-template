#!/usr/bin/env python3
"""The check every career-log trigger runs first (SKILL.md › Trigger check).

  python3 -I tools/check.py <mode> [--root <root>]     (Windows: py -3 -I tools/check.py <mode>)

<mode> is a mode from SKILL.md's modes table (`setup` checks every optional tool), or `browser`:
playwright-cli's lines alone, with `now` steps, for browser.md before a first open. <root> is the
Log's root, by default the folder above this script's real path, a skill link resolved (the skill's
start.py runs this script from there). The first line is `root: <root>`, the path every `<root>` in
the skill stands for. Then one `<what>: <state>` line per thing checked, then `next:` lines, the agent's steps in order: a
`next: when <moment>, first: <step>` line waits for that moment (`now`: before anything else), and
`next: stop: ...` ends the mode. The last line is `next: go on with the mode` when nothing stops it now
and no `next: now` step asks to run this check again (in setup: a tool missing, or a question about
it): that line waits for the rerun.

Checks run in the order of CHECKS. Each takes the Context and returns (lines, nexts, stop);
`stop` ends the run after its lines are printed, for a state no later check can help with.
A later check is one more function appended to CHECKS.

Machine setup: TinyTeX (with poppler) is required, so setup installs it with no question.
~/.career-log/machine.toml holds the user's yes or no per optional tool (playwright-cli) on this
machine, one `<tool> = true|false` line each, written by tools/setup.sh and tools/setup.ps1; a
leftover `tinytex` line from before TinyTeX was required is ignored. Whether a tool is installed is
detected here on every run, never stored. Setup also records there where poppler came from
(`poppler = "micromamba"` or `"own"`); the check tells that from the path of the pdftotext
tools/resume.py picks, so the path wins when the two disagree.

Missing machine pieces read as one clause ("the links in <dir> are broken and playwright-cli is
missing"). playwright-cli's lines end with `playwright-cli files:`, whether git ignores what it writes
in this checkout (PLAYWRIGHT_FILES), asking the user when it does not.

Mode state (check_mode_state), lines the mode files read in place of their own checks: in every
mode, `direction <item>: set|empty|unreadable (<why>)` per Direction item (tools/config.py show
says what it holds); in setup, `front page: template|trimmed|edited|missing` (config.py's
front_page_state), `eol: ok|wrong (...)` (SETUP.md step 2's check) and one `skill link <agent>:
ok|missing|broken|elsewhere` line per row of SETUP.md step 4; in import, `gitignore inbox: ok|missing`, with
a `next: now` step that adds and commits the lines; in scan, `scan window:`, window and
scheduled_window in days; in interview, the `next:` step for a profile shown only to signed-in
members, from interviewer_profiles.

Unattended: with CAREER_LOG_UNATTENDED set (a scheduled run), a step that would install something or
ask the user says setup is needed instead, since no one is there to answer a question.

Uncommitted Log changes: the Log's own files (LOG_PATHS) that git shows as changed or new are
listed, so a session settles what an earlier one left before it writes anything; the `next:` line
points at tools/sync.py's `status` and `settle`.

This Log's git state, read only (tools/sync.py makes every change): `identity: ok (<email>)` or
`identity: missing`, the repo-local user.email every commit needs (SETUP.md step 3); a missing one
holds up only a step that commits. `default branch: <name>` from origin/HEAD, or `unknown` while
that is unset, with the command that sets it. On the default branch, `ahead: <n>`, the commits on
HEAD not on origin/<default> as of the last fetch (nothing is fetched), with no step of its own:
a sync.py commit that pushes takes them along, and in a mode that commits nothing, Next up names
`sync.py push`; on any other branch, `branch: <name> (not
<default>)` in its place. With no origin remote: `default branch: none (no origin remote)`, and no
ahead or pull line. A root that is not the top folder of a git repository prints `git: not a
repository` in place of these lines.

Pull: a run with no `next: stop:`, on a branch with an upstream, ends its steps with a `next: now`
line to run tools/sync.py pull (another clone may have pushed); this script itself never pulls.

Setup for this Log: config.toml at the Log root (tools/config.py) says setup has run. Without it every
mode but setup stops and points to setup; with it, one `config <field>: <value>` line per Config field.

Entry size: an `entry over threshold: <path> <n> tokens` line for each entry tools/entries.py
estimates past its threshold (half of what one Read call returns), in every mode. It has no
next: line: the modes say what to do with an entry that size.

Newer Template release: an `update: v<x> available (you have v<y>): ...` line, saying what to do with
it, when the public Template has a release newer than tools/TEMPLATE_VERSION's version, and
nothing otherwise. It asks GitHub's Releases API, for the Template tools/upgrade.py fetches
(CAREER_LOG_RELEASES_URL overrides the address), at most once a day, for 2 seconds at most,
sending nothing from the Log, and keeps the answer in ~/.career-log/release.json; offline,
rate-limited or slow, it says nothing. It never asks with `update_check = "off"` in
config.toml, in an unattended run, or without a released version in TEMPLATE_VERSION (the
Template's source, an export's `next`). It only tells: the upgrade mode upgrades.

Session hygiene (SKILL.md › Next up): every mode but log also prints a `mode start: <sha>@<time>`
line (HEAD and the time, for `done --since`; the mode keeps its first check's, as the line says) and a `next: now, first:` line telling the agent to
suggest a fresh session when this session already ran another mode. The modes that do not count
come from the flows table of docs/guide.md (tools/guide.py flows): a step whose session is `same`.

  python3 -I tools/check.py done <mode> [--since <sha>@<time>] [--for <mode>] [--no-posting]

(--root as above) prints the Next up block that ends <mode>: the commits made since `mode start` (pulled ones, older,
left out), the next step from the flows table for this Log's state (consolidate again while an
entry is `stub` or `imported`, import again while the Log has no entries, and import in place
of a step that reads entries while the Log has none; a step whose work is
done is skipped: import once there are entries, consolidate once no entry is `stub` or
`imported`, stories once stories/ holds a Talking points file), the fresh-session line, and the modes in no flow under "Also available". `--for <mode>`: setup ran because the Trigger check of <mode>
started it, so the block sends the user back to <mode> in this session. `--no-posting` (fit only):
the run answered a question with no posting ("does <company> sponsor?"), so no next step follows
from a posting's fit, and the block names none. With Log changes
uncommitted or commits not pushed, it says so in place of the fresh-session line and exits 1; for
commits not pushed, its `next:` line names `sync.py push`. It prints nothing for log, nor in an
unattended run.

Exit 1 when the check ends the run (a `next: stop:` line, or this Python is too old), 2 on a bad
argument, 0 otherwise. -h or --help prints this text and exits 0. Standard library only.
Python 3.11+ (tomllib); an older Python gets as far as saying so, and where a newer one is.
"""
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))   # through a skill link too
ROOT = os.path.dirname(HERE)
WINDOWS = os.name == "nt"
LINUX = platform.system() == "Linux"
MIN_PYTHON = (3, 11)
MIN_NODE = 18
MODES = ["log", "consolidate", "interview", "stories", "fit", "write", "rank", "scan", "import", "audit", "setup"]
UNATTENDED = bool(os.environ.get("CAREER_LOG_UNATTENDED"))

# The tools of Machine setup: TOOLS are optional (machine.toml), the rest of NEEDS's are required.
# `hard`: the step that needs it cannot run without it. `soft`: that step has a fallback
# (browser.md › Fallback order). Either way only the step that needs the tool waits on it (WHEN),
# never the whole mode.
TOOLS = ["playwright-cli"]
NEEDS = {
    "fit": [("playwright-cli", "soft")],
    "write": [("tinytex", "hard"), ("playwright-cli", "soft")],
    "rank": [("playwright-cli", "soft")],
    "scan": [("tinytex", "soft"), ("playwright-cli", "soft")],
    "interview": [("playwright-cli", "soft")],
    "import": [("playwright-cli", "soft")],
    "setup": [("playwright-cli", "soft"), ("tinytex", "soft")],
    "browser": [("playwright-cli", "soft")],   # not a mode: browser.md's own check, before a first open
}
WHAT = {
    "playwright-cli": "Node 18+ (unless one is already installed), Microsoft's playwright-cli"
                      " in npm's global folder, and its skill in this checkout, ignored by git"
                      + (" (about 150 MB in all; Edge stands in for Chrome, so with Edge installed no Chromium is downloaded)"
                         if WINDOWS else
                         ", and, when Chrome and Edge are both missing, Chromium in Playwright's cache in your"
                         " home folder (about 400 MB in all; about 150 MB with Chrome or Edge installed (on"
                         " macOS, in /Applications))"),
}
NAME = {"playwright-cli": "playwright-cli"}
PURPOSE = {"playwright-cli": "reads web pages that show their content only after their scripts run"
                             " or you sign in"}
FEATURE = {"playwright-cli": "Browser capture"}
WHEN = {"playwright-cli": "when a page needs a Browser capture (item 2 of browser.md, Fallback order)",
        "tinytex": "when a step builds a PDF"}
# How to run setup when it installs something: TinyTeX outlasts a shell tool's usual time limit.
RUN_SETUP = "as a background command, and wait for it to end (it can take 5-20 minutes)"


class Context:
    def __init__(self, mode, root=ROOT, home=None):
        self.mode = mode
        self.root = root
        self.home = home or os.path.expanduser("~")
        self.machine_toml = os.path.join(self.home, ".career-log", "machine.toml")


def setup_cmd(root, yes=(), no=()):
    """The setup command, its path in single quotes: PowerShell, bash and zsh all read them."""
    if WINDOWS:
        path = os.path.join(root, "tools", "setup.ps1").replace("'", "''")
        cmd = "powershell -ExecutionPolicy Bypass -File '%s'" % path
        return cmd + (" -Yes " + ",".join(yes) if yes else "") + (" -No " + ",".join(no) if no else "")
    cmd = "sh '%s/tools/setup.sh'" % root.replace("'", "'\\''")
    return cmd + (" --yes " + ",".join(yes) if yes else "") + (" --no " + ",".join(no) if no else "")


def run(cmd, timeout=30):
    """(exit code, stdout+stderr) of a command, or (None, why) when it cannot start."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    return p.returncode, p.stdout + p.stderr


# ---- Python ----

def newer_pythons(home):
    """Python 3.11+ interpreters off this one's PATH, where setup puts them."""
    if WINDOWS:
        pattern = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python3*", "python.exe")
        minor = lambda path: re.fullmatch(r"python3(\d+)", os.path.basename(os.path.dirname(path)).lower())
    else:
        pattern = os.path.join(home, ".local", "bin", "python3.*")
        minor = lambda path: re.fullmatch(r"python3\.(\d+)", os.path.basename(path))
    found = []
    for path in glob.glob(pattern):
        m = minor(path)
        if m and int(m.group(1)) >= MIN_PYTHON[1] and os.access(path, os.X_OK):
            found.append((int(m.group(1)), path))
    return [path for _, path in sorted(found, reverse=True)]


def check_python(ctx):
    v = sys.version_info
    version = "%d.%d.%d" % (v[0], v[1], v[2])
    if v[:2] >= MIN_PYTHON:
        return ["python: ok (%s)" % version], [], False
    lines = ["python: too old (%s at %s; career-log needs 3.11+)" % (version, sys.executable)]
    newer = newer_pythons(ctx.home)
    if newer:
        nexts = ["next: run this check again with %s in place of %s, and use that command for every"
                 " %s in this skill" % (newer[0], python_cmd(), python_cmd())]
    elif UNATTENDED:
        nexts = ["next: stop: setup is needed on this machine: career-log needs Python 3.11+, and this"
                 " is %s. This run is unattended (CAREER_LOG_UNATTENDED), so it installs nothing: say so"
                 " in the run's result." % version]
    else:
        nexts = ["next: stop: setup is not done on this machine: career-log needs Python 3.11+, and"
                 " this is %s. Ask the user whether to run this machine's setup now: Python 3.13, and TinyTeX"
                 " with poppler, for their user only (about 180 MB to download; about 250 MB when no poppler is installed): `%s`. On yes run it %s;"
                 " then run this check again with the command its output names."
                 % (version, setup_cmd(ctx.root), RUN_SETUP)]
    return lines, nexts, True


# ---- machine.toml ----

def read_choices(ctx):
    """{tool: True|False} from machine.toml; (None, error) when it does not parse."""
    if not os.path.exists(ctx.machine_toml):
        return {}, None
    import tomllib
    try:
        with open(ctx.machine_toml, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        return None, str(e)
    return {k: v for k, v in data.items() if k in TOOLS and isinstance(v, bool)}, None


# ---- Tool detection ----

def which(name, extra_dirs):
    """(path, on_path) for the first `name` on PATH, else in extra_dirs (on_path False)."""
    found = shutil.which(name)
    if found:
        return found, True
    exts = [".exe", ".cmd", ".bat", ""] if WINDOWS else [""]
    for d in extra_dirs:
        for ext in exts:
            p = os.path.join(d, name + ext)
            if os.path.isfile(p):
                return p, False
    return None, False


def node_dirs(home):
    if WINDOWS:
        local = os.environ.get("LOCALAPPDATA", "")
        return (sorted(glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "OpenJS.NodeJS*", "node-*")), reverse=True)
                + [os.path.join(local, "Microsoft", "WinGet", "Links"),
                   os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "nodejs")])
    # setup's links to nvm's Node first, then nvm's versions, newest first
    nvm = glob.glob(os.path.join(home, ".nvm", "versions", "node", "*", "bin"))
    key = lambda d: [int(n) for n in re.findall(r"\d+", os.path.basename(os.path.dirname(d)))]
    return [local_bin(home)] + sorted(nvm, key=key, reverse=True)


def local_bin(home):
    return os.path.join(home, ".local", "bin")


def broken_links(home):
    """setup's links in ~/.local/bin whose nvm version was uninstalled (macOS, Linux)."""
    paths = [os.path.join(local_bin(home), b) for b in ("node", "npm", "playwright-cli")]
    return [] if WINDOWS else [p for p in paths if os.path.islink(p) and not os.path.exists(p)
                               and "/.nvm/" in os.readlink(p)]


def npm_bin_dirs(home):
    """Where `npm install -g` puts commands: %APPDATA%\\npm for an installed Node (its copy in a
    packaged app's store first, as resume.APPDATA_STORE says), the Node folder itself for winget's
    per-user zip, and nvm's bin folder elsewhere."""
    if WINDOWS:
        store = glob.glob(os.path.expandvars(resume_module().APPDATA_STORE + "npm"))
        return [os.path.normpath(d) for d in sorted(store)] + [os.path.join(os.environ.get("APPDATA", ""), "npm")] + node_dirs(home)
    return node_dirs(home)


def path_reload(dirs):
    dirs = list(dict.fromkeys(dirs))
    if WINDOWS:
        return ("$env:Path = '%s;' + [Environment]::GetEnvironmentVariable('Path','Machine') + ';'"
                " + [Environment]::GetEnvironmentVariable('Path','User')" % ";".join(dirs))
    return 'export PATH="%s:$PATH"' % ":".join(dirs)


def chrome_installed():
    if WINDOWS:
        roots = [os.environ.get(k, "") for k in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)")]
        return any(os.path.isfile(os.path.join(r, "Google", "Chrome", "Application", "chrome.exe")) for r in roots if r)
    if platform.system() == "Darwin":   # playwright-core's chrome channel looks here only, not in ~/Applications
        return os.path.exists("/Applications/Google Chrome.app")
    return os.path.isfile("/opt/google/chrome/chrome")


# Where playwright-core's msedge channel finds Edge off Windows (on macOS, /Applications only)
EDGE_PATHS = {"Darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
              "Linux": ["/opt/microsoft/msedge/msedge"]}


def edge_installed():
    """Edge where playwright-core looks for it: playwright-cli picks it when Chrome is missing."""
    if not WINDOWS:
        return any(os.path.isfile(p) for p in EDGE_PATHS.get(platform.system(), []))
    roots = [os.environ.get(k, "") for k in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)")]
    return any(os.path.isfile(os.path.join(r, "Microsoft", "Edge", "Application", "msedge.exe")) for r in roots if r)


def playwright_cache(home):
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return os.environ["PLAYWRIGHT_BROWSERS_PATH"]
    if WINDOWS:
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if platform.system() == "Darwin":
        return os.path.join(home, "Library", "Caches", "ms-playwright")
    return os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache"), "ms-playwright")


def pinned_chromium(cli):
    """[Chromium's folder names, the headless shell's]: the folders in Playwright's cache this
    playwright-cli may launch Chromium from, named as playwright-core's registry names them from the
    browsers.json beside its cli.js: `<name>-<revision>`, or `<name>_<host>_special-<revision>` for a
    revisionOverrides entry. Any host's override counts: this check does not work out playwright-core's
    host name. With no channel, a headless launch takes the headless shell, so both are needed.
    None when there is no playwright-cli or its browsers.json cannot be read."""
    core = playwright_core_cli(cli) if cli else None
    try:
        with open(os.path.join(os.path.dirname(core), "browsers.json"), encoding="utf-8") as f:
            browsers = {b.get("name"): b for b in json.load(f)["browsers"]}
        pinned = []
        for name in ("chromium", "chromium-headless-shell"):
            prefix, entry = name.replace("-", "_"), browsers[name]
            overrides = entry.get("revisionOverrides") or {}
            pinned.append(["%s-%s" % (prefix, entry["revision"])]
                          + ["%s_%s_special-%s" % (prefix, host, rev) for host, rev in overrides.items()])
        return pinned
    except (TypeError, OSError, ValueError, KeyError, AttributeError):
        return None


def chromium_installed(home, pinned):
    """True when Playwright's cache holds a folder of each list in `pinned` (pinned_chromium), False
    when it lacks one, None when nothing is pinned to compare with but the cache holds some Chromium."""
    cache = playwright_cache(home)
    if pinned is None:
        return None if glob.glob(os.path.join(cache, "chromium-*", "INSTALLATION_COMPLETE")) else False
    return all(any(cached(cache, f) for f in names) for names in pinned)


def cached(cache, folder):
    return os.path.isfile(os.path.join(cache, folder, "INSTALLATION_COMPLETE"))


def unpinned(cli):
    """Why a Chromium in the cache cannot be compared with the revision playwright-cli launches."""
    return ("its revision is checked once playwright-cli is installed" if not cli else
            "playwright-cli's playwright-core has no readable browsers.json to give the revision it launches")


def home_chrome(home):
    """macOS's ~/Applications Chrome, which playwright-core does not look for, or None."""
    app = os.path.join(home, "Applications", "Google Chrome.app")
    return app if platform.system() == "Darwin" and os.path.exists(app) else None


def missing_libraries(home, pinned):
    """True when ldd finds a library missing for a downloaded Chromium, as Playwright checks at launch:
    for the `pinned` folders when they are known, else for every revision's."""
    cache = playwright_cache(home)
    folders = [f for names in pinned for f in names] if pinned else ["chromium-*", "chromium_headless_shell-*"]
    for binary in [b for f in folders for b in glob.glob(os.path.join(cache, f, "chrome-linux*", "chrome"))
                   + glob.glob(os.path.join(cache, f, "chrome-*", "chrome-headless-shell"))]:
        code, out = run(["ldd", binary])
        if code is not None and "not found" in out:
            return True
    return False


def cli_configs(ctx):
    """playwright-cli's config files that exist, as (where, path): this checkout's, then the global one."""
    places = [("this checkout", os.path.join(ctx.root, ".playwright", "cli.config.json")),
              ("global", os.path.join(ctx.home, ".playwright", "cli.config.json"))]
    return [(where, path) for where, path in places if os.path.isfile(path)]


def load_cli_config(path):
    """(config, error): a JSON config as a dict ({} when it holds no object), None for one that is not
    JSON (playwright-cli reads it as INI; this check does not), or the error for JSON that does not parse."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return None, str(e)
    def no_constant(name):   # JavaScript's JSON.parse has no NaN or Infinity
        raise ValueError("%s is not JSON" % name)
    try:
        data = json.loads(text, parse_constant=no_constant)
    except ValueError as e:
        return None, (str(e) if text.lstrip().startswith("{") else None)
    if data is None:   # playwright-core fails on a config that is null
        return None, "the file holds null"
    return (data if isinstance(data, dict) else {}), None


def config_browser(configs):
    """The browser playwright-cli launches with these configs (dicts, the global one first), merged
    as playwright-core's resolveCLIConfigForCLI does: each later file's keys over the earlier ones',
    a channel kept only while the merged browserName is chromium, and no browserName meaning Chrome.
    "Chrome", "Edge" or "Chromium", else what the configs set that this check does not look for."""
    name = channel = None
    for config in configs:
        if config is None:
            return "a format other than JSON"
        if config.get("extension"):
            return "extension"
        browser = config.get("browser") if isinstance(config.get("browser"), dict) else {}
        launch = browser.get("launchOptions") if isinstance(browser.get("launchOptions"), dict) else {}
        for key, value in (("cdpEndpoint", browser.get("cdpEndpoint")), ("remoteEndpoint", browser.get("remoteEndpoint")),
                           ("executablePath", launch.get("executablePath"))):
            if value:
                return key
        name = browser["browserName"] if browser.get("browserName") is not None else name
        channel = launch["channel"] if "channel" in launch else channel   # a null channel overrides too
        if name != "chromium" and not str(channel).startswith("moz-"):
            channel = None
    if name is None:
        return "Chrome"
    if name != "chromium":
        return 'browserName "%s"' % name
    return {None: "Chromium", "chromium": "Chromium", "chrome": "Chrome", "msedge": "Edge"}.get(
        channel, 'channel "%s"' % channel)


# playwright-core's environment variables that override the browser the config files name
BROWSER_ENV = ["PLAYWRIGHT_MCP_BROWSER", "PLAYWRIGHT_MCP_EXECUTABLE_PATH", "PLAYWRIGHT_MCP_CDP_ENDPOINT",
               "PLAYWRIGHT_MCP_EXTENSION", "PLAYWRIGHT_MCP_CONFIG"]


def config_names_chromium(configs):
    """True when `configs` (from cli_configs) make `playwright-cli open` launch Playwright's own
    Chromium. False when a config does not load or a BROWSER_ENV override is set, the cases where
    config_state names no browser."""
    if not configs or any(os.environ.get(k) for k in BROWSER_ENV):
        return False
    loaded = [load_cli_config(path) for _, path in configs]
    if any(error for _, error in loaded):
        return False
    return config_browser([config for config, _ in loaded][::-1]) == "Chromium"


def config_state(ctx, configs, chrome, chromium, cli):
    """The config line, and the question to ask when the browser the config names is missing or
    the config does not parse: ("ask", fact, question), or None. `chromium` is chromium_installed's."""
    paths = " and ".join(path for _, path in configs)
    checkout_only = [w for w, _ in configs] == ["this checkout"]
    if len(configs) == 2:
        where = "this checkout, over the global %s" % configs[1][1]
    else:
        where = "this checkout" if checkout_only else "global, %s" % paths
    command = "`playwright-cli install --skills` from %s" % ctx.root
    loaded = []
    for place, path in configs:
        config, error = load_cli_config(path)
        if error:
            if place == "global":
                choice = "; it is global, read in every folder, so it stays theirs to edit."
            else:
                choice = " or to let you delete it%s." % (" (%s then writes a new one)" % command if checkout_only else "")
            return ("playwright-cli config: unreadable (%s: %s)" % (path, error),
                    ("ask", "playwright-cli cannot start with its config %s (%s)." % (path, error),
                     "Show the user the file and the error, and ask them to fix it" + choice))
        loaded.append(config)
    env = next((k for k in BROWSER_ENV if os.environ.get(k)), None)
    if env:
        return ("playwright-cli config: present (%s; %s is set, which this check does not look for)" % (where, env),
                None)
    browser = config_browser(loaded[::-1])
    present = {"Chrome": chrome, "Edge": edge_installed(),
               "Chromium": chromium}.get(browser)
    if browser == "Chromium" and chromium is None:
        return ("playwright-cli config: present (%s; Chromium, in %s; %s)" % (where, playwright_cache(ctx.home), unpinned(cli)),
                None)
    if present is None:
        return ("playwright-cli config: present (%s; it sets %s, which this check does not look for)" % (where, browser),
                None)
    if present:
        return "playwright-cli config: ok (%s; %s)" % (where, browser), None
    options = []
    picks = "Chrome" if chrome else "Edge" if edge_installed() else None
    download = "downloads Chromium into Playwright's cache%s" % (" (about 320 MB)" if WINDOWS else "")
    if checkout_only and (picks or browser != "Chromium"):
        options.append("delete it and run %s, which then %s" % (
            command, "picks %s, the browser this machine has" % picks if picks else download))
    moved = home_chrome(ctx.home) if browser == "Chrome" else None
    if browser == "Chromium":
        options.append("run %s, which %s" % (command, download))
    elif moved:
        options.append("move %s into /Applications" % moved)
    else:
        options.append("install %s themselves" % browser)
    missing = ("not in %s" % playwright_cache(ctx.home) if browser == "Chromium" else
               "not in /Applications, where playwright-cli looks (it is in %s)" % moved if moved else "not installed")
    return ("playwright-cli config: browser missing (%s; names %s, %s)" % (where, browser, missing),
            ("ask", "the playwright-cli config %s names %s, which is %s." % (paths, browser, missing),
             "Ask the user once whether to %s." % ", or to ".join(options)))


def playwright_core_cli(cli_path):
    """playwright-core's cli.js inside the installed @playwright/cli package."""
    real = os.path.realpath(cli_path)
    cands = [os.path.join(os.path.dirname(real), "node_modules", "playwright-core", "cli.js"),
             os.path.join(os.path.dirname(real), "node_modules", "@playwright", "cli", "node_modules", "playwright-core", "cli.js"),
             os.path.join(os.path.dirname(os.path.dirname(real)), "lib", "node_modules", "@playwright", "cli", "node_modules", "playwright-core", "cli.js")]
    return next((c for c in cands if os.path.isfile(c)), None)


def node_version(node):
    code, out = run([node, "--version"])
    m = re.match(r"v(\d+)\.", out.strip()) if code == 0 else None
    return (int(m.group(1)), out.strip()) if m else (None, None)


def playwright_state(ctx):
    """lines, machine-level missing pieces, checkout-level missing pieces, PATH dirs to add.

    A machine-level piece is a name setup installs, `sudo:<what>:<command>` for one that needs
    sudo (Linux), or `user:<what>:<instruction>` for one setup cannot install. A checkout-level
    piece is a name `install --skills` writes, or ("ask", fact, question) for the user's choice."""
    lines, machine, checkout, off_path = [], [], [], []
    node, on_path = which("node", node_dirs(ctx.home))
    major, version = node_version(node) if node else (None, None)
    if on_path and major is not None and major < MIN_NODE:
        # An old Node first on PATH (a distribution's package); setup's newer one is off it
        for d in node_dirs(ctx.home):
            newer = os.path.join(d, "node.exe" if WINDOWS else "node")
            if os.path.isfile(newer):
                m, v = node_version(newer)
                if m is not None and m >= MIN_NODE:
                    node, on_path, major, version = newer, False, m, v
                    break
    if not node or major is None:
        lines.append("node: missing")
        machine.append("node")
    elif major < MIN_NODE:
        lines.append("node: too old (%s; needs %d+)" % (version, MIN_NODE))
        machine.append("old node")
    elif (not on_path and not WINDOWS and os.path.dirname(node) != local_bin(ctx.home)
          and not os.path.lexists(os.path.join(local_bin(ctx.home), "node"))):
        # nvm's Node with no link in ~/.local/bin: a setup from before the links makes them
        lines.append("node: ok but not on this shell's PATH (%s); setup links it into %s" % (node, local_bin(ctx.home)))
        machine.append("links in %s" % local_bin(ctx.home))
    elif not on_path:
        lines.append("node: ok but not on this shell's PATH (%s)" % node)
        off_path.append(os.path.dirname(node))
    else:
        lines.append("node: ok (%s)" % version)
    for link in broken_links(ctx.home):
        lines.append("%s: broken link (%s was uninstalled)" % (link, os.readlink(link)))
        links = "links in %s" % local_bin(ctx.home)
        if "broken " + links not in machine:
            machine[:] = [m for m in machine if m != links] + ["broken " + links]
    cli, on_path = which("playwright-cli", npm_bin_dirs(ctx.home))
    if not cli:
        lines.append("playwright-cli: missing")
        machine.append("playwright-cli")
    elif not on_path:
        lines.append("playwright-cli: ok but not on this shell's PATH (%s)" % cli)
        off_path.append(os.path.dirname(cli))
    else:
        lines.append("playwright-cli: ok")
    chrome = chrome_installed()
    edge = not chrome and edge_installed()
    pinned = pinned_chromium(cli)
    chromium = chromium_installed(ctx.home, pinned)
    cache = playwright_cache(ctx.home)
    if chrome:
        lines.append("browser: ok (Chrome)")
    elif edge:
        lines.append("browser: ok (Edge)")
    elif chromium:
        have = [next(f for f in names if cached(cache, f)) for names in pinned]
        lines.append("browser: ok (%s in %s)" % (" and ".join(have), cache))
    elif chromium is None:   # no browser step: with no playwright-cli, setup installs it; with no
        # readable browsers.json, a fresh install would not tell the revision either
        lines.append("browser: present (Chromium in %s; %s)" % (cache, unpinned(cli)))
    else:
        found = sorted(os.path.basename(os.path.dirname(p))
                       for p in glob.glob(os.path.join(cache, "chromium*-*", "INSTALLATION_COMPLETE")))
        stale = [f for f in found if pinned and not any(f in names for names in pinned)]
        lacking = [names[0] for names in pinned if not any(cached(cache, f) for f in names)] if pinned else ["Chromium"]
        moved = home_chrome(ctx.home)
        lines.append("browser: missing (%sno %s in %s%s)" % (
            "Chrome is in %s, not in /Applications, where playwright-cli looks; " % moved if moved else
            "no Chrome, no Edge, ",
            " and ".join(lacking), cache, "; found %s, which this playwright-cli does not launch" % ", ".join(stale) if stale else ""))
        if not moved or not cli_configs(ctx):   # no config: setup downloads Chromium (setup.sh, like this
            # check, ignores ~/Applications); with a config, its line asks about the browser it names instead
            machine.append("browser")
    configs = cli_configs(ctx)
    # Chrome's and Edge's packages bring their libraries; a config naming Chromium launches it even
    # with them installed, once it is downloaded (until then the config line asks about it)
    chromium_launched = (not chrome and not edge) or (chromium is not False and config_names_chromium(configs))
    if LINUX and chromium_launched and cli and node and "browser" not in machine:
        core = playwright_core_cli(cli)
        if not missing_libraries(ctx.home, pinned):
            lines.append("browser libraries: ok")
        elif core:
            lines.append("browser libraries: missing (needs sudo)")
            machine.append("sudo:Chromium's system libraries:sudo %s %s install-deps chromium" % (node, core))
        else:   # playwright-core's install-deps downloads no browser; without it, no command here is
            # libraries only
            where = os.path.dirname(os.path.realpath(cli))
            lines.append("browser libraries: missing (playwright-core not found in %s)" % where)
            machine.append("user:Chromium's system libraries:reinstall playwright-cli with `npm install -g"
                           " @playwright/cli@latest`, since playwright-core, whose install-deps installs"
                           " them, is not in %s" % where)
    skills = [os.path.join(ctx.root, d, "skills", "playwright-cli", "SKILL.md") for d in (".claude", ".agents")]
    if any(os.path.isfile(s) for s in skills):
        lines.append("playwright-cli skill: ok (this checkout)")
    else:
        lines.append("playwright-cli skill: missing (this checkout)")
        checkout.append("skill")
    unignored = unignored_files(ctx.root)
    if unignored:
        lines.append("playwright-cli files: not ignored by git (%s)" % ", ".join(unignored))
        checkout.append(("ask-git", "git does not ignore what playwright-cli writes in this checkout (%s), so a"
                         " commit could take it along." % ", ".join(unignored),
                         "Ask the user whether to add %s to %s, the lines the Template keeps under"
                         " `# Browser capture`." % (", ".join("`%s/`" % f for f in unignored),
                                                     os.path.join(ctx.root, ".gitignore"))))
    elif unignored is not None:
        lines.append("playwright-cli files: ignored by git")
    if configs:   # install --skills keeps a config it finds, here or global, and picks no browser
        line, ask = config_state(ctx, configs, chrome, chromium, cli)
        lines.append(line)
        if ask:
            checkout.append(ask)
    elif not chrome:
        lines.append("playwright-cli config: missing (this checkout; picks %s when Chrome is missing)"
                     % ("Edge" if edge else "Chromium"))
        checkout.append("config")
    return lines, machine, checkout, off_path


# The folders playwright-cli writes in a checkout, which .gitignore keeps out of git
PLAYWRIGHT_FILES = [".claude/skills/playwright-cli", ".agents/skills/playwright-cli", ".playwright", ".playwright-cli"]


def ignored(root, paths):
    """The paths (relative to root) git's ignore rules leave out, whether or not they exist; None when
    git cannot tell (no git, or root not in a repository)."""
    try:
        p = subprocess.run(["git", "-C", root, "-c", "core.quotepath=false", "check-ignore", "--no-index", "--"] + paths,
                           capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode not in (0, 1):   # 1: none of them is ignored
        return None
    return {l.strip().replace("\\", "/") for l in p.stdout.splitlines()}


def unignored_files(root):
    """The PLAYWRIGHT_FILES folders git would not ignore a file in; None when git cannot tell."""
    probes = {f: f + "/probe" for f in PLAYWRIGHT_FILES}
    found = ignored(root, list(probes.values()))
    return None if found is None else [f for f, probe in probes.items() if probe not in found]


def missing_clause(items):
    """Machine pieces as one clause: "node and playwright-cli are missing", "the links in <dir> are
    broken and playwright-cli is missing". An item is a name setup installs, `links in <dir>`
    (setup's links to nvm's Node, not made yet), `broken links in <dir>` or `old node`."""
    def joined(names):
        return names[0] if len(names) == 1 else "%s and %s" % (", ".join(names[:-1]), names[-1])
    def clause(items, state):
        names = ["the " + i if i.startswith("links ") else "a browser" if i == "browser" else i for i in items]
        plural = len(items) > 1 or items[0].startswith("links ") or items[0].endswith("libraries")
        return "%s %s %s" % (joined(names), "are" if plural else "is", state)
    states = {"broken ": "broken", "old ": "too old"}
    groups = {}
    for i in items:
        prefix = next((p for p in states if i.startswith(p)), "")
        groups.setdefault(prefix, []).append(i[len(prefix):])
    clauses = [clause(groups[p], states.get(p, "missing")) for p in ("broken ", "old ", "") if p in groups]
    return " and ".join(clauses)


def tools_module(name):
    """A script beside this one, imported: -I leaves this folder off sys.path."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
    return __import__(name)


def resume_module():
    """tools/resume.py, which finds TinyTeX and poppler for both scripts."""
    return tools_module("resume")


def tinytex_state(ctx):
    resume = resume_module()
    lines, machine = [], []
    tex = resume.tex_bin("pdflatex")
    lines.append("pdflatex: ok (%s)" % tex if tex else "pdflatex: missing")
    if not tex:
        machine.append("pdflatex")
    pdftotext = resume.poppler_bin("pdftotext", ctx.home)
    if pdftotext:
        lines.append("pdftotext: ok (%s; %s)" % (pdftotext, poppler_source(ctx, pdftotext)))
    else:   # setup installs conda-forge's into its micromamba environment, with no admin step (#281)
        lines.append("pdftotext: missing (poppler's, with -bbox-layout)")
        machine.append("poppler")
    return lines, machine, [], []


def poppler_source(ctx, pdftotext):
    """Where the poppler in use came from, and how it is updated. Told by its path, which is what
    tools/resume.py uses; the `poppler` line setup writes into machine.toml only records it."""
    env = os.path.normcase(os.path.abspath(tools_module("resume").poppler_env(ctx.home)))
    if os.path.normcase(os.path.abspath(pdftotext)).startswith(env + os.sep):
        return "setup's micromamba environment; rerun setup to update it"
    return "the user's own install; setup leaves it as it is, and the tool that installed it updates it"


STATE = {"playwright-cli": playwright_state, "tinytex": tinytex_state}


def offer(ctx, tool, kind):
    need = (" %s cannot do that without it." % ctx.mode) if kind == "hard" and ctx.mode != "setup" else ""
    return ('ask the user once, in these words: "%s %s.%s Install it on this machine? It installs'
            ' %s, for your user only. Your answer is kept in %s, so I will not ask again on this'
            ' machine." Any answer but yes is a no. On yes run `%s` %s; on no run `%s`. Then run this'
            ' check again.'
            % (NAME[tool], PURPOSE[tool], need, WHAT[tool], ctx.machine_toml,
               setup_cmd(ctx.root, yes=[tool]), RUN_SETUP, setup_cmd(ctx.root, no=[tool])))


def check_tools(ctx):
    needs = NEEDS.get(ctx.mode, [])
    if not needs:
        return [], [], False
    choices, error = read_choices(ctx)
    if choices is None:
        return (["machine setup: unreadable (%s: %s)" % (ctx.machine_toml, error)],
                ["next: stop: show the user %s and the error, and rewrite it with one `<tool> ="
                 " true|false` line for each answer it held (tools: %s); then run this check again."
                 % (ctx.machine_toml, ", ".join(TOOLS))],
                True)
    lines, nexts = [], []
    for tool, kind in needs:
        required = tool not in TOOLS
        choice = True if required else choices.get(tool)
        lines.append("%s: required" % tool if required else
                     "%s wanted: %s" % (tool, {True: "yes", False: "no (declined)", None: "not asked"}[choice]))
        tl, machine, checkout, off_path = STATE[tool](ctx)
        lines += tl
        sudo = [m.split(":", 2)[1:] for m in machine if m.startswith("sudo:")]
        user = [m.split(":", 2)[1:] for m in machine if m.startswith("user:")]
        machine = [m for m in machine if not m.startswith(("sudo:", "user:"))]
        # A hard need ends the mode at the step that needs the tool; a soft one falls back.
        hard = kind == "hard" and ctx.mode != "setup"
        stop = "stop: " if hard else ""
        if hard:
            unavailable = "%s cannot go past this step" % ctx.mode
        elif tool == "playwright-cli":
            unavailable = "go to the next item of browser.md, Fallback order"
        else:
            unavailable = "skip the steps that need it"
        todo = []
        missing = machine + [what for what, _ in sudo + user]
        if missing and choice is None and UNATTENDED and ctx.mode != "setup":
            todo.append("%s is not offered on this machine yet, and this run is unattended"
                        " (CAREER_LOG_UNATTENDED), so it asks nothing: offer it in a session with the user;"
                        " for this run, %s." % (tool, unavailable))
        elif missing and choice and UNATTENDED:
            todo.append("%ssetup is needed on this machine: %s. This run is unattended"
                        " (CAREER_LOG_UNATTENDED), so it installs nothing and asks nothing: say so in the"
                        " run's result; for this run, %s." % (stop, missing_clause(missing), unavailable))
        elif choice is False:
            if hard:
                todo.append("stop: %s needs %s, which the user turned off on this machine. Tell them, and"
                            " that saying \"install %s\" turns it on: `%s`."
                            % (ctx.mode, tool, tool, setup_cmd(ctx.root, yes=[tool])))
            elif ctx.mode == "setup":   # a state: setup has nothing to install, and reads no page
                lines[-1 - len(tl)] += (" (%s is off on this machine; nothing to do in setup unless the user asks"
                                        " to install it: `%s`)" % (FEATURE[tool], setup_cmd(ctx.root, yes=[tool])))
            else:
                todo.append("%s is off on this machine (the user declined %s): %s. Install it only when"
                            " the user asks for it: `%s`."
                            % (FEATURE[tool], tool, unavailable, setup_cmd(ctx.root, yes=[tool])))
        elif choice is None and missing and ctx.mode == "setup":   # setup's own round asks
            if os.path.exists(os.path.join(ctx.root, "config.toml")):
                lines[-1 - len(tl)] += " (the user skipped it in setup; the skill offers it when a mode needs it)"
        elif choice is None and missing:
            todo.append(offer(ctx, tool, kind))
        elif machine and required:
            todo.append("%s is part of this machine's setup, and %s: tell the user that setup"
                        " installs it now, with no question, then run `%s` %s; then run this check again."
                        % (tool, missing_clause(machine), setup_cmd(ctx.root), RUN_SETUP))
        elif machine:
            todo.append("the user chose %s on this machine, and %s: run `%s` %s; then run this"
                        " check again." % (tool, missing_clause(machine), setup_cmd(ctx.root, yes=[tool]), RUN_SETUP))
        else:
            if off_path:
                todo.append("start every command that runs node, npm or playwright-cli in this session"
                            " with `%s; `" % path_reload(off_path))
            for what, command in sudo:
                todo.append("%smissing: %s, which needs sudo. Give the user this command to run in their"
                            " own terminal, where it asks for their password: `%s`. When they say it ran,"
                            " run this check again; until then, %s." % (stop, what, command, unavailable))
            for what, instruction in user:
                todo.append("%smissing: %s, which setup cannot install here. Tell the user to %s. When"
                            " they say it is done, run this check again; until then, %s."
                            % (stop, what, instruction, unavailable))
            asks = [c for c in checkout if isinstance(c, tuple)]
            config_asks = [c for c in asks if c[0] == "ask"]
            for _, fact, question in asks:
                if UNATTENDED:
                    todo.append("%s%s This run is unattended (CAREER_LOG_UNATTENDED), so it asks nothing:"
                                " say so in the run's result; for this run, %s." % (stop, fact, unavailable))
                else:
                    todo.append("%s%s %s Do what they choose, then run this check again; until then, %s."
                                % (stop, fact, question, unavailable))
            if len(asks) < len(checkout) and not any(c[0] == "ask-git" for c in asks):   # git first ignores what it writes
                reload = path_reload(off_path) + "; " if off_path else ""
                # With a config whose browser is missing, the download waits for the user's answer
                install = "playwright-cli install --skills"
                if config_asks and WINDOWS:   # PowerShell keeps $env: set for the rest of the session
                    install = ("$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'; %s; Remove-Item"
                               " Env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD" % install)
                elif config_asks:
                    install = "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 " + install
                todo.append("from %s run `%s%s` (`--skills agents` for agents that read .agents/skills/),"
                            " with no question: it writes only files git ignores in this checkout and, when it"
                            " is missing, about 3 MB of FFmpeg in Playwright's cache." % (ctx.root, reload, install))
        when = "now, for %s" % tool if ctx.mode == "setup" else "now" if ctx.mode == "browser" else WHEN[tool]
        nexts += ["next: %s, first: %s" % (when, t) for t in todo]
    return lines, nexts, False


# ---- Uncommitted Log changes ----

logfiles = tools_module("logfiles")
python_cmd = logfiles.python_cmd   # how a printed command starts Python (SKILL.md › Platforms)
# The Log's own files (AGENTS.md › Changes); Engine files and the ignored inbox are not reported.
LOG_PATHS = logfiles.LOG_PATHS


def tool_cmd(root, name):
    """How the agent runs another tool of this Log, its path in double quotes."""
    return '%s -I "%s"' % (python_cmd(), os.path.join(root, "tools", name))


def check_uncommitted(ctx):
    """One line per Log file with uncommitted changes; nothing when the Log is clean or git fails."""
    try:
        p = subprocess.run(["git", "-C", ctx.root, "-c", "core.quotepath=false", "status", "--porcelain",
                            "-z", "--untracked-files=all", "--"] + LOG_PATHS,
                           capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return [], [], False
    if p.returncode != 0:
        return [], [], False
    files, entries = [], iter(p.stdout.split("\0"))
    for entry in entries:
        if len(entry) > 3:
            status, path = entry[:2], entry[3:]
            if "R" in status or "C" in status:   # a rename's -z entry is followed by its old path
                path += " (from %s)" % next(entries, "?")
            files.append((status.strip(), path))
    if not files:
        return [], [], False
    lines = ["log changes: uncommitted (%d file(s))" % len(files)]
    lines += ["log change: %s %s" % (status, path) for status, path in files]
    sync = tool_cmd(ctx.root, "sync.py")
    nexts = ["next: now, first: the files above that are not this session's own bulk change waiting for the"
             " user's yes are changes an earlier session left. Show the user what `%s status -- <file>...`"
             " prints for those files and ask whether to commit them (`%s settle commit -- <file>...`) or"
             " discard them (`%s settle discard -- <file>...`, then follow its output), naming those files"
             " each time; then go on with the request." % (sync, sync, sync)]
    return lines, nexts, False


# ---- This Log's git state ----

def is_repo(root):
    """Whether root is the top folder of a git work tree (not a folder inside another repo)."""
    top = logfiles.git_run(root, "rev-parse", "--show-toplevel")
    same = lambda path: os.path.normcase(os.path.realpath(path))
    return top.returncode == 0 and same(top.stdout.strip()) == same(root)


def has_origin(root):
    return logfiles.git_run(root, "remote", "get-url", "origin").returncode == 0


def check_git(ctx):
    """identity, default branch and ahead; read only (sync.py commits, pushes and pulls)."""
    try:
        if not is_repo(ctx.root):
            return ["git: not a repository (%s)" % ctx.root], [], False
        lines, nexts = [], []
        _, email = logfiles.local_identity(ctx.root)
        if email:
            lines.append("identity: ok (%s)" % email)
        else:
            lines.append("identity: missing (no repo-local user.email)")
            nexts.append("next: when a step commits, first: set this Log's own git identity with the user, as"
                         " SETUP.md step 3 says: the machine-wide one may belong to someone else, so sync.py"
                         " commits nothing without it.")
        if not has_origin(ctx.root):
            return lines + ["default branch: none (no origin remote)"], nexts, False
        default = logfiles.default_branch(ctx.root)
        if default is None:
            lines.append("default branch: unknown (origin/HEAD is not set)")
            nexts.append("next: when a step names <default>, first: run `git -C \"%s\" remote set-head origin"
                         " --auto`; <default> is then what `git -C \"%s\" symbolic-ref --short"
                         " refs/remotes/origin/HEAD` prints, without `origin/`." % (ctx.root, ctx.root))
            return lines, nexts, False
        lines.append("default branch: %s" % default)
        current = logfiles.git_run(ctx.root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
        if current != default:   # a scan draft branch, a worktree's own: commits go elsewhere
            return lines + ["branch: %s (not %s)" % (current or "detached HEAD", default)], nexts, False
        ahead = logfiles.git_run(ctx.root, "rev-list", "--count", "origin/%s..HEAD" % default)
        n = ahead.stdout.strip()
        if ahead.returncode != 0 or not n.isdigit():   # origin/<default> not fetched, or no commit yet
            lines.append("ahead: unknown")
        elif n == "0":
            lines.append("ahead: 0")
        else:   # no step of its own: a pushing sync.py commit pushes HEAD, these commits with it
            lines.append("ahead: %s (not on origin yet; a sync.py commit that pushes takes them along, or, in a"
                         " mode that commits nothing, `sync.py push` at Next up)" % n)
        return lines, nexts, False
    except logfiles.LogError as e:   # git cannot start, or gives no answer in time
        return ["git: unavailable (%s)" % e], [], False


def check_pull(ctx):
    """The pull every mode starts with (SKILL.md › Trigger check), after the other steps; sync.py pulls."""
    try:   # a branch with no upstream (a detached HEAD too) has nothing to pull from
        upstream = logfiles.git_run(ctx.root, "rev-parse", "--verify", "-q", "@{upstream}").returncode == 0
        if not (is_repo(ctx.root) and has_origin(ctx.root) and upstream):
            return [], [], False
    except logfiles.LogError:
        return [], [], False
    return [], ["next: now, first: run `%s pull` (another clone may have pushed) and follow its output;"
                " go on once it ends with `sync: ok`, with no rerun of this check for the pull." % tool_cmd(ctx.root, "sync.py")], False


# ---- Setup for this Log ----

def check_config(ctx):
    """Whether setup has run for this Log (config.toml exists and parses), and its Config values."""
    config_tool = tools_module("config")
    try:
        config = config_tool.load(ctx.root)
    except config_tool.ConfigError as e:
        return (["config: unreadable (%s)" % e],
                ["next: stop: show the user the error above, fix the file it names with them so that `%s -I"
                 " \"%s\" show` prints its fields, then run this check again."
                 % (python_cmd(), os.path.join(ctx.root, "tools", "config.py"))],
                True)
    if config is None and ctx.mode == "setup" and not UNATTENDED:
        return ["config: missing (setup writes it)"], [], False
    if config is None and UNATTENDED:
        return (["config: missing (setup has not run for this Log)"],
                ["next: stop: setup has not run for this Log, and this run is unattended"
                 " (CAREER_LOG_UNATTENDED), so it asks nothing: say so in the run's result."], True)
    if config is None:
        return (["config: missing (setup has not run for this Log)"],
                ["next: stop: setup has not run for this Log, so no mode runs yet. Tell the user, and"
                 " on their yes start the setup mode (SKILL.md, Modes) in place of this request; take"
                 " the request up again once setup is done."], True)
    return ["config %s: %s%s" % (f, v, " (default)" if d else "") for f, (v, d) in config.items()], [], False


# ---- Mode state ----

# The skill link of each agent SETUP.md step 4 lists, under the home folder
SKILL_LINKS = {"claude": ".claude/skills/career-log", "codex": ".agents/skills/career-log",
               "antigravity-app": ".gemini/config/skills/career-log",
               "antigravity-cli": ".gemini/antigravity-cli/skills/career-log"}
INBOX_LINES = ["sources/inbox/*", "!sources/inbox/.gitkeep"]   # raw chat exports stay out of git (a guard file)
PROFILE_STEP = "next: when a step would read an interviewer's profile shown only to signed-in members, first: "


def same_path(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def direction_state(ctx):
    """`direction <item>: set|empty|unreadable (<why>)`, one per Direction item, from config.py show's lines."""
    config_tool = tools_module("config")
    lines = config_tool.direction_lines(ctx.root)
    out = []
    for item in config_tool.DIRECTION_LINES:
        mine = [l[len("direction %s: " % item):] for l in lines if l.startswith("direction %s: " % item)]
        state = "empty" if mine == ["empty"] else mine[0] if mine and mine[0].startswith("unreadable") else "set"
        out.append("direction %s: %s" % (item, state))
    return out


def eol_state(root):
    """setup's `eol:` line: SETUP.md step 2's check of the line ends git wrote."""
    out = git_out(root, "ls-files", "--eol")
    if out is None:
        return "eol: unknown (git ls-files failed)"
    wrong = []
    for line in out.splitlines():
        fields, _, path = line.partition("	")
        work = next((f for f in fields.split() if f.startswith("w/")), "")
        want = "w/crlf" if "eol=crlf" in fields.split() else "w/lf"   # .gitattributes: *.ps1 and *.bat CRLF
        if work not in (want, "w/", "w/none", "w/-text"):   # w/: deleted from the working tree
            wrong.append("%s %s" % (path, work))
    if not wrong:
        return "eol: ok"
    return "eol: wrong (%s%s; SETUP.md step 2)" % (", ".join(wrong[:5]), " and %d more" % (len(wrong) - 5) if len(wrong) > 5 else "")


def skill_link_lines(ctx):
    """setup's `skill link <agent>:` lines, one per row of SETUP.md step 4."""
    skill = os.path.join(ctx.root, "skills", "career-log")
    out = []
    for agent, rel in SKILL_LINKS.items():
        link = os.path.join(ctx.home, *rel.split("/"))
        if not os.path.lexists(link):
            out.append("skill link %s: missing (%s; only an agent the user runs needs it, made as SETUP.md step 4"
                       " says)" % (agent, link))
        elif not os.path.exists(link):
            out.append("skill link %s: broken (%s leads to %s, which is gone)" % (agent, link, os.path.realpath(link)))
        elif same_path(link, skill):
            out.append("skill link %s: ok (%s)" % (agent, link))
        else:
            out.append("skill link %s: elsewhere (%s leads to %s)" % (agent, link, os.path.realpath(link)))
    return out


def inbox_state(ctx):
    """import's `gitignore inbox:` line, and the step that adds the lines .gitignore lacks."""
    try:
        with open(os.path.join(ctx.root, ".gitignore"), encoding="utf-8-sig") as f:
            have = {l.strip() for l in f}
    except FileNotFoundError:
        have = set()
    except (OSError, UnicodeDecodeError) as e:
        return (["gitignore inbox: unreadable (%s)" % e],
                ["next: now, first: tell the user that .gitignore cannot be read (%s), and put nothing in"
                 " sources/inbox/ until it reads and holds %s." % (e, " and ".join("`%s`" % l for l in INBOX_LINES))])
    found = ignored(ctx.root, ["sources/inbox/probe", "sources/inbox/.gitkeep"])
    if found is None:   # git cannot tell: the lines themselves
        lacking = [l for l in INBOX_LINES if l not in have]
    else:   # an equal rule in other words counts too
        lacking = (([] if "sources/inbox/probe" in found else [INBOX_LINES[0]])
                   + ([INBOX_LINES[1]] if "sources/inbox/.gitkeep" in found else []))
    if not lacking:
        return ["gitignore inbox: ok"], []
    return (["gitignore inbox: missing (%s)" % ", ".join(lacking)],
            ["next: now, first: add the line(s) %s to %s, then run `%s commit \"gitignore: sources/inbox\" --"
             " .gitignore`, before anything is put in sources/inbox/: the raw exports there stay out of git"
             " (skills/career-log/engine-changes.md › Exceptions, guard files)." % (", ".join("`%s`" % l for l in lacking),
                                                        os.path.join(ctx.root, ".gitignore"), tool_cmd(ctx.root, "sync.py"))])


def profile_step(config):
    """interview's step for a profile shown only to signed-in members, from interviewer_profiles."""
    if config["interviewer_profiles"][0] == "always":
        return (PROFILE_STEP + "read it through the signed-in profile (browser.md › Sign-in):"
                " config.toml's interviewer_profiles is \"always\".")
    return (PROFILE_STEP + "keep to public pages and search results, with a `GAP:` for what they do not show,"
            " and make that `GAP:` the report's last word on the profile. Say once that"
            " `interviewer_profiles = \"never\"` in config.toml is why, and that the user changes it by saying so"
            " (setup › Changes).")


def check_mode_state(ctx):
    """The state lines one mode reads: Direction items in every mode; setup's front page, line ends and
    skill links; import's inbox lines in .gitignore; scan's windows; interview's profile step."""
    config_tool = tools_module("config")
    try:
        config = config_tool.load(ctx.root)
    except config_tool.ConfigError:
        config = None   # check_config has stopped the run, but in setup
    lines, nexts = direction_state(ctx), []
    if ctx.mode == "setup":
        try:
            lines.append("front page: %s" % config_tool.front_page_state(ctx.root))
        except config_tool.ConfigError as e:
            lines.append("front page: unreadable (%s)" % e)
        lines.append(eol_state(ctx.root))
        lines += skill_link_lines(ctx)
    elif ctx.mode == "import":
        il, nexts = inbox_state(ctx)
        lines += il
    elif ctx.mode == "scan" and config:
        window, scheduled = config["window"][0], config["scheduled_window"][0]
        scheduled = window if scheduled == "window" else scheduled
        lines.append("scan window: %s days (window); %s days in an unattended run (scheduled_window)" % (window, scheduled))
    elif ctx.mode == "interview" and config:
        nexts.append(profile_step(config))
    return lines, nexts, False


# ---- Entry size ----

def check_size(ctx):
    """One line per entry past tools/entries.py's threshold; never stops the mode."""
    entries = tools_module("entries")
    try:
        return entries.over_threshold(entries.load(ctx.root)), [], False
    except (OSError, UnicodeDecodeError):
        return [], [], False


# ---- Newer Template release ----

RELEASES_URL = os.environ.get("CAREER_LOG_RELEASES_URL")   # None: the Template tools/upgrade.py fetches
RELEASE_TIMEOUT = 2   # seconds, for the whole request, name lookup included
RELEASE_EVERY = 24 * 3600


def latest_release(url):
    """The newest release's version from a Releases API URL, or None when it cannot be had in time."""
    import threading
    import urllib.request
    found = []

    def fetch():
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=RELEASE_TIMEOUT) as r:
                tag = json.loads(r.read(1 << 20)).get("tag_name")
            found.append(tag[1:] if isinstance(tag, str) and tag.startswith("v") else tag)
        except Exception:
            pass

    t = threading.Thread(target=fetch, daemon=True)
    t.start()
    t.join(RELEASE_TIMEOUT)
    return found[0] if found and isinstance(found[0], str) else None


def release_cache(ctx):
    return os.path.join(ctx.home, ".career-log", "release.json")


def cached_release(ctx, now):
    """The newest release known from the last day: (True, version or None), or (False, None) to ask."""
    try:
        with open(release_cache(ctx), encoding="utf-8") as f:
            cache = json.load(f)
        latest = cache["latest"]
        if 0 <= now - cache["checked"] < RELEASE_EVERY and (latest is None or isinstance(latest, str)):
            return True, latest   # None: the last ask failed (offline, rate-limited); ask again tomorrow
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return False, None


def check_release(ctx):
    """An `update:` line when a newer Template release than tools/TEMPLATE_VERSION's exists; never stops."""
    try:
        config = tools_module("config").load(ctx.root) or {}
        if UNATTENDED or config.get("update_check", ("on",))[0] != "on":
            return [], [], False
        upgrade = tools_module("upgrade")
        have = upgrade.stamped(ctx.root)[0]
        if not have or not upgrade.SEMVER.match(have):   # no stamp, or `next`: an unreleased export
            return [], [], False
        now = time.time()
        known, latest = cached_release(ctx, now)
        if not known:
            repo = upgrade.URL.removeprefix("https://github.com/").removesuffix(".git")
            latest = latest_release(RELEASES_URL or "https://api.github.com/repos/%s/releases/latest" % repo)
            path = release_cache(ctx)
            own = "%s.%d" % (path, os.getpid())
            try:   # through a file of its own, so a session running the check at the same time reads a whole one
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(own, "w", encoding="utf-8") as f:
                    json.dump({"checked": now, "latest": latest}, f)
                os.replace(own, path)
            except OSError:   # on Windows, another session holding release.json open
                try:
                    os.remove(own)
                except OSError:
                    pass
        if latest and upgrade.SEMVER.match(latest) and upgrade.key(latest) > upgrade.key(have):
            return (["update: v%s available (you have v%s): tell the user once this session, in passing, and go"
                     " on; only their request (\"upgrade\") starts the upgrade mode, and `update_check = \"off\"` in"
                     " config.toml stops this line (setup › Changes)" % (latest, have)], [], False)
    except Exception:
        pass
    return [], [], False


# ---- Session hygiene ----

FRESH = "Start a new session (or `/clear`) first: everything this session did is in the Log."
# Files the Log's mode commits keep beside LOG_PATHS (which holds stories/): the guard files
# (SKILL.md › Commits)
SAVED_TOO = [".export-deny", ".export-cleared"]


def consolidated(root):
    """True when no README row has the status `stub` or `imported`."""
    rows, _ = tools_module("entries").readme_rows(root)
    return not any(re.match(r"(stub|imported)\b", row.get("status", "")) for row in rows.values())


# A step of the first-use flow is done, and skipped, when the Log's state says so. The inbox is no
# sign: import-chats leaves its raw exports there for the user to move.
DONE = {"import": lambda root: bool(tools_module("entries").load(root)), "consolidate": consolidated,
        "stories": lambda root: bool(tools_module("entries").talking_points_files(root))}


def git_out(root, *args):
    """git's stdout, with its last newline taken off, or None when git fails; its warnings on stderr
    are left out."""
    try:
        p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, encoding="utf-8",
                           errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.rstrip("\n") if p.returncode == 0 else None


class Guide:
    """The flows table and SKILL.md › Modes, read through tools/guide.py; `error` when they cannot be."""

    def __init__(self, root):
        self.flows, self.modes, self.error = [], {}, None
        try:
            guide = tools_module("guide")
            self.flows = guide.flows(root)
            header, rows = guide.table(guide.read(os.path.join(root, *guide.SKILL_MD.split("/"))), "Modes")
        except Exception as e:   # GuideError, OSError: the block goes on without the guide
            self.error = str(e)
            return
        col = {h.lower(): i for i, h in enumerate(header)}
        cell = lambda r, name: r[col[name]] if name in col and col[name] < len(r) else ""
        for r in rows:
            examples = re.findall(r'"([^"]+)"', cell(r, "for example"))
            name = r[0].strip("* ")
            if name == "guide":   # the guide's request for where to go from here
                examples = [e for e in examples if "next" in e] + examples
            self.modes[name] = {"example": examples[0] if examples else None, "file": cell(r, "file")}

    def parent(self, mode):
        """The SKILL.md › Modes row a mode runs under: its own, or the one whose File links modes/<mode>.md."""
        if mode in self.modes:
            return mode
        return next((m for m, v in self.modes.items() if "modes/%s.md" % mode in v["file"]), mode)

    def step(self, mode):
        """The first flows row of a mode, or None."""
        return next((r for r in self.flows if r["mode"] == mode), None)

    def said(self, mode):
        example = self.modes.get(mode, {}).get("example")
        return '`%s` (say "%s")' % (mode, example) if example else "`%s`" % mode


def check_session(ctx):
    """The mode start line and the fresh-session suggestion; nothing for log or an unattended run."""
    if ctx.mode == "log" or UNATTENDED:
        return [], [], False
    guide = Guide(ctx.root)
    same = sorted({r["mode"] for r in guide.flows if r["session"] == "same" and guide.parent(r["next"]) == ctx.mode})
    head = git_out(ctx.root, "rev-parse", "--short", "HEAD")
    lines = (["mode start: %s@%d (Next up's --since; on a rerun of this mode's check, keep the first one)"
              % (head, int(time.time()))] if head else [])
    nexts = ["next: now, first: on any rerun of this check within this run of %s, skip this line: it is for the"
             " mode's first check. At the first check: if this session already ran a career-log mode before this"
             " run started, an earlier run of %s included, suggest that the user start a new session (or `/clear`)"
             " for %s, saying why in one line: a session that fills up writes worse, and the Log and git already"
             " hold what the earlier mode saved. Then wait for their answer: for a new session, stop here; if they"
             " stay, go on here. Not counted: log, guide, a setup this request's Trigger check started%s."
             % (ctx.mode, ctx.mode, ctx.mode, ", and %s, whose flow the guide goes on with in the same session"
                % ", ".join(same) if same else "")]
    return lines, nexts, False


def saved_lines(root, since):
    """The commits made since `mode start`: those in <sha>..HEAD committed at or after <time>."""
    if not since:
        return ["Saved: not listed (no --since)"]
    sha, _, at = since.partition("@")
    out = git_out(root, "log", "--no-show-signature", "--format=%ct %h %s", "%s..HEAD" % sha)
    if out is None or not at.isdigit():
        return ["Saved: not listed (%s is not a `mode start` value of this Log)" % since]
    commits = []
    for line in out.splitlines():
        stamp, _, rest = line.partition(" ")
        if stamp.isdigit() and int(stamp) >= int(at):
            commits.append(rest)
    if not commits:
        return ["Saved: no commit (this mode changed nothing in the Log)"]
    shown = ["  " + c for c in commits[:10]] + (["  ... and %d more" % (len(commits) - 10)] if len(commits) > 10 else [])
    return ["Saved: %d commit(s) in the Log:" % len(commits)] + shown


def unsaved(ctx):
    """What keeps the Log from holding everything: uncommitted Log files, commits not on origin."""
    lines, _, _ = check_uncommitted(ctx)
    files = [l[len("log change: "):] for l in lines if l.startswith("log change: ")]
    extra = git_out(ctx.root, "-c", "core.quotepath=false", "status", "--porcelain", "-z", "--untracked-files=all",
                    "--", *SAVED_TOO)
    files += [e[:2].strip() + " " + e[3:] for e in (extra or "").split("\0") if len(e) > 3]
    ahead = git_out(ctx.root, "rev-list", "--count", "@{upstream}..HEAD")
    if ahead is None:   # no upstream: compare with origin's default branch
        default = git_out(ctx.root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        ahead = git_out(ctx.root, "rev-list", "--count", "%s..HEAD" % default) if default else None
    out = []
    if files:
        out.append("%d Log file(s) not committed (%s)" % (len(files), ", ".join(files)))
    if ahead and ahead.isdigit() and ahead != "0":
        out.append("%s commit(s) not pushed%s" % (ahead, PUSHES if pushable(ctx.root) else ""))
    return out


PUSHES = " (`sync.py push` pushes them)"


def pushable(root):
    """Whether HEAD is on a branch sync.py pushes from: origin's default one, or a scan draft branch."""
    current = git_out(root, "symbolic-ref", "--short", "-q", "HEAD")
    default = git_out(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    return bool(current) and (current.startswith("scan/") or "origin/%s" % current == default)


# Why a step comes again when the Log's state says its work is not done yet. An import answered No
# leaves no entries; the steps after it, which read entries, are not done but cannot start.
AGAIN = {"consolidate": "Entries still marked `stub` or `imported` in README.md have gaps and pending notes too",
         "import": "The Log has no entries yet: the import was undone, or found nothing to keep"}
# The steps that read entries: on a Log with none, import comes first, whichever mode ran (#424)
READS_ENTRIES = ("consolidate", "stories", "fit", "write", "interview")
NO_ENTRIES = ("The Log has no entries yet, and the later steps read them: import your old resumes, exports and chat"
              " histories first")


def next_step(guide, mode, root):
    """The flows row whose Next is the step for this Log's state: this mode again while its own work
    is not done (AGAIN), else its Next, walking past steps already done; import when that Next reads
    entries and the Log has none."""
    if mode in AGAIN and not DONE[mode](root):
        return {"mode": mode, "next": mode, "why": AGAIN[mode], "session": "new"}
    row, seen = guide.step(mode), set()
    while row and row["next"] in DONE and row["next"] not in seen and DONE[row["next"]](root):
        seen.add(row["next"])
        after = guide.step(row["next"])
        if not after:
            break
        row = dict(after, session="new")
    if row and row["next"] in READS_ENTRIES and not DONE["import"](root):
        return {"mode": mode, "next": "import", "why": NO_ENTRIES, "session": "new"}
    return row


def done(argv, root=ROOT):
    """`done <mode> [--since <sha>@<time>] [--for <mode>] [--no-posting]`: the Next up block; (exit code, lines)."""
    opts, args = {}, list(argv)
    no_posting = "--no-posting" in args
    args = [a for a in args if a != "--no-posting"]
    for flag in ("--since", "--for"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                return 2, ["usage: %s needs a value" % flag]
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    guide = Guide(root)
    known = set(MODES) | set(guide.modes) | {r["mode"] for r in guide.flows}
    if (len(args) != 1 or args[0] not in known
            or ("--for" in opts and (args[0] != "setup" or opts["--for"] not in MODES))
            or (no_posting and args[0] != "fit")):
        return 2, ["usage: %s -I tools/check.py done <mode> [--since <sha>@<time>] [--for <mode>] [--no-posting]"
                   " (--for with setup only, --no-posting with fit only); <mode> is one of %s"
                   % (python_cmd(), ", ".join(sorted(known)))]
    mode = args[0]
    if mode == "log" or UNATTENDED:
        return 0, []
    out = ["Next up"] + saved_lines(root, opts.get("--since"))
    missing = unsaved(Context(mode, root=root))
    if "--for" in opts:
        out.append("Next: go back to `%s` in this session: setup ran for that request." % opts["--for"])
        if missing:
            out.append("Not saved yet: %s. Save it before you go on." % "; ".join(missing))
    else:
        row = None if no_posting else next_step(guide, mode, root)   # its Next follows from a posting's fit
        if guide.error:
            out.append("Next: not found (docs/guide.md: %s)." % guide.error)
        elif row is None:
            out.append("Next: no fixed step after `%s`; pick what you need from the modes below." % mode)
        elif row["next"] == "-":
            out.append("Next: none in this flow. %s." % row["why"].rstrip("."))
        else:
            out.append("Next: %s. %s." % (guide.said(row["next"]), row["why"].rstrip(".")))
        if missing:
            out.append("Not saved yet: %s. Save it before you leave this session." % "; ".join(missing))
        elif row and row["next"] != "-" and row["session"] == "same":
            out.append("Go on in this session: the guide runs `%s` right after `%s`, in the same session."
                       % (row["next"], mode))
        else:
            out.append(FRESH)
        flow_modes = {r["mode"] for r in guide.flows} | {r["next"] for r in guide.flows}
        # upgrade is the user's call, on a release they heard of, not a next step to offer
        also = [m for m in guide.modes if m not in flow_modes and m not in ("guide", "upgrade", mode)]
        if not tools_module("entries").load(root):
            also = []   # with no entries, the modes outside the flows have nothing to read
        out.append("Also available: " + ", ".join(guide.said(m) for m in also + ["guide"]))
    show = ("end your last message with the block above, from `Next up` on" if "--for" not in opts else
            "show the user the block above, from `Next up` on, then go on with %s, starting with its Trigger"
            " check" % opts["--for"])
    as_printed = (", line for line, translated into the user's language; commit subjects, backticked names and"
                  " quoted requests stay as printed.")
    if missing:
        push = ""
        if any(m.endswith(PUSHES) for m in missing):   # no other command only pushes
            push = (" (commits not pushed: `%s push`; in the upgrade mode before its step 5, leave them: that"
                    " push waits for the user's yes)" % tool_cmd(root, "sync.py"))
        out.append("next: now, first: settle what is not saved, as SKILL.md › Commits says%s, then run this"
                   " command again. When it cannot be settled (a push that fails), say what failed and %s, as"
                   " it stands%s" % (push, show, as_printed))
        return 1, out
    out.append("next: %s%s" % (show, as_printed))
    return 0, out


CHECKS = [check_python, check_session, check_uncommitted, check_git, check_config, check_mode_state, check_size,
          check_release, check_tools, check_pull]
BROWSER_CHECKS = [check_python, check_tools]   # `browser`: playwright-cli's state alone


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):   # Log file names in any language, whatever the code page
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if "-h" in argv or "--help" in argv:
        print(__doc__.rstrip())
        return 0
    try:
        root, argv = logfiles.split_root(argv, os.path.join(HERE, "check.py"))
    except logfiles.LogError as e:
        print("usage: %s" % e)
        return 2
    root = os.path.realpath(root)
    if argv[:1] == ["done"]:
        code, out = done(argv[1:], root=root)
        for line in out:
            print(line)
        return code
    if len(argv) != 1 or argv[0] not in MODES + ["browser"]:
        print("usage: %s -I tools/check.py <mode> [--root <root>]; <mode> is one of %s, or browser"
              % (python_cmd(), ", ".join(MODES)))
        return 2
    resume_module().no_error_dialogs()   # for every program the checks start, not only poppler
    ctx = Context(argv[0], root=root)
    print("root: %s" % ctx.root)
    lines, nexts, stopped = [], [], False
    for check in BROWSER_CHECKS if ctx.mode == "browser" else CHECKS:
        cl, cn, stop = check(ctx)
        lines += cl
        nexts += cn
        if stop:
            stopped = True
            break
    for line in lines + nexts:
        print(line)
    if stopped:
        return 1
    if not any(n.startswith("next: now") and "run this check again" in n for n in nexts):
        print("next: go on with the mode")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
