# Handlers across managed work

The next slice makes a handler table part of the language's explicit callable
context. A managed submission captures the active table. Accepted work retains
the table's executable modules independently of the parent scope. Nested
tables replace the selected effect's methods and restore their predecessor in
`finally`. Reused workers restore their own prior context after invocation.

The public language interface will provide named synchronous effects and
method tables. Oracle uses one table with `:script` and `:query` methods, so an
installed table missing the requested method refuses that method. A completely
unhandled effect may use its supplied default operation. These are scoped
handlers and ordinary function calls; continuation capture is a separate
language feature.

The runtime owns a fixed registered callable-scope field. It does not copy
arbitrary process-dictionary keys. Callback modules come from the declared
callable slots, with existing managed graph, explicit outside-dependency and
Source admission rules retained. A context value alone grants no code custody.

Normal managed spawning, futures, execution registration and generated actor
starts must retain these callbacks before publishing work. Raw Erlang spawning
continues with its explicit native context. Logical query data can cross that
boundary, while a native session remains borrower-owned.

The starting cases are in `test/bl/system/formal_effect_test.bl`. Implementation
and qualification are pending. Automatic handler inheritance remains separate
from any claim of a verified runtime or compiler.
