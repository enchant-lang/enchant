# Versioned portable question graphs — next design

This is a design, not an implemented packet or proof identity. The unchanged
standard encoder refuses one complete three-key closure question among the
187 preceding cases: its expanded public data walk needs 110,551 nodes, above
the 100,000-node budget. Native DAG import still accepts that question.

The comparison-only Merkle audit established equal public contents across SDKs;
it did not authorize packets, change standard identities, or qualify a decoder.

## Preserve old meanings and old evidence

Keep `formal.identity` version 1 unchanged. Existing seals, question references,
proofs and ledger objects must still be checkable under their declared profile.
Do not silently swap a new hash under the old profile or treat a failed old
identity computation as a successful new proof identity.

Introduce an explicit portable data-graph profile and a structured identity
reference carrying both profile and digest. Migrate one consumer at a time.
A version-2 point packet can reference a graph question identity without
rewriting the meaning of a version-1 point. Backend selection remains outside
the language question; no native arena handle belongs in the portable graph.

## Encode every public datum, not only the main formula

A graph must preserve scalar kind and Float bits, all map entries, set/list/
vector/tuple distinctions, statement profiles, scopes, observers and context.
Compressing only root terms is insufficient. Opaque values, functions, live
resources and implicit metadata remain outside portable formal data.

A candidate canonical graph has a versioned root reference and a dense,
immutable node vector. Every child precedes its parent. Reject dangling,
forward, duplicate and unreachable nodes; cyclic or noncanonical graphs must
not be normalized into a valid packet behind the caller's back.

Intern exact tagged node structures. Never use BL numeric equality to merge an
Int with a Float or signed-zero patterns. Map and set ordering must be stable
regardless of VM traversal order. A two-phase construction can first collect
content-described nodes, then order them by height and deterministic content
identity before assigning dense references. Detect any digest collision by
checking exact node content rather than merging it silently.

Explicit budgets should distinguish unique nodes, edges, depth, scalar bytes,
encoded bytes and expansion size. Sharing should remove duplicate traversal;
it should not permit a tiny graph to force unbounded expansion or allocation.

## Decoding has its own obligations

Do not deserialize arbitrary new atoms or module names from an untrusted graph.
A default decoder should use an existing-atom policy or retain keyword tokens
until an explicitly bounded context admits them. Symbol strings and plain byte
strings should remain distinguishable. Runtime Float decoding must preserve
signed zero and reject nonfinite BEAM representations; mathematical IEEE data
keeps its separate representation.

Qualify exact round trips, stable canonical order, every scalar kind, repeated
subgraphs, invalid references, forged rehashes and capacity boundaries. Include
a large closure question and SDK-only/fresh-process consumers. The standard
small-data identities should remain byte identical. A data-graph model theorem
and its connection to the actual BL encoder/checker are separate obligations.

## Reuse across the boundary

The same data graph can support large query identity, typed reply equality and
ledger transport. These uses should share a checked representation, while
keeping authority separate: a codec proves no logical theorem. A Native SAT
model still needs original assertion replay; a Source claim still needs its
own Source connection or actual observation.

Keep the default backend and compiler proof authority unchanged while this
interface is explored. Full native theories, further Source admission and the
remaining language semantic review remain parallel goals, not solved by a
more compact serialization.
