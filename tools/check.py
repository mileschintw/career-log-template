#!/usr/bin/env python3
"""The check every career-log trigger runs first (SKILL.md › Trigger check).

  python3 -I tools/check.py <mode>        (Windows: py -3 -I tools/check.py <mode>)

<mode> is a mode from SKILL.md's modes table (`setup` checks every optional tool). Prints one
`<what>: <state>` line per thing checked, then `next:` lines, the agent's steps in order: a
`next: when <moment>, first: <step>` line waits for that moment (`now`: before anything else), and
`next: stop: ...` ends the mode. The last line is `next: go on with the mode` when nothing stops it now.

Checks run in the order of CHECKS. Each takes the Context and returns (lines, nexts, stop);
`stop` ends the run after its lines are printed, for a state no later check can help with.
A later check is one more function appended to CHECKS.

Machine setup: TinyTeX (with poppler) is required, so setup installs it with no question.
~/.career-log/machine.toml holds the user's yes or no per optional tool (playwright-cli) on this
machine, one `<tool> = true|false` line each, written by tools/setup.sh and tools/setup.ps1; a
leftover `tinytex` line from before TinyTeX was required is ignored. Whether a tool is installed is
detected here on every run, never stored.

Unattended: with CAREER_LOG_UNATTENDED set (a scheduled run), a step that would install something or
ask the user says setup is needed instead, since no one is there to answer a question or a dialog.

Uncommitted Log changes: the Log's own files (LOG_PATHS) that git shows as changed or new are
listed, so a session settles what an earlier one left before it writes anything.

Setup for this Log: config.toml at the Log root (tools/config.py) says setup has run. Without it every
mode but setup stops and points to setup; with it, one `config <field>: <value>` line per Config field.

Entry size: an `entry over threshold: <path> <n> tokens` line for each entry tools/entries.py
estimates past its threshold (half of what one Read call returns), in every mode. It has no
next: line: the modes say what to do with an entry that size.

Exit 0 when the last line is `next: go on with the mode`, 1 when a `next: stop:` line ends the
mode now, 2 on a bad argument. -h or --help prints this text and exits 0. Standard library only.
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

HERE = os.path.dirname(os.path.abspath(__file__))
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
# How to run setup when it installs something: TinyTeX and Homebrew outlast a shell tool's usual
# time limit, and a step that needs an administrator opens the system's dialog for the user.
RUN_SETUP = ("as a background command, and wait for it to end (it can take 5-20 minutes). Before you"
             " start it, tell the user that on a Mac without Homebrew, or Windows without the Visual C++"
             " runtime, it opens the system's administrator dialog for them to answer at the machine"
             " (on Windows it may wait behind a flashing shield button on the taskbar), and that the"
             " password goes to the system, never to the chat")


class Context:
    def __init__(self, mode, root=ROOT, home=None):
        self.mode = mode
        self.root = root
        self.home = home or os.path.expanduser("~")
        self.machine_toml = os.path.join(self.home, ".career-log", "machine.toml")


def python_cmd():
    return "py -3" if WINDOWS else "python3"


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
                 " with poppler, for their user only (about 180 MB to download): `%s`. On yes run it %s;"
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
        machine.append("node")
    elif (not on_path and not WINDOWS and os.path.dirname(node) != local_bin(ctx.home)
          and not os.path.lexists(os.path.join(local_bin(ctx.home), "node"))):
        # nvm's Node with no link in ~/.local/bin: a setup from before the links makes them
        lines.append("node: ok but not on this shell's PATH (%s); setup links it into %s" % (node, local_bin(ctx.home)))
        machine.append("the links in %s" % local_bin(ctx.home))
    elif not on_path:
        lines.append("node: ok but not on this shell's PATH (%s)" % node)
        off_path.append(os.path.dirname(node))
    else:
        lines.append("node: ok (%s)" % version)
    for link in broken_links(ctx.home):
        lines.append("%s: broken link (%s was uninstalled)" % (link, os.readlink(link)))
        if "the links in %s" % local_bin(ctx.home) not in machine:
            machine.append("the links in %s" % local_bin(ctx.home))
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
        else:
            lines.append("browser libraries: missing (needs sudo)")
            command = ("sudo %s %s install-deps chromium" % (node, core) if core else
                       'sudo env PATH="$PATH" playwright-cli install-browser --with-deps chromium')
            machine.append("sudo:Chromium's system libraries:" + command)
    skills = [os.path.join(ctx.root, d, "skills", "playwright-cli", "SKILL.md") for d in (".claude", ".agents")]
    if any(os.path.isfile(s) for s in skills):
        lines.append("playwright-cli skill: ok (this checkout)")
    else:
        lines.append("playwright-cli skill: missing (this checkout)")
        checkout.append("skill")
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
    pdftotext = resume.poppler_bin("pdftotext")
    lines.append("pdftotext: ok (%s)" % pdftotext if pdftotext else "pdftotext: missing (poppler's, with -bbox-layout)")
    if not pdftotext and LINUX and shutil.which("apt-get"):
        machine.append("sudo:poppler:sudo apt-get install poppler-utils")
    elif not pdftotext and LINUX:
        machine.append("user:poppler:install poppler (pdfinfo, pdftotext, pdftoppm) with the package manager"
                       " you use, or set POPPLER_BIN to the bin folder of one you have")
    elif not pdftotext:   # Homebrew's on macOS (setup installs Homebrew when it is missing), winget's on Windows
        if poppler_needs_runtime():
            lines[-1] = "pdftotext: cannot start (poppler is installed; the Visual C++ runtime it needs is missing)"
        machine.append("poppler")
    return lines, machine, [], []


def poppler_needs_runtime():
    """winget's poppler is installed but cannot start: 0xC0000135, a DLL missing (the VC++ runtime)."""
    exe = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                                 "*Poppler*", "*", "Library", "bin", "pdftotext.exe"))
    if not exe:
        return False
    code, _ = run([exe[0], "-v"])
    return code is not None and code & 0xFFFFFFFF == 0xC0000135


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
            todo.append("%ssetup is needed on this machine: %s missing. This run is unattended"
                        " (CAREER_LOG_UNATTENDED), so it installs nothing and asks nothing: say so in the"
                        " run's result; for this run, %s." % (stop, ", ".join(missing), unavailable))
        elif choice is False:
            if hard:
                todo.append("stop: %s needs %s, which the user turned off on this machine. Tell them, and"
                            " that saying \"install %s\" turns it on: `%s`."
                            % (ctx.mode, tool, tool, setup_cmd(ctx.root, yes=[tool])))
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
            todo.append("%s is part of this machine's setup, and %s is missing: tell the user that setup"
                        " installs it now, with no question, then run `%s` %s; then run this check again."
                        % (tool, ", ".join(machine), setup_cmd(ctx.root), RUN_SETUP))
        elif machine:
            todo.append("the user chose %s on this machine and %s is missing: run `%s` %s; then run this"
                        " check again." % (tool, ", ".join(machine), setup_cmd(ctx.root, yes=[tool]), RUN_SETUP))
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
            for _, fact, question in asks:
                if UNATTENDED:
                    todo.append("%s%s This run is unattended (CAREER_LOG_UNATTENDED), so it asks nothing:"
                                " say so in the run's result; for this run, %s." % (stop, fact, unavailable))
                else:
                    todo.append("%s%s %s Do what they choose, then run this check again; until then, %s."
                                % (stop, fact, question, unavailable))
            if len(asks) < len(checkout):
                reload = path_reload(off_path) + "; " if off_path else ""
                # With a config whose browser is missing, the download waits for the user's answer
                install = "playwright-cli install --skills"
                if asks and WINDOWS:   # PowerShell keeps $env: set for the rest of the session
                    install = ("$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'; %s; Remove-Item"
                               " Env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD" % install)
                elif asks:
                    install = "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 " + install
                todo.append("from %s run `%s%s` (`--skills agents` for agents that read .agents/skills/),"
                            " with no question: it writes only files git ignores." % (ctx.root, reload, install))
        when = "now, for %s" % tool if ctx.mode == "setup" else WHEN[tool]
        nexts += ["next: %s, first: %s" % (when, t) for t in todo]
    return lines, nexts, False


