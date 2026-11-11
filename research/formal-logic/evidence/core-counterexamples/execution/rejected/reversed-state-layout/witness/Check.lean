import Witness
set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def originalContext : Context :=
[(Term.bool true), (Term.bool true), (Term.bool true), (Term.and (Term.eqInt (Term.inputInt 2) (Term.int (Int.ofNat 0))) (Term.and (Term.inputBool 0) (Term.bool true))), (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0)), (Term.le (Term.inputInt 0) (Term.int (Int.ofNat 1))), (Term.or (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 0))) (Term.or (Term.and (Term.bool true) (Term.and (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.or (Term.not (Term.bool true)) (Term.or (Term.bool true) (Term.bool false))) (Term.bool true)))) (Term.bool false))), (Term.eqInt (Term.inputInt 3) (Term.ite (Term.and (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.and (Term.bool true) (Term.and (Term.implies (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))) (Term.bool true))) (Term.bool true))) (Term.sub (Term.inputInt 2) (Term.inputInt 1)) (Term.inputInt 2))), (Term.eqBool (Term.inputBool 1) (Term.ite (Term.and (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.and (Term.bool true) (Term.and (Term.implies (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))) (Term.bool true))) (Term.bool true))) (Term.inputBool 0) (Term.inputBool 0))), (Term.implies (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 1)) (Term.inputInt 1)) (Term.bool true)))) (Term.bool true))))), (Term.not (Term.and (Term.bool true) (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 2)) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 3)) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.implies (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.bool true) (Term.and (Term.implies (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.implies (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.bool true) (Term.and (Term.implies (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))) (Term.bool true)))) (Term.bool true)) (Term.bool true))))) (Term.bool true))))]

def suppliedWitness : Witness :=
(Witness.mk [(Int.ofNat 1), (Int.ofNat 1), (Int.ofNat 0), (Int.negSucc 0)] [true, true])

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
