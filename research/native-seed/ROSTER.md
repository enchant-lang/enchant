# Native compiler roster

One line per piece of work. Status: ✅ done · 🔨 in progress · ⏳ next · 🅿️ parked.
The latest work is at the top of each section. The commit links the evidence;
the journal (`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`)
holds the reasoning.

## Now

| | Work | Why | Done when |
|---|---|---|---|
| 🔨 | Native bundle export (metadata self-hosted) | Regenerating a bundle needs the retired `partition-closure.py` and an old pinned SDK | `bundle.scm` produced natively, byte-identical to today's |
| ⏳ | Disk safety on Work and the build station | Work filled to 100% twice | Nix `min-free`/`max-free` set; old SDK preparations pruned |
| ⏳ | Foundry: sharded unit compilation | A compiler edit recompiles 659 units on 4 cores (575 s) | Compiler-edit SDK under 1 minute |
| ⏳ | Foundry: incremental SDK for runtime edits | 6.4 min for about 1 s of compilation | Runtime-edit SDK under 30 s |
| ⏳ | Codegen candidates in `qualify.bl` | Code-changing compiler work needs a fixpoint and behaviour gates | `candidate --codegen` iterates to a fixpoint and checks corpus and actors |
| ⏳ | Structural compiler work | Env reads 18%, positions 22% of lookups; macro walks about 7% | Each step qualified and paired |

## Done

| | Work | Result | Commit |
|---|---|---|---|
| ✅ | JS runtime copies, seed test floor | Both BEAM failures fixed; 315 checks pass | `32ad701fa` |
| ✅ | `env.bl` `:tools` | Tools as Nix packages; `qualify.bl` uses them | `1fab5d6dc` |
| ✅ | Escape scan + table, one-pass `maps/without` | Reader job 133.5 → 121.2 ms | `e0fedbf6a`, `f665458be` |
| ✅ | BL-hosted qualification; Python retired | Cold 20.8 s, repeat 0.4 s | `8a837114f` |
| ✅ | Host lookups: small-map find, env index, `str`/iolist, keyword memo | 144 → 126 ms | `a09bf6138` … `b669774cc` |
| ✅ | Compiler candidates without BEAM | 13 gates in about 3 min (later 0.8 s warm) | `a09bf6138` |
| ✅ | Checkout client digest cache | Warm `./bin/bl run` 410 → 60 ms | `0799b257c` |
| ✅ | Warm VM stderr | Errors reach the client | `52ef85948` |
| ✅ | Local-lock wakeup | Lock waits per 10 requests 4.3 s → 0.19 s | `60aede9b3` |
| ✅ | Chez substrate qualified | Byte-identical fixpoint, 461 actor checks × 3 budgets | `c69269bc5` |

## Numbers to beat

| Measure | Now | Warm BEAM |
|---|---|---|
| Reader job (read + compile + emit) | 121 ms | 158 ms |
| Native qualification, cold / repeat | 20.8 s / 0.4 s | — |
| SDK preparation, runtime edit / compiler edit | 6.4 min / 22 min | — |

## Parked

| | Work | Why parked |
|---|---|---|
| 🅿️ | Python in `formal-logic`, `checked-tiles` and other research | Not on the critical path |
| 🅿️ | Incremental per-namespace native AOT on Chez | Waits for the native export |
