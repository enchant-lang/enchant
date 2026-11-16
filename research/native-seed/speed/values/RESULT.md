# Workstream V: value fast paths (result)

Branch `native-speed-values`. Representation unchanged. The work touches only
procedure bodies in `host/host-values.scm`, `host/host-lazy.scm` and two
helper bodies in `host/host-leaves.scm` (`native-erlang-equal?` and the
`native-term-compare` `set!`). No `native-add-leaf!` form and no registry form
(`native-global-registry`, `native-register!`) was edited.

## Changes and why each is exact

| Procedure | Change | Why the result is identical |
| --- | --- | --- |
| `native-keyword?`, `native-atom-name`, `native-compare-string` | The final layered definitions now sit at their first definition. The later `set!` overrides and the `native-scalar-keyword?`, `native-scalar-atom-name` and `native-scalar-string-compare` aliases are deleted. | Same final semantics: a colon symbol or a `utf16-keyword` wrapper; the memoized atom name; UTF16 string order. |
| `native-colon-symbol?` (new) | Tests the first char of `symbol->string` without allocating. | In Gambit 4.9.5, `symbol->string` returns the interned name itself (checked: `(eq? (symbol->string s) (symbol->string s))` gives `#t`). The string is only read, never mutated. |
| `native-scalar-string-compare-from` (new, replaces `native-scalar-string-compare`) | Same UTF16-order loop with start offsets, using fx ops. | Keyword names are compared inside their symbol strings starting at index 1. That is the same string the former `substring` built. |
| `native-key-rank` | One type dispatch (symbol, vector tag `case`, pair, null, string, boolean, exact integer) instead of up to 10 sequential tag tests. | Same 11 classes and numbering. The Scheme types are disjoint, and `bl-nil` is a 1-slot vector. |
| `bl-key-compare` | `eq?`, then same-kind fast paths: colon-symbol/colon-symbol, string/string, fixnum/fixnum, pair/pair, pair/`()`, `()`/pair. Everything else goes to `native-key-compare-ranked` (the former rank body). | Each fast path returns what the ranked path returns for that pair. Rank 2 now uses `native-compare-atoms`, which compares nil/true/false spellings and symbol names in place. Atoms involving a `utf16-keyword` keep the former `native-compare-string` over `native-atom-name`. |
| `bl-key-equal?` | `eq?` shortcut. | `(bl-key-compare a a)` is 0. |
| `native-small-map-search` | The `eq?` pre-scan is skipped for string keys. For scalar keys (rank 0/1/2/7/9) the ordered phase is a binary search. Composite and opaque keys keep the left-to-right scan. | Entries are strictly sorted by a total order, so bisection finds the same first row that is not below the key. Comparing a scalar key against any entry never calls `native-opaque-id`, so it has no side effects. Comparing a composite or opaque key may lazily assign opaque ids, so it keeps the exact former comparison sequence. |
| `native-small-map-assoc`, `native-small-map-remove` | `subvector` / `subvector-move!` instead of per-slot Scheme fill loops. Replacing an existing key copies the rows and sets one value slot, without re-sorting. | The rows, the original stored key object and the exact-size vector are the same. Storage is checked to be `equal?` against the former code. |
| `bl-get` | `#!optional` default plus an ignored `#!rest`, so a defaulted lookup no longer allocates a rest list. Body inlined. | Same results. Extra arguments are still ignored. |
| `native-map-ref` (new) | Value-only lookup: the value or a caller-supplied missing marker. Used by `bl-match` map patterns and by map equality, instead of the `native-map-entry` cons. | Same search. |
| `native-map-keys`, `native-tree-keys`, `native-map-every?` (new) | Iterate keys / (key, value) in storage order without building entry tuples. | Same order as `native-map-pairs`. |
| `native-map-pairs`, `native-tree-pairs` | `(vector 'tuple (vector k v))` instead of `(bl-tuple (list k v))`. | Same structure. |
| `native-set-items`, `h-map-keys` | Use `native-map-keys`. | Same key objects in the same order. |
| `native-struct-module` | Constant interned keys (`__struct__`, Vector, Set). Skips the opaque-struct weak-table lookup for non-vectors while no non-vector has been registered. | `bl-key` of a constant name always returns the same interned symbol. `native-register-struct!` sets `native-opaque-nonvector-structs?` the first time it sees a non-vector, and from then on the table is consulted as before. Today only 7-slot reference vectors are registered. |
| `native-decimal?`, `native-number?` | Constant Decimal key. The disjunction is reordered by type (fixnum first). | The predicates are pure, so the disjunction is the same. |
| `bl-equal?` | Fast paths: distinct fixnums give `#f`, scalar strings use `string=?`, and a symbol or boolean on either side gives `#f`. The last two apply only while the non-vector flag is clear. The remainder (`native-equal-general?`) is the former body, with maps through `native-map-every?` + `native-map-ref` and tuples through a vector-index loop. | A symbol or boolean is not a number, string or collection, so only identity equals it. The tuple loop compares the common prefix element by element and then the sizes, exactly as the former list walk did (element comparisons may assign opaque ids). |
| `bl-vec` | A proper list builds the final trie directly: capacity is the least power of two ≥ n, absent slots are `#f`, and meta is nil. The empty vector keeps its 4-slot storage. Improper input keeps the former incremental loop and its primitive error. | Storage is `equal?` to the former output for n = 0..140, checked by the fixture. |
| `bl-items` | One right-to-left trie walk for vectors instead of a bounds-checked root-to-leaf descent per index. | Same list. |
| `bl-nth` | A tuple with an in-range fixnum index goes straight to `vector-ref`; everything else uses the former body. | Same validity condition. |
| `bl-match` (`map`/`struct` patterns) | `native-map-ref` instead of `native-map-entry`. | Same value. |
| `native-lazy?`, `native-cursor?`, `native-delay?` (host-lazy) | Constant module keys. | Same interned symbols. |
| `native-erlang-equal?` (host-leaves) | Tuple vector loop over the common prefix and then sizes; map loop through `native-map-every?` / `native-map-ref`. | Same comparison order. |
| `native-term-compare` (host-leaves `set!` body) | Two scalar strings are compared in place by codepoint (`native-codepoint-string-compare`, defined in host-values). | A Gambit scalar string cannot hold a lone surrogate (`integer->char #xD800` raises), so its `h-str-codepoints` list is exactly its characters. Fragment wrappers keep the unit-list path. |

