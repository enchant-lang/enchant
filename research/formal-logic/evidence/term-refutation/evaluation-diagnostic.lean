import Terms
set_option maxRecDepth 1000
set_option maxHeartbeats 200000
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true), (Term.le (Term.int (Int.ofNat 2)) (Term.inputInt 0)), (Term.le (Term.int (Int.ofNat 3)) (Term.inputInt 1))] (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 7)) (Term.add (Term.mul (Term.int (Int.ofNat 2)) (Term.inputInt 0)) (Term.inputInt 1))) (Term.bool true))))

 theorem originalEvaluation (i : Nat → Int) (b : Nat → Bool) : originalQuestion.claim.eval i b = some (decide (7 ≤ 2 * i 0 + i 1)) := by
  simp [originalQuestion, Term.eval, strict₂]
#print axioms originalEvaluation
