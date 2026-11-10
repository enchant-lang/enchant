import Std

/- A mathematical model of the scalar and finite-product core. Products model
   nested closed record values. The correspondence of ordered map construction
   and canonical named-field layouts with these products remains unproved, as
   does the BL implementation, ANF elaborator, runtime and compiler bridge. -/
namespace BeamLispCore

inductive Ty where
  | int | bool | unit | prod : Ty → Ty → Ty
  deriving DecidableEq

abbrev Value : Ty → Type
  | .int => Int
  | .bool => Bool
  | .unit => Unit
  | .prod α β => Value α × Value β

def valueDecidableEq : (τ : Ty) → DecidableEq (Value τ)
  | .int => inferInstance
  | .bool => inferInstance
  | .unit => inferInstance
  | .prod α β =>
    letI : DecidableEq (Value α) := valueDecidableEq α
    letI : DecidableEq (Value β) := valueDecidableEq β
    inferInstance

instance (τ : Ty) : DecidableEq (Value τ) := valueDecidableEq τ

inductive Var : List Ty → Ty → Type where
  | zero : Var (τ :: Γ) τ
  | succ : Var Γ τ → Var (σ :: Γ) τ

inductive Env : List Ty → Type where
  | nil : Env []
  | cons : Value τ → Env Γ → Env (τ :: Γ)

def Env.lookup : Env Γ → Var Γ τ → Value τ
  | .cons v _, .zero => v
  | .cons _ env, .succ index => env.lookup index

inductive Outcome (τ : Ty) where
  | returned : Value τ → Outcome τ
  | raised : String → Outcome τ
  deriving DecidableEq

def Outcome.bind (result : Outcome α) (next : Value α → Outcome β) : Outcome β :=
  match result with
  | .returned value => next value
  | .raised reason => .raised reason

inductive IntOp where
  | add | sub | mul | quot | rem | mod

def IntOp.apply (op : IntOp) (a b : Int) : Outcome .int :=
  match op with
  | .add => .returned (a + b)
  | .sub => .returned (a - b)
  | .mul => .returned (a * b)
  | .quot => if b = 0 then .raised "zero-divisor" else .returned (Int.tdiv a b)
  | .rem => if b = 0 then .raised "zero-divisor" else .returned (Int.tmod a b)
  | .mod =>
    if b = 0 then .raised "zero-divisor"
    else
      let r := Int.tmod a b
      .returned (if r ≠ 0 ∧ ((r < 0 ∧ b > 0) ∨ (r > 0 ∧ b < 0)) then r + b else r)

inductive Comparison where
  | lt | le | gt | ge

def Comparison.apply (op : Comparison) (a b : Int) : Bool :=
  match op with
  | .lt => decide (a < b)
  | .le => decide (a ≤ b)
  | .gt => decide (a > b)
  | .ge => decide (a ≥ b)

inductive BoolOp where
  | and | or

def BoolOp.apply (op : BoolOp) (a b : Bool) : Bool :=
  match op with
  | .and => a && b
  | .or => a || b

def valueEq : (τ : Ty) → Value τ → Value τ → Bool
  | .int, a, b => decide (a = b)
  | .bool, a, b => decide (a = b)
  | .unit, _, _ => true
  | .prod α β, a, b => valueEq α a.1 b.1 && valueEq β a.2 b.2

