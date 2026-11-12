# Explicit original points — checkpoint 42 candidate

This runtime batch is implemented as a prototype and **not yet qualified**.
The selected SDK and live dossier remain checkpoint 41.

`formal.point/prepare` takes a complete `formal.query` and explicit typed
coordinates. It validates all original assertions and, for a proof question,
the original counterexample condition. Only true assertions produce a sealed
packet. False assertions reject it; incomplete arithmetic remains unsupported.
Every original free variable, including displayed inputs, is required, with a
512-variable capacity. No missing native coordinate is inferred or completed.

`formal.point/check` reconstructs the packet against the exact complete query
and replays it afresh. Its result is `checked-data-connection`, with the data
evaluator identified as reviewed implementation reasoning. Kernel execution is
not run; compiler proof authority remains false. This separate profile does
not extend the restricted Int/Bool `formal.witness` metatheory or borrow its
Lean receipts. Existing standard identity capacities remain unchanged; a
comparison-only Merkle hash cannot authorize these packets.

The mathematical data evaluator supports concrete Bool, Int, rational Real,
text, rounding modes, BV, FP, enum, sequence and finite-update array data within
its implemented operations and limits. An unimplemented operation or missing
coordinate is not filled by a solver call. Display observations can remain
unavailable without becoming assertion evidence. Mathematical NaN remains a
semantic value without an observed IEEE payload.

`veritas.property/observe-point` is the separate Source operation. It prepares
the declared function/predicate and generator domain, binds an ordered vector
of actual runtime arguments, checks an original mathematical counterexample,
then runs the stored ANF and compares both outcomes. Only an independently
checked point plus a reproduced actual Source failure yields `refuted`.
A mismatch remains disagreement. Fresh preparation can execute phase code;
this is not a sandbox or universal Source/compiler preservation theorem.
The pure point checker itself performs neither Source preparation nor native
queries. The Source observation must not inherit a universal purity claim.

`veritas/float-of` is a new finite binary64 interval generator, separate from
historical `real-of` (which also admits integer sample endpoints). Numeric
closed bounds that contain zero admit both signed zeros. Sampling, enumeration
and shrinking use exact ordered bit keys rather than host Float interpolation
or numeric deduplication. `float-cardinality` counts admitted patterns exactly;
`float-domain` records finite cardinality and enumeration budget separately.
The old `gen-enumerate` sentinel `:infinite` still means not enumerated above
10,000 values, not mathematical infinity. Float generators have typed term
domains and do not reuse the legacy SMT Real printer.

Runtime observation now checks scalar kind as well as value: an Int descriptor
cannot accept a returned Float merely because numeric `=` agrees. A Source
equivalence query with distinct scalar result kinds asks whether both sides
raise; successful results of different observable kinds differ. Same-kind
questions retain their previous construction. Unsupported shapes return a
structured refusal rather than leaking a sort-construction exception. This
outcome relation still ignores exception categories when both sides raise.

The confirmed SDK41 baseline and its exact pin are retained under
`evidence/explicit-points`: Int observations accepted runtime `1.0`, cross-kind
Source equivalence threw, and `real-of 0.0 0.0` admitted both Int and Float.
Qualification and fresh-process evidence for this batch are pending.
