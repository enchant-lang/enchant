# Native compiler roster

The goal: one self-hosted native compiler on Chez that `bl` uses by default.
No user-visible change. An unchanged request costs ~1 ms of fixed floor
(200× warm BEAM's 158 ms). An edit costs in proportion to what it changes,
when building `bl` and when using it, cold and hot.

Status: ✅ done (passed the integration gate) · 🧪 branch ready, waiting for the gate · 🔨 in progress · ⏳ ready to take · 🔒 waits on another card · 🅿️ parked.
The journal (`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`)
holds the reasoning; `research/checked-tiles/evidence/` the measurements.

## Where it stands (measured 2026-11-22)

| What a user waits for | Now | Target |
|---|---|---|
| Warm `./bin/bl run` in this checkout | 550 ms before the scratch cleanup; remeasure (card U1) | ~1–5 ms |
| Warm installed `bl run` of `(println 1)` | 80 ms | ~1–5 ms |
| Cold `bl run` | 7.6 s | ≤ 1 s |
| Compile the reader file (read + compile + emit) | native ~117 ms median, warm BEAM 158 ms | only matters on edits |
| SDK after a compiler edit / a Rust edit | 862 s / 82 s | ~1 min / ~1 min |
| Native compiler on the user path | **not at all**: it emits Scheme only | the default compiler, BEAM kept as fallback |

The one rule behind every card: a cost should scale with what changed, not
with the size of the tree, the SDK or the compiler.

## How a card gets done: work, check inside, one integration gate

An agent does the whole card and checks it right where it works, in seconds to
a few minutes. It never waits on an SDK build. **The integrator (the session
that fanned the cards out) merges finished branches in batches, builds one SDK
per batch, and runs the gate tests.** A card is ✅ only after that gate.

### Where an agent works
- **In its own git worktree** on its own branch, never the shared checkout.
  Commit there freely, and finish with a clean, committed branch.
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

### The inner loop, per tree (measured 2026-11-22)

| You changed | Check it inside, like this | Cost |
|---|---|---|
| `research/native-seed/src/native/*.bl` (compiler or emitter source) | `cd $WT && QUALIFY_ROOT=$WT work run --memory 4G --timeout 900 -- $MAIN/bin/bl run research/native-seed/chez/qualify.bl -- candidate --image $MAIN/research/native-seed/out/chez-main --out OUT --source-root $WT [--codegen]` | tens of seconds; first run of a new stage ~1 min |
| `research/native-seed/host/*.scm` (native host) | the same, with `derive --image $MAIN/research/native-seed/out/chez-main --out OUT` | the same |
| any native speed claim | `... -- pair --base $MAIN/research/native-seed/out/chez-main/prelude.scm --cand OUT/prelude.scm --out OUT2 --reps 8 --rounds 8` | a few minutes |
| a native behaviour | `... -- eval --image OUT --file CHECK.bl` runs a BL file on the native image | seconds |
| `tooling/drop/` (Rust client) | `cd $WT/tooling/drop && CARGO_TARGET_DIR=$WT/.cargo-target work run --memory 4G --timeout 1500 -- nix shell nixpkgs#cargo nixpkgs#rustc nixpkgs#gcc --command cargo test --release` | 66 s cold, seconds warm |
| client speed or behaviour | run the binary cargo built, the way `bin/bl` does: `$WT/.cargo-target/release/drop-launcher --checkout $MAIN -- run /tmp/x.bl`, with `BL_CHECKOUT_PLATFORM`, `BL_BIN` and the rest exported as in `$MAIN/bin/bl` | ms |
| a BL file the coordinator or a script runs directly (`nix/*.bl`, `scripts/*.bl`, `research/**.bl`) | `$MAIN/bin/bl run FILE ...` or a test file next to it, on the main SDK | seconds |
| `priv/` code (runtime, library, compiler) | **No hot path:** reload refuses SDK namespaces (`sdk_forwarder_route_changed`), and `:shadow` only reaches callers inside the project, not library-to-library calls. Check the logic by copying the changed function into a scratch namespace under your own project dir and calling it from a test there (`$MAIN/bin/bl test`). Then hand the branch over with the exact gate test files listed. | seconds; the real check is the integration gate |
| measurement only | `work run` the probe with 3+ runs; report median and spread and the machine load (`uptime`) | — |

`scripts/check-runtime-hosts` is meant for host checks without an SDK, but it
is stale: it needs Elixir on `PATH`, and the flake has no dev shell. Fixing it
is card T1.

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
1. Merge the branches into `main`.
2. Run `work run --memory 4G --timeout 3000 -- scripts/prepare-checkout-sdk`.
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

### U — the request path (what every user pays)

#### U1 🔨 The checkout client inventories declared inputs only · S · Rust · branch `lane/client` (2026-11-22)
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

#### U2 🔨 A warm VM that dies at start fails the request at once · S · Rust · branch `lane/client` (2026-11-22)
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

#### U3 🔨 A failed SDK preparation names its first cause · H/S · BL · branch `lane/tools` (2026-11-22)
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

#### U4 🔒 Lock work per request proportional to change · S+ · BL runtime (after U1)
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

#### U5 ⏳ Where a cold start goes · S · measurement only
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

### N — the native compiler on the default path

#### N1 🔨 `cerl` as data on the native host · S+ · native-only · branch `lane/cerl` (2026-11-22)
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

#### N2 🔒 Core Erlang from Chez to a loaded `.beam` · S+ (after N1)
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

#### N3 🔒 The native compile service, in shadow mode · S+ (after N2)
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

#### N4 🔒 The SDK rebuilds only what changed · S+ (after N2)
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
- **Pitfall.** Two consecutive layered SDKs must both prepare. On 2026-11-22
  the first layered SDK broke the next preparation (`d2cd91781`). Every
  SDK-layout change is qualified by preparing twice in a row, across a
  compiler-key rotation.

### C — native compile throughput (only matters for edits and SDK builds)

#### C1 🔨 Emitter `ident` without the per-character join · H · native-only · branch `lane/native-speed` (2026-11-22)
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

#### C2 🔨 Interned names on the native host · S · native-only · branch `lane/native-speed` (2026-11-22)
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

#### T1 🔨 A host check without an SDK build · S · branch `lane/tools` (2026-11-22)
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

### J — JavaScript target

#### J1 🔨 Four JS test files fail on `main` · S · BL (`priv/lib/js`) · branch `lane/tools` (2026-11-22)
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

## Scratch

| Tree | Owner | Removed when |
|---|---|---|
| `research/native-seed/out/chez-main` | base image for candidates and pairs (matches `main`) | replaced by the next qualified image |

