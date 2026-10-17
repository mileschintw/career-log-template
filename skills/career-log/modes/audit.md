# Mode: audit

Report how ready the log is to produce outputs. Read-only: it changes nothing except the report it prints.

Check and report, most important first:

1. **Story coverage.** Each question type in `stories.md` with no entry behind it, or only a thin one.
2. **Gaps.** Per entry, the count of `GAP:` markers and the ones that block common outputs (attribution, results, likely questions).
3. **Provenance.** Numbers missing a source, measurement or caveat.
4. **Conflicts.** Unresolved `## Conflicts` sections.
5. **Outputs.** `applications.md` events with no next step; folders in `outputs/applications/` missing a provenance table, or a sent one missing its `resume.pdf`; a target in `outputs/resumes/` whose `.pdf` is older than its `.tex` (by the last commit that touched each, `git log -1 --format=%ct -- <file>`), so a sent-version hash would point at a PDF that does not match its source; anything at the top of `outputs/` besides `applications/`, `resumes/` and `reports/`.
6. **Staleness.** Entries marked ongoing whose last log line is over two months old; `README.md` rows that disagree with their entry's frontmatter.

End with a short ranked to-do list (which entry to consolidate first and why). Fixing more than one entry from that list is a bulk change ([SKILL.md › Commits](../SKILL.md)).

Done when every entry in `README.md` has been checked against all six points.
