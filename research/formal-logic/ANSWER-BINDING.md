# Keep the answer attached to its question

Checkpoint 38 implementation is under qualification. The selected dossier SDK
remains checkpoint 37 until the new artifact passes its independent checks.

Every exported `formal.logic` answer now contains the complete question it
actually answered. Retained assumptions, scope, profiles and context generation
are included. A receiver does not reconstruct this binding from a verdict,
displayed values, cache key or its current request.

`veritas.mock/accept-answer` requires that exact question. A SAT answer for
`x = 0` cannot witness a request requiring `x > 10`, even when zero satisfies
every response law. An UNSAT answer to a different question cannot turn a
realizable response request into an absence claim. The owned `execute` path
retains its actual context-extended question before applying this same boundary.

The published response also gets a separate independent check. Its concrete
fields are bound back to their typed model coordinates, merged with remaining
native assignments, and replayed against every assertion, concrete pin and
counterexample goal. This catches a decoded field that disagrees with the
model's variables: a response of zero still fails the extra `x > 10` condition
when the native assignment says eleven. That mismatch remains a candidate.

The resulting `:projection-replay` is evidence about the actual response point.
The ledger retains it. An extremum record keeps it on the feasible-response
side, alongside the SAT question; its final unchecked UNSAT question carries
no witness or projection replay of that feasible point.

Large records use the language's existing content-addressed file tier. Only
small descriptors enter covering indexes; the complete question, evidence and
witness retain the ordinary datom value codec outside those keys. Public ledger
reads reconstruct the same values and continue reading older inline records.
Missing or corrupt payloads are errors. Payloads have an explicit 16 MiB byte
capacity; storing them still grants no mathematical or compiler authority.

The preceding SDK passes one assertion and fails nine in the retained baseline.
The candidate passes all twenty-five focused files, including all ten boundary
assertions. Broader qualification remains in progress. None of these changes
checks native absence certificates or establishes compiler preservation.

This binding is also a prerequisite for checked query preparation. A future
normalization plan must retain both the original and executed question, prove
their connection, and explicitly recheck any transported response. Equivalent
meaning does not justify silently treating two different query objects as one
execution.
