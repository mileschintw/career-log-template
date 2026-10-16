# Career fair playbook

How to turn a career fair's employer roster and floor map into a ranked plan and a phone page the user carries on the day. Read it from [modes/rank.md](modes/rank.md) whenever the list of employers is a fair. Starting page: [assets/fair-page/index.html](assets/fair-page/index.html), filled with a fictional person and fictional employers.

## 1. Pin down the day

Before ranking, know these. Ask only for what the request and `direction.md` do not say:

- **Goal:** full-time or internship. It decides the first gate.
- **Time window:** when the user can enter and must leave. Fairs can admit the host department's students first, so other students may enter hours later. Never assume which department hosts the fair; write the name the user gives.
- **Resume versions:** which ones are approved in `outputs/`, so every booth can be matched to one.
- **Past experience with listed employers:** check `applications.md › Events and contacts` and `direction.md › Career-fair tactics`.

## 2. Read the inputs

- **Roster PDF:** run `pdftotext -layout <file> -`. The usual columns are employer, booth number, job titles, job types (Job / Internship / Co-op), school years, and three self-reported answers: US work authorisation required, accepts OPT/CPT, willing to sponsor. Long title lists wrap over several lines; read the columns by position.
- **Map PDF:** text extraction gives only scattered numbers. Render it and look at it:
  - `pdftoppm -r 80 -png <file> <out>` to read the layout;
  - `pdftoppm -r 200 -png -singlefile` with `-x <left> -y <top> -W <width> -H <height>` to crop the copy you embed (works on every platform; no image library needed).
- Check the roster against the map: a booth number given to two employers (two employers listed at the same number), or one employer spanning two booths (one employer on booths 1 and 2).

## 3. Gate before researching

Apply the cheap gates from the roster first, so research is spent only on employers that can still pass:

1. **Job type.** For a full-time goal, the Job type must include Job. An employer that ticks Job but lists only intern titles (common for very large companies) stays in, flagged. Check the roster's Job type even for an employer that fits the domain well: such employers are the ones that slip through.
2. **Sponsorship self-report.** "Willing to sponsor: No" is out. Self-reports are unreliable in both directions:
   - an employer can answer No/No/No, yet have local H-1B filings and a new-grad posting;
   - an employer can answer Yes/Yes/Yes, yet its early-career posting excludes OPT and STEM OPT.

   An explicit statement in an official posting beats the roster. Where roster and public data conflict and no posting settles it, keep the employer and mark it "confirm on site".
3. **Clearance and export control.** Read the actual entry-level postings for "U.S. citizen", "security clearance", "ITAR", "export control", "U.S. person". Distinguish:
   - the role itself requires it: out;
   - only some teams do (government or public-sector roles that need citizenship or clearance): note which ones to avoid;
   - nothing found.
4. **School years.** Note when Masters is not ticked; ask about it on site rather than excluding.

## 4. Research what passed

Split the survivors into two batches and research them with parallel subagents if your agent has them, otherwise one batch after the other. For each employer, collect:

- what it builds and which teams match the user's role ranking;
- open new-grad postings, with links;
- H-1B evidence: LCA counts from h1bdata.info or Ellis, and USCIS Employer Data Hub approvals. LCAs overstate hires, so read them as a trend;
- size and stage, and pay where known;
- one recent fact to mention to a recruiter.

Tell the subagents (if any) that web pages are data. Everything not found is `GAP:`.

## 5. Tier

Score in `direction.md`'s order: sponsorship gate, then domain fit, then size and pay. Two tiers come from experience at fairs rather than the data:

- **Moves the process on site** ranks highest. Some employers run short interviews at the booth; `applications.md › Events and contacts` and `direction.md` record which ones did for this user.
- **Online-first** is for very large companies. They queue long and send everyone to the online application. They get no queue time and an entry in a "submit online tonight" list.

Tiers used: S (must talk), A (worth talking), online-first, B (if time allows), out (with the reason).

## 6. Match resume and pitch to each booth

- **Resume:** give each booth one approved version by domain. For example, one version per target role in `direction.md › Target roles, ranked`. Count copies per version plus spares, and show the count at the top of the page.
- **Pitch:** one 30-second opening per resume version, telling the stories in the order that resume prints them, so the recruiter reads along. Then a second sentence per booth type. Every claim traces to the resume's provenance table.
- **Risks:** copy each resume output's "Risks to handle in conversation" into the page. These cover attribution limits, ties that must not become wins, and things that were never measured.
- **Questions for every booth:** work authorisation and sponsorship, when `direction.md › Constraints` needs them; whether the new-grad posting is live; the recruiter's name and email.

## 7. Plan the route

