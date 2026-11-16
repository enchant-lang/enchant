# Native self-hosting and big-O fan-out: round 2 contract

Dossier: [`native-speed.bl.org`](native-speed.bl.org), section *Where the big-O
changes are* and the roster items M, D, R, U, T, C2, P. Round 1 (L, K, V, C)
is integrated on `worktree-native-speed`; its contract is [`CONTRACT.md`](CONTRACT.md)
and every rule there still holds unless replaced here.

## Goals

1. **Fix the big-O study**: M (lazy cells walk what they capture), D (compiled
   ANF depends on loaded namespaces), R (reader ~250 calls per byte), U (one
   edit rebuilds most of stage 1), T (BEAM invocation toll), C2 (emitter
   throughput).
2. **Self-host**: no native `.scm` code may replicate a `.bl` file. Every
   function that has a BL definition (`priv/boot`, `priv/host`, `priv/compat`,
   `priv/lib`, `research/native-seed/src`) runs natively *compiled from that
   source* by the native compiler.
3. **Self-emission parity (P)**: the native compiler's own emission path uses
   the same linking context as the BEAM driver, so stage 2 = stage 3.

## What host Scheme may still contain

A Scheme definition is legitimate only when it is the native counterpart of
something that has **no BL source**:

| Category | Examples | BEAM counterpart |
| --- | --- | --- |
| (a) value representation and term semantics | `host-values.scm`: maps, keyword order, equality, compare | the BEAM VM's term model |
| (b) Erlang/OTP BIFs and Elixir stdlib | `erlang/element/2`, `lists/reverse/1`, `Elixir.String/split/2`, `K`'s BIF templates | ERTS / Elixir, not BL |
| (c) a NIF's native counterpart | the lazy-memo *cell* (`nif_new`, `nif_read_versioned`, `nif_exchange_version*`) | Rust in `native/lazy_memo` |
| (d) OS, FFI, IO, scheduler, clocks | `native-posix.scm`, `virtual-turn-clock.scm`, actor turn machinery | the BEAM scheduler/ports |

Everything else is a **replica** and must be deleted in favour of the compiled
BL. In particular:
- `host/host-kernel.scm`'s `kernel-rt-*` procedures and `native.intrinsics`'s
  `kernel-override` re-implement `priv/boot/rt.bl`;
