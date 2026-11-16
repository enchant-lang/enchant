# FRONT: D (load-independent compiled ANF) and T (BEAM invocation toll)

Branch `native-self-front`. Files: `priv/boot/compiler.bl`, `priv/boot/rt.bl`
(only the gate functions `source-callable!`, `source-invocation!`,
`source-invocation1!`, `source-invocation2!`; `call-invoke` is unchanged and now
reaches the cheap gate), `priv/host/env.bl` (`source_head`, plus the owner-side
writes of pid-keyed head rows, see "Ownership note").

## D: compiled ANF no longer depends on what the VM has loaded

**Cause.** A cross-namespace call compiled to a guarded direct call
(`Loader/ensure_ready` followed by `Module:fun`) only when the provider's
registry link row existed, that is, once the provider was initialized. Before
that it compiled to `invoke(global-exact …)`. `string/join` in `native.scheme`
therefore compiled two ways depending on whether `clojure.string` had loaded.

**Fix (compiler.bl).** When the link row is absent, `compile-call` asks
`declared-link`, which takes the triple from the provider's declared interface.
It reads the provider's source under the search dirs its `:require` was
declared with, without evaluating anything. Every top-level
`defn`/`defn-` inside `(ns provider)` goes through the same
`defn-clauses-of` → `prelink-info` path that AOT prelink and `Link.defvar` use.
The result is memoized per process by the md5 of the exact source bytes. The
result is the same triple the provider installs when it loads, so the call is
the same artifact before and after loading. The readiness guard is emitted as
before: it is a constant fact (foreign, non-boot provider) and initializes the
provider at first call.

New functions: `provider-source`, `scan-declared-links`, `declared-links`,
`declared-link`, `declared-refer-link`. The bare `:refer` path (`link_owner`
returning `:error` for a deferred, not-ready refer source) uses the same
mechanism. Changed: `compile-call`, in its qualified-var and bare-symbol
branches.

The scan is consulted only when all of these hold:
- the provider is not the current namespace and not in the boot tier;
- the provider is not `loaded_ns?`;
- the provider is declared deferred (`deferred_dirs` is set by the header's
  `:require`);
- the member is not yet a var.

When the provider is loaded, its own link rows answer, and a var without a link
row stays a value (invoke). On the native compiler image every provider is
loaded, so the scan never runs there. Its behaviour, and the native/BEAM
emission parity, are unchanged.

### Check: `incr.bl` identity

`work run --memory 4G --timeout 1800 -- ./bin/bl --cold run research/native-seed/speed/bigo/incr.bl` (and `-- reset`):

| | before | after (both modes) |
|---|---|---|
| same source | changed 12 of 67 (clauses emit-multi … with-subject) | **changed 0 of 67** |
| comment+reindent | changed 12 of 67 | **changed 0 of 67** |
| one body | changed 13 of 67 | **changed 1 of 67 ("ident")** |

After the fix, `literal-items` compiles to the same
`(do (ensure_ready "clojure.string") (Clojure.String:join …))` on both
compiles ("first difference at 393 of 393", which means identical).

## T: the per-invocation gate

**What the gate guarantees.** Only this: inside an admitted Source extent of
the calling process, every invoked callable and its actual arguments pass
Env's capture and target policy (`check_source_invocation*`). "Admitted" means
a pid-keyed row in Env's protected `beam_lisp_source_extent_heads` table.
Outside every extent, `source_head` is nil and the gate does nothing. The gate
does not cover readiness, interrupts or source frames. Those are separate
mechanisms.

**Before.** Every invocation ran `erlang:function_exported/3` in rt, then a
remote call into Env. `source_head` then ran `ets:whereis`, `persistent_term:get`
(the table proof) and `ets:lookup(self())`. `check_source_invocation1!/2!`
then called `source_head` a second time.

**After (structural).**
- Env publishes one `atomics` cell at persistent_term key
  `:bl_source_extent_heads_live` when it creates the heads table, and keeps it
  equal to the number of pid-keyed head rows. Only the table owner writes the
  table (it is protected, and every write runs inside `source_private`), so the
  count is exact. The helpers are `source_head_put!` and
  `source_head_delete!`, used at every pid-row write: push, leave, departed
  cleanup, and the owner-transition window's save and restore.
- In rt, each gate function first reads `persistent_term:get` plus
  `atomics:get`. A count of 0 returns `f` at once: there is no
  `function_exported`, no remote call into Env, and no ETS access. A nonzero
  count, or no published cell (early recovery, or a host without Env custody),
  runs the previous code unchanged.
- `source_head` has the same zero-count fast path, so `source_execution_active?`
  and every other Env reader also skip ETS when no extent exists anywhere.

