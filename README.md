# career-log

Raw records of past work, projects and achievements, written once so they never have to be remembered again. Resumes, cover letters, bios and interview answers are derived from these records by the `career-log` skill. It works with coding agents that read `AGENTS.md` and Agent Skills: [Claude Code](https://claude.com/claude-code), OpenAI Codex, Cursor and Google Antigravity. Only Claude Code is fully tested; the others should broadly work.

## Quick start

1. On GitHub, click **Use this template** to create your own repo, and make it **Private**: it will hold your personal records.
2. Clone it, open your coding agent in the repo root, and say "set up this machine following SETUP.md". It sets your git identity, links the skill into the skill folder your agent reads (SETUP.md step 4), installs the LaTeX tools and runs the checks.
3. Put your old resumes (PDF, `.tex`, Word) in `sources/inbox/` and say "import my old resumes".
4. From then on, when something worth remembering lands in any project, say "log this to my career log"; to apply for a job, paste the posting URL and say "apply to <URL>".

Talk to your agent in any language. Records are written in English by default (change it in `direction.md`); each output picks its own language. The example data in `skills/career-log/examples/` only shows the format and is never treated as your experience.

> **快速開始（繁體中文）**
> 1. 在 GitHub 按 **Use this template** 建立自己的 repo，並設為 **Private**：這裡會放你的個人經歷。
> 2. 把它 clone 到電腦上，在 repo 根目錄開你的 coding agent，對它說「照 SETUP.md 幫我設定這台電腦」。它會設定 git 身分、把 skill 連到你的 agent 讀取的 skill 資料夾（SETUP.md 第 4 步）、安裝 LaTeX 工具並跑檢查。
> 3. 把舊履歷（PDF、`.tex`、Word）放進 `sources/inbox/`，說「import my old resumes」。
> 4. 之後在任何專案完成一件值得記的事，說「log this to my career log」；要投履歷時，貼職缺網址說「apply to <網址>」。
>
> 支援讀取 `AGENTS.md` 與 Agent Skills 的 coding agent：Claude Code、OpenAI Codex、Cursor、Google Antigravity。目前只有 Claude Code 完整測過，其他應該大致可用。
>
> 你可以用任何語言跟你的 agent 對話。記錄預設用英文寫（可在 `direction.md` 改），每份產出各自選語言。範例資料在 `skills/career-log/examples/`，只是格式示範，不會被當成你的經歷。

## How to use

The `career-log` skill (in [`skills/career-log/`](skills/career-log/SKILL.md)) works from any session of those agents once it is linked into the skill folder your agent reads (see [SETUP.md](SETUP.md) step 4):

| Say | Mode |
|---|---|
| "log this to my career log" | **log**: append a dated line to an entry |
| "consolidate the <project> entry" | **consolidate**: fill every section, interviewing you on the gaps |
| "apply to <posting URL>" | **apply**: fit call, tailored resume and form answers, second-agent review |
| "prep me for the <company> interview" | **interview**: prep pack from what they read, then a mock interview |
| "what should I learn for these postings" | **upskill**: evidence-based gap heatmap and a project-first learning plan |
| "rank these career fair employers" | **rank**: tiers by sponsorship, domain fit, size; for a fair, also a timed route and a phone page with the floor map |
| "write resume bullets for <role>" | **write**: derive an output, with a provenance table |
| "import my old resumes" (files in `sources/inbox/`, or a logged-in site) | **import**: merge old documents into entries |
| "audit my career log" | **audit**: report missing stories, gaps and conflicts |

Recommended: install the [humanizer](https://github.com/blader/humanizer) skill. The skill runs its own AI-tell check either way ([writing.md](skills/career-log/writing.md)); with humanizer installed, it also runs humanizer on every employer-facing output.

## Entries

Entries appear here as you log them.

| Period | Entry | Type | Tags | Status |
|---|---|---|---|---|

## Files

- [`profile.md`](profile.md): contact, education, languages, skills summary
- [`stories.md`](stories.md): behavioural question types → stories, and recurring application questions → material
- [`applications.md`](applications.md): applications this repo prepared materials for, career fairs and recruiter contacts
- [`direction.md`](direction.md): target roles, employer preferences, constraints, what to emphasise, languages
- `entries/`: one file per experience ([template](entries/_template.md))
- `outputs/`: derived documents, each with a provenance table
- [`SETUP.md`](SETUP.md): per-machine setup for macOS, Windows and Linux
- `tools/`: LaTeX setup scripts and `resume.py` (build and layout-check a resume); usage in [latex.md](skills/career-log/latex.md)
- `skills/career-log/`: the skill itself, its [writing standards](skills/career-log/writing.md) and [examples](skills/career-log/examples/README.md)
- `sources/`: imported originals, the import inbox (`inbox/`), the [import log](sources/import-log.md) and the [source keys](sources/keys.md)
- [`GLOSSARY.md`](GLOSSARY.md) and [`docs/adr/`](docs/adr/): the repo's vocabulary and design decisions

## License

MIT, see [LICENSE](LICENSE). The example resume is based on the [r/EngineeringResumes template](https://github.com/r-engineeringresumes/resume-templates) (MIT).
