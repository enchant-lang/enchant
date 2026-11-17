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

### New files (`research/native-seed/speed/actor/`)

- `prepare.bl`: compile one or more actor applications against a frozen
  closure through `proc-link`, as `corpus/prepare.bl` does, printing a refused
  link's ex-data (which `corpus/prepare.bl` hides).
- `lazy-actors.bl`: the native counterpart of the BEAM test, 21 checks in
  actor processes on the original actor runtime.
- `run-native.py`: runs a prepared program in the pinned gsi with
  `corpus/qualify.py`'s transport (frozen host, compiled `text.o1`), optionally
  substituting this worktree's `native-memo.scm` for the frozen copy, and
  optionally comparing labels/traces/witness with round 1's oracle.
- `memo-actor-check.scm`: host-level checks of the new native-memo plumbing.
- `test/bl/lazy_cross_process_wait_test.bl`: the four BEAM cases.

RESULTS_PLACEHOLDER