inductive Expr : List Ty → Ty → Type where
  | literal : Value τ → Expr Γ τ
  | variable : Var Γ τ → Expr Γ τ
  | bind : Expr Γ α → Expr (α :: Γ) β → Expr Γ β
  | cond : Expr Γ .bool → Expr Γ τ → Expr Γ τ → Expr Γ τ
  | seq : Expr Γ α → Expr Γ β → Expr Γ β
  | neg : Expr Γ .int → Expr Γ .int
  | intOp : IntOp → Expr Γ .int → Expr Γ .int → Expr Γ .int
  | comparison : Comparison → Expr Γ .int → Expr Γ .int → Expr Γ .bool
  | boolNot : Expr Γ .bool → Expr Γ .bool
  | boolOp : BoolOp → Expr Γ .bool → Expr Γ .bool → Expr Γ .bool
  | equal : (α : Ty) → Expr Γ α → Expr Γ α → Expr Γ .bool
  | pair : Expr Γ α → Expr Γ β → Expr Γ (.prod α β)
  | first : Expr Γ (.prod α β) → Expr Γ α
  | second : Expr Γ (.prod α β) → Expr Γ β
  | firstDefault : Expr Γ (.prod α β) → Expr Γ γ → Expr Γ α
  | setFirst : Expr Γ (.prod α β) → Expr Γ α → Expr Γ (.prod α β)
  | setSecond : Expr Γ (.prod α β) → Expr Γ β → Expr Γ (.prod α β)
  | raise : String → Expr Γ τ

/- Lean checks structural recursion here. The model evaluator has no fuel,
   unchecked recursive definition, or host evaluator inside its semantics. -/
def eval : Expr Γ τ → Env Γ → Outcome τ
  | .literal value, _ => .returned value
  | .variable index, env => .returned (env.lookup index)
  | .bind initial body, env =>
    (eval initial env).bind fun value => eval body (.cons value env)
  | .cond condition yes no, env =>
    (eval condition env).bind fun value => if value then eval yes env else eval no env
  | .seq initial body, env => (eval initial env).bind fun _ => eval body env
  | .neg value, env => (eval value env).bind fun a => .returned (-a)
  | .intOp op left right, env =>
    (eval left env).bind fun a => (eval right env).bind fun b => op.apply a b
  | .comparison op left right, env =>
    (eval left env).bind fun a => (eval right env).bind fun b => .returned (op.apply a b)
  | .boolNot value, env => (eval value env).bind fun a => .returned (!a)
  | .boolOp op left right, env =>
    (eval left env).bind fun a => (eval right env).bind fun b => .returned (op.apply a b)
  | .equal α left right, env =>
    (eval left env).bind fun a => (eval right env).bind fun b => .returned (valueEq α a b)
  | .pair left right, env =>
    (eval left env).bind fun a => (eval right env).bind fun b => .returned (a, b)
  | .first record, env => (eval record env).bind fun value => .returned value.1
  | .second record, env => (eval record env).bind fun value => .returned value.2
  | .firstDefault record fallback, env =>
    (eval record env).bind fun value => (eval fallback env).bind fun _ => .returned value.1
  | .setFirst record replacement, env =>
    (eval record env).bind fun value => (eval replacement env).bind fun newValue => .returned (newValue, value.2)
  | .setSecond record replacement, env =>
    (eval record env).bind fun value => (eval replacement env).bind fun newValue => .returned (value.1, newValue)
  | .raise reason, _ => .raised reason

theorem typed_total (expression : Expr Γ τ) (env : Env Γ) :
    ∃ outcome : Outcome τ, eval expression env = outcome :=
  ⟨eval expression env, rfl⟩

theorem no_stuck_typed_outcome (expression : Expr Γ τ) (env : Env Γ) :
    (∃ value : Value τ, eval expression env = .returned value) ∨
    (∃ reason : String, eval expression env = .raised reason) := by
  cases h : eval expression env with
  | returned value => exact Or.inl ⟨value, rfl⟩
  | raised reason => exact Or.inr ⟨reason, rfl⟩

theorem deterministic (expression : Expr Γ τ) (env : Env Γ)
    (h₁ : eval expression env = first) (h₂ : eval expression env = second) :
    first = second := h₁.symm.trans h₂

theorem lexical_binding (value : Value α) (body : Expr (α :: Γ) β) (env : Env Γ) :
    eval (.bind (.literal value) body) env = eval body (.cons value env) := rfl

theorem true_branch_only (yes no : Expr Γ τ) (env : Env Γ) :
    eval (.cond (.literal true) yes no) env = eval yes env := rfl

