import CoreLoop

namespace ActorTrace
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop

structure Handler (state : BeamLispCore.Ty) where
  admitted : Value state → Inputs → Prop
  run : Value state → Inputs → Outcome state

abbrev Event (handlers : List (Handler state)) := Option (Fin handlers.length × Inputs)
abbrev Configuration (state : BeamLispCore.Ty) := Value state × Option String

/- A source handler is attempted only for admitted messages. A raise retains
   the previous state and its exact reason. Only an idle event can follow it. -/
inductive Step (handlers : List (Handler state)) :
    Configuration state → Event handlers → Configuration state → Prop where
  | idle (current : Configuration state) : Step handlers current none current
  | returned (index : Fin handlers.length) (message : Inputs)
      (admitted : handlers[index].admitted before message)
      (outcome : handlers[index].run before message = .returned after) :
      Step handlers (before, none) (some (index, message)) (after, none)
  | raised (index : Fin handlers.length) (message : Inputs)
      (admitted : handlers[index].admitted before message)
      (outcome : handlers[index].run before message = .raised reason) :
      Step handlers (before, none) (some (index, message)) (before, some reason)

inductive Trace (handlers : List (Handler state)) (initial : Value state → Prop) :
    List (Event handlers) → Configuration state → Prop where
  | start : initial first → Trace handlers initial [] (first, none)
  | append : Trace handlers initial events before → Step handlers before event after →
      Trace handlers initial (events ++ [event]) after

theorem after_failure (handlers : List (Handler state))
    {before : Value state} {reason : String} {event : Event handlers} {after : Configuration state}
    (transition : Step handlers (before, some reason) event after) :
    event = none ∧ after = (before, some reason) := by
  cases transition
  exact ⟨rfl, rfl⟩

def Safe (handler : Handler state) (invariant : Value state → Prop) : Prop :=
  ∀ before message, invariant before → handler.admitted before message →
    ∃ after, handler.run before message = .returned after ∧ invariant after

theorem trace_safe (handlers : List (Handler state)) (initial invariant : Value state → Prop)
    (starts : ∀ state, initial state → invariant state)
    (safe : ∀ handler ∈ handlers, Safe handler invariant)
    {events : List (Event handlers)} {outcome : Configuration state}
    (trace : Trace handlers initial events outcome) : invariant outcome.1 ∧ outcome.2 = none := by
  induction trace with
  | start h => exact ⟨starts _ h, rfl⟩
  | append earlier transition previous =>
    cases transition with
    | idle _ => exact previous
    | returned index message admitted returned =>
      have member := List.getElem_mem (l := handlers) index.isLt
      obtain ⟨next, observed, holds⟩ := safe _ member _ _ previous.1 admitted
      have same := Outcome.returned.inj (returned.symm.trans observed)
      exact ⟨same.symm ▸ holds, rfl⟩
    | raised index message admitted raised =>
      have member := List.getElem_mem (l := handlers) index.isLt
      obtain ⟨next, observed, _⟩ := safe _ member _ _ previous.1 admitted
      cases raised.symm.trans observed

structure StatePolicy (state : BeamLispCore.Ty) where
  slots : Layout state
  intCount : Nat
  boolCount : Nat
  init : Term .boolean
  inv : Term .boolean

def zeroInputs : Inputs := ⟨fun _ => 0, fun _ => false⟩

def holds (term : Term .boolean) (input : Inputs) : Prop :=
  term.eval input.ints input.bools = some true

def StatePolicy.initial (p : StatePolicy state) (value : Value state) : Prop :=
  holds p.init (p.slots.put value zeroInputs)

def StatePolicy.invariant (p : StatePolicy state) (value : Value state) : Prop :=
  holds p.inv (p.slots.put value zeroInputs)

def StatePolicy.erase (p : StatePolicy state) (input : Inputs) : Inputs :=
  ⟨fun i => if i < p.intCount then input.ints i else 0,
   fun i => if i < p.boolCount then input.bools i else false⟩

def StatePolicy.mask (p : StatePolicy state) : Replacement :=
  ⟨fun i => if i < p.intCount then .inputInt i else .int 0,
   fun i => if i < p.boolCount then .inputBool i else .bool false⟩

def StatePolicy.covered (p : StatePolicy state) : Prop :=
  ∀ value left right, p.erase (p.slots.put value left) = p.erase (p.slots.put value right)

