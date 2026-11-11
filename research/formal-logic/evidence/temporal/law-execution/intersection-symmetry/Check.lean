import Terms
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.and (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.and (Term.le (Term.inputInt 0) (Term.inputInt 1)) (Term.bool true))) (Term.and (Term.le (Term.inputInt 0) (Term.inputInt 1)) (Term.bool true))) (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.and (Term.le (Term.inputInt 2) (Term.inputInt 3)) (Term.bool true))) (Term.and (Term.le (Term.inputInt 2) (Term.inputInt 3)) (Term.bool true))) (Term.bool true))) (Term.and (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.and (Term.le (Term.inputInt 2) (Term.inputInt 3)) (Term.bool true))) (Term.and (Term.le (Term.inputInt 2) (Term.inputInt 3)) (Term.bool true))) (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.and (Term.le (Term.inputInt 0) (Term.inputInt 1)) (Term.bool true))) (Term.and (Term.le (Term.inputInt 0) (Term.inputInt 1)) (Term.bool true))) (Term.bool true))) (Term.bool true)))] (Term.and (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)) (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)) (Term.bool true))) (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)) (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)) (Term.bool true))) (Term.bool true))) (Term.and (Term.eqBool (Term.and (Term.lt (Term.inputInt 0) (Term.inputInt 1)) (Term.and (Term.lt (Term.inputInt 2) (Term.inputInt 3)) (Term.and (Term.lt (Term.inputInt 0) (Term.inputInt 3)) (Term.and (Term.lt (Term.inputInt 2) (Term.inputInt 1)) (Term.bool true))))) (Term.and (Term.lt (Term.inputInt 2) (Term.inputInt 3)) (Term.and (Term.lt (Term.inputInt 0) (Term.inputInt 1)) (Term.and (Term.lt (Term.inputInt 2) (Term.inputInt 1)) (Term.and (Term.lt (Term.inputInt 0) (Term.inputInt 3)) (Term.bool true)))))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.ofNat 1), (Int.negSucc 0), (Int.ofNat 0), (Int.ofNat 0)] (Int.ofNat 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 1), (Int.negSucc 0)] (Int.ofNat 0))), (Atom.linear (Row.mk [(Int.ofNat 1), (Int.negSucc 0), (Int.ofNat 0), (Int.ofNat 0)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 1), (Int.negSucc 0)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.ofNat 1), (Int.ofNat 0), (Int.ofNat 0), (Int.negSucc 0)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.negSucc 0), (Int.ofNat 1), (Int.ofNat 0)] (Int.negSucc 0)))] [(Formula.both (Formula.both (Formula.both (Formula.atom 0) (Formula.atom 0)) (Formula.both (Formula.atom 1) (Formula.atom 1))) (Formula.both (Formula.both (Formula.atom 1) (Formula.atom 1)) (Formula.both (Formula.atom 0) (Formula.atom 0)))), (Formula.neg (Formula.either (Formula.both (Formula.both (Formula.both (Formula.atom 2) (Formula.atom 3)) (Formula.both (Formula.atom 4) (Formula.atom 5))) (Formula.both (Formula.both (Formula.atom 3) (Formula.atom 2)) (Formula.both (Formula.atom 5) (Formula.atom 4)))) (Formula.both (Formula.neg (Formula.both (Formula.both (Formula.atom 2) (Formula.atom 3)) (Formula.both (Formula.atom 4) (Formula.atom 5)))) (Formula.neg (Formula.both (Formula.both (Formula.atom 3) (Formula.atom 2)) (Formula.both (Formula.atom 5) (Formula.atom 4)))))))])

def packetProof : Proof :=
(Proof.split 0 (Proof.split 1 (Proof.split 2 (Proof.split 3 (Proof.split 4 (Proof.split 5 Proof.boolean Proof.boolean) Proof.boolean) Proof.boolean) Proof.boolean) Proof.boolean) Proof.boolean)

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([0, 1, 2, 3] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([0, 0, 0, 0, 0, 0] : List Nat)[index]?.getD 0)

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
  all_goals first
    | (simp_all [Term.eval, strict₂, partial₂, divide, modulus, Bool.and_assoc, Bool.and_comm, Bool.and_left_comm, Bool.or_assoc, Bool.or_comm, Bool.or_left_comm]
       all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
       all_goals omega)
    | (simp [Term.eval, strict₂, partial₂, divide, modulus, Bool.and_assoc, Bool.and_comm, Bool.and_left_comm, Bool.or_assoc, Bool.or_comm, Bool.or_left_comm] at *
       all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
       all_goals omega)

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails
