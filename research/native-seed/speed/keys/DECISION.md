# Q3: collection keys use value equality

Decision by Othman (2026-11-17): `(get {1 :x} 1.0)` is `:x`. He delegated the
details. This file records them. Later work keeps them unless Othman reopens Q3.

## The law

> Two keys `k1` and `k2` are the **same key** of a map, a set, a sorted
> collection, `frequencies`, `group-by` or `distinct` exactly when
> `(= k1 k2)` is true.

There are two recorded exceptions:

1. **NaN.** `=` is not reflexive on NaN, and a key relation has to be (see
   below).
2. **A list and a vector with equal elements are different keys.** `=` says
   `(= [1 2] '(1 2))`, but `(get {[1 2] :x} '(1 2))` is nil, as it was before
   this change. Making them one key would mean storing one sequential kind for
   both, so `keys` would hand back a vector where the program stored a list.
   Compiler and macro code reads list keys back as forms, so that is the larger
   surprise. Within one kind the law holds fully: `(get {'(1 2M) :l} '(1.0 2))`
   is `:l`.

Every operation that takes a key follows the law:
`get`, `assoc`, `dissoc`, `contains?`, `find`, `conj` into a map or set, `disj`,
calling a map or set as a function, set and map literals, `set`, `hash-map`,
`into`, `zipmap`, `merge`, `select-keys`, `frequencies`, `group-by`, `distinct`,
and the transient forms of these operations.

## The mechanism: one canonical representative per equality class

Each key is replaced by a **canonical representative** of its `=` class before
the store sees it. The BEAM map, `MapSet` or native tree then compares the
canonical terms exactly. This is the cheapest choice:

* An equal pair becomes the same term, so the native hash (`phash2`, the
  `MapSet` and map hashing) and the native ordered tree (`bl-key-compare`)
  stay as they are. Equal keys hash equal because they are the same term.
* The value layout does not change (D1). A map is still a BEAM map, a set is
  still a `MapSet`, and a native map is still the sorted tree.
* The common keys pay nothing extra. Integers, keywords and strings are already
  canonical, and canonicalisation tests their type before anything else.

We rejected two alternatives:

* **Storing the first-written key, as Python does.** Every lookup would need
  the stored key, so each map entry would carry it next to the value. That is
  a layout change (D1), and Erlang interop reads maps directly.
* **Probing alternatives on a miss** (try `1`, then `1.0`). This fails for
  decimals, which have infinitely many scales, and for composite keys.

### Canonical numbers

| Value class | Canonical representative | Examples |
| --- | --- | --- |
| Integral value (int, float or decimal) | the **integer** | `1.0 → 1`, `-0.0 → 0`, `0.0 → 0`, `1.00M → 1`, `1E+2M → 100`, `1.0e300 → 10…0` (exact) |
| Non-integral value that a binary64 float represents exactly | the **float** | `1.5M → 1.5`, `0.50M → 0.5`, `1.5 → 1.5` |
| Any other non-integral decimal | the decimal **with trailing zeros removed** | `0.10M → 0.1M`, `0.1M → 0.1M` (and not the float `0.1`, which is a different number) |
| Non-integral float | itself | `0.1 → 0.1` |
| NaN (only once E8 admits non-finite floats) | one canonical NaN | — |
| `+inf`, `-inf` (only once E8 admits them) | themselves | — |

Floats keep the most common non-integer form: a float key such as `0.25` is
never rewritten. A decimal takes the float form only when its value is exactly
that float, because the class has to have one representative.

### Composite keys

`=` walks into collections, so `[1]`, `[1.0]` and `(list 1M)` are equal and must
be one key. Canonicalisation walks the same shapes that metadata stripping
already walked, plus tuples, records and large (trie) vectors:

* vectors, lists, raw tuples, sets and plain maps (both keys and values)
* records: their field values; the `__struct__` tag and field names stay as
  they are
* metadata is removed everywhere, as before

When nothing inside a value needs to change, the same term is returned and
nothing is allocated. Sorted collections used as keys are already canonical,
because every sorted entry point canonicalises its keys.

### What you get back

* `(keys m)`, `(seq m)`, `(first m)`, `(find m k)` and set members return the
  **canonical** key, never the spelling the caller wrote:
  `(keys {1.0 :x})` is `(1)`, `(find {1 :x} 1.0)` is `[1 :x]`,
  `(get #{1} 1.0)` and `(#{1} 1.0)` are `1`, `(first #{1.50M})` is `1.5`.
