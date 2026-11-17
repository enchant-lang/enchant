# Workstream SERVICES: self-hosting the runtime-service host modules

Owner files: `priv/host/{record,server,supervisor,trace,atom_guard,link,emit,tiers,loader}.bl`
(none edited), the leaves of those modules and of `Env`/`AOT`/`Compiler`/`Code`/`host`/
`crypto`/`Base` in `host/host-compiler.scm`, and `host/native-readiness.scm`,
`host/host-source-frames.scm`, `host/native-text.scm`.

New files: `speed/services/emit.bl` (pinned-SDK emitter and BEAM oracle),
`speed/services/check.py` (gsi differential), `speed/services/closure-additions.edn`.

## 1. Classification

Kinds:
- **replica**: the logic has a BL definition and the Scheme reimplements it.
- **primitive**: categories (a)–(d) of CONTRACT2.
- **service**: the native counterpart of a BEAM VM service (ETS registry, code
  loading, the atom table, the filesystem). The BL definition is bound to that service.
- **refusal**: a named `native-unavailable` stub. It has no logic, and calling it
  raises. It is the native answer for a BEAM-only capability.

### Leaves in `host-compiler.scm`

| Leaf(s) | Kind | Native counterpart / reason | Action |
| --- | --- | --- | --- |
| `Server/callback/1`, `Server/callback_order/0` | replica | literal tables copied from `server.bl` | **deleted**; compiled `host.server` |
| `Server/return_constructor_shapes/0` | replica | read a copy of the BL answer from bundle metadata | **deleted**; compiled `host.server` |
| `Server/module_for/2` | replica | its own camelize over `native-known-module` | **deleted**; compiled `host.server` |
| `Emit/module_for/1`, `Emit/base_module_for/1`, `Link/module_for/1` | replica | `native-known-module`: captured table, else its own CamelCase | **deleted**, with `native-known-module`; compiled `host.emit` / `host.link` |
| `Compiler/read_data/1` | replica (thin forwarder) | forwarded to `compiler/read_data` without the BL `string?` guard | **deleted**; compiled `host.compiler` |
| `Link/settle/0` | replica of a service answer | rebuilds BEAM namespace shims (`ets/match_object`, `publish_binaries!`). The native leaf answered `:ok`. | **deleted**. `link.bl settle` now returns `:ok` when `ets/whereis :beam_lisp_vars` is `:undefined`. That is the one `.bl` edit (see below). |
| `Tiers/boot_namespaces/0` | service (frozen data) | BEAM globs `priv/boot/*.bl`; native has no tier tree | kept. **The list was stale** (10 of the 16 names); now corrected, see Risks |
| `AtomGuard/{check!,account!,reset,to_atom}` | service | the BEAM atom-table watermark (`erlang/system_info :atom_count`). Native bounds new source symbols by count and bytes. | kept |
| `Loader/{ensure_loaded,ensure_ready,load_provider,resolvable?,declare_require,maybe_load_macro,source_decl}` | service | `loader.bl` (1.8 k lines) resolves files, AOT caches and the Loader.Server. Native has a closed, preloaded closure. | kept |
| `Env/*` (≈45 leaves: lookup, put_key, intern, fetch*, alias/refer/import, meta, match, public_names, …) | service | `env.bl` (8.9 k lines) is ETS/process-dictionary bound. The native registry is a sorted map of rows. | kept |
| `Env/check_source_*`, `Env/assert_native_framework_execution!/0`, `Env/os_env_call/2` | refusal | Source custody is BEAM-only | kept |
| `Record/{info,record_module?,deftype_module?,record?,fields_of}` | **replica over a service** | `info` is the closed native registry (empty). The other four repeat `record.bl`'s logic over `info`. | **Residual** (see below) |
| `Record/declaration_descriptor/4,5`, `Record/declaration_kind/3` | refusal | class publication is BEAM-only | kept |
| `AOT/*` (7) | refusal | staged-macro and constructor metadata need BEAM Source custody | kept |
| `Trace/trace/3,4`, `Trace/untrace/2` | refusal | tracing wraps live BEAM vars and processes | kept |
| `Server/{start,start_link,call,cast,stop}/*` (11) | refusal | OTP actor start and calls | **deleted**. Compiled targets win over leaves (CLOSURE), so these were dead. The compiled bodies raise through the refused `Env` start leaves. |
| `Supervisor/{supervise,worker}/*` | refusal | OTP actor start. `actor-links.edn` gives the seed path. | kept (`host.supervisor` is not compiled) |
| `host/{eval-scheme,eval-node,read-file,write-file,command-line}` | primitive (d) | Scheme eval and OS I/O. No BL source. | kept |
| `erlang/function_exported/3`, `erlang/term_to_binary/2`, `binary_to_term/2`, `monitor/2`, `exit/2`, `link/1` | primitive (b) / refusal | BIFs | kept |
| `Elixir.Code/ensure_loaded?/1`, `crypto/hash/2`, `Base/encode16/1,2` | refusal (b) | stdlib that is not provided natively | kept |
| new: `Macro/camelize/1`, `Module/concat/1,2`, `ets/whereis/1`, `erlang/error/3` | primitive (b) | Elixir/ERTS stdlib that the compiled modules need. `ets/whereis` answers `:undefined` because native owns no named table. | added |
| new: `native-service-refusals` (49 keys) | refusal | BEAM-only remotes named by the compiled modules: Source custody, actor start, code loading, ETS match, atomics, `persistent_term`, plus some stdlib only reached on unported paths | added |