theorem false_branch_only (yes no : Expr Γ τ) (env : Env Γ) :
    eval (.cond (.literal false) yes no) env = eval no env := rfl

theorem first_failure_wins (reason : String) (right : Expr Γ .int)
    (op : IntOp) (env : Env Γ) :
    eval (.intOp op (.raise reason) right) env = .raised reason := rfl

theorem sequence_failure (reason : String) (body : Expr Γ β) (env : Env Γ) :
    eval (.seq (.raise (τ := Ty.int) reason) body) env = .raised reason := rfl

theorem quotient_zero_raises (a : Int) :
    IntOp.apply .quot a 0 = .raised "zero-divisor" := rfl

theorem remainder_zero_raises (a : Int) :
    IntOp.apply .rem a 0 = .raised "zero-divisor" := rfl

theorem modulus_zero_raises (a : Int) :
    IntOp.apply .mod a 0 = .raised "zero-divisor" := rfl

theorem quotient_negative_divisor :
    IntOp.apply .quot 7 (-3) = .returned (-2) := by decide

theorem remainder_dividend_sign :
    IntOp.apply .rem (-7) 3 = .returned (-1) := by decide

theorem modulus_divisor_sign :
    IntOp.apply .mod 7 (-3) = .returned (-2) := by decide

theorem valueEq_true_iff (τ : Ty) (a b : Value τ) : valueEq τ a b = true ↔ a = b := by
  induction τ with
  | int => simp [valueEq]
  | bool => simp [valueEq]
  | unit => cases a; cases b; simp [valueEq]
  | prod α β ihα ihβ =>
    cases a with
    | mk a₁ a₂ =>
      cases b with
      | mk b₁ b₂ => simp [valueEq, ihα, ihβ]

theorem product_returns_in_order (left : Expr Γ α) (right : Expr Γ β) (env : Env Γ)
    (hl : eval left env = .returned a) (hr : eval right env = .returned b) :
    eval (.pair left right) env = .returned (a, b) := by simp [eval, hl, hr, Outcome.bind]

theorem product_first_failure (reason : String) (right : Expr Γ β) (env : Env Γ) :
    eval (.pair (.raise (τ := α) reason) right) env = .raised reason := rfl

theorem product_second_failure (left : Expr Γ α) (env : Env Γ)
    (hl : eval left env = .returned a) (reason : String) :
    eval (.pair left (.raise (τ := β) reason)) env = .raised reason := by
  simp [eval, hl, Outcome.bind]

theorem projection_preserves_hidden_failure (a : Value α) (reason : String) (env : Env Γ) :
    eval (.first (.pair (.literal a) (.raise (τ := β) reason))) env = .raised reason := rfl

theorem second_projection_preserves_first_failure (b : Value β) (reason : String) (env : Env Γ) :
    eval (.second (.pair (.raise (τ := α) reason) (.literal b))) env = .raised reason := rfl

theorem present_field_evaluates_default (a : Value α) (b : Value β) (reason : String) (env : Env Γ) :
    eval (.firstDefault (.literal (τ := .prod α β) (a, b)) (.raise (τ := γ) reason)) env =
      .raised reason := rfl

theorem projection_default_preserves_base_failure (fallback : Expr Γ γ) (reason : String) (env : Env Γ) :
    eval (.firstDefault (.raise (τ := .prod α β) reason) fallback) env = .raised reason := rfl

theorem update_preserves_base_failure (replacement : Expr Γ α) (reason : String) (env : Env Γ) :
    eval (.setFirst (.raise (τ := .prod α β) reason) replacement) env = .raised reason := rfl

theorem update_preserves_replacement_failure (a : Value α) (b : Value β) (reason : String) (env : Env Γ) :
    eval (.setFirst (.literal (τ := .prod α β) (a, b)) (.raise reason)) env = .raised reason := rfl

theorem update_preserves_other_field (a replacement : Value α) (b : Value β) (env : Env Γ) :
    eval (.setFirst (.literal (τ := .prod α β) (a, b)) (.literal replacement)) env =
      .returned (replacement, b) := rfl

