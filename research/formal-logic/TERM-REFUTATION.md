# Checked entailment for the original typed terms

The normalized checker has a soundness theorem. The next connection now has
executable proofs too: for each accepted packet, Lean checks a theorem about
the **original typed assertion and claim trees**, quantified over all their
integer and Boolean inputs. It proves that a counterexample to those original
trees would satisfy the normalized problem, then uses the checked refutation
to rule that out.

This is per-question translation validation. It does not assert a universal
correctness theorem for the BL normalizer. A generated connection proof may
use arithmetic reasoning about the complete original question, including
showing that its countermodel premise is impossible. It is not required to
establish pointwise equivalence of every intermediate normalization rule.

## Data interface

```clojure
(def made (formal/certify question))
(def ready (formal/term-refutation question (:certificate made)))
(def packet (:packet ready))
(formal/check-term-refutation-data question (:certificate made) packet)
```

`term-refutation` retains the exact original assertion/claim terms alongside
the existing normalized packet. Variables that cancel out of normalized rows
remain present in the original trees. All earlier normalized packet identities
and certificates remain unchanged. The versioned wrapper uses
`:bl/typed-term-refutation-v1` and names the mathematical semantics explicitly.

Fresh reconstruction compares the whole wrapper against the original query
and certificate. Its `:checked-data-connection` status establishes that data
connection, with `:term-connection :not-run` and `:kernel-execution :not-run`.
It runs no Lean process and does not authenticate an external execution receipt.

The external runner proves the contained typed trees. Its original-question
digest is an identity label carried by the normalized packet. Connecting that
label to a separately saved full query still requires the BL reconstruction
above; an independently rehashed metadata label does not establish provenance.

## Precise mathematical semantics

`metatheory/Terms.lean` defines an intrinsically typed Int/Bool term language.
Its evaluator returns `Option Int` or `Option Bool`. Integer division/modulus
by zero returns `none`, rather than selecting a total arithmetic answer.
Nonzero division/modulus use Lean's unbounded Euclidean integer operations,
including negative divisors.

Arithmetic, equality and ordered relations require their operands' values.
Boolean conjunction/disjunction use three-valued dominance: a known false
conjunct or true disjunct determines the result even if another term is
undefined. Implication is negation/disjunction. Boolean equality and xor
require both values. A conditional evaluates only the selected arm when its
condition is known. Variadic conjunction/disjunction become ordered right
folds with true/false identities in the reviewed data encoding.

This describes mathematical term values and unavailable values, not general
BL program exceptions, evaluation effects or BEAM operational behavior. The
earlier Core program model has its own outcomes and Source connections.

The final theorem says: whenever every original assertion evaluates to
`some true`, the original claim evaluates to `some true`. Its countermodel
premise includes an undefined claim, so a division-by-zero result cannot be
silently counted as a successful promise. Inconsistent assumptions still
permit conditional entailment; feasibility remains a separate obligation.

## External proof check

```sh
research/formal-logic/check-term-refutation \
  research/formal-logic/evidence/term-refutation/examples/weighted.json \
  --output /tmp/original-term-proof
```

The runner validates both packet schemas and independently reconstructs their
canonical identities. It derives the original input layout from the full term
trees, emits fixed typed constructors and numerical mappings, then independently
parses those declarations and checks them against the original data. Names stay
data; they never become Lean identifiers. Equality sorts, reversed greater-than
relations and every variadic operand are checked by that data relation.

Lean receives only the pinned `Refutation.olean` and `Terms.olean` in a private
library directory. It checks three generated theorems:

1. `packetAccepted`: the executable normalized checker accepts the proof.
2. `normalizationConnected`: an original countermodel would satisfy that exact
   normalized problem under the named input mappings.
3. `originalQuestionEntails`: the composition rule establishes the original
   typed conditional claim.

The connection proof first resolves concrete syntax lists and atom lookups.
It splits original Boolean inputs and conditional guards, retains each guard's
equation while selecting the corresponding branch, and applies Lean's checked
integer arithmetic tactic. Indexed value aliases are reduced before arithmetic
reflection. These proof-search steps do not add logical axioms. Accepted source
must match the closed proof template; substituted imports, additional
declarations, `sorry` and a replaced `native_decide` template are rejected.

The current generator limits the combined Boolean-input/choice cases to 12,
integer names to 1,024, original visits to 65,536 and original depth to 128.
The existing normalized checker limits also apply. The proof process has a
2 GB memory cap and a 120-second child deadline. Failure to construct or check a
proof is `not-accepted`, not a counterexample to the claim. These are limits of
this generator and transport, not finite bounds on the theorem's integers.

The seventeen original checkpoint examples' final theorem audits list `propext`
and `Quot.sound`; computed normalized acceptance lists `propext`. The default
standalone axiom policy remains `choice-free`, permitting those two foundations.
`--axiom-policy lean-standard` additionally permits `Classical.choice`; the
larger [common loop obligation](OBLIGATIONS.md) actually uses it in a generated
arithmetic proof. Every connection and final theorem's actual audit is recorded
and checked against the selected policy. A rejected choice-free proof does not
show that no choice-free proof of the statement exists. The model's 14 general results have one empty
audit, twelve using only `propext`, and the composition rule using `propext`
and `Quot.sound`. Neither an admitted theorem nor a native-evaluation axiom is
accepted. Receipts are local checker observations, not cryptographic execution
attestations.

## Remaining connections

The checked theorem addresses the contained typed term model. The BL data
encoding/model interpretation remains reviewed code, with independent decoding
and adversarial checks. This is not a proof of the BL implementation of the
term evaluator, Source/Core extraction, model-to-term lowering, compiler or
BEAM runtime. Existing production solver/compiler authority remains unchanged.

The same format is independent of Z3 and OxiZ. Current examples use BL's separate
certificate producer. Future proof adapters can target the common format; the
new implementation does not imply either native solver exports such proofs.
Broader theories need their own checked semantics and evidence rules. General
normalizer preservation, recursive Source summaries, richer term domains and
effect/process refinement remain work toward the full language foundation.
