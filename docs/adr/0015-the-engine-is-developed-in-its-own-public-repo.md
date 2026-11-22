# The Engine is developed in its own public repo, apart from any Log

Supersedes [ADR 0001](0001-engine-and-log-share-one-repo.md), whose revisit condition now holds: the Template has had an outside user who filed issues on it, releases are versioned and a Log can upgrade ([ADR 0011](0011-template-versions-and-upgrades.md)). One half of ADR 0001 stays: the skill still finds the Log by resolving the git repo it sits in, and the Template is still a GitHub template repository, not a plugin. The other half goes: the Engine is no longer developed inside the maintainer's Log.

Sharing one repo cost four things (#562). Every export depended on `.export-deny`, `tools/deny_coverage.py` and source-only blocks to keep one person's records out of the Template. The repo had to be private, so CI minutes were billed. The maintainer's Log never upgraded, so the upgrade path was tested on scratch Logs only. And issues and pull requests on the public Template arrived in a snapshot and were taken back by hand.

So there are three repos:

| Repo | Holds | Visibility |
|---|---|---|
| **Engine repo**, `career-log-engine` | The Engine's source and everything only its maintainer needs: the maintainer docs, `maintainer/`, CI, `docs/agents/`, `docs/research/`, the project's agent settings, the `coord` branch | Public |
| **Template**, `career-log-template` | The allowlist export of the Engine repo, as before | Public |
| **The maintainer's Log**, `career-log` | One person's Log, kept current with the upgrade mode like any other Log | Private |

- **The repo that held both stays the Log.** It keeps its history, its issues and pull requests and its old `coord` branch, all private. The Engine repo starts a new history from a snapshot with no Log in it. The other direction, keeping the old repo as the Engine repo and filtering the Log out of its history, would have to clean every commit, issue, pull request and coordination record of personal content, and a pull request cannot be moved at all.
- **The export stays**, because "Use this template" copies every file on the default branch and the maintainer's files must not reach a user's agent. What retires in the Engine repo is the part that guarded a Log sitting beside the source: the `tools/deny_coverage.py` gate before an export and the `.export-allow` masking. The `.export-deny` scan stays, since every Log has it.
- **A push is a publication.** The Engine repo is public, so the guard moves from the export to the push: a local pre-push check there scans the commits about to leave against the `.export-deny` of the maintainer's own Log, read from its checkout on the same machine. That list is itself personal and never enters the Engine repo.
- **The Engine repo is the one place for issues and pull requests.** The Template's issue forms point to it. Taking an upstream issue or pull request back by hand ends with that.
- **Old issues stay where they are.** The issues open at the split are rewritten without personal content and opened again in the Engine repo; nothing is transferred, since a transfer publishes each body and comment as written.
- **Dev builds.** On each merge to the Engine repo's default branch, CI commits the export to a `builds` branch there and tags it `v<next version>-dev.<n>`. A dev build is an export, never a tag on a source commit: an upgrade checks the Engine paths out of the tag as they are, so a source commit would bring unstripped source-only blocks and the maintainer's CI into a Log. This amends ADR 0011, where a build stamped `next` is one no Log upgrades from or to: a dev build carries a pre-release version a Log can upgrade to and from. The upgrade mode takes one only when `--to` names it; by default it still picks the newest release on the Template, and the Template never carries a dev tag. Anyone may follow dev builds, with no promise that one is stable.
- **The maintainer's Log follows dev builds**, so the upgrade path runs on real records between releases. To try a change before it is merged, the maintainer tags the same export in a local repo and upgrades from that path. The inner loop of a change still runs on scratch Logs.
- **A guide's steps can be run again.** A Log that follows dev builds runs `upgrade-next.*` on each of them and once more at the release, while the guide is still being written. Each step and each check must therefore leave already-migrated data alone.
- **No Engine edit in a Log.** A fault found while using the maintainer's Log becomes an issue in the Engine repo and is fixed there. A rule that concerns only the maintainer as a user of their Log (the language to answer in) lives with that Log's agent, not in the Engine repo's maintainer docs.
- **The maintainer's Log joins at a release.** The first release made from the Engine repo is where it starts: its Engine paths are replaced by that release's export, the maintainer's files are removed, `tools/TEMPLATE_VERSION` is stamped with that version, and the result is checked to be the same tree as the release. Stamping it with an earlier release it never matched would give every later merge the wrong base.

Releases stay as ADR 0011 has them: the maintainer decides when and which version, and publishes by hand; only dev builds are automatic. The Engine repo carries the Template's licence.

## The order of the split

1. Find why pull request CI stopped starting (#790), so a broken workflow is not carried over.
2. Clean the snapshot of personal content, create the Engine repo from it, and get its CI green.
3. Build the dev build channel and the pre-push check there.
4. Publish the first release from the Engine repo, and check that its export matches what the old repo would have exported from the same Engine.
5. Turn the old repo into a Log, as above.
6. Point the Template's issue forms at the Engine repo, reopen the open issues there, and drop the two "taking back" procedures.

No other Engine change lands between steps 2 and 5.

## Consequences

- An Engine change reaches the maintainer's Log through a dev build and an upgrade, not at once. The upgrade needs a clean tree and several steps, so trying a change on real records costs more than it did.
- `tools/upgrade.py` must order pre-release versions, take one only on `--to`, and find the tag a Log on a dev build came from, which is not on the Template.
- The Engine repo's history starts at the split. What came before is read in the private repo.
- The maintainer docs, the coordination records and every commit message are public from the first push. The pre-push check covers the names `.export-deny` lists and nothing else.
- The rules that kept billed CI minutes low no longer bind; whether to relax them is left to the work that follows.

## Considered options

- **Develop in the Template repo itself.** Every user would get the maintainer's files: `AGENTS.md` loads into their agent, `.claude/settings.json` would ask them to install the maintainer's plugins, and each upgrade would write them into their Log again.
- **Run the Engine from its checkout against a Log elsewhere**, a `--root` for the skill's entry point. It is the fastest loop, but the Log's own Engine files would never change, so the upgrade path would stay unused, and there would be a second way to find the Log.
- **Dev builds kept on the maintainer's machine only.** Nobody else could try a fix before its release, and each one would be made by hand.
- **Keep the Engine repo private.** It keeps billed CI and the hand-carried upstream issues, the two costs the split is meant to end.
- **Transfer the old issues.** It keeps the numbers and redirects, and publishes every body and comment unread.
- **A no-reply address for commits in the Engine repo.** The maintainer's address is already in the public Template's history, so a change would only stop further exposure; the maintainer chose to keep it.
