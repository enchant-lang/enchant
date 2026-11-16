# Workstream LAZY: lazy cells stop walking what they capture, and lazy self-hosts

Items: **M** (big-O study) and **self-host lazy** (CONTRACT2.md).

## M: cycles are detected at force time

### What changed on BEAM

`priv/host/lazy_memo.bl` no longer walks anything. Deleted: `dependencies/1`,
`deps_walk/6`, `deps_scalar?`, `deps_lazy_node?`, `deps_scalar_list?`, `deps_env/3`,
`deps_big?`, `deps_shape`, the clean-value identity memo (`deps_clean_*`,
`deps_walked!`, the `:bl_deps_clean_*` process keys), `deps_merge_resources` and
`plain!/1`. `create/1` passes `()` as edges, `exchange/3,4` is `exchange_ref`
(no edges), and `cursor/1` passes `()`. The NIF API is unchanged; the Rust is
untouched. The memo graph is therefore always empty, so `would_cycle` is never
true and the NIF never answers `:cycle` for a host call.

`priv/host/lazy_seq.bl` detects cycles where they happen:

| Cycle | Detected by | Answer |
| --- | --- | --- |
| a re-entrant force by the cell's owner | `force_state` (unchanged): the owner finds its own `:running` cell | terminal `:recursive_force` |
| two or more processes forcing each other's running cells | `wait_for_attempt`: before blocking, record `:bl_lazy_waits_on owner` in the process dictionary, then follow those entries from the owner with `process_info(Pid, {dictionary, Key})` (`wait_cycle?`). Reaching self raises. Entries exist only while a force is blocked and are erased on every exit (`join_attempt`) | `ForceError :recursive_force` in the waiter; each thunk in the cycle then fails (retryable) and its waiters replay that failure |
| a completed value that aliases its own node, directly or through a chain of completed nodes | `publishable` / `alias_cycle?` / `alias_link?` in `publish_attempt`: one constant-size `peek` per chain link; only a `:completed` link's value is read | terminal `:cyclic_memo` |

A value that merely **embeds** its own node (`(list 1 self)`, a map holding it,
a failure reason carrying it) is ordinary data and is published. This is the
contract change item M asked for: the old walk refused it as a "retained cycle".
The NIF's cycle collector (its own census, not the edge graph) reclaims such
cycles once dropped, as it already did for atoms. `attempt_deps/1` now always
answers `:keep`.

Cost per cell in BL: O(1). Creating a cell still copies the thunk into the NIF
and `estimate_bytes` still calls `erts_debug:flat_size`; both are C-level and
outside this item. Per the updated coordinator rules no before/after timing or
slope is part of this workstream's acceptance (see Skipped).

### Tests rewritten for the new contract

- `test/bl/lazy_clean_capture_test.bl`: was the clean-capture memo's test. Now:
  creating a cell records no edge for its capture (an explicit edge back to the
  creator is accepted by the NIF); a publish records no edge for its value (two
  nodes publishing each other is accepted); the walk and memo exports are gone;
  self-alias and a completed alias chain are `:cyclic_memo`; a re-entrant force is
  `:recursive_force`; two tasks forcing each other's running cells both get
  `:recursive_force` and leave no `:bl_lazy_waits_on` entry; a value embedding
  its own node is data.
- `test/bl/memo_bounds_sunset_port_test.bl`: the three retained-cycle cases became
  `the-nif-still-refuses-explicit-cyclic-edges-and-the-host-passes-none`,
  `a-published-value-may-embed-its-own-node` and
  `a-failure-diagnostic-may-retain-its-own-memo`. The alias case
  (`a-result-that-refers-to-its-evaluator-is-rejected-on-the-first-force`) is
  unchanged and still passes.
- `test/bl/host_lazy_memo_test.bl`: the export list drops the walk; a new
  assertion checks the walk and memo are not exported; the pure-predicate test
  became `estimate-bytes-answers-without-the-nif`.
- `test/bl/host_seq_cursor_test.bl`: one comment.
- Unchanged and green: `host_lazy_seq_test` (recursive, direct and pair cycles),
  `legacy_wave23_lazyseq_test` (direct and indirect alias cycles).

## Self-host lazy

### `host/host-lazy.scm` is deleted

