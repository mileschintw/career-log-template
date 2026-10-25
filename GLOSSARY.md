# Career log

A git repo of one person's raw career records, plus the skill and tools that turn those records into resumes and application material.

## Language

**Engine**:
The parts of the repo that run a Log rather than record it: the `career-log` skill, `tools/`, the setup and agent instructions, and the other paths [AGENTS.md › Changes](AGENTS.md#changes) lists.
_Avoid_: framework, code, the skill (when the tools are meant too)

**Log**:
One person's career records: entries, sources, outputs, profile, direction, stories and applications.
_Avoid_: data, content, my repo

**Template**:
A shareable repo holding the Engine and an empty Log skeleton, from which someone starts their own private Log.
_Avoid_: clean version, starter, fork

**Release**:
One published version of the Template, a semver tag `v<version>` on its public repo with a GitHub Release; a Log names the one it came from in `tools/TEMPLATE_VERSION`. A **breaking** release changes a Log's data format and ships an **upgrade guide**, `docs/upgrades/upgrade-<version>.md`, which the upgrade mode runs with the user. A release that only adds a setting (a Config field with a default, or a Direction item) is not breaking, but ships a guide too, whose `## 3. New settings` asks about it; a release that changes only the Engine needs none.
_Avoid_: update, snapshot, publish (when the versioned release is meant)

**Example**:
A fictional person's records shipped inside the Engine to show the format and to test the setup; never part of anyone's Log.
_Avoid_: sample entry, demo data, dummy

**Writing standards**:
Rules for outputs that hold for anyone, kept in the Engine; a person's own preferences stay in their Log's direction.
_Avoid_: style guide, writing preferences (that is the personal part)

**Direction**:
What the user wants: target roles (ranked), the sorting order for employers, work authorisation and other hard constraints, what to emphasise per target. Log content in `direction.md`, each line with its source; no defaults, so an item with no line, or only a `GAP:` line, is empty. Formerly part of "settings".
_Avoid_: setting, preference (`direction.md` uses "preferences" for its own content)

**Config**:
A choice about how the Engine runs for one Log, each with a safe default: the record language, whether to read interviewer profiles only signed-in members can see (default `never`), whether the front page is trimmed, and how far back and how much a scan collects, screens, fits and drafts. Kept in `config.toml` at the Log root, committed; a field left out takes its default from `tools/config.default.toml`. No `config.toml` means setup has not run for that Log. Formerly part of "settings".
_Avoid_: setting, preference, option

**Save level**:
Whether a saved application or bullets report feeds later runs (**Reference**, the default) or is kept only as the record of what was sent (**Archived**); chosen per run, and the rules are in write's Save levels.
_Avoid_: draft (an Archived application was sent), record (that word is the Log's)

**Story**:
One concrete point of an experience (an entry, or a whole series), recorded in one of its sections, that can answer behavioural interview questions; its facts live only in the entry, and a long experience holds many Stories. A **core Story** is an experience the user marked core: one of the few they reuse across many question types, from different angles.
_Avoid_: anecdote, example

**Talking points**:
The spoken route for one behavioural question type: the Stories chosen for it in order of preference, an opening line, and cue lines in telling order that each point at an entry section. It holds no facts and is not a script; the user confirms it, and it is checked again when an entry it points at changes.
_Avoid_: answer (that is a written form answer), script, answer outline

**Durable source**:
A source that stays and can be linked: the user's repos, PRs, issues and ADRs, and the files in a Log's `sources/`; an entry links it and does not copy it.
_Avoid_: reference, permanent source

**Perishable source**:
A source that disappears or cannot be linked, such as an agent session transcript; the passages a fact cites are copied into an excerpt in `sources/`, which is durable from then on.
_Avoid_: temporary source, ephemeral source

**Series**:
One experience split into several entries, one per part a reader would pick for a posting (a project within a long job, a phase within a long project), each standing alone and naming the earliest part's slug in `series:`; consolidate splits an entry that is still over the size threshold once it holds only what belongs.
_Avoid_: sub-entry, chapter, entry folder

**Machine setup**:
Whether the user wants each optional tool on one machine (playwright-cli, with Node, its skill and a browser), kept as a yes or no per tool in `~/.career-log/machine.toml`, outside every repo; whether a tool is installed is detected by `tools/check.py` on every run, never stored. TinyTeX is required, so it has no yes or no; the same file records where poppler came from (setup's micromamba environment, or the user's own).
_Avoid_: config, environment, settings (for this)

**Screen**:
The step of a scan between the prefilter and fit: for each of up to `screen_budget` captured postings, the gate on the full text, the tier, and a rough coverage that matches the posting's requirements against the one-line entry list, never entry bodies. Its top `fit_budget` go on to fit; the rest are reported as screened, not fully fitted, and compete again in a later scan whose window still holds them, with their Screen result reused while the entry list and the direction it was made on are unchanged.
_Avoid_: light fit, pre-fit, triage

**Draft branch**:
The throwaway branch `scan/<YYYY-MM-DD>[-<n>]` on which a scan keeps its drafts, one folder per posting with a decisions table and a hand-off note; pushed so any session can pick a draft up, never merged, and deleted once every draft is accepted or declined, or after 90 days.
_Avoid_: scan branch, staging branch

**Dashboard**:
One read-only HTML page of the scan's results (pending postings, the newest ranking, declined postings, applications, scan history), generated by a tool from the Log and committed beside it, then published as a private hosted page where the agent can publish one. The Log stays the source: the page is regenerated, never edited.
_Avoid_: tracker, board, report (for this)

**Browser capture**:
Reading a web source that shows its content only after its scripts run or the user signs in; a page a plain fetch can read is not one.
_Avoid_: advanced operation, scraping, crawling

## Languages

**Conversation language**:
Whatever language the user talks to the agent in.

**Record language**:
The language Log files are written in, a Config field (`record_language`); the user's own words are paraphrased in it, and their original wording, when it came from a session, is kept in an excerpt.
_Avoid_: log language, entry language

**Output language**:
The language of one output, chosen for that output.
