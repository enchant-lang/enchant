# Programs that carry their stated promises

`formal/program-contract` elaborates a reviewed BL expression, or accepts an
explicit core tree, then builds a closed data definition. Verification derives
the question from that definition afresh. The first profile is the specified
scalar/record core; it does not admit arbitrary BL functions or host effects.
The initial scalar path below is extended by real function source, ordered
record parameters and concrete core counterexample replay in
[RECORD-HANDLERS.md](RECORD-HANDLERS.md).

```clojure
(ns accounts (:require [formal.api :as formal] [formal.term :as t]))

(def withdraw
 (formal/program-contract
  {:name "withdraw"
   :parameters {"balance" t/Int "amount" t/Int}
   :source "(- balance amount)"
   :requires (fn [in]
               (t/all [(t/ge (get in "balance") (t/int 0))
                       (t/ge (get in "amount") (t/int 0))
                       (t/le (get in "amount") (get in "balance"))]))
   :ensures (fn [in result] (t/ge result (t/int 0)))
   :returns :must
   :effects #{}}))

(formal/verify-contract withdraw)                  ; independent certificate
(formal/verify-contract {:backend :z3} withdraw)    ; plus native observations
(formal/verify-contract {:backend :oxiz} withdraw)  ; identical definition
```

Builders receive ordinary typed terms. They run during construction and are
absent from the stored definition. Their own implementations are not verified.
Predicates cannot introduce undeclared input identities, uninterpreted functions,
foreign sorts or hidden host behavior. The body, predicates, policy, source,
profile and input declarations participate in the definition identity. A changed
definition cannot reuse an embedded cached question or stale identity.

`returns :must` requires successful return and the postcondition. With
`returns :may`, `effects #{:raise}` and `raises #{:some-error}`, a returned value
must meet the postcondition and a raised result must name a permitted error.
An empty effect set forbids raising even if a broader error list was supplied.
The current core's only modeled effect is explicit failure; actor, state and
foreign effects need separate extensions.

Verification produces a certificate for the conditional property when the
current proof fragment can express it. It also searches independently for a
certificate that the assumptions are inconsistent. If that succeeds, the result
is `vacuous`, with the inconsistency proof retained. Failure to prove inconsistency
does not establish feasibility. An optional native backend separately supplies
a feasibility witness and counterexamples, checked by independent replay.

`checked` means a checked conditional core-term contract. `uncertified` means
the solver proved a question outside the independent checker fragment. A valid
counterexample is `refuted`; an opposing solver/certificate result is a visible
`disagreement`. None of these statuses silently becomes compiler authority.
The source and symbolic interpretation remain reviewed, unmechanized code.
Source preparation now also requires an independently checked ANF/Core pair:
`:elaboration {:status :checked ...}` records that relation separately from the
conditional term proof. The common evidence envelope exposes it under
`:evidence/:connection/:elaboration`. A Core-only authored contract reports
`:not-applicable` there. The relation checker does not regenerate a Core or
call a solver; Source expansion and selected-unit specialization are earlier,
still-unproved bridges. See [ELABORATION.md](ELABORATION.md) for the exact rules
and the distinct mathematical model preservation theorem.

## Displaying a counterexample

Inputs, returned value, return status and error code are separate observations.
OxiZ can expose concrete inputs while leaving a compound arithmetic observation
opaque. The shared result layer can calculate supported scalar observations
from the assignments. Each term records backend versus independent replay
provenance and retains its native availability/reason. Assertion validation is
unchanged and does not trust these display fallbacks.

Fallback is limited to Bool, Int, rational Real, codepoint String, BV and enum
observations that the independent evaluator can compute. It does not fabricate
floating-point NaN payloads or opaque array/function values. Backend model
availability, witness validation, certificate checking and compiler authority
remain separate fields.

## Remaining boundary

Finite core syntax has a structural termination argument with explicit raised
outcomes. This is not yet a termination system for recursive source functions.
Nor is the current source-to-ANF-to-core path mechanically verified. Next steps
are checked recursive summaries and ranking obligations, effect/trace contracts,
translation validation and mechanically checked foundation metatheory.
