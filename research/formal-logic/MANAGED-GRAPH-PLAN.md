# Put graph execution in the actual solver owner

The shared SDK evaluator supplies fresh typed admission and privately metered
numeric point evaluation. Its graph IDs are portable data. They do not grant
permission to use a native solver, certify a native answer or identify a live
arena. This document specifies the next implementation boundary; it is not a
qualification receipt or a claim that managed graph replay is delivered.

## Reuse the owner, change what it admits

`formal.backend/native-owner` already retains the actual port, term registry,
named assumptions, generation and context revision. `managed-exchange` checks
the captured context in the same owner turn as a scope exchange. A successful
load commits assumptions; reset clears them and advances the revision. Raw
transport makes portable accounting unavailable. Keep these rules.

Today `formal.logic/solve-graph-in` opens an original graph but passes a
materialized operational view to `solve-native-in`. `prepare-owned` then uses
`formal.term/export`, whose registry keys are term trees. The graph reference
is bound at the language boundary, but the native owner has not itself admitted
the original question graph. The scoped SDK point evaluator is also separate
from native assertion replay.

Introduce an explicit graph operation on the existing owner. Keep the legacy
tree registry and APIs readable and qualified. The new operation accepts only:

```clojure
{:question original-closed-question-graph
 :settings closed-normalized-graph-settings
 :context captured-live-owner-guard}
```

The context guard contains the live owner/generation/revision and remains
ephemeral. Every other input is ordinary portable data. Reject supplied forests,
node translations, model-validation booleans, observer templates and counters.
The owner derives those views during the operation. A backend choice changes
the adapter and artifact identity, not the mathematical question.

## One transaction, with separate identities

1. Check borrower, owner liveness, portable context and exact revision before
   doing native work. Normalize closed settings inside the owner; an exported
   settings map or digest alone is not evidence of prior normalization.
2. Compose the owner's actual retained assumptions into the original graph.
   Preserve the existing label convention, domain/profile joins and complete
   public context. Do not trust a client mirror to add or erase assumptions.
3. Freshly derive the question inventory and typed graph forest from that
   effective original graph. Include claim, exact negated counterexample,
   assertions, semantic predicates and observation roots. Unrelated public
   fields remain part of exact question binding without being materialized.
4. Translate the locally admitted graph definitions into owner-local native
   definitions. Maintain an explicit mapping from source IDs to arena IDs;
   neither number is interpreted as the other. Intern definitions using their
   operator, sort, admitted data and translated children. Do not key the new
   registry by expanded term trees or by a digest without an equality check.
5. Run the existing feasibility preflight when required, then the query scope,
   at the existing solver and hard deadlines. Scoped assertions remain
   temporary. Commit native registry additions only under the actual protocol's
   successful exchange rules; retire on failed transport as today.
6. For SAT, validate original variable coordinates and replay the actual scoped
   assertions through the SDK point operation. Include retained assumptions and
   the counterexample, rather than checking only displayed observations.
7. Decode display observations separately, preserving definedness, presence,
   constructor selection, length, unavailable fields and original descriptor
   graphs. A backend observation or display fallback cannot repair failed or
   incomplete assertion replay.
8. Return an explicit versioned result bound to the complete effective question,
   normalized settings, evaluation policy and actual backend artifact. Recheck
   the captured context before exposing the fallback result to the caller.

Keep these references distinct: the caller's original question, the effective
question including retained assumptions, settings, point assignment and ordered
evaluation request. Native scope identifiers belong only to the owning process.
The same graph under different resource settings has the same mathematical
identity and a different execution identity.

## Start with an explicit numeric fragment

The first managed graph profile should opt into Bool/Int/Real admission and
the SDK's direct numeric policy. It can then reserve rational literal work
before constructors run and arithmetic work before concrete primitives run.
An out-of-fragment sort is a request refusal before native execution. A valid
operator whose point interpretation is unavailable can still yield incomplete
replay; do not classify it as an invalid term or a false assertion.

Keep the current general graph path explicitly available. Structural node
bounds alone do not bound concrete value growth. Widen the managed profile
only as text/sequence lengths, array updates, FP formats and compound-value
expansion acquire actual preflight rules and private request accounting.

Replay needs three outcomes, independent of the backend's status:

| Replay | Meaning for a SAT reply |
| --- | --- |
| Valid | All actual assertions evaluate to true at checked coordinates. |
| Invalid | At least one actual assertion evaluates to false. |
| Incomplete | Some assertion is unavailable or refused within policy and no false assertion establishes invalidity. |

Preserve the individual refusal reasons and completion states. Incomplete
replay leaves SAT as a candidate; it does not become a refutation or checked
witness. Native UNSAT remains an unchecked solver claim. Resource completion
does not establish a universal cost theorem, totality or compiler preservation.

## Qualification that exercises this boundary

Use the existing immutable SDK candidate gates as the arithmetic baseline.
Batch the owner/inventory/translation/replay changes into one subsequent SDK.
Qualify actual owner turns, not a caller-only simulation:

- Retain an assumption, corrupt/restore the client mirror, and ensure it still
  appears in the exact effective graph and assertion replay.
- Change/reset the real context before fallback; refuse the stale request
  before a counted native check. Preserve retirement and borrower cleanup.
- Supply altered/rehashed graphs, forged prepared views, malformed settings
  and another owner's guard. Observe the actual refusal boundary.
- Exercise a highly shared graph that fits the new term table and exceeds the
  earlier expanded path. Check source/native ID separation and bounded import.
- Count real normalizer and primitive calls at admission and evaluation
  refusals. A caller's ready forecast must never authorize execution.
- Exercise SAT with valid, false, absent and ill-sorted coordinates; missing
  backend observations; decisive Boolean demand; retained assumptions; and
  counterexamples. Keep replay separate from display reconstruction.
- Compare all preceding common-theory questions on both backends at unchanged
  solver deadlines, retaining unsupported/unknown outcomes and exact artifact
  identities. Reopen portable records in fresh SDK-only consumers without a
  native query, and qualify the actual dossier separately.

The [native ownership contract](NATIVE-CONTEXTS.md),
[graph consumer contract](GRAPH-CONSUMERS.md),
[structured observation rules](GRAPH-OBSERVATIONS.md) and
[shared SDK boundary](SHARED-PRIMITIVES.md) remain the implementation anchors.
