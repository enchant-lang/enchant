# Next interface: explicit points and exact runtime observations

This is a design for the next implementation batch, not an implemented API.
It follows the binary64 qualification in `FLOAT-SOURCE.md`.

The paired Float examples expose a useful capability: BL should be able to
check a caller-supplied original input even when a backend cannot return it.
That point must never be described as a recovered native model coordinate.

## Keep three operations separate

1. Build an exact `formal.query` from the selected semantics. Source preparation
   may compile phase code; it is not an effect-free or sandboxed operation.
2. Construct and independently check a sealed mathematical point against that
   complete query. Check the original assertions and, for a proof question,
   its original counterexample condition. Reopening and checking this packet
   should require neither a solver nor fresh Source compilation.
3. Optionally observe the selected Source function at that point. Freshly
   prepare the stored Source, compare the actual question, bind declared
   runtime inputs, run its ANF, check returned kind/bits or raisedness, and
   retire emitted artifacts. Keep this observation separate from a universal
   Source-preservation theorem.

A combined result can retain a native unknown answer and a checked explicit
counterexample at once. Its verdict basis should name the explicit point;
the native answer and its model availability must remain unchanged.

## Do not extend the wrong metatheory

`formal.witness` has a deliberately restricted Int/Bool data model, including
its completion convention and separate metatheory receipts. Adding FP, Real,
arrays or sequences to that packet would misstate those premises. A new point
profile should name the independent data evaluator and its explicit limits.
Unsupported operations or missing coordinates must remain incomplete.

Mathematical FP NaN has one semantic value. Its representative data encoding
must not become an observed IEEE payload. Source Float inputs are finite, so
runtime materialization should refuse NaN and infinity. A future semantic NaN
data constructor needs its own reviewed protocol, rather than guessed bits.

## Preserve runtime distinctions

Audit `formal.runtime-values/matches?` for every scalar kind. Numeric `=` is
not enough to establish that a returned Int and a returned Float have the same
runtime kind: `int?`, `float?` and strict equality can distinguish them. Keep
BL numeric equality separate from returned-value correspondence.

Likewise, cross-kind Source equivalence should return a structured outcome,
not leak a sort-construction exception. Both raisedness and successful value
kind matter. Unreviewed mixed branches remain unsupported.

## Add a real Float generator

Introduce `float-of` separately from historical `real-of`: the latter also
admits integer sample endpoints, so mapping it silently to Float would change
its domain. A Float interval should use finite binary64 endpoints and numeric
closed bounds, admitting both signed zeros whenever zero is included.

Use ordered integer bit keys for enumeration, sampling and shrinking; host
Float interpolation can overflow and numeric deduplication loses signed zero.
Expose the finite cardinality separately from whether enumeration is within
budget. The historical `:infinite` enumeration sentinel must not be presented
as a theorem that a binary64 interval is mathematically infinite.

An explicit finite enumeration engine could check every declared point, while
an explicit sampling engine establishes only its observed examples. Neither
should rewrite the native engine's answer or silently complete its model.

## Further Source cutover

The known-Float legacy guard is not complete process typing. Unknown state
fields, helper effects, Decimal semantics and other legacy printer consumers
still need explicit admission or typed migration. The next process adapter
should consume selected compiler ANF and declared runtime domains, rather than
inherit an implicit Int fallback. Compiler and delivery authority stay false
until their own correspondence obligations are implemented and qualified.
