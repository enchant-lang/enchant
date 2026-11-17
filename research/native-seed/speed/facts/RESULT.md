# Workstream FACTS (item E1): one ANF fact pass, two backends

## What changed

**New namespace: `priv/host/facts.bl`, the pinned host module `Elixir.BeamLisp.Facts`.**
Natively it compiles as the namespace `host.facts`, declared in
`speed/facts/closure-additions.edn`. It has to be a pinned host module and not an
ordinary namespace because `host.optimize` runs while the boot namespaces are being
compiled, so its facts must load before any `BeamLisp.Ns.*` exists. The native
closure already compiles pinned host modules from their `.bl` source, so both targets
run this one file and nothing is replicated in host Scheme. It calls only
`host.compiler-data` (a base host module) and Erlang BIFs that have registered native
leaves. I checked each one against `round2-build/leaves.json`; `lists:zip`,
`lists:usort` and `erlang:min` have no leaves, so the module does not use them.

Hard cutover, in one change:
- **`priv/host/optimize.bl`**: the tag lattice is deleted. That covers `fact`,
  `refine`, `pattern-names`, `shadow`, `scaffold-body`, `literal-fn`, `native-arity`,
  `integer-list?`, `args-tag?`, `integer-op?`, `closed-int?`, `expression-fuel` and
  `int-callback`. The rewrites now read one-line wrappers over `BeamLisp.Facts`, and
  `:let` scoping uses `Facts/bind`. The rewrite preconditions stay in optimize.bl:
  predicate totality (`predicate-fuel`/`total-predicate?`) and materialised scalars.
  Version `optimize-3` becomes `optimize-4`; no test pins the version.
- **`research/native-seed/src/native/scheme.bl`, only the fact threading**:
  `forget-facts`, `integer-operand?`, `integer-binding` and `integer-branch` now read
  `BeamLisp.Facts`. The options key `:integer-facts` (a set of names) becomes `:facts`
  (a Facts environment, mapping each name to its value fact). `integer-intrinsic` and
  every call site are textually unchanged, so no other workstream's function was
  touched.
- **Registration as a codegen host**, following the SourceGraph/BuildPlan precedent
  (`cc9882f4d`): the `priv/build/seed.bl` host table (Facts goes before Optimize), and
  `priv/host/aot_cache.bl` `codegen_modules` + `pinned_host_source`, so that a change to
  facts.bl rotates the compiler key. The matching tests: `codegen_provenance_test`,
  `aot_cache_host_test`, and `seed_host_inventory_test` (73 → 74 modules, the three
  sorted lists and the table-order list).

## API (`BeamLisp.Facts`, version `facts-1`)

A fact is a map. An absent key means unknown, and unknown is always correct.
- Value keys: `:tag` is one of `:int | :bool | :float | :number | :integer-list`.
  `:lo`/`:hi` are inclusive integer bounds and appear only with `:int`. `:arity` and
  `:callback` are the callable facts the optimizer already used.
- Evaluation keys, from `expr`: `:raise?` is `false` only when evaluation cannot raise.
  `:footprint` is `:pure` when evaluation has no effect other than raising, otherwise
  `:unknown`.

| Function | Meaning |
| --- | --- |
| `(function-facts node)` / `(function-facts node params)` | **The interface function.** `node` is a fn, the compiler's self-application scaffold, or a `:defn-clause`. `params` is optional: value facts for a single plain-variable clause. Returns `{:version :params [{:name :fact}] :bindings [{:name :fact :ann}] :result fact :limited?}`. Bindings are in source pre-order across every clause and nested fn. |
| `(expr n env)` | The fact of one expression under a lexical environment (value + `:raise?` + `:footprint`). |
| `(bind env name init)`, `(forget env names)`, `(shadow env pats)`, `(refine env test)` | Scope threading, as both backends walk. `bind` always replaces, so shadowing never leaks a stale fact. `refine` handles `is_integer`/`is_float`/`is_number`/`is_function` and `(if a b false/nil)` chains. |
| `tag`, `int-fact?`, `bool-fact?`, `raise?`, `pure?`, `range-of` | Accessors. |
| `integer-op?`, `closed-int?`, `expression-fuel`, `int-callback`, `literal-fn`, `native-arity`, `pattern-names` | The former optimizer helpers, now shared. |

