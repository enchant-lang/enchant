# Workstream C: compiled control, with nothing interpreted

Branch `native-speed-control`. Files changed: `src/native/scheme.bl` (C-owned
functions only) and the new `host/host-match.scm`. Test files are under
`speed/control/`.

## Changes (`src/native/scheme.bl`)

| Change | Functions |
| --- | --- |
| Every pattern kind now compiles to decision code. The runtime pattern-data path is gone: `pattern`, the `bl-match-args` / `(cdr (assoc "x" bindings))` emission, `direct-pattern?`, `direct-pattern(s)` and `direct-arguments` are deleted. | new: `match-pattern`, `match-each`, `match-entries`, `match-indexed`, `match-arguments`, `map-key-bindings`, `literal-test`, `tag-test`, `with-subject`, `pattern-child`, `vector-pattern?`, `vector-items-pattern` |
| Clause chains: fixed subjects, one shared failure continuation per clause (`clause-next` thunk). Only the constant fallback is inlined. Clauses after an irrefutable clause are not emitted. A clause of the wrong width never matches. | `clauses` (rewritten), `irrefutable?` |
| Functions with several clauses of the same width get fixed formals `fa0…` in a `case-lambda`. The wrong-arity arm keeps the same entry tick/frame and `function clause` error. Only a mixed-width chain still uses `(lambda argv …)`, and that is direct list matching, not pattern data. The single distinct-variable fast path is unchanged. | `function-expression`, `fixed-function` |
| `:case` / `:recv` / catch clauses match their host locals (`subject`, `message`, `caught-kind caught-reason`) directly. Before, they built `(list subject)`. | `emit` `:case` `:recv`, `emit-try` |
| A guard skips `bl-guard` when `total?` proves it cannot raise. Otherwise it keeps `bl-guard` (any exception counts as false). | `total?`, `boolean-test?`, `atomic-literal?` |
| `:if` and guard truthiness are inline: `(let ((t X)) (if (or (eq? t #f) (eq? t bl-nil)) E T))`. When the test is an erlang boolean BIF (type tests, comparisons, `not`), it is a plain `(if X T E)`. | `branch`, `emit` `:if` |
| Direct named loops, integer facts and integer intrinsics are the default. The `:scan-v1?` / `:specialize-v1?` gating is removed. | `emit` head, `integer-branch`, `integer-intrinsic`, `integer-binding`, `emit-source-loop`, `:let`, `:fn` |
| Loop safety now takes one walk per outermost loop region. The verdicts travel in options as `:loop-verdicts`. This replaces the per-loop fuel walk (`atom` + `vals/dissoc` per node, repeated for nested loops). | `structural-loop-parts`, `loop-walk`, `loop-walk-clauses`, `loop-verdicts`, `loop-plan` (replace `scan-loop-safe?` / `scan-loop-parts`) |
| Integer facts are now also dropped for catch stack binders and the scaffold self, and `forget-facts` returns the options unchanged when there are no facts. | `forget-facts`, `emit-try`, `emit-source-scaffold` |

I did not touch the L-owned code: `remote`, `ordered-call`, `ordered-language-call`, `ordered-target-call`, `multi-layout`, `emit-multi*`, or the `:global` `:remote` `:apply` `:invoke` cases. The one exception: the `:remote` case already contained the `integer-intrinsic` call, and its line did not change. `native.scheme` adds no new requires (it uses `clojure.string/starts-with?`, and `clojure.string` was already required). The `:source-frames?` paths (frames, `bl-source-call`, the unchecked loop lowering) and the `:emission-counts` keys `:compiled-pattern-clauses`, `:direct-loops` and `:integer-intrinsics` are kept. `:generic-pattern-clauses` no longer exists.

## Why the results are the same

Each argument mirrors the host `bl-match` that is actually installed (the `set!` in `host-values.scm`):

- **var**: `_` never unifies and binds nothing (the body cannot name it). A variable repeated within one clause is checked with `(bl-key-equal? first new)`, the host's argument order.
- **lit / nil**: `bl-key-equal?`. Two literal kinds use a faster test that gives the same answer:
  - Keywords other than `true`/`false`/`nil` use `eq?`. Rank 2 compares names, and only the interned symbol carries that name.
  - Exact integers use `eqv?` (rank 0 holds only exact integers).
  - Booleans, nil, text, floats and others keep `bl-key-equal?`, because `':true` equals `#t` in `bl-key-compare`.
