# Observe the program behind the model

The research interface now has an explicit effectful path from an admitted
source handler to actual compiled BEAM execution. Its result is a finite
observation, checked against both the extracted handler core and state model.
It is separate from logical proof search and certificate checking.

```clojure
(def definition (formal/source-protocol spec))
(def observed
  (formal/observe-protocol-trace definition {"count" 0}
    [{:transition "add" :inputs {"amount" 3}} {:stutter true}]))
(formal/check-runtime-observation definition (:receipt observed))
```

All public inputs and returned evidence are BL data. PIDs, monitor references,
functions and code leases stay inside the observing invocation. The receipt
survives an Erlang external-term round trip. The readable JSON rendering is
diagnostic: it does not preserve every keyword/string distinction and is not
the semantic interchange format.

Current receipts and closed source definitions carry the canonical
`:identity-profile` specified in `DATA-IDENTITY.md`. Pre-canonical default-ETF
objects remain historical evidence tied to their recorded checker commit; the
current checker does not silently migrate those identities.

The fresh-VM research script reads a bounded, hash-pinned trusted ETF archive.
It does not expose an arbitrary ETF decoder. A fresh `:safe` decode otherwise
refuses archive keywords that the new VM has not interned, including sample
IDs. Network/native-worker decoding retains its separate closed vocabulary
and `:safe` boundary.

## Three operations with distinct responsibilities

| Operation | Responsibility | Effects |
| --- | --- | --- |
| `observe-protocol-trace` | Compile the exact admitted source; run the requested sequential trace; return and check its receipt. | Loads owned BEAM modules and starts one owned actor. |
| `check-runtime-observation` | Rebuild the source/core/model connection, reproduce each artifact and compare recorded outcomes. | Compiles to bytes; does not load the recorded BEAM or invoke its handlers. |
| `observe-protocol-counterexample` | First fully replay a source-bound native counterexample, then observe that exact initial state and event sequence. | Observes only after successful native term and source/model replay. |

The common SMT `check/compare/describe` interface still has seven subject kinds.
Actual execution is an explicitly requested operation, not a hidden side effect
of checking a mathematical proposition.

## Exact source and artifact custody

The producer freshly prepares the source-derived protocol. Initial state,
message shapes, assumptions, the complete event sequence and both reference
executions must be admitted before it starts an actor. An unsafe admitted trace
is allowed: observing a bug is useful evidence.

Each handler is re-extracted through the real compiler's ANF and checked against
its core identity. `lower/descriptor->beam` emits a private module with a
zero-argument constructor for the native two-argument handler. The SDK retains
those exact bytes with `Env/retain_exact_binary!`. Before execution the producer
checks the actual function's arity, module and loaded code MD5. Parent code
leases retain the artifacts until the monitored child has stopped. SDK
`spawn-monitor` conveys the caller's execution environment and custody.

Each manifest records handler name, exact source, core identity, module name,
arity, BEAM SHA-256 and code MD5. The checker compiles the expected definition
under the recorded private module name and compares the entire manifest. It
does not compile a replacement source supplied by the receipt, publish that
artifact or call its constructor. Private module names have a bounded grammar;
a receipt cannot choose an SDK module as its compilation target.

Compilation and source elaboration remain executable compiler work. The claim
that the checker does not run recorded application handlers does not imply that
compilation is a sandbox or a verified pure operation.

## The sequential trap-and-stop adapter

Profile: `:bl/owned-beam-observation-v1`. Adapter:
`:sequential-trap-and-stop-v1`.

1. One owned actor reports its supplied initial state.
2. The parent sends one transition name and typed message, tagged with a fresh
   reference and its position. It waits for that exact reply before sending the
   next event.
3. A normal return commits only when it inhabits the declared state type. The
   reply records both the returned outcome and the committed state.
4. A caught handler failure records the raw outcome and last committed state,
   then the adapter deliberately exits normally. This is an adapter policy;
   it is not a general crash/restart or durable-state property.
5. A stutter is observation padding. No message is delivered for it. Padding
   after failure does not claim the actor is still running.
6. The parent stops or kills its actor, confirms the monitor outcome, drains
   its private replies, releases its leases and retires the temporary modules.
   Unconfirmed cleanup cannot yield conforming evidence.

The runtime deadline covers actor startup and the delivery/reply sequence.
Compiler/preflight work is bounded by the outer capped command. The default
actor budget is 10 seconds; the maximum accepted budget is 30 seconds. A zero
budget reports incomplete before actor execution. Other limits are 64 requested
events and a two-megabyte receipt. These are resource limits, not language errors.

## Match a failure by its cause

The first projection supports integer zero division for `quot`, `rem` and `mod`.
It requires a caught `ArithmeticError`, exception kind `:error`, and the first
raw stack frame `erlang/div` or `erlang/rem` with arguments `[integer 0]`.
The captured stack must also name that handler's emitted module. Exception
class or message text alone cannot establish the named core error.

