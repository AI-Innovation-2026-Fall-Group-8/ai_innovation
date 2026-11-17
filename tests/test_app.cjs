// Dependency-free feed, filtering, security and failure-state regression tests.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const feed = JSON.parse(fs.readFileSync(path.join(root, 'data/output/unified_events.json'), 'utf8'));

async function createApp(fetcher, protocol = 'http:') {
  const nodes = {};
  const get = id => nodes[id] ||= {textContent: '', innerHTML: '', hidden: false, value: id === 'eventPeriod' ? 'upcoming' : '', checked: false,
    handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; }, querySelectorAll() { return []; }};
  class FixedDate extends Date { static now() { return Date.parse('2026-11-16T20:00:00Z'); } }
  const context = vm.createContext({document: {getElementById: get}, location: {protocol}, fetch: fetcher,
    Date: FixedDate, URL, Intl, AbortController, setTimeout, clearTimeout, console});
  vm.runInContext(code, context);
  await new Promise(resolve => setImmediate(resolve));
  return {nodes, run: code => vm.runInContext(code, context)};
}
const response = data => async () => ({ok: true, json: async () => data});

async function run() {
  const app = await createApp(response(feed));
  assert.equal(app.run('UCI_EVENTS.length'), feed.length);
  assert.equal(app.run('feedState'), 'ready');
  assert.ok(app.nodes.cardGrid.innerHTML.includes('View on ZotSpot'));
  assert.ok(!app.nodes.cardGrid.innerHTML.includes('Demo listing'));
  const ongoing = await createApp(response([{id:'long',title:'Ongoing service',source:'zotspot', start_datetime:'2021-06-28T00:00:00-07:00', end_datetime:'2028-01-01T10:00:00-08:00'}]));
  assert.equal(ongoing.run('getFilteredListings().length'), 1, 'ongoing multi-year event stays visible');
  app.run("eventPeriod.value = 'all'; render();");
  assert.equal(app.run('getFilteredListings().length'), feed.length);
  app.run("eventPeriod.value = 'past'; render();");
  assert.ok(app.run('getFilteredListings().every(isPastEvent)'));
  app.run("eventPeriod.value = 'all'; searchText = 'zzzz-no-such-event'; render();");
  assert.equal(app.nodes.emptyState.hidden, false);
  app.nodes.clearFiltersBtn.handlers.click();
  assert.equal(app.run('getFilteredListings().length'), feed.length);
  app.run("searchText = UCI_EVENTS[0].organizer.toLowerCase(); render();");
  assert.ok(app.run('getFilteredListings().some(item => item.id === UCI_EVENTS[0].id)'));
  app.run("searchText = ''; showDemos.checked = true; activeCategories.clear(); render();");
  assert.equal(app.run('LISTINGS.length'), feed.length + 18);
  assert.ok(app.nodes.cardGrid.innerHTML.includes('Demo listing'));
  assert.equal(app.run("safeContact('javascript:alert(1)')"), '');
  assert.throws(() => app.run("normalizeFeed([{id:'1',title:'bad', start_datetime:'2026-11-17T18:00:00'}])"), /timezone offsets/);
  assert.throws(() => app.run('normalizeFeed({})'), /JSON array/);
  assert.equal(app.run('normalizeFeed([]).length'), 0);

  const hostile = await createApp(response([{id:'hostile',title:'<img src=x onerror=alert(1)>',source:'club-site', source_url:'javascript:alert(1)', start_datetime:'2026-12-01T18:00:00-08:00'}]));
  assert.ok(hostile.nodes.cardGrid.innerHTML.includes('&lt;img'));
  assert.ok(!hostile.nodes.cardGrid.innerHTML.includes('href="javascript:'));
  assert.ok(hostile.nodes.cardGrid.innerHTML.includes('Official link not provided'));

  const undated = await createApp(response([{id:'unknown',title:'TBA',source:'club-site'}]));
  assert.equal(undated.nodes.emptyState.hidden, false);
  undated.run("eventPeriod.value = 'undated'; render();");
  assert.ok(undated.nodes.cardGrid.innerHTML.includes('Date to be confirmed'));

  const empty = await createApp(response([]));
  assert.equal(empty.nodes.emptyState.hidden, false);
  const broken = await createApp(async () => ({ok: false, status: 404}));
  assert.equal(broken.nodes.feedError.hidden, false);
  assert.equal(broken.nodes.emptyState.hidden, true);
  assert.match(broken.nodes.feedErrorMessage.textContent, /404/);
  broken.run("fetch = async () => ({ok:true,json:async()=>[]});");
  await broken.nodes.retryFeed.handlers.click();
  assert.equal(broken.run('feedState'), 'ready');
  assert.equal(broken.nodes.feedError.hidden, true);
  const malformed = await createApp(async () => ({ok:true, json:async () => {throw new SyntaxError('Invalid JSON');}}));
  assert.match(malformed.nodes.feedErrorMessage.textContent, /Invalid JSON/);
  const local = await createApp(async () => {throw new Error('Failed to fetch');}, 'file:');
  assert.match(local.nodes.feedErrorMessage.textContent, /web server/);
  return 'Passed: real feed loading, ongoing/past/undated filters, search, empty states, optional demos, safe rendering, bad dates, malformed JSON, HTTP errors, retry and file startup guidance.';
}
module.exports = run;
if (require.main === module) run().then(console.log).catch(error => {console.error(error); process.exitCode = 1;});