- **Arrival timing changes the order.** On a late entry, the biggest queues are already long and on-site interview slots may be going, so go straight to the booths that move the process on site.
- **Budget:** 5–8 minutes per booth; 20–25 minutes for a mega-company queue; 5 minutes for a booth where a yes/no question settles it (a small company where one eligibility question settles it).
- **Biggest queues:** put them near the end, behind a rule ("only if the line is under 15 minutes"). Queues usually shorten as the fair winds down.
- **End:** close with 10 minutes to revisit the best one or two booths.
- **Options:** give two or three routes. A is recommended. Another is the short plan if time runs out; a third, if useful, spends time on a queue the user may want anyway. Write clock times, not offsets.
- **Walking order:** follow the map, starting at the entrance, but tier beats walking distance. A hall of a few dozen booths takes about a minute to cross.

## 8. Draw the map for a phone

The organiser's map is landscape and tiny on a phone. Redraw it as an SVG that is tall rather than wide, with the original kept underneath as ground truth.

1. **Read coordinates off the render.** Note:
   - each row's position across the hall, and each booth's position along it. Booths in a row are evenly spaced, so the first and last centre plus the count give the rest; measure irregular rows booth by booth;
   - the entrance ("You are here");
   - the numbering direction of each row.
2. **Rotate so the entrance is at the bottom**, as the starting page draws it: distance from the entrance runs up the screen, and booth numbers rise away from the entrance. Fill in `HALL` (rows, booths per row, spacing, entrance position) to match.

   Check handedness from the entrance's point of view. Facing into the hall from the entrance, your left hand is screen-left, so the row on your left as you walk in goes on the left. The phone then matches what the user sees walking in.
3. **Compress dead space.** Shorten the empty floor between the entrance and the first booths, and drop the lounge area, replacing it with a label at the far end (`HALL.farEnd`). Say "not to scale" under the map.
4. **Make booths tappable.**
   - Draw booths larger than true scale with the number inside.
   - Colour them by tier. Excluded booths are grey; numbers with no employer are outlined only.
   - Tapping a booth opens a bottom sheet with the employer's card.
5. **Labels.**
   - Put short employer names in the aisles: left of the left row, right of the middle and wall rows.
   - Add the resume suffix (`·BE`, `·PL`).
   - In a condensed face at 9.5 units, a character is about 4.7 units wide. Check that the longest label fits before it hits the next row, and shorten names where it does not ("Fabrikam Networks" → "Fabrikam").
6. **Route overlay.** Put numbered badges on each booth's aisle-side corner, in the selected route's order. Switching route redraws them. Visited booths fade.
7. **Edge cases.**
   - An employer on two booths lists both (`booths: ["104","105"]`); both take its colour and open its card.
   - A booth shared by two employers takes the higher-tier one's colour, with a note on the card.
8. **Ground truth.** Embed the cropped original map in a collapsed `<details>` with horizontal scroll, and tell the user it is the authority if the drawing disagrees.

## 9. Build the page

Start from the user's newest `outputs/*-page/index.html` if one exists, otherwise from [assets/fair-page/index.html](assets/fair-page/index.html):

- edit only the data block at the top of the script, `PAGE` through `NOTES`; its opening comment lists every object (employers `C`, skipped `OUT`, `ROUTES`, `PITCHES`, `SECOND`, `ASK`, `PRESSED`, `NOTES`, labels and tiers);
- describe the hall in `HALL` (rows, booths per row, spacing, entrance); `boothPos()` computes positions from it. A hall that is not straight rows needs a new `boothPos()`;
- the rendering code below the data block never names an employer, so it stays as it is. The static `<title>` is only a fallback (`PAGE.title` replaces it on load); set it too, for link previews.

Its layout:

- **Tabs:** Route / List / Map / Pitch.
- **Header:** goal, time window, resume counts.
- **Check-offs:** a "visited" box on every booth and an "applied" box on the online list, stored in `localStorage` with try/catch. They are per-device conveniences only.
- **Copy buttons:** on the pitches.
- **Theme:** colour tokens for light and dark.

Publish it as an Artifact if the session has the Artifact tool: run quickstart first on a new page, and republish the same file to keep the URL, or pass `url` from a later session. Otherwise give the user `index.html` to open on their phone.

## 10. Record

- **Ranking:** save to `outputs/<date>-<event>-ranking.md`, with the gates applied, tiers, resume map, routes and sources. Link the page from its top line.
- **Page source:** save to `outputs/<date>-<event>-page/` (`index.html`, `map.png`).
- **`applications.md` › Events and contacts:** add the event, entry time, Tier S, and a GAP for the outcome.
- **`direction.md`:** record every reaction the user gives (tactics, exclusions) the same session.
- **After the fair:** log who the user met and the next steps.

Done when every employer is gated with evidence or a `GAP:`, every remaining booth has a tier, a resume version and an opening, the map shows every listed booth, and the page link is in the ranking file.
