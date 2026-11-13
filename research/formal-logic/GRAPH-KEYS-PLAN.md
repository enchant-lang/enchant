# Keep application keys as graph data

Candidate 3 completed both 187-question native corpora. Its first fresh
SDK-only reader then failed in `formal.graph-question/with-prepared` while
decoding application keys through `binary_to_existing_atom`. The independent
`managed-key-probe.bl` now reproduces both outer observation keys and nested
payload keys, using names that are absent before and after the probe. A string
key control passes. Native sessions, exchanges and managed queries stay zero.

This is an inventory boundary issue, not a reason to create atoms from input,
load application Source, register the fixture vocabulary, or relax the safe
public graph decoder. Candidate 3 remains unpromoted.

## Separate inventory from materialization

The current inventory discovers nested data correctly, then materializes keys
in order to rebuild host maps. That makes fresh numeric admission depend on
which application atoms happen to exist in a VM. It also lets host map
construction decide traversal/collapse behavior before display decoding.

Add an explicit graph-key inventory profile. It must:

- Keep outer labels and nested keys as original component graphs/references.
  No key value must be materialized merely to find term roots.
- Traverse every original map value in its canonical portable row order.
  Preserve exact key identity and all entries; do not reconstruct a host map
  or silently drop an entry through runtime key equality.
- Choose and document deterministic outer observation ordering over original
  key graph bytes. Keep original source IDs in every root description.
- Read required assertion labels as string data only. Existing assertion labels
  are strings; a malformed raw declaration is a refusal, not a request to
  intern a keyword.
- Keep the existing generic/value-label inventory under its declared profile
  for the qualified project APIs. The new managed path uses the raw-key mode.

Observation output should become ordered rows with `label-graph`, a fresh
label reference, the original descriptor graph and evaluated source roots.
A map keyed by decoded application values is no longer the compulsory
transport. Optional explicit materialization can use the existing safe decoder
and refuse unavailable atoms or collapsing runtime keys. The portable data
remains available when materialization is refused.

## Version the changed contract

The raw-key inventory and managed reply need explicit new profiles/versions.
Their traversal order is part of their execution/accounting contract. The
original mathematical question graph/reference stays unchanged. Native watch
names can continue using private ordinal strings; native IDs and ephemeral
callbacks never become public key identities.

Update the owner observation builder, native corpus recorder, fresh reader and
staged request point/answer implementations together. Bind observation values
using graph composition with original key fragments where a map reference is
needed; do not recreate application atoms to compute a reference. Keep binding
checks and actual assertion replay before observation work.

The current general graph APIs and their durable version-2 answers stay under
their existing declared formats. Unpromoted managed-v1 experiments are retained
as historical data, with their refusal/gaps explicit. Do not silently relabel
one profile's record as another profile's execution.

## Preserve the actual scope of proof and resource checks

Raw key traversal is not structured-value materialization. Preserve deferred
materialization, unsupported concrete operations and canonical-coordinate
rules. Every scalar sort declaration, including an unused quantifier binder,
still passes the strict preconstructor gate. Native deadlines stay 500/2000 ms
in the comparison corpora. Keep actual owner retirement and mixed import
allocator checks.

This codec/key decision does not settle future language numeric equality or
ordinary map/set key semantics. Exact graph identity must keep saved data
readable independently of those preview language choices.

## Concrete next batch and qualification

1. Implement the SDK raw-key inventory and versioned owner observation rows.
   Add tests using unknown outer/nested keyword *bytes* that remain absent
   after both admission and native execution. Include original key identity,
   deterministic order and all-entry traversal checks.
2. Adapt the 118-assertion staged language request/answer/effect/ledger code to
   the new inventory/output contract. Its existing basic Int/native/lifetime/
   in-memory ledger tests pass on the exact candidate-3 SDK; arbitrary graph
   keys and fresh persisted ledger consumers remain unqualified.
3. Commit the full runtime source batch, run Source preflight, build one new
   immutable SDK and reuse it. Record candidate 3 as an unqualified preparation
   predecessor, keeping SDK46 as the qualification baseline.
4. Run focused admission/owner/key/primitive and applicable regression checks.
   Compare complete generic inventories before migrating the project inventory
   to an SDK delegate. Retain the exact legacy/native questions and statuses.
5. Run both native corpora and two genuinely fresh SDK-only readers with no
   application import path, no input atom creation and no source-payload
   execution. Preserve false-point and assurance tamper controls.
6. Exercise the common request interface and actual persisted-ledger reopening
   in separate processes. Complete its formal effect/ledger SDK integration
   without adding proof or execution authority to recorded labels.
7. Promote only after these gates, then execute/check actual Org cells,
   activate the exact SDK and inspect the real browser presentation.
