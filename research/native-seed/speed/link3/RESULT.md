# LINK (round 3, wave 1): P3 self-emission stubs, N3 sealed direct links

Branch `native-r3-link`. Contract: [`../CONTRACT3.md`](../CONTRACT3.md).
Scratch: `/tmp/r3link` (closure snapshot, outputs). MAIN artifacts were only read.

## P3: the native Env answers the stub's link rows as BEAM does

**Cause.** `compiler.bl` calls one stub function: `(lower/eval-anf modname node)`
in `eval_form`. On BEAM, `lower` is loaded, so `Env/link "compiler"
"lower/eval-anf"` returns `{Elixir.BeamLisp.Ns.Lower, %{2 => :"eval-anf"}, nil}`.
`linked-call` then emits a `:remote` to `Ns.Lower`, which the link plan decides
as `excluded-namespace`. The native image had no link row for `lower`, so the
same source compiled to `:global "lower" "eval-anf"`, and
`native.resolution/global-decision` refused it with *global context namespace
absent from closure (lower)*.

**Fix.**
- `native.resolution-ledger/stub-links` (new) reads the link rows of every
  closure `:stubs` namespace from the driver's BEAM Env
  (`Env/match {{:link ns $1} $2}`). It produces `[ns name info private?]` rows,
  sorted, and refuses a stub that has no rows.
  `bundle-metadata` carries the rows as `:stub-links`. This is the same
  mechanism as `:core-links`, which `probe.bl` also takes from the live Env.
- `host-compiler.scm` `native-install-bundle!` puts each row as
  `{:link ns name} → info`, plus `{:private true}` meta for private rows.
  `reject-private!` therefore refuses a private stub call natively, as BEAM does.

The native Env now gives the same answer for every stub member. So
`compile-call` takes the same `linked-call` branch on both targets (there is
no readiness guard, because `lower` is boot tier on both), and the link plan
emits the same `(native-remote "Elixir.BeamLisp.Ns.Lower/eval-anf/2")`, which
raises *explicitly excludes namespace* if it is ever called.

### Checks

1. **BEAM rows = BEAM Env** (`speed/link3/stubs.bl`, pinned SDK):
   ```
   work run --memory 4G --timeout 1800 -- research/native-seed/run run research/native-seed/speed/link3/stubs.bl -- \
     /tmp/r3link/closure/partition.json MAIN/NS/out/round2-build/leaves.json /tmp/r3link/out
   ```
   (`/tmp/r3link/closure` = `snapshot-closure.py MAIN/NS/out/speed-closure-2`.)
   ```
   STUB_LINK_ROWS 46 namespaces=["lower"]
   STUB_LINK_ROWS_EQUAL_ENV 46 private=12
   CLOSURE_STUB_REMOTES ["Elixir.BeamLisp.Ns.Lower/descriptor->beam/1" "Elixir.BeamLisp.Ns.Lower/eval-anf/2"]
   CLOSURE_STUB_GLOBALS 0
   BEAM_EMIT compiler/eval_form 2192B sha=31845be5…bae4 lower-remotes=1
   ```
   - Every row equals `Env/link "compiler" "lower/NAME"`.
   - Across the whole closure's ANF, every stub call is a remote decided as
     `excluded-namespace`, and no `:global` names a stub.
   - The second remote, `descriptor->beam`, comes from host.emit's explicit
     `BeamLisp.Ns.Lower/…` module call. It was never affected.
   - `beam-eval_form.scm` is `compiler/eval_form` compiled from SOURCE on BEAM
     (per-definition fresh reset, as `bootstrap/prepare` does) and emitted
     through the link plan.
2. **The failing path, on the real round-2 image** (`speed/link3/native-probe.bl`,
   no rebuild):
   ```
   work run --memory 4G --timeout 1800 -- MAIN/NS/out/round2-build/stage1 \
     --eval MAIN/NS/out/round2-build/bundle.scm research/native-seed/speed/link3/native-probe.bl
   ```
   The image compiles `compiler/eval_form` from the bundle's source text. It
   builds the link plan from the bundle metadata and every unit's
   definitions, exactly as `compile-bundle` does, then emits once before and
   once after it puts the `:stub-links` rows (the same puts the new
   `native-install-bundle!` makes). Results:
   ```
   NATIVE_PROBE units=33 stub-link-before=error
   NATIVE_EMIT_REFUSED compiler/eval_form native resolution: global context namespace absent from closure {:namespace "lower"}
   NATIVE_PROBE stub-link-after={:ok, {BeamLisp.Ns.Lower, %{2 => :eval-anf}, nil}}
   NATIVE_EMIT compiler/eval_form 2386B
   NATIVE_PROBE_DONE
   ```
   The image reproduces the round-2 failure exactly (same message, same
   namespace). With the rows in place, the same compile emits. The stub call
   is now `(native-remote "Elixir.BeamLisp.Ns.Lower/eval-anf/2")`, which is
   also what BEAM emits.
