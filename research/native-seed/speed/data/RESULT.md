# Workstream DATA: self-host the data host modules

Round 2, contract [`../CONTRACT2.md`](../CONTRACT2.md). Branch `native-self-data`.

## Summary

| Module (`priv/host`) | Leaves before | Status this round |
| --- | --- | --- |
| `ex_info.bl` → `host.ex-info` | 5 (`host-compiler.scm`) | **self-hosted**: leaves deleted, module compiles natively, differential below |
| `compile_error.bl` → `host.compile-error` | 1 (`host-extra.scm`) | **self-hosted** |
| `sorted.bl` → `host.sorted` | 15 (`host-extra.scm`) + the list-of-entries replica (`native-sorted-*`) | **self-hosted** over a new OTP `gb_trees` port (category b) |
| `num.bl` | 15 | residual (needs `host.decimal`) |
| `decimal.bl` | 6 | residual (stdlib, regex FFI, `term_to_binary`) |
| `vector.bl` (+`vector_enumerable`) | 7 | residual (value representation) |
| `set.bl` (+`set_enumerable`) | 6 | residual (value representation) |
| `transient.bl` | 9 | residual (not checked this round) |
| `refs.bl` (+`refs_structs`) | 20 | residual (processes, Env, Execution, LazyMemo) |
| `multi.bl` | 1 | residual (Env/Loader) |
| `reactive.bl` | 1 | residual (LazyMemo, Refs) |
| `sorted_map.bl`, `sorted_set.bl` | 0 | no leaves; not added (only `__struct__`/`__info__`, never called natively) |

21 replica leaves and 4 replica procedures are deleted. **No `priv/host/*.bl` file was edited**, so
BEAM semantics are unchanged by construction and no BEAM test batch was needed.

`Elixir.BeamLisp.Float/ratio/1` and `to_float/1` (`host-leaves.scm`) have **no BL source**
(`git grep BeamLisp.Float` finds only these leaves). They are not replicas. They stay.

## What changed

- `host/host-extra.scm`: deleted `native-sorted-new/-entries/-find/-put/-delete`, the 15
  `Elixir.BeamLisp.Sorted/*` leaves, `native-compile-error` and `Elixir.BeamLisp.CompileError/exception/1`.
  `native-canonical-compare` stays because `Enum/sort_by/2` uses it.
- `host/host-compiler.scm`: deleted `native-ex-info` and the 5 `Elixir.BeamLisp.ExInfo/*` leaves.
  `native-exception-value?` stays. It is the representation predicate, and `Exception/message` uses it.
- New `host/native-gb-trees.scm` (category b). It is a port of OTP 29 `gb_trees.erl` with the same
  node shapes (`{Size, Tree}`, `{K, V, Smaller, Bigger}`, `nil`), the same size-based balancing
  (p = 2) and the same `{ordered, Nodes}` iterator. A tree built natively is therefore the exact
  term BEAM builds. Keys compare in Erlang term order, where `1 == 1.0` also holds inside tuples and
  lists. `native-term-compare` gets this wrong for tuples: it is the round-1 term-order difference
  K reported for V. The port defines `empty/0 size/1 lookup/2 is_defined/2 insert/3 enter/3
  delete/2 smallest/1 largest/1 values/1 iterator/1 iterator_from/2 next/1`. `sorted.bl` reaches
  them through `erlang/apply/3`.
- New `host/native-data-bifs.scm` (category b). It holds the Erlang and Elixir stdlib functions the
  three modules call:
  - `erlang/error/2`, which delegates to the live `erlang/error/1` leaf.
  - `Elixir.KeyError/exception/1` and `Elixir.CaseClauseError/exception/1`, built as defexception
    structs with the declared fields.
  - `Elixir.Exception/message/1`. It calls the linked module's `message/1` if one exists, else the
    generated messages of KeyError, CaseClauseError and ErlangError, else `:message`, and it
    reports a non-binary result the way Elixir does.
  - `Elixir.Keyword/get/2` and `fetch!/2`.
  - `Elixir.String.Chars/to_string/1`, which reuses `native-vector-index-text`, already exactly
    that protocol dispatch.
- `speed/data/closure-additions.edn`: `host.ex-info`, `host.compile-error`, `host.sorted`, in that
  order. The format is the one integrated `update-closure.bl` reads.

## Checks

All commands run from the worktree root. VMs and gsi run under `work run`.

