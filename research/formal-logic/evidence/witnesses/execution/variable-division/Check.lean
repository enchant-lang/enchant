import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.eqInt (Term.div (Term.inputInt 0) (Term.inputInt 1)) (Term.int (Int.ofNat 3))), (Term.eqInt (Term.mod (Term.inputInt 0) (Term.inputInt 1)) (Term.int (Int.ofNat 2)))]

def suppliedWitness : Witness :=
(Witness.mk [(Int.negSucc 6), (Int.negSucc 2)] [])

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
