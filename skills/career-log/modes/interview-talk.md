# interview: a prepared talk

The prepared talk of [interview.md](interview.md): a timed talk the stage asks the user to give on a subject of their choice, often followed by questions, which the prep file holds as its `talk` item (`prep-init --with talk`). Five phases use this file. Align settles *The prompt*, *Topic* and *Thesis, hook, story and call to action*; Pack writes *talk.md*; Diagnose, Plan and Practise rehearse it as *Rehearsal* says, to [speaking.md › A prepared talk](../speaking.md#a-prepared-talk).

A prepared talk is a talk worth hearing on its own, the form of a short TED-style talk: one question, one picture, one story and two or three numbers. It is not a behavioural answer in disguise: a project from the Log may be its subject, but it is not chosen or ranked by the values it shows.

## The prompt

The employer's prompt for the talk rules it. Before proposing anything about the talk, read the prompt's full text and save it as `talk-prompt.md` in the application folder: from the recruiter's mail or its attachment as Intake saved them, or as the user pastes it. When there is none, ask the user for it, and add the question to `recruiter-questions.md`. Until it comes, ask the user what they know of each item below and write it with the user as source; when the prompt arrives, save it, check each row and `talk.md` against it, and change what it contradicts.

Write down from it, in the prep file's `## Decisions`, one row each, with the prompt as source:
- **the allowed kinds** of subject it lists;
- **the audience** and **what is judged**;
- **the length window** (`<min>–<max>` minutes);
- **the room's rules:** notes, devices, slides, a whiteboard, handouts;
- **the suggested structure and timings,** when it gives them;
- **what follows the talk:** questions or none, and how long.

The prompt's audience and judging criteria rule over the interviewer profiles from Research: the topic, the hook and the call to action are each weighed against the prompt's audience. What the prompt leaves open (are notes allowed, are there questions after it, who hears it and what they do with it) comes from `research-<stage>.md` or goes to `recruiter-questions.md`.

Done when `talk-prompt.md` is saved (or the recruiter question for it is open) and the prep file has a Decisions row for each item above, each from the prompt, the research, the user, or a recruiter question that is still open.

## Topic

Align's first `talk` exchange. The topic comes out of a conversation with the user, in the conversation language, not a ranked menu to pick from. Open it with the kinds the prompt allows and, for each, one or two subjects the Log offers (an entry, a skill the user learned, an interest `direction.md` names), as material to talk about, none of them recommended. Ask what the user wants to talk about, then grill it: who in this audience cares, what they would take away, whether it fills the window without rushing, whether the user can draw it. A subject outside the Log is as welcome as one in it. Classify the chosen topic as one of the prompt's allowed kinds.

Done when the user has named the topic and its kind, and the prep file has its Decisions row.

## Thesis, hook, story and call to action

In this conversation, after *Topic*, one exchange each, so each decision about the talk is made in one place (a forked session or a subagent would split it):
- **Thesis:** one sentence, in the talk's output language ([SKILL.md › Languages](../SKILL.md#rules-for-every-mode)), that the whole talk argues.
- **Hook:** the opening, usually a question the audience can answer in their head.
- **The story:** the one story that carries the thesis, with its entry when it comes from the Log.
- **Call to action:** one specific action the audience can take, tied to the thesis.

Each is a Decisions row. Then set the prep file's `talk` item to `done`, where `prep-<stage>.md#decisions`.

Done when the four rows are in the prep file and the `talk` item is `done`.

## talk.md

Pack writes `talk.md` in the application folder from the Decisions rows, in the talk's output language, and sets the `talk` item's where to `talk.md`. It is the talk's one source: the script, the notes and any page built for rehearsal come from it, so a change is made in `talk.md` first and a page built from it is rebuilt and listed in the prep file's `## Pages`. Its sections:

1. `## Frame`: the prompt's rules from the Decisions rows, the length window and the target ([speaking.md](../speaking.md) rule 13).
2. `## Outline`: one `### <part> (<m:ss>–<m:ss>)` per part, its planned time window beside it, the windows adding up to the target. The parts follow the prompt's suggested structure and its timings when it gives them; otherwise hook, what it is, why it matters, how it works, call to action. Under each part, its points in a line each. *Rehearsal* resets the windows from the first spoken run.
3. `## Picture`: the one picture the talk is drawn around, as the user would draw it on a whiteboard (boxes, arrows, labels), when the room has one; a one-page handout instead only when the prompt allows handouts and the user wants one; else `None.`
4. `## Script`: the full reference script, part by part under the outline's headings, as the user would say it.
5. `## Presenter notes`: per part, its points with their key phrases; the opening question and the last two lines word for word; `[pause]`, `[draw]` and `[point]` where the user does them. The user delivers from these, as from a slide's presenter notes ([speaking.md](../speaking.md) rule 12).
6. `## Questions after`: sized by the Decisions row on what follows the talk ([speaking.md](../speaking.md) rule 15). With questions: the obvious comparison the audience will raise and a fair answer to it, then four or five likely questions, each answered with one point in a sentence or two. With none: `None expected (<its source>).`
7. `## Sources`: one row per number and per external claim the script makes, `| claim | source | checked |`.

**A number about the user's own work** cites its entry and section (`entries/<file>.md › <section>`) or `profile.md`'s line. One the Log does not hold goes into its entry first, as the user gives it ([interview.md](interview.md)'s rule for new facts), or is cut.

**An external claim** (a quote, or a figure or fact about another product, company or the field) is checked in this run on its primary source, fetched as [interview.md › 2. Research and deep dives](interview.md#2-research-and-deep-dives) reads pages; its row gives the URL and the date read. A claim the fetched page does not confirm is corrected to what the page says, or cut. Every claim is settled in this run: confirmed, corrected or cut.

Done when `talk.md` has the seven sections; the outline's windows add up to the target; every number and external claim in the script has its `## Sources` row, each number about the user's work citing an entry or `profile.md`, each external claim a URL fetched this run; and the `talk` item's where is `talk.md`.

## Rehearsal

Diagnose's talk round is one spoken, timed run, which you ask the user to give standing, as in the room, not read at a desk: the whole talk, or the opening and one part when the user cannot yet give it all; write each part's time in the practice log's row. Then set those parts' windows in `talk.md` from the times; the first full run sets any window still planned. When the windows no longer add up to the target, cut or lengthen parts' text until they do, first any part past the prompt's timing for it. Commit `talk.md` with the phase's commit. Plan sizes the rehearsal by that round's verdict; Practise runs it, each run a practice log row with item `talk` for a full run or `talk/<part>` for one part. Judge each run against [speaking.md › A prepared talk](../speaking.md#a-prepared-talk), naming each rule it misses by number, with feedback in the conversation language. The `practice` item is not `done` for the talk until rule 16 holds.
