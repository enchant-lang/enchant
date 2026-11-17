# Workstream ACTOR: actor corpus and cross-process lazy waits (item X)

Round 3, wave 1. Contract: [`../CONTRACT3.md`](../CONTRACT3.md). Branch
`native-r3-actor`.

## Decision: a force on a cell owned by another actor WAITS, on both targets

When a frame forces a lazy cell that another process (actor) is evaluating,
it blocks until the owner publishes, and gets the owner's outcome. This is
BEAM's behaviour, unchanged, and now the native behaviour too. The other
outcomes follow from the same protocol on both targets:

| Situation | Answer (BEAM and native) |
| --- | --- |
| owner parked inside the thunk, then completes | the waiter gets the value; the thunk ran once |
| two actors each force the other's running cell | `ForceError :recursive_force` in both (the wait-for cycle is found before blocking) |
| the owner's thunk raises | the waiter replays the owner's exact failure; the cell stays retryable |
| the owner dies while parked (`exit :kill`) | the waiter gets `ForceError {:force_owner_lost owner attempt}`; the cell is terminal |
| re-entrant force by the owner | `:recursive_force` (unchanged) |

Why wait rather than refuse:

1. **It is BEAM exactly.** BEAM already waits (`wait_for_attempt`,
   `join_attempt`, `receive_attempt` in `priv/host/lazy_seq.bl`). Refusing
   natively would make a correct BEAM program raise on native, and a native
   refusal could not be made to match BEAM without changing BEAM.
2. **Cycle detection stays sound.** Round 2 detects cycles at force time. A
   refusal would turn *every* cross-actor force into an error, including the
   ones that are no cycle at all; only waiting distinguishes a genuine
   wait-for cycle (raised) from contention (waited out). The wait-for walk
   (`wait_cycle?`) records `:bl_lazy_waits_on` before blocking, so of two
   actors that block on each other at least one sees the other's entry. That
   needs per-process dictionaries and `process_info` of another process,
   which the native side now provides.
3. **No replica.** The native wait is the compiled BL protocol itself. The
   host supplies only the actor runtime's own primitives (category d of
   CONTRACT2): no lazy policy is written in Scheme.

## What changed

### BEAM: `priv/host/lazy_seq.bl`, `receive_attempt` only

The DOWN clause selects by the monitor reference, not by the tag:
`[_down ref :process _own _reason] :when (== ref monitor)` (was
`[:DOWN ref …]`). BEAM posts `{:DOWN …}`, the native actor runtime
(`priv/lib/js/actor/runtime.bl`, `rt-notify-monitors!`) posts
`[:down …]`. Only the owner's death notice carries this fresh monitor
reference, so on BEAM the clause selects exactly what it did. No other BEAM
behaviour changes.

Ownership note: CONTRACT3 names "the cross-process wait/refuse path in
`priv/host/lazy_memo.bl`". That path lives in `lazy_seq.bl`
(`wait_cycle?`, `wait_for_attempt`, `join_attempt`, `receive_attempt`,
`owner_lost`); `lazy_memo.bl` has no wait code. I edited only
`receive_attempt` there and left `lazy_memo.bl` untouched.

### Native: `research/native-seed/host/native-memo.scm`

The compiled wait path used to stop at `Process/monitor`, which refused as
`native_unsupported` (round-2 LAZY Risk 3). Now these leaves are the actor
runtime's operations, looked up in `native.kernel` when called:

| Leaf | Native meaning |
| --- | --- |
| `Elixir.Process/monitor/1` | `native-monitor! :process pid` (bridges.bl → `rt-monitor`) |
| `Elixir.Process/demonitor/2` | `native-demonitor!` (honours `[:flush]`) |
| notifications of a publication (`native-memo-notify!`) | `native-send!` (was `(native-leaf "erlang/send/2")`, which no native image defines) |
| `erlang/is_pid/1` | `rt-pid?` when an actor runtime is loaded; otherwise the old answer (`false`) |
| `erlang/process_info/2` (`{:dictionary k}`) | self, or any **live** actor's dictionary; a dead or unknown pid answers `:undefined` and its dictionary is dropped |
| `erlang/get/put/erase`, `Process/get/put` | the **running actor's own** dictionary (`native-pdict` keyed by `h-self`); outside any actor (`self` nil, the compiler image) the single dictionary as before |

The `receive` in the compiled `receive_attempt` already lowers to the global
`rt-receive`, which an actor program defines (kernel definitions keep their
bare names). In the compiler image (no actor runtime, `self` nil) no cell can
run under another owner, so none of this is reachable there; if it were, the
calls refuse as `native_unsupported`, as before.

