# KEYS (Q3) result

The decision is recorded in [`DECISION.md`](DECISION.md). In short: two keys
are the same key iff `(= k1 k2)`. Each key is replaced by one canonical
representative of its `=` class:

* an integral number becomes the integer;
* a decimal whose value is exactly a float becomes that float;
* any other decimal loses its trailing zeros;
* a composite is rebuilt only when something inside it changes.

`keys`, `find` and set members return the canonical key. There are two recorded
exceptions: NaN, which no target can build today, and list against vector,
which stay distinct keys.

## Changed functions

**BEAM, `priv/boot/rt.bl`**

* The `rt.hash` section is rewritten:
  * new: `meta-wrapper?`, `float-canon`, `decimal-float`, `decimal-fraction`,
    `decimal-canon`, `key-dirty?`, `key-dirty-list?`, `key-dirty-tuple?`,
    `key-dirty-map?`, `vector-dirty?`, `canon-list`, `canon-vector`;
  * rewritten: `normalize-map`, `hash-hash-key`;
  * deleted (hard cutover): `carries-meta?`, `any-meta-in-list?`,
    `needs-normalizing?`, `any-meta-in-map?`, `normalize-set`.
* `coll-get`: map lookups fall back to the raw term; sets and sorted sets return
  the stored member; sorted keys are canonicalised.
* `coll-contains?`, `coll-find` (returns the stored key), `coll-assoc`,
  `coll-conj` and `coll-disj` handle sorted keys.
* `invoke`: a set or sorted set called as a function goes through `coll-get`.
* `sorted-sorted-set`, `sorted-sorted-set-of`, `sorted-sorted-map`,
  `sorted-sorted-map-of` and `sorted-sorted-dissoc` canonicalise their keys.
* `coll-hash-key` has a new docstring, and the `rt.key` comment is updated.

**BEAM, outside `rt.bl`.** These are the named key operations, and no other
workstream owns these files:

* `priv/boot/core.bl` `dissoc`: removes the canonical key, then the raw term.
* `priv/host/set.bl` `new/1`: members are keyed by `Rt.hash_key`. Before this,
  set literals, `(set coll)` and quoted sets were not canonicalised at all, not
  even for metadata.
* `priv/host/transient.bl` `conj!`, `assoc!`, `dissoc!`, `get` and `hash_map`:
  keys go through `Rt.hash_key`. Before this, `into` above 8192 elements and
  `hash-map` skipped key normalisation entirely.

**Native, `research/native-seed/host/host-values.scm`.** Behaviour only; the
layout is unchanged.

* New: `native-key-canon`, `native-integral-float?`, `native-decimal-canon`,
  `native-key-dirty?`, `native-vector-any?`, `native-key-rebuild`.
* `bl-key-value`, which the `hash_key` leaf calls, is now `native-key-canon`.
* Every map entry point canonicalises its key: `native-map-entry`,
  `native-map-ref`, `bl-get`, `native-map-has?`, `bl-assoc`,
  `native-map-remove` and `native-small-map-build` (map literals).
* `h-table-insert` and `h-table-delete` canonicalise their key, so the
  key-order list agrees with the map.
* `bl-invoke` returns the stored set member.

**Tests**

* New: `test/bl/value_keys_test.bl`, `speed/keys/native-keys-check.scm` and
  the runner `speed/keys/check-native.sh`.
* Changed: `research/native-seed/fixtures/host-extra-check.scm` (see below).

## Checks

All runs went through `work run`. No timings were taken.

1. Focused BEAM batch, one cold VM:
   ```
   work run --memory 4G --timeout 5400 -- ./bin/bl --cold test test/bl/value_keys_test.bl \
     test/bl/numeric_equality_test.bl test/bl/host_set_test.bl test/bl/host_vector_test.bl \
     test/bl/host_sorted_test.bl test/bl/sorted_test.bl test/bl/host_transient_test.bl \
     test/bl/host_num_test.bl test/bl/host_decimal_test.bl test/bl/eval_closed_test.bl \
     test/bl/formal/data_graph_test.bl test/bl/wave18_rt_port_test.bl test/bl/wave27_into_port_test.bl \
     test/bl/reduce_kernel_cutover_test.bl test/bl/compiler_data_literal_test.bl \
     test/bl/core_additions_test.bl test/bl/datom/query_composite_join_test.bl \
     test/bl/decimal_codec_port_test.bl test/bl/system/footprint_forcing_test.bl \
     test/bl/anf_direct_emit_test.bl
   ```
   Result: **20 files passed, 0 failed, 8,847 assertions, "all green"**
   (value-keys 3,892, numeric-equality 2,479, data-graph 297,
   reduce-kernel 451, …). The log is `speed/keys/out/batch.log`, which is
   gitignored.

   An earlier run of `value_keys_test.bl` alone had 6 failures. Four were
   errors in the tests themselves (`keys` returns a seq, not a list) or wrong
   claims (`case` already tests with `=`), so the tests and DECISION were
   corrected. One was a real design point: a list key against a vector key.
   That is now recorded as exception 2.