## Checks

```
python3 research/native-seed/check-host.py --out /tmp/wsV-host --evidence /tmp/wsV-host/host.json
```
All 11 runs PASS. Counts: `native value/control checks: 27`, lazy memo passed,
extra passed, `NATIVE_LISTS_SPLIT_ABI_PASS 24`, `symbol-name 15`,
`raw-map-get 19`, `NATIVE_HOST_ARRAY_TUPLE_ABI_PASS 13`,
`NATIVE_RUNTIME_ID_ABI_PASS 7`, `NATIVE_OPTIONAL_INPUT_DEADLINE_ABI_PASS 18`,
`compiler-cache 96`, `global-cache 48`, source-frames passed, and POSIX worker
passed. (`--out` avoids rewriting `evidence/host.json`.)

Differential fixture
[`values-diff-check.scm`](values-diff-check.scm). Its first part is every
pre-change host form of the changed procedures (from `ff1aae6bf`), renamed to
`old-*`. Its second part runs the comparisons:

```
cd research/native-seed
cat host.scm host/host-values.scm host/host-leaves.scm host/host-lazy.scm host/host-extra.scm \
    speed/values/values-diff-check.scm > /tmp/values-diff.scm
timeout 120 $(jq -r .gambit toolchain-pin.json)/bin/gsi /tmp/values-diff.scm
# native value differential checks: 145790 failures: 0
# NATIVE_VALUE_DIFFERENTIAL_PASS
```

