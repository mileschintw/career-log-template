# Mode: upgrade

Move this Log to a newer Template release: replace the Engine with the release's, run the upgrade guide of each release in between, put back this Log's own Engine edits, and commit on the user's yes. Why it works this way: [ADR 0011](../../../docs/adr/0011-template-versions-and-upgrades.md).

This mode has no *Trigger check*: the check is part of the Engine it replaces, and an old one can stop on what the upgrade fixes. Its step 1 pulls the Log itself.

Placeholders: `<root>` is the Log's root, `<py>` is `python3` (`py -3` on Windows, [SKILL.md › Platforms](../SKILL.md#platforms)), `<url>` is the Template's repo, https://github.com/mileschintw/career-log-template.git, unless the user names another (a fork they made their Log from), `<tool>` is `<root>/.build/upgrade/tools/upgrade.py`. Commit with the Log's local git identity (`git -C <root> config --local user.email`; when it is unset, stop and ask the user: the global one may belong to someone else).

## 1. Start, from the target release

1. `git -C <root> status --short` prints nothing. When it lists files, show them to the user and ask: commit them or discard them first. The upgrade starts only from a clean tree, so the commit before it is the whole backup. Then `git -C <root> pull --ff-only`.
2. Fetch the releases and pick the target: the newest, or the version the user named.
   ```
   git -C <root> fetch --no-tags <url> "+refs/tags/v*:refs/career-log-upgrade/v*"
   git -C <root> for-each-ref --sort=-v:refname --count=1 "--format=%(refname)" refs/career-log-upgrade/
   ```
   The second line prints the newest release's ref (`refs/career-log-upgrade/v<version>`); for a version the user named, the ref is `refs/career-log-upgrade/v<that version>`.
3. Take the target's tool and this mode's file as the target has them, into `<root>/.build/upgrade/` (`.gitignore` leaves `.build/` out); this writes those two files there and leaves the Log's index and working tree as they are:
   ```
   mkdir -p <root>/.build/upgrade
   git -C <root> --work-tree=<root>/.build/upgrade restore --source=<ref> --worktree -- tools/upgrade.py skills/career-log/modes/upgrade.md
   ```
   In Windows PowerShell, the first line is `New-Item -ItemType Directory -Force <root>/.build/upgrade | Out-Null`.
4. Read `<root>/.build/upgrade/skills/career-log/modes/upgrade.md`. When its text differs from this file's, it is the newer mode: follow it from its step 2, in place of this file.

Done when `<tool>` exists and you are following the target's text of this mode.

## 2. Plan

