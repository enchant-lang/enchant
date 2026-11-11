import CoreTerms

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
set_option linter.unusedSimpArgs false
set_option linter.unusedVariables false
open BeamLispCore FormalTerms FormalRefutation CoreTerms

namespace ControllerCore


def originalProgram : Expr [BeamLispCore.Ty.int, BeamLispCore.Ty.int, BeamLispCore.Ty.int, BeamLispCore.Ty.int] (BeamLispCore.Ty.prod BeamLispCore.Ty.bool (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) BeamLispCore.Ty.unit))) :=
(Expr.cond (Expr.comparison Comparison.gt (localExpr BeamLispCore.Ty.int (Var.succ (Var.succ (Var.succ Var.zero)))) (intLit (Int.ofNat 0))) (Expr.bind (boolLit true) (Expr.bind (intLit (Int.ofNat 0)) (Expr.bind (Expr.bind (Expr.intOp IntOp.sub (localExpr BeamLispCore.Ty.int (Var.succ (Var.succ (Var.succ (Var.succ (Var.succ Var.zero)))))) (intLit (Int.ofNat 1))) (Expr.bind (Expr.intOp IntOp.add (localExpr BeamLispCore.Ty.int (Var.succ (Var.succ (Var.succ (Var.succ (Var.succ Var.zero)))))) (intLit (Int.ofNat 1))) (Expr.pair (localExpr BeamLispCore.Ty.int Var.zero) (Expr.pair (localExpr BeamLispCore.Ty.int (Var.succ Var.zero)) unitLit)))) (Expr.pair (localExpr BeamLispCore.Ty.bool (Var.succ (Var.succ Var.zero))) (Expr.pair (localExpr BeamLispCore.Ty.int (Var.succ Var.zero)) (Expr.pair (localExpr (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) Var.zero) unitLit)))))) (Expr.bind (boolLit false) (Expr.bind (localExpr BeamLispCore.Ty.int (Var.succ (Var.succ (Var.succ Var.zero)))) (Expr.bind (Expr.bind (intLit (Int.ofNat 0)) (Expr.bind (intLit (Int.ofNat 0)) (Expr.pair (localExpr BeamLispCore.Ty.int Var.zero) (Expr.pair (localExpr BeamLispCore.Ty.int (Var.succ Var.zero)) unitLit)))) (Expr.pair (localExpr BeamLispCore.Ty.bool (Var.succ (Var.succ Var.zero))) (Expr.pair (localExpr BeamLispCore.Ty.int (Var.succ Var.zero)) (Expr.pair (localExpr (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) Var.zero) unitLit)))))))

def originalInputs (i : Nat → Int) (b : Nat → Bool) : Env [BeamLispCore.Ty.int, BeamLispCore.Ty.int, BeamLispCore.Ty.int, BeamLispCore.Ty.int] :=
(Env.cons (i 1) (Env.cons (i 0) (Env.cons (i 3) (Env.cons (i 2) Env.nil))))

def errorCodes : List Nat :=
[1]

def symbolicOK : Term FormalTerms.Ty.boolean :=
(Term.bool true)

def symbolicValue : Payload (BeamLispCore.Ty.prod BeamLispCore.Ty.bool (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) BeamLispCore.Ty.unit))) :=
(Payload.pair (Payload.boolean (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 2)) (Term.bool true) (Term.bool false))) (Payload.pair (Payload.integer (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 2)) (Term.int (Int.ofNat 0)) (Term.inputInt 3))) (Payload.pair (Payload.pair (Payload.integer (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 2)) (Term.add (Term.inputInt 3) (Term.int (Int.ofNat 1))) (Term.int (Int.ofNat 0)))) (Payload.pair (Payload.integer (Term.ite (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 2)) (Term.sub (Term.inputInt 2) (Term.int (Int.ofNat 1))) (Term.int (Int.ofNat 0)))) Payload.unit)) Payload.unit)))

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

end ControllerCore