### Host files

| File | Procedures | Kind |
| --- | --- | --- |
| `native-readiness.scm` | the poll(2) reactor and FFI job ownership (`native-readiness-*`, `native.readiness/*` leaves) | primitive (d). No BL source; `fixtures/actor-posix.bl` is only a caller. |
| `host-source-frames.scm` | the source-frame call/tail ABI (`bl-with-source-frame`, `bl-source-call`), trace capture, transport-leaf rebinding | primitive (a)/(d): the native counterpart of ERTS stack traces (JS: `callSrc`). No BL source. |
| `native-text.scm` | PCRE2 FFI, `Regex/*` leaves, regex branches of `String.replace`/`split`, `native-graphemes`, `string/to_float/1` | primitive (b)/(d) |
| `native-text.scm` | `(set! native-decimal-parse …)` | **replica** of `host/decimal.bl parse/1`. **Residual**: the `Decimal/parse/1` leaf belongs to DATA. |

## 2. Cutovers

Four namespaces are compiled: `host.emit`, `host.server` and `host.compiler` from
unchanged source, and `host.link` with one guard added to `settle`. `closure-additions.edn` lists them in dependency order.
`host.compiler` (`priv/host/compiler.bl`) is the pinned host module of
`Elixir.BeamLisp.Compiler`. Its `read_data` leaf was in scope.

Deleted leaves (20):
- replicas: `Server/callback/1`, `Server/callback_order/0`,
  `Server/return_constructor_shapes/0`, `Server/module_for/2`, `Emit/module_for/1`,
  `Emit/base_module_for/1`, `Link/module_for/1`, `Compiler/read_data/1`, `Link/settle/0`;
- dead refusals: `Server/{start/1,2,3, start_link/1,2,3, call/2,3, cast/2, stop/1,2}`.
Also deleted: `native-known-module`, the only Scheme copy of the module-naming algorithm.

Each module must link as a whole namespace. `emit.bl` records every remote's link
decision in `remotes.txt`: template, leaf, arity/variadic/generic cell, or missing. After
this change, the only missing remotes are calls into closure namespaces
(`Elixir.BeamLisp.Ns.{Core,Rt,Anf}`, `Ns.Lower` (stub) and `CompilerData`). The integrated
closure resolves those.

### The one `.bl` edit

`priv/host/link.bl settle`: the body now runs only when
`(ets/whereis :beam_lisp_vars)` is not `:undefined`. `emit.bl realm_of` already uses
the same idiom.
- BEAM: the registry exists whenever a shim can be pending, so the answer is unchanged
  (`test/bl/link_test.bl`, below). Before Env starts, `settle` used to raise `badarg`
  from `ets/match_object`; it now returns `:ok`.
- Native: `ets/whereis` answers `:undefined`, so `settle` returns `:ok`. This is the old
  leaf's answer, now produced by compiled BL.

### New primitive leaves (category b)

- `Macro/camelize/1`: Elixir's byte-wise clauses, including `__` collapse, `_<digit>`,
  `_<Upper>` kept, trailing `_` dropped and `/` → `.`.
