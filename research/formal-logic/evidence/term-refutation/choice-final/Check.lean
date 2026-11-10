import Terms
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true)] (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.inputInt 0) (Term.int (Int.ofNat 0))) (Term.int (Int.ofNat 0)) (Term.inputInt 0))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.ofNat 1)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.negSucc 0)] (Int.ofNat 0)))] [(Formula.constant true), (Formula.neg (Formula.either (Formula.atom 0) (Formula.both (Formula.neg (Formula.atom 0)) (Formula.atom 1))))])

def packetProof : Proof :=
(Proof.split 0 Proof.boolean (Proof.split 1 Proof.boolean (Proof.linear [(0, 1), (1, 1)])))

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([0] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([0, 0] : List Nat)[index]?.getD 0)

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem normalizationConnected : ∀ integers booleans,
    originalQuestion.assumed integers booleans →
    originalQuestion.claim.eval integers booleans ≠ some true →
    packetProblem.satisfied (integerMap integers) (booleanMap booleans) := by
  intro integers booleans assumed failed
  all_goals simp [Question.assumed, originalQuestion] at assumed
  all_goals simp only [originalQuestion] at failed
  all_goals simp only [Problem.satisfied, packetProblem]
  all_goals simp only [List.mem_cons, List.not_mem_nil, forall_eq_or_imp, forall_eq, forall_false, implies_true, and_true]
  all_goals try dsimp only [Formula.eval]
  all_goals try dsimp only [Problem.values]
  all_goals simp only [List.getElem?_cons_zero, List.getElem?_cons_succ, List.getElem?_nil]
  all_goals simp [Row.holds, dot, integerMap, booleanMap]
  all_goals cases hGuard0 : (Term.lt (Term.inputInt 0) (Term.int (Int.ofNat 0))).eval integers booleans
  all_goals first | (rename_i guardValue0; cases guardValue0) | skip
  all_goals simp only [Term.eval, strict₂, partial₂, divide, modulus, known_and, known_or, known_not, FormalTerms.false_and, FormalTerms.and_false, FormalTerms.true_or, FormalTerms.or_true] at *
  all_goals try simp only [hGuard0] at failed
  all_goals try simp only [hGuard0] at assumed
  all_goals simp_all [Term.eval, strict₂, partial₂, divide, modulus]
  all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
  all_goals omega

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails
