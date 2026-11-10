import CoreTerms

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
set_option linter.unusedSimpArgs false
set_option linter.unusedVariables false
open BeamLispCore FormalTerms FormalRefutation CoreTerms


def originalProgram : Expr [BeamLispCore.Ty.bool, (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)), BeamLispCore.Ty.int, BeamLispCore.Ty.int] (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)) :=
(Expr.bind (localExpr (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)) (Var.succ Var.zero)) (Expr.bind (localExpr BeamLispCore.Ty.int (Var.succ (Var.succ (Var.succ Var.zero)))) (Expr.bind (localExpr BeamLispCore.Ty.int (Var.succ (Var.succ (Var.succ (Var.succ (Var.succ Var.zero)))))) (Expr.bind (localExpr BeamLispCore.Ty.bool (Var.succ (Var.succ (Var.succ Var.zero)))) (Expr.pair (localExpr BeamLispCore.Ty.int (Var.succ Var.zero)) (Expr.pair (localExpr BeamLispCore.Ty.bool Var.zero) unitLit))))))

def originalInputs (i : Nat → Int) (b : Nat → Bool) : Env [BeamLispCore.Ty.bool, (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)), BeamLispCore.Ty.int, BeamLispCore.Ty.int] :=
(Env.cons (b 0) (Env.cons (Prod.mk (i 0) (Prod.mk (b 1) Unit.unit)) (Env.cons (i 1) (Env.cons (i 2) Env.nil))))

def errorCodes : List Nat :=
[1]

def symbolicOK : Term FormalTerms.Ty.boolean :=
(Term.bool true)

def symbolicValue : Payload (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)) :=
(Payload.pair (Payload.integer (Term.inputInt 2)) (Payload.pair (Payload.boolean (Term.inputBool 0)) Payload.unit))

def symbolicError : Term FormalTerms.Ty.integer :=
(Term.int (Int.ofNat 0))

theorem coreTermCorrespondence : ∀ (i : Nat → Int) (b : Nat → Bool),
    agrees (BeamLispCore.eval originalProgram (originalInputs i b))
      (symbolicOK.eval i b) (symbolicValue.eval i b) (symbolicError.eval i b) (errorCode errorCodes) := by
  intro i b
  simp [originalProgram, originalInputs, symbolicOK, symbolicValue, symbolicError, errorCodes,
    BeamLispCore.eval, Env.lookup, Outcome.bind, Payload.eval, eval_choice,
    Term.eval.eq_1, Term.eval.eq_2, Term.eval.eq_3, Term.eval.eq_4, Term.eval.eq_5,
    Term.eval.eq_6, Term.eval.eq_7, Term.eval.eq_8, Term.eval.eq_9, Term.eval.eq_10,
    Term.eval.eq_11, Term.eval.eq_12, Term.eval.eq_13, Term.eval.eq_14, Term.eval.eq_15,
    Term.eval.eq_16, Term.eval.eq_17, Term.eval.eq_18, Term.eval.eq_19,
    apply_quot, apply_rem, apply_mod, Comparison.apply, BoolOp.apply, valueEq]
  all_goals try simp [IntOp.apply, Outcome.bind, divide, modulus,
    known_and, known_or, known_not, quotientValue, remainderValue, modulusValue, errorCode, errorName]
  all_goals try dsimp (config := { instances := true }) only [FormalTerms.Ty.Value, BeamLispCore.Value] at *
  all_goals repeat' (split <;> simp_all [IntOp.apply, Outcome.bind, divide, modulus,
    known_and, known_or, known_not, quotientValue, remainderValue, modulusValue, errorCode, errorName])
  all_goals try dsimp (config := { instances := true }) only [FormalTerms.Ty.Value, BeamLispCore.Value] at *
  all_goals try simp_all
  all_goals first | rfl | decide | omega

theorem errorCatalogueRoundTrip : errorCodes.all (fun code => errorCode errorCodes (errorName code) == Int.ofNat code) = true := by decide

#print axioms coreTermCorrespondence
#print axioms errorCatalogueRoundTrip