`<py> -I <tool> plan <root>`, with `--to <version>` when the user named one and `--url <url>` when `<url>` is not the default. It prints:
- **`OK:`** the Log is at the target already: tell the user, run `<py> -I <tool> clean <root>`, and end the mode.
- **`stop:` with `before 0.1.0`:** the Log was made before the first release. Follow the guide the line names (`<root>/.build/upgrade/upgrade-0.1.0.md`) whole, with the user; once it is done, start this mode again from step 1. When the line names no guide, the target release does not ship one (0.1.0 itself does not): ask the user for a later target and run `plan` again with `--to`.
- **`stop: uncommitted changes`:** settle them as step 1 item 1 does, then run `plan` again.
- **`stop: this Log's version <x> has no release tag`, or `stop: … says next`:** the Log's own release is unknown. Show the line to the user and ask which release the Log came from. With an answer, write that version as the first line of `tools/TEMPLATE_VERSION`, commit it as `upgrade: name the Log's Template release`, and run `plan` again; with none, run `clean` and end the mode.
- **`stop: no release v<x> at <url>`:** show the user the releases the line lists, and run `plan` again with `--to` set to the one they pick.
- **`stop: no release tags at <url>`:** `<url>` holds no release: check it with the user, as for a failed fetch below.
- **`error:`** (a git call failed, exit 2): show it to the user. A failed fetch is the network or `<url>`: fix it with them and run `plan` again; for any other, run `clean` and end the mode.
- **The plan:** `from:`, `to:`, `start:`, one `step:` line per release in order, and the Engine files this Log changed since `from:`. Keep `start:`: it is the commit the upgrade can go back to. When `to:` is not the version of step 1's ref, go back to step 1 with `to:`'s version, so that the tool and this text are that release's.

Tell the user, in one message: the versions from and to, each step, and what happens to the Engine files the Log changed, then ask whether to go on:
- `edited:` files are replaced by the new release's; their version stays in git history, and step 4 offers to merge their edits into the new Engine.
- `added:` files are the Log's own, and stay.
- `overwritten:` files are the Log's own too, at a path a release on the way uses for its own file: the release's replaces it, and the Log's version stays in git history (`git -C <root> show <start>:<path>`); offer to move its content to another path after step 3.
- `removed:` files come back, as the release has them.
- `dropped:` files are Engine files the new release no longer has: a step deletes them (an edited one shows again in step 4).
- The Log's own `.gitignore` lines are put back after each step, with no question.

Done when the user has said yes to the plan, or the mode has ended at `OK:` or a `stop:` the user chose not to settle now.

## 3. One release at a time

For each `step: <version>`, in order:
1. `<py> -I <tool> engine <root> <version>`. Its `done:` lines are what it changed. On `stop: the next step of the plan is <v>`, run `engine` with `<v>`; on `stop: uncommitted changes`, do item 3 for the step before, or, on the first step, settle them as step 1 item 1 does.
2. **`guide: <file>`:** follow that guide with the user, all of it. It may start another mode, such as setup; that mode commits as usual, with `--no-push` right after `commit` in each `sync.py commit` and `sync.py settle commit`: every push waits for step 5. **`guide: none`:** the release changed no Log format; go on.
3. Commit everything the step changed:
   ```
   git -C <root> add -A
   git -C <root> commit -m "upgrade: Template <version>" -m "The upgrade to the released Template <version> (the upgrade mode), not an Engine change to review."
   ```
   The body keeps [AGENTS.md › Changes](../../../AGENTS.md#changes)' rule for an Engine commit on the default branch from being applied to it later.

Done when `git -C <root> log --oneline <start>..HEAD` lists an `upgrade: Template <version>` commit for every `step:` line, and `git -C <root> status --short` prints nothing.

## 4. This Log's Engine edits

Only when the plan printed `edited:` lines. Ask the user, in one numbered message, for each edited file: merge their edits into the new Engine, or keep the release's version. Preselected: merge. Then `<py> -I <tool> reapply <root> <path>...` with the paths to merge (`--all` for every edited file); when the user keeps the release's version of every file, skip `reapply`. For each line it prints:
- **`merged: <path>`:** show the user `git -C <root> diff -- <path>`, one hunk at a time: what they had changed, and where it now sits in the new text. A hunk they no longer want goes back to the release's text.
- **`conflict: <path>: <n>`:** the file holds `<n>` conflicts between `<<<<<<< this Log` and `>>>>>>> <to>`. Show each to the user with both sides, write the text they choose, and remove the markers.
- **`review: <path>`:** the new release has no such file. Show the user their version (`git -C <root> show <start>:<path>`) and ask whether to keep it as their own file, written back at that path, or let it go.

Then commit, with `--allow-empty` (every file may keep the release's version), as `upgrade: this Log's Engine edits on Template <to>`, with the body `The upgrade to the released Template <to> (the upgrade mode), not an Engine change to review.`, and the files kept at the release's version listed in it (`Kept the release's version: <paths>`), so a later session can merge them from `git -C <root> show <start>:<path>`.

Done when every edited file has the user's answer, `git -C <root> grep -n "^<<<<<<< this Log"` finds nothing, and `git -C <root> status --short` prints nothing.

## 5. The user's yes

Show the user `git -C <root> log --oneline <start>..HEAD`, `git -C <root> diff --stat <start>..HEAD` and a short summary per step, and ask them to read the full diff in their editor. Then:
- **Yes:** `git -C <root> push`.
- **A change:** make it, commit it as `upgrade: <what changed>`, and show the log and stat again.
- **Undo the whole upgrade:** on their explicit yes to dropping every commit since `start:`, `git -C <root> reset --hard <start>`; nothing else is lost, since the tree was clean at `start:`.

Then `<py> -I <tool> clean <root>`.

Done when the user has said yes and `git -C <root> rev-list --count '@{upstream}..HEAD'` prints `0`, or the Log is back at `<start>`; and `<root>/.build/upgrade/` is gone.

## 6. Other machines and clones

Tell the user what every other clone needs: `git -C <root> pull --ff-only`, then each machine step a guide of step 3 named (a guide says when one of its steps runs on every machine).
