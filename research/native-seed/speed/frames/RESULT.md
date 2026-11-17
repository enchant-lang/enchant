# Workstream FRAMES (N4): budget sites and source frames

Branch `native-r3-frames`. Files changed:

| File | Change |
| --- | --- |
| `src/native/scheme.bl` (FRAMES functions only) | `function-entry`, `fixed-function`, `function-expression` (tick and site arguments only), `source-call`; new `site-symbol?`, `site-datum`, `frame-site`, `primitive-remote?`, `any-calls?`, `body-calls?` |
| `host/host-source-frames.scm` | rewritten: site statements, static site descriptors, explicit extent restoration; the thunk/`parameterize`/`call/cc` trampoline path is deleted |
| `host/host-values.scm` | frame base section only: the `native-logical-frames` parameter and the base `bl-with-source-frame`/`native-with-frame` are deleted; `native-source-frames`/`native-source-pending` are plain variables |
| `fixtures/host-source-frames-check.scm` | rewritten for the new site statements (15 checks) |
| `fixtures/host-values-check.scm` | the two checks of the deleted base frame wrapper now check that release keeps no stack (count stays 27) |
| `speed/frames/` | `corpus.bl`, `check.bl`, `harness.scm`, `run.py`, `job.sh`, `emit-units.bl` |

`emit-source-loop`'s loop-head tick is unchanged (it already is the back-edge tick).

## The budget rule

A turn budget is spent by `(h-tick)` at exactly two kinds of site:

1. **Loop back-edges**: the head of every lowered loop (named `let`), once per iteration. Unchanged.
2. **Entries of calling functions**: the entry of a function whose body can pass control to BL code. `body-calls?` decides this from the ANF. It walks the function's clauses, guards and pattern keys. It does not descend into nested `fn` bodies, because each of those is a function with its own decision. The body *can call BL code* when it contains:
   - an `:apply` or `:invoke`, including unknown callees, global Vars, `$blfn` dispatch and scaffold self-calls that are not lowered;
   - a `:recv` (`rt-receive` is BL);
   - a `:remote` whose module is a BL-compiled module (`Elixir.BeamLisp.*`), or any `apply`.

   Two things do not count as calls. The `recur` of a lowered loop is a jump. A loop is lowered when the verdicts say so, as `loop-plan` decides; in source-frame emission every loop is lowered. A remote to a host primitive, OTP or Elixir function (`erlang`, `lists`, `maps`, `Elixir.Enum`, `:host`, …) is not a call either.

A function that cannot call BL code (a *leaf*) pays no tick at entry. Whether its caller knows it statically makes no difference. The wrong-arity `case-lambda` arm never ticks, because it only raises. No tick is placed at call sites. A tick at an unknown call site is subsumed: the callee ticks at its own entry if it can call further, and if it cannot, its run is bounded.

### Why every non-terminating program still yields

Take an infinite BL execution inside a turn. Host leaves run finite work over finite data; lazy sequences are BL code, not host loops. So the execution performs infinitely many loop iterations or infinitely many BL function activations.

- **Infinitely many loop iterations.** Each one ticks at the loop head.
- **Infinitely many activations.** These form a tree in which each activation has finitely many children: an activation outside a loop makes boundedly many calls, and calls inside a loop are paid for by that loop's ticks. By König's lemma the tree has an infinite path, and every edge on it is a call into BL code.
  - The caller of such an edge contains a BL call, so it ticked at its own entry.
  - The callee is the caller of the next edge, so it ticks too.
  - Hence infinitely many ticks.

Between two ticks the work is bounded by code size. A non-ticking leaf contains no BL call and no un-ticked loop. A ticking function runs at most its own body plus calls into leaves before the next tick.

Host callbacks do not break this argument. When a host leaf calls a BL callback, the callback is either a calling function, which ticks at entry, or a leaf, which is bounded. The leaf itself iterates over finite data. The new set of tick sites is a subset of the old set (every function entry plus loop heads), and no site was added.

Checked with deliberately non-terminating programs in actor turns at budget 50, in both release and debug emission: `spin` (tail self-call), `spin-loop` (`loop`/`recur`), `ping`/`pong` (mutual recursion through globals), `grow` (unbounded non-tail recursion), `spin-self` (`(f f)` through unknown calls), `hof-spin` (a host leaf calling a spinning callback) and `spin-catch` (a spin inside `try`). Every one yields three turns in a row; a hang would fail the 120 s gsi deadline. Deep recursion (`deep 300`, `even-down? 301`) finishes at budgets 17/41/1000.

### Do turn counts per budget change?

