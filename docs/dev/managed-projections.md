# Managed projections

Use `data.projection` for expensive shared reads. Declare one logical name in
an application instance and give observers `projection/reader` handles. A
subscription grants demand. `read` returns retained data or an explicit status;
calling it repeatedly never starts work. The creator owns the controller's
lifetime. Duplicate names refuse.

Use `projection/status` with a reader grant to inspect status, counters, demand
and retention limits. It neither decodes result payloads nor acknowledges a
subscriber wake. `live.observatory/attach` mounts an explicitly enabled,
host-authorized development view at `/__enchant`; its JSON endpoint and public
`snapshot` function share the same bounded observation model. It creates no
subscription, timer or computation. See `examples/tooling/work-observatory.bl`.

`start!` accepts a closed query containing up to eight positive stored Datom patterns on an
actual native SDK connection. Source evidence includes attribute changes,
compiler generations and provider provenance. Unknown evidence refuses reuse.
A source revision replaces the latest pending intent; one worker remains active
until its actual death, including callback cleanup. Tickets discard obsolete
completions. Unrelated attribute commits preserve a valid answer.

Physical reads reserve step credits before entering the substrate's bounded
page operation. Every page also has a byte ceiling. Every unification reserves a step and a conservative byte charge before
extending a binding. Hash-bucket construction is charged too. Exhaustion is
re-thrown before a hash join can restart as a Cartesian fallback. Compound
clauses, rules, functions and computed providers stay outside this fragment.

The controller reserves shared retention credits for the declaration, revision
evidence, answer and incremental state. Each query worker has a heap ceiling
and deadline. Capacity exhaustion, oversized output, cancellation and eviction
leave an explicit blocked status. Only a changed source revision or a controller
retry can admit another attempt. A reader has no retry or publication authority.

For event histories, use `start-incremental!` with a data declaration:

```clojure
(def totals
  (projection/start-incremental! :usage/totals
    {:source-id "usage/v1" :group-by [:user :model] :sum [:tokens]
     :window-ms 86400000 :max-events 1024 :max-groups 128 :max-delta 32}))
```

The controller publishes consecutive `delta!` checkpoints with bounded `:upsert`
and `:remove` vectors. A checkpoint and its count/sum changes publish atomically.
Identical replay is inert; conflicting replay, sequence gaps and capacity
exhaustion refuse. Missing meters remain unknown. Seed data must arrive through
the same bounded checkpoint stream. Persist checkpoints and accepted source
events together when durability is required.

Only changed IDs and their groups are maintained. Expiry uses an ordered tree
of due IDs and removes at most `:max-delta` rows in one turn. Timers run while
subscribed. Idle readers can observe expiry as stale but cannot drain it.
Resubscription resumes bounded maintenance. The reducer accepts first-order
fields and built-in count/sum operations; it executes no supplied functions.

Run the focused files listed in `scripts/projection-preflight.json` on the
qualified SDK. They assert exact admission and work counts, checkpoint atomicity,
expiry boundaries, shared answers, refusal and lifecycle cleanup. Their deadlines
detect stuck protocols; performance assertions use operation counts. Source
preflight compiles committed candidates into private namespaces on a retained
SDK and records frozen input hashes. Canonical SDK qualification runs the same
test files under their original names on the integrated artifact. Use
`scripts/projection-preflight --canonical --sdk /nix/store/SDK --out RECEIPT.json`;
the runner refuses unless every selected consumer source matches the SDK image
byte for byte. It freezes committed test inputs, caps one cold VM at two cores
and 2 GiB with no swap, and records source and artifact hashes.

These guarantees apply to the managed API. `data.bounded-cache/value` remains an
optional cache with compute-on-miss semantics. Use a managed projection at a hot
call site to obtain demand, work and retention admission. General foreign-code
preemption requires runtime support beyond the closed query/data-only boundary.

## Shared application integration

`live.app` accepts `:projections (fn [me] {:totals reader})`. The resolver grants
read capabilities for the authenticated principal and runs once per socket.
Create controllers in an application owner that outlives its sockets. Share a
controller only among principals allowed to see the same answer; managed reads
do not add row-level authorization to a raw connection.

