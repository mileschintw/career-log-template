# Mode: audit

Before this mode's first step, run the **Start check** in [SKILL.md](../SKILL.md), once per session.

Report how ready the log is to produce outputs. Read-only: its only writes are the target builds in `.build/audit/` (*How to check outputs*). Everything else, `outputs/` included, it only reads, and its result is the report it prints.

Check and report, most important first:

1. **Story coverage.** The findings of `python3 -I <root>/tools/entries.py story-coverage <root>`, the same report the [stories](stories.md) mode starts with, then each question type whose only entries are thin.
2. **Gaps.** Per entry, the count of `GAP:` markers and the ones that block common outputs (attribution, results, likely questions).
3. **Provenance.** Numbers missing a source, measurement or caveat.
4. **Conflicts.** In entries and `profile.md › Conflicts`: `Open:` lines in those Conflicts sections, and any other line there that is not one `Settled:` line (a settled conflict still listing its versions, or an open one without its `Open:` marker).
5. **History in the files modes read** ([SKILL.md › Current truth only](../SKILL.md#rules-for-every-mode)):
   - **`## Past phrasings`:** each line holds the verbatim wording and one citation: its source, or, for a wording from an output, the form `write` prescribes, an application folder's path or `outputs/resumes/<target>.tex, YYYY-MM-DD` (the date is how git finds that version). Report a line with more than one citation, or with a usage note outside its citation (a date, or the company or posting the wording was sent to; names inside the verbatim wording are fine), and, in `consolidated` entries, more than two wordings of one claim for one angle.
   - **Every file modes read:** facts that cite an output instead of its source; notes about the record such as "superseded" or "moved to" (an earlier design or replaced component of the project itself is a fact, not one of these).
   - **`direction.md`:** replaced answers kept beside the current one, and event stories instead of the rule they teach (the sourced "why this path" account is neither).
   - **`stories.md › Application questions`:** a row with no scope (`shared`, `per-angle` or `per-company`), more than one pointer in a `shared` row, more than one pointer for one angle in a `per-angle` row, or any pointer in a `per-company` row.
6. **Outputs.** `applications.md` events with no next step; folders in `outputs/applications/` missing a provenance table (except one `interview` recorded, which has a `sent-version.md` instead), or a sent one missing its `resume.pdf`; a target in `outputs/resumes/` whose committed `.pdf` does not match its `.tex`, so a sent-version hash would point at a PDF built from something else (*How to check outputs* below gives the build and the compare); anything at the top of `outputs/` besides `applications/`, `resumes/` and `reports/`. Then check the saved text of every output an employer may still read against the entries' current rulings, as *How to check outputs* says. Report each hit with its file and line. A hit inside a `## Risks to handle in conversation` section is not a finding: that section names those claims on purpose, as warnings. A hit in a target or an unsent folder is fixed before it is sent; a folder is frozen once sent, so a hit there is reported as a risk to handle in conversation, never as an edit (ask the user which folders were sent when nothing in the log says).
7. **Staleness.** Entries marked ongoing whose `last_updated` is over two months old; entries whose `## Pending` lines go back more than two months (consolidate them); `README.md` rows that disagree with their entry: compare the row's title, period, tags and status with the entry's frontmatter and body (the status note too), not the status alone.

End with a short ranked to-do list (which entry to consolidate first and why). Fixing more than one entry from that list is a bulk change ([SKILL.md › Commits](../SKILL.md#rules-for-every-mode)).

Done when every entry in `README.md` has been checked against all seven points: every entry, every point, never a sample. Required reads: each entry file in full, frontmatter included (read the whole file, not its first lines or a grep), `README.md`, `stories.md`, `profile.md`, `direction.md`, and the outputs point 6 and *How to check outputs* name.

## How to check outputs

- **An application folder** (point 6): grep its `.tex` as **Saved text against current rulings** below says, and leave it unbuilt: a build copies the PDF next to the `.tex` (`tools/resume.py`), over the folder's `resume.pdf`, which in a sent folder is the one the employer received.
- **A target's PDF against its `.tex`** (point 6): copy the `.tex` to `.build/audit/<target>/`, build it there with `python3 tools/resume.py .build/audit/<target>/<target>.tex --out .build/audit/<target>/build --no-png` (its own scratch dir, so a `write` draft of the same target building at the same time can't collide with it), and compare the two with `python3 tools/resume.py .build/audit/<target>/<target>.pdf --same-text outputs/resumes/<target>.pdf` (it compares words only, since the bytes always differ and a toolchain update can move line breaks, and it runs the same in every shell).
- **Saved text against current rulings** (point 6): for each folder in `outputs/applications/` (its `resume.tex`, `answers.md` and `provenance.md`) and each target in `outputs/resumes/` (its `.md` and `.tex`), grep for the wrong side of every `Settled:` line and every claim a `## Conflicts` line marks unsupported, in every entry and in `profile.md`.
