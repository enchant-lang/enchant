# Workstream CLOSURE: closure extension and self-emission parity (P)

Branch `native-self-closure`. Contract: [`../CONTRACT2.md`](../CONTRACT2.md).

## 1. Closure extension

### Declaring an addition

Every workstream writes `research/native-seed/speed/<ws>/closure-additions.edn`,
a vector in dependency order:

```clojure
[{:ns "host.vector" :path "priv/host/vector.bl" :module :Elixir.BeamLisp.Vector}]
```

`:module` is given only for a pinned BL host module. Its source header must say
``the pinned HOST MODULE for `Elixir.BeamLisp.Vector` ``; the update checks it.

### What `update-closure.bl` does

`src/native/update-closure.bl DIR/partition.json [ADDITIONS.edn …]`. With no
file argument it reads every `speed/*/closure-additions.edn`, sorted by path.

1. Existing members: reused when their source SHA is unchanged, recompiled
   otherwise. A recompiled member may require only closure members, stubs or
   declared additions. Any other dependency is still refused with
   `added dependency requires explicit closure extension`.
2. Additions, in declared order: compiled with `js.build/prepare-ns`. An
   addition may require only members, stubs and *earlier* additions. It goes
   into `:order` right after its last closure dependency, and never before
   `rt`/`core`/`sugar`. If it is already a member, it is just a member (the
   update is idempotent).
3. Order check: every member that requires an addition comes after it.
4. `:host-modules` (new closure metadata key) is a sorted vector of
   `[ns module]`: the three existing host members (`host.compiler-data`,
   `host.form-meta`, `host.meta`) plus each declared `:module`. One module per
   namespace and one namespace per module. Each header is checked.
5. Macro providers (the known `priv/lib/live/app.bl` trap). A provider is now
   read from **where the pinned compile loads it**:
   - closure members and `research/native-seed/src/**` come from the checkout
     (`-p` path);
   - every other `priv/{boot,lib,std,compat}` source comes from the pinned
     SDK's immutable Source (`sdk-pin.json` `source`).

   Each record carries `:origin "checkout"|"sdk"`. The guard compares
   `[path sha256]` of the macro providers, excluding addition paths. Main's edits
   to `priv/lib/live/app.bl` no longer matter, because the SDK never loads that
   file. No file copy or `git checkout` workaround is needed.
6. Writes `closure.etf`, `identity.json` and `update.json`. `update.json` is v2
   and adds `added`, `additions-files` and `host-modules`.

`snapshot-closure.py` now accepts any parent with 18 to 256 distinct
namespaces. `partition-closure.py` needed no change.

### Linking (`native.bootstrap/link-plan`, one implementation)

`by-module` maps each unit's `:module`/`:base-module` and every `:host-modules`
row to its namespace. This generalises the old hard-coded `CompilerData` /
`FormMeta` / `Meta` table, which is deleted in `chunks.bl` and in
`host-compiler.scm` `native-install-bundle!`. The dynamic `native-remote` path
now reads `host-modules` from the bundle metadata.

A `:remote` to `M/f/a` resolves as follows (`remote-decision`):
1. `native.intrinsics/remote-template` (BIF template), else
2. **compiled**, when `by-module[M]` defines `f` (the `__bl_v` suffix is
   stripped). The link shape is `arity` (`v_ns/f$a`), `variadic` (`$v`),
   `generic` (live slot) or `dynamic`. This branch now comes BEFORE the leaf
   branch.
3. leaf `lv_…`
4. excluded namespace
5. refusal: `native link: unresolved remote signature KEY`.

**Dead leaves.** `chunks.bl` (`plan`, `build-next` when the plan changes,
`emit-unit`, and the new `dead-leaves` mode) writes `OUT/dead-leaves.json` and
prints `NATIVE_DEAD_LEAF key` / `NATIVE_DEAD_LEAVES n` for every registered leaf
whose key now links to a compiled definition. The owning workstream deletes
those leaves.

The chunk policy is `native-aot-link-v2`. `emission-input` adds
`resolution_ledger_sha256`. Every chunk rebuilds once.

### How the main thread runs the integrated update

From the integration checkout root, after every workstream's
`closure-additions.edn` is merged:

```sh
NS=research/native-seed
python3 $NS/snapshot-closure.py $NS/out/speed-closure $NS/out/speed-closure-2
work run --memory 3G --timeout 1800 -- $NS/run run $NS/src/native/update-closure.bl -- \
  $NS/out/speed-closure-2/partition.json
python3 $NS/partition-closure.py --out $NS/out/speed-closure-2
# then the usual chunks.bl build-next … $NS/out/speed-closure-2/partition.json
# (it reports NATIVE_DEAD_LEAVES n and writes OUT/dead-leaves.json)
```

## 2. P: self-emission parity

