import CoreContract

namespace CoreTranslation
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract

/- A zero lookup would hide the difference between two missing error names.
   Check syntactic coverage and prove it covers all dynamically raised names. -/
def covers (names : List String) : Expr Γ τ → Bool
  | .literal _ | .variable _ => true
  | .bind initial body => covers names initial && covers names body
  | .cond condition yes no => covers names condition && (covers names yes && covers names no)
  | .seq initial body => covers names initial && covers names body
  | .neg value => covers names value
  | .intOp _ left right => names.contains "zero-divisor" && (covers names left && covers names right)
  | .comparison _ left right => covers names left && covers names right
  | .boolNot value => covers names value
  | .boolOp _ left right | .equal _ left right => covers names left && covers names right
  | .pair left right => covers names left && covers names right
  | .first record | .second record => covers names record
  | .firstDefault record fallback => covers names record && covers names fallback
  | .setFirst record replacement | .setSecond record replacement =>
    covers names record && covers names replacement
  | .raise reason => names.contains reason

def covered (names : List String) (result : Outcome τ) : Prop :=
  match result with
  | .returned _ => True
  | .raised reason => reason ∈ names

private theorem covered_bind {names : List String} {result : Outcome α} {next : Value α → Outcome β}
    (initial : covered names result) (continuation : ∀ value, covered names (next value)) :
    covered names (result.bind next) := by
  cases result with
  | returned value => exact continuation value
  | raised reason => exact initial

private theorem covered_intOp (names : List String) (op : IntOp) (x y : Int)
    (zero : "zero-divisor" ∈ names) : covered names (op.apply x y) := by
  cases op <;> simp [IntOp.apply, covered]
  all_goals split <;> simp [covered, zero]

theorem eval_covered (names : List String) (expression : Expr Γ τ) :
    ∀ env, covers names expression = true → covered names (eval expression env) := by
  induction expression <;> intro env check <;>
    simp only [covers, Bool.and_eq_true, List.contains_iff_mem] at check <;>
    simp only [eval]
  all_goals first
    | exact True.intro
    | exact check
    | (apply covered_bind <;> first
        | (solve | exact (by assumption : _ ) | apply_assumption <;> first | assumption | exact check.1 | exact check.2.1)
        | (intro v
           first
           | exact True.intro
           | (cases v <;> simp only [Bool.false_eq_true, ↓reduceIte] <;>
              apply_assumption <;> first | exact check.2.1 | exact check.2.2)
           | (apply covered_bind
              · apply_assumption <;> first | exact check.2 | exact check.2.2
              · intro w
                first | exact True.intro | exact covered_intOp _ _ _ _ check.1)
           | (apply_assumption <;> exact check.2)))

theorem decode_covered (codes : List Nat) (reason : String) (member : reason ∈ codes.map errorName) :
    errorName (errorCode codes reason).toNat = reason := by
  unfold errorCode
  cases found : codes.find? (fun n => errorName n == reason) with
  | none =>
    obtain ⟨code, inCodes, rfl⟩ := List.mem_map.mp member
    have absent := (List.find?_eq_none (p := fun n => errorName n == errorName code)).mp found code inCodes
    exact (absent (by simp)).elim
  | some code =>
    have accepted : (errorName code == reason) = true :=
      List.find?_some (p := fun n => errorName n == reason) (a := code) found
    simpa using beq_iff_eq.mp accepted

/- A record is a right-associated product with unit at the end. Its
   conjunction follows that layout, including each nested record field. -/
def payloadEqual : Payload τ → Payload τ → Term .boolean
  | .integer x, .integer y => .eqInt x y
  | .boolean x, .boolean y => .eqBool x y
  | .unit, .unit => .bool true
  | .pair x xs, .pair y ys => .and (payloadEqual x y) (payloadEqual xs ys)

theorem payload_equal_eval (left right : Payload τ) (i : Nat → Int) (b : Nat → Bool)
    (x y : Value τ) (leftValue : left.eval i b = some x) (rightValue : right.eval i b = some y) :
    (payloadEqual left right).eval i b = some (valueEq τ x y) := by
  induction left with
  | integer l => cases right; simp_all [Payload.eval, payloadEqual, Term.eval, valueEq]
  | boolean l => cases right; simp_all [Payload.eval, payloadEqual, Term.eval, valueEq]
  | unit => cases right; rfl
  | pair l ls first rest =>
    cases right with
    | pair r rs =>
      cases hl : l.eval i b <;> cases hls : ls.eval i b <;>
        cases hr : r.eval i b <;> cases hrs : rs.eval i b <;>
        simp [Payload.eval, hl, hls, hr, hrs] at leftValue rightValue
      subst x
      subst y
      simp [payloadEqual, Term.eval.eq_16, valueEq, first r _ _ hl hr, rest rs _ _ hls hrs]

