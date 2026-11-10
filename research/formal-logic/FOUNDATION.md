# An executable formal foundation for Beam Lisp

Owner: the integration session, writing directly to `main`. The autonomous
goal is to implement the dossier's formal-language vision in coherent stages.
All project checks reuse `sdk-pin.json`; builds and checks are serialized.

## Implementation sequence

1. **Checked evidence.** A pure certificate checker for Boolean reasoning and
   linear integer contradictions; a separate, incomplete certificate producer;
   statement/profile/assumption binding; adversarial and independent checks.
2. **Specified core.** A small typed language with explicit outcomes, a reference
   interpreter, elaboration from reviewed compiler ANF and translation checks.
3. **Contracts and totality.** Preconditions, postconditions, effects and
   termination obligations, checked evidence attached to exact definitions.
4. **Composition.** Checked function summaries, refinement boundaries, effect
   frames, language collections and arithmetic profiles; explicit unsupported
   domains and assumptions.
5. **Processes.** Transition contracts, safety and trace refinement, bounded
   exploration, ranking-based progress, fairness and failure assumptions.
6. **Integration.** A common term-based production path, both native backends,
   compiler gates and regression qualification, with deliberate legacy migration.

Each stage must expose useful BL data/functions and retain executable evidence.
The sequence can change when code or checks reveal a better boundary. A stage's
existence does not imply the whole language, compiler or BEAM is verified.

## First proof system

`formal.certificate` checks a refutation of the assumptions together with the
negated claim. Its own normalization recognizes only Bool and linear Int terms.
It rewrites strict integer inequalities exactly, and can divide an inequality
by the positive gcd of its variable coefficients while rounding the bound down.

A certificate contains a finite binary case split on a normalized Boolean or
arithmetic atom. Every branch closes either because a Boolean assertion is
false under that branch, or because a nonnegative integer weighted sum of its
linear inequalities produces `0 <= b` with `b < 0`. Both branches of every
split must check. Atom definitions come from the statement, never the proof.
The checker recomputes all inequalities, weights, sums and statement identity.
It never calls a solver or trusts a producer's intermediate conclusion.

`formal.proof` searches for such objects separately, using case splits and
Fourier–Motzkin elimination with retained weights. Search is incomplete for
integer arithmetic and bounded by explicit budgets. Failure is `unknown`,
never a proof of satisfiability. Nonlinear multiplication, division, arrays,
quantifiers, floating point and unreviewed source effects are refused by this
proof system even when a solver can decide them.

This uses the standard distinction between Boolean combinations of linear
integer inequalities ([SMT-LIB logic catalogue](https://smt-lib.org/logics.shtml))
and proof checking by explicit arithmetic combinations (compare the linear
arithmetic rules in the [veriT proof format](https://www.verit-solver.org/download/2021.06.1/proofonomicon.pdf)).
The certificate format and implementation here are ours; they are not an
implementation of the veriT or Z3 proof formats.

Checked entailment is conditional on the named assumptions. It does not assert
that those assumptions are satisfiable. A source theorem also needs a reviewed
connection between source semantics and its term statement. The checker,
normalization, term validation, exact integer operations, BL compiler and BEAM
runtime remain in the implementation trust boundary. This first checker is not
itself mechanically verified and does not certify all SMT theories.
