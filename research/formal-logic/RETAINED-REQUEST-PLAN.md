# Retained owners must not hide assumptions

The public request bridge currently acquires a fresh owner. The lower owner
primitive already supports retained assertions and authoritative context
guards. Extending the language bridge should preserve one rule: a portable
request contains the entire mathematical question, including every assumption
used to interpret an answer. A live session cannot silently strengthen it.

## Freeze meaning before choosing execution

Read retained assertions from the actual owner through `backend/context`,
not the diagnostic session atom. Compose them with the caller's original
question using the same graph composition as the owner primitive. Prepare a
normal portable request whose subject is that complete effective graph.

Retain the caller's original part, captured generation/revision and owner
token only in an expiring local execution lease. The request itself contains
no PID, port, callback, admitted forest or native ID. Changing the retained
assertions requires a different subject; it cannot be an unrecorded preference.

A possible surface is `formal.logic/with-context-request`: it receives the
session, caller question and options, then calls a local body with the
portable request and an expiring execution callback. This name is proposed.
The callback needs the existing same-process, single-use and retirement rules.
Plain `execute-request` on the same portable request remains useful: it opens
a fresh owner and asks the complete question.

## Reuse the owner primitive without composing twice

The local callback can call `backend/graph-question!` with the captured
original caller part and actual expected context guard. The owner rechecks
its state, derives the effective graph and performs fresh admission. The
bridge then requires that complete graph to equal the portable request subject
byte for byte. It also binds the original caller graph, policy, backend and
native limits to the captured lease, and rechecks the actual context after
the operation. Recorded guard fields alone establish nothing.

Sending the already composed subject through the current primitive would
prepend retained assumptions again. Avoid that route. The lease holds the
original part for the owner call; the complete portable subject is what fresh
point replay and saved evidence consume. A later native optimization may
avoid duplicate assertion imports, but that is separate from this bridge.
No speed advantage is assumed.

The answer needs an explicitly versioned extension to the current fresh-owner
record: nonzero recorded generations/revisions and composition provenance.
Provenance remains recorded data. A pure reader checks its declared
composition when present, then rechecks the complete request subject. It does
not authenticate a historical owner, guard or native execution. Keep existing
v2 fresh-owner records readable under their own contract.

## Compare engines on the same complete subject

A handler-supplied point must satisfy the complete subject, including retained
assumptions. The handler needs no live context to supply a mathematical
candidate. Only the local fallback uses the lease; copied execution flags
cannot replace it.

Backend comparison can use fresh owners for both engines with the identical
complete subject and replay policy. Reusing an existing owner is optional
execution plumbing. Availability and reported statuses stay visible; neither
reuse nor agreement grants proof authority.

## Required controls

Qualify actual load/reset, stale generation/revision, changed owner, changed
caller graph, changed complete subject and changed policy/adapter settings.
Refuse stale leases before a native scope attempt; preserve retirement after
uncertain native work. Include a point satisfying the caller part but
violating a retained assertion.

Store actual retained-context answers and reopen them in fresh SDK-only
processes with no application imports or native calls. Compare complete
question bytes and point results with the fresh-owner route. Keep original,
effective and execution identities separate. These are future gates; the
current numeric/fresh-owner API has not implemented this extension yet.

## Review against the current implementation

The owner already composes retained assumptions in
`formal.graph-execution/effective-question`. That function is private; the
bridge must not reproduce its label, assumption, domain, profile and scope
rules in a second implementation. Extract the pure composition into one small
module shared by the owner and the request bridge. Its input is original graph
data and declared retained data, not a session or an admitted forest. Calling
that pure function establishes no owner authority.

`backend/context` currently returns the authoritative owner, generation,
revision, assertions and portability/retirement flags. It does **not** return
the owner's adapter configuration. The session's `:identity`, `:solver-ms` and
`:hard-ms` fields are client mirrors; existing managed tests intentionally
corrupt them and require the real owner to remain authoritative. The retained
bridge therefore needs an owner-read configuration operation, or an explicit
extension of the local context result, before it can freeze request adapter
settings and reject mismatches before native scope work. Reading the session
map is insufficient. The adapter settings are ordinary portable data after
capture; the owner PID and live guard remain local.

Composition currently places a declared generation in the effective question's
`:context` graph. That is part of the exact content reference and remains
recorded data. It is not an authenticated owner identity or a canonical identity
for all logically equivalent propositions. Preserve this distinction when
comparing a retained answer with fresh execution of its complete subject.
Changing that annotation policy would require an explicit composition profile,
with compatibility readers for the existing graph contract.

The fresh-owner answer has two separate restrictions that must remain intact:
`source!` requires recorded generation/revision zero, and `from-managed`
requires the original and effective subject references to coincide. A retained
answer cannot simply relax those conditions. Give the extension a new answer
profile with closed composition provenance: original caller graph, retained
assertion graph, declared generation/revision and effective subject. A reader
must recompute the declared composition and require its complete bytes to match
the request. It must still recheck the point against that effective subject,
without accepting recorded owner or execution authenticity. Existing v2 answers
keep their zero-context contract.

The current request-record and ledger paths delegate answer validation to
`formal.request-answer`; they do not independently authenticate a solver.
Review both paths when adding the new answer profile. Keep historical v2 rows
readable and qualify new retained rows in separate fresh SDK-only processes.

The focused numeric gate also exposed that the test CLI can print failed
assertions and return process status zero. The local qualification runner now
checks the complete green summary as well. Repair the general CLI outcome
contract in a later coherent runtime batch; a process exit alone is presently
insufficient test evidence.

## Composition must remain graph-based when records reopen

Extracting the current function verbatim is insufficient for saved v3 answers.
Its live snapshot contains BL assertions, whereas a portable record must keep
their terms and application metadata as flat graph data. Decoding the entire
retained assertion vector would expand shared argument trees and could attempt
to intern application keywords that the SDK does not know. The fresh-request
interface deliberately avoids both operations.

Make the shared composition boundary consume an original caller graph and a
retained-assertion graph. Use `formal.data-graph/keyword-nodes` and subgraphs to
select the closed SDK fields, patch the renamed labels, and concatenate the
assertion/assumption vectors. Term bodies and arbitrary origin metadata must
pass through as graphs. Only the small fields actually needed for composition
may be materialized: labels and the declared domain/scope/profile vocabulary.
The pure reader should use that same function to recompute the complete subject.

`q/assertion` already normalizes labels to strings. Raw `backend/load!` currently
accepts manually constructed assertion maps and stringifies labels for native
transport, while keeping their original representation in the retained mirror.
Review normalization at the owner boundary so both paths have a single named
assertion contract. Preserve the existing `context/index/label` text and
original origin data; do not silently change the effective question. A strict
reserved `:formal/retained-domain` grammar also needs explicit treatment rather
than interpreting arbitrary origin metadata as a trusted domain declaration.

Required graph controls include a shared retained term, unfamiliar keywords
inside origin metadata, absent versus present-nil origin/context fields, empty
retained assertions after reset, duplicate original labels, and explicit
domain/profile joins. Compare complete effective bytes with the existing owner
composition for every admitted compatibility case. A record with a recomputed
hash but altered retained assertions must either change the request subject or
be refused; it cannot keep the original mathematical binding.
