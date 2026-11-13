# Retained owners must not hide assumptions

The first implementation boundary is now checked as a prototype:
`formal.retained-question/compose` is shared with the native owner, and
`backend/context-configuration` atomically reads the actual context, adapter
limits and artifact fields. The pure composer passed 54 assertions against the
preceding unchanged owners. Explicit namespace projections of the integrated
owner/composer then passed 278 assertions across three files: 202 existing
managed-owner controls, 22 configuration controls and those 54 composition
checks. The receipt is `evidence/retained-owner-prototype/qualification.json`.
These checks preserve the selected numeric SDK and produce no replacement SDK.
The versioned retained-answer envelope and local request leases below remain
the next implementation work.

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

There are two nested lifetimes. The outer execution callback expires when the
`with-context-request` body ends. A fallback passed to an effect handler expires
as soon as that particular execution returns, even when the outer body remains
active. Capturing the fallback and calling it after returning a candidate point
must fail before native scope work. Qualify both expirations, cross-process
calls, repeated calls and exception cleanup separately. A count of local
fallback attempts does not establish that an arbitrary handler made no other
native calls; whole-process observations need their own instrumented boundary.

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

The owner now delegates its private effective-question operation to
`formal.retained-question/compose`. The bridge must reuse that rule for labels,
assumptions, domains, profiles and scope. Its input is original graph data and
declared retained graph data, not a session or an admitted forest. Calling that
pure function establishes no owner authority.

`backend/context` currently returns the authoritative owner, generation,
revision, assertions and portability/retirement flags. It does **not** return
the owner's adapter configuration. The session's `:identity`, `:solver-ms` and
`:hard-ms` fields are client mirrors; existing managed tests intentionally
corrupt them and require the real owner to remain authoritative. The retained
bridge now has the explicit `backend/context-configuration` owner-read
operation in the prototype source. It reads context and settings atomically,
ignores corrupted client mirrors and performs no native exchange. It must be
qualified in the eventual replacement SDK before claiming that SDK capability.
The adapter settings are ordinary portable data after
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

`q/assertion` already normalizes labels to strings. The prototype raw
`backend/load!` now retains the same string labels it already sent to native
transport. This preserves existing `context/index/label` text while making the
stored assertion contract explicit. Original origin data stays untouched. The
composer requires a closed reserved `:formal/retained-domain` map containing
scope and profiles; other origin metadata remains opaque. A declared domain
is recorded meaning, not trusted execution evidence.

Required graph controls include a shared retained term, unfamiliar keywords
inside origin metadata, absent versus present-nil origin/context fields, empty
retained assertions after reset, duplicate original labels, and explicit
domain/profile joins. Compare complete effective bytes with the existing owner
composition for every admitted compatibility case. A record with a recomputed
hash but altered retained assertions must either change the request subject or
be refused; it cannot keep the original mathematical binding.
