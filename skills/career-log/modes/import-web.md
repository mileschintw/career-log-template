# Import from a logged-in website

Capture a web source into `sources/<origin>/` as files, so the normal import steps can read it. This is a Browser capture: read [browser.md](../browser.md) first, with one session named for the site, opened with the signed-in profile when the site needs a sign-in ([browser.md › Sign-in](../browser.md#sign-in)). Reading is authorised by the user's request; posting, editing or sending anything on the site needs a separate yes.

## Steps

1. **Scope.** Confirm which spaces the user authorised (one project, the whole account, one profile page). Read only those; list the rest in the import log as not read.
2. **Capture.** Prefer the site's own JSON endpoints, called with `fetch` from a page on the same origin, over scraping the DOM. Recipes are below.
3. **Write the capture to a file.** Write every result straight to a file in the scratch space with `eval … --filename=<scratch>/<site>-<what>.json`, an absolute path outside the repo ([browser.md › Running it](../browser.md#running-it)), never through the reply, and parse it from there. Check the item count in the file against the page's.
4. **Write two files per source:** `<name>-prompts.md` with only the user's own messages, and `<name>-threads.md` with the full exchange. Number turns stably (`T<thread>.<turn>`, threads in order of their first turn) and add the source key's row to `sources/keys.md`. The prompts file is the user's words; the threads file is AI drafts (see *Drafts are leads*). For a chat history, save the capture as `<scratch>/capture/perplexity-capture.json` instead (create `<scratch>/capture/` first, and keep every other scratch file, such as the thread listing, outside it) and continue with [import-chats.md](import-chats.md) from step 2, whose parser writes both files and the key's row: run its `index` on that folder, `<scratch>/capture`, in place of `sources/inbox`. The capture stays in the scratch space: never copy it into `sources/inbox/`, which other sessions and imports read.
5. **Filter for privacy.** Keep only career-relevant material in the repo. Health, shopping, relationships, finances and other personal items stay out, even when the user authorised reading them; say in the import log what was left out by category.
6. **Log it** in `sources/import-log.md`: scope, counts (threads, turns, items), files written, what was skipped and why.
7. **Clear up.** Once the capture is on disk, close the session (`playwright-cli -s=<name> close`), so the captured data does not stay in page memory, and delete `.playwright-cli/` (only that folder: [browser.md › Running it](../browser.md#running-it)) and the scratch capture files after parsing.

Done when every authorised space is either captured into `sources/<origin>/` or listed as skipped with a reason.

## Recipes

### Perplexity (perplexity.ai)
Open a session on `https://www.perplexity.ai/` with the signed-in profile ([browser.md › Running it](../browser.md#running-it)). Three scripts in `tools/` make the calls from that page, each run as `playwright-cli -s=<name> run-code --filename=<root>/tools/<script>`. Each returns a summary whose `next` lines are your steps, in order; when a step runs a script again, that run's `next` lines replace the rest.
- **Threads and projects:** run `perplexity-list.js` and follow its output.
- **Capture for the chat parser:** run `perplexity-job.js` and follow its output.
- **Project files, account memories, custom instructions,** each only when the user authorised it: run `perplexity-extras.js` and follow its output.

### LinkedIn (linkedin.com)
- Read the detail pages as text: `/in/<handle>/details/projects/` and `/in/<handle>/details/experience/`. These hold the full descriptions that the main profile truncates.
- Save one snapshot per date: `sources/linkedin/<date>-projects-experience.md`, the visible text minus navigation and "viewers also viewed".
- First-person sentences ("I developed…") are the user's words; "we achieved…" is shared work until the user says otherwise.
