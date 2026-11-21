# The native compiler on Rust, without a collector

An experiment, not a backend. It answers two questions with measurements:
how long does `rustc` take on the compiler, and how fast does a Rust-built,
reference-counted compiler compile itself?

```text
stage2.scm ── translate.py ──▶ Rust (gen/*.rs) + rt.rs ── rustc ──▶ stage
                                                                      │
              stage --compile bundle.scm host.scm OUT  ◀──────────────┘
              OUT = stage2.scm, byte for byte
```

`translate.py` reads the emitted Scheme of a qualified stage (the same
`stage2.scm` Chez runs: host plus 4 876 definitions) and writes Rust. Every
Scheme value is a `V`; heap values are `Rc`. There is no garbage collector.
`rt.rs` is the runtime: 156 Scheme primitives, tables, ports, a reader, and an
evaluator for the Scheme the compiler evaluates at run time.

## Results

Measured on the Build host (8 cores, 21 GB), rustc 1.98.1, image
`cutover-core-build-v3`. Receipts are in `evidence/`.

| What | Result |
|---|---|
| Translate stage 2 to Rust | 5.2 s; 7.1 MB of Rust, 2 120 direct functions |
| `rustc` type and borrow check only | 25–32 s, 1.6 GB peak |
| `rustc` unoptimized build | 44–53 s wall, 2.5 GB peak |
| `rustc -O2`, 16 codegen units | 322 s, 450 s and 792 s wall on three builds; 4.6–5.0 GB peak |
| Chez `compile-file` of the same stage, one thread | 7–10 s, 0.28 GB |

Self-emission (`--compile bundle.scm host.scm OUT`), same machine:

| Stage built by | Wall | Peak memory | Output |
|---|---|---|---|
| Chez, optimize level 2 | 10.3–13.4 s | 0.67 GB | identical to `stage2.scm` |
| Rust `-O2`, first translation, glibc malloc | 57.0 s | 2.07 GB | identical |
| Rust `-O2`, shared bindings + size-class allocator | 43.3–46.3 s | 1.72 GB | identical |
| Rust unoptimized, same | 191.9 s | 1.73 GB | identical |

The Rust-built compiler emits the stage it was translated from, so translating
its output gives the same Rust again (the translation is deterministic).

## What the measurements say

- **The borrow checker accepts all of it and constrains nothing.** Values are
  shared `Rc`s and calls pass `&V`. rustc verifies the emitted Rust, including
  the binding sharing below, but no Enchant program is rejected.
- **Compile-time eval is not a cost on this path.** A full self-emission makes
  105 `eval` calls (0.03 s) and 6 159 calls into evaluated code (0.09 s). The
  evaluator in `rt.rs` compiles forms to closures; it has no `eval` to lean on.
- **No exception is raised** during self-emission.
- **Memory management is the gap.** In the first build about 35% of samples
  are `malloc`/`free` and about 25% are `Rc` clone and drop. A size-class
  allocator and not cloning when a `let` only renames an immutable local take
  57 s to 44 s. After that, clone and drop are still about 40% of samples.
- **Reference cycles leak.** All 764 local named functions are
  `(letrec ((f (bl-register-callable! … (lambda …)))) …)`: the closure reaches
  itself through its own binding. Reference counting never frees these.

## What it does not cover

- **Actors.** `h-park` needs a re-entrant continuation; `rt.rs` has escape-only
  `call/cc` (unwinding). The compile path never parks. The actor corpus is not
  run.
- **Qualification.** Only the self-emission gate is checked. The source corpora
  are not run.
- **Tail calls.** Self tail calls and named-`let` loops become Rust loops (352
  sites). Other tail calls use the Rust stack; the stage runs on a 4 GB stack.
- **Numbers.** Integers stop at 128 bits; rationals are minimal.
- **Rebound functions.** The stage rebinds 37 functions by name at load (its
  NIF replacement). `dynamic-globals.txt` lists them, taken from a first run;
  the translator keeps those as slots instead of direct calls.

## Run

```sh
export RS_WORK=/some/scratch
./cycle.sh check   ''                                 IMAGE/stage2.scm   # rustc front end only
./cycle.sh debug   'cfg = "--cfg rs_fastalloc";'      IMAGE/stage2.scm
./cycle.sh release 'cfg = "--cfg rs_fastalloc";'      IMAGE/stage2.scm
nix build --impure -L --expr 'import ./bench.nix {
  stage = "/nix/store/…-rust-substrate-stage-release"; image = IMAGE; chez = ../native-seed/chez; profile = true; }'
```

`cycle.sh` translates locally and builds on the Build host (`measure.nix`),
printing rustc's wall time, CPU time and peak memory. `bench.nix` times the Chez
build and the Rust build of the same stage on the Build host and compares each
output with the image's `stage2.scm`. `RS_SHARE=0` turns the binding sharing
off; omit the `cfg` to use glibc malloc.
