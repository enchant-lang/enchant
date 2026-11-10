# Checking selected closure specialization

`formal/check-specialization` independently checks the relation between an
original SDK contextual unit and a proposed residual ANF program. Its pure
implementation is `formal.specialization`, separate from the selected-source
producer, compiler, expander, ANF walkers/constructors, Core lowering and solver.
It reads the actual supplied trees rather than generating a second residual
program. Its profile is `:bl/selected-specialization-validation-v1`.

The closed object contains `:formal/specialization 1`, profile, original `:unit`,
selected `:target` reference, ordered typed `:parameters`, ordered input-alias
`:arguments`, proposed `:anf`, and canonical identity fields. `claim` only
packages this data; `check` validates it afresh. A recomputed identity cannot
authorize a changed reduction. The original unit has the pinned SDK's version-2
compiled-contextual-unit grammar. The target must belong to that supplied unit's
export table; this data check does not grant Source execution authority.

The admitted scope is initialize the declaration-only unit, then call the target
once. Every row occurs exactly once in the initialization schedule. Slots and
references are distinct. Function constructors become immutable captured lexical
environments. A scalar initializer always remains an ordered residual `let`,
even when unused. Its first failure can prevent the target call.

A call checks one fresh residual argument binding per parameter, in order.
Each argument is compared under the **caller** environment. The body is compared
under the **definition** environment extended by those argument values. It
cannot borrow a same-spelled caller local in place of a captured scalar/helper.
Residual input aliases and all residual binders remain globally distinct. The
compiler's recursive-self knot is recognized exactly; self references cannot
borrow an outer binding. Recursive calls, higher-order/escaping values, computed
argument lists and unlinked references require other rules and are refused.

Conditionals, sequencing, scalar literals, native and canonical-arithmetic
leaves, ordered map pairs and literal list cells retain their complete shapes
and operand order. The checker neither evaluates a native leaf nor assigns its
meaning. Unchanged leaf identity is a different fact from admitting that leaf as
a pure formal intrinsic. The following ANF/Core checker owns that admission.

The selected-source producer now requires both checks. The specialization
checker derives the residual-input alias-to-role map from the target's ordered
call inputs. The ANF/Core gate consumes that derived map, rather than accepting
the producer's separate input-binding map as its own premise. This binds the two
relations at the shared residual ANF and parameter boundary. Prepared selected
contexts expose both complete objects/checks. Contracts and the common evidence
envelope expose `:specialization` separately from `:elaboration`, the conditional
term certificate, and Source/runtime connection. Context and contract semantic
identities remain unchanged for an unchanged source/Core proposition.

This is a reviewed rule checker, not a proved preservation theorem. It assumes
the wellformedness of an SDK-compiled unit, including closure construction and
lexical binding. The selected-source front end supplies the actual unit from
the SDK and its phase check. Standalone checking authenticates no Source
provenance, phase authority, world selection or native admission. Uncalled
closure bodies are not function contracts. The unit model, closure environments,
named binding representation, checker implementation, original SDK Source
compiler and BEAM runtime still need their own mechanized connections. No
termination, purity, total normal return, postcondition or compiler authority
follows just from this reduction check.

Limits are 4 MiB per object, 128 initializers, 16 parameters, 64 packed arguments,
256 expanded calls, 65,536 relation visits and depth 128. Canonical data and the
following Core relation impose additional bounds. Refusing a capacity is not a
modeled language exception. Checking invokes no runtime initializer, application
function, specializer, compiler or solver.
