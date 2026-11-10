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
- Actual compiled handler observation: 921 integrated assertions, including
  159 new runtime checks, eight observed traces and eight fresh-VM receipt
  checks. Exact source/artifact custody and finite state/outcome conformance
  are implemented. The fresh checker loads no recorded handler BEAM and invokes
  no recorded handlers in the instrumented window. Environment/intrinsic,
  effect and universal implementation/model correspondence work remains.
- Exact source intrinsic admission: the actual observer exposed a host division
  mismatch. Remote callee/arity and canonical arithmetic identities are now
  checked; Erlang Boolean negation is distinct from BL truthiness. A focused
  nine-file follow-up passed 4,877 assertions, including 135 identity regressions.
  Declared record Vars retain an explicit binding assumption. `INTRINSICS.md`
  records this repair and the remaining source-environment boundary.
- First-class binding contexts: explicit fixed record-call linking is shared
  by function contracts, source protocols, bounded native questions and observed
  artifacts. A focused fourteen-file run passed 5,494 assertions, including 139
  context checks. An owned child-Env probe demonstrates the original ambient
  disagreement and its absence in the explicitly linked execution. `CONTEXTS.md`
  distinguishes function-ANF closure from transitive runtime/source closure.
- Canonical formal data identity: a real fresh-VM receipt mismatch exposed the
  default-ETF hashing assumption. A shared tagged codec and explicit identity
  profile now cover formal objects, core/term/proof digests and cache keys.
  A coherent 22-file run passed 7,099 assertions. Nine execution records and
  three portable proof records recheck in a fresh VM; historical raw-ETF data
  remains separate. `DATA-IDENTITY.md` specifies the format and version boundary.
- Selected Source contexts: actual SDK world/revision selection and hygienic
  expansion now feed a bounded lexical-call specializer and the existing typed
  core/contract interface. Private helpers, captured values and ordered scalar
  initialization are retained. The coherent 23-file run passed 7,266 assertions,
  including 118 selected-context checks. Both source expression front ends now
  share exact callee admission and reject foreign inputs posing as local ones;
  loops reuse the same declared-input namespace. `SELECTED-SOURCE.md` records
  the initialize-then-call scope and the unproved specialization/runtime bridges.
  Four contexts, eight conditional certificates and two native witnesses recheck
  in a fresh VM with no native session in its calibrated checking window.
- Original selected Source execution: contracts now observe the normal SDK's
  actual factory and selected export. Structured byte capture preserves original
  source coordinates without writing at them; emitted unit identities match the
  formal context. The coherent 24-file run passed 7,396 assertions, including
  130 runtime checks. Eight actual observations and a fresh calibrated window
  retain finite conformance, separate contract safety, exact BIF causes and the
  recorded original-instance boundary. Source tail-call frame loss is explicit;
  the older handler projection is unchanged. `SELECTED-RUNTIME.md` specifies the
  profile, initialize-then-call scope and remaining universal proof obligations.
- Source/Core lexical hygiene: a real pre-repair probe modeled 20 where the
  source returned 17, because a semantic role captured a compiler-local alias.
  Expression/loop inputs now enter the actual compiler as lexical parameters;
  every ANF let receives a Core identity fresh for all supplied role references.
  Global values cannot borrow local aliases. The coherent 25-file run passed
  7,560 assertions, including 164 adversarial hygiene checks. Both engines refute
  the old claim, the actual old object is refused on fresh source reconstruction,
  and the original selected Source call returns 17. `HYGIENE.md` specifies the
  boundary. Universal elaborator/compiler soundness remains unproved.
- Independent ANF/Core validation: the source front ends and final selected-ANF
  lowering now pass a separate syntax-directed relation checker. It checks
  lexical mappings, capture-free Core locals, exact primitive identities,
  selective branches and eager scalar/record outcomes without regenerating
  the Core. The coherent 26-file run passed 8,059 assertions, including 499 new
  relation checks. Five archived pairs recheck in another VM with calibrated
  zero compiler, elaborator, canonicalizer, evaluator and native-session calls;
  the actual retained pre-repair pair is rejected. All 187 native corpus
  questions retain their per-case verdicts. Eight prior original Source runtime
  records still recheck unchanged with zero recorded-code loads or invocations.
  `ELABORATION.md` specifies the checked relation and remaining premises.
