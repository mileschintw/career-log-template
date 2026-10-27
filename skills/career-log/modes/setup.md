# Mode: setup

Before this mode's first step, run the **Trigger check** in [SKILL.md](../SKILL.md).

Sets up this Log's Direction and Config, and this machine's optional tool ([GLOSSARY.md](../../../GLOSSARY.md): Direction, Config, Machine setup), and makes every later change to them. Its *Trigger check* is `check.py setup`. In this mode, the check's `next: now, for <tool>` lines are the install step's work, done after the user has heard *Quick* step 2's notice about the install: at *Quick* step 5, in *Changes* for the tool, or else at *Advanced* step 3. After a no to the install, drop the *Trigger check*'s `next: now, for <tool>` lines, `playwright-cli install --skills` included: the install step follows only the lines its own setup run prints. A setup started for one *Changes* request that touches no tool runs none of those lines (the mode that next needs the tool runs its line then), and still runs the check's other `next: now` lines, its pull included. *Advanced* step 3 still runs them. While one of them asks to run the check again, the check prints no `next: go on with the mode`; the mode goes on with its next step, and *Quick* step 5's check is the one that waits for that line.

The names setup may change are the ones `python3 -I <root>/tools/config.py fields` prints: each Config field with its allowed values, and each Direction item with where it lives in `direction.md`. Map every answer and every change request onto those names, and onto nothing else.

**Which path.**
- A request to change something ("write my records in Chinese from now on", "don't read LinkedIn profiles"): *Changes*.
- The check printed `config: missing`: *Quick*, or *Advanced* when the user asked for it.
- Anything else: *Advanced*.

## Quick

