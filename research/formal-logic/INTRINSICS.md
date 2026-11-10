# A callee is part of a program's meaning

The source front end now uses the reviewed catalog in `formal.intrinsics`,
profile `:bl/exact-intrinsic-identities-v1`. A remote call is identified by
module, function **and arity**, then checked against its typed core operation.
Sharing a spelling does not establish sharing a meaning.

The actual-BEAM observer exposed a concrete earlier error. The old front end
read `BeamLisp.Num/div` as integer quotient. For a state containing `7`, the
model returned `3` while the compiled handler returned `3.5`. The adapter
reported disagreement and refused that value as an integer state. The raw
pre-fix source, compiler calls, model and observation are retained in
`evidence/intrinsics/intrinsics-probe.json` (probe commit `5d4724548`).

The repaired front end passed 4,877 assertions across nine focused files,
including 135 identity regressions. The eight prior runtime observations also
passed fresh-VM validation through the repaired front end, with no handler
capture calls or observed-module loads in the calibrated record-check window.
These checks qualify this implementation; they do not establish its soundness.

The formal Int/Bool core now refuses that call. The BL language function keeps
its existing floating/decimal behavior. Modeling it needs the corresponding
source numeric domain; it cannot borrow the integer-quotient contract.

## Reviewed identities

| Source target | Meaning in this core |
| --- | --- |
| Erlang `+/-/*`, ordered comparison, `==` and `=:=` at the reviewed arities | Typed Int arithmetic/comparison or same-sort scalar equality. |
| Erlang `div/2`, `rem/2` | Signed integer quotient and remainder, including the exact zero-divisor failure. |
| Erlang `not/1` | Boolean negation; Int operands are refused. |
| `BeamLisp.Num` add/sub/mul/neg, comparisons, num_eq, sign predicates | Their reviewed meanings on admitted core operands. `div/2` is excluded. |
| `BeamLisp.Ns.Rt` eqv, not_, sign predicates | BL scalar equality, truthiness negation and admitted integer predicates. |
| `BeamLisp.Ns.Core` inc/dec/quot/mod | Their actual reviewed scalar meanings and arities. |
| `BeamLisp.Ns.Rt` get/assoc/assoc_variadic | The separately specified ordered closed-record operations. |

Canonical `:arith` nodes must also carry a reviewed matching Num function/BIF
pair and exactly two arguments. A mismatched or unknown pair is refused.
Erlang's raw `not` and BL's `not` remain distinct: `(not 7)` returns false in
BL, while `erlang:not(7)` raises. The strict Boolean target cannot borrow BL
truthiness semantics merely because both names contain “not”.

## The remaining declared Var assumption

The compiler leaves some calls, including variadic `assoc`, as fetched global
Vars. The formal front end still accepts declared `get/assoc` calls in its own
explicit `formal.core.intrinsics` compilation namespace, with no exact-member
lookup and no lexical shadow. Their record operation, arity, literal keys,
evaluation order and whole-record outcome are checked as before. Foreign
namespaces and other unresolved globals are refused.

This exception is a **declared intrinsic meaning**, not evidence that a mutable
runtime Var always has that binding. The actual observer conveys the caller's
Env. It does not freeze global resolution or prove absence of external effects.
The exact physical callee catalog closes the host-identity mismatch, while this
separate environment boundary stays visible. The first tightened run rejected
legitimate variadic updates; its failed log is retained. The follow-up preserves
only this explicitly scoped declaration.

Stored source definitions are freshly re-elaborated before proof or runtime
checking. An old, rehashed `Num/div` source paired with the former quotient
model is therefore refused before its proof can be considered. Older receipts
remain historical evidence for their recorded implementation, not authority
for the repaired admission policy.

## The next architectural boundary

An eventual formal source declaration should carry a closed compilation context:
its actual resolved intrinsic identities, semantic profiles and immutable code
dependencies. Logical assumptions about inputs and runtime assumptions about
bindings should occupy separate fields. Neither a Var handle nor an Env ID is a
portable mathematical constant or proof-granted execution authority.

There are two useful future routes: restrict a formal block to immutable reviewed
intrinsics, or give admitted mutable calls explicit checked summaries and a
binding-validity boundary. Either needs implementation and qualification against
the SDK's real Source/custody model. Rewriting a fetched call into a fixed host
call and calling it “the same source” would hide a semantic change; any such
translation must state and justify its binding precondition.

The Z3/OxiZ term interface is unchanged. Both engines receive the same corrected
source interpretation. The catalog, BL elaborator, actual compiler and runtime
remain reviewed implementations; this repair is not a proof of their soundness.
