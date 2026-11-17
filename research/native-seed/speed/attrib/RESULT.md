# A3 · Attribute the gap on a real corpus

Workstream MEASURE, round 3 wave 1. No runtime or compiler source changed.
Everything here is counts and shares from **one profiling run per target**
(plus one extra BEAM run explained below). No timings are claimed.

## The fixture

`priv/boot/reader.bl` (86,200 bytes, 1,648 lines): 105 top-level forms, 104
`defn`/`defn-`/`def` definitions. Both targets run the same steps
(`native-attrib.scm.in` and `beam-attrib.bl`):

1. **read**: `reader/read-string` over the whole file, attribution
   `priv/boot/reader.bl`;
2. **compile**: for every definition, `compiler/declaration-source`, position
   meta on the value form, `compiler/reset-fresh!`, then `compiler/compile` in
   namespace `reader` with `:target :js`. This is `native.bootstrap/prepare`
   without its Env side effects, so it is what self-compilation does per unit;
3. **emit**: `native.scheme/emit` of each node with `native.eval/context
   "reader"` as options.

Native runs it inside the round-2 image (`MAIN/NS/out/round2-build/stage1`,
`7c32ac57…`) as the `--eval` payload of a single process, after
`native.bootstrap/install-source-macros!` and an `eval-form` of the `ns`
header (setup, not measured). BEAM runs it in one warm VM on the pinned SDK
(`v8jbl8q0…`, `NS/run`).

**The emitted Scheme is not byte-identical between the targets, and this is a
finding** (`raw/emitted-diff.txt`). 26 of 104 definitions are equal. The
difference comes from *compile*, not emit: on BEAM a call to a sibling
definition (`reader/x`, `diag/error`, `reader-node/…`) compiles to a remote
call into the loaded module (`(native-remote "Elixir.BeamLisp.Ns.Reader/…")`,
585 sites). Natively it compiles to a Var fetch plus `bl-invoke`
(`(native-global-exact "reader" …)`, 469 sites). The compiler's output depends
on how the Env answers link questions, which is P3's subject. Each target's
output is stable: native's uninstrumented and fully wrapped passes produce the
same bytes (`9755174f…`), and the bare and snapshot BEAM runs produce the same
bytes (`bcb3c4b0…`). So each target's counts describe its own ANF, and the two
targets do comparable work, not identical work.

## Method

**Native sampling pass** (shares). A heartbeat interrupt
(`##interrupt-vector-set! 2`, every 5 ms, 6 rounds of read+compile+emit) keeps
the whole stack of every sample: 6,544 samples. Gambit names a compiled BL
definition only by its unit (`unit_<hash>#`), because the definition is an
unnamed `case-lambda` inside the unit's top level. So the sampler records each
frame's **return point** (unit plus subprocedure id), and `analyze.py` maps it
to the enclosing definition:
- `CODE` rows give the entry id of every linked slot, host procedure and leaf
  (2,547).
- `CALIB` rows (551) come from wrapping `h-tick`: its continuation is the
  return point right after the entry tick of the calling definition, joined to
  the slot whose counting wrapper is active. In every calibrated definition the
  return points sit 2 to N ids above the entry. So a return id belongs to the
  nearest entry at or below it. The topmost entry of a unit has its range
  capped, because the unit's host Scheme lies above it.

A sample's **bucket** is decided by its innermost run of host frames: the
outermost frame of that run is the host operation that BL code invoked, and the
first BL frame above it is the caller. Self time of compiled BL code is
charged to its definition.

**Native counting pass** (exact counts, one round). Every linked BL slot
(`v_…$N`, `$v`, `$g`), every host leaf (`lv_…`) and every host procedure is
replaced by a counting closure: 4,526 wrappers. The closures count calls per
target and caller→callee edges. Counting perturbs time, so these rows are
counts only.

**BEAM**: `bl.profile/call-time` (OTP `tprof`, `call_time`). Each phase runs
3 repetitions under one profile. tprof traces every call, so call-heavy code
is overweighted relative to BIF-heavy code. Read the BEAM shares as an
ordering, not as exact fractions.

**The second BEAM run** (`snapshot`). In the first run, about 46 % of BEAM
compile went to filesystem lookups: `Loader/find_file`, `source_relatives`,
`Path/join`, `File/regular?` and `file:read_file_info`, about 219k calls per
compile of reader.bl. The cause is `Loader/resolvable?`. It caches only inside
`BeamLisp.Loader/with_declaration_snapshot`, so the bare compiler API searches
the source path again for each unresolved lowercase prefix (`erlang/…`,
`lists/…`). A real load runs inside a snapshot, so the run that ranks BEAM
wraps every repetition in it. The bare figure stays in
`raw/beam-bare-summary.json`, and it matters to anyone who calls
`compiler/compile` directly, as the warm-core benchmark does.

