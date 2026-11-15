# BL → Scheme → Gambit → C

[Live development review](https://work.tailcb5318.ts.net:18138/) · [Snapshot](evidence/native-seed.html) · [Complete compiler fixpoint](evidence/scheme-fixpoint/qualification.json)

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

Active work reuses BL's existing build-plan keys, guarded Reader reuse, AOT
workspaces and warm realm replay for native Scheme compilation. The target
adapter must preserve those invalidation and ownership contracts; new native
warm/edit speed results remain unqualified.

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

`run` verifies `sdk-pin.json` and invokes that retained SDK directly. It does
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