3. **Native vs BEAM, same definition from source**
   (`/tmp/r3link/out/{beam,native}-eval_form.scm`):
   - The stub call, the `lv_` leaves and the `core/list$v` cell are identical.
   - The bytes still differ, in exactly two links, and neither involves a
     stub. They are `compiler`'s calls to ITS OWN `assert-native-evaluation!`
     and `compile`. BEAM emits `…$0` and `…$2` (arity cells: on BEAM the
     compiler's own defns have link rows, so `compile-call` emits a remote to
     `Ns.Compiler`). Native emits a `…$g` value read (the image's Env has no
     link rows for closure members, only `:core-links`, so the call is a
     `:global`).
   - This is item D's class of bug for closure members rather than stubs. It
     makes stage1 (BEAM ANF) differ from stage2 (native ANF). It does NOT
     affect stage2 = stage3, where both sides are native.
   - The same mechanism fixes it: carry `Env/match {{:link ns $1} $2}` for
     every closure namespace, not only `:stubs`, as bundle rows. I did not
     widen it, because the scope was the stubs and the effect on every chunk
     needs the integrated image build to check. It is listed under Requests.

## N3: sealed direct links

### Where "sealed" lives

| Target | Declared by | Read by |
| --- | --- | --- |
| native | `bundle-metadata` sets `:sealed true`, because the native closure is always sealed. It travels in `bundle.scm`, so the BEAM driver and the self-emission see the same value. | `bootstrap/link-plan` → `:sealed?` |
| BEAM | `BeamLisp.Env/seal!` writes persistent_term `:bl_sealed_image` once, node-wide and irreversibly. A release build calls it after loading its closure. A dev image never calls it. | `Env/sealed?`, `Env/sealed_value`, `Env/refuse_sealed_redefinition!` |

### Native (`native.bootstrap`, `host-compiler.scm`)

When `:sealed?` is set:
- `link-definition` has a new sealed arm, `sealed-link-definition`.
  - Each arity cell is `(define v_ns/f$N (native-arity-entry v_ns/f N))`, and
    the variadic cell is the same kind of define.
  - A `:val` gets `(define v_x$g (native-unmacro v_x))`.
  - There is no `native-link!` and no `set!`: every link cell and binding is
    a constant top-level definition.
- The `:global-resolver` reads a selected compiled `:fn` through its binding
  `v_ns/f` directly, not through the `$g` view cell. Seeds and `:val`s keep
  their `$g` cell.
- `:aot-link` gains `:global (fn [n arity])` (`global-link`). For a sealed
  compiled `:fn` with that fixed arity, it returns the same direct-call link
  that a `:remote` gets. The emitter does not consult it yet; see Requests.
- `seal-source` emits `(native-seal-image!)` after every initializer and
  before the entry point. It does this in both `emit-compiled-bundle`
  (self-emission) and `chunks.bl assemble!` (driver), so stage1 and stage2
  have the same shape.
- `native-seal-image!` (host) does three things:
  - It refuses to seal if any Env value row shadows a compiled definition, so
    a direct binding read always equals what a fetch would return.
  - It marks every compiled slot and every seed global view as sealed.
  - It replaces each compiled slot's setter with one that restores the
    sealed value and then raises.

  After sealing, redefinitions raise
  `native sealed image: redefinition refused (AOT callers are linked directly)`
  in each of these places:
  - `native-register!` of a compiled slot;
  - an Env value row put (`Env/intern`, `put_key`) for a compiled slot or a seed;
  - `delete_key` of such a row;
  - `Env/refuse_sealed_redefinition!` (called from host.link `defvar`).

  New names (for example user code under `--eval`) remain definable.
- Unsealed plans (no `:sealed` key) emit exactly today's bytes.

### BEAM (`compiler.bl`, `env.bl`, `link.bl`)

