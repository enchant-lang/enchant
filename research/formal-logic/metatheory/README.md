# A mechanically checked model, with an explicit bridge boundary

[Witness.lean](Witness.lean) checks concrete satisfying assignments over the same
partial typed terms as `Terms.lean`. Four audited results connect executable
acceptance to explicit satisfying environments and distinguish empty from false
contexts. [The witness interface](../WITNESSES.md) includes authored and native
assignments, independent data decoding, fresh original-query replay and the
remaining implementation boundary. These are existence proofs, separate from
conditional entailment.

Mixed obligation checking imports a freshly checked entailment object and
supplies a concrete witness in its variable layout. Lean checks the original
premises at those values and constructs a theorem that the premises and claim
hold together. The proof source and actual axiom dependencies are retained.
[Mixed obligation data](../OBLIGATIONS.md) describes the full subject check.

[Terms.lean](Terms.lean) adds a typed partial Int/Bool term model and a composition
rule for original-term entailment through checked countermodel preservation.
Generated proofs establish that premise for actual original question trees,
then apply the normalized checker theorem. [The term interface](../TERM-REFUTATION.md)
states the explicit undefined arithmetic, per-question proof scope, independently
decoded data and remaining BL implementation/Source connections. Its 14 general
results and the actual applied proofs are audited separately from Core semantics.

[Refutation.lean](Refutation.lean) is now a second, executable proof-checking
artifact. Seventeen audited lemmas/theorems establish that every accepted
normalized Boolean/linear-integer refutation excludes all models of its input.
Actual packets exported from BL are checked by this exact definition, using
`by decide` and the soundness theorem. [The kernel interface](../REFUTATION-KERNEL.md)
explains the independent data decoding, printed axioms and remaining unproved
normalization/implementation connections. This has a different scope from the
Core semantic model below; neither artifact proves the BL compiler sound.

[Core.lean](Core.lean) defines an intrinsically typed mathematical Int/Bool
language, lexical environments and a structurally recursive evaluator with
returned values and named raised outcomes. It formalizes the reference profile's
selected branches, left-to-right failure behavior and signed integer division
profiles. Binary Boolean operations and sequencing represent folds of the
finite variadic forms. Lexical variables use typed indices.

The Lean model is a separate artifact. Its proofs are not proofs that the BL
type checker, reference interpreter, canonicalizer, symbolic lowering, compiler,
runtime or source elaborator implement that model correctly. Those bridges are
still reviewed implementations with scoped tests. No production compiler
authority follows from these theorems.

