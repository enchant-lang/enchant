# Checked state models and replayable protocol traces

`formal/protocol` closes pure model builders into ordinary BL data. Its first
profile has named Bool/Int state fields, a predicate describing admitted initial
states, named invariants, and a finite vector of transition variants. Every
variant declares input sorts, an optional guard, explicit environment
assumptions and simultaneous state updates. Builders disappear after producing
the descriptors. State and input names are strings; an injective component
encoding keeps punctuated names distinct.

```clojure
(def counter
 (formal/protocol
  {:name "counter" :state {"value" t/Int}
   :init (fn [s] (t/eq (get s "value") (t/int 0)))
   :invariant (fn [s] (t/ge (get s "value") (t/int 0)))
   :transitions
   [{:name "add" :inputs {"amount" t/Int}
     :assumptions (fn [s in] [(t/ge (get in "amount") (t/int 0))])
     :next (fn [s in] {"value" (t/add (get s "value") (get in "amount"))})}]}))
(formal/check {:initial-state {"value" 0}} counter)
(formal/compare counter)
(formal/replay-protocol-trace counter {"value" 0}
 [{:transition "add" :inputs {"amount" 3}}])
```

The common `check`, `compare` and `describe` functions accept this subject.
`check` produces and checks portable certificates with no native solver by
default. Supplying `:backend :z3` or `:backend :oxiz` also asks for initial-state
feasibility and countermodels to the induction obligations. `:initial-state`
supplies a concrete candidate witness for independent replay; it does not add
an assumption or narrow the set of admitted initial states.

## What an induction argument covers

The checking boundary reconstructs the underlying `formal.transition` machine
and every induction obligation from the closed definition. It refuses cached
models, derived success flags and supplied questions. It validates all field
sorts, free identities, value descriptors, transition coverage and the exact
model identity. Certificates are bound to that identity and their individual
obligation scopes. Removing a transition's proof, reordering rows or reusing
another subject's certificate fails checking.

The base obligation establishes the invariant for every admitted initial
state. Each transition obligation establishes both normal evaluation of its
attempt and preservation of the invariant, under the invariant, enabled attempt
and that transition's declared environment assumptions. An explicit
inconsistency certificate can mark an unreachable case. Initial feasibility
remains a separate result: an empty initial domain is vacuous, and a proof
without a feasibility witness remains conditional.

The mathematical induction rule covers every finite prefix of the declared
model, without a trace-depth limit. The separate Lean model proves invariant
preservation on reachable states, exclusion of failed attempts there, and the
invariant at every position of a permitted trace. The correspondence between
those theorems and the BL generator/checker remains reviewed implementation.
The compiled model, printed axiom audits and qualified sources are retained
under `evidence/protocol/`; older model receipts remain historical snapshots.

An obligation countermodel can use an invariant state that no execution ever
reaches. Its status is `obligation-refuted`, rather than a claimed execution
counterexample or proof that the program is unsafe. A solver-only proof is
`uncertified`. Neither grants compiler authority.

## Concrete model execution

`protocol-step` and `replay-protocol-trace` use an independent term evaluator.
A false guard disables a transition. An undefined guard is a failed attempt.
An undefined update also fails, with the previous state retained; partial
updates never commit. All successful updates read the same old state. A trace
can include explicit `{:stutter true}` events. After a failed attempt only
stuttering is permitted, so later steps cannot erase the recorded failure.

Every event must satisfy the declared input schema and environment assumptions.
An assumption violation is outside the modeled environment, not an invented
language exception. A disabled transition cannot occur as an executed event.
Initial-state admission and invariants are replayed too. A valid finite trace
reports whether the invariant and normal-step safety held along that trace.
An evaluator's unavailable result stays incomplete. It never becomes a guessed
value or language failure.

This profile accepts exact scalar descriptors with explicit definedness. It
refuses hidden representation constraints and nontrivial model-capacity flags,
which could otherwise remove a failing attempt from the searched domain.
Bounded collections need their own explicit representation and admission
obligations. Limits are sixteen fields, inputs, invariant names and transition
variants, with 1,024 distinct terms per scalar descriptor. Explicit replay
accepts up to 64 events. Those implementation limits do not bound the induction
argument's trace length.

## The boundary to real actors

This is an authored state model, not a live BEAM actor verification result. The
updates and guards are semantic descriptors; they are not automatically
extracted from a handler's implementation. Failure observations currently
distinguish guard/update failure and the failed field, rather than proving an
actual source exception's name or source evaluation order.

There is no mailbox, delivery scheduler, external effect or liveness theorem in
this first profile. A terminating handler, a service that keeps responding and
a process that eventually finishes are different promises. Live actor work
must connect send/receive observations, message ordering, selective receive,
crashes and fairness assumptions to source behavior. Safety proofs require no
fairness assumption here: they quantify over every permitted transition. An
eventual-delivery or response claim would require its own stated assumptions.
