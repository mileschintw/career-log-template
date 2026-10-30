# Guide

What this repo is, what to ask it for and in what order, how it is set up, and where its files and rules come from. Written for the agent first, readable by its user too. The front page, `README.md`, is the short version for people.

## For agents

Follow this when the user asks what this repo is or can do, where to start or what to do next (`guide` in [SKILL.md › Modes](../skills/career-log/SKILL.md#modes)), or when a fresh clone's `AGENTS.md` sent you here. Commands run from the repo root, the `root:` line of the skill's `start.py` when you came through the skill ([SKILL.md](../skills/career-log/SKILL.md)); on Windows write `py -3` for `python3`.

1. **Read the state.** First `python3 -I tools/sync.py pull`, and follow its output, so a second machine's entries count. Then `python3 -I tools/config.py show`: `config.toml: missing` means this Log's setup has not run (when Python cannot start, this machine's setup has not run either). Then `python3 -I tools/entries.py list`: one line per entry, with its README status (`stub`, `imported`, `consolidated`). Done when you know whether setup has run and how many entries there are at each status.
2. **Introduce the repo** for that state, in the user's language, in a few short paragraphs: what it is (*Introduction*), where they stand in *Flows* and the step after it, and the modes that fit, each with a request from *Modes* they could say. Done when the user has read all three.
3. **Ask** what they want to do, unless their request already said it ("set me up"). Done when you know the mode to start.
4. **Hand over.** When setup has not run, or they asked to be set up: run [SETUP.md](../SETUP.md) step 3 (git identity) when its check fails, offer step 4 (skill link) for using the skill from other projects, then start the setup mode, *Trigger check* first ([SKILL.md](../skills/career-log/SKILL.md)); it runs SETUP.md step 5 itself. Otherwise start the mode they picked, the same way. Done when that mode's first step has begun.

## Introduction

career-log keeps a career log (a "brag document") in git and lets the user's AI coding agent turn it into tailored resumes, cover letters, job application answers and interview prep. It is a Log (the user's records) with its Engine (the `career-log` skill and its tools; [GLOSSARY.md](../GLOSSARY.md)).

- **Records first.** One Markdown file per experience under `entries/`, each fact with its source. Every resume bullet, answer or bio is an output derived from them, with a provenance table linking each claim to the record behind it, so the agent cannot invent anything.
- **Hand over what you have.** Old resumes and CVs, bios, reports, LinkedIn exports, AI chat histories (ChatGPT, Claude.ai, Gemini, Perplexity) and logged-in websites are merged into one entry per experience.
- **No commands to learn.** The user says what they want in their own words, in any language; SKILL.md picks the mode.
- **Log from any project.** "log this to my career log" adds a dated line to an entry and commits it, without leaving the work at hand.
- **Rules you can override.** The writing rules in [writing.md](../skills/career-log/writing.md) are defaults; the user's own preferences in `direction.md` win, and the skill records the preferences they state as they go.

Example data in `skills/career-log/examples/` only shows the format: it is never the user's experience.

## What it can do

What each mode gives the user, in more detail than *Modes*.

- **Career log / brag document**: one Markdown file per job, project or course, with dated notes waiting to be merged into it, plus a bank of stories for behavioural interview questions.
- **Tailored resumes**: LaTeX resumes, one page by default (ATS-friendly PDF), built and layout-checked by `tools/resume.py`. Make one for a single job posting (the agent looks up what the company builds and runs on, to choose what the resume leads with), one per target role, or a general version; a second agent reviews each (where your agent can, in the background, so you see the draft as soon as it builds), and nothing is saved until the review has passed. The first time you ask for a role, the agent asks what that version should lead with and saves your answer in `direction.md`.
- **Fit check and skill gaps**: ask how well you fit a posting and get a go / no-go without any writing: your hard constraints (work authorisation, for one) against the posting, where the role ranks among your targets, and each stated requirement and duty sorted into proven by a record, shallow, claimed but unproven, or a gap. Then, if you want it, a project-first learning plan for its gaps. For a batch of postings, a gap heatmap and the same kind of plan.
- **Job applications**: "apply to <posting URL>" goes straight to the resume, plus answers to the form's free-text questions, drawn from your records. Paste the questions, or the agent finds them on the posting's own page (Ashby, Greenhouse); when they sit behind a multi-step apply flow (Workday and the like), it asks you to paste them. Your own tools fill in the rest of the form and track the application. A resume made for one posting is saved with the posting and the answers. Later applications reuse that application's wordings and answers, unless you save it as Archived: kept as the record of what you sent, never reused. For a reusable version you upload yourself, git history and the application date recover the exact file (keep its file name when you upload it).
- **Interview prep**: a prep pack from what the employer will read, then a mock interview.
- **Behavioural questions**: prepare one question or a pasted list, no application needed. The agent shows the stories your log has for that question type and asks which to use; a better story it lacks gets recorded in its entry, with sources. Once you confirm them, it saves Talking points for each question type: an opening line and cue lines that point at your records, ready the next time that question comes up, and checked against any record that has changed since.
- **Employer ranking**: sort a career fair roster or job list by your hard constraints, then your own sorting order (domain fit, size, pay, ...).
- **Job scan**: collect new postings from your job sources (a job board you are signed in to, a public GitHub list of postings), drop the ones you applied to or declined, screen the rest against your entry list, give the best a full fit and rank them in a saved report. With auto-drafting on, the best few get a resume and answers on a draft branch, with every judgement call listed, until you accept one as an application. Run it by hand or as a scheduled task; it never applies, and never signs in for you.
- **Import**: merge old resumes and CVs (PDF, Word, LaTeX), bios, reports, LinkedIn exports, AI chat histories (ChatGPT, Claude.ai, Gemini, Perplexity) and logged-in websites into one entry per experience. Reading a website, and Perplexity, which has no export, uses `playwright-cli` (optional; the agent offers to install it) or the agent's own browser tool.
- **Provenance**: every output ships with a table linking each claim to its source record.

## Flows

The order users usually take the modes in. Each mode saves everything it did to the Log and git, so the next one can start in a fresh session (or after `/clear`): a session that fills up writes worse. `Session` says whether the next mode is best started fresh (`new`) or goes on in the same session (`same`).

- **First use:** setup → import → consolidate → stories → fit → write → interview.
- **Day to day:** log as things happen; consolidate an entry now and then, so its pending notes move into its sections and the agent asks about its gaps. `log` and `write` say when an entry is due, and `audit` ranks which to consolidate first.
- **A job search:** scan, then its results in the same session (scan-results: accept or decline its drafts) → fit → write → interview. `rank` sorts a list of employers the user brings (a career fair).

<!-- flows: one row per step; tools read this table (tools/guide.py flows) -->
| Flow | Mode | Next | Why | Session |
|---|---|---|---|---|
| first use | `setup` | `import` | Your old resumes, exports and chat histories become entries, so nothing has to be typed in | new |
| first use | `import` | `consolidate` | Imported entries still have gaps and pending notes; consolidating fills them, interviewing you | new |
| first use | `consolidate` | `stories` | With entries complete, pick and save the stories for behavioural questions | new |
| first use | `stories` | `fit` | Check a posting against your records before writing for it | new |
| first use | `fit` | `write` | When a posting fits, write the resume and answers for it | new |
| first use | `write` | `interview` | Once an application turns into an interview, prepare from what the employer will read | new |
| first use | `interview` | - | The last step: the next posting starts the flow again at `fit` | new |
| day to day | `log` | `consolidate` | Pending notes pile up; consolidate an entry when its experience ends or it is due | new |
| job search | `scan` | `scan-results` | Accept or decline the postings and drafts the scan just saved | same |
| job search | `scan-results` | `fit` | A posting the scan ranked but did not draft needs a full fit | new |
| job search | `fit` | `write` | When a posting fits, write the resume and answers for it | new |
| job search | `write` | `interview` | Once an application turns into an interview, prepare from what the employer will read | new |
| job search | `interview` | - | The last step: the next posting starts the flow again at `fit` | new |
<!-- /flows -->

## Modes

Each mode, a request that starts it (any wording works), and when it fits. From [SKILL.md › Modes](../skills/career-log/SKILL.md#modes).

<!-- generated by tools/guide.py: modes; edit SKILL.md › Modes, then run `python3 -I tools/guide.py write` -->
| Mode | Say, for example | When |
|---|---|---|
| **guide** | "introduce this repo and set me up", "what can it do?", "what next?" | The user asks what this repo is or can do, where to start, or what to do next |
| **log** | "log this to my career log" | Something worth remembering just happened |
| **consolidate** | "consolidate the <project> entry" | An experience has finished, or an entry is full of gaps |
| **interview** | "prep me for the <company> interview", "give me a mock interview" | An interview is scheduled, or the user wants a mock interview |
| **stories** | "prepare this BQ", "behavioural questions", a pasted list of BQs, "keep this story" | The user wants to prepare a behavioural question, no interview needed, or says a story is good and should be kept |
| **fit** | "should I apply to <URL>?", "how well do I fit <URL>?", "what should I learn for these postings?", "what should I learn to work at <kind of company>?", "does <company> sponsor H-1B?" | The user asks how well they fit a posting, whether to apply, or what they are missing for it, what to learn for the postings they target or for a kind of employer with no saved postings, or whether an employer sponsors a US visa. Not for "apply to <URL>", which is `write` |
| **write** | "apply to <URL>", "make a resume for <URL>", "write a backend engineer resume" | The user needs an output: a resume tailored to a job posting or a target role, form answers, cover letter, bio, pitch; or archives a saved application, or makes it a Reference again |
| **rank** | "rank these career fair employers" | The user has a list of employers (career fair, job board export) to sort |
| **scan** | "scan", "any new postings?", "scan the job board twice a day", "accept the <company> draft" | The user wants new postings found on their job sources, a scan on a schedule, or to handle a scan's results (accept a draft, decline postings, show the dashboard). A list the user hands over is `rank` |
| **import** | "import my old resumes", "import my ChatGPT history" | Old resumes or documents are in `sources/inbox/`, the user hands some over, or points at a logged-in web source (chat history, LinkedIn) |
| **audit** | "audit my career log" | Before a job-search push, or when asked how complete the log is |
| **setup** | "set me up", "write my records in Chinese from now on", "I don't need visa sponsorship" | The *Trigger check* says setup has not run, or the user asks to set up or to change a target, a constraint, the record language or another Config field, or an optional tool |
| **upgrade** | "upgrade to the latest Template", "upgrade my Log to 0.3.0" | The user wants this Log on a newer Template release, or names one to move to |
<!-- /generated: modes -->

## Setup

Some of what the skill does depends on who the user is, not on general resume rules: whether a role needing visa sponsorship is out, which employers come first, what a resume for a given role leads with. None of that is built in. It lives in two files of the Log: `direction.md` (Direction: what the user wants) and `config.toml` (Config: how the Engine runs for this Log). Optional tools are per machine (Machine setup, [SETUP.md](../SETUP.md) step 5).

The first request to a new Log starts the setup mode, and nothing else runs until it has: one round of questions, each with a suggested answer to accept as is ([setup.md › Quick](../skills/career-log/modes/setup.md#quick)). Ask for **advanced setup** to see every item with its current value and change any of them.

**Changing one later:** say it in your own words ("I don't need visa sponsorship", "rank employers by pay first", "write my records in Chinese from now on"). The agent shows each item before and after and writes it, dated, on a yes. "None" is an answer too. Something said about one request only ("this time, leave out the internship") changes that request and is written nowhere. A target or a work authorisation found in an import is never applied on its own: the import report lists it, and the user adopts it through setup.

**Direction items.** An empty one (no line, or only a `GAP:` line) has no default: a mode that needs it goes on without it and says what it did instead.

<!-- generated by tools/guide.py: direction; edit tools/config.py DIRECTION or tools/template/direction.md, then run `python3 -I tools/guide.py write` -->
| Item | Where it lives | What it holds |
|---|---|---|
| Target roles | `direction.md › Target roles, ranked` | A numbered list, best first. Setup fills it; empty until then. |
| Sorting order | `direction.md › Employer preferences`, its `**Sorting order` line | The sorting order for ranking employers, on a line `- **Sorting order:** …` (after your hard constraints: domain fit, size, pay, location, ...), and any other preference about employers. |
| Work authorisation, visa sponsorship, other hard constraints | `direction.md › Constraints` | Hard constraints: a role or employer that breaks one is out. One bullet each, work authorisation first (`- **Work authorisation:** …`), each followed by its source, `(user, YYYY-MM-DD)`. "None" is an answer too. Change one by saying so: setup shows it before and after and writes it on your yes. When you need US visa sponsorship, a line `- **Visa sponsorship needed:** H-1B` (or `H-1B; green card (PERM)`) right after work authorisation makes fit, scan, write and rank look up each employer's past H-1B LCA (and PERM) filings. On OPT or CPT, `OPT` or `CPT` there (joined to the visa you need next: `H-1B; OPT`) makes fit and scan quote a posting's wording that asks for unrestricted work authorisation or keeps out F-1 or J-1 students. |
| What to emphasise | `direction.md › What to emphasise, by target` | One line per resume target (`general` included): the entries to lead with and what to leave out. Experience that ended more than about five years ago stays off resumes by default (writing.md › Recency); a line here changes that window for one target or for all of them, for example "Recency: ten years, every target" or "Backend: keep <entry> despite its age". |
<!-- /generated: direction -->

**Config fields,** in `config.toml`; a field left out takes its default.

<!-- generated by tools/guide.py: config; edit tools/config.default.toml or tools/config.py, then run `python3 -I tools/guide.py write` -->
| Field | What it does | Values | Default |
|---|---|---|---|
| `record_language` | The language Log files are written in. | one line of text | `"English"` |
| `interviewer_profiles` | Interviewer profiles only signed-in members can see (LinkedIn): "never" or "always". | "never" or "always" | `"never"` |
| `front_page` | "full" (the Template's page, both languages) or "trimmed" (a personal index). | "full" or "trimmed" | `"full"` |
| `window`<br>`scheduled_window` | scan (skills/career-log/modes/scan.md): collect only postings posted in the last `window` days (1 to 90); an unattended run uses `scheduled_window` instead ("window": the same as window). | `window`: a whole number from 1 to 90<br>`scheduled_window`: "window" or a whole number from 1 to 90 | `window`: `7`<br>`scheduled_window`: `"window"` |
| `screen_budget`<br>`fit_budget`<br>`n` | scan: screen at most `screen_budget` captured postings (1 to 100); the top `fit_budget` of them (1 to 50, never above screen_budget) get a full fit, and the ranking shows the top `n` (1 to 50). | `screen_budget`: a whole number from 1 to 100<br>`fit_budget`: a whole number from 1 to 50<br>`n`: a whole number from 1 to 50 | `screen_budget`: `40`<br>`fit_budget`: `15`<br>`n`: `10` |
| `auto_write`<br>`m` | scan: "on" drafts a resume and answers for the top `m` (1 to 20); "off" drafts none. | `auto_write`: "off" or "on"<br>`m`: a whole number from 1 to 20 | `auto_write`: `"off"`<br>`m`: `5` |
| `update_check` | "on": the check every mode runs first says when a newer Template release exists (it asks GitHub at most once a day and sends nothing from the Log); "off" never asks. | "on" or "off" | `"on"` |
| `resume_max_pages` | write (skills/career-log/modes/write.md): the most pages a resume may have (1 to 3); tools/resume.py fails a longer one. 2 suits 10+ years of experience. | a whole number from 1 to 3 | `1` |
<!-- /generated: config -->

**On each machine:** TinyTeX with poppler (required, for resume PDFs) and `playwright-cli` (optional, for web pages that need scripts or a sign-in). The answer for `playwright-cli` is kept in `~/.career-log/machine.toml`, outside the repo.

**No administrator step.** Setup installs everything for the user only and asks for no password: poppler is one the user already has, or conda-forge's, which setup installs with micromamba into `~/.career-log/poppler`. On Linux, Chromium's system libraries for `playwright-cli` need sudo; setup prints that command for the user to run in their own terminal ([SETUP.md](../SETUP.md) step 5).

**Recommended:** the GitHub CLI, `gh`, and a GitHub remote for the Log. With the remote, every machine pulls the same Log, and `scan` keeps its drafts on a branch any later session can open. With `gh`, the agent reads GitHub pages (a public list of postings, the user's repos and pull requests) through the API. Also the [humanizer](https://github.com/blader/humanizer) skill: the skill runs its own AI-tell check either way ([writing.md](../skills/career-log/writing.md)), and with humanizer installed it also runs humanizer on every employer-facing output.

## Files

The Log's files, from [SKILL.md › Layout](../skills/career-log/SKILL.md#layout) and the *Files* table of each skill file with files of its own. Git keeps every file's history, so nothing keeps one inside the files.

<!-- generated by tools/guide.py: files; edit SKILL.md › Layout or a skill file's `## Files`, then run `python3 -I tools/guide.py write` -->
| Path | What |
|---|---|
| `README.md` | Index: its Entries table is a generated view, rewritten whole from the entries' front matter, one row per plain entry and one per series, newest first (`tools/entries.py --help` › README.md's Entries table). The tools that change an entry write it; after a hand edit to an entry's title, period, type, series or status, run `python3 -I <root>/tools/entries.py readme --root <root>`. An entry's status is its front matter's `status:`: `stub` (mostly `GAP`), `imported` (filled from documents or repos, not yet consolidated) or `consolidated`, optionally followed by a short note in parentheses, written with `entries.py set-status` |
| `profile.md` | Static facts: contact, education, languages, skills summary |
| `direction.md` | Direction: target roles ranked, employer preferences, constraints, emphasis by target, languages, the user's own writing preferences |
| `config.toml` | Config: how the Engine runs for this Log (record language, interviewer profiles, front page, scan settings). Written by [setup](../skills/career-log/modes/setup.md); its fields and defaults are in `tools/config.default.toml` |
| `applications.md` | Career fairs, recruiter contacts, sent versions outside an application, and applications that have no folder in `outputs/applications/` (that folder's name is the index for the rest). Not a submission tracker (`direction.md › Tools the user already uses`). Search it for the company or event; never read it whole |
| `stories.md` | Story index (behavioural question type → entry section) and the application-question bank |
| `entries/<YYYY-MM>-<slug>.md` | One file per experience. Template: `entries/_template.md`. An experience too long for one file is a series: the earliest part keeps this path, each later part is `entries/<YYYY-MM>-<slug>-<part>.md`, and every part has `series: <slug>` ([consolidate](../skills/career-log/modes/consolidate.md), its split step) |
| `outputs/applications/<YYYY-MM-DD>-<company>-<role>/` | One folder per application: posting, resume (`.tex` and the `.pdf` as sent), answers, provenance, interview packs. Frozen once sent; later interview packs and notes are added beside it. `archived.md` in it marks it Archived ([write › Save levels](../skills/career-log/modes/write.md#save-levels)) |
| `outputs/resumes/<target>.md` / `.tex` / `.pdf` | One file set per general or target resume version (`general`, `ai-infra`, `backend-infra`, ...), no date: the approved text with its provenance table, the source and the built PDF. Overwritten in place; git history holds the old versions. A version sent outside an application is recorded in `applications.md` as a commit hash ([sent-versions.md](../skills/career-log/sent-versions.md)) |
| `outputs/reports/<YYYY-MM-DD>-<slug>.md` | Dated documents that are neither a resume nor an application: rankings, fit reports (and older upskill reports), bios, pitches, reusable answers. Each has a provenance table |
| `outputs/projects/<slug>.md` | Project briefs: one per project the user said they will build, written by fit for the new project's agent ([fit-several-postings.md](../skills/career-log/modes/fit-several-postings.md) step 8). Public-safe; no mode reads them back |
| `sources/inbox/` | Files waiting to be imported. Ignored by git, so raw chat exports never get committed |
| `sources/resumes/` | Imported resume and CV originals, never edited |
| `sources/<origin>/` | Other imported originals, one folder per origin (for example `linkedin/`, `transcripts/`, one folder per chat-history export), never edited |
| `sources/import-log.md` | One section per import run: the record of what came in and what was dropped. No mode reads it to produce an output |
| `sources/keys.md` | Source keys for this log's imported material (below) |
| `tools/` | The scripts the modes run, and `tests/` for them. The trigger check: `check.py`; pulls, commits and pushes: `sync.py`; Config: `config.py`; the resume tools: [latex.md](../skills/career-log/latex.md); the chat-export parser: [modes/import-chats.md](../skills/career-log/modes/import-chats.md), and its session excerpts: [excerpts.md](../skills/career-log/excerpts.md); machine setup and the Template export: [SETUP.md](../SETUP.md) |
| `sources/<agent>/<YYYY-MM-DD>-<slug>.md` | Excerpts of agent sessions (`claude-code/`, ...), one session per file: the turns entries cite, added to by the tool, the only hand edit a redaction ([excerpts.md](../skills/career-log/excerpts.md)) |
| `outputs/reports/sponsorship.jsonl` | Each employer's US visa filings found (H-1B LCA, PERM) and the day they were looked up, reused until older than `tools/sponsorship.py --help` says; [fit.md › Sponsorship lookup](../skills/career-log/modes/fit.md#sponsorship-lookup) keeps it through `tools/sponsorship.py` |
| `scan-sources.md` | The job sources [scan](../skills/career-log/modes/scan.md) reads, one section each, with how each was last read (Log content: an endpoint found is kept here, never in the Engine) |
| `outputs/reports/<YYYY-MM-DD>-scan[-<n>].md` | A scan report, saved without approval: its pending list (each posting's status and draft), the ranking, the postings dropped at screen and those screened but not fully fitted, and the fit maps. `tools/scan.py name` gives the next one |
| `outputs/reports/scan-declined.jsonl` | Postings the user declined from a scan, newest first, with an optional reason; later scans drop them; [scan](../skills/career-log/modes/scan.md) prunes old lines |
| `outputs/dashboard/dashboard.html` | The dashboard: one read-only page of the scan's results, written by `tools/dashboard.py` from the Log and regenerated in the scan and scan-results commits; no date, no provenance table. `artifact.md` beside it holds the `Artifact: <url>` line of the page published from it ([scan-results › Dashboard](../skills/career-log/modes/scan-results.md#dashboard)) |
| `scan/<YYYY-MM-DD>[-<n>]` branches | A scan's drafts, one folder per posting under `scan-drafts/`; pushed, never merged, deleted by `tools/scan.py cleanup` ([scan-results](../skills/career-log/modes/scan-results.md#finish)) once no draft on it is pending, or by [scan](../skills/career-log/modes/scan.md)'s prune once old |
| `stories/<question-type-slug>.md` | Talking points, one file per behavioural question type; its `stories.md` row links it. Written by [stories](../skills/career-log/modes/stories.md) |
| `stories/wordings/<question-type-slug>.md` | The wordings of the behavioural questions the user brought, word for word, one file per question type, Talking points or not. Written by `tools/entries.py story-wording-add` ([stories](../skills/career-log/modes/stories.md) step 2) |
<!-- /generated: files -->

## Scope and models

The skill is designed for **English resumes in the North American style**: one page by default (`resume_max_pages`), the rules in [writing.md](../skills/career-log/writing.md), and the bundled LaTeX template built and layout-checked by `tools/resume.py`. The user can talk to the agent in any language, and records can be in any language; the scope is about the resume it produces. Custom resume templates, Typst templates and CJK resumes are planned; even then, resumes in other languages or styles may not work as well, since no rules are tuned for other markets.

How `write` (resumes and application answers) did in testing with Claude models in Claude Code:

| Model | `write` |
|---|---|
| Opus, Sonnet | Tested. Sonnet or above is recommended. |
| Haiku | Not supported. In a reference round at extra-high effort its `write` passed, but two other modes failed; earlier rounds skipped the humanizer step and set up subagents wrong ([ADR 0008](adr/0008-sonnet-is-the-lowest-supported-model.md)). |

On every model, the agent sometimes skips the one-line note it writes before starting a review or humanizer subagent; the subagent itself still runs. Sonnet also sometimes sets up a subagent wrong, less often than Haiku. Codex, Cursor and Antigravity should broadly work, but are not tested.

## Where the writing rules come from

Every rule in [writing.md](../skills/career-log/writing.md) names its source in parentheses. There are two kinds.

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

Like every rule here, these are defaults the user can override (*Introduction*).

## Where the speaking rules come from

Every rule in [speaking.md](../skills/career-log/speaking.md), which covers answers said aloud to behavioural interview questions, names its source in parentheses. They come from published guides, which anyone can check:
- [Tech Interview Handbook behavioral guide](https://www.techinterviewhandbook.org/behavioral-interview/) and its [guide for senior candidates](https://www.techinterviewhandbook.org/behavioral-interview-senior-candidates/) (`TIH`): 3–5 core stories, ending on a lesson, leading with impact for senior or complex stories, showing scope, bullet points instead of a script, adapting one story to several questions.
- [Hello Interview behavioral course](https://www.hellointerview.com/learn/behavioral/overview/introduction) (`HI`, partly paywalled): the minimum context, 3–5 core stories plus 5–7 gap fillers, a lesson as the natural end.
- [interviewing.io guide to one large tech employer's behavioral interview](https://interviewing.io/guides/amazon-behavioral-interview) and [how Meta evaluates behavioral interviews](https://interviewing.io/blog/how-software-engineering-behavioral-interviews-are-evaluated-meta) (`iio`): 80% of the answer on your own part, 10–15 minutes of follow-ups on one point, scope by people and teams.
- That employer's own [interview tips](https://aboutamazon.com/news/workplace/amazon-interview-best-tips) and [interview mistakes](https://aboutamazon.com/news/workplace/amazon-jobs-interview-mistakes) (`employer`): "I", not "we"; four minutes or less; one accomplishment per question.
- Jacob Kaplan-Moss on [the project-you-led question](https://jacobian.org/2021/feb/9/interview-questions-project-you-led/) (`jacobian`): the follow-ups an interviewer asks about one project.
- Wes Kao, [keep your backstory short](https://newsletter.weskao.com/p/in-job-interviews-keep-your-backstory) (`Kao`): 2–3 sentences and 10–15 seconds of context.

Lessons from real interviews (`practice`, `feedback`) will join them as they come up. Like the writing rules, these are defaults the user can override.