Yes. Tick sites only disappear, so for any execution the number of ticks up to any point is ≤ before. At a fixed budget each turn therefore runs at least as far as before. Turn boundaries move later in the computation or vanish, and a computation needs ≤ as many turns.

Measured (TURNS = turns to finish one workload in an actor turn loop, TICKS = executed `h-tick` calls; old = round-2 emitter, new = N4):

| Workload | TICKS old → new | TURNS @17 old → new | @41 | @1000 |
| --- | --- | --- | --- | --- |
| `work 2000` (`sum-to`: a loop) | 2003 → 2002 | 118 → 118 | 49 → 49 | 3 → 3 |
| `work-calls 200` (recursion calling leaf `leaf-add`) | 401 → 201 | 24 → 12 | 10 → 5 | 1 → 1 |
| `deep 300` (non-tail self recursion) | 301 → 301 | 18 → 18 | 8 → 8 | 1 → 1 |
| `even-down? 301` (mutual recursion) | 302 → 302 | 18 → 18 | 8 → 8 | 1 → 1 |
| `tail-count 500` (tail self recursion) | 501 → 501 | 30 → 30 | 13 → 13 | 1 → 1 |
| `mapped (1..8)` (`lists/map`, leaf callback) | 9 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |

The release and debug programs give identical counts.

The loop-only, self-recursive and mutually recursive workloads keep their counts: every activation is a calling function, and every iteration is a loop head. Workloads that call leaves lose those leaves' ticks (`work-calls`: half the ticks, half the turns). On the compiler's own units, static entry ticks drop as shown below.

**What the actor corpus could notice** (`evidence/original-actor-corpus`, run by ACTOR only):

- The ordered PASS labels and the EXIT-PARITY, SUP-PARITY and SUP-TRACE lines are already required to be identical across the 17, 41 and default (200) budgets, and identical to JavaScript, whose budget counts generator steps rather than ticks. So they do not depend on where a turn boundary falls within that 12× range.
- N4 lowers the ticks per unit of work. Each budget now behaves like an equal or larger old budget. For 17 and 41 that stays inside the qualified range. For **default (200)** it moves beyond 200, which no run covers today.
- The virtual clock advances 1 ms per completed turn. Fewer turns mean that a deadline in virtual ms is reached after at least as much work as before.
  - Fallback timeouts are now reached later, or not at all: `(after 2000 :timeout)`, 3000, 30000, 100000.
  - "Settle" waits give peers at least as much progress: `(receive :life-tick (after 20 :life-waited))` (test.bl lines 294, 399, 404), `(after 30 :life-settled)` (440), `parity-settle` (517), and `r2 (receive :busy-done … (after 30000 :no-busy))` (219).
  - Only a check that needs a deadline to fire *before* a runnable peer finishes could flip. These are the lines above, in the default run.
- The witness requires `yield_turns > 0` at every budget. That still holds: the corpus runs 50 000-iteration loops (`trace-countdown`), and loop heads keep their ticks.
- `trace-tail-frames-bounded` and `(host/max-frames) < 1024` concern frames, not ticks (see below).

## Source frames from static site tables

Debug (`:source-frames?`) emission used to wrap every function body and every call:

- `(bl-with-source-frame (bl-map …) (lambda () …))` around each function body: a thunk, a `call/cc` boundary, three `parameterize`s and an exception catcher per entry, plus a trampoline through `call/cc` for each tail call;
- `(bl-source-call (bl-map …) tail? (lambda () call))` around each call: a thunk, two `parameterize`s and an exception catcher per call;
- the 10-key frame map was rebuilt at every execution.

Now:

```scheme
(bl-source-enter '#(#f |:arity| 1 |:call| |:direct| … |:line| 12 |:ns| "user"))  ; entry statement
(let ((source-entry (bl-source-call SITE))) (bl-source-return source-entry CALL)) ; non-tail call
(begin (bl-source-tail SITE) CALL)                                                ; tail call
```

- **The site is the emission table.** Each site is a constant quoted vector in the code: slot 0 is the `internal?` flag, then key/value pairs. Keys are the keyword symbols themselves (`|:line|` is `(bl-key "line")`), and nil is written `#!void`. The frame map is built only when a stack is observed (`h-logical-stack`, a raise). A value with no Scheme datum falls back to `#(internal? (lambda () map))`.
- **Tail calls stay Scheme tail calls.** No trampoline is needed, and the control stack of a tail loop is bounded by Scheme itself.
- **State.** The logical stack is a list of mutable records `#(site critical depth)` (`native-source-frames`). The pending call site is `native-source-pending`.
- **The JS semantics are kept**:
  - `srcs[caller]` restoration: a non-tail callee records the call site in its own frame, and the caller goes back to its entry site.
  - Tail replacement.
  - `internal` runtime-helper sites keep the caller's source.
  - Host-callable leaves give their callbacks a fresh frame on the leaf caller's stack, through a host marker.
  - Raw apply forwards the call.
  - Per-frame critical depth is restored on completion and on unwind.
  - `max-frames` is maintained in O(1) from the record depth.