2. Native host, gsi under a 120 s cap per fixture:
   `work run --memory-high 900M --memory 1G --timeout 5400 -- bash research/native-seed/speed/keys/check-native.sh`
   * `native keys checks: 2947` PASS
   * `native value/control checks: 27` PASS
   * `native memo checks: 27` PASS
   * extra/raw-leaf fixtures PASS: `native extra checks passed`,
     `NATIVE_LISTS_SPLIT_ABI_PASS 24`, `native symbol-name checks: 15`,
     `native raw-map-get checks: 19`, `NATIVE_HOST_ARRAY_TUPLE_ABI_PASS 13`,
     `NATIVE_RUNTIME_ID_ABI_PASS 7` and `NATIVE_OPTIONAL_INPUT_DEADLINE_ABI_PASS 18`.
     These are the counts `check-host.py` asserts.

   The first extra run failed at "hybrid raw key count", which is the changed
   expectation below. It passed after the fixture change.
3. `./bin/bl realm stop`: no realm was running.

### Existing expectations that changed

* `fixtures/host-extra-check.scm`, "Hybrid maps must preserve the OLD raw key
  relation". It stored both `1` and `1.0`, and `10.0M` beside them, as distinct
  keys, and asserted a count of 13. Under Q3 those keys merge, by design. The
  fixture's purpose is mixed-kind storage order, so it now uses `1.5` and
  `0.1M`, which are canonical non-integers. The merging is asserted in
  `native-keys-check.scm`.
* No BEAM test expectation changed. `formal/data_graph_test.bl`
  `materialization-preserves-exact-keys-or-refuses-runtime-collapse` already
  adapts to a runtime that collapses `1`/`1.0`: it now takes its "refuse" branch
  and passes. `datom/query_composite_join_test.bl` passes unchanged.

## Requests (outside KEYS ownership)

1. **Quoted map literals.** `compiler.bl` `datum` (the `:map` tag,
   `maps/from_list`) and `syntax.bl`'s datum (`Map/new`) build raw maps, so
   `'{1.0 :x}` keeps the raw key `1.0`. The raw-term fallback finds
   `(get '{1.0 :x} 1.0)`, but `(get '{1.0 :x} 1)` misses. Wrap each datum key in
   `BeamLisp.Ns.Rt/hash_key`. Quoted sets are already fixed through `Set.new`.
2. **`host/sorted.bl` `encode_key`.** Decimals fall into rank 8 ("other"). After
   this change only non-float-exact decimals such as `0.1M` stay decimals. Their
   membership is correct, but they sort after every collection instead of
   among the numbers. Encode decimals in rank 3 with an exact-order payload.
3. **Native raw map BIFs** (`maps:put/get/is_key/remove` leaves in
   `host-leaves.scm`) route through `bl-assoc`/`bl-get`, so they now
   canonicalise too. BEAM's raw `maps:put(1.0, …)` keeps `1.0` distinct. If any
   code needs raw Erlang map semantics natively, those leaves should call
   non-canonicalising internals.
4. **JS target** (`priv/lib/js/rt.mjs` `keyEq`) is unchanged. Q3 on JS is
   separate work.
5. **E8:** add a NaN canonicalisation clause and a fixed NaN position in
   `bl-key-compare`, which currently compares a NaN as 0 against every float.

## Residual replicas

`native-decimal-canon`/`native-key-canon` restate `rt.bl`'s
canonical-representative rule in host Scheme. The contract assigns this "matching
key code" to KEYS, and both implementations are checked against the same
example list (`value_keys_test.bl` and `native-keys-check.scm`). Nothing else is
replicated.

## Risks for integration

