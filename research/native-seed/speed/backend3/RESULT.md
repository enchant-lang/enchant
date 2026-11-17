# Workstream BACKEND, round 3: N1 (kernel emitter forms) and N2 (multi-arity rt fast paths)

Branch `native-r3-backend`. Changed files:
- `src/native/scheme.bl` (N1)
- `priv/boot/rt.bl` (N2)
- `speed/backend3/` (checks)

No image, SDK, benchmark or timing was run. All counts below are occurrence counts.

## N1: emitter (`scheme.bl`)

| Item | What is emitted now | Functions |
| --- | --- | --- |
| (a) boolean `and`/`or` | The compiler expands `(and a b)` to `(let [x a] (if x b x))`. When `a` is always `#t`/`#f`, this junction is emitted as `(let ((x A)) (if x B x))`, with no `(let ((t …)) (if (or (eq? t #f) (eq? t bl-nil)) …))` wrapper. A test that is boolean-valued also takes a plain `if`. Boolean-valued means one of: a guard-position erlang BIF (`boolean-test?`), a boolean literal, an `if` whose branches are both boolean, or a junction of boolean parts. Clause guards that `total?` accepts get the same treatment. | new `boolean-junction?`, `junction-part?`, `boolean-valued?`, `emit-junction`; `branch` tests `boolean-valued?`; one new `cond` arm in `emit` |
| (b) keyword dispatch | Two or more chained `if`s that test one variable with AOT-linked `erlang/==` or `=:=` against distinct plain keywords become one `(case x ((\|:a\| \|:b\|) A) … (else E))`. The chain qualifies only when the KERNEL template for each test is exactly `(eq? var kw)`: the emitter calls the link and compares its text. Adjacent arms with identical code share one clause. The tests are a variable and a literal, so they are not emitted; the branches are emitted in source order. The value layout is unchanged (D1): keywords are still interned `:name` symbols, and `case` uses `eqv?`, which is `eq?` on symbols. | new `plain-keyword?`, `keyword-test`, `keyword-dispatch`, `emit-keyword-dispatch`; the `:if` arm of `emit` |
| (c) direct self-calls | `((self self) args…)` whose self is the `letrec` local of a function scaffold (`emit-source-scaffold` with an `:fn` inner) emits `(let ((callee F)) (let* (…) (callee a0 …)))`, or `(apply callee arguments)` for a dynamic argument list. The `procedure?`/`bl-invoke` branch is gone. The local is always a procedure, because `bl-register-callable!` returns its argument. Multi-arity arms bind self to the `$blfn` tuple, so they remove themselves from the set and keep the generic call. | new `procedure-self?` and option `:procedure-selves`; `linked-language-call`, `emit-source-scaffold`, `emit-multi-arm` |
| (d) keyword constants | A keyword whose name is plain ASCII symbol text (alphanumerics and `-_?!*+<>=/.$%&~^@:`) is emitted as the quoted constant `'\|:name\|` instead of `(string->symbol ":name")`. Any other name keeps the escaped `string->symbol`. | new `symbol-safe-codes`, `keyword-datum`, `keyword-literal`; `literal` |

None of this touches tick, frame or budget emission (FRAMES) or the `:integer-facts` threading (FACTS). `emit-junction` *calls* `integer-binding` and `integer-branch` exactly as the `:let` and `:if` arms do, so that it threads facts identically. See Requests.

### Occurrence counts on the rt.bl unit (468 functions)

`speed/backend3/explain.py count FILE` produces these. *Before* is `out/rt-base.scm`: HEAD's rt.bl and HEAD's emitter, linked through `native.bootstrap/emit-definition`. All 468 of its defines are identical to round 2's `out/round2-build/stage1.scm` after compiler gensyms are renamed, and `out/stage1-rt.scm` gives the same counts. *N1* is `out/rt-n1.scm` (HEAD rt.bl, new emitter). *After* is `out/rt-new.scm` (new rt.bl, new emitter).

