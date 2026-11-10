import Refutation
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
open FormalRefutation

def packetProblem : Problem :=
(Problem.mk [Atom.boolean] [(Formula.constant true), (Formula.neg (Formula.either (Formula.atom 0) (Formula.neg (Formula.atom 0))))])

def packetProof : Proof :=
(Proof.split 0 Proof.boolean Proof.boolean)

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem packetUnsatisfiable : ∀ integers booleans, ¬ packetProblem.satisfied integers booleans :=
  checked_refutation_unsatisfiable packetProblem packetProof packetAccepted
#print axioms packetAccepted
#print axioms packetUnsatisfiable
