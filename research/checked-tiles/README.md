# Checked tiles

Edit an ordinary Enchant channel function, prove its byte law, and render a frame from the Ora film on BEAM, CPU and GPU. The default run changes a helper while an old CPU frame is in flight, switches to a second independently authored function, then tries an invalid boundary edit. Each run owns a fresh local directory.

From the checkout root:

    research/checked-tiles/run --require-gpu

Open the printed directory's original.png and current/frame.png. Each revision retains its BL, generated C/OpenCL, Lean theorem, BEAM output and timing receipt. Read exercise.json to see which request completed after activation. Compare cpu_1, cpu_4, cpu_lookup and gpu_whole_call within one receipt. Timings include output allocation and the GPU upload and download. Setup and the BEAM reference call are measured separately.

To edit the source yourself:

    cp research/checked-tiles/examples/wash.bl /tmp/my-wash.bl
    research/checked-tiles/run --watch --source /tmp/my-wash.bl

Change the helper body to (quot (+ (* 3 x) 255) 4) and save. Refresh current/frame.png after acceptance. Replace the body with 254 and save. The checker reports channel 255 and the previous image stays current. Ctrl-C ends the watch. Use --image FILE to supply a different frame, --once for one revision, --cpu-only on a machine without a GPU, or --width, --height and --tile to change the work. --out must name a new directory.

This workstation experiment pins its immutable Enchant SDK, Lean, OpenMP C compiler and OpenCL loader in tools.json. It requires Python 3.10+, ffmpeg, a systemd user session, and a GPU ICD for hardware execution. The runner caps the whole process tree. It uses the project's pinned SDK executable, with one cold BL process at a time. It never chooses an installed bl from PATH.

The pure fragment admits natural literals, unary definitions and calls to preceding helpers, addition, multiplication, positive literal quotients and comparisons in if. Inputs are byte channels. All intermediates must fit unsigned 32 bits. RGB rows have three channels per pixel and positive dimensions. The wash specializes constant white-over-destination integer blending. Alpha, color spaces, neighboring pixels, and stateful functions need different contracts.

The protected law requires input ≤ output ≤ 255 for every byte. The normal BL compiler executes the original function for the entire domain and the input image. Lean checks the lowered expression against all 256 observed values and checks the universal channel law. The geometric model covers unique tile ownership, reconstruction and clipped edges. Independent hardware differentials include every channel and partial tiles. The reader, emitter, proof/data export, C/OpenCL compiler, driver, and runtime remain trusted or tested implementation boundaries. Publication is a single-writer local prototype with an atomic symlink switch. Its historical build artifacts stay on disk for inspection.

See [the design discussion](journal/01-bend-and-enchant.bl.org), [the experiment log](journal/02-experiment.bl.org), [the live compiler design](journal/03-live-compiler.bl.org), and [the native concurrent Core proposal](journal/04-native-concurrent-core.bl.org).

Add --sweep to measure the same operation on an 8×8 patch, a 320×180 RGB frame and a 1920×1080 RGB frame. The two larger inputs repeat the captured scene bytes. Each result is checked against the exhaustive table.

The default placement runs every admitted route, checks identical output, and selects the lowest median whole-call time on this frame. The finite-domain lookup baseline uses the 256 observed and independently checked values as an executable table. Use --placement device to publish the GPU result whenever available. --require-gpu always requires a successful hardware render, including with measured placement.

### Compare Bend and FFmpeg on the same bytes

On this workstation, one command prepares pinned Bend 2.0.40 and NVIDIA CUDA 12.9 headers/NVRTC in temporary storage, runs the comparisons, and removes the temporary toolchain. It downloads the Bend source and about 93 MB of CUDA archives. BEND_TREE and CUDA_HOME select existing installations. Use the session directory printed by the main exercise.

    research/checked-tiles/comparison/run SESSION

The comparison includes prepared Enchant CPU and OpenCL processes, the independent Bend fork/join implementation, FFmpeg, and the existing film worker’s EGL executor with a hand-authored wash shader. Resident EGL draw times exclude upload/readback. The device and driver are recorded separately from the OpenCL device.

For a manual Bend/FFmpeg comparison, use the default exercise session. The optional comparison needs Bun, Clang 19+, and the pinned Bend source. GPU builds on Linux also need CUDA headers, libcuda and NVRTC under CUDA_HOME. The NVIDIA driver/OpenCL loader are sufficient for the main Enchant exercise.

    git clone https://github.com/bendlang/bend /tmp/checked-tiles-bend
    git -C /tmp/checked-tiles-bend checkout --detach 9c586f094f4fc88bef440dc8b4d77a2f92c257cc
    systemd-run --user --scope -p MemoryMax=2G python3 research/checked-tiles/comparison/compare.py SESSION /tmp/checked-tiles-bend --require-gpu