- `compiler.bl` `sealed-call` and `sealed-link-info` (new) handle the two
  fetched-global fallbacks of `compile-call`: the qualified `alias/var` call
  and the bare-symbol call. When the image is sealed, the var that the runtime
  fetch would select (`Env/sealed_value`: the exact row, or `peek` order,
  never a per-env descriptor) cannot change. If its value is an exported BL
  function, the call becomes the static remote call of a linked defn
  (`linked-call`). That value is a defn capture `fun M:f/n`, or a `$blfn` tag
  whose arms all belong to one module. Closures and other values keep the
  fetch, as does any call in a dev image (`sealed_value` answers `:error`).
  Calls to defns with link rows were already static remote calls and are
  unchanged.
- `env.bl` gains `seal!`, `sealed?`, `sealed_value` and
  `refuse_sealed_redefinition!`. Both `intern` and `define_per_env` call the
  refusal first: a sealed image cannot rebind an existing var.
- `link.bl` `defvar` refuses before compiling or publishing a body module or
  shim. A rebuilt shim would otherwise silently reroute direct callers.
- Native leaves for the two new Env calls that natively compiled code makes:
  - `sealed_value/3` answers `:error`. Compile-time sealing is BEAM build
    state; natively, compiled ANF stays a function of source.
  - `refuse_sealed_redefinition!/2` consults the image seal.

### Checks

1. **Sealed vs dev emission** (`speed/link3/seal-diff.bl`, pinned SDK):
   ```
   work run --memory 4G --timeout 1800 -- research/native-seed/run run research/native-seed/speed/link3/seal-diff.bl -- \
     /tmp/r3link/closure/partition.json MAIN/NS/out/round2-build/leaves.json MAIN/NS/out/round2-build/chunks \
     /tmp/r3link/seal sugar,server-clause,reader-node,clojure.string
   ```
   ```
   SEAL_DIFF sugar dev=BYTE-EQUAL-ROUND2 dev-bytes=6455 sealed-bytes=6163 dev-native-link=1 sealed-native-link=0 sealed-set!=4 sealed-compiled-fn-$g-reads=0 sealed-arity-cells=3
   SEAL_DIFF server-clause dev=BYTE-EQUAL-ROUND2 dev-bytes=16778 sealed-bytes=15152 dev-native-link=4 sealed-native-link=0 sealed-set!=0 sealed-compiled-fn-$g-reads=0 sealed-arity-cells=4
   SEAL_DIFF reader-node dev=BYTE-EQUAL-ROUND2 dev-bytes=19176 sealed-bytes=15490 dev-native-link=10 sealed-native-link=0 sealed-set!=0 sealed-compiled-fn-$g-reads=0 sealed-arity-cells=10
   SEAL_DIFF clojure.string dev=BYTE-EQUAL-ROUND2 dev-bytes=72074 sealed-bytes=58861 dev-native-link=30 sealed-native-link=0 sealed-set!=4 sealed-compiled-fn-$g-reads=0 sealed-arity-cells=34
   SEAL_DIFF_DONE dev-equal=4/4
   ```
   - The dev plan is byte-identical to the round-2 driver chunks for all four
     units, so dev behaviour is unchanged bit for bit.
   - The 8 remaining `set!`s are the emitter's local `$multi/fnself_*`
     letrec knots, not link cells.
2. **Seal semantics on the real image body** (gsi, `speed/link3/seal-check.scm`):
   - The host is this worktree's host sources plus round-2 `text.o1`
     (`/tmp/r3link/host-gsi.scm`).
   - The image is the round-2 `prelude.scm` after its host
     (`/tmp/r3link/image-body.scm`, the full dev image of 33 namespaces).
   ```
   G=$(jq -r .gambit research/native-seed/toolchain-pin.json)/bin/gsi
   work run --memory 4G --timeout 1800 -- timeout 900 $G -e '(load "/tmp/r3link/host-gsi.scm")' \
     -e '(load "/tmp/r3link/image-body.scm")' research/native-seed/speed/link3/seal-check.scm < /dev/null
   ```
   (`< /dev/null`, plus a final `(exit 0)`, so that gsi cannot sit in its REPL.
   Two earlier runs without them reached the 1800 s cap.)
   ```
   SEAL_CHECKS_PASSED 17
   ```
   - The dev image runs compiled code and allows redefinition.
   - The seal succeeds on the real image, so no Env value row shadows any of
     its compiled definitions.
   - After the seal, the following raise: `native-register!` of `core/inc`
     (with the sealed value restored, and calls still answering 42),
     `Env/intern` over `core/inc`, `Env/intern` over the seed `core/+`,
     `delete_key` of the seed, `refuse_sealed_redefinition!` on a sealed slot,
     and a second seal.
   - New `user` vars, and rebinding a non-sealed `user` var, still work.
   - `sealed_value` answers `:error` natively.