def comparisonQuestion (pre leftOK rightOK : Term .boolean)
    (leftValue rightValue : Payload τ) (leftError rightError : Term .integer) : Question :=
  let compared := .and (.eqBool leftOK rightOK)
    (both (.implies leftOK (payloadEqual leftValue rightValue))
          (.implies (.not leftOK) (.eqInt leftError rightError)))
  ⟨[.bool true, pre], both (.bool true) (both (.bool true) compared)⟩

theorem checked_comparison_equal (pre leftOK rightOK : Term .boolean)
    (leftValue rightValue : Payload τ) (leftError rightError : Term .integer)
    (left right : Outcome τ) (codes : List Nat) (i : Nat → Int) (b : Nat → Bool)
    (leftAgreement : agrees left (leftOK.eval i b) (leftValue.eval i b) (leftError.eval i b) (errorCode codes))
    (rightAgreement : agrees right (rightOK.eval i b) (rightValue.eval i b) (rightError.eval i b) (errorCode codes))
    (leftCovered : covered (codes.map errorName) left) (rightCovered : covered (codes.map errorName) right)
    (claim : (comparisonQuestion pre leftOK rightOK leftValue rightValue leftError rightError).claim.eval i b = some true) :
    left = right := by
  cases left with
  | returned x =>
    obtain ⟨lo, lv, _⟩ := (agrees_returned _ _ _ _ _).mp leftAgreement
    cases right with
    | returned y =>
      obtain ⟨ro, rv, _⟩ := (agrees_returned _ _ _ _ _).mp rightAgreement
      have payload := payload_equal_eval leftValue rightValue i b x y lv rv
      have same : valueEq τ x y = true := by
        simpa [comparisonQuestion, both, Term.eval.eq_2, Term.eval.eq_14, Term.eval.eq_15,
          Term.eval.eq_16, Term.eval.eq_18, lo, ro, payload] using claim
      exact congrArg Outcome.returned ((valueEq_true_iff τ x y).mp same)
    | raised reason =>
      obtain ⟨ro, _⟩ := (agrees_raised _ _ _ _ _).mp rightAgreement
      simp [comparisonQuestion, both, Term.eval.eq_2, Term.eval.eq_14, Term.eval.eq_16, lo, ro] at claim
  | raised l =>
    obtain ⟨lo, le⟩ := (agrees_raised _ _ _ _ _).mp leftAgreement
    cases right with
    | returned y =>
      obtain ⟨ro, _, _⟩ := (agrees_returned _ _ _ _ _).mp rightAgreement
      simp [comparisonQuestion, both, Term.eval.eq_2, Term.eval.eq_14, Term.eval.eq_16, lo, ro] at claim
    | raised r =>
      obtain ⟨ro, re⟩ := (agrees_raised _ _ _ _ _).mp rightAgreement
      have same : errorCode codes l = errorCode codes r := by
        simpa [comparisonQuestion, both, Term.eval.eq_2, Term.eval.eq_13, Term.eval.eq_14,
          Term.eval.eq_15, Term.eval.eq_16, Term.eval.eq_18, lo, ro, le, re] using claim
      have namesEqual : l = r :=
        (decode_covered codes l leftCovered).symm.trans
          ((congrArg (fun code : Int => errorName code.toNat) same).trans (decode_covered codes r rightCovered))
      exact congrArg Outcome.raised namesEqual

theorem composed_translation (left right : Expr Γ τ)
    (inputs : (Nat → Int) → (Nat → Bool) → Env Γ) (codes : List Nat)
    (pre leftOK rightOK : Term .boolean) (leftValue rightValue : Payload τ) (leftError rightError : Term .integer)
    (leftAgreement : ∀ i b, agrees (eval left (inputs i b)) (leftOK.eval i b) (leftValue.eval i b)
      (leftError.eval i b) (errorCode codes))
    (rightAgreement : ∀ i b, agrees (eval right (inputs i b)) (rightOK.eval i b) (rightValue.eval i b)
      (rightError.eval i b) (errorCode codes))
    (leftCovers : covers (codes.map errorName) left = true)
    (rightCovers : covers (codes.map errorName) right = true)
    (entailment : (comparisonQuestion pre leftOK rightOK leftValue rightValue leftError rightError).entails) :
    ∀ i b, pre.eval i b = some true → eval left (inputs i b) = eval right (inputs i b) := by
  intro i b admitted
  apply checked_comparison_equal pre leftOK rightOK leftValue rightValue leftError rightError _ _ codes i b
    (leftAgreement i b) (rightAgreement i b)
    (eval_covered _ left _ leftCovers) (eval_covered _ right _ rightCovers)
  apply entailment
  intro assertion member
  simp only [comparisonQuestion, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with first | second
  · subst assertion; rfl
  · subst assertion; exact admitted

#print axioms eval_covered
#print axioms decode_covered
#print axioms payload_equal_eval
#print axioms checked_comparison_equal
#print axioms composed_translation
end CoreTranslation
