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

See [the design discussion](journal/01-bend-and-enchant.bl.org) and [the experiment log](journal/02-experiment.bl.org).
