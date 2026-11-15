# BL → Scheme → Gambit → C

[Live development review](https://work.tailcb5318.ts.net:18138/) · [Snapshot](evidence/native-seed.html) · [Complete compiler fixpoint](evidence/scheme-fixpoint/qualification.json)

The agreed wider direction is a **native BL development tool first** for the
compiler and proc/actor work: edit, diagnose, test, run and reload in one warm
native host, with deployment following the same pipeline. Ordinary use should
require no BEAM. Speed must be established against equivalent warm BEAM work;
the current native prototype does not establish that comparison.

The dossier separates the checked bootstrap from the next delivery work:
fair baselines, measured frontend optimization, a usable native project loop,
incremental native self-emission, then a packaged daily tool. Initial targets
(3× frontend throughput over warm BEAM, <100ms unchanged requests, <1s small
edit-to-test) are provisional engineering goals to ratify against the baseline.

```text
BL Source → existing reader / macros / bl-ANF → BL-owned Scheme emitter
                                                   ↓
Native compiler ← native executable ← Gambit-generated C
       └── stage 2 → stage 3: identical bytes
```

The canonical route is self-hosted. A qualified BEAM SDK seeds stage 1;
three native compiler generations pass the original Source corpus and all
461 actor checks at default / 17 / 41 turn budgets. Self-emission takes
200.642 and 211.299 seconds with the 240-second limit unchanged.
Gambit supplies the native runtime, collector and continuations.

| Gate | Retained evidence |
| --- | --- |
| Values + control | [377 shared BEAM / JavaScript / native observations; 52 original BEAM protocol fields](evidence/values-parity/qualification.json) |
| Actors | [461 unchanged checks × 3 budgets](evidence/original-actor-corpus/qualification.json) |
| Real clock + readiness + blocking FFI | [14 actor checks × 3 budgets](evidence/real-actors/qualification.json) |
| Native self-hosting | [Stage 2 = stage 3; all three executables qualified](evidence/scheme-fixpoint/qualification.json) |

Native incrementality uses BL's existing owners:

```text
build-plan / Source interfaces → AOT workspace → original Source ANF
                                                     ↓
unit-store/artifact-target! ← Scheme → Gambit C → loadable native module
```

`native.aot-scheme` emits the existing constructor's plans and publication
operations before BEAM rewriting. `native.aot-target` connects it to the
existing unit store; `native_module.py` transports Scheme bytes to C/native
objects. Namespace products retain exact Source, phase, emitter, ABI and tool
identities. The existing session/realm transport keeps the compiler warm.
No Chez dependency or additional incremental compiler policy is introduced.

`aot-prepare.bl` checks cold/warm/copy/edit behavior and independent native
bytes. `aot-probe.bl` uses the existing artifact process owner for native
ownership, replacement and retained-closure/GC checks. The
[qualified prototype](evidence/incremental-aot/qualification.json) passes
154 focused owner assertions and 18 native checks. Cold native emission takes
3.752 s; warm verification takes 1.570 s with zero staging/emission/compiler
jobs. Independent native products match byte for byte.
The cross-namespace planner check is separate from this one-namespace native
prototype; incremental rebuilding of the complete self-hosted compiler remains
future work.

Reproduce the namespace prototype with the separately qualified AOT SDK pin
(both output directories must be fresh):

```sh
research/native-seed/run --sdk-pin research/native-seed/incremental-sdk-pin.json \
  run research/native-seed/aot-prepare.bl -- research/native-seed/out/my-aot
research/native-seed/run --sdk-pin research/native-seed/incremental-sdk-pin.json \
  run research/native-seed/aot-probe.bl -- \
  research/native-seed/out/my-aot/proof.json research/native-seed/out/my-probe
```

`native.chunks` caches checked ANF / resolution emission chunks;
`native_elf.py` caches exact Gambit C and native objects. Both preserve Source,
SDK, host, tool and compiler-option identities. Source corpus execution in the
qualified generations takes 12.8–13.6 seconds.

GVM remains an isolated native-procedure experiment. Tail-call and captured-
closure pilots passed; full compiler emission reached the 3 GiB bound before
full Source / self-build qualification. Its [tail-call](https://github.com/undefine-org/enchant/commit/9927a07bbb470a1836b7efbf0c1da329221e923a)
and [capture](https://github.com/undefine-org/enchant/commit/515a3123dedf9a2c758653646a0225fd1ab1883a)
receipts remain in Git. The raw C stepper and duplicate explicit IR routes
are retired from the working tree.

The managed tailnet service is `native-bl-dev`. It reads `native-seed.bl.org`
on every request; document edits refresh automatically and authenticated
review comments save to that file. Host code changes need a restart:

```sh
WORK_BL="$PWD/bin/bl" work restart native-bl-dev
WORK_BL="$PWD/bin/bl" work stop native-bl-dev
```

The service uses the pinned SDK, listens on loopback behind the tailnet
publisher, and has a 2 GiB memory limit with swap disabled. Stop it when the
requested development review is retired.

`run` verifies `sdk-pin.json` and invokes that retained SDK directly. Its
`--sdk-pin FILE` option selects another explicit immutable SDK receipt. It does
not build another SDK when unrelated integration edits change the checkout's
selection. Each bounded snapshot command exits its VM. `toolchain-pin.json`
records the immutable Gambit and Clang products.

Refresh the dossier's actual cells and rendered source cards:

```sh
research/native-seed/run \
  -p ~/projects/enchanted-skills/bl-org-dossier/kit \
  -p ~/projects/enchanted-skills/codebase-review/kit \
  run research/native-seed/review-build.bl
node research/native-seed/browser-check.mjs
```

Run one substantive check at a time under the existing memory and time limits.
`fixpoint-full.py` is the complete Scheme qualification driver;
`check-compiler.py` is a focused preflight and does not establish self-hosting.
