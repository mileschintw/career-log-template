# Setup per machine

The log can be cloned on macOS, Windows or Linux, on one machine or several. Run these steps once per clone, in order, from the repo root; step 7 only after an Engine change. Setting up the Log itself (Direction and Config, `config.toml`) happens once per Log, not per machine: the skill's setup mode, which the first request to a new Log starts. Each step ends on a **check**: the step is done when the check holds, and a step whose check already holds is skipped. An agent runs the commands itself and reports each check's output; a human copies them the same way.

**Shells.** macOS: zsh or bash. Windows: PowerShell (the agent's shell tool, or a PowerShell window). Git Bash also works on Windows, but it puts Git's own tools first on `PATH`, so PowerShell is the reference shell. On Windows, write `py -3` wherever a command says `python3`, in Git Bash too ([SKILL.md › Platforms](skills/career-log/SKILL.md#platforms)).

## 1. Prerequisites

| | macOS | Windows | Linux |
|---|---|---|---|
| Install | git (`git --version` offers Xcode's command-line tools when it is missing, which can take 10+ minutes) | Git for Windows; winget is built in | `sudo apt-get update && sudo apt-get install git curl xz-utils ca-certificates poppler-utils` (Debian/Ubuntu; other distributions: the same packages under their names) |
| Check | `git --version` and `curl --version` print versions | `git --version` and `winget --version` print versions | `git --version`, `curl --version`, `xz --version` and `pdftotext -v` print versions |

Python 3.11 or later is needed too; step 5 installs it, for your user only, when the one you have is older or missing.

## 2. Clone

Clone your own log repo. If you started from the Template, first create your copy on GitHub (**Use this template**, and make it **private**: a log holds personal records), then:

```
git clone https://github.com/<you>/<your-log-repo>.git
```

In an existing clone, `git pull --ff-only` instead.

**Check:** `git status` is clean, and `git ls-files --eol` shows `w/lf` for every text file except `tools/setup.ps1` (`w/crlf`); empty files show `w/none`. `.gitattributes` sets this; leave `core.autocrlf` at its default.

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

**Check:** from a directory outside the repo, `git -C <link path> rev-parse --show-toplevel` prints this repo's root (possibly with symlinks resolved, e.g. `/private/tmp/…` for `/tmp/…`), and the agent's next session lists the `career-log` skill. On Windows, `(Get-Item <link path>).LinkType` is also `Junction`.

## 5. Machine setup

Installs Python 3.11+ when `python3` (`py -3` on Windows) is older, TinyTeX with poppler, and the optional tool if the user wants it on this machine. Everything installs for this user only, except two steps that open the operating system's administrator dialog (item 2). On Linux, a step that needs sudo is printed for the user instead. The user's yes or no for the optional tool is kept in `~/.career-log/machine.toml` ([Machine setup](GLOSSARY.md)), so the skill never asks again on this machine.

| Tool | What it installs | Needed for |
|---|---|---|
| TinyTeX (required) | TinyTeX (`~/Library/TinyTeX` on macOS, `~/.TinyTeX` on Linux, `%APPDATA%\TinyTeX` on Windows) with the packages in `tools/tex-packages.txt`, and poppler (on Windows, winget's, with the Visual C++ runtime; on macOS, Homebrew's, installing Homebrew first when it is missing; on Linux, step 1 installs it). About 130 MB to download, 300–400 MB on disk; the largest package, `cm-super`, is about 63 MB, and tlmgr's time estimate for it is meaningless | `write`: building and checking resume PDFs |
| `playwright-cli` (optional) | Node 18+ when none is installed (nvm into `~/.nvm` on macOS and Linux; winget's per-user zip on Windows), [`playwright-cli`](https://github.com/microsoft/playwright-cli) in npm's global folder, its skill in this checkout (`.claude/skills/`, ignored by git), and, when Chrome and Edge are both missing (on macOS, one in `~/Applications` counts as missing: playwright-cli looks only in `/Applications`), Chromium in Playwright's cache in the home folder. About 400 MB; about 150 MB with Chrome or Edge, which playwright-cli uses instead | A Browser capture ([GLOSSARY.md](GLOSSARY.md)): a page a plain fetch cannot read in `fit`, `write`, `import`, `rank` or `interview` |

1. Ask the user whether they want `playwright-cli` on this machine, with what it installs and its size (the table above). TinyTeX needs no question. Skipping `playwright-cli` is fine: the skill offers it the first time a mode needs it.
2. **Administrator dialogs.** On a Mac without Homebrew, or Windows without the Visual C++ runtime poppler needs, the script opens the system's dialog: a password dialog to install Homebrew, or UAC. Before running it there, tell the user the dialog is coming, that they answer it at the machine (on Windows it may wait behind a flashing shield button on the taskbar), and that the password goes to the operating system, never to the chat.
3. Run the script with their answer, as a background command (Claude Code: the shell tool's background option), and wait for it to end: TinyTeX and Homebrew take 5–20 minutes, longer than a shell tool's usual time limit.

   | macOS and Linux | Windows (PowerShell) |
   |---|---|
   | `sh tools/setup.sh --yes playwright-cli` | `powershell -ExecutionPolicy Bypass -File tools\setup.ps1 -Yes playwright-cli` |

   On a no, write `--no playwright-cli` (`-No playwright-cli`) instead. With neither, the script installs Python, TinyTeX and the tools `machine.toml` already says yes to, and lists the tools not chosen yet. It is idempotent, so rerun it whenever a tool goes missing; `tools/setup.sh` run from Git Bash hands over to `setup.ps1`. On Windows, a run started inside a packaged app's container (the Claude desktop app's Git Bash, or a Windows PowerShell started from it) first prints `Inside a packaged app's container`, then shows the output of a second run outside it; wait for the script to exit as usual.
4. **Steps the script cannot do** are printed at its end, never run: a `needs sudo:` block (Linux: Chromium's system libraries, needed when there is no Chrome or Edge or when a playwright-cli config names Chromium, with a command that downloads no browser; and poppler) and a `not installed by this script:` block (a dialog the user declined, which the next run asks again; Linux without apt: poppler). Give each `needs sudo:` command to the user to run in their own terminal, where it asks for their password, and each `not installed by this script:` line for them to do; then rerun the script.
5. **New shells.** nvm, uv, Homebrew and the `PATH` entries the script adds reach shells started after it. On macOS and Linux the script also links nvm's `node`, `npm` and `playwright-cli` into `~/.local/bin` and puts that folder on the login shell's `PATH`, so a non-interactive shell (`bash -lc`, an agent's shell tool) finds them too. A shell that was already open (an agent's session) needs a line first: on Windows, the `$env:Path = …` line the script prints last, before `py -3` or anything it installed; on macOS and Linux, the `export PATH=…` line `tools/check.py` prints, and `~/.local/bin/python3` when it names one.

The TinyTeX install ends by building a copy of the example resume (`skills/career-log/examples/resume.tex`) into `.build/setup-check/` as a smoke test, and every run, except one given only `--no`, ends with the output of `tools/check.py setup`. With `CAREER_LOG_UNATTENDED=1` set (a scheduled or unattended run, [SKILL.md › Trigger check](skills/career-log/SKILL.md)), the script records any `--yes` or `--no`, installs nothing, opens no dialog and exits 3. A `machine.toml` from before TinyTeX was required may hold a `tinytex` line: the script removes it, and `tools/check.py` ignores it.

**Check:** the script exits 0, or 1 with only item 4's blocks left for the user; in the `tools/check.py setup` lines at its end, `python: ok` holds, and no `next:` line names TinyTeX or a tool the user chose, except to repeat one of those blocks. On Windows, `tlmgr update --self` may print one "path not found" line in the console's language, and on Windows and Linux `tlmgr` prints `not verified: gpg unavailable` lines; both are harmless.

## 6. Verify against the baseline

macOS and Linux:

```
mkdir -p .build/verify && cp skills/career-log/examples/resume.tex .build/verify/
python3 tools/resume.py .build/verify/resume.tex
```

Windows (PowerShell):

```
New-Item -ItemType Directory -Force .build\verify | Out-Null; Copy-Item skills\career-log\examples\resume.tex .build\verify\
py -3 tools/resume.py .build/verify/resume.tex
```

**Check:** exit code 0, and the report contains these lines (macOS, Linux and Windows, 2026-10-15), with bottom slack within 1pt:

```
note: p1: 6 bullets, text block x 36–576, bottom slack 321pt
note: dates use en dashes (–); some ATS imports (Workday) drop them
OK
```

Also check that `.build/verify/resume-1.png` shows one whole page. `.build/` is ignored by git, so the folder can stay.

## 7. Self-test after an Engine change

After a change to `tools/resume.py` or `tools/tex-packages.txt`, run the cases below on every platform you use (step 6 first). Each case edits its own copy of the example resume in `.build/selftest/`; delete the folder afterwards.

| Case | How to make it | Expected |
|---|---|---|
| Too long | Replace `removing a manual spreadsheet step` with that text plus ` that the finance team had run by hand every Friday afternoon for years before this consumer replaced it` | `FAIL: p1 bullet has 3 lines`; exit code 1 |
| Dangling line | Replace `across 50 injected node failures` with that text plus ` in testing` | `FAIL: p1 dangling last line (6% of width)`; exit code 1 |
| Missing package | Add `\usepackage{lipsum}` to the preamble, then run first without and then with `--install-missing`; then remove lipsum again (below) | Without the flag: `BUILD FAILED`, a hint to rerun, and exit code 2. With it: an `installing lipsum` line, then `OK` |
| Broken source | Delete one `\end{itemize}` | `BUILD FAILED` with the `!` error lines; exit code 2 |

The missing-package case can fail only while lipsum is not installed. If the run without the flag prints `OK`, an earlier run installed it and did not remove it: remove it, then run the case again. This removes it from the TeX that `tools/resume.py` uses:

```
python3 -c "import subprocess, sys; sys.path.insert(0, 'tools'); import resume; subprocess.run([resume.find_tex_bin('tlmgr'), 'remove', 'lipsum'], check=True)"
```

Whatever changed, also run the checks that match it (`py -3 -I` for `python3 -I` on Windows):
- any Engine change: `sh tools/export-template.sh <scratch>/export`, to a new folder. **Check:** the last line is `OK`.
- `tools/chat_export.py` or `tools/tests/`: `python3 -I tools/tests/test_chat_export.py`. **Check:** the last line is `OK`.
- `tools/check_save.py`, `tools/check_run.py` or their tests: `python3 -I tools/tests/test_check_save.py`, then `python3 -I tools/tests/test_check_run.py`, which imports it. **Check:** each last line is `OK`.
- `tools/check.py`, `tools/resume.py` or `tools/tests/test_check.py`: `python3 -I tools/tests/test_check.py`. **Check:** the last line is `OK`.
- `tools/entries.py` or `tools/tests/test_entries.py`: `python3 -I tools/tests/test_entries.py`, then `python3 -I tools/tests/test_check.py`, `python3 -I tools/tests/test_deny_coverage.py`, `python3 -I tools/tests/test_check_run.py` and `python3 -I tools/tests/test_check_save.py`, which import it. **Check:** each last line is `OK`.
- `tools/setup.sh` or `tools/setup.ps1`: run step 5 with the tools it changes, on each platform you can. **Check:** step 5's check.
- `tools/config.py`, `tools/config.default.toml` or `tools/tests/test_config.py`: `python3 -I tools/tests/test_config.py`, then `python3 -I tools/tests/test_check.py`, which reads Config through it. **Check:** each last line is `OK`.
- `tools/scan.py` or `tools/tests/test_scan.py`: `python3 -I tools/tests/test_scan.py`, then `python3 -I tools/tests/test_dashboard.py`, which imports it. **Check:** each last line is `OK`.
- `tools/dashboard.py` or `tools/tests/test_dashboard.py`: `python3 -I tools/tests/test_dashboard.py`. **Check:** the last line is `OK`.
- `skills/`, `tools/template/`, `SETUP.md`, `AGENTS.md`, `CLAUDE.md`, `GLOSSARY.md`, `entries/_template.md`, `docs/adr/`, `tools/skill_lint.py` or `tools/tests/test_skill_lint.py`: `python3 -I tools/tests/test_skill_lint.py`, then `python3 -I tools/skill_lint.py`. **Check:** the first's last line is `OK`, and the second prints `skill lint: ok`.

## How `tools/resume.py` finds its tools

The lookup order is:
1. `TINYTEX_BIN` / `POPPLER_BIN`;
2. the install locations from step 5 (TinyTeX in the user profile; poppler in the winget, scoop, choco or Homebrew folders);
3. `PATH`.

A `pdftotext` without `-bbox-layout` is skipped. That is xpdf's, and Git for Windows ships one. Another TeX on `PATH` (MacTeX, an older TeX Live) is therefore ignored once TinyTeX is installed; if `tools/resume.py` does build with a TeX outside TinyTeX, it first prints a `warning: building with …` line. To use a different copy, set the variable to its `bin` folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `... not found. Run tools/setup...` or `pdftotext failed` | Run `python3 -I tools/check.py write` (`py -3 -I` on Windows) and do its `next: when a step builds a PDF` lines |
| `warning: building with …, not TinyTeX`, or bottom slack off by more than 1pt | A different TeX built it (another TeX can build the baseline to the same slack, so the warning is the reliable sign). `python3 -c "import sys; sys.path.insert(0, 'tools'); import resume; print(resume.find_tex_bin('pdflatex'))"` (`py -3` on Windows) prints the one in use; it should sit under the TinyTeX folder from step 5. Otherwise point `TINYTEX_BIN` at TinyTeX's `bin` folder |
| `git -C <link path> ...` (step 4) answers "not a git repository" | Use the realpath fallback in [SKILL.md](skills/career-log/SKILL.md) |
| `tlmgr itself needs to be updated` | Run `tlmgr update --self` from TinyTeX's `bin` folder (step 5's script does this first), then rerun step 5 |
| A package is missing (`File '<x>.sty' not found`) | See [latex.md › Toolchain](skills/career-log/latex.md#toolchain) |

## Daily use

- **More than one machine.** Pull before starting and push when done; the skill pushes after every mode that writes. An import or another bulk change stays uncommitted until you answer yes ([SKILL.md › Commits](skills/career-log/SKILL.md#rules-for-every-mode)): answer before switching machines, or the other clone will not have it. Generated files (`.build/`, page PNGs) are ignored, so nothing machine-specific reaches the repo.
- **Changing `tools/` or this file.** Push, then run steps 6 and 7 on every other platform you use. On Windows, run them in PowerShell and in Git Bash: Git Bash puts Git's own xpdf `pdftotext` first on `PATH`, which once broke only there.
