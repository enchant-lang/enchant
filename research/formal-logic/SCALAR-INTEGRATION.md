# Text and independent evidence in one term-based interface

The immutable SDK is qualified and selected, with 604 namespace preflight
checks, 783 focused assertions and 11,705 assertion executions across all four
gates passing. All 187 paired native cases retain their preceding outcomes.
Cold SDK-only word, text and certificate packet readers also pass with zero
native/oracle calls. Two fresh durable readers passed all twenty saved packets
and actual ledger rows, sixteen refusal controls and three invalid text-point
controls. All three older saved generations also passed fresh-reader and
refusal gates with their original producer identities. Read the exact
[qualification](evidence/scalar-integration/qualification.json) and
[selection](evidence/scalar-integration/promotion.json). Dossier execution and
browser activation remain a separate checkpoint.
The built artifact is recorded in [sdk-candidate.json](evidence/scalar-integration/sdk-candidate.json);
its [build linkage](evidence/scalar-integration/build-linkage.json) binds all 723
packaged sources, thirteen changed units and the unchanged compiler floor.

The runtime batch adds `formal.scalar-text`, `formal.resources.text`, the shared
`formal.scalar-text-value` predicate, `formal.finite-word-certificate` and
`formal.request-evidence`. The ordinary `formal.logic` facade exposes the new
evidence effect and comparison. Existing request/answer ownership formats remain
available; the default compiler oracle has not migrated.

## Ask either backend about the same text terms

```clojure
(ns example.text
 (:require [formal.scalar-text :as text] [formal.value :as value]
           [formal.data :as data] [formal.query :as q]
           [formal.question-graph :as graph] [formal.logic :as logic]))

(let [x (text/variable "name")
      claim (value/equal (text/at x 1) (data/some (text/literal "́")))
      subject (graph/prepare
                (q/prove claim {:assumptions [(value/equal x (text/literal "é"))]}))
      request (logic/prepare-request subject
                {:policy {:profile logic/numeric-word-text-policy}})]
 (logic/compare-evidence request))
```

Both engines receive the same original subject. The actual candidate tests
observe Z3 UNSAT and OxiZ UNKNOWN for this contract. Each result exposes
`:answer-check`, `:proof-check`, `:proof-account`, `:conclusion` and local
delegation. A native UNSAT report alone leaves the independent conclusion
unestablished. A valid supplied or native point can establish a witness or
counterexample under the named point policy. Compiler authority remains false.

`text/at-total` uses the total SMT empty-result convention. `text/at` returns
an explicit Option; `text/at!` is a deliberately strict formal accessor;
`text/at-or` chooses a fallback. `find-index` exposes a signed sentinel and
`find` returns an Option. Length, slicing and positions use codepoints. These
APIs do not reinterpret ordinary BL grapheme operations. See the
[text-domain review](SCALAR-TEXT-DOMAIN.md) before relating symbolic String
quantifiers to host text: point-domain metadata does not add native assumptions.

## Supply a certificate without opening an engine

```clojure
(ns example.proof
 (:require [oracle] [formal.logic :as logic]
           [formal.finite-word-certificate :as finite]))

;; word-request is a prepared request using logic/numeric-word-policy.
(oracle/with-oracle
 {:request-evidence
  (fn [request _fallback]
   (logic/propose-evidence request {:certificate (finite/candidate request)}))}
 #(logic/compare-evidence word-request))
```

The handler supplies ordinary data. It supplies no checking result. The
installed checker derives every valuation itself, accepts at most five combined
Boolean/word variable bits, and retains the exact original assumption nodes.
The mathematical statement is reusable across backend choices; each outer
bundle still binds its complete request. Feasibility and Source correspondence
remain unestablished. The checker and its BL/BEAM execution are trusted, without
a mechanical implementation-soundness theorem.

The caller can pass `{:proof-work-units n}` to `execute-evidence`,
`compare-evidence` or `recheck-evidence`. The first strategy conservatively
reserves 3,300,000 units before invocation, even for a smaller question. A lower
allowance produces incomplete proof checking. The reservation is a named work
convention, separate from point accounting and physical process limits.

An existing answer and a candidate certificate can coexist:

```clojure
(logic/propose-evidence request {:answer response :certificate candidate})
```

Native history, point validity and independent certificates stay distinct.
Saved evidence packets contain the original request and candidate data;
reopening uses the reader's current allowance and runs the checks afresh.
Existing native/point answers can also use the indexed durable request ledger.
The new certificate bundle does not yet have its own durable ledger format.

## What the runtime actually checks

The extended profile admits Bool, Int, Real, fixed-width words and scalar text
through the existing graph dispatcher. It reserves all literal work before
constructors or text validation, then meters demanded coordinates and operations
inside the private point scope. Syntax-only coordinate parsing creates no
normalization token. Source, point, primitive and whole-process limits remain
separate. Raising an allowance cannot widen the word grammar or text alphabet.

Qualification still requires the unchanged 187-question native audit, project
regressions, fresh SDK-only text/certificate packets, actual mixed durable
records and compatibility with older recorded producers. This implementation
does not establish complete String theory, general word proofs, native solver
soundness, compiler preservation or language-wide totality.
