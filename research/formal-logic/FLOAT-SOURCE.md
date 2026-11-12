# Binary64 Source integration — checkpoint 41

The SDK40 baseline in `evidence/float-source/baseline.json` records an actual
compiled counterexample at `1.0` to cancellation by `0.1`, while the legacy
process verifier reported a complete proof over Real. That is a model mismatch,
not a Z3 arithmetic error.

This batch promotes `formal.floating` and `formal.ieee-arithmetic` into the SDK,
adds `formal.beam-float`, and extends the reviewed compiler-ANF Source profile
with finite binary64 inputs and round-to-nearest-even arithmetic. The independent
integer/rational evaluator supports all five theory rounding modes within its
explicit format and resource limits. It does not call a native solver or use
host floating arithmetic. Its implementation correspondence is tested, not a
machine-checked IEEE implementation theorem.

The runtime profile separates finite input admission from successful operation
results. Overflow, zero division, or another nonfinite result fails definedness;
it is never erased by adding the result's finiteness to the input premise.
Gradual underflow and signed zero remain successful values. BL numeric equality
agrees on signed zeros; strict Erlang equality and returned-value observation
preserve their distinction. Unary negation flips the sign bit: it is not `0-x`.

Mixed arithmetic accepts exactly representable Int literals only. Symbolic
Int/Float casts, inexact literal conversions, mixed-type branches, nullable
Float profiles, and strict equality of Float-containing composites remain
explicitly unsupported. Homogeneous Float `one-of` generators retain both
signed zeros by exact bits. Generator membership distinguishes Int from Float,
matching values a generator actually produces. `real-of` remains its historical
sampling / explicit ideal-model API, without a typed Float domain.

Known Float/declared Real legacy process checks now refuse Source proof claims
before a solver call, with a visible diagnostic. The explicit option
`:semantics :ideal-real-model` retains a mathematical result in `:model-result`;
its top-level `:holds` is nil and `:checked` is false. Legacy repair/discovery
also refuse these inputs. This admission guard is not a complete Source type
analysis. Other legacy process questions remain labelled mathematical models
with Source correspondence unestablished and no compiler proof authority.
Length, content and phase abstractions remain separately scoped models.

Runtime native-offload candidates call the representation `Float64`, separately
from the SMT theory `Real`; argument representation and bounded work remain
obligations of an actual lowering.

Portable FP(e,2) terms are valid and independently evaluable. The pinned Z3
4.16 native API refuses that significand size. Managed Z3 preflight now reports
unsupported before native import, preserving the owner's registry, assertions,
generation and revision so subsequent supported queries can still run. No
OxiZ capability is inferred from that Z3 restriction.

Checkpoint 41 qualifies one immutable SDK with 19,415 assertion executions:
1,310 focused, 8,191 arithmetic, 167 migration, 299 preparation, 1,307 preceding
focused and 8,141 regression assertions. The 141-file compiler artifact floor,
frozen-source preflight and negative controls pass. Four Source subjects run
on both engines from an unrelated directory without research imports; a fresh
process reopens eight complete records, reconstructs their questions and
observes the original functions with zero managed query calls in the named
record-rechecking window. Recompiling Source may execute phase code.

The 26 selected binary64 patterns are checked against actual BL arithmetic.
A separate FP(2,2) finite grid covers all pairs for add/sub/mul and all pairs
with a nonzero divisor for division, across five rounding modes. Another 160
pinned Z3 FP(2,3) reference questions and separate special-value checks cover
rounding and nonfinite results. This is not exhaustive binary64 testing.

All 187 preceding native statuses/verdicts remain unchanged. A separately
profiled bounded Merkle audit compares every public field of their complete
questions on SDK40 and SDK41. One closure question exceeds the unchanged
standard identity walk budget (110,551 versus 100,000); no runtime budget was
relaxed and this comparison hash grants no packet/proof identity.

Z3 reproduces the cancellation, negative-zero identity and zero-division
counterexamples in actual Source; the rounded-sum positive answer remains an
unchecked solver claim. OxiZ returns unknown for cancellation and the positive
sum, and candidate for the other two, with original replay incomplete.

Observation replay keeps semantic NaN classification/equality available
without manufacturing IEEE payloads. The policy is shared by native fallback,
handler reconstruction, fresh answer checking, and nested FP sequences/arrays.
Internal mathematical evaluation still retains a semantic NaN representative.

Original bytes, rejected candidates and complete receipts remain in
`evidence/float-source`. The code qualification is `qualification.json`; the
full-content audit is `complete-question-identity-qualification.json`.
`NEXT-POINTS.md` records the next interface design and remaining Source cutover.
