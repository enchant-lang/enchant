# A formal value keeps its identity when it moves

The first fresh-VM context archive exposed a serialization bug. Its receipt
retained the right definition, semantic profile, adapter and limits, but hashing
the decoded value produced a different identity. The default ETF encoding had
been used as though it supplied canonical bytes.

Erlang explicitly does not promise stable bytes from default `term_to_binary`.
Its deterministic option guarantees repeatability within one OTP major release,
with no such guarantee across major releases. The implementation now also
normalizes collection contents before encoding, rather than depending on their
runtime storage shape. [Official Erlang documentation](https://www.erlang.org/docs/28/apps/erts/erlang.html#term_to_binary/2).

## The data contract

`formal.identity` defines `:bl/canonical-formal-data-v1`. Current closed objects
carry `:identity-profile` as well as their semantic `:profile` and `:identity`.
Constructors seal the complete object; validators require the known identity
profile and reconstruct its digest.

```clojure
(identity/seal {:formal/example 1 :state {"x" 1}})
(identity/valid? stored-object)
```

The encoding normalizes public data to a map-free tree of tagged native tuples
and proper lists. It encodes that tree with deterministic ETF minor version 2
and hashes the bytes with SHA-256. A fixed codec-version prefix is included.

| Value family | Canonical content |
| --- | --- |
| nil, Boolean, Int | Distinct type tag and exact value. |
| Float | Distinct float64 tag and exact IEEE representation; signed zero stays distinct. |
| Binary/text | Exact bytes; no Unicode normalization. |
| Keyword, symbol | Distinct tags and complete names, including namespaces. |
| Vector, proper list, native tuple | Distinct kind tags and ordered elements. |
| Set | Canonical element encodings in byte order. |
| Map | Canonical key/value pairs in encoded-key byte order. |

Map and set entries must have unique canonical keys/elements. Ambiguous runtime
representations are refused. Nonempty attached metadata must instead appear in
explicit data fields. Functions, lazy sequences, PIDs, references, ports, foreign
objects and ordered runtime collections with an unmodeled ordering policy are
outside this codec. An identity does not capture or grant their authority.

Limits: 100,000 visited values, depth 192 and 8 MiB of encoded data. These are
implementation limits, not language exceptions. This is formal **data identity**,
distinct from generic BL equality, numeric equality, raw collection key identity
and live resource ownership.

## Shared across the formal interface

Canonical identities cover sealed contexts, contracts, ranked loops,
translations, protocols, source protocols, bounded subjects and runtime receipts.
Core identities, term digests, certificate statement digests, optimizer
fingerprints, query identities and backend cache keys use the same codec with
their appropriate content/domain. Observation maps have a canonical root order
before DAG hashing. Explicit vector and argument order remains meaningful.

The semantic profile describes what a program or theory means. The identity
profile describes how its data is named. Neither selects the backend. Z3 and
OxiZ receive the same typed question; runtime/session identities remain separate
provenance and custody facts.

## Experimental format change

Earlier research objects used default-ETF hashes and lacked the identity-profile
marker. They remain historical evidence for their recorded checker commits.
Current validators do not reinterpret those bytes or silently re-sign old
executions. Reconstruct definitions and evidence under the new format, or use
the original recorded code to inspect the historical format.

The archive that revealed the problem remains under
`evidence/contexts/raw-etf-identity/`, with the failed fresh-VM logs beside it.
New executions have new sealed definitions and receipts. All nine new records
retain their expected verdicts in a fresh VM: eight conform and one preserves
the ordinary-program disagreement. The two function-contract certificates and
contextual protocol proof also recheck without native solving. The calibrated
window loads no recorded handler modules and invokes no recorded handlers.

The old probe BEAM bytes are separate: exact source-to-byte reproduction still
matches all five original SHA-256 artifacts without executing their handlers.
The report records old and new core identities separately rather than equating
different identity encodings.

## Evidence and scope

The coherent combined run passed 7,099 assertions across 22 focused files,
including 50 identity assertions and 139 context assertions. Checks include
map/set insertion order, vector construction history, kind distinctions,
namespace-sensitive cache keys, resource refusal and eight independent byte/hash
fixtures. The Python fixture producer specifies selected normal forms directly
and implements the relevant ETF fragment; it starts no Erlang VM.

The recorded SDK fixes OTP 29. Fixtures and fresh-VM replay qualify that runtime.
Future SDK/OTP upgrades must recheck the codec and version it if needed; this is
not an unqualified cross-version encoding theorem. The encoder, crypto/runtime
and checker remain reviewed code. Canonical identity is neither execution
attestation nor compiler proof authority.

Implementation: `src/formal/identity.bl`. Independent fixtures:
`canonical_identity_fixtures.py` and `evidence/contexts/canonical-fixtures.json`.
Checks: `test/identity_test.bl` and `evidence/contexts/qualification.json`.