The corpus covers nil, `#t`, `#f`, `()`, and keywords: ASCII, empty, non-BMP,
`\xFFFF`, `é`, raw `:nil`/`:true`/`:false` symbols and UTF16-fragment
keywords. It also has non-colon symbols, fixnum extremes, bignums, rationals,
boxed and raw floats including -0.0, decimals, and strings (empty, prefixes,
BMP/non-BMP mixes, fragments). The rest are proper and improper lists, tuples,
vectors (including tries larger than 32), small and AVL maps, sets, and
opaque values: procedures, references, a registered ref struct, foreign
vectors and a char.

The fixture asserts the same outcome, or both raising, for:
- every corpus pair under `bl-key-compare`, `bl-key-equal?`, `bl-equal?`,
  `native-erlang-equal?` and `native-term-compare`;
- per value: keyword?, rank, atom-name, number?, struct-module, `bl-items`,
  `h-map-keys`, set items, map pairs (by identity), and `bl-nth` with and
  without a default at 10 indices;
- `bl-vec` storage, items and `conj` for n = 0..140, plus improper input;
- 60 random assoc/remove/re-put sequences and 60 random literal `bl-map`s
  (duplicates, more than 16 pairs). After each, storage is `equal?`, and
  pairs order, count, get, get with default, has?, entry and ref agree for
  every corpus key;
- small-map search positions, and flat `bl-match` map patterns.

Mutation sanity: breaking `native-colon-symbol?`, a float `bl-equal?` case or
`fxmin` makes the fixture fail (634, 11 and 40 failures). Forcing bisection
for composite keys is not detected, because the corpus pre-assigns every
opaque id. The scan is kept for those keys by argument, not by a test.

## Standard-bindings audit

Every top-level `define`/`set!` name in `host.scm` and `host/*.scm` was checked
against a vanilla `gsi` global environment (`##global-var-ref` not unbound).
All 671 names were checked, and none redefines a Gambit standard, extended or
`##` binding. Local `let` names that shadow standard procedures (`map` in
`h-table-insert`, `length`/`exp`/`first`/`last` in `native-js-float-text`,
`list?` in `native-render`) are lexical, so `(declare (standard-bindings)
(extended-bindings))` does not affect them. Fixtures do `set!` host globals
(`native-atom-name`, `native-keyword?` in `host-compiler-cache-check.scm`),
but no Scheme primitives. The new code uses extended bindings (`fixnum?`,
`fx+`/`fx<`/`fxquotient`/`fxmin`, `subvector`, `subvector-move!`), which
gsc can inline under that declaration.

## Integration notes and risks

- The emitted Scheme text is unaffected: no emitter file was touched, and
  every ordering primitive is differentially identical.
- `bl-key-compare` no longer looks up `native-keyword?`/`native-atom-name`
  through their mutable globals on its fast paths. Production never rebinds
  them, and the hooks in the compiler-cache fixture still pass (96/96).
- Deleted helper names: `native-scalar-string-compare` (now `-from` with
  offsets), `native-scalar-keyword?` and `native-scalar-atom-name`. None is
  referenced by compiled chunks in `out/compiler-native-owner` (only host
  copies mention them).
- `host-leaves.scm` hunks are inside `native-erlang-equal?` and the
  `native-term-compare` `set!`, not on any `native-add-leaf!` line, so they
  should merge cleanly with L. `native-codepoint-string-compare` lives in
  host-values.
- Not changed: `bl-guard` (one `with-exception-catcher` per guard is left to
  workstream K's compiled guards), `bl-make-tuple`/`bl-map` rest lists
  (inherent to variadic procedures), `native-tree-*` (they benefit through
  `bl-key-compare`), and map/vec/set ordering (`native-compare-lists` over
  pairs).
- Timings were not measured beyond interpreter micro-checks used to choose
  implementations.
