# Portable public-data graphs

Checkpoint 43 candidate, pending exact SDK and presentation qualification.

`formal.data-graph` adds an explicit `:bl/public-data-graph-v1` representation.
It does not change `formal.identity` version 1. The immediate capacity target
is the complete three-key transitivity question: its public data repeats
110,551 nodes, so the standard 100,000-node identity walk refuses it even
though Native imports its term DAG successfully.

## Public interface

```clojure
(def saved (graph/encode question))
(graph/check! saved)       ; canonicality, structure, budgets and reference
(graph/reference saved)    ; {:profile :bl/public-data-graph-v1 :sha256 ...}
(graph/decode! saved)      ; existing keywords only; may refuse materialization
(graph/of question)        ; explicit graph reference of complete public data
(graph/bytes saved)        ; canonical bytes for identity, not an ETF ingress API

(def prepared (point/prepare-graph question {"input" typed-data}))
(point/check-graph question (:packet prepared))
```

A graph has exactly four public fields:

```clojure
{:formal/data-graph 1
 :profile :bl/public-data-graph-v1
 :root 4
 :nodes [[kind payload] ...]}
```

The root is the final node. IDs are dense, every child precedes its parent,
and every node must be reachable. The scalar kinds are `nil`, `bool`, `int`,
`float64`, `binary`, `keyword`, and `symbol`. Container kinds are `vector`,
`list`, `set`, `tuple`, and `map`. A sequence payload contains child IDs; a
map payload contains `[key-id value-id]` pairs. Scalar payloads contain data,
not child IDs. A Float64 payload is its exact deterministic ten-byte ETF
float envelope. Runtime nonfinite representations are refused; mathematical
IEEE values remain ordinary explicitly typed formal data.

## Canonical construction and checking

Construction walks the original public data with explicit limits, interns
exact tagged descriptors containing already interned children, and detects
any digest collision instead of merging unequal descriptors. It orders the
unique nodes by height and content digest, then assigns dense IDs. Set
members and map keys are ordered by their content digests. A checker
independently reconstructs these digests and heights from each preceding
child, rejects duplicate content, noncanonical order, invalid references,
unreachable rows, reserved runtime representations and exceeded budgets.

The new graph reference hashes a deterministic ETF wrapper containing only
tagged native tuples/lists and scalar data. Its bytes and digest differ from
the standard identity and the preceding comparison-only Merkle audit. A
reference carries its declared profile; no consumer guesses a format from a
bare digest. SHA-256 collision resistance remains a cryptographic assumption.

Initial tree-to-graph conversion still visits repeated occurrences. Graph
checking, storage and reference calculation work on unique structure. This
is not a claim that an arbitrary raw BEAM term can be converted in time
proportional only to its sharing.

| Budget | Maximum |
|---|---:|
| Unique nodes | 32,768 |
| Unique edges | 262,144 |
| Root-to-leaf edges | 192 |
| Unique scalar bytes | 8 MiB |
| Canonical encoded bytes | 8 MiB |
| Expanded node occurrences | 4,000,000 |
| Expanded scalar bytes | 64 MiB |

Expanded costs are computed bottom-up before materialization. A short graph
that repeatedly doubles a child can therefore be refused without first
expanding it. The native check remains under an external process memory cap.
The limits are capacity decisions, not mathematical axioms.

## Data checking and runtime materialization differ

A checked graph can retain an unfamiliar keyword name as bytes. `decode!`
only calls `binary_to_existing_atom`; it never creates a new atom, loads a
module, looks up a runtime handle or invokes a described value. Nil and
Boolean names cannot masquerade as keyword rows. Symbols contain names as
bytes. Function, resource, sorted collection, runtime struct and reserved
tuple representations are outside this profile. Metadata belongs in an
explicit field.

BL map/set equality can be coarser than the graph's exact kind/bit identity.
Materialization refuses a map or set if the runtime collapses distinct
encoded entries. It does not silently convert two distinct formal data
points into one. Checking canonical data alone is not a promise that every
future keyword or mathematically distinct key set can be materialized by this
runtime.

The test transport writes an owned ETF qualification file and reopens it
with the existing-atom option. That fixture is not an untrusted ETF decoding
API. `bytes` defines canonical identity bytes; a public byte-stream ingress
would need a separately bounded parser and its own qualification.

## Explicit point migration

`point/prepare` and `point/check` retain version-1 semantics and byte identities.
The opt-in graph pair uses `:formal/point 2` and
`:bl/independent-original-point-v2`, and puts a structured complete-question
reference in the packet's `:question` field. Its packet seal still uses the
standard small-data identity; large binding packets retain that capacity
boundary. Neither checker accepts the other version implicitly.

Both versions use the same independent mathematical evaluator. They require
exactly all original free variables, replay every original assertion and
counterexample condition, and distinguish unavailable mathematics from a
false assertion. A graph identity does not prove a claim, validate a solver
model, establish Source preservation or grant compiler authority.

## Next consumers and obligations

* Carry explicit graph references through typed answer binding and the durable
  verdict ledger; preserve the old declared formats and old saved receipts.
* Add a bounded untrusted byte ingress if transport users need it, rather than
  treating a canonical hashing envelope as a general safe deserializer.
* Model graph expansion/canonicality rules mechanically, then separately
  connect that model to the actual BL encoder/checker.
* Extend theory and Source interfaces on top of this shared data boundary;
  keep native availability, independent replay, Source observation and proof
  authority separate at each layer.
