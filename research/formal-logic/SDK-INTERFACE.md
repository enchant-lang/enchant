# Typed questions at the SDK oracle boundary

The public SDK interface passed 86 focused assertions and a 16-file regression
with 2,549 assertions in this checkout. The 187 paired theory questions retain
their preceding canonical identities and native verdicts. The portable
term, question, proof and state-model implementations now live under
`priv/lib/formal`. Research imports resolve these namespaces from the selected SDK. Readable source
links live outside the research import root, under `sdk-src`.
The SDK image supplies its default native worker and Z3 library. Explicit
option/environment pins retain their separate provenance.

The [temporal interface](TEMPORAL.md) adds semantic integer spans and complete
overlap/chronology questions. `datom.time` consumes these questions through the
same oracle method; symbolic endpoint constraints travel with the values.

The [source-property interface](SOURCE-PROPERTIES.md) turns compiler ANF and
generator domains into the same portable questions. Source counterexamples
require term replay and execution of that exact ANF. The scalar source, numeric
and data adapters also live in the SDK.

The [Veritas term interface](VERITAS-TERMS.md) extends this path to quantifiers
and compiler-backed clause coverage. Options maps choose the backend and the
terms/enumeration/sampling engine separately. Enum payloads, positional products,
collection-length abstractions and text prefixes compose as typed inputs.
`veritas/prepare` exposes the complete question before solving; the ledger can
retain it with its identity, caller evidence and explicit witness presence.
Native claims, runtime replay and recorded evidence keep separate authority.

[Complete reply binding](ANSWER-BINDING.md) also covers native answers. Every
exported answer retains its exact effective question. Response consumers refuse
foreign-question data and independently check the actual point being published;
complete ledger evidence uses content-addressed payloads.

[Checked preparation](PREPARATION.md) introduces explicit original/execution
questions with independently checked component equalities. `formal.affine`
proposes a useful Bool/Int representation; `formal.preparation` checks, executes
or purely accepts its returned answer. Original replay and native model API
access retain different records. [The size consumer](COMPILER-LINEARITY.md)
uses the same interface alongside fresh positive certificates and constructed
counterexamples; its unknown result has no false truth projection.

## Ask through a standard consumer

```beam-lisp
(ns account-check
 (:require [system.core :as system] [formal.protocol :as protocol] [formal.term :as t]))

(def bank
 (protocol/define
  {:name "bank" :state {"balance" t/Int}
   :init (fn [s] (t/eq (get s "balance") (t/int 0)))
   :invariant (fn [s] (t/ge (get s "balance") (t/int 0)))
   :transitions
    [{:name "withdraw" :inputs {"amount" t/Int}
      :guard (fn [s in] (t/all [(t/ge (get in "amount") (t/int 0))
                                (t/le (get in "amount") (get s "balance"))]))
      :next (fn [s in] {"balance" (t/sub (get s "balance") (get in "amount"))})}]}))

;; Portable certificate production and fresh checking.
(system/prove-box {:initial-state {"balance" 0}} bank)

;; Each engine receives the same terms and conditions.
(system/preserves? {:backend :z3} bank "withdraw")
(system/preserves? {:backend :oxiz} bank "withdraw")
(system/establishes? {:backend :z3} bank)
(system/fireable? {:backend :oxiz} bank "withdraw")
```

The typed arities return the common formal evidence envelope. Its certificate,
native verdict, feasibility, source connection and authority fields describe
the result's basis. The existing script arities retain their established result
shape.

`system.formal` exposes the question constructors directly. A caller can inspect
`preservation-question`, `establishment-question` and `fireability-question`
before checking. `formal.check/query` checks any portable term question.
Backend options and the existing `ENCHANT_FORMAL_WORKER` and
`ENCHANT_Z3_LIBRARY` variables select native artifacts.

Fireability asks whether a guard can return true normally under the model's
invariant and input assumptions. Preservation also covers an admitted guard
that raises. The update's definedness stays in the preservation claim.
The supplied state model has its own source and runtime connection fields.

