// Captures the listed Perplexity threads for the chat parser, for
// skills/career-log/modes/import-web.md › Perplexity. Run it after perplexity-list.js, in the same session:
//   playwright-cli -s=<name> run-code --filename=<root>/tools/perplexity-job.js
// Fetching hundreds of threads takes longer than one call, so the first run starts the capture in the page,
// four threads at a time, and returns while it goes on. Each run waits up to 20 s for it to end and returns
// how far it got, with `next` lines, the agent's steps in order. A run after the end starts any listed
// thread not captured yet (after perplexity-list.js added some), or else retries each failed thread once.
// When a thread failed with HTTP 401 or 403 or a page that is not JSON, it first checks that the session
// is still signed in, with the first page of the thread listing, and asks for a sign-in only if not.
// Input: window.__threads, [{slug, title, space}]. Output: window.__cap, the capture
// [{slug, title, space, entries: [{t, q, a, att}]}] that tools/chat_export.py reads (t the entry's time,
// q the prompt, a the answer, att the attachment file names), and window.__err, the threads that failed
// (HTTP error, a login page, bad JSON), each with its error. window.__waitMs, for tests, shortens the wait.
//
// The call: GET /rest/thread/<slug>?with_parent_info=true&with_schematized_response=true&limit=100,
// following next_cursor (&cursor=). The answer is the block whose intended_usage is "ask_text", at
// markdown_block.answer.
async page => page.evaluate(async () => {
  const WAIT_MS = window.__waitMs || 20000, PAGES = 50;  // PAGES caps a thread whose API repeats a cursor
  const cli = 'playwright-cli -s=<name>', run = `${cli} run-code --filename=<root>/tools/perplexity-job.js`;
  if (!/^https?:$/.test(location.protocol))
    return {state: 'no page', next: [`Open https://www.perplexity.ai/ in this session first: ${cli} goto "https://www.perplexity.ai/". Then list the threads: ${cli} run-code --filename=<root>/tools/perplexity-list.js.`]};
  if (!Array.isArray(window.__threads))
    return {state: 'no listing', next: [`List the threads first: ${cli} run-code --filename=<root>/tools/perplexity-list.js.`]};

  async function one(th) {
    const entries = [], seen = new Set();
    let cursor = null;
    for (let p = 0; p < PAGES; p++) {
      const r = await fetch(`/rest/thread/${encodeURIComponent(th.slug)}?with_parent_info=true&with_schematized_response=true&limit=100` +
        (cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''));
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      for (const e of j.entries || []) {
        const b = (e.blocks || []).find(b => b && b.intended_usage === 'ask_text' && b.markdown_block);
        entries.push({t: e.updated_datetime || e.created_datetime || '', q: e.query_str || '',
          a: b ? b.markdown_block.answer || '' : '',
          att: (e.attachments || []).filter(a => a).map(a => (typeof a === 'string' ? a.split('/').pop() : a.name || a.file_name || ''))});
      }
      cursor = j.next_cursor || null;
      if (!cursor || seen.has(cursor)) break;
      seen.add(cursor);
    }
    return entries;
  }
  function start(threads) {
    window.__done = false;
    window.__job = (async () => {
      const queue = threads.slice();
      async function worker() {
        while (queue.length) {
          const th = queue.shift();
          try { window.__cap.push({...th, entries: await one(th)}); }
          catch (err) { window.__err.push({...th, error: String(err)}); }
        }
      }
      try { await Promise.all([1, 2, 3, 4].map(worker)); } finally { window.__done = true; }
    })();
    return threads.length;
  }

  window.__cap = window.__cap || [];
  window.__err = window.__err || [];
  window.__retried = window.__retried || [];  // slugs retried once already
  let started = 0, retrying = false;
  if (window.__done !== false) {
    const have = new Set([...window.__cap, ...window.__err].map(t => t.slug));
    const todo = window.__threads.filter(t => !have.has(t.slug));
    const again = window.__err.filter(t => !window.__retried.includes(t.slug));
    if (todo.length) started = start(todo);
    else if (again.length) {
      window.__err = window.__err.filter(t => window.__retried.includes(t.slug));
      window.__retried.push(...again.map(t => t.slug));
      retrying = true;
      started = start(again.map(({error, ...th}) => th));
    }
  }
  const until = Date.now() + WAIT_MS;
  while (!window.__done && Date.now() < until) await new Promise(r => setTimeout(r, 250));

  const out = {state: window.__done ? 'done' : 'running', started, retrying, captured: window.__cap.length,
    failed: window.__err.length, threads: window.__threads.length, next: []};
  if (!window.__done) { out.next.push(`Run this script again to check on it: ${run}.`); return out; }
  if (window.__err.some(t => /HTTP 40[13]|JSON|Unexpected token/.test(t.error))) {
    let signedIn = false;
    try {
      const r = await fetch('/rest/thread/list_ask_threads', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({limit: 100, offset: 0, ascending: false, search_term: ''})});
      const j = r.ok ? await r.json() : null;  // a signed-out page may answer an empty listing
      signedIn = (Array.isArray(j) ? j : Object.values(j || {}).find(Array.isArray) || []).length > 0;
    } catch (_) { /* signed out */ }
    if (!signedIn) {
      out.next.push(`Threads failed with HTTP 401 or 403 or a login page, and the thread listing fails too: the session is signed out. Have the user sign in again (browser.md › Sign-in item 3), reopen the session (item 2), then run perplexity-list.js and this script again.`);
      return out;
    }
  }
  const unretried = window.__err.filter(t => !window.__retried.includes(t.slug)).length;
  if (unretried) { out.next.push(`Run this script again: it retries the ${unretried} failed threads once. ${run}.`); return out; }
  out.next.push(`Write the capture (create <scratch>/capture/ first): ${cli} eval "() => window.__cap" --filename=<scratch>/capture/perplexity-capture.json. Check: the file lists ${out.captured} threads.`);
  if (out.failed) out.next.push(`List the ${out.failed} threads that still failed in the import log: ${cli} eval "() => window.__err" --filename=<scratch>/perplexity-failed.json.`);
  out.next.push('Then go on with import-web.md step 4.');
  return out;
})
