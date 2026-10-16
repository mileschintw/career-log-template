# CLAUDE.md

This repo is a personal career log (a Log, with its Engine; see [GLOSSARY.md](GLOSSARY.md)), managed through the `career-log` skill in `skills/career-log/`. Read `skills/career-log/SKILL.md` before creating or editing anything here; its rules (provenance, attribution, gaps) apply to every file.

Edit the skill here, in the repo, so changes are versioned.

## Machines

The log may be cloned on more than one machine (macOS, Windows, Linux). Per-machine setup (git identity, skill link, LaTeX toolchain) is in [SETUP.md](SETUP.md); the cross-platform rules for commands are in [SKILL.md › Platforms](skills/career-log/SKILL.md#platforms).

## Sharing

`tools/export-template.sh <dest>` builds the shareable Template: the Engine (`skills/`, `tools/`, `SETUP.md`, this file, `GLOSSARY.md`, `docs/adr/`) plus the empty Log skeleton in `tools/template/`. Keep every Engine file free of personal content: no names, employers, projects, dates or quotes from this Log. Those belong in the Log files (`direction.md`, entries). It exports committed content only, so commit before exporting. It scans file names and contents for the patterns in `.export-deny` and fails on a hit; add a pattern whenever a new employer, project or person appears in the Log.