| Shape | Before | N1 | After |
| --- | --- | --- | --- |
| (a) truthiness wrappers `(if (or (eq? t #f) (eq? t bl-nil)) …)` | 287 | 131 | 131 |
| (b) keyword template tests `(let* ((a0 x) (a1 'k)) (eq? a0 a1))` | 303 | 32 | 32 |
| (b) Scheme `case` dispatches (keyword datums) | 0 | 45 (271) | 45 (271) |
| (c) self-call sites through a `procedure?` test | 51 / 51 | 0 / 51 | 0 / 51 |
| `(if (procedure? callee) …)`, all | 101 | 50 | 51 |
| (d) `(string->symbol …)` | 1 185 | 0 | 0 |
| (d) quoted keyword constants `'\|:k\|` | 0 | 896 | 906 |

The 131 wrappers left in rt test values that are not known booleans:
- 67 test calls to compiled rt functions, such as `struct-of?` and `kind-*?`;
- the rest test leaf results, such as `maps/get`, or junctions whose first operand is not boolean (8 `and`/`or` junctions).

The 32 keyword tests left are single tests, not chains. The 50 `procedure?` tests left are calls through Var/global cells and closures. After N2 there is one more of them, in `nth`/`conj`, and 10 more quoted constants (`:__struct__` and the Vector module).

The same counts over all 1 723 closure definitions (`chunks inspect`): wrappers 3 198 → 2 400, `case` 0 → 59 (332 datums), self-call tests 259 → 0, `string->symbol` 7 067 → 2.

## N2: multi-arity rt fast paths (`rt.bl`)

Each fast path is the exact answer the original clauses reach for that input. Every other input falls through to the original body, which is unchanged (D3). No rt definition was added: a name missing from the pinned SDK's rt module would link as `:global` (KERNEL2).

| Function | Fast path (inline type tests) | Was |
| --- | --- | --- |
| `k-nth/2` | a list with an integer `i ≥ 0` → `nth-list`; a Vector (`is_map` plus `maps/get :__struct__` `=:=` the literal module) with an integer `i ≥ 0` → `Vector/nth` | `lists-at` → `nth-list`; a vector went through `struct-of?` after three tests |
| `k-nth/3` | the same two cases compute `v` directly; `k-nth/2` otherwise. The nil/`in-range?` default logic is unchanged. | always a `k-nth/2` call |
| `nth/2` (facade, 141 call sites in stage 1) | `k-nth/2`'s two fast paths, else `k-nth` | always a `k-nth` call |
| `coll-conj/2` | a list → `raw-cons`; a Vector → `Vector/conj`; else the original `kind-kind` dispatch, inline | a `kind-kind` call first |
| `conj/2` (facade, 25 call sites) | `coll-conj/2`'s two fast paths, else `coll-conj` | always a `coll-conj` call |

Exactness, from the source:
- `kind-kind` answers `:list` for every `is_list` term and `:vector` for exactly a map whose `__struct__` is the Vector module.
- `lists-at` with an integer `i ≥ 0` is `nth-list`.

`coll-get`/`get` are KEYS's and are untouched. `k-fold`/`k-reduce` dispatch once per traversal and were left alone.

## Checks

Every bl or VM command ran under `work run --memory 4G --timeout …`.

Commands, from the worktree, with `B3=research/native-seed/speed/backend3`:

