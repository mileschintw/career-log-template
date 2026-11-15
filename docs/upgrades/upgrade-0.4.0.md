# Upgrade a Log from 0.3.2 to 0.4.0

For the agent running the upgrade mode (`skills/career-log/modes/upgrade.md`) at 0.4.0's step. The mode has replaced the Engine with 0.4.0's and copied this guide and its script into `<root>/.build/upgrade/`; follow the steps below with the user, in order, then go back to the mode. Talk to the user in their language; the files stay in the Log's record language.

Placeholders: `<root>` is the Log's root, `<py>` the Python the mode uses, `<script>` is `<root>/.build/upgrade/upgrade-0.4.0.py`. The script prints one line per thing the Log still has in the old format; each line starts with its kind: `apply:` its `--apply` makes the change, `migrate:` you make it by hand, `ask:` the user decides, `review:` you show it to the user, who may keep it as it is, `later:` it waits for a later mode, `done:` `--apply` changed it. It exits 1 while an `apply:`, `migrate:` or `ask:` line is left, and 0 with `OK: nothing left to migrate`.

## Changes

One line per change to the Log's data format, with the pull request that made it and the step below that migrates it.

- A Story in `stories.md` may carry a name (#695): an item's link takes the name as its title, `[<label>](entries/<file>.md#<anchor> "<name>")`, a slug, and the Story's key is then `entries/<file>.md#<anchor>~<name>`, so the Stories of one section are told apart. A key with no name keeps its meaning, the whole section as one Story, so no Log needs a change; `tools/entries.py story-name` names an item. Step 2 offers names where one section is listed under several types.

## 1. Mechanical changes

`<py> -I <script> <root> --apply`, then `<py> -I <script> <root>`.

Done when the second run prints no `apply:` line.

## 2. By hand and with the user

Each `migrate:` line, as its item below says. Then the `ask:` and `review:` lines in one numbered message, each with its preselected answer, so the user can answer every item at once; write the answers and run `<py> -I <script> <root>` again.

- `review: stories.md: <key>: no name, in <n> rows: <types>`: one section of an entry is listed under several question types with no name, so `story-coverage` counts it as one Story. Propose names as the stories mode's step 1 says for a line that ends with the name hint (`skills/career-log/modes/stories.md`; each row's label and summary: `<py> -I <root>/tools/entries.py story-candidates "<type>" --root <root>`), and write the names the user accepts as it says. The preselected answer is your proposal; the user may accept it, change it, or keep the key as it is (the whole section as one Story).

Done when it prints `OK: nothing left to migrate` (a `review:` line the user chose to keep may stay).

## 3. New settings

Each Config field and Direction item 0.4.0 adds, listed here: the setup mode's *Changes* (`skills/career-log/modes/setup.md`) for each, with the user.

- **`conversation_language`** (Config; default empty: the language the user writes in): the language the agent talks to the user in, a BCP 47 tag with its script and region (`zh-Hant-TW`). When `direction.md` holds a line on the languages the user wants (often under `## Writing preferences for applications`), propose the tag for the conversation language it names; otherwise propose the language the user is writing in. Name the language in words, and on the user's yes run `<py> -I <root>/tools/config.py set conversation_language "<tag>"`. Then propose trimming that line to what Config does not cover (the language of an output: practice answers in English, cover letters in German), and edit it on the user's yes.

Done when every new setting is answered or left at its default on the user's word.

## 4. Check

1. `<py> -I <root>/tools/check.py log`: the last line is `next: go on with the mode`, and every other `next:` line is the one for the `log change:` lines of the files this guide changed, which the mode commits next, or the one that runs `tools/sync.py pull` (printed when the Log's branch has an upstream), which you follow first.
2. `<py> -I <root>/tools/entries.py check --root <root>` (the root as `--root`, the form 0.4.0's tool takes): no finding a step above names.
3. `<py> -I <script> <root>`: `OK: nothing left to migrate`.

Done when items 1 to 3 hold; the mode commits this step.
