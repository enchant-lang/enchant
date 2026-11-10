import CoreCheck
import EntailmentCheck
import CoreContract

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract


def contractPre : Term FormalTerms.Ty.boolean :=
(Term.bool false)

def contractPost : Term FormalTerms.Ty.boolean :=
(Term.bool false)

def mustReturn : Bool :=
true

def declaredAllowed : List Nat :=
[]

def integerSlots : List Nat :=
[]

def booleanSlots : List Nat :=
[]


def mapInt (n : Nat) : Nat := integerSlots[n]?.getD 0
def mapBool (n : Nat) : Nat := booleanSlots[n]?.getD 0

theorem exactContractQuestion :
    renameQuestion originalQuestion mapInt mapBool =
      policyQuestion contractPre contractPost symbolicOK symbolicError mustReturn declaredAllowed := rfl

theorem allowedPositive : ∀ n ∈ declaredAllowed, 0 < n := by
  have checked : declaredAllowed.all (fun n => decide (0 < n)) = true := by decide
  simpa only [List.all_eq_true, decide_eq_true_eq] using checked

theorem originalCoreSatisfiesContract : ∀ i b, contractPre.eval i b = some true →
    holds (BeamLispCore.eval originalProgram (originalInputs i b)) (symbolicValue.eval i b)
      (contractPost.eval i b) mustReturn declaredAllowed :=
  composed_contract originalProgram originalInputs contractPre contractPost symbolicOK symbolicValue symbolicError
    mustReturn declaredAllowed errorCodes allowedPositive coreTermCorrespondence
    (exactContractQuestion ▸ rename_entails originalQuestion mapInt mapBool originalQuestionEntails)

#print axioms exactContractQuestion
#print axioms allowedPositive
#print axioms originalCoreSatisfiesContract
