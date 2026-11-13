# Wrapped values need a separate bound for temporary arithmetic

The pinned Lean model in [WordEnvelope.lean](metatheory/WordEnvelope.lean) is
qualified by [the actual receipt](evidence/word-envelope-model/qualification.json):
six theorems, nine definition/library audits and two rejected false claims.
This is a mathematical model, separate from the BL resource-planner prototype.

The model defines capacity as `2 ^ width`, natural-number wrapping by remainder,
and profile admission by positive width below an explicit limit. Its checked
results establish positive capacity, a wrapped value below capacity, an addition
bound below the next capacity, and a multiplication bound below the doubled-width
capacity. It also rejects zero-width admission. The concrete two-bit example
wraps `3 * 3` to `1`, while the temporary `9` exceeds two-bit capacity.

Five theorem audits are empty. Multiplication inherits `propext` through the
pinned Std `Nat.pow_add` theorem. The separate dependency run audits that fact
and eight other definitions/helpers; those eight lists are empty. This exact
ledger is checked, rather than accepting an arbitrary set of tool-reported
assumptions.

The first run checked the theorems but refused qualification because the declared
multiplication ledger omitted `propext`. Its actual output remains under
`before-axiom-ledger/`. The first zero-width negative control was rejected for
missing decidability, which did not establish the intended false-claim refusal;
that attempt remains under `before-zero-width-control/`. The corrected control
unfolds its concrete proposition and is rejected because the proposition is
false. The wrapped-size control is also actually rejected as false.

Natural modular arithmetic does not by itself prove equivalence to BL's bit
masking, signed views, negative subtraction, shifts, coordinate reader, resource
planner or graph evaluator. The source-to-model and compiler/solver connections
remain separate obligations. No allocation, CPU-cost or language-totality theorem
follows from these magnitude bounds. The whole formal-language goal remains
active beyond this artifact.