theorem second_update_preserves_other_field (a : Value α) (b replacement : Value β) (env : Env Γ) :
    eval (.setSecond (.literal (τ := .prod α β) (a, b)) (.literal replacement)) env =
      .returned (a, replacement) := rfl

/- A generic ranking rule for the next language layer. Its premise still
   needs a checked proof for each program's actual transition relation. -/
theorem natural_rank_accessible {State : Type} (rank : State → Nat)
    (step : State → State → Prop)
    (decreases : ∀ {current next}, step current next → rank next < rank current) :
    ∀ state, Acc (fun next current => step current next) state := by
  have all : ∀ n, ∀ state, rank state = n → Acc (fun next current => step current next) state := by
    intro n
    induction n using Nat.strongRecOn with
    | ind n ih =>
      intro state hstate
      refine Acc.intro state ?_
      intro next hstep
      exact ih (rank next) (by simpa only [hstate] using decreases hstep) next rfl
  exact fun state => all (rank state) state rfl

theorem natural_rank_wellFounded {State : Type} (rank : State → Nat)
    (step : State → State → Prop)
    (decreases : ∀ {current next}, step current next → rank next < rank current) :
    WellFounded (fun next current => step current next) :=
  ⟨natural_rank_accessible rank step decreases⟩

theorem ranked_relation_wellFounded {State Rank : Type}
    (order : Rank → Rank → Prop) (wf : WellFounded order)
    (rank : State → Rank) (step : State → State → Prop)
    (decreases : ∀ {current next}, step current next → order (rank next) (rank current)) :
    WellFounded (fun next current => step current next) := by
  apply Subrelation.wf (r := InvImage order rank)
  · intro next current hstep
    exact decreases hstep
  · exact InvImage.wf rank wf

theorem lexicographic_pair_rank_wellFounded {State : Type}
    (rank : State → Nat × Nat) (step : State → State → Prop)
    (decreases : ∀ {current next}, step current next →
      Prod.Lex Nat.lt Nat.lt (rank next) (rank current)) :
    WellFounded (fun next current => step current next) :=
  ranked_relation_wellFounded (Prod.Lex Nat.lt Nat.lt)
    (Prod.lex Nat.lt_wfRel Nat.lt_wfRel).wf rank step decreases

theorem integer_rank_wellFounded {State : Type} (rank : State → Int)
    (step : State → State → Prop) (nonnegative : ∀ state, 0 ≤ rank state)
    (decreases : ∀ {current next}, step current next → rank next < rank current) :
    WellFounded (fun next current => step current next) := by
  apply natural_rank_wellFounded (fun state => (rank state).toNat) step
  intro current next hstep
  have h := decreases hstep
  exact (Int.toNat_lt_toNat (Int.lt_of_le_of_lt (nonnegative next) h)).2 h

theorem integer_pair_rank_wellFounded {State : Type} (rank : State → Int × Int)
    (step : State → State → Prop)
    (nonnegative : ∀ state, 0 ≤ (rank state).1 ∧ 0 ≤ (rank state).2)
    (decreases : ∀ {current next}, step current next →
      (rank next).1 < (rank current).1 ∨
        ((rank next).1 = (rank current).1 ∧ (rank next).2 < (rank current).2)) :
    WellFounded (fun next current => step current next) := by
  apply lexicographic_pair_rank_wellFounded
    (fun state => ((rank state).1.toNat, (rank state).2.toNat)) step
  intro current next hstep
  rcases decreases hstep with h | ⟨same, h⟩
  · exact Prod.Lex.left _ _ ((Int.toNat_lt_toNat (Int.lt_of_le_of_lt (nonnegative next).1 h)).2 h)
  · have heq := congrArg Int.toNat same
    change Prod.Lex Nat.lt Nat.lt ((rank next).1.toNat, (rank next).2.toNat)
      ((rank current).1.toNat, (rank current).2.toNat)
    rw [heq]
    exact Prod.Lex.right _ ((Int.toNat_lt_toNat (Int.lt_of_le_of_lt (nonnegative next).2 h)).2 h)

