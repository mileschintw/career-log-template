# Mode: audit

Report how ready the log is to produce outputs. Read-only: it changes nothing except the report it prints.

Check and report, most important first:

1. **Story coverage.** Each question type in `stories.md` with no entry behind it, or only a thin one.
2. **Gaps.** Per entry, the count of `GAP:` markers and the ones that block common outputs (attribution, results, likely questions).
3. **Provenance.** Numbers missing a source, measurement or caveat.
4. **Conflicts.** Unresolved `## Conflicts` sections.
5. **Outputs.** `applications.md` events with no next step; folders in `outputs/applications/` missing a provenance table (except one `interview` recorded, which has a `sent-version.md` instead), or a sent one missing its `resume.pdf`; a target in `outputs/resumes/` whose committed `.pdf` does not match its `.tex`, so a sent-version hash would point at a PDF built from something else: copy the `.tex` to `.build/audit/<target>/`, build it there with `python3 tools/resume.py .build/audit/<target>/<target>.tex --out .build/audit/<target>/build --no-png` (its own scratch dir, so a `write` draft of the same target building at the same time can't collide with it), and compare the two with `python3 tools/resume.py .build/audit/<target>/<target>.pdf --same-text outputs/resumes/<target>.pdf` (it compares words only, since the bytes always differ and a toolchain update can move line breaks, and it runs the same in every shell); anything at the top of `outputs/` besides `applications/`, `resumes/` and `reports/`.
6. **Staleness.** Entries marked ongoing whose last log line is over two months old; `README.md` rows that disagree with their entry's frontmatter.

End with a short ranked to-do list (which entry to consolidate first and why). Fixing more than one entry from that list is a bulk change ([SKILL.md › Commits](../SKILL.md)).

Done when every entry in `README.md` has been checked against all six points.
