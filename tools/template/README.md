English | [繁體中文](README.zh-TW.md)

# career-log: an AI career journal and resume builder for Claude Code, Codex, Cursor and Antigravity

![Claude Code: tested](https://img.shields.io/badge/Claude_Code-tested-2ea44f) ![Codex: should work](https://img.shields.io/badge/Codex-should_work-blue) ![Cursor: should work](https://img.shields.io/badge/Cursor-should_work-blue) ![Antigravity: should work](https://img.shields.io/badge/Antigravity-should_work-blue)

![macOS](https://img.shields.io/badge/macOS-supported-2ea44f) ![Windows](https://img.shields.io/badge/Windows-supported-2ea44f) ![Linux](https://img.shields.io/badge/Linux-supported-2ea44f)

[![Watch a one-minute video tour of career-log-template](https://gitdiagram.com/video-badge.svg)](https://gitdiagram.com/mileschintw/career-log-template/video)

A GitHub template for keeping a career log (a "brag document") in git and letting your AI coding agent turn it into tailored resumes, cover letters, job application answers and interview prep. Every claim it writes traces back to a dated record, so it can't invent anything, and nothing you logged gets lost.

- **Hand over everything you have.** You don't type your history in. Give the agent your old resumes and CVs, bios, reports, LinkedIn exports and AI chat histories, or let it read a website you sign in to. It merges them into one entry per experience.
- **No commands to learn.** Invoke the skill and say what you want, in your own words and in any language. It picks the right mode from your request and walks you through it.
- **Log anytime, from any project.** When a PR merges, a project wraps up or something else is worth remembering, say "log this to my career log" in whatever session you're in. It adds a dated line and commits it, without pulling you out of your work.
- **Rules you can override.** The writing rules in [writing.md](skills/career-log/writing.md) are defaults. Your own preferences in `direction.md` win where they differ, and the skill records the preferences you state as you use it, so the rules adapt to you over time. Your background is part of your setup too, not a built-in assumption: whether you need visa sponsorship, how to rank employers, what each resume version leads with ([Your setup](#your-setup)).
- **Your OS, your agent.** Runs on macOS, Windows and Linux with Claude Code, Codex, Cursor and Antigravity. Only [Claude Code](https://claude.com/claude-code) is fully tested; the others should broadly work, but are not tested on Windows.

![career-log: log your work as it happens, then write a tailored resume from the record](docs/social-preview/social-preview.svg)

## Quick start

1. On GitHub, click **Use this template** to create your own repo, and make it **Private**: it will hold your personal records.
2. Clone it, open your coding agent in the repo root, and say "set up this machine following SETUP.md". It sets your git identity, links the skill into the skill folder your agent reads (SETUP.md step 4), asks which optional tools you want on this machine (the LaTeX tools for resume PDFs, `playwright-cli` for websites), installs them for your user only, and runs the checks.
3. Hand over what you have. Put old resumes and CVs (PDF, `.tex`, Word), bios, reports and LinkedIn exports in `sources/inbox/` and say "import my old resumes". For an AI chat history, say "import my ChatGPT history" (or Claude, Gemini, Perplexity) and the agent tells you how to export it; drop the download in as it arrived, zipped or not, and the agent finds the export inside. For a logged-in website, name the site; the agent reads it with `playwright-cli`, which it offers to install the first time unless you chose it or declined it in setup (SETUP.md step 5), or with its own browser tool.
4. From then on, when something worth remembering lands in any project, say "log this to my career log"; to apply for a job, paste the posting URL and say "apply to <URL>"; for a reusable version, say "write a backend engineer resume".

Your first request to a new Log starts setup, and nothing else runs until it has: one round of five questions, each with a suggested answer you can accept as is. Your target roles and your work authorisation and other hard constraints (skip either to leave it empty), the record language (English), whether to install `playwright-cli` on this machine (yes), and whether to trim this page into a personal index of your records (yes: it keeps How to use, Your setup, Entries, Files, Upstream and License, drops the rest, and deletes the Chinese translation). See [Your setup](#your-setup).

**Administrator dialogs.** Setup installs everything for your user only, except two steps that need administrator rights: on a Mac without Homebrew it installs Homebrew, which opens the system's password dialog; on Windows without the Visual C++ runtime the PDF tools need, it opens the UAC dialog, which may wait behind a flashing shield button on the taskbar. The agent tells you before either one opens. Answer it at the machine: your password goes to the operating system, never to the chat. On Linux, a step that needs sudo is printed for you to run in your own terminal. A scheduled or unattended run never opens a dialog.

Talk to your agent in any language. Records are written in English by default (change it by saying so); each output picks its own language. The example data in `skills/career-log/examples/` only shows the format and is never treated as your experience.

## Features

- **Career log / brag document**: one Markdown file per job, project or course, with dated notes waiting to be merged into it, plus a bank of stories for behavioural interview questions.
- **Tailored resumes**: one-page LaTeX resumes (ATS-friendly PDF), built and layout-checked by `tools/resume.py`. Make one for a single job posting (the agent looks up what the company builds and runs on, to choose what the resume leads with), one per target role, or a general version; a second agent reviews each (where your agent can, in the background, so you see the draft as soon as it builds), and nothing is saved until the review has passed. The first time you ask for a role, the agent asks what that version should lead with and saves your answer in `direction.md`.
- **Fit check and skill gaps**: ask how well you fit a posting and get a go / no-go without any writing: your hard constraints (work authorisation, for one) against the posting, where the role ranks among your targets, and each stated requirement and duty sorted into proven by a record, shallow, claimed but unproven, or a gap. Then, if you want it, a project-first learning plan for its gaps. For a batch of postings, a gap heatmap and the same kind of plan.
- **Job applications**: "apply to <posting URL>" goes straight to the resume, plus answers to the form's free-text questions, drawn from your records. Paste the questions, or the agent finds them on the posting's own page (Ashby, Greenhouse); when they sit behind a multi-step apply flow (Workday and the like), it asks you to paste them. Your own tools fill in the rest of the form and track the application. A resume made for one posting is saved with the posting and the answers. Later applications reuse that application's wordings and answers, unless you save it as Archived: kept as the record of what you sent, never reused. For a reusable version you upload yourself, git history and the application date recover the exact file (keep its file name when you upload it).
- **Interview prep**: a prep pack from what the employer will read, then a mock interview.
- **Behavioural questions**: prepare one question or a pasted list, no application needed. The agent shows the stories your log has for that question type and asks which to use; a better story it lacks gets recorded in its entry, with sources. Once you confirm them, it saves Talking points for each question type: an opening line and cue lines that point at your records, ready the next time that question comes up, and checked against any record that has changed since.
- **Employer ranking**: sort a career fair roster or job list by your hard constraints, then your own sorting order (domain fit, size, pay, ...).
- **Job scan**: collect new postings from your job sources (a job board you are signed in to, a public GitHub list of postings), drop the ones you applied to or declined, screen the rest against your entry list, give the best a full fit and rank them in a saved report. With auto-drafting on, the best few get a resume and answers on a draft branch, with every judgement call listed, until you accept one as an application. Run it by hand or as a scheduled task; it never applies, and never signs in for you.
- **Import**: merge old resumes and CVs (PDF, Word, LaTeX), bios, reports, LinkedIn exports, AI chat histories (ChatGPT, Claude.ai, Gemini, Perplexity) and logged-in websites into one entry per experience. Reading a website, and Perplexity, which has no export, uses `playwright-cli` (optional; the agent offers to install it) or the agent's own browser tool.
- **Provenance**: every output ships with a table linking each claim to its source record.

## Where the writing rules come from

Every rule in [writing.md](skills/career-log/writing.md) names its source in parentheses. There are two kinds.

**Published guides**, which anyone can check:
- [r/EngineeringResumes wiki](https://www.reddit.com/r/EngineeringResumes/wiki/index/) and its [sample bullet points](https://www.reddit.com/r/EngineeringResumes/wiki/sample-bullet-points/) (`r/ER`): one page, bullet style (XYZ, STAR), opening verbs, the Skills section.
- [r/EngineeringResumes LaTeX template](https://github.com/r-engineeringresumes/resume-templates) (`r/ER`, MIT): the resume layout that `tools/resume.py` builds and checks.
- [humanizer](https://github.com/blader/humanizer), based on Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (`humanizer`): the AI-tell check.
- [r/cscareerquestions resume guide](https://www.reddit.com/r/cscareerquestions/comments/1577dm9/the_ultimate_guide_to_writing_your_resuume_for/), by a senior engineer who reviews resumes (`r/csCQ`): two rules adopted, when to list GPA and choosing projects that have real users.
- [Tech Interview Handbook resume guide](https://www.techinterviewhandbook.org/resume/) (`TIH`): two rules adopted, spelling out abbreviations and the plain-text ATS check. Its format advice conflicts with r/ER, so the rest is not used.

**Lessons from real applications**, which generic guides miss. They come from the author's calls while preparing real applications with this skill (`practice`) and from advice by recruiters, hiring engineers and peers (`feedback`). Some of them:
- Lead a bullet with what you did and put the metric after it: a bullet that opens with its number hides your part. (a peer's advice)
- For a student or recent graduate, put the graduation date where the reader sees it at once. (a recruiter's screening order, passed on by a peer)
- A skill on the Skills line also shows up in a bullet: recruiters check the Skills section against the posting, then look for experience that uses it. (the same recruiter's view)
- Show soft skills as 1–3 pieces of evidence inside technical bullets, not as bullets of their own. (a hiring engineer's advice)
- Name the exact quantity a metric measures ("p95 queue wait", not "p95 latency"). (caught by a review pass on a real application)
- Where a posting uses an umbrella term, put it in a bullet next to the concrete tool. (a low keyword-scan score on a real application)
- An outcome metric beats a caught-failure metric, and test counts are not impact. (the author's calls while drafting)

Like every rule here, these are defaults you can override (see the top of this page).

## Where the speaking rules come from

Every rule in [speaking.md](skills/career-log/speaking.md), which covers answers you say aloud to behavioural interview questions, names its source in parentheses. They come from published guides, which anyone can check:
- [Tech Interview Handbook behavioral guide](https://www.techinterviewhandbook.org/behavioral-interview/) and its [guide for senior candidates](https://www.techinterviewhandbook.org/behavioral-interview-senior-candidates/) (`TIH`): 3–5 core stories, ending on a lesson, leading with impact for senior or complex stories, showing scope, bullet points instead of a script, adapting one story to several questions.
- [Hello Interview behavioral course](https://www.hellointerview.com/learn/behavioral/overview/introduction) (`HI`, partly paywalled): the minimum context, 3–5 core stories plus 5–7 gap fillers, a lesson as the natural end.
- [interviewing.io guide to one large tech employer's behavioral interview](https://interviewing.io/guides/amazon-behavioral-interview) and [how Meta evaluates behavioral interviews](https://interviewing.io/blog/how-software-engineering-behavioral-interviews-are-evaluated-meta) (`iio`): 80% of the answer on your own part, 10–15 minutes of follow-ups on one point, scope by people and teams.
- That employer's own [interview tips](https://aboutamazon.com/news/workplace/amazon-interview-best-tips) and [interview mistakes](https://aboutamazon.com/news/workplace/amazon-jobs-interview-mistakes) (`employer`): "I", not "we"; four minutes or less; one accomplishment per question.
- Jacob Kaplan-Moss on [the project-you-led question](https://jacobian.org/2021/feb/9/interview-questions-project-you-led/) (`jacobian`): the follow-ups an interviewer asks about one project.
- Wes Kao, [keep your backstory short](https://newsletter.weskao.com/p/in-job-interviews-keep-your-backstory) (`Kao`): 2–3 sentences and 10–15 seconds of context.

Lessons from real interviews (`practice`, `feedback`) will join them as they come up. Like the writing rules, these are defaults you can override.

## Scope and limitations

The skill is designed for **English resumes in the North American style**: one page, the rules in [writing.md](skills/career-log/writing.md), and the bundled LaTeX template. You can talk to your agent in any language, and records can be in any language; the scope is about the resume it produces.

Other languages and resume styles depend on three planned features: custom resume templates, Typst templates, and CJK (Chinese, Japanese, Korean) resumes. Even after those land, resumes in other languages or styles **may not work as well** as North American English ones. Those features will extend the design built and tested for this style, and none of them adds rules tuned for other markets.

**Models.** How `write` (resumes and application answers) did in testing with Claude models in Claude Code:

| Model | `write` |
|---|---|
| Opus, Sonnet | Tested. Sonnet or above is recommended. |
| Haiku | Works, but the humanizer step is unreliable (skipped in 2 of 3 test runs, even at extra-high effort), and its subagents are often set up wrong at medium and high effort. |

On every model, the agent sometimes skips the one-line note it writes before starting a review or humanizer subagent; the subagent itself still runs. Sonnet also sometimes sets up a subagent wrong, less often than Haiku.

## How to use

Invoke the skill and say what you want. The `career-log` skill (in [`skills/career-log/`](skills/career-log/SKILL.md)) works from any session of Claude Code, Codex, Cursor or Antigravity once it is linked into the skill folder your agent reads (see [SETUP.md](SETUP.md) step 4), and it picks the mode from your request. The table shows what you can ask for. The quoted phrases are examples; any wording works.

| You can ask | Mode |
|---|---|
| "log this to my career log" | **log**: add a dated line to an entry's pending notes |
| "consolidate the <project> entry" | **consolidate**: fill every section, interviewing you on the gaps |
| "prep me for the <company> interview" | **interview**: prep pack from what they read, then a mock interview |
| "help me prepare 'tell me about a conflict'", "here are my BQs" | **stories**: pick a story with you for each behavioural question, fill in what its entry lacks, and save confirmed Talking points per question type |
| "how well do I fit <posting URL>", "what should I learn for these postings" | **fit**: a go / no-go on one posting, each requirement mapped to the record that proves it; or a gap heatmap across several. A project-first learning plan for the gaps on request |
| "rank these career fair employers" | **rank**: tiers by your hard constraints and your sorting order, with an opening line for every employer it does not rule out |
| "scan for new postings", "scan twice a day", "accept the <company> draft" | **scan**: new postings from your job sources, deduplicated, fitted and ranked in a saved report, with drafts for the top few when auto-drafting is on, and a dashboard page of the results; then accept or decline them, in this session or a later one |
| "apply to <posting URL>", "write a backend engineer resume" | **write**: a resume for that posting, a target role or a general version, plus answers to the posting's free-text questions. Employer-facing drafts get a second-agent review and a provenance table |
| "import my old resumes" (files in `sources/inbox/`, or a logged-in site) | **import**: merge old documents into entries |
| "import my ChatGPT history" (or Claude, Gemini, Perplexity) | **import**: tells you how to export it, screens every conversation, and copies only the ones you pick; the raw export stays out of git |
| "audit my career log" | **audit**: report missing stories, gaps and conflicts |

Keeping it current: `log` only notes things down; consolidate an entry from time to time, so its pending notes move into the right sections and the agent asks you about its gaps. `log` and `write` tell you when an entry is due, and `audit` ranks which entries to consolidate first. Nothing keeps a history inside the files: git does.

Recommended: the GitHub CLI, `gh`, and a GitHub remote for your Log. With the remote, every machine you work on pulls the same Log, and `scan` keeps its drafts on a branch that any later session can open; without one, drafts stay on the machine that made them. With `gh`, the agent reads GitHub pages (a public list of postings, your own repos and pull requests as sources) through the API instead of the web page.

Recommended: install the [humanizer](https://github.com/blader/humanizer) skill. The skill runs its own AI-tell check either way ([writing.md](skills/career-log/writing.md)); with humanizer installed, it also runs humanizer on every employer-facing output.

## Your setup

Some of what the skill does depends on who you are, not on general resume rules: whether a role needing visa sponsorship is out, what decides which employers come first, what a resume for a given role leads with. None of that is built in. It lives in two files of your Log that you can read: `direction.md`, for what you want (Direction), and `config.toml`, for how the skill runs (Config).

| Item | What it changes | Where it lives | Until you set it |
|---|---|---|---|
| Target roles | Where a posting's role ranks among your targets in the fit check, and what employer ranking measures domain fit against | `direction.md › Target roles, ranked` | Empty: the fit check gives no rank and weighs every posting in a batch the same, ranking goes by the areas your records show, and each says so |
| Work authorisation | The fit check's go / no-go, and what employer ranking researches (sponsorship, citizenship, clearance) | `direction.md › Constraints` | Empty: the fit check gates nothing on it and lists the posting's requirement for you to check, a ranking rules no employer out by it, and interview prep lists the question as unprepared; each says so. A resume for a posting never stops on it: it quotes the posting's sponsorship language for you to check |
| Other hard constraints (location, start date, role level) | The same go / no-go | `direction.md › Constraints` | No limit |
| Employer sorting order | How `rank` orders employers after your hard constraints | `direction.md › Employer preferences` | Domain fit, then size and pay; the ranking says so |
| What a resume version leads with | Which records each target version puts first, what it leaves out, and how far back it reaches (about five years by default) | `direction.md › What to emphasise, by target` | The records that fit the target best; the draft says so |
| Writing preferences | Overrides for the rules in [writing.md](skills/career-log/writing.md) | `direction.md › Writing preferences for applications` | writing.md as it is |
| Record language | The language your Log files are written in | `config.toml`, `record_language` | English |
| Interviewer profiles | Whether interview prep reads an interviewer's profile that only signed-in members can see (LinkedIn) | `config.toml`, `interviewer_profiles` | `never`: public pages only |
| Front page | Whether this page is trimmed to a personal index | `config.toml`, `front_page` | `full` |
| Scan window | How many days back `scan` collects postings; a scheduled run can use its own | `config.toml`, `window` and `scheduled_window` | 7 days; a scheduled run the same |
| Scan size | How many postings `scan` screens, how many of those get a full fit, and how many its report ranks | `config.toml`, `screen_budget`, `fit_budget` and `n` | 40 screened, 15 fitted, top 10 |
| Auto-drafting | Whether `scan` drafts a resume and answers for the top postings, and for how many | `config.toml`, `auto_write` and `m` | `off`; 5 when on (at most 20) |
| Scan sources | Which job boards and lists `scan` reads, and how it last read each | `scan-sources.md` | Asked the first time you scan |
| `playwright-cli` on this machine | Whether the skill reads web pages that need scripts or a sign-in | `~/.career-log/machine.toml`, outside the repo | Asked in setup; on another machine, the first time a mode needs it |

Facts in `profile.md` shape outputs too, but they are records, not setup: a graduation date that differs by application type, for example, is used only when `profile.md › Education` and its Conflicts record it.

**Quick or advanced.** Quick setup is the one round above. Ask for advanced setup to see every item, with its current value preselected, and change any of them. A work authorisation or a target role found in an import (an old resume, a chat history) is never applied on its own: the import report lists it, and you adopt it through setup.

**How to change one.** Say it in chat, in your own words: "I don't need visa sponsorship", "rank employers by pay first", "write my records in Chinese from now on". The agent maps it onto the items it changes, shows each one before and after, and writes it with the date on your yes, then commits. "None" is an answer too: "no constraint" is recorded like any other. Something you say about one request only ("this time, leave out the internship") changes that request and nothing else.

## Entries

Entries appear here as you log them.

| Period | Entry | Type | Tags | Status |
|---|---|---|---|---|

## Files

- [`profile.md`](profile.md): contact, education, languages, skills summary
- [`stories.md`](stories.md): behavioural question types → stories, and recurring application questions → material
- `stories/`: Talking points, one file per behavioural question type, saved once you confirm them; `stories/wordings/` keeps each question you were asked, word for word, by type, so the next one maps to its type
- [`applications.md`](applications.md): career fairs, recruiter contacts, resume versions sent outside an application, and applications with no folder under `outputs/applications/`
- [`direction.md`](direction.md): target roles, employer preferences, constraints, what to emphasise, languages
- `config.toml`: how the skill runs for this Log (record language, interviewer profiles, front page, scan settings), written by setup; the defaults are in `tools/config.default.toml`
- `scan-sources.md`: the job sources `scan` reads, written the first time you scan
- `entries/`: one file per experience, or per part when a long one is split into a series ([template](entries/_template.md))
- `outputs/`: derived documents, each with a provenance table except the dashboard: `applications/` (one folder per application, frozen once sent), `resumes/` (one living file per resume target; git history keeps the old versions), `reports/` (dated rankings, scan reports and other reports) and `dashboard/` (the scan dashboard, regenerated by `dashboard.py`)
- [`SETUP.md`](SETUP.md): per-machine setup for macOS, Windows and Linux
- `tools/`: the machine setup scripts and `check.py` (what the skill checks on this machine before each request), `resume.py` (build and layout-check a resume; usage in [latex.md](skills/career-log/latex.md)), `chat_export.py` (screen and extract AI chat exports, and excerpt agent sessions; usage in [import-chats.md](skills/career-log/modes/import-chats.md) and [excerpts.md](skills/career-log/excerpts.md)) with its tests in `tools/tests/`, `scan.py` (the mechanical steps of `scan`: report names, dedup, the screen's order and reuse, pruning, the pending list), `dashboard.py` (the scan dashboard page, from the Log), and `export-template.sh` (build a shareable Template from your repo)
- `skills/career-log/`: the skill itself, its [writing standards](skills/career-log/writing.md), [speaking standards](skills/career-log/speaking.md) and [examples](skills/career-log/examples/README.md)
- `sources/`: imported originals, excerpts of agent sessions, the import inbox (`inbox/`), the [import log](sources/import-log.md) and the [source keys](sources/keys.md)
- [`GLOSSARY.md`](GLOSSARY.md) and [`docs/adr/`](docs/adr/): the repo's vocabulary and design decisions

## Upstream

This repo was created from the Template at https://github.com/mileschintw/career-log-template. Report a changed chat-export format or a broken step there, as an issue (use the "Chat export format changed" form) or a pull request. Issues are public: include keys and shapes only, never your records. The import mode drafts the report for you and asks before posting ([import-chats.md](skills/career-log/modes/import-chats.md), step 8).

## License

MIT, see [LICENSE](LICENSE). The example resume is based on the [r/EngineeringResumes template](https://github.com/r-engineeringresumes/resume-templates) (MIT).