Set BUN and CC to the executable paths when they are outside PATH. Remove --require-gpu for a CPU-only Bend build. The comparator verifies Bend compiler source identities and compares the entire output with the accepted BEAM wash. It measures fresh processes including file IO, alternates launch order, and records build time. The Enchant receipt measures warm transform calls. The FFmpeg comparator uses its standard lutrgb filter on a decoded frame; the existing scene worker supplied the retained input image.

### Recheck and read the record

Run the negative controls against a session with an accepted revision:

    python3 -B research/checked-tiles/controls.py SESSION

They compile a deliberately wrong GPU boundary, submit an incorrect coordinate theorem to Lean, and try four inadmissible source functions. All run outside the published directory. The archived evidence includes the original, first wash, helper edit and posterized output.

Read the journals as Org or open the Enchanted dossier renderer locally. It uses ~/projects/enchanted-skills by default and binds only to loopback. Ctrl-C stops it.

    research/checked-tiles/journal/view
    research/checked-tiles/journal/view discussion
    research/checked-tiles/journal/view pipeline
    research/checked-tiles/journal/view core

The original discussion and subsequent experiment are separate entries so the initial predictions can be compared with the measurements.

## Browser workbench

Run the web server from the checkout on the workstation with the pinned tools and ffmpeg available.

```sh
systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=256M \
  python3 -B research/checked-tiles/server.py
```

Open <http://127.0.0.1:8765/>. Choose **White wash**, select **Require physical GPU**, and press **Check & render**. Drag the divider or focus it and use the arrow keys. Open the receipt to see the exact accepted BL, generated Lean, axiom report, backend samples and SDK. The timing table reports medians of five frame calls. Lean time includes its process startup.

Select **Broken edge** and check again. The counterexample identifies input 64 and output 63. The frame, receipt and revision continue to describe the last accepted run. **Run rehearsal** runs the fixed multi-revision CLI scenario, including the stale completion and ELF retirement checks, and publishes its final posterized frame. Its starting source is independent of the editor draft.

The service accepts one run at a time across all browsers. Each edit uses the small BL channel grammar, with unary helpers named `mix-white` or `tile-…` and argument `x`. The server emits the parsed forms back to BL before running the CLI. The accepted bundle is atomically saved in `~/.local/state/checked-tiles-web/accepted.json`. The first visit to a fresh server shows the recorded wash example. Draft edits are local to the browser, and a restart clears last-run status. Set `CHECKED_TILES_STATE` to use a separate state directory, `HOST` and `PORT` to change the listener, and `CHECKED_TILES_HOSTS` to allow specific additional HTTP hostnames when using a private proxy. Everyone with access to this private workbench shares its accepted revision.

## Exercise a live change in the native actor and compiler

