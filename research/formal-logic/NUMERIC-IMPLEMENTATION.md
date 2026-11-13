# Exact values before stronger logical promises

The integration source repairs generic numeric equality and the legacy
modulus translation. The second numeric SDK is now **core-qualified**. Its
12,151 BEAM assertions, 40 JS tests, three real numeric routes and all 187 paired
native questions pass, with native outcomes unchanged. The selected project
SDK and live dossier still keep the preceding qualified artifact while the
separate cross-version readers and mathematical model finish their adoption
gates. See `evidence/numeric-semantics/qualification.json`.

The compiler-only P/B/C product has now passed its complete 141-file check;
84 files of the checked-in floor changed when that verified product was
installed with its manifest last. Two numeric SDK candidates have been produced;
the second has passed the complete core qualification. The compiler
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
the replacement has now passed all packaged core gates on its own exact SDK.

The second SDK now matches all 900 exact-number pairs on BEAM, direct JS and
actual compiled BL. It also matches all 1,051 captured Decimal oracle cases,
five compiled representation API cases and eleven named Float approximations
per route. Its 40 JS unit tests, compiler floor, source preflight and refusal
controls pass. These completed gates do not select the project SDK. The native corpus also
completed at the unchanged 500/2000ms limits, with zero differences from the
preceding 187-question run.

The focused BEAM gate exposed a source-relative fixture omission and one stale
scale-equality expectation in the older host ABI tests. Both are corrected in
the check sources without rebuilding the runtime. Its combined nested-modulus
query returned `unknown/timeout`, retained under
`focused-before-law-decomposition/`. Three separate universal native queries
now establish magnitude, divisor sign and explicit quotient reconstruction at
the unchanged deadline. Their UNSAT results remain solver claims, not checked
BL certificates. Zero division stays outside that law domain and is tested as
a runtime failure.

That run also exposed a test CLI limitation: assertion failures may print a
failed summary while the process exits zero. The numeric runner now requires
both process success and the complete green test summary, retaining both
statuses separately. Repairing the general CLI exit behavior belongs to a
subsequent runtime batch; it is not hidden by these qualification scripts.

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

Two fresh SDK-only consumers are checking the preceding managed graph records
without rewriting their subjects, coordinates or recorded producer identity.
The first has reopened all 187 records and replayed 52 points with zero native
exchanges or managed queries. The second reader and 11 tamper controls must
pass before selection. Producer SDK identity and current checker SDK identity
remain separate; this does not attest historical native execution.

The separate integer modulus model's first attempt failed at its negative-bound
proof script. That unqualified attempt and actual audit are retained. The
source now reduces the local binding before the split and declares exact
per-theorem axiom footprints, including the imported Std floor identities'
`Classical.choice` dependency. A new actual Lean run and both refusal controls
remain required; no model qualification is claimed from the corrected source.
