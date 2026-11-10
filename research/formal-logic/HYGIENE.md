# A name is not a binding identity

The source/core bridge must distinguish three things: a name written in source,
the compiler's fresh lexical alias, and the caller's semantic input role. Their
strings may coincide without denoting the same binding.

The retained pre-repair probe demonstrated a concrete mistake:

```clojure
(fn [a] (let [local 10] (erlang/+ a local)))
```

With the compiler's fresh counter reset, its let alias was `local_3`. Giving
the function parameter the semantic role `"local_3"` caused the old elaborator
to name both Core variables `local_3`. It modeled 20 for input 7, although the
actual function returned 17. Its conditional term certificate checked a true
property of that wrong model. It did not establish the claimed source behavior.

The same problem affected the two expression front ends: a free input named
`local_1` could collide with an ANF let alias and be replaced by 10. A separate
bug let a free global in a function body borrow a parameter's compiled alias.
These were source-interpretation errors, rather than failures in arithmetic
proof rules. The original objects, ANF and observations are preserved under
`evidence/hygiene/baseline/` at their recorded implementation commit.

## The repaired boundary

`formal.anf-inputs` introduces declared expression and loop inputs as actual
compiler lexical parameters. It supplies a separate alias for each source name
through the compiler's existing `:locals` table. Those aliases end in `/N`;
the pinned compiler's fresh variables end in `_N`. The two families are
disjoint. Intrinsic and macro names obey the real compiler's lexical shadowing
rule: an Int input called `inc` is a value, and a call through it is refused by
the formal fragment.

Expression/loop input keys are one exact, unqualified source identifier, at
most 512 bytes, with at most 4,096 inputs. Qualified references belong to actual
Source selection. The semantic-value entry point retains symbol-key convenience
but refuses two keys that normalize to the same source name. Literal, partial,
comment-bearing or ambiguous input spellings are refused.

Function-source semantic roles remain independent portable names. They may
contain `/` or look exactly like compiler or Core names. The source parameter
patterns supply the lexical aliases; the role names describe the mathematical
inputs. A role does not declare an ambient global.

Every ANF let now receives its own fresh Core identity. The allocator reserves
all local identities found inside the supplied Core binding values, including
compound values. Nested elaboration shares the allocator. The resulting Core
is then alpha-normalized as before. Changing source aliases or compiler fresh
counters preserves the canonical semantic program for these qualified cases.

Low-level `formal.elaborate/from-anf` interprets supplied bindings as lexical
aliases only. `formal.source/lower` likewise resolves only lexical values.
Unresolved global values and selected references require the selected Source
adapter. The existing synthetic namespace exception for declared record *calls*
remains explicitly scoped; scalar declarations cannot turn arbitrary globals
into mathematical inputs.

## Checking the original object again

Source-backed contracts reconstruct their source/Core relation on preparation.
The actual old contract from the retained probe is therefore refused when its
stored Core disagrees with the repaired elaboration, even though its identity
was valid for the old data. Historical evidence is not silently rewritten.

Both backends now refute the old `20` promise under input 7 and check the `17`
promise. The original selected Source observer also returns 17 with the
colliding semantic role. Plain expressions, semantic values, function-source
contracts, selected contexts and loops use the same repaired lexical boundary.

The focused first run passed 4,201 assertions across five files, including 142
hygiene assertions before the additional input-spelling cases. Tests cover
role/binder collisions, nested Core binding values, real intrinsic shadowing,
forbidden globals, alpha stability and actual original Source execution.
`hygiene-check.bl` checks the actual historical object and records the repaired
source/Core/native behavior. The final coherent receipt is in
`evidence/hygiene/qualification.json`.

This is a repair and finite implementation qualification. It adds no universal
source-preservation theorem or Lean theorem, changes no production runtime
default, and grants no compiler proof authority. The current immutable SDK
remains the same.