* `native.resolution` is split:
  - `native.resolution` (closure member, no requires) keeps the `:global`
    decisions: `direct`, `exact`, `normal`, `global-decision`.
  - `native.resolution-ledger` (BEAM-only) keeps the ledger builder `build`,
    which uses `BeamLisp.AOT/namespace_header`, a call with no native leaf. It
    also gains `bundle-metadata`: the single metadata value written into
    `bundle.scm`. It now also carries `:host-modules` and `:leaves`.
* The whole linking context moved from `chunks.bl` into `native.bootstrap`:
  - `link-plan [metadata units]`
  - `remote-decision`, `global-decision`, `compiled-target`
  - `remote-link`, which calls `native.intrinsics/remote-template`
  - `link-context`, which is `native.eval/context` plus `:aot-link`
  - `link-definition`, `seed-links`
  - `emit-definition [plan unit d]`, which applies `kernel-override`
  - `emit-functions` and `emit-initializers`, which are the row/unit text
  - `emit-compiled-bundle`
* `chunks.bl` builds `(bootstrap/link-plan (ledger/bundle-metadata closure leaves) units)`
  and calls those same functions. It no longer requires `native.intrinsics`,
  `native.eval`, `native.scheme` or `native.resolution`.
* `bootstrap --compile` (stage1 → stage2, stage2 → stage3) works like this:
  - it evaluates `bundle.scm`;
  - it builds the plan from `(dissoc bundle :units)` and its prepared units;
  - it emits through the same `emit-functions`/`emit-initializers`.

  The old late-bound `bootstrap/emit-definition` (plain `ev/context`, no
  seed links, no arity cells) is deleted.
* Closure additions for P (real, global): `speed/closure/closure-additions.edn`
  adds `native.resolution` and `native.intrinsics`. Their contents are KERNEL's;
  CLOSURE only moved them into the closure.
* Callers adapted with one-line hunks:
  - `export.bl` takes its bundle from `ledger/bundle-metadata`.
  - `debug-definition.bl` builds a plan.
  - `gvm/…/gvm-produce.bl` requires `native.resolution-ledger`.

### Stage-1 image entry point for stage 2 / stage 3

Unchanged command; new behaviour:

```
stage1 --compile OUT/bundle.scm OUT/host.scm OUT/stage2.scm   # native-main → native.bootstrap/main
stage2 --compile OUT/bundle.scm OUT/host.scm OUT/stage3.scm
```

`bundle.scm` must be the one `chunks.bl assemble!` writes from the *updated*
closure, because it carries `:leaves` and `:host-modules`. The existing
`out/speed-build/stage1` was built from the old closure, so it still emits
late-bound code. It cannot show the new path; the next integrated image can.

## Checks (all run once, sequentially, one VM at a time)

Scratch generation: `S=/home/othman/.claude/jobs/bbc0cb7e/tmp/closure-out/gen1`
(never `out/speed-closure`). The logs and JSON are copied into `proof/`.

1. **Snapshot.** `python3 snapshot-closure.py MAIN/NS/out/speed-closure $S` printed
   `NATIVE_CLOSURE_GENERATION_COPIED`.
2. **Closure update with additions** (pinned SDK, 2.5 min). The checkout's
   `priv/lib/live/app.bl` was left as main has it.
   ```
   work run --memory 4G --timeout 1800 -- research/native-seed/run run research/native-seed/src/native/update-closure.bl -- \
     $S/partition.json research/native-seed/speed/closure/closure-additions.edn \
     research/native-seed/speed/closure/proof/closure-additions.edn
   ```
   Output:
   - 17 `NATIVE_UPDATE_REUSED`
   - `NATIVE_UPDATE_COMPILE native.bootstrap`
   - `NATIVE_UPDATE_ADD native.resolution | native.intrinsics | host.deferred`
   - `NATIVE_UPDATED 1 changed, 3 added, 21 units`

   The new order is:
   - rt, core, sugar, **host.deferred**, **native.resolution**
   - clojure.core-ext … clojure.string
   - **native.intrinsics**, native.scheme, native.eval, native.bootstrap

   `host-modules` holds compiler-data, deferred, form-meta and meta. There are
   607 providers (567 `sdk`, 40 `checkout`). The macro set is unchanged. Then
   `python3 partition-closure.py --out $S` printed `NATIVE_PARTITION 21 bounded units`.
   See `proof/update.json`.
3. **Linking a pinned host module** (`chunks.bl inspect`, output in `proof/inspect-calls.txt`):
   - `core/memoize` now calls `host.deferred/delay$1` and `host.deferred/force$1`.
     These are the compiled arity cells. Before, they were the leaves
     `Elixir.BeamLisp.Deferred/*`.
   - `host.deferred/force` calls `host.deferred/delay?$1`.
   - `native.bootstrap/remote-decision`, `native.resolution/direct` and
     `native.intrinsics/remote-template` are now emitted as closure members.
     All their calls are linked cells or leaves.
   - No inspected definition has a `native-remote` or `native-global`.
