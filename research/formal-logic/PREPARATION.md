# A checked plan between a question and its execution

Design for the next implementation checkpoint. The normalization probe is
executable; the general plan interface described here is not implemented yet.

Beam Lisp should own the meaning of a formal question and make useful
representations available to either engine. The observed compiler-size cases
show why: distributing a ground integer coefficient lets OxiZ settle questions
that its original native execution leaves unknown. A backend's response to one
term shape should not determine the language's mathematical interface.

The plan has three ordinary data pieces: the original complete question, the
complete execution question, and evidence connecting their actual term sites.
Its identity covers all three. A normalizer proposes the execution question;
an independent checker reconstructs the connection from those questions.

The first supported fragment should be explicit Bool and affine Int terms,
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

Execution is a separate effect. Initially it should own a fresh session and
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

UNSAT and vacuity may travel across a checked equivalence connection, but remain
native claims with unchecked absence certificates. An equivalence certificate
does not become a proof of the theorem being queried. Unknown, unsupported,
error, incomplete models and explicit budgets keep their distinct meanings.

The first production consumer can be `system.linear`: a declared constructor
size recurrence, a portable positive certificate, a replayed constructed
double-placement counterexample, and optional paired native executions. Native
uncertainty must not invalidate an independently checked arithmetic object, or
grant compiler authority. Bounded overhead, recursive placement and the
connection to actual compiler emission remain visible premises.