```
# 0. out/old-src = `git archive HEAD research/native-seed/src`; out/rt-orig.bl = `git show HEAD:priv/boot/rt.bl`
# 1. rt emission: base (HEAD src tree, out/old-src) and new, each in one VM (emit.sh)
work run --memory 4G --timeout 3600 -- $B3/emit.sh
#    = bl-src.sh out/old-src WT run $B3/emit-rt.bl -- speed-closure-2/partition.json round2-build/leaves.json out/rt-orig.bl out/rt-base.scm
#      bl-src.sh src         WT run $B3/emit-rt.bl -- … priv/boot/rt.bl out/rt-new.scm out/rt-orig.bl out/rt-n1.scm
# 2. whole-closure AOT emission, old and new emitter (inspect-both.sh → inspect-run.sh ×2)
work run --memory 4G --timeout 7200 -- $B3/inspect-both.sh
# 3. non-AOT emitter equality, five option sets (round 2's equality.bl inputs)
work run --memory 4G --timeout 3600 -- $B3/bl-src.sh research/native-seed/src research/native-seed \
  -p research/native-seed/speed run $B3/equality.bl -- $B3/out/eq benchmark/compiler-values.bl \
  speed/control/corpus.bl src/native/{scheme,eval,resolution,intrinsics}.bl
python3 $B3/explain.py forms $B3/out/rt-base.scm $B3/out/rt-n1.scm --gensyms
python3 $B3/explain.py forms $B3/out/inspect-old/inspect.scm $B3/out/inspect-new/inspect.scm
python3 $B3/explain.py pairs $B3/out/eq/eq-old.txt $B3/out/eq/eq-new.txt
# 4. native differential
work run --memory 4G --timeout 3600 -- $B3/bl-src.sh research/native-seed/src . run $B3/oracle.bl -- $B3/out
work run --memory 4G --timeout 7200 -- python3 $B3/check.py
# 5. BEAM
work run --memory 4G --timeout 10800 -- ./bin/bl --cold test test/bl/{numeric_equality,wave18_rt_port,\
host_test_rt,compiler_kernel_values,callable_kernel,wave19_str,host_meta,sorted,host_vector,host_set,\
reduce_kernel_cutover,wave27_prims_port,java_oracle_port,decimal_oracle_port,clojure_source_port,\
conj_variadic,host_lazy_seq,wave27_destructure_port}_test.bl
./bin/bl realm stop
```

### (1) Every emission change is one of (a)–(d)

`explain.py` parses both sides as Scheme data. It applies to both the same four canonical rewrites, each the inverse of exactly one N1 change:
- (a) a truthiness wrapper becomes a plain `if`;
- (b) a `case` becomes an `eq?` if-chain, and the template test becomes `(eq? x 'k)`;
- (c) a `procedure?` branch becomes a direct call, inside `(let ((callee F)) …)`, where `F` is a scaffold `letrec` local;
- (d) `(string->symbol ":k")` and `'|:k|` become one constant.

A pair passes if the texts are equal, or if the canonical forms are equal. The rewrites that fire a different number of times on the two sides are the explanation. A refusal must be identical.

| Corpus | Compared | Identical | Different, all explained | Unexplained |
| --- | --- | --- | --- | --- |
| rt unit, AOT link (`rt-base` vs `rt-n1`, gensyms renamed) | 3 306 forms (468 defines) | 3 113 | 193 (a 6, c 15, d 99, mixed 73) | **0** |
| whole closure, AOT link (`chunks inspect`, 1 723 definitions) | 12 114 forms | 11 101 | 1 013 (d 664, a+d 163, c+d 41, a 39, c 34, others 72) | **0** |
| round 2's emitter equality: fixture, control corpus, `scheme`/`eval`/`resolution`/`intrinsics` sources × 5 option sets, plus helpers | 2 353 | 1 744 (894 identical refusals) | 609 (d 605, a+d 4) | **0** |

`EXPLAIN_OK` is printed for all three.
- `inspect-old/inspect.scm` holds all 1 723 defines verbatim from round 2's `stage1.scm`, so the "before" side is the shipped bytes. `seed-links.scm` is identical.
- The equality corpus now has 155 nodes and 2 353 comparisons, against round 2's 141 and 2 143, because its source inputs have grown.
- (b) and (c) apply only under `:aot-link`, so they do not appear in the non-AOT equality. Emission counts are identical in every comparison.

### (2) Native differential (`check.py`, round 2's kernel2 harness adapted): `KERNEL2_CHECK_PASS`

- `base` is HEAD's rt.bl with HEAD's emitter.
- `new` is this branch's rt.bl with this branch's emitter.

Both ran interpreted in the pinned gsi with the current host load order. 10 slices were re-run as halves after gsi GC crashes, and every row was evaluated.

