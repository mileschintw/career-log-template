# Setup per machine

The log can be cloned on macOS, Windows or Linux, on one machine or several. Run these steps once per clone, in order, from the repo root; step 7 only after an Engine change. Setting up the Log itself (Direction and Config, `config.toml`) happens once per Log, not per machine: the skill's setup mode, which the first request to a new Log starts. Each step ends on a **check**: the step is done when the check holds, and a step whose check already holds is skipped. An agent runs the commands itself and reports each check's output; a human copies them the same way.

**Shells.** macOS: zsh or bash. Windows: PowerShell (the agent's shell tool, or a PowerShell window). Git Bash also works on Windows, but it puts Git's own tools first on `PATH`, so PowerShell is the reference shell. On Windows, write `py -3` wherever a command says `python3`, in Git Bash too ([SKILL.md › Platforms](skills/career-log/SKILL.md#platforms)).

## 1. Prerequisites

| | macOS | Windows | Linux |
|---|---|---|---|
| Install | git (`git --version` offers Xcode's command-line tools when it is missing, which can take 10+ minutes) | Git for Windows; winget is built in | `sudo apt-get update && sudo apt-get install git curl xz-utils ca-certificates` (Debian/Ubuntu; other distributions: the same packages under their names) |
| Check | `git --version` and `curl --version` print versions | `git --version` and `winget --version` print versions | `git --version`, `curl --version` and `xz --version` print versions |

Python 3.11 or later is needed too; step 5 installs it, for your user only, when the one you have is older or missing.

## 2. Clone

Clone your own log repo. If you started from the Template, first create your copy on GitHub (**Use this template**, and make it **private**: a log holds personal records), then:

```
git clone https://github.com/<you>/<your-log-repo>.git
```

In an existing clone, `git pull --ff-only` instead.

**Check:** `git status` is clean, and `git ls-files --eol` shows `w/lf` for every text file except `tools/setup.ps1` (`w/crlf`); empty files and files with no line end show `w/none`, and binary files `w/-text`. `.gitattributes` sets this; leave `core.autocrlf` at its default.

## 3. Git identity (this repo only)

```
git config --local user.name "<your name>"
git config --local user.email <your email>
```

**Check:** `git config --local user.email` prints your email. The machine-wide identity may belong to someone else, so the skill refuses to commit until the repo-local one is set.

## 4. Skill link

The skill lives in this repo. Link it into the folder your agent reads skills from, so edits stay versioned here and the skill works from any project. Do the row for each agent you use. Working inside this repo needs no link: `AGENTS.md` points the agent at the skill.

| Agent | Link path | Also read by |
|---|---|---|
| Claude Code | `~/.claude/skills/career-log` | Cursor |
| Codex | `~/.agents/skills/career-log` | Cursor |
| Antigravity App and IDE | `~/.gemini/config/skills/career-log` | |
| Antigravity CLI | `~/.gemini/antigravity-cli/skills/career-log` | |

Only Claude Code is tested, on macOS, Windows and Linux. The other rows follow each vendor's documented skill folder and are not tested on Windows.

### Claude Code

macOS and Linux:

```
mkdir -p ~/.claude/skills
ln -s "$(git rev-parse --show-toplevel)/skills/career-log" ~/.claude/skills/career-log
```

Windows (PowerShell; a directory junction needs no admin rights or Developer Mode, while `ln -s` in Git Bash copies the folder instead):

```
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME\.claude\skills\career-log" -Target "$(git rev-parse --show-toplevel)/skills/career-log"
```

### Codex (not tested on Windows)

macOS and Linux:

```
mkdir -p ~/.agents/skills
ln -s "$(git rev-parse --show-toplevel)/skills/career-log" ~/.agents/skills/career-log
```

Windows (PowerShell):

```
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME\.agents\skills\career-log" -Target "$(git rev-parse --show-toplevel)/skills/career-log"
```

### Antigravity (not tested on Windows)

App and IDE, macOS and Linux:

```
mkdir -p ~/.gemini/config/skills
ln -s "$(git rev-parse --show-toplevel)/skills/career-log" ~/.gemini/config/skills/career-log
```

CLI, macOS and Linux:

```
mkdir -p ~/.gemini/antigravity-cli/skills
ln -s "$(git rev-parse --show-toplevel)/skills/career-log" ~/.gemini/antigravity-cli/skills/career-log
```

Windows (PowerShell), App and IDE, then CLI:

```
New-Item -ItemType Directory -Force "$HOME\.gemini\config\skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME\.gemini\config\skills\career-log" -Target "$(git rev-parse --show-toplevel)/skills/career-log"
New-Item -ItemType Directory -Force "$HOME\.gemini\antigravity-cli\skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME\.gemini\antigravity-cli\skills\career-log" -Target "$(git rev-parse --show-toplevel)/skills/career-log"
```

**Check:** from a directory outside the repo, `git -C <link path> rev-parse --show-toplevel` prints this repo's root (possibly with symlinks resolved, e.g. `/private/tmp/…` for `/tmp/…`), and the agent's next session lists the `career-log` skill. With Python 3 on the machine, `python3 -I <link path>/start.py` (`py -3 -I` on Windows) prints `root: ` and the same folder (its slashes may differ). On Windows, `(Get-Item <link path>).LinkType` is also `Junction`. Step 5's check repeats this as its `skill link <agent>:` lines.

## 5. Machine setup

Installs Python 3.11+ when `python3` (`py -3` on Windows) is older, TinyTeX with poppler, and the optional tool if the user wants it on this machine. Everything installs for this user only, with no administrator dialog and no password. On Linux, a step that needs sudo (Chromium's system libraries, for the optional tool) is printed for the user instead. The user's yes or no for the optional tool is kept in `~/.career-log/machine.toml` ([Machine setup](GLOSSARY.md)), so the skill never asks again on this machine.

| Tool | What it installs | Needed for |
|---|---|---|
| TinyTeX (required) | TinyTeX (`~/Library/TinyTeX` on macOS, `~/.TinyTeX` on Linux, `%APPDATA%\TinyTeX` on Windows) with the packages in `tools/tex-packages.txt`, and poppler: a poppler the user already has (found as *How `tools/resume.py` finds its tools* below says) is used as it is; otherwise the script downloads micromamba (one program, into `~/.career-log/micromamba`), which installs conda-forge's poppler into `~/.career-log/poppler`, and a rerun of the script updates it there; once the script finds the user's own poppler and no working poppler of its own, it removes micromamba and what is left of `~/.career-log/poppler`. About 130 MB to download, 300–400 MB on disk, plus, when the user has no poppler, about 70 MB to download for micromamba and poppler, about 250 MB on disk; the largest package, `cm-super`, is about 63 MB, and tlmgr's time estimate for it is meaningless | Building and checking resume PDFs |
| `playwright-cli` (optional) | Node 18+ when none is installed (nvm into `~/.nvm` on macOS and Linux; winget's per-user zip on Windows), [`playwright-cli`](https://github.com/microsoft/playwright-cli) in npm's global folder, its skill in this checkout (`.claude/skills/`, ignored by git), and, when Chrome and Edge are both missing (on macOS, one in `~/Applications` counts as missing: playwright-cli looks only in `/Applications`), Chromium in Playwright's cache in the home folder. About 400 MB; about 150 MB with Chrome or Edge, which playwright-cli uses instead | A Browser capture ([GLOSSARY.md](GLOSSARY.md)): a page a plain fetch cannot read |

1. Ask the user whether they want `playwright-cli` on this machine, with what it installs and its size (the table above). TinyTeX needs no question. Skipping `playwright-cli` is fine: the skill offers it the first time a mode needs it.
2. Run the script with their answer, as a background command (Claude Code: the shell tool's background option), and wait for it to end: TinyTeX takes 5–20 minutes, longer than a shell tool's usual time limit.

   | macOS and Linux | Windows (PowerShell) |
   |---|---|
   | `sh tools/setup.sh --yes playwright-cli` | `powershell -ExecutionPolicy Bypass -File tools\setup.ps1 -Yes playwright-cli` |

   On a no, first run it with `--no playwright-cli` (`-No playwright-cli`), which only records the answer and installs nothing, then run it again with neither. With neither, the script installs Python, TinyTeX and the tools `machine.toml` already says yes to, and lists the tools not chosen yet. It is idempotent, so rerun it whenever a tool goes missing; `tools/setup.sh` run from Git Bash hands over to `setup.ps1`. On Windows, a run started inside a packaged app's container (the Claude desktop app's Git Bash, or a Windows PowerShell started from it) first prints `Inside a packaged app's container`, then shows the output of a second run outside it; wait for the script to exit as usual.
3. **Steps the script cannot do** are printed at its end, never run: a `needs sudo:` block (Linux: Chromium's system libraries, needed when there is no Chrome or Edge or when a playwright-cli config names Chromium, with a command that downloads no browser) and a `not installed by this script:` block (poppler, when micromamba could not download or install it: offline, or behind a proxy that `HTTPS_PROXY` must name; Chromium's system libraries, when no playwright-core sits beside playwright-cli to install them). Give each `needs sudo:` command to the user to run in their own terminal, where it asks for their password, and each `not installed by this script:` line for them to do; then rerun the script.
4. **New shells.** nvm, uv and the `PATH` entries the script adds reach shells started after it. On macOS and Linux the script also links nvm's `node`, `npm` and `playwright-cli` into `~/.local/bin` and puts that folder on the login shell's `PATH`, so a non-interactive shell (`bash -lc`, an agent's shell tool) finds them too. A shell that was already open (an agent's session) needs a line first: on Windows, the `$env:Path = …` line the script prints last, before `py -3` or anything it installed; on macOS and Linux, the `export PATH=…` line `tools/check.py` prints, and `~/.local/bin/python3` when it names one.

The TinyTeX install ends by building a copy of the example resume (`skills/career-log/examples/resume.tex`) into `.build/setup-check/` as a smoke test, and every run, except one given only `--no`, ends with the output of `tools/check.py setup`. With `CAREER_LOG_UNATTENDED=1` set (a scheduled or unattended run, [SKILL.md › Trigger check](skills/career-log/SKILL.md)), the script records any `--yes` or `--no`, installs nothing and exits 3. A `machine.toml` from before TinyTeX was required may hold a `tinytex` line: the script removes it, and `tools/check.py` ignores it.

**Check:** the script exits 0, or 1 with only item 3's blocks left for the user; in the `tools/check.py setup` lines at its end (a run that printed none installed nothing), `python: ok` and `eol: ok` hold (step 2's check), the `skill link <agent>:` line whose path is a link you made in step 4 says `ok` (for any other state, redo step 4 for it), the last line is `next: go on with the mode` unless a `next: now` line asks to run the check again (as item 3's blocks do), and no `next:` line names TinyTeX or a tool the user chose, except to repeat one of those blocks. On Windows, `tlmgr update --self` may print one "path not found" line in the console's language, and on Windows and Linux `tlmgr` prints `not verified: gpg unavailable` lines; both are harmless.

## 6. Verify against the baseline

```
python3 -I tools/resume.py --baseline
```

(`py -3 -I` on Windows.) It builds a copy of the example resume in `.build/verify/` (ignored by git, so the folder can stay), checks it, and compares its page with the one expected on macOS, Linux and Windows.

**Check:** the last line is `baseline: OK`, and `.build/verify/resume-1.png` shows one whole page.

## 7. Self-test after an Engine change

Run `python3 -I tools/checks_for.py <base>` (`py -3 -I` on Windows), `<base>` being the commit the change started from (`origin/<default>` for a branch), then every `run:` and `do:` line it prints, `<scratch>` being a new folder in your scratchpad, and fix what each `warn:` line names. Commit first: the export reads commits only. After a fix that changes files, commit and run it again, with a new `<scratch>`. Its `engine:`, `guard:` and `coordination:` lines say how each path lands ([AGENTS.md › Changes](AGENTS.md#changes), [engine-changes.md](skills/career-log/engine-changes.md)). **Check:** each `run:` line's `check:` line holds, each `do:` step is done, and each `warn:` is fixed (one for a change only to Entries-table rows needs no fix); after `run: none`, nothing is left.

Optional, for a change to how `tools/resume.py` installs packages: run `tools/tests/test_resume.py` with `RESUME_TEST_INSTALL=1` set (PowerShell: `$env:RESUME_TEST_INSTALL='1'`), and its last line is `OK`; it installs lipsum with tlmgr into the TeX `tools/resume.py` uses and removes it afterwards. When it skips because lipsum is installed already, remove it with `<tlmgr> remove lipsum`, `<tlmgr>` being the one beside the `pdflatex` *How `tools/resume.py` finds its tools* below finds, and run it again.

## How `tools/resume.py` finds its tools

The lookup order is:
1. `TINYTEX_BIN` / `POPPLER_BIN`;
2. the usual install locations (TinyTeX in the user profile, where step 5 puts it; for poppler, the winget, scoop, choco or Homebrew folders of one the user installed);
3. `PATH`;
4. for poppler, setup's own environment in `~/.career-log/poppler`, so a poppler the user has always comes first.

`pdfinfo` and `pdftoppm` are taken from the folder of the `pdftotext` found. A `pdftotext` without `-bbox-layout` (xpdf's; Git for Windows ships one), or with no `pdftoppm` beside it, is skipped. Another TeX on `PATH` (MacTeX, an older TeX Live) is therefore ignored once TinyTeX is installed; if `tools/resume.py` does build with a TeX outside TinyTeX, it first prints a `warning: building with …` line. To use a different copy, set the variable to its `bin` folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `... not found. Run tools/setup...` or `pdftotext failed` | Run `python3 -I tools/check.py write` (`py -3 -I` on Windows) and do its `next: when a step builds a PDF` lines |
| `warning: building with …, not TinyTeX`, or bottom slack off by more than 1pt | A different TeX built it (another TeX can build the baseline to the same slack, so the warning is the reliable sign). `python3 -c "import sys; sys.path.insert(0, 'tools'); import resume; print(resume.find_tex_bin('pdflatex'))"` (`py -3` on Windows) prints the one in use; it should sit under the TinyTeX folder from step 5. Otherwise point `TINYTEX_BIN` at TinyTeX's `bin` folder |
| `git -C <link path> ...` (step 4) answers "not a git repository" | This git does not follow the junction (Git 2.38 does). The skill finds its root without git: `python3 -I <link path>/start.py` (`py -3 -I` on Windows) prints `root: ` and this repo's root |
| `tlmgr itself needs to be updated` | Run `tlmgr update --self` from TinyTeX's `bin` folder (step 5's script does this first), then rerun step 5 |
| A package is missing (`File '<x>.sty' not found`) | See [latex.md › Toolchain](skills/career-log/latex.md#toolchain) |

## Daily use

- **More than one machine.** Pull before starting and push when done; the skill pushes after every mode that writes. An import or another bulk change stays uncommitted until you answer yes ([SKILL.md › Commits](skills/career-log/SKILL.md#rules-for-every-mode)): answer before switching machines, or the other clone will not have it. Generated files (`.build/`, page PNGs) are ignored, so nothing machine-specific reaches the repo.
- **Changing `tools/` or this file.** Push, then run steps 6 and 7 on every other platform you use. On Windows, run them in PowerShell and in Git Bash: Git Bash puts Git's own xpdf `pdftotext` first on `PATH`, which once broke only there.