* **Programs that relied on `1` and `1.0` being distinct keys.** Any compiler
  or data code that keys a map or set by literal values now merges equal
  numbers. The focused compiler and literal tests passed, including
  `[1.0 1]` keeping both kinds as values, but the full suite has not been run
  (agents may not run it). Integration should run it.
* **Raw maps.** Maps built by interop keep raw keys. Exact-term lookups and
  `dissoc` still work, but `=`-only lookups miss.
* **Cost.** Composite keys now pay a walk over tuples, records and trie vectors
  (previously only dense vectors, lists, maps and sets were walked). Struct keys
  call `BeamLisp.Record/record_module?` once.
* **Native tables** (`h-table-*`) now use value keys. ETS `set` tables on BEAM
  match exactly, so the two diverge for integral-float and decimal keys only.
* The `priv/boot` and `priv/host` edits trigger a toolchain rebuild on the next
  run, as usual. The integrated SDK must include `set.bl` and `transient.bl`
  together with `rt.bl`.

---

# Second pass (after `git merge worktree-native-speed` at `12241b695`)

The second pass closed Requests 1–3 of the first pass and added the two
native items MEASURE asked for.

## Commits

* `c4d733726`: canonical quoted and syntax map keys, decimals ranked with the
  numbers in sorted collections, raw native map leaves.
* `b07f9432c`: native struct-field fast path, inline keyword compare,
  fixtures, and the native differential in `check-native.sh`.
* `14f7da044`: `host_sorted_test` improper-list encodings use the new number
  payload.

## Changes

1. **Quoted map literals.**
   * `compiler.bl` `datum`, `:map` branch only: each key goes through
     `Rt.hash_key`. LINK's `compile-call` hunks are untouched.
   * `syntax.bl` `to-datum`, `:map` branch: the same.
   * Result: `(get '{1.0 :x} 1)` is `:x`, `(count '{1 :a 1.0 :b})` is 1, and
     syntax data round-trips with canonical keys.
2. **`host/sorted.bl` `encode_key`.**
   * Every number, of any kind, encodes as `{3, [floor | fraction-digits]}`.
     The fraction digits are the exact decimal digits of the fractional part,
     with no trailing zeros. A float's fraction m/2^k always has k decimal
     digits, so Erlang's list order equals numeric order.
   * Decimals that are not floats, such as `0.1M`, now sort among the
     numbers: `[0 0.1M 0.1 0.25 1]`.
   * The pinned encodings in `host_sorted_test` changed from `(tuple 3 1)`
     to `(tuple 3 (list 1))`, plus the two improper-list rows. The documented
     helper list gained `bits`, `fraction-digits`, `number-payload` and
     `pow10`. No persisted format uses `encode_key`; it only orders the
     in-memory `gb_trees`.
3. **Native raw Erlang map leaves are exact-term again, as on BEAM.**
   * `host-values.scm` splits each map operation into an exact-term
     `native-raw-get/has?/assoc/remove` and a BL key path
     (`bl-get`/`bl-assoc`/`native-map-has?`/`native-map-remove`) that
     canonicalises the key, then calls the raw one.
   * Raw again: the literal constructor (`bl-map`, whose keys the compiler
     already passed through `hash_key`), `h-bmap`, `native-map-entry` and
     `native-map-ref`.
   * Switched to the raw operations in `host-leaves.scm`: `maps:get/2,3`,
     `maps:find`, `maps:is_key`, `erlang:is_map_key`, `erlang:map_get`,
     `maps:put`, `maps:remove`, `maps:without`, `maps:with`, `maps:merge`,
     `maps:filter`, `maps:from_list`, the process dictionary, and
     `Process.get`.
   * Switched in `host-extra.scm`: `Map.get`, `Map.delete`, `Map.update`,
     `Enum.group_by` and the `maps:map` helper.
   * Tables now canonicalise in `h-table-lookup` as well, so their three
     operations agree.
4. **Struct fast path (MEASURE A3, about 10.9% natively).**
   * `maps:get/2,3`, `erlang:map_get` and `is_map_key` of `:__struct__` on a
     native set, vector or opaque struct answer from the tag. They no longer
     build the set's member map through `native-struct-fields`.
   * The field keys (`meta`, `items`, `members`) are interned once. Before
     this, `native-raw-map-has?` allocated
     `(list (bl-key …) …)`, a `string-append` plus an intern, on every call.
   * Other fields (`:members`) still materialise, as before.
