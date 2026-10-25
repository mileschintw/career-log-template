# scan: the results

Before this file's first step, run the **Trigger check** in [SKILL.md](../SKILL.md) with the mode `scan`: it covers this file.

What to do with the postings a [scan](scan.md) found, in any session, from the files alone: the newest report's `## Pending` table, its `## Screened, not fully fitted` table, and each draft folder. It comes after scan's pending check, or on requests such as "show the pending postings", "look at the Acme draft", "accept it", "decline these", "show the dashboard". `<scan>` is as [scan.md](scan.md) defines it.

## Show the list

`<scan> pending`: show its lines, one per pending posting; beside one whose fit map is `stale`, say that an entry its map cites has changed since (`reuse`: none has, so the map still holds; `none`: the report has no map for it; `unknown`: git could not say). On `pending: none`, say there is none and skip the question. Otherwise ask once: "Any to drop? A reason is optional." (*Decline*).

## Act on a posting

Each is the user's choice, on the posting they name:
- **Look at a draft:** `<scan> draft <url>`, which copies the draft's files into the folder its `folder:` line names; read them there (on a refusal, follow its `next:` line). Show `handoff.md`, the `needs you` rows of `decisions.md`, the other decisions, the resume and answers, and the fit result. Then ask about dropping it, as *Show the list* does.
- **Look at a posting with no draft:** a pending row with no draft shows its fit map from the report `<scan> fitmap <url>` names. A posting under `## Screened, not fully fitted` has had no full fit: run fit's one-posting run on its URL ([fit.md](fit.md)), which offers the next step as usual.
- **Accept a draft,** to take it on as an application:
  1. `<scan> draft <url>` (after a look too: it keeps the files the look copied; on a refusal, follow its `next:` line); the files in its `folder:` are the write posting run's draft: `posting.md` is the posting, `fit.md` the map, `company.md` the lookup notes. Ask its `needs you:` rows; record each answer in the entry, or `profile.md`, it belongs to, as [write.md](write.md) step 7 says, and put it in the draft there.
  2. Build that folder's `resume.tex` there, after the PDF lines `python3 -I <root>/tools/check.py write` prints, if any.
  3. Check the draft claim by claim against the entries as they are now (write step 7), then review it as write step 8 says, with this session's reviewer: the draft's own review ran in another session, so it does not count for step 10.
  4. Go on as write step 9, showing the draft. Every request for approval ends with the line `Save as Archived (default) or Reference?`, in place of step 9's line, until the user picks one: a scan draft saves Archived unless the user says Reference ([write.md › Save levels](write.md#save-levels)).
  5. Save as write step 10 says. Before its commit, run `<scan> status <url> accepted --draft outputs/applications/<the folder step 10 saves>/`, and add the report and `outputs/dashboard/` to that commit.

  A pending posting with no draft is accepted as an ordinary write posting run on its URL, saved at write's own default level, with the same status line before its save.
- **Decline:** for each posting the user names, `<scan> status <url> declined --reason "<reason, or empty>"`. A reason that states a preference, a hard constraint or a reaction to the company also goes into `direction.md`, as [SKILL.md › Direction upkeep](../SKILL.md#rules-for-every-mode) says. A reason about this posting alone stays in `scan-declined.jsonl`, where `status` wrote it. The same line declines a posting under `## Screened, not fully fitted`, which has no Pending row.

A posting the user leaves undecided stays pending, and the next scan's report carries it.

## Finish

1. **Commit** the newest report (`<report>`) and `scan-declined.jsonl`, when an accept did not commit them already: `python3 -I <root>/tools/sync.py commit "<the subject of the last status's commit: line>" -- <report> outputs/reports/scan-declined.jsonl outputs/dashboard/`. When nothing was left to commit and `<dashboard> --check` (*Dashboard*) prints `stale`, regenerate and commit as *Show* does. Then publish the dashboard, once, when a commit of this flow changed it.
2. **Clean up:** `<scan> cleanup`.
3. **Next up**, after the clean-up: run the command [SKILL.md › Next up](../SKILL.md#rules-for-every-mode) gives, with `scan-results`.

Done when every posting the user acted on has its new status in the newest report that lists it, committed and pushed; every accepted draft is an application folder, saved in the same commit as its row; `<scan> cleanup` printed a line for each branch and run folder; and `<dashboard> --check` prints `dashboard: up to date`. The last message ends with the Next up block.

## Dashboard

`outputs/dashboard/dashboard.html` is one read-only page of the scan's results, generated from the Log by `<dashboard>`: `python3 -I <root>/tools/dashboard.py` (`py -3 -I` on Windows), whose `--help` lists its sections and the files that feed each. The tool writes it; the Log stays the source.

- **Regenerate:** `<scan> report` and `<scan> status` regenerate the page themselves; their commits add `outputs/dashboard/`. A commit made elsewhere (write's own save) leaves the page behind until the next one; `<dashboard> --check` says whether it is.
- **Show** ("show the dashboard", "open the dashboard"): run `<dashboard>`, then `python3 -I <root>/tools/sync.py commit "dashboard: regenerate" -- outputs/dashboard/` (`<scan> status` may have written the page since its last commit; a page already committed leaves nothing to commit). Then publish, and give the user the published URL, or the file's path.
- **Publish** once a flow's last commit that changed `dashboard.html` is pushed (scan step 11, *Finish* step 1, *Show*), without asking, when your agent can publish an HTML file as a private hosted page (in Claude Code, the Artifact tool), an unattended run included. Read `dashboard.html` before publishing it (Claude's Artifact tool publishes only a file the session has read; a first publish takes the icon `chart`). The tool's `artifact:` line names the page already published:
  1. **A URL:** read that page with the tool (Claude's Artifact tool refuses to update a page the session has not read), then publish the file to that URL. When the read or the publish fails because the page is gone or belongs to another account, go on as for `none`.
  2. **`none`:** publish the file as a new page, then run `<dashboard> --artifact <its URL>`; when it prints a `commit:` line, `python3 -I <root>/tools/sync.py commit "<its subject>" -- outputs/dashboard/artifact.md`.

  An agent that cannot publish names the file's path instead: it opens in any browser.

Done when `<dashboard> --check` prints `dashboard: up to date` on the committed page, and, where the agent can publish, the last publish succeeded or the last message names its failure and the file's path.
