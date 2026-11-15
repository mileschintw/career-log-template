# interview: the technical round

The technical part of [interview.md](interview.md), for a stage whose prep file has the `areas` item: the recruiter's mail, the posting or the research names technical areas or topics. Four phases use it: Research finds how the round is asked, Align settles the areas, Pack writes `## Technical areas`, and Practise studies each topic to its done bar.

## How the round is asked

In Research, find the round's **form** as well as its topics: from the recruiter's mail, any assessment the user took for this employer, and candidate reports (forum posts, interview write-ups), each fact with its URL or file. A form is how a question comes: the interviewer lets the user pick an area, asks for a design for a customer in that area, asks to explain a concept to a listener outside the field, or grows a technical question from a behavioural answer or from the user's own design. Write the forms and the topics each source names into `research-<stage>.md`, under `## Technical round`; the research item is `done` only once that section is written.

## Areas

In Align's **areas** exchange, show one table: each area the mail, the posting or the research names; the Log's evidence for it (entries, by file and section); its exposure, the requirement map's `gap` and `claimed, unbacked` rows that fall in it; and your proposal: depth, breadth or drop, as many of each as the mail asks for. Read the mail's wording for whether the areas are a choice, and say which way you read it. Name an area plainly as a drop candidate when nothing in the team, the posting or the user's background touches it. Then the user cuts and chooses, and rates each kept area (confident, fair, worried); write one Decisions row per area: its role and the user's rating. The areas item is then `done`, with `prep-<stage>.md#decisions` as where.

## The pack's Technical areas

Pack writes `## Technical areas` into the pack and adds the row `| technical-areas | pack | done | interview-<stage>.md#technical-areas |` to the prep file. The section holds:

- **Areas:** each chosen area, depth or breadth, with its Decisions row.
- **Form:** how the round is asked, from *How the round is asked*, each form with its source.
- **Drill table,** `| tier | topic | why likely | source | your evidence | time |`, three tiers in this order: `will be asked`, `often asked`, `if time is left`. Each row names its source: the recruiter's mail, an assessment the user took, or a candidate report's URL; a topic no source names stays out. Your evidence is the entry and section the user's answer can tie to, or `bridge`. Time is the minutes the topic's study takes, one question per topic; total each tier, so the Plan can size each area's effort and cut a tier the schedule cannot hold.
- **Depth study list,** for each depth area: the primary sources to read (vendor docs, papers, the Log's own deep-dive notes and the PRs, issues and ADRs they cite), and, for a project the round may probe in depth, the **resume-line ladder**: what the user built, how it works, what happens on failure, why this design, its known limits, each rung with its source.
- **Bridges:** for each area the Log does not back, its honest bridge, as [interview-pack.md › Likely questions](interview-pack.md#likely-questions) says; in the room, "I haven't done that; here is how I'd reason about it" counts as a good answer.
- **Done bar,** one for every topic: a plain-words definition of about 30 seconds that a listener outside the field follows; one trade-off ("when A, when B"); one link to the user's own experience, or the bridge. When the role calls for explaining to a non-technical listener or at a whiteboard, the bar also asks for the answer said aloud, with a sketch where the topic has one.

Then add one prep row per drill-table topic, `| areas/<topic> | practise | open | interview-<stage>.md#technical-areas |`, `<topic>` a lowercase slug, in tier order.

## Study

In Practise, each `areas/<topic>` row is studied in one round of [interview-practice.md › A round](interview-practice.md#a-round), item `areas/<topic>`, and its retests follow [interview-practice.md › Retests](interview-practice.md#retests). Take the rows by the schedule, `will be asked` first. Write each part in its language as [SKILL.md › Languages](../SKILL.md#rules-for-every-mode) says (study material, questions and model answers). A technical round adds these to the steps of *A round*:

1. **Terms and Teach**, in *Ask it with its bar*, in a message of their own before the question, which ends your turn on asking whether any term is still unclear: define each term the topic and its question use, pitched at the user's level (Align's rating, Diagnose's verdict); explain the topic from primary sources, citing each number and each claim of a model answer with its source, as the pack cites its facts; and tie it to the user's evidence from the drill table.
2. **Ask** one question in the form *How the round is asked* found, against the topic's bar in the pack's *Done bar* ("in plain words, with one trade-off and where you have met it"). Where the forms include it, grow the question from the user's last behavioural answer or their own design.
3. **Wrong statements**, in *Feedback*: a statement about the topic itself that is wrong (not only one the Log does not hold) goes under the practice log's `## Do not say`, with its correction and its source.
4. **Mark done**, after *Write the verdict*: when the verdict is `passed`, ask the user whether the topic is done; on their yes, set its row to `done`. Any other verdict leaves it open, and a `near` is asked once more before the next new topic, as another `--kind drill` round, not a retest.

Done when every `areas/` row is `done` or `set aside` (a topic the Plan cut, or one the user set aside), and `prep-status` prints no `retest:` line for an `areas/` topic.
