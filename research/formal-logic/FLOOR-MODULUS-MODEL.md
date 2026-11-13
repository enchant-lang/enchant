# One arithmetic law, with two evidence paths

The legacy expression repair translates Euclidean remainder `e` into
`if e = 0 or b > 0 then e else e + b`. Its companion quotient chooses `a div b`
or one less. The native tests ask separate universal questions about range,
divisor sign and reconstruction at the existing solver deadline. A preceding
combined query timed out and is retained as undecided evidence.

`metatheory/FloorModulus.lean` now specifies those formulas in a separate
integer model. Its source contains proof attempts connecting them to Lean's
floor division and remainder for every nonzero divisor. It also specifies an
explicit partial outcome, so the successful arithmetic equations cannot erase
zero-division failure. Two negative controls claim the raw negative-divisor
remainder is sufficient and zero division succeeds.

These new model sources are **pending execution and qualification**. Run
`run-floor-modulus-model.py` after the current numeric SDK gates terminate,
using the already pinned Lean toolchain. The runner requires ten actual theorem
audits, records their axiom dependencies and checks both false claims are
rejected. It produces no SDK.

Even successful mathematical checks would not prove that the BL compiler,
legacy renderer or either solver implements this model. The translated syntax,
concrete runtime sign cases and native law queries are separate checks of that
reviewed connection. A mechanically proved implementation connection remains
future work.
