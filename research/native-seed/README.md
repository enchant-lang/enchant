# BL → Scheme → Chez

The native compiler is BL source compiled to Scheme by its own BL-owned
emitter and run on Chez Scheme. It builds and qualifies itself with BL and
Scheme only: no Python, and no tool taken from `PATH`.

```text
BL Source → reader / macros / bl-ANF → native.scheme emitter → Scheme
                                                                 ↓
native compiler ← Chez compile-file (chunked, parallel) ← translate.ss
      └── stage 2 → stage 3: identical bytes
```

## Build and qualify

```sh
./bin/bl run research/native-seed/chez/qualify.bl -- qualify   --image IMG --work DIR
./bin/bl run research/native-seed/chez/qualify.bl -- candidate --image IMG --out DIR
./bin/bl run research/native-seed/chez/qualify.bl -- derive    --image IMG --out DIR [--base REV]
./bin/bl run research/native-seed/chez/qualify.bl -- pair      --base PRELUDE --cand PRELUDE --out DIR
./bin/bl run research/native-seed/chez/qualify.bl -- profile   --prelude PRELUDE --out DIR
```

Run these under `work run` with a memory cap. `chez/qualify.bl`'s header
documents each gate.

- **Tools.** Chez Scheme and the C compiler for the host's text FFI come from
  this repository's locked nixpkgs (`nix build --inputs-from`). Their store
  paths are recorded per `flake.lock`.
- **`qualify`** checks an image against its recorded receipt:
  - both source corpora on stage 1 and stage 2;
  - stage 1 emits the image's stage 2 byte for byte;
  - stage 2 emits itself (the fixpoint);
  - the original actor corpus, 461 checks at default, 17 and 41 turn budgets,
    on both stages, with the oracle's labels and traces.
- **`candidate`** qualifies a compiler-source change without BEAM. Every unit
  of the qualified bundle carries its BL source, and each equals its checkout
  file.
  1. The candidate bundle takes the checkout's sources.
  2. The image's stage 1 compiles it (S2).
  3. S2 is qualified as both stage 1 and stage 2.
  4. S2 must also compile the original bundle into the image's stage 2, byte for
     byte.
- **`derive`** applies host Scheme edits (`host/*.scm`, against `--base`) to a
  qualified image, by exact source span.
- **`pair`** times the reader job on two preludes, interleaved, and checks byte
  equality.
- **`profile`** samples the reader job's frames and spells emitted names as BL
  names.

Work is content-addressed under `~/.cache/beam-lisp/native-chez`:
- **A stage build** is keyed by its prelude, the translator, the shim, the
  optimize level and the tool paths. A stage and its actor overlay share one
  build. The translated prelude compiles as 12 chunks in parallel; the
  translator writes one top-level form per line and the stage defines no
  syntax.
- **A stage run** is keyed by its build, every argument (files by content) and
  its environment overlay. Each receipt row records whether it was reused, and
  `--fresh` ignores reused runs.

Independent gates run concurrently. Measured on Work (16 cores), qualifying the
current image:

| Case | Inside the run | Wall |
|---|---|---|
| Cold, empty cache | 20.8 s | 24 s |
| Repeat | 0.4 s | 3.5 s, mostly the VM request |
| Compiler-source candidate, repeat | 0.8 s | |

The Gambit qualification took 200–211 s for each self-emission alone. The two
remaining long steps of a cold run are the self-emissions, about 6.4 s each:
that is the native compiler compiling itself.

## Images

`out/` (not tracked) holds images: `stage1.scm`, `stage2.scm`, `bundle.scm`,
`host.scm`, `eval-prepared.scm`, `full-fixpoint.json` (the recorded corpus and
actor receipt) and `actor-check/`. `out/cutover-core-build-v3` is the image
seeded from the pinned BEAM SDK (`sdk-pin.json`, used through `./run`).
Images derived from it carry `derived.json`. Their qualification receipts are
in `research/checked-tiles/evidence/substrate-*.json`, and the journal
`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`
records each step.

## What still depends on BEAM

The bundle's link metadata is the pinned BEAM SDK's export: namespace modules,
leaves and the resolution ledger. `candidate` replaces unit sources inside
that metadata, so it covers any edit to existing namespaces. A change that
adds a namespace or a host leaf needs a new export.

Incremental per-namespace native products used the Gambit object transport,
retired below. On Chez they become chunked `compile-file` products. That port
has not been made.

## Retired

The Gambit route and its Python drivers are no longer in the tree; they remain
in Git history before this change:
- `fixpoint-full.py`, the `check-*.py` drivers, `native_elf.py` and
  `native_module.py`;
- the GVM, benchmark, cutover, scan, values, proc, real and corpus qualifiers;
- the BL drivers that only invoked them: `aot-prepare.bl`, `aot-probe.bl`,
  `linked-prepare.bl`, `src/native/aot-target.bl`, `cutover/build.bl`,
  `scan/build.bl`, `gvm/prepare-generation.bl`, `values/prepare.bl` and
  `benchmark/build-equality-shortcut.bl`.

Their receipts under `evidence/` stay as records. The emitter, host Scheme,
fixtures and corpus sources are unchanged.
