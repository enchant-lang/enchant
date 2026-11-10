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

The checked mathematical ranking rule does not prove that the BL ANF reader,
control extraction, integer term interpretation, obligation generator or
reference executor implements that rule correctly. Their composition remains
reviewed implementation backed by focused checks. Compiler/runtime admission is
disabled. In the first profile, nested loops, general recursive functions, other
value domains and effectful bodies are explicitly outside the recognized source
fragment; they require further interfaces and evidence.
