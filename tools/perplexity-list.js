// Lists the threads and projects of the signed-in Perplexity account, for
// skills/career-log/modes/import-web.md › Perplexity. Run it in a session open on https://www.perplexity.ai/:
//   playwright-cli -s=<name> run-code --filename=<root>/tools/perplexity-list.js
// It leaves two page variables: window.__threads, [{slug, title, space}] merged by slug (the input of
// perplexity-job.js), and window.__projects, [{title, uuid, slug, instructions, description}]. It returns
// the counts and `next` lines, the agent's steps in order.
// Optional input: window.__terms, search words for threads a listing that ended early missed. Set them
// with eval and run this again: it adds what they find to the threads already listed.
//
// The calls, relative so they go to the page's own origin with its sign-in:
//   POST /rest/thread/list_ask_threads {limit: 100, offset, ascending, search_term}: listed newest-first,
//     and oldest-first too only when that does not reach its end; then the two must meet
//   GET /rest/collections/list_user_collections?limit=50&offset=<n>: the projects (spaces)
//   GET /rest/collections/list_collection_threads?collection_slug=<slug>&limit=50&offset=<n>: a project's
//     threads, the only listing that gives a thread's space
// Pages can come back short before the end (seen on a real account, 2026-10-24: 97 of 100 at offset 1000,
// then more), so a listing ends on an empty page or on an item whose has_next_page is false, and only
// falls back to a short page when the items carry no has_next_page; an empty page right after has_next_page
// true goes under `stopped`, as a cap would. A failed page ends that listing and is
// reported under `stopped`, except the first page of the newest-first listing: its failure (often a lost
// sign-in) stops the script and is reported under `errors`.
async page => page.evaluate(async () => {
  const cli = 'playwright-cli -s=<name>', run = `${cli} run-code --filename=<root>/tools/perplexity-list.js`;
  if (!/^https?:$/.test(location.protocol))
    return {state: 'no page', next: [`Open https://www.perplexity.ai/ in this session first: ${cli} goto "https://www.perplexity.ai/". Then run this script again: ${run}.`]};
  const items = j => (Array.isArray(j) ? j : Object.values(j || {}).find(Array.isArray) || []);
  async function call(url, body) {
    const r = await fetch(url, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : undefined);
    if (!r.ok) throw new Error(`HTTP ${r.status} from ${url.split('?')[0]}`);
    return r.json();
  }
  const stopped = [];
  async function pages(what, get, size, maxPages, fatal) {
    const out = [];
    out.ended = false;
    for (let p = 0; p < maxPages; p++) {
      let got;
      try { got = items(await get(p * size)); }
      catch (err) { if (fatal && p === 0) throw err; stopped.push(`${what} at offset ${p * size}: ${err.message}`); break; }
      out.push(...got);
      const last = Object(got[got.length - 1]);
      if (!got.length && p && Object(out[out.length - 1]).has_next_page === true) { stopped.push(`${what} at offset ${p * size}: an empty page, though the one before said has_next_page`); break; }
      if (!got.length || last.has_next_page === false || (got.length < size && !('has_next_page' in last))) { out.ended = true; break; }
      if (p === maxPages - 1) stopped.push(`${what}: ${maxPages} pages without an end`);
    }
    return out;
  }
  const account = (ascending, term) => pages(term ? `search "${term}"` : ascending ? 'oldest first' : 'newest first',
    offset => call('/rest/thread/list_ask_threads', {limit: 100, offset, ascending, search_term: term}), 100, 200, !ascending && !term);

  const bySlug = new Map((window.__threads || []).map(t => [t.slug, t]));
  const before = bySlug.size;
  function add(list, space) {
    for (const t of list) {
      if (!t || !t.slug) continue;
      const old = bySlug.get(t.slug);
      if (!old) bySlug.set(t.slug, {slug: t.slug, title: t.title || '', space: space || ''});
      else if (space && !old.space) old.space = space;
    }
  }

  const terms = Array.isArray(window.__terms) ? window.__terms.map(String) : [];
  const errors = [];
  let newest = [], oldest = [], projects = [], projectThreads = 0;
  try {
    newest = await account(false, '');
    if (!newest.ended) oldest = await account(true, '');
    add(newest); add(oldest);
    projects = await pages('projects', o => call(`/rest/collections/list_user_collections?limit=50&offset=${o}`), 50, 200);
    for (const p of projects) {
      const list = await pages(`project ${p.slug}`,
        o => call(`/rest/collections/list_collection_threads?collection_slug=${encodeURIComponent(p.slug)}&limit=50&offset=${o}`), 50, 200);
      projectThreads += list.length;
      add(list, p.title || p.slug);
    }
    for (const term of terms) add(await account(false, term));
  } catch (err) { errors.push(String(err.message || err)); }

  window.__threads = [...bySlug.values()];
  window.__projects = projects.map(p => ({title: p.title || '', uuid: p.uuid || '', slug: p.slug || '',
    instructions: p.instructions || '', description: p.description || ''}));
  const seen = new Set(newest.map(t => t.slug));
  const complete = newest.ended || oldest.some(t => seen.has(t.slug));
  const out = {threads: window.__threads.length, added: window.__threads.length - before, newest_first: newest.length,
    oldest_first: oldest.length, complete, projects: projects.length, project_threads: projectThreads,
    searched: terms, stopped, errors, next: []};
  const signIn = `have the user sign in again (browser.md › Sign-in item 3), reopen the session (item 2), then run this script again: ${run}.`;
  if (errors.length) {
    out.next.push(`The first listing call failed (errors). On HTTP 401 or 403, or a login page, ${signIn} Otherwise run this script again once; if it fails again, stop and show the user the errors.`);
    return out;
  }
  if (!newest.length) { out.next.push(`The account listing is empty. If the user says the account has threads, ${signIn}`); return out; }
  if (stopped.length) out.next.push(`Some listings stopped early (stopped). Run this script again once, keeping the threads already listed: ${run}. If you already ran it again for this, name those listings in the import log as possibly incomplete and follow the next lines.`);
  const oldestStopped = !oldest.length && stopped.some(s => s.startsWith('oldest first'));
  if (!complete && !oldestStopped) out.next.push(terms.length
    ? `Threads may still be missing between the newest-first and oldest-first listings. If added is 0, go on with the next line. Otherwise add new career and technical words (from direction.md and the entry titles) to window.__terms and run this script again. Say in the import log that the listing may be incomplete.`
    : `The newest-first listing did not reach its end and the oldest-first listing does not meet it, so threads between them are missing. Set career and technical search words (from direction.md and the entry titles) with ${cli} eval "() => { window.__terms = ['<word>', '<word>'] }" and run this script again: ${run}. Say in the import log that the listing may be incomplete.`);
  out.next.push(`Write the listings for the import log: ${cli} eval "() => window.__threads" --filename=<scratch>/perplexity-threads.json (check: it lists ${out.threads} threads), then ${cli} eval "() => window.__projects" --filename=<scratch>/perplexity-projects.json.`);
  out.next.push(`Capture the threads: ${cli} run-code --filename=<root>/tools/perplexity-job.js.`);
  return out;
})
