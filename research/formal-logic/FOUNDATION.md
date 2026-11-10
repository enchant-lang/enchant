# An executable formal foundation for Beam Lisp

Owner: the integration session, writing directly to `main`. The autonomous
goal is to implement the dossier's formal-language vision in coherent stages.
All project checks reuse `sdk-pin.json`; builds and checks are serialized.

## Implementation sequence

1. **Checked evidence.** A pure certificate checker for Boolean reasoning and
   linear integer contradictions; a separate, incomplete certificate producer;
   statement/profile/assumption binding; adversarial and independent checks.
2. **Specified core.** A small typed language with explicit outcomes, a reference
   interpreter, elaboration from reviewed compiler ANF and translation checks.
3. **Contracts and totality.** Preconditions, postconditions, effects and
   termination obligations, checked evidence attached to exact definitions.
4. **Composition.** Checked function summaries, refinement boundaries, effect
   frames, language collections and arithmetic profiles; explicit unsupported
   domains and assumptions.
5. **Processes.** Transition contracts, safety and trace refinement, bounded
   exploration, ranking-based progress, fairness and failure assumptions.
6. **Integration.** A common term-based production path, both native backends,
   compiler gates and regression qualification, with deliberate legacy migration.

Each stage must expose useful BL data/functions and retain executable evidence.
The sequence can change when code or checks reveal a better boundary. A stage's
existence does not imply the whole language, compiler or BEAM is verified.

## First proof system

`formal.certificate` checks a refutation of the assumptions together with the
negated claim. Its own normalization recognizes Bool and piecewise linear Int
terms, with ground nonzero Euclidean division in the current version.
It rewrites strict integer inequalities exactly, and can divide an inequality
by the positive gcd of its variable coefficients while rounding the bound down.

A certificate contains a finite binary case split on a normalized Boolean or
arithmetic atom. Every branch closes either because a Boolean assertion is
false under that branch, or because a nonnegative integer weighted sum of its
linear inequalities produces `0 <= b` with `b < 0`. Both branches of every
split must check. Atom definitions come from the statement, never the proof.
The checker recomputes all inequalities, weights, sums and statement identity.
It never calls a solver or trusts a producer's intermediate conclusion.

`formal.proof` searches for such objects separately, using case splits and
Fourier–Motzkin elimination with retained weights. Search is incomplete for
integer arithmetic and bounded by explicit budgets. Failure is `unknown`,
never a proof of satisfiability. Nonlinear multiplication, variable division, arrays,
quantifiers, floating point and unreviewed source effects are refused by this
proof system even when a solver can decide them.

