# From a native search to an independently replayed trace

`formal/protocol-trace` constructs a closed bounded safety subject from an exact
authored or source-derived protocol and a depth from zero to sixteen. `check`, `compare` and
`describe` accept it through the same interface as the other formal subjects.

```clojure
(def bounded (formal/protocol-trace counter 2))
(def answer (formal/check {:backend :oxiz} bounded))
(:scope answer)
(:counterexample answer)
(formal/compare bounded)
```

The checker reconstructs the model, unrolls its permitted transitions and
builds the safety question afresh. Neither a cached query nor an authored
transition relation can be supplied. Its identity binds the exact model, depth,
profile and closed subject. Portable proof objects also carry that identity and
are checked against the reconstructed question. Changing the bound or model
requires fresh evidence, even when both questions happen to be true.

The question covers all modeled prefixes of at most the declared number of
real transitions. Explicit stuttering retains shorter traces. Safety includes
the invariant at each state and normal evaluation of every attempted step;
failed attempts persist in the trace. A depth-zero search can expose an unsafe
admitted initial state. An empty initial domain remains vacuous.

## What makes a counterexample concrete

A native SAT answer is only the start. The replay boundary:

1. Checks that the observation belongs to this exact bounded subject.
2. Reads the initial state, transition choices and inputs from ordinary scalar
   assignments and native observations.
3. Labels missing Bool/Int scalars completed with false or zero. It preserves
   every concrete native assignment. A concrete watched variable can fill an
   opaque assignment, with its own provenance.
4. Independently executes the declared model and records each state, disabled
   guard, failed attempt, simultaneous update or stuttering event.
5. Fills missing derived state observations from that execution. These values
   are labelled model-execution completion, rather than native observations.
6. Revalidates every unrolled assertion and the negated safety claim using the
   completed assignments. It compares every available concrete observation,
   including the native state sequence, with the replayed values.

Only a valid term replay, a matching state sequence and an unsafe execution
produce `refuted`. An incomplete completion stays a candidate. An observation
conflict after valid term replay, or a mismatch between that valid term model
and concrete execution, becomes an explicit disagreement. Other invalid or
incomplete replay remains visible in the candidate evidence. A chosen completion never upgrades the backend's
original model availability or proof-certificate status.

The counterexample contains ordinary BL maps and vectors: initial state,
choices, events, execution frames, completed assignments and per-variable
provenance. `formal/replay-protocol-counterexample` rebuilds the subject before
checking a supplied native observation again. It accepts no prepared model or
query from the caller.

## What makes a safe answer checked

The portable producer/checker can prove supported bounded questions without a
native solver. Its finite search budget and term fragment remain explicit.
`check-protocol-trace-proof` rechecks a saved proof object without proof search
or a native backend. Native UNSAT alone is `uncertified`; it does not open a
compiler gate or certify the bounded relation's implementation. Unknown,
unsupported, candidate, vacuous and disagreement results remain separate.

Comparisons now report `backend-status-agreement` separately from
`logical-agreement`. The former requires decisive matching native checks and
feasibility phases; the latter can hold because both paths carry the same
checked portable argument. `status-agreement` consistently denotes the native
comparison. A shared proof cannot manufacture a backend capability, and a raw
backend contradiction remains visible even when portable evidence agrees.

## The source-backed path

Pass a `formal/source-protocol` definition to the same constructor. Its closed
subject selects `:bl/source-record-trace-v1`; authored protocols retain
`:bl/pure-state-trace-v1`, their original identities and their existing term
questions. A source-backed question binds the exact full source protocol, its
derived state model and the depth in its identity, profile and scope. Equal
state behavior under a differently spelled source function does not authorize
reusing a proof or native observation for the other source subject.

Preparation re-extracts every handler from real compiler ANF, checks its core
identity and compares the model's complete guard/updates with fresh lowering.
It then builds the bounded question. Native backends receive that source-bound
question directly, rather than a renamed result from an unrelated model query.

Replay first executes the pure state model. It then independently re-extracts
the source connection and replays each selected handler through the concrete
core. Every returned state or named failure must match the model; both complete
state sequences, failure outcomes and accumulated safety must agree. Only then
can a valid full term replay and unsafe trace yield `refuted`.

The counterexample retains `:model-execution`, source-enriched `:execution`
frames, per-handler `:core-execution`, and `:source-replay` with a handler count
and sequence/outcome comparisons. Zero-step initial violations have zero handler
executions. Missing derived states may be completed from model execution, with
the existing provenance; the separate source execution must still reproduce
them. Concrete native observations cannot be replaced. A repaired final state
cannot erase an earlier source violation, and failed handlers retain state and
permit only stuttering afterwards.

Portable proofs bind the complete source subject too. Source/profile swaps,
altered bounds and source/model substitutions are rejected before rechecking.
The common result envelope describes accepted source counterexamples as
`:term-state-and-handler-core-replay` and assumption feasibility as
`:replayed-source-trace`. Neither changes the native certificate status.

`Core.lean` adds a typed handler step/run model and four generic refinement
laws. They show how universal return/failure simulation premises connect a
handler to the state model and carry model safety to handler runs. Those
universal premises are not established by testing a finite trace. The actual
BL/source/symbolic correspondence remains reviewed and unproved. The compiled
46-theorem model, its exact axiom ledger, 762 focused assertions and nine paired
native examples are retained in `evidence/source-traces/`.

## Limits and the next connection

The maximum depth is sixteen. A preflight check caps estimated model-unrolling
work at 32,768 units across depth and model size. Default proof search allows 2,048
search nodes and 512 arithmetic rows; callers can supply supported search
budgets. Runtime, memory and solver deadlines remain controlled by the runners
and backend sessions. These resource limits do not become language exceptions
or proofs of nontermination.

This searches authored or source-extracted pure state models. The implemented
source-handler connection remains reviewed; its mechanized correctness and
the live actor, mailbox and scheduler connections remain unproved. A safe bounded
answer covers its declared depth; an unbounded induction argument is a separate
subject. Delivery fairness, crashes, external effects and liveness need their
own semantics and evidence. No compiler proof authority is granted.
