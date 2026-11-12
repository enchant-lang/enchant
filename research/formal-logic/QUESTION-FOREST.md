# Prepare a question's terms without expanding their argument trees

The project `formal.question-forest/prepare` takes the original closed question
graph and derives its complete ordered term inventory. It reads assertion
labels, proof/SAT mode, claim/counterexample agreement, observation leaves and
vacuity policy. Its output contains fresh native definitions and root IDs,
beside the original complete graph reference. It is derived data, not an
accepted cached question or a managed execution.

The [qualification](evidence/question-forest/qualification.json) passes 68
focused assertions and all 187 preceding questions. Every question keeps the
same exact native definitions, ordered roots, assertion labels, normalized
claim/counterexample IDs, observation term inventory, mode and vacuity as the
selected SDK path. No native engine or managed query is invoked.

## Keep syntax and data identity separate

A counterexample must be the claim's negation. Checking only graph node IDs
would reject the SDK's accepted list/vector argument aliases. The prototype
compares freshly checked typed syntax with a bounded memo of node pairs,
including operations, sorts, explicit data and ordered children. It preserves
the exact original graph reference separately.

Term roots stop observation traversal before argument trees. Ordinary maps
retain the existing BL value-iteration order; outer observation labels use the
same identity-byte order as the SDK. Descriptor memoization deduplicates each
subgraph's term references. A graph-built observation with 16 doubled container
layers needs 17 descriptor states and one term definition, rather than a
repeated term inventory. Labels and map keys still need bounded materialization.

## Admission is not observation reconstruction

Unrelated metadata and uninterpreted observation leaves remain original graph
data. A focused example leaves an unfamiliar observation keyword unmaterialized,
while the ordinary operational projection refuses to decode it. The new result
has no operational `:view` and is not a decoded witness. A versioned observation
policy is needed before promoting that distinction into managed replies.

The focused controls also confirm two existing issues to review centrally:

* The query validator compares a counterexample with the negated claim using
  generic equality, but omits it from its own typed-root walk. A forged Int
  datum `1.0` can pass that comparison against Int `1`. Both the actual existing
  exporter and the new inventory refuse it when checking their complete roots.
  This is an admission distinction, not an accepted ill-typed native execution.
* Observation collection visits lists, while the existing decoder reconstructs
  only maps/vectors. Bare containers can likewise contribute terms without
  being directly decodable as lifted formal values. Review a closed, consistent
  observation grammar instead of silently changing one representation path.

## What remains before promotion

Prepare structured observation templates and graph-native point/reply checking
against the original question. Revalidate inside the actual owner turn, retain
assumptions and revisions, allocate owner-local IDs, and preserve portable
context accounting. Add [derived-value resource accounting](TERM-FOREST-RESOURCE-PLAN.md)
before treating bounded graph traversal as bounded concrete evaluation.

This remains a project preview on SDK 44. The default managed interface retains
its qualified operational view. These compatibility checks do not establish a
complete question-interpretation theorem, native certificate or compiler proof.
See the [architecture and semantic review](QUESTION-FOREST-PLAN.md),
[implementation](src/formal/question-forest.bl),
[focused controls](test/question_forest_test.bl) and
[whole-corpus comparison](question-forest-check.bl).