## Exact commands

From `research/native-seed/speed/attrib/`, with
`B=MAIN/research/native-seed/out/round2-build`:

```sh
python3 prepare.py --build $B --source ../../../../priv/boot/reader.bl \
  --out runs/native4 --reps 6 --interval 0.005
work run --memory 4G --timeout 1800 -- ./run-native.sh runs/native4
# exit 0; A3_FIXTURE forms 105 definitions 104 emit-failures 0 chars 308923
# A3_WRAPPED 4526; outputs native.scm == native-counted.scm

N=…/r3-measure/research/native-seed     # absolute; run's cwd is the repo root
work run --memory 4G --timeout 1800 -- bash -lc "./run run $N/speed/attrib/beam-attrib.bl -- \
  $N/../../priv/boot/reader.bl $N/speed/attrib/runs/beam2 3 snapshot > …/beam2/beam.log 2>&1"
# exit 0; A3_FIXTURE snapshot true forms 105 definitions 104 emit-failures 0 chars 258690
# (runs/beam1: the same without `snapshot`)

python3 analyze.py native runs/native4      # -> native-summary.json
python3 analyze.py beam runs/beam2          # -> beam-summary.json
python3 diff-emitted.py runs/beam2/beam.scm runs/native4/native.scm
```

Earlier native runs (`native1` to `native3`) were debugging runs of the same
observer: a sampler livelock at 0.5 ms, frames named only by unit, and the
missing calibration. Their counts are identical to `native4`'s.

## Phase shares

| Phase | Native (samples) | BEAM (tprof µs, snapshot) |
| --- | --- | --- |
| read | 6.7 % | 6.8 % |
| compile | 82.5 % | 54.9 % |
| emit | 10.8 % | 38.3 % |

On a real namespace, native's gap sits in **compile**. The warm-core fixture's
read ratio (22.5×) mostly reflected fixed costs. Native emit is a smaller share
than BEAM emit because BEAM's emit is dominated by its own Var-invocation gate
(below).

## Native ranking (share of all pipeline samples)

| # | Cost | Share | read / compile / emit | Roster item |
| --- | --- | --- | --- | --- |
| 1 | Compiled `rt.bl` kernel code, self time (`rt/eqv` 3.0 %, `first`, `nth`, `hash_key`, `k-eqv`, `inc`/`dec`, `not_`, `empty?`) | **15.8 %** | 2.1 / 16.9 / 15.9 | N1 + N2 |
| 2 | Variadic and multi-arity calls dispatched through `bl-invoke` → `native-resolve-call` (arity-map `bl-get`, `native-take`/`drop` to split rest args, `(bl-key "$blfn")` interned at every test) | **12.3 %** | **43.5** / 10.0 / 9.9 | N3 (link the variadic entry), N1 for known `core/tuple`/`list` |
| 3 | A struct or kind test on a **set** materialises its fields: `rt/kind-kind` → `maps/get :__struct__` → `native-map-fetch` → `native-assert-map` → `native-struct-fields` builds a MapSet map of every member | **10.9 %** | 0 / 12.9 / 2.1 | V2b (header metadata); a host-values fast path for `:__struct__` on `set`/`vec` gets most of it without a layout change |
| 4 | Map and set operations: AVL `native-tree-put`/`find`, small-map search, keyword keys compared as strings (`bl-key-compare` → `native-scalar-string-compare-from`, `native-colon-symbol?`) | **10.4 %** | 10.5 / 9.7 / 15.7 | V2a (interned keywords: `eq?`) + V2c (hash maps) |
| 5 | **Quoted set literal rebuilt on every call**: `compiler/kernel-special-forms-literal` (2,962 calls) and `kernel-java-lang-classes-literal` (861) run `bl-set-from-list`, 111k `native-set-put` per compile | **10.2 %** | 0 / 12.4 / 0 | N1 (quoted literals hoisted to constants) |
| 6 | Grapheme `String.length` and codepoint slicing: `core/subs`, `compiler/split-slash` (from `name-provider`, `slash-target`), `k-count` of a string; `native-with-matches`, `native-byte-slice`, `native-utf8-*` | **10.0 %** | 1.8 / 11.7 / 1.7 | V2e (text as bytes) |
| 7 | Other host procedures, mostly the native Env answering compile-time questions (`native-env-link`, `native-fetch`, `native-known-ns?`, `native-maybe-load-macro`, `native-fold`) | 8.8 % | 9.6 / 9.4 / 4.0 | P3 / LINK (native Env), partly N3 |
| 8 | Compiled compiler, reader and emitter algorithms, self time | 7.2 % | 19.6 / 5.8 / 10.4 | E5 (the real work) |
| 9 | List BIFs and leaves (`Enum/map` leaf, Env `alias_target`/`refer_source` leaves) | 5.3 % | 3.9 / 3.8 / 17.7 | — / P3 |
| 10 | Emitter text assembly (`native-join`, `##wr`, string ports) | 4.3 % | 6.8 / 2.4 / 17.0 | C2 / V2e |
| 11 | Generic arithmetic: `native-arith-add` is `(native-num 'add a b)` with **no fixnum path**, and every op probes `native-decimal?` 4× (1.16M calls) | 2.8 % | 0 / 2.9 / 3.7 | N1 (fixnum template) then E1 + E2 |
| 12 | Generic equality (`kernel-exact-equal?` from `k-eqv`) | 1.6 % | 1.8 / 1.6 / 1.8 | E6 / E1 |
| 13 | Run-time keyword interning (`bl-key`: 377k calls, mostly host code such as `native-multi-callable?` and `native-raw-map-has?`) | 0.4 % self | — | N1 + V2a |
| — | `h-tick` | < 0.1 % self, 4.55M calls | — | N4 |

