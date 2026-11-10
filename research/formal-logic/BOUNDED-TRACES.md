# From a native search to an independently replayed trace

`formal/protocol-trace` constructs a closed bounded safety subject from an exact
protocol definition and a depth from zero to sixteen. `check`, `compare` and
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

## Limits and the next connection

The maximum depth is sixteen. A preflight check caps estimated model-unrolling
work at 32,768 units across depth and model size. Default proof search allows 2,048
search nodes and 512 arithmetic rows; callers can supply supported search
budgets. Runtime, memory and solver deadlines remain controlled by the runners
and backend sessions. These resource limits do not become language exceptions
or proofs of nontermination.

This searches and executes an authored pure state model. The source-handler,
live actor, mailbox and scheduler connections remain unproved. A safe bounded
answer covers its declared depth; an unbounded induction argument is a separate
subject. Delivery fairness, crashes, external effects and liveness need their
own semantics and evidence. No compiler proof authority is granted.