1. **Read the state.** The *Trigger check*'s `playwright-cli wanted:` and `front page:` state lines.
2. **Ask one round,** all items in one numbered message, keeping the numbers below when an item is left out, each with its preselected answer, so the user can answer every item at once or accept them all:
   1. **Target roles,** best first (for example backend engineer, then platform engineer)? Skip to leave it empty.
   2. **Work authorisation and other hard constraints:** does any role need a sponsorship, citizenship or clearance you lack? If you need US visa sponsorship: H-1B, and a green card too? On a student's work authorisation (OPT, CPT), which? Any location, start date or level that rules a role out? Skip to leave it empty.
   3. **Record language** for your Log files? Preselected: English.
   4. **Install playwright-cli on this machine?** It reads web pages that show their content only after their scripts run or you sign in: Node, the CLI and a browser, about 1 GB with TinyTeX, which installs either way. Preselected: yes. Leave this item out when the `playwright-cli wanted:` line says yes or no: this machine has its answer.
   5. **Trim the front page** into a personal index of your records (keeps Entries, Upstream and License, points at the guide, and deletes the Chinese translation)? Preselected: yes. Only when that `front page:` state line says `template`.

   Under the items, tell the user that the install is for their user only and asks for no password. On Linux, one step can need sudo (Chromium's system libraries, for playwright-cli): it is printed for them to run in their own terminal, never run for them.
3. **Write the answers.**
   - `python3 -I <root>/tools/config.py init`, then `python3 -I <root>/tools/config.py set record_language "<answer>"` unless the answer is English.
   - Item 1: `python3 -I <root>/tools/config.py direction set "target roles" "<role>"...`, best first. Item 2: `direction set "work authorisation" "<answer>"`; when the user needs US visa sponsorship or works on OPT or CPT, `direction set "visa sponsorship" "<value>"`: `H-1B`, `H-1B; green card (PERM)` when they want a green card too, `green card (PERM)` for a green card alone, `OPT` or `CPT` for the student's authorisation, joined with `; ` to the visa they need next (`H-1B; OPT`); when their answer needs no US visa sponsorship and names neither OPT nor CPT (a citizen or permanent resident), `direction set "visa sponsorship" "none"`, so the item reads as set; then `direction set "other hard constraints" "<constraint>"...`, or `none` when the user has none. A skipped item stays as it is.
   - Item 5, on yes: `python3 -I <root>/tools/config.py set front_page trimmed` (it rewrites `README.md` and deletes `README.zh-TW.md`, which step 4 stages).
   - A refusal is shown to the user as it stands; that item stays unwritten.
4. **Commit:** `python3 -I <root>/tools/sync.py commit "setup: quick" -- config.toml direction.md README.md README.zh-TW.md`. Done when it ends with `sync: ok`.
5. **Install:** run [SETUP.md](../../../SETUP.md) step 5 items 2 to 4 with the answer to item 4 (`--yes playwright-cli` or `--no playwright-cli`; neither when item 4 was left out). Done when step 5's check holds.
6. **Close.** Name what is still empty: each `direction <item>: empty` or `unreadable` line of `python3 -I <root>/tools/config.py show` (for `unreadable`, say what it says is missing). A mode that needs one says so and goes on. To fill one later, the user says it in their own words or asks for advanced setup.
7. **Next up**, after the close: run the command [SKILL.md › Next up](../SKILL.md#rules-for-every-mode) gives, with `setup` (and `--for <mode>` when that mode's *Trigger check* started this setup). Then take up the request the *Trigger check* stopped, if there was one, starting with its check.

## Advanced

1. **Show the state,** in one numbered message, current values preselected: every Config field (`python3 -I <root>/tools/config.py show`; `(default)` marks a field the file leaves out; when the check printed `config: missing`, run `config.py init` first, then `python3 -I <root>/tools/sync.py commit "setup: init" -- config.toml`), every Direction item with its current lines (the same command's `direction <item>:` lines), and the `playwright-cli wanted:` answer for this machine. When `resume_max_pages` shows `(default)` and `profile.md` or the entries show 10+ years of experience, preselect 2 and say why. Before the tool item, give *Quick* step 2's notice about the install.
2. **Take the user's changes** through *Changes*, steps 2 to 4. Anything they leave as shown stays as it is.
3. **Close.** Carry out any `next: now, for <tool>` line no change has run, as *Quick* step 5 does with neither flag; then close as *Quick* step 6 says. Done when every item the user changed is written and committed, and `config.toml` is committed.
4. **Next up**, after the close: run the command [SKILL.md › Next up](../SKILL.md#rules-for-every-mode) gives, with `setup` (and `--for <mode>` when that mode's *Trigger check* started this setup). Then take up the request the *Trigger check* stopped, if there was one, as *Quick* step 7 does.

## Changes

A change, asked for in advanced setup or stated in any mode (it runs inside that mode, with no check of its own), is written one field at a time:
1. **Map** the request onto the names `config.py fields` prints, and only the ones it changes: "write my records in Chinese from now on" is `record_language`, nothing else. A request that maps onto no name: say so, and ask what they want changed.
2. **Show** each field before and after: run step 3's command with `--dry-run`.
   - A Config field: `python3 -I <root>/tools/config.py set <field> "<value>" --dry-run`.
   - `target roles`, `other hard constraints`: `python3 -I <root>/tools/config.py direction set "<item>" "<line>"... --dry-run`, the item's whole new list: the list lines `config.py show` prints for it that the user keeps, and the new ones (a kept line given no indented lines keeps its own).
   - `work authorisation`, `visa sponsorship`, `sorting order`: the same with the one new line ("I don't need visa sponsorship" is `visa sponsorship` `none`, or `OPT` or `CPT` alone while they work on it); `what to emphasise`: the one new line and `--target "<target>"`, the target's label as `show` prints it.
   - A line with indented lines under it that changes: right after the new line, its indented lines as arguments, each with the indentation `show` prints (a new one indented like the others, or, with none, by the width of its line's list mark: three spaces under `1. `, two under `- `): the ones that still hold as they stand, the others rewritten to fit the new line. A line that stays and needs its indented lines changed: give its whole new set the same way.
   - The tool: `yes` or `no`.

   Say each `tell the user:` and `front page:` line. `drops:` lines are indented lines the change deletes: a rewritten line shows up there too, under its old text. Show them with the before and after: the user's yes to that dry run, `drops:` lines included, is the yes to add `--drop-indented` to step 3's command; never add it without one. Draft the kept or rewritten indented lines yourself rather than asking whether to drop them or edit by hand. `unchanged`: no change; say so, and leave it out of step 3. A refusal: show it as it stands, and write nothing for that field.
3. **Write it on the user's yes:** step 2's command without `--dry-run`; for the tool, SETUP.md step 5 items 2 to 4 with `--yes playwright-cli` or `--no playwright-cli`, after *Quick* step 2's notice about the install. A new `record_language` applies to what is written from now on; existing files are translated only when the user asks. On a no, write nothing. Inside a mode, the run follows the user's statement either way, in place of the check's line: the yes decides only whether it is written for later runs.
4. **Commit:** `python3 -I <root>/tools/sync.py commit "setup: <fields>" -- <file>...`, naming each changed file. Done when it ends with `sync: ok`.
5. **Next up**, only when the change was the request itself, not stated inside another mode or in advanced setup: run the command [SKILL.md › Next up](../SKILL.md#rules-for-every-mode) gives, with `setup`.