- `Module/concat/1,2`: `:elixir_aliases.concat/1`.
- `ets/whereis/1`: `:undefined`.
- `erlang/error/3`: raises like `error/1`; the arguments only annotate BEAM frames.

`erlang/fun_info/2` is **not** added. The main thread adds it once at integration. The
compiled modules only reach it on `FunctionClauseError` paths.

### `closure-additions.edn`

`host.emit`, `host.link`, `host.server`, `host.compiler`, with modules
`Elixir.BeamLisp.{Emit,Link,Server,Compiler}`.

## Checks

The BEAM VM ran through `work run --memory 3G`, one at a time.

1. **Emission and BEAM oracle** (pinned SDK, one VM):
   ```
   work run --memory 3G --timeout 3600 -- research/native-seed/run run research/native-seed/speed/services/emit.bl -- \
     OUT LEAVES.txt host.emit=priv/host/emit.bl=Elixir.BeamLisp.Emit host.link=priv/host/link.bl=Elixir.BeamLisp.Link \
     host.server=priv/host/server.bl=Elixir.BeamLisp.Server host.compiler=priv/host/compiler.bl=Elixir.BeamLisp.Compiler oracle
   ```
   Output: `SERVICES_EMIT` for host.emit (30 definitions), host.link (7), host.server (13)
   and host.compiler (17), then `SERVICES_ORACLE 148 cases` and `SERVICES_ORACLE_ENV global`.
   - `LEAVES.txt` is the registered-leaf set of this checkout's host. It was observed with
     a gsi registry probe, then the deletions and additions were applied, plus the
     native-text keys.
   - Emission uses `native.scheme` with `:aot-link` in the order of
     `native.bootstrap/remote-decision`: template, then compiled target, then leaf.
   - `remotes.txt` has two unresolved non-closure remotes: `erlang/fun_info/2` (main
     thread) and `CompilerData/check_reader_data!/1` (closure member).
2. **gsi differential**:
   `work run --memory 3G -- python3 research/native-seed/speed/services/check.py OUT`.
   The program loads this checkout's host sources, then the round-1 `text.o1` addon, then
   the round-1 prelude's compiled closure, then the emitted modules, then the checks.
   Result: **`SERVICES_CHECKS 172 FAILURES 0`**.
   - 148 BEAM-vs-native outcomes through the dynamic `native-remote` path:
     - `Server/callback/1` ×11 and `callback_order/0`;
     - `return_constructor_shapes/0`;
     - `Server/module_for/2` ×38, including two raising inputs;
     - `Emit/module_for` ×19, `Link/module_for` ×19, `Emit/base_module_for` ×20;
     - `Emit/realm_of` ×19 and `realm_base` ×4;
     - `Compiler/read_data/1` ×13, including non-binary and unbalanced inputs;
     - `Link/settle/0`, `Server/start/1` and `Server/call/2`.

     The namespace names cover `_`, `__`, `_X`, `_1`, `/`, `-`, empty, leading and
     trailing `_`, `..` and non-ASCII.
   - 20 checks that each deleted leaf is absent from the registry.
   - 2 direct AOT cell calls: `host.server/callback$1` and `host.emit/base_module_for$1`.
   - 2 service checks: compiled `settle` → `:ok`, and `Tiers/boot_namespaces/0` equals
     the pinned SDK's sorted `priv/boot/*.bl` minus `data-readers`.

   The first run without `text.o1` failed 3 `read_data` cases. The cause was
   `string/to_float/1`, which is a native-text leaf, and the old forwarder failed the same
   way. Loading the addon, as `prepare-host.py` does, fixed it.
3. **Host fixtures**:
   `work run --memory 3G -- python3 research/native-seed/check-host.py --out …/services-out/host`.
   All 11 stages PASS: values-control, lazy-memo, storage-and-raw-leaves, source-frames,
   foreign-fixture and the POSIX C link/object/readiness stages.
4. **BEAM** (one batch): `work run --memory 3G -- ./bin/bl --cold test test/bl/link_test.bl`,
   then `./bin/bl realm stop`: **`link-test 45 passed`, all green.**

Skipped, per the coordinator's rules: every speed or timing measurement, the actor corpus
and any image or SDK build.

## Residual replicas