Open the [native actor lab on the workstation](https://work.tailcb5318.ts.net:18180/#actors) and choose **Run native experiment**. The browser builds a native executable, runs two mailbox implementations and changes a compiler dependency while a compilation is suspended. The receipt includes the residual message, emitted Scheme, allocation counts and forced-GC observations. The browser runs the short fixture. To run the timing sweep from the checkout root:

```sh
research/checked-tiles/actor-lab/run --quick
research/checked-tiles/actor-lab/run --out /tmp/my-native-actor-results.json
```

The output path must be new. The runner uses Python 3.10+, a systemd user session, pinned Gambit and Clang, and the workstation's retained qualified objects under `research/native-seed/out/real-actors`. The checked-in qualification names those exact artifacts. A source-only checkout also needs that native build capture and its SDK. The script checks its digests, rebuilds the final application unit, links the fixture in a temporary directory, and releases it on exit. The full run adds three trials at five depths and scheduling comparisons at the normal and 17-step budgets. [Native actor build background](../native-seed/real/README.md) · [Recorded full run](evidence/native-actor-lab.json) · [Research journal](journal/04-native-concurrent-core.bl.org)

### Change a blend while the Ora film is running

Open [Live film edit](https://work.tailcb5318.ts.net:18180/#film), choose **Prepare live scene**, then **Save blend edit** when frame A appears. An old render has completed half its CPU grade and an old compile is suspended inside the native identifier emitter. The button saves the displayed helper into the session. After B appears, the driver releases both old jobs, attempts stale publication twice, submits a broken helper, and renders another frame from the serving slot. Expand the receipt for digests and timings. The browser records the interval from click to a decoded image at a paint opportunity. The server measures source save to availability of the accepted PNG.

From the checkout, pass a new directory for the immutable source snapshots, proofs, frames and receipt.

    research/checked-tiles/live-render/run --out /tmp/ora-live-first

To exercise your own trusted edit, add `--helper /path/to/blend.bl`. Define one ordinary unary `mix-white` function. A successful full rehearsal needs a visibly different bright-byte mapping from A. The fixed callers live in [entry.bl](live-render/entry.bl). The browser exercises the supplied change.

The runner uses the exact SDK and Lean in [tools.json](tools.json), the retained stage-two executable and macro bundle in `research/native-seed/out/compiler-native-owner`, the compressed Ora scene plan, and an EGL/GLES device supporting the film renderer. The compiler inputs are checked against the [native bootstrap qualification](../native-seed/evidence/scheme-fixpoint/qualification.json). On another workstation provide equivalent EGL libraries via `SCENE_EGL` and `SCENE_GLES` and the appropriate Mesa vendor configuration. Warmup, setup of the two pending jobs, late completion and teardown are outside the save interval. A browser session waits up to three minutes for a save.

## Measure ordinary Enchant against Bend

The speed corpus checks five resident jobs using runtime inputs. It exercises a qualified self-hosted native compiler, the checkout's newer native emitter hosted on the pinned SDK, and Bend 2.0.40. The follow-up runs compile two ordinary byte loops, replay the map/filter/sum descriptor through Cranelift, and compile a bounded recurrence to an unboxed machine loop with an actor-aware fallback. [Journal and results](journal/04-native-concurrent-core.bl.org) · [Speed harness](speed/)

On the research workstation, from the checkout root, give the replay a **new** directory. Each phase runs under a memory cap, writes its own receipt and stops its workers.

    research/checked-tiles/speed/replay /tmp/my-enchant-speed

For the smaller CPU-only initial corpus and the same specialist checks, use the following command.

    research/checked-tiles/speed/replay /tmp/my-enchant-speed-small --cpu-only --quick

The replay needs the immutable SDK and Lean from tools.json, the retained stage-two executable and bundle in research/native-seed/out/compiler-native-owner, the pinned Gambit, Clang, Bun and Rust/Cargo tools, and the locked Cranelift crate dependencies. The initial corpus prepares the pinned Bend sources and, for the GPU run, CUDA tooling. Set BEND_TREE, CUDA_HOME and CARGO_TARGET_DIR to reuse existing copies. The quick option reduces the initial corpus to one block and two sizes. The published full run used three blocks, nine configurations and a hardware GPU. The byte follow-ups use 20 trials per size and arm. [Native compiler qualification](../native-seed/evidence/scheme-fixpoint/qualification.json) · [Raw corpus](evidence/speed-corpus.json) · [Ordinary byte loops](evidence/speed-ordinary-bytes.json) · [Packed descriptor](evidence/speed-packed.json) · [Scalar region](evidence/speed-bounds-word.json)

To reproduce an individual arithmetic ablation, point the runner at a completed corpus directory. The default measures a machine primitive used as a value. Pass --direct, --machine, --frame-aware or --word for the successive lowerings. Each output directory must be new.

    scripts/bl-mem
    systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=256M python3 -B research/checked-tiles/speed/bounded.py /tmp/my-enchant-speed/corpus --frame-aware --out /tmp/my-frame-replay

## How close is the native compiler to running the whole boot?

Read the journal or print the recorded comparisons on any machine with Python 3.10 or newer. The second command runs the current self-hosted reader against the pinned downstream SDK on this workstation.

    python3 research/checked-tiles/boot/summary.py
    research/checked-tiles/boot/replay /tmp/my-reader-run --smoke

For the full experiment, give the runner a fresh directory. It runs one capped process tree at a time. The compiler jobs need the qualified Gambit stage-two executable and its native split build at `research/native-seed/out/native-prepared-eval-build`, its prepared macro file, the immutable SDK selected by `tools.json`, retained source history and the matching Nix compilation tools. The first-party run checks the image and SDK digests. For a checkout without those local artifacts, the committed observations and the summary remain readable.

    research/checked-tiles/boot/replay /tmp/my-native-boot-run
    python3 research/checked-tiles/boot/summary.py /tmp/my-native-boot-run

The reader session retains the source list, complete typed terms and mismatch excerpts. The other sessions retain individual timings, compiled objects, binding and import inventories, and the actual stdout, stderr and exit codes. The compiler comparison times reading through emitted Scheme in already-running processes. The CLI comparison invokes cold processes separately. Results for a losing candidate and for an unsupported operation remain visible in both. [Read the journal](journal/04-native-concurrent-core.bl.org) · [Native image qualification](../native-seed/speed/attrib/raw/native-prepared-eval-qualification.json)

To try your own file after the extension job completes, use the native public reader. It verifies the built objects, installs the first-party reader exports and evaluates the actual built-in data-reader registrations before reading the input. Its stdout is the tree rendered by the Enchant printer. Syntax errors go to stderr and exit 1.

    printf '%s\n' '#time"2026-06-15"' | research/checked-tiles/boot/read /tmp/my-native-boot-run/extension -
    research/checked-tiles/boot/read /tmp/my-native-boot-run/extension --syntax priv/boot/reader-node.bl

To build just those four objects in a new directory, run `scripts/bl-mem` and then:

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=256M python3 -B research/checked-tiles/boot/extension.py --out /tmp/my-reader-extension

Compare the same semantic observations with the original receipts after a full replay. This also prints both timing panels. The completed workstation replay is at `research/native-seed/out/checked-boot-replay`.

    python3 -B research/checked-tiles/boot/compare.py /tmp/my-native-boot-run

To attribute the compiler gap on the successful pipeline replay, run the two comparisons sequentially. The first queries the pinned SDK once and measures phase costs, procedure calls and stack samples in separate native processes. The second compiles the boot macros and compares them with the evaluated bundle. See the journal for the allocator counter caveat.

    scripts/bl-mem
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=256M python3 -B research/checked-tiles/boot/cost.py research/native-seed/out/checked-boot-replay/pipeline --out /tmp/my-compiler-cost
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=256M python3 -B research/checked-tiles/boot/macro-cost.py research/native-seed/out/checked-boot-replay/pipeline --out /tmp/my-macro-cost

### Reproduce the compiler changes on main

From the checkout root, these commands exercise the real native build and the pinned SDK using the retained workstation inputs described above. Use fresh output directories. The matched panel measures one warm translation eight times per arm, checks identical emission, and counts physical ANF layouts outside the timer. The work census counts exact fixed-arity BL bodies on both engines. The boundary clock measures the time spent inside individual BL operations. Its nested measurements overlap.

```sh
scripts/bl-mem
boot=research/checked-tiles/boot
seed=research/native-seed
pipeline=$seed/out/checked-boot-replay/pipeline
build=$seed/out/checked-fields-build
cap() { systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=512M "$@"; }
cap "$seed/run" run "$boot/definition-edits.bl" -- /tmp/my-definition-edits
cap "$build/stage1" --eval "$boot/symbol-budget.scm" unused
cap python3 "$boot/field_pipeline.py" "$pipeline" "$seed/out/perf-declaration-snapshot-build" "$build" --before-symbols "$seed/out/checked-fields-before-symbols" --out /tmp/my-field-panel
cap python3 "$boot/semantic_work.py" "$pipeline" --out /tmp/my-work-counts
cap python3 "$boot/boundary_clock.py" "$pipeline" --out /tmp/my-boundary-clocks
cap python3 "$boot/primitive_cost.py" "$pipeline" --out /tmp/my-byte-cost
cap python3 "$boot/runtime_flags.py" "$pipeline" --out /tmp/my-compiler-flags
```

To rebuild the current sources into a separate native image on this workstation, start from the captured compiler closure. The stage-one build reads the updated closure and emits it using the first-party BL emitter. The qualification command then runs the compiler and actor corpus and rebuilds the compiler using its own native executable. The checkout selects the immutable toolchain and SDK recorded under `research/native-seed`. The timing panel selects its exercising SDK from `research/checked-tiles/tools.json`.

```sh
export ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'
closure=$seed/out/my-closure
build=$seed/out/my-build
cap python3 "$seed/snapshot-closure.py" "$seed/out/perf-declaration-snapshot-closure" "$closure"
cap "$seed/speed/final/closure-r3.sh" "$closure"
mkdir "$build"
cp "$closure/identity.json" "$closure/partition.json" "$build/"
cap python3 "$seed/prepare-host.py" --out "$build"
cap "$seed/speed/final/emit.sh" out/my-closure out/my-build
cap "$boot/verify-native-build" "$build" "$seed/out/my-actors" .local/native-speed-integration/wave1-compiled-actors/javascript-corpus-fixed/manifest.json
```
