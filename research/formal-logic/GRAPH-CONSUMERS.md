# Graph-backed formal questions: checkpoint 44 candidate

Implementation candidate; not yet qualified. Checkpoint 43 remains the selected
qualified SDK and live dossier runtime until the new receipts are retained.

`formal.question-graph/prepare` converts a complete typed question once.
`from-graph` admits an already canonical graph. Its closed wrapper has exactly
`:formal/question-graph 1`, `:profile :bl/portable-question-graph-v1`, and `:graph`.
Every use checks the authoritative graph again. Caller-supplied cached views,
references and extra wrapper fields are refused.

`open!` derives only the operational question: mode, assertion labels/terms,
claim/counterexample, observations and vacuity policy. Unrelated provenance,
profiles and scope stay in the graph, including unfamiliar keyword names as
bytes. They still bind the complete reference and exact canonical bytes.
`field-graph` preserves missing versus explicit nil; `field-data!` and
`materialize!` explicitly request existing-keyword materialization. Observations
and typed terms still use the existing evaluator and binder checks; this is
not a graph-native evaluator or a universal O(unique nodes) claim.

The data graph adds `subgraph`, `assemble`, `concat-vectors`, `patch-map` and
selective `decode-nodes!`. Composition follows checked node tables, preserves
exact kinds and scalar bits, deduplicates exact content, and canonicalizes the
result. Working node/edge/scalar budgets and cumulative inspection limits can
conservatively refuse a composition even if its pruned result might fit.
No atom is created to make unfamiliar metadata materialize.

`formal.logic/run-graph`, `solve-graph-in` and `compare-graph` explicitly use
`:query-graph` effects and version-2 graph-bound replies. The old raw-question,
script, identity and reply paths keep their declared formats. A handler must
provide the named graph method. Native owners/revisions remain private. Retained
assertions compose into the effective question graph before interception.

`formal.answer/check-graph` checks complete exact binding and replays candidate
assignments. Only the owner-supplied matching actual fallback retains native
observation provenance. A pure reopened check moves stored execution labels to
`:reported-execution`; it does not authenticate them. A live result describes
only its provided fallback as not invoked, attempted or returned. Handler work
outside that fallback is not counted. An invalid reply after fallback execution
retains the actual returned raw answer under the error's execution report.
Native UNSAT remains unchecked solver evidence, never a portable certificate.

`veritas.ledger/record-graph!` uses explicit `:bl/graph-verdict-v1` and payload
media type v2. The complete question occurs once per record; separate canonical graphs
hold caller evidence, an optional stripped reply body and an optional witness.
The indexed reference is checked on reopen. `all`/`about` return these as graph
data; `graph-evidence!` and `graph-witness!` request materialization. A stored
answer is rebound before exposure, not replayed implicitly. Nil/false witness
presence is explicit. Old inline and v1 payload records remain readable. The
existing owned-store codec is not a newly admitted untrusted byte parser.

`formal.check/query` and the research `formal.api/check`, `compare`, `describe`
accept the same explicit graph subject with either native backend. The evidence
envelope names scope/profile/relation graph fields; the wrapper format profile
never substitutes for the statement profile. Portable proof production for this
subject is explicitly not admitted yet.

Qualification must cover all 187 existing subjects, both native engines, exact
old identities/graph references and point packets, opaque metadata, binder and
vacuity semantics, retained-context ownership/effect conveyance, failed replies,
forged/rehashed bindings, old/new durable records, and fresh SDK-only readers.
Compiler and Source gates remain separate. Graph mechanics, evaluator soundness,
Source/compiler preservation, termination and actor liveness remain open proof
obligations; serialization does not discharge them.
