# From an arithmetic law to typed terms

The qualified arithmetic model establishes floor remainder as an integer law.
`metatheory/TermFloorModulus.lean` now connects that law to the existing pinned
partial mathematical term evaluator. It builds the corrected conditional from
typed `mod`, equality, ordering, Boolean `or`, addition and `ite` nodes.

Six checked results establish:

- Known integer operands with a nonzero divisor evaluate to the repaired value.
- That result equals floor remainder.
- A known zero divisor produces no value.
- An undefined left operand produces no value, including when the positive
  divisor makes the Boolean condition determinate.
- An undefined right operand produces no value.
- The concrete `7 mod -3` correction gives `-2`; raw Euclidean remainder gives `1`.

The exact evidence is in
`evidence/term-floor-modulus-model/qualification.json`. The check reuses the
hash-pinned compiled `Terms`, `Refutation` and qualified `FloorModulus` parents
under the same immutable Lean 4.34.1 toolchain. Both false proof controls are
actually rejected: raw remainder cannot replace the correction, and zero
division cannot become a successful integer value.

Every result uses `propext`, including the reflexive concrete example. The
separate definition audit identifies that dependency in the imported partial
Boolean operation and evaluator. The floor-equivalence result additionally
inherits `Classical.choice` and `Quot.sound` through the arithmetic model's
standard-library floor identity. The correction term constructor and arithmetic
`modulus` definition have no axiom dependencies. The runner requires the exact
reviewed footprint for each theorem and audited definition. Earlier refused
proof and ledger attempts remain recorded beside the successful check.

This connects two mathematical models. The BL flat-graph decoder, actual term
constructors, legacy renderer, compiler, concrete exception type and native
solver implementation still need their own correspondence evidence. These six
results produce no SDK and confer no compiler proof authority.
