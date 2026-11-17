# Round 3, wave 1: both targets faster, native at native speed

Dossier: [`native-speed.bl.org`](native-speed.bl.org), section *Round 3 roster*.
Rounds 1 and 2 are merged on `main`. Every rule in [`CONTRACT.md`](CONTRACT.md)
and [`CONTRACT2.md`](CONTRACT2.md) still holds unless replaced here; in
particular, **no host Scheme may replicate a `.bl` file** (CONTRACT2's
categories a–d).

## Decisions already taken (Othman, 2026-11-17)

| Id | Decision | Consequence for this wave |
| --- | --- | --- |
| D1 | The value representation stays fixed until V2, which has a single owner | Nobody changes the term layout in `host-values.scm` this wave |
| D2 | AOT code calls plain procedures; planners are chosen at emission | — |
| D3 | Kernel fast paths delegate to the compiled BL body for other cases | BACKEND's N2 fast paths fall through to `rt.bl` |
| D4 | Optimiser facts are computed by conservative BL code and validated by `formal.elaboration/check` in tests; no solver at compile time | FACTS |
| Q1 | Map iteration order is **unspecified**; canonical order only through `formal.identity` | No test may newly depend on map order; V2c may use hash maps |
| Q2 | The kernel signature lives in the formal Core, with Lean models | Later wave |
| Q3 | Collection keys use **value equality**: `(get {1 :x} 1.0)` is `:x`. Othman delegated the details: pick what is easiest to implement and least surprising, record it, and stick to it | KEYS |
| Q4 | A sealed release links global calls directly; a dev image keeps Vars mutable | LINK's N3 |
| Q5 | Floats follow IEEE binary64 with round-to-nearest-even; signed zeros and NaN are kept | Later wave (E8) |

## Fixed this wave

- The value representation (D1).
- Emitted Scheme for the warm-core benchmark fixture stays byte-identical between
  BEAM and native, because both run the same `scheme.bl`. It may differ from
  round 2's bytes when an item's purpose is to change emission (N1, N4, E1).
- BEAM semantics are unchanged except where an item's purpose is to change them
  (Q3 keys; Q4 sealed releases). Existing BEAM tests for touched areas must pass.

## Workstreams and file ownership

Paths are relative to the repository root. `NS` = `research/native-seed`.

| WS | Item(s) | Owns (may edit) | Must not edit |
| --- | --- | --- | --- |
| MEASURE | A3 | new `NS/speed/attrib/` only | runtime and compiler source |
| LINK | P3, then N3 | `NS/src/native/{bootstrap,eval,chunks,resolution*}.bl`, `NS/update-closure.bl`; native Env/AOT/Loader leaves in `NS/host/host-compiler.scm`; for N3 the global-call link path on BEAM (find it: Var fetch emission in `priv/boot/compiler.bl` / `priv/host/link.bl` / Var binding in `priv/host/env.bl`), touching only those functions | `scheme.bl` (see below), `rt.bl` |
| ACTOR | X | the cross-process wait/refuse path in `priv/host/lazy_memo.bl` and `NS/host/native-memo.scm`; actor-corpus scripts; lazy/actor tests | the rest of the lazy runtime |
| KEYS | Q3 | `NS/speed/keys/DECISION.md`; in `priv/boot/rt.bl` the key paths (`coll-get`, `get`, `assoc`, `dissoc`, `contains?`, `find`, set membership and construction, `hash`); the matching key code in `NS/host/host-values.scm` (behaviour only; no layout change); key tests | `nth`/`k-nth` (BACKEND) |
| BACKEND | N1, N2 | `NS/src/native/scheme.bl` **except** tick/frame emission (FRAMES) and `:integer-facts` threading (FACTS); in `rt.bl` `nth`, `k-nth` and other multi-arity functions that lack fast paths, except KEYS's | KEYS's `rt.bl` functions |
| FRAMES | N4 | in `scheme.bl` only the functions that emit `(h-tick)`, budget checks and source-frame parameters; `NS/host/host-source-frames.scm`; tick/turn primitives in host Scheme | the rest of `scheme.bl` |
| FACTS | E1 | new `priv/host/facts.bl` (or another new namespace; say which); `priv/host/optimize.bl`; in `scheme.bl` only the `:integer-facts` threading; a validation test against `formal.elaboration/check` (sources in `research/formal-logic/sdk-src/formal/`) | the rest of `scheme.bl` |

Three workstreams share `scheme.bl`, split by function. Keep hunks inside your
own functions. If you need a change in someone else's function, write the request
in your `RESULT.md` under **Requests**, and the main thread will do it at
integration.

## Interfaces

- **FACTS → BACKEND, FRAMES and the later E items.** One function (name it)
  takes an ANF function and returns per-binding facts: Int or Bool type, integer
  range when known, whether the expression can raise, and footprint from
  `system.analyze`. `optimize.bl`'s tag lattice and `scheme.bl`'s
  `:integer-facts` become readers of it in the same change (hard cutover). The
  facts are conservative: "unknown" is always correct.
- **KEYS:** value equality must agree with `=` and with `hash`, on BEAM and
  native. Decide for Decimal keys, integral floats, `-0.0` and NaN, and for what
  `keys` returns for a key stored as `1.0`. State the cost on the common case
  (integer, keyword and string keys) as the number of extra guards on each path,
  not as a timing.
- **LINK N3:** "sealed" is a property the build declares, such as a release
  image or the native closure. A dev image keeps today's Var fetch. A sealed
  image must refuse a later redefinition clearly, not silently use the old
  procedure.
- **MEASURE:** add a second fixture that compiles a real namespace
  (`priv/boot/reader.bl` or a similar size) through read, compile and emit. Count
  on native and profile on BEAM, then rank the remaining cost. Its ranking
  decides wave 2; it changes no code.

## Tools and budgets

- `MAIN` = `/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed`.
  These artifacts are read-only (gitignored; do not write to them):
  `MAIN/NS/out/speed-closure-2/` (the closure), and `MAIN/NS/out/round2-build/`
  (`stage1` ELF, `stage1.scm`, `host.scm`, `prelude.scm`, `leaves.json`,
  `chunks/`).
- **Every** VM or compile command runs through
  `work run --memory 4G --timeout 1800 -- COMMAND…`. The account runs at most two
  at a time, and the timeout includes queue time, so expect to wait. Never start
  `bl` outside `work run`.
- Pinned SDK (the round-2 integrated SDK): `NS/run run FILE.bl -- args`.
- For your own `priv/` edits: `./bin/bl --cold test test/bl/ONE_test.bl …` from
  your worktree root. Batch the files into one invocation. Run `./bin/bl realm
  stop` before you finish.
- Gambit: `$(jq -r .gambit NS/toolchain-pin.json)/bin/gsi`, under `timeout 120`.
- **No timing benchmarks** in agents, and no before/after timings. MEASURE
  counts operations and profiles shares on one run per target.
- **Forbidden in agents**: rebuilding the native compiler image,
  `fixpoint*.py`, `chunks.bl build-next` over all chunks, the warm-core
  benchmark, full `bl test`, producing an SDK, and any Nix build. Only ACTOR may
  run the actor corpus, once per target, under the cap. The main thread does the
  rest once, at integration.

## Definition of done

1. Hard cutover: the old path is deleted in the same change.
2. Focused checks are green and recorded in `NS/speed/<ws>/RESULT.md`, with the
   exact commands and their output summaries, plus **Requests**, **Residual
   replicas** (if any) and **Risks for integration**.
3. Commit on your branch, in your worktree only, as you go. Never push, merge,
   rebase or touch other branches. Your final message lists commits, changed
   functions, checks run and risks.
