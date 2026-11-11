# Passing arbitrary runtime terms into formal test executions

The reviewed symbolic fragment has first-order data inputs and no escaping
closures or effects. Its counterexample executor retires exact code after a
call. General sampling also needs to accept references, processes and function
values as actual arguments, without printing them or embedding them in compiler
literals.

Compiling a function once and lending an invocation operation would remove
per-input compilation. An owner-bound operation can expire at callback return
and clear its private native-function cell before releasing the lease. That
alone does not establish safe code retirement for arbitrary user code: the
function may return another closure, place one in a container, or store one in
an effect before returning a Boolean. Such values may still refer to the
compiled module after the test ends.

A general sampler needs the existing Source/Env code custody boundary. Its
policy must distinguish reviewed non-escaping fragments from arbitrary callback
code whose closures retain an Env-owned publication. A closed invocation handle
and ownership of every returned or stored function are separate requirements.
Implicitly purging callback code after a successful sample would violate this
boundary.

The retained `evidence/veritas-terms/callable-design-draft.patch` explores the
invocation-cell structure. It is unqualified design evidence and is not part of
the SDK. The current sampler retains its older quoted-data evaluation boundary;
the typed quantifier path uses the reviewed ANF executor.

Qualification of a replacement must cover actual opaque BEAM arguments, nested
returned closures, closures stored through effects, use after the callback,
foreign callers, callback errors, borrower death, Env disposal and exact module
retirement. No current result is a global code-memory or termination theorem.
