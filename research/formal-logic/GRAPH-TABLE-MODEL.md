# A checked structural model for shared graph data

Lean 4.34.1 accepts 15 model lemmas/theorems and six original-value instance
theorems for three graphs exported by the qualified SDK. Fourteen altered data
packets and two false proof sources are refused. Exact source, compiled files,
axiom reports and limits are retained in
[evidence/graph-table-model/qualification.json](evidence/graph-table-model/qualification.json).

A length-indexed table makes each appended row refer only to earlier rows.
Its mathematical interpretation is total by construction. Scalar kinds and
Float64 bit patterns stay distinct; map slots identify an ordered entry and
its key or value. This is a structural data model, not a numeric equality law
or a definition of runtime keyword admission.

The general fold theorem relates an algebra over the expanded value to the
same algebra over the finite table. Node count, height and a parameterized
scalar cost are instances. A prefix law keeps existing values stable when a
new row is appended. The counter-certificate rule checks each new count against
the original row and previously checked values. These local facts establish
the root's actual expanded count and depth without asking Lean to unfold the
whole expanded representation.

The independent Python reader reconstructs the exact canonical wire bytes from
SDK-exported tagged rows and checks the complete reference, row ordering,
backward references, reachability, node expansion and depth. Generated Lean
inputs preserve the same scalars and container shapes. The three accepted
instances cover scalar/container distinctions, a shared unfamiliar keyword
(17 stored nodes, 131,071 expanded), and the original closure question
(332 stored nodes, 110,551 expanded, depth 26). The closure instance proves its
structural quantities; it does not prove transitivity.

The positive proof logs depend only on the reported ordinary Lean axioms
`propext` and `Quot.sound` where listed. They contain no `sorryAx` or native
computation axiom. Closed counter checks use kernel reduction. Earlier failed
proofs and capped instance attempts remain explicitly unqualified in separate
folders. Those attempts led to certified local counters rather than a larger
resource allowance.

The bridge is bounded and consumes owned SDK exports. It is not a new public
untrusted byte parser. Its limits are narrower than the public graph format.
The scalar external-size fields remain SDK reports: the generic scalar-cost
law has not been instantiated as an independent byte-cost bridge. Canonical
encoding/hash soundness, runtime admission, typed binder interpretation,
selective graph interpretation, the BL implementation, Source lowering and
compiler preservation require their own connections. Compiler authority stays
false.

Sources: [the model](metatheory/GraphTable.lean),
[SDK-only exporter](graph-table-export.bl),
[independent reader and proof generator](graph_table_lean.py),
[capped runner](run-graph-table-model.py),
[negative controls](graph-table-negative-controls.py), and
[the next obligations](GRAPH-MODEL-PLAN.md).
