# Mode: audit

Report how ready the log is to produce outputs. Read-only: it changes nothing except the report it prints.

Check and report, most important first:

1. **Story coverage.** Each question type in `stories.md` with no entry behind it, or only a thin one.
2. **Gaps.** Per entry, the count of `GAP:` markers and the ones that block common outputs (attribution, results, likely questions).
3. **Provenance.** Numbers missing a source, measurement or caveat.
4. **Conflicts.** Unresolved `## Conflicts` sections.
5. **Applications.** `applications.md` events with no next step, and `outputs/` application folders missing a provenance table.
6. **Staleness.** Entries marked ongoing whose last log line is over two months old; `README.md` rows that disagree with their entry's frontmatter.

End with a short ranked to-do list (which entry to consolidate first and why).

Done when every entry in `README.md` has been checked against all six points.
