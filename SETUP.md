# Setup per machine

The log can be cloned on macOS, Windows or Linux, on one machine or several. Run these steps once per clone, in order, from the repo root. Each step ends on a **check**: the step is done when the check holds, and a step whose check already holds is skipped. An agent runs the commands itself and reports each check's output; a human copies them the same way.

**Shells.** macOS: zsh or bash. Windows: PowerShell (the agent's shell tool, or a PowerShell window). Git Bash also works on Windows, but it puts Git's own tools first on `PATH`, so PowerShell is the reference shell. On Windows, write `py -3` wherever a command says `python3`, in Git Bash too: the `python3` alias that the Python install manager adds cannot see `%APPDATA%\TinyTeX`, so `tools/resume.py` would build with another TeX or find none.

## 1. Prerequisites

| | macOS | Windows | Linux |
|---|---|---|---|
| Install | git, Python 3.9+, [Homebrew](https://brew.sh) (its installer asks for your admin password and may install Xcode's command-line tools first, which can take 10+ minutes) | Git for Windows, Python 3.9+ (`winget install Python.Python.3.12`); winget is built in | `sudo apt-get update && sudo apt-get install git python3 curl xz-utils ca-certificates poppler-utils` (Debian/Ubuntu; other distributions: the same packages under their names) |
| Check | `git --version` and `python3 --version` print versions | `git --version` and `py -3 --version` print versions | `git --version`, `python3 --version`, `xz --version` and `pdftotext -v` print versions |

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

## 5. LaTeX toolchain

| macOS and Linux | Windows |
|---|---|
| `tools/setup.sh` | `powershell -ExecutionPolicy Bypass -File tools\setup.ps1` |

Both install, without sudo or admin and without touching `PATH`:
- TinyTeX into the user profile (`~/Library/TinyTeX` on macOS, `~/.TinyTeX` on Linux, `%APPDATA%\TinyTeX` on Windows);
- the packages in `tools/tex-packages.txt`;
- poppler (Homebrew; winget, scoop or choco; on Linux, step 1 installs it).

They download about 130 MB (the largest package, `cm-super`, is about 63 MB; tlmgr's time estimate for it is meaningless, ignore it), use 300–400 MB of disk, ask no questions, and take 1–3 minutes on a fast connection. They then build a copy of the example resume (`skills/career-log/examples/resume.tex`) into `.build/setup-check/` as a smoke test. They are idempotent, so rerun them whenever a tool goes missing. `tools/setup.sh` run from Git Bash hands over to `setup.ps1`.

**Check:** the script exits 0 and its last line is `OK`. On Windows, `tlmgr update --self` may print one "path not found" line in the console's language, and on Windows and Linux `tlmgr` prints `not verified: gpg unavailable` lines; both are harmless.

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

## 7. Self-test after changing `tools/`

Run on every platform you use after any change to `tools/` (step 6 first). Each case edits its own copy of the example resume in `.build/selftest/`; delete the folder afterwards.

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

## How `tools/resume.py` finds its tools

The lookup order is:
1. `TINYTEX_BIN` / `POPPLER_BIN`;
2. the install locations from step 5 (TinyTeX in the user profile; poppler in the winget, scoop or choco folders);
3. `PATH`.

A `pdftotext` without `-bbox-layout` is skipped. That is xpdf's, and Git for Windows ships one. Another TeX on `PATH` (MacTeX, an older TeX Live) is therefore ignored once TinyTeX is installed; if `tools/resume.py` does build with a TeX outside TinyTeX, it first prints a `warning: building with …` line. To use a different copy, set the variable to its `bin` folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `... not found. Run tools/setup...` or `pdftotext failed` | Rerun step 5 |
| `warning: building with …, not TinyTeX`, or bottom slack off by more than 1pt | A different TeX built it (another TeX can build the baseline to the same slack, so the warning is the reliable sign). `python3 -c "import sys; sys.path.insert(0, 'tools'); import resume; print(resume.find_tex_bin('pdflatex'))"` (`py -3` on Windows) prints the one in use; it should sit under the TinyTeX folder from step 5. Otherwise point `TINYTEX_BIN` at TinyTeX's `bin` folder |
| `git -C <link path> ...` (step 4) answers "not a git repository" | Use the realpath fallback in [SKILL.md](skills/career-log/SKILL.md) |
| `tlmgr itself needs to be updated` | Run `tlmgr update --self` from TinyTeX's `bin` folder (step 5's scripts do this first), then rerun step 5 |
| A package is missing (`File '<x>.sty' not found`) | See [latex.md › Toolchain](skills/career-log/latex.md#toolchain) |

## Daily use

- **More than one machine.** Pull before starting and push when done; the skill pushes after every mode that writes. If you turned on *Bulk changes as pull requests* in `direction.md › Repo workflow`, an import or another bulk change sits on a `data/` branch until you merge its pull request ([SKILL.md › Commits](skills/career-log/SKILL.md)): merge or close it before switching machines, or the other clone will not have it. Generated files (`.build/`, page PNGs) are ignored, so nothing machine-specific reaches the repo.
- **Changing `tools/` or this file.** Push, then run steps 6 and 7 on every other platform you use. On Windows, run them in PowerShell and in Git Bash: Git Bash puts Git's own xpdf `pdftotext` first on `PATH`, which once broke only there.
