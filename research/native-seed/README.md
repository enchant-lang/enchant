# A native seed for BL

[Live development review](https://work.tailcb5318.ts.net:18138/) · [Snapshot](evidence/native-seed.html) · [Qualification evidence](evidence/qualification.json)

The managed tailnet service is `native-bl-dev`. It reads `native-seed.bl.org`
on every request; document edits refresh automatically and authenticated review
comments save back to that file. Host code changes need a restart:

```sh
WORK_BL="$PWD/bin/bl" work restart native-bl-dev
WORK_BL="$PWD/bin/bl" work stop native-bl-dev
```

The service retains the pinned SDK, listens on loopback behind the tailnet
publisher, and has a 2 GiB memory limit with swap disabled. Its owner is the
requested development review; stop the service when that review is retired.

The emitter is BL. It consumes the existing compiler's bl-ANF, emits Scheme,
and imports actor definitions directly from `priv/lib/js/actor/runtime.bl`.
`verify.py` qualifies Scheme → Gambit C → native and C → LLVM IR → native.
The native programs still link Gambit's runtime and GC. The compiler runs on
the pinned BEAM SDK; this slice does **not** establish native self-hosting.

```sh
systemd-run --user --collect --wait --pipe --working-directory="$PWD" \
  --property=MemoryMax=3G --property=MemorySwapMax=0 \
  --property=RuntimeMaxSec=600 python3 research/native-seed/verify.py
research/native-seed/run realm stop
```

`run` verifies `sdk-pin.json` and directly invokes that retained SDK for
bounded cold snapshot commands. It does not prepare another SDK when unrelated
engine edits move the integration checkout's SDK selection. Each command exits
its VM. `toolchain-pin.json` records the immutable Gambit and Clang products. Provision missing tools from that Nixpkgs
revision; do not silently replace the pinned SDK.

The executable fixture covers selective receive, clause/message order, guards,
retained unmatched messages, parking and wakeup, deadlines, exact large
integers, closures, map equality/keys, operand order, monitors, language exits,
dead targets and distinct PIDs. Its 26 shared checks also run against the
production JavaScript actor backend; native cleanup adds a 27th check.
Its scheduler also checks cleanup and actual bounded turns. Time is virtual.
Maps are association maps; floats, decimals, generic structs, general exception
handlers, native I/O, links, supervision, ETS semantics and Source custody are
outside this seed. Unsupported ANF and host calls fail during emission.

`native-seed.bl.org` maps the implementation, the `proc` host boundaries,
Jolt's relevant ideas and the staged native self-hosting gates.

Render its checked cells and source cards with the installed dossier kit:

```sh
research/native-seed/run \
  -p ~/projects/enchanted-skills/bl-org-dossier/kit \
  -p ~/projects/enchanted-skills/codebase-review/kit \
  run research/native-seed/review-build.bl
node research/native-seed/browser-check.mjs
research/native-seed/run realm stop
```

The five approved milestones continue beyond that frozen seed. Current focused
witnesses live in `evidence/host.json`, `evidence/text-host.json` and
`evidence/direct-scalar/qualification.json`. The direct route lowers authored
BL control into C program counters and rooted slots; Gambit supplies values,
GC and host services. Its ten scalar checks pass through both pinned Clang C
and LLVM IR builds with byte-identical output. Full actor and native compiler
fixpoint qualification remain separate gates in the live dossier.

`check-compiler.py` cheaply executes the emitted canonical compiler on GSI
before a full native image is built. It authenticates its emitted artifact and
records any host adapter replacement used for preflight. Final stage artifacts
are assembled by `native.chunks`, which reuses exact checked emission chunks.