5. **Keyword comparison.**
   * In `bl-key-compare`, two symbols now take one `symbol->string` and one
     first-character test per side, inline. Before, a comparison made two
     `native-colon-symbol?` calls, each fetching the name again.
   * The order is unchanged: names are still compared from after the colon
     with the same UTF-16 rule, and non-keyword symbols still go through the
     ranked path.
   * A different representation (cached ranks) would need a layout or
     global-table change, so this is the only part done.

## Checks

* **Native**: `work run --memory-high 900M --memory 1G --timeout 5400 -- bash research/native-seed/speed/keys/check-native.sh`, final run `out/native-run5.log`, exit 0.
  * `native keys checks: 2964` (2,947 earlier). New rows:
    * raw `maps:put`/`maps:get`/`is_key`/`is_map_key`/`maps:remove`/`maps:from_list`/`Map.get` keep `1` and `1.0` apart, and BL `get` on such a map takes the canonical key;
    * `:__struct__` of a set or vector is answered with **zero** `native-struct-fields` calls (counted by wrapping it), while `:members` still makes exactly one.
  * values 27, memo 27, extra and raw-leaf fixtures all at the counts `check-host.py` expects.
  * **values differential** (`speed/values/values-diff-check.scm`, which compares the round-2 host procedures): 145,790 checks, 1,320 differing outcomes. **All of them are map storage or lookup with float or decimal keys**: 1,029 `random map *` rows, whose random keys include `-0.0`, `1.0` and decimals, and 371 `bl-map literal *` rows, each naming a float or decimal key looked up through the canonical `bl-get` in a raw literal. **Zero** differences in key order (`bl-key-compare`, `small-map-search`, `term-compare`), keywords, strings, struct modules, equality or vectors. The script fails if any other row differs.
* **BEAM**, one batched cold run of 26 files: value_keys, the 19 files from the first pass, and the compiler/syntax literal tests (`compiler_metadata_datum`, `contextual_datum_macro`, `contextual_syntax`, `reader_literal`, `reader_number_literal`, `test_macro_literal`).
  * The merged tree (`12241b695`) **cannot prepare an SDK**. Preboot fails at
    `true = BeamLisp.Bootstrap.packaged_member?(BeamLisp.CompilerData)` (`scripts/check-source-floor`, "generation P fresh boot failed").
  * I reproduced the same failure on `12241b695` with none of my pass-2
    changes (`out/isolate.log`). It is FACTS' pending floor regeneration: their
    RESULT says the seed table now has `Facts` and the floor must be
    regenerated. Agents may not regenerate it.
  * So I ran the batch on the pre-merge KEYS tree (`deb67233a`) plus exactly
    the pass-2 `priv/` diff (`out/pass2.patch`). The 26 test files are
    byte-identical in both trees. The working tree was restored to `HEAD`
    afterwards.
  * Result (`out/batch3.log`): 25 files passed. `host_sorted_test` had two
    stale improper-list encodings, fixed in `14f7da044`. Rerun of
    `host_sorted`, `sorted` and `value_keys` (`out/batch4.log`):
    **3 files passed, 0 failed, all green** (170 + 93 + 3,906 assertions).
    The other 23 files: 4,921 assertions, all passed.
* `./bin/bl realm stop`: on the restored tree this began an SDK preparation
  (no realm was running). I stopped that preparation, since it would fail
  the same way.

## Requests (updated)

* The first pass's Requests 1–3 are closed.
* Still open: 4 (Q3 on the JS target) and 5 (NaN in E8).
* **New, for the main thread**: after the FACTS floor regeneration, rerun
  `out/batch3.log`'s command on the merged tree, once. These KEYS checks
  were not run on the merged tree.

## Risks (added)

* The integrated BEAM run of these changes is still pending on the floor
  regeneration.
* Native raw map leaves are exact-term again. The values differential's
  `bl-map literal` rows show the boundary: a raw literal holding a float or
  decimal key is not found by BL `get` with the equal integer. That is the
  BEAM behaviour too, where only the BL paths canonicalise. Real BL literals
  pass through `hash_key` first.
* Numbers in sorted collections now encode as a list. Each comparison costs a
  little more, and non-integral floats and decimals build a digit list (up to
  1,074 digits for a subnormal float).
