# READER (R): the reader as a per-codepoint automaton

Workstream READER of the round-2 fan-out ([`CONTRACT2.md`](../CONTRACT2.md)).
Owned files: `priv/boot/reader.bl` (rewritten), `priv/boot/reader-node.bl`
(unchanged). Item R of the dossier: the reader made ~250 calls per byte.

## What changed

The reader keeps its representation, a charlist (one Erlang list cell per
codepoint, and one Scheme pair natively). The contract asks for a representation
that is O(1) per step on both backends, and the charlist is that representation:
native text is a string of codepoints, so a byte-indexed binary reader would be
O(n) per access there. What changes is the cost of each step.

- **Hot loops are BIF-only.** Whitespace and comment skipping, token scanning,
  and string, regex and raw-string bodies use `erlang/hd`, `erlang/tl`,
  `(erlang/=:= xs ())`, and integer comparisons on a codepoint guarded by
  `erlang/is_integer`. The native emitter turns those comparisons into fixnum
  ops through integer facts. Line, column and offset are plain integer loop
  variables. The hot path makes no generic `=`, `first`, `rest`, `empty?`,
  `cons` or lazy-sequence call.
- **Classes are integer range trees.** `delimiter?` decides a letter in two
  comparisons. It replaces both the per-token `string/cspan` stop-list (13
  conses per token natively) and every `cond` chain of generic `=`.
- **Scan, then cut once.** A token, a string segment between escapes, a regex
  body or a raw body is counted first and then split off with a single
  `lists/split`. No cons cell is built per character of text. A string with
  escapes becomes chardata (`[acc, segment, escape]`) and is converted once.
- **Positions come from counters.** The old `advance-to` re-walked consumed text
  and stopped at `identical?`, which is `=:=`, a structural comparison of two
  list suffixes. It is gone. Each step now builds a `{line col file offset}`
  tuple only at a token or form boundary. A skip that consumes nothing returns
  the original position.
- **Internal results are tuples.** The `{form rest pos state}` step results
  replace bl vectors and their `nth` destructuring. Nodes are built with
  `erlang/list_to_tuple` rather than `rn/->tuple [..]`, which went from vector
  to list to tuple. Accumulators use `(lists/reverse (list x) acc)` rather than
  the generic `cons` dispatch.
- **Fast token paths.** A token that cannot start a number (it does not begin
  with a digit, or with a sign followed by a digit) goes straight to the symbol
  path. Every number rule (`string:to_integer`, `to_float`, the exp-float
  patch, radix, octal, `M`/`N` and `digit-led?`) needs that prefix, so no
  answer changes. A plain decimal (an optional sign, then digits with no
  leading 0) is read with one `string/to_integer`.
- **The stream shares one step.** `read-forms*`, `read-next` and
  `read-next-string` share `next-form`, which returns a tuple. The batch read
  no longer rebuilds the stream map per form. `read-next-string` slices with a
  bounded `lists/split` rather than `lists/sublist`, whose native leaf calls
  `length` on the whole remaining source for every form. That made the native
  stream quadratic.

The diagnostics, the reader.ex position quirks (`#(`, `#tag{`, data-reader
payloads, prefix forms), the BOOTSTRAP rule (no new top-level `def` on the read
path), the public API and the shapes it returns are all unchanged.

### Deviation: no tuple class table or `case`

The brief suggested a tuple class table read with `erlang/element` and a `case`
on class codes. I did not use either:

1. **`case` would not dispatch cheaply.** BL `case` on literal constants lowers
   to a chain of `rt/eqv` calls. The ANF of `(case c 40 :a 41 :b :c)` is
   `(if (rt/eqv c 40) … (if (rt/eqv c 41) …))`. That is exactly the generic
   equality this item removes.
2. **A table would be rebuilt on every call.** It would have to be a top-level
   `def`, which the BOOTSTRAP rule in `reader.bl` forbids on the read path, or a
   literal. Natively, `native.scheme/literal` emits a tuple literal as
   `(bl-make-tuple …)`, so the table would be rebuilt on every evaluation.

