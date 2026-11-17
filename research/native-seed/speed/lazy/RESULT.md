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

`priv/host/lazy_seq.bl` detects cycles where they happen (and `realize_step`
calls `force_state` instead of the bare name `force`: under the namespace compile
the native closure uses, `force` resolves to core's Deferred `force`, which
answers a lazy node unchanged, so native `realize` looped):

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
- `host/host-leaves.scm`: `native-lazy?` and `native-cursor?` are now plain
  struct-tag predicates there (category a), because `native-finite-items`,
  `host-extra.scm`'s kind test and `host-compiler.scm`'s sequence projection use
  them.
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

All VMs under `work run`; the pinned-SDK runs go through `research/native-seed/run`.

| Check | Command | Result |
| --- | --- | --- |
| BEAM lazy tests (one batch, after the M commit 09117c1c5) | `work run --memory 4G --timeout 2400 -- ./bin/bl --cold test test/bl/host_lazy_memo_test.bl test/bl/host_lazy_seq_test.bl test/bl/lazy_pressure_cycles_test.bl test/bl/lazy_clean_capture_test.bl test/bl/lazy_scaling_test.bl test/bl/memo_bounds_sunset_port_test.bl test/bl/lazy_budget_test.bl test/bl/lazy_fold_test.bl test/bl/lazy_producers_test.bl test/bl/sdk_lazy_library_context_test.bl test/bl/legacy_wave23_lazyseq_test.bl test/bl/host_seq_cursor_test.bl` | 10 files green (host_lazy_memo 19, host_lazy_seq 207, pressure_cycles 37, scaling 26, budget 66, fold 468, producers 226, sdk_lazy_library_context 8, legacy_wave23 64, host_seq_cursor 175, including the new cross-process `:recursive_force` and alias cases). 3 failures: two reduction-ratio asserts in lazy_clean_capture_test (since replaced by structural no-edge tests, see Risks) and `memo_bounds_sunset_port_test/elixir-source-is-confined-to-reviewed-native-drivers`, which lists `research/native-seed/evidence/values-parity/beam-oracles/*.exs` from round 1 and is unrelated to this change |
| Native emission | `research/native-seed/run run research/native-seed/speed/lazy/emit.bl -- MAIN/research/native-seed/out OUT` | 6 namespaces, 132 definitions, **0 unresolved remotes**; 18 `fun_info(fn, :module)` reads linked to the unit module; 2 `fun_info(var, :arity)` stay dynamic |
| BEAM oracle | `research/native-seed/run run research/native-seed/speed/lazy/oracle.bl -- OUT` | 28 cases written |
| Native differential (gsi) | `python3 research/native-seed/speed/lazy/check.py MAIN/research/native-seed/out OUT` (assembles `OUT/check.scm`; gsi under `timeout 600`) | **`LAZY_CHECKS 28 FAILURES 0`**: map/filter/remove/iterate/concat/lazy-cons/take-while/drop-while/mapcat/partition/interleave/distinct (Seen), cursors over 35- and 100-element inputs, count/nth over 100/1000, fold path (`reduce` of `take`), transducer `into`, realize-once memo, empty/nil seqs, `realized?`, delay force/deref/realized, failure then retry (thunk ran twice), alias cycle `:cyclic_memo`, re-entrant force `:recursive_force`, self-embedding value accepted. The native compiler itself (reader, compiler, emitter of the integration prelude) runs on the compiled lazy modules for every case |
| Native memo fixture | gsi over `host.scm host-values host-leaves host-extra native-memo.scm fixtures/native-memo-check.scm` | `native memo checks: 27` (the count `check-host.py` asserts) |

The differential's harness-only pieces, all in `check.py`: `Tiers/priv_root/0`
(SERVICES') and `erlang/fun_info/2` stand-in leaves (the main thread owns the
real one); `native-text.scm`'s FFI leaves as refusals, a PCRE-free
`string/to_float/1` and an ASCII grapheme adapter, because gsi cannot load the
FFI file. The corpus spells `lazy-seq`/`delay` as their expansions because the
native image's runtime eval has no such macros.

## Residual replicas

None. `host/host-lazy.scm` is deleted and no `LazySeq`/`SeqCursor`/`Deferred`/
`LazyMemo`/`Delay` leaf is defined in host Scheme. Not compiled natively, and so
listed in `closure-additions.edn` neither: the protocol impls
`lazy_seq_enumerable.bl`, `lazy_seq_inspect.bl`, `seq_cursor_enumerable.bl`
(Elixir protocol dispatch has no native counterpart; nothing native reached them).

## Risks for integration

1. **Not yet run after the last BL edit**: `lazy_seq.bl realize_step` now calls
   `force_state` (equivalent on BEAM: `force` = `lazy?` check + `force_state`, and
   the argument is always a lazy node there), and lazy_clean_capture_test's two
   cost asserts became structural tests. Next step: the main thread's single
   `./bin/bl --cold test` batch above, then `./bin/bl realm stop`.
2. **check-host.py not run in full** (its POSIX step compiles C); only its
   memo step was reproduced. Next step: `python3 research/native-seed/check-host.py`.
3. **Native processes**: the compiled force protocol waits on another process
   with `Process/monitor` + `receive`; the native image has neither, so those
   leaves refuse as unavailable. The deleted host-lazy spun with `h-park "yield"`
   when another actor frame owned a running cell, and its `h-set-state` observer
   made a dead owner's cells terminal. A native actor program that forces one lazy
   seq from two frames while the owner parks inside the thunk now raises instead
   of waiting. Not exercised (the actor corpus is forbidden here). Next step: run
   the proc corpus at integration; if it trips, give `Process/monitor`/`receive`
   their actor-runtime counterparts (category d), not a lazy replica.
4. **Semantics change of M**: a value that embeds its own node, and a failure
   reason that holds it, are now accepted; with the NIF collector off
   (`collector_status` non-empty) such dropped cycles leak, as atoms already did.
   `bench/memocell_bench.bl` and `!tasks/artifacts/performance-runtime-probes.bl`
   call the deleted `LazyMemo/dependencies` (not run by any test).
5. **Native `LazySeq/cell` of a string** now answers graphemes (BEAM's answer)
   instead of the string itself, through the `native-text` grapheme adapter.
6. `speed/kernel/kernel-check.scm` (KERNEL's) still calls `native-lazy-new`.
7. Host source lists (`prepare-host.py`, `check-host.py`, `check-compiler.py`,
   `check-self-emission.py`, `build-host-parts.py`) append `host/native-memo.scm`
   in place of `host-lazy.scm`; CLOSURE owns the final lists. native-memo.scm must
   load after `host-values.scm` (it wraps `native-register!`) and before any
   compiled `host.lazy-memo` unit. It defines no `persistent_term` or `fun_info`
   leaf.
8. Shared host files: `host-extra.scm` (Delay deref via the Deferred remote),
   `host-leaves.scm` (two tag predicates), `fixtures/host-extra-check.scm`; small
   separate hunks.

## Skipped (coordinator rules of this round)

- The deep-fn scaling slope (`speed/bigo/scaling.bl -- 64 256 1024`) and a
  reductions-per-cell calibration were dropped from acceptance: no before/after
  timing in agents. The calibration run was stopped before it produced numbers
  and its script deleted. The main thread's final benchmark measures M.
