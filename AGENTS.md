# AGENTS.md

This repo is a personal career log (a Log, with its Engine; see [GLOSSARY.md](GLOSSARY.md)), managed through the `career-log` skill in `skills/career-log/`. Read `skills/career-log/SKILL.md`, the skill entry point (the modes are in `skills/career-log/modes/`), before creating or editing anything here; its rules (provenance, attribution, gaps) apply to every file.

Tool names in the skill (subagents, `Explore`, the PowerShell tool) are Claude Code's; use your agent's equivalent, or do the work inline.

Edit the skill here, in the repo, so changes are versioned.

## Machines

The log may be cloned on more than one machine (macOS, Windows, Linux). Per-machine setup (git identity, skill link, LaTeX toolchain) is in [SETUP.md](SETUP.md); the cross-platform rules for commands are in [SKILL.md › Platforms](skills/career-log/SKILL.md#platforms).

## Changes

Log data (entries, profile, direction, applications, outputs, sources) is committed as [SKILL.md › Commits](skills/career-log/SKILL.md) says. Engine changes change how the agent behaves: every path in the `ALLOW` list of `tools/export-template.sh` (the skill, the tools and the Template skeleton in `tools/template/`, `SETUP.md`, this file and `CLAUDE.md`, `GLOSSARY.md`, `docs/adr/`, `docs/social-preview/`, `.gitignore`, `.gitattributes`, `entries/_template.md`).

Engine changes never go straight to the default branch: work on a branch in a worktree (under `.worktrees/`, or where the agent's tooling puts them) started from the default branch, as for data branches (`worktree add --no-track … origin/<default>`, [SKILL.md › Commits](skills/career-log/SKILL.md)), open an issue describing the change, then commit and push the branch as often as the work needs: the push backs the work up and lets another machine see it. Open the pull request, with `Closes #<issue>`, only once the change is finished: the issue's fix is done and the local checks the change touches have run (an export to a scratch directory with `tools/export-template.sh` after any Engine change, `tools/tests/test_chat_export.py` after a change to the parser or its tests), so the user reviews one finished diff. Once it is open, gather the fixes from a review and push them together, not one push per fix. Merge only when the user says so. Without `gh` or a GitHub remote, show the user the branch's diff instead, and merge it locally with `git merge --no-ff` only on their yes. Two guard files are exceptions: the names the `import` and `log` modes append to `.export-deny`, and the `sources/inbox/` lines that import-chats step 1 restores to `.gitignore`. Both go straight to the default branch at once, even during a bulk data session, because they protect the main checkout and every export made from it. A session that does both commits the data and the Engine change separately, each its own way. To take back an Engine commit that went straight to the default branch, revert it there and re-land it through a pull request; never rewrite the published history.

## Sharing

`tools/export-template.sh <dest>` builds the shareable Template: the Engine (`skills/`, `tools/`, `SETUP.md`, this file and `CLAUDE.md`, `GLOSSARY.md`, `docs/adr/`, `docs/social-preview/social-preview.svg`) plus the empty Log skeleton in `tools/template/`. Keep every Engine file free of personal content: no names, employers, projects, dates or quotes from this Log. Those belong in the Log files (`direction.md`, entries). It exports committed content only, so commit before exporting. It scans file names and contents for the patterns in `.export-deny` and fails on a hit; the `import` and `log` modes append new employer and project names, and the export refuses an empty list.

A Log made from the Template has no CI: after an Engine change, run the checks [SETUP.md](SETUP.md) step 7 lists for what changed, and report their results before asking the user to merge.

