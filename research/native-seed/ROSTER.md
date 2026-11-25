# Native compiler roster

The goal, as re-scoped on 2026-11-23: `bl` is fast to build and to use, cold and
hot. An unchanged request costs a few ms. An edit costs in proportion to what it
changes. An SDK edit is bound by the pipeline, not by recompiling everything. The
native-compiler path is parked after N0; see `ROSTER-revisit.md`.

This file holds only open work:
- finished cards, batch notes and dropped prototypes are in `ROSTER-archive.md`;
- results that missed their target and wait for a second round are in `ROSTER-revisit.md`.

Status: ✅ done (passed the integration gate) · 🧪 branch ready, waiting for the gate · 🔨 in progress · ⏳ ready to take · 🔒 waits on another card · 🅿️ parked.
The journal (`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`)
holds the reasoning, and `research/checked-tiles/evidence/` holds the measurements.

## Where it stands (2026-11-25, main after batch 29)

| What a user waits for | Now | Was (2026-11-23) | Next |
|---|---|---|---|
| Warm `./bin/bl run` in this checkout | 6.6 ms; `.bl/bin/bl` 4.7 ms (load ~5) | 25 ms | 2 ms (F3, revisit) |
| Warm or cold **installed** `bl` | still October's drop (`/nix/store/jqb3a1d6…-bl`): none of the gains below have shipped | — | R1: v2026.12 |
| Cold `bl run` | ~1.05 s | 2.56–2.77 s | 0.8 s (init, revisit) |
| `./bin/bl --cold` over the SDK's own | +55 ms | +570 ms | — |
| Body edit, then `bl test` (`m1.py`) | ~300 ms; ~240 ms with E1 (batch 30) | 448–500 ms | 200 ms (revisit) |
| `priv/lib` edit, then the next command | 850–936 ms | 1.1–1.5 s | ≤ 600 ms, then 400 (L1) |
| First command in a fresh checkout VM | ~6.1 s | 5.8 s | `--cold` (M3b, revisit) |
| SDK after a `priv/host` comment | 611–670 s (668/668 units restored) | ~2,500 s | ≤ 3 min dev SDK (N4d) |
| SDK after a `priv/boot` edit | ~1,720 s | 2,967 s | N4d, then per-unit cutoff |

The one rule behind every card: a cost should scale with what changed, not
with the size of the tree, the SDK or the compiler.

## The plan (2026-11-25)

Order chosen on 2026-11-25:
1. Ship what main has (v2026.12). Batch 30 found a fresh-VM stall at its gate, so it waits for the next release.
2. Make SDK edits cheap to try (N4d). Every later host or boot card, and every
   revisit, waits on a 30–40 minute gate until then.
3. Take the library edit, the largest edit cost a user still notices.

| Order | Card | Done when |
|---|---|---|
| 1 | **B30** E1 + T5 + W4 (gate 30: fresh-VM stall, not merged) | No `first-in-fresh-vm` row slower than main, interleaved |
| 2 | **R1** Release v2026.12 | Installed `bl` is v2026.12, remeasured warm and cold |
| 3 | **N4d** Dev SDK outside QEMU | A `priv/host` edit runnable in ≤ 3 min |
| 4 | **L1** A library edit costs its compile | `m1.py` `lib/first` and `lib/repeat` ≤ 600 ms median (then 400) |
| — | Revisit round | Entries in `ROSTER-revisit.md`, after N4d |

## How a card gets done: work, check inside, one integration gate

An agent does the whole card and checks it right where it works, in seconds to
a few minutes. It never waits on an SDK build. **The integrator (the session
that fanned the cards out) merges finished branches in batches, builds one SDK
per batch, and runs the gate tests.** A card is ✅ only after that gate.

### Where an agent works
- **At most two lanes at a time, each time-boxed to about 3 hours.** The account
  runs two `work run` jobs at once, and the gate needs one of them. A third lane only
  queues. Each card states its measurement. If the first measurement misses the target
  by a wide margin, the agent reports back instead of searching on. Batch 30's lanes
  ran 16 hours each and still came back partial.
- **In its own git worktree** on its own branch, never the shared checkout, and **never
  `git checkout` a branch in `$MAIN`**. On 2026-11-23 an agent checked its branch out there, and
  six landed batches went onto that branch instead of `main` (recovered by fast-forwarding).
  Commit there freely, and finish with a clean, committed branch.
