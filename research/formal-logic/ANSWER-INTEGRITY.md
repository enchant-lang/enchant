# Next slice: complete typed answers

This slice is pending baseline probes and qualification. The SDK interface is
qualified in `evidence/sdk-interface/qualification.json`; the items below are
further boundaries identified while reviewing its implementation.

## Separate the architectural pieces

A pure `formal.answer` layer should bind a response to the whole portable
question, validate phase/status combinations, and reconstruct observations.
It should depend on terms, values, queries and independent evaluation. Oracle
routing, native execution, session custody and evidence projection retain their
separate owners. Keep the existing public oracle helpers as forwarding APIs.

| Boundary | Qualification target |
| --- | --- |
| Variable bindings | Check each supplied value against its declared sort before treating its evaluation as a typed model. Unsupported and missing values retain explicit availability. |
| Observations | Derive handler observations from checked assignments and descriptors. A supplied display witness cannot override those values. |
| Phases | A consistency-only SAT response cannot answer the main proof question. A frontend response cannot become an entailment. SAT and proof questions keep their distinct verdict meanings. |
| Native fallback | Bind delegation to the question context's generation and retained assumptions. Loading or resetting that context must not silently change the question executed by a saved fallback. |
| Derived procedures | Enumeration, finite optimization, synthesis and deletion explanations should use the common logical session before opening a native worker. Incomplete projection values prevent completeness claims. |
| Evidence | Keep handler claims, actual native execution, independent replay and checked certificates visible as distinct bases. |

## Record the baseline first

The evaluator currently looks up variable assignments directly. Probe a Bool
variable assigned an integer under conjunction and disjunction, and an Int
variable assigned a float. The first safety case should use a Boolean
contradiction, so accepting the proposed assignment would be an observable
failure of typed replay. Retain the actual failing log before changing code.

Probe a handler supplying valid assignments and a different displayed witness;
a SAT response for only the assumptions of a proof; and a native context whose
handler loads an additional assumption before invoking its fallback. Existing
closed/foreign-context checks do not establish mutation safety within a live
context. Include positive cases and both native engines in the final regression.

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