### Actor-corpus linker: `research/native-seed/src/native/proc-link.bl`

`build-project`'s module map now includes the closure's pinned host modules
(`:host-modules`, as `native.bootstrap` does). Without it the round-2
closure cannot link the original corpus at all (see below): its units record
generic modules (`Elixir.BeamLisp.Ns.Host.Ex-info`), while a `throw` lowers to
`BeamLisp.ExInfo/raise_payload` and a lazy call to `BeamLisp.LazySeq/force`.

It also drops a **pending tail source call** at every call into a prelude
body (`native-linked-external-call`, new in `host/host-proc-link.scm`). This
was a real native bug that the lazy test found. Prelude bodies are compiled
without source frames, so they never consume the pending call that the
source-frame caller set up. The next source-frame function they reach (the
actor runtime's `native-monitor!`, `rt-receive`, a callback or a lazy thunk)
took that entry as its own. In tail position it then *retired* the BL
caller's frame: `(receive [:go other] (force other))` returned
`native-monitor!`'s monitor reference straight out of `force`, which skipped
the wait. Only a tail entry is dropped. A non-tail entry is kept, so frame
attribution is unchanged, and the corpus's 23 trace rows stay identical (below).
The change applies only with `:source-frames?` on.

### New files (`research/native-seed/speed/actor/`)

- `prepare.bl`: compile one or more actor applications against a frozen
  closure through `proc-link`, as `corpus/prepare.bl` does, printing a refused
  link's ex-data (which `corpus/prepare.bl` hides).
- `lazy-actors.bl`: the native counterpart of the BEAM test, 17 checks in
  actor processes on the original actor runtime.
- `run-native.py`: runs a prepared program in the pinned gsi with
  `corpus/qualify.py`'s transport (frozen host, compiled `text.o1`). It can
  substitute this worktree's `native-memo.scm` for the frozen copy
  (`--memo worktree`), apply this change's `receive_attempt` DOWN clause to the
  frozen compiled `host.lazy-seq` (`--patch-down`: the two
  `(eq? X (string->symbol ":DOWN"))` tests become `(begin X #t)`, which is what
  the new wildcard compiles to), and compare labels, traces and the witness
  with round 1's oracle (`--oracle`).
- `memo-actor-check.scm`: host-level checks of the new native-memo plumbing
  (14 checks, with a stand-in `native.kernel` lookup).
- `test/bl/lazy_cross_process_wait_test.bl`: the four BEAM cases.

## The actor corpus: how it runs, and what round 3 sees

The "461 actor checks" are `research/js-actors/test.bl` running on the actor
runtime `priv/lib/js/actor/runtime.bl`. Its two **execution targets are
native (Scheme) and JavaScript (Node)**. BEAM does not run the corpus: it is
the producer. The pinned round-2 SDK compiles the corpus into a native program
(`corpus/prepare.bl` → `proc-link`) and builds the JavaScript bundle
(`corpus/prepare-js.bl` → `bl.js/build!`). Round 1 (`evidence/original-actor-corpus/qualification.json`)
ran the native side as a compiled ELF (`stage1-actors`, built by
`fixpoint*.py --compile-stage1-actors-only`, which agents may not run) and
compared it label-for-label with Node at default/17/41.

### Closure used

`out/actor-closure/` (gitignored) holds copies of the read-only round-2
artifacts: `prelude.scm`, `host.scm`, `leaves.json`, `text.o1`,
`text-addon.json` and `chunk-export.json` from `MAIN/NS/out/round2-build/`,
plus `partition.json` from `MAIN/NS/out/speed-closure-2/`. Their identity is the
same (`identity.json` artifact `a044bdb8…` in both). The copy is needed because
`corpus/prepare.bl` and `qualify.py` expect all of these files in one
directory.

### Results

| Target / run | Result |
| --- | --- |
| **JavaScript** (`corpus/prepare-js.bl` on the pinned SDK) | **Cannot be rebuilt.** `js.build: 12 unresolved name(s): in rt: leaf/atomics/get/2, leaf/persistent_term/get/2`. `rt.bl`'s `source-callable!`/`source-invocation*!` gate (commit 94f5adb90, 2026-11-16, on `main`) reads `persistent_term`/`atomics`, which the JS target has no leaves for. Not caused by this workstream. The round-1 JS oracle (`oracle.json`) is the reference below |
| **Native corpus link** with `corpus/prepare.bl`, before the proc-link fix | **Refused**: `unsupported source host dependency {:target "Elixir.BeamLisp.ExInfo/raise_payload/1", :caller "research/js-actors/test.bl", line 732}` (`throw`). corpus/prepare.bl prints no target; `speed/actor/prepare.bl` does |
| **Native corpus, default budget**: round-2 image as is (frozen host and prelude), gsi transport, after the proc-link fix | **461 PASS, 0 FAIL**, `js-actors: ALL PASS`. Ordered labels **identical** to round 1's oracle; the 23 EXIT-PARITY/SUP-PARITY/SUP-TRACE rows **identical**; witness budget `default`, cleanup all zero, witness is the last line |
| Same, with this change (`--memo worktree --patch-down`, linker with the external-call wrapper) | **461 PASS**, labels and traces identical to round 1, cleanup zero |
| **Native corpus, budgets 17 and 41**, gsi transport | **Not observable here**: gsi dies with SIGSEGV (exit −11) before finishing, with the frozen host and with this change alike, and with `ulimit -s unlimited` too. Output is buffered, so the logs hold 0 or 62 PASS lines (62 = up to `loop-50000`). Round 1 ran these budgets on the compiled ELF; that is the integration check (below) |

Differences from round 1: none in labels or traces where the run completes
(default budget). The differences in how the corpus can be run at all are: (a)
the JavaScript baseline no longer builds; (b) the original link needed the
`:host-modules` fix; (c) budgets 17/41 need the ELF, because gsi crashes. No
label was added, dropped or reordered, and no deadline or assertion was
changed.

### Cross-process lazy waits

| Check | Command | Result |
| --- | --- | --- |
| BEAM: new test + lazy suites (one VM) | `work run --memory 4G --timeout 1800 -- ./bin/bl --cold test test/bl/lazy_cross_process_wait_test.bl test/bl/lazy_clean_capture_test.bl test/bl/host_lazy_seq_test.bl test/bl/host_lazy_memo_test.bl test/bl/legacy_wave23_lazyseq_test.bl test/bl/lazy_pressure_cycles_test.bl` | **6 files green**: lazy_cross_process_wait 18, lazy_clean_capture 21, host.lazy-seq 207, host.lazy-memo 19, legacy.wave23.lazyseq 64, lazy.pressure-cycles 37 |
| Native host: existing memo fixture | gsi over `host.scm host/host-values.scm host/host-leaves.scm host/host-extra.scm host/native-memo.scm fixtures/native-memo-check.scm` (check-host.py's composition) | `native memo checks: 27` (unchanged count) |
| Native host: new plumbing | same composition + `speed/actor/memo-actor-check.scm` | `memo actor checks: 14` |
| Native actors, this change (`--memo worktree --patch-down`) | `run-native.py out/actor2/lazy-actors/program.scm out/actor-closure --memo worktree --patch-down` | **17 PASS, 0 FAIL**: parked owner → value, thunk ran once, memoised; two-actor cycle → `:recursive_force` in both; owner's thunk raises → waiter replays `"owner crashed"`, retry recovers; owner killed → waiter gets `{:force_owner_lost owner attempt}`, no wait entry left, cell terminal |
| Native actors, round-2 behaviour (`--memo frozen`) | same with `--memo frozen` | 6 PASS, 11 FAIL: every waiter gets `{:native_unsupported "Elixir.Process/monitor/1"}`, and one cycle actor never replies. This is the refusal LAZY's Risk 3 predicted |

Before the external-call fix the same native run failed the cycle (both actors
`[:ok [:ref 1 1]]`) and, with `contains?` on the native exception struct, the
kill classification. A gsi trace of the memo NIF calls located the cause.
`lazy-actors.bl` now classifies with `get`.

## Commands (reproduce)

All from the worktree root; every VM or gsi run under `work run` (shared-queue
waits exceeded 1800 s several times, so the later runs used `--timeout 5400`,
which includes queue time).

```sh
# closure copy (read-only sources)
C=research/native-seed/out/actor-closure; M=$MAIN/research/native-seed/out
mkdir -p $C; cp $M/speed-closure-2/partition.json $C/
for f in prelude.scm leaves.json host.scm text.o1 text-addon.json chunk-export.json; do cp $M/round2-build/$f $C/; done
# compile corpus + lazy actors (one pinned-SDK VM)
work run --memory 4G --timeout 5400 -- research/native-seed/run run research/native-seed/speed/actor/prepare.bl -- \
  $C research/native-seed/out/actor2 research/js-actors/test.bl research/native-seed/speed/actor/lazy-actors.bl
# run (gsi), e.g.
R=research/native-seed/speed/actor/run-native.py; O=research/native-seed/out/actor2
ORACLE=research/native-seed/evidence/original-actor-corpus/oracle.json
python3 $R $O/test/program.scm $C --memo frozen --budget default --oracle $ORACLE
python3 $R $O/test/program.scm $C --memo worktree --patch-down --budget default --oracle $ORACLE
python3 $R $O/lazy-actors/program.scm $C --memo worktree --patch-down
```

## Integration (main thread)

The image must be rebuilt for the native half to be real: the frozen
round-2 image still holds the old `native-memo.scm` and the old compiled
`receive_attempt`. Once, at integration:

1. Rebuild the integrated SDK/closure/image with this branch's
   `priv/host/lazy_seq.bl`, `NS/host/native-memo.scm`,
   `NS/host/host-proc-link.scm`, `NS/src/native/proc-link.bl`.
2. Corpus at all budgets on the ELF:
   `research/native-seed/run run research/native-seed/corpus/prepare.bl -- NEW-CLOSURE research/native-seed/out/original-actor-corpus`,
   then `fixpoint-full.py --compile-stage1-actors-only --actor-manifest research/native-seed/out/original-actor-corpus/manifest.json …`,
   then `python3 research/native-seed/corpus/qualify.py --native-only --native-executable …/stage1-actors --native-build …/stage1-actors-build.json`
   for default, 17 and 41 (observed-not-qualified, because the JS baseline does not build; see Requests),
   and compare its labels and traces with `evidence/original-actor-corpus/oracle.json`
   (`run-native.py --oracle` does that comparison on a gsi run).
3. Lazy actors on the new image without the test-only patches:
   `speed/actor/prepare.bl -- NEW-CLOSURE OUT research/native-seed/speed/actor/lazy-actors.bl`, then
   `run-native.py OUT/lazy-actors/program.scm NEW-CLOSURE` (no `--memo worktree`, no `--patch-down`): expect `LAZY_ACTORS 17 0`.
4. BEAM: the test batch above (already green on this branch).

## Requests

- **Main / whoever owns `rt.bl`'s Source gate:** the JS core build fails on
  `persistent_term/get/2` and `atomics/get/2` (commit 94f5adb90). The original
  actor corpus cannot be qualified (native vs JS) until JS gets these leaves or
  the gate is target-conditional.
- **CLOSURE / check-host.py owner:** add `speed/actor/memo-actor-check.scm` as a
  check-host step (`memo actor checks: 14`), with the same composition as the
  memo fixture.
- **FRAMES (host-source-frames.scm):** the dropped-tail-entry rule now lives at
  proc-link's prelude-call boundary. If FRAMES prefers it in
  `bl-with-source-frame`/`bl-invoke` instead (for example "an entry is consumed only by
  the callee it was made for"), move it there and delete
  `native-linked-external-call`. Packed (`__bl_v`) prelude calls
  (`native-linked-packed-call`) do not drop it yet.

## Residual replicas

None. No lazy policy is written in Scheme: the wait, the cycle walk, owner loss
and replay are the compiled `lazy_seq.bl`. `native-memo.scm` adds only
actor-runtime primitives (monitor, demonitor, send, `is_pid`, per-process
dictionaries, `process_info`), and each one forwards to the compiled
`native.kernel` runtime.

## Risks for integration

1. **Per-process dictionaries natively.** `erlang/get/put/erase` and
   `Process/get/put` now act on the running actor's own dictionary. This is
   BEAM semantics, but a native actor program that relied on one shared
   dictionary across actors changes behaviour. Outside actors (compiler image)
   nothing changes. A dead actor's dictionary is dropped only when a
   `process_info` asks about it. Dictionaries of dead actors that nobody asks
   about stay in the table (a leak bounded by the number of pids that used the
   dictionary).
2. **`erlang/is_pid/1`** answers `true` for `[:pid runtime n]` when an actor
   runtime is loaded (it was always `false`). Prelude code that branches on
   `is_pid` inside actor programs sees actor pids as pids now.
3. **The `receive_attempt` DOWN clause** matches any 5-tuple whose second element is
   the fresh monitor reference and whose third is `:process`. On BEAM only the
   monitor's DOWN carries that reference.
4. **Not run on the ELF / not at budgets 17 and 41.** The native evidence is
   gsi plus the two test-only substitutions above. The rebuilt image may still
   differ (for example compiled-code inlining of the leaves this change replaces;
   `native-replace-leaf!` updates the `lv_` bindings, which compiled code
   reads at call time, as the trace run confirmed for gsi).
5. **The external-call wrapper changes emitted bytes** of every actor program
   (1,032 resolver lambdas in the corpus program, 423 in lazy-actors). Corpus labels and traces
   are unchanged at the default budget; 17/41 were not observed (see 4).
6. `memo-actor-check.scm` stands in for `native-fetch-value`; the real Env
   lookup is exercised only by the actor program runs.
