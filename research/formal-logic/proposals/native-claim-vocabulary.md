# Make the claim and its checking basis explicit

This is a reviewed follow-up proposal, not an applied runtime change. The
retained SDK remains frozen during qualification.

The managed request interface reconstructs an unchecked UNSAT result as
`:solver-claim`. Older `formal.logic` and `formal.answer` paths still derive
`:proved` for a proof query from native or handler-reported UNSAT, while also
carrying `:trusted false`, an unchecked certificate and no compiler authority.
`formal.result` maps that label to an entailment claim with a separate basis.
The fields preserve the distinction, but the headline vocabulary obscures it.

The next migration should make one evidence vocabulary apply across term,
graph, contract, loop, translation and protocol entry points:

| Observation | Public meaning |
|---|---|
| Native/handler UNSAT | Reported conditional entailment claim; no checked proof |
| Fresh complete point satisfying all assumptions and the negated claim | Replayed counterexample under its named mathematical/Source profile |
| Fresh complete point satisfying a SAT question | Replayed witness under that profile |
| Independently checked proof object bound to the original complete subject | Checked entailment in the named proof system, with its assumption ledger |
| Inconsistent assumptions | Vacuity information, distinct from an inhabited proof |
| Missing coordinates, refused resources or unsupported replay | Incomplete evidence, even when a backend reports SAT |

Do not rename every `:proved` occurrence mechanically. Portable certificate
checking, mathematical fixture expectations, historical saved records and
compiler policy have different roles. In particular, `logic/invariant`,
`formal.protocol`, result projections and project contract/translation
aggregators currently consume legacy native verdicts. Each must retain the
reported claim while leaving proof acceptance to its actual checker. The
compiler's existing oracle policy remains an explicitly separate boundary.

Version the affected public answer/result profiles and keep historical readers
honest about their original labels. New checks must reconstruct the result from
its complete subject and evidence instead of accepting a caller's headline.
Preserve recorded native outcomes, including actual UNSAT/unknown/unsupported
and the two native deadlines, in the before/after comparison. An intentional
verdict-name change belongs in a migration receipt; it is not zero behavioral
difference. The mature common request profile remains the migration target.

Required controls include a forged `:proved` field, a handler UNSAT claim, an
invalid certificate attached to UNSAT, missing/invalid coordinates attached to
SAT, inconsistent assumptions, actual checked portable proofs and fresh
solver-denied readers of both earlier and new saved formats. Result projection
alone must never manufacture checker or compiler authority.
