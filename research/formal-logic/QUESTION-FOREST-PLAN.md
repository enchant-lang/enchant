# Prepare the question, not just its formulas

The project module and focused/corpus recipes now exist; qualification is
pending. They prepare a term inventory. Structured observation reconstruction
and managed owner admission remain separate work.

The next project boundary should accept the original closed question-graph
wrapper and derive a fresh term inventory without expanding argument trees.
Keep the original complete graph/reference authoritative. A prepared object
is diagnostic data and must never be accepted as an already checked question.

## Preserve the existing meaning explicitly

Read version, mode, assertions, claim, counterexample, observations and vacuity
from graph rows. Assertion labels must retain their actual strings. SAT has
neither claim nor counterexample. Proof mode requires a Boolean claim and a
counterexample that is exactly its negation under the existing term relation.
Comparing node IDs alone is insufficient: list/vector argument aliases remain
equal under the SDK's generic sequential equality. Compare the freshly checked
typed syntax with a bounded memo of node pairs, including operation, sort,
explicit data and ordered children. Keep exact graph identity separate.

Collect observation leaves using the current `formal.value/terms` rules:
terms stop traversal; formal values contribute payload leaves plus definedness
and model-admission terms; ordinary maps contribute their values; vectors and
lists contribute ordered elements; other leaves contribute no terms. Preserve
the existing BL map iteration order where it affects the current exported
inventory, and sort outer observation labels with the same identity bytes as
`formal.query/roots`. Label/key materialization is an explicit bounded cost.

Do not rebuild a term's arguments to collect this inventory. Memoize descriptor
subgraphs and deduplicate their collected term references at each step, so a
repeated container cannot make the inventory itself grow exponentially. Gather
the needed labels/keys once, materialize them in one selected decode, then
prepare the complete ordered term forest once.

The derived result should contain original graph references, ordered native
definitions, assertion and counterexample root IDs, observation descriptor
graph references, and selected observation term IDs. It is not an operational
question view or a model witness. Unrelated provenance and unused observation
metadata remain in the original graph rather than being decoded for admission.
The consequences of newly accepting unmaterialized observation leaves need an
explicit versioned observation profile before managed reply promotion.

## Review observations before producing answers

The current SDK collects term leaves inside lists but `resolve-payload` only
reconstructs maps/vectors. A list can therefore be admitted as an observation
and then retain unresolved terms. A bare container can also contribute terms
to validation while the observation decoder still expects a lifted formal
value. These are language design issues to settle centrally, with shared
negative/positive cases, rather than silently repairing one backend path.

Prefer a closed observation grammar: a typed scalar or explicit formal value
with a portable payload template, domain, definedness and admission predicates.
Support maps, vectors and lists consistently, retain false/nil/presence and
exact scalar kinds, and define what a set or unfamiliar keyword means as
display data. Domain-specific decoding must use the original graph template;
a private sort descriptor or placeholder cannot become a checked witness.

## Qualification and promotion

Compare complete ordered definitions/root IDs for all 187 existing questions,
plus labels, SAT/proof mode, vacuity and structured observation leaf inventories.
Exercise independently encoded but generically equal claim aliases, forged
counterexamples, unused metadata, shared descriptor expansion and malformed
success/admission terms. Keep unsupported native outcomes unchanged.

Only then promote preparation, evaluation and the reviewed observation grammar
as one SDK batch. Inside the actual owner turn, revalidate the original graph,
retain assumptions and revisions, allocate owner-local IDs, and preserve
portable-context accounting. Check replies/explicit points against the original
question and rebuild observations from that original graph. Qualify effects,
durable records and fresh-process readers on the exact new SDK. None of these
compatibility checks supplies typed-forest soundness, evaluator equivalence or
compiler preservation automatically.
