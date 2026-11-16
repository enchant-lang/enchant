# Workstream K: native kernel results

Files: `src/native/intrinsics.bl` (the interface), `host/host-kernel.scm` (new; load it after
`host-compiler.scm`), and `speed/kernel/` (the checks).

## Coverage

These targets account for 90.6 % of the remote calls in one warm read, compile and emit pass
(`evidence/warm-core-counts`). That is 203 312 of 224 447 calls: templates cover 157 296 and
overrides cover 46 016.

### `remote-template`: 47 BIF keys

Each template answers inline only where the fixed native representation decides the leaf's
answer. In every other case it calls the **registered leaf procedure itself**. `host-kernel.scm`
captures that procedure once at load (`kernel-leaf-…`). The result is identical to the leaf by
construction, including errors.

| BIFs | Inline fast path, else the leaf |
| --- | --- |
| `is_list` `is_tuple` `is_float` `is_integer` `is_boolean` `is_function/1` | pure tests (`null?`/`pair?`, a 2-slot tagged vector, `exact-integer?`, `boolean?`, `procedure?`). These never call the leaf. |
| `is_atom` `is_map` `is_binary` `is_bitstring` | symbols use the colon test, and nil/booleans answer #t. Map/vec/set tags answer directly, and other vectors go to the leaf. A non-vector cannot be an opaque struct (see the guard below). |
| `==` `/=` `=:=` `=/=` | for fixnums, symbols, scalar strings, `()`, nil and booleans, the answer is decided by identity or content. A symbol against nil or a boolean, a pair against a pair, and anything else go to the leaf. |
| `<` `>` `=<` `>=` `+` `-` `*` | both operands fixnum: `fx<` etc. and `+ - *` |
| `hd` `tl` `not` | `pair?` → `car`/`cdr`; `boolean?` → `not` |
| `element` `tuple_size` `tuple_to_list` `setelement` `make_tuple` `list_to_tuple` `length` | a tuple with a fixnum index in range, a fixnum count ≥ 0, or a proper list |
| `lists/append/2` | `(null? a)` → `b` |
| `function_exported/3` `is_function/2` `apply/3` `integer_to_binary/1` `iolist_to_binary/1` `map_get` `map_size` `is_map_key` `lists/reverse/1` `maps/{get/2,get/3,is_key,put,find,size}` | a direct call to the captured leaf, which skips the string-keyed lookup |

The guard-position BIFs (`is_*`, the equality BIFs, `<` `>` `=<` `>=`) never raise and return
exactly `#t`/`#f`. The check verifies this over the whole corpus, which matters for workstream C's
plain `if`.

### `kernel-override`: 34 `rt` definitions

All of these are fixed-arity definitions. Each override is a procedure:

```
(bl-register-callable! (case-lambda ((p…) fast-or-original) (argv (apply ORIGINAL argv))) n)
```

| Mode | Definitions | Behaviour |
| --- | --- | --- |
| partial | `kind-kind`, `k-compare`/`compare`, `k-eqv`/`eqv`, `call-not-`/`not_`, `struct-of?`, `reduce-reduced?`, `k-first`/`first`, `k-rest`/`rest`, `k-empty?`/`empty?`, `k-cons`/`cons`, `hash-hash-key`/`hash_key`, `to-str` | The `kernel-rt-…` fast path returns `kernel-miss` unless the answer is proven; on a miss, `original` is called unchanged. The wrapper calls `(h-tick)` only on a fast answer, so a delegated call ticks exactly as before. |
| total | `call-identical?`/`identical?` (the `=:=` template helper), `empty-list?` (`null?`), `raw-cons` (`cons`), `seq-one`/`reduce-one` (`list`), `seq-two`/`reduce-two`, `tuple2`, `tuple3` | Always answers; one tick. |
| gate | `source-callable!`, `source-invocation!`, `source-invocation1!`, `source-invocation2!` | Ticks first, as the body does, because it reads registry state. Answers `f` when no `Elixir.BeamLisp.Env` gate is exported (always the case today, since those keys are in `native-excluded-host-leaves`). Otherwise it delegates, and that path ticks twice. |

Fast paths take only fixnums and bignums, `bl-nil`, booleans, plain keywords, scalar strings,
pairs and `()`, plain tuples, plain maps (no `:__struct__` key), and the 'vec, 'set and 'float tags.
Everything else delegates: `{:meta …}` wrappers and other reserved tuple tags (except where the
body answers by kind alone), struct maps (except modules in rt's literal table, for `kind-kind`
only), lazy sequences, records, sorted collections, decimals, int×float pairs, floats that do not
compare strictly, UTF16 fragments and keywords, the symbols `:nil`, `:true` and `:false`, refs and
procedures.

### Guard installed by `host-kernel.scm`

`native-register-struct!` is re-bound so that it refuses anything that is not a vector of length
greater than 2. Today only `native-ref-new` registers opaque structs, and those are length-7
vectors. The guard enforces the assumption behind `is_map`/`kind` instead of trusting it.