- Model elaboration preservation: a separately evaluated, intrinsically typed
  mathematical ANF lowers to the existing Lean Core. A universal preservation
  theorem covers every model expression/environment and exact returned or
  named-error outcome. Ten new audited laws bring the model to 56 theorems:
  44 empty audits, four using only `propext`, six using `propext` and `Quot.sound`,
  and the two previous integer ranking laws with their three standard axioms.
  The named ANF encoding, BL relation checker, primitive dispatcher, selected
  specialization and actual Source/compiler bridges remain unproved.

- Selected-unit reduction validation: a separate checker now compares the
  original SDK unit with its proposed residual ANF. It checks captured lexical
  environments, eager caller arguments, fresh beta bindings and every ordered
  scalar initializer, then derives the alias map consumed by the ANF/Core gate.
  The coherent 27-file run passed 8,207 assertions, including 148 new reduction
  checks. Five saved current pairs reproduce in a fresh VM; a deliberate
  capture forgery returns 102 instead of the original Source call's 42 and is
  rejected even though its consistent ANF/Core pair passes the later gate.
  Positive calibration observes compiler, expander, specializer, elaborator,
  canonicalizer, evaluator and native-session calls; all seven counts are zero
  while checking saved pairs. The 187 native questions retain their verdicts,
  and eight earlier original Source records recheck unchanged with no recorded
  code loads, initializations or exports. `SPECIALIZATION.md` states the exact
  SDK-wellformedness and leaf-admission premises.
- Lexical-call model laws: seven new audited results prove typed Core renaming
  preserves complete outcomes under environment agreement, and one-/two-
  argument eager-call laws retain definition captures and caller order. The
  full model now has 63 theorem audits: 47 empty, four with only `propext`, ten
  with `propext` and `Quot.sound`, and the two earlier integer ranking results
  with their three standard axioms. No named-unit encoding, arbitrary-arity
  closure machine or BL specialization-checker soundness theorem follows.

- Separate interpretation ledger: authored Core contracts and Core/Core
  comparisons now explicitly carry no BL Source claim. Every model subject
  exposes a versioned reviewed model-to-term record, identifying its exact
  model and prepared property/obligation questions. Direct term questions and
  failed preparation retain distinct not-applicable/not-established states.
  The coherent 28-file run passed 8,396 assertions, including 189 connection
  checks. Four old certificates, two old counterexamples and one original
  Source observation remain valid without regeneration or re-signing. Four
  saved connection records reconstruct identically in another VM with one
  positively calibrated native session before the window and zero within it.
  All 187 backend verdicts remain unchanged. `CONNECTIONS.md` specifies these
  records as reviewed implementation links; no proof gate accepts them as
  certificates. This checkpoint adds no Lean theorem or soundness claim.

- Executable normalized proof kernel: `Refutation.lean` supplies 17 audited
  results proving soundness of its actual Boolean/linear-integer checker.
  Eleven real BL certificate exports have checked Lean applications of that
  theorem; five well-shaped, rehashed false refutations are rejected by Lean.
  The BL facade exports a closed normalized packet and freshly reconstructs it
  from the exact original question/certificate. The capped external checker
  independently reconstructs canonical identities and parses its generated
  constructors/template before invoking the pinned Lean kernel. Computed
  acceptance audits use `propext`; the general and applied unsatisfiability
  theorems use `propext` and `Quot.sound`. The next missing theorem connects
  original typed term semantics to this normalized problem. BL normalization,
  data encoding, BL checker correspondence and Source/compiler bridges remain
  reviewed, with no new production compiler authority. See
  `REFUTATION-KERNEL.md` for the executable interface and exact proof scope.
  The coherent 29-file run passed 8,504 assertions, including 108 new export
  checks; all 187 native question verdicts remain unchanged.

