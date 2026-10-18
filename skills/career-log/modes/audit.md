# Mode: audit

Report how ready the log is to produce outputs. Read-only: it changes nothing except the report it prints.

Check and report, most important first:

1. **Story coverage.** Each question type in `stories.md` with no entry behind it, or only a thin one.
2. **Gaps.** Per entry, the count of `GAP:` markers and the ones that block common outputs (attribution, results, likely questions).
3. **Provenance.** Numbers missing a source, measurement or caveat.
4. **Conflicts.** In entries and `profile.md › Conflicts`: `Open:` lines in those Conflicts sections, and any other line there that is not one `Settled:` line (a settled conflict still listing its versions, or an open one without its `Open:` marker).
5. **History in the files modes read** ([SKILL.md › Current truth only](../SKILL.md#rules-for-every-mode)): `## Past phrasings` lines with more than one citation, or a usage note outside their single citation (a date, or the company or posting the wording was sent to; names inside the verbatim wording are fine), and, in `consolidated` entries, more than two wordings of one claim for one angle; facts that cite an output instead of its source; notes about the record such as "superseded" or "moved to" (an earlier design or replaced component of the project itself is a fact, not one of these); in `direction.md`, replaced answers kept beside the current one, and event stories instead of the rule they teach (the sourced "why this path" account is neither); in `stories.md › Application questions`, a row with no scope (`shared`, `per-angle` or `per-company`), more than one pointer in a `shared` row, more than one pointer for one angle in a `per-angle` row, or any pointer in a `per-company` row.
6. **Outputs.** `applications.md` events with no next step; folders in `outputs/applications/` missing a provenance table (except one `interview` recorded, which has a `sent-version.md` instead), or a sent one missing its `resume.pdf`; a target in `outputs/resumes/` whose committed `.pdf` does not match its `.tex`, so a sent-version hash would point at a PDF built from something else: copy the `.tex` to `.build/audit/<target>/`, build it there with `python3 tools/resume.py .build/audit/<target>/<target>.tex --out .build/audit/<target>/build --no-png` (its own scratch dir, so a `write` draft of the same target building at the same time can't collide with it), and compare the two with `python3 tools/resume.py .build/audit/<target>/<target>.pdf --same-text outputs/resumes/<target>.pdf` (it compares words only, since the bytes always differ and a toolchain update can move line breaks, and it runs the same in every shell); anything at the top of `outputs/` besides `applications/`, `resumes/` and `reports/`.
7. **Staleness.** Entries marked ongoing whose `last_updated` is over two months old; entries whose `## Pending` lines go back more than two months (consolidate them); `README.md` rows that disagree with their entry's frontmatter.

End with a short ranked to-do list (which entry to consolidate first and why). Fixing more than one entry from that list is a bulk change ([SKILL.md › Commits](../SKILL.md)).

Done when every entry in `README.md` has been checked against all seven points.