inductive LoopStep (State Result : Type) where
  | finished : Result → LoopStep State Result
  | again : State → LoopStep State Result

/- Given a total finite controller and a well-founded back-edge relation,
   this definition builds an unbounded loop evaluator in the checked logic. -/
def runLoop (body : State → LoopStep State Result)
    (wf : WellFounded (fun next current => body current = .again next)) : State → Result :=
  wf.fix fun state recurse =>
    match h : body state with
    | .finished result => result
    | .again next => recurse next h

theorem runLoop_equation (body : State → LoopStep State Result)
    (wf : WellFounded (fun next current => body current = .again next)) (state : State) :
    runLoop body wf state = match body state with
      | .finished result => result
      | .again next => runLoop body wf next := by
  unfold runLoop
  rw [WellFounded.fix_eq]
  cases hbody : body state <;> rfl

theorem runLoop_postcondition (body : State → LoopStep State Result)
    (wf : WellFounded (fun next current => body current = .again next))
    (post : Result → Prop)
    (finishes : ∀ state result, body state = .finished result → post result) :
    ∀ state, post (runLoop body wf state) := by
  intro state
  induction state using wf.induction with
  | h state ih =>
    rw [runLoop_equation]
    cases hbody : body state with
    | finished result => exact finishes state result hbody
    | again next => exact ih next hbody

/- Reachability ranges over every finite successful prefix, with no depth cap.
   Failure exclusion is a separate premise, not hidden in the step relation. -/
inductive StateReachable (initial : State → Prop) (step : State → State → Prop) : State → Prop where
  | initial {state} : initial state → StateReachable initial step state
  | advance {current next} : StateReachable initial step current → step current next →
      StateReachable initial step next

theorem invariant_on_reachable (initial : State → Prop) (step : State → State → Prop)
    (invariant : State → Prop)
    (starts : ∀ state, initial state → invariant state)
    (preserves : ∀ current next, invariant current → step current next → invariant next)
    {state} (reachable : StateReachable initial step state) : invariant state := by
  induction reachable with
  | initial h => exact starts _ h
  | advance _ hstep ih => exact preserves _ _ ih hstep

theorem no_failed_attempt_on_reachable (initial : State → Prop) (step : State → State → Prop)
    (invariant failedAttempt : State → Prop)
    (starts : ∀ state, initial state → invariant state)
    (preserves : ∀ current next, invariant current → step current next → invariant next)
    (excludesFailure : ∀ state, invariant state → ¬ failedAttempt state)
    {state} (reachable : StateReachable initial step state) : ¬ failedAttempt state :=
  excludesFailure state (invariant_on_reachable initial step invariant starts preserves reachable)

theorem invariant_on_every_trace_position (initial : State → Prop) (step : State → State → Prop)
    (invariant : State → Prop)
    (starts : ∀ state, initial state → invariant state)
    (preserves : ∀ current next, invariant current → step current next → invariant next)
    (trace : Nat → State) (begins : initial (trace 0))
    (advances : ∀ n, step (trace n) (trace (n + 1))) : ∀ n, invariant (trace n) := by
  intro n
  induction n with
  | zero => exact starts _ begins
  | succ n ih => exact preserves _ _ ih (advances n)

/- Explicit finite model runs. The Bool flag records a past failed attempt;
   failure retains the old state and permits only idle events afterwards. -/
inductive ModelStep (step : State → State → Prop) (failedAttempt : State → Prop) :
    (State × Bool) → (State × Bool) → Prop where
  | idle (state : State) (failed : Bool) : ModelStep step failedAttempt (state, failed) (state, failed)
  | success {current next} : step current next → ModelStep step failedAttempt (current, false) (next, false)
  | failure {state} : failedAttempt state → ModelStep step failedAttempt (state, false) (state, true)

