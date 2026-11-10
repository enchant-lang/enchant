# A sound executable checker, applied to actual BL data

The normalized Boolean/linear-integer checker now has a Lean soundness theorem.
An accepted proof rules out **every** integer/Boolean model of its normalized
problem. Eleven certificates exported by the real BL implementation have been
checked by that exact executable kernel. This is stronger than testing a set of
solver answers: the theorem covers every input accepted by the Lean checker.

This narrows one part of the trust boundary. The original term normalizer, BL
checker implementation, data bridge, Source connections and compiler are still
reviewed implementations. The theorem does not prove those connections sound.
The existing BL proof API and production compiler authority remain unchanged.

## The two BL operations

```clojure
(def made (formal/certify question))
(def exported (formal/normalized-refutation question (:certificate made)))
(def packet (:packet exported))
(formal/check-normalized-refutation-data question (:certificate made) packet)
```

`normalized-refutation` returns `:ready` only after the existing certificate
checker accepts the exact question/certificate pair. It reruns preparation under
the certificate's original rule version. The packet binds the full original
question identity, normalized statement identity, rule version, variable layout,
normalized formulas and proof tree. Every value is ordinary portable BL data.

`check-normalized-refutation-data` freshly reconstructs the whole packet from
that question/certificate and compares every field. Its successful status is
`:checked-data-connection`. A self-consistent hash cannot substitute for this
comparison. Neither BL operation starts Lean or authenticates a Lean receipt.
Both say `:kernel-execution :not-run` and grant no compiler proof authority.

## What the normalized checker accepts

Its vocabulary is deliberately closed:

| Data | Meaning |
| --- | --- |
| `[:boolean]` atom | One independent Boolean input. |
| `[:linear coefficients bound]` atom | An integer dot product is at most the bound. |
| `[:constant b]`, `[:atom i]`, `[:neg f]` | Constants, atom references and negation. |
| `[:both f g]`, `[:either f g]` | Binary conjunction and disjunction. |
| `[:boolean]` proof | A formula is already false under the partial assignment. |
| `[:linear [[i weight] ...]]` proof | Positive weighted assigned rows combine to an impossible constant inequality. |
| `[:split i yes no]` proof | An unassigned atom is checked in both branches. |

The checker obtains linear rows from the problem's atom table; the proof cannot
supply its own premises. A false integer atom uses the exact complement
`-coefficients <= -bound - 1`. The BL export requires primitive normalized rows
with coefficient gcd one, including rows whose bounds were tightened during BL
preparation. Its n-ary Boolean forms become balanced binary trees.

`Refutation.lean` proves the executable check sound through 17 audited lemmas
and theorems. `checked_refutation_unsatisfiable` quantifies over arbitrary integer
and Boolean environments. Integer vectors use mathematical unbounded integers;
this is not an argument about machine integer overflow or runtime resource use.
The theorem establishes normalized unsatisfiability, including the ordinary
case of inconsistent assumptions. It does not establish assumption feasibility.

The kernel consumes the normalized outputs of the three current BL certificate
rule versions. Piecewise choices and supported ground division/modulus are
resolved by BL preparation before this checker sees them. The kernel theorem
does not thereby prove those normalization rules correct, nor does this extend
certification to arbitrary solver theories, nonlinear arithmetic or symbolic
division. The earlier 63 Core-model theorems retain their own separate scope.

## Apply the theorem to a packet

```sh
research/formal-logic/check-refutation \
  research/formal-logic/evidence/refutation-kernel/examples/weighted.json \
  --output /tmp/weighted-refutation
```

The capped runner validates a narrow JSON schema and independently reconstructs
BL's canonical tagged ETF identity, including large signed integers. It emits
only fixed Lean constructors, validated numerals and Boolean constants. Variable
names remain data and never enter generated source. A second parser decodes
that source and checks both the recovered input and the exact proof template.
Unknown tokens, altered imports, trailing declarations, `sorry` and a substituted
`native_decide` template fail that comparison.

The pinned Lean binary receives only the pinned `Refutation.olean` in a private
library directory. A generated `packetAccepted` theorem is checked with
`by decide`; `packetUnsatisfiable` applies the general soundness theorem to that
same problem and proof. The output includes the checked source, compiled object,
printed axiom audit and a local execution receipt. Exact executable, kernel
source and compiled-kernel hashes are checked before execution. This runner is a
reviewed data connection, not a mechanized proof of the Python encoder/decoder
or a cryptographic runtime attestation.

Actual accepted packets print `packetAccepted: [propext]` and
`packetUnsatisfiable: [propext, Quot.sound]`. The runner requires those exact
audits. There is no admitted theorem or native-evaluation axiom in accepted
proofs. A failure is reported as `not-accepted`; it does not establish that the
original claim is false.

The initial wrapper expected an empty dependency list for computed acceptance.
Lean's actual output included `propext`, so that wrapper rejected an otherwise
checked proof. Its source, log and rejection receipt are retained under
`weighted-initial-audit/`. Earlier model-development failures and BL fixture
failures are retained separately and excluded from successful qualification.

## Evidence and the next bridge

The real packet examples cover weighted inequalities, integer parity, negative
floor tightening, Boolean branching, piecewise choice, signed ground division
and modulus, vacuous assumptions, code-like variable names and a 2,058-bit bound.
Five validly rehashed, well-shaped packets with false refutations reach Lean and
are rejected there. Schema, identity and generated-source tampering are checked
separately. `refutation_kernel_test.py` runs these checks sequentially under one
resource cap.

The next valuable theorem connects **original typed term semantics** to the
normalized problem. It should establish that a satisfying assignment for the
assertions and negated claim induces a satisfying assignment for the exported
atoms/formulas. Combined with this kernel theorem, that would justify the
conditional original term claim. The connection needs explicit variable
layouts, gcd floor tightening, integer complements, choice expansion, and the
v3 ground arithmetic rules. Source/Core interpretation and compiler preservation
remain later, separately named connections.
