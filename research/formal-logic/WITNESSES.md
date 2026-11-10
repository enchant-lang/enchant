# Positive evidence: an actual satisfying assignment

A conditional proof says that a promise follows whenever its assumptions hold.
A SAT witness supplies values for which those assumptions actually hold. These
are separate evidence facets. An unreachable-path refutation does not establish
feasibility; a feasible initial state does not establish a whole protocol's safety.

The prototype now has a constructive witness interface over the same original
partial mathematical Int/Bool terms as the entailment checker:

```clojure
(def x (t/variable "x" t/Int))
(def y (t/variable "y" t/Int))
(def question (q/sat {:assumptions [(t/eq (t/mul x y) (t/int 42))]}))
(def ready (formal/term-witness question [[x 6] [y 7]]))
(formal/check-term-witness-data question (:packet ready))
;; :checked-data-connection, :kernel-execution :not-run
```

A string-keyed map such as `{"x" 6 "y" 7}` is also accepted. Every free input
in the assertions needs exactly one value of its declared type. No implicit
completion of those inputs is allowed. Duplicate names, extra names, expression
keys, integer/Boolean confusion, false assertions and unavailable assertions are
rejected. Explicit `{}` or `[]` can witness an empty context; absent `nil` data
cannot. The finite binding vectors explicitly choose zero/false outside their
indices, so the semantic existence theorem supplies total environments.

## Search, replay and existence

`formal/term-witness-from-result` takes the original SAT query and a native SAT
result from either Z3 or OxiZ. It selects assertion-variable values from
`:assignments`, checks their types and independently replays every original
assertion. Displayed `:witness` observations and a saved `:validation` verdict
are not evidence for this check. Observation-only values never add constraints.
A model from a stronger persistent session is useful only if its explicit values
independently satisfy this original question.

Native discovery metadata stays outside the sealed mathematical packet. It is
claimed origin, not cryptographic backend attestation. The same valid explicit
values can be supplied without a solver. A forged SAT status with wrong values
still fails the assertion check.

The sealed `:bl/typed-term-witness-v1` packet contains the exact assertion trees,
typed finite bindings, a canonical identity, the full original-question identity,
SAT mode and `:bl/partial-mathematical-int-bool-v1` semantics. The pure BL checker
reconstructs the entire packet from the original query and the supplied bindings.
Changing observers or query metadata requires a new full-query connection even
when the mathematical assertion theorem stays the same.

The external command performs the independent proof step:

```sh
research/formal-logic/check-term-witness packet.json --output /tmp/checked-witness
```

It validates the closed schema and canonical bytes, checks exact pinned Lean,
Refutation, Terms and Witness artifacts, emits only closed constructor data and
fixed proof declarations, then independently decodes the emitted terms and
values. Names never enter Lean source as identifiers or syntax. Lean checks
`accepts originalContext suppliedWitness = true` by reduction and applies
`FormalWitness.checked_witness_satisfiable`. This is an explicit existence
proof for these original assertion trees. Printed axiom dependencies must stay
within `propext` and `Quot.sound`; `Classical.choice` is not admitted.

`Witness.lean` provides four audited general results: accepted witnesses satisfy
the context, accepted contexts have a model, the empty context has a model, and
a context containing the sole assertion false has no model. The separate applied
proofs audit their actual dependencies too.

## What ground evidence can express

Concrete replay and reduction support nonlinear multiplication and division or
modulus by a supplied nonzero variable. That is broader than the entailment
producer's linear and ground-division fragment. It does not extend that producer's
search or turn sample values into a universal theorem.

Arithmetic is unbounded mathematical integer arithmetic with Euclidean division.
Zero division/modulus is unavailable. A selected conditional arm and known
Boolean dominance can make an irrelevant unavailable expression harmless;
requiring the unavailable expression itself to be true fails. Real, bit-vector,
string, array, quantified and uninterpreted assertion trees are not represented
in this checker, including logically dead occurrences. Observation-only terms
may use other supported query sorts because they do not enter the assertions.

Ground witness checking does not split Boolean assignments or conditional guards,
so the entailment generator's twelve-case-input limit does not apply. The narrow
external codec still caps bytes, assertion/binding counts, tree depth and visits.
An oversized or unrepresented packet is rejected rather than granted authority.

## One meaning for portable questions

`formal.query/validate!` now serves native checks, certificate preparation,
obligation planning and witnesses. A proof counterexample must be exactly the
negation of its claim. SAT has neither claim nor counterexample. `q/sat` rejects
a supplied nonnil claim, which the previous constructor would silently discard;
put the condition in `:assumptions`. Root sorts, portable contents and observers
are validated at the same boundary. Watchers remain observations. This is a
shared subject rule: a backend may interpret division by zero with a totalized
SMT operation, while this witness profile requires the partial evaluation to
return true. A solver verdict alone does not bridge those semantics.

## Remaining connections

The external report proves satisfiability of the contained typed assertion model.
Its full-query hash is an attribution label until the fresh BL checker matches
it to the original query. The term-data/Lean semantics bridge and local execution
custody remain reviewed. No Source function, compiler, runtime or cryptographic
attestation theorem follows from this result.

The existing common-obligation v1 format deliberately retains its missing-witness
status. The next format can combine these positive packets with conditional
proofs, report feasibility separately from required proof coverage, and freshly
reconstruct the complete model plan. Existing v1 evidence must keep its original
interpretation. Model-to-question soundness and model composition remain distinct
work after that integration.
