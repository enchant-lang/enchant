# A formal declaration carries its binding context

A function's meaning depends on what its calls resolve to. The research API
now makes one part of that environment explicit as a first-class BL value.

```clojure
(def binding
  (formal/source-context
    "(fn [s msg] (assoc s \"n\" (+ (get s \"n\") (get msg \"amount\")) \"flag\" false))"
    [["state" state-type] ["message" message-type]]))

(formal/check-source-context binding)
(formal/program-contract {:name "add" :context binding :ensures postcondition})
(formal/source-protocol (assoc specification :bindings :closed-records))
```

The context contains source, ordered typed parameter roles, the canonical core
identity, the intrinsic policy, used record bindings and its own identity. It
contains no functions, PIDs, Env IDs or code leases. It survives a term round
trip. The same context can be stored inside a function contract or built for
each handler in a source protocol. Context contracts derive their parameters
from that declaration; a second parameter declaration is refused.

## Why this boundary exists

The retained probe changed only `formal.core.intrinsics/assoc` in an owned child
Env. Source preparation still returned ready and the formal state update stayed
the same, but the actual ordinary handler returned a replacement state. The
observer reported disagreement. Destroying that child restored the ordinary
behavior. No SDK/core Var or operator Source was modified.

The new context is an explicit linking declaration. It defines the program
compiled under that binding policy. Equivalence to an ordinary ambient program
requires that program's fetched bindings to have the declared meanings.
It is not an unconditional claim that overriding a language function has no
effect on an existing program.

## What linking does

The real compiler first supplies admitted function ANF. The linker resolves only
the declared `get/assoc` calls in `formal.core.intrinsics`:

| Declared call | Fixed target |
| --- | --- |
| `get` with two or three arguments | `BeamLisp.Ns.Rt.get` at that arity. |
| Three-argument `assoc` | `BeamLisp.Ns.Rt.assoc/3`. |
| Variadic `assoc` | `BeamLisp.Ns.Rt.assoc_variadic/4`, with remaining arguments packed into an ordered proper list. |

Every argument remains eager and ordered. An earlier failure cannot be erased
by a later update or field projection. The remaining function ANF must contain
no fetched globals, unresolved binding references or language `invoke` calls.
Lexical self-scaffold applications and reviewed host calls remain.

The checker reinterprets the linked ANF and requires exact equality of its
canonical typed core with the original declared-intrinsic interpretation. A
stored context is reconstructed afresh; changing a target, parameter role,
source, policy, core identity or cached success field cannot replace that work.
The result is `:checked-context`, with `:model-connection
:identical-canonical-cores`. This is checked reconstruction under the reviewed
elaborator, not a mechanically verified linking theorem.

Source and link work is bounded: source 64 KiB, walk 16,384 values, depth 128,
stored context 2 MiB, plus the existing typed-core limits. Refusal at a resource
ceiling is not a language exception.

## One interface, explicit profiles

`source-protocol` retains its ordinary declared-binding mode and adds the opt-in
`:bindings :closed-records` policy. The closed definition stores a context per
handler. Fresh preparation checks the source, parameter roles, context and
derived whole-handler state model together. The common `check/compare/describe`
interface still has seven subject kinds; binding evidence travels in its
connection ledger.

| Boundary | Explicit-context profile |
| --- | --- |
| Context declaration | `:bl/record-intrinsic-context-v1` |
| Source-derived protocol | `:bl/context-record-handlers-v2` |
| Bounded native question | `:bl/context-record-trace-v2` |
| Actual BEAM observation | `:bl/context-beam-observation-v2` |

The context's source and identity bind the emitted linked BEAM manifest.
Independent receipt checking reconstructs the context and reproduces those
exact bytes. A legacy observation cannot be relabelled as contextual evidence.
Z3 and OxiZ receive the same model and scope; neither engine chooses the binding
meaning. Function contracts retain their typed outcome profile and include the
context inside their exact source/definition identity.

## Actual observations and remaining trust

The context checks exercise ordinary and linked execution under the replaced
record Var. Only the ordinary program calls that replacement. The explicitly
linked handler returns the modeled state. Both artifacts and their actors are
retired. Hidden failures, empty-state errors, signed modulus, zero-step invariant
failure and unsafe witnesses from both native engines have recorded examples.

The first combined context run passed 5,494 assertions across fourteen files.
Fresh-VM transfer then exposed a default-ETF identity bug. The canonical identity
repair passed 7,099 assertions across 22 focused files, including 139 context
and 50 identity assertions. These counts overlap earlier checkpoints.
The initial integration log retains an outdated two-profile capability
expectation; the corrected expectation and final green run are separate files.

`DATA-IDENTITY.md` specifies the new explicit identity format. All nine new
runtime records survive fresh-VM validation, including the ordinary-program
disagreement. The two function-contract certificates and source-protocol proof
also recheck. Older raw-ETF objects remain preserved as historical evidence;
the current checker requires the new identity profile.

The guarantee is **no fetched Vars in this function's ANF**. This is not a
closed transitive runtime graph. SDK intrinsic implementations, source/macro
compilation, runtime code, observer reporting and compiler correctness retain
their stated assumptions. Compilation is executable compiler work, not an
execution sandbox. The actor still conveys the caller's Env; the fixed record
calls no longer consult the overridden record Var in that handler. Other
unobserved effects remain outside the finite observation relation.

The separate Lean model still has 46 theorems. No theorem count or axiom claim
changes here, and its universal handler simulation premises remain unproved.
Compiler proof authority remains false. Production runtime defaults and the
operator Source are unchanged; this milestone uses the same pinned SDK.

Unexpected observer exceptions now report an explicit execution stage. A
failure before actor entry reports `execution-started false`; an exception
during the actor call reports `:unknown`; a returned actor call establishes
entry. This avoids claiming that no execution occurred merely because the
adapter did not return normally. It does not authorize retrying unknown effects.

Next extend these declarations toward actual selected Source units, explicit
compile-time and transitive dependencies, effect/summary contracts and checked
compiler preservation. Ordinary quoted source forms and general runtime
function-contract execution still need their own qualified interface. This
context is a foundation for that work, not its completion.

Implementation: `src/formal/context.bl`, the source/contract/protocol boundaries
and the contextual runtime artifact path. Evidence: `evidence/contexts/`.
`context-check.bl` records the examples. To validate a trusted recorded archive
in a fresh capped VM, use `runtime-recheck.bl -- ARCHIVE_DIRECTORY` through the
project runner and set `ENCHANT_FORMAL_EVIDENCE_ROOT` to the desired output
directory. The archive is bounded and hash-pinned; arbitrary public ETF decoding
is not exposed by the receipt API.
