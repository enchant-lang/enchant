import CoreTerms


set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

namespace ActorInitTerms

def originalQuestion : Question :=
(Question.mk [(Term.bool true), (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))] (Term.and (Term.bool true) (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [] [(Formula.constant true), (Formula.constant true), (Formula.constant false)])

def packetProof : Proof :=
Proof.boolean

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([] : List Nat)[index]?.getD 0)

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem normalizationConnected : ∀ integers booleans,
    originalQuestion.assumed integers booleans →
    originalQuestion.claim.eval integers booleans ≠ some true →
    packetProblem.satisfied (integerMap integers) (booleanMap booleans) := by
  intro integers booleans assumed failed
  all_goals simp [Question.assumed, originalQuestion] at assumed
  all_goals simp only [originalQuestion] at failed
  all_goals simp only [Problem.satisfied, packetProblem]
  all_goals simp only [List.mem_cons, List.not_mem_nil, forall_eq_or_imp, forall_eq, forall_false, implies_true, and_true]
  all_goals try dsimp only [Formula.eval]
  all_goals try dsimp only [Problem.values]
  all_goals simp only [List.getElem?_cons_zero, List.getElem?_cons_succ, List.getElem?_nil]
  all_goals simp [Row.holds, dot, integerMap, booleanMap]
  all_goals first
    | (simp_all [Term.eval, strict₂, partial₂, divide, modulus]
       all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
       all_goals omega)
    | (simp [Term.eval, strict₂, partial₂, divide, modulus] at *
       all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
       all_goals omega)

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails

end ActorInitTerms



set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
set_option linter.unusedSimpArgs false
set_option linter.unusedVariables false
open BeamLispCore FormalTerms FormalRefutation CoreTerms

namespace ActorHandlerCore0


def originalProgram : Expr [(BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit), BeamLispCore.Ty.unit] BeamLispCore.Ty.unit :=
(Expr.cond (Expr.first (localExpr (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit) Var.zero)) unitLit (localExpr BeamLispCore.Ty.unit (Var.succ Var.zero)))

def originalInputs (i : Nat → Int) (b : Nat → Bool) : Env [(BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit), BeamLispCore.Ty.unit] :=
(Env.cons (Prod.mk (b 0) Unit.unit) (Env.cons Unit.unit Env.nil))

def errorCodes : List Nat :=
[1]

def symbolicOK : Term FormalTerms.Ty.boolean :=
(Term.bool true)

def symbolicValue : Payload BeamLispCore.Ty.unit :=
Payload.unit

def symbolicError : Term FormalTerms.Ty.integer :=
(Term.int (Int.ofNat 0))

theorem errorCatalogueRoundTrip : errorCodes.all (fun code => errorCode errorCodes (errorName code) == Int.ofNat code) = true := by decide

private theorem representedErrorCode (code : Nat) (present : code ∈ errorCodes) :
    errorCode errorCodes (errorName code) = Int.ofNat code :=
  beq_iff_eq.mp (List.all_eq_true.mp errorCatalogueRoundTrip code present)

private theorem zeroDivisorCode : errorCode errorCodes "zero-divisor" = 1 :=
  representedErrorCode 1 (by decide)

theorem coreTermCorrespondence : ∀ (i : Nat → Int) (b : Nat → Bool),
    agrees (BeamLispCore.eval originalProgram (originalInputs i b))
      (symbolicOK.eval i b) (symbolicValue.eval i b) (symbolicError.eval i b) (errorCode errorCodes) := by
  intro i b
  simp [originalProgram, originalInputs, symbolicOK, symbolicValue, symbolicError,
    BeamLispCore.eval, Env.lookup, Elaboration.returned_bind, Elaboration.raised_bind, Payload.eval, eval_choice,
    Term.eval.eq_1, Term.eval.eq_2, Term.eval.eq_3, Term.eval.eq_4, Term.eval.eq_5,
    Term.eval.eq_6, Term.eval.eq_7, Term.eval.eq_8, Term.eval.eq_9, Term.eval.eq_10,
    Term.eval.eq_11, Term.eval.eq_12, Term.eval.eq_13, Term.eval.eq_14, Term.eval.eq_15,
    Term.eval.eq_16, Term.eval.eq_17, Term.eval.eq_18, Term.eval.eq_19,
    apply_quot, apply_rem, apply_mod, Comparison.apply, BoolOp.apply, valueEq]
  all_goals try simp [IntOp.apply, Elaboration.returned_bind, Elaboration.raised_bind, divide, modulus,
    known_and, known_or, known_not, quotientValue, remainderValue, modulusValue, zeroDivisorCode]
  all_goals try dsimp (config := { instances := true }) only [FormalTerms.Ty.Value, BeamLispCore.Value] at *
  all_goals repeat' (split <;> simp_all [IntOp.apply, Elaboration.returned_bind, Elaboration.raised_bind, divide, modulus,
    known_and, known_or, known_not, quotientValue, remainderValue, modulusValue, zeroDivisorCode])
  all_goals try simp (disch := decide) [representedErrorCode, zeroDivisorCode]
  all_goals try dsimp (config := { instances := true }) only [FormalTerms.Ty.Value, BeamLispCore.Value] at *
  all_goals try simp_all
  all_goals first | rfl | decide | omega

#print axioms coreTermCorrespondence
#print axioms errorCatalogueRoundTrip

end ActorHandlerCore0


set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
set_option linter.unusedSimpArgs false
open FormalRefutation FormalTerms

namespace ActorHandlerTerms0

def originalQuestion : Question :=
(Question.mk [(Term.bool true), (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)), (Term.bool true)] (Term.and (Term.bool true) (Term.and (Term.and (Term.bool true) (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true)) (Term.bool true))) (Term.bool true))))

def packetProblem : Problem :=
(Problem.mk [] [(Formula.constant true), (Formula.constant true), (Formula.constant true), (Formula.constant false)])

def packetProof : Proof :=
Proof.boolean

def integerMap (integers : Nat → Int) (index : Nat) : Int := integers (([] : List Nat)[index]?.getD 0)

def booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (([] : List Nat)[index]?.getD 0)

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem normalizationConnected : ∀ integers booleans,
    originalQuestion.assumed integers booleans →
    originalQuestion.claim.eval integers booleans ≠ some true →
    packetProblem.satisfied (integerMap integers) (booleanMap booleans) := by
  intro integers booleans assumed failed
  all_goals simp [Question.assumed, originalQuestion] at assumed
  all_goals simp only [originalQuestion] at failed
  all_goals simp only [Problem.satisfied, packetProblem]
  all_goals simp only [List.mem_cons, List.not_mem_nil, forall_eq_or_imp, forall_eq, forall_false, implies_true, and_true]
  all_goals try dsimp only [Formula.eval]
  all_goals try dsimp only [Problem.values]
  all_goals simp only [List.getElem?_cons_zero, List.getElem?_cons_succ, List.getElem?_nil]
  all_goals simp [Row.holds, dot, integerMap, booleanMap]
  all_goals first
    | (simp_all [Term.eval, strict₂, partial₂, divide, modulus]
       all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
       all_goals omega)
    | (simp [Term.eval, strict₂, partial₂, divide, modulus] at *
       all_goals try dsimp (config := { instances := true }) only [Ty.Value] at *
       all_goals omega)

theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails

end ActorHandlerTerms0