| Check | Count |
| --- | --- |
| oracle rows (BEAM, pinned SDK) | 147 027 |
| round-2 rt rows: new = BEAM | 42 033 |
| round-2 rt rows: new ≠ BEAM, new = base | 84 |
| round-2 rt rows: a difference introduced by this branch | **0** |
| N2 rows (`k-nth`/`nth` /2 and /3 over 79 values × 12 indices × 2 defaults; `coll-conj`/`conj` × 6 operands): new = BEAM | **6 636 / 6 636** |
| native-only exotic inputs, new = base outcome by outcome (now including the N2 functions) | 6 156 / 6 156 |
| BIF template = leaf / = BEAM / guard booleans / literal templates | 92 376 / 91 952 / 27 642 / 5 840 |

The round-2 rt rows total 42 117, as in round 2. Round 2 had 42 040 equal to BEAM and 77 not. There are 7 more non-equal rows now, all identical in `base`. They come from the current host, not from this branch:
- `{:a 1 :b 2}` now iterates as `:a, :b` natively (`first`, `rest`, `seq`, `next`, `to-str`; Q1, order unspecified);
- the other 77 are round 2's known groups (no text adapter, map order, `-0.0`, `core/tuple`).

Harness adaptations:
- `host-lazy.scm` no longer exists, so the harness loads `prepare-host.py`'s host list.
- The lazy-seq exotic was dropped, because lazy seqs are compiled BL now and not loaded in this rt-only harness.
- Multi-arity bindings are called with `bl-invoke`.
- `emit-rt.bl` now emits through `native.bootstrap/link-plan` and `emit-definition`. kernel2's private link context no longer resolves the closure (`native.resolution/build` is gone).

### (3) BEAM: 17 of 18 files pass

| File | Assertions passed |
| --- | --- |
| numeric equality | 2 479 |
| rt port | 90 |
| host rt | 58 |
| kernel values | 124 |
| callable kernel | 40 |
| str | 10 |
| meta | 46 |
| sorted | 93 |
| vector | 186 |
| set | 64 |
| reduce cutover | 451 |
| prims | 53 |
| decimal oracle | 2 |
| clojure source port | 88 |
| conj variadic | 11 |
| lazy-seq | 207 |
| destructure | 11 |

The failure is `java_oracle_port`, row 9, `(.equals 1.0M 1.00M)`. It is the same failure KERNEL2 recorded before this change: decimal `=` is by value, and neither N2 path touches decimals. `./bin/bl realm stop`: not running.

## Requests

1. **FACTS (integration of `scheme.bl`):** `emit-junction` repeats the `:let`/`:if` fact calls (`integer-binding` on the init, `integer-branch` on the test). If E1 changes those signatures or replaces `:integer-facts`, update `emit-junction` in the same way. When FACTS supplies Bool facts per binding, `boolean-valued?` should read them. Today it decides structurally, so a variable bound to a boolean elsewhere is still wrapped.
2. **Compiler (`case` macro, not owned):** BL `case` on keywords lowers to `(rt/eqv v :k)` calls, not `erlang/==`. Those are not dispatched: 0 in rt, but common in `native.scheme` itself, e.g. `binders-into`'s `case (:pop p)`. `(= x :k)` is also true for a `{:meta :k …}` wrapper (`k-eqv`), so the emitter must not turn it into `eq?`. The exact lowering is `(if (erlang/is_tuple v) <eqv chain> (case v …))`, or a `case` macro that emits `erlang/=:=` plus that tuple fallback. That decision belongs to the compiler/KEYS (Q3 value equality), not the emitter.
3. **KERNEL/V2:** the 67 remaining wrapped tests in rt are calls to small compiled predicates. A boolean return fact per definition, from FACTS or a declared `^boolean`, would remove them.

## Residual replicas

None. No host Scheme was added. N2 is BL in `rt.bl`.

## Risks for integration

