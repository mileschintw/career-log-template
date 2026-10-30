# Upgrade a Log from 0.2.1 to 0.3.0

For the agent running the upgrade mode (`skills/career-log/modes/upgrade.md`) at 0.3.0's step. The mode has replaced the Engine with 0.3.0's and copied this guide and its script into `<root>/.build/upgrade/`; follow the steps below with the user, in order, then go back to the mode. Talk to the user in their language; the files stay in the Log's record language.

Placeholders: `<root>` is the Log's root, `<py>` the Python the mode uses, `<script>` is `<root>/.build/upgrade/upgrade-0.3.0.py`. The script prints one line per thing the Log still has in the old format; each line starts with its kind: `apply:` its `--apply` makes the change, `migrate:` you make it by hand, `ask:` the user decides, `review:` you show it to the user, who may keep it as it is, `later:` it waits for a later mode, `done:` `--apply` changed it. It exits 1 while an `apply:`, `migrate:` or `ask:` line is left, and 0 with `OK: nothing left to migrate`.

## Changes

One line per change to the Log's data format, with the pull request that made it and the step below that migrates it.

- Each entry keeps its status in its front matter, `status:` (#573), and `README.md`'s Entries table is generated from the entries' front matter (#574): columns Period, Entry, Type and Status (no Tags), one row per plain entry and one per series (its short name in bold, then a link per part, newest first), and `tools/entries.py readme` writes it whole. `readme-row` and `readme-sort` are gone: `set-status` writes a status, and `new`, `period`, `split` and `drop` write the table themselves. Step 1 copies each README row's status into its entry's front matter, where the entry has none, then writes the table; step 2 settles the entries and rows it cannot.

## 1. Mechanical changes

`<py> -I <script> <root> --apply`, then `<py> -I <script> <root>`.

Done when the second run prints no `apply:` line.

## 2. By hand and with the user

Each `migrate:` line, as its item below says. Then the `ask:` and `review:` lines in one numbered message, each with its preselected answer, so the user can answer every item at once; write the answers, then run `<py> -I <script> <root> --apply` (it writes the table once every entry has a status and every `ask:` row is answered) and `<py> -I <script> <root>` again.

- `ask: <entry>: no status: ...`: the entry has no `status:`, and its README row gave none, or none that reads. Ask the user for its status (SKILL.md › Layout: `stub`, mostly `GAP`; `imported`, filled from documents or repos, not yet consolidated; `consolidated`), preselecting the one the entry reads as, `stub` when unsure, with the row's note in parentheses when it had one. Write the answer by hand as the line `status: <status>` before the front matter's closing `---`: `entries.py set-status` would rewrite the table before the other lines are settled.
- `ask: README.md:<n>: <cells>: links no entry ...`: a row of the old Entries table that links no entry (a note the user kept there). Ask whether to keep it as a line under the table (preselected) or drop it. Either way, delete the row from the table; to keep it, also write its text as a plain line after the table's last row, with a blank line between.
- `migrate: README.md: README table not generated: ...`: `README.md` has no place for the table. Add a `## Entries` heading where it goes (`tools/template/README.md` has it before `## Upstream`), then `<py> -I <root>/tools/entries.py readme --root <root>`.

Done when it prints `OK: nothing left to migrate` (a `review:` line the user chose to keep may stay).

## 3. New settings

Each Config field and Direction item 0.3.0 adds, listed here: the setup mode's *Changes* (`skills/career-log/modes/setup.md`) for each, with the user.

This release adds none.

Done when every new setting is answered or left at its default on the user's word.

## 4. Check

1. `<py> -I <root>/tools/check.py log`: the last line is `next: go on with the mode`, and every other `next:` line is the one for the `log change:` lines of the files this guide changed, which the mode commits next.
2. `<py> -I <root>/tools/entries.py check --root <root>` (the root as `--root`, the form 0.3.0's tool takes): no finding a step above names.
3. `<py> -I <script> <root>`: `OK: nothing left to migrate`.

Done when items 1 to 3 hold; the mode commits this step.
