# Workstream KERNEL (round 2): the native kernel is compiled from rt.bl

Files: `priv/boot/rt.bl` (hot functions), `src/native/intrinsics.bl` (BIF templates only),
`host/host-kernel.scm` (template helpers and captured leaves only), `speed/kernel2/` (checks).

## What changed

### Deleted (hard cutover)

- `native.intrinsics/kernel-override`, the 34-row `rt-overrides` table and `override-names`.
- Every `kernel-rt-*` procedure in `host/host-kernel.scm`, and the support code only they used:
  `kernel-miss`, `kernel-kind`, `kernel-tuple-kind`, `kernel-family-rank`, the kind, module and
  tuple-tag tables, `kernel-plain-keyword?`, `kernel-plain-non-map?`, the Env gate helpers and the
  captured `Elixir.BeamLisp.Vector/*` leaves. The template helpers that inline templates no
  longer call are gone too (`kernel-is-atom?`, `kernel-is-map?`, `kernel-element`,
  `kernel-tuple-size`, `kernel-lt`).
- Round 1's harness: `speed/kernel/{oracle.bl,check.py,kernel-check.scm,gsi-run.py}`. It drove
  `kernel-override`. `speed/kernel2/` replaces it.

What `host-kernel.scm` keeps is category (b): the registered BIF leaves, captured once, and the
helpers that BIF templates call. The opaque-struct guard on `native-register-struct!` also stays,
because the `is_map` template relies on it.

### BIF templates (`intrinsics.bl`, category b)

- **Equality against a literal.** `remote-template` now reads the ANF node. When one operand of
  `==`, `/=`, `=:=` or `=/=` is a literal, the template emits an inline test:

  | Literal | Emitted test |
  | --- | --- |
  | `()` | `(null? x)` |
  | a keyword other than nil/true/false | `(eq? x LIT)` |
  | `nil` | `(or (eq? x bl-nil) (eq? x kernel-symbol-nil))` |
  | `true`, `false` | the same shape, with `#t`/`#f` and their symbols |
  | an integer | `eqv?` for `=:=`; for `==`, `eqv?` when `x` is an integer, otherwise the leaf (a float can equal it) |

  This is exact for two reasons. BEAM atoms are UTF-8, so no `'utf16-keyword` wrapper can share
  a plain keyword's name. The only symbols that share an atom name with `bl-nil`, `#t` and `#f`
  are `:nil`, `:true` and `:false`. The kind keywords in the template avoid `:nil`, `:true` and
  `:false`, because in BL those are nil, true and false.
- **Inline type tests.** `is_atom`, `is_map`, `is_binary`/`is_bitstring`, `element` and
  `tuple_size` are now written out in full. Before, they called `kernel-is-atom?` and similar
  helpers, which called the leaf for every vector, tuple or float. Every input the tests do not
  decide still goes to the captured leaf.
- **New templates.** `erlang/++/2` (a one-element left list becomes one `cons`; everything else
  is the leaf) and `erlang/atom_to_binary/2` (the captured leaf).

`string->symbol` of a constant name, which the emitter writes for keyword literals, is folded to
a symbol constant by `gsc` under `(standard-bindings)`. In C output for the whole of rt, it
appears 17 times as `___SYM__3a_tuple` and is never called at run time.

### rt.bl rewrites (same semantics on BEAM; fast cases first)