It replicated `lazy_seq.bl`'s force protocol and realization, `lazy_memo.bl`'s
policy, `seq_cursor.bl` and `deferred.bl`, and registered 33 leaves under
`Elixir.BeamLisp.{LazySeq,SeqCursor,LazyMemo,Deferred}`. Its fixture
`fixtures/host-lazy-check.scm` is deleted with it. No leaf of those modules is
left in host Scheme (`grep` over `host.scm host/*.scm`).

### `host/native-memo.scm` (new): the NIF's native counterpart

One procedure per NIF function `lazy_memo.bl` declares, under the NIF's name
(`native-memo-nifs`): `nif_loaded?`, `nif_runtime_identity`, `nif_new[_fast]`,
`nif_read[_fast]`, `nif_read_versioned[_fast]`, `nif_exchange_version[_fast]`,
`nif_exchange_version_admitted[_fast]`, `nif_compare_exchange[_fast]`,
`nif_put[_fast]`, `nif_id`, `nif_resource_id`, `nif_dependency_resource`,
`nif_peek`, `nif_stats`, `nif_retained_bytes`, `nif_reserved_bytes`,
`nif_fast_lane_bytes`, `nif_set_fast_lane_bytes`, `nif_cursor`,
`nif_cursor_chunk[_fast]`, `nif_cursor_dirty_chunks`, `nif_seen_new`,
`nif_seen_admit`, `nif_collect_cycles`, `nif_collector_status`; the four
`nif_file_*` lock functions refuse as `native_unsupported`.

Binding works like `load_nif`: `native-register!` of a `host.lazy-memo/nif_*`
stub publishes the native procedure instead, so linked call sites, arity cells
and the global view all see it. A cell is a native reference (`is_reference`
true, `=:=` identity) whose record `#(id version state bytes)` sits in a weak
table. Versions, notifications, budget admission (growth against retained bytes)
and the 32-head cursor index follow the Rust. Edge arguments are accepted and
ignored, because the BL host passes none.

The file also carries the category (b)/(d) leaves the compiled modules call and
the native image lacked (21 keys, `speed/lazy/leaves.txt`): `erlang/self/0`,
`node/0,1`, `process_info/2` (dictionary items of self), `fun_info/2` (`:arity`),
`garbage_collect/0`, `system_info/1` (`:wordsize`), `nif_error/1`,
`erts_debug/flat_size/1`, `System/monotonic_time/1`, `Application/get_env/3`,
`Integer/to_string/1`, `Path/join/2`, `Enum/take/2`, `Enumerable/impl_for/1`; and
refusing ones for `Process/monitor/1`, `Process/demonitor/2`, `Process/sleep/1`,
`erlang/load_nif/2`, `global/trans/2`.

### Other host edits (small, references to deleted procedures)

- `host/host-extra.scm` deref: a `Delay` is forced through
  `(native-remote "Elixir.BeamLisp.Deferred/force/1")`.
- `host/host-compiler.scm` `native-canonical-sequence-items`: the cursor test is
  the struct-tag test.
- `fixtures/host-extra-check.scm`: the two "storage-only host refuses lazy
  values" cases build the struct shapes directly.
- Host source lists: `host/host-lazy.scm` replaced by `host/native-memo.scm` in
  `prepare-host.py`, `check-host.py`, `check-compiler.py`,
  `check-self-emission.py`, `build-host-parts.py`. `check-host.py` runs
  `fixtures/native-memo-check.scm` (27 checks) in place of the old lazy fixture.
  CLOSURE owns these lists and finalises them.

### `speed/lazy/closure-additions.edn`

`host.lazy-seq-force-error`, `host.lazy-memo`, `host.seq-cursor`,
`host.lazy-seq`, `host.delay`, `host.deferred`, in dependency order, with their
pinned module atoms.

### Request to CLOSURE: `fun_info(F, :module)` is a link-time fact

The lazy modules read their own module atom with
`(erlang/element 2 (erlang/fun_info (fn [] nil) :module))` (struct tags, the
module-exact self call in `SeqCursor/cell`, error metadata), so the same source
serves production and probe compiles on BEAM. A native closure does not know its
module. `speed/lazy/emit.bl` answers it in the AOT link context: a
`:remote erlang/fun_info/2` whose first operand is a `:fn` literal and second
the literal `:module` emits `(bl-make-tuple (bl-key "module") (bl-key "<unit
module>"))`. `native.chunks/checked-context` needs the same rule (it knows each
unit's `:module`). Without it every `SeqCursor/new` and `Delay/new` raises
natively.

## Checks run

(filled in below with commands and results)

## Residual replicas

## Risks for integration

## Skipped (coordinator rules of this round)
