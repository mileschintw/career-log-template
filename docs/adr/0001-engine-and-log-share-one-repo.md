# Engine and Log share one repo; the Template is a repo, not a plugin

The skill finds the Log by resolving the git repo it sits in, so the Engine and one person's Log live in the same repo, and the shareable Template is a GitHub template repository built from it. Splitting the Engine into a Claude Code plugin would let others pull updates automatically, but it needs a new way to locate the Log, a migration of the author's daily repo, and re-verification on macOS and Windows: two to three times the work, for an update channel nobody needs yet. Revisit if several people want ongoing Engine updates.

## Consequences

The Template is a snapshot. Refreshing it means re-running the allowlist export from the author's repo, so the Engine in that repo must stay free of personal content.