Items 3 and 5 share one call site. `compiler/compile-node` asks
`(contains? special-forms name)` for every node, which **rebuilds** the quoted
set and then classifies it with `kind-kind`, which materialises it again.
Together that is **about 21 % of the native pipeline (25 % of compile)**.

### Native counts (counting pass, one round)

| Phase | host calls | linked-slot calls (arity / generic `$g` / variadic) | leaf calls | `h-tick` (= BL function entries) |
| --- | --- | --- | --- | --- |
| read | 3,044,758 | 307,566 (307,566 / 0 / 0) | 22,052 | 464,312 |
| compile | 32,543,665 | 2,589,414 (2,310,559 / 243,366 / 35,489) | 334,180 | 3,108,250 |
| emit | 6,638,509 | 864,075 (700,440 / 163,611 / 24) | 49,255 | 978,052 |

Host calls by category in compile: map 11.56M, key-compare 5.64M,
call-dispatch 5.55M, tick 3.11M, arith 2.68M, keyword-build 1.15M, text 0.79M,
equality 0.65M. Map and comparison counts across the pipeline:
`bl-key-compare` 1,985,492; `native-scalar-string-compare-from` 1,758,797;
`native-colon-symbol?` 1,110,514; `native-tree-find` 752,303;
`native-tree-put` 562,896; `kernel-exact-equal?` 516,102.

**Kernel fast paths** (`rt` function → calls → fallthroughs to the
`kind-kind` classifier):

| Function | Calls | Classifier fallthroughs | Fast-path hit |
| --- | --- | --- | --- |
| `k-first` | 73,461 | 0 | 100 % |
| `k-nth` (2) | 92,433 | 0 | 100 %, but `nth` → `k-nth` → `lists-at` → `nth-list` is 4 calls and 4 ticks per list access |
| `k-count` | 30,014 | 0 (but 9,987 go to `k-count-classified`, then grapheme `String.length`) | 100 % |
| `k-empty?` | 15,334 | 0 | 100 % |
| `struct-of?` | 49,429 | 0 | 100 % |
| `k-eqv` | 474,548 | 0; every call reaches `kernel-exact-equal?`, half also `kernel-colon-symbol?` | — |
| `coll-contains?` | 14,234 | 14,234 | **0 %** |
| `coll-assoc` | 14,079 | 14,079 | **0 %** |
| `k-count-classified` | 9,987 | 9,987 | 0 % |
| `call-set?` | 7,214 | 7,214 | 0 % |
| `coll-get` (3) | 2,968 | 2,968 | **0 %** (N2) |
| `k-fold` | 2,963 | 2,963 | 0 % |
| `k-seq` | 2,371 | 2,498 | 0 % |
| `call-invoke` | 8,703 | 2,788 | 68 % |

