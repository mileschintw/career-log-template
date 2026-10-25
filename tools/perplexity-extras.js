// Reads a Perplexity account's custom instructions, memories and project files, each only when the user
// authorised it, for skills/career-log/modes/import-web.md › Perplexity. Run it in a session open on
// https://www.perplexity.ai/:
//   playwright-cli -s=<name> run-code --filename=<root>/tools/perplexity-extras.js
// Input: window.__want = {instructions: true, memories: true, files: ['<project uuid>', ...]}, holding only
// what the user authorised (the uuids are in window.__projects, from perplexity-list.js). Run without it,
// it says how to set it. Output: window.__extras = {instructions, memories: [...], files: [{project, path,
// content}]}; it returns the counts and `next` lines, the agent's steps in order.
//
// The calls:
//   GET /rest/user/get_user_ai_profile: the custom instructions
//   GET /rest/memories/list?limit=50&offset=<n>: the memories (display_key_pretty, display_value), paged
//   GET /rest/collections/<uuid>/project_files/tree, then .../project_files/content?path=<path> for each file
async page => page.evaluate(async () => {
  const cli = 'playwright-cli -s=<name>', run = `${cli} run-code --filename=<root>/tools/perplexity-extras.js`;
  if (!/^https?:$/.test(location.protocol))
    return {state: 'no page', next: [`Open https://www.perplexity.ai/ in this session first: ${cli} goto "https://www.perplexity.ai/". Then run this script again: ${run}.`]};
  const want = window.__want;
  if (!want || typeof want !== 'object')
    return {state: 'no input', projects: (window.__projects || []).map(p => ({title: p.title, uuid: p.uuid})),
      next: [`Set what the user authorised, leaving out the rest: ${cli} eval "() => { window.__want = {instructions: true, memories: true, files: ['<project uuid>']} }". The project uuids are under projects (empty until perplexity-list.js has run). Then run this script again: ${run}.`]};
  const items = j => (Array.isArray(j) ? j : Object.values(j || {}).find(Array.isArray) || []);
  async function get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status} from ${url.split('?')[0]}`);
    return r;
  }
  // The file paths of a project tree: nodes with a path and no children, folders left out
  function paths(node) {
    if (Array.isArray(node)) return node.flatMap(paths);
    if (!node || typeof node !== 'object') return [];
    if (Array.isArray(node.children) && node.children.length) return paths(node.children);
    if (typeof node.path === 'string' && node.path && !/dir|folder/i.test(node.type || '')) return [node.path];
    return Object.values(node).filter(v => v && typeof v === 'object').flatMap(paths);
  }

  const extras = {instructions: null, memories: [], files: []}, errors = [];
  if (want.instructions) {
    try { extras.instructions = await (await get('/rest/user/get_user_ai_profile')).json(); }
    catch (err) { errors.push(`instructions: ${err.message}`); }
  }
  if (want.memories) {
    try {
      for (let offset = 0; offset < 5000; offset += 50) {
        const got = items(await (await get(`/rest/memories/list?limit=50&offset=${offset}`)).json());
        extras.memories.push(...got);
        if (got.length < 50) break;
      }
    } catch (err) { errors.push(`memories: ${err.message}`); }
  }
  for (const uuid of Array.isArray(want.files) ? want.files : []) {
    const base = `/rest/collections/${encodeURIComponent(uuid)}/project_files`;
    try {
      for (const path of paths(await (await get(`${base}/tree`)).json())) {
        try {
          const text = await (await get(`${base}/content?path=${encodeURIComponent(path)}`)).text();
          let content = text;
          try { const j = JSON.parse(text); content = typeof j.content === 'string' ? j.content : j; } catch (_) { /* plain text */ }
          extras.files.push({project: uuid, path, content});
        } catch (err) { errors.push(`file ${path} of ${uuid}: ${err.message}`); }
      }
    } catch (err) { errors.push(`files of ${uuid}: ${err.message}`); }
  }

  window.__extras = extras;
  const out = {state: 'done', instructions: extras.instructions !== null, memories: extras.memories.length,
    files: extras.files.length, errors, next: []};
  if (errors.some(e => /HTTP 40[13]/.test(e))) {
    out.next.push(`A call answered HTTP 401 or 403: have the user sign in again (browser.md › Sign-in item 3), reopen the session (item 2), set window.__want again, then run this script again: ${run}.`);
    return out;
  }
  out.next.push(`Write what it read: ${cli} eval "() => window.__extras" --filename=<scratch>/perplexity-extras.json.`);
  if (errors.length) out.next.push('List the reads that failed (errors) in the import log.');
  return out;
})