- Original typed term entailment: `Terms.lean` defines partial Int/Bool term
  values and the countermodel-preservation composition rule, with 14 audited
  general results. The external runner proves that premise for each accepted
  original question tree, then applies the normalized refutation theorem.
  Seventeen real BL exports have checked universal original-term entailments;
  five rehashed false or undefined original claims/assumption changes are
  rejected despite unchanged accepted normalized refutations. This closes the
  original-to-normalized premise for those questions in the contained typed
  model. The data/semantic encoding remains reviewed; it is not a general BL
  normalizer, term-evaluator implementation or Source/compiler proof.
  `TERM-REFUTATION.md` specifies partial arithmetic, guarded proof search,
  original erased inputs, provenance reconstruction and the separate pure API.
  Qualification passed 8,558 assertions across 30 BL files, including 54 new
  original-tree binding checks. All 187 backend verdicts remain unchanged.
  Seventeen archived packets reconstruct in a fresh VM with positive native
  calibration before the window and zero native sessions during reconstruction.

- Common obligation proof data: all seven subject kinds expose a closed plan
  and labelled required/auxiliary questions. BL can search for certificates or
  package another producer's supplied certificates, then freshly check full
  coverage and original-term packet data. Thirteen exports include eleven
  complete declared bundles and two visibly incomplete ones. External checking
  proves 22 required leaves (21 entailments and one unreachable path), plus
  one auxiliary initial-inconsistency leaf. A manifest-only check does not
  reconstruct a whole model: omitted loop premises are rejected by the fresh
  BL subject checker, while external reports retain their declared-leaf scope
  and reviewed model-composition boundary. `OBLIGATIONS.md` specifies the routes.
- Explicit proof foundations: common bundles name `:lean-standard-v1` or
  `:choice-free-v1`. Two countdown obligation proofs actually use
  `Classical.choice` through Lean's arithmetic tactic; standard policy records
  them and choice-free policy rejects the same proof source. Actual theorem
  dependencies are retained per leaf, without implying that no alternative
  choice-free proof exists. Standalone term checking retains its choice-free
  default. The original seventeen accepted term cases and five rejected
  alterations still pass after this policy extension.
  The coherent run passed 8,860 assertions across 31 BL files, including 302
  common coverage/policy assertions; all 187 backend verdicts remain unchanged.
  All thirteen saved bundles reconstruct in a fresh VM and repackage supplied
  certificates with positively calibrated proof-search/formal-session entries
  observed before the window and zero inside it. Source phase preparation is
  explicitly allowed, and no broader compiler-internal absence claim follows.

- Constructive SAT witnesses: `WITNESSES.md` defines explicit typed assertion
  bindings, pure original-query reconstruction and a separate Lean existence
  check. Z3 and OxiZ models use the same adapter and ordinary data packet;
  original assertion replay determines acceptance. Thirty-two packets pass
  the external checker, including five from each engine, and six false or
  undefined replacements fail. Concrete nonlinear multiplication and nonzero
  variable division work without the entailment generator's Boolean case limit.
  Four general results and all applied proofs retain their exact dependency
  audits without `Classical.choice`. Fresh VM replay distinguishes full query
  attribution from the theorem over the contained typed assertions.
- Shared query meaning: proof counterexamples must match their negated claims,
  and SAT cannot carry a hidden claim or counterexample. Native, certificate,
  obligation and witness boundaries share the shape and typed-root checks.
  Expanded serialization limits belong to evidence formats; native shared
  term graphs stay usable. Witness checking validates canonical packet identity
  separately from ordinary Lisp equality. The integration run passed 9,213
  assertions across 33 files; all 187 native verdicts remain unchanged.
