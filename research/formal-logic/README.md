# Enchant formal logic, expressed as language terms

This is the expanded OxiZ experiment: one typed, term-based BL interface with
native Z3 and OxiZ backends. It prototypes language semantics, verification
procedures and native theory access together. **The existing compiler/oracle
defaults retain their trust policy.** `system.linear` is now a term-based compiler
consumer with an explicitly declared arithmetic scope.

The latest [graph point-evaluation preview](TERM-FOREST-EVALUATION.md) keeps
argument references through independent BL evaluation. It matches 6,300 root
values across 187 questions and four deterministic point maps each. The shared
131,071-occurrence example evaluates 17 nodes without an engine call. Small
cases pay more admission overhead; managed question/reply integration remains
next. The live dossier includes the actual evaluation and an adjustable,
source-backed structural counting notebook.

The design review is in [ATLAS.bl.org](ATLAS.bl.org), its machine-readable
catalogue in [atlas.json](atlas.json), and the semantic decisions in
[SEMANTICS.md](SEMANTICS.md). The catalogue has 46 interface families, with
implemented fragments and deferred work distinguished per family. It does not
claim 46 complete solver theories. [CONTRACT.md](CONTRACT.md) defines the shared
data contract; [INTEGRATION.md](INTEGRATION.md) describes the production cutover.

[SDK-INTERFACE.md](SDK-INTERFACE.md) connects the experiment to ordinary SDK
programs: typed `system.core` entry points, portable question inspection and a
complete-query oracle handler. Canonical term, proof and state-model sources
now live under `priv/lib/formal`; research imports use the pinned SDK, while
`sdk-src` supplies readable source links outside import search. The initial
qualification passed 86 focused SDK assertions and 2,549 regression assertions.
The [source-property interface](SOURCE-PROPERTIES.md) connects reviewed compiler
ANF to the same questions. Both engines receive identical typed domains and
claims. Source failures require model replay and concrete invocation of that
ANF, with exact code custody and retirement. Checked term certificates retain
the reviewed source/compiler connection as a separate fact. Broader source
extraction, remaining legacy consumers, formal effect semantics and native
pooling remain active work.

The [Veritas term interface](VERITAS-TERMS.md) now covers quantifiers and
compiler-backed clause selection. Typed generator models compose enums,
products, vector lengths and text prefixes without hiding their abstraction
boundaries. Concrete replay, exhaustive search and sampling retain distinct
result meanings; nil and false remain valid witnesses. The ledger stores the
whole question and caller evidence without promoting their authority.
The [typed response interface](RESPONSE-CONTRACTS.md) replaces the mock and fault
SMT-script paths with portable relations, exact source replay and named pins.
It distinguishes isolated faults, all-law faults, vacuity and global integer
boundaries. A server retains its first complete answer per key; the ledger keeps
feasible-response evidence separate from an unchecked optimality claim.
[Complete reply binding](ANSWER-BINDING.md) attaches every native answer to its
exact question and replays the actual published response against all conditions.
The ledger retains complete large evidence in content-addressed payloads.
Checkpoint 38 passed 9,411 assertion executions (1,307 focused and 8,104
regression), an SDK-only consumer and a separate-process compound-ledger reopen
on one immutable SDK. OxiZ's opaque unconstrained model coordinates remain
candidates instead of invented values.

[Checked query preparation](PREPARATION.md) keeps an original question, its
execution form and fresh equality objects. Both engines receive the same plan;
models are replayed and observations reconstructed against the original.
OxiZ settles the selected affine size questions that it leaves unknown in their
factored form. [Declared size evidence](COMPILER-LINEARITY.md) also supplies
portable positive certificates and constructive counterexamples, with true,
false and unknown kept distinct. Checkpoint 39 passes 9,712 assertion
executions (299 new focused, 1,307 preceding focused and
8,106 regression), SDK-only consumption and a fresh-process
four-record recheck. Whole-compiler preservation remains open.

[Typed migration previews](MIGRATIONS.md) separate admitted inputs, preservation
and counterexamples. A fresh conditional certificate and checked admission
permit `verified true`; a checked counterexample gives false; incomplete or
native-only evidence leaves nil. Quoted Source functions are reconstructed and
can be observed at concrete points. Checkpoint 40 passes 9,891 assertion
executions, SDK-only consumption, six fresh-process record checks and the
compiler/source gates. All 187 preceding paired questions remain unchanged;
three new migration subjects use the same questions on both backends. This
grants no mailbox delivery or compiler authority.