- **Pending is not consumed by an entry.** Callbacks that core/rt release code makes (those functions have no sites) are still callees of the debug call site, exactly as under the old `parameterize`.
- **Extent is restored explicitly** where the parameters used to unwind: caller-side `bl-source-return`, host-callable calls (the `bl-invoke` override), `bl-try` catches (`native-source-unwind!`), `bl-guard`, `h-park` (resume restores the actor's stack) and `h-run-turn` (each turn starts empty, and the scheduler's stack comes back).
- **Host errors** are no longer converted at every frame boundary. They take their trace where they are caught (`bl-try`, `h-run-turn`), from the stack in force at the raise, which nothing has restored by then.

### One code shape

Release and debug now share the control structure. There is no wrapper, thunk or continuation in either, the tail positions are the same, and the tick sites are the same (the rule above). Debug adds straight-line site statements only. Three emission differences remain, all outside FRAMES's functions; see **Requests**:

- the `loop-plan` unchecked lowering under `:source-frames?`;
- `ordered-call`/`ordered-language-call` route debug calls through `bl-invoke`, so a host-callable target can get its marker;
- `emit-try`'s `bl-trace-frames` normalization (traces are `{raw, frames}` tuples in debug).

## Counts (static sites, emitted with the AOT link context of `native.chunks`)

Closure `out/speed-closure-2` (copied, read-only original), leaves `round2-build/leaves.json`, every `:fn` definition of the unit, `bootstrap/emit-definition` (release), plus the same definitions in source-frame emission:

Release emission (`bootstrap/emit-definition`, what stage 1 links):

| Unit | definitions | `(h-tick)` before → after | bytes before → after |
| --- | --- | --- | --- |
| `rt` | 468 | **1275 → 586** (−54%) | 942,687 → 936,486 |
| `reader` | 103 | **247 → 115** (−53%) | 391,967 → 390,779 |
| `reader-node` | 10 | **24 → 8** | 19,178 → 19,034 |

Source-frame (debug) emission of the same definitions:

| Unit | `(h-tick)` | entry wrappers `bl-with-source-frame` → `bl-source-enter` statements | call wrappers `bl-source-call` (thunk) → `bl-source-call` + `bl-source-tail` statements | per-call `(bl-map …)` frame builds | `(lambda () …)` thunks | bytes |
| --- | --- | --- | --- | --- | --- | --- |
| `rt` | 1275 → 586 | 1234 → 1234 | 3049 → 2162 + 887 | 4454 → 171 (code literals only; sites are constants) | 4286 → 3 | 2,217,228 → 1,481,811 |
| `reader` | 247 → 115 | 224 → 224 | 1453 → 1262 + 191 | 1681 → 4 | 1680 → 3 | 952,200 → 683,202 |
| `reader-node` | 24 → 8 | 24 → 24 | 38 → 23 + 15 | 62 → 0 | 62 → 0 | 33,544 → 22,497 |

Dynamic frame-parameter work per debug call: before, every call ran 2 `parameterize`s, one thunk, one catcher and one frame-map build, and every entry ran 3 `parameterize`s, `call/cc`, one catcher, one result vector and one frame-map build. After, every non-tail call allocates one 6-slot entry vector, every entry allocates one record and one pair, and a tail call allocates one entry vector. No `parameterize` and no `call/cc` remain.

## Checks

Commands (from the worktree root; every VM/gsi step inside one `work run`):

```sh
work run --memory 4G --timeout 1800 -- env UNITS=1 research/native-seed/speed/frames/job.sh
work run --memory 4G --timeout 1800 -- python3 research/native-seed/check-host.py --out research/native-seed/out/frames-host
```

`job.sh` does four things:

1. It runs `speed/frames/check.bl` twice on the pinned SDK, once with the old `scheme.bl` (`out/before-src`) and once with the new one.
2. It emits the 53 corpus definitions in release and debug emission.
3. It runs `emit-units.bl` for the counts.
4. `run.py` assembles four gsi programs (old/new × release/debug). The old programs use the pre-N4 host files of base commit 073fe16e8 (`git archive`); the new ones use this branch's host.

