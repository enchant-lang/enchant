# Checked changes to a core program

`formal.translation` compares two typed scalar/record core programs. Its observation
relation includes whether evaluation returns or raises, the successful value,
and the exact named error. This is a pure core: external effects, actor traces
and arbitrary calls require richer relations before they can pass this gate.

The subject is closed BL data. It contains both programs, their parameter sorts,
one explicit precondition and the semantic profile. Bound local names are
canonical. `prepare` rebuilds the symbolic comparison; it accepts no cached
question supplied by an optimizer. The certificate statement also contains the
translation identity and both core identities. Even a different pair that
happens to lower to an identical arithmetic claim needs its own evidence.

This compares two Core data programs and therefore reports
`:source-connection :authored-core-no-source-claim`. A separate
`:model-interpretation` record identifies both Core programs and the exact
prepared equivalence question. The interpretation remains reviewed,
unmechanized implementation code even when the resulting term certificate is
checked. An earlier Source extraction, a later compiler lowering and actual
runtime preservation each need their own connection. [CONNECTIONS.md](CONNECTIONS.md)
defines the common assurance fields.

```clojure
(def change
 (formal/translation
  {:name "add-zero" :parameters {"x" t/Int}
   :before (core/operation :add [(core/variable "x" t/Int) (core/literal 0)])
   :after (core/variable "x" t/Int)}))
(def answer (formal/verify-translation change))
(formal/check-translation-proof change (get-in answer [:proof :object]))
```

The default path produces a portable proof and checks it independently, without
a native solver. Adding `{:backend :z3}` or `{:backend :oxiz}` searches for input
feasibility and counterexamples too. Native UNSAT alone is `uncertified`, never
an accepted translation. Contradictory inputs are `vacuous`. Both remain
distinct from a checked conditional comparison with unknown input feasibility.

The common facade also accepts this subject through `(formal/check change)`,
`(formal/check {:backend :oxiz} change)`, `(formal/compare change)` and
`(formal/describe change)`. The same functions accept term queries, program
contracts and loop contracts. Original result fields remain available; the
additional `:evidence` map keeps the claim, certificate, assumption ledger,
feasibility, source connection, native observations and authority separate.
Z3 is a comparison reference engine, and the comparison explicitly has no
compiler proof authority. Native UNSAT and portable checked evidence are
different fields even when both backends agree.

Native counterexamples get two checks: independent term replay, then concrete
execution of both core programs. OxiZ sometimes leaves unused inputs opaque.
The second check can complete an absent Bool with false or an absent Int with
zero, explicitly marking that value `explicit-replay-completion`. It then
rechecks every assumption and the counterexample claim with the completed
assignment before running either program. These chosen values never appear as
native observations. A completion that cannot be validated stays a candidate;
it cannot establish a refutation or open the optimizer gate.

## A real candidate optimizer

`formal/optimize-core` walks a core program and proposes constant folding,
literal-branch selection, arithmetic identities, redundant literal sequencing,
returning a local binding and Boolean double negation. It records each rewrite
and asks the independent translation boundary to check the whole resulting
program. Only a `checked` comparison returns the candidate as `output`. An
unsupported, unknown, vacuous, uncertified or refuted comparison retains the
original program. An unchanged program needs no translation certificate.

Error preservation constrains the rewrites. Multiplying an expression by zero
becomes a sequence that evaluates the expression before returning zero. Equal
conditional branches still evaluate the condition. Eager Boolean operations
retain failing operands. An optimizer's arithmetic intuition cannot erase an
observable failure.

The result carries its explicit precondition. A caller may use a conditional
rewrite only where that precondition is established. The current built-in
rewrites need no extra assumptions; a supplied false precondition yields a
vacuous comparison and cannot admit them.

## Versioned checking rules

The original `bl/boolean-linear-integer-v1` normalizer remains available for
saved certificates. `bl/boolean-piecewise-linear-integer-v2` adds case analysis
for integer conditionals, including choices nested inside linear arithmetic.
The current `bl/piecewise-ground-integer-v3` also simplifies known logical
guards and checks ground Euclidean division/modulus with a nonzero divisor.
It never assigns a meaning to division by zero. A logically irrelevant value
need not be interpreted after its guard is proved false during normalization.

General nonlinear multiplication and variable division remain outside this
certificate system. Search remains incomplete and resource bounded. No new
arithmetic oracle is trusted: the checker recomputes the normalization and every
weighted contradiction. All historical rule versions keep their normalization
and atom ordering so previously produced certificates can be checked again.

## What this establishes

This is an executable optimization gate for **core models**, built as a research
library on the pinned SDK. It can consume core extracted from the actual BL
compiler ANF. Its source/core/symbolic correspondence and its certificate
checker implementation are reviewed and tested, not mechanically proved. It
does not emit optimized BEAM, modify the production compiler, or grant compiler
proof authority. Connecting those implementations to the mathematical model
and installing a qualified compiler pass remain explicit integration work.
