# Exact values before stronger logical promises

The integration source now repairs generic numeric equality and the legacy
modulus translation. This batch is **not qualified on a new SDK yet**. The
selected SDK and live dossier keep their already qualified behavior while the
new compiler floor, SDK and checks are produced.

The original proposed diffs remain in `proposals/` as review history. Applied
source defines finite generic numeric equality by exact value and introduces
`decimal/same-representation?` for coefficient and scale. Decimal arithmetic
still refuses Float operands. JavaScript compares actual binary64 values using
exact BigInt cross-products. Ordinary map/set keys retain their existing raw
relation; changing that language contract is a separate implementation.

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

Run `build-numeric-sdk.py seed` under a durable owner. It uses the previous
SDK's pinned toolchain and the repository's capped bare-VM regeneration path.
Review and commit its real floor before running `build-numeric-sdk.py prepare`.
Reuse that one immutable artifact for `run-numeric-semantics.py candidate PIN`
and focused checks. Qualify the full produced compiler floor and source
preflight, then compare the affected formal/backend paths at their unchanged
deadlines. Only complete passing gates may select the candidate and update
the live dossier's executed observations. No compiler theorem or whole-language
totality follows from finite test vectors.
