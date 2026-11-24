# Native compiler roster

The goal: one self-hosted native compiler on Chez that `bl` uses by default.
No user-visible change. An unchanged request costs ~1 ms of fixed floor
(200× warm BEAM's 158 ms). An edit costs in proportion to what it changes,
when building `bl` and when using it, cold and hot.

Status: ✅ done (passed the integration gate) · 🧪 branch ready, waiting for the gate · 🔨 in progress · ⏳ ready to take · 🔒 waits on another card · 🅿️ parked.
The journal (`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`)
holds the reasoning; `research/checked-tiles/evidence/` the measurements.

## Where it stands (measured 2026-11-23)

| What a user waits for | Now | Target |
|---|---|---|
| Warm `./bin/bl run` in this checkout | 25 ms median (was ~82 ms on 2026-11-22) | ~1–5 ms |
| Warm installed `bl run` of `(println 1)` | unmeasured; the installed drop is still October's `f5ee4ce9` (`/nix/store/jqb3a1d6…-bl`) | ~1–5 ms, after R1 |
| Cold `bl run` (store SDK, after U8) | 2.56–2.77 s (`research/checked-tiles/evidence/cold-start-u8.json`); the checkout's own cold path is unmeasured | ≤ 1 s |
| Compile the reader file (read + compile + emit) | native ~117 ms median, warm BEAM 158 ms | only matters on edits |
| Try a one-file `priv/std` edit | 440 s (a full SDK; compiling is <10%) | seconds (U15) |
| SDK after a compiler edit / a Rust edit | 862 s+ (P/B/C ~1500 s more) / 82 s | ~1 min / ~1 min |
| Native compiler on the user path | **not yet**: 663/667 SDK units byte-identical on Chez, nothing calls it (N3) | the default compiler, BEAM kept as fallback |

The one rule behind every card: a cost should scale with what changed, not
with the size of the tree, the SDK or the compiler.

## The plan after the fresh review (2026-11-23)

An independent review read this roster against the code. Its main finding: **the native
compiler is not on any path a user waits on.** An unchanged request replays forms it already
compiled (U12a). A changed project file compiles in ~2 ms in the warm VM. A one-file std edit
is 440 s, under 10% of it compiling. The 158 ms "warm BEAM" baseline was the BEAM running the
native *emitter* on one file (BL → Scheme), which the product never runs. And the native front
end isn't measured faster on real units yet: 745 s for 666 units on Chez against 549 s for 662
on the BEAM (`research/checked-tiles/evidence/native-beam-backend.json`
`step3_corpus.timing_ms.beam_dump_662_units`), with different harnesses.

So the order is now: the request floor, the std/lib hot path, cold start, shipping, then the
build pipeline. The native compiler comes after a go/no-go measurement (N0).

| Order | Card | Done when |
|---|---|---|
| ✅ | **F1** One exec to the client (batch 21: 19.4 → 11.5 ms; gate 12 ms at load 21) | Warm `./bin/bl run` median ≤ 12 ms over 15 runs, load recorded |
| ✅ | **F2** One request, one process (items 1–3 batch 21, item 4 batch 26) | VM handler ≤ 3 ms; client total ≤ 6 ms; ten files and `checkout_transport.py` pass |
| ✅ | **U15** std/lib edits reload in the warm VM (batch 21: edit seen in 1.0 s, revert 0.86 s) | A `priv/lib` edit is seen by the next `bl test` in < 10 s with no SDK |
| ✅ | **K1 + K1b** Sealed boot state, lazy owner registry and lease (batch 25: cold `bl run` ~1.19 s median, was 2.06–2.44 s) | Cold `$SDK/bin/bl --cold run` ≤ 1.2 s median |
| 🔨 | **F3** Fast entry and request (batch 26: `.bl/bin/bl` 4.7 ms warm at the repo root; ≤ 2 ms needs a resident client) | Warm unchanged request ≤ 2 ms on a quiet machine |
| ✅ | **K2** The checkout's cold path (batch 26: +55 ms over the SDK's own, was +570) | `./bin/bl --cold` adds ≤ 100 ms over `$SDK/bin/bl --cold` |
| 🧪 | **M2** Project units restored on realm retirement (`lane/m2`, batch 29 after 28b; gate 28 found keys never matched; fixed: unchanged realm 285–310 → 170 ms, body edit seen by `run` −55 ms, `body/first/test` unchanged ~290–335 ms) | No `m1.py` row slower than restore-off; unchanged units restore; the edited unit's compile is the next card |
| 🧪 | **M1** A real edit benchmark (2026-11-24: body edit 448–500 ms, macro edit 395–423 ms, `priv/lib` edit 1.1–1.5 s, warm test 159 ms, first command in a fresh VM 5.8 s; next M2, M3, M4) | Enchant edit-to-result, cold and warm, recorded |
| 4 | **R1** Ship it | Installed `bl` rebuilt from main through the release gate, remeasured |
| ✅ | **N4a** Restored units by reference (batch 23) | Std-edit SDK unit work 40 s → < 8 s |
| ✅ | **N4b** Compiler-edit bootstrap (batch 23: P/B/C for a host edit ~1,500 s → ~50 s; C elided) | P boots the previous qualified compiler; C skipped when B = P; a `priv/host` edit's SDK ≤ 15 min |
| 5 | **N4d** Dev SDK outside QEMU | Beams path-normalized so they match the store; a `priv/host` edit runnable in ≤ 3 min |
| ✅ | **N0** Native go/no-go (landed `d7a9487d1`: **no-go**, native 1.86× *slower* at the median unit) | Per-unit native vs BEAM front-end time, `aot.bl` compiled into the image; N3, N4c, N5 and C3 go ahead only at ≥ 2× |
| — | W4 | As written below |
| — | C2 | Dropped: its prototype measured 0.4%, within noise |

N3 (shadow mode) is replaced by N0, then N5 (the native image as a Nix-built SDK input,
failing the build on `priv/boot` drift) if N0 passes. Shadow mode would double compile work
to produce equality data N2b already has.

## How a card gets done: work, check inside, one integration gate

An agent does the whole card and checks it right where it works, in seconds to
a few minutes. It never waits on an SDK build. **The integrator (the session
that fanned the cards out) merges finished branches in batches, builds one SDK
per batch, and runs the gate tests.** A card is ✅ only after that gate.

### Where an agent works
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

- **Retained worktrees (2026-11-24).** Only `.claude/worktrees/integration`, the integrator's gate tree. `lane-cerl` was retired after N0's no-go; N0 kept its own data in `~/.cache/n0/d`. `git worktree list` also shows `.claude/worktrees/sdk-lock-wait` (locked) and four `~/projects/enchant-*` worktrees, which belong to other sessions; leave them alone.

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

### F — the request floor (2026-11-23 review)

#### F1 ✅ One exec to the client · landed batch 21 (`fe11a7cbc`) · S · `bin/bl`, `scripts/prepare-checkout-platform`, `tooling/drop`
- **Why.** About 10 ms of the 25 ms warm floor is shell, before the Rust client runs. `bin/bl` is `/bin/sh` with `resolve_dir` subshells. Line 18 runs `scripts/prepare-checkout-platform` (bash plus a `find` over `nix/ tooling/drop native/`) on every request; measured 7.3–10.2 ms per call at load 22.
- **Change.** The warm path does one `exec` of the client. The client (or the generation service it already talks to) answers the platform fingerprint from its stat cache, falling back to the script only when the cache misses. Cold and sandbox paths (`BL_CHECKOUT_PLATFORM` preset, `--cold`) keep working.
- **Done when.** Warm `./bin/bl run` of `(println 1)` median ≤ 12 ms over 15 runs, load recorded. Editing a file under `nix/` or `tooling/drop/` still changes the platform. `test/scripts/checkout_transport.py` and `scripts/tests/test_engine_ci_inputs.py` pass.

#### F2 🔨 One request, one process · items 1–3 landed batch 21 (`fe11a7cbc`) · S+ · `priv/std/vm/` request handler
- **Why.** The VM handler was 13.6 ms before U11 (`research/checked-tiles/evidence/warm-floor-u9.json`): 9 spawns, `realm/open`, proxy and heartbeat, custody registration. U11 removed about 3 ms of it. Nothing has measured it since.
- **Change.** First re-run the U9 probes (`research/substrate-ab/floor/u9/`) on the current SDK. Then follow the plan in `research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org` lines 182–203: run the command in the connection process, with a realm handle opened once per generation. Write to the socket directly, start the heartbeat only past a threshold, and skip custody registration for an unchanged module set.
- **Done when.** VM handler ≤ 3 ms and client total ≤ 6 ms, both measured. The ten files, `realm_shared`, `session` and `checkout_transport.py` pass.

#### F3 ⏳ Keep-alive client, compact request · S · Rust + VM · after F1, F2
- Persistent connection, so no connect or hello per request. Send argv, cwd and an environment generation instead of 91 variables.
- **Done when.** Warm unchanged request ≤ 2 ms median on a quiet machine.

#### F2 status after batch 21
- Landed: replay modules kept loaded (bounded at 64, `priv/boot/lower.bl`); `realm/open` reused per (root, generation, caller scope); library store paths registered once per VM. Micro-benchmarks: replay one form 2,813 → 0.71 µs, `register-store-paths!` 624 → 77 µs, same-generation `realm/open` 529 → 33 µs.
- Not yet shown end to end: the gate's warm median (12 ms at load 21) is within noise of F1 alone (11.5 ms at load ~14). Measure the VM handler again on a quiet machine with `research/substrate-ab/floor/f1/start_wall_min.bl`.
- Open: item 4, running the command in the connection process. It changes cancellation, so it needs a SIGTERM/SIGKILL cancel check alongside the session and `realm_shared` tests.

#### Batch 22 (`31a8b524e`): the U15 overlay with live server owners, and `realm stop` after an overlay
- **What broke after batch 21.** Another session's `priv/lib/data/bounded-cache.bl` edit landed after main's SDK was built. Every warm request then recompiled it, failed with `{:code_leased …Bounded-cache.Owner}` and exited 1, at 1.2 s each. The first `realm stop` then crashed the VM manager, because a drain-time first load of `reload.generation` was refused under the overlay, and the VM stayed up.
- **Fix.**
  - A unit that defines a server owner, or trips a publication pin, is held: it stays on the SDK's code with one note per digest. 21 library files define a server.
  - Failures are remembered per (file, digest), so a broken file costs ~1 ms per request, not a recompile.
  - Drain dependencies load at VM boot.
  - A failed drain is reported (`retirement failed: <reason>`) instead of crashing.
- **Gate (SDK `mqs6v3vg`, prep 1964 s).**
  - All overlay tests pass, and so does the scenario with a live bounded-cache owner.
  - `test/scripts/realm_stop_after_overlay.py` passes.
  - `session`, `realm_shared` and the ten files pass; `checkout_transport` exits 0.
  - Warm median: 13 ms in the gate at load 16; 6 ms on main at load 19 before.


#### Batch 23 (`423e3c8ee`): N4a and N4b, measured on consecutive preparations
- **N4a.** Restored units are checked only for what could change (manifest identity, compiler key, exact file list, regular files in bounds) and hard-linked rather than copied. Their bytes are hashed once, at assembly. Locally, unit work for 668 restored units went from ~7.4 s to ~1.2 s, with identical outputs. Tampering is still refused.
- **N4b.**
  - P boots the previous qualified compiler when a startup probe (3–15 s) accepts it; otherwise it falls back to the committed seed.
  - Generation C is elided when P = B byte for byte, because B's own run already is C's proof. When P ≠ B, C runs as before.
  - Edits to `env.bl`, `loader.bl`, `compiler.bl`, `bootstrap.bl` and `aot_cache.bl` make the probe refuse, and those still take the seed path.
