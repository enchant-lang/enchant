# Checkpoint 13: a separate ANF/Core validation gate

`qualification.json` binds the complete coherent 8,059-assertion run across
26 files to the exact 77 library/test source hashes and immutable SDK/worker
pins. `corpora-comparison.json` compares all 187 per-case Z3/OxiZ verdicts with
the preceding hygiene checkpoint; no verdict changed, and neither corpus has
a disagreement or invalid model. This is an overlapping regression total.

`examples/` retains five actual compiler-produced ANF/Core pairs and the ACTUAL
pre-repair pair extracted from the original hash-pinned hygiene archive.
`fresh/` checks all six in another VM: the five current pairs reproduce their
results exactly; the historical pair fails lexical-reference matching.
Positive calibration sees every instrumented compiler, elaborator, Core
canonicalizer/evaluator and native-session entry before the checking window.
Each corresponding count is zero inside that window.

`prior-runtime-fresh/` rechecks the eight earlier original Source execution
records against the added gate. All remain conforming, with the same three
violated promises. Calibration observes a real unrelated Source initialization,
export call and owned module load; checking the old records sees none.

`Core.olean`, `model-check.txt` and `model-qualification.json` qualify the full
56-theorem Lean model, including the typed mathematical ANF translation's
whole-outcome preservation. Forty-four axiom audits are empty. The other twelve
list their exact standard assumptions. No admitted proof or `sorryAx` occurs
in the successful log. The named SDK ANF, BL checker, selected-unit specializer,
primitive dispatcher and actual Source/compiler/runtime bridges remain
unproved. No production compiler authority follows from these artifacts.

Retained initial failures are excluded from successful qualification:
`initial-check.txt` and `focused-reader-rejection.txt` record test delimiter
mistakes; `focused-check-2.txt` records an invalid list mutation in a test and a
test that reached the canonical codec's depth bound before the relation;
`model-initial-check.txt` records two initially unclosed proof goals. The later
complete logs and exact hashes are the qualified evidence. `model-check-2.txt`
is an intermediate successful compile with a redundant simp-argument warning;
the final model log is warning-free.