## Handle the complete question

```beam-lisp
(oracle/with-query-handler
 (fn [question execute]
   (println (select-keys question [:id :mode :profile :scope]))
   (oracle/query-answer question (execute)))
 (fn [] (system/preserves? {:backend :oxiz} bank "withdraw")))
```

A query method receives the complete question and a zero-argument owned
fallback. It can return a bound response directly, or delegate the same question
to native execution. `query-answer` binds the response to the exact question
and records an unchecked handler claim. The boundary replays SAT assignments
against the original assertions and counterexample goal. A handler's supplied
validation or certificate status cannot replace that check.

`oracle/with-oracle` accepts a method map with `:query` and `:script`
callbacks. The script callback keeps its `[text model?]` arguments.
`oracle/query-table` keys answers by the whole typed question.
`oracle/deny` supports both callback forms. A missing method refuses the
corresponding effect.

Custom handlers receive script questions even when the default path previously
memoized them. Those handler scopes bypass the shared script memo. This makes
table and deny scopes effective over previously asked questions too.

## Own a conversation

`formal.logic/with-session` supplies the common question context. An installed
handler uses a logical context with BL assumptions, and the default path uses
one native owner. `load!` normalizes retained assumptions, and `solve-in`
includes their generation and digest in each scoped question. `reset!`
advances the context and removes those assumptions. A closed or foreign
context refuses execution.

Delegating from a handler opens an owned native context for that fallback and
closes it afterward. A retained fallback also checks its original context's
lifetime and borrower before execution. These scopes carry the existing
native hard deadline and solver budget.

The migration includes the normal question paths for contracts, loops,
translations and protocol induction. Direct `formal.backend` operations remain
the explicit native transport layer. Source consumers and the default legacy
oracle still have further migration work.

The handler scope currently belongs to the calling process. Ordinary `spawn`
conveys the language environment, but does not yet convey this oracle handler.
The derived search procedures now use the common logical context. Automatic
process inheritance remains a separate runtime design and qualification task.

Exact artifacts, source hashes and retained failed-run evidence are in
`evidence/sdk-interface/qualification.json`.

The first document-cell qualification exposed a source-selection conflict:
research symlinks inside the import root shadowed SDK namespaces. Ordinary
tests loaded the equal source bytes, while static declaration checking refused
the conflicting provider identity. Those aliases were removed from the import
root. The `sdk-src` link is for authored source browsing, outside import search.
Removing those aliases required no change to the qualified SDK or its
declaration checks.

## Checked answer data

`formal.answer/bind` and `check` give complete typed replies a pure boundary.
The current SDK adds 134 focused answer assertions; the preceding 86 public
SDK assertions still pass. The wider twenty-two-file regression passed 7,086
assertions. `ANSWER-INTEGRITY.md` records the contract and semantic choices.

Concrete assignment encodings are checked against their sorts. Handler
observations are reconstructed from those assignments. An exact reply from an
owned native fallback retains its native-only observations and provenance; a
modified reply is replayed, with the supplied display retained separately.
Phase/status combinations must answer the requested question.

Derived procedures now use the common logical session before opening a native
worker. The subsequent native-context boundary uses owner-held assumptions,
registry, generation and revision. A changed owner context refuses a saved
fallback, and raw transport requires a managed reset before portable reuse.
Client bookkeeping is diagnostic. The added 136 owner assertions bring the
focused SDK run to 356. See `NATIVE-CONTEXTS.md`; these are API consistency
checks, not security capabilities against arbitrary Erlang introspection.

The [response relation interface](RESPONSE-CONTRACTS.md) extends the same question
boundary to `veritas.mock` and `veritas.fault`. `formal.response` owns portable
relations, `formal.response-runtime` owns source and concrete replay, and
`formal.integer-optimize` owns integer extremum search. A semantic assumption's
constraints, admission and scope travel with it, including through a retained
context. Mock and fault consumers take options maps and complete question data.
