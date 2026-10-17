# LaTeX resumes

How to edit, build and check a resume `.tex` locally. Read before touching any `.tex`; `apply` and `write` point here.

## Toolchain

- **Engine: pdfLaTeX**, from TinyTeX. The templates call `\pdfgentounicode`, a pdfTeX primitive, so XeLaTeX, LuaLaTeX and Tectonic cannot build them. Overleaf's default (pdfLaTeX) matches.
- **Install:** [SETUP.md](../../SETUP.md) step 5 (TinyTeX, the packages in `tools/tex-packages.txt`, poppler), checked by step 6. TinyTeX is not put on `PATH`; `tools/resume.py` finds it itself, in the order SETUP.md › How `tools/resume.py` finds its tools gives.
- **New package:** when a build stops on `File '<x>.sty' not found`, rerun with `--install-missing`, then add the package name to `tools/tex-packages.txt` so the next machine gets it.

## The loop

```bash
python3 tools/resume.py <file.tex>
```

(`py -3 tools/resume.py` on Windows; see SKILL.md › Platforms.) It compiles into `.build/<stem>/` (ignored), copies the PDF next to the `.tex`, then checks:

| Check | Fails when |
|---|---|
| Pages | more than 1 |
| Bullet length | a bullet wraps past 2 lines |
| Dangling line | a wrapped bullet's last line fills under 25% of the width |
| Overfull box | the log reports a line over 1pt too wide |
| Text layer | no email address, or `(cid:…)` / `�` garbage |

It also prints the bottom slack and writes `<stem>-1.png`. Read the PNG after every build that passes: the checks cannot see a heading stranded at the bottom, an uneven gap, or a bold run that reads wrong. Exit 0 means the checks pass, 1 a check failed, 2 the build failed. `--check <file.pdf>` checks a PDF without building (for a PDF built elsewhere).

The checks are calibrated on the r/EngineeringResumes template. The older sb2nov template builds but nests bullets, so its bullet counts are not meaningful.

Build from a copy, never in `sources/resumes/` or `outputs/`: originals in `sources/resumes/` are never edited, a build writes a PDF and a PNG beside the source, and a rebuilt PDF differs byte for byte from the committed one. Draft in `.build/drafts/<name>/` (ignored), so iteration never shows up in `git status`: copy the starting `.tex` there (`<name>` is the target for a `write` resume, the application folder's name for `apply`), edit and build it there, and copy the `.tex` and its built `.pdf` into `outputs/` only when the user approves.

## Editing the r/EngineeringResumes template

A first resume starts from [assets/resume-blank.tex](assets/resume-blank.tex); replace every `<...>` placeholder with facts from the entries.

- One bullet is one `\item` inside the entry's `itemize`. Bold sparingly: r/ER advises against bolding keywords inside bullets ([writing.md](writing.md)), so bold with `\textbf{}` only where the user's approved versions already do.
- Escape `& % $ # _ { } ~ ^ \` in text: `C\#`, `\&`, `\%`. Use `--` for date ranges, as every version does; the checker notes en dashes because some ATS imports drop them, which is a known trade-off, not a failure.
- Spacing between blocks uses the `\vspace{…}` values already in the file; copy a neighbouring entry's pattern instead of inventing values.

## Fixing a failed check

Fix the words before the layout. In order:

1. **Bullet over two lines, or a dangling last line:** rewrite the bullet. Cut a clause, swap a long phrase for a shorter one the entry supports, or add a few words to fill a dangling line. Every rewrite still passes `write.md` step 5.
2. **Over one page:** cut by relevance to the target, not by section: the weakest bullet for this posting goes first, wherever it sits. `direction.md › What to emphasise` decides what is weak.
3. **Only then layout:** a `\vspace` nudge copied from the existing pattern. Margins, font size, font and the `itemsep`/`topsep` settings stay as they are; they are the template's identity across versions.

Done when `tools/resume.py` exits 0 and the PNG reads cleanly.

The content rules for bullets and the skills section are in [writing.md](writing.md).