- **(d) and the native reader.** Emitted Scheme now contains `|:k|` symbols. gsc and gsi read them, as the interpreted differential and the whole-closure parse show. Any tool that scans emitted Scheme for `string->symbol` or with a non-Scheme tokenizer needs to know this. I found none in `NS` besides frozen test emitters.
- **(b) relies on the template text.** The `case` dispatch requires `remote-template` to emit exactly `(eq? a0 a1)` or `(eq? a1 a0)` for a keyword literal. If KERNEL changes that text, the dispatch silently stops applying. That is a missed optimisation, never a wrong answer.
- **(c) and redefinition.** Only scaffold-local self-calls are direct. Calls to a definition's own global name still go through its Var cell (LINK N3), so dev-image redefinition is unaffected.
- **N2 facades duplicate the fast path text** of `k-nth` and `coll-conj` in `nth` and `conj`. A future change to the underlying clause semantics, for example KEYS changing what a Vector is, must update both. The original bodies remain the single fallback.
- **Byte changes.** Integration recompiles every unit, because `scheme.bl` changed and nearly every definition's bytes change through (d). `rt.bl` changed, so the rt unit relinks.
- **Checks ran interpreted on gsi only.** Compiled behaviour and speed are for the main thread's benchmark.
- `speed/backend3/old-scheme.bl` is a frozen copy of HEAD's emitter, used only by `equality.bl`. Delete it after integration.

---

# Second pass: cross-workstream requests (after `git merge worktree-native-speed`)

The integrated tip (12241b695: LINK, KEYS, FACTS, FRAMES and BACKEND) was merged into `native-r3-backend`. In this pass BACKEND owns all of `scheme.bl`. The two consumers in `bootstrap.bl` that the requests need were changed too (see Risks).

## Changes

| # | Request | What is emitted now | Where |
| --- | --- | --- | --- |
| (e) | LINK: sealed global calls | A `:global` callee with static arguments consults `(:aot-link options) :global` (`bootstrap/global-link`). A linked target is called as `(v_ns/f$N a…)`, like a linked remote, with no `(let ((callee v_ns/f)) (if (procedure? callee) …))`. Dev plans have no `:global` hook, so their bytes do not change. | `scheme.bl` `global-call-link`, `linked-language-call` |
| (i) | MEASURE #2: variadic and multi-arity calls | `global-link` also links a static call whose arity has no fixed arm, but which a variadic arm accepts (arity ≥ its minimum). The call is `(v_ns/f$v a1…am (list rest…))`, exactly as `native-resolve-call` splits the arguments. `core/list` (858 sites) and `native.scheme/glue` (109) were the largest users of `bl-invoke` → `native-resolve-call` in the sealed closure. | `bootstrap.bl` `global-link`, new `variadic-call` |
| (f) | LINK: inlinable arity cells | A sealed definition with exactly one fixed arity and no variadic arm emits `(define v_ns/f$N (lambda (formals) (h-tick)? body))`, a literal lambda that Gambit can inline. The definition's value is `(bl-register-callable! (case-lambda ((formals) (v_ns/f$N formals)) (argv function-clause)) N)`, which keeps the wrong-arity arm, because `bl-invoke` applies procedures directly. Self-calls of that arity call the cell; the self as a value is `v_ns/f`. Ticks and sites are unchanged: the entry tick sits in the lambda only, and the forwarding arm has none. This applies in release only; source-frame emission keeps the scaffold. | `scheme.bl` new `emit-sealed-function`, `fixed-parts`, `function-ticks?`, `:self-cells`; `bootstrap.bl` `sealed-raw`, `emit-definition`, `sealed-link-definition` (a `raw` cell argument), `link-definition` (new arity) |
| (a′) | FACTS: Bool facts | `boolean-valued?` (and with it `branch` and the junctions) also accepts any expression that `BeamLisp.Facts/expr` tags `:bool` under `:facts`, such as a variable bound to a comparison. `emit-junction` was re-checked against the merged `:let`/`:if` arms: it emits the init with `operand-options`, binds through `integer-binding` (now `Facts/bind`), and emits then/else with `integer-branch` (now `Facts/refine`) of the test, so it matches the `:let` + `:if` it replaces. | `boolean-junction?`, `junction-part?`, `boolean-valued?`, `branch` (now take options) |
| (g) | FRAMES: one loop lowering | `loop-plan` no longer lowers unchecked loops under `:source-frames?`, so debug lowers exactly the loops release lowers. `body-calls?`'s `:frames?` flag is deleted. | `loop-plan`, `body-calls?`, `function-expression` |
| (h) | MEASURE #5: constant literals | Under a definition's constant sink (set by `bootstrap/emit-definition`), every `:lit` whose Scheme builds a value (set, map, vector, list, tuple, struct, float, decimal, non-symbol-safe keyword) is emitted once as `(define v_ns/f$q<i> LIT)`. It is referenced by name and built at load. A function's constants follow its define; any other definition's constants precede it. `compiler/kernel-special-forms-literal`, `kernel-java-lang-classes-literal` and the six other `kernel-*-literal` tables now return a constant. Emitted keyword interning (`(bl-key "match")`, `(bl-key "nomatch")`, the self-module tuple) is now quoted constants. | `scheme.bl` new `hoisted`, `:lit`, `clauses`, `:recv`; `bootstrap.bl` `constant-defines`, `emit-definition`, `self-module` |

