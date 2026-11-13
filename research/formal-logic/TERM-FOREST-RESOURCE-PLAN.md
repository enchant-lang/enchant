# Bound derived values as well as graph traversal

Before managed promotion, give point evaluation an explicit derived-value
resource policy shared with the ordinary evaluator. Node/depth bounds alone
do not bound exact arithmetic or concrete container expansion.

A small graph can repeatedly square its previous integer. Its term table grows
by one node per step, but the result's bit length doubles. Repeated sequence or
text concatenation has a similar shape. Sharing makes these good, compact
representation fixtures; it does not make their concrete results small.

First retain small, capped examples that measure the actual bit/length growth.
Then define per-value and per-request limits with units: integer bits, rational
component bits, text code points/bytes, sequence elements, array updates and
expanded portable value nodes. Forecast expensive operations before allocating
their result. A post-computation encoding limit arrives too late.

Use operation-specific conservative bounds. Integer multiplication needs at
most the sum of its operands' bit lengths; addition/subtraction needs at most
one extra bit over their maximum. Rational rules must account for cross
products before normalization. Concatenation adds element or byte counts.
Propagate metrics alongside memoized values rather than repeatedly walking
expanded results. Review FP format/exponent limits separately from payload
width and include compound element/domain costs.

A budget refusal is an incomplete evaluation with an explicit resource reason,
not false, UNSAT or a counterexample. Demand still matters: an inactive branch
must not consume evaluation capacity, although its syntax remains admitted.
Record configured limits and the charged counts in evidence. Keep successful
small-case compatibility checks and add just-below/above-limit controls that
refuse before expensive work. Do not advertise universal evaluator termination
or cost bounds until the implementation and its cost model have their own
correspondence argument.

The first [integer primitive planner](INTEGER-PREFLIGHT.md) now passes 10,248
focused assertions, alongside three capped concrete growth probes. It returns
term-based forecasts without running the primitive. It is not integrated with
the graph evaluator, and does not cover the whole gate. Cumulative accounting,
other value families and a cost-model correspondence remain open.

The current project checks run under whole-process memory and time caps. Its
graph evaluator has admission/node bounds but no general derived-value preflight
policy yet.

## The first integration boundary

Start with an explicit Bool/Int resource profile and retain the current preview
profile as a separate interface. Unsupported policies must return incomplete
work rather than fall through to an unmetered primitive. Constructor admission
and concrete evaluation need separate accounting: an untaken branch is still
typed, but does not spend its concrete evaluation capacity.

Share primitive application with the ordinary evaluator instead of maintaining
two arithmetic implementations. The actual owner derives forecasts from its
admitted node and real child values, reserves capacity, then invokes the SDK
primitive. A caller's ready plan or exported counter map is never authorization.
Scoped lookup functions need a same-process guard before they carry accounting;
they already retire after the operation returns or fails.

A per-value refusal is not automatically a failed whole expression. Preserve
the SDK's three-valued demand rules: an incomplete child followed by false can
still determine a conjunction; true can determine a disjunction. A refused
expensive operation does not spend work that it never performed. Report root
completion, resource refusals and charged work separately. Bind the original
question, point assignments and normalized settings in distinct references;
none of those diagnostics grants a solver verdict or compiler authority.
