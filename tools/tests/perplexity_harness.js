// Runs tools/perplexity-*.js against perplexity_fake.js, for test_perplexity.py. Each script is loaded the
// way `playwright-cli run-code --filename` loads it: its text wrapped in ( ) and evaluated, so a trailing
// `;` or a last-line comment fails here too. The page is a vm context standing in for the browser tab:
// window is its global object, fetch answers from the fake, and page.evaluate(fn) calls fn in it.
//   node perplexity_harness.js <case.json>
// case.json: {spec: <fake spec>, steps: [{run: <script path>} | {set: {<window variable>: <value>}}],
// keep: [<window variable>, ...], delay: <ms each call takes>, url: <the page's address>, settle: <wait for a
// started job to end>}. Prints {results: [<each run's return value>], window: {<kept variables>}}.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const {makeFake} = require('./perplexity_fake.js');

async function main() {
  const c = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const handle = makeFake(c.spec);
  const calls = [];
  const fetch = async (url, opts = {}) => {
    const method = opts.method || 'GET';
    calls.push(`${method} ${url}`);
    if (c.delay) await new Promise(r => setTimeout(r, c.delay));
    const r = handle(method, url, opts.body);
    return {ok: r.status >= 200 && r.status < 300, status: r.status,
      text: async () => r.body, json: async () => JSON.parse(r.body)};
  };
  const ctx = vm.createContext({fetch, setTimeout, URL, console, location: new URL(c.url || 'https://www.perplexity.ai/')});
  vm.runInContext('var window = globalThis;', ctx);
  const page = {evaluate: (fn, arg) => fn(arg)};
  const results = [];
  for (const step of c.steps) {
    if (step.set) for (const [k, v] of Object.entries(step.set)) ctx[k] = vm.runInContext(`(${JSON.stringify(v)})`, ctx);
    if (step.run) {
      const src = fs.readFileSync(path.resolve(step.run), 'utf8');
      const fn = vm.runInContext(`(${src})`, ctx, {filename: step.run});
      results.push(await fn(page));
    }
  }
  if (c.settle) await vm.runInContext('window.__job || null', ctx);  // let a started job finish
  const win = {};
  for (const k of c.keep || []) win[k] = ctx[k];
  process.stdout.write(JSON.stringify({results, window: win, calls}));
}

main().catch(err => { console.error(err && err.stack || err); process.exit(1); });
