# Native speed fan-out: shared contract

Dossier: [`native-speed.bl.org`](native-speed.bl.org). This file is the part
every workstream must obey so four agents can work in parallel and merge.

## Goal

The warm read → compile → emit pipeline of the self-hosted native compiler
(stage-1 Gambit image) is 35× slower than warm BEAM (132.7 ms vs 3.8 ms), the
reader 127×. The measured cause is a flat ~300–500 ns toll on every primitive
operation (`evidence/bridge-microcost`, `evidence/warm-core-counts`): late
string-keyed binding, BEAM guards emulated through remote calls, allocating
key comparisons and interpreted patterns. Remove the toll structurally.

The main thread alone rebuilds the full native compiler, runs the Source
corpus, the warm-core benchmark and byte-equality of emitted Scheme. Agents run
only focused, fast checks (seconds; at most ~3 minutes wall per check).

## Fixed value representation (do not change in this round)

| BL value | Native representation |
| --- | --- |
| nil | the singleton `bl-nil` = `(vector 'nil)`; test with `eq?` |
| true / false | `#t` / `#f` |
| keyword / atom | interned Scheme symbol whose name begins with `:` (`(bl-key "x")` = `':x`) |
| integer | Scheme exact integer (fixnum or bignum) |
| float | `(vector 'float <flonum>)` (see `bl-float`) |
| text / binary | Scheme string |
| list | Scheme pairs and `'()` |
| tuple | `(vector 'tuple <items-vector>)` |
| map | `(vector 'map <storage>)`, storage sorted flat (≤16) or AVL; iteration in Erlang term order |
| vector / set | `(vector 'vec …)` / `(vector 'set …)` |
| multi-arity fn | `$blfn` tuple `{:$blfn {arity → fn} {min fn}|nil}` |

Map iteration order and every observable ordering must stay exactly as today:
emitted Scheme text must remain byte-identical between BEAM and native.

## File ownership

| WS | Owns (may edit) | May touch narrowly |
| --- | --- | --- |
| L · direct linking & call protocol | `src/native/chunks.bl`, `src/native/eval.bl`, `src/native/bootstrap.bl`, `host/host-compiler.scm`, `host/host-leaves.scm` (naming leaves only, no semantic change) | `src/native/scheme.bl`: only `remote`, `ordered-call`, `ordered-language-call`, `ordered-target-call`, `multi-layout`, `emit-multi*`, the `:global` `:remote` `:apply` `:invoke` cases of `emit` |
| K · native kernel | `src/native/intrinsics.bl`, new `host/host-kernel.scm`, new fixtures under `speed/kernel/` | none |
| V · value fast paths | `host.scm`, `host/host-values.scm`, `host/host-lazy.scm`, `host/host-extra.scm`; leaf bodies in `host/host-leaves.scm` only where they call value primitives | none |
| C · compiled control | `src/native/scheme.bl` everything not listed for L | none |

`host-leaves.scm` is shared by L (turning each `(native-add-leaf! "m/f/a" (lambda …))`
into a named top-level procedure) and V (fast bodies). L only renames/binds;
V only edits bodies. Keep hunks small.

## Interfaces between workstreams

- `native.intrinsics/remote-template` and `kernel-override` (stub in
  `src/native/intrinsics.bl`). L calls them from the AOT context in
  `chunks.bl`; K implements them. Templates may reference host procedures
  defined in `host/host-kernel.scm` (loaded after `host-compiler.scm`).
- The AOT emission context passes an explicit option `:aot-link {…}` (owned by
  L) into `native.scheme/emit`. Any new emission behaviour that depends on
  linking is keyed on it. The benchmark's own emission (no resolvers, options
  `{:ns "user" :namespace "user" :namespace-qualified? true :callable-arities? true}`)
  must produce the same bytes on BEAM and native; it does by construction since
  both run the same `scheme.bl`.
- `native.scheme` and `native.eval` must NOT require any namespace outside the
  closure (`update-closure.bl` refuses added dependencies). `chunks.bl` may.
- Leaves: after L, every registered leaf has a stable Scheme binding name
  produced by `(native.bootstrap/leaf-binding-name "m/f/a")`. K's templates may
  call leaves through those names.

## Tools

- Pinned SDK only: `research/native-seed/run run FILE.bl -- args` (3 GiB cap,
  240 s). One bl VM at a time per agent. Never run `bl test` suites.
- Gambit: `$(jq -r .gambit research/native-seed/toolchain-pin.json)/bin/gsi`.
  Run gsi under `timeout 120`.
- Host fixtures: `fixtures/host-*-check.scm`, harnessed by `check-host.py`
  (expected check counts are asserted there; update counts when you add checks).
- Read-only reference artifacts (do not write):
  `/home/othman/code/undefine/beam-lisp--execution-protocol/research/native-seed/out/compiler-native-owner/`
  (`leaves.json`, `partition/`, `chunks/*.functions.scm` = what the compiler
  currently emits, `prelude.scm`).
- Do not rebuild the compiler image, run `fixpoint*.py`, `chunks.bl build-next`
  over all chunks, the actor corpus, or any benchmark.

## Definition of done for an agent

1. Hard cutover: the old path is deleted, not left behind a flag (except the
   explicit `:aot-link` option boundary above).
2. Focused checks green and recorded in `speed/<ws>/RESULT.md` with commands.
3. Committed on the agent's branch; final message lists commits, changed
   functions, checks run, risks for integration.
