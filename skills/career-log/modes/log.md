# Mode: log

Capture a milestone in under a minute, without interrupting the user's work. Write and commit directly, then report in one line.

1. **Find the entry.** Match the current work to an entry in `README.md` by project, repo or organisation. If none fits, create `entries/<YYYY-MM>-<slug>.md` from `entries/_template.md`: fill the frontmatter you can determine, leave every other section as `GAP:`, add a row to `README.md` with status `stub`, and append the new organisation or project name to `.export-deny` when that file exists (one per line, regex characters escaped: `Node\.js`, `C\+\+`). If the milestone falls outside the entry's `period`, extend it (or set it to `ongoing`) and update its `README.md` row.
2. **Gather the facts from the current session.** The milestone itself, links (commit SHA, PR, issue, doc), numbers with how they were measured (if that is not in context, ask once in one line; with no answer, write `GAP: how measured`), and any decision or feedback that came up. Use what is already in context and cheap lookups (`git log`, `gh pr view`); skip anything that needs a long investigation.
3. **Append to `## Log`.** One dated bullet per milestone, newest last:
   `- YYYY-MM-DD: <what happened, in one or two sentences>. <links>`
   A quote of the user's words may follow the links, with a translation in brackets when the record language differs (SKILL.md › Languages). Update the frontmatter's `last_updated`. Leave the other sections alone: folding the log into them is consolidate's job.
4. **Commit and push** in the career-log repo: `log(<slug>): <milestone>`.
5. **Report** to the user in one line: which entry, what was logged. If the entry now has many log lines and a mostly-`GAP` body, suggest running consolidate.

Done when the log line is pushed and the user has the one-line report.
