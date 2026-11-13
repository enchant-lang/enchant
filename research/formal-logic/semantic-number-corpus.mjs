// Direct runtime observations; actual compiled BL/JS qualification is separate.
import {readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';

const [runtimePath, fixturePath, outputPath, mode, compiledBuild] = process.argv.slice(2);
const R = await import(pathToFileURL(resolve(runtimePath)).href);
let relations = (a, b) => [R.eqv(a, b), R.compare(a, b), R.eqv(R.vec(a), R.list(b)),
                          R.eqv(R.hashMap('value', a), R.hashMap('value', b)), R.hashSet(a, b).cnt];
if (compiledBuild) {
 // Emitted namespaces and fixture values must use the same runtime classes.
 assert.equal(resolve(runtimePath), resolve(compiledBuild, 'rt.mjs'));
 const compiled = await import(pathToFileURL(resolve(compiledBuild, 'ns/semantics.numeric.mjs')).href);
 assert.equal(typeof compiled.d_relations, 'function');
 relations = (a, b) => Array.from(compiled.d_relations(a, b));
}
const fixture = JSON.parse(await readFile(fixturePath, 'utf8'));
assert.equal(fixture.schema, 'bl.proposed-finite-exact-numeric-cases.v1');
function value(row) {
 switch (row.kind) {
  case 'integer': {
   const n = BigInt(row.digits);
   return n >= BigInt(Number.MIN_SAFE_INTEGER) && n <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(n) : n;
  }
  case 'decimal': return R.dec(BigInt(row.coefficient), row.scale);
  case 'float': {
   const view = new DataView(new ArrayBuffer(8));
   view.setBigUint64(0, BigInt('0x' + row.bits), false);
   return R.flt(view.getFloat64(0, false));
  }
  default: throw Error('Unknown finite-number fixture kind');
 }
}
const values = new Map(fixture.values.map(row => [row.id, value(row)]));
const rows = fixture.pairs.map(pair => {
 const a = values.get(pair.left), b = values.get(pair.right);
 const actual = relations(a, b);
 assert.equal(actual.length, 5);
 const [equal, compare, sequenceEqual, mapEqual, keyCardinality] = actual;
 return {left: pair.left, right: pair.right, equal, compare,
         'sequence-equal': sequenceEqual, 'map-value-equal': mapEqual,
         'key-cardinality': keyCardinality,
         'matches-exact-profile': equal === pair.equal && sequenceEqual === pair.equal && mapEqual === pair.equal && compare === pair.compare};
});
assert.equal(values.size, 30);
assert.equal(rows.length, 900);
const differences = rows.filter(row => !row['matches-exact-profile']);
if (mode === 'require-profile') assert.equal(differences.length, 0);
const representationSamples = [];
if (compiledBuild && mode === 'require-profile') {
 const compiled = await import(pathToFileURL(resolve(compiledBuild, 'ns/semantics.numeric.mjs')).href);
 assert.equal(typeof compiled.d_representations, 'function');
 for (const [name, a, b, expected] of [
  ['same-decimal-representation', R.dec(150n, 2), R.dec(150n, 2), [true, true]],
  ['different-decimal-scale', R.dec(15n, 1), R.dec(150n, 2), [true, false]],
  ['decimal-float', R.dec(15n, 1), R.flt(1.5), [true, false]],
  ['decimal-integer', R.dec(1n, 0), 1, [true, false]],
  ['decimal-inexact-float', R.dec(1n, 1), R.flt(0.1), [false, false]]]) {
  const actual = Array.from(compiled.d_representations(a, b));
  assert.deepEqual(actual, expected, name);
  representationSamples.push({name, actual});
 }
}
const target = compiledBuild ? 'js-compiled-language' : 'js-direct-runtime';
await writeFile(outputPath, JSON.stringify({schema: 'bl.finite-number-runtime-observation.v1', target,
 'runtime-path': resolve(runtimePath), process: process.pid, cwd: process.cwd(), profile: fixture.profile,
 values: values.size, pairs: rows.length, rows, differences, 'managed-query-calls': 0,
 'representation-samples': representationSamples,
 scope: compiledBuild ? 'Actual compiled BL function observations; raw key cardinality is recorded separately.' :
                       'Direct runtime observations; raw key cardinality is recorded separately. This is not the compiled BL path.',
 'compiler-proof-authority': false}, null, 2) + '\n');
console.log(JSON.stringify({target, values: values.size, pairs: rows.length, differences: differences.length}));
