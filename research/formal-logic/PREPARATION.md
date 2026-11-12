# A checked plan between a question and its execution

Checkpoint 39 is qualified on the selected immutable SDK: 299
new focused assertions, 1,307 preceding focused assertions and
8,106 regression assertions passed. All 187 preceding paired
questions retain their identities and native verdicts. SDK-only use and a
fresh-process ledger recheck passed. [Exact qualification](evidence/query-preparation/qualification.json).

Beam Lisp should own the meaning of a formal question and make useful
representations available to either engine. The observed compiler-size cases
show why: distributing a ground integer coefficient lets OxiZ settle questions
that its original native execution leaves unknown. A backend's response to one
term shape should not determine the language's mathematical interface.

The plan has three ordinary data pieces: the original complete question, the
complete execution question, and evidence connecting their actual term sites.
Its identity covers all three. A normalizer proposes the execution question;
an independent checker reconstructs the connection from those questions.

The API keeps these pieces separate:

```beam-lisp
(ns checked-size
 (:require [formal.affine :as affine] [formal.preparation :as preparation] [system.linear :as linear]))
(def original-question (linear/size-lemma 12 2 8))
(def plan (affine/prepare original-question))
(preparation/check plan)
(preparation/execute {:backend :z3} plan)
(preparation/execute {:backend :oxiz} plan)
;; A pure receiver checks an already returned execution answer:
(preparation/accept plan execution-answer)
```

`prepare` is an untrusted producer. A plan's stored status is diagnostic;
`check`, `execute` and `accept` reconstruct the connection afresh. Both engines
initially receive the same execution question from the same plan. Backend
settings, native provenance and any later alternative plan remain visible data.

The first normalization fragment is explicit Bool and affine Int terms,
with plain typed observations. Each changed assertion, claim and observation
needs an unconditional equality certificate. Assertion order, labels, origins,
scope, profiles, context and arbitrary other question metadata stay identical.
The counterexample is derived afresh from the execution claim. Unsupported
observations, nonlinear operations, capacity exhaustion and failed certificate
search must refuse preparation rather than silently drop a condition.

Unchanged sites can use exact structural identity. A proposed certificate's
stored checking label cannot establish the connection: the checker rebuilds its
equality question and checks the proof object. It rejects missing, duplicated,
foreign and extra sites, changed observation labels, modified metadata and a
certificate for a merely similar term. Checked means equivalence under the
existing certificate fragment and implementation trust boundary.

Execution is a separate effect. The implementation owns a fresh session and
send the execution question through the ordinary complete-query handler. It
must verify the returned question before any transport. A borrowed live
context is separate work: rewriting a query cannot silently rewrite assertions
already retained by a native engine.

A transported SAT model must independently satisfy every original assertion
and the original counterexample goal. Original observations are reconstructed
from those assignments, with unavailable coordinates kept unavailable. Retain
the native answer, its execution question and replay, alongside this separate
original-question replay. A decoded response still goes through the actual
published-point boundary introduced in checkpoint 38.

The public answer belongs to the original question. Its separate execution
record retains the actual execution question and native answer. Reconstructing
original observations can reuse the independent answer decoder; copying native
decoded values or validation labels would bypass the transport check. If
normalization removes a variable that the original replay still needs, missing
assignments remain an incomplete model. No default coordinate is invented.

The first candidate's lost-coordinate test exposed an important reporting
distinction. Native `:model-status` describes access to the execution backend's
model API; it is not original-coordinate completeness. The receiver now marks
that basis explicitly and separately records `:original-replay`: assertion
validation, typed binding availability and observation availability. This also
keeps an unavailable original value distinct from a concrete constant observed
after simplification. The selected SDK passes the corrected reporting checks.

UNSAT and vacuity may travel across a checked equivalence connection, but remain
native claims with unchecked absence certificates. An equivalence certificate
does not become a proof of the theorem being queried. Unknown, unsupported,
error, incomplete models and explicit budgets keep their distinct meanings.

The first migrated compiler consumer is `system.linear`: a declared constructor
size recurrence, a portable positive certificate, a replayed constructed
double-placement counterexample, and optional paired native executions. Native
uncertainty must not invalidate an independently checked arithmetic object, or
grant compiler authority. Bounded overhead, recursive placement and the
connection to actual compiler emission remain visible premises.


`system.linear` also separates theorem search from preparation search. Its
primary `:status` retains checked, refuted, unknown, unsupported and error.
`:holds` is true after fresh positive checking, false after a checked original
counterexample, and nil when truth was not established. Duplicated-child
negative controls retain their own status. An unchecked native positive label
cannot fill a missing portable certificate.