- **Checks that don't change engine inputs:** prefix `$MAIN/bin/bl` with `BL_SDK_REUSE_CURRENT=1`, so they run on the current SDK instead of queueing behind a rebuild of a moving main.
- **Never run the worktree's own `./bin/bl`.** It would prepare a whole SDK for
  that tree (~14 min on the 4-CPU build station, which is shared). Use the main
  checkout's client against the main SDK:
  `MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol` and
  `$MAIN/bin/bl ...`.
- **Run every check through `work run --memory 4G --timeout S -- ...`.** The
  queue allows two running checks for the whole account, shared with every other
  agent on the station. A check can wait 20 minutes before it starts (seen
  2026-11-22), so:
  - batch: one `work run -- bash -lc 'cargo test && cargo build'`, and one
    `bl test a.bl b.bl c.bl`, never one check per file;
  - set `--timeout` to cover the queue wait too (1500–2400);
  - read the code while a check waits; don't poll it.

  Don't use 6G; it's refused.
- **Don't touch** `priv/lib/scenario.bl`,
  `test/bl/scenario/browser_world_verdict_test.bl` or `research/field-station/`.
  Delete only by explicit path; `rm` inside `bash -c` is blocked.
- **Stop VMs you start.** Use `$MAIN/bin/bl realm stop` from the directory
  that started one.

- **Retained worktrees (2026-11-25).** `.claude/worktrees/integration` is the integrator's gate tree. Lanes `lane-e1`, `lane-t5` and `lane-m3b` retire after batch 30, but branch `lane/m3b` is kept for `ROSTER-revisit.md`. N0 kept its own data in `~/.cache/n0/d` (744 MB), which can be deleted. `git worktree list` also shows `.claude/worktrees/sdk-lock-wait` (locked) and four `~/projects/enchant-*` worktrees, which belong to other sessions; leave them alone.

### The inner loop, per tree (measured 2026-11-22)

| You changed | Check it inside, like this | Cost |
|---|---|---|
| `research/native-seed/src/native/*.bl` (compiler or emitter source) | `cd $WT && QUALIFY_ROOT=$WT work run --memory 4G --timeout 900 -- $MAIN/bin/bl run research/native-seed/chez/qualify.bl -- candidate --image $MAIN/research/native-seed/out/chez-main --out OUT --source-root $WT [--codegen]` | tens of seconds; first run of a new stage ~1 min |
| `research/native-seed/host/*.scm` (native host) | the same, with `derive --image $MAIN/research/native-seed/out/chez-main --out OUT` | the same |
| any native speed claim | `... -- pair --base $MAIN/research/native-seed/out/chez-main/prelude.scm --cand OUT/prelude.scm --out OUT2 --reps 8 --rounds 8` | a few minutes |
| a native behaviour | `... -- eval --image OUT --file CHECK.bl` runs a BL file on the native image | seconds |
| `tooling/drop/` (Rust client) | `cd $WT/tooling/drop && CARGO_TARGET_DIR=$WT/.cargo-target work run --memory 4G --timeout 1500 -- nix shell nixpkgs#cargo nixpkgs#rustc nixpkgs#gcc --command cargo test --release` | 66 s cold, seconds warm |
| `priv/host/*.bl` (runtime host: aot, env, loader, reader …) | `cd $WT && work run --memory 4G --timeout 1800 -- python3 scripts/check-runtime-hosts --sdk-image "$(readlink -f $MAIN/.bl/sdks/current-sdk)/image" --work-dir /tmp/hc-$USER-NAME test/bl/ONE_test.bl ...`. It builds `.#erlang .#elixir` itself (cached), compiles only the edited host files with the SDK's compiler, and runs the tests in a capped VM on those beams. It checks host behaviour; it is not a compiler-floor or SDK qualification, and `priv/lib` edits are not seen (the image's library stays the SDK's). **It does not run the pinned-host emitter**, so a host module it accepts can still be refused by an SDK build — see the rule below. | `js_local_shadow_test.bl`: 40 s with hosts unchanged (14 s in the VM); 192 s after editing `env.bl` (compiling it takes ~2.5 min), and the break was caught: 3 of 5 assertions failed, exit 1. A `work run` may first wait in the queue |
| client speed or behaviour | run the binary cargo built, the way `bin/bl` does: `$WT/.cargo-target/release/drop-launcher --checkout $MAIN -- run /tmp/x.bl`, with `BL_CHECKOUT_PLATFORM`, `BL_BIN` and the rest exported as in `$MAIN/bin/bl` | ms |
| a BL file the coordinator or a script runs directly (`nix/*.bl`, `scripts/*.bl`, `research/**.bl`) | `$MAIN/bin/bl run FILE ...` or a test file next to it, on the main SDK | seconds |
| `priv/lib` and most `priv/std` code | **Hot path (U15, batch 21):** in a checkout, `./bin/bl` compiles a changed library file inside the warm VM under the SDK's module names; the next request sees it in about 1 s. Held back, still needing an SDK: the 7 compiler-key `priv/std` files, `priv/std/vm/**`, `bl/daemon.bl`, `bl/cli.bl`, `bl/dev-overlay.bl` (list: `nix/dev-reload.json`). A new or deleted library file, a macro already expanded elsewhere and a captured `def` value need an SDK. `BL_CHECKOUT_DEV_OVERLAY=0` turns it off. | about 1 s |
| `priv/boot`, `priv/host` | **No hot path:** check host logic with `scripts/check-runtime-hosts`; the real check is the integration gate | the gate |
| measurement only | `work run` the probe with 3+ runs; report median and spread and the machine load (`uptime`) | — |