The evaluator's definition passes Lean's structural recursion checker. Its
totality and typed-outcome statements describe that total mathematical function;
the deterministic-outcome statement follows from functional evaluation. The
other results check selected evaluation laws, zero-divisor behavior, signed
division examples, and well-founded ranking rules. These are not an independent
small-step semantics equivalence proof. Lean's treatment of
[structural recursion](https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/)
and [inductive type recursors](https://lean-lang.org/doc/reference/latest/The-Type-System/Inductive-Types/)
explains how such model definitions enter its checked logic.

The generic ranking result establishes well-foundedness of a transition relation
when a ranking map decreases in a well-founded order. Scalar natural ranks and
lexicographic pairs are concrete instances. Each BL loop must still supply
checked obligations for its actual steps, invariant and nonnegative ranks;
proof of the rule does not supply its premises automatically.

Run the exact pinned tool under a memory and time cap:

```sh
research/formal-logic/metatheory/run \
  -o research/formal-logic/evidence/metatheory/Core.olean \
  research/formal-logic/metatheory/Core.lean
```

[tool-pin.json](tool-pin.json) pins Lean 4.34.1 and the Nix store artifact from
the repository's existing nixpkgs revision. The runner verifies the executable
hash. This separate proof tool does not replace or rebuild the pinned BL SDK.
The actual proof log and compiled artifact are retained in
`../evidence/metatheory/`; axiom reports are the tool's output, not hand-written
claims about an unchecked file.

The loop extension adds nonnegative integer scalar and pair ranking rules.
Their current proofs depend on `propext`, `Classical.choice` and `Quot.sound`
through the library's integer-to-natural comparison lemma. The initial eighteen
theorems retain their empty axiom audits. Two further theorems give the equation
and exit-postcondition law for an unbounded evaluator built from a total
controller and a well-founded back-edge relation; their audits are empty too.
The twenty-two-theorem compiled artifact,
log and individual axiom lists are retained separately in `../evidence/loops/`;
the initial eighteen-theorem receipt remains historical evidence.

The state/protocol extension adds three general induction theorems. Initiation
and one-step preservation imply an invariant on every reachable state; a
separate failure-exclusion premise then rules out failed attempts there. A
third result gives the invariant at every position of a permitted Nat-indexed
trace. None asserts trace existence, delivery fairness or eventual progress.
Their printed axiom audits are empty. The current 25-theorem source and its
compiled artifact/audit are retained under `../evidence/protocol/`. Connecting
the BL state definition, induction obligations and concrete model executor to
these mathematical rules remains reviewed code, not a mechanized bridge.

The bounded-trace extension defines explicit finite runs with idle, successful
and failed-attempt steps. Failure retains the old state; only idle steps are
permitted afterwards. Five additional theorems check that failure is persistent,
idle padding is allowed, run states are reachable by successful steps, checked
induction premises imply run safety, and every reachable state has a finite
successful run. Their audits are empty. That checkpoint's 30-theorem compiled model
and receipt are retained under `../evidence/protocol-traces/`. The BL unroller,
witness decoder and concrete executor are still unproved implementation
connections; the mathematical model does not qualify live actor behavior.

The record extension adds Unit and finite products to `Ty`, structural recursive
equality, ordered pair construction, both projections, an eager-default
projection and field updates. Twelve further laws check value equality and
whole-product outcome behavior, including failure in a projected-away field.
The new 42-theorem compiled model and printed audit are retained in
`../evidence/record-handlers/`. Thirty-seven audits are empty; value equality and
two construction laws use `propext`, and the two integer rank rules retain their
three standard assumptions above. The named-field layout/construction-order
translation to products and the BL/source/symbolic connections remain unproved.

The source-bounded extension adds typed `HandlerStep` and `HandlerRun` relations.
Four further theorems check persistent failure, one-step simulation, whole-run
simulation and safety inherited through that simulation. Their audits are
empty. The 46-theorem checkpoint and compiled artifact are retained in
`../evidence/source-traces/`; 41 audits are empty and the other five retain the
assumptions listed above. The rules require universal return/failure simulation
premises. Concrete finite replays test instances, not those universal premises;
the BL source/core/symbolic/record-layout and live actor bridges remain unproved.

The elaboration extension defines a second typed syntax, `Elaboration.Anf`, with
its own structural evaluator and a lowering to `Expr`. Its general preservation
theorem covers every typed model expression and environment, preserving both
returned values and exact named failures. The model includes lexical binding,
truthiness, negation and scalar sugars, selective branches, eager sequencing,
arithmetic, products, projections, eager defaults and updates. The primitive
mathematical operations are shared semantic definitions. This is a preservation
theorem for that translation, not a proof about the SDK's named ANF maps, MFA
dispatcher, BL pair checker, named/index encoding, selected-unit specializer or
actual Source compiler. Those bridges remain active work.

The ten new laws bring the audited model to 56 theorems. Three outcome-bind laws
have empty audits; the condition law uses `propext`; general preservation and
five consequences use `propext` and `Quot.sound`. Combined with the earlier
checkpoints, 44 audits are empty, four use only `propext`, six use `propext` and
`Quot.sound`, and two retain `propext`, `Classical.choice` and `Quot.sound`.
The actual compiled artifact, complete audit and qualification are retained
under `../evidence/elaboration/`. The initial failed proof log is historical
evidence of unclosed goals, excluded from successful qualification.

The lexical-call extension adds `Lexical.Renaming` and a complete renaming of
the typed Core grammar. The universal preservation law requires agreement
between the old and new environments through that mapping. Lifting a mapping
through a binding retains the new parameter value. Eager-call laws evaluate
arguments in the caller environment and the body in its captured definition
environment; the two-argument law explicitly weakens the second argument so the
first binding cannot capture it. Exact first/second failure laws prevent the
later argument or body from hiding an earlier failure.

Seven new audited laws bring the model to 63 theorems. The lifting, weakening
and first-failure laws have empty audits; the other four use `propext` and
`Quot.sound`. The complete audit has 47 empty lists, four using only `propext`,
ten using `propext` and `Quot.sound`, and the two prior integer ranking results
with their three standard assumptions. The checkpoint is retained in
`../evidence/specialization/`. No named-unit encoding, arbitrary-arity closure
machine, Source-specializer soundness or BL checker implementation theorem
follows from these results. Their environment-agreement hypotheses require
separate connection proofs for that implementation.