## Checks

All of these come from one job, `speed/backend3/pass2.sh`, under `work run --memory 4G --timeout 10800`. OLD is the merged tip's `src` (`out/r2/old-src`, `git archive HEAD`). NEW is this worktree. The pinned SDK predates `Elixir.BeamLisp.Facts`, so every run goes through `speed/backend3/facts-run.bl`, which compiles and loads `priv/host/facts.bl` first, as `speed/facts/sites.bl` does. `chunks inspect` now asserts against the moved-on main checkout, so the closure emission uses `speed/backend3/emit-closure.bl`: the same link plan and `emit-definition` over every named definition.

### explain.py: every difference reduces to a named transform

Four transforms are new in `explain.py`, each the inverse of one change:
- (e): the `procedure?`-tested call of a binding becomes `(binding$N A…)`.
- (i): `(f$v a… (list r…))` becomes `(f$N a… r…)`.
- (f): forwarding value plus raw lambda become scaffold plus `native-arity-entry`.
- (h): `$q` constants are substituted back.

(d) also covers `(bl-key "x")`. (g) accepts a frame-variant pair when debug now has fewer named loops than before, and exactly as many as release of the same node.

| Corpus | Compared | Identical | Explained | Unexplained | Transform occurrences |
| --- | --- | --- | --- | --- | --- |
| whole closure, sealed AOT (1 723 definitions, 33 units) | 8 716 forms | 8 067 | 649 | **0** | e 2 504, i 973, f 1 542, h 62 constants (62 references), a 74, d 276 + 64 `bl-key` |
| rt unit, sealed AOT (475 functions, gensyms renamed) | 2 405 forms | 2 394 | 11 | **0** | f 450, e 36, h 2, a 3 |
| emitter equality (non-AOT, five option sets) | 2 548 | 2 540 | 8 | **0** | a 24, d 108 (`bl-key` → quoted); g 0 |

`EXPLAIN_OK` on all three. (g) never fired: neither the equality corpus nor the FRAMES corpus contains a loop the verdicts call unsafe. The FRAMES harness below is the behavioural check.

### Occurrence counts (OLD → NEW)

| Shape | rt unit | whole closure |
| --- | --- | --- |
| `(if (procedure? callee) …)` | 87 → 51 | 4 216 → 1 710 |
| `(native-arity-entry …)` cells | 501 → 51 | 1 794 → 252 |
| literal-lambda arity cells | 0 → 450 | 0 → 1 542 |
| `$v` variadic-arm calls | 27 → 27 | 406 → 1 379 |
| truthiness wrappers | 136 → 133 | 2 400 → 2 325 |
| hoisted constants (`$q`) | 0 → 2 | 0 → 62 |
| `bl-set-from-list` inside function bodies | 0 → 0 | 9 → 0 (8 are now load-time `$q` constants) |

### Native rt differential (`check.py`): `KERNEL2_CHECK_PASS`

