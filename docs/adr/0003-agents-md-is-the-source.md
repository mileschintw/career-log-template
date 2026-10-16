# AGENTS.md is the single source of instructions

The repo's instructions live in `AGENTS.md`, which Codex, Cursor and Antigravity read natively. `CLAUDE.md` holds only `@AGENTS.md`, because Claude Code ignores `AGENTS.md` whenever a `CLAUDE.md` exists, and imports the file this way without loading it twice. We commit no symlinks (`CLAUDE.md -> AGENTS.md`, `.agents/skills/career-log`): Git for Windows checks them out as one-line text files unless `core.symlinks` is on. We also keep no copies of the skill or the rules in `.cursor/`, `.codex/` or `.agents/rules`: they drift, and Antigravity silently drops rule files with a bad `trigger` field. The skill is reached from other projects through a per-machine link instead (SETUP.md step 4).

## Consequences

`AGENTS.md` is on the export allowlist and must stay free of personal content. Only Claude Code is fully tested; the other agents' skill folders follow their vendors' docs. Tool names in the skill are Claude Code's, so the skill says what to do when an agent has no equivalent (inline work).