- **Record** (`Record/{info,record_module?,deftype_module?,record?,fields_of}`).
  - `record.bl` keys its registry on `{self-mod, :registry}` in `persistent_term`, and
    `self-mod` is `erlang/fun_info(fn, :module)`. It also needs `Env/with_module_locks`,
    `class_schema_held?`, `global/trans`, `beam_lib/md5`, `code/get_object_code`, MapSet
    and more.
  - The four predicates repeat BL logic over `info`, which is the native closed (empty)
    registry.
  - To cut over: wait for the main thread's `erlang/fun_info/2` leaf. Then compile
    `host.record` with `persistent_term/get,put` as a real native table (category b) and
    refusals for the class-publication remotes. Then run this same differential over
    `info`/`record_module?`/`record?`/`fields_of` on struct, non-struct and atom inputs.
- **Tiers/boot_namespaces/0** (service with frozen data).
  - It was stale: it listed 10 names, and the pinned SDK answers 16.
  - `compiler.bl ns-boot-tier?` uses this list to skip readiness guards, so the stale
    list made the native compiler emit `Loader/ensure_ready` guards on calls into
    `binding`, `expand`, `expand-source`, `lower-core`, `server-clause` and `syntax`.
    BEAM emits none, so self-emission diverged (P).
  - It is corrected now and checked against the pinned `priv/boot`, but it is still a
    literal.
  - Proper fix (CLOSURE, `chunks.bl bundle-metadata`): record
    `:boot-namespaces (BeamLisp.Tiers/boot_namespaces)` as `return-constructor-shapes`
    is recorded, and have the leaf read the bundle metadata.
- **`native-text.scm` `(set! native-decimal-parse …)`** is a replica of `decimal.bl
  parse/1`. `Decimal/parse/1` belongs to DATA. Delete this `set!` in the same change that
  cuts `Decimal/parse/1` over to compiled `host.decimal`, which uses these Regex leaves.
- **AtomGuard, Loader, Env** are services, not replicas. Their BL definitions are bound
  to the atom table, file and AOT loading and ETS respectively. No smaller shared
  algorithm could be checked within budget. The only candidate was AtomGuard's limit
  message, and native uses a different policy.
- **Supervisor, Trace**: refusal leaves only (no logic). Compiling them needs the actor
  runtime checks that the actor corpus provides, and that corpus is unavailable to this
  workstream.

## Risks for integration

- **Compiled-wins linking.** All 11 `Server` start/call refusal leaves are deleted, so
  `function_exported(BeamLisp.Server, :start, 1)` now answers true natively (as on BEAM).
  Calling it raises `native compiler excludes BEAM Source custody` from a refused `Env`
  leaf instead of from the old `Server` refusal.
- **Leaf collisions.** `native-service-refusals` registers a key only when no earlier
  host file provides it. A real implementation loaded *later* (for example
  `host-kernel.scm`, or the main thread's leaves) collides: either drop the key from this
  list, or load the provider first.
  - The list holds general stdlib keys: `Enum/member?/2`, `Enum/any?/2`,
    `Enum/find_value/2`, `Enum/group_by/3`, `Enum/uniq_by/2`, `Map/put/3`,
    `Keyword/get/2`, `Integer/to_string/1`, `Tuple/insert_at/3`,
    `String.Chars/to_string/1`, `Access/get/2`, `persistent_term/*`.
  - If DATA or LAZY add real versions of any of these, theirs should win. These keys are
    only reached on unported paths of the compiled modules.
- **New leaves `Macro/camelize/1`, `Module/concat/1,2`, `ets/whereis/1`, `erlang/error/3`**
  use plain `native-add-leaf!`, so a duplicate registration fails loudly.
- **Module identity.** Compiled `Emit/module_for` no longer consults the captured
  `native-namespace-modules` table. It computes `Macro.camelize`/`Module.concat` exactly
  as BEAM does for the global realm. For every closure namespace, the captured
  identities came from the same function on BEAM. They still feed `native-module-names`.
- **Global references** in the emitted modules go through `native-global` in this check,
  because the ledger lives in the integrated closure. At integration they link to `$g`
  cells.
- **`priv/host/link.bl` changed**, so `update-closure.bl` recompiles `host.link`, and the
  pinned host beam for `BeamLisp.Link` changes at the next SDK.