- **Gate (load ~17, `prepare-checkout-sdk` wall time).**
  - The batch itself: 674 s.
  - A `priv/host/delay.bl` comment: 1175 s. P took 40 s (1 compiled, 90 cached), B 8 s, and C was elided.
    - **But the library recompiled all 668 units (cached 0), in 4 shards of ~415–505 s each.** Every library unit is keyed on the whole compiler key, and any `priv/host` edit rotates it. That is N4c.
  - A `priv/boot` comment, which rotates the key: 1732 s, against 2967 s in batch 21. The previous compiler was accepted and all 91 compiled.
  - Going back to the base reuses the SDK in 0 s.
  - Two layered preparations in a row, across a rotation, both succeeded.

#### N4c ✅ Per-unit compiler key for library units · landed batch 25 (`1023d1519`)
- **Why.** After N4b, a `priv/host` edit costs ~50 s of compiler work and ~1,000 s of library recompiling, because every library unit's key includes the whole compiler key.
- **Change.** Key each library unit on its own inputs plus the bytes of the compiler and host modules that compiling it actually loads. Codegen modules (`emit`, `lower`, `aot`, …) stay in every key. A host module that changes no unit's compiled output therefore restores every unit. Alternatively, use early cutoff: recompile, compare the emitted bytes, and stop when they are equal. That needs the native front end or a cheap compile, so it is weaker.
- **Done when.** A `priv/host/delay.bl` comment's SDK restores ≥ 95% of library units, and preparation is ≤ 600 s end to end.

#### Batch 28 (`48aab0e08`): M3 and M4 (M2 follows in batch 29)
- **m1.py on SDK `bckrfcnx`, against batch 26 (5 cycles, load ~17):**

  | Case | Before | After |
  |---|---|---|
  | body/first/test | 351 ms | 291 ms |
  | macro/first | 355 ms | 320 ms |
  | lib/first | 1,304 ms | 903 ms (client 119 → 10 ms) |
  | revert | 1,153 ms | 913 ms |
  | first-in-fresh-vm/test | 6.25 s | 6.1 s, with cold/test 3.2 → 3.4 s at higher load, so not conclusive |
- **M4.**
  - The 15.5 s client stall was a 12 MB shared digest cache that stat-checked 63k rows on every save. It is now a cache per checkout root.
  - After a reloadable file edit, the generation service re-reads only that file.
  - The overlay scan reads a file only when its stamp moved.
  - An install patches the runtime inventory for the replaced unit instead of walking the SDK.
- **M3.**
  - The client sends the first request as soon as the socket accepts.
  - A request that arrives during boot waits on a flag instead of racing the boot's `:global` locks.
  - The manager and realm locks poll every 2 ms instead of `:global.trans` backoff, which was 147–497 ms.
  - The remaining surplus over `--cold` is about 1 s of daemon namespaces loaded one by one, plus the per-load inventory.
- **M2** fixed its key: it had included VM publication counters that tick on ordinary commands. An unchanged realm restores and drops from 285 to 170 ms, with no regression. It lands as batch 29.
- **T5 ⏳** `loader_path_test` `a-configured-path-shadows-priv` writes into the store SDK (`erofs`). It only passed on check-runtime-hosts' writable image.
- **E1 ⏳ (new)** The compile of the one edited unit is now the floor of an edit: frame-plan takes 80–150 ms, and `core.bl` ~350 ms for a lib edit. Profile `compile_file`/`eval_string` on real units and cut it.

#### Batch 26 (`d6c48cc33`): T3, F2 item 4 + F3, K2 + init trims
- **T3.**
  - Restored unit links are now read-only, or a copy is made. A write to a restored path unlinks first, so a write can never reach a store the user owns. That was a real hazard from N4a.
  - Four tests were wrong rather than the code: `aot_implicit_dependencies` (realm path), `sdk_loading_batch` (warm VM already initialised), `test_test_prerequisites` (stale line numbers in the boundary map), and `codegen_provenance` (wrote into the store SDK). All pass on the batch SDK.
- **F2 item 4 and F3.**
  - The command runs in the connection process, and the connection watcher owns cancellation and the heartbeat.
  - The accept loop pre-starts the next owned worker.
  - The project `env.bl` value is memoized by its bytes. That cost 1.85 ms per request at the repo root, and it was the "regression" that took warm time from 6 to 12 ms.
  - The client keeps `.bl/bin/bl`, a symlink to itself that skips the 2.4 ms `/bin/sh` script.
  - Warm `(println 1)`, 21 runs at load ~5: repo root `./bin/bl` 6.6 ms and `.bl/bin/bl` 4.7 ms; scratch project 7.9 and 5.2 ms.
  - What is left below that: a resident client or broker (a keep-alive across processes) and a compact environment (a protocol bump). `run_file` on an unchanged file still costs 0.43 ms.
- **K2.**
  - A settled tree takes the client's fingerprint, accepted only against a `selection.v1` record that the Python path writes after full verification.
  - `bin/bl` execs the SDK's `boot.exs`.
  - `./bin/bl --cold` is now 1.10–1.15 s against the SDK's own 1.03–1.14 s.
- **Init trims.** `packaged_compiler?` stops at its first match; `declared_ns` scans a 64 KiB window; the floor proof skips the Rt/Compiler attribute chunks; seed manifests are parsed once per VM on store paths. Cold sealed paired: 1.04–1.07 s, against 1.09–1.21 s.
  - What remains toward 0.8 s is design work:
    - initializers, 226 ms, of which `mark_emitted` receipt compression is 84 ms. Storing receipts uncompressed saves ~45 ms for ~3 MB per VM, which is a call for the user;
    - attribute decoding of the phase library, 46 ms, which is a `priv/boot` emitter change;
    - the floor proof, 52 ms, which could be sealed in `do-prime`;
    - erts + Elixir, ~240 ms.
- **A host comment after T3's `priv/build` change:** 670 s.

#### T4 ✅ (landed `5585e228a`: both were test bugs, green warm and --cold on SDK vdd8ppwp) `proc/owner_registry_test` and `application_package_test` fail after other files in one VM · H
- In gate 26 (after the T3 group in the same VM) and on main's SDK `8as75r07`, these fail:
  - `proc/owner_registry`: all 4 tests fail with "Test owner failed during admitted startup".
  - `application_package` `package-consumers-preserve-source-effects-across-fresh-vms`: "Application package realm identity mismatch".
- In gate 25 the same code passed `proc/owner_registry` 53/53, run first in its VM.
- Find the shared state, and make each file pass in any order.

#### Batch 25 (`1023d1519`): K1b, N4c, and the fresh-VM start and stop races
- **dupstart.**
  - A fresh VM's boot and its first request both started `vm-manager`, and the check-then-start wasn't atomic. It now runs under a `:global` lock, and the loser gets the winner's pid. This removes `server failed to start: {:already_started …}`, which hit 1 in 3 fresh VMs on main and every other one with K1b.
  - `realm stop` now waits, up to 30 s, until the VM no longer answers and its process or socket is gone. Before, the next run reached the stopping VM in 4–7 of 10 cycles.
  - `test/scripts/realm_stop_after_overlay.py` is strict by default and passes 10 of 10 fresh cycles. `test/bl/vm/manager_start_race_test.bl` races 8 first starts.
- **K1b.**
  - The owner registry and the SDK lease start with the first managed actor, not at app start.
  - A namespace loaded before the lease takes the sealed image's unit rows.
  - `sdk-code.term` is read once per VM on a store root.
  - Cold `bl run` of `(println 1)`: 1123–1261 ms (median ~1.19 s) at load ~5, against 2.06–2.44 s before.
  - Next lever: `BeamLisp.init` (rt, core, reader, compiler, multi, sugar), ~550 ms.
- **N4c.**
  - The card's premise was wrong. A `priv/host` comment does not change the compiler key. It changes the exact runtime image key, which hashes every floor BEAM, and the edited BEAM differs only in its `bl_source_hash` attribute.
  - The `library-runtime-key` is that key with each floor module's digest taken without `bl_source_hash`. A unit is reused on it unless its compile read a whole-floor identity; the four functions that return one are counted.
  - Gate: a `priv/host/delay.bl` comment restored 668 of 668 units (`"reuse":"library-runtime"`). Unit work took 21.6 s, with `verify-restored` 1.8 s and `copy-restored` 0.8 s, so N4a holds in the VM. The SDK took 611 s end to end, against 1175 s before.
  - The rest is the fixed pipeline: Nix, P/B, and the library's fixed phases. That is N4d.
- **Pre-existing failures on main's SDK, now T3.** `sdk_loading_batch` (`sealed-dependency-admission-…`), `aot_implicit_dependencies` (a missing `Implicit.Consumer.beam` in the package ebin), and `build_pipeline_image` (`eacces` writing a restored-unit path, which is likely N4a's hard links on a 0444 file).

#### K1b ✅ Cold start below 1.2 s · landed batch 25 (`1023d1519`): ~1.19 s median on SDK rvjj1lps
- After K1, the remaining app start (~1.3 s) is code running, not values recomputed: namespace loads and initializers (~1/3 of samples), the owner registry leasing the whole SDK runtime closure (~15%), native stub compiles (~3%). See the journal section "K1: sealed boot state, and what a seal cannot reach" and `research/checked-tiles/evidence/cold-start-k1.json`.
- **Change.** Start the owner registry and the SDK lease lazily, so the first actor pays and a plain `bl run` does not. Load `bl.cli`'s namespaces on demand (~300 ms).
- **Done when.** Cold `$SDK/bin/bl --cold run` of `(println 1)` ≤ 1.2 s median, paired with the batch-21 SDK.
- **Branch result (scratch store image, not an SDK).** 2,159 → 1,170 ms median over 6 alternating pairs against the batch-22 SDK at load 18–22 (`research/checked-tiles/evidence/cold-start-k1b.json`); app start 1,405 → 552 ms.
  - No owner registry and no SDK lease at app start. The first managed actor starts the collector (`Env/ensure_sdk_owner_registry!`, fresh process, same supervisor); the lease comes from its existing on-demand callers, plus `sdk_runtime_retained_modules?` for a native adapter.
  - The first lease batch-loads its closure and plans the requires of pre-lease namespaces. Without that a cold managed-app run was +6.7 s; with it, level with the eager lease.
  - Pre-lease image loads publish the sealed image's unit rows instead of going through the per-user AOT cache. On a `/nix/store` root, `sdk-code.term`, the image-table path and the preinit directory stamps are read once per VM.
  - `package_module_identity` loads what it fingerprints; the eager lease used to have loaded it (`realm_package_test` caught this).
  - Left: erts/Elixir/boot.exs 290 ms (the `elixir -e :ok` floor is 190), `BeamLisp.init` 550, the rest about 300.
- **Gate.** Build the SDK, then `scripts/sealed-boot/measure $OLD_SDK 4 OLD=$OLD_SDK NEW=$NEW_SDK`, expecting ≤ 1.2 s. Run in one `bl test`:
  - the ten files;
  - `host_application`, `host_supervisor`, `host_loader_server`, `cli_application_startup` and `native_owner_registry_start`: the collector absent at start and started on demand;
  - `proc/owner_registry`, `proc/inventory`, `proc_framework` and `sdk_loading_batch`;
  - `aot_implicit_dependencies`, which fails on a scratch image only because its child runs the SDK's own `bin/bl`;
  - the seed/aot suites. Four of their files fail on a scratch cwd for the old SDK as well.

#### T3 ⏳ Tests that fail on main's SDK · H
- `build_pipeline_image_test` `restored-units-feed-byte-identical-serial-and-parallel-images`: `eacces` writing `/tmp/build-image-*/parallel-units/…beam`. Likely a hard-linked read-only restored file (N4a) that is written in place.
- `aot_implicit_dependencies_test`: `Implicit.Consumer.beam` is missing from the package ebin.
- `sdk_loading_batch_test` `sealed-dependency-admission-preserves-deferred-initializers-and-converges`: intermittent.
- `scripts/tests/test_test_prerequisites.py`: 5 preflight failures.
- `codegen_provenance_test`:
- (Fixed in batch 22: the U15 scenario now stops its probe VM.)
- Two tests error with `erofs` writing `.../lib/beam_lisp-0.1.0/priv/codegen.sources` on any store SDK (same on main's `2nvkh1n5` and batch 21's `0nzlyz01`). Point them at a scratch copy.

### K — cold start