## Differential checks

```
research/native-seed/run run research/native-seed/speed/kernel/oracle.bl -- research/native-seed/speed/kernel/out   # BEAM, ~16 s
python3 research/native-seed/speed/kernel/check.py                                                                  # gsi, ~11 s
```

`oracle.bl` evaluates every covered BIF and rt function on BEAM over a 61-value corpus. The corpus
has nil, booleans, keywords (`:meta`, `:symbol`, `:__struct__`, module atoms, `:"$blfn"`), small,
negative and big ints, floats (including ±0.0), decimals, strings (including é and 😀), empty,
proper and improper lists, tuples of sizes 0 to 3, meta/symbol/blfn tuples, maps (keyword, int and
string keys, and a 20-key AVL map), a struct, a Reduced, vectors and sets. Binary operations run
over 46×46 pairs. Values are encoded with `native.scheme/literal`, plus explicit improper lists and
structs.

`check.py` loads the host sources, `host-kernel.scm`, the generated templates and overrides, and
`kernel-check.scm`. Each override uses a stub `original` that records delegation.

Result: **KERNEL_CHECK_PASS, 0 failures.**

| Check | Count |
| --- | --- |
| BEAM rows | 78 588 |
| template = registered leaf (value or identical raise) | 54 196 / 54 196 |
| template = BEAM | 53 918 |
| guard-position BIF results that are booleans | 17 538 |
| override fast answer = BEAM | 18 188 |
| override delegated | 6 154 |
| fast path raised | 0 |
| native-only exotic inputs: delegated | 3 829 |
| native-only exotic inputs: decided, checked against hand derivations from rt.bl | 708 |
| constructors checked natively | 1 780 |
| gates delegated once Env gates are exposed | 4 / 4 |
| wrong-arity calls delegated | 34 / 34 |
| tick accounting (fast, miss, total, gate) | 4 / 4 |
| opaque-struct guard | 1 / 1 |

Two mutations were each caught by the check: swapping the atom order in `k-compare`, and making
`is_atom` true for strings.

Mismatches that already exist between the registered leaves and BEAM are counted, not failed. In
these rows template and leaf agree:
- 200 rows of term order (`<` `>` `=<` `>=`): maps, structs and improper lists order differently.
- 68 rows of raw `+`/`-`/`*`: they accept decimals, and `-0.0*2` gives `0.0`.
- 4 rows where `=:=` treats -0.0 and 0.0 as equal; this also shows up as 4 `call-identical?` rows.
- 6 rows where `iolist_to_binary` accepts a bare integer.
- 46 rows skipped where `make_tuple(2^70, _)` would make the leaf diverge.

These belong to workstream V.

A note on the harness: interpreted gsi 4.9.5 segfaults inside its GC after about 50 000 calls in
one process. I reproduced this with a leaf-only harness and no kernel code loaded. `check.py`
therefore runs the rows in slices of 15 000, one process per slice. Separately, an interpreted
`case-lambda` with an `()` clause is broken ("Unbound variable #:g0"), so there are no zero-arity
overrides.

## Exclusions

- Multi-arity `$blfn` definitions are not overridden: `k-nth`/`nth` (1 177 calls each) and `coll-get`.
- Zero-arity `empty-list` and `k-empty-list` are not overridden (the gsi `case-lambda` issue above).
- `erlang/error|exit|throw` get no template, because host-source-frames re-binds those leaves.
- `apply/2` (source-frames path), `map-join`, `str_v`, `step`, `compat-reduced?` and the `core` namespace are not covered.

## Integration notes

- Load order: `host-values` → `host-leaves` → `host-lazy` → `host-extra` → `host-compiler` →
  **`host-kernel.scm`** → compiled definitions. Every leaf it captures must already be registered;
  `kernel-leaf` raises at load if one is missing. Add the file to `prepare-host.py`,
  `check-host.py` and `check-compiler.py`.
- Templates: L binds operands `a0 a1 …` and splices `((remote-template node) ["a0" …])`. The
  result refers only to `kernel-…` globals and standard Gambit procedures.
- Overrides: `(kernel-override "rt" name original)` returns nil for anything not in the table.
  `original` is referenced by global name at call time, so its define may come before or after
  the override.
- Helpers for checks: `native.intrinsics/template-keys` and `override-names`.

## Risks

- A facade override (`first`, `eqv`, `compare` and the like) answers fast without going through
  `k-first` and friends. If something re-defines `rt/k-*` at runtime, the facade's fast paths would
  not follow it.
- Captured leaves freeze the leaf registry for the covered keys at kernel load. Later rebinds of
  those keys, through `native-rebind-transport-leaf!` or Source, would not be seen. Today only
  error, exit and throw are rebound, and they are not captured.
- Fast-path ticks are fewer than the original's nested ticks. This changes yield points only, not
  values.
- The checks ran interpreted on gsi only. Compiled behaviour, linked emission and the speed effect
  remain for the main thread to verify.