`scripts/check-runtime-hosts` is meant for host checks without an SDK, but it
is stale: it needs Elixir on `PATH`, and the flake has no dev shell. Fixing it
is card T1.

**Pinned host modules carry only top-level `defn`s.** `priv/host/aot.bl`
(`pinned_unit_descriptor`, ~line 848) refuses a host unit holding any value
definition: `pinned host module BeamLisp cannot yet carry value definitions
(host.beam-lisp); only top-level defns are emitted`. A constant is a `defn-`
returning it. `scripts/check-runtime-hosts` compiles the file and passes, so
this costs one SDK build to find (batch 17: generation P failed at
`host.beam-lisp` after 20 units). Before handing back a `priv/host` edit, run
`grep -n "^(def \|^(def \^" priv/host/*.bl`; the only hits should be none.

**The producer's own entry point runs on the installed floor.** Generation B
runs `produce.exs` through `priv/host/beam_lisp.bl`'s `run_file` using the
compiler of the floor that was already installed. A new boot function called
from there (batch 17: `BeamLisp.Compiler/eval_string_forms/3`) is undefined on
that floor and fails the build with `UndefinedFunctionError`. Guard a new call
whose absence is acceptable with
`(erlang/function_exported :Elixir.BeamLisp.Compiler :name arity)` and keep the
old path; the file's first use of `assert_native_framework_execution!` is the
precedent.

**`BeamLisp.Compiler` is the host facade, not the boot compiler.** The
public module is `priv/host/compiler.bl` (`host.compiler`, ~25 exports), and
each function forwards to `BeamLisp.Ns.Compiler` (`priv/boot/compiler.bl`). A
new boot compiler function is invisible to `BeamLisp.Compiler/...` callers and to
`function_exported` checks until the facade forwards it (batch 17: U12a's guard
was always false, so every run compiled; only an SDK-built check showed it).
Add the forward in the same change.

**`$MAIN/bin/bl` roots its realm at the current directory's tree.**
- Started from a worktree whose engine inputs differ from main's, it prepares
  that tree's own SDK. Even with `BL_SDK_REUSE_CURRENT=1`, the warm VM did not
  become ready.
- `nix/*.bl` counts as such an input.
- The preparation is a detached `bl-checkout-*.scope` plus a
  `foundry-artifact-job_*.service`, and both outlive the `work run` unit that
  started them. Stop them with `systemctl --user stop`.
- To test a changed `nix/` or `scripts/` BL file against main's SDK, run from
  `$MAIN` and point the test at your tree with `BL_TEST_SOURCE_ROOT=$WT`, or
  hand it to the integrator.

**A failed SDK preparation's message shows the error chain, not its leaf.** U3
reports the first three `error:` lines, which for a Nix dependency failure are
all `Cannot build '<drv>'.` The cause is higher in the same events file, e.g.
`{:artifact-failed host.beam-lisp}` followed by the producer's own
`** (ArgumentError) …` lines. Read
`.bl/sdks/<fp>/job-*/foundry-state/ledger/events/<job>.jsonl` and look near the
first failure.

### What an agent hands back
1. A branch name, with each commit message ending in the attribution line the
   harness gives you.
2. What changed and why, in two or three sentences.
3. Inner-loop results: exact commands and their outputs (numbers, gate counts,
   test counts).
4. **Gate tests:** the test files the integrator must run on the integration
   SDK, and what each should show.
5. Anything left undone, and why.

Numbers in "Done" rows are measured, never estimated.

### The integration gate (integrator only)
For each batch:
1. Merge the branches into `main`. First `git -C $MAIN branch --show-current` must print `main`;
   after, `git -C $MAIN log --oneline -1` must show the merge.
