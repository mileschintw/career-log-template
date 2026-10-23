# Mode: setup

Before this mode's first step, run the **Start check** in [SKILL.md](../SKILL.md), once per session.

Sets up this Log's Direction and Config, and this machine's optional tool ([GLOSSARY.md](../../../GLOSSARY.md): Direction, Config, Machine setup), and makes every later change to them. Its *Trigger check* is `check.py setup`. In this mode, the check's `next: now, for <tool>` lines are the install step's work, done after the user has heard about the dialogs: at *Quick* step 5, in *Changes* for the tool, or else at *Advanced* step 3.

The names setup may change are the ones `python3 -I <root>/tools/config.py fields` prints: each Config field with its allowed values, and each Direction item with where it lives in `direction.md`. Map every answer and every change request onto those names, and onto nothing else.

**Which path.**
- A request to change something ("write my records in Chinese from now on", "don't read LinkedIn profiles"): *Changes*.
- The check printed `config: missing`: *Quick*, or *Advanced* when the user asked for it.
- Anything else: *Advanced*.

## Quick

1. **Read the state.** The check's `playwright-cli wanted:` line, and whether the front page is still the Template's: `python3 -c "import sys; a, b = (open(p, encoding='utf-8-sig').read().split('## How to use')[0] for p in sys.argv[1:]); print('template' if a == b else 'edited')" <root>/README.md <root>/tools/template/README.md`.
2. **Ask one round,** all items in one numbered message, keeping the numbers below when an item is left out, each with its preselected answer, so the user can answer every item at once or accept them all:
   1. **Target roles,** best first (for example backend engineer, then platform engineer)? Skip to leave it empty.
   2. **Work authorisation and other hard constraints:** does any role need a sponsorship, citizenship or clearance you lack? Any location, start date or level that rules a role out? Skip to leave it empty.
   3. **Record language** for your Log files? Preselected: English.
   4. **Install playwright-cli on this machine?** It reads web pages that show their content only after their scripts run or you sign in: Node, the CLI and a browser, about 1 GB with TinyTeX, which installs either way. Preselected: yes. Leave this item out when the `playwright-cli wanted:` line says yes or no: this machine has its answer.
   5. **Trim the front page** into a personal index of your records (keeps How to use, Your setup, Entries, Files, Upstream and License, and deletes the Chinese translation)? Preselected: yes. Only when step 1 printed `template`.

   Under the items, tell the user what this machine's install may open: on a Mac without Homebrew, the system's password dialog, to install Homebrew; on Windows without the Visual C++ runtime, the UAC dialog, which may wait behind a flashing shield button on the taskbar. They answer it at the machine, and the password goes to the operating system, never to this chat. On Linux, a step that needs sudo is printed for them to run in their own terminal.
3. **Write the answers.**
   - `python3 -I <root>/tools/config.py init`, then `python3 -I <root>/tools/config.py set record_language "<answer>"` unless the answer is English.
   - Target roles: a numbered list under `direction.md › Target roles, ranked`, best first, each role followed by `(user, YYYY-MM-DD)`. Work authorisation: `- **Work authorisation:** <answer> (user, YYYY-MM-DD)` under `direction.md › Constraints`, and each other hard constraint its own bullet there, with the same source. "None" is an answer: write it (`- **Other hard constraints:** none (user, YYYY-MM-DD)`). A skipped item stays as it is.
   - Trim, on yes: replace the part of `README.md` above `## How to use` with the line `# career-log` and the line `Raw records of my past work, projects and achievements, and the resumes and answers derived from them.`, each followed by a blank line, keep the rest unchanged, delete the file `README.zh-TW.md` from disk (step 4 stages the deletion), and run `python3 -I <root>/tools/config.py set front_page trimmed`. The Template's page in `tools/template/` stays whole.
4. **Commit** with `git -C <root> add -A -- config.toml direction.md README.md README.zh-TW.md`, as `setup: quick`, and push. Done when `git -C <root> status --short` lists none of those files.
5. **Install:** run [SETUP.md](../../../SETUP.md) step 5 items 3 to 5 with the answer to item 4 (`--yes playwright-cli` or `--no playwright-cli`; neither when item 4 was left out); the user has heard about the dialogs in step 2. Done when step 5's check holds.
6. **Close.** Name what is still empty, with the two items Quick does not ask (`sorting order`, `what to emphasise`): a mode that needs one says so and goes on. To fill one later, the user says it in their own words or asks for advanced setup. Then take up the request the *Trigger check* stopped, if there was one, starting with its check.

## Advanced

1. **Show the state,** in one numbered message, current values preselected: every Config field (`python3 -I <root>/tools/config.py show`; `(default)` marks a field the file leaves out; when the check printed `config: missing`, run `config.py init` first, then commit it as `setup: init` and push), every Direction item with its current lines from `direction.md` (an item with no line, or only a `GAP:` line: empty), and the `playwright-cli wanted:` answer for this machine. Before the tool item, give *Quick* step 2's notice about dialogs.
2. **Take the user's changes** through *Changes*, steps 2 to 4. Anything they leave as shown stays as it is.
3. **Close.** Carry out any `next: now, for <tool>` line no change has run, as *Quick* step 5 does with neither flag; then close as *Quick* step 6 says. Done when every item the user changed is written and committed, and `config.toml` is committed.

## Changes

A change, asked for in advanced setup or stated in any mode (it runs inside that mode, with no check of its own), is written one field at a time:
1. **Map** the request onto the names `config.py fields` prints, and only the ones it changes: "write my records in Chinese from now on" is `record_language`, nothing else. A request that maps onto no name: say so, and ask what they want changed.
2. **Show** each field before and after. A field whose new value equals its current one (a `(default)` included) is no change: say so, and write nothing. Otherwise: `python3 -I <root>/tools/config.py set <field> "<value>" --dry-run` for a Config field (it refuses a name or value it does not allow); the current and new lines of `direction.md` for a Direction item; `yes` or `no` for the tool. For `interviewer_profiles` going to `always`, say with it that the site may show each interviewer the visit unless the user's account browses privately, and that its terms may limit automated reading.
3. **Write it on the user's yes:** `config.py set <field> "<value>"`; the new `direction.md` lines with `(user, YYYY-MM-DD)`, replacing the lines they change ([SKILL.md › Direction upkeep](../SKILL.md#rules-for-every-mode)); for the tool, SETUP.md step 5 items 3 to 5 with `--yes playwright-cli` or `--no playwright-cli`, after *Quick* step 2's notice about dialogs. `front_page = "trimmed"` is *Quick* step 3's trim. Once the page is trimmed, `front_page` stays `trimmed`: tell the user the Template's page is in `tools/template/README.md` and git history, for them to restore by hand, and set `full` only after they have. A new `record_language` applies to what is written from now on; existing files are translated only when the user asks. On a no, write nothing. Inside a mode, the run follows the user's statement either way, in place of the check's line: the yes decides only whether it is written for later runs.
4. **Commit** the changed files by name, as `setup: <fields>`, and push. Done when `git -C <root> status --short` lists none of them.