Inline BIF templates that fell through to a host `kernel-leaf-*` in compile:
`is-map-key` from `kind-kind` 29,588; `maps-put` from `coll-assoc` 10,385;
`is-function2` from `rt/step` 10,366 and `compat-reduced?` 8,134; `map-get`
from `kind-kind` 8,472. `rt/eqv` is reached through `bl-invoke` 159,570 times
in compile (`=` passed as a value).

## BEAM ranking (snapshot run, share of profiled µs, whole pipeline)

| # | Cost | Share | read / compile / emit | Calls | Roster item |
| --- | --- | --- | --- | --- | --- |
| 1 | Var-invocation gate: `rt/source-invocation!`, `call-invoke`, `invoke`, `Env/ns_ready?`, `Loader/ensure_ready`, `persistent_term/get`, `atomics/get`, `Env/own-module`/`fetch!`/`chain`/`current_epoch` | **17.2 %** | 0.4 / 7.4 / **34.4** | 6.65M | N3 (sealed direct links) |
| 2 | Generic equality `=` / `not=` (`rt/eqv` → `k-eqv`, `core/not=` → `rt/not_` → `call-not-`) | **11.1 %** | 0 / 10.1 / 14.6 | 8.27M | E1 + E6 (`eq?` for keyword/atom operands) |
| 3 | Other (Process dictionary reads, `core/elem`, `erlang/++`, `core/index-of`, `rt/cons`) | 9.5 % | | | — |
| 4 | Enum, lists and text BIFs | 9.4 % | 13.2 / 11.1 / 6.2 | 3.56M | — |
| 5 | Variadic constructors `core/tuple__bl_v`, `core/list__bl_v` + `list_to_tuple` | **8.9 %** | 9.8 / 5.0 / 14.2 | 5.23M | E5 (inline; same root as native #2) |
| 6 | Key paths `coll-get`, `facade-get`, `hash-hash-key`, `coll-hash-key`, `hash_key` | **7.9 %** | 3.5 / 6.7 / 10.5 | 4.52M | Q3 (KEYS: guards per lookup), V2c |
| 7 | `nth`/`first`/`count` chains (`nth` → `k-nth` → `lists-at` → `nth-list`) | **7.8 %** | 0 / 13.5 / 1.0 | 5.21M | N2, on BEAM too |
| 8 | Compiler / ANF own code | 5.7 % | — / 10.3 / — | 1.20M | E5 |
| 9 | Reader own code | 4.7 % | 69.0 / — / — | 2.30M | V2e |
| 10 | Emitter own code | 3.5 % | — / — / 9.2 | 1.01M | C2 |
| — | `kind-kind` classifier | 3.2 % | | 2.16M | N2 |
| — | Source-file resolution, even inside the snapshot | 3.2 % (5.9 % of compile) | | 0.76M | FRONT follow-up |
| — | Env/Loader compile-time resolution | 2.7 % | | 0.61M | LINK |
| — | `inc`/`dec`/comparison helpers | 2.0 % | | 1.56M | E1 + E2 |

Without the snapshot, BEAM compile spends **46 %** on source-file resolution
(`raw/beam-bare-summary.json`). It is a cache miss, not a target property.

## What wave 2 should do first

1. **N1, hoisting quoted literals** (native ≈ 10 %; ≈ 12 % of compile). A
   `(quote #{…})`/`(quote {…})` body must become a module constant, as BEAM's
   literal pool does. Do it together with the **`:__struct__`-on-set fast
   path** (native ≈ 11 %), or the hoisted set still materialises on every
   `contains?`. Both come from one call site in `compile-node`, about 21 % of
   the native pipeline. The struct fast path is host-values behaviour, not
   layout, so it fits D1. It touches `native-map-fetch`/`native-raw-map-has?`
   for `set`/`vec`, which KEYS owns this wave: **request for integration**.
2. **Direct variadic and multi-arity calls** (native ≈ 12 %, 44 % of read;
   BEAM ≈ 9 % through the variadic constructors). Natively, link `core/tuple`,
   `core/list` and other known-variadic callees to their `$v` entry, or emit
   tuple/list construction inline. Stop routing them through
   `bl-invoke`/`native-resolve-call`. On BEAM, inline the variadic
   constructors in the front end. This is N3's direct-link machinery plus one
   N1 form.
3. **N3 on BEAM** (BEAM ≈ 17 %, 34 % of emit). The Var-invocation gate
   (`source-invocation!` + `ns_ready?` + `ensure_ready` + `persistent_term`) is
   BEAM's largest single cost on this fixture.
4. **V2a + V2c** (native ≈ 10 %, plus most of the 1.1M `native-colon-symbol?`
   tests): `eq?` keywords and hash maps.
5. **V2e** (native ≈ 10 %): byte text, so `subs`/`split-slash`/`count` stop
   being grapheme walks. A cheaper first step is for `compiler/split-slash` to
   use a byte or codepoint index rather than `core/subs`/`String/length`.
6. **N2** (BEAM ≈ 8 %, native part of #1): collapse `nth` → `k-nth` →
   `lists-at` → `nth-list`, and give `coll-get`/`coll-contains?`/`coll-assoc`
   a map/set fast path ahead of `kind-kind` (0 % hit today).
7. **E1 + E6** after these (BEAM ≈ 11 % equality; native ≈ 3 % arithmetic +
   1.6 % equality + part of #1's `rt/eqv`). A one-line fixnum fast path in
   `native-arith-*` is a cheap N1-sized preface.
8. **N4** is not where the time is: `h-tick` is 4.55M calls but under 0.1 % of
   native samples as self time. Its residual cost is the call itself, folded
   into the callers' self time (item 1).

## Requests

- **KEYS / integration**: a `:__struct__` answer for `set` and `vec` in
  `native-map-fetch` and `native-raw-map-has?` that does not call
  `native-struct-fields` (ranking item 3). Also, host helpers that build
  constant keywords per call (`(bl-key "__struct__")`, `(bl-key "$blfn")` in
  `native-multi-callable?`, `native-raw-map-has?`) should use hoisted
  constants.
- **BACKEND (N1)**: hoist `quote`d collection and keyword literals in
  `scheme.bl`. The 2,962 `kernel-special-forms-literal` calls per compile of
  reader.bl are the test case.
- **FRONT / LINK**: `Loader/resolvable?` misses its cache outside
  `with_declaration_snapshot` (46 % of bare BEAM compile). The emitted ANF also
  differs between targets on sibling calls (Var fetch natively, remote call on
  BEAM); P3 should make that difference disappear.

## Residual replicas

None introduced. MEASURE adds no Scheme that replicates a `.bl` file. The
observer only wraps and samples existing procedures.

## Risks and caveats

- **Attribution of compiled frames is reconstructed.** Return-point ids map to
  definitions by entry adjacency, and 551 calibration points confirm the
  direction. Inner lambdas, such as a `fn` passed to `map`, are charged to the
  definition whose id range contains them. In practice that is their lexical
  parent.
- **GC is not separated.** Gambit defers the heartbeat during collection, so
  GC time lands on the allocating procedure. Allocation-heavy buckets (2, 3, 5)
  include their GC.
- **Native and BEAM run different ANF** for 78 of 104 definitions (sibling
  calls; see the fixture section). Native compile and emit therefore include
  work BEAM does not do, and the reverse.
- **BEAM shares come from tprof `call_time`**, which charges a per-call tracing
  cost. Code made of many small calls (the gate, `nth` chains, `eqv`) is
  overweighted against BIF-heavy code. The ordering is reliable; the
  percentages are not exact.
- The BEAM ranking uses the `snapshot` run, which is the realistic one. The
  bare run is kept for the cache-miss finding. That makes two BEAM runs, one
  more than planned.
- The counting pass wraps 4,526 procedures with interpreted closures. Its
  counts are exact for that pass's output, which is byte-identical to the
  uninstrumented output. Its time is meaningless.
- Wave-1 work (KEYS, BACKEND N1/N2, FACTS, FRAMES) changes these numbers. The
  ranking is for the round-2 image `7c32ac57…` and SDK `v8jbl8q0…`.
- `./bin/bl realm stop` at the end caused the checkout launcher to prepare
  its toolchain once (job `job_a7b640812839fede`, succeeded). No realm was
  running.

## Files

- `prepare.py`, `native-attrib.scm.in`, `run-native.sh`: the native run.
- `beam-attrib.bl`: the BEAM run.
- `analyze.py`: rankings and buckets. `diff-emitted.py`: emitted-text
  comparison.
- `raw/`: `native-summary.json`, `native-counts.tsv` (all COUNT rows),
  `native-edges-top600.tsv`, `native-log-head.txt`, `native-preparation.json`,
  `beam-snapshot.log` (all PROF rows), `beam-snapshot-summary.json`,
  `beam-bare-summary.json`, `beam-bare-head.txt`, `emitted-diff.txt`,
  `emitted-sha256.txt`. Full stacks stay in the git-ignored `runs/`.
