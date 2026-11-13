# One complete question, with an optional live owner

The retained-request implementation is now in source. The selected numeric SDK
is unchanged; the new source is being checked under explicit namespace
projections before producing a coherent replacement SDK.

The checked prototype boundaries are:

- Graph composition: 54 assertions, including exact compatibility with both
  preceding native owners and retained assumptions in point replay.
- Integrated owner/composer: 278 assertions, including atomic configuration
  reads, corrupted client mirrors and zero native exchanges for metadata reads.
- Portable composition envelope: 22 controls for exact subject binding and
  declared provenance.
- Retained answers and existing fresh requests: 479 assertions, including
  strict version-2 compatibility, version-3 point replay and refused tampering.

The nested lease and facade checks are running separately. These numbers are
overlapping prototype gates, not a total of unique tests or a replacement SDK
qualification. Their exact source projections and base SDK identities are in
the corresponding `evidence/retained-*/qualification.json` receipts.

## The architectural pieces

| Piece | Contents | Meaning |
|---|---|---|
| Portable request, existing v2 | Complete subject graph, checking policy, adapter limits | The mathematical question and requested execution settings |
| Retained composition, new v1 | Caller graph, retained assertion graph, declared generation/revision | Recomputable provenance; no authenticated owner history |
| Fresh answer, existing v2 | Bound source claim and optional point | Recorded fresh context must stay generation/revision zero |
| Retained answer, new v3 | Bound source claim, recomputed composition, optional point | All retained assumptions bind the complete subject |
| Local execution lease | Actual owner, guard, original caller and callback | Same-process execution capability with an explicit lifetime |

`formal.retained-question/compose` is the single pure composition rule used by
the owner and portable provenance checker. It keeps terms and arbitrary origin
metadata as flat graphs. It joins scope and profile graphs without decoding
application keyword names. Initial conversion of an existing owner's ordinary
BL assertions still has the data graph's bounded input-walk cost; this is not
an end-to-end claim of allocation-free term construction.

`formal.retained-composition` recomputes the complete bytes from declared data.
Changing a caller or assumption cannot retain the old complete subject.
Revision numbers are provenance: a self-consistent edited history can still
describe the same mathematical question, and pure readers do not authenticate
that history. Generation appears in the existing retained-question annotation.
Content references identify exact data, not all logically equivalent formulas.

`backend/context-configuration` reads the actual owner atomically. Client
`:identity`, `:solver-ms` and `:hard-ms` mirrors cannot choose the captured
configuration. Raw retained labels now keep the same string form already sent
to native transport. The reserved `:formal/retained-domain` map has a closed
scope/profiles grammar; other origin data remains opaque.

## The language surface in this source batch

`formal.logic/with-context-request` takes an existing native session, an original
caller question graph, optional ordinary request options and a body receiving
`[portable-request execute]`.

The request already contains every retained assumption. A request effect
handler can supply coordinates against that complete subject, or invoke the
local native fallback. Returned coordinates undergo fresh point replay. Using
an existing owner does not make an unchecked native status a proof.

The local callback executes the **original caller** through the guarded owner
primitive, which recomputes the effective subject once. Sending the already
complete subject to that primitive would prepend retained facts twice. The
version-3 binder instead requires the primitive's caller and effective bytes to
match the captured composition and request exactly.

Calling ordinary `execute-request` later on the frozen request uses a fresh
owner and asks its complete subject directly. Backend comparison likewise uses
fresh owners for Z3 and OxiZ with that same subject and checking policy.

The existing owner has already performed its handshake and retained loads.
A handler avoiding its provided fallback therefore establishes zero fallback
scope work, not an absence of every earlier native exchange. Arbitrary handler
code can also perform its own native calls.

## Two nested lifetimes

The outer `execute` callback is same-process and single-use. It expires when
the request body returns or raises, even if it was never called. Actual context
and adapter guards are checked before execution.

Each invocation creates a separate inner effect fallback. That fallback expires
when this individual execution returns, while the outer body may remain open.
Capturing it cannot schedule native work after a handler has returned a point.
Foreign-process calls and repeated calls refuse before native scope work.

The owner guard is checked again after execution. Retired native work is never
silently restarted or retried. The native solver and hard worker deadlines are
unchanged; the owner-operation budget does not bound arbitrary handler code or
the separately accounted pure replay.

## Remaining qualification

Complete the actual lease checks, then exercise portable records and ledger
payloads in fresh processes. Batch the source changes into one immutable SDK,
qualify its runtime and native corpus, and reopen the prior version-2 records
without native calls. Only then select the replacement SDK and refresh the live
dossier with actual new language execution results. Compiler preservation and
historical native-execution authentication remain separate obligations.
