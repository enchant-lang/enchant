# Exact values before stronger logical promises

The integration source now repairs generic numeric equality and the legacy
modulus translation. This batch is **not qualified on a new SDK yet**. The
selected SDK and live dossier keep their already qualified behavior while the
new compiler floor, SDK and checks are produced.

The compiler-only P/B/C product has now passed its complete 141-file check;
84 files of the checked-in floor changed when that verified product was
installed with its manifest last. The new SDK is still pending. The compiler
receipt binds its actual inputs; subsequent changes confined to JavaScript
runtime source do not rewrite that historical compiler receipt.

The original proposed diffs remain in `proposals/` as review history. Applied
source defines finite generic numeric equality by exact value and introduces
`decimal/same-representation?` for coefficient and scale. Decimal arithmetic
still refuses Float operands. JavaScript compares actual binary64 values using
exact BigInt cross-products. Ordinary map/set keys retain their existing raw
relation; changing that language contract is a separate implementation.

The candidate also implements Decimal's named JavaScript host API, so ordinary
BL importing `decimal` can compile to JS. Its construction, scale, arithmetic,
eight rounding modes and conversions use the same JS value representation as
core operators. Exact division now computes termination from denominator
factors instead of guessing a 64-place ceiling, and keeps the BEAM preferred
operand-scale difference. The generated compiled-BL program executes all
1,051 existing JVM-captured cases, with expectations in a separate fixture.
Those cases compare values and raisedness; exception type/message coverage is
separate. No new JVM reference answers are authored.

Named Float approximation is separate from exact comparison and arithmetic.
A real 17-case observation on the preceding qualified BEAM SDK records its
shortest Float spelling and resulting Decimal coefficient/scale. The JS
implementation follows the pinned OTP 17 formatting policy, including its
scientific-form boundary at `2^53`. Fresh candidate observations also compare
every Float in the shared fixture through BEAM, direct JS and compiled BL.
These are pending qualification gates, not claims of a whole-target theorem.

`system.smt` now reconstructs BL divisor-sign modulus instead of aliasing SMT's
Euclidean modulus. The repaired legacy expression is qualified only when its
divisor is nonzero. Runtime zero division still raises; this expression API
does not encode or prove preservation of that raised outcome.

The completed baseline uses the same 30 values and 900 ordered pairs through
three real routes on the selected SDK:

| Route | Pairs differing from the proposed exact-value profile |
| --- | ---: |
| BEAM language | 6 |
| Direct JavaScript runtime | 14 |
| Actual BL function compiled to JavaScript | 6 |

See `evidence/numeric-semantics/baseline/observation-summary.json` for the exact
SDK, committed inputs, separate processes and report hashes. The generated JS
is retained in a hashed archive. Private runtime and consumer directories were
removed. These are baseline discrepancies, not failed new-profile gates.

The candidate gate requires zero discrepant pairs on every route. The compiled
BL test also calls the new Decimal representation API, including equal values
with different scale and Decimal/Float comparisons. Focused language tests
check equivalence laws, nesting, metadata and semantic keys/hashes. Datom checks
cover the existing codec, scans/hash joins, same-value identity claims, CAS,
retraction, no-op representation retention and durable payload reopen. Index
version 2 and the existing immutable identity format remain unchanged in source;
their compatibility is a gate to execute, not a conclusion inferred from the diff.

The first packaged SDK passed the complete compiler-floor check, the
595-namespace source preflight and its refusal controls. BEAM and direct JS
both matched all 900 exact-number pairs. Compiled BL then correctly refused
one missing host registration: `Elixir.BeamLisp.Decimal/rescale/2`.
`candidate-1/` retains the real failure and its unqualified SDK pin, plus a
self-contained source-only recovery bundle and Git archive ref. No JVM oracle
execution or project adoption is claimed for that candidate. The registration
is now repaired, with a test of both rescale arities and their rounding behavior;
the replacement must pass all packaged gates on its own exact SDK.

The legacy bare-VM regeneration attempts are retained under the three
`before-*` recovery directories plus `before-local-image/`. They stopped on
initialization, protected SDK routes or kernel attestation; no candidate floor
was installed. The compiler-only staging copy error is separately retained.
Private recovery images were retired. Their guards were not relaxed.

Run `build-numeric-compiler.py produce` under a durable owner. It captures
immutable source and uses the existing Nix compiler-only P/B/C producer, with
its unchanged generation deadlines and fresh-boot gates. This produces no SDK.
After actual qualification, `build-numeric-compiler.py install` verifies the
complete product and current source again, then installs its floor with the
manifest last. Review and commit that real floor before running
`build-numeric-sdk.py`.
Reuse that one immutable artifact for `run-numeric-semantics.py candidate PIN`
and focused checks. Qualify the full produced compiler floor and source
preflight, then compare the affected formal/backend paths at their unchanged
deadlines. Only complete passing gates may select the candidate and update
the live dossier's executed observations. No compiler theorem or whole-language
totality follows from finite test vectors.