#### K1 ✅ Sealed boot state · landed batch 21 (`fe11a7cbc`), short of 1.2 s; the rest is K1b · S+ · `priv/host` (aot, aot_cache, env), `priv/build/selfbuild.bl` · branch `lane/sealed-boot`
- **Why.** Cold `bl run` on a store SDK is 2.56–2.77 s after U8. 65–70% is the `:beam_lisp` start plus `vm.native` `build-all!` (U5, `research/checked-tiles/evidence/cold-start-phases.json`). That work re-derives and re-checks SDK publication state on every start: environment tables, 1,438 published definitions, forwarder disassembly, MD5 leases. U6–U8 trimmed 5–26% each; that curve does not reach 1 s.
- **Change.** The SDK build writes the post-start runtime state as one sealed artifact (U8's `priv/seed-metadata.term` is the precedent). An immutable `/nix/store` SDK loads it in one step, trusted by store-path identity. MD5 checks remain only for modules actually loaded. A writable checkout image keeps today's path.
- **Done when.** Cold `$SDK/bin/bl --cold run` of `(println 1)` ≤ 1.2 s median over 4 pairs against the old SDK, load recorded. The ten files pass on the sealed SDK.
- **Branch result (scratch store image, not an SDK).** Re-derivations sealed or done once per VM on a `/nix/store` root: image unit metadata (`priv/image-metadata.term`, 2,567 rows equal to a live decode), the native bootstrap scan and negative declarations, the live toolchain keys and `packaged_compiler?` walk, the sealed seed table's per-miss sha256, the doubled floor proof. Cold run 2,962 → 2,163 ms median over 5 alternating rounds (−27%, load ~8); app start 1,944 → 1,326 ms. **1.2 s is not reachable by sealing:** what remains is execution (namespace loads and initializers about a third of the samples, the owner registry's SDK closure lease about 15%, native stub compiles 3%). The next levers are a lazy owner registry/SDK lease and a restorable Env snapshot; see the journal's K1 section and `research/checked-tiles/evidence/cold-start-k1.json`.

#### K2 ⏳ The checkout's cold path · S · `bin/bl`, `scripts/prepare-checkout-sdk`
- Before `elixir` starts, `./bin/bl --cold` runs `scripts/prepare-checkout-sdk --selection` (Python `scripts/sdk-inputs`: 184 ms warm, 1.5 s with a cold file cache), a second Python check and `exec elixir -e`.
- **Done when.** `./bin/bl --cold` adds ≤ 100 ms over `$SDK/bin/bl --cold` on a settled tree.

### R and M — shipping and measuring what users see

#### R1 ⏳ Ship it · release
- The installed `bl` is October's drop. Rebuild it from main through the release gate, with the `AUTO_RELEASE_ENABLED` rehearsal (AGENTS.md); root deploys. Remeasure installed warm and cold.

#### M1 🧪 A real edit benchmark · measurement · branch `lane/m1`
- Edit one Enchant namespace (`/home/othman/projects/enchant`), once a body and once a macro provider. Time it until the result shows, cold and warm, and record that as the user-path baseline.
- **Measured 2026-11-24** on main `535538242`, SDK `vdd8ppwp`, platform `k3f6kmfx`, load 6.6–7.8 (`research/checked-tiles/evidence/m1-edit-benchmark.json`; script `research/substrate-ab/m1/m1.py`, private copy by `copy.sh`).
  - `/home/othman/projects/enchant` is this repository. The run used a private `git worktree` of main whose `.bl` links to main's exact client and SDK, so its VM was its own (`$MAIN/bin/bl` would share main's VM with the integrator and other agents, and a `priv/lib` edit needs an engine checkout). Same VM pid through every cycle; nothing prepared.
  - Enchant has no project macro provider with project dependents, so the copy adds `scene_demo/m1_guard.bl`, expanded by `scene-demo.frame-plan` and `scene-demo.film`. Every edit was checked by output.

  | Case (5 cycles; wall ms, median [min–max]) | `bl test frame_plan_test` | `bl run` probe |
  |---|---|---|
  | 1 Warm, unchanged (n=15) | 159 [119–620] | 62 [33–334]; `run examples/hello.bl` 192 [148–311]; `check` 202 [118–1,649] |
  | 2 Body edit, first / repeated | 464 [353–16,289] / 448 [371–592] | — / 500 [374–665] |
  | 3 Macro provider edit, first / repeated | — / 406 [337–484] | 395 [359–485] / 423 [375–519] |
  | 4 Cold: `--cold` / first command after `realm stop` | 4,018 [3,325–5,431] / 5,765 [5,205–6,494] | `--cold run hello` 2,028 [1,693–4,037] |
  | 5 `priv/lib/scene/core.bl` edit (U15), first / repeated / revert | — / 1,080 [986–1,334] | 1,531 [968–1,662] / 1,175 [1,069–1,304] / 1,066 [978–1,195] |

  - **Where it goes.** Client: 0.6 ms unchanged; 10–17 ms after a project edit; after a `priv/lib` edit the generation service times out at 150 ms and the client inventories locally (118–404 ms; once 15.5 s after a body edit). VM handler: ~1 ms unchanged; +47–67 ms `realm/open` after a project edit; ~1.1 s of overlay after a `priv/lib` edit. Compile: `AOT/ensure_loaded_local` is `:no_module` for every project namespace in every new realm, so any edit recompiles the whole loaded project closure (frame-plan 80–133 ms, film 85–127, guard 10–21): a macro edit recompiles 3 of 3, a body edit too. The test file recompiles on every `bl test` (6–12 ms), and the first `bl run` after a `bl test` recompiles the project again (~200–320 ms). Run: an unchanged warm test is ~40% loader file probing, ~35% compiling. The first `bl check` per VM compiles `bl.check` and 27 more SDK namespaces from source (`bl.check` 897 ms).
  - The 2026-11-20 numbers (body 170–269 ms, macro 167–169 ms) were a two-file scratch project on the October drop and are not comparable.
- **Gate.** None (measurement only). To reproduce it: `bash research/substrate-ab/m1/copy.sh $MAIN /tmp/m1-$USER/enchant`, then `cd /tmp/m1-$USER/enchant && work run --memory 4G --timeout 2400 -- python3 -I $WT/research/substrate-ab/m1/m1.py --checkout /tmp/m1-$USER/enchant --out OUT --cycles 5 --cold 5`; remove it with `copy.sh --remove`.

#### M2 🧪 Project namespaces restored, not recompiled, when a realm retires · branch `lane/m2` · S+ · BL runtime (`priv/host/aot.bl` `ensure_loaded_local`, `priv/host/loader.bl` `do_load`) · from M1
- **Why.** An edit to one 18-line namespace costs 450–500 ms, because the new realm recompiles every loaded project namespace (`ensure_loaded_local` always misses). The cost scales with the project, not the edit. `bl run` and `bl test` also don't share loaded project code, so alternating them recompiles each time.
- **Change.** Keep compiled project units keyed by source digest plus the digests of the macro providers and `:require`d declarations each unit read (the U12a replay and the N4c reuse rule are the precedents). A new realm restores unchanged units and recompiles only the edited namespace and those whose recorded macro inputs changed. Share the key across `run` and `test` realms of one project generation.
- **Done when (revised 2026-11-24, after gate 28).** In `m1.py` on a private copy of the integration SDK: no row is slower than the same SDK with `BL_REALM_UNIT_RESTORE=0`, measured interleaved; unchanged units restore in a later realm (revert/run-probe, and film and m1-guard after a body edit, show `restore` under `BL_REALM_UNIT_TIMES=1`); every edit still shows its output and the new expansion (15/15). The ≤ 200 ms body edit is no longer M2's target: `body/first/test` loads only the edited unit, and its compile (80–150 ms) is the next card. *Original target:* a body edit's first command ≤ 200 ms median, recompiling 1 namespace; a macro edit recompiling the provider and its dependents only; the first `bl run` after a `bl test` recompiling nothing.
- **Branch `lane/m2` (2026-11-24).** `ensure_loaded_local` now admits every realm-local namespace whose top-level heads are standard defining forms (one `ns` per file), not only the finite lexical subset. Miss: `AOT/compile_source` once, stored in the AOT cache. Hit: publish the stored beams and replay `__bl_init__` in the new realm's env.
  - **Key (`realm_unit_key`).** The interface-aware require closure (`ns_closure_hash`), plus the *compile-time closure* as bytes: the whole require closure of every uncovered edge target (macro providers, referenced macros, files defining macros), so a helper two requires below a macro is keyed by its body (the plain closure key keys it by interface: a real hole for expansion-time helpers). Plus project namespaces reached by unrequired `p/name` references, capabilities of the env (the compile gate), realm facts, compiler namespace generations, compiler key, the SDK's priv root and U15 overlay digests of library members.
  - **Restore also needs.** The compiler's replay witness (`bl_aot_replay_complete`) on the cached forwarder; load stamps (`note_realm_unit_loaded!`, written by `do_load`) proving each loaded closure member still holds only what its source load defined (a REPL redefinition compiles the dependent fresh); and no retained busy code for the realm key (stable module names cannot take a third version; that realm keeps the eval path's fresh names).
  - **Not keyable.** A macro whose expansion reads the world (a file, env var, clock) expands once per key, as in an SDK library. Definitions made by REPL in a namespace before its first load. `BL_REALM_UNIT_RESTORE=0` turns it off; `BL_REALM_UNIT_TIMES=1` prints key/fetch/witness/register/init/compile/store per unit.
  - **Inner loop** (`scripts/check-runtime-hosts`, edited `aot.bl`/`loader.bl` on SDK `vdd8ppwp`, load 9–14): `test/bl/realm_unit_restore_test.bl` 17/17, three runs; `realm_aot_reuse`, `realm_namespace`, `loader_sources_realm`, `realm_code_lifetime`, `contextual_realm_retirement`, `vm/realm_reopen`, `vm/realm_lifecycle` pass. `realm_package_test` 108/112 with edited hosts (fresh child VMs refuse the non-SDK `BeamLisp.AOT`: `sdk_preinit_producer_unproved`; 112/112 with hosts unedited, so it needs the SDK gate). `ward_realm_clean` and `realm_ownership` fail identically with hosts unedited.
  - **Fixture timings** (10 small namespaces, one with a top-level effect; ms, median [min–max] of 3): today's eval path, every unit compiled 207 [195–210]; M2 unchanged realm 122 [113–126]; body edit (1 recompiled) 167 [166–181]; macro edit (provider + 3 dependents) 231 [223–250]; first compile of all 377 [347–383]. Per unit: restore 12–17 ms (init replay 6–9 of it), key 0.6–2.5, `compile_source` 30–45 vs ~20–28 through `eval_string`. So a macro edit that recompiles most of a small project is ~10% slower than today; see what's left.
  - **Gate (integrator, on the integration SDK).** The ten files, `realm_shared`, `session`, the overlay tests, `test/scripts/checkout_transport.py`, `realm_stop_after_overlay.py` (strict), plus `test/bl/realm_unit_restore_test.bl`, `realm_aot_reuse_test.bl`, `realm_package_test.bl`, `realm_code_lifetime_test.bl`. Then `m1.py --cycles 5`: `body/first` and `body/repeat` rows should compile only `frame-plan` (trace: `ensure_loaded_local` `:loaded` for film and m1-guard), `macro` rows compile 3 of 3 and show the new expansion 15/15, and the first `run` after a `test` compiles nothing.
  - **Left.** Whether `body/first` reaches ≤ 200 ms is for m1.py to say: frame-plan alone compiled in 80–133 ms in M1, and realm open is 47–67 ms. The next costs are `run_init_modules` (6–9 ms per restored unit for a 3-line namespace) and `compile_source` against `eval_string`.
