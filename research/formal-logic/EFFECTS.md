# Handlers across managed work

The handler table is part of the language's explicit callable
context. A managed submission captures the active table. Accepted work retains
the table's executable modules independently of the parent scope. Nested
tables replace the selected effect's methods and restore their predecessor in
`finally`. Reused workers restore their own prior context after invocation.

The public language interface provides named synchronous effects and
method tables. Oracle uses one table with `:script` and `:query` methods, so an
installed table missing the requested method refuses that method. A completely
unhandled effect may use its supplied default operation. These are scoped
handlers and ordinary function calls; continuation capture is a separate
language feature.

```clojure
(effect/with-handler :app/read
  (fn [request default-operation] (+ request (default-operation)))
  (fn []
    ;; Submission captures the handler; running the callback restores it.
    (future (effect/perform :app/read 2 (fn [] 40)))))
```

`perform` passes the request and the zero-argument default function to the
handler. `call` invokes a named method with an eager argument vector.
`handlers` reads the active table; `handled?` asks about an effect or a method.
The entire table for one full keyword identity is replaced. Other effects
remain active. This makes a query-only Oracle table refuse a legacy script
request rather than silently opening a native solver. Handler arity errors
remain ordinary runtime errors; installing a table is not an effect type proof.

`oracle/with-oracle` and `with-query-handler` use the `:oracle` table.
Complete term questions retain their typed answer boundary. Each child can
open a fresh logical session under its captured handler; a captured handler
does not transfer a borrower's native session or port to another process.
The legacy `ask-all` path uses managed tasks with one fresh correlation ticket
and submission indices, preserving duplicate labels and unrelated mailbox
messages. It retains its existing legacy verdict and timeout contract.

The runtime owns a fixed registered callable-scope field. It does not copy
arbitrary process-dictionary keys. Callback modules come from the declared
callable slots, with existing managed graph, explicit outside-dependency and
Source admission rules retained. A context value alone grants no code custody.

Normal managed spawning, futures, execution registration and generated actor
starts must retain these callbacks before publishing work. Raw Erlang spawning
continues with its explicit native context. Logical query data can cross that
boundary, while a native session remains borrower-owned.

Preparing a Source world starts a distinct framework context. It does not bake
the builder's handler into a compiled world. An explicit world entry selects
that world's context; a Source entry can install its own handlers and spawn
managed work with that snapshot. Fixed SDK framework adoption also clears
application handler tables when it replaces application lifetime with class
custody. Ordinary function calls preserve the active dynamic table.

`effect/with-handler`, `with-methods`, `perform` and `call` are the public
language interface. The optional dependency vector names native modules for
captured callbacks outside a managed graph, following the existing execution
registration contract. Declaring a module for retention grants no Source
execution authority. `Env/convey` transports context; a delayed native callback
still needs actual registration/custody for all its executable dependencies.

The runtime admits at most 32 effect tables, 64 methods per table and 4,096
explicit outside modules per table. The table snapshot has an 8 MiB ceiling;
the existing pooled execution-context limits also apply.

The starting twenty assertions in `test/bl/system/formal_effect_test.bl`
passed six and failed fourteen on the preceding SDK. The selected SDK passes
450 assertions across six focused files, including 94 handler and Source cases;
284 native lifetime/capacity assertions; and 7,086 formal regression assertions.
All 187 preceding paired native questions retain their identities and verdicts.
The compiler's P/B/C production and complete installed floor are checked;
B and C inventories agree byte for byte.

The [executable examples](src/formal/effect-examples.bl) run four managed
boundaries for each backend choice with deliberately unavailable native paths.
Every handled answer has a replayed value of seven and a valid typed model.
Its certificate remains unchecked. The generic named effect returns forty-two
in submitted work and restores the caller's default of forty.
The [qualification receipt](evidence/effects/qualification.json) binds the code,
SDK and retained checks. These are scoped implementation checks, separate from
runtime preservation or compiler soundness proofs.

Further formalization needs a model of effect requests, handler selection,
submission, completion and cancellation, with explicit outcome contracts for
each handler. Source extraction must preserve that relation rather than replace
an effectful call with a convenient constant. Effect typing, continuation
capture, fairness and totality require their own rules and evidence. Remaining
legacy Oracle migration and native worker packaging are also active work.
