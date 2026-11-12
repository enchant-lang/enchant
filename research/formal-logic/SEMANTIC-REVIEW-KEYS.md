# Preview review: equality, key identity and evaluation order

Review items exposed by checkpoint 43. These are not installed language
changes or a new authority profile.

## Numeric equality is not automatically key identity

The two fresh readers on the selected SDK record cardinality two for both
`(set [1 1.0])` and `(set [0.0 -0.0])`, and for the corresponding two-key maps.
The executed dossier example additionally compares numeric equality with the
runtime's strict relation. These observations belong to this pinned BL/OTP
runtime; they are not inferred from older Erlang releases.

A formal language needs to name the relation used by each operation. Numeric
comparison, exact portable data identity, runtime observation equivalence and
map/set key identity need not all coincide. But a membership or substitution
law must use its declared relation consistently.

Three language choices merit an explicit decision:

* Keep numeric `=` and specify a distinct structural key identity. Make the
  relation available to formal collection interfaces and explain which
  familiar equality/substitution laws require it.
* Make collection keys follow numeric equality. Audit heterogeneous numeric
  keys and signed zeros, define normalization before hashing, and version any
  changed persistence or observation semantics. A bit-preserving data graph
  could then refuse some native collection materializations explicitly.
* Give general data equality a strict kind/bit meaning and retain an explicit
  numeric comparison. Review all existing numeric, recursive collection and
  compatibility uses before changing this central operator.

The present graph profile deliberately keeps exact kinds and Float bits. It
is suitable for evidence identity regardless of the eventual language choice.
Its decoder verifies collection cardinality; it does not decide language
semantics by silently normalizing keys. Existing typed theory fragments keep
their declared sorts and relations. Mixed runtime numeric key theories need
a reviewed profile before admission.

## Map literal evaluation needs a language rule

The first corpus report evaluated the hash walk and counter reads as values
of one map literal. The digest was correct but its scalar counter was sampled
before the walk, so the report retained zero. Explicitly binding the completed
walk before building the report fixes the instrumentation. Both runs remain
in `evidence/question-graphs/`.

That finding does not itself establish a universal map evaluation order or a
compiler bug against a language specification. It demonstrates that textual
map order was an invalid assumption in this program. A formal Source rule
must not make that assumption without a specified implementation connection.

A desirable preview rule is left-to-right evaluation of literal entries,
including keys, values, duplicate-key behavior and the first raised outcome.
Installing it requires a syntax representation that retains entry order all
the way through reading, macros, ANF and lowering. Sorting data-map keys for
canonical storage must happen after evaluating the ordered expressions; it
cannot justify reordering effects. Quoted data maps and executable map syntax
need a precise boundary too.

Until that review is implemented, effectful code and instrumentation should
sequence dependent operations explicitly with `let`. Pure data-map contents
remain independent of iteration order, as required by both identity formats.