- **Gate 28 (2026-11-24, SDK `sf819y5q`): not landed.** `m1.py` showed no gain (body/first/test 351 → 334 ms) and slower macro edits (355 → 584 ms). Cause, found on a private copy with `BL_REALM_UNIT_TIMES=1`: the key folded the VM's global publication counters for `core` and the other compiler namespaces, and `core` advances on ordinary commands (2498 → 2500 → 2504 over three requests). So no key ever matched in a later realm, and every miss paid `compile_source`, ~1.8× the eval path on real units (frame-plan 150–240 ms against 80–133).
- **Fix (`c35b388bf`).** Compiler code is named by the compiler key, the SDK root and the overlay only. A miss on a key seen once in the VM takes the old eval path and stores nothing; a key asked for again pays `compile_source` once, then restores. SDK closure nodes are remembered per VM, which cuts the key from 12–45 ms to 1.5–5 ms (film 3.4, frame-plan 4.7, guard 1.5 ms mean over 40–55 keys). Restores now hit: film 25/40 loads, frame-plan 35/55, guard 15/25, 11–14 ms each.
- **Measured** on a private copy of the integration tree (SDK `sf819y5q`), the fixed `BeamLisp.AOT` hot-loaded into its warm VM. The base is the same VM image with `BL_REALM_UNIT_RESTORE=0`. Rounds interleaved fix/base ×2, 5 cycles each, unique edit text per run, load 16–18; ms, medians of the two rounds:

  | `m1.py` case | base | M2 |
  |---|---|---|
  | body/first/test | 290 / 337 | 293 / 335 |
  | body/repeat/run-probe | 302 / 323 | 248 / 260 |
  | body/repeat/test | 293 / 318 | 307 / 348 |
  | macro/first/run-probe | 309 / 316 | 324 / 377 |
  | macro/repeat/test | 321 / 300 | 285 / 317 |
  | macro/repeat/run-probe | 338 / 320 | 315 / 381 |
  | revert (unchanged units) / run-probe | 285 / 310 | 170 / 173 |

  An unchanged realm restores (−120 ms), and a body edit seen from `run` saves ~55 ms. Macro edits are within noise of the base (fix round 2 ran high across every row, warm/test included). **body/first/test ≤ 200 ms is out of M2's reach:** that command loads only the edited `frame-plan` (which must compile, 80–150 ms on the eval path at this load) and the 3-line guard. The rest is the warm test floor (~128 ms) and realm open. Reaching 200 needs a cheaper compile of the edited unit, not restoration.

#### M3 🔨 The first command in a fresh checkout VM costs what `--cold` costs · S · `tooling/drop` (cold child), `priv/std/vm/manager.bl` · branch `lane/m3`, waits on the gate
- **Why.** The first `bl test` after `realm stop` takes 5.2–6.5 s, 1.7 s more than `bl --cold test` of the same file (3.3–5.4 s). Every user pays it once per VM: after a reboot, after `realm stop`, after a runtime edit.
- **Change.** First split the 5.8 s with `BL_CHECKOUT_PHASE_TIMES=1` and the K1/U5 phase stamps: client wait for readiness, scope start, generation service start, VM boot, realm open, first-command compile. Then remove the warm path's surplus over `--cold`, for example by running the first command in the booting VM rather than waiting for readiness and reconnecting.
- **Done when.** `first-in-fresh-vm/test` in `m1.py` ≤ the `cold/test` median of the same run, over 5 cycles, load recorded.
- **Split (2026-11-24, `research/checked-tiles/evidence/m3-first-command.json`, boot tracer `research/substrate-ab/m3/`).** Median of 5 traced pairs: warm first 5,065 ms, cold 3,178 ms. Surplus 1,887 ms:
  - client and spawn +40, VM boot to `bl.cli` +42: the same in both;
  - the daemon's own namespaces and listen 228, then the client's readiness poll, hello and reconnect 171;
  - the request waiting for the daemon's infrastructure 829: `bl.daemon` queued behind the boot's loads 260, then the manager-start lock, dev-overlay sync, realm open 569. The boot's services were still running 626 ms after the request arrived, and the request slept in `:global`'s retry backoff (0–250 ms, then 0–500 ms…) after the boot released the manager lock (285 ms in one run);
  - the test itself +556: after the SDK lease every SDK load re-derives the runtime inventory, 107–115 ms per load in the cold VM, 174–214 ms in the warm one with ~20 more namespaces loaded (M4's `retain_sdk_runtime!`).
  - So the card's premise is wrong: the readiness wait is hidden behind the VM's own boot services. About 1 s of the surplus is daemon namespaces loaded through the one loader (`vm.owner` 162–212 ms, `proc.reg` 131–175, `reload.generation` 131–173, …), which `--cold` never loads.
- **Branch change.** The client sends the command as soon as the VM listens (no readiness poll, no reconnect). In the VM a command that arrives during `boot-realm-services!` waits on a per-session flag (`await-boot!`), and the manager start and realm lifecycle use `vm.manager/trans` (2 ms poll) instead of `:global.trans`. The client change alone, on the old VM code, measured worse (median 6.5 s vs 5.5 s, 6 rounds), so the two land together. Expected gain 100–300 ms; the done-when needs the daemon's namespaces off the first command's path (sealed into the boot image, K-style) and M4.
- **Gate.** `test/bl/vm/manager_trans_test.bl`, `test/bl/vm/manager_start_race_test.bl`; `test/scripts/checkout_transport.py`, `test/scripts/warm_cancel.py`, `test/scripts/realm_stop_after_overlay.py` (strict); then `m1.py --cycles 5 --cold 5` and compare `first-in-fresh-vm/test` with `cold/test` (expected still above).

#### M4 ✅ A `priv/lib` edit costs its compile, not an SDK inventory · landed batch 28 (`48aab0e08`): client 119 → 10 ms, edit 1,304 → 903 ms; ≤ 400 ms needs a cheaper compile
- **Why.** A one-function `priv/lib/scene/core.bl` edit costs 1.1–1.5 s, and so does its revert. About 1.1 s is in the VM handler before the command runs: the sampler shows `AOT/sdk_runtime_inventory_uncached!`, `Env/retain_sdk_runtime!` and `install_dev_sdk_unit!`. Before that, the generation service declines at its 150 ms read timeout and the client inventories the tree locally (118–404 ms). Once, after a project edit, that local inventory took 15.5 s.
- **Change.** Re-derive only the replaced unit's rows in the runtime inventory, not the whole SDK closure. Have the generation service answer a reloadable-source change, or answer "changed" within a few ms, instead of timing out. Find and bound the 15 s local inventory (cold digest cache?).
- **Done when.** In `m1.py`, `lib/first` and `lib/repeat` ≤ 400 ms median, the client ≤ 20 ms on those rows, and no client row over 1 s across 5 cycles.

### U — the request path (what every user pays)

#### U1 ✅ The checkout client inventories declared inputs only · S · Rust
- **Why.** Each `./bin/bl` request first hashes the project's sources so the
  warm VM can tell whether they changed.
  - `checkout_sources_walk` in `tooling/drop/src/checkout.rs` (~line 374)
    descends into every directory of the project. For this checkout that is the
    whole repository, so request cost grew with untracked scratch: 52k `statx`
    and 302k `readlink` per request, 18k directories under
    `research/native-seed/out` alone (deleted 2026-11-22), and 2k under
    `research/formal-logic/evidence`.
  - It also calls `std::fs::canonicalize` for each directory and each file.
- **Change.** Inventory exactly what the realm can load:
  1. the project's `env.bl` `:paths` (this repo: `["examples" "examples/scene-renderer"]`);
  2. `env.bl` and `.env.local.bl` themselves;
  3. the explicit argv sources `checkout_extra_sources` already finds;
  4. with no `:paths`, the realm's default search roots. Find them in
     `priv/host/loader.bl` and `daemon.rs::project_dir`; don't guess.

  Keep the runtime pin (`checkout_runtime_generation`, driven by
  `nix/engine-inputs.json`) unchanged. Canonicalize once per root, not per file.
- **Files.** `tooling/drop/src/checkout.rs` (and its tests, same file).
- **Done when.**
  - `cargo test` passes in `tooling/drop`, including the existing
    `project_edits_change_the_realm_input_but_preserve_the_runtime_pin`.
  - A new test adds 1,000 junk directories outside `:paths` and asserts that
    the project generation is unchanged.
  - After the platform rebuild (`scripts/prepare-checkout-platform`, run by
    `./bin/bl`), seven warm `./bin/bl run /tmp/x.bl` requests have a median
    under 100 ms (it was 550 ms).
  - Editing a `.bl` under `examples/` still retires the realm: the next run
    shows the edit.
- **Pitfall.** A file the realm loads but the inventory misses means stale
  code: the bug class this pin exists to prevent. When unsure, inventory more
  roots, never fewer.
- **Conflicts with** U2 (both edit `tooling/drop`, one platform build).

#### U2 ✅ A warm VM that dies at start fails the request at once · S · Rust
- **Why.** `retry_from_warm` → `wait_ready` (`tooling/drop/src/launcher.rs`
  ~line 525) waits the whole readiness deadline even when the VM it started
  has already exited. On 2026-11-22 the installed `bl` inside this checkout
  logged `** (BeamLisp.ExInfo) Invalid native refresh project` at once, and the
  client still waited 120 s.
- **Change.** While waiting, notice that the started VM exited (keep its pid
  from `start_daemon_detached`, or watch the log for a `--- … bl vm start`
  section followed by an `** (` line). Then return immediately and print the
  last ~15 lines of that log section.
- **Done when.**
  - A unit test with a start command that exits 1 at once returns within 2 s,
    with the log tail in stderr.
  - `cargo test` passes.
  - Rerunning the installed-`bl`-in-checkout case fails in under 5 s with the
    exception text.
- **Conflicts with** U1.

#### U3 ✅ A failed SDK preparation names its first cause · H/S · BL
- **Why.** A failed preparation reports only
  `Preparation ended failed: exited with code 1` (`nix/preparation-operation.bl`
  line ~481). On 2026-11-22 the real cause, a cached nixbuild.net failure for
  `beam-lisp-sdk-unit-archive.drv`, sat in
  `.bl/sdks/<fp>/job-*/foundry-state/ledger/events/<job>.jsonl` as `"text"`
  lines starting `progress machine: error:`. Two agents lost time to it.
- **Change.** When `await!` sees a terminal failed state, read that job's
  events file. Append the first 3 distinct lines containing `error:` (strip
  `progress machine: `, cap at 1,500 bytes) to the refusal. The directory is
  the preparation's own job directory, already known to `await!`.
- **Done when.**
  - A test under `test/scripts/` feeds a fixture events file and checks the
    message contains `Cached build failure`.
  - A real failed preparation shows its cause in the client message.
  - The test fails without the change.
- **Note.** `nix/` is an SDK input: batch this with other SDK-input cards.
- **Follow-up (batch 17).** On 2026-11-23 the first three `error:` lines were all
  `Cannot build '<drv>'.` — the leaf (`{:artifact-failed host.beam-lisp}`, then the producer's
  `** (ArgumentError) …`) sits higher in the same file. Prefer distinct lines that are not
  `Cannot build`, falling back to the first three; add a fixture whose chain hides its leaf.
  **Done in batch 19 (`9d9f68bb8`).**
  - Leaves are a `** (…Error)` line, an `:artifact-failed` unit, or any `error:` line other
    than `Cannot build`. They come first, and the links fill what's left of the three.
  - Builder prefixes are stripped.
  - The new fixture is `test/fixtures/preparation/producer-failed`, from batch 17's real
    failure, trimmed.
  `nix/` is an SDK input, so land it with the next SDK-input batch.

#### U4 ✅ Lock work per request proportional to change — retargeted: locks cost 1–3 ms per request, Env full-table scans cost 15–30 ms; U4b replaces the scans with exact-key lookups (`lane/runtime`, Env own time per spawn 1,904 → 971 µs) · S+ · BL runtime (after U1)
- **Why.** Journal 06, "Where a warm request waits": ~84
  `bl_native_publication_lock` acquisitions per warm request, through
  `run_code_callback_entry!`, `retain_code_components!`,
  `register_code_callback!`, `close_execution_registration!` and
  `release_eval_module!` (all in `priv/host/env.bl`: lines ~3548, 951, 2957,
  3120, 4080). They run for modules already loaded and unchanged.
- **Change.** Measure first with the probes in `research/substrate-ab/floor/`
  (`ab_wall.erl`, `ab_sampler.erl`; see the journal for how they were run).
  Then make registration happen once per module version, keyed by the module's
  md5, so that an unchanged request takes the lock zero times. Keep
  dead-owner recovery.
- **Done when.**
  - On an unchanged warm request the lock is acquired 0 times (counted with the
    same probe).
  - Median warm request time is reported before and after.
  - These test files pass: `test/bl/compiler_unit_store_test.bl` plus every
    test file whose name contains `reload`, `execution` or `env`. List them
    with `ls test/bl | grep -E 'reload|execution|env'`.
- **SDK build.** Yes (~14 min). Batch with U3.

#### U5 ✅ Where a cold start goes · S · measurement only
- **Why.** Cold `bl run` of `(println 1)` takes 7.6 s, and nobody knows the
  split.
- **Do.** Time phases of `./bin/bl --cold run /tmp/x.bl` under `work run`:
  - launcher → `erl` exec;
  - erts boot;
  - application starts (the ~50 dependency apps);
  - SDK module loading;
  - realm setup;
  - first user form.

  Use `+S`-free `-init_debug` or `erlang:system_time` stamps that the launcher
  passes through (`BL_*` env), and `:application.which_applications` timing.
  Record in `research/checked-tiles/evidence/cold-start-phases.json`. Propose
  the fix for the top phase: a lazy app start, a boot script, or a spare
  pre-started VM per SDK. Change nothing.
- **Done when.** The phases sum to within 10% of the measured total, over 3 runs.

#### U6 ✅ The SDK inventory is walked once per VM · S · BL runtime · branch `lane/cold-start`
- **Why.** U5 measured a cold `bl run` at ~4.3 s (load ~4). 65–70% is the `:beam_lisp` app start
  plus `vm.native`'s `build-all!`, and the VM re-reads the whole SDK `priv` tree (~2,800 `.bl` files,
  `precompiled.term` 8 times) in 12–17 sweeps per run: 1.5–1.7 s. Phases 1–3 (client, erts boot,
  dependency apps) total only 0.3–0.45 s, so boot scripts and lazy app start would not help.
  Evidence: `research/checked-tiles/evidence/cold-start-phases.json`.
