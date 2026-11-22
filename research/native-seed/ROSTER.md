# Native compiler roster

One line per piece of work. Status: ✅ done · 🔨 in progress · ⏳ next · 🅿️ parked · 🧪 prototype only.
The latest work is at the top of each section. The commit links the evidence;
the journal (`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`)
holds the reasoning.

## Now

| | Work | Why | Done when |
|---|---|---|---|
| ⏳ | Interned names on the native host | Lookups and any memo pay a string hash per name; `string-hash`/`equal-hash` are ~4–5% of the reader job | The reader interns symbol names; byte-identical candidate; paired |
| ⏳ | Emitter `ident` | `ident` joins one text per character for every emitted name | A memo or a direct encoder; byte-identical; paired |


## Done

| | Work | Result | Commit |
|---|---|---|---|
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

## Numbers to beat

| Measure | Now | Warm BEAM |
|---|---|---|
| Reader job (read + compile + emit) | ~110 ms min, ~117 ms median under load | 158 ms |
| Native qualification, cold / repeat | 20.8 s / 0.4 s | — |
| SDK build, native edit / compiler edit | 82 s / 13 min | — |

## Parked

| | Work | Why parked |
|---|---|---|
| 🅿️ | Python in `formal-logic`, `checked-tiles` and other research | Not on the critical path |
| 🅿️ | Incremental per-namespace native AOT on Chez | Waits for the native export |
| 🅿️ | Interned names on the native host | Memo and lookup both pay string hashes; worth it only with the fused walk landed |
