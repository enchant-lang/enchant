import Terms
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true), (Term.le (Term.mul (Term.int (Int.ofNat 2)) (Term.inputInt 0)) (Term.int (Int.negSucc 0)))] (Term.and (Term.bool true) (Term.and (Term.le (Term.inputInt 0) (Term.int (Int.negSucc 0))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.ofNat 1)] (Int.negSucc 0)))] [(Formula.constant true), (Formula.atom 0), (Formula.neg (Formula.atom 0))])

def packetProof : Proof :=
(Proof.split 0 Proof.boolean Proof.boolean)

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([0] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([0] : List Nat)[index]?.getD 0)

theorem packetAccepted : check packetProblem packetProof = true := by decide
set_option trace.omega true in
theorem normalizationConnected : ∀ integers booleans,
    originalQuestion.assumed integers booleans →
    originalQuestion.claim.eval integers booleans ≠ some true →
    packetProblem.satisfied (integerMap integers) (booleanMap booleans) := by
  intro integers booleans assumed failed
  simp [Question.assumed, originalQuestion] at assumed
  simp only [originalQuestion] at failed
  simp only [Problem.satisfied, packetProblem]
  simp only [List.mem_cons, List.not_mem_nil, forall_eq_or_imp, forall_eq, forall_false, implies_true, and_true]
  dsimp only [Formula.eval]
  dsimp only [Problem.values]
  simp only [List.getElem?_cons_zero, List.getElem?_cons_succ, List.getElem?_nil]
  simp [Row.holds, dot, integerMap, booleanMap]
  all_goals simp_all [Term.eval, strict₂, partial₂, divide, modulus]
  all_goals trace_state
  all_goals omega

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails

example (x : Int) (h : 2 * x ≤ -1) : x ≤ -1 := by omega
