import InitializerCore
import ControllerCore
import EntailmentCheck
import CoreLoop

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract LoopTotal CoreLoop


def stateSlots :=
(Layout.pair (Layout.bool 1) (Layout.pair (Layout.int 1) Layout.unit))

def resultSlot :=
(Layout.bool 0)

def loopPre :=
(Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0))

def loopInv :=
(Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 1))

def rankFirst :=
(Term.inputInt 1)

def rankSecond :=
(Term.int (Int.ofNat 0))

def loopPost :=
(Term.bool true)

def integerSlots : List Nat :=
[0, 1]

def booleanSlots : List Nat :=
[1]

def policy := Policy.mk stateSlots resultSlot loopPre loopInv rankFirst rankSecond loopPost
def stepData := StepTerms.unpack ControllerCore.symbolicValue
def loopInputs (input : Inputs) := InitializerCore.originalInputs input.ints input.bools
def mapInt (n : Nat) : Nat := integerSlots[n]?.getD 0
def mapBool (n : Nat) : Nat := booleanSlots[n]?.getD 0

theorem sameLoopInputs : ControllerCore.originalInputs = InitializerCore.originalInputs := rfl

theorem exactStepPayload : stepData.pack = ControllerCore.symbolicValue := rfl

theorem exactLoopQuestion :
    renameQuestion originalQuestion mapInt mapBool =
      policy.question InitializerCore.symbolicOK InitializerCore.symbolicValue ControllerCore.symbolicOK stepData := rfl

theorem originalCoreLoopReturns : ∀ input, policy.pre.eval input.ints input.bools = some true →
    ∃ first last result,
      initial InitializerCore.originalProgram loopInputs policy.stateSlots input = .ok first ∧
      Returns (control ControllerCore.originalProgram loopInputs policy.stateSlots) first last result ∧
      policy.good last ∧ policy.resultHolds last result := by
  apply composed_loop policy InitializerCore.originalProgram ControllerCore.originalProgram loopInputs
    InitializerCore.symbolicOK ControllerCore.symbolicOK InitializerCore.symbolicValue stepData
    InitializerCore.symbolicError ControllerCore.symbolicError
    (errorCode InitializerCore.errorCodes) (errorCode ControllerCore.errorCodes)
  · intro input
    exact InitializerCore.coreTermCorrespondence input.ints input.bools
  · intro input
    simpa only [loopInputs, sameLoopInputs, exactStepPayload] using ControllerCore.coreTermCorrespondence input.ints input.bools
  · exact exactLoopQuestion ▸ rename_entails originalQuestion mapInt mapBool originalQuestionEntails

#print axioms sameLoopInputs
#print axioms exactStepPayload
#print axioms exactLoopQuestion
#print axioms originalCoreLoopReturns
