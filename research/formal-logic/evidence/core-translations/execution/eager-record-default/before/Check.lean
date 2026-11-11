import CoreTerms

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
set_option linter.unusedSimpArgs false
set_option linter.unusedVariables false
open BeamLispCore FormalTerms FormalRefutation CoreTerms

namespace BeforeCore


def originalProgram : Expr [BeamLispCore.Ty.int] BeamLispCore.Ty.int :=
(Expr.bind (Expr.bind (localExpr BeamLispCore.Ty.int Var.zero) (Expr.pair (localExpr BeamLispCore.Ty.int Var.zero) unitLit)) (Expr.seq (raiseExpr BeamLispCore.Ty.int 2) (Expr.first (localExpr (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) Var.zero))))

def originalInputs (i : Nat → Int) (b : Nat → Bool) : Env [BeamLispCore.Ty.int] :=
(Env.cons (i 0) Env.nil)

def errorCodes : List Nat :=
[1, 2]

def symbolicOK : Term FormalTerms.Ty.boolean :=
(Term.bool false)

def symbolicValue : Payload BeamLispCore.Ty.int :=
(Payload.integer (Term.inputInt 0))

def symbolicError : Term FormalTerms.Ty.integer :=
(Term.int (Int.ofNat 2))

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

end BeforeCore
