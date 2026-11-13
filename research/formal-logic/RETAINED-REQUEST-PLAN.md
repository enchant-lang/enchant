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