| Function | Change |
| --- | --- |
| `raw-cons` | `(erlang/++ `(~x) xs)`. The syntax-quoted list is a literal cons cell. The BEAM compiler folds `[x] ++ xs` into `[x\|xs]`, and native code gets one `cons`. This replaces the five-BIF dance. |
| `tuple2`, `tuple3` | `(erlang/list_to_tuple `(~a ~b))` |
| `seq-one`, `seq-two` | `` `(~x) ``, `` `(~a ~b) `` |
| `empty-list?` | `(erlang/=:= xs ())`, which is `(null? xs)` natively |
| `k-cons` | `is_list` comes first and conses inline. `nil` gives `` `(~x) ``. |
| `k-first`, `k-rest`, `k-empty?` | `()` is tested inline instead of through a call to `empty-list?`. `nil` is answered before the struct test. The Vector test is written with the literal module. |
| `unwrap-meta` | `(erlang/== (kind-kind x) :meta)` becomes an in-place test of a non-empty tuple whose first element is `:meta`, so the value is no longer classified. |
| `k-compare` | New clause: two keywords (atoms other than nil and the booleans) are ordered by term order. The general path computes each family inline for nil, booleans, atoms, integers, binaries and lists, and classifies only the rest. |
| `k-eqv` | An integer or binary against an integer, binary or list it is not identical to is decided `false`. Floats, decimals and `{:meta …}` wrappers still defer to `k-compare`. |
| `to-str` | Binary, nil, boolean, keyword and integer are answered before `kind-kind`, in kind-kind's order. |

`kind-kind`, `tuple-kind`, `struct-kind`, `struct-of?`, `reduce-reduced?`, `call-not-`,
`call-identical?` and `hash-hash-key` are unchanged in BL. The new templates are enough to turn
them into inline tests (see below).

No new rt definitions sit on hot paths. A definition that the pinned SDK's loaded `rt` module
lacks compiles as a `:global` reference (item D). An early draft added `vector-struct?`,
`value-family` and `to-str-classified` and saw exactly that, `rt/vector-struct?$g`. They are
inlined instead.

### What the native code is now (read from `out/rt-new.scm`)

- `kind-kind`: a chain of inline tests, `(or (eq? x bl-nil) (eq? x kernel-symbol-nil))`,
  `boolean?`, the inline atom test, `exact-integer?`, the float tag, the inline binary test,
  the inline map test, `pair?`/`null?` and the tuple tag. There is no host call before the
  struct or tuple sub-classifiers. `tuple-kind` is `tuple_size` inline plus ten `eq?` tests.
- `k-first`: `(or (null? x) (pair? x))`, then `(null? x)`, then `car`. `nil` is two `eq?`
  tests. Before, a list paid a call to `empty-list?` and `nil` paid a call to
  `kernel-erlang-equal?`.
- `empty-list?`: `(null? xs)`. `raw-cons`: `cons` plus the `++` template (one `cons`).
  `call-not-`: four `eq?` tests.
- `k-eqv` and `k-compare`: the first clause is still one `kernel-exact-equal?` or
  `kernel-erlang-equal?` call, which is right because both operands are variables. After it
  come inline type tests only.
- In the whole emitted rt, a `nil` literal never reaches `kernel-erlang-equal?` (0
  occurrences), and 666 literal comparisons are `eq?`.

## Checks

### Native semantic differential (`speed/kernel2/check.py`): see the counts below

```
research/native-seed/run run research/native-seed/speed/kernel2/oracle.bl -- research/native-seed/speed/kernel2/out
git show HEAD:priv/boot/rt.bl > research/native-seed/speed/kernel2/out/rt-orig.bl   # the original rt.bl (commit 970dc871e)
research/native-seed/run run research/native-seed/speed/kernel2/emit-rt.bl -- \
  $MAIN/research/native-seed/out/speed-closure/partition.json $MAIN/research/native-seed/out/speed-build/leaves.json \
  priv/boot/rt.bl research/native-seed/speed/kernel2/out/rt-new.scm \
  research/native-seed/speed/kernel2/out/rt-orig.bl research/native-seed/speed/kernel2/out/rt-base.scm
python3 research/native-seed/speed/kernel2/check.py
```

Each command ran under `work run --memory 3G` (the first two under 4G, before the rules
changed). `differences.py` lists the rt rows that differ from BEAM, with both outcomes.

- `oracle.bl` (BEAM, pinned SDK) evaluates the covered BIFs, the literal-equality cases and the
  checked rt functions over a 73-value corpus. That is round 1's 61 values plus `{:meta}`, nested
  meta, `{:bl_vec …}`, `{:$remote …}`, `{:__struct__ nil}`, lists of strings and of meta
  wrappers, `1.0e300`, `"true"`, `:zz` and meta-wrapped strings and floats. It writes 140 609
  rows. Private rt functions are checked against their original bodies.
- `emit-rt.bl` compiles this worktree's `rt.bl` and the original `rt.bl` on the pinned SDK. It
  puts each in place of the closure's rt unit and emits every rt function through
  `native.scheme/emit` with the AOT link context exactly as `native.chunks/checked-context`
  builds it, without `kernel-override`.
- `check.py` loads the worktree host sources, `host-kernel.scm`, one emitted rt and the oracle
  into the pinned gsi, in slices of 12 000 rows with one process per slice, for `base` (original
  rt.bl) and `new` (rewritten). The rules:
  - an rt row passes when `new` equals BEAM, or when `new` equals `base` (a difference compiled
    original rt.bl already has natively, that is, a leaf/BEAM difference);
  - every native-only input (`:nil`/`:true`/`:false` symbols, UTF16 fragments and keywords,
    refs, lazy seqs, UTF16 structs and tuples) must give the same outcome on both sides;
  - every template must equal its registered leaf, and every guard-position or literal
    template must return a boolean.

Result: **KERNEL2_CHECK_PASS**, with no rt failure, no exotic failure and no template failure.

| Check | Count |
| --- | --- |
| BEAM rows (oracle, after removing the 219 rows of three helpers that were dropped from rt.bl) | 140 391 |
| rt rows: compiled rewritten rt.bl = BEAM | 42 040 |
| rt rows: ≠ BEAM, and identical to compiled original rt.bl (an existing leaf/BEAM difference) | 77 |
| rt rows: a difference introduced by the rewrite | **0** |
| native-only exotic inputs: rewritten = original, outcome by outcome | 5 135 / 5 135 |
| BIF template = registered leaf (value or identical raise) | 92 376 |
| ... of which also = BEAM | 91 952 (424 rows where the leaf already differs from BEAM) |
| guard-position template results that are booleans | 27 642 |
| literal-equality templates = leaf, = BEAM, boolean | 5 840 each |
| `make_tuple(2^70, _)` rows skipped (the leaf would diverge, as in round 1) | 58 |

Per function, the rows equal to BEAM: `k-eqv`, `eqv`, `k-compare`, `compare`, `k-cons`, `cons`,
`raw-cons`, `tuple2`, `seq-two`, `struct-of?` 3 364/3 364 each; `call-identical?` and
`identical?` 3 362 (2 are -0.0 against 0.0); `kind-kind`, `kind-family`, `rank`, `call-not-`,
`not_`, `reduce-reduced?`, `empty-list?`, `seq-one`, `unwrap-meta` 73/73; `tuple3` 216/216.
`k-first`, `first`, `k-empty?`, `empty?` and `k-count` have 66 + 7. `k-rest`, `rest`, `k-seq`
and `k-next` have 65 + 8. `to-str` has 69 + 4, and `hash-hash-key` and `hash_key` 72 + 1. In
each "+ n", the native answer is identical to the original's. The 77 rows (`out/differences.txt`,
written by `differences.py`) fall into four groups, and none comes from rt.bl:
- 63 rows: `seq` of text (and `first`, `rest`, `next`, `count`, `empty?` of text) raises
  "native Unicode grapheme adapter is not installed". The harness does not load the
  `native-text` addon (`text.o1`).
- 8 rows: maps with more than 16 keys and struct maps print or order their entries differently,
  in `to-str` and in the entries of `rest`, because the native map leaves use a different
  iteration order. This is the leaf/BEAM term-order difference round 1 recorded.
- 4 rows: `0.0 =:= -0.0` is true in the native leaf, as round 1 recorded.
- 2 rows: `hash-hash-key` (and `hash_key`) of a list holding a `{:meta …}` wrapper calls `core/tuple`, which is
  not loaded in this rt-only harness.

Interpreted gsi 4.9.5 still dumps core in its GC after enough calls in one process. `check.py`
runs 2 000-row slices, and re-runs a slice that crashes without reporting a failure as two
halves, down to 250 rows. That happened 14 times in the final run. Every row was evaluated.

### Native microcost: not measured

The rules changed during the task: no before/after measurements, and speed is not an acceptance
criterion. I stopped a `gsc` build of the host for a compiled microbench and deleted the bench
scripts before they ran. "Compiles to inline tests" is shown above by reading the emitted Scheme.

### BEAM

One batch, at the end, as the updated rules allow. The toolchain was prepared through the
configured Nix backend.

```
work run --memory 4G --timeout 7200 -- ./bin/bl --cold test \
  test/bl/{numeric_equality,wave18_rt_port,host_test_rt,compiler_kernel_values,callable_kernel,wave19_str,host_meta,sorted,host_vector,host_set,reduce_kernel_cutover,wave27_prims_port,java_oracle_port,decimal_oracle_port,clojure_source_port}_test.bl
./bin/bl realm stop
```

Result: **14 of 15 files pass**: numeric equality 2 479 assertions, rt port 90, host rt 58,
kernel values 124, callable kernel 40, str 10, meta 46, sorted 93, vector 186, set 64, reduce
kernel cutover 451, prims 53, decimal oracle 2, clojure source port 88.

The one failure is `java_oracle_port_test`, row 9: `(.equals 1.0M 1.00M)`. The JVM says false;
bl says true. I believe this failure was already there before my change, but I could not check
it on the unmodified tree, because the rules allow only one test batch:
- The `java.manifest` row maps `equals` to `(= a b)`. `=` on decimals compares exact values by
  design (`k-eqv`'s docstring: `(= 1.5M 1.50M)` is true), and BigDecimal scale equality is
  `decimal/same-representation?`.
- For two decimals, the rewritten `k-eqv` takes none of the new clauses (it checks atom, integer
  and binary first, and a decimal is a map). It reaches `k-compare`'s general path as before.
  That path still classifies a map with `kind-family (kind-kind …)` and gives `:number`, then
  `eq-num-cmp`.

Treat it as unconfirmed at integration.

No BEAM microbench was run (same rule). The `[x] ++ xs` → `[x|xs]` fold is the claim of the
BEAM compiler's `sys_core_fold` for a literal-headed `++`. It is not measured here.

## Residual replicas

None in `host-kernel.scm` or `intrinsics.bl`. Everything left there is a BIF (category b) or its
captured leaf.

Outside my files:
- `native.bootstrap/original-binding-name` (the `$bl` indirection) is now unused by the kernel.
  CLOSURE owns `bootstrap.bl` and can delete it once `chunks.bl` stops calling `kernel-override`.
- The source-invocation gates (`source-callable!`, `source-invocation*!`) lost their round-1
  override with this change. They are FRONT's functions and now run as compiled BL.

## Requests for BACKEND (`scheme.bl`)

1. **`and`/`or` over boolean tests.** `(and (erlang/is_map x) (erlang/=:= …))` emits
   `(let ((and-tmp (...))) (let ((t and-tmp)) (if (or (eq? t #f) (eq? t bl-nil)) and-tmp …)))`,
   and that is then truthiness-tested again by the enclosing `cond`. When every operand is a
   `boolean-test?`, emit a Scheme `(and …)`/`(or …)` and use a plain `if`. This affects
   `k-compare`'s guards, `struct-of?`, `reduce-reduced?`, `hash-hash-key`, `call-not-` and
   `k-first`'s Vector test.
2. **Keyword dispatch.** Chains of `(erlang/== kd :k1)`, `(erlang/== kd :k2)` and so on are now
   `eq?` chains (in `k-first`, `k-rest-classified`, `kind-family`, `family-rank`,
   `literal-struct-kind` and `tuple-kind`). A `case` or `cond` whose tests are all `eq?` on one
   variable against keyword literals could become a Scheme `case`, which dispatches on symbols.
3. **Self-calls.** A self-recursive call emits `(let ((callee fnself_N)) (if (procedure? callee)
   (callee a0) (bl-invoke …)))`. `fnself_N` is always a procedure, so it can be called directly.
4. **Keyword literals** are `(string->symbol ":x")`. `gsc` folds them, but interpreted gsi pays
   for each one at run time. A quoted `'|:x|` would be free in both.

## Risks for integration

1. **`chunks.bl` still calls `intrinsics/kernel-override`.** CLOSURE owns that file. Until the
   call is removed, every emitted definition fails with an undefined function. The change
   needed in `native.chunks/emit-definition`:
   ```
   -         override (intrinsics/kernel-override ns (:name d) (bootstrap/original-binding-name ns (:name d)))
   ...
   -    (str (if override
   -          (str "(define " (bootstrap/original-binding-name ns (:name d)) " " value ")\n"
   -               "(define " binding " " override ")\n")
   -          (str "(define " binding " " value ")\n"))
   +    (str "(define " binding " " value ")\n"
   ```
   The emission in `speed/kernel2/emit-rt.bl` is exactly this.
2. Native speed is unmeasured by rule. Two things are slower than round 1's overrides by
   construction:
   - each facade (`first`, `eqv`, `compare`, `cons`, `hash_key`, `not_`, `identical?`) is now a
     call to its `k-*` owner, one extra tick and call;
   - compiled functions tick on entry and on every nested rt call.

   The main thread's final benchmark is the judge.
3. Native vector, struct and Reduced tests go through the `maps/get/3` leaf
   (`native-raw-map-get`) for `:__struct__`. Round 1 tested the `'vec` tag directly. That cost
   is in a BIF leaf, which belongs to DATA or V2, not rt.
4. The `is_map` template trusts the opaque-struct guard: registered structs are vectors longer
   than 2. The guard is still installed by `host-kernel.scm`.
5. Integration rebuilds the closure: `rt.bl` changed, so the rt unit and every chunk that links
   rt recompile.
