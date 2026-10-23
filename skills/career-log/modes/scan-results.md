# scan: the results

Before this file's first step, run the **Start check** in [SKILL.md](../SKILL.md), once per session (the `scan` *Trigger check* covers this file).

What to do with the postings a [scan](scan.md) found, in any session, from the files alone: the newest report's `## Pending` table, its `## Screened, not fully fitted` table, and each draft folder. It comes after scan's pending check, or on requests such as "show the pending postings", "look at the Acme draft", "accept it", "decline these", "show the dashboard". `<scan>` is as [scan.md](scan.md) defines it.

## Show the list

`<scan> pending`: one line per pending posting (company, role, status, where its draft is, URL), from the report it names. For each, `<scan> fitmap <url>`; `stale` means an entry its map cites has changed since, so say so beside the posting. Then ask once: "Any to drop? A reason is optional." (*Decline*).

## Act on a posting

Each is the user's choice, on the posting they name:
- **Look at a draft** whose Draft cell is `scan/<name>:<path>`: `git -C <root> fetch`, then read each file of the folder with `git -C <root> show origin/scan/<name>:<path>/<file>` (a `.build/scan/` cell is the folder itself, on this machine). Show `handoff.md`, the `needs you` rows of `decisions.md`, the other decisions, the resume and answers, and the fit result. Then ask about dropping it, as *Show the list* does.
- **Look at a posting with no draft:** a pending row with no draft shows its fit map from the report. A posting under `## Screened, not fully fitted` has had no full fit: run fit's one-posting run on its URL ([fit.md](fit.md)), which offers the next step as usual.
- **Accept a draft,** to take it on as an application:
  1. Ask the `needs you` rows; record each answer in the entry it belongs to, as [write.md](write.md) step 7 says, and put it in the draft.
  2. Read the folder's files as *Look at a draft* says, then copy `resume.tex` to `.build/drafts/<folder>/` and build it there, after the PDF lines `python3 -I <root>/tools/check.py write` prints, if any. The draft folder's files are the write posting run's draft: the capture is the posting, `fit.md` the map, `company.md` the lookup notes.
  3. Check the draft claim by claim against the entries as they are now (write step 7), then review it as write step 8 says, with this session's reviewer: the draft's own review ran in another session, so it does not count for step 10.
  4. Go on as write step 9, showing the draft. Every request for approval ends with the line `Save as Archived (default) or Reference?`, in place of step 9's line, until the user picks one: a scan draft saves Archived unless the user says Reference ([write.md › Save levels](write.md#save-levels)).
  5. Save as write step 10 says. Before its commit, run `<scan> status <url> accepted --draft outputs/applications/<the folder step 10 saves>/`, then regenerate the dashboard (*Dashboard*), and add the report and `outputs/dashboard/` to that commit.

  A pending posting with no draft is accepted as an ordinary write posting run on its URL, saved at write's own default level, with the same status line before its save.
- **Decline:** for each posting the user names, `<scan> status <url> declined --reason "<reason, or empty>"`, which also adds it to `scan-declined.jsonl`, so later scans drop it. A reason that states a preference, a hard constraint or a reaction to the company also goes into `direction.md` ([SKILL.md › Direction upkeep](../SKILL.md#rules-for-every-mode); a Direction item through [setup › Changes](setup.md#changes)): show the new line first and write it on the user's yes. A reason about this posting alone stays in the jsonl. The same line declines a posting under `## Screened, not fully fitted`, which has no Pending row.

A posting the user leaves undecided stays pending, and the next scan's report carries it.

## Finish

1. **Commit** the report and `scan-declined.jsonl`, when an accept did not commit them already, with the dashboard regenerated (*Dashboard*), as `scan(<name>): <x> accepted, <y> declined`, and push. When nothing was left to commit and `<dashboard> --check` (*Dashboard*) prints `stale`, regenerate and commit as *Show* does. Then publish the dashboard, once, when a commit of this flow changed it.
2. **Clean up:** `<scan> cleanup`. It deletes each `scan/*` branch, local and on origin, whose every draft is accepted or declined, and keeps the others. Delete each `.build/scan/<name>/` folder whose report's postings are all accepted or declined.

Done when every posting the user acted on has its new status in the newest report that lists it, committed and pushed; every accepted draft is an application folder, saved in the same commit as its row; `<scan> cleanup` printed a line for each branch; and `<dashboard> --check` prints `dashboard: up to date`.

## Dashboard

`outputs/dashboard/dashboard.html` is one read-only page of the scan's results, generated from the Log by `<dashboard>`: `python3 -I <root>/tools/dashboard.py` (`py -3 -I` on Windows), whose `--help` lists its sections and the files that feed each. The tool writes it; the Log stays the source.

- **Regenerate** before every commit that changes a scan report, `scan-declined.jsonl` or an application folder, in this file and in [scan.md](scan.md): run `<dashboard>` and add `outputs/dashboard/` to the commit. A commit made elsewhere (write's own save) leaves the page behind until the next one; `<dashboard> --check` says whether it is.
- **Show** ("show the dashboard", "open the dashboard"): run `<dashboard>`; when it prints `wrote:`, commit `outputs/dashboard/` as `dashboard: regenerate` and push. Then publish, after `unchanged:` too, and give the user the published URL, or the file's path.
- **Publish** once a flow's last commit that changed `dashboard.html` is pushed (scan step 11, *Finish* step 1, *Show*), without asking, when your agent can publish an HTML file as a private hosted page (in Claude Code, the Artifact tool), an unattended run included. Read `dashboard.html` before publishing it (Claude's Artifact tool publishes only a file the session has read; a first publish takes the icon `chart`). The tool's `artifact:` line names the page already published:
  1. **A URL:** read that page with the tool (Claude's Artifact tool refuses to update a page the session has not read), then publish the file to that URL. When the read or the publish fails because the page is gone or belongs to another account, go on as for `none`.
  2. **`none`:** publish the file as a new page. Write its URL to `outputs/dashboard/artifact.md` as the one line `Artifact: <url>`, commit that file as `dashboard: artifact`, and push.

  An agent that cannot publish names the file's path instead: it opens in any browser.

Done when `<dashboard> --check` prints `dashboard: up to date` on the committed page, and, where the agent can publish, the last publish succeeded or the last message names its failure and the file's path.
