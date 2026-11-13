# Plan a word operation before constructing its result

This project prototype forecasts existing word primitives from declared widths.
It does not extend the selected SDK, admit a managed graph, read model
coordinates or reserve a complete request budget. Those integrations follow a
qualified standalone planner and a separate SDK source batch.

The common shape follows the existing integer/rational planners: explicit
profile and limits, exact input reference, ready/incomplete decision, prospective
result and intermediate sizes, policy work charge, and a precise refusal metric.
Wrong arity, widths, operation data and result sorts are malformed. A known
well-formed operation over budget stays incomplete. Unknown operations stay
unsupported rather than becoming a guessed arithmetic rule.

No powers of two, masks, word values, native solver calls or callbacks are
constructed by the planner. Width metadata can therefore refuse a billion-bit
multiplication without allocating a billion-bit integer. Wrapped results have
separate intermediate rules: multiplication and an unsaturated left shift can
need twice the operand width; wrapping itself constructs the next power of two.
The charges are a resource-policy convention, not a BEAM time or allocation
bound. The separately pinned Lean word-envelope model covers mathematical
arithmetic bounds only; it does not establish this implementation's correctness.

Before integration, compare every current primitive against actual SDK point
semantics, qualify exact policy boundaries and malformed controls, then add
coordinate normalization admission and aggregate request reservation. Keep the
existing general evaluator and bounded numeric profile contracts unchanged.
