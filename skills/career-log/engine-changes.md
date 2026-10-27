# Engine changes

The branch, issue and pull-request flow for an Engine change (a parser fix, a change to the skill, a tool or the Template skeleton: any path [AGENTS.md › Changes](../../AGENTS.md#changes) lists), its exceptions, and what the Template export needs: no personal content in Engine files, and the checks a Log with no CI runs itself.

## Steps

1. Work on a branch in a worktree (under `.worktrees/`, or where the agent's tooling puts them) started from the default branch: `git fetch`, then `git worktree add --no-track .worktrees/<topic> -b <branch> origin/<default>`; `--no-track` keeps a push from ever landing on the default branch.
2. Open an issue describing the change.
3. Commit and push the branch as often as the work needs: the push backs the work up and lets another machine see it.
4. Open the pull request, with `Closes #<issue>`, only once the change is finished: the issue's fix is done and the checks [SETUP.md](../../SETUP.md) step 7 runs for what changed have run, so the user reviews one finished diff.
5. Once it is open, gather the fixes from a review and push them together, not one push per fix.
6. Merge only when the user says so.

## Exceptions

- **No `gh` or GitHub remote:** show the user the branch's diff instead, and merge it locally with `git merge --no-ff` only on their yes.
- **Guard files** go straight to the default branch at once, even while a bulk data change waits for the user's yes, because they protect the main checkout and every export made from it: the names the `import`, `log` and `consolidate` modes, or a `tools/deny_coverage.py` failure, append to `.export-deny`; on the user's word, a name a `tools/deny_coverage.py` failure clears into `.export-cleared` and the `.export-deny` line it takes out; and the `sources/inbox/` lines that the `gitignore inbox:` step of `tools/check.py import` restores to `.gitignore`.
- **Data and Engine in one session:** commit the data and the Engine change separately, each its own way.
- **An Engine commit that went straight to the default branch:** revert it there and re-land it through a pull request; never rewrite the published history.

## The Template export

`tools/export-template.sh <dest>` builds the shareable Template: the Engine paths [AGENTS.md › Changes](../../AGENTS.md#changes) lists, plus the empty Log skeleton in `tools/template/`. Keep every Engine file free of personal content: no names, employers, projects, dates or quotes from this Log. Those belong in the Log files (`direction.md`, entries). It exports committed content only, so commit before exporting. It scans file names and contents for the patterns in `.export-deny` and fails on a hit; the `import`, `log` and `consolidate` modes append new employer and project names, and the export refuses an empty list.

A Log made from the Template has no CI: after an Engine change, run the checks [SETUP.md](../../SETUP.md) step 7 runs for what changed, and report their results before asking the user to merge.