[Binary64 Source](FLOAT-SOURCE.md) now preserves finite runtime Float bits,
RNE arithmetic, numeric/strict zero equality and nonfinite-result failure in
typed terms. Checkpoint 41 passes 19,415 assertion executions and the compiler
and source gates. Four paired Source subjects and eight reopened records keep
backend answers, independent replay and actual calls separate. Known Float
legacy checks refuse the former exact-Real shortcut. The full public contents
of all 187 preceding questions match across SDKs; a standard identity capacity
refusal remains explicitly recorded. [Next point interfaces](NEXT-POINTS.md)
remain design work.

[Explicit original points](EXPLICIT-POINTS.md) let BL check typed coordinates
against a complete question even when a native answer is unknown. Point
checking is a separate data-evaluator profile; fresh Source observation is a
separate phase. `veritas/float-of` adds finite binary64 interval domains with
exact pattern counts, while scalar observations preserve runtime kind.
Checkpoint 42 passes 19,726 assertion executions, SDK-only paired examples,
eight reopened points and six separately repeated Source observations.

[Portable public-data graphs](QUESTION-GRAPHS.md) preserve the complete question,
including profiles, observers and provenance, with explicitly versioned references.
The closure question's 110,551 expanded nodes fit in 332 unique nodes and
10,685 canonical bytes. Opt-in version-2 points use the new reference;
version-1 identities and points remain checkable. Checkpoint 43 passes 8,749
targeted assertions, 187 exact public-data round trips, unchanged native results
on both engines, two fresh SDK-only readers and the compiler/source gates.
The targeted run retains earlier arithmetic qualifications as historical evidence.
[Answer and ledger migration](NEXT-GRAPH-CONSUMERS.md) and the
[equality/literal-order review](SEMANTIC-REVIEW-KEYS.md) remain active. There is
no public untrusted byte ingress, graph model theorem or compiler authority.

[ANSWER-INTEGRITY.md](ANSWER-INTEGRITY.md) records the implemented typed-answer
boundary: exact question binding, checked model sorts, reconstructed handler
observations, phase rules and tracked context guards. Its immutable SDK passes
220 focused assertions and 7,086 regression assertions; all preceding 187 native
questions retain their identities and verdicts. Three additional ground cases
exercise floating-point equality through sequences and arrays.
The subsequent [native-context interface](NATIVE-CONTEXTS.md) moves the registry,
assumptions and revision into the port-owning process. Its selected SDK passes
356 focused assertions and 7,086 regression assertions. A client atom is now diagnostic; raw transport requires
a managed reset before portable reuse.
[Managed handler scopes](EFFECTS.md) now carry synchronous named method tables
through managed spawning, futures, registered callbacks and generated actors,
with actual callback custody. Explicit Source world entry and fixed SDK
framework adoption have declared context boundaries. The selected SDK passes
450 focused assertions, 284 native lifetime/capacity assertions and 7,086 formal
regression assertions; all 187 preceding native questions retain their identities
and verdicts. Effect typing and formal runtime preservation remain ahead.
[Packaged worker discovery](PACKAGED-WORKER.md) supplies both native adapters
from the SDK image without research paths or worker environment variables.
Its 503 focused assertions include ordinary and selected Source callers;
7,086 formal assertions and the preceding 187 paired questions still pass.
The portable product has observed host execution with separately recorded
producer and relocated hashes. Clean-host activation remains a separate gate.
[Session lifetime](SESSION-LIFETIME.md) tightens cleanup around setup and user
callbacks, kills stalled owners by exact PID, and refuses trailing ETF bytes.
Its native-process and fault-peer evidence remains separate from genuine
busy-solver cancellation and future pool admission. The selected SDK passes
686 focused assertions and 7,086 formal assertions; all 187 paired question
identities and native verdicts remain unchanged.
[Temporal values and consumers](TEMPORAL.md) now expose symbolic integer spans,
all thirteen Allen relations and complete overlap/chronology questions in the
SDK. Both native engines replay concrete datings; three generated unbounded
term laws have checked portable certificates and original-term Lean proofs.
The temporal SDK passes 2,373 focused and 7,086 formal assertions. The reviewed
semantics distinguish empty spans, endpoint equality, infeasible inputs and
solver uncertainty. Full runtime correspondence remains ahead.

