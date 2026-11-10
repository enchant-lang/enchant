import Refutation
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
open FormalRefutation

def packetProblem : Problem :=
(Problem.mk [(Atom.linear (Row.mk [(Int.negSucc 0)] (Int.negSucc 0))), (Atom.linear (Row.mk [(Int.negSucc 0)] (Int.ofNat 0)))] [(Formula.constant true), (Formula.atom 0), (Formula.neg (Formula.atom 1))])

def packetProof : Proof :=
(Proof.split 0 (Proof.split 1 Proof.boolean (Proof.linear [(0, 1), (1, 1)])) Proof.boolean)

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem packetUnsatisfiable : ∀ integers booleans, ¬ packetProblem.satisfied integers booleans :=
  checked_refutation_unsatisfiable packetProblem packetProof packetAccepted
#print axioms packetAccepted
#print axioms packetUnsatisfiable
