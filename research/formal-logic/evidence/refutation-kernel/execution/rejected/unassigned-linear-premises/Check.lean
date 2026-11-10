import Refutation
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
open FormalRefutation

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.negSucc 0), (Int.ofNat 0)] (Int.negSucc 1))), (Atom.linear (Row.mk [(Int.ofNat 0), (Int.negSucc 0)] (Int.negSucc 2))), (Atom.linear (Row.mk [(Int.negSucc 1), (Int.negSucc 0)] (Int.negSucc 6)))] [(Formula.constant true), (Formula.atom 0), (Formula.atom 1), (Formula.neg (Formula.atom 2))])

def packetProof : Proof :=
(Proof.linear [(0, 2), (1, 1), (2, 1)])

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem packetUnsatisfiable : ∀ integers booleans, ¬ packetProblem.satisfied integers booleans :=
  checked_refutation_unsatisfiable packetProblem packetProof packetAccepted
#print axioms packetAccepted
#print axioms packetUnsatisfiable