This uses the standard distinction between Boolean combinations of linear
integer inequalities ([SMT-LIB logic catalogue](https://smt-lib.org/logics.shtml))
and proof checking by explicit arithmetic combinations (compare the linear
arithmetic rules in the [veriT proof format](https://www.verit-solver.org/download/2021.06.1/proofonomicon.pdf)).
The certificate format and implementation here are ours; they are not an
implementation of the veriT or Z3 proof formats.

Checked entailment is conditional on the named assumptions. It does not assert
that those assumptions are satisfiable. A source theorem also needs a reviewed
connection between source semantics and its term statement. The checker,
normalization, term validation, exact integer operations, BL compiler and BEAM
runtime remain in the implementation trust boundary. This first checker is not
itself mechanically verified and does not certify all SMT theories.

## Current implementation checkpoints

- Independent certificate fragment: 577 focused assertions and nine retained
  examples, seven with checked proofs and matching Z3/OxiZ UNSAT observations.
- Executable core: concrete and symbolic semantics, exact named errors and real
  ANF elaboration. The initial focused run passed 3,194 assertions.
- Program contracts and scalar observation provenance: the integrated run
  passed 4,575 assertions across ten files, retaining all 187 original backend
  questions and their verdicts in a separate evidence directory.
- Lexical canonicalization: repeated compilation now gives identical closed
  contract definitions; a focused follow-up passed 3,302 assertions.
- Lean metatheory: the pinned tool checks a separate intrinsically typed model
  and ranking rules. This does not verify the BL implementation or compiler
  bridge; the metatheory directory records its actual checked scope.
- Ranked loops: 3,404 focused assertions, six retained examples on both native
  backends, and 22 checked Lean model theorems with explicit axiom dependencies.
- Checked core translations and optimizer candidates: 4,432 combined assertions
  and nine retained examples on both native backends. Common facade: 199 new
  assertions in a separate focused run of 481 assertions. See
  `evidence/translation/qualification.json` for exact qualified sources.

## Loops with checked ranking obligations

This slice is implemented in `formal.loop-core` and `formal.loop`; `LOOPS.md`
specifies the interface. The focused loop/core/contract/API check passed 3,404
assertions, six examples ran with both engines, and the separate Lean model now
checks 22 theorems. The specification below records the boundaries it follows.

Build a separate loop layer around finite core expressions; do not add unchecked
recursion to the core while retaining its structural-evaluation claim. Consume
the real compiler's ANF through `system.ir/anf-loop?`, `loop-parts`, `recur?` and
`recur-vals`. Strengthen recognition to one unguarded inner clause, distinct
variable patterns, matching initializer/recur arities, and an exact self-call.
Do not turn the legacy `^{:decreasing ...}` author assertion into a checked proof.

The intended native interface is a closed loop contract with parameter sorts,
one source loop, `requires(inputs)`, `invariant(inputs, state)`,
`rank(inputs, state)` and `ensures(inputs, state, result)` builders. Infer loop
state sorts from the typed initializers. Recover display names from the pinned
compiler's fresh binding names, refusing duplicate aliases. Keep original input
parameters immutable and distinct from state variables. Builders disappear after
they produce the term descriptors.

Represent loop control as a finite tree of lexical bindings, conditionals,
sequencing, tail recurrence and return; embed typed core expressions at its
leaves. Canonicalize lexical identities. A reference executor must evaluate
recurrence arguments left to right before replacing the state simultaneously.
Its iteration/step ceiling yields incomplete work, not a nontermination proof.

Generate named obligations for initialization, input consistency, invariant
preservation, normal evaluation on each reachable path, exit postconditions,
nonnegative integer ranks, and strict scalar or lexicographic decrease on every
back-edge. Path obligations may be vacuous when the path is unreachable; input
feasibility remains separate. Start with scalar and two-component ranks, using
the checked mathematical ranking rules in the Lean model. The Int-to-Nat and
ANF/core/term connections must retain their implementation trust boundaries.

Qualify an unbounded countdown with an accumulator invariant, a lexicographic
reset loop, growing/nondecreasing counterexamples, selective failure paths and
ignored author assertions. Native counterexamples should expose input, current
and next state with per-field observation provenance. No bounded execution count
may substitute for a ranking proof or for compiler admission authority.

## Common evidence facade

The public `formal/check`, `formal/compare` and `formal/describe` functions now
dispatch on explicit query/contract/loop/translation data tags. They keep a common result envelope for the logical
verdict, conditional certificate status, assumption feasibility, source/model
assurance, counterexample provenance and compiler admission. Preserve existing
query fields deliberately while adding the richer subjects; do not silently
equate a solver proof label with a checked source theorem.

Capabilities expose native solver-proof availability separately from portable
certificate checking. A comparison identifies Z3 as its reference engine and
reports authority as none. This replaces the misleading experimental
`:authority :z3` label; production oracle defaults remain a separate, qualified
migration. The evidence projection in `formal.result` does not perform checking
or fill in missing proof, model, feasibility or source assurance.

## Translation validation and optimizer candidates

`formal.translation` now binds portable evidence to two exact core programs,
their precondition and a return/value/named-error relation. A separate candidate
optimizer implements real core rewrites; it retains the original when the
independent translation gate cannot check the whole result. Native model replay
and concrete execution remain distinct evidence. `TRANSLATION.md` specifies the
gate and versioned normalizers. Qualification is retained under
`evidence/translation`; this is not a production compiler pass.