- **tuple**: the inlined `bl-tag?` check plus a storage-length check. This equals `bl-match-args` over `bl-items` of a tuple.
- **cons / alias**: same order as the host. The subject is bound once.
- **map**: `bl-tag? 'map`, then for each pair in order `native-map-entry`, where a missing key fails and a nil value matches.
  - Literal keys are emitted inline.
  - Non-literal keys are evaluated once per clause attempt, before matching, in the clause's outer scope (`pk<path>`). So they cannot see this clause's binders, as before. The `key-capture` shape checks this.
- **struct**: `bl-match-struct-fields` follows the host. It takes the fields from `native-struct-fields` and checks the module with `bl-key-equal?`. For a plain map it reads `__struct__` directly. That is equivalent, because for maps `native-struct-fields` returns the map itself.
- **vector**: `bl-tag? 'vec`, then the items are matched as a tuple. If the inner pattern is a ptuple, this uses count + `native-vector-ref`. Otherwise it uses `(bl-tuple (bl-items v))`, exactly as the host does.
- **Order of side effects**: the host matcher ran no Source code, and the only Source code here is the hoisted keys, so evaluation order is unchanged. The matching code calls only host predicates that do not raise.
- **Guards**: `total?` admits only these:
  - literals and variables
  - `if` over total parts, with integer refinement on the then branch
  - unary erlang type tests. All of them are total host leaves: `is_number`, `is_pid`, `is_port` and `is_reference` live in `host-extra.scm`.
  - `== =:= /= =/=` with one atomic non-text literal operand. Their `bl-key-compare` / `native-erlang-equal?` cannot reach `string<?` on a UTF-16 fragment.
  - integer intrinsics on integer-fact operands
  - `not` of a boolean BIF or a boolean literal. `erlang/not/1` raises badarg on a non-boolean.

  Anything else (`tuple_size`, `element`, `rem`, `<` on unknown operands, `map?` expansions) keeps `bl-guard`.
- **Loops**: a lowered loop gets the same verdict as `scan-loop-safe?` without the fuel limit. Its self may appear only as `((self self) …)` with its own arity, in tail position (through let body, if branches and the last `do` statement); no let may rebind it, and nested fns and case or try bodies do not count as tail positions. `scan/emission-check.bl` still passes all 10 cases. Integer facts follow commit `599c7dabe`: clause binders, fn params, loop params, let rebinding, catch binders and the scaffold self all drop the fact.

## Checks

The commands, run from the worktree root:

```
research/native-seed/run -p research/native-seed/speed run research/native-seed/speed/control/check.bl -- OUT
timeout 120 $(jq -r .gambit research/native-seed/toolchain-pin.json)/bin/gsi OUT/program.scm
research/native-seed/run -p research/native-seed/speed run research/native-seed/speed/control/size.bl
research/native-seed/run run research/native-seed/scan/emission-check.bl
```

- **`check.bl` + gsi**: `CONTROL_CHECKS 768 FAILURES 0 OLD_DIFFERS 0 SHAPE_VALUES 326` (gsi takes about 5 s).
  - **141 checks against BEAM.** The `speed/control/corpus.bl` cases ran on BEAM, and the same forms were compiled by the SDK compiler (`compiler/compile`, `:target :js`, fresh state per form) and emitted with `native.eval/context` resolvers.
    - Coverage: guarded multi-clause functions with raising and non-raising guards; type predicates; comparisons; int ranges with bignum operands; `not`, `or`; multi-arity; variadic; `[_ _]`; same-width clauses; wrong-arity calls.
    - Also: loops (sum to 100000, factorial with integer facts up to 40!), fixnum overflow (`+ * -` around 2^61), mixed integer/float, `if` truthiness, `try` with throw, error and finally.
    - Receive patterns are rewritten to `case`, with the `after` body as the final catch-all clause. They cover tuple-or-vector alternatives, nested tuples, maps with present, absent and nil keys and extra entries, nested maps, string/int/nil/true/keyword literals, empty vector, and guarded receive clauses.
    - The frozen reference emitter (`speed/control/reference.bl`, the old `scheme.bl`) agrees on all of these.
  - **603 checks of hand-built ANF against the reference generic `bl-match-args` emitter**, over 43 subjects × 11 shapes. The shapes cover repeated variables in tuples, maps and across function arguments, cons/nil, alias, int/string/nil/keyword map keys, generic struct / struct without fields / Set struct, vector of ptuple and vector with a variable inner pattern, every literal kind, a non-literal map key, total and raising guards, and a mixed-width function. 326 of these return values; the rest raise.
  - **24 checks on the benchmark's six forms**, emitted under the benchmark's own options. They emit without refusal: new 3830 B against old 3946 B. The `loop` form is now a named let.
  - Every corpus case also emits with `:source-frames? true` without refusal (60362 B).
  - A mutation test (`null?`→`pair?` in pnil, plus a broken `eqv?`) produced 10 failures, so the check can detect errors.
