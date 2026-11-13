// Proposed finite exact-value equality profile; apply with the BEAM change.
import {test} from "node:test";
import assert from "node:assert/strict";
import * as R from "../../priv/lib/js/rt.mjs";

const values = [0, R.flt(-0), R.dec(0n, 0), R.dec(0n, 2), 1, R.flt(1),
 R.dec(1n, 0), R.dec(100n, 2), R.flt(1.5), R.dec(15n, 1), R.dec(150n, 2),
 R.flt(0.1), R.dec(1n, 1), R.flt(0.5), R.dec(50n, 2),
 9007199254740992n, R.flt(9007199254740992), 9007199254740993n, -9007199254740993n];

test("finite numeric equality is an equivalence relation and agrees with compare", () => {
 for (const a of values) assert.ok(R.eqv(a, a));
 for (const a of values) for (const b of values) {
  assert.equal(R.eqv(a, b), R.eqv(b, a));
  assert.equal(R.eqv(a, b), R.compare(a, b) === 0);
  assert.ok(R.compare(a, b) === -R.compare(b, a));
  for (const c of values) if (R.eqv(a, b) && R.eqv(b, c)) assert.ok(R.eqv(a, c));
 }
});

test("Decimal/Float comparison keeps actual IEEE values at rounding boundaries", () => {
 assert.ok(R.eqv(R.dec(15n, 1), R.dec(150n, 2)));
 assert.ok(R.eqv(R.dec(150n, 2), R.flt(1.5)));
 assert.ok(!R.eqv(R.dec(1n, 1), R.flt(0.1)));
 assert.equal(R.compare(R.dec(1n, 1), R.flt(0.1)), -1);
 assert.equal(R.compare(R.dec(9007199254740993n, 0), R.flt(9007199254740992)), 1);
 assert.equal(R.compare(R.dec(-9007199254740993n, 0), R.flt(-9007199254740992)), -1);
 // Independent exact constants, not an expected value computed by the helper.
 const exactTenthFloat = R.dec(3602879701896397n * 5n ** 55n, 55);
 assert.ok(R.eqv(exactTenthFloat, R.flt(0.1)));
 const minSubnormal = R.dec(5n ** 1074n, 1074);
 assert.ok(R.eqv(minSubnormal, R.flt(Number.MIN_VALUE)));
 assert.equal(R.compare(R.dec(1n, 324), R.flt(Number.MIN_VALUE)), -1);
 assert.ok(R.eqv(R.dec(-minSubnormal.u, minSubnormal.s), R.flt(-Number.MIN_VALUE)));
 const maxFinite = R.dec(((1n << 53n) - 1n) << 971n, 0);
 assert.ok(R.eqv(maxFinite, R.flt(Number.MAX_VALUE)));
 assert.equal(R.compare(R.dec(maxFinite.u + 1n, 0), R.flt(Number.MAX_VALUE)), 1);
});

test("nested values use exact numeric equality while raw keys retain their own rule", () => {
 for (const a of values) for (const b of values) {
  assert.equal(R.eqv(a, b), R.eqv(R.vec(a), R.list(b)));
  assert.equal(R.eqv(a, b), R.eqv(R.hashMap("value", a), R.hashMap("value", b)));
  assert.equal(R.eqv(a, b), R.eqv(R.tup([a]), R.tup([b])));
 }
 const a = R.dec(15n, 1), b = R.dec(150n, 2);
 assert.ok(R.eqv(a, b));
 assert.ok(!R.keyEq(a, b));
 assert.equal(R.hashMap(a, "tenths", b, "hundredths").cnt, 2);
 assert.ok(!R.keyEq(1, R.flt(1)));
 assert.equal(R.hashMap(1, "integer").get(R.flt(1), null), null);
 assert.equal(R.dec(150n, 2).plain(), "1.50");
 assert.throws(() => R.add(a, R.flt(1)), /float cannot enter decimal arithmetic/);
});