# ---- Uncommitted Log changes ----

# The Log's own files (AGENTS.md › Changes); Engine files and the ignored inbox are not reported.
LOG_PATHS = ["entries", ":(exclude)entries/_template.md", "profile.md", "direction.md", "config.toml",
             "applications.md", "stories.md", "scan-sources.md", "README.md", "README.zh-TW.md", "outputs", "sources"]


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
    nexts = ["next: now, first: settle the files above as the *Uncommitted Log changes* bullet of"
             " SKILL.md, Commits, says."]
    return lines, nexts, False


# ---- Setup for this Log ----

def check_config(ctx):
    """Whether setup has run for this Log (config.toml exists and parses), and its Config values."""
    config_tool = tools_module("config")
    try:
        config = config_tool.load(ctx.root)
    except config_tool.ConfigError as e:
        return (["config: unreadable (%s)" % e],
                ["next: stop: show the user the error above, fix config.toml with them so that `%s -I"
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


# ---- Entry size ----

def check_size(ctx):
    """One line per entry past tools/entries.py's threshold; never stops the mode."""
    entries = tools_module("entries")
    try:
        return entries.over_threshold(entries.load(ctx.root)), [], False
    except (OSError, UnicodeDecodeError):
        return [], [], False


CHECKS = [check_python, check_uncommitted, check_config, check_size, check_tools]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):   # Log file names in any language, whatever the code page
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if "-h" in argv or "--help" in argv:
        print(__doc__.rstrip())
        return 0
    if len(argv) != 1 or argv[0] not in MODES:
        print("usage: %s -I tools/check.py <mode>; <mode> is one of %s" % (python_cmd(), ", ".join(MODES)))
        return 2
    if WINDOWS:   # a program that cannot load a DLL fails at once, with no dialog waiting for a click
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x8003)
    ctx = Context(argv[0])
    lines, nexts, stopped = [], [], False
    for check in CHECKS:
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
    print("next: go on with the mode")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
