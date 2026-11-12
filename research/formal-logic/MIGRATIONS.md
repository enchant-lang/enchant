# Term-based message migration previews

`formal.migration` describes a message transformation as immutable Beam Lisp
data. It separates three questions: can the old message be admitted, does the
transformation preserve the declared promise, and is there an admitted input
that breaks it? Both backends receive the same reconstructed questions.

The first profile uses up to eight ordered Bool/Int parameters and one message
role. It covers exact scalar results. It refuses mixed Real/Float semantics,
bounded or abstract value domains, and undeclared input identities.

```clojure
(ns message-preview
 (:require [formal.migration :as migration] [formal.term :as t] [formal.value :as v]))

(def increment
 (migration/define
  {:name "message-increment"
   :parameters [["message" t/Int]] :message "message"
   :source-function '(fn [x] (+ x 1))
   :admit-before (fn [in] (t/ge (get in "message") (t/int 0)))
   :admit-after (fn [_ result] (t/ge (v/term result) (t/int 0)))}))

(migration/verify {:admission {"message" 0}} increment)
(migration/verify {:backend :z3 :admission {"message" 0}} increment)
(migration/verify {:backend :oxiz :admission {"message" 0}} increment)
```

`define` runs builders once and stores the resulting semantic values, never the
builders. `:transform` is an alternative to `:source-function`; it receives the
parameter map and produces a term or semantic value. Its implementation is
not the proved subject. A stored Source function goes through the actual
compiler ANF, is lowered afresh at preparation, and must reproduce the stored
transformation. Source elaboration can execute phase code; it is not a sandbox.

For `:preserves-admission`, the old and new admission predicates are separate.
A new message contract may differ from the old one. Admitted inputs satisfy
`:requires` and the normal true old predicate. The claim requires the transform
to complete normally and the new predicate to complete normally with true.
A division by zero or an undefined new predicate is a failing claim, never an
extra assumption that removes the offending input.

`:relation :equivalent` instead requires equality of raisedness and successful
message values. The old message is an already supplied input value, so this
also requires normal completion of its transformation. Admission predicates
are refused in that mode rather than silently discarded. This relation does
not compare exact error identities or arbitrary effects.

| Result | `verified` | Evidence |
| --- | --- | --- |
| `checked`, with admitted input | `true` | Fresh conditional certificate and independently checked admission packet |
| `checked`, admission not established | `nil` | Conditional certificate only |
| `refuted` | `false` | Independently checked original counterexample packet |
| `uncertified` | `nil` | Native proof claim without a checked portable certificate |
| `vacuous` | `nil` | Inconsistent admission, with its evidence retained |
| `unknown`, `unsupported`, disagreement | `nil` | Limits or disagreement remain explicit |

The proof and admission are independent. A tiny theorem budget can leave a
native proved answer uncertified. A proof under contradictory premises never
makes `verified` true. Invalid requested points are retained in
`:requested-points`; they do not count as admitted or refuting evidence.
The returned common `formal.result` envelope retains the conditional claim,
certificate, assumptions, feasibility, source connection and native diagnostics.

`prepare` exposes `:problem`, `:admission`, `:counterexample` and `:inconsistency`.
`check-proof`, `check-admission` and `check-counterexample` reconstruct their
subjects and check saved objects without invoking their own native fallback or
proof search. If a definition stores a Source function, reconstruction also
re-elaborates it; that preparation may run phase code. These are not sandboxed,
side-effect-free checkers for arbitrary Source macros. The retained ledger
rechecking experiment covers two authored term definitions and one stored
intrinsic Source function on each backend. It counts the managed query method
only in its explicitly named checking window; this is no guarantee about
arbitrary Source macro effects.
`point` constructs evidence from an explicit complete role/value map. It keeps
Bool false and never invents a missing native coordinate. Witness packets prove
existence in the declared term model; their data semantics bridge is reviewed,
not a newly executed external theorem prover.

`replay-source` executes the stored Source function on a supplied admitted point
through the SDK compiler and exact binary lease. It compares normal completion
and returned values against independent term evaluation. It retires the emitted
module before returning. Publication/compilation errors remain observer errors.
This is one observed invocation; it does not establish universal compiler
preservation, termination of arbitrary functions, or exact exception identity.

The research facade adds `message-migration`, `check-migration-proof`,
`check-migration-admission`, `check-migration-counterexample` and
`replay-migration-source`. The same subject works with `formal.api/check`,
`compare` and `describe`. The obligation-bundle interface does not yet include
migration definitions; its advertised subject list stays separate.

`reload.migrate/verify-migration` has a new two-argument form taking options and
a closed definition, or a migration spec carrying `:formal-model`. It does not
invoke or certify a spec's unrelated `:fn`. Its historical three-argument path
is explicitly labelled `:legacy-smt`, retains unchecked certificate status and
is also accessible as `verify-migration-legacy`. Existing source invariant
discovery remains in that compatibility path. It has not been silently
relabelled as typed Source extraction.

Every new result has `:compiler-proof-authority false` and
`:delivery-authority false`. This is a logical preview. Actual mailbox custody,
dispatch coverage, live generation coherence and transport remain separate
obligations owned by reload and process evolution.

Qualification evidence is retained under `evidence/migrations`. The first
candidate passed 103 assertions and errored on two Source cases: composed
semantic values carried a closed `(and true true)` admission, while the new
interface expected a literal true. The correction independently evaluates
closed Boolean admission with no assignments. A false or unresolved bound is
still refused. The failed run and exact candidate are retained; qualification
requires a later complete pass.

The second candidate passed all 156 assertions across the new migration file
and both legacy files. A subsequent review exposed a conditional Source
case: both result branches have unconditional bounds, but the bound expression
contains the input-dependent test. That candidate is retained with the failing
conditional baseline. The next correction reduces equal branch bounds only
when the test uses total Bool/Int operations. A partial division or unresolved
function test cannot be erased by that rule. Partial branch *results* remain
allowed, and the concrete inactive-error example checks lazy definedness.

The third candidate introduced a constructor regression in that bound walker:
it sent literal Boolean nodes through the compound-operation constructor.
The retained run records an incoherent migration test module and one errored
conditional case. Literal leaves now retain their original validated nodes.
Only the subsequently qualified SDK is eligible for selection.

The first durable-reader attempt passed a raw native answer to the bound-handler
reply checker and was refused. Inspection confirmed that the complete saved
question matched. The reader now compares those exact canonical bytes first,
then explicitly binds the raw answer before replay. The failure is retained
under `ledger-before-binding`; it was a consumer error, not a backend failure.
The rebound answer is a rechecked record, not a newly executed native result.

Checked model truth takes precedence over unchecked backend claims. For example,
a checked conditional certificate and a valid admitted point still establish
the declared model promise if a handler falsely reports that admission is
UNSAT. That untrusted absence remains visible under `:backend`; it cannot erase
the independently checked point. `:disagreement` concerns contradictory checked
objects. Native-only vacuity remains a reported result with `verified nil`.