inductive ModelRun (initial : State → Prop) (step : State → State → Prop)
    (failedAttempt : State → Prop) : Nat → (State × Bool) → Prop where
  | initial {state} : initial state → ModelRun initial step failedAttempt 0 (state, false)
  | append {n current next} : ModelRun initial step failedAttempt n current →
      ModelStep step failedAttempt current next → ModelRun initial step failedAttempt (n + 1) next

theorem modelStep_after_failure (step : State → State → Prop) (failedAttempt : State → Prop)
    {state next} (event : ModelStep step failedAttempt (state, true) next) : next = (state, true) := by
  cases event
  rfl

theorem modelRun_append_idle (initial : State → Prop) (step : State → State → Prop)
    (failedAttempt : State → Prop) {n state failed}
    (run : ModelRun initial step failedAttempt n (state, failed)) :
    ModelRun initial step failedAttempt (n + 1) (state, failed) :=
  .append run (.idle state failed)

theorem modelRun_state_reachable (initial : State → Prop) (step : State → State → Prop)
    (failedAttempt : State → Prop) {n outcome} (run : ModelRun initial step failedAttempt n outcome) :
    StateReachable initial step outcome.1 := by
  induction run with
  | initial h => exact .initial h
  | append _ event ih =>
    cases event with
    | idle _ _ => exact ih
    | success h => exact .advance ih h
    | failure _ => exact ih

theorem modelRun_safety (initial : State → Prop) (step : State → State → Prop)
    (failedAttempt invariant : State → Prop)
    (starts : ∀ state, initial state → invariant state)
    (preserves : ∀ current next, invariant current → step current next → invariant next)
    (excludesFailure : ∀ state, invariant state → ¬ failedAttempt state)
    {n outcome} (run : ModelRun initial step failedAttempt n outcome) :
    invariant outcome.1 ∧ outcome.2 = false := by
  induction run with
  | initial h => exact ⟨starts _ h, rfl⟩
  | append _ event ih =>
    cases event with
    | idle _ _ => exact ih
    | success h => exact ⟨preserves _ _ ih.1 h, rfl⟩
    | failure h => exact False.elim (excludesFailure _ ih.1 h)

theorem reachable_has_modelRun (initial : State → Prop) (step : State → State → Prop)
    (failedAttempt : State → Prop) {state} (reachable : StateReachable initial step state) :
    ∃ n, ModelRun initial step failedAttempt n (state, false) := by
  induction reachable with
  | initial h => exact ⟨0, .initial h⟩
  | advance _ hstep ih =>
    obtain ⟨n, run⟩ := ih
    exact ⟨n + 1, .append run (.success hstep)⟩

/- A mathematical source-handler refinement rule. The handler is a total typed
   function with named returned/raised outcomes. The BL extraction and symbolic
   interpretation must still establish the two universal simulation premises;
   testing concrete runs does not discharge them for every input. -/
inductive HandlerStep {τ : Ty} {Message : Type} (handle : Value τ → Message → Outcome τ) :
    (Value τ × Bool) → (Value τ × Bool) → Prop where
  | idle (state : Value τ) (failed : Bool) : HandlerStep handle (state, failed) (state, failed)
  | success {state next} (message : Message) : handle state message = .returned next →
      HandlerStep handle (state, false) (next, false)
  | failure {state} (message : Message) (reason : String) : handle state message = .raised reason →
      HandlerStep handle (state, false) (state, true)

inductive HandlerRun {τ : Ty} {Message : Type} (initial : Value τ → Prop)
    (handle : Value τ → Message → Outcome τ) : Nat → (Value τ × Bool) → Prop where
  | initial {state} : initial state → HandlerRun initial handle 0 (state, false)
  | append {n current next} : HandlerRun initial handle n current →
      HandlerStep handle current next → HandlerRun initial handle (n + 1) next

theorem handlerStep_after_failure {τ : Ty} {Message : Type}
    (handle : Value τ → Message → Outcome τ) {state next}
    (event : HandlerStep handle (state, true) next) : next = (state, true) := by
  cases event
  rfl