Here `base` is the merged tip's rt.bl with the merged tip's emitter, and `new` is the same rt.bl with this pass's emitter. Both are sealed AOT emission, with raw lambdas and constants loaded in the harness.

The first run of `check.py` was taken before (h) and (i) were added; it showed 0 differences introduced. The re-run after (h)/(i) is recorded in `out/r2/check2.log`; its numbers follow.

| Check | Count |
| --- | --- |
| round-2 rt rows: new = BEAM | 42 019 |
| round-2 rt rows: new ≠ BEAM, new = base | 98 |
| rt rows: difference introduced by this pass | **0** |
| N2 rows = BEAM | 6 636 / 6 636 |
| native-only exotic inputs, new = base | 6 156 / 6 156 |
| templates = leaf / = BEAM / guard booleans | 92 376 / 91 952 / 27 642 |

The 98 non-BEAM rows (84 in pass 1) are all identical in `base`. They come from the merged tip's rt.bl and host, for example KEYS's value-equality keys against the pinned SDK's oracle and native map order, not from the emitter.

### FRAMES harness (`speed/frames/check.bl` + `run.py`, NEW emitted here, OLD = FRAMES's pre-N4 reference)

```
old-release / old-frames / new-release / new-frames: FRAMES_CHECKS 72 FAILURES 0 (each)
release: 47 observation lines; old == new: True
frames:  47 observation lines; old == new: True
```

TICKS and TURNS equal FRAMES's own recorded numbers, for example `work-calls` 401 → 201 and `mapped` 9 → 1.

No BEAM test was needed: this pass changes only `research/native-seed/src` (`scheme.bl`, `bootstrap.bl`), not `priv/`. No `bl` realm was started.

## Requests (pass 2)

1. **LINK / owner of `bootstrap.bl`:** review the consumers I added. They are:
   - `sealed-raw` and the `raw` argument of `sealed-link-definition`/`link-definition` (a new arity, with old callers unchanged);
   - `variadic-call` in `global-link`;
   - the constant sink and `constant-defines` in `emit-definition`;
   - `self-module` with quoted keywords.

   `speed/data|lazy|services|kernel2` keep private copies of `link-definition` with the old arity, and they are unaffected.
2. **Host (`native-resolve-call`, `native-multi-callable?`):** they intern `(bl-key "$blfn")` on every call (MEASURE #13). That is host code, not emitted code. A module-level `(define native-blfn-key (bl-key "$blfn"))` would end it.
3. **`chunks.bl inspect`:** asserts that the main checkout's sources still match the closure SHAs. After integration they no longer do, so it fails. `speed/backend3/emit-closure.bl` is the assertion-free equivalent.

## Risks (pass 2)

- **(f) changes procedure identity.** A sealed single-arity definition now has two procedures: the registered forwarding value `v_ns/f` and the cell `v_ns/f$N`. Callers through cells never see the value, and every value use, including the self as a value, is `v_ns/f`. Anything that compared an arity cell with the binding (`eq?`) would now differ. I found nothing that does.
- **(f) interacts with splitting.** `v_ns/f$N` is still a `$` name after its head, so it stays in its unit. Cross-unit inlining still needs the caller and callee in one Gambit unit (LINK's note).
- **(h) and constants of non-function definitions** are emitted before their define, so the splitter attaches them to the previous group. This is correct, because units load in order, but a value definition's constants can sit in the neighbouring unit.
- **(h) and identity:** every evaluation of one quoted literal now returns the same object. This matches BEAM's literal pool. A program that relied on fresh literals (`identical?`) would see a difference, as it would on BEAM.
- **(i) applies only when sealed,** because it goes through `global-link`. Dev images keep `bl-invoke` for variadic global calls.
- **(a′) relies on facts.bl's `:bool` tag meaning exactly `#t`/`#f` natively.** That holds for BIF and comparison results and boolean literals. If `facts.bl` ever tags a value that can be the native `:true` symbol, the plain `if` would misread it.
- **The pinned SDK lacks `BeamLisp.Facts`.** Every BEAM-side emitter run must load `facts.bl` first (`facts-run.bl`) until the SDK is re-pinned.