* `assoc` replaces the value of an equal key, and the stored key stays
  canonical: `(assoc {1 :a} 1.0 :b)` is `{1 :b}`, and so is
  `{1 :a 1.0 :b}`, the later entry winning.
* Values are never canonicalised: `(get {:a 1.0} :a)` is still the float `1.0`.

## Specific answers

| Question | Answer |
| --- | --- |
| Integral floats | `1.0` and `1` are the same key. The stored key is `1`. |
| Decimal keys | Any scale of a decimal is the same key as the equal int or float. `1.50M`, `1.5M` and `1.5` are the same key, stored as `1.5`. `0.1M` and `0.1` are different keys, because `(= 0.1M 0.1)` is false. |
| `-0.0`, `0.0`, `0` | One key, stored as `0`. They are already equal under `=` (`(= 0.0 -0.0)` is true). |
| NaN | Neither target can build a NaN today. BEAM floats are finite, and native `bl-float` refuses non-finite values. When E8 admits them, **every NaN is one key, equal to itself as a key**, even though `(= ##NaN ##NaN)` is false. This is JavaScript's SameValueZero rule, and the reasons for it are listed under NaN below. This wave adds no NaN clause on either target, because none can be reached. E8 must add two things: a canonicaliser clause that maps every NaN to one NaN term, and a fixed NaN position in the native tree order. `bl-key-compare` currently compares a NaN as 0 against every float. |
| `(keys m)` for a key written as `1.0` | `(1)`. |
| Set membership | Members are canonical, so `(count #{1 1.0})` is 1, `(contains? #{1} 1.0)` is true and `(= #{1} #{1.0})` is true. |
| Sorted collections | The tree order is `compare`, and `compare` is 0 exactly when `=` holds, so sorted lookups already used value equality for int and float. The stored key is now canonical too, and decimal keys now land among the numbers: `(get (sorted-map 1.5M :x) 1.50M)` is `:x`. `(keys (sorted-map 1.0 :x))` is `(1)`. |
| Hash consistency | `(hash-key a)` and `(hash-key b)` are the identical term when `(= a b)`, so every hash of them (`phash2`, map and set hashing) is equal. `semantic-hash` already hashed the exact rational value and is unchanged. Native: equal keys become the identical canonical term, so `bl-key-compare` returns 0. |
| Raw BEAM maps built outside the BL key paths | Maps built by Elixir or Erlang interop, `maps:from_list` or a quoted literal map can hold raw keys such as `2.0`. `get`, `contains?`, `find` and `dissoc` try the canonical key first, then the exact raw term, so an exact-term lookup still finds the entry. A key that is only `=`-equal to a raw key (`(get raw-map-with-2.0 2)`) misses. Only maps built by BL get the full law. |

### NaN

* A key relation has to be reflexive. Otherwise
  `(get (assoc m ##NaN 1) ##NaN)` would be nil, and repeated
  `(assoc m ##NaN …)` would add a new entry every time.
* `distinct` and `frequencies` over data containing NaN then terminate with
  sensible counts.
* It is the cheapest rule: one canonical NaN term.

Under SameValueZero, `-0.0`, `0.0` and `0` are still one key, as `=` requires.

## Cost on the common case (guards, not timings)

A guard is one BEAM type or term test executed in the key path. "Before" is the
code at `073fe16e8`.

| Path | int key | keyword key | string key | float key | decimal key |
| --- | --- | --- | --- | --- | --- |
| `hash-key` (used by literal maps, `assoc`, `conj`, sets, `distinct`, transients) | 1 (was 3) | 2 (was 3) | 3 (was 3) | 4 tests, then `trunc` and one compare | struct dispatch, then the decimal reduction |
| `get` / `contains?` / `find` on a map | `hash-key` + 1 `=:=` (raw-key fallback test) | same | same | same; on a dirty key, one extra lookup | same |
| `dissoc` on a map | `hash-key` + 1 `=:=` | same | same | one extra `maps:remove` when dirty | same |
| sorted collection operations | + `hash-key` (1–3 guards) | | | | |
| native `bl-get` / `bl-assoc` / `has?` / `remove` | +1 (`fixnum?`) | +1 (`symbol?`) | +1 (`string?`) | `bl-tag?`, `integer?` | struct-module check, then the decimal reduction |

