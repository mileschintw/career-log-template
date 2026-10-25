// A made-up Perplexity API for the tests of tools/perplexity-*.js: it answers the calls those scripts make,
// with the shapes skills/career-log/modes/import-web.md › Perplexity documents, from a spec instead of an account.
// It holds no real data. Used by perplexity_harness.js (unit tests) and, served over HTTP, by a manual run
// of the scripts through playwright-cli.
//
// spec fields, all optional:
//   threads    number of account threads, newest first: slug t<i>, title "<word> thread <i>" (default 5)
//   words      words the titles cycle through, for search_term (default ["notes"])
//   hidden     [<index>...]: threads the listings leave out, so a page comes back short before the end, as
//              on a real account; every listed item carries has_next_page, false on the last page
//   cap        how many threads list_ask_threads gives per direction (default: all); past it, capError
//              decides: true answers HTTP 400, otherwise an empty page; noNext: items carry no has_next_page
//   projects   [{title, uuid, slug, threads: [<index>...], broken: true}]: a broken project's listing answers HTTP 500
//   entries    entries per thread (default 2); pageSize: entries per page of a thread, to exercise next_cursor
//   fail       {<slug>: <n>}: the first n requests for that thread answer HTTP 500; html: [<slug>]: answer a login page
//   memories   number of memories; files: {<uuid>: [<path>...]}; profile: the custom-instructions object
//   wrap       true wraps every listing in {data: [...]}, as an API that returns an object would
//   unauth     true answers HTTP 401 to everything; unauthAfter: n answers HTTP 401 from the (n+1)th call on
'use strict';

function makeFake(spec = {}) {
  const n = spec.threads ?? 5, words = spec.words || ['notes'], cap = spec.cap ?? Infinity, hidden = new Set(spec.hidden || []);
  const entries = spec.entries ?? 2, pageSize = spec.pageSize || 100;
  const fail = Object.assign({}, spec.fail || {});
  const threads = Array.from({length: n}, (_, i) => ({
    i, slug: `t${i}`, title: `${words[i % words.length]} thread ${i}`,
    last_query_datetime: new Date(Date.UTC(2030, 0, 1) - i * 3600e3).toISOString(),
  }));
  const projects = spec.projects || [];
  const list = a => (spec.wrap ? {data: a} : a);
  const json = (body, status = 200) => ({status, body: JSON.stringify(body), type: 'application/json'});
  // One page of a listing: offset and limit count every thread, hidden ones too, so a page with one is short
  function paged(a, offset, limit, end = a.length) {
    const more = offset + limit < a.length;  // a cap hides the rest without saying so
    return a.slice(offset, Math.min(offset + limit, end)).filter(t => !hidden.has(t.i))
      .map(({i, ...t}) => (spec.noNext ? t : {...t, has_next_page: more}));
  }
  const page = (a, q, size) => paged(a, +q.get('offset') || 0, +q.get('limit') || size);

  function entry(slug, k) {
    return {query_str: `question ${k} of ${slug}`, updated_datetime: `2030-01-01T00:0${k % 10}:00Z`,
      attachments: k === 0 ? ['https://files.example/u/a1/report.pdf?sig=x', {name: 'notes.txt'}] : [],
      blocks: [{intended_usage: 'web_results'}, {intended_usage: 'ask_text', markdown_block: {answer: `answer ${k} of ${slug}`}}]};
  }

  let served = 0;
  return function handle(method, url, body) {
    if (spec.unauth || (spec.unauthAfter !== undefined && served++ >= spec.unauthAfter)) return json({error: 'unauthorized'}, 401);
    const u = new URL(url, 'https://fake.test'), q = u.searchParams, p = u.pathname;
    if (method === 'POST' && p === '/rest/thread/list_ask_threads') {
      const b = JSON.parse(body || '{}');
      let a = threads.filter(t => !b.search_term || t.title.toLowerCase().includes(String(b.search_term).toLowerCase()));
      if (b.ascending) a = a.slice().reverse();
      if (b.offset >= cap) return spec.capError ? json({error: 'offset too large'}, 400) : json(list([]));
      return json(list(paged(a, b.offset, b.limit, Math.min(a.length, cap))));
    }
    if (p === '/rest/collections/list_user_collections')
      return json(list(page(projects.map(({threads: _, broken: __, ...c}) => ({instructions: '', description: '', ...c})), q, 50)));
    if (p === '/rest/collections/list_collection_threads') {
      const c = projects.find(c => c.slug === q.get('collection_slug'));
      if (c && c.broken) return json({error: 'server error'}, 500);
      return c ? json(list(page(c.threads.map(i => threads[i]), q, 50))) : json({error: 'no such project'}, 404);
    }
    let m = p.match(/^\/rest\/thread\/([^/]+)$/);
    if (m) {
      const slug = m[1];
      if (!threads.some(t => t.slug === slug)) return json({error: 'not found'}, 404);
      if (fail[slug] > 0) { fail[slug]--; return json({error: 'server error'}, 500); }
      if ((spec.html || []).includes(slug)) return {status: 200, body: '<!doctype html><title>Sign in</title>', type: 'text/html'};
      const from = q.get('cursor') ? +q.get('cursor').slice(1) : 0;
      const ks = Array.from({length: Math.min(pageSize, entries - from)}, (_, i) => from + i);
      const more = from + ks.length < entries;
      return json({entries: ks.map(k => entry(slug, k)), next_cursor: more ? `c${from + ks.length}` : null});
    }
    if (p === '/rest/memories/list') {
      const all = Array.from({length: spec.memories || 0}, (_, i) => ({display_key_pretty: `Key ${i}`, display_value: `value ${i}`}));
      return json(list(page(all, q, 50)));
    }
    if (p === '/rest/user/get_user_ai_profile') return json(spec.profile || {bio: 'made-up profile'});
    m = p.match(/^\/rest\/collections\/([^/]+)\/project_files\/(tree|content)$/);
    if (m && spec.files && spec.files[m[1]]) {
      const paths = spec.files[m[1]];
      if (m[2] === 'content') return paths.includes(q.get('path')) ? json({content: `text of ${q.get('path')}`}) : json({error: 'no file'}, 404);
      const dirs = {};
      for (const f of paths) (dirs[f.includes('/') ? f.split('/')[0] : ''] ||= []).push({path: f, type: 'file'});
      const children = (dirs[''] || []).concat(Object.keys(dirs).filter(d => d).map(d => ({path: d, type: 'directory', children: dirs[d]})));
      return json({path: '', type: 'directory', children});
    }
    return json({error: 'not found'}, 404);
  };
}

module.exports = {makeFake};
