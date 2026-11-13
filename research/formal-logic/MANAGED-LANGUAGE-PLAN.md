# From the owner primitive to one language request

Design record for the common request interface now implemented in candidate
SDK4. Read [REQUEST-INTERFACE.md](REQUEST-INTERFACE.md) for the actual API and
the [progress receipt](evidence/managed-graph/progress.json) for completed
qualification gates. The retained-session extension, full structured display
and wider resource families below remain open. Older answer/effect/ledger
formats remain readable under their own declarations.

The concrete surface is `formal.logic/prepare-request`, `request-from-graph`,
`execute-request`, `compare-request`, `answer-request`, `recheck-request` and
`with-request-handler`. The dedicated `formal.request-record` interface writes
and reopens the existing ledger's typed request payload. No owner handle,
admitted forest or caller verdict enters a request. Application observation
keys, point data and diagnostic data remain original graphs.

## Keep three kinds of identity

The mathematical subject is an original closed `formal/question-graph`.
Semantic choices, assumptions and bounds that change the proposition belong
in that subject. A solver deadline or an arithmetic work allowance belongs
in execution policy. Display preferences belong in neither.

The language request should be one portable term, with an explicit version,
containing that subject, a normalized replay policy, and requested adapter
settings (backend and native deadlines). Its reference binds all three.
The subject reference stays unchanged when only execution policy changes.
The result records the actual owner artifact and actual native limits
separately from what the request asked for. A pure reader cannot establish
that the recorded artifact executed anything.

A live session is a separate argument to the local bridge. Owner PIDs, port
handles, callbacks, admitted forests and native node IDs never enter request
or evidence data. Existing `backend/graph-question!` is the primitive behind
this bridge; it already derives admission and imports inside the owner.

Original sketch, retained to show the intended separation (actual names above):

```clojure
(request subject {:policy numeric-policy
                  :adapter {:backend :oxiz :solver-ms 500 :hard-ms 2000}})
(execute request)                 ; acquire/retire a local owner
(execute-in session request)      ; check actual owner against adapter settings
(compare request [:z3 :oxiz])     ; change adapter, preserve subject/policy
(recheck saved-evidence)          ; fresh pure admission and point replay
```

The concrete namespace and record tags should be chosen together with the
existing `formal.logic`, `formal.answer` and `oracle` APIs. Avoid another
permanent public family of nearly identical functions merely to bridge the
preview formats. Keep old records readable under their declared formats.

## One pure replay function, shared by effects and readers

Extract the SDK-only reader's fresh original-graph point checking into a
reusable implementation. It must take the original effective subject,
normalized policy and coordinates; it must not accept a prepared forest,
source-to-native map, cached checking result or ready work plan.

Use the locally captured admission to check assertion-variable bindings,
then actual assertions and the counterexample, then observation roots.
Preserve invalid encoding, false assertion, missing coordinate and resource
refusal as distinct diagnostics. A decisive assertion may tolerate an
irrelevant missing coordinate; an invalid supplied coordinate or a refused
binding check retains its existing effect on validation.

Record original request and effective subject separately. Retained assumptions
come from actual owner state during execution. On reopening, their graph is
part of the recorded conditional mathematical subject, not proof of actual
native context or execution. Validate composition where the record provides
its original graph and retained-assertion graph; never infer custody from a
recorded generation, revision or digest.

Native observations remain labelled raw data. They cannot repair assertion
replay. Full structured decoding should consume original descriptor graphs
and checked point operations, with explicit expansion/value budgets. Until
that is implemented, preserve deferred materialization in the public result.

## Effects delegate requests, not authority

Introduce an explicit request method at the existing formal effect boundary.
An installed handler receives the complete portable request and a local
fallback. It can return recorded or supplied coordinates, deny the request,
or delegate. A handler missing this method must refuse explicitly; do not
coerce older script/query methods into the new request format.

Recheck every supplied response against the exact request and effective
subject. Keep fallback provenance in a lexical variable held by the caller.
Only exact binding to the actual fallback's returned data can retain that
local provenance. Copied execution booleans or artifact descriptors cannot
establish it. Recheck the actual owner guard after fallback return.

A valid independently replayed point can be useful without any native
execution. A saved UNSAT/UNKNOWN/unsupported response remains a reported
native claim unless its own evidence is checked. Neither kind of response
acquires compiler or totality authority.

## Store data once; reopen under declared formats

Reuse the existing content-addressed graph store and durable ledger envelope.
Store original subject, effective subject, request policy and answer body as
separate referenced data where appropriate. Preserve their exact references;
indexes and exported summaries are navigation aids. On reopening, validate
all referenced graph bodies and bind them afresh before interpreting them.

The reader must work from a fresh selected SDK with no research import path,
no native session, no source-payload execution and a denied oracle. Preserve
all original kinds, float bits and byte payloads. A future change to default
collection equality must not rewrite an older evidence graph's identity.

## Qualification before replacing the preview route

Use actual handlers and both native owners, including retained assumptions,
stale guards, changed revisions, raw transport, abandonment and cleanup.
Compare the same complete question/policy on both engines. Keep unsupported
sorts and unavailable concrete interpretations visible rather than reducing
the comparison to successful cases.

Add fresh-process and tamper controls for original/effective/request binding,
retained-context composition, policy and actual limits, artifact labels,
coordinate encoding, rehashed false points, and copied delegation claims.
Calibrate actual no-query/no-exchange counters with separate positive controls.
Reopen the resulting ledger records independently before exposing the new
route as the common language interface. Wider resource families, semantic
review, mechanized implementation connections and compiler/totality work
remain subsequent parts of the active goal.