2. Run `work run --memory 4G --timeout 3000 -- scripts/prepare-checkout-sdk`, then
   **`./bin/bl realm stop`** on that tree before the gates. A warm realm started before the rebuild
   keeps the old SDK modules, and a gate on it reports errors (undefined functions, a keyword
   called with six arguments) that do not exist on the rebuilt image.
   Only when `priv/`, `nix/`, `scripts/`, `bin/`, `native/` or `tooling/drop/`
   changed. The two most recent runs took 862 s and 1301 s.
3. Run every gate test the cards named, in one `./bin/bl test a.bl b.bl ...`.
4. Run `qualify.bl -- qualify` for a new native base image, then make it the
   next `chez-main`.
5. Mark the cards ✅ with the measured result.

If a gate fails, the card goes back to 🔨 with the failure.


## Cards

Suggested model per card: **H** = Haiku can do it from this text; **S** =
Sonnet; **S+** = Sonnet with a long budget, or Opus.

#### B30 🔨 Batch 30: E1, T5 and W4 · not merged: the first command in a fresh VM stalls · integrator
- **Gate 30 (2026-11-25, SDK `ynjnpx9x`, prep 1,819 s, load 13–17).** Every test passed:
  - the E1 and T5 files: 11 files;
  - `sdk_loading_batch` in all three placements;
  - five rounds of 4-way `seed_*_abi` in one realm, with 0 failures;
  - the M2 tests, the ten files in both orders, and the "more" group;
  - all four scripts.

  `m1.py`: `warm/test` 87 ms, against 135 ms on batch 29. `body/first/test` 310 ms, level with batch 29 (306). `lib/first` 1,052 ms, against 936.
- **Blocker.** `first-in-fresh-vm/test` regressed intermittently. An interleaved A/B (`realm stop`, then `bl test scene/frame_plan_test`, load 13–15) against a private copy of main on the batch-29 SDK:

  | Run | 1 | 2 | 3 | 4 | 5 | 6 |
  |---|---|---|---|---|---|---|
  | batch 29 (ms) | 8,725 | 5,661 | 5,410 | 4,973 | 5,067 | 5,462 |
  | batch 30 (ms) | 24,260 | 9,567 | 5,882 | 4,785 | 10,088 | 22,343 |

  `m1.py` gave 5.7, 7.8, 18.7, 10.6 and 53.9 s. Client phases are about 9–15 ms, so the stall is inside the VM. `--cold` rows are normal (cold test about 3.6 s).
- **Suspects.**
  - T5's lease change (`env.bl` `sdk_runtime_inventory_cached!`).
  - W4's two-identical-answers path in `sdk_declaration_kind`, which has a 5 s deadline. Several queries would add up to stalls of 10–24 s.
  - W4's `Link/forward`.
  - E1's one-pass test load (`d6a1ab316`).
- **Next.** Trace a stalled fresh VM on a copy of the integration tree, whose SDK is retained. Check for stalls in multiples of 5 s. Then fix the cause or drop the commit. Do this before the next gate.
- **E1 (`d6a1ab316`).** A test file loads as one declaration pass.
  - Body edit then test: 300 → 239 ms.
  - Unchanged warm test: 115 → 67 ms.
  - The rest of E1 is in `ROSTER-revisit.md`.
- **T5 (`019b29a5e`, `b5adee25c`).**
  - `loader_path` no longer writes into the store SDK.
  - `sdk_loading_batch` was intermittent because its check takes a warm or a
    fresh-VM branch depending on what ran before.
  - The fresh-VM branch exposed a real bug: since K1b, a fresh VM's first lease
    walks the SDK twice. The fix is in `env.bl` `sdk_runtime_inventory_cached!`.
- **W4 (`746e5b99f`).** Two compiler states were shared between requests:
  - The `Link/forward` shim: a fork's own definitions now come first.
  - `sdk_declaration_kind` stability under code churn: two identical
    complete-unit answers are now accepted.
- **Gate.** The ten files, `session`, `realm_shared` and the M2 tests. Also the
  E1 and T5 tests and `sdk_loading_batch` twice plus once after
  `dev_sdk_overlay_test`. Five rounds of 4-way `seed_*_abi` in one realm, the
  overlay and transport scripts, and `m1.py --cycles 5 --cold 5`.

#### R1 🔨 Release v2026.12 · integrator
- **Why.** The installed `bl` is still October's drop, so nobody outside this
  checkout has the request floor, cold start, hot reload or SDK build gains.