4. **Unit chunk emission** (`chunks.bl emit-unit … "sugar,server-clause,reader-node,host.deferred"`,
   3G, `proof/emit-unit.log`):
   - `NATIVE_DEAD_LEAF Elixir.BeamLisp.Deferred/{delay,delay?,force,realized?}/1`,
     `NATIVE_DEAD_LEAVES 4`, written to `dead-leaves.json`.
   - One chunk each for sugar, server-clause and reader-node.
   - host.deferred is **refused**: `native link: unresolved remote signature erlang/fun_info/2`.
     `delay` calls `(erlang/fun_info (fn [] nil) :module)` in its error path,
     and no native leaf or template exists for it. This is the expected
     exact-capability refusal (see Risks).
5. **Compiled host module runs natively** (gsi, `proof/host_modules_check.py`,
   `proof/host-modules-check.log`). The program is the host sources,
   `native-install-bundle!` with `:host-modules`, and the REAL emitted
   host.deferred definitions. It printed `host-modules checks: 10`:
   - the module table holds `Deferred` and `CompilerData` from metadata, and no
     hard-coded `Meta` row;
   - compiled `delay?`, `realized?` and `force` work on a leaf-made delay, both
     before and after forcing, and on non-delays.
6. **P parity, driver path against self-emission path** (`speed/closure/parity.bl`, 3G,
   `proof/parity.log`, `proof/parity.json`):
   ```
   PARITY sugar BYTE-EQUAL functions=6455B ...
   PARITY server-clause BYTE-EQUAL functions=16817B ...
   PARITY reader-node BYTE-EQUAL functions=17377B ...
   PARITY_DONE 3/3 byte-equal
   ```
   The driver side is the chunk files `chunks.bl emit-unit` wrote. The self side
   is `native.bootstrap/emit-functions`/`emit-initializers`, using a plan built
   from the bundle value (`bundle-metadata` plus source units), the same path
   `compile-bundle` takes natively.
7. **No output drift from round 1** (`proof/compare_round1.py`). The new
   self-emission text for sugar, server-clause and reader-node is byte-identical
   to the round-1 stage-1 chunks in `MAIN/NS/out/speed-build/chunks`. The
   refactor changes no emitted byte for namespaces that do not touch a new
   host module.

### Skipped (per the updated rules: correctness only, minimal local work)

- No speed measurement of any kind.
- No `check-host.py` / `check-compiler.py` run. The host change is the one
  `native-install-bundle!` hunk, covered by check 5.
- No variant emission with a test-only `erlang/fun_info/2` leaf to produce a
  complete host.deferred chunk. Check 4 shows the exact refusal instead.
- No stage-1 image run. The existing image predates this code.

## Risks for integration

- **Missing BIF `erlang/fun_info/2`.** Almost every `priv/host/*.bl` module finds
  its own module with `(erlang/fun_info (fn [] nil) :module)`. Before DATA,
  SERVICES or LAZY modules can join the closure, the native side needs a
  category (b) leaf or KERNEL template for `erlang/fun_info/2`. Without it,
  emission refuses those modules, as in check 4.
- **The `NATIVE_SELF_COMPILE 18 namespaces` literal** sits in
  `fixpoint-full.py` (lines 612, 632, 656) and `check-self-emission.py:27`. It must
  become the integrated unit count (20 + additions). These files are
  BACKEND's/main's.
- **Dynamic priority.** Statically, a compiled target wins over a leaf. The
  dynamic `native-remote-resolve` (host-compiler.scm) still tries the leaf
  first. The two agree once the reported dead leaves are deleted. Until then,
  runtime-evaluated code and `erlang/apply/3` reach the leaf.
- **New metadata keys.** The prelude's bundle metadata must carry
  `:host-modules`. Old preludes with the new `host-compiler.scm` lose the
  CompilerData/FormMeta/Meta module rows (`fixtures/compiler-vector-check.scm`
  uses one). Rebuild the prelude from the updated closure.
- **`kernel-override`.** `bootstrap/emit-definition` still calls
  `intrinsics/kernel-override`. If KERNEL deletes it, delete the `override`
  branch there. It is one `let` binding and one `if`.
- **Initializer order.** An addition goes after its `:require`d dependencies.
  A member that calls a host module's `:val` definitions at LOAD time through
  a `:remote` (not a require) is not ordered by this rule. Every `:fn` cell
  is defined before any initializer runs, so only `:val` reads are exposed.
- **Chunk keys.** The keys change (policy v2, `resolution_ledger_sha256`, new
  bootstrap/driver hashes), so the next `build-next` re-emits every chunk once.
- **Stage-1 bytes.** stage1 is BEAM-emitted from closure ANF; stage2 is
  natively emitted from source-compiled ANF. Both now go through the same
  linker. Any remaining stage1 ≠ stage2 difference would come from ANF, not
  linking. stage2 = stage3 holds by construction (same code, same bundle).
- **Non-owned files touched, each with one small hunk:**
  - `host/host-compiler.scm` (`native-install-bundle!` host-module rows)
  - `gvm/src/native/gvm-produce.bl` (require rename)
  - `src/native/export.bl`
  - `src/native/debug-definition.bl` (API callers)
