The private fast path applies only to `emit-unit`'s owned C output. Let
`A = {LF10} ∪ {ASCII32…126}`.

| C construction path | Why its output stays in A |
|---|---|
| `state`, `reg`, `block`, `pool`, `service` (c.bl17–30) | Slot, block and pool indices begin as integers and grow only by integer increments/counts. Decimal integer spelling is ASCII. |
| `r`, `k`, `jump`, `action`, `action-at` (31–37) | Fixed ASCII C tokens, allocated numeric indices, fixed action names and boolean0/1. |
| `lower-simple-clause` (129), function return/tick/closure (153), call (213), guard/case/if/value/register branches (110,305) | Each block combines fixed ASCII/LF templates with those numeric/index expressions. Backend-created `slot-node` carries an allocated integer, never a Source variable's spelling. |
| `emit-unit` (381–393) | Fixed ASCII/LF header/trailer plus ordered numeric case labels and the owned blocks. The only input-derived C identifier goes through unchanged `scalar/ident` (scheme.bl5): `v` followed by `_` and decimal Unicode codepoints, hence ASCII even for Unicode names. |

Induction over lowering of canonical compiler ANF and emitter-created internal
nodes therefore gives `c-source ∈ A*`. Concatenation and joining with LF
preserve this property. `emit-unit` starts with its own fresh state; resolver
options supply Scheme service values, not raw C blocks.

Authored literal strings, variable/function names, remote/service expressions,
Source filenames, annotations and source frames go into the **Scheme** constant
and service vectors through `pool`/`service` (21–28,75–81,153–180,305–341).
They are never interpolated into C. Their ordinary `scalar/text`/`literal`
formatting, including Unicode and every control character, remains unchanged.
The separate `c-lambda` unit-name quoting also still uses `scalar/text`.

On A, canonical `scalar/text` changes only backslash, quote and LF. The new
private function performs those exact literal global replacements in that
order, then adds the same surrounding quotes. Backslash must be first so
escapes introduced by quote/LF are not doubled. Adjacent special characters
preserve the same characterwise result; the SDK fixture checks all9,216
ordered pairs,96 singletons and8 longer/empty cases.

Passive inspection of all46 actual compiler C units and13 actual actor C units
found exactly this alphabet across **14,280,885 bytes**. The index/unit hashes,
per-file sizes and special-character counts are retained in
`alphabet-observation.json`. This observation is not SDK parity or native
qualification. Root's canonical anonymous-form SDK fixture additionally checks
old/new quoted bytes and exact reconstructed FFI wrappers for every unit.

Source identities:

| Source | SHA256 |
|---|---|
| native.c before | `0934dd46b7761649f5e9018d9b19cb8f4dc5a836634b363971de043944eec42c` |
| native.c after | `e38e825c9a4b90940a77e8bfd9f86458f9afba0f2f8666ea486b759103d6a883` |
| native.scheme unchanged | `76f40ac5b9b10efd033a84e984926d46d20494322338722ba55365eebf566cab` |
| Root-owned fixture after Reader fixes | `3aa8516b2e8f2c0795caf1078beac8dc765fa4f47e8da3bfe7580659fe6a4467` |

The authoritative fixture is now
`research/native-seed/fixtures/generated-c-quote-parity.bl`; the earlier staged
`parity.bl` must not replace it. Only native.c changes inside the finite C
suffix. The eighteen compiler Source units remain byte-identical. Existing
canonical profile extension replaces the five suffix provider records, so
the changed native.c ledger row needs no Source18 gate exception.
