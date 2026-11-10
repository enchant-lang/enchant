import Terms

/- A constructive SAT facet over the same partial typed semantics as the
   entailment checker. A witness chooses total environments explicitly; each
   original assertion must evaluate to some true, never false or none. -/
namespace FormalWitness
open FormalTerms

abbrev Context := List (Term .boolean)

structure Witness where
  integers : List Int
  booleans : List Bool

def Witness.integerEnv (witness : Witness) (index : Nat) : Int :=
  witness.integers[index]?.getD 0
def Witness.booleanEnv (witness : Witness) (index : Nat) : Bool :=
  witness.booleans[index]?.getD false

def contextSatisfied (context : Context) (integers : Nat → Int) (booleans : Nat → Bool) : Prop :=
  ∀ assertion ∈ context, assertion.eval integers booleans = some true

def satisfiable (context : Context) : Prop :=
  ∃ integers booleans, contextSatisfied context integers booleans

def accepts (context : Context) (witness : Witness) : Bool :=
  context.all (fun assertion => decide (assertion.eval witness.integerEnv witness.booleanEnv = some true))

theorem checked_context_holds (context : Context) (witness : Witness)
    (accepted : accepts context witness = true) :
    contextSatisfied context witness.integerEnv witness.booleanEnv := by
  simpa [accepts, contextSatisfied] using accepted

theorem checked_witness_satisfiable (context : Context) (witness : Witness)
    (accepted : accepts context witness = true) : satisfiable context :=
  ⟨witness.integerEnv, witness.booleanEnv, checked_context_holds context witness accepted⟩

theorem empty_context_satisfiable : satisfiable [] :=
  ⟨fun _ => 0, fun _ => false, by simp [contextSatisfied]⟩

theorem false_context_unsatisfiable : ¬ satisfiable [.bool false] := by
  rintro ⟨integers, booleans, holds⟩
  have impossible := holds (.bool false) (by simp)
  simp [Term.eval] at impossible

#print axioms checked_context_holds
#print axioms checked_witness_satisfiable
#print axioms empty_context_satisfiable
#print axioms false_context_unsatisfiable
end FormalWitness