1. **Native compilation and link coverage.**
   `work run --memory 3G --timeout 2400 -- bash research/native-seed/speed/data/beam.sh`
   runs `speed/data/emit.bl` on the pinned SDK. It compiles the three modules as
   `update-closure.bl` does, then emits every definition with the `chunks.bl` AOT link context, with
   the modules' own leaves removed from the leaf set. It prints
   `DATA_EMITTED host.ex-info,host.compile-error,host.sorted defs=52 unresolved=6`. The 6 unresolved
   remotes are exactly the stdlib functions now in `native-data-bifs.scm` (`CaseClauseError/exception/1`,
   `Exception/message/1`, `KeyError/exception/1`, `Keyword/fetch!/2`, `Keyword/get/2`,
   `String.Chars/to_string/1`), plus `erlang/error/2`, which is also added there. `leaves.json` predates
   those leaves. Every other remote links to a leaf or to compiled closure code (`rt/print_str`, …).
   The run then writes the BEAM oracle (`speed/data/oracle.bl`): `DATA_ORACLE_WRITTEN 698 skipped 0`.
2. **Host smoke.** `work run --memory-high 900M --memory 1G --timeout 900 -- bash research/native-seed/speed/data/smoke.sh`
   loads this checkout's host sources plus the two new files and exercises gb_trees, Keyword and
   KeyError. It prints `DATA_SMOKE_OK`.
3. **Differential.** `work run --memory-high 2500M --memory 3G --timeout 1800 -- python3 research/native-seed/speed/data/check.py`.
   The program is this checkout's host sources (prepare-host order, after the cutover), then the two
   new files, then the compiled closure definitions the modules reach, then `out/a/data.scm`, then
   `check.scm`. `speed/data/extract.py` pulls those closure definitions out of the read-only
   reference prelude: 158 owners, 357 KB. The whole prelude cannot be interpreted, because its host
   part carries `c-declare`. Each BEAM row is called through the compiled arity cell
   (`v_host.x/f$n`), the cell remotes link to after integration.

   Comparison rules: values must be strictly the same (types, float bits, map content). Errors must
   have the same class and the same normalized Elixir exception module, plus the same message
   whenever the native reason is an exception struct.

   Result: **692 of 698 rows agree with BEAM**: 641 compiled calls return a value and 57 raise.

   | Module | Signatures (every deleted leaf) | Rows |
   | --- | --- | --- |
   | ExInfo | `ex_info/2 ex_data/1 ex_message/1 ex_original/1 raise_payload/1` | 16 + 4 × 16 |
   | CompileError | `exception/1` (binary, keyword lists with/without file/line/form, missing `:message`, non-list) | 10 |
   | Sorted | `map_new/1 set_new/1 map_put/3 map_delete/2 map_get/3 map_has_key?/2 set_del/2 set_member?/2 set_add/2 map_count/1 set_count/1 map_to_list/1 set_to_list/1 last_entry/1 last_key/1` over 15 keys (int, float, `1`/`1.0` collisions, text, keywords, nil, booleans, vectors, lists, symbols, decimals), a 40-entry tree (balancing), wrong-type inputs | 608 |

   The 6 rows that disagree are outside this workstream's files and are left as they are:
   - 2 rows (`ex_message`, `raise_payload` on `%Foo{a: 1}`): `Kernel/inspect` key order for a
     struct whose module is not loaded. BEAM gives `%{a: 1, __struct__: Foo}`, the host
     `Kernel/inspect/1` leaf gives `%{__struct__: Foo, a: 1}`. This is the existing round-1 leaf
     (`native-erlang-inspect`).
   - 2 rows (`ex_message`, `raise_payload` on an exception struct of the non-existent module
     `Foo`): BEAM calls `Foo.message/1`, gets `UndefinedFunctionError`, and embeds its stacktrace in
     the message. Natively, an unlinked module falls back to the `:message` field (`"m"`). The
     stacktrace text cannot be reproduced.
   - 2 rows (`CompileError/exception/1` on `12` and on `nil`): the emitter's clause fallthrough
     raises the host error `native seed: function clause` instead of `FunctionClauseError`. See
     Risks.

   On the first run Sorted had 22 more mismatches, all int/float key collisions (`{3, 1}` against
   `{3, 1.0}`): the host `native-term-compare` treats them as distinct inside tuples, while Erlang
   treats them as equal. `native-gbt-compare` fixes this for gb_trees. There were also KeyError and
   ErlangError message formats, which `native-data-bifs.scm` now reproduces.

## Residual replicas

- **Vector (7 leaves), Set (6).** The native representation is fixed this round (CONTRACT.md):
  `#(vec #(pvec-v1 …))` is a binary trie and `#(set map)` is a map. `vector.bl` operates on the
  BEAM shape, a struct map with `:items` holding a tuple or a 32-way `{:bl_vec …}` trie. `set.bl`
  operates on `%{__struct__ Set, members: MapSet}`. Compiled natively, they reach the native values
  only through the `maps/get :items` / `:members` projections. Those are O(n) per call (projection,
  or `native-struct-fields`), and their `maps/put` results are plain tagged maps, not `vec`/`set`
  values, so equality and every `bl-tag? 'vec` consumer would break. Self-hosting them needs the V2
  representation (native storage = the BEAM terms).