theorem handlerStep_refines_modelStep {τ : Ty} {Message : Type}
    (handle : Value τ → Message → Outcome τ)
    (step : Value τ → Value τ → Prop) (failedAttempt : Value τ → Prop)
    (returns : ∀ state message next, handle state message = .returned next → step state next)
    (raises : ∀ state message reason, handle state message = .raised reason → failedAttempt state)
    {current next} (event : HandlerStep handle current next) : ModelStep step failedAttempt current next := by
  cases event with
  | idle state failed => exact .idle state failed
  | success message h => exact .success (returns _ message _ h)
  | failure message reason h => exact .failure (raises _ message reason h)

theorem handlerRun_refines_modelRun {τ : Ty} {Message : Type}
    (handle : Value τ → Message → Outcome τ)
    (initial : Value τ → Prop) (step : Value τ → Value τ → Prop) (failedAttempt : Value τ → Prop)
    (returns : ∀ state message next, handle state message = .returned next → step state next)
    (raises : ∀ state message reason, handle state message = .raised reason → failedAttempt state)
    {n outcome} (run : HandlerRun initial handle n outcome) : ModelRun initial step failedAttempt n outcome := by
  induction run with
  | initial h => exact .initial h
  | append _ event ih => exact .append ih (handlerStep_refines_modelStep handle step failedAttempt returns raises event)

theorem handlerRun_safety {τ : Ty} {Message : Type}
    (handle : Value τ → Message → Outcome τ)
    (initial : Value τ → Prop) (step : Value τ → Value τ → Prop) (failedAttempt invariant : Value τ → Prop)
    (returns : ∀ state message next, handle state message = .returned next → step state next)
    (raises : ∀ state message reason, handle state message = .raised reason → failedAttempt state)
    (starts : ∀ state, initial state → invariant state)
    (preserves : ∀ current next, invariant current → step current next → invariant next)
    (excludesFailure : ∀ state, invariant state → ¬ failedAttempt state)
    {n outcome} (run : HandlerRun initial handle n outcome) : invariant outcome.1 ∧ outcome.2 = false :=
  modelRun_safety initial step failedAttempt invariant starts preserves excludesFailure
    (handlerRun_refines_modelRun handle initial step failedAttempt returns raises run)

#print axioms typed_total
#print axioms no_stuck_typed_outcome
#print axioms deterministic
#print axioms lexical_binding
#print axioms true_branch_only
#print axioms false_branch_only
#print axioms first_failure_wins
#print axioms sequence_failure
#print axioms quotient_zero_raises
#print axioms remainder_zero_raises
#print axioms modulus_zero_raises
#print axioms quotient_negative_divisor
#print axioms remainder_dividend_sign
#print axioms modulus_divisor_sign
#print axioms valueEq_true_iff
#print axioms product_returns_in_order
#print axioms product_first_failure
#print axioms product_second_failure
#print axioms projection_preserves_hidden_failure
#print axioms second_projection_preserves_first_failure
#print axioms present_field_evaluates_default
#print axioms projection_default_preserves_base_failure
#print axioms update_preserves_base_failure
#print axioms update_preserves_replacement_failure
#print axioms update_preserves_other_field
#print axioms second_update_preserves_other_field
#print axioms natural_rank_accessible
#print axioms natural_rank_wellFounded
#print axioms ranked_relation_wellFounded
#print axioms lexicographic_pair_rank_wellFounded
#print axioms integer_rank_wellFounded
#print axioms integer_pair_rank_wellFounded
#print axioms runLoop_equation
#print axioms runLoop_postcondition
#print axioms invariant_on_reachable
#print axioms no_failed_attempt_on_reachable
#print axioms invariant_on_every_trace_position
#print axioms modelStep_after_failure
#print axioms modelRun_append_idle
#print axioms modelRun_state_reachable
#print axioms modelRun_safety
#print axioms reachable_has_modelRun
#print axioms handlerStep_after_failure
#print axioms handlerStep_refines_modelStep
#print axioms handlerRun_refines_modelRun
#print axioms handlerRun_safety

end BeamLispCore
