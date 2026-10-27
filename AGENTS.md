# AGENTS.md

This repo is a personal career log (a Log, with its Engine; see [GLOSSARY.md](GLOSSARY.md)), managed through the `career-log` skill in `skills/career-log/`. Read `skills/career-log/SKILL.md`, the skill entry point (the modes are in `skills/career-log/modes/`), before creating or editing anything here; its rules (provenance, attribution, gaps) apply to every file.

Asked what this repo is or can do, where to start or what to do next ("introduce this repo and set me up"): read [docs/guide.md](docs/guide.md) and follow its *For agents*.

Tool names in the skill (subagents, `Explore`, the PowerShell tool) are Claude Code's; use your agent's equivalent, or do the work inline.

## Changes

Log data (entries, profile, direction, applications, outputs, sources) is committed as [SKILL.md › Commits](skills/career-log/SKILL.md) says. Engine changes change how the agent behaves: every path in the `ALLOW` list of `tools/export-template.sh` (the skill, `tools/` and the Template skeleton in `tools/template/`, `SETUP.md`, this file and `CLAUDE.md`, `GLOSSARY.md`, `docs/guide.md`, `docs/adr/`, `docs/upgrades/`, the two `.svg` files of `docs/social-preview/`, `.gitignore`, `.gitattributes`, `entries/_template.md`). `tools/checks_for.py` ([SETUP.md](SETUP.md) step 7) prints `engine: <path>` for each Engine path a change touches.

An Engine change never goes straight to the default branch: first a branch, then an issue, then a pull request. Before its first edit, read [skills/career-log/engine-changes.md](skills/career-log/engine-changes.md): the steps, their exceptions, the checks to run, and keeping Engine files free of personal content.

