# Run the original function behind a contract

The research API can now observe one real call to a selected Source function.
The normal SDK producer emits the **original linked unit**, its actual Source
instance owner initializes it, and the owner invokes the exact selected export.
The specializer's derived ANF is not emitted as a substitute.

```clojure
(def observed
 (formal/observe-contract promise {"balance" 10 "amount" 3}))

(formal/check-contract-observation promise (:receipt observed))

;; Optional, explicit execution of a native counterexample, after full replay:
(formal/observe-contract-counterexample
 promise (get-in native-answer [:backend :property]))
```

`promise` is an existing `formal/program-contract` backed by a
`formal/selected-source-context`. Preconditions must hold for the exact typed
assignment. The counterexample adapter first replays the complete native term
question and concrete core contract, then observes that exact completed input.
Altered profiles, another contract's model or incomplete replay cannot trigger
execution. A solver's answer does not itself authorize a call.

The observer is an explicit framework operation with effects. Ordinary contract
checking still runs no selected runtime initializer or export. All public
inputs, receipts and results are BL data. Functions, PIDs, graph objects,
Env handles, monitors and leases stay inside the observing operation.

## Preserve the actual Source program

The capture adapter writes bounded exact Source bytes to its own temporary
input files. Original source names remain coordinates, even when they contain
absolute paths or `..`; those names are never filesystem destinations. It
constructs the closed capture manifest as BL data. It does not print or evaluate
a manifest expression or synthesize binding tables.

The SDK's `compile.world/prepare-captured` rechecks the input bytes and owns
Source selection, expansion, phase analysis and lexical linkage. The adapter
requires the original unit's canonical identity and selected export reference
to match the formal context. `prepare-unit` and `AOT/compile_unit` emit the
normal Source-guarded factory ABI and its phase companion. The receipt retains
both members' hashes, code MD5s, metadata identity, original unit identity and
target reference. Temporary byte inputs are then removed.

Execution uses `reload.execution/prepare-captured-unit!`,
`initialize-instance!`, `complete-preparation!` and
`invoke-instance-binding!`. The actual private preparation owns admission and
the Source graph. No metadata label, proof flag, Env imitation or manually
installed runtime floor substitutes for that path. The phase companion is not
loaded to invoke the runtime export.

## Initialize once, call once, retire

One monitored worker prepares one actual Source instance in a private parent
Env. Initialization and the export call have separate capture boundaries.
Failure in framework preparation or completion is an adapter failure, not a
fabricated language error. The exact input assignment determines argument order.
Returns must inhabit the core's declared scalar or nested-record result sort.

After its observation the worker asks the normal owner to retire its graph.
The parent confirms the worker's monitor, closes the private parent to fence
new admissions, and drains its actual contextual preparations through the SDK.
Conforming evidence requires no live worker, no pending preparation, the closed
parent and unloaded runtime and phase modules. A public `:retired` flag alone
does not establish cleanup.

The contract still covers **initializing this unit, then one call**. An unused
initializer that raises prevents the export from running. Contracts on an
already initialized instance remain a separate future scope.

The default worker budget is 10 seconds, capped at 30 seconds. Zero reports
incomplete before execution. The budget covers instance preparation through
the worker's observation/retirement reply; compiler/byte preflight and parent
cleanup have the outer command's resource ceiling. Timeout or process death
does not become a named language exception or an assumed safe retry. Unexpected
errors after worker entry conservatively report execution as unknown.

## Error cause and error ownership are different facts

Profile: `:bl/selected-contract-observation-v1`. Adapter:
`:initialize-source-instance-and-call-once-v1`. Error projection:
`:bl/source-instance-integer-error-projection-v1`.

The first actual call-error check showed that Source tail calls can erase the
application frame from the raw stack. It still contained `erlang:div(7, 0)` and
the real owner invocation, but no private application module. Requiring that
debug frame would classify this real zero-divisor as incomplete.

This profile therefore records its **original Source-owner invocation
boundary** separately: context, original artifact, selected target and whether
the caught operation was initialization or export invocation. Checking
reconstructs those identities and their stage relation. The raw cause must
still be an `ArithmeticError`, kind `:error`, with first frame `erlang/div` or
`erlang/rem`, integer dividend and zero divisor. A class, message or boundary
label alone is insufficient. Missing or different causes remain unclassified.

`error-stack-bound-to-artifact` remains an honest diagnostic and may be false.
`failure-origin` explicitly names the recorded Source-instance boundary. These
are observer reports, not cryptographic execution attestations. The older
source-handler receipt profiles retain their separate stack-binding requirement;
this change does not weaken their checker.

The runtime snapshot is captured after actual instance preparation and before
initialization, so SDK loading performed by the owner precedes the recorded
fingerprints. Its stage is explicit; incomplete attempts may retain only the
earlier preflight snapshot. Fingerprints remain scoped provenance rather than
a proof of the transitive runtime or native leaf implementations.

## Check the record without running the function

`check-contract-observation` freshly reconstructs the contract, typed input,
precondition and concrete core outcome. It emits the original Source unit to
bytes under the bounded private module name and compares every artifact field.
It starts no Source instance and invokes no recorded initializer or export.
Compilation may perform the SDK's bounded expansion-phase semantics.

| Result | Meaning |
| --- | --- |
| `:conforming` | This complete recorded return or classified error matches the reconstructed core, with confirmed recorded cleanup. |
| `:disagreement` | A complete recorded result differs from that core. |
| `:incomplete` | Timeout, process death or an unclassified cause prevents the comparison. |
| `:rejected` | Invalid identities, input, artifact, boundary, stage or cleanup data. |

`contract-safety` independently reports `:holds` or `:violated` for a conforming
observation. A faithful execution of a bug is conforming and violates its
promise. This is a finite observation, not universal program correctness.

The source specializer, symbolic interpreter, checker and compiler remain
reviewed implementations. Universal specialization preservation, implementation
soundness, transitive native runtime closure and full actor/scheduler semantics
are not established. Compiler proof authority remains false.

## Qualification

The first direct probe returned 42 through the normal Source owner and retired
its graph/module without an adopted runtime floor. The focused runtime file
then passed 130 assertions, including original private helper captures,
imported hygienic macros, records, signed arithmetic, initialization/call
failures, tail-call frame loss, altered receipt data and both engines' replay
gates. The failed initial stack-bound projection is retained with its actual
raw cause and missing module frame.

`selected-runtime-check.bl` records examples as bounded, hash-pinned trusted
project ETF, with diagnostic JSON. `selected-runtime-recheck.bl -- DIRECTORY`
checks those records in a fresh VM. Its trace calibrates actual Source
initialization, export invocation and module publication on an unrelated
synthetic program before the checking window. The window then requires zero
initializers, zero exports and zero application-module loads.

Evidence lives in `evidence/selected-runtime/`. This uses the same immutable SDK
pin, changes no production compiler default and adds no Lean theorem.
