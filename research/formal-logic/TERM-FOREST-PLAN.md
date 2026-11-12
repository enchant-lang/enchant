# Keep typed terms shared through native preparation

The current question graph preserves the whole question, but its operational
view rebuilds ordinary typed terms. `formal.term/export` then walks those terms
again to produce the shared native node table. Both workers already accept
that table. A first prototype can replace preparation without changing the
worker protocol, native arenas or managed query authority.

## A small boundary with a concrete comparison

The research prototype accepts one checked public data graph and an ordered
vector of roots that must denote canonical typed terms. It follows term
argument references directly. It decodes the operation, sort and literal/data
fields in one batch. Argument traversal keeps graph references; explicit data
payloads can themselves be structured and still require bounded materialization.

Each local node is checked using the existing term constructors with privately
derived child-sort descriptors. These descriptors are internal to the operation;
no caller's cached view or claimed checked result is accepted. The term map
still has exactly its five canonical fields. Literal normalization, primitive
arity and operand sorts retain the selected SDK's current rules.
Its constructor comparison treats lists and vectors as one ordered value
family. Both portable argument representations are admitted; the full graph
reference still distinguishes their original containers. Canonical input
representation, generic BL equality and exact evidence identity are therefore
separate relations, not interchangeable validation tests.

Scope checking is separate. Its memo key is `(graph node ID, binder environment)`.
A reused bound node can be valid under one environment and invalid under another.
The current nominal-binder rule rejects escapes, duplicate identities, nested
shadowing and wrong sorts. Free-variable names must keep one sort across the
whole requested forest. Explicit capacities bound nodes and scope states;
crossing them refuses preparation rather than establishing a solver result.

The output contains the complete input graph reference, ordered source roots,
fresh portable node definitions, translated root IDs and checking statistics.
Those IDs belong to this prepared table. They are neither native arena handles
nor proof objects, and this output is not an accepted substitute for the
original question at the query/evidence boundary.

For ordinary examples, compare the complete definitions and roots with
`formal.term/export` from a fresh registry. Include every existing primitive
family, repeated roots, sharing, labels and quantifiers. A graph-built expansion
example should prepare without materializing its argument tree. Negative
controls must cover malformed fields, canonical literals, conflicting variable
sorts and shared bound nodes reached in different environments.

## Native exercise before managed admission

Use a fresh borrower-owned session and the existing raw compatibility transport
to exercise the produced table on Z3 and OxiZ. That transport deliberately
invalidates managed portable-context accounting. Record that distinction rather
than presenting this experiment as a managed graph query or checked execution.
Keep existing solver and hard deadlines, native identity and artifact checks.

Promotion is a later coherent SDK batch. Managed admission must revalidate the
original graph inside its actual owner turn, allocate IDs in that owner's
registry, and preserve revision checks and retained assumptions. The common
question/effect/reply/ledger interface should continue to accept the original
question. Independently replaying answers still needs its own graph-native
consumer; faster preparation alone does not remove that materialization cost.

## Semantic choices to review explicitly

The first compiler follows the pinned term grammar so both paths are comparable.
Before promotion, review ignored primitive `data`, sort/constructor naming and
text admission rather than accidentally giving the two validators different
languages. Review the current fresh nominal-binder requirement as a language
design choice: a lexical BL frontend can generate stable binding identities
while preserving authored names for readers. It must not derive identity from
per-VM counters or conflate a display name with binding authority.

Numeric equality, collection keys, literal sequencing and their versioned
profiles remain the separate preview decisions in
[SEMANTIC-REVIEW-KEYS.md](SEMANTIC-REVIEW-KEYS.md). This preparation prototype
does not silently settle those decisions. Its next mathematical obligation is
typed-forest interpretation and scope preservation, beyond the already checked
structural [selection law](GRAPH-SELECTION-MODEL.md).