The range tree has neither problem and is still O(1) per step.

### Functions

- **Rewritten:** `fail!`, `syntax-error`, `syntax-fail` (unchanged bodies),
  `tuple2`, `node`, `symbol-node`, `make-pos`, `advance-pos`, `pos-meta`,
  `pos-meta-span`, `wrap-list-pos`, `take-token`, `skip-pos`, `chars->string`,
  `hex-value`, `parse-hex`, `valid-codepoint?`, `parse-unicode-escape`,
  `escaped-codepoint`, `read-string-body`, `pipe-chars`, `pipe-run`,
  `read-regex-body`, `read-raw-string-body`, `split-tag-at-pipes`,
  `whole-number`, `suffixed-number`, `exp-float`, `digit-value`,
  `radix-digits`, `strip-n`, `unsigned-integer-literal`, `integer-literal`,
  `digit-led?`, `character-literal`, `classify`, `pair-items`, `prefix-pos`,
  `wrap-prefix`, `keyword-node?`, `metadata-key`, `metadata-spec`,
  `attach-meta`, `read-meta`, `opener-for`, `splice-marker?`, `read-until`,
  `fn-arg-index`, `rewrite-fn-seq`, `rewrite-fn-arg`, `positional-params`,
  `desugar-fn`, `feature-selected?`, `select-conditional`, `splice-marker`,
  `read-reader-conditional`, `data-reader-fn`, `read-tag`, `read-raw-tag`,
  `read-dispatch`, `read-atom`, `source-kind`, `read-form-core`, `read-form`,
  `unwrap-deep`, `read-next`, `read-next-string`, `read-forms*`,
  `read-source*`. The public `stream`, `read`, `read-string`, `read-all`,
  `read-source-spans`, `read-syntax`, `read_string`, `read_all` and `read_one`
  are unchanged.
- **New (all `defn-`):** `tuple3`, `tuple4`, `push`, `meta-node`,
  `advance-cols`, `delimiter?`, `token-length`, `bad-unicode-escape`,
  `unterminated-string`, `all-decimal?`, `digit?`, `number-start?`,
  `plain-decimal?`, `classify-number`, `flatten-pairs`, `with-state`,
  `unexpected-closer`, `next-form`, `prefix-chars`.
- **Deleted:** `ignored-char?`, `advance-to`, `skip-comment`, `skip-ignored`,
  `parse-fixed-unicode`, `parse-braced-unicode`, `splice-items*`.
- `reader-node.bl` is unchanged: the reader no longer calls `rn/->tuple` or
  `rn/meta-node` on its hot path.

## Equivalence: differential before the cutover

