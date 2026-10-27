# Sonnet is the lowest supported model, and Opus keeps the rules written for Sonnet

The Engine is tested in Claude Code on Opus and on Sonnet, and Sonnet at medium effort is the lowest supported model: once the modes' fixes landed, 12 of their 13 representative cases passed on it, and the last consolidate run failed only on one character it miscopied while pasting a diff whole (#72, #512, #518, #519). Haiku is not supported. A Haiku reference round at xhigh effort passed 10 of the 13 modes, failed two, and went over scan's 10-page cap in a third, where it was stopped without a result; it cost about half of what Sonnet did, and took longer in 12 of the 13 modes. Codex, Cursor and Antigravity are untested.

Most of the fixes that brought Sonnet to a pass moved a step out of the mode's wording and into a tool: a check the run prints and cannot pass by rewording (`check_save.py --commit`), or an output it pastes as printed (`fit.py map --show`, `entries.py diff`, `application.py phrasings`), or a choice it hands back to the user (`entries.py story-leads`). The worry was that the #518 and #519 sentences telling a run to use these tools make Opus mechanical, so #126 ran Opus at medium effort, the effort it normally runs at, with and without the #518 and #519 sentences that tell a run to use those tools. The tools themselves stayed in both versions. The rules stay, because the run without them was not better:
- **Write** (a live Greenhouse posting): no measurable difference. Without the rule, Opus still pasted the requirement map whole, because `fit.md › Show the map` already asks for it as printed. Both versions added exactly the Past phrasings that `phrasings` marked `add:` but one, and it was the same one: a coursework line the tool had read as a resume bullet (#524), which each run skipped on its own judgement. The rule did not make Opus follow the tool blindly. A blind reviewer scored the two saves a tie.
- **Interview** (a recruiter screen, with a fixture type whose Talking points the user had confirmed): the rule costs a round trip. Run under the rule, Opus asked the user for every lead, the confirmed type's included, and waited for the answers before writing the pack: three user turns before its one commit. Without the rule, it took the confirmed type's lead from the file, wrote and committed the pack, and only then asked the user for the other leads, in a second commit. Committing before asking broke the pre-#519 text too, which wanted those leads from the user before the pack. The run also committed two entry corrections from its deep dives that no one had asked for. It is graded a fail: the Opus count under *A user's choice made for them* below. A blind reviewer rated the pack written without the rule better aimed at a 30-minute screen. It rated the deep dives written under the rule more careful about the claims the employer had read, which is what #519's deep-dive sentence asks for. It called the bare `Type:`/`Lead:` lines that #519's pack format writes the most mechanical part of either output.

Whether to ask only for types that have no confirmed Talking points is left to the maintainer. Decided in #526: a type with confirmed Talking points takes its lead from the file without asking; the other types are still asked. Each version ran each case once, so a difference this size cannot be told apart from one run's chance.

## Results

Each cell is the mode's last graded run after its fixes, with its effort. "Pass" means the run reached the case's expected result with no failed check; notes do not change it.

| Mode | Opus | Sonnet (medium) | Haiku (xhigh; reference, not supported) |
|---|---|---|---|
| guide | not run | pass | pass |
| log | pass (effort not recorded) | pass | pass |
| consolidate | pass (high) | fail: one character miscopied in the pasted diff | pass |
| interview | pass (high; medium in #126, under the rule) | pass | fail: no requirement map |
| stories | not run | pass | pass |
| fit | pass (default effort) | pass | pass |
| write | pass (high; medium in #126) | pass | pass |
| rank | pass (high) | pass | pass |
| scan | not run | pass, over the 10-page cap | stopped after 11 pages, over the 10-page cap; no result |
| import | pass (effort not recorded) | pass | pass |
| audit | run, no grade recorded | pass | fail: Next up block cut |
| setup | pass (high) | pass | pass |
| upgrade | not run | pass | pass |

Codex, Cursor and Antigravity: not tested.

**Cost.** Compared on 11 of the 13 cases, the Haiku runs cost $5.78 as Claude Code reported it, and the Sonnet runs of the same cases come to about $11.94 at list prices from their token counts: about half (0.48×). Two cases are left out: scan, whose Haiku run was stopped at the page cap, and consolidate, whose Sonnet run was a short rerun, not the same work. The Sonnet figure is an estimate, likely high: the same arithmetic overstated Opus's reported cost by about 8%. The Sonnet runs were made on earlier heads (#72, #518, #519), so the two models ran slightly different skill text. Haiku read and wrote more tokens than Sonnet in every mode, and its active time was longer in 12 of the 13, with up to four Haiku runs going at once.

## Statistics

From 2026-10-18 to 2026-10-26, the Haiku evaluation (#72's first part, #85, #86, #90, #91, #122, #88) and the model-compatibility phase (#103, #72, #511–#513, #518, #519, #521, #126) made 365 clean-agent runs:

| Model | Runs | Pass | Fail | Partial | Ungraded | Does not count |
|---|---|---|---|---|---|---|
| Haiku | 137 | 72 | 35 | 8 | 11 | 11 |
| Sonnet | 146 | 89 | 42 | 0 | 1 | 14 |
| Opus | 82 (30 of them single-turn skill-trigger runs, #103) | 66 | 4 | 0 | 7 | 5 |

Write took most of the Haiku and Sonnet runs (51 and 108), then fit (47 and 16). Opus's were #103's trigger runs (30) and write (23), then interview (6). Two corrections are applied: #72's v2s-3 is a harness crash, not a Sonnet exit, and does not count (#513). #519's Sonnet scan passed but read about 13 pages against a 10-page cap.

The main failure classes, each line giving the Haiku / Sonnet / Opus count (a few fails fall outside them):
- **A map rule broken:** 15 / 7 / 0. The map's labels, rows or written-by column.
- **The humanizer hand-off:** 7 / 7 / 0. It did not run after the review, or ran with the wrong arguments.
- **Stale provenance:** 1 / 11 / 0. A pointer to an overwritten output, or a lost citation.
- **Output not pasted whole:** 5 / 6 / 0. A tool's output, a diff or a map summarised, cut or reformatted.
- **A step skipped:** 4 / 3 / 0.
- **A subagent set up wrong:** 3 / 1 / 0. Not a read-only type, no model named, or the lookup run inline.
- **A commit outside its gate:** 1 / 3 / 0. A commit before the check passed, a fix-up commit, or a subagent's commit.
- **A user's choice made for them:** 1 / 2 / 1. The Opus count is #126's run without the rule.
- **A board's API read before its page, or the page cap broken:** 0 / 1 / 0. Two scans broke the 10-page cap without counting as a fail: #519's Sonnet run, which passed with a note, and the Haiku round's, which was stopped at the cap and does not count.

The skill changes this period made for cheaper models were mode wording, from #85 through #72's fixes. The last four (#512, #518, #519 and #521) moved what kept failing into tools instead.

## Considered options

- **Support Haiku as well.** Haiku at xhigh costs about half of what Sonnet at medium does, but it failed two modes and went over scan's page cap in a third. It also took longer in nearly every mode. Supporting it would bring back the wording rounds this phase ended.
- **Remove the #518 and #519 rules for Opus only** (two texts, or a model check in the mode). The ablation found no harm from them in write and one extra round trip in interview, so two texts to keep in step would cost more than they save.