- **Change.** Memoize the inventory per VM, keyed by the image's identity. For an immutable image,
  take digests from the sealed manifest it already carries. Keep the full walk for mutable
  checkouts, with the same authentication authority.
- **Done when.** The sweeps happen once (counted with a probe), the cold total drops (measured on
  the integration SDK), and the inventory and custody tests pass.

#### U7 ✅ Cold-start hot spots · S · BL runtime · branch `lane/cold-start`
- **Why.** U6's sampler over 3 cold runs of an unchanged store SDK (3.5–3.65 s) ranks
  `Emit.collect_execution_entries` 9.6%, `seed_artifact_metadata!` 6.7% (first decode of 95 seeds),
  `Loader.find_file` 5.2%, `compile_sdk_source!` 3.5% (a compile on an unchanged SDK), and
  `code_server:call`/`gen:do_call` ~21% (serialized loads).
- **Change.** For each: why it runs on an unchanged immutable SDK; remove it or seal the answer at
  SDK build time; keep authentication; measure. Drop what doesn't pay.

#### T2 ✅ Three test files fail on main (predate U7) · S · landed batch 11
- `test/bl/emit_test.bl` ("the live module's bytes ARE the committed seed's bytes"), `test/bl/seed_publication_test.bl` (its `/tmp/bl-seed-test-host-out` manifest is missing) and `test/bl/perf/cold_namespace_load_test.bl` fail the same way on the batch-7 and batch-8 SDKs. Find whether it is the seeded floor (a `bl seed --check` question) or the tests' environment.
- **Done when.** Each passes on a fresh integration SDK, or its premise is corrected and the reason recorded.

#### U10 ✅ Remove the fixed recomputation per request · landed batch 17 (`611414488`)
- **Why.** U9: of a ~51 ms warm request, engine capture is 22.8 ms (976 files) and project generation 11.1 ms, both recomputed though the tree did not change.
- **What landed.** A per-tree generation service, observed by the kernel, answers the tree's generations. The first version hung in the real checkout and was reverted (`da07cadf8`). The fixed version is `1739d87a2`.
- **Measured (gate 17d, one SDK, load ~12).**
  - Warm request median 40 ms with the service, 91 ms without, over 15 runs.
  - 0 declined requests.
  - The ten files pass 10/10 in both orders.
  - `seed_runtime_abi` passes warm twice, and `warm_request_env` passes.
  - Two successive helper edits are both seen.

#### U11 ✅ Fewer process starts per request · landed batch 19 (`ffa931ab0`)
- **What landed.** Three fewer owned process starts per request. Each owned start costs about 1.04 ms; a plain `erlang/spawn` costs about 1.8 µs.
  - The heartbeat comes from the connection process while it waits.
  - `vm.net`'s client watcher and `vm.io`'s output proxy are plain processes.
  - The connection worker and the command's child stay owned, so a client that leaves still cancels its command. Gate 19c checked this: a client sent SIGTERM at 4 s left no marker. The agent also checked SIGKILL.
- **Left (≈1–2 ms).**
  - The connection worker could be a plain process too. It hands its environment to the command's child, so check that first.
  - `realm/open` re-reads `env.bl` and takes a `:global` lock on every request (0.67 ms traced).

#### U12 ✅ Request framing and the client's fixed cost · landed batches 17 and 19
- **U12a (batch 17).** `run FILE` replays an unchanged file's compiled forms, keyed by source hash, while the realm's `definition_context` is unchanged.
  - The code is in `priv/host/beam_lisp.bl`, forwarded through `priv/host/compiler.bl`.
  - It needed three fixes: host constants as `defn`s, a floor guard, and facade forwards.
- **Platform selection reuse (batch 19, `a99ca9941`).** This was the largest remaining cost, and U9 had missed it.
  - Every `./bin/bl` re-hashed `nix/`, `tooling/drop` and `native/` (20 ms).
  - `scripts/prepare-checkout-platform` now reuses the fingerprint recorded for an identical settled stat listing, stored in `.bl/platform-stat.v1`.
  - `BL_CHECKOUT_DIGEST_CACHE=0` recomputes.
- **U12b (batch 19, `5053857f6`).** The generation service and its client read lines in blocks. This made no measurable difference.
- **Declined.**
  - Skipping connect and hello isn't possible while each command is a new client process, and hello costs only 0.79 ms.
  - An environment delta would save about 0.5 ms and needs a protocol change.
- **Warm floor after batch 19** (gate 19c, load ~24, 15 runs):
  - `bl run` of `(println 1)`: 26 ms median;
  - with the generation service off: 73 ms;
  - with the platform cache off: 41 ms.

#### U13 ✅ The checkout, not the caller, supplies the engine pin · landed batch 20 (`6b4a4074f`)
- **Cause.** U10 moved `set_var("BL_CHECKOUT_SDK_INPUTS")` after `checkout_generations`, so the runtime token folded the caller's value or nothing. That had two effects:
  - a caller could choose its VM;
  - editing `nix/` or `tooling/drop` stopped retiring the VM.
- **Fix (`c95703e54`).**
  - The captured fingerprint is passed in explicitly, and the token is byte-identical to the pre-17 one.
  - The variable is dropped from the service's token environment.
  - The resident socket name includes the client executable (protocol v2).
- **Second fix (`bb8069980`).** A file the realm records after an answer was missed, because the re-walk served cached project tokens. `watch_inputs` now clears them.
- **Gate 20.** `checkout_transport.py` exits 0.
- **Cleanup.** Old-client residents never exit. Kill them once with `for p in $(pgrep -f -- "--generation-servic[e]"); do kill $p; done`. The bracket keeps the pattern from matching your own shell.

#### U14 ✅ Sessions inside a VM keep their own records · landed batch 20 (`85f9d8ddb`, `a7063f090`)
- **Cause.** These were VM-wide in `priv/std/vm/session.bl`, not per session:
  - the draining flag;
  - the in-flight count;
  - the realm list.
- **Effect.** An inner session's stop waited on the outer `bl test` request and set the VM's draining flag, which killed the warm realm. That caused all 53 + 6 `realm_shared` failures and the 3 `session_test` failures.
- **One stale test.** The schedule test relied on the inner session clearing commands-only.
- **Gate 20.**
  - Both files pass warm, twice, then the ten files pass in the same realm.
  - Cold passes 53 / 111 / 43.
- **Left.** `contextual_session_retirement_test` still assumes it is the VM's only session. It passes cold, but run warm it takes the realm down, so keep it out of warm runs.