Net change for the common keys on BEAM:

* `assoc`: int −2, keyword −1, string 0 guards.
* `get`: int −1, keyword 0, string +1 guards.

Natively, every map entry point pays exactly one extra type test for a fixnum,
keyword or string key. Composite keys pay one walk to prove they are already
canonical, which is the walk metadata stripping already did for dense vectors,
lists, sets and maps. It now also covers tuples, records and large vectors.

## Counterexamples that expose a wrong implementation

Each line is true under this decision. `test/bl/value_keys_test.bl` asserts
them on BEAM, and `research/native-seed/speed/keys/native-keys-check.scm` asserts
the native ones.

```clojure
(get {1 :x} 1.0)                      ;=> :x
(get {1.0 :x} 1)                      ;=> :x
(get {0 :z} -0.0)                     ;=> :z
(get {1.5 :h} 1.50M)                  ;=> :h
(get {0.1 :f} 0.1M)                   ;=> nil   ; 0.1 is not one tenth
(get {0.1M :d} 0.10M)                 ;=> :d
(count {1 :a 1.0 :b})                 ;=> 1
(get {1 :a 1.0 :b} 1)                 ;=> :b
(keys {1.0 :x})                       ;=> (1)
(keys {-0.0 :x})                      ;=> (0)
(keys {1.50M :x})                     ;=> (1.5)
(keys {0.10M :x})                     ;=> (0.1M)
(find {1 :x} 1.0)                     ;=> [1 :x]
(contains? {1 :x} 1.0)                ;=> true
(dissoc {1 :x} 1.0)                   ;=> {}
(assoc {1 :a} 1.0 :b)                 ;=> {1 :b}
(count #{1 1.0 1M 1.00M})             ;=> 1
(contains? #{2} 2.0)                  ;=> true
(#{1} 1.0)                            ;=> 1
(disj #{1} 1.0)                       ;=> #{}
(= #{1} #{1.0})                       ;=> true
(count (set [0 0.0 -0.0]))            ;=> 1
(get {[1 2] :v} [1.0 2.0])            ;=> :v
(get {{:a 1} :m} {:a 1.0})            ;=> :m
(get {#{1} :s} #{1.0})                ;=> :s
(frequencies [1 1.0 1M])              ;=> {1 3}
(get {'(1 2M) :l} '(1.0 2))           ;=> :l
(get {[1 2] :x} '(1 2))               ;=> nil   ; recorded exception 2
(group-by identity [1 1.0])           ;=> {1 [1 1.0]}  ; values keep their spelling
(distinct [1 1.0 2])                  ;=> (1 2)
(get (sorted-map 1.5M :x) 1.50M)      ;=> :x
(keys (sorted-map 1.0 :x))            ;=> (1)
(float? (get {:a 1.0} :a))            ;=> true  ; values are untouched
(= (hash-key 1.0) (hash-key 1))       ;=> true and identical terms
```

Three of these expose the usual wrong implementations:

* `(get {0.1 :f} 0.1M)` must be nil. An implementation that compares a decimal
  with a float through its printed shortest form gets it wrong.
* `(keys {0.10M :x})` must be `(0.1M)`. An implementation that turns every
  decimal into a float gets `0.1`, a different number.
* `(get {[1 2] :v} [1.0 2.0])` must be `:v`. An implementation that
  canonicalises only top-level keys misses it.

## Out of scope (recorded so nobody reopens it by accident)

* `identical?` and raw Erlang term equality are unchanged:
  `(identical? 1 1.0)` is false.
* `case` already tests its constants with `=`, so `(case 1.0 1 :int :float)`
  is `:int`. That was true before this change and is unchanged. Destructuring
  and Erlang-level pattern matching stay exact-term.
* Datom indexes have their own semantic keys (`datom.index/value-key`) and
  formats. Nothing changes there.
* `formal.identity` and the data graph keep exact kinds and float bits, which
  is evidence identity, not language equality. A data graph that holds the
  distinct keys `1` and `1.0` now refuses to materialise as a BL map, as its
  decoder already does when a runtime collapses them
  (`test/bl/formal/data_graph_test.bl`).
* Map iteration order stays unspecified (Q1).
