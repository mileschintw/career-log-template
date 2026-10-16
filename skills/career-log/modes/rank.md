# Mode: rank

Sort a list of employers (a career fair roster, a job board export, a set of postings) into tiers the user can act on, and give each worthwhile one an opening line backed by the log.

**Career fair:** when the list is a fair roster (often with a floor map), follow [../career-fair.md](../career-fair.md) as well: roster gates before research, resume and pitch per booth, a timed route, and a phone page with a redrawn map.

1. **Load the rules.** Read `direction.md` in full: the role ranking, the sorting order under Employer preferences, the Constraints, and What to emphasise, by target. Read `applications.md` for earlier contact with any listed employer.
2. **Research each employer.** For every name on the list, look up from the web, citing each fact's URL:
   - what it builds, and which teams hire engineers in the user's target areas;
   - sponsorship: whether it sponsors OPT and H-1B (H-1B filing history is public data), and whether roles need citizenship or export-control clearance;
   - size and stage.
   Mark anything not found as `GAP:`. Research in parallel (subagents) when the list is long.
3. **Score in the order `direction.md` gives.** Hard constraints first, as a gate: when `direction.md › Constraints` names work authorisation, a role that needs citizenship or clearance, or an employer that will not sponsor, is out, whatever else it offers. Then domain fit against `direction.md › Target roles, ranked`. Then size and pay.
4. **Write the tiers.** For each employer: tier, one-line reason, the sponsorship evidence, and for the top tiers an opening line that names the entry to lead with (from `direction.md › What to emphasise`) and one question to ask them. Every claim about the user traces to an entry.
5. **Show the ranking** to the user and apply their changes. Their reactions to companies are direction: record them in `direction.md`.
6. **Save** to `outputs/<YYYY-MM-DD>-<event>-ranking.md` with the sources, add the event to `applications.md › Events and contacts`, commit and push: `rank(<event>): <n> employers`.

Done when every employer on the list has a tier with sponsorship evidence or an explicit `GAP:`, every top-tier employer has an opening line traced to an entry, and the event is in `applications.md`.
