# Upgrade a Log from 0.3.0 to 0.3.1

For the agent running the upgrade mode (`skills/career-log/modes/upgrade.md`) at 0.3.1's step. The mode has replaced the Engine with 0.3.1's and copied this guide and its script into `<root>/.build/upgrade/`; follow the steps below with the user, in order, then go back to the mode. Talk to the user in their language; the files stay in the Log's record language.

Placeholders: `<root>` is the Log's root, `<py>` the Python the mode uses, `<script>` is `<root>/.build/upgrade/upgrade-0.3.1.py`. The script prints one line per thing the Log still has in the old format; each line starts with its kind: `apply:` its `--apply` makes the change, `migrate:` you make it by hand, `ask:` the user decides, `review:` you show it to the user, who may keep it as it is, `later:` it waits for a later mode, `done:` `--apply` changed it. It exits 1 while an `apply:`, `migrate:` or `ask:` line is left, and 0 with `OK: nothing left to migrate`.

## Changes

One line per change to the Log's data format, with the pull request that made it and the step below that migrates it.

No Log format change yet.

## 1. Mechanical changes

`<py> -I <script> <root> --apply`, then `<py> -I <script> <root>`.

Done when the second run prints no `apply:` line.

## 2. By hand and with the user

Each `migrate:` line, as its item below says. Then the `ask:` and `review:` lines in one numbered message, each with its preselected answer, so the user can answer every item at once; write the answers and run `<py> -I <script> <root>` again.

Done when it prints `OK: nothing left to migrate` (a `review:` line the user chose to keep may stay).

## 3. New settings

Each Config field and Direction item 0.3.1 adds, listed here: the setup mode's *Changes* (`skills/career-log/modes/setup.md`) for each, with the user.

- `plan_preview` (Config, default `"ask"`): after a fit learning plan, a Plan preview: the resume bullets and the heatmap as they would read once the planned projects land, each number a goal marked `<target: …>`, shown in chat and written to `<root>/plan-previews/`, which git ignores. `"ask"` offers it with each plan, `"always"` makes it, `"never"` does not. Ask which the user wants; preselect `"ask"`.

Done when every new setting is answered or left at its default on the user's word.

## 4. Check

1. `<py> -I <root>/tools/check.py log`: the last line is `next: go on with the mode`, and every other `next:` line is the one for the `log change:` lines of the files this guide changed, which the mode commits next.
2. `<py> -I <root>/tools/entries.py check --root <root>` (the root as `--root`, the form 0.3.1's tool takes): no finding a step above names.
3. `<py> -I <script> <root>`: `OK: nothing left to migrate`.

Done when items 1 to 3 hold; the mode commits this step.