- **Steps.**
  1. Freeze: no new lanes merge until the tag. N4d may run on its lane.
  2. Local CI: `python3 -m unittest discover -s scripts/tests`,
     `scripts/embed-test-library.py --check`, `scripts/check-public-evidence.py`.
     All passed on 2026-11-25. The red CI on `origin/main`
     (`consumer map drift`) is from 2026-11-18 and already fixed on main.
  3. Upgrade path: the October drop and the new one share `~/.cache/beam-lisp`.
     Run both, cold and warm, on one cache, in either order. Cache format changes
     use new file names; check that no old name is read by the new format.
  4. Dev-only switches: `BL_REALM_UNIT_RESTORE` and `BL_REALM_UNIT_TIMES` are
     documented. The U15 overlay is active only in a checkout, so confirm that the
     installed drop never reads `nix/dev-reload.json`.
  5. Changelog `docs/changelog/v2026.12.md`, in v2026.11's style, with numbers
     from evidence files.
  6. Push main, wait for green CI on the exact commit, then tag `v2026.12` and push
     the tag. `release.yml` runs its exact-runtime gates; `AUTO_RELEASE_ENABLED`
     stays `false`.
  7. Root deploys it (`intranet-deploy upgrade`).
  8. Remeasure the installed `bl`: warm `(println 1)` over 15 runs, and cold over
     4 runs, with the load recorded.
- **Done when.** Step 8 is recorded here.

#### N4d ⏳ A dev SDK outside QEMU: a `priv/host` edit runnable in ≤ 3 min · S+ · `nix/bl-drop.nix`, `priv/build/selfbuild.bl`, `scripts/prepare-checkout-sdk`
- **Where N4 stands.** N4a (restored units by reference), N4b (P boots the previous compiler; C elided), N4c (library-runtime key: 668/668 units restored on a host comment) and M4 are done; see the archive. A `priv/host` comment still takes 611–670 s. Almost all of that is the fixed pipeline: Nix evaluation and copying, P and B in a 4-CPU QEMU VM, and the library's fixed phases.
- **Change.** Give checkouts a dev SDK path that builds on Work, outside QEMU and outside the release pipeline:
  - compile only the edited host or boot units against the current SDK's compiler;
  - path-normalise their beams, so they are byte-equal to what the store build would make;
  - restore every library unit whose `library-runtime-key` holds;
  - assemble an image that `./bin/bl` can run.
  The release SDK is unchanged and stays the qualification. A dev SDK is never published; it is marked so that `release.yml` and the selection record refuse it.
- **Done when.**
  - A `priv/host/delay.bl` comment is runnable through `./bin/bl` in ≤ 3 min end to end, on a loaded host.
  - Its beams for unchanged units match the store SDK's byte for byte.
  - The ten files pass on it.
  - A `priv/boot` edit either works the same way or is refused with a clear message.
- **Background.** N4's measured breakdown (2026-11-23) lists where a one-file edit's 440 s goes, phase by phase, along with the pitfall that two layered SDKs in a row must both prepare. It is under N4 in `ROSTER-archive.md`. Read the full build log on the build station (`nix log`), not the 64 KB foundry events file.

#### L1 ⏳ A library edit costs its compile · S+ · `priv/host` (`aot.bl`, `env.bl`, `loader.bl`), `priv/std/bl/dev-overlay.bl` · after N4d
- **Why.** A one-function `priv/lib/scene/core.bl` edit takes 850–936 ms to show up in the next command, against about 300 ms for a project body edit. M4 removed the client stall and the full SDK inventory; E1's profile shows what is left:
  - OTP compile is 29%: about 60 `compile:forms` per edit, half of it in `beam_ssa_opt`.
  - `load_unit` is 14%. Each `defn` is compiled three times: an eval module, a per-defn body module and the final emit.
  - Recompiling the project units that depend on the library is 13%.
  - The inventory patch is 6%, `emit` 5% and `retain_sdk_runtime!` 4.4%.
- **Change.**
  - Compile each defn once: reuse the final emit and drop the throwaway modules, or compile them with fewer passes.
  - Restore the dependent project units through M2's key when their macro inputs did not change.
  - Patch the inventory's source-target map incrementally. M3b's split needs the same thing.
- **Done when.** In `m1.py` interleaved against main, `lib/first` and `lib/repeat` are ≤ 600 ms median over 5 cycles. Every edit's output is still seen (15/15). Stretch: 400 ms (M4's original target).
- **Inner loop.** Until N4d lands, each `priv/host` attempt needs a gate. Profile first with E1's sampler (`/tmp/e1-othman/prof/e1_sampler.erl`, stack depth 250), so that each SDK build tests a measured hypothesis.

## Scratch

| Tree | Owner | Removed when |
|---|---|---|
| `research/native-seed/out/chez-main` | base image for candidates and pairs (matches `main`) | replaced by the next qualified image |
