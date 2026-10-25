# LaTeX resumes

How to edit, build and check a resume `.tex` locally. Read before touching any `.tex`; `write` points here.

## Toolchain

- **Engine: pdfLaTeX**, from TinyTeX. The templates call `\pdfgentounicode`, a pdfTeX primitive, so XeLaTeX, LuaLaTeX and Tectonic cannot build them. Overleaf's default (pdfLaTeX) matches.
- **Install:** through the trigger check ([SKILL.md](SKILL.md)), whose `next:` lines run [SETUP.md](../../SETUP.md) step 5's script for TinyTeX, the packages in `tools/tex-packages.txt` and poppler; step 6 checks the result. TinyTeX is not put on `PATH`; `tools/resume.py` finds it itself, in the order SETUP.md › How `tools/resume.py` finds its tools gives.
- **New package:** when a build stops on `File '<x>.sty' not found`, rerun with `--install-missing`, and add each package its `add to tools/tex-packages.txt:` lines name to that file, so the next machine gets it (an Engine change: [AGENTS.md › Changes](../../AGENTS.md#changes)).

## The loop

```bash
python3 -I <root>/tools/resume.py --root <root> <file.tex>
```

(`py -3 -I` on Windows; see SKILL.md › Platforms.) It scans the source, builds in a scratch folder under `.build/resume/` (ignored), copies the PDF next to the `.tex`, and checks it; `--help` lists every check. Fix each `FAIL:` line as *Fixing a failed check* below says. After every build that passes, read each PNG its `note: png:` line names: the checks cannot see a heading stranded at the bottom, an uneven gap, or a bold run that reads wrong. `--check <file.pdf>` checks a PDF without building (for a PDF built elsewhere).

The checks are calibrated on the r/EngineeringResumes template. The older sb2nov template builds but nests bullets, so its bullet counts are not meaningful.

Build from a copy, never in `sources/resumes/` or `outputs/`: originals in `sources/resumes/` are never edited, a build writes a PDF and a PNG beside the source, and a rebuilt PDF differs byte for byte from the committed one. Draft in `.build/drafts/<name>/` (ignored), so iteration never shows up in `git status`: copy the starting `.tex` there with `tools/application.py start` (`<name>` the one its `name` prints), edit and build it there, and copy the `.tex` and its built `.pdf` into `outputs/` with `tools/application.py save` only when the user approves ([write.md](modes/write.md) steps 6 and 10).

## Editing the r/EngineeringResumes template

A first resume starts from [assets/resume-blank.tex](assets/resume-blank.tex); replace every `<...>` placeholder with facts from the entries (the build fails on each one left).

- One bullet is one `\item` inside the entry's `itemize`. Bold is `\textbf{}`, used only as [writing.md](writing.md) › Format allows (where the user's approved versions already bold).
- Escape `& % $ # _ { } ~ ^ \` in text (`C\#`, `\&`, `\%`), and write `--` for a date range, never a Unicode `–`: the build's `source line` lines name each one missed. The checker's note on en dashes in the PDF (some ATS imports drop them) is a known trade-off, not a failure.
- Spacing between blocks uses the `\vspace{…}` values already in the file; copy a neighbouring entry's pattern instead of inventing values.

## Fixing a failed check

Fix the words before the layout. In order:

1. **Bullet over two lines, or a dangling last line:** rewrite the bullet as [writing.md](writing.md) › Format › *A long bullet* says. Every rewrite still passes [write.md](modes/write.md) › *Check the draft claim by claim*.
2. **Over the page limit:** cut as [writing.md](writing.md) › Format › *Over the page limit* says.
3. **A Skills line that wraps:** drop its weakest tool ([writing.md](writing.md) › Skills section › *Fill each line by relevance*). **A Skills line with no `\textbf{<label>}` the check can read:** start that line with its bold label (a mark such as `\checkmark\ ` may come before it); dropping tools does not clear it. Treat a `line wraps` fail the same way when the row it names starts its own source line or follows a `\\` or `\newline`: the check reads such a row as a wrap when the row above nearly fills the width. **A `FAIL: source line`:** fix it as *Editing* above says. **An overfull box:** rewrite the words on that source line. **No email address:** put the one in `profile.md` back in the header. **`email: GAP (needs you)`,** or no email in `profile.md`: [write.md](modes/write.md) step 6 › *A header field `profile.md` lacks*. **Garbage glyphs:** keep or restore the template's `\input{glyphtounicode}` and `\pdfgentounicode=1` lines, and replace the character the text layer shows as `(cid:…)` or `�`.
4. **Only then layout:** a `\vspace` nudge copied from the existing pattern, built with `--same-layout <the .tex the draft started from>`, which fails on any other layout change: margins, font size, font and the `itemsep`/`topsep` settings are the template's identity across versions. A `layout` line: put back the start version's line (`is gone`), or take out the one the draft added (`is not in`). A package a new command needs (`amssymb` for `\checkmark`) goes on its own `\usepackage{<package>}` line, leaving the start version's lines as they are. That line passes, unless the package changes the layout or the font (`geometry`, `parskip`, `setspace`, a font), which the tool judges: an `is not in` line for that `\usepackage` means take it out, along with whatever the draft uses from that package, and never install it. Only when no such line names it and the build stops on its missing `.sty`, install it as *Toolchain* › New package says.

Done when `tools/resume.py` exits 0 and every PNG reads cleanly.

The content rules for bullets and the skills section are in [writing.md](writing.md).
