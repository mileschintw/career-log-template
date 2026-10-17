English | [繁體中文](README.zh-TW.md)

# career-log: an AI career journal and resume builder for Claude Code, Codex, Cursor and Antigravity

![Claude Code: tested](https://img.shields.io/badge/Claude_Code-tested-2ea44f) ![Codex: should work](https://img.shields.io/badge/Codex-should_work-blue) ![Cursor: should work](https://img.shields.io/badge/Cursor-should_work-blue) ![Antigravity: should work](https://img.shields.io/badge/Antigravity-should_work-blue)

![macOS](https://img.shields.io/badge/macOS-supported-2ea44f) ![Windows](https://img.shields.io/badge/Windows-supported-2ea44f) ![Linux](https://img.shields.io/badge/Linux-supported-2ea44f)

A GitHub template for keeping a career log (a "brag document") in git and letting your AI coding agent turn it into tailored resumes, cover letters, job application answers and interview prep. Every claim it writes traces back to a dated record, so it can't invent anything, and nothing you logged gets lost.

- **Hand over everything you have.** You don't type your history in. Give the agent your old resumes and CVs, bios, reports, LinkedIn exports and AI chat histories, or let it read a logged-in website in its browser. It merges them into one entry per experience.
- **No commands to learn.** Invoke the skill and say what you want, in your own words and in any language. It picks the right mode from your request and walks you through it.
- **Log anytime, from any project.** When a PR merges, a project wraps up or something else is worth remembering, say "log this to my career log" in whatever session you're in. It adds a dated line and commits it, without pulling you out of your work.
- **Rules you can override.** The writing rules in [writing.md](skills/career-log/writing.md) are defaults. Your own preferences in `direction.md` win where they differ, and the skill records the preferences you state as you use it, so the rules adapt to you over time.
- **Your OS, your agent.** Runs on macOS, Windows and Linux with Claude Code, Codex, Cursor and Antigravity. Only [Claude Code](https://claude.com/claude-code) is fully tested; the others should broadly work, but are not tested on Windows.

![career-log: log your work as it happens, then write a tailored resume from the record](docs/social-preview/social-preview.svg)

## Quick start

1. On GitHub, click **Use this template** to create your own repo, and make it **Private**: it will hold your personal records.
2. Clone it, open your coding agent in the repo root, and say "set up this machine following SETUP.md". It sets your git identity, links the skill into the skill folder your agent reads (SETUP.md step 4), installs the LaTeX tools and runs the checks.
3. Hand over what you have. Put old resumes and CVs (PDF, `.tex`, Word), bios, reports and LinkedIn exports in `sources/inbox/` and say "import my old resumes". For an AI chat history, say "import my ChatGPT history" (or Claude, Gemini, Perplexity) and the agent tells you how to export it. For a logged-in website, name the site; that part needs an agent with a browser tool.
4. From then on, when something worth remembering lands in any project, say "log this to my career log"; to apply for a job, paste the posting URL and say "apply to <URL>"; for a reusable version, say "write a backend engineer resume".

Talk to your agent in any language. Records are written in English by default (change it in `direction.md`); each output picks its own language. The example data in `skills/career-log/examples/` only shows the format and is never treated as your experience.

## Features

- **Career log / brag document**: one Markdown file per job, project or course, with dated log lines, plus a bank of stories for behavioural interview questions.
- **Tailored resumes**: one-page LaTeX resumes (ATS-friendly PDF), built and layout-checked by `tools/resume.py`. Make one for a single job posting, one per target role, or a general version; a second agent reviews each before you see it. The first time you ask for a role, the agent asks what that version should lead with and saves your answer in `direction.md`.
- **Fit check**: paste a posting URL and get a go / no-go before any writing: sponsorship and clearance, where the role ranks among your targets, and each stated requirement mapped to the record that proves it, or marked as a gap. Ask for the fit alone and it stops there.
- **Job applications**: answers to the form's free-text questions, drawn from your records. Your own tools fill in the rest of the form and track the application. A resume made for one posting is saved with the posting and the answers. For a reusable version you upload yourself, git history and the application date recover the exact file (keep its file name when you upload it).
- **Interview prep**: a prep pack from what the employer will read, then a mock interview.
- **Skill gap analysis**: for one dream posting or a batch of them, a gap heatmap that separates skills your records prove from skills you only claim, and a project-first learning plan. The fit check decides whether to apply; this decides what to learn.
- **Employer ranking**: sort a career fair roster or job list by sponsorship, domain fit and size.
- **Import**: merge old resumes and CVs (PDF, Word, LaTeX), bios, reports, LinkedIn exports, AI chat histories (ChatGPT, Claude.ai, Gemini, Perplexity) and logged-in websites into one entry per experience. Reading a website, and Perplexity, which has no export, needs an agent with a browser tool.
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
- Put the graduation date where the reader sees it at once. (a recruiter's screening order, passed on by a peer)
- A skill on the Skills line also shows up in a bullet: recruiters check the Skills section against the posting, then look for experience that uses it. (the same recruiter's view)
- Show soft skills as 1–3 pieces of evidence inside technical bullets, not as bullets of their own. (a hiring engineer's advice)
- Name the exact quantity a metric measures ("p95 queue wait", not "p95 latency"). (caught by a review pass on a real application)
- Where a posting uses an umbrella term, put it in a bullet next to the concrete tool. (a low keyword-scan score on a real application)
- An outcome metric beats a caught-failure metric, and test counts are not impact. (the author's calls while drafting)

Like every rule here, these are defaults you can override (see the top of this page).

## Scope and limitations

The skill is designed for **English resumes in the North American style**: one page, the rules in [writing.md](skills/career-log/writing.md), and the bundled LaTeX template. You can talk to your agent in any language, and records can be in any language; the scope is about the resume it produces.

Other languages and resume styles depend on three planned features: custom resume templates, Typst templates, and CJK (Chinese, Japanese, Korean) resumes. Even after those land, resumes in other languages or styles **may not work as well** as North American English ones. Those features will extend the design built and tested for this style, and none of them adds rules tuned for other markets.

## How to use

Invoke the skill and say what you want. The `career-log` skill (in [`skills/career-log/`](skills/career-log/SKILL.md)) works from any session of those agents once it is linked into the skill folder your agent reads (see [SETUP.md](SETUP.md) step 4), and it picks the mode from your request. The table shows what you can ask for. The quoted phrases are examples; any wording works.

| You can ask | Mode |
|---|---|
| "log this to my career log" | **log**: append a dated line to an entry |
| "consolidate the <project> entry" | **consolidate**: fill every section, interviewing you on the gaps |
| "prep me for the <company> interview" | **interview**: prep pack from what they read, then a mock interview |
| "what should I learn for these postings", "how do I close the gap to <posting URL>" | **upskill**: evidence-based gap heatmap and a project-first learning plan |
| "rank these career fair employers" | **rank**: tiers by sponsorship, domain fit, size, with an opening line for each top employer |
| "apply to <posting URL>", "how well do I fit <posting URL>", "write a backend engineer resume" | **write**: a fit call on a posting; a resume for that posting, a target role or a general version; form answers and cover letters. Employer-facing drafts get a second-agent review and a provenance table |
| "import my old resumes" (files in `sources/inbox/`, or a logged-in site through the agent's browser) | **import**: merge old documents into entries |
| "import my ChatGPT history" (or Claude, Gemini, Perplexity) | **import**: tells you how to export it, screens every conversation, and copies only the ones you pick; the raw export stays out of git |
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
- `outputs/`: derived documents, each with a provenance table: `applications/` (one folder per application, frozen once sent), `resumes/` (one living file per resume target; git history keeps the old versions) and `reports/` (dated rankings and other reports)
- [`SETUP.md`](SETUP.md): per-machine setup for macOS, Windows and Linux
- `tools/`: LaTeX setup scripts and `resume.py` (build and layout-check a resume); usage in [latex.md](skills/career-log/latex.md)
- `skills/career-log/`: the skill itself, its [writing standards](skills/career-log/writing.md) and [examples](skills/career-log/examples/README.md)
- `sources/`: imported originals, the import inbox (`inbox/`), the [import log](sources/import-log.md) and the [source keys](sources/keys.md)
- [`GLOSSARY.md`](GLOSSARY.md) and [`docs/adr/`](docs/adr/): the repo's vocabulary and design decisions

## Upstream

This repo was created from the Template at https://github.com/mileschintw/career-log-template. Report a changed chat-export format or a broken step there, as an issue (use the "Chat export format changed" form) or a pull request. Issues are public: include keys and shapes only, never your records. The import mode drafts the report for you and asks before posting ([import-chats.md](skills/career-log/modes/import-chats.md), step 8).

## License

MIT, see [LICENSE](LICENSE). The example resume is based on the [r/EngineeringResumes template](https://github.com/r-engineeringresumes/resume-templates) (MIT).
