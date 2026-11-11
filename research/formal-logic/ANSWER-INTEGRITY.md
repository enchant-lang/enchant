# Next slice: complete typed answers

The first behavioral baseline passed 13 assertions and failed 27. The repaired
immutable SDK passes 134 answer checks and the preceding 86 public SDK checks.
The wider regression and dossier qualification are in progress.

## Architectural pieces

`formal.answer` is a pure boundary above both engines. It binds a response to
the complete portable question, checks phase/status combinations and reconstructs
observations. It depends on terms, values, queries, data identity and independent
evaluation. Oracle routing, native execution, session custody and evidence
projection retain their separate owners. Existing oracle helpers forward to
this layer.

| Boundary | Implemented behavior |
| --- | --- |
| Variable bindings | Concrete values must match their declared sorts. Missing or opaque values remain incomplete. A supplied ill-sorted assertion binding invalidates the proposed model. |
| Observations | An ordinary handler's display is reconstructed from assignments and descriptors. Its supplied display remains labelled `:reported-witness`. |
| Phases | A consistency-only SAT response cannot answer the proof goal. A frontend UNSAT response is refused. SAT and proof questions keep distinct verdict meanings. |
| Native delegation | Oracle records its actual owned fallback result. An exactly matching reply retains native-only observations and their provenance. A modified reply is reconstructed independently. |
| Fallback lifetime | Delegation checks borrower, retirement, context generation and retained assumptions before execution, then checks the context again afterward. |
| Derived procedures | Enumeration, finite optimization, synthesis and deletion explanations use the logical session before opening a native worker. An unavailable projection stops enumeration as partial. |
| Evidence | Handler claims, native execution, independent replay and checked certificates retain distinct bases. Compiler authority stays disabled. |

## Concrete models and equality

Bool bindings contain `true` or `false`; Int bindings contain integers. Real
bindings use canonical rational pairs with positive denominators. BV and FP
values retain their declared widths/formats and bounded bit patterns. Enums,
rounding modes, arrays and sequences have recursively checked encodings.
Uninterpreted representatives remain unavailable to this evaluator.

Concrete String bindings use UTF-8 values in the current SMT alphabet,
codepoints 0 through 196607. BL grapheme operations and binary bytes retain
separate models. [SMT-LIB Unicode Strings](https://smt-lib.org/theories-UnicodeStrings.shtml)

FP identity is interpreted recursively through sequences, array defaults and
array keys. The mathematical FP domain has one NaN value per format; distinct
NaN representations therefore name the same key. IEEE `fp.eq` has its separate
comparison rule. The checks preserve the previous lack of a native NaN payload
observation. [SMT-LIB FloatingPoint](https://smt-lib.org/theories-FloatingPoint.shtml)

Formal data identity remains distinct from mathematical equality. Reply
binding uses the existing canonical profile, preserving integer/float kinds,
list/vector kinds and floating bit patterns in metadata. Its existing data
format limits apply: 100,000 nodes, depth 192 and 8 MiB. Nominal term, value
and reply version markers require integers.

The optional execution record accepted by the pure answer checker is data.
Oracle supplies that record from its owned fallback. A standalone call does
not authenticate the record's origin. Native and handler answers retain
unchecked certificate status; independent replay remains an implementation
whose general soundness has not been mechanically proved.

## Observed baseline failures

The old evaluator accepted a Boolean contradiction under the assignment `p = 1`
and accepted a float for an Int variable. A handler's display could report 999
where its checked input implied 8. Both engines correctly solved a native
context after a handler added a false assumption, while the reply still named
the original question. The new fallback guard refuses that context change.
The original logs are retained under `evidence/answer-integrity`.

## Review process semantics separately

Oracle handlers are currently process-local. Normal `spawn` conveys the language
environment; arbitrary process-dictionary keys are intentionally excluded.
There is no general dynamic `binding` form to reuse. Automatic handler inheritance
needs a language/runtime design, including nested scopes and reused workers.

Executable ownership matters: `Env/callback_modules` inspects callable arms,
not arbitrary captured data. Adding a callback to a conveyed token alone does
not establish its code lifetime. Preserve the runtime's registration and Source
custody rules. Legacy `oracle/ask-all` also needs an explicit handler-conveyance
review. Keep these API scopes distinct from security capabilities.
