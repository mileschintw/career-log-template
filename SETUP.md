# Setup per machine

The log can be cloned on macOS, Windows or Linux, on one machine or several. Run these steps once per clone, in order, from the repo root. Each step ends on a **check**: the step is done when the check holds, and a step whose check already holds is skipped. An agent runs the commands itself and reports each check's output; a human copies them the same way.

**Shells.** macOS: zsh or bash. Windows: PowerShell (Claude Code's PowerShell tool, or a PowerShell window). Git Bash also works on Windows, but it puts Git's own tools first on `PATH`, so PowerShell is the reference shell.

## 1. Prerequisites

| | macOS | Windows | Linux |
|---|---|---|---|
| Install | git, Python 3.9+, Homebrew | Git for Windows, Python 3.9+ (`winget install Python.Python.3.12`); winget is built in | git, Python 3.9+, curl, and poppler (`sudo apt-get install poppler-utils` or your distribution's package) |
| Check | `git --version` and `python3 --version` print versions | `git --version` and `py -3 --version` print versions | `git --version`, `python3 --version` and `pdftotext -v` print versions |

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

The skill lives in this repo and is linked into `~/.claude/skills/`, so edits stay versioned here.

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

**Check:** from a directory outside the repo, `git -C ~/.claude/skills/career-log rev-parse --show-toplevel` prints this repo's root, and the next Claude Code session lists the `career-log` skill. On Windows, `(Get-Item $HOME\.claude\skills\career-log).LinkType` is also `Junction`.

## 5. LaTeX toolchain

| macOS and Linux | Windows |
|---|---|
| `tools/setup.sh` | `powershell -ExecutionPolicy Bypass -File tools\setup.ps1` |

Both install, without sudo or admin and without touching `PATH`:
- TinyTeX into the user profile (`~/Library/TinyTeX` on macOS, `~/.TinyTeX` on Linux, `%APPDATA%\TinyTeX` on Windows);
- the packages in `tools/tex-packages.txt`;
- poppler (Homebrew; winget, scoop or choco; on Linux, step 1 installs it).

They then build a copy of the example resume (`skills/career-log/examples/resume.tex`) into `.build/setup-check/` as a smoke test. They are idempotent, so rerun them whenever a tool goes missing. `tools/setup.sh` run from Git Bash hands over to `setup.ps1`.

**Check:** the script exits 0 and its last line is `OK`. On a first Windows install, `tlmgr` prints one "path not found" line in the console's language; it is harmless.

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

**Check:** exit code 0, and the report contains these lines (macOS, 2026-10-15), with bottom slack within 1pt:

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
| Missing package | Add `\usepackage{lipsum}` to the preamble, then run first without and then with `--install-missing` | Without the flag: `BUILD FAILED`, a hint to rerun, and exit code 2. With it: an `installing lipsum` line, then `OK` |
| Broken source | Delete one `\end{itemize}` | `BUILD FAILED` with the `!` error lines; exit code 2 |

## How `tools/resume.py` finds its tools

The lookup order is:
1. `TINYTEX_BIN` / `POPPLER_BIN`;
2. the install locations from step 5 (TinyTeX in the user profile; poppler in the winget, scoop or choco folders);
3. `PATH`.

A `pdftotext` without `-bbox-layout` is skipped. That is xpdf's, and Git for Windows ships one. Another TeX on `PATH` (MacTeX, an older TeX Live) is therefore ignored once TinyTeX is installed. To use a different copy, set the variable to its `bin` folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `... not found. Run tools/setup...` or `pdftotext failed` | Rerun step 5 |
| Bottom slack off by more than 1pt | A different TeX built it. `python3 -c "import sys; sys.path.insert(0, 'tools'); import resume; print(resume.find_tex_bin('pdflatex'))"` (`py -3` on Windows) prints the one in use; it should sit under the TinyTeX folder from step 5. Otherwise point `TINYTEX_BIN` at TinyTeX's `bin` folder |
| `git -C ~/.claude/skills/career-log ...` answers "not a git repository" | Use the realpath fallback in [SKILL.md](skills/career-log/SKILL.md) |
| `tlmgr itself needs to be updated` | Run `tlmgr update --self` from TinyTeX's `bin` folder (step 5's scripts do this first), then rerun step 5 |
| A package is missing (`File '<x>.sty' not found`) | See [latex.md › Toolchain](skills/career-log/latex.md#toolchain) |

## Daily use

- **More than one machine.** Pull before starting and push when done; the skill pushes after every mode that writes. Generated files (`.build/`, page PNGs) are ignored, so nothing machine-specific reaches the repo.
- **Changing `tools/` or this file.** Push, then run steps 6 and 7 on every other platform you use. On Windows, run them in PowerShell and in Git Bash: Git Bash puts Git's own xpdf `pdftotext` first on `PATH`, which once broke only there.
