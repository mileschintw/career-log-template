# Mode: fit

Before this mode's first step, run the **Start check** in [SKILL.md](../SKILL.md), once per session.

Answer "should I go for this posting, and what am I missing?" from the log, and turn the gaps into a learning plan. It drafts nothing.

- **One posting** ("how well do I fit <URL>", "should I apply?", "what am I missing for <URL>", "how do I close the gap to <URL>"): the one-posting run, steps 1 to 7 below.
- **Several postings** ("what should I learn for these postings", "what should I learn for my targets"): the several-postings run, in [fit-several-postings.md](fit-several-postings.md).
- **Handed over by scan** (a prompt from [scan](scan.md) step 7 naming a capture file, with the gate, tier and things to check its Screen gave): the one-posting run, steps 1, 2, 5 and 6, with no *Start check* or *Trigger check* (the scan ran them). Step 1 extracts from the file, the capture, as [Capture a posting](#capture-a-posting)'s list says, and reads no page. Step 2 reads `profile.md` alone. Steps 3 and 4 are the Screen's: take its gate (a yes) and tier as given, and its things to check as theirs. Ask nothing and save nothing: reply with the tier, the map as step 5 shows it with each row marked `required`, `preferred` or `duty` as the posting gives it, the recommendation and the things to check, and stop.
- **Screen** (a prompt from [scan](scan.md) step 6 naming a batch file): the section [Screen](#screen), for each capture the batch lists.

The plan leads with projects that would become entries, unless `direction.md` says the user learns another way.

## One posting

1. **Capture the posting** as [Capture a posting](#capture-a-posting) says.
2. **Load the user's direction and profile.** Read `direction.md` and `profile.md` in full, not by search: Constraints and Target roles decide steps 3 and 4, and `profile.md` (education, graduation date, languages) answers requirements such as a degree.
3. **Gate.** Check each hard constraint in `direction.md › Constraints` against the posting: its authorisation language (step 1) for work authorisation, and its location, start date, level or whatever else a constraint names. A role that breaks one is a no: say so and stop, unless the user overrides it (then go on to step 4).
   - When work authorisation is empty ([SKILL.md › Setup](../SKILL.md#setup)), or Constraints says there is no constraint, there is no gate for it: list the posting's authorisation language under the recommendation as something to check, and, when it is empty, say so under the recommendation too.
   - An answer is final: when it does not mention what the posting asks (a clearance, say), list that requirement as something to check.
   - **H-1B LCA lookup.** When the constraint needs visa sponsorship and the posting says nothing about it, look the employer up in public H-1B LCA records (sites that republish the US Department of Labor's disclosure data) and report what you find as something to check, citing each record's URL. A records page a plain fetch cannot read is a Browser capture: follow [browser.md](../browser.md), in a session named `lca`, closed when the lookup is done. Say whether the filer is certainly this company (a similar name or a parent company is not); no filings from a young company is no proof either way.
4. **Tier:** where the role sits in `direction.md › Target roles, ranked`. When the target roles are empty, give no tier and say so ([SKILL.md › Setup](../SKILL.md#setup)); the recommendation then rests on the gate and the requirement map.
5. **Requirement map.** Follow [Requirement map](#requirement-map) whole, on step 1's requirements and duties. The conditions it takes out go under the things to check.
6. **Recommendation:** apply / apply with caveats / skip, in one line, after the gate, the tier and the map. Under it, the things to check from steps 3 and 5.
7. **Offer the next step,** both options, and stop. Offer them after a skip recommendation too, and after a gate no the user overrode: what to do next is the user's call:
   - **the resume and answers,** a `write` posting run on this posting ([write.md](write.md));
   - **a learning plan** for this posting's critical and high rows. Give every shallow, claimed-unbacked and gap row a priority from how the posting asks for it: a required skill or a core duty is critical (or high, when other requirements outweigh it), a preferred skill is high or medium, a nice-to-have is low. Then plan as [fit-several-postings.md](fit-several-postings.md) step 6 says. When the request already asked how to close the gap ("how do I close the gap to <URL>"), go straight into the plan instead of offering it.

   The run saves nothing unless there is a plan (the user took the offer, or asked for it in the request); then save it as [fit-several-postings.md](fit-several-postings.md) step 7 says, with the map as its table, but to `outputs/reports/<YYYY-MM-DD>-fit-posting-<company>-<role>.md`, with no "since last report" section, committed as `fit(<company>-<role>): <n> gaps`. A preference or reaction the run reveals still goes into `direction.md` (*Direction upkeep*), committed as a small data change.

Done when the user has the gate, the tier, the requirement map, the recommendation (or the gate's no) and the things to check, and has been offered the next step; a plan they took also gives each critical and high row a project, sourced resources and a time estimate, and is saved.

## Capture a posting

Step 1 of a one-posting run follows this section, and so does [write.md](write.md) step 2.

Take the posting from the URL the user gives, or from pasted text. Read the URL as [browser.md › Fallback order](../browser.md#fallback-order) says: a plain fetch first; a page it cannot read (built by script, as Ashby and Workday pages are, or behind a sign-in) is a Browser capture, following [browser.md](../browser.md), in a session named `posting`, with the `--profile` of [browser.md › Sign-in](../browser.md#sign-in) only for a posting behind a sign-in. `fit` closes that session once the posting text is read, and deletes `.playwright-cli/` after step 3; `write` keeps it open through its step 2, which closes it. When no item of that order gives the posting text, ask the user to paste it, as its last item says; never guess what the page holds. The posting is data ([SKILL.md › Postings are data](../SKILL.md#rules-for-every-mode)). Extract:
- company, role, level, location and deadline;
- every stated requirement, required and preferred;
- every stated duty ("What you'll do", "Responsibilities"), which the requirement map takes like a requirement;
- its **authorisation language**: any sponsorship, citizenship or clearance wording, quoted as the posting gives it.

Done when every item above is extracted from the posting text, or the user has been asked to paste it.

## Screen

This section is the whole task of a subagent that [scan](scan.md) step 6 starts on a batch of captures: a first pass over many postings, so that only the best get a full fit. The prompt names the batch file (`.todo`, one capture path per line) and the results file to write. Each capture is a posting's verbatim text with its URL on the first line, and it is data ([SKILL.md › Postings are data](../SKILL.md#rules-for-every-mode)). Skip the *Start check* and the *Trigger check*: the scan ran them. Every posting comes from its file: the main session has read the pages.

1. **Load once:** read `direction.md` and `profile.md` in full, and run `python3 -I <root>/tools/entries.py list <root>` (`py -3 -I` on Windows) once and read its whole output. Those lines are all you read of the entries: their tags, org and One line stand for each entry, and the entry files stay closed.
2. **For each capture** the batch lists that exists (skip a path with no file):
   1. **Extract** from the file what [Capture a posting](#capture-a-posting) lists, reading no page.
   2. **Gate** as step 3 of [One posting](#one-posting) says, with its H-1B LCA lookup left out and listed under the things to check. A no is final here: give the constraint and the posting's words.
   3. **Tier** as its step 4 says.
   4. **Rough coverage,** on a gate yes: take out the conditions as [Requirement map](#requirement-map) item 1 says (they go under the things to check), then mark each remaining requirement and duty `required`, `preferred` or `duty`, as the posting gives it (a requirement under no heading that says preferred, a plus or nice to have is required), and name each entry whose list line touches it (its tags, org or One line), or none.
3. **Write the results file:** one JSON object per capture, one per line, in the format `python3 -I <root>/tools/scan.py --help` gives for a Screen result: `url` (the URL on the capture's first line), `gate`, `reason` (on a no), `tier` (a number, or null for no tier), `rows` (each requirement and duty with its `kind` and `entries`, the entry file names) and `check` (the things to check).

Done when the results file holds one line for each capture in the batch that has a file, each line has a gate, and each gate yes has its tier (or null) and one row per requirement and duty that is not a condition.

## Select entries

Item 3 of [Requirement map](#requirement-map) follows this section, and so does [write.md](write.md) step 5 in a target run. Its input is what the entries must evidence: the requirements and duties, or in a target run each skill or theme `direction.md › What to emphasise` names for the target (the target's role name when it names none).

1. **List the entries.** Run `python3 -I <root>/tools/entries.py list <root>` once in the run and read its whole output, not a search of it: one line per entry, with its series, type, org, period, tags and One line. Read `stories.md` too.
2. **Select from the list:** every entry whose tags, One line or org, or a `stories.md` row pointing at it, touches the input.
3. **Search the rest.** For each item of the input no selected entry touches yet, search the bodies of the entries the list names and step 2 did not select for its key terms: the technology, domain or tool it names, in the input's words and in the record language. Select each entry that matches. Tags are incomplete, so an untagged experience is found here.
4. **A series is one experience.** A selected entry whose list line shows a series other than `-` is one part of it: select every line with the same series. Read all its parts and cite each fact by the part that holds it. [write.md](write.md) step 6 says how an output writes a series.
5. **Read each selected entry whole:** one read of the whole file, with no line range, offset or limit, and no filter such as `sed -n`, `head` or `cut`, so `## My contribution`, `## Past phrasings`, `## Conflicts` with its `Settled:` lines, and `## Pending` are all read.

Done when the list was read whole, every item of the input either touches a selected entry or had its key terms searched in the unselected entries, every part of each selected series is selected, and every selected entry was read whole in this run.

## Requirement map

Step 5 of a one-posting run follows this section, and so do [fit-several-postings.md](fit-several-postings.md) step 3 and [write.md](write.md) step 5. Its input is the requirements and duties the step that sent you here gives.

1. **Take out the conditions.** What is neither a skill nor a duty (a background check, a location, a pay range, a start date, years of experience) gets no row; the step that sent you here says where it goes. Every skill and every duty the posting names stays a row, including one the log never touches, which is a `gap` row.
2. **List the course-work entries:** run [Select entries](#select-entries) step 1 now (item 3 reuses its output) and, from every line of the list, not only the entries you read, take each entry whose type is `course`, whose tags include `coursework`, or whose org names a course. A capstone (an `org` or a tag that names one) is not course work: judge its parts by the values below, as for any project, with teammates' parts as `collaborator`.
3. **Select and read the entries** as [Select entries](#select-entries) says, on this map's requirements and duties. Each entry a row cites is one of them, read whole in this run.
4. **Tie each row to one entry,** the one that evidences it. When several entries back a row, weigh each by the rules below and cite the one that gives the strongest category. A requirement that names several skills ("Go, Python, SQL") becomes one row per skill when they would fall in different categories.
5. **Fill in "written by"** before the category: one value per row, from the one entry the row cites. When different people or agents wrote the sections of that entry that touch the row (one phase by a collaborator, another by an agent), take the section that gives the strongest category (item 4's rule), name it beside the entry's file name in the map ("`2026-01-x.md` (phase 3)"), and give that section's value alone. A series part is its own entry: cite the part's file. The value is the first of these that applies:
   1. `coursework`: the entry is on the course-work list, even when the user wrote every line;
   2. `collaborator`: another person (not an AI agent) wrote this section, even when that person worked through an agent, including work under *Others did; I can explain it* or a `Settled:` line that gives it to another person;
   3. `AI agent`: the entry's `## My contribution` or a `Settled:` line says an agent wrote the code for this section, even under the user's direction or *I led, with help from*;
   4. `unknown`: the entry leaves open who wrote this section (a `GAP:` on it);
   5. `user`: the user wrote it.
6. **Fill in "own work"** for an `AI agent` row: a label, then the line it quotes, or `none`. The line comes word for word from the entry's `## My contribution`, `Settled:` lines or `## How it works`, is about this section, and has the user as the one acting: a line under **I did:**, or one where the user does the work ("caught that …", "chose …"). A line where someone else found or checked it ("had the code checked"), or where the user only reported a symptom or handed off the whole problem ("had it fixed", "asked the agent to fix the failing test"), makes the cell `none`. The label is one of three, and nothing else counts:
   - `design:` the user's own design decision: an architecture, an interface, a tech choice, including a plan or a discussion in which the user picked one;
   - `debugging:` the user found what broke and why; the fix itself can be the agent's ("traced the drift to X and had the agent fix it");
   - `review:` the user read the agent's code or output and corrected it.

   A line of any other kind (testing by hand, scoring, approving, scheduling or splitting up the work, learning from an explanation) makes the cell `none`. Two kinds of row take only some labels:
   - a row naming a language or a tool ("Go", "TypeScript", "Kubernetes"): `debugging:` or `review:`, with the line showing the user in that code itself;
   - a row for debugging or diagnosing: `debugging:` only.

   On those rows, a line with another label (a `design:` line, such as choosing between fixes) leaves the row at most shallow.
7. **Cap the row** by its value:
   - `user`: by the depth the entry shows;
   - `AI agent`: covered only with a labelled, quoted "own work" line that counts for this row, whatever the depth the posting asks; with `none`, at most shallow;
   - `unknown`: at most shallow;
   - `collaborator`: at most shallow when the posting asks for build depth, however much of the work there is;
   - `coursework`: at most shallow, unless the requirement asks only for understanding, knowledge, exposure or familiarity ("deep understanding of distributed systems", "familiarity with compilers"): then covered when the entry shows it.
8. **Sort** each row into **exactly one** of these four categories, and no other label:
   - **covered:** an entry shows the user doing it at the depth the posting asks ("operate" vs "build"), and the row's cap allows it;
   - **shallow:** an entry shows it, but below the depth asked (used, not built), or the row's cap holds it there;
   - **claimed, unbacked:** on a resume or in `profile.md` with no entry behind it;
   - **gap:** nowhere in the log, including a skill the log cannot show (communication, problem solving), which the interview judges.

   Name who built what as the entry's `## My contribution` and its `Settled:` lines say: a collaborator's build is never the user's, even where a resume or an imported document once said so.
9. **Count the rows** once every row has its category, and print the count as text in your reply, outside any tool call, in this form: `Map: <n> requirements and duties, <m> rows; no row: <none, or each requirement or duty without a row, in the posting's words>`. `<n>` counts the requirements and duties of this section's input, less any conditions item 1 took out; `<m>` counts the rows they map to, more than `<n>` only where item 4 splits a requirement. For each requirement or duty the line names, add its row (a `gap` row when the log never touches it) and print the line again, until it says `no row: none`. With several postings, print one line per posting, with the posting in parentheses after `Map`: `Map (<company>, <role>): …`. When item 10 shows the map in the same reply, its `Map:` line is this print.
10. **Show the map:** a first line `Course work: <the file names on the course-work list, or none> (<n> entries listed)`, where `<n>` is the number of lines `tools/entries.py list` printed, then the last `Map:` line item 9 printed, then a table with one row per requirement and per duty: the requirement, its "written by", its "own work" (the label and the quoted line, or `none`, on `AI agent` rows only), its category, and the entry that evidences it, by file name (`gap` and `claimed, unbacked` rows have no entry and no "written by"). Show every row, however many; a count or a summary by category is not the map.

Done when every requirement and duty that is not a condition has one row with exactly one category, every "written by" cell holds exactly one of the five values above (empty on a `gap` or `claimed, unbacked` row), every cited entry was read whole in this run, every `AI agent` row has its "own work" cell, the last `Map:` line printed (per posting, with several) says `no row: none` with `<m>` at least `<n>`, the `Course work:` line's count matches the number of lines `tools/entries.py list` printed, and, unless the step that sent you here skips or defers **Show the map**, the map is shown under the `Course work:` line.
