import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as R from '../../priv/lib/js/rt.mjs';
import {LEAVES} from '../../priv/lib/js/leaves.mjs';

const mode = R.kw;
const decimalError = type => error => error instanceof R.BLError && error.data?.get(R.kw('type'), null) === R.kw(type);

test('both named rescale arities link with their default and explicit rounding behavior', () => {
 const exact = LEAVES['Elixir.BeamLisp.Decimal/rescale/2'];
 const rounded = LEAVES['Elixir.BeamLisp.Decimal/rescale/3'];
 assert.equal(exact(R.dec(150n, 2), 1).plain(), '1.5');
 assert.throws(() => exact(R.dec(155n, 2), 1), decimalError('decimal/rounding-necessary'));
 assert.equal(rounded(R.dec(155n, 2), 1, mode('half-even')).plain(), '1.6');
});

test('exact division has no guessed digit ceiling and preserves the BEAM preferred scale', () => {
 const result = R.div(R.dec(1n, 0), R.dec(1n << 80n, 0));
 assert.equal(result.u, 5n ** 80n);
 assert.equal(result.s, 80);
 assert.equal(R.div(R.dec(600n, 2), R.dec(30n, 1)).plain(), '2.0');
 assert.equal(R.div(R.dec(120n, 2), R.dec(3n, 0)).plain(), '0.40');
 assert.equal(R.div(R.dec(0n, 0), R.dec(30n, 1)).plain(), '0');
 assert.throws(() => R.div(R.dec(1n, 0), R.dec(3n, 0)), decimalError('decimal/non-terminating'));
 assert.throws(() => R.div(R.dec(1n, 0), R.dec(0n, 0)), decimalError('decimal/divide-by-zero'));
});

test('rounding covers negative ties, divisor signs and explicit refusal', () => {
 for (const [name, expected] of [['half-even', '-2'], ['half-up', '-3'], ['half-down', '-2'],
                                ['ceiling', '-2'], ['floor', '-3'], ['down', '-2'], ['up', '-3']]) {
  assert.equal(R.decimalRescale(R.dec(-25n, 1), 0, mode(name)).plain(), expected);
  assert.equal(R.decimalDivide(R.dec(5n, 0), R.dec(-2n, 0), 0, mode(name)).plain(), expected);
 }
 assert.throws(() => R.decimalRescale(R.dec(25n, 1), 0), decimalError('decimal/rounding-necessary'));
 assert.throws(() => R.decimalDivide(R.dec(1n, 0), R.dec(0n, 0), 0, mode('unknown-mode')),
               error => error.blType === R.kw('Elixir.FunctionClauseError'));
});

test('construction and conversions keep representation and typed Float refusal explicit', () => {
 assert.equal(R.decimalOf('1.50').plain(), '1.50');
 assert.equal(R.decimalScaled(150, 2).plain(), '1.50');
 assert.equal(R.decimalPrecision(R.dec(-150n, 2)), 3);
 assert.equal(R.decimalStrip(R.dec(150n, 2)).plain(), '1.5');
 assert.equal(R.decimalMove(R.dec(150n, 2), 3, true).plain(), '0.00150');
 assert.equal(R.decimalMove(R.dec(150n, 2), 3, false).plain(), '1500');
 assert.equal(R.decimalIntegerPart(R.dec(-159n, 2)), -1);
 assert.equal(R.decimalFloat(R.dec(150n, 2)).v, 1.5);
 assert.throws(() => R.decimalOf(R.flt(0.1)), decimalError('decimal/inexact-operand'));
 assert.throws(() => R.add(R.dec(1n, 0), R.flt(0.1)), decimalError('decimal/inexact-operand'));
 assert.throws(() => R.decimalOf('invalid'), decimalError('decimal/parse'));
 assert.throws(() => R.decimalOf(null), decimalError('decimal/coerce'));
});

test('shortest Float spelling and named approximation match captured BEAM observations', () => {
 const recorded = JSON.parse(readFileSync(new URL('../../research/formal-logic/evidence/numeric-semantics/float-format.json', import.meta.url)));
 assert.equal(recorded.rows.length, 17);
 for (const row of recorded.rows) {
  const value = R.flt(Number(row['float-text'])), converted = R.decimalFromFloat(value);
  assert.equal(R.shortestFloatText(value), row['float-text']);
  assert.equal(converted.plain(), row['decimal-text']);
  assert.equal(converted.u.toString(), row.coefficient);
  assert.equal(converted.s, row.scale);
 }
 assert.ok(!R.eqv(R.decimalFromFloat(R.flt(0.1)), R.flt(0.1)));
 for (const value of [NaN, Infinity, -Infinity]) {
  assert.throws(() => R.decimalFromFloat(R.flt(value)), error => error.blType === R.kw('Elixir.FunctionClauseError'));
 }
});
