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

## Checked state and protocol invariants

This slice is implemented in `formal.protocol` and `formal.protocol-run`, with
`formal.transition` reused underneath. The first focused check passed 648
assertions, including 133 protocol assertions. The current Lean source checks
25 model theorems; the three new reachable-state, failure-exclusion and trace
induction audits are empty. `PROTOCOLS.md` specifies the actual interface and
its boundary to live actors. The design constraints below remain in force.

The existing `formal.transition` already constructs portable machines, bounded
traces and initiation/preservation questions. Extend that model with a checked
aggregate subject rather than introducing a second transition engine. A new
boundary must reconstruct every obligation from a validated closed definition;
cached `defined`, `within`, next-state constraints or authored proof labels
cannot replace their derivation. Validate free identities, schemas, guard and
update sorts, every transition and the exact profile/scope. Keep assignments
simultaneous and the distinction between a false guard and a raising guard.

Start with Bool/Int state, finite named message/transition variants and pure
term updates. Independently check initiation, normal successful evaluation and
invariant preservation for every transition. Prove the general finite-trace
induction rule in the Lean model, while retaining the unproved connection to
the BL obligation generator. Initial feasibility remains separate; a failed
induction template yields an obligation countermodel, not an actual execution
trace. Bounded exploration should provide independently replayed model traces
and keep model capacity separate from language failure.

This first protocol slice specifies a state machine, not live BEAM actor
correctness. Actor integration needs a deliberate observation boundary: send
and receive events, message identity, per-sender ordering, selective receive,
mailbox capacity assumptions, crashes and external effects. A handler that
terminates, a service that keeps responding, and a process that eventually
finishes are different properties. Safety should hold for all permitted
schedules; eventual-delivery and response claims must name their fairness and
failure assumptions. Do not turn a bounded mailbox or a finite trace into an
unbounded actor guarantee.

## Native bounded safety subjects

This slice is implemented in `formal.protocol-trace`, including independent
execution replay, observation comparison, portable proof rechecking and the
common facade. The initial combined run passed 473 assertions, including 103
trace assertions; nine examples ran with both backends and ten native unsafe
answers became independently replayed executions. The generic Lean run model
now formalizes stuttering and persistent failure too. `BOUNDED-TRACES.md` records
the exact behavior and remaining implementation/model boundary.

Connect `formal.transition/safety` bounded questions to the new closed protocol
subject and concrete executor. A bounded safety subject should contain its
exact protocol definition and depth, rebuild the question afresh, retain an
explicit bounded scope, and participate in the common check/compare/describe
facade. Certificates must bind both identities and the requested scope.

Native SAT needs a complete execution witness, separate from an induction
countermodel. Decode its initial state, choices and selected transition inputs,
explicitly label any completion of opaque unused scalars, and replay the
executor. Fill missing derived state observations from that execution while
retaining every concrete native observation for comparison. Revalidate every
query assertion and the negated safety claim with the completed assignment.
Only a valid term replay and a matching unsafe concrete model trace establish a
trace refutation. Invalid, unsupported or incomplete replay remains visible.

Then connect actual source handlers and actor events. Reuse the precisely
specified outcomes and effect boundaries rather than claiming a state-model
proof automatically verifies asynchronous actor behavior. Live mailbox and
scheduler semantics, trace refinement, handler summaries and progress/fairness
arguments remain required parts of the full goal.

## Source-handler connection

The scalar/record core and actual source-function extraction are implemented.
The first source-derived protocol slice passed 1,292 focused assertions across
six files, including 689 record and 125 source-protocol checks. That model
checkpoint checks 42 theorems, with the actual axiom ledger retained separately.
`RECORD-HANDLERS.md` describes the closed interfaces and exact remaining scope.
The BL/source/symbolic/model connections remain reviewed and unproved.

The next bounded connection is now implemented too: one `protocol-trace`
constructor accepts either protocol kind with distinct profiles. Source-backed
native questions bind the exact source and depth; accepted counterexamples pass
both state-model and handler-core replay. Its focused run passed 762 assertions
and the separate mathematical model now checks 46 theorems, including explicit
handler simulation premises. `BOUNDED-TRACES.md` records the connection.

The design below led to those implementations. Next define explicit live actor
observations and refinement. Neither source
extraction nor a finite trace establishes mailbox, scheduling or progress laws.

Prioritize an actual source-backed handler path after the bounded witness
connection. A handler should consume declared state/message records and return
a new state record with an explicit whole-program outcome. Extract its real
resolved ANF; do not substitute a separately authored update callback as proof
of that handler's implementation.

The original core had only scalar results. Its extension needed a specified product or
closed-record form before lowering a handler field by field. Record creation
must preserve the compiler's actual field evaluation order, shared bindings,
selected branches and the first named failure. Projecting one field must retain
any failure from evaluating the whole record. Symbolic fields share one overall
definedness/error outcome. This avoids erasing a failing field just because a
postcondition observes a different one.

Connect that core to the existing closed state subject while retaining exact
source/ANF/core identities and profile versions. Prove or validate the lowered
normal-return and state relation, compare concrete executions with actual BL
handlers, then add live actor observation hooks. Mailbox, scheduler, crash,
external-effect and liveness semantics remain further required work; the pure
record-handler path cannot stand in for them.

The first pinned-SDK observations are retained in
`evidence/record-handlers/probe.json`. Five source samples compiled and six
runtime probes ran. In these observations, map literals preserve their field
evaluation order, `assoc` evaluates supplied updates in argument order, a
projection retains failure in another constructed field, an untaken record
branch stays unevaluated, and an update preserves other fields. These finite
observations guide the implementation; they are not preservation proofs.

The actual ANF uses ordered `:map/:pairs`; literal keys are wrapped in the
reviewed runtime's `hash_key` call. `get` and `assoc` are remote calls into that
runtime. The two-argument function has an outer self-application scaffold and
an inner unguarded variable-pattern clause. Recognize those exact shapes and
identities, retaining evaluation order and refusing unreviewed key operations,
computed calls or incompatible handler patterns.
