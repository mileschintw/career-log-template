# Mode: write

Produce an output (resume bullets, a full resume section, cover letter, bio, elevator pitch, application answer, interview answer) from the log.

1. **Pin down the target.** Kind of output, audience (role, company, job posting if any), language, length limit. Ask only for what the request does not already say.
2. **Load the user's direction.** Read `direction.md` in full. It decides:
   - which entries to lead with, and which skills to de-emphasise or leave out (§ What to emphasise, by target);
   - the user's own voice and format preferences (§ Writing preferences for applications), on top of [../writing.md](../writing.md), which every draft must pass;
   - the constraints to state or avoid: graduation date by application type, work authorisation (`profile.md › Conflicts` holds the resolved dates).
   Then check `applications.md` for earlier answers to the same company, and `stories.md › Application questions` for an approved answer to the same question type.
3. **Select material.** Read `README.md` and `stories.md`, then the entries whose tags and stories fit the target. Read each selected entry in full, including `## Past phrasings` and `## Conflicts`: earlier wordings are reusable, and Conflicts lists claims already found false.
4. **Draft.** For a resume version, edit a `.tex` copy in `.build/drafts/<target>/` (of `outputs/resumes/<target>.tex` when the target exists; else of the user's newest resume, found as `apply.md` step 3 orders it, or of the blank layout [../assets/resume-blank.tex](../assets/resume-blank.tex) when there is none; never of the example resume) following [../latex.md](../latex.md), and build it with `tools/resume.py` after each change. `<target>` is a short lowercase name for the version (`general`, or the target role family); reuse an existing target's name rather than starting a near-duplicate. Lead with impact and numbers. Every claim must trace to a sentence in an entry. For a US audience, generalise entities those readers will not know: name what the thing does instead of what it is called locally.
5. **Check the draft claim by claim** against the entries:
   - the verb matches the attribution (led / built only for the user's own work),
   - each number is the entry's number, with its caveat respected (a tie stays a tie),
   - nothing repeats a claim an entry's `## Conflicts` marks as unsupported,
   - every rule in [../writing.md](../writing.md) and `direction.md › Writing preferences` holds, including the AI-tell check and its humanizer layer,
   - `visibility: nda` material is generalised,
   - nothing comes from outside the log. If the output needs a fact the log lacks, stop and ask, then record the answer in the entry too.
6. **Review** with [review.md](review.md) when the output goes to an employer (resume, cover letter, application answer). Skip it for personal drafts such as notes or a bio the user is still shaping.
7. **Show the user the draft** together with the risks you found (attribution stretch, numbers that need a caveat in conversation, likely follow-up questions). Revise until they approve.
8. **Save.** A resume version goes to `outputs/resumes/<target>.md`, with the approved `.tex` and its built `.pdf` copied from the draft folder as `<target>.tex` and `<target>.pdf`, overwriting the previous version in place (git history keeps it). An output for one application goes into its `outputs/applications/` folder. Anything else goes to `outputs/reports/<YYYY-MM-DD>-<slug>.md`. Each `.md` holds the approved text, then a provenance table (claim → entry section → source). Append a pointer line to each used entry's `## Past phrasings`. For an application, add a row to `applications.md`; for an answer to a recurring question type, point `stories.md › Application questions` at it. Commit and push: `write(<slug>): <target>`.
9. **Record a sent version.** When the user sends a resume version outside an application (a career fair, a recruiter email), record it in that event's `applications.md` row as a commit hash, in the format [SKILL.md › Sent versions](../SKILL.md#sent-versions) gives. Commit and push.

Done when the user has approved the text, an employer-facing output has passed the review, and the saved output's provenance table covers every claim in it.