3. **Sealed text runs and answers as dev** (gsi, `speed/link3/seal-units-check.scm`):
   - On the same dev image it computes 16 compiled `clojure.string` answers.
   - It loads the SEALED re-emission of sugar, server-clause, reader-node and
     clojure.string, recomputes the answers, seals, and recomputes again.

   ```
   SEAL_UNITS answers=16 sealed-text-equal=#t after-seal-equal=#t
   SEAL_UNITS_PASSED
   ```
   The sealed text is valid Scheme. It loads over the dev image and links
   through constant cells, and the answers are equal before and after sealing.
4. **BEAM tests**, in one batch, followed by `./bin/bl realm stop`:
   ```
   work run --memory 4G --timeout 1800 -- ./bin/bl --cold test test/bl/sealed_link_test.bl test/bl/link_test.bl \
     test/bl/env_test.bl test/bl/env_vars_test.bl test/bl/env_peek_test.bl test/bl/env_fetch_memo_test.bl \
     test/bl/compiler_invocation_test.bl test/bl/namespace_demand_test.bl test/bl/macro_core_alias_test.bl
   ```
   | file | result |
   |---|---|
   | sealed_link_test (new; sealed-vs-dev on BEAM) | 20 passed (second run, after a fixture fix; the first run had 16 passed) |
   | link_test | 45 passed |
   | env_test | 136 passed |
   | env_peek_test | 22 passed |
   | env_fetch_memo_test | 26 passed |
   | compiler_invocation_test | 28 passed |
   | namespace_demand_test | 52 passed |
   | macro_core_alias_test | 3 passed |
   | env_vars_test | 3 passed, 1 failed: `every-variable-read-is-documented` reports `BEAM_LISP_CUSTODY_INPUT_V1`, `BEAM_LISP_CUSTODY_STREAM_V1` and `BL_CHECK_PROGRESS` undocumented. None of these is read by my code; the failure is not mine, though I did not run it on the base commit. |

   `sealed_link_test` covers these cases:
   - Dev: `(alias-twice 21)` stays `:invoke` of `:global`, and redefinition is
     allowed.
   - Sealed: `alias-twice` (a `def` of a defn), its qualified form and
     `alias-arities` (a `$blfn`, both a fixed arm and a variadic arm) become
     `:remote` to the defn's module. A closure value keeps today's ANF.
     Answers are equal.
   - Redefinition by `defn` or `def` raises *sealed image: cannot redefine
     ns/name*, and the old procedure keeps answering. A new name is still
     definable.

## Integration command (main thread)

The stub rows and the seal reach the image through `bundle.scm`/`prelude.scm`.
Every chunk key changes once (`bootstrap_sha256`, `driver_sha256` and
`resolution_ledger_sha256` all changed). Run this from the integration
checkout after merging:

```sh
NS=research/native-seed
# 1. closure update (compiler.bl, host.link changed) + partition, as usual
python3 $NS/snapshot-closure.py $NS/out/speed-closure-2 $NS/out/speed-closure-3
work run --memory 4G --timeout 1800 -- $NS/run run $NS/src/native/update-closure.bl -- $NS/out/speed-closure-3/partition.json
python3 $NS/partition-closure.py --out $NS/out/speed-closure-3
# 2. host + leaves (two new Env leaves), then chunks + assemble (bundle carries :stub-links, :sealed)
python3 $NS/prepare-host.py --out $NS/out/round3-build      # or the usual host/leaf step
work run --memory 4G --timeout 1800 -- $NS/run run $NS/src/native/chunks.bl -- build-next \
  $NS/out/speed-closure-3/partition.json $NS/out/round3-build/host.scm $NS/out/round3-build   # repeat until NATIVE_BUILD_COMPLETE
grep -c '(native-seal-image!)' $NS/out/round3-build/stage1.scm      # expect 1
# 3. image + stage2 = stage3 (fixpoint-full builds stage1, runs stage1 --compile, stage2 --compile, compares bytes)
work run --memory 8G --timeout 1800 -- python3 $NS/fixpoint-full.py --out $NS/out/round3-build --corpus $NS/fixtures/compiler-source.bl
# equivalently, by hand:
#   OUT=$NS/out/round3-build
#   $OUT/stage1 --compile $OUT/bundle.scm $OUT/host.scm $OUT/stage2.scm   # must print NATIVE_SELF_COMPILE 33 namespaces
#   (build stage2 from stage2.scm), then
#   $OUT/stage2 --compile $OUT/bundle.scm $OUT/host.scm $OUT/stage3.scm && cmp $OUT/stage2.scm $OUT/stage3.scm
```

