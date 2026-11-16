# Workstream L: link once

The AOT context (`native.chunks/checked-context`, keyed by `:aot-link`) now links
every call it can decide statically, at emission time, to a Scheme top-level
cell. Plain emission with no resolvers (the benchmark's options) never reaches
the new code: every new branch in `scheme.bl` checks `(:aot-link options)`.

## Design

### Cells (names from `native.bootstrap`)

| Cell | Name fn | Holds | Maintained by |
| --- | --- | --- | --- |
| `v_<ns/name>` | `binding-name` | compiled value (registry view) | `define` + slot setter |
| `v_…$<n>` | `arity-binding-name` | entry for fixed arity n: the procedure itself, the `$blfn` fixed arm, or a `bl-invoke` fallback | slot setter (`native-arity-entry`) |
| `v_…$v` | `variadic-binding-name` | `$blfn` variadic arm (takes the rest list), else a raising stub | slot setter (`native-variadic-entry`) |
| `v_…$g` | `global-binding-name` | global view: env row if present, else compiled value, with `$macro` unwrapped | global setter |
| `v_…$bl` | `original-binding-name` | unchanged compiled body when K overrides the slot | `define` |
| `lv_<key>` | `leaf-binding-name` = `"l"` + `scheme/ident` | host leaf procedure | `native-add-leaf!` / `native-replace-leaf!` (`##global-var-set!`) |

`$`, `l` and `v` cannot collide: `ident` only emits `v`, `_` and digits.

### Emission per definition (`chunks.bl emit-definition` + `link-definition`)

```
(define v_X <body>)                  ; or (define v_X$bl <body>) (define v_X <kernel override>)
(native-register! ns name v_X)
(native-put-meta …) (native-register-arities! …)
(define v_X$1 #f) … (define v_X$v #f) (define v_X$g #f)
(native-link! ns name (lambda (value) (set! v_X value) (set! v_X$1 (native-arity-entry value 1)) …)
                      (lambda (value) (set! v_X$g value)))
```

Arity cells are published for the arities the declaration lists
(`declaration-arities`). `native-link!` runs both setters right away.

### Call sites

- `:remote`: first `(native.intrinsics/remote-template node)`. If it returns a
  template, every operand is bound in source order to `a<i>` and
  `(template names)` is spliced in. If not, `remote-decision` picks the target:
  - leaf: `(lv_KEY ops…)`
  - compiled, fixed arity it declares: `(v_X$n ops…)`
  - compiled `__bl_v` call to a definition with a variadic arm: `(v_X$v ops… rest)`.
    The rest list is passed exactly as the old wrapper passed it.
  - compiled `:val` definition, or an arity it does not declare: `(let ((linked v_X)) (if (procedure? linked) (linked ops…) (bl-invoke linked (list ops…))))`
  - excluded namespace, or a rest call to a definition with no variadic arm:
    these stay `(native-remote KEY)` and raise when called, as before.

  Variable and literal operands are passed in place. Any other operand is
  bound with `let*` in source order. The cell is read after the operands, as
  the old wrapper read its slot when invoked.
- `:global`: `v_<sel-ns/sel-name>$g`, using the candidate that
  `native.resolution/global-decision` selected (kind compiled or seed).
- `:apply` / `:invoke` (invoke fast path):
  `(let ((callee F)) (let* (…) (if (procedure? callee) (callee a…) (bl-invoke callee (list a…)))))`.
  A non-static argument list uses `apply`/`bl-invoke` instead.
- Seeds (seed names that are not compiled definitions): the first core chunk's
  initializers emit `(define v_core/x$g (native-unlinked …))
  (native-link-global! …)` just before `rt/seed-core`. Each `native-intern`
  of a seed then publishes it.
- `:arith` (`eval.bl`): named host procedures `native-arith-{add,sub,mul,div,lt,gt,le,ge,num-eq}`.
  Any other operator keeps the old lambda.

### Redefinition semantics (same as the old live lookup)

- `native-register!` (compiled/registry view) updates `v_X`, every arity cell
  and the variadic cell. It also updates `$g` when no env row shadows the slot.
  This matches the old wrapper, which read `native-global-registry`.
- `native-intern`, `Env/put_key` and `Env/delete_key` on an `(ns name)` row
  update `$g` (or restore it to the compiled value). This matches the old
  `native-global`: env row first, then registry, macro unwrapped. They do not
  touch the remote cells, which the old wrapper never consulted for env rows.
- `native-replace-leaf!` updates the registry, the `lv_` cell and the dynamic
  table. `host-source-frames.scm`'s transport rebinding now calls it. This is a
  one-line edit in an unowned file.

### Decisions to document

- Planners are now a compile-time choice. Compiled AOT code applies plain
  procedures directly and does not consult a `bl-invoke` or
  `native-resolve-call` that was replaced at runtime. The old wrapper did, via
  `native-remote-original-invoke`. Code emitted with `:source-frames?` keeps its
  existing `ordered-target-call`/`bl-source-call` path, because the source-frames
  branches come before the `:aot-link` branches.
- Normal-mode global candidate selection (alias, refer, core, sugar) is now
  fixed at emission. A later runtime intern of a name that comes earlier in
  the candidate list does not shadow a linked global. Redefining the selected
  slot is still observed. This only matters if code is evaluated at runtime
  into a compiler-closure namespace.
- Reading a seed cell before `seed-core` publishes it gives the `native-unlinked`
  stub. Calling it raises "undefined native var", but a non-call use gets the
  stub value instead of an error.

## Deleted

- `native-remote`: the four epoch roots (`native-remote-cache-{leaves,modules,stubs,arities}`),
  `native-refresh-remote-cache!`, the eq/weak identity front cache,
  `native-remote-resolve-key`, the epoch-checking wrapper lambdas and
  `native-remote-original-{invoke,resolve}`.
- Availability: the five-root vector, `native-refresh-availability-cache!`, the
  nested eq tables and the `native-availability-original-*` guards.
- `fixtures/host-compiler-cache-check.scm` (96 checks).

## Kept, and why

- The dynamic `native-remote` path is used by `native.eval/context` (runtime
  eval and `bootstrap --compile`), `erlang/apply/3` (2.7k calls per warm emit),
  `make_fun/3` and a few host calls. It is now one `equal?` table from key to
  procedure. Compiled wrappers read their link record, so the table needs no
  epoch. It is cleared explicitly by `native-link-changed!` (leaf
  add/replace, `native-install-bundle!`).
- The `function_exported/3` memo (about 3.3k calls per warm benchmark) is now
  one `equal?` table on `#(module function arity)` for atom arguments. It is
  cleared explicitly by `native-link-changed!` and `native-register-arities!`.
- The `native-fetch-value` global cache (`Env/fetch`, `bound?` and dynamic
  `native-global`) is unchanged. It serves the compiler's runtime symbol
  resolution, and AOT code no longer calls `native-global`. Its fixture
  `host-global-cache-check.scm` (48) still passes and stays.

## Checks (all run, all green)

1. Host fixtures:
   `python3 research/native-seed/check-host.py --out /home/othman/.claude/jobs/bbc0cb7e/tmp/link-out/host`
   gives PASS on every stage (values 27, lazy, extra suites, source-frames, POSIX C link and run).
   `check-host.py` now asserts `native link checks: 56` (new
   `fixtures/host-link-check.scm`) and still asserts `native global-cache checks: 48`.
   The new fixture covers:
   - leaf cell naming, and every registered leaf has its binding
   - leaf replacement reaches the cell and the dynamic table
   - arity, variadic and global cells across plain → multi → partial multi → nil → fn redefinitions
   - env-row shadowing, `$macro` unwrap, `delete_key`/`put_key`
   - seed link
   - dynamic wrapper redefinition, rest-list, stub, unknown and invalid key errors, `erlang/apply/3`
   - memo retirement on arity and leaf publication
   - the invoke fast-path shape
   - named arithmetic equal to `bl-arithmetic` (ints and floats)
2. Emission inspection with real AOT output over the reference closure. This
   runs the pinned SDK on the `chunks.bl inspect` mode added here. Its cwd
   mirrors the closure sources the partition pins: the partition's
   `native.scheme` source is commit `fcc12c757`, not HEAD.
   ```
   bash research/native-seed/speed/link/inspect-run.sh run …/wt-link/research/native-seed/src/native/chunks.bl -- inspect \
     $OWNER/partition.json $OWNER/host.scm /home/othman/.claude/jobs/bbc0cb7e/tmp/link-out $OWNER/leaves.json \
     "reader/pos-line,host.compiler-data/namespace_require_refuse!,native.scheme/literal-items,core/inc,core/min,core/tuple"
   ```
   It prints `NATIVE_CHUNKS_INSPECT 6` and writes `link-out/inspect.scm` and
   `link-out/seed-links.scm` (147 seed links). Every remote in the inspected
   definitions is a direct cell call: leaves, `$1`/`$2`, `core/tuple$v`. Every
   global is a `$g` cell, and arithmetic uses `native-arith-*`. No
   `native-remote`, `native-global` or arithmetic lambdas remain.
3. Emitted-code behaviour with gsi:
   `python3 research/native-seed/speed/link/emission_check.py && gsi link-out/link-emission-check.scm`
   prints `link emission checks: 18`. The program is the host files plus five
   stub slots, published and linked in the emitted shape, plus the real emitted
   definitions above. It covers:
   - a direct leaf call
   - named arithmetic
   - `core/min` arity arms `$1`/`$2` and its variadic arm through the global `core/reduce`
   - the zero-fixed `core/tuple$v`
   - a global plus the invoke fast path
   - a variadic remote followed by a leaf raise
   - `native-register!` redefinition seen by direct callers
   - `native-intern` redefinition and `$macro` unwrap seen by global references
   - `$blfn` and keyword callees through the fast path
   - row deletion
   - leaf replacement seen by direct callers
   - dynamic and linked results agreeing
4. Compiled Gambit: `##global-var-set!` cells and `set!` cells work under
   `gsc -exe`, checked with a scratch program.

## Integration risks (for the main thread)

- **`bootstrap --compile` (stage2/3) is still late-bound.**
  `native.bootstrap/emit-definition` uses `ev/context`, which has no `:aot-link`
  because the decision tables (leaves.json, ledger) live only in `chunks.bl`.
  Stage2/stage3 stay byte-equal to each other but differ from stage1, and run
  on the dynamic path (now memoized without epochs). To link them as well, port
  `remote-link`/`link-definition` behind a plan built from native data.
- **The closure changed.** `native.scheme`, `native.eval` and
  `native.bootstrap` are closure members, so regenerate the partition before
  the rebuild. `chunks.bl` now requires `native.intrinsics`, which is outside
  the closure and only BEAM-side.
- **Chunk keys.** `emission-input` adds `intrinsics_sha256`, and the policy
  becomes `native-aot-link-v1`. The decision of each compiled remote now
  carries its link shape (`arity|variadic|generic|dynamic`), so a target's
  arity change invalidates its callers. Every chunk rebuilds once.
- **Load order.**
  - `host-values.scm` defines `native-link-records`, `native-register!` and a
    stub `native-publish-global!`.
  - `host-leaves.scm` defines leaf cells and the `native-link-changed!` stub.
  - `host-compiler.scm` installs both.
  - `host-kernel.scm`, loaded after `host-compiler.scm`, may use all of them.
  - Leaves registered after compiled code loads still work through their cells.
- **New host names.** `native-link!`, `native-link-global!`,
  `native-arity-entry`, `native-variadic-entry`, `native-unmacro`,
  `native-unlinked`, `native-global-view`, `native-env-row-changed!`,
  `native-link-record(s)`, `native-publish-global!`, `native-leaf-binding-name`,
  `native-bind-leaf!`, `native-replace-leaf!`, `native-link-changed!`,
  `native-remote-resolve`, `native-remote-table`, and `native-arith-*`.
  Removed: `native-remote-resolve-key` (used by
  `evidence/equality-shortcut/…/observer-used.scm.in`, historical) and
  `native-refresh-remote-cache!`.
- **Counting harness.** `benchmark/native-counts.scm.in` intercepts
  `native-remote`/`native-global`/`bl-invoke`. Linked calls bypass all three, so
  the warm-core counts no longer attribute linked remotes. I removed its guard
  on the deleted `native-remote-original-invoke`.
- **K templates.** K receives operand names (`a<i>`, every operand bound,
  nothing inlined). Templates may call `lv_…` cells, and `v_…$n` cells of
  compiled slots, read when called. K's overrides are published under `v_X`,
  and arity cells derive from the override value, so an override should be a
  procedure accepting the declared arities. Otherwise arity cells fall back to
  `bl-invoke`.
- **Prelude size.** Each named definition adds 1 + (fixed arities) + (variadic)
  `define` lines and one `native-link!` call holding two closures. That is
  roughly 6k extra small closures at load.
- The `inspect` mode in `chunks.bl` writes only `OUT/inspect.scm` and
  `OUT/seed-links.scm`.