- leaves named `"Elixir.BeamLisp.X/f/a"` where `X` is a pinned BL host module
  (`priv/host/*.bl`, header comment "the pinned HOST MODULE for
  `Elixir.BeamLisp.X`") re-implement that module;
- `host/host-lazy.scm` re-implements `lazy_seq.bl`, `lazy_memo.bl`'s policy,
  `seq_cursor.bl` and `deferred.bl`.

When a BL function is a thin wrapper over a category (a)–(d) primitive, give
that primitive its own name in Scheme and compile the BL. If a replica cannot be
removed this round, keep it, and list it in `RESULT.md` under **Residual
replicas**, with the exact reason (e.g. "Env registry: native registry is a
different data structure; env.bl is ETS-bound"). A residual list that is
honest beats a cutover that is not checked.

## Fixed this round

- Value representation: unchanged (table in `CONTRACT.md`). V2 is later.
- Emitted Scheme for the benchmark fixture must stay byte-identical between
  BEAM and native (both run the same `scheme.bl`).
- BEAM semantics: unchanged for every BL program, except where an item's
  purpose is to change it (M: when cycles are detected; D: compile output no
  longer depends on load state). Existing BEAM tests for touched areas must pass.

## Workstreams and file ownership

Paths are relative to the repository root. `NS` = `research/native-seed`.

| WS | Item(s) | Owns (may edit) | Must not edit |
| --- | --- | --- | --- |
| LAZY | M + self-host lazy | `priv/host/lazy_memo.bl`, `lazy_seq*.bl`, `seq_cursor*.bl`, `deferred.bl`, `delay.bl`; `NS/host/host-lazy.scm` (delete or shrink to category c); new `NS/host/native-memo.scm`; lazy tests under `test/bl/` | `native/lazy_memo` Rust (keep the NIF API; pass `:keep`/empty edge sets instead) |
| FRONT | D + T | `priv/boot/compiler.bl`; in `priv/boot/rt.bl` only `source-invocation!`, `source-invocation1!`, `source-invocation2!`, `source-callable!`, `call-invoke`; in `priv/host/env.bl` only `check_source_invocation*` and `source_head` | the rest of `rt.bl` (KERNEL) |
| READER | R | `priv/boot/reader.bl`, `priv/boot/reader-node.bl` | everything else |
| BACKEND | U + C2 | `NS/src/native/scheme.bl`, `NS/fixpoint-full.py` (split and unit cache only), `NS/split-top-level.scm` | `chunks.bl` (CLOSURE) |
| KERNEL | self-host rt (B2) | `priv/boot/rt.bl` except FRONT's functions; `NS/src/native/intrinsics.bl`; `NS/host/host-kernel.scm` | `scheme.bl` (BACKEND) |
| DATA | self-host data modules | `priv/host/{vector,vector_enumerable,set,set_enumerable,sorted,sorted_map,sorted_set,transient,refs,refs_structs,num,decimal,ex_info,multi,compile_error,reactive}.bl` (minimal edits); those modules' leaves in `NS/host/host-leaves.scm`, `host-extra.scm`, `host-compiler.scm` | other modules' leaves |
| SERVICES | self-host runtime-service modules | `priv/host/{record,server,supervisor,trace,atom_guard,link,emit,tiers,loader}.bl` (minimal edits); leaves for those modules and for `Env`/`AOT`/`Compiler`/`Code` in `NS/host/host-compiler.scm`; `NS/host/native-readiness.scm`, `host-source-frames.scm`, `native-text.scm` | `env.bl` and `aot.bl` beyond what FRONT owns |
| CLOSURE | closure extension + P | `NS/update-closure.bl`, `NS/partition-closure.py`, `NS/snapshot-closure.py`, `NS/src/native/{chunks,eval,bootstrap,resolution*}.bl`; host source lists in `NS/prepare-host.py`, `NS/check-host.py`, `NS/check-compiler.py` | `intrinsics.bl` contents (KERNEL); it may move the ns into the closure |

The shared leaf files (`host-leaves.scm`, `host-extra.scm`, `host-compiler.scm`) are
edited by LAZY, DATA and SERVICES. Each deletes or renames only the leaves of
the modules it owns. Keep hunks small and separate.

## Interfaces

- **Adding a namespace to the native closure** is CLOSURE's mechanism. Every
  self-hosting WS writes `NS/speed/<ws>/closure-additions.edn`: a vector of
  `{:ns "host.vector" :path "priv/host/vector.bl" :module :Elixir.BeamLisp.Vector}`
  in dependency order. CLOSURE makes the closure read every
  `NS/speed/*/closure-additions.edn` and documents how a `:remote` to
  `Elixir.BeamLisp.X/f/a` links to the compiled `host.x/f` (this already works
  for `host.compiler-data`). The main thread rebuilds the closure once at
  integration.
- **Testing a module before integration**: compile the module's definitions on
  the pinned SDK, emit them with `native.scheme` (with `:aot-link` as `chunks.bl`
  builds it), load the result in gsi on top of the current host and prelude, and
  run a differential against BEAM. `NS/speed/control/harness.scm`,
  `NS/speed/kernel/{oracle.bl,gsi-run.py}` and `NS/speed/link/emission_check.py`
  are working examples from round 1.
- **Lazy primitive set (LAZY → everyone)**: after LAZY, the only lazy code in
  Scheme is the memo cell in `host/native-memo.scm`, named after the NIF
  functions `lazy_memo.bl` calls.
- **Kernel (KERNEL)**: `kernel-override` and every `kernel-rt-*` are deleted.
  BIF templates (`remote-template`) stay, since they are category (b). Hot `rt.bl`
  functions are rewritten so the compiled BL is fast on both backends.
  KERNEL may add BIF templates. It may not edit `scheme.bl`; if it needs emitter
  support, it records the request in its `RESULT.md`.
- **Reader representation (READER)**: native text is a Scheme string of
  *codepoints*, not UTF-8 bytes. `byte_size` and `binary:at` are O(n) or
  wrong-unit natively, so a byte-indexed reader is slow on native even if it is
  fast on BEAM. Choose a representation that is O(1) per step on both backends
  (e.g. the charlist with a small-integer class table read through
  `erlang/element`, and `case` on class codes). Keep every reader answer:
  forms, `{:meta …}` positions, spans and diagnostics.

## Tools and budgets

- `MAIN` = `/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed`.
  Read-only artifacts (gitignored, do not write):
  `MAIN/NS/out/speed-closure/` (closure partition), `MAIN/NS/out/speed-build/`
  (`stage1` ELF, `host.scm`, `prelude.scm`, `leaves.json`, `chunks/`, `emit.log`).
- **Every** VM or compile command runs through
  `work run --memory 4G --timeout 1800 -- COMMAND…`. The account runs at most
  two at a time, and the timeout includes queue time, so expect to wait.
- Pinned SDK (round-1 behaviour, unchanged language):
  `NS/run run FILE.bl -- args` (3 GiB cap, 240 s per call).
- Your own `priv/` edits: `./bin/bl --cold test test/bl/ONE_test.bl …` from your
  worktree root. Batch the files into one invocation. The first run after a
  `priv/boot` edit rebuilds the toolchain, which takes minutes. Run
  `./bin/bl realm stop` before you finish.
- Gambit: `$(jq -r .gambit NS/toolchain-pin.json)/bin/gsi` under `timeout 120`.
- `NS/speed/bigo/{scaling,profile,incr}.bl` reproduce the study's
  measurements. Run them with a small size list (e.g. `-- 64 256 1024`).
- **Forbidden in agents**: rebuilding the native compiler image, `fixpoint*.py`,
  `chunks.bl build-next` over all chunks, the actor corpus, the warm-core
  benchmark, full `bl test`, producing an SDK or regenerating the seed floor.
  The main thread does those once.

## Definition of done

1. Hard cutover: the old path is deleted in the same change.
2. Focused checks are green and recorded in `NS/speed/<ws>/RESULT.md`, with the
   exact commands and their output summaries. The file also lists **Residual
   replicas** (self-hosting WSs) and **Risks for integration**.
3. Commit on your branch, in your worktree only. Never push, merge, rebase or
   touch other branches. The final message lists commits, changed functions,
   checks run and risks.
