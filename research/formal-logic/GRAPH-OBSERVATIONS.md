# Reconstruct useful observations from the original graph

The new project `formal.graph-observations/reconstruct` takes the original
question-graph wrapper and a portable point-assignment map. It derives the
question inventory afresh, admits the complete typed forest, and shares one
memoized evaluator across the term roots actually demanded by observations.
Its output is display reconstruction. Assertion replay is explicitly
`:not-run`; no native query or compiler proof authority is granted.

The [complete code qualification](evidence/observation-semantics/qualification.json)
passes 9,964 targeted assertions, all 187 exact inventories, all preceding paired
native outcomes and two fresh SDK-only durable readers. The project pin now
selects this exact immutable SDK. The live presentation is qualified separately.

The observation comparison covers 748 deterministic point maps: 1,176 exact
observation values and 6,300 exact root values match the SDK, without managed
queries in that reconstruction window. Its approximately 14-minute run is
compatibility evidence, not a speed comparison.

## The common semantic repairs

Query admission now type-checks the actual counterexample as part of the whole
forest. Generic equality still accepts the reviewed list/vector argument
aliases, but cannot substitute for local term typing. An Int datum `1.0` that
compares equal to Int `1` is refused before execution.

Explicit semantic values now reconstruct list payloads as lists, including
nested values, nil, false and empty lists. Composite equality traverses ordered
list/vector payloads according to the current BL sequence-value relation.
Choosing between two list branches preserves a list result. Top-level
observations must be typed terms or explicit semantic values; `v/make` supplies
the latter. This admits the format the decoder consumes and refuses ambiguous
bare containers before native execution.

These changes repair concrete gaps in the existing common interface. They do
not establish a complete observation-domain grammar or settle every language
semantic distinction.

## What remains shared and what is materialized

The interpreter follows term argument references. Operation/sort/data admission
still uses the typed forest's explicit bounded component decoding. Display
values use the selected SDK's observation rules, including its IEEE NaN
availability policy. A cached per-root display result avoids repeating this
work across fields.

The descriptor projector uses private placeholders to reuse the common SDK
domain decoder. Each placeholder carries an operation-local BEAM reference;
caller data cannot supply it through the portable graph. The placeholders are
neither checked terms nor exported witnesses. The decoder consumes them inside
one admitted operation. Its source-root lookup and diagnostic functions retire
after the consumer returns or throws.

Domain, scope and needed map-key data are materialized explicitly under the
existing-keyword policy. Payload values stay deferred until their definedness,
presence, constructor or length selects them. An inactive option item or
undefined payload can therefore remain unread even when it contains an
unfamiliar keyword. The original complete question reference still binds it.

For an active field that cannot materialize, reconstruction returns an explicit
`:formal/observation-refused` record containing its reason and original
descriptor graph. Malformed template shapes receive a separate admission
reason. A refusal is neither a concrete value nor a negative logical verdict.
The complete question reference stays on the reconstruction result.

## The next architectural connections

The scoped point operation is internal implementation plumbing; the public
question, assignments and resulting evidence remain terms. It does not expose
native arena handles or accept a prepared table as input authority. Managed
promotion must revalidate the original graph inside its actual owner turn and
preserve retained assumptions, revisions and owner-local IDs.

Before that promotion, add [derived-value preflight budgets](TERM-FOREST-RESOURCE-PLAN.md)
and connect original assertion replay. A finite, shared expression can produce
a very large concrete integer or collection. Per-node memoization and the
whole-process caps used for qualification do not supply that general bound.
Domain/scope/key materialization also remains an explicit cost; this is not a
universal O(unique nodes) or speed claim.

The implementation is a project preview, outside the SDK's managed reply path.
Its compatibility checks do not establish a decoder/evaluator soundness theorem,
a native certificate or compiler preservation.

Implementation: [graph observer](src/formal/graph-observations.bl),
[scoped point interpreter](src/formal/term-forest-evaluate.bl),
[focused observer checks](test/graph_observations_test.bl) and
[point-map comparison](graph-observations-check.bl).
