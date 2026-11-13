# One arithmetic law, with two evidence paths

The legacy expression repair translates Euclidean remainder `e` into
`if e = 0 or b > 0 then e else e + b`. Its companion quotient chooses `a div b`
or one less. The native tests ask separate universal questions about range,
divisor sign and reconstruction at the existing solver deadline. A preceding
combined query timed out and is retained as undecided evidence.

The separate `metatheory/FloorModulus.lean` model is now qualified. Its ten
checked results connect those formulas to Lean floor division and remainder,
reconstruct the dividend, establish positive and negative divisor bounds and
congruence, and make zero division an explicit failed outcome. The concrete
negative-divisor example also checks in the kernel. Both false controls are
actually rejected: raw Euclidean remainder is insufficient, and division by
zero cannot become a successful pair.

`evidence/floor-modulus-model/qualification.json` records the exact pinned
Lean toolchain, source, compiled objects, check logs and axiom ledger. Eight
additional audits expose the imported standard-library dependencies.

The two bounds results use `propext` and `Quot.sound`. The floor equivalences,
reconstruction, congruence and successful-outcome results additionally inherit
`Classical.choice` from the listed Std floor identities. Zero failure and the
definedness equivalence use `propext`; the concrete example has no axiom
dependencies. The runner requires these exact per-theorem footprints. The
negative bound uses direct integer order lemmas to avoid adding choice through
arithmetic automation. Earlier unqualified proof/audit attempts are retained.

These mathematical checks do not prove that the BL compiler, legacy renderer
or either solver implements this model. The translated syntax, concrete
runtime sign cases and native law queries check that reviewed connection
separately. A mechanically proved implementation connection remains future
work. This model produces no SDK and grants no compiler proof authority.
