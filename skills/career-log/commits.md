# Commits: bulk changes and denied names

The parts of [SKILL.md › Commits](SKILL.md#rules-for-every-mode) that only some modes reach: committing a bulk data change, and appending names to `.export-deny`.

## Bulk data changes

The working tree is the staging area: write every file of the change and leave them uncommitted until the user's yes. Show the user what `python3 -I <root>/tools/sync.py status` prints and a short summary naming each entry created or changed, and ask them to read the full diff in their editor. If they ask for changes, apply them and show the status again. Then:
- **Yes:** `python3 -I <root>/tools/sync.py settle commit --subject "<the mode's message>"`.
- **No:** first move each original that [import](modes/import.md) step 1 moved out of `sources/inbox/` back into it, under its old name (the inbox is ignored, so it holds the user's only copy); then `python3 -I <root>/tools/sync.py settle discard --sources-checked`.

## Names appended to `.export-deny`

When a mode says to deny the names of some entry files and `.export-deny` exists, run `python3 -I <root>/tools/deny_coverage.py entry --root <root> --commit <entry file>...` with one path per entry file the mode names, at once: before the mode commits the entries, and outside any bulk change's yes or no, so a Template export never scans with an old list. Follow its output; done when it prints `OK:` or ends with `sync: ok`.
