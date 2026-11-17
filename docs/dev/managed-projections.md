# Managed projections

Use `data.projection` for expensive shared reads. Declare one logical name in
an application instance and give observers `projection/reader` handles. A
subscription grants demand. `read` returns retained data or an explicit status;
calling it repeatedly never starts work. The creator owns the controller's
lifetime. Duplicate names refuse.

`start!` accepts a closed query containing one stored Datom pattern on an
actual native SDK connection. Source evidence includes attribute changes,
compiler generations and provider provenance. Unknown evidence refuses reuse.
A source revision replaces the latest pending intent; one worker remains active
until its actual death, including callback cleanup. Tickets discard obsolete
completions. Unrelated attribute commits preserve a valid answer.

Physical reads reserve step credits before entering the substrate's bounded
page operation. Every page also has a byte ceiling. Managed plans refuse joins
because page counts cannot bound intermediate binding multiplication. Extending
this fragment requires admission before intermediate rows are allocated in the
query engine, including its fallback paths.

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

## Other shared opportunities

| Entry point | Suitable improvement | Required boundary and test |
| --- | --- | --- |
| `datom.watch` query watches | Share maintained query state across subscribers | Preserve per-commit callback effects and principal scope; assert every accepted commit is delivered once while shared query work runs once. |
| `datom/memo-by-basis` | Add an explicit owned derivation API for expensive views | Arbitrary closures need their existing execution owner; assert concurrent readers do not duplicate an admitted derivation and rejected retention cannot trigger a retry loop. |
| `system.evidence/source` and `lsp/analyzed` | Share bounded analysis jobs and retain smaller per-consumer artifacts | Preserve compiler scope and code generation; assert one analysis for concurrent requests and exact invalidation after a provider edit. |
| `datom.query.engine` managed joins | Admit intermediate rows before allocation | Debit every expansion, including alternate plans and fallbacks; adversarial Cartesian products must refuse before exceeding credits. |
| `datom.query.rank-demand` | Reuse measured work receipts for construction policy | Forecasts remain policy; assert cache hits mint no work credits and aborted construction releases its slot only after worker death. |

Existing transaction watches deliver effects, and ordinary queries return values
synchronously. Adopting a retained status protocol at these boundaries requires
an explicit API contract. Each consumer can use managed readers where pending
or blocked results are meaningful.
