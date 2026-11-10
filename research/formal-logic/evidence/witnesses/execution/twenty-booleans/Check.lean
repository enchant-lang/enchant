import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.and (Term.inputBool 0) (Term.and (Term.inputBool 1) (Term.and (Term.inputBool 12) (Term.and (Term.inputBool 13) (Term.and (Term.inputBool 14) (Term.and (Term.inputBool 15) (Term.and (Term.inputBool 16) (Term.and (Term.inputBool 17) (Term.and (Term.inputBool 18) (Term.and (Term.inputBool 19) (Term.and (Term.inputBool 2) (Term.and (Term.inputBool 3) (Term.and (Term.inputBool 4) (Term.and (Term.inputBool 5) (Term.and (Term.inputBool 6) (Term.and (Term.inputBool 7) (Term.and (Term.inputBool 8) (Term.and (Term.inputBool 9) (Term.and (Term.inputBool 10) (Term.and (Term.inputBool 11) (Term.bool true)))))))))))))))))))))]

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