The producer retains up to eight normalized raw frames. A missing cause,
unrecognized failure or missing artifact frame remains unclassified. Timeout,
untrappable process death and invalid returned state remain distinct from a
modeled language exception. A hidden failing record field is still observable
even when the handler subsequently projects another field or returns an empty
state record.

## Reading the result

| Result | What it establishes |
| --- | --- |
| `:conforming` | The complete recorded trace matches the stated state, return and named-failure relation; cleanup is recorded as complete. |
| `:disagreement` | A recorded returned value, state or classified outcome differs from the reconstructed reference. |
| `:incomplete` | Deadline, process death, incomplete extent or an unclassified failure prevents that conclusion. |
| `:rejected` | The receipt, identities, source/artifact binding or declared execution is invalid. |

The producer returns `:observed` when its checker returns `:conforming`.
`runtime-safety` separately reports `:holds` or `:violated` for that complete
finite observation, and `:not-established` otherwise. A faithfully observed
unsafe withdrawal is **conforming and unsafe**. The model predicted its bug.
An unsafe supplied initial state can need zero handler executions.

## Runtime identity and the assumption ledger

The observer requires the immutable SDK product and records its descriptor hash,
OTP/Elixir versions and twelve critical compiler/runtime module fingerprints.
Those modules are retained inside a code lease during the observation. The
selected launch has no adopted runtime floor; the producer reports that fact
without installing one. The loaded `Ns.Core` projection can differ from the
SDK image and across cold VMs. The receipt records both fingerprints and their
relation rather than claiming an image-wide runtime identity.

Rechecking requires the same SDK descriptor and compilation code and exact
artifact reproduction. A historical runtime snapshot may differ from today's
runtime code; `sdk-check` reports that difference explicitly. The recorded
snapshot is observer provenance, not evidence that those old bytes executed.
No checksum or data round trip cryptographically attests an execution.

The observed relation concerns state returns and the supported named integer
failure. The actor inherits the caller's environment. The formal interpretation
assumes the declared core meanings of intrinsics; this first adapter does not
freeze mutable Var bindings or prove absence of external effects. Unknown
source calls are refused by admission, but admission is not an execution
sandbox. Making source resolution, captured environments and intrinsic meaning
an explicit checked boundary is further work.

Finite conformance does not discharge the universal handler simulation premises
of the separate Lean refinement rules. BL/source/ANF/core/symbolic preservation,
compiler and checker soundness, mailbox policy, independent senders, scheduling,
fairness, progress, arbitrary host calls, crashes/restarts and upgrades still
need their own semantics and evidence. Compiler proof authority remains false.

Implementation: `src/formal/runtime-{artifact,outcome,actor,protocol}.bl`.
Focused checks: `test/runtime_protocol_test.bl`. Executable examples:
`runtime-check.bl`; fresh-VM record validation: `runtime-recheck.bl`. Qualification
and raw observations live in `evidence/actor-runtime/`.

## Check the recorded prefixes in Lean

The finite bridge has two checks. Run the first against the original source
protocol and the complete receipt.

```beam-lisp
(def recorded (formal/observe-protocol-trace definition initial events))
(def receipt (:receipt recorded))
(def packet (:packet (formal/core-actor-observation-data definition receipt)))
(formal/check-core-actor-observation-data definition receipt packet)
```

The export requires `:conforming`. BL reconstructs the source model and
recompiles the recorded manifests into bytes during validation. This path
does not load a handler or send messages to an actor. The sealed packet
carries the exact Core model, receipt and artifact identities, and every
recorded state, message and projected outcome. Record fields are ordered
name/value pairs with their scalar kinds fixed by the Core declarations.

Write the packet as JSON using `interop/->json` for the second check.

```sh
research/formal-logic/check-core-observation run.json --output check/
research/formal-logic/check-core-observation run.json --safety actor-proof.json --output linked/
```

The independent bridge decodes the exact programs, admission predicates and
observed values into typed Lean declarations. Lean checks initiation, each
recorded step and a trace proof for every prefix. A step checks admission
and the exact handler outcome. Lean also checks that the handler's typed
environment reads the actual recorded message record. A raise preserves the prior state and records
`:zero-divisor` under the current projection. Idle frames preserve the whole
configuration, including that failure. The independent checker can establish
an unsafe prefix even when the final state satisfies the invariant.

`--safety` accepts an exact `formal/core-actor-data` packet for the same model.
It checks the universal proof afresh, then applies it to every recorded prefix.
The result includes the imported proof's identity and the axiom audit for
each application. The standalone path needs no proof search or solver.

The finite receipt cap still applies. The Core theorem proves a claim about
the projected values. Fresh BL reconstruction binds those values to the
original receipt. An observer who can supply a receipt is still trusted to
report the run faithfully. This bridge has no cryptographic execution
attestation and establishes no universal BEAM refinement.

The seven real receipts, exact Lean proofs, fresh reconstruction and rejected
substitutions are indexed by `evidence/core-observations/qualification.json`.
