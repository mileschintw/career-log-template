# Import from a logged-in website

Capture a web source into `sources/<origin>/` as files, so the normal import steps can read it. Use the built-in browser, where the user is already signed in. Reading is authorised by the user's request; posting, editing or sending anything on the site needs a separate yes.

## Steps

1. **Scope.** Confirm which spaces the user authorised (one project, the whole account, one profile page). Read only those; list the rest in the import log as not read.
2. **Capture.** Prefer the site's own JSON endpoints, called with `fetch` from a page on the same origin, over scraping the DOM. Recipes are below.
3. **Handle large output.** A browser-tool result over the size limit is saved to a tool-results file as JSON `[{type, text}]`. Return big payloads in slices of about 140k characters, then in Python: take each slice's `text`, strip the trailing `\n\n(captured at origin …)` note, `json.loads` the slice if it is itself a quoted string, concatenate, and parse.
4. **Write two files per source:** `<name>-prompts.md` with only the user's own messages, and `<name>-threads.md` with the full exchange. Number turns stably (`T<thread>.<turn>`, threads in order of their first turn) and add the source key to `sources/keys.md`. The prompts file is the user's words; the threads file is AI drafts (see *Drafts are leads*).
5. **Filter for privacy.** Keep only career-relevant material in the repo. Health, shopping, relationships, finances and other personal items stay out, even when the user authorised reading them; say in the import log what was left out by category.
6. **Log it** in `sources/import-log.md`: scope, counts (threads, turns, items), files written, what was skipped and why.

Done when every authorised space is either captured into `sources/<origin>/` or listed as skipped with a reason.

## Recipes

### Perplexity (perplexity.ai)
- Projects (collections): `GET /rest/collections/list_user_collections?limit=50&offset=0` gives `title`, `uuid`, `slug`, `instructions`, `description`.
- Threads in a project: `GET /rest/collections/list_collection_threads?collection_slug=<slug>&limit=50&offset=<n>`, paged until a page has fewer than 50.
- One thread: `GET /rest/thread/<thread slug>?with_parent_info=true&with_schematized_response=true&limit=100`, following `next_cursor` (`&cursor=`). Each entry has `query_str` (the user's prompt) and `blocks`; the answer text is the block with `intended_usage == "ask_text"`, at `markdown_block.answer`.
- Project files: `GET /rest/collections/<uuid>/project_files/tree`, then `/content?path=<path>`.
- Account memories: `GET /rest/memories/list?limit=50&offset=<n>`; fields `display_key_pretty`, `display_value`. Apply the privacy filter.
- Custom instructions: `GET /rest/user/get_user_ai_profile`.
- If a call returns 401 or the page shows a login, ask the user to sign in again in the browser pane.

### LinkedIn (linkedin.com)
- Read the detail pages as text: `/in/<handle>/details/projects/` and `/in/<handle>/details/experience/`. These hold the full descriptions that the main profile truncates.
- Save one snapshot per date: `sources/linkedin/<date>-projects-experience.md`, the visible text minus navigation and "viewers also viewed".
- First-person sentences ("I developed…") are the user's words; "we achieved…" is shared work until the user says otherwise.
