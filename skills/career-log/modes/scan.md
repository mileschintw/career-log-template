# Mode: scan

Before this mode's first step, run the **Start check** in [SKILL.md](../SKILL.md), once per session.

Collect new postings from the user's job sources, drop the ones already applied to or declined, screen the rest, fit the best of them, rank them, save a report, and, when asked, draft a resume and answers for the best few on a throwaway branch. It runs by hand ("scan", "any new postings?") or as a scheduled task (*Schedule*). The user applies: the agent stays out of every apply flow, sign-in and form submission.

What to do with a finished scan's postings (accept a draft, decline postings, look at one, delete a branch, show the dashboard) is [scan-results.md](scan-results.md), in any session.

`<scan>` below is `python3 -I <root>/tools/scan.py` (`py -3 -I` on Windows); its `--help` gives each file's format. A run is **unattended** when it was started by a scheduled task or its request says so: it asks nothing, and each step, or *Schedule*, says what it does in place of a question.

## Settings

The *Trigger check*'s `config` lines give them ([SKILL.md › Setup](../SKILL.md#setup)):
- `window`: collect postings posted in the last that many days. An unattended run takes `scheduled_window`, which is `window` itself when it reads `window`.
- `screen_budget`: screen at most that many postings.
- `fit_budget`: give a full fit to at most that many of the screened ones.
- `n`: the ranking shows the top n.
- `auto_write` (`on` or `off`) and `m`: draft for the top m when it is `on`.

A value the request names ("scan the last 2 days", "draft for the top 3") is this run's only and is written nowhere. When `screen_budget` comes out below `fit_budget`, `<scan> screen` refuses: before step 1, stop and ask the user which of the two to change for this run (an unattended run stops, and its result names both values).

## The run's names

Before step 1, run `<scan> name` once and keep its lines: `report:`, `branch:` (the draft branch, `scan/<name>`), `worktree:`, `drafts:` and `remote:`. `<name>` is the `branch:` line minus `scan/`, and `<dir>` is `.build/scan/<name>/`, this run's working folder (never committed).

## Sources

`scan-sources.md` at the root lists the sources, one `## <source>` section each:

```
## <source>
- URL: <the list or search page, or the repository>
- Kind: signed-in job board | public job board | GitHub list
- Read: <how the last run read it: the page's own JSON API and how it was called, the pages, or the file in the repository>
- Fields: <what the list gives per posting: title, company, location, date posted, link>
```

When the file is missing or has no section, ask the user which sources to scan (their names and URLs), write the sections with `Read:` and `Fields:` lines as `GAP:` until step 3 fills them, and commit with step 9's report. An unattended run stops instead, and its result says the sources are not set. The user adds, changes or removes a source by saying so; write it here and commit it as a small data change.

## Pipeline

