import Terms
set_option maxRecDepth 1000
set_option maxHeartbeats 100000
open FormalRefutation FormalTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true), (Term.le (Term.int (Int.ofNat 2)) (Term.inputInt 0)), (Term.le (Term.int (Int.ofNat 3)) (Term.inputInt 1))] (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 7)) (Term.add (Term.mul (Term.int (Int.ofNat 2)) (Term.inputInt 0)) (Term.inputInt 1))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.negSucc 0), (Int.ofNat 0)] (Int.negSucc 1))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.negSucc 0)] (Int.negSucc 2))), (Atom.linear (Row.mk [(Int.negSucc 1), (Int.negSucc 0)] (Int.negSucc 6)))] [(Formula.constant true), (Formula.atom 0), (Formula.atom 1), (Formula.neg (Formula.atom 2))])

def packetProof : Proof :=
(Proof.split 0 (Proof.split 1 (Proof.split 2 Proof.boolean (Proof.linear [(0, 2), (1, 1), (2, 1)])) Proof.boolean) Proof.boolean)

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([0, 1] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([0, 0, 0] : List Nat)[index]?.getD 0)

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
  trace_state
  fail "diagnostic boundary only"
