# Pages

Rules for a **page**: an HTML file built for the user to read, rehearse from or practise with on a screen (a teaching page, a rehearsal page, a cue card, presenter notes), often published so they can open it on a phone or tablet. Read this before building or changing one. A Markdown file the user reads as it is, in the repo, is no page.

## One source

A page is built from one Log file, its **source** (a talk script, a cue card's `.md`, `stories.md`), or is its own source when it has no Markdown twin. The text lives in the source only. A change goes into the source first, then the page is rebuilt from it. A page that needs another page's text links that page.

## Saved with the run

Save the page and its source in the application folder before you give the user its link; a page in a scratch folder alone is lost with the session. Keep a page small: inline what it needs and leave out what it does not, since every page is committed to the Log.

When you build a page, add its row to the prep file's `## Pages` table, in the form `python3 -I tools/application.py --help` gives under `prep-init`.

## Stale pages

`tools/application.py prep-status` prints a `stale:` line for each page whose source changed after the page was last built. Rebuild and republish every stale page before the mode ends, and commit the page with its source.

## Look before publishing

Render the page at the size of the device it is for (the row's `for`), look at the result, and fix what does not fit: text too small, lines cut off, a table wider than the screen. When you give the link, name each device it was not tried on.

## No state in the page

A page shows text; whatever the user marks on it stays in their browser. A verdict, a self-rating or a result from a practice goes in the practice log (`practice log:` in the prep file's header), where the next session reads it.

## Keeping them

When the application is archived, ask the user whether its pages stay in the Log. Delete the ones they let go, with their `## Pages` rows, in one commit.
