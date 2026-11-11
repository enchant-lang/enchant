import BeforeCore
import AfterCore
import EntailmentCheck
import CoreTranslation

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreTranslation


def translationPre : Term FormalTerms.Ty.boolean :=
(Term.bool true)

def integerSlots : List Nat :=
[]

def booleanSlots : List Nat :=
[]

def mapInt (n : Nat) : Nat := integerSlots[n]?.getD 0
def mapBool (n : Nat) : Nat := booleanSlots[n]?.getD 0

theorem exactTranslationQuestion :
    renameQuestion originalQuestion mapInt mapBool =
      comparisonQuestion translationPre BeforeCore.symbolicOK AfterCore.symbolicOK
        BeforeCore.symbolicValue AfterCore.symbolicValue BeforeCore.symbolicError AfterCore.symbolicError := rfl

theorem sameCoreInputs : AfterCore.originalInputs = BeforeCore.originalInputs := rfl
theorem sameErrorCatalogue : AfterCore.errorCodes = BeforeCore.errorCodes := rfl

theorem beforeErrorsCovered :
    covers (BeforeCore.errorCodes.map errorName) BeforeCore.originalProgram = true := by decide

theorem afterErrorsCovered :
    covers (BeforeCore.errorCodes.map errorName) AfterCore.originalProgram = true := by decide

theorem originalCoreOutcomesEqual : ∀ i b, translationPre.eval i b = some true →
    eval BeforeCore.originalProgram (BeforeCore.originalInputs i b) =
      eval AfterCore.originalProgram (AfterCore.originalInputs i b) := by
  have afterAgreement : ∀ i b, agrees (eval AfterCore.originalProgram (BeforeCore.originalInputs i b))
      (AfterCore.symbolicOK.eval i b) (AfterCore.symbolicValue.eval i b)
      (AfterCore.symbolicError.eval i b) (errorCode BeforeCore.errorCodes) := by
    simpa only [sameCoreInputs, sameErrorCatalogue] using AfterCore.coreTermCorrespondence
  rw [sameCoreInputs]
  exact composed_translation BeforeCore.originalProgram AfterCore.originalProgram BeforeCore.originalInputs
    BeforeCore.errorCodes translationPre BeforeCore.symbolicOK AfterCore.symbolicOK
    BeforeCore.symbolicValue AfterCore.symbolicValue BeforeCore.symbolicError AfterCore.symbolicError
    BeforeCore.coreTermCorrespondence afterAgreement beforeErrorsCovered afterErrorsCovered
    (exactTranslationQuestion ▸ rename_entails originalQuestion mapInt mapBool originalQuestionEntails)

#print axioms exactTranslationQuestion
#print axioms sameCoreInputs
#print axioms sameErrorCatalogue
#print axioms beforeErrorsCovered
#print axioms afterErrorsCovered
#print axioms originalCoreOutcomesEqual
