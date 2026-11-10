import Terms
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true)] (Term.and (Term.bool true) (Term.and (Term.le (Term.inputInt 0) (Term.ite (Term.inputBool 0) (Term.add (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.add (Term.inputInt 0) (Term.int (Int.ofNat 2))))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [Atom.boolean] [(Formula.constant true), (Formula.neg (Formula.either (Formula.atom 0) (Formula.neg (Formula.atom 0))))])

def packetProof : Proof :=
(Proof.split 0 Proof.boolean Proof.boolean)

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([0] : List Nat)[index]?.getD 0)

theorem packetAccepted : check packetProblem packetProof = true := by decide
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
  all_goals cases h0 : booleans 0
  all_goals simp_all [Term.eval, strict₂, partial₂, divide, modulus]
  all_goals (repeat (first | omega | (split at * <;> simp_all [Term.eval, strict₂, partial₂, divide, modulus])))

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails
