# Import from a logged-in website

Capture a web source into `sources/<origin>/` as files, so the normal import steps can read it. This is a Browser capture: read [browser.md](../browser.md) first, with one session named for the site, opened with the signed-in profile when the site needs a sign-in ([browser.md › Sign-in](../browser.md#sign-in)). Reading is authorised by the user's request; posting, editing or sending anything on the site needs a separate yes.

## Steps

1. **Scope.** Confirm which spaces the user authorised (one project, the whole account, one profile page). Read only those; list the rest in the import log as not read.
2. **Capture.** Prefer the site's own JSON endpoints, called with `fetch` from a page on the same origin, over scraping the DOM. Recipes are below.
3. **Write the capture to a file.** Write every result straight to a file in the scratch space with `eval … --filename=<scratch>/<site>-<what>.json`, an absolute path outside the repo ([browser.md › Running it](../browser.md#running-it)), never through the reply, and parse it from there. Check the item count in the file against the page's.
4. **Write two files per source:** `<name>-prompts.md` with only the user's own messages, and `<name>-threads.md` with the full exchange. Number turns stably (`T<thread>.<turn>`, threads in order of their first turn) and add the source key to `sources/keys.md`. The prompts file is the user's words; the threads file is AI drafts (see *Drafts are leads*). For a chat history, save the capture as `<scratch>/capture/perplexity-capture.json` instead (create `<scratch>/capture/` first, and keep every other scratch file, such as the thread listing, outside it) and continue with [import-chats.md](import-chats.md) from step 2, whose parser writes both files: run its `index` on that folder, `<scratch>/capture`, in place of `sources/inbox`. The capture stays in the scratch space: never copy it into `sources/inbox/`, which other sessions and imports read.
5. **Filter for privacy.** Keep only career-relevant material in the repo. Health, shopping, relationships, finances and other personal items stay out, even when the user authorised reading them; say in the import log what was left out by category.
6. **Log it** in `sources/import-log.md`: scope, counts (threads, turns, items), files written, what was skipped and why.
7. **Clear up.** Once the capture is on disk, close the session (`playwright-cli -s=<name> close`), so the captured data does not stay in page memory, and delete `.playwright-cli/` (only that folder: [browser.md › Running it](../browser.md#running-it)) and the scratch capture files after parsing.

Done when every authorised space is either captured into `sources/<origin>/` or listed as skipped with a reason.

## Recipes

### Perplexity (perplexity.ai)
Open a session on `https://www.perplexity.ai/` with the signed-in profile ([browser.md › Running it](../browser.md#running-it)), and run each call as `fetch` inside an `eval` there, writing its result to a file. Responses are JSON.
- **All threads in the account:** `POST /rest/thread/list_ask_threads` with body `{"limit": 100, "offset": <n>, "ascending": false, "search_term": ""}`. Each item has `slug`, `title` and `last_query_datetime`. Paging stops at about 1,000 threads per direction. For a larger account, also list with `"ascending": true`, list each project (below), and run `search_term` with career and technical words to recover the middle. Merge by `slug`. Say in the import log that the listing may be incomplete.
- **Projects (spaces):** `GET /rest/collections/list_user_collections?limit=50&offset=0` gives `title`, `uuid`, `slug`, `instructions`, `description`.
- **Threads in a project:** `GET /rest/collections/list_collection_threads?collection_slug=<slug>&limit=50&offset=<n>`, paged until a page has fewer than 50. This listing gives each thread's space.
- **One thread:** `GET /rest/thread/<thread slug>?with_parent_info=true&with_schematized_response=true&limit=100`, following `next_cursor` (`&cursor=`). Each entry has `query_str` (the user's prompt), `updated_datetime`, `attachments` and `blocks`. The answer text is in the block with `intended_usage == "ask_text"`, at `markdown_block.answer`.
- **Capture for the chat parser:** a list of `{slug, title, space, entries: [{t, q, a, att}]}`, where `t` is the entry's time, `q` the prompt, `a` the answer and `att` the attachment file names. Save it as `perplexity-capture.json` (the parser only opens files named like an export). Fetching hundreds of threads takes longer than one tool call, so run the listing calls in one `eval` that sets `window.__threads = [{slug, title, space}, …]` in the page and returns its length (write `() => window.__threads` to a file too, for the import log), save the script below as `.build/perplexity-job.js`, and start it with `playwright-cli -s=<name> run-code --filename=.build/perplexity-job.js`: it returns at once while the job runs on in the page. Check on it in later calls with `eval "() => [window.__cap.length + window.__err.length, window.__done]"` against the number of threads, and once `window.__done` is true write the capture with `eval "() => window.__cap" --filename=<scratch>/capture/perplexity-capture.json`. It runs four threads at a time. A thread that fails (HTTP error, a login page, bad JSON) goes to `window.__err` with its slug instead of stopping the job; retry those once at the end, and list any that still fail in the import log.

  ```js
  async page => page.evaluate(() => {
  window.__cap = []; window.__err = []; window.__done = false;
  window.__job = (async (threads) => {  // threads: [{slug, title, space}] from the listings
    const queue = threads.slice();
    async function one(th) {
      const entries = [], seen = new Set();
      let cursor = null;
      for (let page = 0; page < 50; page++) {  // a cap, in case the API repeats a cursor
        const u = `/rest/thread/${th.slug}?with_parent_info=true&with_schematized_response=true&limit=100` +
          (cursor ? `&cursor=${encodeURIComponent(cursor)}` : '');
        const r = await fetch(u);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        for (const e of j.entries || []) {
          const b = (e.blocks || []).find(b => b.intended_usage === 'ask_text' && b.markdown_block);
          entries.push({t: e.updated_datetime || e.created_datetime || '', q: e.query_str || '',
            a: b ? b.markdown_block.answer || '' : '',
            att: (e.attachments || []).map(a => typeof a === 'string' ? a.split('/').pop() : a.name || a.file_name || '')});
        }
        cursor = j.next_cursor || null;
        if (!cursor || seen.has(cursor)) break;
        seen.add(cursor);
      }
      return entries;
    }
    async function worker() {
      while (queue.length) {
        const th = queue.shift();
        try { window.__cap.push({...th, entries: await one(th)}); }
        catch (err) { window.__err.push({slug: th.slug, error: String(err)}); }
      }
    }
    await Promise.all([1, 2, 3, 4].map(worker));
    window.__done = true;
  })(window.__threads);
  })
  ```
- **Project files:** `GET /rest/collections/<uuid>/project_files/tree`, then `/content?path=<path>`.
- **Account memories:** `GET /rest/memories/list?limit=50&offset=<n>`; fields `display_key_pretty`, `display_value`. Apply the privacy filter.
- **Custom instructions:** `GET /rest/user/get_user_ai_profile`.
- If a call returns 401 or the page shows a login, or the first page of `list_ask_threads` comes back empty while the user says the account has threads, have the user sign in again ([browser.md › Sign-in](../browser.md#sign-in) item 3).

### LinkedIn (linkedin.com)
- Read the detail pages as text: `/in/<handle>/details/projects/` and `/in/<handle>/details/experience/`. These hold the full descriptions that the main profile truncates.
- Save one snapshot per date: `sources/linkedin/<date>-projects-experience.md`, the visible text minus navigation and "viewers also viewed".
- First-person sentences ("I developed…") are the user's words; "we achieved…" is shared work until the user says otherwise.
