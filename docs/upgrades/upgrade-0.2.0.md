# Upgrade a Log from 0.1.0 to 0.2.0

For the agent running the upgrade mode (`skills/career-log/modes/upgrade.md`) at 0.2.0's step. The mode has replaced the Engine with 0.2.0's and copied this guide and its script into `<root>/.build/upgrade/`; follow the steps below with the user, in order, then go back to the mode. Talk to the user in their language; the files stay in the Log's record language.

Placeholders: `<root>` is the Log's root, `<py>` the Python the mode uses, `<script>` is `<root>/.build/upgrade/upgrade-0.2.0.py`. The script prints one line per thing the Log still has in the old format; each line starts with its kind: `apply:` its `--apply` makes the change, `migrate:` you make it by hand, `ask:` the user decides, `review:` you show it to the user, who may keep it as it is, `later:` it waits for a later mode, `done:` `--apply` changed it. It exits 1 while an `apply:`, `migrate:` or `ask:` line is left, and 0 with `OK: nothing left to migrate`.

## Changes

One line per change to the Log's data format, with the pull request that made it and the step below that migrates it.

- `README.md`'s Entries table keeps one order: rows with a `GAP` in the period first, then the ongoing rows by start, then the rest by end, newest first, and a series' rows stay together, newest part first, the block sorted by the series' earliest start and latest end as `entries.py readme-sort` in its `--help` says (#372); the tools now write each row in place (#292). Step 1 sorts the table once, series included; the rows move, and no cell changes.
- A scan report's `## Fit maps` keeps each row's kind (`required`, `preferred` or `duty`) in a `Kind` column, and `tools/scan.py report` writes its `## Ranking` and `## Not fitted` itself (#301). No step migrates it: old reports are not migrated, and a map an old report holds, reused by a later scan, ranks on every row until it is fitted again.
- A report `write` saves in `outputs/reports/` holds a `Kind: <kind>` line above its approved text; a `Kind: resume bullets` report feeds `## Past phrasings`, cited by its path, and when saved Archived holds the line `Archived (user, YYYY-MM-DD)` under it (#304). Nothing to migrate: a report saved before has no `Kind:` line, feeds nothing, and stays as it is; the save check reads a report only when it is saved.
- A `Kind: resume bullets` report holds a `## Risks to handle in conversation` section after its provenance table, as a resume's provenance file does, and `tools/check_save.py` fails a save without it; `tools/application.py` names, copies, demotes and reads back application folders and sent versions, in the layout they already had (#306). Nothing to migrate: a bullets report saved before has no such section, and `tools/application.py risks` prints `risks: none` for it.
- `direction.md`'s Direction items are read and written by `tools/config.py` (`show`, `direction set`), which finds each one under its section's Template heading: `## Target roles, ranked`, `## Employer preferences`, `## Constraints`, `## What to emphasise, by target` (#299). Step 2 renames a heading the Log wrote differently; the lines under it stay.
- `direction.md › Constraints` may hold a `**Visa sponsorship needed:**` line (`H-1B`, `green card (PERM)`, both as `H-1B; green card (PERM)`, or `none`), the Direction item `visa sponsorship` that `tools/config.py` writes; while it names a visa, fit, scan, write and rank look up each employer's H-1B LCA (and PERM) filings without being asked, and keep them in `outputs/reports/sponsorship.jsonl`, which the first lookup creates (#284). Each of its lines names the pages read (`sources`) and how recent their data is (`data_date`), and may name the `parent` company whose records it holds, or say why no read answered it (`unanswered`), as `tools/sponsorship.py --help` says; a line written before these fields still reads (#284). The line also takes `OPT` and `CPT`, alone or joined to a visa (`H-1B; OPT`): they ask for no lookup, and fit and scan quote a posting's wording (and in scan its employer's) that asks for unrestricted work authorisation or keeps out F-1 or J-1 students, as a requirement the user may not meet (#377). Step 3 asks for the line; nothing else migrates.
- `sources/keys.md`'s line under its title now says that `tools/chat_export.py extract --keys` writes a chat extract's row (#387). Step 1 replaces 0.1.0's line with 0.2.0's; a line the user edited stays as it is.

## 1. Mechanical changes

`<py> -I <script> <root> --apply`, then `<py> -I <script> <root>`.

Done when the second run prints no `apply:` line.

## 2. By hand and with the user

Each `migrate:` line, as its item below says. Then the `ask:` and `review:` lines in one numbered message, each with its preselected answer, so the user can answer every item at once; write the answers and run `<py> -I <script> <root>` again.

- `migrate: README.md: tools/entries.py readme-sort cannot read it: ...`: README.md has no Entries table the tool reads. Give it the Template's: a `## Entries` section with a table headed `| Period | Entry | Type | Tags | Status |`, holding the Log's rows (one per entry: `python3 -I <root>/tools/entries.py readme-row <entry> --root <root> --status <status>`), then run the script again.
- ``migrate: direction.md: tools/config.py cannot read <items>: direction.md has no `## <heading>` section``: find the section that holds those items under another heading (`## Target roles`, say) and rename that heading to `## <heading>`, keeping its lines; when there is none, add `## <heading>` from `tools/template/direction.md`, with its comment. Then run the script again.
- `migrate: direction.md: tools/config.py cannot read <items>: direction.md is missing`: copy `tools/template/direction.md` to the root, then run the script again.
- `review: direction.md: <line> speaks of visa sponsorship, and no **Visa sponsorship needed:** line says which`: the user wrote the need in their own words (in work authorisation, or a `**Visa:**` line), which no tool reads. Leave it out of this round: step 3's `visa sponsorship` question shows that line and answers it; their own line stays as it is.
- `migrate: direction.md: its Visa sponsorship needed line cannot be read: ...`: the line holds a value the tools do not read (`yes`, say). Ask the user which of step 3's values it means and write it with `<py> -I <root>/tools/config.py direction set "visa sponsorship" "<value>"`, then run the script again.
- Any other `migrate: direction.md: ...` line (`cannot be read`, `show failed`): fix what it names (a `direction.md` not saved as UTF-8, say, or the Engine's `tools/config.py` as the mode replaced it), then run the script again.

Done when it prints `OK: nothing left to migrate` (a `review:` line the user chose to keep may stay).

## 3. New settings

Each Config field and Direction item 0.2.0 adds, listed here: the setup mode's *Changes* (`skills/career-log/modes/setup.md`) for each, with the user.

- `update_check` (Config, default `"on"`): the *Trigger check* now says when a newer Template release exists, asking GitHub at most once a day and sending nothing from the Log. Ask whether to keep it on.
- `resume_max_pages` (Config, default `1`): the most pages `tools/resume.py` lets a resume have. Ask whether to keep 1; preselect 2 when `profile.md` or the entries show 10+ years of experience, and say why.
- `visa sponsorship` (Direction, a `**Visa sponsorship needed:**` line in `direction.md › Constraints`, empty by default): does the user need US visa sponsorship, or work on a student's authorisation: `H-1B`, `H-1B; green card (PERM)` for a green card too, `green card (PERM)` alone (already on another visa), `OPT` or `CPT` (joined to the visa they need next: `H-1B; OPT`), or `none`? Show their work authorisation line, and any `review:` line step 2's script printed, with the question; preselect from them when they say the user needs H-1B or a green card, or is on OPT or CPT. While the line names a visa, fit, scan, write and rank look up each employer's H-1B LCA (and PERM) filings without being asked; while it names OPT or CPT, fit and scan quote each posting's wording that asks for unrestricted work authorisation or keeps out F-1 or J-1 students. Tell the user that, left empty, nothing is looked up unless they ask, even when work authorisation says they need sponsorship: before 0.2.0 a one-posting fit looked LCA records up from that line's wording.

Also tell the user, with nothing to change now: `tools/resume.py`'s checks are stricter in 0.2.0 (a wrapped bullet's last line must fill 60% of the width, not 25%; a Skills line may not wrap; the source may hold no placeholder, unescaped character or Unicode dash), so a resume in `outputs/` that passed before may fail its next build. `write` fixes it in the words when it next builds that resume.

Done when every new setting is answered or left at its default on the user's word.

## 4. Check

1. `<py> -I <root>/tools/check.py log`: the last line is `next: go on with the mode`, and each other `next:` line is one of these two, which this step leaves to the mode: the one for the `log change:` lines of the files this guide changed (the mode commits them next), and the `sync.py pull` line.
2. `<py> -I <root>/tools/entries.py check --root <root>` (the root as `--root`, the form 0.2.0's tool takes): no finding a step above names.
3. `<py> -I <script> <root>`: `OK: nothing left to migrate`.

Done when items 1 to 3 hold; the mode commits this step.
