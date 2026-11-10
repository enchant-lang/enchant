# A contract can select a real Source function

`formal/selected-source-context` connects the research contract interface to
the pinned SDK's actual selected Source catalog. A context names a public
phase-zero function in one `[namespace revision]`, with exact Source bytes for
its selected providers. Private helpers and captured immutable values retain
their lexical identities. No mutable namespace lookup supplies their meanings.

```clojure
(def program
 (formal/selected-source-context
  {:sources [{:namespace 'accounts :revision 'v1 :file "accounts.bl"
              :source "(ns accounts) (def fee 2) (defn- debit [n amount] (erlang/- n amount)) (defn withdraw [n amount] (debit n (erlang/+ amount fee)))"}]
   :entry ['accounts 'v1] :target 'withdraw
   :parameters [["balance" t/Int] ["amount" t/Int]]}))

(def promise
 (formal/program-contract
  {:name "withdraw" :context program
   :requires (fn [in] (t/ge (get in "balance") (t/add (get in "amount") (t/int 2))))
   :ensures (fn [in out] (t/ge out (t/int 0)))}))

(formal/check-source-context program)
(formal/check {:backend :z3} promise)
(formal/check {:backend :oxiz} promise)
```

The existing `:context` contract field owns its ordered typed parameters. All
seven subject kinds and the shared `check/compare/describe` envelopes remain.
The context is ordinary portable BL data, not an execution grant. Its profile
is `:bl/selected-source-context-v1`; its identity profile is
`:bl/canonical-formal-data-v1`.

## What the contract covers

The program in this profile is **initialize the selected unit, then call the
selected function once**. Every scalar initializer in the canonical schedule
is retained, even if the function never reads it. An initializer that divides
by zero prevents the call from returning. This differs from a future contract
for repeated calls on an already initialized instance.

The input role names belong to the contract. Source parameter names are lexical
aliases. Generated specialization names avoid those roles. Arguments and
initializers are evaluated eagerly in their actual order; their first failure
is preserved. Helpers capture their definition environment, so a caller's
same-spelled local variable cannot replace a captured constant.

This is a first-order Int/Bool/closed-record fragment. It supports fixed-arity,
unguarded, single-clause functions; lexical helpers; captured scalar/record
values; nested records; and the exact reviewed native leaves in
`formal.intrinsics` and the record elaborator. A checked predicate still uses
the same independently checked Boolean/piecewise-linear Int proof format.

This profile refuses entry expressions, captured entry results, recursive
control, computed or higher-order calls, escaping functions, variadic or
multiple clauses, unlinked references, unsupported native calls and effects
on the selected call path. A private export cannot be selected as the public
target. An uncalled helper's latent body is not a proved function contract.

## Source, expansion and specialization have separate owners

1. `expand/program` reads the exact supplied units. The real SDK owns world
   selection, revision imports, hygiene, expansion and canonical lexical links.
   No handwritten Source references or synthetic authority tables enter this
   API. Paths are source coordinates; this adapter does not read those files.
2. `system.phase/check` rechecks the resulting program's binding/phase facts.
   Its `:proved` status concerns contextual binding resolution. Its native
   admission remains false; it does not establish general effect safety.
3. The new bounded specializer follows lexical closures in that actual ANF.
   Calls become fresh lexical argument bindings and specialized bodies.
   Initializers remain ordered. A separate unit/ANF relation checker now compares
   that proposed reduction against the original SDK unit. It derives the input
   alias map consumed by the following independent ANF/Core check. Only then
   can the prepared formal model back a contract. The producers and checkers
   remain reviewed code with unproved implementation soundness.
4. A context stores exact sources, entry, target, parameters, canonical core
   identity, actual selected target reference and canonical identities of the
   unit, selection, reference table and expansion records. Fresh preparation
   reconstructs all of it. Rehashing changed source or a stale cache cannot
   skip reconstruction.
5. A contract reconstructs that context and core before producing or checking
   a term proposition. Backend results cannot replace that source connection.

Source-defined hygienic macros can participate through the SDK's bounded
constructor session. A retained example imports a macro from one revision; its
syntax quote selects a private helper in the macro's definition environment.
Preparation does execute expansion-phase semantics. It runs no selected runtime
initializer or target function. The macro, specializer, BL checker and compiler
implementations are reviewed code, not mechanically proved implementations.

The specialized ANF is a derived program. The next implemented slice now emits
and observes the **original** selected unit through its normal SDK Source owner,
then checks finite outcome conformance against this core. See
[SELECTED-RUNTIME.md](SELECTED-RUNTIME.md). This does not prove universal
preservation from the original unit to the specialized core. The earlier actor
observer remains a separate source-handler experiment with its own profile.

## Closure and limits

The connection ledger reports `:closure :selected-source-and-lexical-callees`,
`:model-connection :freshly-reconstructed-core` and
`:ambient-equivalence :no-ambient-vars-in-selected-unit`. That last field means
this selected program has no ambient Var dependency; it does not claim equality
to an ordinary program under arbitrary overrides. Native leaf implementations,
their transitive runtime dependencies and compiler correctness still have their
own trust boundary. `:transitive-runtime-closure` remains `:not-established` and
compiler proof authority remains false.

Limits are eight source units, 64 KiB each, 128 KiB total, 128 initializers,
16 typed parameters, 256 expanded calls, 65,536 specialization visits and depth
128. Stored contexts are limited to 2 MiB; canonical data and core limits also
apply. A capacity refusal is incomplete analysis, not a language exception.

The focused implementation check passed 118 assertions. It covers lexical
capture, repeated and nested helper calls, arguments that fail, an unused
failing initializer, generated-name collisions, nested record leaves, explicit
revision imports, hygienic macro expansion, owned ambient overrides, both
backends and altered context data. The actual logs, failed attempts and
qualification are retained in `evidence/source-selection/`.

`selected-check.bl` records contexts, checked contracts and native witnesses.
`selected-recheck.bl -- ARCHIVE_DIRECTORY` reconstructs them in a fresh capped
VM. Its archive decoder is for bounded, hash-pinned trusted project artifacts;
it is not a public ETF endpoint. The pinned SDK and production defaults remain
unchanged. This milestone adds no Lean theorem or universal refinement proof.

The subsequent [specialization checkpoint](SPECIALIZATION.md) adds an independent
reduction check and a distinct typed-model proof scope. The model proves lexical
renaming preserves complete outcomes, and one-/two-argument eager-call laws
preserve the caller's argument order and the definition's captured environment.
These mathematical laws do not establish the named unit encoding, arbitrary-
arity closure machine or BL checker soundness. `formal/prepare-source-context`
returns the full reconstructed Core and both ordinary-data translation objects;
`formal/check-specialization` and `formal/check-elaboration` check those supplied
objects without another compiler or specializer invocation.