- **`scan/emission-check.bl`**: `SCAN_EMISSION_PASS 10`.

## Emission size and time (real compiler closure, read-only artifact)

From `size.bl`, over 1353 definitions, all of which emit with both the old and the new emitter:

- **Total size**: 3,559,492 B before, 3,589,153 B after (+0.8%). The cost of an inlined truthiness test is mostly offset by boolean-BIF tests that no longer need a wrapper, and by loops.
- **The compiler's ANF has no multi-clause functions and no guards.** All 4184 `fn` take the simple distinct-variable path. The only clause chains are 16 `case` and 17 `try`. So there is no "large multi-clause reader function" to inspect. The definitions with clause chains, before → after:

  | Definition | Before | After |
  | --- | --- | --- |
  | `host.compiler-data/check_reader_data!` | 22102 | 20360 |
  | `assert_bootstrap_metadata_symbol_data!` | 20804 | 20382 |
  | `self_application_parts` | 13943 | 14278 |
  | `anf/validate-contextual-unit!` | 11351 | 10976 |
  | `native.scheme/emit-definition` | 8156 | 7980 |

- **Largest growth**: `anf/validate-node!` 51220 → 53297 (+4%, inlined `if` tests). There is no exponential growth: one thunk per clause, and only constant fallbacks are duplicated.
- **Emission time** on BEAM, whole closure, minimum of 3 alternating passes: old 3255 ms / new 3371 ms in one run, and 6339 / 6910 ms in a run while the machine was loaded. That is roughly +4–9%, from the loop analysis and fact bookkeeping that are now always on.
  - The first version used the per-loop fuel walk and was +17–40%. That is why the loop analysis is a single region walk with explicit traversal per op.

## Integration notes

- **Load position**: add `host/host-match.scm` to the host source list after `host-values.scm`. Putting it after `host-compiler.scm`, as the check does, works too.
  - It defines `bl-match-entry`, `bl-match-struct-fields`, `bl-match-struct-key`, `bl-match-vector-count`, `bl-match-vector-ref` and `bl-match-vector-items`.
  - It calls the V-owned `native-map-entry`, `native-missing`, `native-struct-fields`, `native-struct-module`, `native-vector-count` and `native-vector-ref` at call time. If V renames any of them, update this file.
  - `prepare-host.py`, `check-host.py` and `check-compiler.py` need the new entry.
- **Inlined representation checks**: the emitted code now contains the `bl-tag?` test (`(and (vector? s) (= (vector-length s) 2) (eq? (vector-ref s 0) 'tuple))`), tuple storage `(vector-ref s 1)` and the `bl-nil` / `#f` truthiness test. All three follow the fixed representation in CONTRACT.md.
- **Options**: `aot-scheme.bl` still passes `:specialize-v1?` / `:scan-v1?`, and the emitter now ignores them. Its `:emission-mode` refusal of specialize/scan together with source frames still exists. That is harmless, but someone needs to decide whether to delete it.
- **Merging with L**: my hunks in `emit` are the new `loop-plan` lines after the `multi-layout` line and the `:let`/`:if`/`:fn`/`:case`/`:recv` cases. L's cases are untouched.
- **Byte identity**: the emitted text changes for every definition that has an `if`, `case`, `try` or loop. It stays the same on BEAM and native, since both run this `scheme.bl`. The integration build must re-emit everything.

## Risks

- **Guard totality assumes the BIF leaves do not raise.** `total?` assumes that whatever the resolver returns for erlang type tests and equalities (`native-remote` leaves, the AOT primitive aliases, or K's templates) does not raise for any value. It also assumes comparison BIFs return `#t`/`#f`, which the plain `(if X …)` relies on. If K implements these BIFs, it must keep both properties.
- **Loops are lowered more widely.** With the fuel limit gone, safe loops whose bodies exceed 10000 nodes are now lowered too. Loop lowering is now on by default outside source frames. That is semantically checked, but it has not yet been through the main thread's full Source corpus.
- **Unchanged host gaps.** Thrown tuples/strings render their message differently, and `ExInfo :data` differs from BEAM. Both are host differences that were there before this work and are outside control. They were excluded from the corpus (the old emitter shows the same difference).