The rules are conservative and need no solver:
- Literals.
- Integer `+ - *` (canonical `:arith` or the erlang BIF) on Int operands gives Int
  with interval arithmetic, and cannot raise.
- Erlang term comparisons and type tests give Bool and cannot raise.
- Canonical numeric comparisons give Bool. They cannot raise only on numeric operands.
- `erlang:not` gives Bool, and cannot raise only on a Bool operand.
- `erlang:div`/`rem` on Ints give Int but may raise, which matches Core's `:zero-divisor`
  effect.
- `:if` joins its branches' facts (range hull). `:let`, `:do`, cons, integer lists,
  `lists:seq`/`lists:map` (as before) and literal fns (arity and closed integer
  callback; they cannot raise) are also covered.
- Anything else is unknown and may raise.

`expr` spends fuel (64) only where the pass recurses beyond the old lattice (`:let`,
`:if`, `:do`, non-arithmetic operations). Cons chains and `+ - *` trees cost nothing,
as before, so a large expression can lose only new facts, never an old one.

**Footprint:** `system.analyze` cannot run at compile time. It is a whole-program
library namespace (`priv/lib`) that needs Source, `typed` and `system.summary`, and it
is not loaded when the optimizer runs during boot. `:footprint` is therefore the local
conservative fact above (`:pure` or `:unknown`), not a `system.analyze` summary.

**Loops** stay conservative, as allowed. Native loop parameters are still forgotten
(`emit-source-loop` calls `forget-facts`), and `function-facts` treats fn parameters
as unknown. E2 extends this.

## Checks (exact commands, all from the worktree root, each under `work run --memory 4G --timeout 3000`)

1. **Site counts and emission, before → after** (`speed/facts/sites.bl`). For the
   closure's `rt` (468 defs) and `reader` (104 defs) units
   (`MAIN/NS/out/speed-closure-2/partition.json`; the parts are copied into
   `.local/facts/*/parts`, read-only for MAIN), it records:
   - each definition's Scheme through `native.scheme/emit` with `native.eval/context`:
     the sha, the erlang-operator callee sequence, and `:integer-intrinsics`;
   - the `BeamLisp.Optimize/run` evidence, refusals and per-definition sha of the
     optimized node.
   It does the same for the warm-core fixture (`benchmark/compiler-values.bl`,
   benchmark options). "After" compiles this checkout's facts.bl into the VM and loads
   optimize.bl at a probe atom.
   ```
   research/native-seed/run run research/native-seed/speed/facts/sites.bl -- $MAIN/research/native-seed/out/speed-closure-2/partition.json .local/facts/before/sites.etf        # at 073fe16e8, before any edit
   research/native-seed/run run research/native-seed/speed/facts/sites.bl -- $MAIN/research/native-seed/out/speed-closure-2/partition.json .local/facts/after1/sites.etf hot .local/facts/before/sites.etf
   ```
   | Unit | Integer intrinsic sites | Optimize evidence | Scheme | Optimized ANF |
   | --- | --- | --- | --- | --- |
   | reader (104 defs) | 36 → 36 | none → none | byte-identical, every def | identical, every def |
   | rt (468 defs) | 0 → 0 | `native-call` 22 → 22 | byte-identical, every def | identical, every def |
   | warm-core fixture (6 forms) | — | none → none | sha `9aa5284c…` unchanged (3835 bytes) | unchanged |

   `FACTS_COMPARE_PROBLEMS 0`, and the run printed no `FACTS_SCHEME_CHANGED` or
   `FACTS_OPTIMIZED_CHANGED` line. Every old site is still recognised at the same
   position. The pass finds no new site on these units, so there is no new-site list.
   The new facts (let-bound arithmetic results, `if` joins, Bool, ranges) have no
   integer-operator consumer there yet. That is E2's and BACKEND's ground.
2. **Fact scope on native emission**: the existing
   `research/native-seed/scan/emission-check.bl` covers let/fn/case/loop shadowing and
   `is_integer` refining only the then-branch. It runs against this facts.bl through
   `speed/facts/scope-check.bl`:
   `research/native-seed/run run research/native-seed/speed/facts/scope-check.bl -- .local/facts/scope`
   gave `SCAN_EMISSION_PASS 10`.
