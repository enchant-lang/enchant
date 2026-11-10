import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.eqInt (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.add (Term.int (Int.ofNat 0)) (Term.ite (Term.inputBool 0) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 1) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 12) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 13) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 14) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 15) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 16) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 17) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 18) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 19) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 2) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 3) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 4) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 5) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 6) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 7) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 8) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 9) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 10) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.ite (Term.inputBool 11) (Term.int (Int.ofNat 1)) (Term.int (Int.ofNat 0)))) (Term.int (Int.ofNat 20)))]

def suppliedWitness : Witness :=
(Witness.mk [] [true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true])

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