So on the compile path (no Source extent), the entries the study listed
(`source_head`, `function_exported/3`, `ets:whereis`, `ets:lookup`, the
persistent_term table proof, `Env.check_source_invocation*`) are no longer
called per invocation. `persistent_term:get/2` (cell lookup) and
`atomics:get/2` remain, once each per invocation. I did not profile this
afterwards, per the updated rules.

**Semantics preserved.** A process in an extent always has its row counted, so
it always takes the full check. A count can only be too high (a failure is
fail-safe), never too low, because increment and decrement are tied to the
actual row's presence by `ets:member` in the single writer.

## Focused tests

One batch (`work run --memory 4G --timeout 1800 -- ./bin/bl --cold test …`),
then `./bin/bl realm stop`. It ran before the `:managed-source` restriction
below.

| file | result |
|---|---|
| macro_core_alias_test | 3 passed |
| codebase_alias_reachability_test | 38 passed |
| compiler_invocation_test | 28 passed |
| optimizer_canonical_invocation_test | 4 passed |
| env_fetch_memo_test | 26 passed |
| boot_namespace_readiness_test | 25 passed |
| namespace_demand_test (incl. the AOT direct-call guard and deferred init) | 52 passed |
| reload/native_source_extent_test (Source extents, gate) | 75 passed |
| js_source_gate_test | 2 passed |
| system/analysis_alias_context_test | 4 passed |
| contextual_namespace_require_test | 33 passed |
| namespace_readiness_fast_path_test | 1 passed, 1 errored: assertion `(= (Path/join sdk "image/priv") (Tiers/priv_root))`. This is about the environment (the test expects to run from an SDK image) and does not involve my code. Not checked at the base commit. |
| proc/message_readiness_test | 3 errored: `unsealed-compiled-dependency` for `Datom.Query.Read-only` |
| reload/prepared_callback_arguments_test | 5 errored: `undeclared-native-target` for `Reload.Prepared-callback-fixture` |

The last two were caused by D. `reload.generation` compiles with
`:managed-source true`, and its admission (`check-anf!`, `compile-exact`)
accepts a direct call only into modules of already-analyzed namespace
inventories. An unloaded stable provider now got a direct call, which was
refused. Fix, committed after that batch: `declared-link` is not consulted
under `:managed-source`, so managed generation compiles are exactly as before.
**These two files were not re-run** (the updated rules allow one test batch).
The main thread should re-run
`test/bl/proc/message_readiness_test.bl test/bl/reload/prepared_callback_arguments_test.bl`.

## Skipped under the updated rules

- The after-profile (`profile.bl -- 1024 compile wide-let`) and any
  before/after timing. The before-profile I captured earlier showed the gate
  entries at about 24% of self time; it is not used as a gate.
- A baseline run of the failing tests on the base commit.

## Ownership note

Besides `source_head`, the T fix had to touch the owner-side writes of
pid-keyed head rows in env.bl: Agent init, `source_push!`, `source_leave!`,
`source_owner_departed_rows!` and `owner_transition_native_window`. It also
adds two private helpers. Each write is a one-line swap of `ets/insert` or
`ets/delete` for the counting helper. No other workstream owns env.bl.

## Risks for integration

- **Native (KERNEL).** Once `kernel-override` for the gate functions is
  removed, natively compiled rt.bl calls `persistent_term/get/2` and
  `atomics/get/2`. The host needs a `persistent_term/get/2` leaf (category b)
  that returns the default (nil). The gate then takes the old path exactly as
  today.
- **Native compiler image (CLOSURE/SERVICES).** compiler.bl now references
  `Loader/with_search_dir`, `Loader/source_content`, `Env/deferred_dirs`,
  `Ns.Reader/read_all` and `erlang/md5`. They are reached only for an unloaded
  provider, which never happens natively, but if unresolved leaves are a
  build-time error, they need stubs.
- **Residual D cases.** The result is still load-dependent where the source
  scan cannot see the definition:
  - a `defn` produced by a macro, or nested in a top-level `do`/`when`;
  - a provider redefined at the REPL, or edited on disk but not reloaded;
  - a deferred provider with no source;
  - `:managed-source` generation compiles, which are deliberately excluded
    (their admission is defined over loaded inventories; a fix belongs in
    `reload/generation.bl`).
- **Scan cost.** For each compiled call into an unloaded deferred provider, the
  scan reads that provider's source file (parsing is memoized by digest). This
  is the same discipline as `Loader/source_decls` outside a pass.
- **Semantics change.** A call into an unloaded deferred provider is now a
  direct guarded call, not a fetched global. If the source declares an arity
  the loaded code lacks, the failure is `undef` instead of an arity error.
- **Stale cell.** The persistent_term cell survives an Env crash. A stale
  nonzero count only costs speed. A stale zero with a squatted table skips the
  owner-mismatch error, which only fired on reads anyway, while no real Env
  extents can exist.
- **Seed floor.** I did not regenerate it (I am not allowed to). compiler.bl,
  rt.bl and env.bl changed, so the main thread must regenerate it.