- Mixed obligation evidence: format v2 carries refutations and constructive
  witnesses in the same plan. The external checker independently compares
  assertion contexts and applies each matching entailment in Lean. Concrete
  bindings follow original variable names and sorts into the proof's layout.
  The resulting theorem exhibits values satisfying the original assumptions
  and claim. Seventeen exports contain 39 checked leaves and 11 applied claim
  theorems. Initial feasibility can accompany incomplete coverage. A model
  with complete conditional coverage can also have inconsistent assumptions.
  `OBLIGATIONS.md` describes the v2 opt-in and the exact term-model scope.

The selected unit's reduction now has an independent implementation gate, in
addition to the final ANF/Core gate. Connect the named representation and both
accepted rule relations to the typed model. Unit wellformedness, pure lexical
closure construction, environment agreement and reviewed intrinsic meanings
are explicit premises, not facts supplied by a solver. Keep that work separate
from proof-kernel soundness, recursive summaries, broader Source theory domains,
effects/process refinement and the production term-backend cutover.

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

## Actual BEAM observation boundary

The first sequential adapter described below is now implemented. It compiles
only the freshly admitted source, retains its exact BEAM through the SDK's code
custody, observes an owned actor, and separately reconstructs recorded
state/return/named-failure conformance without executing the recorded handlers.
`RUNTIME-OBSERVATIONS.md` specifies the public APIs and exact remaining scope.
Its finite relation does not prove universal runtime refinement. Caller
environment/intrinsic meanings, unobserved effects and the observer itself
remain explicit assumptions. The design below records the boundary that guided
the implementation; broader runtime and soundness work remains active.

The source-bound replay path now supplies a concrete source/core/model witness.
The next implementation should observe the corresponding compiled source in an
owned BEAM process. Keep that effectful producer separate from pure question
construction, portable proof checking and recorded-trace replay. An observation
receipt must not become a theorem about every future execution.

First qualify the pinned SDK's actual compiler/loader and callable boundary.
The current repository has `compiler/eval_form`, `lower/descriptor->beam` and
`lower/eval-anf` paths; their existence in current source does not qualify their
exact pinned-SDK behavior. Retain the emitted module identity/bytes or code
fingerprint, exact admitted source and core identity, SDK identity, successful
returns, raw failure class and owned-process monitor outcomes. Probe ordinary
record updates, variadic updates, signed division and hidden-field failures
before choosing an error normalizer or public runtime interface.

The runtime producer should compile the exact freshly admitted source, not
accept an unrelated callback claimed to match it. Its plain-data receipt should
bind source, core, loaded artifact, initial state, ordered event identities and
each observed outcome. Logical participant IDs belong in the portable data;
live PIDs and function values are custody handles of that one execution, not
logical constants that can be reused after serialization.

Start with one owned sequential actor adapter and explicit delivery/reply
handshakes. Distinguish an accepted message, successful state commit, modeled
named error, unclassified runtime failure, process death, timeout and resource
limit. Only a successful returned state commits. A failed process leaves a last
committed observation; that is not a promise that a dead actor retains live
state. Explain precisely how this adapter's terminal failure maps to the pure
model's retained-state flag. Model stuttering after failure is padding of the
observation, not evidence of a running actor or a delivered message.

A separate checker must rebuild the exact source/model connection and compare
the recorded runtime states/outcomes with both existing reference executions.
It should reject changed source/artifact bindings and partial/inconsistent
records. The execution receipt still depends on the observer and runtime;
replaying ordinary data does not cryptographically attest that an execution
occurred. Keep observed finite conformance, logical certificates, artifact
custody and mechanized correspondence as distinct evidence fields.

Every actor, monitor and temporary module belongs to the capped cold run and
must be retired through the qualified SDK's lifecycle. No persistent project
daemon, operator Source change, compiler authority, arbitrary mailbox policy or
fairness/progress claim follows from this first adapter. Broader OTP actors,
selective receive, sending, crashes/restarts, recursive summaries, general
effects and the checker/compiler soundness bridges remain parts of the goal.
