# Unbounded loop arguments from ordinary BL source

The loop interface uses real compiler ANF and the finite Int/Bool core. It does
not extend the core's structural evaluator with unchecked recursion. One closed
definition supplies the source loop, input types, precondition, invariant,
integer ranking vector and result condition.

```clojure
(ns count-example (:require [formal.api :as formal] [formal.term :as t]))

(def count-up
 (formal/loop-contract
  {:name "count-up" :parameters {"n" t/Int}
   :source "(loop [i n acc 0] (if (> i 0) (recur (- i 1) (+ acc 1)) acc))"
   :requires (fn [in] (t/ge (get in "n") (t/int 0)))
   :invariant (fn [in state]
                (t/all [(t/ge (get state "i") (t/int 0))
                        (t/eq (t/add (get state "i") (get state "acc")) (get in "n"))]))
   :rank (fn [in state] [(get state "i")])
   :ensures (fn [in state result] (t/eq result (get in "n")))}))

(formal/verify-loop count-up)
(formal/verify-loop {:backend :z3} count-up)
(formal/verify-loop {:backend :oxiz} count-up)
```

The argument is symbolic for every admitted nonnegative integer `n`; it has no
iteration bound. State sorts come from typed initializers. Input parameters stay
immutable. State names come from the pinned compiler's fresh variable names,
with duplicate aliases refused. Lexical binding is canonical, so recompilation
does not change the definition identity.

The first profile checks normal return and permits no external effects. It
generates named obligations for normal initialization, the initial invariant,
nonnegative ranks, each reachable condition/binding/prefix, normal recurrence
arguments, invariant preservation, strict rank decrease and exit results.
Recurrence updates state simultaneously after evaluating arguments left to right.

One rank decreases in the natural-number order. Two ranks decrease
lexicographically: an outer counter can decrease while an inner counter resets
upward. Invariants keep both ranks nonnegative. The separate Lean model checks
the natural and lexicographic rules and their nonnegative integer versions.
It also defines an unbounded evaluator from a total controller and that
well-founded relation, and checks the propagation of exit postconditions.
The current integer-rule proofs expose `propext`, `Classical.choice` and
`Quot.sound` in their axiom audits; returned rule metadata retains these names.
The earlier eighteen model theorems retain their empty axiom dependency lists.

Every successful aggregate proof carries a certificate for each exact obligation.
`formal/check-loop-proof` reconstructs all obligations and checks the object
without either solver. An unreachable path can instead carry a checked proof
that its assumptions are inconsistent, even when its unused result is outside
the arithmetic fragment. Input inconsistency is reported separately as vacuity.
An author `^{:decreasing ...}` assertion is never a substitute for these checks.

## Prove normal return of the exact Core controller

`formal/core-loop-question` builds one portable term question from the same
loop contract. It describes the exact finite initializer and one execution of
the body. The question checks successful initialization and establishment of the
invariant. On a state satisfying the precondition and invariant, it checks that
the controller returns normally, both ranks are nonnegative, a recurrence
preserves admission and decreases the rank, and an exit meets the postcondition.

```clojure
(def question (:problem (formal/core-loop-question count-up)))
(def certificate (:certificate (formal/certify question)))
(def exported (formal/core-loop-data count-up certificate))
(formal/check-core-loop-data count-up certificate (:packet exported))
```

The packet contains the original closed loop control, the exact finite Core
programs and the original predicates. The external checker reconstructs the
initializer and controller from the contained control. It checks both finite
Core outcome theorems and the complete term entailment in Lean. It then checks
that the question matches those programs and predicates after slot alignment.
The Lean substitution theorem connects the symbolic next-state terms to the
values returned by the Core controller. The result slot refers to the actual
return value in the exit state's postcondition.

The final theorem exhibits a successful initialization, a finite sequence of
controller steps, and a normal return satisfying the postcondition at the
exit state, for every admitted input. The proof uses well-founded recursion on
states satisfying the invariant and has no fixed iteration bound. A rank with
one component is padded with zero in the second position. Finite control with
zero ranks uses a pair of zeros. The applied reports record the standard Lean
axiom policy, including the dependency on `Classical.choice` in the integer
ranking proof.

Export the packet as JSON with `interop/->json` and use the pinned checker.

```sh
research/formal-logic/check-core-loop \
  research/formal-logic/evidence/core-loops/examples/countdown.json \
  --output /tmp/enchant-core-loop
```

The whole-controller question uses the current partial Int/Bool proof
fragment. For example, a division by zero in an unreachable return payload can
exceed that fragment. The separate path checker can establish that branch's
unreachability. The exact whole-controller runner also accepts a qualified case
where the unreachable division is evaluated in a strict prefix and its value
is discarded.

## What a failed argument means

`obligation-refuted` identifies a countermodel to a proposed invariant, rank or
other proof obligation. That state can be unreachable in the actual execution.
A loop that only starts at zero can return immediately even if a proposed
invariant also admits an abstract state at two that fails preservation. The
interface retains this distinction and does not call the program nonterminating.

The concrete reference executor is separately bounded by iteration and step
ceilings. Exhaustion reports incomplete work. A bounded successful run or an
unfinished run does not establish termination or nontermination for all inputs.
The retained example execution is explicitly a raw model run, with its exact
input and whether the contract precondition holds recorded beside it. Contract
verification does not silently wrap the source program with runtime admission.

## Remaining trust

The composed proof covers the contained Core control, its typed model and the
exact question. The named-data codec and the connection from Source and compiler
ANF to that control remain reviewed. The BL reference executor and BEAM
preservation still need their own correspondence evidence. Nested loops,
general recursion, further value domains and effectful bodies require
additional semantics and proof rules.
