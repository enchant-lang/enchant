import Refutation
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
open FormalRefutation

def packetProblem : Problem :=
(Problem.mk [] [(Formula.constant true), (Formula.constant false)])

def packetProof : Proof :=
Proof.boolean

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem packetUnsatisfiable : ∀ integers booleans, ¬ packetProblem.satisfied integers booleans :=
  checked_refutation_unsatisfiable packetProblem packetProof packetAccepted
#print axioms packetAccepted
#print axioms packetUnsatisfiable
