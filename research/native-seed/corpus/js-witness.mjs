// Observes the production actor host while its ORIGINAL complete corpus runs.
// No mailbox, process, timer, recipient or failure policy is implemented here.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const bundle = pathToFileURL(resolve(process.argv[2]));
const budgetName = process.argv[3] || 'default';
assert.ok(['default', '17', '41'].includes(budgetName), 'unsupported corpus budget');
const H = await import(new URL('../host.mjs', bundle));
const K = H.kw;
const get = (value, key) => H.mapGet(value, K(key));
const keys = value => H.listToArray(H.mapKeys(value));
const size = value => keys(value).length;
const witness = { budget: budgetName, samples: 0, deaths: 0,
  max_procs: 0, max_monitors: 0, max_tables: 0, max_links: 0 };
let previous = new Set();
let runtime;
const typed = (value, tag) => H.isVec(value) && H.vecSize(value) === 3 &&
  H.eq(H.vecEl(value, 0), K(tag)) && H.isInt(H.vecEl(value, 1)) && H.isInt(H.vecEl(value, 2));

function sample(rt) {
  runtime = rt;
  if ((rt.criticalDepth || 0) !== 0) return;
  const state = rt.state;
  const procs = get(state, 'procs');
  if (procs === null) return;
  const monitors = get(state, 'monitors');
  const tables = get(state, 'tables');
  const tableNames = get(state, 'table-names');
  const pids = keys(procs);
  const live = pid => H.mapHas(procs, pid);
  const current = new Set(pids.map(H.hashKey));
  for (const key of previous) if (!current.has(key)) witness.deaths++;
  previous = current;
  witness.samples++;
  witness.max_procs = Math.max(witness.max_procs, pids.length);
  witness.max_monitors = Math.max(witness.max_monitors, size(monitors));
  witness.max_tables = Math.max(witness.max_tables, size(tables));
  let links = 0;
  for (const pid of pids) {
    assert.ok(typed(pid, 'pid'), 'untyped actor id');
    const process = H.mapGet(procs, pid);
    for (const other of keys(get(process, 'links'))) {
      links++;
      assert.ok(live(other), 'link to dead actor');
      assert.ok(H.mapHas(get(H.mapGet(procs, other), 'links'), pid), 'one-sided link');
    }
    for (const child of keys(get(process, 'owned'))) {
      assert.ok(live(child), 'dead owned child');
      assert.ok(H.eq(get(H.mapGet(procs, child), 'owner'), pid), 'ownership backlink');
    }
  }
  witness.max_links = Math.max(witness.max_links, links);
  for (const ref of keys(monitors)) {
    assert.ok(typed(ref, 'ref'), 'untyped monitor ref');
    const entry = H.mapGet(monitors, ref);
    assert.ok(live(get(entry, 'from')), 'monitor from dead actor');
    assert.ok(live(get(entry, 'to')), 'monitor to dead actor');
  }
  for (const pid of H.vecItems(get(state, 'runnable'))) assert.ok(live(pid), 'dead runnable actor');
  const sink = get(state, 'input-sink');
  assert.ok(sink === null || live(sink), 'dead input sink');
  for (const name of keys(get(state, 'names'))) assert.ok(live(H.mapGet(get(state, 'names'), name)), 'dead registered actor');
  for (const tid of keys(tables)) {
    assert.ok(typed(tid, 'table'), 'untyped table id');
    assert.ok(live(get(H.mapGet(tables, tid), 'owner')), 'table owned by dead actor');
  }
  for (const name of keys(tableNames)) {
    const tid = H.mapGet(tableNames, name);
    assert.ok(H.mapHas(tables, tid), 'table name points to absent table');
    assert.ok(H.eq(get(H.mapGet(tables, tid), 'name'), name), 'table name backlink');
  }
}

const original = H.RT_HOST['run-turn'];
H.RT_HOST['run-turn'] = (rt, frames, budget) => {
  sample(rt);
  const answer = original(rt, frames, budgetName === 'default' ? budget : Number(budgetName));
  sample(rt);
  return answer;
};
await import(bundle);
assert.ok(runtime, 'corpus never entered an actor turn');
sample(runtime);
const state = runtime.state;
witness.cleanup = {
  procs: size(get(state, 'procs')), monitors: size(get(state, 'monitors')),
  tables: size(get(state, 'tables')), names: size(get(state, 'names')),
  table_names: size(get(state, 'table-names')), runnable: H.vecItems(get(state, 'runnable')).length,
  input_sink: get(state, 'input-sink'), critical: runtime.criticalDepth || 0, errors: runtime.errors || 0,
};
for (const [name, value] of Object.entries(witness.cleanup)) {
  assert.equal(value, name === 'input_sink' ? null : 0, `final ${name} leak`);
}
for (const key of ['samples', 'deaths', 'max_procs', 'max_monitors', 'max_tables', 'max_links']) {
  assert.ok(witness[key] > 0, `missing lifecycle observation: ${key}`);
}
console.log('JS_CORPUS_WITNESS ' + JSON.stringify(witness));
