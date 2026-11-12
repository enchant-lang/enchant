# Evaluate shared terms without rebuilding their argument trees

The project evaluator takes the original public data graph, ordered term-root
references and a portable assignment map. It freshly checks the graph and typed
forest, then evaluates demanded nodes with a per-operation memo. A caller's
prepared map is refused. Explicit sort/data components and model coordinates
still require bounded materialization; the argument traversal keeps references.

The [qualification](evidence/term-forest-evaluation/qualification.json) records
92 focused assertions and all 187 preceding questions at four deterministic
point maps each: absent, zero, alternate and ill-sorted coordinates. All 6,300
root values agree exactly with the selected SDK evaluator, including 1,484
incomplete values. These points are compatibility fixtures, not exhaustive
semantics or solver-generated model certificates.

The shared example has 45 saved data nodes and 131,071 term occurrences.
Requesting the root twice yields `[true true]` while evaluating just 17 typed
nodes. No native engine or managed query is invoked. This example also powers
the new executable dossier cell.

## Preserve demand and the meaning of incomplete values

`if`, `and` and `or` retain the SDK's demand rules. An unused branch is still
admitted by the typed checker, but is not evaluated. Conjunction and disjunction
preserve the last incomplete value unless a decisive Boolean appears.
Implication evaluates both operands, as the SDK does today. False is cached as
a real result; absence, nil, ill-sorted coordinates and explicit incomplete
values remain distinguishable.

Other local primitives reuse the SDK evaluator through private shallow terms
whose child values have already been computed. Their temporary child names do
not refer to caller variable names or introduce new atoms. The constructor
checker and primitive evaluator remain reviewed implementation dependencies.
Quantifiers and uninterpreted mathematics retain their existing incomplete
behavior; this work does not add a quantified interpretation.

## The useful improvement and its cost

Across the 748 point maps, graph evaluation totals 66,462 ms, including fresh
graph admission and typed preparation for each point. The old evaluator totals
410 ms on already materialized terms. Initial graph conversion is outside both
figures. This is a serial compatibility run with unequal preparation costs,
not a solver-speed or matched end-to-end benchmark. Small inputs pay more.

The demonstrated capability is bounded evaluation of highly shared, graph-built
input. Complete-question preparation, structured observation reconstruction,
managed owner admission and reply/point/ledger integration remain separate
steps. The evaluator is a project preview on SDK 44, outside that immutable SDK
and its managed graph-query path. No native model certificate, mechanized
evaluator-equivalence theorem or compiler authority is granted.

Implementation: [evaluator](src/formal/term-forest-evaluate.bl),
[focused controls](test/term_forest_evaluate_test.bl),
[187-question point comparison](term-forest-evaluation-check.bl) and
[actual sharing example](src/formal/term-forest-evaluation-examples.bl).
