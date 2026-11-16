# Workstream BACKEND: C2 (emitter throughput) and U (content-addressed units)

Branch `native-self-backend`. Files changed:
- `src/native/scheme.bl` (C2)
- `split-top-level.scm` and the split and unit-cache parts of `fixpoint-full.py` (U)

New check tools are in `speed/backend/`.

Under the updated round rules, the gates are correctness only. They are byte-identical emission and the unit-stability split test. **Skipped by rule:** the fixture emit timing, the `scaling.bl` slopes, and any before/after timing. A timing run that was queued was stopped. The main thread runs the one BEAM-vs-native benchmark after integration. No SDK and no image was built. One unit was compiled with gsc.

## C2: emitter

### What made emission slow (one eprof of the previous emitter on the fixture, before the rules changed)

No timing numbers are recorded here. By call count, the profile was dominated by three things:

1. **The lazy-memo capture walk.** `LazyMemo.deps_walk` and its neighbours ran under the lazy seqs that emission built: `map`, `mapcat`, `concat`, `map-indexed`, `range` and `distinct`. Those seqs captured ANF subtrees and `options`.
2. **`str`.** `rt/str_v` goes through `map-join`, then `raw-cons` and `to-str` for each argument. Every piece also re-entered the invocation toll: `source-invocation!`, `check_source_invocation!` and `Env.source_head`.
3. **`clojure.string/join`.** It does `(map str …)`, which is lazy and adds the same toll per element.

### Changes (`scheme.bl`)

| Change | Functions |
| --- | --- |
| Text is assembled by `glue` (one `Enum.join` over strings) and `spaced` (`Enum.join` with `" "`), not by `str` / `string/join`. Integers are converted explicitly with `erlang/integer_to_binary`. `str` is kept only where a value may not be a string: `refuse`, the decimal literal, and the qualified name in `emit-definition`. | all emitters |
| No lazy sequence is created anywhere in the emitter. Every collection is an eager Erlang list built with `Enum/map`, `Enum/reduce`, `Enum/with_index`, `Enum/flat_map`, `Enum/zip`, `Enum/uniq` or `lists/seq`. The `items` helper turns an ANF list, vector, set or nil into a list. | `joined`, `ordered`, `ordered-call`, `linked-operands`, `linked-language-call`, `literal-items`, `clauses`, `irrefutable?`, `function-expression`, `match-indexed`, `match-pattern`, `emit-source-loop`, `multi-layout`, `emit-multi`, `argument-list`, `emit` (`:fn`, `:map`, `:struct`, `:do`) |
| Binders and map-key bindings are accumulated in reverse with one `Enum.reverse`. They replace the nested `mapcat`/`concat`/`apply concat` chains. | `binders-into`/`binders`, `patterns-binders`, `clauses-binders`, `key-bindings-into` (replaces `map-key-bindings`) |
| `forget-facts` takes a thunk for the names, so no binder list is built when there are no integer facts (the common case). | `forget-facts` and its 5 callers |
| `ident` uses a precomputed table of `"_<c>"` strings for ASCII and one `Enum.join`, with no `str` per character. `text` returns `"\"" s "\""` directly when nothing needs escaping, and otherwise uses the per-character map. Operand, formal and loop-initial names (`a<i>`, `fa<i>`, `loop-initial-<i>`) come from tables. | `ident`, `text`, `code-text`, `operand-name(s)`, `formal-names` |
| The loop-safety walk threads its `{:candidates :unsafe}` state through return values: no atom, no `doseq`, no `vals` except for unknown ops, and a `case` dispatch on `:op`. Each self-application region is still walked exactly once, by its outermost candidate, and every nested loop reads the verdicts from options. | `loop-walk`, `loop-walk-all`, `loop-walk-clauses`, `loop-verdicts`, `loop-unsafe` |
| `total?`, `irrefutable?`, `multi-layout` and `integer-intrinsic` use `Enum.all?` and `any-of?` (built on `Enum.all?`, because native has no `Enum.any?` leaf), not BL `every?`/`some`. | |

The order in which subtrees are emitted is unchanged everywhere. That order decides which refusal is reported first, and the order of any resolver-side recording. `emit-multi` keeps the previous order: keys, variadic tag, arms, `$blfn` tag. `clauses` still emits later clauses before the current body, and `emit-try` still emits its handler first.

