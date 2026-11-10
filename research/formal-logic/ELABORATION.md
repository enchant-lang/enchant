# Independently checking the ANF/Core pair

`formal.elaboration/check` checks a closed, term-based translation relation
between supplied actual compiler ANF and a typed Core. It does not call the
elaborator, canonicalizer, compiler, reference evaluator, proof producer, native
worker, or solver. Its syntax-directed rules live in a separate module with a
separate exact module/function/arity table. The shared Core type checker and
canonical formal-data identity implementation remain dependencies.

The object is ordinary data: `:formal/elaboration 1`, profile
`:bl/anf-core-validation-v1`, complete `:anf` and `:core`, ordered `:parameters`,
`:input` (`:expression` or `:function`), `:aliases`, `:record-vars`, and the
canonical identity fields. `claim` and `function-claim` only package a proposed
pair. `formal/check-elaboration` checks it afresh. A recomputed hash authenticates
the exact proposed contents; it cannot make a wrong relation pass.

For expressions, aliases explicitly map compiler lexical identities to semantic
input roles. A standalone supplied mapping is a premise. For function ANF,
the checker recognizes the exact self-application scaffold and derives this map
from its ordered variable parameters; a caller cannot supply a replacement map.
The Source/expression front end supplies the lexical mapping from its actual
compiler input environment. Selected Source supplies the mapping of its
specialized ANF. Neither boundary's producer is invoked by the checker.

The relation checks literals, lexical references, fresh Core binders, eager
`let` and sequencing, selective branches, Bool conditions, non-Bool truthiness
with retained evaluation, exact reviewed arithmetic calls and canonical
arithmetic identities. It checks ordered closed-record construction, projections,
eager defaults and repeated ordered updates too. Removing an evaluation because
its value is unobserved fails this check. Fresh binders cannot capture inputs or
other binders, including the previously failing `local_3` example.

Exact runtime record calls are separate from an unresolved synthetic `get` or
`assoc` Var. The latter requires `:record-vars :declared` and adds
`:ambient-record-var-must-match-declaration` to the returned assumptions. It is
never silently called a closed runtime binding. Other globals, computed calls,
effects and recursion are refused. Author annotations do not grant admission.

There are hard limits of 2 MiB per proposed object, 4,096 relation visits, depth
128 and 64 packed arguments. Core typing and the canonical-data codec impose
their own bounds as well. Reaching a bound refuses the relation; it does not
prove a language exception or a mathematical impossibility.

The source elaborator and the final selected-ANF lowering now require this check
before returning an elaborated result. Their result carries `:elaboration
{:object ... :check ...}`. Contracts reconstruct it during preparation, and
verification exposes the check separately from the conditional term proof and
Source connection. Stored contract and context identities do not change solely
because this extra gate exists. No cached check is accepted as authority.

This is an independent implementation check, not yet a mechanized soundness
proof. In particular:

- Actual Source to compiler ANF remains a compiler/expansion connection.
- Selected-unit closure specialization, captured environments, beta expansion
  and ordered initializers remain reviewed transformations before the checked
  final ANF boundary.
- The BL checker, primitive semantics, Core implementation and execution on
  BEAM still require soundness and preservation arguments.
- A checked relation does not prove a postcondition, input feasibility,
  total normal return, runtime observation, or compiler authority.

The separate term certificate checker proves a different proposition: the
conditional Core contract. Keeping these two results visible prevents a good
mathematical proof of the wrong source model from being presented as a source
proof. The prior naming repair demonstrated why this matters.
