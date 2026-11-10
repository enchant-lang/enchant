import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.and (Term.bool true) (Term.and (Term.inputBool 0) (Term.and (Term.or (Term.inputBool 1) (Term.or (Term.inputBool 0) (Term.or (Term.bool false) (Term.bool false)))) (Term.bool true))))]

def suppliedWitness : Witness :=
(Witness.mk [] [true, false])

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
