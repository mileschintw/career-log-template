# Mode: import

Bring old resumes, CVs, LinkedIn exports, bios or reports into the log. Different versions describe the same experience in different words and contexts; the job is to merge them into one entry per experience without losing any wording or inventing anything.

When the source is a logged-in website rather than files (an AI chat history such as Perplexity, a LinkedIn profile), first follow [import-web.md](import-web.md) to capture it into `sources/<origin>/`, then continue from step 3 with those files.

1. **Collect and preserve the originals.** Take every file in `sources/inbox/` (or the files the user handed over and copy them there first). Move each, unchanged, to `sources/resumes/<YYYY-MM-DD>-<label>.<ext>` (the document's date when it gives a day, otherwise the import date, with the document's own date noted in the report) if it is a resume or CV, otherwise to `sources/<origin>/` (e.g. `linkedin/`) with the same naming. Ask the user for a document's date or target role only when the file and its name do not show it.
2. **Extract text.** `.md`/`.txt`/`.tex`: read directly. `.docx`/`.rtf`/`.doc`: `textutil -convert txt -stdout <file>` on macOS, `pandoc -t plain <file>` elsewhere. `.pdf`: the Read tool. Check each extraction is complete before moving on.
3. **Split into items.** For each document list every experience item (job, internship, project, research, leadership, award, course), plus profile facts (contact, education, skills, languages).
4. **Match items across documents and against existing entries.** Same organisation and overlapping period is a match; for projects, the same project under a different title or framing is a match too. Classify each item as **match**, **new**, or **ambiguous**. Put every ambiguous case to the user in one numbered round with your proposed answer, and wait.
5. **Merge into entries.** For each experience:
   - Create the entry from `entries/_template.md` if it is new, and add it to `README.md`.
   - Append every bullet, verbatim, under `## Past phrasings` with its source file and the context it was written for (target role, date).
   - Lift facts (dates, titles, numbers, technologies, outcomes) into the matching sections, each with provenance `(sources/resumes/<file>)`.
   - Record contradictions between versions (different dates, numbers, titles, scope) under `## Conflicts`, quoting each side with its source. Leave them unresolved for consolidate.
   - Leave every section the documents cannot fill as `GAP:`.
   Merge profile facts into `profile.md` the same way.
   For any story an imported item could tell (a hard bug, a lead role, a conflict), add a link under its question type in `stories.md`, marked *(raw)*.
6. **Write the import report** as a new section in `sources/import-log.md`: files imported; entries created and updated; conflicts found; and, per entry, the gaps that matter most, with the consolidate questions they imply.
7. **Show the report** to the user, then commit and push: `import: <n> file(s), <m> entr(y/ies)`.

Done when every file in the inbox is preserved under `sources/resumes/`, every item from every document is either in an entry or listed in the report as deliberately skipped (with the reason), and every conflict is recorded.
