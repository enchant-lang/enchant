import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.bool true), (Term.bool true), (Term.bool true), (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 0))), (Term.not (Term.and (Term.bool true) (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.bool true)))) (Term.bool true)) (Term.bool true)) (Term.bool true))))]

def suppliedWitness : Witness :=
(Witness.mk [(Int.ofNat 0)] [])

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
