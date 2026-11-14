# A native seed for BL

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

`run` verifies the immutable SDK pin and uses this checkout's `./bin/bl`, with
one private compiler VM. Stop it when finished. `toolchain-pin.json` records the
immutable Gambit and Clang products. Provision missing tools from that Nixpkgs
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
