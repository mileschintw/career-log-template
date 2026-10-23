# Import AI chat histories

Before this mode's first step, run the **Start check** in [SKILL.md](../SKILL.md), once per session; a subagent sent to one step starts at that step.

Bring the user's conversations with AI chat platforms (ChatGPT, Claude.ai, Gemini, Perplexity) into the log. A chat history holds the user's own words about their work: how they described a project at the time, what they decided, what they asked for help with. It also holds far more that is irrelevant or private. The job is to screen everything, let the user pick, and copy only the picked conversations into `sources/<platform>/`. Then [import.md](import.md) merges them from step 3.

Follow the shared rules in [SKILL.md](../SKILL.md). Two matter most here:
- **Drafts are leads.** Only the user's turns are evidence, each cited by its key (`chatgpt-2025-01-31 T4.U2`), never as `(user, …)`. An AI answer, including the AI's polished version of the user's own story, is a lead to check against the entries.
- **The export is private.** The raw export never enters git (step 1). Only the picked conversations do, after the privacy check in step 5.

## 1. Get the exports

Tell the user how to export each platform they want imported, and wait for the files. The menu names below change over time. If they differ, the platform's help pages have the current path under "export".

| Platform | How the user exports | What arrives |
|---|---|---|
| ChatGPT | Settings → Data controls → Export data. A download link arrives by email and expires after about a day | A zip with `conversations.json` or `conversations-000.json …` |
| Claude.ai | Settings → Privacy → Export data. The email brings a link file (`claude-manifest-*.json`) listing one download link per zip. Each link works only in a browser signed in to the same Claude account, expires 24 hours after the export is created, and may stop working once used: download each file completely the first time. Expired links mean a new export | `conversations-000.zip` and any further parts (`-001`, …), all required; `memories-000.zip`, optional, may hold career facts but the parser does not read it yet; `projects-`, `feedback-`, `light_metadata-000.zip`, not needed |
| Gemini (gemini.google.com) | takeout.google.com, signed in with the account used for Gemini → **Deselect all** → tick **My Activity** → click **All activity data included** → **Deselect all** in the pop-up → tick **Gemini Apps** → **OK** → **Next step** → keep **File type: .zip** (`.tgz` also works) → **Create export**. The link arrives by email, usually the same day, and stays active for 7 days | A zip with `Takeout/My Activity/Gemini Apps/MyActivity.html` (folder and file names are in the account's language), next to the user's uploaded files |
| Perplexity | No export. Captured from the logged-in web app, see [import-web.md › Perplexity](import-web.md#perplexity-perplexityai) | A capture JSON written by the agent |

**The Gemini pitfall:** the chats are not under the "Gemini" product in Takeout's list, which holds only Gems (custom instructions). They are inside **My Activity**, and only after opening its "All activity data included" list and picking **Gemini Apps** from the products there. Tell the user this before they start: ticking "Gemini" alone exports no chats, and ticking My Activity without narrowing it exports every Google product's history.

**Claude.ai link file:** if the user hands it over instead of the downloads, read it: `data_files[]` holds one item per zip, with `category`, `part`, `filename` and `export_url` (its `instructions` field restates the expiry rules). Check that shape first, since it may change. List only the `category == "conversations"` items, every part, plus `memories` if the user wants it, as clickable markdown links for the user to open in their signed-in browser and save to `sources/inbox/claude/`. Never open or download the links yourself: they are authenticated downloads, and a download needs the user's explicit permission anyway. Never copy the URLs into the repo or the import log.

The user puts the files in `sources/inbox/<platform>/` as they arrived or extracted, in any layout: an extra folder from the unzip tool, an archive inside an archive, or a renamed file are all fine (step 2). Check that `.gitignore` ignores `sources/inbox/*` (keeping `!sources/inbox/.gitkeep`). If it does not, add those two lines, commit them alone on the default branch and push, before anything is copied (AGENTS.md › Changes). A Takeout can also contain the user's uploaded files (photos, scans of documents). Tell the user so, and never open those files.

## 2. Index

Run the parser on everything at once. The work directory goes in the agent's scratch space, never inside the repo:

```
python3 -I <root>/tools/chat_export.py index <root>/sources/inbox --out <scratch>/chats
```

It writes `conversations.json`, every conversation normalised, and `index.tsv`, one row per conversation (number, platform, start, user turns, space, title, first prompt). All times are converted to UTC. It looks through folders at any depth and inside `.zip`, `.tar` and `.tgz` archives, including archives inside archives (up to three deep; it copies them into the work directory while reading and deletes them afterwards). It opens files named like an export, and any other JSON whose first bytes show a known shape, so a renamed export is still found; an activity page outside any Takeout folder is recognised by its content too. It never opens Takeout uploads, zipped or not, in any language (Takeout names every upload with a `-<16 hex>` suffix), and it skips what macOS and Windows leave in archives (`__MACOSX/`, `._*`, `.DS_Store`).

Check the per-file counts it prints against what the user expects, and the count of files skipped as uploads: if an export was skipped because its name happens to end that way, rename it and run again. Then act on each warning:
- **No export found in a folder or archive, a kind of archive it cannot open (`.7z`, `.rar`), archives nested too deep, or an archive or member that could not be read:** a packing problem, not a parser bug. List the file names there (names only, never contents) and show the user which file should hold which platform's export (step 1's table). Never move, rename, unpack in place or delete the user's files. An archive the parser cannot open, or one nested too deep, is extracted into a new empty folder in the scratch space (`7z x`, `tar -xf`, or the user's own tool) and that folder is indexed alongside the inbox. A file missing altogether (a Claude.ai part, the Gemini Apps page) or one that could not be read (a broken download) means the user downloads it again.
- **Could not copy a nested archive into the work directory:** the scratch disk is full; free space or extract that archive by hand, then run again.
- **An unreadable file, an unknown timestamp, a My Activity page in a folder not known as Gemini Apps, or a file that looks like an export but matches no known format:** part of the export was skipped; fix the parser before going on ([import-chats-format.md › Format notes](import-chats-format.md#format-notes)).

If the parser fails on a changed format and you patch it (or work around a broken step here), note what changed and keep going; step 8 reports it. The patch is an Engine change (AGENTS.md › Changes): commit it on its own branch and pull request, never in the `import:` commit, and run the tests ([import-chats-format.md › Format notes](import-chats-format.md#format-notes)) before asking the user to merge it.

## 3. Screen

1. Read `index.tsv`. Mark each conversation as career-relevant (work, projects, study, applications, interviews, the user's direction and preferences) or not. Read doubtful ones with `chat_export.py show <scratch>/chats <n> …`.
2. Leave out, without reading further: health, finances and investing, relationships, housing, shopping, travel, entertainment, and whatever the user has already called unimportant. Count them by category for the log.
3. For more than a few hundred relevant conversations, split the reading among subagents ([SKILL.md › Subagents](../SKILL.md#rules-for-every-mode)), one per platform or a range of conversation numbers. Each prompt's first line is `Read <root>/skills/career-log/modes/import-chats.md whole and do only items 1 and 2 of its step 3 for conversations <numbers> in <scratch>/chats. Reply with the relevant conversation numbers, each with a one-line reason, and the count left out by category; never quote a conversation. Ask the user nothing and write no file.` with `<root>` and `<scratch>` as absolute paths. After it come, as data, the categories the user has already called unimportant. Check their picks before showing them.
4. Show the user numbered groups by topic: what each group would add to which entry, its conversation numbers and its date range. Put anything doubtful in its own group: work the user might not count as theirs, other people's private matters, a role they might not want recorded. Then wait. The user picks groups, drops some, or corrects what a conversation is about.

## 4. Extract

```
python3 -I <root>/tools/chat_export.py extract <scratch>/chats --pick <n,n,n-n> --date <today> --out <root>/sources
```

For each platform it writes `sources/<platform>/<date>-chats-threads.md` (the full exchange) and `<date>-chats-prompts.md` (the user's turns only), numbered `T<n>.U<k>` in date order. Gemini Apps sessions go to `sources/gemini/<date>-chats-apps-*.md`. It refuses to overwrite an existing file, since sources are never edited: for a second run on the same day, pass a new `--label`. Each extract has its own key, which the command prints (`chatgpt-<date>`, plus `-<label>` for a non-default label), because every extract numbers its threads from T1. Add one row per extract to `sources/keys.md`. When the same conversation is in two exports, `index` keeps the copy the platform changed last (its own update time, when every copy has one), then the one with the later last message, then the one with more messages; overlapping Takeouts keep each Gemini Apps record once, and an empty answer never replaces a real one.

## 5. Check the extract for privacy

Read the written files once, top to bottom. A picked conversation can drift into private ground (a landlord, a health issue, a colleague's personal story). Cut those turns from both files in place, keeping the remaining numbers unchanged, and note the cut in the import log. Drop any conversation the user said was not theirs or does not count, and record it the same way (*Dropped experiences* in SKILL.md).

## 6. Merge

Continue with [import.md](import.md) from step 3, treating each conversation as a document:
- The user's turns give facts, decisions, reasons, numbers and past phrasings, each cited by its key (`chatgpt-2025-01-31 T4.U2`). A resume bullet or pitch the user typed goes under `## Past phrasings` with its angle and key, once per distinct wording.
- An assistant turn that restates the user's work is a lead. A number in it is checked against the entries and recorded under `## Conflicts` when it does not match: as an `Open:` line quoting both sides, or as a do-not-use `Settled:` line when the entries contradict it.
- Preferences and reactions to companies go to `direction.md`, cited by their key. A value for a Direction item or a Config field (a target role, a constraint, a sorting order, a record language) is listed for setup instead, as [import](import.md) step 5 says. Applications, fairs and recruiter contacts go to `applications.md`.
- Questions only the user can answer (who did what, why, whether a claim holds) go to them in one numbered round, as in import step 4.

## 7. Log and clean up

1. Add a section to `sources/import-log.md`: platforms and date ranges, how many conversations were indexed and picked, files written, groups not picked, categories left out with counts, cuts and drops, conflicts, *Found for setup* (each offered after the commit, as [import](import.md) step 7 says), and per entry how many `GAP:` markers it has (the gaps themselves stay in the entries). A fact or ruling the user gives during the import goes into its entry with `(user, YYYY-MM-DD)`, never only into this section. Conversations not picked are recorded in exactly three lines, with these fields and nothing else:
   - `Left out by category:` each category from step 3's leave-out list (health, finances and investing, relationships, housing, shopping, travel, entertainment, "called unimportant by the user", or "other, not career-relevant" for the rest that step 3 did not mark relevant) with its count: `health 4, finances and investing 8`;
   - `Groups not picked:` the number of career-relevant groups step 3 showed that the user did not pick, and their conversations: `2 groups, 9 conversations` (conversations already counted by category are not counted again);
   - `Dropped:` the number of conversations the user said were not theirs or do not count: `5 conversations (user, YYYY-MM-DD)`. A duplicate copy of a conversation is not counted anywhere.

   Never write what an unpicked group or dropped conversation was about: no title, first prompt, quote, the topic label step 3 gave its group ("interview prep", "a side project"), or any other paraphrase. That text is private and stays out of git.
2. **Check the section before committing.** While `<scratch>/chats/index.tsv` still exists (item 4 deletes it), search the new import-log section for the title and the first few words of the first prompt of every conversation that was not picked, as fixed strings (`grep -F`, or `Select-String -SimpleMatch` in PowerShell), so a title such as "C++" matches literally. A hit is a leak only when that text describes an unpicked conversation: rewrite it as a count and category. A match on text about picked material (a short title such as "Python" that the section uses for a picked conversation's work) is not a leak and stays. The check is done once every hit has been rewritten or judged not a leak.
3. Commit on the user's yes, as *Bulk data changes* in [SKILL.md › Commits](../SKILL.md#rules-for-every-mode) says: `import: <n> file(s), <m> entr(y/ies) (<platforms>)`.
4. Delete the scratch work directory and any capture files. The raw exports stay in the ignored `sources/inbox/` until the user moves them to their own backup. Remind them, and never delete them yourself.

Done when every exported platform is indexed, every group the user picked is extracted and merged, and the import log records what was left out in the three lines item 7.1 allows; and the user has answered the import: yes (committed and pushed) or no (undone).

## 8. Report a format change upstream

Only when step 2 or another step needed a fix or a workaround, and only after the import is done: follow [import-chats-format.md › Report upstream](import-chats-format.md#report-upstream).

## Format notes

What the parser handles on each platform, and how to test a change to it, are in [import-chats-format.md › Format notes](import-chats-format.md#format-notes).