Before step 3, update the stale `NATIVE_SELF_COMPILE 18 namespaces` literal to
the current unit count. It appears in `fixpoint-full.py` lines 630, 650 and 674,
and in `check-self-emission.py:27`. These files are not mine. CLOSURE already
reported this in round 2.

## Requests

- **Main thread / a later LINK item: closure-member link rows.** This is P3
  check 3. Widen `ledger/stub-links` from `(:stubs closure)` to
  `(concat (:order closure) (:stubs closure))`, under a new key
  (`:namespace-links`). Then the native compile links intra-closure defn calls
  exactly as BEAM does, and stage1 = stage2 holds at the ANF level too. One
  image build checks it.

- **BACKEND (`scheme.bl`), the `:invoke`/`:apply` case (`ordered-language-call` →
  `linked-language-call`).** When `(:aot-link options)` has `:global`, the
  callee is a `:global` node and the arguments are static (`static-arguments`),
  call `((:global aot) callee (count statics))`. If that returns a link, emit
  it as `linked-call` does for a remote, and skip the `(let ((callee …))
  (if (procedure? callee) …))` wrapper. Today, a sealed global call reads the
  constant binding and still pays the procedure test. With this change it
  becomes `(v_ns/f$N a b)`, the same as a linked remote. Dev plans have no
  `:global` key, so their bytes do not change.
- **BACKEND (`scheme.bl`), so that Gambit can inline.** A sealed arity cell is
  `(native-arity-entry v_ns/f N)`, a computed value. Gambit block compilation
  inlines a call only when the binding is a literal `lambda`. Requested: when
  emitting a top-level single-arity `:fn` definition, expose its raw lambda,
  for example an `emit` option that returns the unregistered function
  expression. `bootstrap/sealed-link-definition` would then emit
  `(define v_ns/f$N (lambda …))` and
  `(define v_ns/f (bl-register-callable! v_ns/f$N N))`. Inlining across the
  70 stage-1 Gambit units also needs those calls inside one unit, which is a
  split/unit concern.
- **Release build owner (AOT/SDK).** Call `BeamLisp.Env/seal!` at the end of
  a release image's boot, after the closure is loaded. Nothing calls it today,
  so every BEAM image is dev.

## Residual replicas

None added. The two new native Env leaves are registry answers, the same
category as the existing `Env/*` leaves in `host-compiler.scm`.

## Risks for integration

- **New native leaves must reach `leaves.json`.** `compiler.bl` now calls
  `Env/sealed_value/3`, and host.link `defvar` calls
  `Env/refuse_sealed_redefinition!/2`. Their leaves are in `host-compiler.scm`,
  but the link plan's `:leaves` comes from `leaves.json`. Regenerate it, or AOT
  linking refuses with `unresolved remote signature`.
- **The seed floor.** `compiler.bl`, `env.bl` and `link.bl` changed, so
  regenerate the seed floor. compiler.bl guards `sealed_value` with
  `function_exported`, so an old floor Env is harmless.
- **Sealed native image versus harnesses.** A sealed prelude refuses to
  redefine closure definitions. Any harness that loads `prelude.scm` and then
  re-registers or interns over a closure slot now raises. A harness that loads
  emitted definitions WITHOUT the prelude's final seal line is unaffected; that
  is how the CLOSURE/DATA fixtures work. The source corpus defines only new
  namespaces.
- **`native-seal-image!` shadow check.** The image refuses to start if an Env
  value row shadows a compiled definition. A grep shows no `defmacro`/`defn`
  name overlap and no seed/compiled-def overlap in the closure sources, and
  check 2 sealed the real image body.
- **BEAM seal scope.** It is node-wide. In a sealed node, every existing var
  is immutable, including any program that rebinds vars at run time
  (`def` in a loop, REPL redefinition), and such programs now raise.
  `sealed_link_test.bl` erases the persistent_term in `finally`.
- **P3 rows come from live BEAM state,** like `:core-links`. They equal what
  the BEAM compile consulted, and `stubs.bl` checks this, but they come from
  the pinned SDK's `lower`, not the checkout's `priv/boot/lower.bl`.
- **No timing was measured** (forbidden). The expected native gain from N3
  alone is small until both BACKEND requests land. Today it removes every
  `set!` on link cells and the `$g` indirection for compiled functions.
