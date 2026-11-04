# fit: Plan preview

The Plan preview of [fit-several-postings.md](fit-several-postings.md) step 6, which a one-posting plan reaches through that step too: what the planned projects would earn once they land, the resume bullets and the heatmap change, so the plan has a concrete goal. It is a **lead** ([SKILL.md › Drafts are leads](../SKILL.md#rules-for-every-mode)): goals that steer the work. Evidence for a resume or a later fit comes from the entries the projects end in.

Step 6 sends you here once the user has answered which skills they will pursue and the items they named are planned.

1. **Bullets.** For each project in the study order, one or two resume bullets as they would read once its finish line is met: an action verb, what was built, and the result its **Credible result** part is built to produce. A materials-only line gets none. Write each number as a goal, inside a mark `<target: <value> vs <baseline>, measured by <how>>`: `Cut p99 latency <target: 40% vs the single-node baseline, measured by a 10k-request load test>`. A count, a size or a speed-up is a number too; name technologies without their versions. Pick the value that would move the user; the project's result will replace it.
2. **Heatmap change.** In prose: the critical and high rows, by `skill` as the heatmap names them, that would turn covered once every project lands, each with the project that covers it; then the gaps count of the `Heatmap:` line (fit-several-postings step 5) as it would read, `<target: <n> gaps vs <now> now>`.
3. **Write and show.** Open with this line, the heading and the warning in one:

   `# Plan preview (a lead): goals for the planned projects, not results; the evidence comes from the entries they end in`

   Then step 1's bullets under each project's name, then step 2's prose. Write it to `<root>/plan-previews/<YYYY-MM-DD>-<scope>.md`: `<scope>` the one fit-several-postings step 7 names the report by, or, for a one-posting plan, the part after `fit-` of the file name on the `save:` line of `python3 -I <root>/tools/fit.py --root <root> map <map file> --save-name`. Each run writes a new file: when that name is taken, add `-2`, `-3`, … before `.md`. The preview lives in chat and in that file. `.gitignore` keeps `plan-previews/` out of git and no tool cleans it, so tell the user the file's full path and that it is not in git: backing it up is theirs.

   Show the preview whole in chat, in the message that hands back the plan's save, right below its answer ([SKILL.md › Chat output](../SKILL.md#rules-for-every-mode) item 1), the heading line and then every line of the file as it stands, copied line for line, with the path and the not-in-git line under it.

Then go on with the plan's save: fit-several-postings step 7, or, for a one-posting plan, the save of [fit.md](fit.md) step 7.

Done when every project in the study order has its bullets, every number in the bullets and step 2's prose sits inside a `<target: …>` mark, the file starts with the heading line, the chat showed the file's text whole, heading line first, and the file exists with `git -C <root> check-ignore <its path>` printing its path (git ignores it).
