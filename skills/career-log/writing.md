# Writing standards

Rules every output follows, whoever the log belongs to. `write` and the review pass check drafts against this file. The user's own preferences live in `direction.md › Writing preferences for applications`; where the two disagree, the user's preference wins.

Each rule names where it comes from:
- **r/ER**: the r/EngineeringResumes wiki ([index](https://www.reddit.com/r/EngineeringResumes/wiki/index/), read 2026-10-15; [sample bullet points](https://www.reddit.com/r/EngineeringResumes/wiki/sample-bullet-points/)) and its [LaTeX template](https://github.com/r-engineeringresumes/resume-templates) (MIT);
- **humanizer**: the [`humanizer`](https://github.com/blader/humanizer) skill, based on Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
- **r/csCQ**: an [r/cscareerquestions resume guide](https://www.reddit.com/r/cscareerquestions/comments/1577dm9/the_ultimate_guide_to_writing_your_resuume_for/) by a senior engineer who reviews resumes, two rules adopted;
- **TIH**: the [Tech Interview Handbook resume guide](https://www.techinterviewhandbook.org/resume/), two rules adopted; on format r/ER wins;
- **practice**: the author's calls and observations while preparing real applications with this skill;
- **feedback**: advice from recruiters, hiring engineers, interviewers or peers.

## AI-tell check

Run this on every draft before the user sees it, then once more on the final text.

1. **No em dashes** (—) in sentences. Use a comma, a colon, parentheses or two sentences. Date ranges keep their en dash (`--` in LaTeX). (humanizer)
2. **No inflated significance.** No "pivotal", "testament to", "plays a crucial role", "in today's fast-paced world". Say what happened. (humanizer)
3. **No stock AI words.** Delve, leverage (as a verb for "use"), seamless, robust, showcase, foster, spearhead, harness, tapestry, landscape. (humanizer)
4. **No forced groups of three.** List as many items as there are. (humanizer)
5. **No bold mini-headings** inside prose answers, and no "**Label:** text" lists where a sentence would do. (humanizer)
6. **No chatbot closers or openers.** No "I hope this helps", "Great question", "In conclusion". (humanizer)
7. **No not-X-but-Y contrasts** set up only to knock down. (humanizer)
8. **No filler.** Cut any sentence whose removal loses nothing. (humanizer)
9. **No repeating what the form or resume already shows**: GPA, school name, timeline, program name. Spend the words on what the reader cannot see elsewhere. (practice)

**Second layer.** If the `humanizer` skill is available in this session, run it on the final text of every employer-facing output after the check above. If it is not available, the check above is the whole pass; do not stop or ask for it.

## Resumes

### Format

- **Template:** the r/EngineeringResumes LaTeX template, single column, no icons or graphics. Editing and building: [latex.md](latex.md). (r/ER)
- **One page**, unless the user has 10+ years of experience. (r/ER)
- **Bullets** are one sentence and at most 2 lines, and a wrapped bullet's last line is not a fragment of 1–4 words. `tools/resume.py` checks the lines. No personal pronouns, no trailing periods. (r/ER)
- **Opening verbs** are strong and past tense (built, designed, reduced), not weak (helped, assisted, worked on) and not inflated (spearheaded, orchestrated, leveraged). Vary them within a section. (r/ER)
- **Bold** sparingly. r/ER advises against bolding keywords inside bullets; follow the user's approved versions if they do. (r/ER)
- **Dates** sit at the right margin. No summary section unless the user is senior, changing careers or explaining a gap; no references section. (r/ER)
- **The graduation date** sits where the reader sees it at once. (feedback)
- **A promotion at one employer** shows as two titles with their own dates. Don't merge or hide it. (practice)
- **Plain-text check:** paste the resume as plain text to check that an ATS reads it in order. (TIH)

### Content

- **Each bullet shows impact**: what was done, how, and the measured result (XYZ: "accomplished X as measured by Y by doing Z", or STAR / CAR). Accomplishments, not duties. Order bullets from most to least impressive. (r/ER)
- **Keep measured metrics** in bullets, as digits with their exact labels. Lead with the action and put the metric right after it or at the end: a bullet that opens with the number hides what the person did. (r/ER; feedback)
- **Keep a range** when the measurement is a range ("2–10x"), not its best case. (practice)
- **A metric's label names the exact quantity measured**: "p95 queue wait", not "p95 latency", when the number is how long jobs waited in the queue. (practice)
- **An outcome metric beats a caught-failure metric** on the page. A skimmer reads "checkout conversion 2.1% → 2.6%" as a result; "caught 312 of 400 requests timing out" reads as "the system was broken". Caught-failure stories go to interviews. (practice)
- **No test counts** as resume content: anyone can write a thousand tests. (practice)
- **Soft skills** appear as 1–3 pieces of leadership or collaboration evidence inside technical bullets, not as separate bullets. (feedback)
- **Courses** are listed by topic when the catalogue title would not mean anything to the reader. (practice)
- **GPA in the Education section** depends on stage: list it for internships, optional at entry level, dropped from mid level on. (r/csCQ)
- **Projects with real users** or active maintenance beat coursework and tutorial clones; rank and choose projects by that. (r/csCQ)
- **Three strong bullets beat four** with a weak one. (practice)
- **On a new-grad resume**, trim inside projects before cutting work bullets. (practice)
- **Local agency and standard names** are translated into the pattern a reader in the target market knows. (practice)
- **Spell out an abbreviation** on first use when the reader may not know it. (TIH)

### Skills section

- **Titled "Skills"**, grouped by category, items comma-separated with their proper names ("C, C++", not "C/C++"). No soft skills, operating systems, editors or proficiency labels. A skill listed here also shows up in a bullet where the log has one that uses it: recruiters check the Skills section against the posting, then look for experience that uses those skills, work before projects. A skill the posting needs and the log records but no bullet can show still gets listed, under **Thin evidence is flagged** below. (r/ER; feedback)
- **List what the user installs, runs or operates:** languages, frameworks, libraries, databases, services. Protocols, standards and algorithms (OAuth 2.0, HTTP/2, consistent hashing) go in the bullets, where the context shows the user understands them; ATS reads the bullets too. An exception needs strong evidence that it helps relevance; argue it out and ask the user if still unsure. (practice)
- **Names follow postings:** write a tool the way postings write it, and list only tools postings name. A concept that is not a tool ("rate limiting") stays in the bullets. (practice)
- **Umbrella terms:** where a posting uses one ("data pipelines"), put that term in a bullet next to the concrete tool. (practice)
- **Each item fits its line's label.** When a tool fits no line, rename the label or leave the tool off; a misfiled tool reads as not knowing what it is. (practice)
- **Fill each line by relevance**, as far as it goes without wrapping: posting-named tools first, weaker but still relevant tools in the tail. Tools from shared projects count even where the user did not write that code, as long as the entry records them. (practice)
- **Thin evidence is flagged.** A skill listed on thin evidence (coursework only, never used in a project) goes on `profile.md › Interview prep list`, so `interview` mode reviews it. (practice)