Screens receive `:projections`, a map of result records with `:status` and, when
ready, `:value`. Rendering reads retained answers. A socket subscribes on mount,
unsubscribes on detach or termination, and resumes demand on an authorized
reattach. A changed projection wakes its subscribers independently of Datom
commits, including incremental updates and expiry. Each subscriber has at most
one outstanding wake until its next authorized read. HTTP first paint reads
without subscribing, so repeated requests cannot initiate background work.

`data.provenance` hashes SDK-owned counter tuples directly into 32-byte receipts,
avoiding recursive identity normalization and retained environment references.
LSP uses `definition-revision`: cost follows environment depth, independent of
definition or namespace count. Datom uses `namespace-revision` over its fixed
query dependencies, preserving answers during unrelated lazy loading. Busy and
dead scopes decline; private analysis forks preserve the parent's receipt.

## Shared tooling work

`data.single-flight/with-key` serializes a finite logical identity in its actual
caller's environment. Waiters recheck retention after admission. Two caller
processes can execute shared work at once across keys; nested consumers reuse
their caller's slot. Native locks release on return or holder death. Waiting
has a deadline and refuses busy capacity. Computation stays under its original
execution authority. Cache eviction or refused retention can still require
another synchronous computation; use an owned derivation for sticky refusal.

LSP and `system.evidence/source` share concurrent requests under that admission.
`codebase/index-source` shares facts by source bytes, namespace, type seeds,
index mode and live code evidence. `code.index` rechecks a disk miss after
admission and publishes complete fact files with an atomic rename. `bl ask`
uses that same artifact path. Persisted identities include namespace, type seeds,
mode, source and qualified SDK; unlike inputs never share an artifact. Mutable
connections remain owned by their callers.

`codebase/loop-plan` propagates weighted loop depths in one topological pass.
Nodes left behind are cycles and their descendants; those contexts receive no
finite depth claim. Fact collection appends eagerly. The plan reports exact
vertex, edge and visited-edge counts.

`system.analyze` processes functions after their dependencies. Changed return
or footprint evidence wakes only dependent functions; duplicate pending work
coalesces. Acyclic functions need one summary evaluation. Recursive work has
at most fourteen evaluations of each dirty definition; latent effects have a
separate sixty-six-evaluations-per-definition ceiling. A costly cycle cannot
borrow the unused budgets of cheap functions. Unfinished work fails
closed and cannot claim complete coverage. Incremental reports count actual
summary evaluations.

`bl check` retains compact compiler facts and source diagnostics separately
from the larger LSP bundle. Lint guards execute on every request, and ambient
warnings merge from the current process after retention. Code publication
invalidates retained facts. Baseline selection and regression rules retain
their normal behavior. The lint/deodorant preorder stacks use native list tails,
so visiting a node shares its remaining siblings. Lint reports `:work :nodes`;
the walk never pops and copies a pending vector of the remaining file.

Eligible `datom.watch` queries share the exact before/after diff under source,
query, provider and code evidence. Each watch still invokes its own callback
for every accepted relevant commit. Unknown providers and behavioral wrappers
use authoritative query execution. Sharing a pure diff does not merge effects.

Ranked-index demand records physical scan work beside elapsed time. A measured
sample with zero work cannot pay for construction; a result-cache hit does not
produce a scan receipt. Cost forecasts remain policy and grant no write or
query authority.

## Owned basis derivations

Use `data.derivation/start!` when an expensive database derivation needs an
explicit owner and retained statuses:

```clojure
(def totals
  (data.derivation/start! :reports/totals database :totals/v1
    (fn [db] (build-totals db))
    {:max-output-bytes 65536 :timeout-ms 5000}))
```

The controller delegates its callback through `proc.work` custody. Readers use
the ordinary projection reader, subscription and read APIs; reading never
starts work. Failure or oversized output stays blocked until a controller
retry or revision change. Worker death releases capacity. Dispose the
controller before closing its database. The owner is responsible for its
callback's effects and declared immutable inputs; this callback interface does
not certify arbitrary code as a closed stored-data query.

Incremental source watermarks advance only with accepted checkpoints. Expiry
maintenance has its own clock, so subscribing or expiring rows cannot reject
an already ordered source update. Rows already expired at maintenance time
are discarded without resurrecting an old window.

`scripts/tooling-efficiency-measure.bl` measures identical synthetic corpora on
two pinned SDKs in separate capped VMs. It records first and warm observations
and reductions. The qualification tests enforce operation counts, invalidation,
capacity and refusal independently of machine timing.
