# A model connection is separate from a Source claim

A Core program can be authored directly as BL data. Proving a promise about it
does not assert that some BL Source function implements that program. Core-only
contracts and Core/Core translation comparisons now report
`:source-connection :authored-core-no-source-claim`. Actual source contracts keep
their reviewed Source-extraction or context-linking status. Direct term queries
report `:not-applicable-direct-term-query` in the common Source connection field;
an arbitrary `:origin` annotation cannot authenticate Source provenance.

Every prepared program/model subject now exposes a separate
`:model-interpretation` record. Its profile is
`:bl/reviewed-model-to-terms-v1`, status
`:reviewed-not-mechanically-proved`, and purpose
`:implementation-connection-not-proof`. This ordinary, canonically identified
data names the exact model descriptor, interpretation relation and generated
property/obligation questions. Each question has a label, full canonical
question identity, mode, profile, scope and relation.

The seven subject kinds share one evidence field:

| Subject | Input to interpretation | Prepared questions |
| --- | --- | --- |
| Term query | Already a term question | No model interpretation; not applicable |
| Contract | Exact typed Core identity | Whole-return/value/named-error property |
| Translation | Both exact typed Core identities | Whole-outcome equivalence property |
| Loop | Exact closed controller/contract identity | Ranking/result obligations and consistency |
| State protocol | Exact authored state model identity | Induction, initial-state and consistency questions |
| Source protocol | Exact Source subject, derived state model and handler Core identities | The derived model's induction questions, linked through its connection identity |
| Bounded trace | Exact trace subject, protocol/state model and depth | Bounded whole-trace safety property |

These are the questions produced during preparation. Additional optional native
feasibility probes retain their own evidence; this record does not claim to
list every diagnostic or solver call. Canonical-data limits apply.

The connection record is rebuilt during preparation, and propagated through
checking and the common `:evidence/:connection/:model-interpretation` field.
It remains visible when a valid model's proof is unknown, refuted or vacuous.
Invalid preparation reports `:not-established`; direct term questions report
`:not-applicable`. An absent proof must not be replaced by a reviewed connection.

The record binds what the implementation interpreted, not a theorem that it
interpreted it correctly. It does not grant Source provenance, establish runtime
conformance or certify the implementation. A content hash is not a soundness
proof. No proof or optimizer gate accepts these records in place of a portable
term certificate, either translation check, or the exact Source definition.

This corrects a misleading older label: Core/Core comparisons and authored-Core
contracts previously used the generic `:reviewed-not-mechanically-proved` Source
connection status for their Core interpretation. Their logical subjects, query
contents, certificate statement identities and result verdicts are unchanged;
the assurance ledger now names the appropriate boundary.