Public signatures are unchanged: `emit`, `emit-definition`, `ident`, `text`, `literal`, `joined`, `ordered`, `clauses`, `binders`, `remote`, `refuse`. `(:call link)` still receives a **vector** of operands. `native.scheme` adds no requires. Every new remote is a registered native leaf. This was checked with `speed/backend/leaf-calls.py` against `MAIN/NS/out/speed-build/leaves.json`: `Enum/{map,reduce,with_index,flat_map,zip,uniq,filter,reverse,all?,join}`, `lists/{seq,append,member}`, `BeamLisp.Vector/to_list` and `erlang/{element,list_to_tuple,integer_to_binary}`.

### Linearity, argued from structure

- Each ANF node is visited once by `emit`, plus at most one loop-verdict walk per outermost loop region. No intermediate value captures a subtree lazily.
- The remaining super-linear term is string copying. A nested node's text is copied once per enclosing `glue`, so deep nesting copies O(depth × size) bytes. That is memcpy inside `Enum.join`, and it is not per-node work. If the post-integration benchmark still shows a deep-fn slope, the next step is iodata through `emit` with one `iolist_to_binary` at `emit`/`emit-definition`. On native, though, `iolist_to_binary` goes through a byte list (`native-iolist-binary`), so that needs a KERNEL template first.

### Byte-equality checks (all green)

