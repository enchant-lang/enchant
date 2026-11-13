// Direct runtime observations; actual compiled BL/JS qualification is separate.
import {readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';

const [runtimePath, fixturePath, outputPath, mode] = process.argv.slice(2);
const R = await import(pathToFileURL(resolve(runtimePath)).href);
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
 const a = values.get(pair.left), b = values.get(pair.right), equal = R.eqv(a, b), compare = R.compare(a, b);
 const sequenceEqual = R.eqv(R.vec(a), R.list(b)), mapEqual = R.eqv(R.hashMap('value', a), R.hashMap('value', b));
 return {left: pair.left, right: pair.right, equal, compare,
         'sequence-equal': sequenceEqual, 'map-value-equal': mapEqual,
         'key-cardinality': R.hashSet(a, b).cnt,
         'matches-exact-profile': equal === pair.equal && sequenceEqual === pair.equal && mapEqual === pair.equal && compare === pair.compare};
});
assert.equal(values.size, 30);
assert.equal(rows.length, 900);
const differences = rows.filter(row => !row['matches-exact-profile']);
if (mode === 'require-profile') assert.equal(differences.length, 0);
await writeFile(outputPath, JSON.stringify({schema: 'bl.finite-number-runtime-observation.v1', target: 'js-direct-runtime',
 'runtime-path': resolve(runtimePath), process: process.pid, cwd: process.cwd(), profile: fixture.profile,
 values: values.size, pairs: rows.length, rows, differences, 'managed-query-calls': 0,
 scope: 'Direct runtime numeric and nested equality/ordering observations. Raw key cardinality is recorded separately; this is not the compiled BL path.',
 'compiler-proof-authority': false}, null, 2) + '\n');
console.log(JSON.stringify({target: 'js-direct-runtime', values: values.size, pairs: rows.length, differences: differences.length}));
