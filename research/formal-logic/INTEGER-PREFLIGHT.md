# Forecast integer growth before computing a result

`formal.integer-preflight/plan` is the first executable piece of the derived-value
policy. It takes an operation keyword, a vector of existing integer operands,
and limit overrides. It returns ordinary BL data; neither backend is involved.
It is committed for focused qualification, not connected to the evaluator yet.

```clojure
(integer-preflight/plan :mul [65536 65536]
  {:integer-bits 32 :intermediate-bits 64 :work-units 1024})
;; :status :incomplete, :reason {:kind :resource-limit ...}
;; :primitive-execution :not-run
```

The limits cover magnitude bits in inputs/results, temporary integer bits, and
an explicit bit-size charging convention called work units. Zero has zero
magnitude bits. Addition/subtraction allow a carry bit; multiplication allows
the sum of operand widths. Euclidean division allows its negative-quotient
adjustment. Modulus also forecasts the SDK's internal product and subtraction.
Integer comparisons forecast the temporary products used by the SDK's common
numeric comparator. Unknown operations remain incomplete.

The planner derives widths from the actual operands. It never accepts a supplied
width table. Its request reference binds the exact operation, ordered operands,
profile and normalized limits. Changing a limit or swapping ordered operands
changes that reference, even when the mathematical result would be the same.

`ready` means only that this primitive's forecasts fit this resource policy.
It is not a computed value, logical verdict, termination proof or execution
capability. A caller can alter a returned map; no evaluator accepts that map as
authority. Work units are not measured CPU instructions, heap bytes, or a proven
upper bound on BEAM runtime. Process memory/time caps remain necessary.

## How the common evaluator should consume it

The actual evaluator must call the planner afresh at the point where an admitted
operation is about to run. It should retain request counters privately and
charge a memoized node once. Exported counts are diagnostics, not accepted
caller state. The operation must belong to the same process/owner turn; a saved
callback or stale revision cannot spend another operation's capacity.

The complete result should bind three subjects: the original question graph,
the original assignment data, and normalized resource settings. A resource
refusal stays an incomplete evaluation with its metric, required amount and
limit. It must not become false, UNSAT, a program exception, or an original
counterexample. Assertion replay and display reconstruction need distinct
completion statuses so a partially reconstructed display cannot certify a point.

Demand is part of this integration. An untaken branch remains syntactically
admitted but spends no concrete evaluation budget. Merely forecasting both
branches eagerly would lose the current language behavior. Unknown operations
must not fall through to an unmetered primitive inside a strict resource profile.

## The rest of the gate remains open

This module covers integer primitive forecasts only. It does not meter the
whole expression, cumulative work, rational cross-products and normalization,
text/sequence expansion, nested portable values, array updates, or floating-point
formats. Format limits must apply before expensive SDK sort/value admission as
well as before arithmetic. Graph size alone does not cover those costs.

The focused controls compare forecasts with independent SDK results over signed
small operands and sparse large operands, including the actual Euclidean-mod
intermediates. Separate small growth probes compute a 65,537-bit integer,
65,536-byte text and 4,096-element sequence from shared input. These checks are
queued; no qualification or mechanical cost-model correspondence is claimed yet.

Implementation: [planner](src/formal/integer-preflight.bl),
[focused controls](test/integer_preflight_test.bl),
[actual growth probes](value-growth-probe.bl),
and [the complete resource plan](TERM-FOREST-RESOURCE-PLAN.md).