1. **AOT link emission, the whole closure.** `chunks.bl inspect` emits every one of the 1394 compiled definitions of `MAIN/NS/out/speed-closure` (from `stage1.scm`'s `native-register!` rows), plus the seed links. It runs once with HEAD's `src/` and once with this branch's `src/`. The cwd is MAIN, read-only.
   ```
   speed/backend/inspect-run.sh OLD_SRC  $S/inspect-old $S/slots.txt
   speed/backend/inspect-run.sh $WT/research/native-seed/src $S/inspect-new $S/slots.txt
   cmp $S/inspect-old/inspect.scm $S/inspect-new/inspect.scm   # INSPECT_IDENTICAL
   ```
   Both print `NATIVE_CHUNKS_INSPECT 1394`. `inspect.scm` is identical (4,505,621 bytes), and so is `seed-links.scm`.
2. **Fixture, control corpus and real sources under every non-AOT option set.** `speed/backend/equality.bl` runs HEAD's emitter, renamed `backend.old-scheme` (`speed/backend/old-scheme.bl`), and the new one on the same ANF. It compares `emit`, `emit-definition` and the `:emission-counts` maps under five option sets:
   - the benchmark options
   - benchmark + `:source-frames?`
   - `ev/context`
   - `ev/context` + frames
   - plain `{:ns "user"}`

   It also compares `ident`, `text` and `literal` on edge inputs: quotes, control characters, non-BMP text, and every literal kind. Refusals must give the same message.
   ```
   work run --memory 3G -- research/native-seed/run -p research/native-seed/speed run \
     research/native-seed/speed/backend/equality.bl -- OUT benchmark/compiler-values.bl \
     speed/control/corpus.bl src/native/{scheme,eval,resolution,intrinsics}.bl
   EQUALITY {:nodes 141, :equal 2143, :bytes 7787097, :refused 810, :compared 2143, :different 0}
   EQUALITY_OK
   ```
   The fixture's six forms are included under the benchmark's exact options (`beam-benchmark.bl`). The control corpus's forms are included under `ev/context`, the options of `control/check.bl`. 810 comparisons are identical refusals, which come mostly from the plain and frames variants.

## U: content-addressed stage-1 units

### Splitter (`split-top-level.scm`)

Forms are grouped by definition. A group starts at a head, `(define NAME …)` or `(define (NAME …) …)`, where NAME has no `$`. So `v_X$1`/`$g` and the registration forms stay with their definition.

- **Natural cut.** A unit ends after group G when `fnv1a32(NAME_G) / sizeclass(bytes_G) < 2^32 / split-mean`. `split-mean` is target/4 (64 KB) and `sizeclass` rounds down to a power of two. The decision reads only G's own name and size class, never a position. Per byte, cuts are equally likely, so a run of big definitions does not become one long unit. The FNV low bits are useless for `v_<digits>` names, so the whole hash is compared.
- **Bounds.** No natural cut is made before a unit reaches `split-min` (target/32). A unit never exceeds `split-target` (unchanged at 256 KB) unless it is a single oversized form. On overflow the unit is cut before its **strongest** group start (lowest score), not at the overflow point, so an edit that moves the overflow point rarely moves the cut.
- **Protocol.** `CHUNK\tforms-i.scm\tforms\tbytes\toversized` lines, file names and the FFI refusal are all unchanged. `fixpoint.py` and `native_elf.py` keep working unmodified. UTF-8 size is now `(u8vector-length (string->utf8 text))`, not an interpreted per-character loop.

### Unit cache (`fixpoint-full.py`)

- `split_source` moved to module level with explicit inputs, so the check can call the driver's own code.
- The new `unit_cache_request(row, ordinal, tools)` keys a unit by `{source_sha256, role: host|forms, tools}`. The **ordinal is no longer in the key.** The C stem, and with it Gambit's module name, is `unit_<key16>`. Two units with one content key raise an error.
- The link table (`gsc -link`, link object and image) stays a separate cached phase over the ordered C units. A changed unit therefore perturbs no other unit's key.
- `unit_cache_request` is added to the compiler-recipe function list. The recipe hash changes, so the first build after integration recompiles every unit once.

### Unit-stability check

`speed/backend/unit-stability.py` copies MAIN's read-only `stage1.scm` and `host.scm` into a scratch directory and splits with the driver's `split_source`. It then keys every unit with `unit_cache_request`. Next it applies 40 random body edits (20 grow by about 3 KB, 20 shrink to `(lambda args bl-nil)`) and re-splits after each one.
```
work run --memory 4G -- python3 research/native-seed/speed/backend/unit-stability.py \
  MAIN/research/native-seed/out/speed-build $S/units40 --edits 40 --seed 11
new UNITS 58 bytes {min 9462, max 248008, mean 82258} split 0.9 s UNCHANGED reused 58 / 58
40 x "EDIT … changed [k] holder [k] reused 57 / 58 EXACT"
UNIT_STABILITY_DONE True
```
- An unchanged re-split reuses all 58 keys.
- Every one of the 40 edits changes **exactly** the one unit holding the edited definition and reuses all 57 others. The report is in `speed/backend/unit-stability-report.json`.
- For comparison, the previous greedy 256 KB splitter (6 edits, `--baseline`, keyed the same way without ordinals) changed `[2,3,4]`, `[3..19]` (17 of 20), `[4]`, `[9]`, `[12]` and `[17,18,19]`. Over 40 edits it was exact in 7 and spread in 33. With ordinal keys, as the old driver had them, the spread is wider still.
- **gsc validity.** One produced unit (`forms-17.scm`, 9 KB) compiles with `gsc -c -prelude '(declare (standard-bindings) (extended-bindings))'` and prints `GSC_OK` (47 KB of C). No other unit was compiled and no image was built.

## Residual replicas

None. BACKEND does not self-host any module.

## Risks for integration

- **Unit count.** There are now about 58 form units of about 82 KB each (previously 20 of about 250 KB). There are more gsc/clang invocations, each smaller, and the link step sees more C files. Mean size is set by `split-mean` in `split-top-level.scm`.
- **Recipe change.** The `fixpoint-full.py` recipe hash and the splitter hash both change, so the first build recompiles everything once. `fixpoint.py` and `native_elf.py` (not owned) still put the ordinal in their unit keys. They benefit from the stable boundaries but not from ordinal-free keys.
- **Upstream shifts.** Boundaries are stable only if the emitted text of unchanged definitions is stable. Compiler gensyms (`fnself_372`) are counter-based per compile. If a chunk is recompiled as a whole and the counter is shared across its definitions, one edit renames later gensyms and changes their bytes. That is D/CLOSURE's concern: the split then correctly reuses only the truly unchanged units.
- **Native cost of the new emitter.** On native, `Enum.join` uses `native-join` (string port) and `Enum.map`/`reduce` invoke through `bl-invoke`. Compared with the old `str` (`bl-str`) path this should be no worse, but it has not been measured, by rule.
- **`glue` on a non-string.** On BEAM `Enum.join` renders nil as `"nil"`, where `str` renders it as `""`. Every `glue` argument was audited to be a string. Both equality checks are green over the 1394 closure definitions and 2143 comparisons.
- `speed/backend/old-scheme.bl` is a frozen copy of the previous emitter, used only by `equality.bl`. Delete it once the main thread has re-run the gates.
