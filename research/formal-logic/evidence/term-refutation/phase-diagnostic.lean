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

#print axioms packetAccepted
example (integers : Nat → Int) (booleans : Nat → Bool) (assumed : originalQuestion.assumed integers booleans) : True := by
  simp [Question.assumed, originalQuestion] at assumed
  trace_state
  trivial
