# Import AI chat histories

Before this mode's first step, run the **Trigger check** in [SKILL.md](../SKILL.md); a subagent sent to one step starts at that step.

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

**Claude.ai link file:** if the user hands it over instead of the downloads, run `python3 -I <root>/tools/chat_export.py manifest <file>` (with `--memories` when the user wants the memories) and follow its output.

The user puts the files in `sources/inbox/<platform>/` as they arrived or extracted, in any layout: an extra folder from the unzip tool, an archive inside an archive, or a renamed file are all fine (step 2). Put nothing there until the *Trigger check*'s `gitignore inbox:` step, if it printed one, is done. A Takeout can also contain the user's uploaded files (photos, scans of documents). Tell the user so, and never open those files.

## 2. Index

Run the parser on everything at once. The work directory goes in the agent's scratch space, never inside the repo:

```
python3 -I <root>/tools/chat_export.py index <root>/sources/inbox --out <scratch>/chats
```

Check the per-file counts it prints against what the user expects (`--help` says what it reads and skips). Then act on each warning by the kind it ends with:
- **`[packing]`:** a packing or download problem, not a parser bug. List the file names there (names only, never contents) and show the user which file should hold which platform's export (step 1's table). The user's files stay as they are: never move, rename, unpack in place or delete them. An archive to extract goes into a new empty folder in the scratch space (`7z x`, `tar -xf`, or the user's own tool), and that folder is indexed alongside the inbox; a file missing altogether or broken in the download means the user downloads it again.
- **`[disk]`:** the scratch disk is too full; free space, or extract that archive by hand as for `[packing]`, then run again.
- **`[parser]`:** part of the export was skipped; fix the parser before going on ([import-chats-format.md › Format notes](import-chats-format.md#format-notes)).

If the parser fails on a changed format and you patch it (or work around a broken step here), note what changed and keep going; step 8 reports it. The patch is an Engine change ([engine-changes.md](../engine-changes.md)): commit it on its own branch and pull request, never in the `import:` commit, and run the tests ([import-chats-format.md › Format notes](import-chats-format.md#format-notes)) before asking the user to merge it.

## 3. Screen

1. Read `index.tsv`. Mark each conversation as career-relevant (work, projects, study, applications, interviews, the user's direction and preferences) or not, and keep the marks in `<scratch>/chats/marks.tsv` (its rows: `tally` in `chat_export.py --help`): a category for each one left out, and a group for each relevant one once item 4 makes the groups. Read doubtful ones with `chat_export.py show <scratch>/chats <n> …`.
2. Leave out, without reading further: health, finances and investing, relationships, housing, shopping, travel, entertainment, and whatever the user has already called unimportant. Each one's row names its category.
3. For more than a few hundred relevant conversations, split the reading among subagents ([subagents.md](../subagents.md)), one per platform or a range of conversation numbers. Each prompt's first line is `Read <root>/skills/career-log/modes/import-chats.md whole and do only items 1 and 2 of its step 3 for conversations <numbers> in <scratch>/chats. Reply with the relevant conversation numbers, each with a one-line reason, and the numbers left out, by category; never quote a conversation. Ask the user nothing and write no file.` with `<root>` and `<scratch>` as absolute paths. After it come, as data, the categories the user has already called unimportant. Check their picks before showing them.
4. Show the user numbered groups by topic: what each group would add to which entry, and its conversation numbers and date range, from `python3 -I <root>/tools/chat_export.py tally <scratch>/chats --groups` once each group's rows are in `marks.tsv` as `G<k>`. Put anything doubtful in its own group: work the user might not count as theirs, other people's private matters, a role they might not want recorded. Then wait. The user picks groups, drops some, or corrects what a conversation is about; give each group's rows the status the user's answer gives.

## 4. Extract

```
python3 -I <root>/tools/chat_export.py extract <scratch>/chats --pick <n,n,n-n> --date <today> --out <root>/sources --keys <root>/sources/keys.md
```

It writes each platform's threads and prompts files, prints each extract's key and adds its row to `sources/keys.md` (`--help`: the names, the numbering and what to do on a second run the same day). Done when it has printed every key.

## 5. Check the extract for privacy

Read the written files once, top to bottom. A picked conversation can drift into private ground (a landlord, a health issue, a colleague's personal story). Cut those turns with `python3 -I <root>/tools/chat_export.py cut <threads file> <turns>` (`T3.U2`, or `T3` for a whole conversation), and note the cut in the import log. Cut any extracted conversation the user said was not theirs or does not count the same way, and mark its row `dropped` in `marks.tsv`. Its whole record is the `Dropped:` line of step 7.1, a count and the user's date: write nothing about what it held. *Dropped experiences* in SKILL.md is for entries, and a dropped conversation has none.

## 6. Merge

Continue with [import.md](import.md) from step 3, treating each conversation as a document:
- The user's turns give facts, decisions, reasons, numbers and past phrasings, each cited by its key (`chatgpt-2025-01-31 T4.U2`). A resume bullet or pitch the user typed goes under `## Past phrasings` through `phrasing-add`, as import step 5 says, with its key as the `--source`.
- An assistant turn that restates the user's work is a lead. A number in it is checked against the entries and recorded under `## Conflicts` when it does not match: as an `Open:` line quoting both sides, or as a do-not-use `Settled:` line when the entries contradict it.
- Preferences and reactions to companies go to `direction.md`, cited by their key, as [SKILL.md › Direction upkeep](../SKILL.md#rules-for-every-mode) says. A value for a Direction item or a Config field (a target role, a constraint, a sorting order, a record language) is listed for setup instead, as [import](import.md) step 5 says. Applications, fairs and recruiter contacts go to `applications.md`.
- Questions only the user can answer (who did what, why, whether a claim holds) go to them in one numbered round, as in import step 4.

## 7. Log and clean up

1. Add a section to `sources/import-log.md`: platforms and date ranges, how many conversations were indexed and picked, files written, groups not picked, categories left out with counts, cuts and drops, conflicts, *Found for setup* (item 4 offers each one), and per entry its `state:` line from `python3 -I <root>/tools/entries.py state <entry>... --root <root>` (the gaps themselves stay in the entries). A fact or ruling the user gives during the import goes into its entry with `(user, YYYY-MM-DD)`, never only into this section. Conversations not picked are recorded in exactly the three lines `python3 -I <root>/tools/chat_export.py tally <scratch>/chats` prints, each as its own `- ` list item with its text unchanged: no rewording, bold or added indent.

   Never write what an unpicked group or dropped conversation was about: no title, first prompt, quote, the topic label step 3 gave its group ("interview prep", "a side project"), or any other paraphrase. That text is private and stays out of git.
2. **Check the section before committing.** While `<scratch>/chats/index.tsv` still exists (item 5 deletes it), run `python3 -I <root>/tools/chat_export.py leaks <scratch>/chats --pick <the index numbers still extracted: step 4's, less those cut whole> <root>/sources/import-log.md` (the new section is the file's last). A hit is a leak only when that text describes an unpicked conversation: rewrite it as a count and category. A match on text about picked material (a short title such as "Python" that the section uses for a picked conversation's work) is not a leak and stays. The check is done once every hit has been rewritten or judged not a leak.
3. Commit on the user's yes, as [commits.md › Bulk data changes](../commits.md#bulk-data-changes) says: `import: <n> file(s), <m> entr(y/ies) (<platforms>)`, each noun in the singular or plural its count takes (1 file, 2 files; 1 entry, 0 entries).
4. **Offer the *Found for setup* values**, as [import](import.md) step 7 says: on a yes, each one, one at a time, through [setup › Changes](setup.md#changes); on a no, none, and tell the user in one line that the `.export-deny` lines committed during the merge stay (import step 7 says why). Done when the user has answered each offer, or there was none to make.
5. Delete the scratch work directory and any capture files. The raw exports stay in the ignored `sources/inbox/` until the user moves them to their own backup. Remind them, and never delete them yourself.
6. **Next up**, after items 4 and 5: run the command [SKILL.md › Next up](../SKILL.md#rules-for-every-mode) gives, with `import`.

Done when every exported platform is indexed, every group the user picked is extracted and merged, and the import log records what was left out in the three lines item 7.1 allows; and the user has answered the import: yes (committed and pushed, and each *Found for setup* value offered) or no (undone). The last message ends with the Next up block.

## 8. Report a format change upstream

Only when step 2 or another step needed a fix or a workaround, and only after the import is done: follow [import-chats-format.md › Report upstream](import-chats-format.md#report-upstream).

## Format notes

What the parser handles on each platform, and how to test a change to it, are in [import-chats-format.md › Format notes](import-chats-format.md#format-notes).
