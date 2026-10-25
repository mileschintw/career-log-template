English | [繁體中文](README.zh-TW.md)

# career-log: an AI career journal and resume builder for Claude Code, Codex, Cursor and Antigravity

![Claude Code: tested](https://img.shields.io/badge/Claude_Code-tested-2ea44f) ![Codex: should work](https://img.shields.io/badge/Codex-should_work-blue) ![Cursor: should work](https://img.shields.io/badge/Cursor-should_work-blue) ![Antigravity: should work](https://img.shields.io/badge/Antigravity-should_work-blue)

![macOS](https://img.shields.io/badge/macOS-supported-2ea44f) ![Windows](https://img.shields.io/badge/Windows-supported-2ea44f) ![Linux](https://img.shields.io/badge/Linux-supported-2ea44f)

[![Watch a one-minute video tour of career-log-template](https://gitdiagram.com/video-badge.svg)](https://gitdiagram.com/mileschintw/career-log-template/video)

A GitHub template for keeping a career log (a "brag document") in git and letting your AI coding agent turn it into tailored resumes, cover letters, job application answers and interview prep. Every claim it writes traces back to a dated record, so it can't invent anything, and nothing you logged gets lost.

- **Hand over what you have:** old resumes, LinkedIn exports, AI chat histories. You don't type your history in.
- **No commands to learn:** say what you want, in your own words and any language.
- **Log from any project:** "log this to my career log" adds a dated line without pulling you out of your work.

![career-log: log your work as it happens, then write a tailored resume from the record](docs/social-preview/banner.svg)

## Quick start

1. On GitHub, click **Use this template**, and make your repo **Private**: it will hold your personal records.
2. Clone it, open your coding agent in the repo, and say: **"introduce this repo and set me up"**. It tells you what it can do, sets up this machine (for your user only) and asks a few questions, each with a suggested answer.
3. Hand over what you have ("import my old resumes"), then ask for what you need ("apply to <posting URL>"). Not sure what comes next? Ask "what next?".

## Support

- **Systems:** macOS, Windows and Linux.
- **Agents:** tested with [Claude Code](https://claude.com/claude-code) (Opus and Sonnet; Sonnet or above recommended). Codex, Cursor and Antigravity should work, but are not tested.
- **Resumes:** one-page English resumes in the North American style. You and your records can use any language.

**More:** the [guide](docs/guide.md) has every mode with example requests, the setup items, the file map and where the writing rules come from; [SETUP.md](SETUP.md) is per-machine setup.

## Entries

Entries appear here as you log them.

| Period | Entry | Type | Tags | Status |
|---|---|---|---|---|

## Upstream

This repo was created from the Template at https://github.com/mileschintw/career-log-template. Report a changed chat-export format or a broken step there, as an issue (use the "Chat export format changed" form) or a pull request. Issues are public: include keys and shapes only, never your records. The import mode drafts the report for you and asks before posting ([import-chats.md](skills/career-log/modes/import-chats.md), step 8).

To upgrade this Log to a newer Template, ask your agent to "upgrade to the latest Template". The upgrade mode ([upgrade.md](skills/career-log/modes/upgrade.md)) fetches the release, replaces the Engine, runs the upgrade guide of each release in between with you, offers to merge your own Engine edits back, and commits once you say yes. The Template's [Releases](https://github.com/mileschintw/career-log-template/releases) page says what each release changed. A Log made before 0.1.0 starts with the guide in [v0.1.0](https://github.com/mileschintw/career-log-template/releases/tag/v0.1.0).

## License

MIT, see [LICENSE](LICENSE). The example resume is based on the [r/EngineeringResumes template](https://github.com/r-engineeringresumes/resume-templates) (MIT).
