# Import AI chat histories

Bring the user's conversations with AI chat platforms (ChatGPT, Claude.ai, Gemini, Perplexity) into the log. A chat history holds the user's own words about their work: how they described a project at the time, what they decided, what they asked for help with. It also holds far more that is irrelevant or private. The job is to screen everything, let the user pick, and copy only the picked conversations into `sources/<platform>/`. Then [import.md](import.md) merges them from step 3.

Follow the shared rules in [SKILL.md](../SKILL.md). Two matter most here:
- **Drafts are leads.** Only the user's turns are `(user, …)` evidence. An AI answer, including the AI's polished version of the user's own story, is a lead to check against the entries.
- **The export is private.** The raw export never enters git (step 1). Only the picked conversations do, after the privacy check in step 5.

## 1. Get the exports

Tell the user how to export each platform they want imported, and wait for the files. The menu names below change over time. If they differ, the platform's help pages have the current path under "export".

| Platform | How the user exports | What arrives |
|---|---|---|
| ChatGPT | Settings → Data controls → Export data. A download link arrives by email and expires after about a day | A zip with `conversations.json` or `conversations-000.json …` |
| Claude.ai | Settings → Privacy → Export data. The email brings a link file (`claude-manifest-*.json`) listing one download link per zip. Each link works only in a browser signed in to the same Claude account, expires 24 hours after the export is created, and may stop working once used: download each file completely the first time. Expired links mean a new export | `conversations-000.zip` and any further parts (`-001`, …), all required; `memories-000.zip`, optional, may hold career facts but the parser does not read it yet; `projects-`, `feedback-`, `light_metadata-000.zip`, not needed |
| Gemini (gemini.google.com) | takeout.google.com, signed in with the account used for Gemini → **Deselect all** → tick **My Activity** → click **All activity data included** → **Deselect all** in the pop-up → tick **Gemini Apps** → **OK** → **Next step** → **Create export**. The link arrives by email, usually the same day, and stays active for 7 days | A zip with `Takeout/My Activity/Gemini Apps/MyActivity.html` (folder and file names are in the account's language), next to the user's uploaded files |
| Perplexity | No export. Captured from the logged-in web app, see [import-web.md › Perplexity](import-web.md#perplexity-perplexityai) | A capture JSON written by the agent |

**The Gemini pitfall:** the chats are not under the "Gemini" product in Takeout's list, which holds only Gems (custom instructions). They are inside **My Activity**, and only after opening its "All activity data included" list and picking **Gemini Apps** from the products there. Tell the user this before they start: ticking "Gemini" alone exports no chats, and ticking My Activity without narrowing it exports every Google product's history.

**Claude.ai link file:** if the user hands it over instead of the downloads, read it: `data_files[]` holds one item per zip, with `category`, `part`, `filename` and `export_url` (its `instructions` field restates the expiry rules). Check that shape first, since it may change. List only the `category == "conversations"` items, every part, plus `memories` if the user wants it, as clickable markdown links for the user to open in their signed-in browser and save to `sources/inbox/claude/`. Never open or download the links yourself: they are authenticated downloads, and a download needs the user's explicit permission anyway. Never copy the URLs into the repo or the import log.

The user puts the files, zipped or extracted, in `sources/inbox/<platform>/`. Check that `.gitignore` ignores `sources/inbox/*` (keeping `!sources/inbox/.gitkeep`). If it does not, add those two lines, commit them on the default branch in the main checkout and push, before anything is copied and before the `data/` worktree below exists, if one is started (AGENTS.md › Changes). A Takeout can also contain the user's uploaded files (photos, scans of documents). Tell the user so, and never open those files.

## 2. Index

If the data-branch flow is on ([SKILL.md › Commits](../SKILL.md)), first start the import's `data/` worktree and run this and every later command from it, so `extract` writes into the branch; the worktree has no copy of the ignored inbox, so the exports are read from the main checkout `<main>`. Run the parser on everything at once. The work directory goes in the agent's scratch space, never inside the repo:

```
python3 -I tools/chat_export.py index <main>/sources/inbox --out <scratch>/chats
```

It writes `conversations.json`, every conversation normalised, and `index.tsv`, one row per conversation (number, platform, start, user turns, space, title, first prompt). All times are converted to UTC. Only files named like an export are opened, and Takeout uploads never are, zipped or not, in any language (Takeout names every upload with a `-<16 hex>` suffix). Check the per-file counts it prints against what the user expects, and the count of files skipped as uploads: if an export was skipped because its name happens to end that way, rename it and run again. A warning about an unreadable file, an unknown timestamp, or a My Activity page in a folder not known as Gemini Apps means part of the export was skipped; fix the parser before going on (*Format notes* below).

If the parser fails on a changed format and you patch it (or work around a broken step here), note what changed and keep going; step 8 reports it.

## 3. Screen

1. Read `index.tsv`. Mark each conversation as career-relevant (work, projects, study, applications, interviews, the user's direction and preferences) or not. Read doubtful ones with `chat_export.py show <scratch>/chats <n> …`.
2. Leave out, without reading further: health, finances and investing, relationships, housing, shopping, travel, entertainment, and whatever the user has already called unimportant. Count them by category for the log.
3. For more than a few hundred relevant conversations, split the reading among read-only subagents (`Explore`), one per platform or topic. Each returns conversation numbers with a one-line reason, never quotes of private material. Check their picks before showing them.
4. Show the user numbered groups by topic: what each group would add to which entry, its conversation numbers and its date range. Put anything doubtful in its own group: work the user might not count as theirs, other people's private matters, a role they might not want recorded. Then wait. The user picks groups, drops some, or corrects what a conversation is about.

## 4. Extract

```
python3 -I tools/chat_export.py extract <scratch>/chats --pick <n,n,n-n> --date <today> --out sources
```

For each platform it writes `sources/<platform>/<date>-chats-threads.md` (the full exchange) and `<date>-chats-prompts.md` (the user's turns only), numbered `T<n>.U<k>` in date order. Gemini Apps sessions go to `sources/gemini/<date>-chats-apps-*.md`. It refuses to overwrite an existing file, since sources are never edited: for a second run on the same day, pass a new `--label`. Each extract has its own key, which the command prints (`chatgpt-<date>`, plus `-<label>` for a non-default label), because every extract numbers its threads from T1. Add one row per extract to `sources/keys.md`. When the same conversation is in two exports, `index` keeps the copy with the later last message (then the one with more messages).

## 5. Check the extract for privacy

Read the written files once, top to bottom. A picked conversation can drift into private ground (a landlord, a health issue, a colleague's personal story). Cut those turns from both files in place, keeping the remaining numbers unchanged, and note the cut in the import log. Drop any conversation the user said was not theirs or does not count, and record it the same way (*Dropped experiences* in SKILL.md).

## 6. Merge

Continue with [import.md](import.md) from step 3, treating each conversation as a document:
- The user's turns give facts, decisions, reasons, numbers and past phrasings, each cited by its key (`chatgpt-2025-01-31 T4.U2`). A resume bullet or pitch the user typed goes under `## Past phrasings` with its date and target.
- An assistant turn that restates the user's work is a lead. A number in it is checked against the entries and recorded under `## Conflicts` when it does not match.
- Preferences, targets and reactions to companies go to `direction.md`. Applications, fairs and recruiter contacts go to `applications.md`.
- Questions only the user can answer (who did what, why, whether a claim holds) go to them in one numbered round, as in import step 4.

## 7. Log and clean up

1. Add a section to `sources/import-log.md`: platforms and date ranges, how many conversations were indexed and picked, files written, groups not picked, categories left out with counts, cuts and drops, conflicts, and the gaps that matter most.
2. Commit and push: `import: <n> file(s), <m> entr(y/ies) (<platforms>)`. On a `data/` branch, open the pull request when the session's work is done ([SKILL.md › Commits](../SKILL.md)).
3. Delete the scratch work directory and any capture files. The raw exports stay in the ignored `sources/inbox/` until the user moves them to their own backup. Remind them, and never delete them yourself.

Done when every exported platform is indexed, every group the user picked is extracted and merged, and the import log records what was left out and why.

## 8. Report a format change upstream

Only when step 2 or another step needed a fix or a workaround, and only after the import is done:
1. Tell the user what broke (which platform, which file, what the parser expected and what it found) and what you changed.
2. Offer to send it to the Template's upstream repo, https://github.com/mileschintw/career-log-template, named in the Template `README.md` under *Upstream*. If this repo has a `.export-allow` file at its root, it is the Template's own source (that file is never exported, so no copy made from the Template has one): fix the Engine here and republish instead (AGENTS.md › Sharing).
3. Draft the report. It describes the change with a redacted structural sample: keys, types and nesting only, with no message text, names, ids, dates or URLs. Nothing in it may come from the user's Log.
4. Post nothing until the user says yes to that specific draft. Then send it one of two ways:
   - **Issue** (public, so anyone can read it): show the user the full body first. It follows the repo's "Chat export format changed" form: platform, what broke, the redacted sample, the parser change, the Template version (the commit the user's repo was created from, or "unknown"). Then `gh issue create -R mileschintw/career-log-template --title "<platform>: <what changed>" --body-file <scratch>/issue.md`.
   - **Pull request:** a repo made with "Use this template" shares no git history with upstream, so it cannot open a PR from itself. Send only the user's own change, never whole files: their copy of the Engine may be older than upstream, and a copied file would undo upstream's later work. Make the patch against the commit the repo was created from (its first commit, `git -C <root> rev-list --max-parents=0 HEAD`): `git -C <root> diff --output=<scratch>/fix.patch <first commit> -- tools/ skills/` (`--output`, not `>`: Windows PowerShell 5.1 writes redirected output as UTF-16, which `git apply` rejects), then cut every hunk that isn't this fix. Fork and clone upstream into the scratch space (`gh repo fork mileschintw/career-log-template --clone`), `git apply --3way <scratch>/fix.patch` there, and if it does not apply cleanly, show the user the conflict and offer the issue instead. Check the diff holds nothing from the Log, commit, and `gh pr create` with the same body as the issue.

## Format notes

What the parser handles, for fixing it when a platform changes its format:
- **ChatGPT:** each conversation is a tree (`mapping`). The visible thread is `current_node` followed up through `parent`. User messages on other branches are edited prompts, kept as `T<n>.A<k>` because the first wording is sometimes the more honest one. Skip messages marked `is_visually_hidden_from_conversation` (system and tool scaffolding).
- **Claude.ai:** `chat_messages[]`, `sender` `human` or `assistant`. Pasted files are in `attachments[].extracted_content` and are kept. Uploaded files (`files[]`) are not in the export.
- **Gemini Apps:** an activity log, not conversations. Each `outer-cell` div is one prompt with its answer. The timestamp is localised (for example `Mar 5, 2026, 2:01:00 PM PST`, or the Chinese form with a period word such as 清晨 or 下午 before the hour; `ZH_AM`/`ZH_PM` list them). A record with an unknown form is skipped with a warning, so add the form rather than ignore the warning. Only "Prompted" records and "Branched" ones (a prompt asked again on a new branch) become user turns. A Canvas Gemini wrote ("Created Gemini Canvas titled …") becomes an assistant turn, since its body is AI text, and bookkeeping records ("Used Gemini Apps", feedback) are dropped with a count. Time-zone names map to UTC through `TZ_HOURS`; an unknown name is read as UTC with a warning. The Gemini Apps folder name is localised too: `GEMINI_FOLDERS` lists the known names, and a My Activity page in an unknown folder is skipped with a warning, so add the name. The parser skips uploads by their `-<16 hex>` suffix, merges records from every Takeout given (each counts once by its time and its prompt or Canvas title, with the most recent Takeout's non-empty answer), and groups prompts into sessions at gaps over 45 minutes (`--gap`, at least 1). Some answers are missing or empty in the export, and attachments appear only as file names.
- **Perplexity:** the capture JSON is `[{slug, title, space, entries: [{t, q, a, att}]}]`, written by the recipe in [import-web.md](import-web.md).
