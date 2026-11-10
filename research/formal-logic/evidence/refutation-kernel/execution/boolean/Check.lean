import Refutation
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
open FormalRefutation

def packetProblem : Problem :=
(Problem.mk [Atom.boolean, Atom.boolean] [(Formula.constant true), (Formula.neg (Formula.either (Formula.both (Formula.neg (Formula.both (Formula.atom 0) (Formula.atom 1))) (Formula.either (Formula.neg (Formula.atom 0)) (Formula.neg (Formula.atom 1)))) (Formula.both (Formula.neg (Formula.neg (Formula.both (Formula.atom 0) (Formula.atom 1)))) (Formula.neg (Formula.either (Formula.neg (Formula.atom 0)) (Formula.neg (Formula.atom 1)))))))])

def packetProof : Proof :=
(Proof.split 0 (Proof.split 1 Proof.boolean Proof.boolean) Proof.boolean)

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem packetUnsatisfiable : ∀ integers booleans, ¬ packetProblem.satisfied integers booleans :=
  checked_refutation_unsatisfiable packetProblem packetProof packetAccepted
#print axioms packetAccepted
#print axioms packetUnsatisfiable
