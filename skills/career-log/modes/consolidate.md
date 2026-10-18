# Mode: consolidate

Turn an entry's pending lines, links and imported phrasings into a complete record, so that any future output can be written from this file alone.

If the session will rewrite more than one entry, it is a bulk change: with the data-branch flow on, start a `data/` worktree before step 1 and end with a pull request ([SKILL.md › Commits](../SKILL.md)).

1. **Read everything the entry points at.** The entry itself, its `## Pending`, its `## Past phrasings`, and every link: repos, PRs, issues, docs, benchmark files. Pull out facts, numbers, dates, decisions, dead ends and review comments, each with its provenance.
2. **Draft every section of the template** from that material. Where the material cannot answer, write `GAP:` with the specific question.
   - **Place every pending line** in the section it belongs to, then delete it. A line's leading date is the day it was recorded: it becomes "as of <date>" on a number a later measurement can replace (and that later measurement replaces it in place), and disappears otherwise, except as the source date of a fact the user stated (`(user, YYYY-MM-DD)`). A date for an event goes into the body only when evidence gives it, and only where an output could use it (the `period`, a launch month).
   - **Settle conflicts the material or the user resolves.** Write the right value in its section with its source, and collapse the conflict to one `Settled:` line in a form `entries/_template.md` gives: usually `Settled: use "<right>", not "<wrong>"[ or "<wrong2>"] (<why>). (<source>)`, the both-right and by-context forms when no side is wrong, or the do-not-use form for a claim with no support, whose quoted claim and why-clause name the false claim itself, not the technique or topic it mentions ([../writing.md](../writing.md) › Principles 3). Drop the list of versions; the sources keep them. Evidence settles what is true; a pick between competing true wordings, or a conflict an approved output merely sidestepped, is the user's ([SKILL.md › Current truth only](../SKILL.md#rules-for-every-mode)). Every other conflict stays as a line starting `Open:` (add the marker to an older line that lacks it).
   - **Trim `## Past phrasings`** to at most two wordings per claim per angle (the claim and the angle as `entries/_template.md` defines them). Of near-identical wordings keep one. Rank a wording from an approved output above an imported one, then the newer above the older, and keep the top two. Each keeps one citation; delete anything else there: usage notes, extra citations, and the dates, companies or postings it was used for outside the citation. Names inside the verbatim wording stay.
   - **Re-cite facts that cite an output** (a resume, report or answer) with the source in that output's provenance table; when the output has since been deleted, read its table at the cited commit (`git -C <root> show <sha>:<path>`).
3. **Interview the user on the gaps**, in rounds. Each round asks every open question that does not depend on another open answer, numbered, with your best guess as a recommended answer the user can accept or correct. Prioritise in this order:
   - attribution (what exactly did *I* do versus others or tools),
   - open conflicts: which side is right,
   - the reasons behind decisions and the alternatives rejected,
   - people: feedback received, disagreements, who was helped,
   - what was learned and what they would do differently,
   - the questions an interviewer is most likely to ask, with draft answers.
   Record each answer with `(user, YYYY-MM-DD)` in the section it belongs to. An unanswerable question stays a `GAP:` with a note. If the user says the experience did not happen or does not count, follow *Dropped experiences* in SKILL.md instead of finishing the entry.
4. **Show the user the updated entry** (or a diff) and apply their corrections.
5. **Update the indexes.** `README.md` row (period, tags, status `consolidated`, with a short note in parentheses if gaps remain); `stories.md`, adding this entry under every behavioural question type it can answer, pointing at the section.
6. **Commit and push**: `consolidate(<slug>): <summary>`. On a `data/` branch, open the pull request when the session's work is done.

Done when every section is filled or carries an explicit `GAP:` the user could not answer, `## Pending` is empty, `## Conflicts` holds only `Open:` and `Settled:` lines, `## Past phrasings` holds at most two wordings per claim per angle, every number has its measurement and source, the attribution section names all three categories (even if one is "none"), and `stories.md` points at this entry for every story it holds.
