# Mode: consolidate

Turn an entry's log lines, links and imported phrasings into a complete record, so that any future output can be written from this file alone.

If the session will rewrite more than one entry, it is a bulk change: with the data-branch flow on, start a `data/` worktree before step 1 and end with a pull request ([SKILL.md › Commits](../SKILL.md)).

1. **Read everything the entry points at.** The entry itself, its `## Log`, its `## Past phrasings`, and every link: repos, PRs, issues, docs, benchmark files. Pull out facts, numbers, dates, decisions, dead ends and review comments, each with its provenance.
2. **Draft every section of the template** from that material. Where the material cannot answer, write `GAP:` with the specific question.
3. **Interview the user on the gaps**, in rounds. Each round asks every open question that does not depend on another open answer, numbered, with your best guess as a recommended answer the user can accept or correct. Prioritise in this order:
   - attribution (what exactly did *I* do versus others or tools),
   - the reasons behind decisions and the alternatives rejected,
   - people: feedback received, disagreements, who was helped,
   - what was learned and what they would do differently,
   - the questions an interviewer is most likely to ask, with draft answers.
   Record each answer with `(user, YYYY-MM-DD)`. An unanswerable question stays a `GAP:` with a note. If the user says the experience did not happen or does not count, follow *Dropped experiences* in SKILL.md instead of finishing the entry.
4. **Show the user the updated entry** (or a diff) and apply their corrections.
5. **Update the indexes.** `README.md` row (period, tags, status `consolidated`, with a short note in parentheses if gaps remain); `stories.md`, adding this entry under every behavioural question type it can answer, pointing at the section.
6. **Commit and push**: `consolidate(<slug>): <summary>`. On a `data/` branch, open the pull request when the session's work is done.

Done when every section is filled or carries an explicit `GAP:` the user could not answer, every number has its measurement and source, the attribution section names all three categories (even if one is "none"), and `stories.md` points at this entry for every story it holds.