- **`job.sh` (job3, `FRAMES_JOB_EXIT 0`).**
  - `old-release`, `old-frames`, `new-release` and `new-frames` each give `FRAMES_CHECKS 72 FAILURES 0`.
  - Old == new on every observation line: 47 lines in release and 47 in debug.
  - Value probes against **BEAM** as the oracle: 20 equal, covering leaf, loop, deep, tail and mutual recursion, higher-order functions, `throw` from several depths, catch/rethrow, finally, a raise inside a higher-order function, and the wrong `case` clause. Two are informational, reported but not failed, and differ identically old and new: `badarith` and `erlang/error` both give the native ErlangError text, a host gap that predates N4.
  - Stack probes (logical stacks returned by `host/logical-stack`):
    - direct call chains with the tail caller elided;
    - a stack after a returned call;
    - 100-deep tail recursion (1 frame) and 5-deep non-tail recursion;
    - a higher-order callback;
    - `lists/map` callbacks, the same stack for each element;
    - a lowered loop;
    - multi-arity and variadic functions;
    - stacks inside a catch, a deep catch, a finally that throws, and after a catch;
    - raw `erlang/apply`.
  - Trace probes: the raw-trace frames of 9 raises, including host errors (`badarith`) and the inline `case clause` error. All byte-identical old vs new.
  - Preemption: the 7 non-terminating programs yield at budget 50 in all four programs.
- **`check-host.py --out out/frames-host`**: every stage passes (values-control with 27 checks, lazy-memo, storage-and-raw-leaves, source-frames with link 56, global-cache 48 and the 15 rewritten source-frame checks, then the POSIX/FFI build and worker).
- **Counts**: `emit-units.bl` with the old and new emitter (above).

## Requests

1. **BACKEND (`loop-plan`).** Drop `(:source-frames? options)` from the lowering condition, so that debug lowers exactly the loops release lowers. Before N4 the unchecked lowering avoided the per-call trampoline cost; that cost is gone. An unsafe loop would then run as calls, which is correct and has bounded tail stacks now. With this change, `body-calls?`'s `:frames?` flag can be deleted (`function-expression` passes it).
2. **LINK (`ordered-call`, `ordered-language-call`).** Once debug calls no longer need `bl-invoke`'s host-callable marker, use the release call shape in debug too. That needs a host-side alternative: mark leaf procedures so that their entry installs the marker. Until then the `:source-frames?` branches stay as they are.
3. **LINK (`bootstrap/remote-link`).** Add `:kind` (`:leaf`, `:template`, `:compiled`, `:self-module`) to link maps, so that `primitive-remote?` can treat `Elixir.BeamLisp.*` remotes that link to leaves or templates as primitives. Today they count as calls, which is conservative. Templates for `erlang/lists/maps` are already primitives by module.
4. **ACTOR.** Run the corpus at default/17/41 once with this branch's `host-source-frames.scm`, `host-values.scm` and `scheme.bl`. Watch the deadline-sensitive labels listed above, in the default run. `corpus/prepare.bl`'s guard `(String/contains? program "(bl-source-call ")` still holds: every non-tail debug call emits `(bl-source-call `.
5. **Main thread.** The integration build must re-emit everything. Release text changes wherever a function is a leaf, and debug text changes everywhere.

## Residual replicas

None added. `host-source-frames.scm` remains category (d) machinery (the actor/source-trace ABI).

## Risks for integration

- **Turn boundaries move**: fewer turns per unit of work at every budget (above). Code that relied on a leaf function's entry tick as a preemption point (a long host iteration over a huge list with a leaf callback) now yields only at the next calling entry or loop head. Host iteration is finite, but its granularity coarsens with the data size.
- **Stale stack after a callback returns into host or release code.** The old wrapper restored the leaf caller's stack when a callback returned. Now it is restored only when control returns to the debug call site. A host or release-code raise *after* a callback has returned, inside the same call, reports a trace with that callback's frame on top. Callbacks of host-callable leaves still get the right parent through the host marker, and raises inside callbacks are exact. No corpus frame check exercises this case; the trace-* checks raise through `throw` at a debug site.
- **Unbalanced critical sections inside callbacks.** The critical depth of a callback is restored when the enclosing debug call returns (or on unwind), not between two callbacks of the same leaf.
- **Captured host bindings.** The extent hooks are `set!` rebindings of `bl-invoke`, `bl-try`, `bl-guard`, `h-park` and `h-run-turn`. Any host code that captured the previous value before `host-source-frames.scm` loaded bypasses them. The old file had the same constraint for `bl-invoke` and `h-run-turn`; `h-park`, `bl-try` and `bl-guard` are new.
- **Analysis cost.** `body-calls?` walks each function body once (it stops at the first call, and nested functions are walked as their own). It recomputes loop verdicts for a loop region not already covered by `:loop-verdicts`, so the emitter does that region walk twice.
