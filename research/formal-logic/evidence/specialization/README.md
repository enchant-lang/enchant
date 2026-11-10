# Checkpoint 14: original unit to residual ANF

`qualification.json` binds the complete 8,207-assertion run across 27 files to
79 exact library/test source hashes, the immutable SDK and native worker/library
pins. `corpora-comparison.json` checks all 187 per-case native verdicts against
the previous elaboration checkpoint. No verdict changed, and neither engine
reported a disagreement or invalid model. This is an overlapping regression
total, not a count to add to older checkpoints.

`examples/` contains five original SDK-unit/residual-ANF pairs with their
corresponding ANF/Core objects. The capture example's original Source call
returns 42 through the normal SDK owner. A deliberate capture forgery returns
102 in its Core model: its consistent later ANF/Core pair passes, and its
earlier original-unit reduction fails. Both engines check the correct Source
promise and the separate authored-Core promise, while refuting the wrong
promise when attached to the original Source context.

`fresh/` reproduces the five current reduction verdicts and alias maps, rejects
the forgery, and independently checks all corresponding late pairs. Positive
calibration sees compiler, expander, selected specializer, elaborator, Core
canonicalizer/evaluator and native-session calls before the checking window.
All seven counts are zero inside it. Standalone checking authenticates no
Source provenance or native execution authority.

`prior-runtime-fresh/` rechecks eight earlier original Source observations,
preserving their conforming verdicts and the same three violated promises.
Positive calibration observes an unrelated Source initialization, export and
owned module load. Checking the historical observations performs none of those
operations. SDK compiler/runtime code and runtime floor still match.

`Core.olean`, `model-check-3.txt` and `model-qualification.json` qualify all 63
typed-model theorems. New laws cover whole-outcome lexical renaming under
environment agreement and eager one-/two-argument calls. Forty-seven audits are
empty; the other sixteen list their exact standard assumptions. No successful
log contains a warning, unclosed goal or `sorryAx`. The SDK's named unit/index
encoding, arbitrary-arity closure machine, BL checker soundness and actual
Source/compiler/runtime bridges remain unproved. Unit wellformedness and pure
lexical closure construction are premises, not solver conclusions.

Initial failures are retained and excluded from qualification. `initial-check.txt`
records an adversarial test that targeted an absent call spelling and therefore
made no mutation; the final test checks that values actually change.
`focused-reader-rejection.txt` records a test delimiter mistake with three other
files passing. `model-initial-check.txt` contains a reserved Lean binder-name
parse failure; `model-check-2.txt` contains unspecialized induction hypotheses.
`fresh-initial-check.txt` records tracing setup treating BL's multi-arity
expander callable as an Erlang function. The corrected setup discovers and
positively calibrates its actual entry points. Complete later logs are the
qualified evidence.