3. **D4 validation against the formal Core** (`speed/facts/validate.bl`):
   `research/native-seed/run -p research/formal-logic/src run research/native-seed/speed/facts/validate.bl -- .local/facts/validate`
   - The corpus is 28 functions that `formal.elaborate/prepare-function` accepts (Int
     and Bool parameters; arithmetic, comparisons, `quot`/`rem`/`mod`, truthiness,
     shadowing, nested ops, Bool lets). For each one, `formal.elaboration/check`
     re-checks the compiler-ANF/Core pair (`:checked` for all 28). `function-facts`
     runs on the same ANF.
   - Each ANF let is paired one to one, in pre-order, with its Core let.
   - Static checks: each `:int`/`:bool` fact must equal the `formal.core/typecheck`
     sort, and `:raise? false` requires typecheck to report no `:raise` effect.
   - Semantic checks: `formal.core/evaluate` over sample inputs (−7 … 2⁷⁰, true/false)
     evaluates every live binding in its actual environment. A no-raise fact must never
     raise; a value must lie in `[lo, hi]` and have its tag's sort.
   - **Result:** `{:functions 28 :violations 0 :evaluations 1802 :unknown-param-violations 0}`.
     The facts it found: 36 Int, 7 Bool, 10 ranges, 40 no-raise.
   - The same functions analysed without parameter facts also have 0 violations
     (unknown stays correct).
   - **Negative controls: 9 of 9 caught.** Each mutates a correct fact:
     - Int result claimed Bool, and Bool result claimed Int (sort);
     - `quot` result, and a `rem` binding, claimed raise-free (Core `:raise` effect);
     - a literal range shifted to `[6,6]` (evaluated 5);
     - a `[?,0]` range invented on `a+b` (evaluated 93);
     - a Bool binding claimed Int;
     - an `if` join range narrowed to `lo 1` (evaluated −1);
     - an Int claimed Float.

Not run: `./bin/bl --cold test` on the touched BEAM tests (`codegen_provenance_test`,
`aot_cache_host_test`, `seed_host_inventory_test`). The checkout SDK would need a Nix
SDK build, which CONTRACT3 forbids in agents. See Requests. No timing was measured.
No native image was built.

## Requests (for the main thread at integration)

1. **Regenerate the bootstrap floor** (`priv/bootstrap/seed/`). The table now has
   `Elixir.BeamLisp.Facts`; the floor and its manifest do not, and optimize.bl calls
   it. Then run `./bin/bl --cold test test/bl/codegen_provenance_test.bl test/bl/aot_cache_host_test.bl test/bl/seed_host_inventory_test.bl test/bl/seed_test.bl`
   plus the optimizer suites (`test/bl/optimizer_*_test.bl`) on the integrated SDK.
2. **Closure:** `update-closure.bl` picks up `speed/facts/closure-additions.edn`
   (`host.facts`, `:module Elixir.BeamLisp.Facts`). Every `:remote` from `native.scheme`
   to `BeamLisp.Facts` must link there. Without it, native emission refuses on
   `Elixir.BeamLisp.Facts/*`.
3. **BACKEND (N1)** may use `BeamLisp.Facts/bool-fact?` on `(BeamLisp.Facts/expr n (:facts options))`
   for "both sides are known booleans". Today `boolean-test?` (BACKEND's) is purely
   syntactic. I did not change it.

## Residual replicas

None. No host Scheme implements any part of facts.bl.

## Risks for integration

- **Not compiled natively yet.** `host.facts` uses only constructs that existing host
  modules use, plus leaf-checked BIFs. Still, the first closure update is the first
  native compile. Vector-valued ANF collections are handled through
  `BeamLisp.Vector/to_list` (a registered leaf).
- **The validation corpus is the elaborator's fragment.** Facts on maps, strings,
  `lists:seq`/`map` integer lists and callbacks are not validated against Core, which
  has no such sorts. They are the optimizer's existing, separately tested facts, moved
  unchanged.
- **Hot-loading caveat in the scripts**: replacing the SDK's own `BeamLisp.Optimize`
  in a running VM trips its Source-owner check
  (`:missing_sdk_dependency_unit_owner`). `sites.bl` therefore loads the edited
  optimizer at `NativeFactsProbe.Optimize`. On the integrated SDK, run `sites.bl`
  without `hot`.
- **Per-call cost**: `bind` now runs `expr` at every let on both backends, bounded by
  64 units of new-case fuel. Old cases cost what they did. No timing was taken, as the
  contract requires.