private theorem mask_reads (p : StatePolicy state) (input : Inputs) : reads p.mask input (p.erase input) := by
  constructor <;> intro n
  · by_cases h : n < p.intCount <;> simp [StatePolicy.mask, StatePolicy.erase, Term.eval, h]
  · by_cases h : n < p.boolCount <;> simp [StatePolicy.mask, StatePolicy.erase, Term.eval, h]

theorem invariant_rebase (p : StatePolicy state) (covers : p.covered)
    (stateOnly : replace p.mask p.inv = p.inv) (value : Value state) (base : Inputs) :
    holds p.inv (p.slots.put value base) ↔ p.invariant value := by
  let input := p.slots.put value base
  let canonical := p.slots.put value zeroInputs
  have left := replacement_eval p.mask input (p.erase input) (mask_reads p input) p.inv
  have right := replacement_eval p.mask canonical (p.erase canonical) (mask_reads p canonical) p.inv
  rw [stateOnly] at left right
  rw [show p.erase input = p.erase canonical from covers value base zeroInputs] at left
  change p.inv.eval input.ints input.bools = some true ↔ p.inv.eval canonical.ints canonical.bools = some true
  rw [left, right]

def StatePolicy.initQuestion (p : StatePolicy state) : Question :=
  ⟨[.bool true, p.init], both (.bool true) p.inv⟩

def StatePolicy.handlerQuestion (p : StatePolicy state) (admission ok : Term .boolean)
    (payload : Payload state) : Question :=
  ⟨[.bool true, p.inv, admission],
    both (.bool true) (both ok (replace (p.slots.plug payload Replacement.identity) p.inv))⟩

def coreHandler (p : StatePolicy state) (body : Expr context state)
    (env : Inputs → Env context) (admission : Term .boolean) : Handler state :=
  ⟨fun state msg => holds admission (p.slots.put state msg),
   fun state msg => eval body (env (p.slots.put state msg))⟩

theorem checked_init (p : StatePolicy state) (checked : p.initQuestion.entails) :
    ∀ value, p.initial value → p.invariant value := by
  intro value starts
  let input := p.slots.put value zeroInputs
  have claim := checked input.ints input.bools (by
    intro t member
    simp only [StatePolicy.initQuestion, List.mem_cons, List.not_mem_nil, or_false] at member
    rcases member with a | b
    · subst t; rfl
    · subst t; exact starts)
  simpa [StatePolicy.initQuestion, both, Term.eval.eq_2, Term.eval.eq_16, StatePolicy.invariant, holds, input] using claim

theorem checked_handler (p : StatePolicy state) (covers : p.covered)
    (stateOnly : replace p.mask p.inv = p.inv)
    (body : Expr context state) (env : Inputs → Env context)
    (admission ok : Term .boolean) (payload : Payload state) (error : Term .integer)
    (errorCode : String → Int)
    (agreement : ∀ input, agrees (eval body (env input)) (ok.eval input.ints input.bools)
      (payload.eval input.ints input.bools) (error.eval input.ints input.bools) errorCode)
    (checked : (p.handlerQuestion admission ok payload).entails) :
    Safe (coreHandler p body env admission) p.invariant := by
  intro before msg invariant admitted
  let input := p.slots.put before msg
  have current : holds p.inv input := (invariant_rebase p covers stateOnly before msg).mpr invariant
  have claim := checked input.ints input.bools (by
    intro t member
    simp only [StatePolicy.handlerQuestion, List.mem_cons, List.not_mem_nil, or_false] at member
    rcases member with a | b | c
    · subst t; rfl
    · subst t; exact current
    · subst t; exact admitted)
  have bothHold : (all [ok, replace (p.slots.plug payload Replacement.identity) p.inv]).eval input.ints input.bools =
      some true := by
    simpa [StatePolicy.handlerQuestion, both, all, Term.eval.eq_2, Term.eval.eq_16] using claim
  have parts := (all_true_iff _ input).mp bothHold
  have returned := parts ok (by simp)
  have sound := agreement input
  cases result : eval body (env input) with
  | raised reason =>
    rw [result] at sound
    rw [((agrees_raised _ _ _ _ _).mp sound).1] at returned
    contradiction
  | returned next =>
    rw [result] at sound
    have value := ((agrees_returned _ _ _ _ _).mp sound).2.1
    have post := parts (replace (p.slots.plug payload Replacement.identity) p.inv) (by simp)
    rw [put_eval _ _ _ input value p.inv] at post
    exact ⟨next, result, (invariant_rebase p covers stateOnly next input).mp post⟩

#print axioms after_failure
#print axioms trace_safe
#print axioms invariant_rebase
#print axioms checked_init
#print axioms checked_handler
end ActorTrace