The [live guided dossier](https://work.tailcb5318.ts.net:18100/) presents the
experiment through approachable examples, source-discovered BL components,
connected theory cards and recorded browser evidence. Its
[fully formal language chapter](https://work.tailcb5318.ts.net:18100/#s-could-beam-lisp-be-fully-formal)
distinguishes precise semantics, checked proofs, an optional total core,
verified compilation and application correctness. It proposes a small specified
core, explicit effects and assumptions, independently checked proof objects,
and a visible compiler/runtime trust boundary. The first narrow certificate
checker is now implemented; the wider foundation and verified compiler remain
work ahead. [FOUNDATION.md](FOUNDATION.md) tracks the autonomous implementation.

[REFUTATION-KERNEL.md](REFUTATION-KERNEL.md) adds a sound executable Lean checker
for normalized Boolean/linear-integer refutations, applied to eleven real BL
certificate exports. BL exposes pure packet export and fresh data reconstruction;
a separate capped runner checks the exact packet with the pinned proof kernel.
Term normalization, encoding, BL checker correspondence and Source/compiler
connections remain separate reviewed bridges. Existing solver and compiler
authority policies are unchanged.

[TERM-REFUTATION.md](TERM-REFUTATION.md) carries checked refutations back to the
contained original Int/Bool term trees. Each accepted packet has a Lean-checked
countermodel-preservation proof and a universal conditional entailment theorem.
Undefined arithmetic stays explicit. These are per-question proofs, with a
reviewed term-data/semantic encoding; a general BL normalizer theorem and
Source/compiler preservation remain separate work.

[OBLIGATIONS.md](OBLIGATIONS.md) gives all seven formal subject kinds one closed
plan and proof-data interface. Required properties, unreachable paths, initial
inconsistency and missing SAT witnesses stay distinct. Callers can package
supplied certificates or use the BL producer, select an explicit axiom policy,
and check included term leaves externally. Fresh subject reconstruction binds
complete coverage; model composition and Source/runtime correspondence remain
reviewed connections.

The Core term checker proves that each accepted original Core tree agrees
with its exported success, value and error terms on every typed input. The
record and arithmetic cases include eager defaults, repeated updates, signed
quotient, remainder and modulus. [Core outcome correspondence](CORE.md)

[CORE-CONTRACTS.md](CORE-CONTRACTS.md) applies a checked term entailment to
the exact Core outcome on every admitted input. A witness adds a checked
existence theorem. The composed proof checks the full question after aligning
input slots by name and sort. Its report records the two premise proofs and
the axioms used by the final theorem.

[RECORD-HANDLERS.md](RECORD-HANDLERS.md) connects the exact Core handler family
to invariant preservation at every finite admitted trace prefix.
[RUNTIME-OBSERVATIONS.md](RUNTIME-OBSERVATIONS.md) adds owned BEAM receipts
and a term-native export for independently checking each recorded Core prefix.
The bank example applies its general safety theorem to the same recorded run.
Execution authenticity remains an explicit observer assumption.
The native counterexample bundle also connects the original bounded question
and its witness to the recorded run. Its independent check rejects mismatched
query and trace values even when both premise proofs succeed.

[WITNESSES.md](WITNESSES.md) adds positive SAT evidence with term-native
bindings. Authored assignments and models from either backend are independently
replayed against the original assertions and checked by a constructive Lean
existence theorem. Concrete nonlinear arithmetic, nonzero variable division and
selected dead branches are supported. Feasibility stays separate from conditional
proof coverage. The common v2 bundle combines both and checks a satisfying
claim instance when the witness meets the entailment's exact assumptions.

[SELECTED-SOURCE.md](SELECTED-SOURCE.md) adds contexts for actual named Source
functions. The SDK selects exact revisions, private helpers, captured values
and hygienic macro bindings; a bounded specializer brings that lexical program
into the existing contract/core interface. Both engines can check the same
context-backed promise. Its initialize-then-call scope, unproved specialization
bridge and remaining native runtime assumptions are explicit.

[SELECTED-RUNTIME.md](SELECTED-RUNTIME.md) connects those contracts to actual
original Source factories and exports. `formal/observe-contract` records one
initialize-then-call execution through the normal SDK owner, while
`formal/check-contract-observation` reconstructs the artifacts and checks the
record without invoking the selected code. Finite conformance, contract safety,
error cause, invocation boundary and universal refinement remain separate facts.

[HYGIENE.md](HYGIENE.md) repairs an observed source/Core capture error: a
semantic input role could share a compiler-local spelling and change 17 into a
modeled 20. Declared inputs are now compiler lexical parameters, Core binders
are fresh for the referenced roles, and unresolved globals cannot borrow local
aliases. The retained old contract is checked afresh through this boundary.

[ELABORATION.md](ELABORATION.md) adds a separate ANF/Core translation validator.
`formal/check-elaboration` reads a saved pair without calling the compiler,
elaborator, canonicalizer, evaluator or either native backend. It checks lexical
bindings, exact intrinsic identities and whole-record evaluation order. Source
front ends now require that gate, separately from the conditional term proof.
A typed mathematical ANF model has a universal lowering-preservation theorem
in Lean; connecting the BL validator, named ANF and Source specialization to
that model remains unproved.

[SPECIALIZATION.md](SPECIALIZATION.md) checks the earlier selected-unit to ANF
reduction too. It retains ordered initializers, compares eager argument bindings
under the caller environment and helper bodies under their captured environment,
then derives the alias map for the following ANF/Core gate. An altered capture
can produce a consistent 102-valued residual model for a Source call that returns
42; the new earlier gate rejects that mismatch. Complete prepared context proof
objects are available through `formal/prepare-source-context`. Neither relation
check is a mechanized proof of the original Source compiler's correctness.

[CONNECTIONS.md](CONNECTIONS.md) separates authored Core, actual Source and
reviewed symbolic interpretation in the common evidence ledger. Core-only
contracts and Core/Core comparisons explicitly carry no BL Source claim.
Every model kind exposes a canonically identified interpretation record naming
its exact model and prepared questions. That record remains a reviewed
implementation connection; no proof gate accepts it as a certificate.

`formal/certify` produces and independently checks Boolean/linear Int proof
objects. `formal/check-certificate` checks a retained object against its exact
statement, assumptions, profile and scope without either native solver.
Search is incomplete and does not turn a failure into SAT. A focused run passed
577 assertions, including 511 for the certificate boundary. The checker's
implementation, source connection and compiler/runtime trust are explicit;
these tests are not a mechanical proof of soundness. Native solver result
certificates retain their original unchecked status.

[CORE.md](CORE.md) specifies the first executable Int/Bool core. It has lexical
bindings, selective conditionals, left-to-right evaluation and exact named
failures, with separate reference and symbolic interpreters and real ANF
elaboration. Its focused file passed 3,194 assertions. Core equivalence includes
the error identity as well as successful values. The source/core and core/term
connections remain reviewed implementations with unmechanized metatheory.

[CONTRACTS.md](CONTRACTS.md) exposes `formal/program-contract` and
`formal/verify-contract`: closed program definitions with preconditions,
postconditions and exact permitted failures, conditional certificates, checked
inconsistency evidence and optional native feasibility/counterexamples. The
integrated ten-file run passed 4,575 assertions. Derived scalar observations can
use labelled replay when OxiZ leaves a compound value opaque; native model
availability and certificate authority remain separate.

[RECORD-HANDLERS.md](RECORD-HANDLERS.md) extends the core to closed records and
actual source functions, preserves eager whole-record outcomes, and derives
protocol state updates from real handler ANF. `formal/source-protocol` joins
the common check/compare/describe interface; accepted source traces also execute
every handler in the concrete core. The focused record/source-protocol run
passed 1,292 assertions across six files. Six retained examples compare both
native engines. That separate product/core checkpoint checks 42 theorems with
explicit axiom audits. Source/model correspondence and live actor semantics
remain unproved; compiler authority remains disabled.

Source protocols now also use the same `formal/protocol-trace` constructor for
bounded safety. Questions bind the exact source and depth; accepted native
counterexamples pass both state-model and extracted handler-core execution
replay. The focused source-bounded/protocol/facade run passed 762 assertions,
including 159 new source-trace checks, and nine examples ran with both engines.
The separate mathematical model now checks 46 theorems; universal source/model
simulation premises remain unproved. [BOUNDED-TRACES.md](BOUNDED-TRACES.md) states
the two trace profiles and exact retained scope.

[RUNTIME-OBSERVATIONS.md](RUNTIME-OBSERVATIONS.md) adds explicit actual BEAM
observation. The producer compiles only the admitted source and runs one owned
sequential actor under exact artifact custody. The separate receipt checker
reproduces artifacts and compares recorded outcomes without loading their BEAM
or calling their handlers. The integrated run passed 921 assertions, including
159 runtime checks. Eight retained observations, including counterexamples from
both engines, matched their models; all eight also passed fresh-VM record
validation with no recorded-handler calls or observed-module loads in the
instrumented check window. Conformance and safety are distinct, and the observer,
caller environment, intrinsic meanings and compiler remain explicit trust
boundaries. No universal runtime refinement or compiler authority follows.

[INTRINSICS.md](INTRINSICS.md) records a source-admission repair discovered by
that observer: `Num/div` cannot borrow integer quotient semantics, and raw
Erlang negation cannot borrow BL truthiness. Remote calls now use reviewed
module/function/arity identities. The declared Var assumption for scoped record
operations remains explicit; this does not freeze mutable environments.

[CONTEXTS.md](CONTEXTS.md) now implements an opt-in explicit record binding
context as portable BL data. One context can back a function contract or a
source-derived protocol; contextual traces and actual artifacts bind its exact
identity. Linked execution avoids the probed ambient record Var while preserving
ordered whole-record outcomes. The canonical-identity follow-up passed 7,099
assertions across 22 files, including 139 context and 50 identity checks.
Transitive runtime closure, macro/source context,
compiler preservation and general effects remain further work.

[DATA-IDENTITY.md](DATA-IDENTITY.md) specifies the new canonical data identity
profile. It fixes a real fresh-VM receipt mismatch, normalizes collection
contents and keeps namespaces and data kinds distinct. New closed objects carry
an explicit identity-profile marker. Earlier default-ETF objects remain
historical evidence for their recorded code, rather than being silently migrated.

[metatheory/Core.lean](metatheory/Core.lean) adds a separate typed mathematical
model checked by pinned Lean 4.34.1. All 18 theorem audits report no axiom
dependencies, including natural and lexicographic ranking rules. This does not
prove the BL implementation, canonicalizer, ANF bridge or compiler correct;
[the metatheory notes](metatheory/README.md) state the boundary. Canonical lexical
identities also passed a 3,302-assertion core/contract/API follow-up.

[LOOPS.md](LOOPS.md) adds ordinary source `loop/recur` contracts with invariants,
scalar or lexicographic integer ranks and exit conditions. Proof objects carry
certificates for every obligation, including unreachable-path justifications.
The focused loop/core/contract/API run passed 3,404 assertions, and six examples
have retained Z3/OxiZ observations. A failed template is `obligation-refuted`,
which does not establish divergence of the actual program. The twenty-two-theorem
Lean model exposes the extra standard axiom dependencies of its integer rules;
compiler/model connections remain unproved.

The canonical source remains [ATLAS.bl.org](ATLAS.bl.org). Owner feedback saves
into that file explicitly; anonymous readers cannot write. The live host is
owned by this integration session. Use `research/formal-logic/review url` to
find it and `research/formal-logic/review stop` to retire it. It uses the
local `~/projects/enchanted-skills` dossier and codebase-review kits. The
[presentation evidence](evidence/story/README.md) records their observed source
identity, browser checks, executable cells, recorded frames and limitations.

The older [standalone interactive atlas](evidence/dossier/atlas.html) is a
retained snapshot with read-only feedback. Its historical
[browser audit](evidence/dossier/browser-audit/audit.json) passes 184 checks
over 12 graphs. It is separate from the new live presentation and starts no
server or application.

Owner: the integration session in the repository's `main` checkout. The
requested `prototype/oxiz-worker` worktree supplied isolation for this
experiment; the qualified research batch is integrated and archived, with the
temporary worktree retired. [retirement.json](evidence/retirement.json) records
the archive, recovery bundle and transfer of the exact native artifacts.
Runtime source is unchanged. [sdk-pin.json](sdk-pin.json) retains the qualified
SDK, verified by the runner; this project produces no SDK.

## The common BL interface

```clojure
(ns example
  (:require [formal.api :as formal] [formal.term :as t]
            [formal.value :as v] [formal.collections :as maps]
            [formal.data :as data]))

(def inputs
  (formal/symbols "ledger"
    {:accounts {:kind :map :keys [:alice :bob] :item t/Int}
     :who {:kind :key :universe [:alice :bob]}
     :amount t/Int}))

(def obligation
  (formal/question inputs
    {:id :read-after-write
     :claim (fn [{:keys [accounts who amount]}]
              (v/equal
                (data/unwrap (maps/map-lookup
                               (maps/map-assoc accounts who amount) who))
                amount))}))

(formal/describe obligation)              ; inspect pure data, profiles, bounds
(formal/check {:backend :z3} obligation)
(formal/check {:backend :oxiz} obligation) ; identical question and interpretation
(formal/compare obligation)               ; agreement and replay remain distinct
```

The map theorem is exact over its declared two-key universe. Map payloads have
independent presence, so a missing entry and an entry holding nil differ. A
symbol declaration does not manufacture every possible BL runtime value.

The architectural seams are:

| Piece | Owns | Common contract |
| --- | --- | --- |
| `formal.term` | Checked primitives and immutable DAG | sort, operation, arguments, literal/index data |
| `formal.value` and theory modules | Language meaning | payload, `defined`, `within`, constraints, domain/profile, scope |
| `formal.source` | Reviewed compiler ANF lowering | declared scalar bindings, explicit unsupported result |
| `formal.query` | The question | named assumptions, claim, observations, profile, bounds and origin |
| `formal.logic` | Shared proof/search methods | feasibility, proof interpretation, witness replay, result provenance |
| `formal.backend` | OTP custody and native lifecycle | generation, DAG import, scoped assertions, check, observations |
| Rust adapters | Solver-specific native objects | direct Z3 C API or OxiZ Context; no SMT script fallback |

Terms contain no pointers, native handles or owner PIDs. Session registries
intern shared subterms once and import only new nodes. Native generations
prevent stale handles; reset preserves the portable terms. Source origins stay
outside semantic term identity. The wire is bounded packet-4 ETF with binary
user names and a fixed atom vocabulary. The solver runs outside the BEAM.
Hard deadlines close and retire the owner; EOF terminates even a busy worker.

The facade accepts native scalar sorts and schemas for nullable values,
Options, finite keys/maps/sets/bags/relations, bounded vectors/bytes, tagged
sums and fixed-scale Decimal values. Theory modules remain independently
usable pure functions. Builder callbacks construct a model; this does not
certify the implementation of an arbitrary BL callback.

## Which interfaces this opens

“Implemented” below means a concrete prototype fragment, with the scope of its
receipt; the atlas carries the detailed contracts and open questions.

| Interface family | Prototype / remaining boundary |
| --- | --- |
| Bool and truthiness | Typed Bool; reviewed scalar ANF truthiness |
| Unbounded Int | Native arithmetic; no machine-width approximation |
| Division profiles | Partial toward-zero quot/rem, divisor-sign BL mod, separate Euclidean remainder |
| Exact rational / Real | Native rational terms; algebraic model values remain opaque |
| Decimal and quantization | Fixed-scale exact coefficients; numeric versus representation equality; contexts/rounding remain |
| Finite floats / IEEE | Reviewed finite binary64 scalar ANF arithmetic, bit-preserving observations and independent IEEE replay; broader casts, functions and preservation proofs remain |
| Fixed-width BV | Native wrapping arithmetic, comparisons, shifts, extract/concat/extend |
| Bytes / bitstrings | Bounded byte vectors; explicit BV layouts, codecs and overflow profiles |
| Codepoint text / regex | Native codepoint strings; regex constructor vocabulary remains |
| Grapheme text | Runtime canaries and reviewed boundary; grapheme decision procedure remains |
| Names / identities | Closed nominal universes; open runtime atom/symbol identity remains |
| Enums / algebraic data | Native enum plus finite tagged sums; recursive native ADTs remain |
| Products / records | Model payloads exist; standalone nominal product API remains |
| Option / Result / errors | Presence, nil, partial selectors and raisedness; exception identity remains |
| Finite lists | Native Seq probes; BL list representation and list-specific operations remain |
| Vectors | Bounded indexed values, current nth/defaults and proposed strict access |
| Lazy prefixes | Scoped proposal; productivity, effects and infinite streams remain |
| Maps | Finite presence-aware updates, lookups, cardinality and extensional laws |
| Sets | Finite characteristic vectors, algebra and cardinality |
| Bags | Finite multiplicities; explicitly weaker than queue order |
| Equality / ordering | Typed SMT identity, domain equality, outcome equivalence; generic runtime repair proposed |
| Uninterpreted functions / sorts | Native terms and explicit model opacity |
| Quantifiers | Native forall/exists, binder scope checks; triggers and completeness remain |
| Recursion / induction | State induction obligations; recursive definitions/source termination remain |
| Finite choice / PB | Bool/Int finite encodings; specialized PB/weighted APIs remain |
| Relations / orders / graphs | Finite closure, cycles, partial/strict order and delegation |
| Pattern coverage | Tagged constructor coverage, strict selectors and partial matches |
| Refinements / units / contracts | Versioned descriptor seam; dedicated units/refinement elaboration remains |
| Function equivalence / symbolic execution | Reviewed scalar ANF; successful value plus raisedness; general calls remain |
| Termination / rankings | Obligation design; whole-call-graph implementation remains |
| Size / cost | Explicit collection bounds; general cost semantics remains |
| Effects / frames / commutativity | Pure update laws; checked source effect summaries remain |
| Ownership / capabilities | Finite delegation relation; runtime admission stays operational |
| State safety | Initiation, preservation, feasibility and bounded traces |
| Temporal / fairness | Safety substrate; liveness/fairness/model checker remains |
| Actor protocols / queues | Capacity and failed-step models; live BEAM scheduling/order remains |
| Migration / simulation | Explicit model-to-model initial and step simulation; hot-load admission remains |
| Datom integrity | Source/key semantic review; database model integration remains |
| Bitemporal data | Interval/timeline interface proposal; implementation remains |
| miniKanren / residual SMT | Typed residual constraint design; scheduler/unifier integration remains |
| Horn / invariant inference | State obligations; native fixedpoint/Horn interface remains |
| Optimization / MaxSMT / Pareto | Exact bounded integer optimization; native optimization/soft constraints remain |
| Synthesis / abduction / repair | Finite grammar candidate search and universal checks; general synthesis remains |
| Enumeration / shrinking / counting | Scalar projection enumeration with UNSAT completeness; counting/shrinking remain |
| Cores / witnesses / certificates | Native Z3 cores, shared deletion explanations, independent replay; separate Bool/linear Int certificates are checked; native solver certificates remain unchecked |
| Operational observations | Captured runtime canaries; facts carry explicit assumptions and never grant authority |

The same `formal.query` is used for theorems, counterexamples, relation laws,
trace safety and simulation obligations. Enumeration, finite optimization,
finite grammar synthesis and deletion explanations are implemented once above
both solvers. They stop on unknown or incomplete evidence. Finite sample limits
do not turn into completeness claims; optimization only claims optimality in
its declared bounds.

## What OxiZ changes, and what belongs to BL

The native term interface is possible with **both** backends. Z3 already has a
native AST API and [user propagators](https://microsoft.github.io/z3guide/programming/Example%20Programs/User%20Propagator/).
Maps with presence, partial arithmetic, domain-aware equality, symbolic traces
and repair are BL design work; replacing Z3 does not supply these semantics.

OxiZ's concrete attraction is a Rust implementation whose internal types and
decision procedures can be developed alongside a Rust worker. That makes a
custom extension an attractive research direction. Its public theory and
propagator traits are not a verified, automatically wired plugin seam into the
main Context/Solver. A module existing in the source tree is not a callable,
qualified BL capability. Z3 also permits custom propagation; neither backend
makes distributed BL state an SMT theory automatically.

This worker pins OxiZ **0.3.4**, `oxiz-core`/`oxiz-solver` with `std` and default
features disabled. Results describe that exact feature selection, not every
OxiZ crate/feature. [Upstream documents open limits](https://github.com/cool-japan/oxiz#honest-limits),
including Bool-argument UF, scalar models and Real division. Our native probes
measure actual fragments and keep unknown/unsupported distinct from matches.
The Z3 adapter uses the exact patched library selected by the SDK runner.

## Evidence and semantic review

The retained evidence includes runtime canaries, source discovery, a language
feature matrix and native theory probes. A qualification receipt records exact
source, SDK, native artifacts, commands and result counts. The combined run
passes **795 assertions across seven files** on one native worker artifact.

| Corpus | Questions | Z3 expected interpreted answers | OxiZ expected interpreted answers |
| --- | ---: | ---: | ---: |
| Language values, relations and transitions | 61 | 61 | 56 |
| Native theory and boundary probes | 95 | 88 | 55 |
| Bit layouts and declared FP outcomes | 31 | 31 | 17 |
| Total | 187 | 180 | 128 |

Z3's seven other outcomes are five SAT candidates with incomplete domain replay
and two explicit adapter boundaries. OxiZ's other outcomes are 36 unknown,
18 unsupported and five SAT candidates. No final case has an opposing decisive
answer or invalid independently replayed model. These are query counts, not a
solver coverage percentage or a performance benchmark. Details are retained in
[features.json](evidence/features.json), [native.json](evidence/native.json),
[advanced.json](evidence/advanced.json) and
[qualification.json](evidence/qualification.json).

Codebase additionally indexed all 21 prototype modules in
[prototype-index.json](evidence/prototype-index.json), with local semantic
analysis requested for `formal.value` and `formal.numeric`. This supplements
the historical 32/33 core-source inventory; it does not erase its failed file
or infer complete external-effect coverage.

The initial native
run is retained in [native-before-normalization.json](evidence/native-before-normalization.json):
it exposed a genuine NaN identity mismatch on the direct OxiZ route. Native
import now normalizes NaN literals to SMT's single NaN; raw payload identity
belongs to BV, and NaN FP observations remain opaque. This narrow correction
does not establish general symbolic FP completeness.

Results keep raw solver status, interpreted verdict, model availability,
independent replay, certificate status, authority and scope separate. A SAT
answer whose witness cannot be replayed is a `candidate`. A failed replay is
`invalid-model`. Proof preflight exposes inconsistent assumptions as `vacuous`.
Persistent session assertions participate in meaning, free-variable replay,
preflight, evidence and cache identity. Observation requests do not add facts.
All experiment answers are untrusted; promotion into compiler caches is disabled.

The semantic review recommends fixing numeric equality, choosing coherent
user-facing key equality, and keeping representation equality explicit. It
also identifies the old negative-divisor modulus translation defect. The
[reviewable equality patch](proposals/numeric-equality.patch) is **unapplied**
and BEAM-only. It includes tests/docs and Datom expectation changes. Cross-target
JS and hash-container semantics need their own qualification; the pinned
runtime observations are not relabeled as proposed behavior.

## Reproduce

From the integration checkout root, with only one substantive check at a time:

```sh
research/formal-logic/build
research/formal-logic/run test research/formal-logic/test/kernel_test.bl \
  research/formal-logic/test/backend_test.bl research/formal-logic/test/api_test.bl \
  research/formal-logic/test/source_test.bl research/formal-logic/test/features_test.bl \
  research/formal-logic/test/native_test.bl research/formal-logic/test/advanced_test.bl
```

The locked release build has a 4 GiB/no-swap cap, one Cargo job and a 30 minute
ceiling. Checks use the exact pinned launcher in one cold VM, a private runtime
directory, a 4 GiB/no-swap cap and a 15 minute ceiling, then remove that directory.
No daemon, SDK build or application startup is part of these checks. The
historical scalar worker remains available under `research/oxiz-prototype`.

Next integration work should qualify the reviewed semantic changes, migrate
the oracle/obligation/cache seam to this typed query contract, and add source
summaries for pure user functions and collection operations. Then the most
valuable language experiments are refinement contracts, residual miniKanren
constraints, Datom invariants and actor protocol simulations. Each can reuse
the term/value/query/evidence architecture while retaining its own semantic
and operational boundaries.