`speed/reader/diff.bl`, driven by `speed/reader/diff.sh`, runs on the pinned SDK.
`reader` is the SDK's compiled reader. Its source is byte-identical to
`priv/boot/reader.bl` at the fan-out base (checked with `diff` against the
pinned source). `reader2` is the new reader under a renamed namespace, loaded
next to it in the same VM. Before the cutover it lived at
`speed/reader/reader2.bl`. Now `diff.sh` generates it from `priv/boot/reader.bl`,
so the check reruns on any later edit. Each answer, whether a value or a raised
diagnostic (the error wrapper's `:original`), is compared with `erlang/=:=`.

Corpus:
- **Files.** 1021 `.bl` files: all 717 under `priv/`, all 23 under
  `research/native-seed/src`, and every fifth of `test/bl` (281), 13.77 MB in
  total. Each file goes through `read-string`, `read-all`, `read-source-spans`,
  `read-syntax`, and a full `stream` drain with `read-next-string` (forms, texts
  and the final stream map). Each file also yields two truncated prefixes, at
  3/10 and 7/10, read with `read-string` and `read-source-spans`. They compare
  the unterminated-collection, unterminated-string and opener diagnostics at
  positions spread through real files.
- **Error corpus** (`speed/reader/errors.txt`). 103 cases: unterminated and
  mismatched collections, stray closers, bad and valid `\u` escapes (fixed and
  braced, surrogates, out of range), string escapes and escaped newlines, bad
  numbers (`1.2.3`, `08`, `0o666`, `1x`, `-0o666`, radix, hex, octal, `M`/`N`
  suffixes, exponent floats, signs), character literals, regex literals, raw
  strings and tagged raw strings, `#?` and `#?@` (inside and outside
  collections, odd counts, non-keyword features, non-collection splices), `#_`
  (stacked and dangling), metadata (`^:kw`, `^{…}`, `^Sym`, `^"str"`, stacked,
  bad keys, missing targets), `%` arguments, `#()` nesting, prefix forms with no
  form after them, quoted keywords, data readers, records, `#js`, comments,
  commas, unicode, tabs and multi-line forms. Each case is read whole and also
  line by line, through every entry: the five above plus `read` with
  `:diagnostics :collect`, a `read-next` drain and `read_one`. Eleven synthetic
  cases add CR, CRLF, vertical tab, NBSP and U+2028.

Result before the cutover (`diff.sh` over `speed/reader/reader2.bl`):

| Pass | Cases | Checks | Raised (compared as data) | Bytes read | Mismatches |
| --- | --- | --- | --- | --- | --- |
| error corpus + 2 files | 246 | 1938 | 1117 | 181 237 | **0** |
| shards 0–5 (1021 files + 2042 prefixes) | 3063 | 9189 | 3674 | 27 625 093 | **0** |

After the cutover, the same `diff.sh` ran again with `reader2` generated from
the committed `priv/boot/reader.bl`. It was clean: the corpus pass had 246
cases, 1938 checks and **0 mismatches**, and all six shards had **0
mismatches**. The corpus byte count rises to 201 737 because the corpus files
include the new `reader.bl`. The job ended `diff exit 0`.

Commands (each VM capped by `research/native-seed/run`: 3 GiB, 240 s, one at a
time):

```sh
work run --memory 3G --timeout 7200 -- research/native-seed/speed/reader/diff.sh
# = for each pass: research/native-seed/run run -p OUT/src \
#     research/native-seed/speed/reader/diff.bl -- LIST SHARD 6 [errors.txt]
```

## Reader tests on the checkout

All tests ran in one capped invocation. That invocation rebuilt the checkout
toolchain with the new reader, which shows the BOOTSTRAP rule holds: the new
reader reads its own generation.

```sh
work run --memory 4G --timeout 7200 -- bash -lc '… ./bin/bl --cold test \
  test/bl/reader_test.bl test/bl/reader_atom_guard_test.bl test/bl/reader_eager_projection_test.bl \
  test/bl/reader_literal_test.bl test/bl/reader_meta_test.bl test/bl/reader_number_literal_test.bl \
  test/bl/reader_raw_string_test.bl test/bl/reader_regex_literal_test.bl test/bl/reader_safety_port_test.bl \
  test/bl/reader_stream_test.bl test/bl/host_reader_test.bl test/bl/host_reader_exception_test.bl \
  test/bl/eval_closed_reader_test.bl test/bl/aot_reader_cache_test.bl \
  test/bl/system/linear_test.bl test/bl/anf_test.bl test/bl/anf_direct_emit_test.bl test/bl/js_diff_test.bl; \
  ./bin/bl realm stop'
```

The last four files go beyond the reader tests. Each one reads
`priv/boot/reader.bl` as a subject:
- `system/linear_test` checks the emitted/source ratio per function;
- `anf_test` and `anf_direct_emit_test` run the ANF census;
- `js_diff_test` compares JS against BEAM read output for the reader.

| File | Result |
| --- | --- |
| reader.test | 48 passed |
| reader-atom-guard.test | 7 passed |
| reader-eager-projection-test | 12 passed |
| reader_literal_test | 9 passed |
| reader-meta.test | 21 passed |
| reader-number-literal-test | 46 passed |
| reader_raw_string_test | 36 passed |
| reader_regex_literal_test | 18 passed |
| reader-safety-port.test | 11 passed |
| reader.stream.test | 108 passed |
| host.reader.test | 268 passed |
| host.reader-exception.test | 169 passed |
| eval.closed-reader-test | 295 passed |
| aot-reader-cache-test | 3 passed (`READER-GUARDS … "status":"passed"`) |
| system.linear-test | 36 passed |
| anf.test | 41 passed |
| anf-direct-emit.test | 30 passed |
| js_diff_test | **INCOHERENT: the test worker timed out** (no assertion failed) |

The summary line was `17 file(s) passed, 0 failed, 1 incoherent`. The rules
allow one test batch, so `js_diff_test` was not rerun. It builds the whole
`priv/boot` tree to JS and runs node, and the worker hit its time limit on a
loaded host. See the risks below. `bl realm stop` reported that no realm was
running, because the run was cold. No VM of this workstream is left running.

## Skipped under the updated rules

The coordinator's updated rules dropped every speed measurement from the gates.
This workstream therefore reports **no per-byte figure**, ran neither the
`bigo/scaling.bl` read rows nor the native gsi microcheck, and made no
before/after comparison. The main thread runs the one BEAM-vs-native benchmark
after integration. The `bench.bl` I had drafted was deleted unrun. Before the
rule change I ran two micro-probes to choose BEAM loop constructs. They were
design input, not acceptance evidence, and are not recorded as results.

Native emission was checked statically instead of in gsi. Every remote the new
reader calls is a registered leaf in `MAIN/NS/out/speed-build/leaves.json` or a
`native.intrinsics` template. The one exception is
`Elixir.BeamLisp.Ns.Rt/data_reader/1`, which the old reader called as well and
which links to compiled `rt`. Compared with the old reader, the new one stops
calling `string/cspan`, `lists/all`, `erlang/tuple_to_list` and generic rt
dispatch. It adds only `erlang/hd`, `erlang/tl`, `erlang/is_list` and the
arithmetic and comparison BIFs, all templated natively and intrinsic in the JS
emitter, plus `lists/reverse/2`, a leaf on both. No new leaf was needed.

## Risks for integration

- **JS reader parity is unverified.** `js_diff_test` timed out rather than
  failing, so it is unproven, not refuted. Every remote the new reader adds is
  in the JS emitter's intrinsic table (`erlang/=:=`, `=/=`, `<`, `>`, `=<`,
  `>=`, `+`, `-`, `list_to_tuple`, `lists/reverse/2`, `is_integer`) or in
  `leaves.mjs` / `host-leaves.mjs` (`erlang/hd`, `erlang/tl`, `erlang/*`,
  `is_list`). The main thread should run `test/bl/js_diff_test.bl` once with a
  longer worker budget.

- **BOOTSTRAP.** The read path now calls 19 new private functions. They are
  module-local functions compiled from this file, not registry vars, and the
  rule only forbids new top-level `def`s. There are none (the
  `CONDITIONAL-FEATURE` def is unchanged). The first `./bin/bl --cold` run
  above rebuilt the toolchain with this reader; see the test result.
- **Native chardata.** `unicode/characters_to_binary` natively
  (`native-char-data`) converts a charlist one string per codepoint through
  `string-append`. The reader now calls it once per token or string, and string
  values with escapes are nested chardata. This stays linear, but that leaf is
  the remaining per-codepoint toll on native. It is a category (b) leaf outside
  READER's files; a flat `list->string` fast path there would remove it.
- **Native leaves on the slice path.** `read-next-string` no longer calls
  `lists/sublist`, but other callers of that leaf still pay `length` of the
  whole list per call natively.
- **Emitted Scheme for the reader chunk changes.** It is generated from the new
  source, so content-addressed chunk caches for `reader` miss once. Stage-2 and
  stage-3 parity is unaffected, because both run the same source.
