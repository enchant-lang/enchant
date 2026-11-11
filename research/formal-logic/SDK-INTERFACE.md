# Typed questions at the SDK oracle boundary

The public SDK interface has passed its focused qualification in this checkout. The portable
term, question, proof and state-model implementations now live under
`priv/lib/formal`. Research import paths point to those canonical sources.
The native worker remains an explicitly configured artifact.

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
The derived search procedures that directly open a native transport context
also need migration to the common logical context. These are explicit next
steps; the focused SDK tests do not establish their handler behavior.
