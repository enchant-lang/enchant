# From ordinary records to source-backed state promises

The formal core now has a second profile, `:bl/core-record-outcomes-v2`.
It admits closed, nested records of integer, Boolean and record fields. Records
lower to ordinary maps of scalar formal terms, with one outcome for the entire
expression. Neither solver needs a native record datatype to handle this path.
The original scalar profile, core identities and default input symbols retain
their version-one encoding.

This is a research interface on the pinned SDK. It does not change the default
language runtime, production compiler or compiler proof authority. The separate
mathematical model and implementation checks do not prove the source bridge.

## The behavior a record must preserve

Construction evaluates field values in the written order. Its type schema has
canonical sorted field names, but sorting a schema must never reorder execution.
The first failure is the outcome of the whole record. Selecting another field
cannot hide that failure:

```clojure
(get {"answer" 42 "unused" (quot 1 0)} "answer")
;; raises; it does not return 42
```

Updates evaluate the base record first, then every update value from left to
right. They replace fields simultaneously after evaluating those arguments;
duplicate updates keep the last value but preserve earlier failures. Reads with
a default evaluate that default eagerly, including when the field is present.
An absent literal field with a default evaluates the whole base and then the
default. A read without a default needs a statically declared field: missing
`nil` results need an explicit nullable extension.

Conditionals evaluate only the selected branch. Let bindings preserve the
whole initial outcome and share the successful value. Record equality compares
the exact typed shape and recursive values; it retains evaluation failures on
both sides. These rules were chosen against actual pinned compiler/runtime
observations, not solver defaults.

`formal.core/record-sort` constructs a schema from a field map. Record types
have at most sixteen fields per record, depth eight and 128 type nodes. The
existing 4,096-node/128-depth syntax limits remain. Inputs must have the exact
shape, with no additional or missing fields. Literal record keys are strings;
empty strings, Unicode and NUL are valid. Hexadecimal, length-prefixed input
paths avoid passing NUL or ambiguous field paths to native symbol names.

## One real function, one closed contract

`formal/source-function` compiles the source through the real compiler ANF and
recognizes its function scaffold. It accepts one unguarded clause with distinct
variable parameters. The ordered declarations bind stable input roles; lexical
source parameter names remain aliases. Canonical core identities survive fresh
compiler names and alpha renaming.

```clojure
(formal/program-contract
 {:name "deposit"
  :parameters [["state" (core/record-sort {"balance" t/Int "flag" t/Bool})]
               ["message" (core/record-sort {"amount" t/Int})]]
  :function-source
    "(fn [s msg] (assoc s \"balance\" (+ (get s \"balance\") (get msg \"amount\"))))"
  :requires
    (fn [in] (t/all [(t/ge (get-in in ["state" "balance"]) (t/int 0))
                      (t/ge (get-in in ["message" "amount"]) (t/int 0))]))
  :ensures
    (fn [in out] (t/all [(t/ge (get out "balance") (t/int 0))
                         (t/eq (get out "flag") (get-in in ["state" "flag"]))]))})
```

Definitions contain data, not executable contract callbacks. Preparation
re-elaborates stored expression/function source and checks the exact core
identity before reconstructing a question. Rehashing a mismatched source or
core cannot establish their connection. Contract question scope now binds both
the full contract identity and its core identity.

Native contract counterexamples must satisfy the entire term context and
re-execute the concrete core to reproduce the contract violation. Scalar leaves
come from concrete assignments first, then backend observations, then explicit
labelled false/zero completions. Completion is an input proposal: it establishes
nothing until both replays pass. `replay-contract-counterexample` reconstructs
the exact definition and refuses a different subject scope/profile. Translation
counterexamples use the same shaped input decoder and execute both programs.

Record translations preserve return/raise, the successful whole value and the
first named error. Mixed scalar/record-profile comparisons use common version-two
input paths. The existing untrusted optimizer can propose changes inside a
record, but a freshly checked whole-outcome translation still gates the output.
The version-one loop profile explicitly refuses record grammar until that
profile's loop semantics is extended and qualified.

## State transitions derived from handler source

`formal/source-protocol` is a seventh common `check`/`compare`/`describe`
subject. It uses the existing protocol induction and trace semantics, adding a
source connection that is reconstructed whenever evidence is accepted.

```clojure
(formal/source-protocol
 {:name "counter" :state {"count" t/Int}
  :init (fn [s] (t/eq (get s "count") (t/int 0)))
  :invariant (fn [s] (t/ge (get s "count") (t/int 0)))
  :handlers
   [{:name "add" :inputs {"amount" t/Int}
     :assumptions (fn [s msg] [(t/ge (get msg "amount") (t/int 0))])
     :source
       "(fn [s msg] (assoc s \"count\" (+ (get s \"count\") (get msg \"amount\"))))"}]})
```

State and message schemas here are flat scalar records and retain the existing
protocol field-name rules: nonempty strings without NUL. The more permissive
record keys above are available in core programs and function contracts.
Each handler must return
the exact state shape. Users author initial-state predicates, invariants and
input assumptions; `:next`, `:guard`, arbitrary effects and mailbox policies are
refused. The handler's conditional behavior belongs in its actual source.

The closed subject contains the exact underlying protocol and an ordered list
of source/core identities. Preparation validates that model, re-extracts every
function, lowers its whole outcome, substitutes the model's exact state/message
symbols and compares every stored guard and update. A tampered cached model
cannot replace this connection, even if its inner and outer hashes are refreshed.

Whole-handler definedness is an explicit model admission outcome. It is never
a false enabling guard that hides an error; it also remains visible for empty
state schemas. The underlying model records such failure in the guard phase.
Source execution labels the phase `:handler` and retains `:model-phase :guard`.
Successful updates retain the same global outcome on every field. Errors keep
the previous state, and only stuttering is permitted afterwards.

A source protocol proof wraps the existing complete protocol proof and binds
it to the full source subject. Rechecking reconstructs the source connection
before checking the model obligations. `source-protocol-step` and
`replay-source-protocol-trace` also execute each extracted handler in the concrete
core and compare its returned state or exact named failure with the term model.
An induction countermodel is still `:obligation-refuted`; it need not be reachable
from the stated initial state.

## What the connection still needs

`Core.lean` adds Unit and finite products to the typed mathematical evaluator.
Twelve additional laws cover recursive value equality, ordered construction,
hidden-field failures, eager defaults and updates preserving failures/other
fields. Structural recursion still checks the evaluator's termination. The
named-field layout and construction-order translation to those products is not
proved. Neither is correspondence with BL's core interpreter, symbolic lowerer,
ANF extraction, certificate checker or runtime.

This handler path executes no live actor. Mailbox order, selective receive,
sending, crashes, persistence, scheduling, fairness and progress remain outside
its claims. Source-bound bounded trace questions now use the same
`formal/protocol-trace` constructor and require both state-model and handler-core
counterexample replay; [BOUNDED-TRACES.md](BOUNDED-TRACES.md) records their distinct
profile, source identities and evidence. Explicit live actor observation and
refinement remain next. Recursive summaries and broader
source domains are separate extensions with their own profiles and evidence.

Evidence is retained under `evidence/record-handlers/`. Probe, initial failing
checks, repairs, final focused checks and the product-model audit have separate
files; repeated runs are not additive coverage.
