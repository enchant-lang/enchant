import Std

/- A mathematical model of the Int/Bool core. This formalizes the typed model,
   not the BL implementation, ANF elaborator, runtime or compiler bridge. -/
namespace BeamLispCore

inductive Ty where
  | int | bool
  deriving DecidableEq

abbrev Value : Ty → Type
  | .int => Int
  | .bool => Bool

instance (τ : Ty) : DecidableEq (Value τ) := by
  cases τ <;> exact inferInstance

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
#print axioms natural_rank_accessible
#print axioms natural_rank_wellFounded
#print axioms ranked_relation_wellFounded
#print axioms lexicographic_pair_rank_wellFounded

end BeamLispCore