#### U15 ✅ A `priv/std` or `priv/lib` edit runs in the warm realm without an SDK · S+ · BL runtime + loader
- **Why.** The SDK is the only route today. A one-file std edit costs 440 s (N4's measurement), and under 10% of that is compiling. Project code already reloads in place. SDK namespaces refuse with `sdk_forwarder_route_changed`, and `:shadow` reaches only callers inside the project.
- **Change.** In a checkout, a changed SDK namespace under `priv/std` or `priv/lib` is compiled in the realm, from the checkout, and routed for every caller, library to library included. The realm then retires as it does for a project edit.
  - Keep `priv/boot` and `priv/host` on the SDK path: they are the compiler and the floor.
  - A released SDK never does this.
- **Simplest form (review, 2026-11-23).** A checkout VM has one tree and one user, so a "dev-tainted" VM may replace SDK modules VM-wide with `code:load_binary`. That already reaches library-to-library callers, with no per-realm routing. The refusal to lift is two strict equality checks, on the SDK runtime lease and on forwarder routes (around `priv/host/env.bl:5462` and `priv/host/aot.bl:2305`; verify the lines).
- **Refuse compiler inputs.** Several `priv/std` files feed the compiler key (`nix/producer-sources.nix:13–22`: `vm/native.bl`, `multi.bl`, `bl/*.bl` among them). An edit to one says so and points to the SDK path, instead of looking fresh while it isn't.
- **Done when.**
  - Editing a `priv/lib` namespace, including one function another library namespace calls, and then running a `bl test` that exercises both uses the edit in under 10 s, with no SDK preparation. Don't use `vm/session.bl`: it serves the request itself.
  - Reverting the edit restores the SDK's code.
  - The ten files pass afterwards.
  - Preparing the SDK for the same tree gives the same results.

### N — the native compiler on the default path

#### N0 ✅ Native go/no-go · landed `d7a9487d1` · measurement only · **no-go**: N3, N5 and C3 stay parked
- **Measured (2026-11-24, SDK `8as75r…`, all 668 units).** Same units, same SDK, one process each side. Native ran 4 times and the BEAM 3, in pairs under the same load (1-min load 4.5–10).
  - **Native** compiles the front end into the image. `front-end/n0/compose.py` makes `lower-core`, `lower`, the hook, `host.record` and `host.aot` (hooked `aot.bl` + `stage.bl` + a timed driver) into units. `qualify.bl candidate --additions --codegen` qualifies the result 13/13.
  - **BEAM** runs `prepare_unit` up to `lower/module->core`. The generated-module beam compile inside `prepare_unit` is timed and removed.
  - **Identity.** Descriptors and Core are `=:=` for 664/668 units. The 4 that differ are N2b's reasons.

  | | native | BEAM |
  |---|---|---|
  | front to Core, 667 units | 349.8 s (348.6–361.4 per run) | 256.4 s (255.7–263.3) |
  | median unit | 316.8 ms | 184.5 ms |
  | 20 smallest units | 104 ms | 53 ms |
  | fit | 144 ms + 28.7 ms/KB | 142 ms + 18.3 ms/KB |
  | `module->core` alone | 18.4 s | 14.5 s |
  | warm restage, 4-line unit | 91 ms | 53 ms (`prepare_unit`); 36 ms (`eval_string`) |

  - **Ratio BEAM/native.** 0.73 of totals and 0.54 at the median unit (p10 0.40, p90 1.00).
  - **Where native wins.** It is faster on 66 of 667 units and ≥ 2× faster on 20. All four size quartiles are 1.7–2.1× slower natively. Of the 10 largest units, only `tooling.pulse` is faster natively.
  - **Not counted on the native side**, because it still comes from the BEAM:
    - custody, 13.4 s;
    - the kernel, 5.5 s per SDK;
    - the MD5 round trip, a second pass of 55 s for the 75 module-generating units, plus 2.2 s on the BEAM.
  - **Against N2b.** Compiling the front end in was 1.8× faster than N2b's evaluated harness: 413–428 s against 745 s with writes and GC.
- **Why no-go.**
  - The bar was native ≥ 2× faster per unit. It is 1.86× slower, so reaching the bar needs ~3.7×.
  - Even lowering, the same BL code on both sides, is 1.27× slower natively.
  - The warm native floor (84–104 ms per unit) is above the BEAM's (`prepare_unit` ~50 ms, `eval_string` of a 4-line namespace ~36 ms), so a native compile service would make a project edit slower.
  - **So N3, N4c, N5 and C3 stay parked.**
- **Host edits (native-only, research).**
  - `host/native-data-bifs.scm`: `host/n0-now-us/0`. The image's `erlang/monotonic_time` is the virtual clock.
  - `host/native-refusals.scm`: `native-front-refusals`, the 126 remotes the compiled front end names that no host file provides. They are refused at their call, as an evaluated call was.
  - Both reach an image only through `qualify.bl derive`, never through `chez-main`'s own files.
- **Evidence.** `research/checked-tiles/evidence/n0-native-vs-beam.json`. Journal 06, "N0". Tooling: `research/native-seed/front-end/n0/run.sh` (setup / native / beam), `summarize.py`.

#### N1 ✅ `cerl` as data on the native host · S+ · native-only
- **Why.** The native image already carries `lower` and `lower-core`
  (`priv/boot/lower.bl`, `priv/boot/lower-core.bl`): bl-ANF → Core Erlang.
  They build Core through OTP's `cerl` module, which doesn't exist on Chez. No
  native host file mentions `cerl`, so every call is refused today.
- **Change.** Add a native leaf set with exactly the 42 `cerl/*` functions
  `lower`/`lower-core` call. List them with
  `grep -o "cerl/[a-z_]*" priv/boot/lower*.bl | cut -d: -f2 | sort -u`:
  - constructors such as `c_var`, `c_fun`, `c_let`, `c_case`, `c_call`;
  - accessors such as `let_body` and `clause_pats`;
  - `get_ann`/`set_ann`, `type`, and `abstract`.

  Each must build the **same tuple OTP's `cerl` builds**: Erlang records such
  as `{c_var, Anno, Name}`. Read the field order from OTP's
  `lib/compiler/src/core_parse.hrl` in the pinned Erlang
  (`nix eval --raw .#erlang` or the store path under the SDK's `erts`).
  `cerl:abstract/1` gives `c_literal` for any literal.
  - **Where.** Follow how other leaves are registered (`host/native-data-bifs.scm`,
    `host/host-leaves.scm`, the leaf registry in `chez-main/leaves.json`).
- **Done when.**
  - A BL check, run with `qualify.bl -- eval --image IMG --file F.bl` on the
    derived image, lowers 20 small ANF forms to Core on Chez.
  - The BEAM lowers the same forms with real `cerl`.
  - Each pair of Core terms is `=` (print both with `inspect`, then diff).
  - The derived image qualifies 13/13.
- **Pitfall.** Annotations carry source positions; keep their order. Fresh
  names come from the process dictionary (`erlang/put :bl_core_fresh_seq`), so
  check the native host's `erlang/put` and `get` (`host-values.scm`).

#### N2 ✅ Core Erlang from Chez to a loaded `.beam` · backend `f4e4cec5c` (2438/2438 descriptors byte-identical), front half N2b
- **Why.** Turning Core into `.beam` (`compile:forms(M, [from_core, binary])`,
  `lower.bl:474` and `:518`) must stay on the BEAM. The Core term therefore has
  to cross over.
- **Change.**
  1. Add a native `erlang/term_to_binary` that writes external term format
     (ETF) for atoms, integers, binaries, lists, tuples and maps.
     `host/host-compiler.scm` already mentions ETF; start there.
  2. Add a BEAM-side function (a new `priv/host` defn, or an existing compile
     entry) taking `binary_to_term` → `compile:forms` from_core →
     `code:load_binary`.
- **Done when.**
  - For every unit of the SDK (`$(readlink -f .bl/sdks/current-sdk)/unit-store`
    lists them; 662), the native path gives a `.beam` byte-identical to the
    BEAM compiler's, or the unit is listed with a named reason.
  - The listed units are under 5% and each reason is one of a short enumerated set.
  - Evidence goes in `research/checked-tiles/evidence/native-beam-backend.json`.
- **SDK build.** Only for the BEAM-side function.

#### N2b ✅ The front half: source → staged unit → Core on Chez · landed `b8d7345ad`: 663/667 units identical, 4 named reasons
- **Re-deriving.** `chez-main`'s host files are still the `f4e4cec5c` ones, so derive with `--base f4e4cec5c`. The default `HEAD` finds no edits.
- **What runs.** `front-end/run.sh TAG simple|all` evaluates the SDK's own
  `host/record.bl`, `host/aot.bl` (hooked) and `boot/lower*.bl` on the derived
  Chez image and stages every unit inside a real constructor context, exactly
  as `AOT/prepare_unit` does (`front-end/stage.bl`). The BEAM supplies custody
  data only: `custody.bl` (paths, closure hashes, stamps, sha256s, the SDK's
  declaration tables, generated-module MD5s) and `kernel.bl` (the constructor
  kernel: boot manifest, Core seed rows, C++ alias rows, the core/sugar phase
  libraries). `compare.bl` prepares each unit on the BEAM and checks the
  native descriptors `=:=` and the native Core's beam bytes `=` the BEAM's.
- **Why `e` refused every unit.** Not the hook: `stage-action-macros!` refuses
  a loaded macro only when *no* constructor context is open, and `e` staged
  without one (the BEAM always stages inside one). **Why `f`/`g` crashed:**
  `stage.bl`'s `nf-unit` was missing a `)`; the native reader reads the whole
  file before evaluating, so the `:unterminated-collection` diagnostic (the
  12-key raised map) came before any output.
- **Measured (2026-11-23, SDK `nhrajw…`, all 667 units, run `nf-n`).**
  Native staging 666/667 (745 s on Chez), generated-module round trip (47 s,
  75 units restaged), compare 806 s: **663 identical (99.4%)**; 4 named
  reasons (0.6%):
  - 3 `:private false` in a meta literal from the native image's own Core
    metadata (`clojure.core-ext`, `clojure.re`, `clojure.string` install into
    Core);
  - 1 `:sdk-stage-dependency-not-ready` (`live.edit.standard`).
  Previous run `nf-h`: 550. What closed the gap:
  - *Map order (83 units).* Native maps iterate in the BEAM's order
    (`host/host-values.scm`): over 32 keys, OTP 29's `erts_internal_hash`
    (`erl_term_hashing.c`) and HAMT child order (4-bit hash digits, lowest
    first); at most 32 keys, exact term order (tuples size first) when a key
    is a tuple or list. Keys holding atoms, pids, ports or refs keep the native
    order: the BEAM hashes their VM-local index. Checked directly:
    `front-end/hamt-check.sh` over 405 maps (`hamt-keys.py`, seeds 7/11/13:
    strings, small and big integers, floats, tuples, lists, byte lists,
    mixtures; sizes 5–1000): **405/405 equal on Chez and the BEAM**.
  - *`value is not callable` (19 units).* A staged namespace's names are
    masked to nil inside the private view; native host code (the reader leaf)
    read them through the Env. Host code now reads the rows the view was
    forked from, and view writes republish no linked slot.
  - *Generated-module MD5 (17 units).* `generated-md5.bl`: the BEAM compiles
    the native generated Core and answers each MD5; a second native pass
    restages those units with them (the round trip N3 will make per request).
- **Speed.** `pair` reader job (8×8, 128 samples, byte-identical output), N2b
  image `nf-f` vs this branch, load average 6–9: medians +0.9% to +4.3% over
  seven rounds (`nf-n` 112.2→115.0, 111.4→114.6, 111.4→116.2, 112.3→113.3 ms;
  `nf-o` 112.0→113.7, 113.3→115.1 ms), minima +0% to +3%. A first cut that
  scanned every small map's keys measured +2.8%; the flatmap check now reads
  the last key's rank first. The noise floor is about the same size: the
  `nf-k` image (map order only) measured +0.7%, +1.3% and +2.6%.
- **Derived image qualifies** 12/12 gates.
- **Next.** The 3 Core-metadata units (the native image's own Core carries
  `:private false` where the SDK's does not); `live.edit.standard`.
- **Done when.** Same as N2's front half: per-unit Core `=` the BEAM's, or a
  named reason, for under 5% of SDK units.

#### N3 🅿️ The native compile service, in shadow mode · replaced by N0 then N5 (see the plan)
- **Why.** Nothing in `bl` calls the native compiler.
- **Change.**
  - One Chez process per realm, started by the VM (0.86 s launch), speaking
    length-prefixed ETF over a port.
  - Request: namespace source plus the realm's macro environment. Answer: Core
    ETF, or a refusal with a reason.
  - A unit whose macros need BEAM-only code (hex libraries, OTP modules outside
    the native leaves) is refused and compiled by the BEAM.
  - **Shadow mode:** both compile, and the BEAM's output ships. Differences are
    logged with the unit name and both hashes. A `:native-compiler` key in the
    private operator config (`~/.config/beam-lisp/env.bl`) selects
    off, shadow or on.
- **Done when.**
  - Shadow mode over the whole test suite, Knowledger and Enchant
    (`/home/othman/projects/enchant`) logs zero differences.
  - The refusal rate is reported per reason.
  - Flipping to "on" passes the same suites.

#### N4 ⏳ The SDK rebuilds only what changed · split into N4a, N4b, N4d (plan table); N4c waits on N0 · S+ (N2 done)
- **Why.** A compiler edit rotates every unit's key, so all 662 units
  recompile in a 4-CPU QEMU VM (862 s on 2026-11-22). The native compiler
  compiles its own 1.8 MB bundle in 6.4 s.
- **Change.**
  - Front-end compile of SDK units through the native compiler, in parallel
    across Work's 16 cores, outside QEMU.
  - Downstream steps (`from_core`, packing, the unit store) keyed on the
    emitted Core bytes, so an output that didn't change stops there
    (early cutoff).
  - The producer is `nix/bl-drop.nix` (`native-image` derivation) with
    `priv/build/selfbuild.bl`.
- **Done when.**
  - A compiler edit that changes no output finishes an SDK in under 2 minutes.
  - An edit that changes one unit's output rebuilds one unit.
  - Both are measured end to end.
- **Measured (2026-11-23).** The foundry events file is capped at 64 KB, so read the full logs on the build station: `ssh beam-build-station "nix log /nix/store/<drv>.drv"`. Every line in those logs appears twice, so de-duplicate before summing.
  - **A one-file `priv/std` edit (gate 19b): 440 s, with 6 units compiled, 661 cached, and the compiler reused whole.**
    - About 100 s before the library starts: Nix evaluation, copying to nixbuild.net, and the unit archive (14 s).
    - The library derivation, 321 s. Its producer is 159 s. Inside the producer:
      - the unit work is only 40 s: `verify-restored` 17.7 s, `copy-restored` 16.6 s, `closure-hash` 5.7 s. The 6 compiles themselves take seconds;
      - the fixed phases are each 2–15 s: setup, materialize, prepare-release, check-floor, assemble-runtime, prime-library-inputs, stage-library, child install/boot, assemble-library-image, prime-freshness, provenance, retain-unit-store.
    - After the producer: `copy-sdk-library` 24 s, then the image and selection.
    - So the edit's own compile is under 10% of the cost. The rest is a fixed pipeline paid in full for every edit.
  - **A change under `priv/boot` (rotates the compiler key) adds the bootstrap.** Generations P, B and C each recompile all 91 boot and host units: 592, 453 and 465 s in the batch-20 log. `host.aot` alone is 104–115 s per generation. The library children then recompile every SDK unit, 416–461 s each with four in parallel.
  - **Gate 20's 2848 s is not representative.** Its `previous-sdk` was a pre-batch-17 SDK, because the integration tree had been checked out at `7e4b5823a` for a baseline. `prepare-checkout-sdk` takes `previous` from the tree's `current-sdk` when the job starts. After checking out an old commit in a tree, expect the next preparation to rebuild everything.
- **Where the leverage is, in order.**
  1. **Don't build an SDK to try a `priv/std` or `priv/lib` edit.** The fixed pipeline (~400 s) can't get near 2 minutes by trimming phases. The qualitative fix is a hot path: let the warm realm load changed SDK namespaces from the checkout, the way project code loads, instead of refusing with `sdk_forwarder_route_changed`. Keep the SDK build for qualification and release. This is the inner-loop table's "`priv/` code: No hot path" row, and it is the single largest remaining edit cost.
  2. **Restored units by reference.** Units are content-addressed, so link them and verify by digest instead of re-verifying and copying (34 s of the 40 s unit work).
  3. **Generation C.** It only shows that B is a fixpoint (C = B), at the price of a third full compile (465 s). When B's unit bytes equal P's, skip it. Otherwise check the fixpoint per unit.
  4. **Per-unit cutoff across a compiler-key change.** Key each unit on its source plus the bytes of the compiler units it actually loads, not on the whole compiler key.
  5. **Native front end.** Compile with Chez on Work's 16 cores, outside QEMU (N2b: 663/667 identical).
- **Pitfall.** Two consecutive layered SDKs must both prepare. On 2026-11-22
  the first layered SDK broke the next preparation (`d2cd91781`). Every
  SDK-layout change is qualified by preparing twice in a row, across a
  compiler-key rotation.

### C — native compile throughput (only matters for edits and SDK builds)

#### C1 ✅ Emitter `ident` without the per-character join · H · native-only
- **Why.** `ident` (`research/native-seed/src/native/scheme.bl` line 32) turns
  every emitted name into `"v"` plus `"_<code>"` per character. It maps over
  the characters and joins the list, for every name, every time.
- **Change.** Keep the output byte-identical. Either memoize per input text in
  the process dictionary (key: the binary), or build it with one
  `erlang/iolist_to_binary` over the mapped list.
- **Done when.**
  - `candidate --codegen` passes 13/13 with a fixpoint.
  - `pair` (256 runs: `--reps 8 --rounds 8`) shows the same bytes; report both
    medians. If it isn't faster, record that and don't merge.

#### C2 ❌ dropped (prototype 0.4%, noise) — Interned names on the native host · S · native-only
- **Why.** `string-hash`/`equal-hash` take ~4–5% of the reader job. Names are
  strings, so every lookup and every memo pays a hash.
- **Change.** The reader interns symbol and keyword names (one Chez symbol or
  canonical string per name), so host lookups can use `eq?` tables. Start
  from `native-key-canon` and `native-raw-get` in `host/host-values.scm`.
- **Done when.** `derive` qualifies 13/13, and `pair` shows the same bytes and a
  measured gain.

#### C3 🅿️ Typed private IR (fixed-layout nodes, positions as one tuple)
After N3. Journal 06, "What the lookup census says about the IR", has the
census to start from.

### T — tools

#### T1 ✅ A host check without an SDK build · S
- **Why.** `priv/` edits have no inner loop. `scripts/check-runtime-hosts`
  compiles changed `priv/host` modules with the existing compiler and tests them
  in a capped VM. It fails before starting: `elixir is not on PATH`, and
  `nix develop` has no shell to give it.
- **Change.** Give it its tools the way the SDK producer does: the `erlang` and
  `elixir` flake packages (`nix build .#erlang .#elixir`) put on `PATH` by the
  script itself. Then make it work against the current SDK image:
  `--sdk-image "$(readlink -f .bl/sdks/current-sdk)/image"`, or whatever the
  script needs (it wants `priv/precompiled.term` and `ebin/`).
- **Done when.**
  - With an unchanged `priv/host`, it runs `test/bl/js_local_shadow_test.bl`
    green in under 5 minutes.
  - With a deliberate break in one host function, the same check fails.
  - The inner-loop table above gets a `priv/host` row with the measured cost.

### W — the test runner

#### J4 ✅ Two small JS disagreements · H · `priv/lib/js` · landed batch 9
- `(- 0.0)` prints `0.0` on JS, `-0.0` on the BEAM; `erlang/-/1` has no JS leaf.
- **Done when.** Both answer as on the BEAM; a js_diff case for each.

#### W3 ✅ `seed_runtime_abi_test` fails on a second run in the same realm · landed batch 18 (`db6b22fba`)
- A 54-file `bl test` set run twice in one warm realm: pass 1 green, pass 2 `seed_runtime_abi` 3 passed/8 failed with
  `/tmp/bl-seed-host-supervisor-src/anf_interpreter.bl: no such pinned host source`. `host-scratch` removes and recreates
  that directory each call, so a child process or a recorded path is the suspect.
- **Found.** `host-scratch`/`scratch` used fixed names in `/tmp` and every call begins with `rm_rf!`. `/tmp` is shared by
  every realm and VM on the machine, so a concurrent call with the same name (the daemon runs each request as its own
  process) deletes the first call's directory mid-compile; `compile-host` checks `File/exists?` per entry, so the victim
  reports `no such pinned host source` for whichever suffix it had not reached. No preceding file is needed — two
  concurrent runs of the file in one realm reproduce it.
- **Fix.** A suffix of OS pid + `unique_integer` on both helper directories, and a test
  `a-scratch-host-directory-belongs-to-one-call` that fails against the old helper (12/1) and passes after (13/13).
- **Gates run by the agent.** Cross-realm collision fixed; `seed_runtime_abi` twice warm 13/13; W1's ten files both
  orders 10/10; the 53-file set twice in one warm realm, both green; realm stopped.
- **Done when.** The ten-file gate and `seed_runtime_abi_test` warm twice pass on the integration SDK.
- **Left undone.** `priv/build/seed.bl` names its compile scratch
  `/tmp/bl-seed-host-<unique_integer>` (no pid), so two producer VMs can collide the same way. It is an SDK input;
  fold the pid suffix in with the next `priv/build` change.

#### W4 ⏳ Two identical `bl test` requests in one realm collide inside the compiler · S+ · BL · from W3
- After W3, a 4-way same-realm run of identical suites still fails: `floor-ebin/1 is undefined or private` and
  `SDK declaration metadata is unavailable for seed/host-sources`. Not `/tmp` — namespace/compiler-level state.
- **Done when.** Four identical `bl test` requests in one warm realm all pass, and a deliberately shared path still
  collides (the isolation is the compiler's, not a fixed-name accident).


#### W2 ✅ Two files still fail inside a multi-file test run · S · BL
- On the batch-5 and batch-10 SDKs: in a run of the ten realm/seed/JS files (W1's list),
  `realm_ownership_test` fails `a-shared-namespace-is-named-from-its-hash` with
  "Shared namespace admission refused … {:reason :compiler-authority-unavailable}" and
  `seed_runtime_abi_test` fails 8 assertions ("publishes … public surface" → false). Both pass alone.
- W1 made the runs coherent; something an earlier file does still breaks the compiler authority and
  the seed publication. Bisect which earlier file, and fix the isolation.
- **Done when.** The ten files pass in both orders.
- Card `0c9a9cf3d` records the first observation.

#### W1 ✅ A multi-file `bl test` breaks after a realm-retirement test · S · BL
- **Why.** On `main` (checked 2026-11-22 on the batch-2 SDK, without U1), `./bin/bl test` with
  `test/bl/contextual_realm_retirement_test.bl` first and nine realm/seed/JS files after it:
  - the first file fails one case, `shutdown-retains-pending-real-consumers-in-the-manager`
    (expected `{:pending 1, :drained 0}`, actual `{:pending 1, :drained 1}`);
  - every later file is INCOHERENT: `crashed while loading: undefined var: <ns>/deftest`.

  Later errors in the same run include module `…Rn-lib`/`…Seed-support` "is not available".
  Each file passes when run alone. One test leaves the warm VM's realm or test harness in a
  state that the next file can't load in.
- **Do.**
  1. Bisect which earlier file breaks which later one; start with the retirement test then one
     other.
  2. Find what state survives: the ward's per-file realm, the test namespace's refers, the realm
     manager.
  3. Fix the isolation, not the test.
- **Done when.** The ten files named above pass in one `bl test` call, in that order and reversed.
- **Inner loop.** `scripts/check-runtime-hosts` for `priv/host`; otherwise a branch plus the
  integration gate.

### J — JavaScript target

#### J1 ✅ Four JS test files fail on `main` · S · BL (`priv/lib/js`)
- **Why.** These four fail at HEAD, both with and without the 2026-11-22
  shadowing fix. Both sessions checked:
  - `test/bl/js_compiled_core_test.bl`
  - `test/bl/js_compiler_boundary_test.bl`
  - `test/bl/js_diff_test.bl` (3 cases: `beam-and-js-print-every-case-identically`,
    `beam-lisp-evaluated-in-js-gives-the-beams-answers` ×2)
  - `test/bl/js_native_live_test.bl`

  Three of them stop with `priv/lib/js/emit.bl: emit-invoke: priv/lib/js/emit.bl:290:
  SDK declaration metadata is unavailable for system.ir/call-site`. The other 18
  `js_*` files pass.
- **Do.**
  1. Read `priv/lib/js/emit.bl` around line 290, and find where SDK
     declaration metadata is looked up (grep `declaration metadata` in
     `priv/host/aot.bl` and `priv/lib/js/`).
  2. Find why `system.ir`'s rows are missing. Candidates:
     - `system.ir` isn't in the selected SDK's metadata;
     - the JS build runs with no constructor context;
     - a recent change to retained definition terms (`5ceb03aab`, "Compact
       retained definition terms…").
  3. Use `git log -S'declaration metadata' -- priv` to find when the message
     appeared, and bisect against an older SDK only if that's cheap.
- **Done when.**
  - All 22 `test/bl/js_*_test.bl` files pass in one run:
    `work run --memory 4G --timeout 3000 -- ./bin/bl test $(ls test/bl/js_*_test.bl)`,
    about 8 minutes on a warm SDK.
  - `js_local_shadow_test.bl` and `js_exact_global_test.bl` still pass.
- **SDK build.** Yes. Lane "SDK inputs".

## Parallel lanes

Cards in one lane conflict; lanes run at the same time.

| Lane | Cards | Shares |
|---|---|---|
| Platform (Rust) | U1 → U2 | one platform build |
| SDK inputs (BL runtime, `nix/`) | J1, U3, U4, then the BEAM half of N2 | one SDK build at a time |
| Native only | C1, C2, N1 → N2 (native half) | `chez-main` as base; no SDK build |
| Measurement | U5 | needs a quiet machine |

## Done

| | Work | Result | Commit |
|---|---|---|---|
| ✅ | J4: JS unary minus keeps the float sign | Floats negate their sign bit; `erlang/-/1` leaf; `js_diff` 547/547 | (batch 9) |
| ✅ | T2: three tests corrected; seed floor helper finds the SDK ebin | emit_test 138, seed_publication 227, cold_namespace_load 2, realm_namespace 17 | (batch 11) |
| ✅ | U1c: one manifest line per searched directory | Misses batched per directory with an entry digest; the client lists each once; declared roots only from top-level `:paths`. Manifest after ten files 1,348 → ~21 lines; project statx −73.6%; warm run 87–96 → 77–87 ms, 7,509 statx per request | (batch 10) |
| ✅ | U1: the client digests what the realm loaded | The loader records each resolved source and absent candidate in `.bl/realm-sources.v1` (epoch token, self-healing); the client digests declared roots plus exactly those. An edited test helper is seen; warm run 152 → 87–96 ms, `--version` 77–80 ms. Next (U1c): 2,506 absent lines and ~35k statx per request | `2d71662e7` |
| ✅ | `Loader/ns_home` answers in JavaScript | A page has no realms (`:global`); all 23 js_* files pass | `2d71662e7` |
| ✅ | U8 sealed seed metadata (`seed_artifact_metadata!`, 5.2%) | producer writes `priv/seed-metadata.term` (105 rows, 716 KB); immutable-root reader checks manifest digest per row; derive 2.2 ms/seed vs sealed 0.5 ms/seed, table read 8.3 ms; 447-assertion equality test | `lane/cold-start` |
| ✅ | U9: the warm request floor, measured | 50.7 ms median = engine capture 22.8 + project generation 11.1 (fixed, recomputed) + VM handler 13.6 + client exec ~3 + connect 1.2 + exit 0.8. Three removals proposed; 1.5–2 ms reachable | `3e6b30096` |
| ✅ | W2: multi-file runs stay isolated, and warm requests keep the engine env | The ward loads its test library at `:global` (a realm-scoped compiler generation made the authority decline every later file's certificates); workers exit `:shutdown` so linked servers die with their file; `bl run` interns `*command-line-args*` at `:global`; the daemon stops tombstoning the VM's own `BL_ROOT`/`BL_EBIN`… on warm requests (that made the seed floor fall back to `<checkout>/build`, and a client could relabel the image). Ten files 10/10 in three orders; seed_runtime_abi 11/11 warm | (batch 15) |
| ✅ | U8: seed metadata sealed at SDK build time | The producer writes `priv/seed-metadata.term` (105 rows, proofs per seed); an immutable image reads it, checking version, compiler key, decoder MD5 and the manifest digest per row. Derive 2.4 ms → read 0.5 ms per seed; cold run median 3,190 → 2,810 ms (4 pairs, load ~20) | (batch 14) |
| ✅ | U7: execution receipts derived on first use | `Env/mark_emitted` stored a computed receipt (an ANF walk) for all 1,438 definitions a cold start publishes; it now stores `{:deferred …}` and the row's decoder derives it. Republication of 158 definitions 70 → 17.7 ms; cold start median 3,375 → 3,247 ms (4 pairs). Batch preload, `find_file` memo and "something compiles" measured and dropped | `0c9a9cf3d` |
| ✅ | U6: SDK files hashed once per VM | Store files hashed once; artifact metadata and kernel disassembly reused; a warm inventory walk 118 → 98 ms; cold run paired with the previous SDK 3,594 → 3,483 ms median (load ~10). U5's "1.5 s of repeated walks" was too high: a repeat walk is ~100 ms | `c8a408a94` |
| ✅ | J3: `js_compiled_core` passes | Fixed by W1's realm-local link fix: 11/11 | `c8a408a94` |
| ✅ | Portable JS leaves, literate JS namespaces, `system.inputs` (from another session, lane/rich-edit) | `js_portable_leaves` 77/77, `system_inputs` 12/12, `js_boot_order` 3/3 | `c8a408a94` |
| ✅ | W1: multi-file test runs stay isolated | `vm.manager` shutdown drained the realm running the tests (now per-file scope); the compiler baked a realm-local provider's platform module name ("module … is not available"). Ten realm/seed/JS files no longer go incoherent; an edited test helper is seen after a retirement | `e4973a0f3` |
| ✅ | SDK lock wait visible and bounded | A waiter prints the holder and a heartbeat; `BL_SDK_LOCK_WAIT` bounds it (exit 75); `BL_SDK_REUSE_CURRENT=1` uses the current SDK; `realm stop` never queues. `checkout_sdk_lock_wait.py` passes | `e4973a0f3` (from another session, d9efc7f5d) |
| ✅ | U5: where a cold start goes | 4.3 s at load ~4: `:beam_lisp` start + `vm.native` ~65–70%, repeated SDK tree sweeps ~35%; client + erts + deps < 8% | `33fd76cc4` |
| ✅ | U4b: Env custody cleanup by exact key | Profile keys and handoff targets kept in the owner's own row; departure and offer lookups no longer scan 22,800-row tables. Env own time per spawn 1,904 → 971 µs, reductions 90k → 24k. 27 custody/execution/env files green with `BL_CUSTODY_SCAN_CHECK=1` | `90e0347ae` |
| ✅ | T1: `scripts/check-runtime-hosts` works | Brings its own erlang/elixir, runs against a store SDK image: `priv/host` edits checked in ~40 s (+2.5 min when `env.bl` changes), a deliberate break fails | `e69f3863f` |
| ✅ | U3: a failed preparation names its first cause | The refusal carries the first `error:` lines from the job's events; `preparation_failure_cause_test` 11/11 | `e69f3863f` |
| ✅ | J1/J2: JS tests and runtime | Tests build from the SDK's library roots; JS value-equal collection keys, `-0.0` printing, alias-only lazy cycles: 21/22 js files, `js_diff` 478/478. Open: `js_compiled_core` (J3) | `e69f3863f` |
| ✅ | U2: a warm VM that dies at start fails the request at once | The client stops waiting when the VM it started exits and prints the log tail: 18 s including VM start, was 120 s of silence. cargo test 114 pass (1 environmental builder test, pre-existing) | `ad3274b1b` |
| ✅ | N1: `cerl` as data on the native host | 38 `cerl` functions build OTP 29's exact records on Chez; the real `lower` runs on Chez; 75 rows BEAM vs Chez byte-identical; derived image 12/12 qualify gates | `701802dc9` |
| ✅ | C1: emitter `ident` in one `iolist_to_binary` | `candidate --codegen` 13/13 with fixpoint; pair: same bytes, emit 26.7 → 25.7 ms (median 123.9 → 119.8 ms, near noise) | `aacc7bd25` |
| ✅ | Scratch removed | `research/native-seed/out` 32 GB → 2.7 GB (kept `cutover-core-build-v3`, `chez-main`) | 2026-11-22 |
| ✅ | SDK preparation from a layered previous SDK | The unit archive read the image's linked `unit-store` and refused the link, so every preparation after the first layered SDK failed; it reads the library's directory: 862 s key rotation, passes | `d2cd91781` and after |
| ✅ | Disk floor | User timer `nix-store-floor` (every 15 min): below 40 GB free, a bounded `nix-store --gc` toward 80 GB; dry-run checked | `~/.config/systemd/user/nix-store-floor.timer` |
| ✅ | Durable base image | Image links name resolved files; `research/native-seed/out/chez-main` (21 MB) qualifies on its own | (this batch) |
| ✅ | SDK in two layers | Library reused across native edits: a Rust edit builds in 82 s (cargo included), same library path; a key rotation in 13 min | `2fa24ed63` |
| ✅ | Balanced shards | Largest-first to the least-loaded shard: 167–197 s per shard (was 236–306 s); library producer 222 s | `2fa24ed63` |
| ✅ | Keyword calls via `native-raw-get` | Codegen fixpoint at generation 2, 13/13; median 133.2 → 130.1 ms | `0b79f6231`, `dd34d93bb` |
| ✅ | Macro path | One head lookup, cheap `datum` and bound checks, reused `&env`, prefix tests; 13/13, 19,532 BEAM checks; median 124.3 → 117.2 ms, compile 87.0 → 80.2 ms | `8e58ace04` |
| ✅ | Native atom write linear in its value | Identity table replaces the visited list; derived image 13/13; 1,000 writes onto a growing map 2.2 s → noise | (this batch) |
| ✅ | SDK sharding on (4 ways) | Root fix: shards are app-shaped (`beam_lisp-0.1.0`); verify: 662 units from scratch, none differ; end to end with a rotated key: producer restores all 662, library 297 s vs 575 s; skipped when the previous store is current | `4229cfbc1` … `96d43a428` |
| ✅ | iodata emitter | 13/13, byte-identical on the original bundle; emit 29.2 → 26.6 ms, reader job 126.3 → 121.3 ms | `959d09c7b` |
| ✅ | Direct tuple construction | Native fixpoint S3 = S4, 13/13 gates; compile min 84.8 → 82.3 ms; BEAM tests pass | `cc49cd44d` |
| ✅ | Native bundle export (metadata self-hosted) | Byte for byte in 2 s; leaves from the image registry; additions qualify 13/13 | `10cef613b` and after |
| ✅ | Disk: SDK preparation pruning, GC roots for tools and PCRE2 | 197 → 14 preparations; GC can no longer take a tool | `56cc89c8c` |
| ✅ | `qualify.bl`: codegen candidates, refresh, eval, `--source-root` | Code-changing compiler work has a fixpoint mode | `56cc89c8c` and after |
| ✅ | JS runtime copies, seed test floor | Both BEAM failures fixed; 315 checks pass | `32ad701fa` |
| ✅ | `env.bl` `:tools` | Tools as Nix packages; `qualify.bl` uses them | `1fab5d6dc` |
| ✅ | Escape scan + table, one-pass `maps/without` | Reader job 133.5 → 121.2 ms | `e0fedbf6a`, `f665458be` |
| ✅ | BL-hosted qualification; Python retired | Cold 20.8 s, repeat 0.4 s | `8a837114f` |
| ✅ | Host lookups: small-map find, env index, `str`/iolist, keyword memo | 144 → 126 ms | `a09bf6138` … `b669774cc` |
| ✅ | Checkout client digest cache | Warm `./bin/bl run` 410 → 60 ms | `0799b257c` |
| ✅ | Warm VM stderr, local-lock wakeup | Errors reach the client; lock waits 4.3 s → 0.19 s | `52ef85948`, `60aede9b3` |
| ✅ | Chez substrate qualified | Byte-identical fixpoint, 461 actor checks × 3 budgets | `c69269bc5` |

## Prototypes kept, not merged

| | Prototype | Finding | Where |
|---|---|---|---|
| 🧪 | Macro answer per call head per form | 57% hits, no gain; superseded by one lookup per call | dropped |
| 🧪 | C1 `ident` memoized in the process dictionary (on top of one `iolist_to_binary`) | qualified 13/13; same bytes; pair median 119.5 -> 119.7 ms, emit 26.3 -> 25.0 ms: no better than the plain `iolist_to_binary` (emit 26.7 -> 25.7 ms); not kept | dropped |
| 🧪 | C2 identity-keyed first level in `native-fetch-value` (profile: hashing is `table-ref` on the equal-keyed global cache, 604 of 7130 samples inclusive, `string-hash` 190 self, callers `expand-macro`, `macro-lookup`, `compat-reduced?`; the reader's own symbols/keywords are not hashed) | derive qualified 12/12 (`qualify`), same bytes; pair median 111.24 -> 110.84 ms (0.4%), emit 24.59 -> 24.57 ms: within noise; not kept | dropped |
| 🧪 | U7 batch preload of the cold-start module set (`code:ensure_modules_loaded`, 369 modules from a recorded cold run, `-s` module before `start_cli`) | the batch itself takes 116-183 ms and the cold run is unchanged: 3283 / 3547 / 3360 ms against 3313 / 3479 / 3340 ms without it. Loading is about 4% of a cold start and is not serialized behind `code_server` hops; most of the 21% `code_server:call` + `gen:do_call` own time in the sampler is a process parked in `receive` that `process_info` reports as running | dropped |
| 🧪 | U7 "something compiles" (`compile_sdk_source!`, 3.1% inclusive) | nothing is compiled on an unchanged SDK: the function stages and admits library Sources (callable-ready checks, retention). The only `compile:forms` work is the 7 native host stubs (14 `compile_descriptor` calls, about 0.5% of samples); their bytes embed the physical `.so` path, so they cannot be sealed before the image has its store path | dropped |
| 🧪 | U7 native-host bootstrap (782 ms in the checker) | a checker artifact: the edited hosts change the live compiler key, so the primed `native-declarations` miss and 6 Sources are re-read. On the real SDK `bootstrap_sdk_native_hosts!` is 1.2% of samples | dropped |
| 🧪 | U7 `Loader.find_file` memo | 2.3% inclusive; a memo would need a stat of every earlier search dir to keep shadowing safe, so at most about 1% | dropped |

## Scratch

| Tree | Owner | Removed when |
|---|---|---|
| `research/native-seed/out/chez-main` | base image for candidates and pairs (matches `main`) | replaced by the next qualified image |

