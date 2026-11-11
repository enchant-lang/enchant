import Terms
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true), (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0))] (Term.and (Term.bool true) (Term.and (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.and (Term.implies (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.and (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.not (Term.eqInt (Term.int (Int.ofNat 0)) (Term.int (Int.ofNat 0)))) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.int (Int.ofNat 0))) (Term.bool true))) (Term.and (Term.implies (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.bool false) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.bool true) (Term.bool false))) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.sub (Term.inputInt 1) (Term.int (Int.ofNat 1))) (Term.int (Int.ofNat 0))))) (Term.and (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.sub (Term.inputInt 1) (Term.int (Int.ofNat 1))) (Term.int (Int.ofNat 0))))) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.int (Int.ofNat 0))) (Term.bool true))) (Term.and (Term.or (Term.and (Term.lt (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.sub (Term.inputInt 1) (Term.int (Int.ofNat 1))) (Term.int (Int.ofNat 0)))) (Term.inputInt 1)) (Term.bool true)) (Term.or (Term.and (Term.eqInt (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.int (Int.ofNat 0)) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.sub (Term.inputInt 1) (Term.int (Int.ofNat 1))) (Term.int (Int.ofNat 0)))) (Term.inputInt 1)) (Term.and (Term.lt (Term.int (Int.ofNat 0)) (Term.int (Int.ofNat 0))) (Term.bool true))) (Term.bool false))) (Term.bool true)))))) (Term.and (Term.implies (Term.not (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.bool false) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.bool true) (Term.bool false)))) (Term.eqInt (Term.ite (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.inputInt 1) (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.int (Int.ofNat 0)) (Term.inputInt 1))) (Term.int (Int.ofNat 0)))) (Term.bool true)))))) (Term.bool true))))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.negSucc 0), (Int.ofNat 0)] (Int.ofNat 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.negSucc 0)] (Int.ofNat 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.ofNat 1)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.negSucc 0)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.ofNat 1)] (Int.ofNat 0)))] [(Formula.constant true), (Formula.atom 0), (Formula.neg (Formula.both (Formula.atom 0) (Formula.both (Formula.atom 0) (Formula.either (Formula.neg (Formula.atom 1)) (Formula.both (Formula.both (Formula.neg (Formula.atom 2)) (Formula.atom 1)) (Formula.both (Formula.either (Formula.neg (Formula.both (Formula.neg (Formula.atom 2)) (Formula.atom 3))) (Formula.both (Formula.both (Formula.atom 0) (Formula.either (Formula.atom 2) (Formula.both (Formula.neg (Formula.atom 2)) (Formula.either (Formula.both (Formula.atom 3) (Formula.atom 3)) (Formula.neg (Formula.atom 3)))))) (Formula.both (Formula.either (Formula.atom 2) (Formula.both (Formula.neg (Formula.atom 2)) (Formula.either (Formula.both (Formula.atom 3) (Formula.atom 3)) (Formula.neg (Formula.atom 3))))) (Formula.either (Formula.both (Formula.atom 2) (Formula.atom 3)) (Formula.both (Formula.neg (Formula.atom 2)) (Formula.either (Formula.atom 3) (Formula.both (Formula.neg (Formula.atom 3)) (Formula.atom 3)))))))) (Formula.either (Formula.neg (Formula.neg (Formula.both (Formula.neg (Formula.atom 2)) (Formula.atom 3)))) (Formula.both (Formula.either (Formula.both (Formula.atom 2) (Formula.atom 4)) (Formula.both (Formula.neg (Formula.atom 2)) (Formula.either (Formula.atom 3) (Formula.both (Formula.neg (Formula.atom 3)) (Formula.atom 4))))) (Formula.either (Formula.both (Formula.atom 2) (Formula.atom 1)) (Formula.both (Formula.neg (Formula.atom 2)) (Formula.either (Formula.atom 3) (Formula.both (Formula.neg (Formula.atom 3)) (Formula.atom 1)))))))))))))])

def packetProof : Proof :=
(Proof.split 0 (Proof.split 1 (Proof.split 2 (Proof.linear [(1, 1), (2, 1)]) (Proof.split 3 Proof.boolean (Proof.split 4 Proof.boolean (Proof.linear [(3, 1), (4, 1)])))) Proof.boolean) Proof.boolean)

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([0, 1] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([0, 0, 0, 0, 0] : List Nat)[index]?.getD 0)

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
  all_goals cases hGuard0 : (Term.lt (Term.inputInt 1) (Term.int (Int.ofNat 0))).eval integers booleans
  all_goals first | (rename_i guardValue0; cases guardValue0) | skip
  all_goals simp only [Term.eval, strict₂, partial₂, divide, modulus, known_and, known_or, known_not, FormalTerms.false_and, FormalTerms.and_false, FormalTerms.true_or, FormalTerms.or_true] at *
  all_goals try simp only [hGuard0] at failed
  all_goals try simp only [hGuard0] at assumed
  all_goals cases hGuard1 : (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 1)).eval integers booleans
  all_goals first | (rename_i guardValue1; cases guardValue1) | skip
  all_goals simp only [Term.eval, strict₂, partial₂, divide, modulus, known_and, known_or, known_not, FormalTerms.false_and, FormalTerms.and_false, FormalTerms.true_or, FormalTerms.or_true] at *
  all_goals try simp only [hGuard1] at failed
  all_goals try simp only [hGuard1] at assumed
  all_goals simp_all [Term.eval, strict₂, partial₂, divide, modulus]
  all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
  all_goals omega

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails
