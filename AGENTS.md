# AGENTS.md

This repo is a personal career log (a Log, with its Engine; see [GLOSSARY.md](GLOSSARY.md)), managed through the `career-log` skill in `skills/career-log/`. Read `skills/career-log/SKILL.md`, the skill entry point (the modes are in `skills/career-log/modes/`), before creating or editing anything here; its rules (provenance, attribution, gaps) apply to every file.

Asked what this repo is or can do, where to start or what to do next ("introduce this repo and set me up"): read [docs/guide.md](docs/guide.md) and follow its *For agents*.

Tool names in the skill (subagents, `Explore`, the PowerShell tool) are Claude Code's; use your agent's equivalent, or do the work inline.

Edit the skill here, in the repo, so changes are versioned.

## Machines

The log may be cloned on more than one machine (macOS, Windows, Linux). Per-machine setup (git identity, skill link, optional tools: [Machine setup](GLOSSARY.md)) is in [SETUP.md](SETUP.md); the cross-platform rules for commands are in [SKILL.md › Platforms](skills/career-log/SKILL.md#platforms).

## Changes

Log data (entries, profile, direction, applications, outputs, sources) is committed as [SKILL.md › Commits](skills/career-log/SKILL.md) says. Engine changes change how the agent behaves: every path in the `ALLOW` list of `tools/export-template.sh` (the skill, the tools and the Template skeleton in `tools/template/`, `SETUP.md`, this file and `CLAUDE.md`, `GLOSSARY.md`, `docs/guide.md`, `docs/adr/`, the two `.svg` files of `docs/social-preview/`, `.gitignore`, `.gitattributes`, `entries/_template.md`). `tools/checks_for.py` ([SETUP.md](SETUP.md) step 7) prints `engine: <path>` for each Engine path a change touches.

An Engine change never goes straight to the default branch:
1. Work on a branch in a worktree (under `.worktrees/`, or where the agent's tooling puts them) started from the default branch: `git fetch`, then `git worktree add --no-track .worktrees/<topic> -b <branch> origin/<default>`; `--no-track` keeps a push from ever landing on the default branch.
2. Open an issue describing the change.
3. Commit and push the branch as often as the work needs: the push backs the work up and lets another machine see it.
4. Open the pull request, with `Closes #<issue>`, only once the change is finished: the issue's fix is done and the checks [SETUP.md](SETUP.md) step 7 runs for what changed have run, so the user reviews one finished diff.
5. Once it is open, gather the fixes from a review and push them together, not one push per fix.
6. Merge only when the user says so.

The exceptions:
- **No `gh` or GitHub remote:** show the user the branch's diff instead, and merge it locally with `git merge --no-ff` only on their yes.
- **Guard files** go straight to the default branch at once, even while a bulk data change waits for the user's yes, because they protect the main checkout and every export made from it: the names the `import`, `log` and `consolidate` modes, or a `tools/deny_coverage.py` failure, append to `.export-deny`; on the user's word, a name a `tools/deny_coverage.py` failure clears into `.export-cleared` and the `.export-deny` line it takes out (*Sharing*); and the `sources/inbox/` lines that the `gitignore inbox:` step of `tools/check.py import` restores to `.gitignore`.
- **Data and Engine in one session:** commit the data and the Engine change separately, each its own way.
- **An Engine commit that went straight to the default branch:** revert it there and re-land it through a pull request; never rewrite the published history.

## Sharing

`tools/export-template.sh <dest>` builds the shareable Template: the Engine (`skills/`, `tools/`, `SETUP.md`, this file and `CLAUDE.md`, `GLOSSARY.md`, `docs/guide.md`, `docs/adr/`, `docs/social-preview/social-preview.svg` and `banner.svg`) plus the empty Log skeleton in `tools/template/`. Keep every Engine file free of personal content: no names, employers, projects, dates or quotes from this Log. Those belong in the Log files (`direction.md`, entries). It exports committed content only, so commit before exporting. It scans file names and contents for the patterns in `.export-deny` and fails on a hit; the `import`, `log` and `consolidate` modes append new employer and project names, and the export refuses an empty list.

A Log made from the Template has no CI: after an Engine change, run the checks [SETUP.md](SETUP.md) step 7 runs for what changed, and report their results before asking the user to merge.