- **Num (15), Decimal (6).** `num.bl` calls `BeamLisp.Decimal/{new,add,sub,mul,div,neg,compare,signum}`,
  so it can only compile with `host.decimal` in the closure. `decimal.bl` needs about 20 more stdlib
  leaves:
  - `Float/parse` and `Float/to_string`
  - `Integer/{digits,floor_div,gcd,pow,to_string}`
  - `String/{pad_leading,split_at,to_integer,trim_trailing}`
  - `List/duplicate`, `binary/encode_unsigned`, `erlang/{band,bsr}`, `MatchError/exception`
  - `Macro.Env/in_guard?` and `elixir_env/to_caller`, for its macro function
  - `erlang/term_to_binary/1`, used for float bits

  `Decimal/parse` runs through `Elixir.Regex`, whose native leaves are the C FFI in
  `native-text.scm`, which interpreted gsi cannot load. I could neither write nor check those
  faithfully inside this round's budget.
- **Transient (9).** It compiles: its unresolved remotes are only `Enum/chunk_every`, `Enum/member?`,
  `Process/delete` and `CaseClauseError/exception`. But cutting it over replaces the native mutable
  transient (`native-transient`, `seed-self`) with process-dictionary state, and I did not run a
  differential for it.
- **Refs (20), Multi (1), Reactive (1).** Their remotes include Env (`assert_*`, `max_heap`,
  `member?`, `with_native_command_callback!`), Execution, LazyMemo (LAZY), `Task`, `spawn*`,
  `send`, `self`, `demonitor` and `process_flag`. `Refs` futures and promises need a native process
  model, and native atoms are opaque `native-ref` structs today. These wait on LAZY, SERVICES and
  FRONT.

## Risks for integration

- **`erlang/fun_info/2` must answer `:module` per closure-member module.** All three modules find
  their own atom with `(erlang/fun_info (fn [] nil) :module)`. `ex_info.bl` puts it in the
  `__struct__` of every ExInfo it builds (`struct_map`), and `compile_error.bl` in every
  CompileError. If the integration leaf answers anything other than `:Elixir.BeamLisp.ExInfo`
  (resp. `CompileError`, `Sorted`) for closures compiled in `host.ex-info` (resp. …), every
  `ex-info` value changes type. A procedure-only leaf cannot know the defining module.
  `speed/data/emit.bl` (`self-module-call`) shows the rule I used and recommend for the shared
  linker: a `:remote` to `erlang/fun_info/2` whose first argument is a closure literal (`:fn`, or
  the self-application constructor) and whose second is the literal `:module`, in a unit with
  `:module M`, links to the constant `{:module, M}`. As requested, I did not add the leaf to the
  shared host files.
- **New host files must join the host list.** `host/native-gb-trees.scm` and
  `host/native-data-bifs.scm` go after `host-compiler.scm` (they use `native-remote-available?`,
  `native-erlang-inspect` and `native-vector-index-text`) in `prepare-host.py` / `check-host.py`
  / `check-compiler.py`, so that `leaves.json` registers them. Until then the 6 remotes above are
  unresolved and the closure build refuses `host.ex-info` / `host.compile-error` / `host.sorted`.
- **Sorted's native representation changes** from `{__struct__, entries: [...]}` to BEAM's
  `{__struct__, tree: gb_tree}`. No host Scheme reads `:entries` any more (checked with grep).
  `host-kernel.scm` names the struct modules only. A sorted map printed natively now shows its tree,
  as BEAM's struct does.
- **Sorted goes through `erlang/apply/3`.** Every gb_trees call is a dynamic
  `native-remote "gb_trees/F/A"` lookup (one `equal?` table probe), not a linked cell. A KERNEL
  template for `erlang/apply/3` with a literal module and function and a literal argument list
  would make these direct leaf calls.
- **Emitter function-clause errors.** A compiled multi-clause guarded `defn` called with no matching
  clause raises the host error `native seed: function clause`, not a BEAM `FunctionClauseError`.
  `CompileError/exception/1` on `12` and on `nil` shows this, and BACKEND's `scheme.bl` owns it.
- The interpreted check needs `extract.py`'s closure subset. It assumes the closure units it pulls
  from the reference prelude match the round-1 integrated host. Rerun it against the rebuilt
  prelude after integration.

## Skipped under the updated rules

- The microcost of the 5 hottest deleted leaves against compiled BL. The coordinator dropped speed
  measurements from the acceptance criteria, so I ran no timing.
- A `./bin/bl --cold test` batch. No `priv/host/*.bl` file was edited, so there is no BEAM
  behaviour to re-test.
