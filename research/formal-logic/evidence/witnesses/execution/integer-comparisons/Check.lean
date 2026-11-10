import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.lt (Term.neg (Term.inputInt 0)) (Term.inputInt 1)), (Term.le (Term.inputInt 0) (Term.inputInt 1)), (Term.le (Term.inputInt 0) (Term.inputInt 1)), (Term.lt (Term.sub (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.inputInt 1))]

def suppliedWitness : Witness :=
(Witness.mk [(Int.ofNat 2), (Int.ofNat 3)] [])

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
