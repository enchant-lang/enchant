# Native compiler roster

One line per piece of work. Status: ✅ done · 🔨 in progress · ⏳ next · 🅿️ parked · 🧪 prototype only.
The latest work is at the top of each section. The commit links the evidence;
the journal (`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`)
holds the reasoning.

## Now

| | Work | Why | Done when |
|---|---|---|---|
| ⏳ | Fused macro-result walk | Each expansion walks its result 3×: the first-order bound check alone is ~9% of the reader job, `data->form` and gensym canonicalization the rest | One pass converts, bounds, refuses and canonicalizes; byte-identical candidate; paired |
| ⏳ | SDK in two layers: library image + native join | A native edit re-produces 2 GB to change one `.so`; nothing reads the packed drop in a checkout SDK | Library identity excludes optional natives; a join links `priv/native`; packing moves to the portable product; a native edit's SDK under 30 s |
| ⏳ | Build VM `cpuCount` for shards | 4 shards share 4 CPUs (297 s vs 575 s serial) | Measured at 8 CPUs |
| 🅿️ | Disk floor | Daemon has `min-free = 0`; this account is not trusted | Root sets `nix.settings.min-free`, or the user approves a user timer running a bounded `nix-store --gc` |

## Done

| | Work | Result | Commit |
|---|---|---|---|
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
| 🧪 | Macro answer per call head per form | 57% of 3,546 `macro?` calls hit; byte-identical 13/13; **no gain**: memo containers (atom, tuple-keyed map) cost what the lookup costs | detached worktree `d5a93cd58` (removed; commit kept in reflog until merged or dropped) |
| 🧪 | Keyword call `(:k m)` as a direct get | 77 → 50 ns per call in isolation; 1,614 sites in the compiler | measured only |

## Scratch

| Tree | Owner | Removed when |
|---|---|---|
| `/tmp/claude-ab/c9` | base image for pairs | the next image becomes the base |
| job tmp `cand-io2`, `der-atom` | current candidate images | superseded |

## Numbers to beat

| Measure | Now | Warm BEAM |
|---|---|---|
| Reader job (read + compile + emit) | 121 ms | 158 ms |
| Native qualification, cold / repeat | 20.8 s / 0.4 s | — |
| SDK preparation, runtime edit / compiler edit | 2.7 min / 16 min (sharded) | — |

## Parked

| | Work | Why parked |
|---|---|---|
| 🅿️ | Python in `formal-logic`, `checked-tiles` and other research | Not on the critical path |
| 🅿️ | Incremental per-namespace native AOT on Chez | Waits for the native export |
| 🅿️ | Interned names on the native host | Memo and lookup both pay string hashes; worth it only with the fused walk landed |