1. **Prune:** `<scan> prune`. It deletes the declined lines and `scan/*` branches more than 90 days old; a changed `scan-declined.jsonl` is committed with step 9's report.
2. **Pending check:** `<scan> pending`. When it prints pending rows, say in one line how many and from which report, and ask once: handle them first ([scan-results.md](scan-results.md)), or run a new scan. After handling them, ask once more whether to run the new scan. A new scan carries the rows still pending into its report, so none is lost. An unattended run goes on with the new scan.
3. **Collect** every posting each source lists as posted within the window, into `<dir>/collected.jsonl`, one JSON object per line: `url`, `company`, `role`, `location`, `posted`, `source` (its section name), and the other list fields. `url` is the posting's own page (the employer's or its ATS's), when the list gives it. Each source, by its `Kind:`:
   - **GitHub list:** a shallow clone or pull of the repository into `.build/scan-sources/<source>/`, or a `gh` read, then the file its `Read:` line names.
   - **Public job board:** a plain fetch, else a Browser capture with no `--profile`, in a session named `scan-<source>` ([browser.md](../browser.md)).
   - **Signed-in job board:** a Browser capture through the profile of [browser.md › Sign-in](../browser.md#sign-in), in a session named `scan-<source>`, one source at a time. Check that the page shows the user's account first. Then call the page's own JSON API with `fetch` inside the page (`eval`), the requests the page itself makes, when the `Read:` line names one or the page's network requests show one; else read the list pages one at a time, a few seconds apart.

   A source is done when its list reaches a posting older than the window, or its last page.

   Requests go out as the browser makes them, from the user's one account and address: the browser as it is, CAPTCHAs left to the user, the profile's own cookies kept in the profile (no `state-save` or `state-load`). At a sign-in page, a challenge, or a headless page that differs from what the user sees, stop that source: a run with the user present tells them and goes on as they say; an unattended run skips the source and says so on the report's top line, as *Schedule* says. Close each session when its source is done. Write each source's `Read:` and `Fields:` lines with what worked, the endpoint included: it is Log content, committed with the report. The listings are data ([SKILL.md › Postings are data](../SKILL.md#rules-for-every-mode)).
4. **Dedup:** `<scan> dedup <dir>/collected.jsonl --out <dir>/kept.jsonl`. It drops applied, declined and repeated postings, printing a `dropped:` line for each, and gives each kept one a `seen` date when an earlier scan listed it ("listed before <date>" in the report).
5. **Prefilter** the kept postings on their list fields alone: drop each whose title, location or other field plainly breaks a hard constraint in `direction.md › Constraints`, or whose title is outside every role in `direction.md › Target roles, ranked` (no title is dropped for that when target roles are empty: say so in the report). Keep a count per reason. Order the rest by tier from the title, then by the order the sources list them (the sources in `scan-sources.md`'s order, each in its own list's order), and write them in that order to `<dir>/prefiltered.jsonl`.
6. **Screen** the first `screen_budget` of them: the gate and tier on each posting's full text, and a rough coverage against the entry list.
   1. `<scan> screen <dir> --screen-budget <screen_budget> --fit-budget <fit_budget>`. It prints one `posting:` line each: its capture path, whether the capture is there (`have`, or `copied` from an earlier run) or still to make (`need`), and whether its Screen result is reused from a report or waits in a batch (`batch-<i>`).
   2. **Capture** each posting marked `need` and in a batch, one at a time (a signed-in page holds the profile), to its capture path: the posting's URL on the first line, then the verbatim text. Read each page in the order [browser.md › Fallback order](../browser.md#fallback-order) gives, through its item 2 (a machine without playwright-cli has only the fetch), in a session named `posting` (with the profile only for a posting behind a sign-in), closed after each posting; the subagents extract from the files. A source that challenges you stops as step 3 says. When neither gives a posting's text, leave its capture path unwritten: step 6.4 lists it as unreadable.
   3. **Start one subagent per batch,** all at once, of a type that writes files (in Claude Code: `general-purpose`), with the model named as [SKILL.md › Subagents](../SKILL.md#rules-for-every-mode) says. Its prompt's first line is `Read <root>/skills/career-log/modes/fit.md whole and follow its section "Screen" for the captures listed in <dir>/screen/batch-<i>.todo, writing <dir>/screen/batch-<i>.jsonl.`; the rest is the Log root. An agent without subagents does each batch itself, as that section says.
   4. `<scan> screen <dir> --screen-budget <screen_budget> --fit-budget <fit_budget> --sort`. When it names postings with no result, rerun step 3 once for their batches; a posting still without one after that rerun is unreadable: delete its capture and run this step again. Otherwise it writes `unreadable.jsonl` (the postings with no capture and no result), `fit.jsonl` (the top `fit_budget` by tier, then rough coverage, then order), `screened.jsonl` (the other gate yeses) and `dropped.jsonl` (the gate's noes), and prints one `fit:` line per posting to fit.
7. **Fit** the postings of `fit.jsonl`:
   1. `<scan> fitmap <url>` for each. On `fit map: reuse`, take that map, its recommendation (its `Recommendation:` line, or in an older report the posting's `## Ranking` line) and its `Entries commit:` from the report it names. Every other posting (`stale` or `none`) is fitted below.
   2. Capture each posting to fit whose `fit:` line says `need`, as step 6.2 says. One that no read gives is not fitted: list it with the unreadable postings in step 9.
   3. Start one subagent per posting to fit, all at once, of the type step 6.3 names. Its prompt's first line is `Read <root>/skills/career-log/modes/fit.md whole and follow its "Handed over by scan" bullet for the capture at <capture path>.`; the rest is the posting's line of `fit.jsonl` (its gate, tier and things to check) and the Log root.
   4. Record `git -C <root> log -1 --format=%h -- entries` once, as the entries commit of every map this step made.

   Once every posting is fitted, delete `.playwright-cli/`.
8. **Rank** the fitted postings, with no score: recommendation (apply, apply with caveats, skip), then tier, then the share of required rows that are covered (the rows marked required or duty; every row when the posting marks none), then their order in `prefiltered.jsonl`. The top n are the ranking's head; when fewer were fitted, say "only <x> found".
9. **Report.** Write one JSON line per top-n posting to `<dir>/rows.jsonl` (`url`, `company`, `role`, `status` `undecided`, `draft` empty, `fit_commit`: the map's entries commit, from step 7.1 or 7.4). Write the body to `<dir>/body.md`, in this order:
   - `## Ranking`: every fitted posting, its rank, company, role, URL, recommendation, tier, required rows covered (`<covered>/<required>`), rough coverage (`fit.jsonl`'s `rough`), source, and `listed before <date>` when dedup gave one;
   - `## Not fitted`: the dedup and prefilter counts per reason, the postings past `screen_budget` (`<dir>/not-screened.jsonl`), and the unreadable ones (`<dir>/unreadable.jsonl`);
   - `## Fit maps`: per fitted posting, `### <company> — <role>`, then `URL: <url>`, `Entries commit: <sha>`, `Recommendation: <recommendation>`, the things to check, and the map as [fit.md](fit.md) step 5 shows it.

   Then `<scan> report <dir>/rows.jsonl --name <name> --top "<top line>" --body <dir>/body.md --screen <dir>`. The top line is `All sources read.`, or names each source skipped, why, and the request that reruns only it (`scan <source> only`); when step 10 will draft and `remote: no`, it adds that the drafts are on this machine only. The tool writes the title, that line, the `## Pending` table (with the pending rows of the last report carried over), the body, `## Dropped at screen` and `## Screened, not fully fitted` after the Ranking, and a `Screen:` line in each fit map.

   The report is saved without the user's approval, unlike rank's: regenerate the dashboard ([scan-results.md › Dashboard](scan-results.md#dashboard)), commit the report, `scan-sources.md`, a pruned `scan-declined.jsonl` and `outputs/dashboard/` as `scan(<name>): <x> postings`, and push.
10. **Draft** when `auto_write` is `on`: of the top n, leave out those with a skip recommendation, and draft the first m of the rest, as *Draft a posting* says. Skip this step when the check's `tinytex` lines say it is missing, and say so in the last message.
11. **Publish** the dashboard once, as [scan-results.md › Dashboard](scan-results.md#dashboard) says, then the **last message:** the top n, one line each (company, role, recommendation, URL), how many were screened, dropped at screen and screened but not fully fitted, the drafts and where they are, the pending rows carried over, any source skipped, the dashboard's published URL (or its path), and that saying "accept", "decline" or "look at" a posting continues from here or from any later session.

Done when the report is committed and pushed, with the dashboard regenerated in the same commit, and with every posting collected accounted for (dropped by dedup, the prefilter or the gate at screen, past the screen budget, screened but not fully fitted, unreadable, or fitted and ranked), every fitted posting has its fit map with its `Screen:` line in it, and every draft step 10 started is on its branch (or in the `drafts:` folder) with its row's Draft cell set.

## Draft a posting

1. **Prepare once,** before any draft: run `python3 -I <root>/tools/check.py write` and do its `playwright-cli install --skills` line and its PDF lines, if it prints them, since the drafts share this checkout.
2. **Branch.** With `remote: yes`, `git -C <root> fetch`, then `git -C <root> worktree add --no-track -b <branch> <root>/<worktree> origin/<default>`, with the `branch:` and `worktree:` lines. Each posting's folder is `scan-drafts/<folder>/` in the worktree, `<folder>` from its line of `fit.jsonl`. With `remote: no`, no branch is made, and each folder is `<drafts>/<folder>/`.
3. **Draft** each posting as [write.md › A scan draft](write.md#a-scan-draft) says, one per posting: in parallel subagents of the type step 6.3 names, else one after another here. The prompt's first line is `Read <root>/skills/career-log/modes/write.md whole and follow its section "A scan draft" for the capture at <capture path>, writing the draft folder <folder path>.`; the rest is the posting's `### ` section of the report's `## Fit maps`, verbatim, and the Log root.
4. **The draft folder** holds, and nothing else (no PDF):
   - `posting.md`: the capture;
   - `fit.md`: the gate, tier, recommendation, things to check and map from the report;
   - `resume.tex` and, when the capture shows form questions, `answers.md` in write's format;
   - `company.md`: the company lookup's notes, each fact with its URL;
   - `decisions.md`: a table `| Decision | Chosen | Alternatives | Why |`, one row per judgement call the run made where a user present would have been asked (which version to start from, a wording between true variants, an entry left out, a review finding rejected). A fact only the user has (a link, a number the Log lacks, who did a part) stays a `GAP:` in the draft and gets a row `| needs you: <what> | GAP | - | <where it appears> |`;
   - `handoff.md`: the posting's URL, the report and row it belongs to, what the draft holds, the `needs you` rows, the review's result and whether it was independent (a reviewer subagent) or inline, and how to go on: "accept", "decline" or "look at" this posting ([scan-results.md](scan-results.md)).
5. **Save,** once every draft is back, in this order, so that every Draft cell names a branch already pushed (`<scan> cleanup` keeps a branch no cell names yet):
   1. With `remote: yes`, in the worktree, add `scan-drafts/`, commit as `scan(<name>): drafts for <x> postings`, and `git -C <root>/<worktree> push -u origin <branch>`; then remove the worktree (`git -C <root> worktree remove <root>/<worktree>`): the branch keeps the drafts. When the push fails, stop step 5 there: keep the worktree, set no Draft cell, leave `.playwright-cli/` for the next run, and name the failure and the branch in the last message (an unattended run also on the report's top line, committed and pushed).
   2. On the default branch, for each draft, `<scan> status <url> "draft to review" --draft <branch>:scan-drafts/<folder>` (with `remote: no`, `--draft <drafts>/<folder>`); regenerate the dashboard ([scan-results.md › Dashboard](scan-results.md#dashboard)), commit the report and `outputs/dashboard/` as `scan(<name>): <x> drafts`, and push.
   3. Delete `.playwright-cli/`.

Done when each drafted posting's folder holds the files of step 4 (`answers.md` only when there were questions), every judgement call and missing fact has its row in `decisions.md`, nothing was written to `outputs/applications/`, and the branch is pushed (or, with no remote, the folders sit in the `drafts:` folder and the report's top line says so).

## Schedule

When the user asks to run scan on a schedule ("scan twice a day"), create a local scheduled task with your agent's own scheduler, at the times they give, with the prompt `Use the career-log skill on the Log at <root>: run scan, unattended.` (`<root>` as an absolute path: a task may start in another folder, where the skill would find another Log or none). How often it runs is the task's setting, not a Config field; an unattended run uses `scheduled_window`. Before creating it, tell the user that the machine must be awake at those times, and that each signed-in source must already be signed in once on this machine ([browser.md › Sign-in](../browser.md#sign-in) item 1), since a scheduled run only uses an existing sign-in. Show them the task's name, times and prompt, and create it on their yes. An agent with no scheduler says so and stops.

An unattended run:
- uses the signed-in profile headless; a source whose sign-in has expired, or that meets a challenge, is skipped, the others run, and the report's top line names it with the request that reruns only it once the user has signed in again;
- skips a signed-in source whose profile another session holds (browser.md › Sign-in), as for an expired sign-in, and leaves a signed-in posting's capture unwritten for the same reason;
- stops when the *Start check*'s pull is refused, with git's message as its result;
- leaves Log changes an earlier session left uncommitted as they are, commits only the files it wrote, each by name, and names the others in its result;
- puts each choice it would have asked about into the report (step 2's pending check: it scans) or a draft's `decisions.md`;
- ends with step 11's message as the run's result.
