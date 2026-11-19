import Std

namespace StationWindow

structure Fact (Group : Type) where
  timestamp : Nat
  group : Group
  amount : Int

variable {Group : Type} [DecidableEq Group]

def contribution (cutoff : Nat) (group : Group) (fact : Fact Group) : Int :=
  if cutoff ≤ fact.timestamp ∧ fact.group = group then fact.amount else 0

def total (cutoff : Nat) (group : Group) (facts : List (Fact Group)) : Int :=
  (facts.map (contribution cutoff group)).sum

/- A committed change can move a fact between timestamps and groups. Each
   bucket checks both contributions against its own unchanged cutoff. -/
theorem committedReplacement (cutoff : Nat) (group : Group)
    (earlier suffix removed inserted : List (Fact Group)) :
    total cutoff group (earlier ++ inserted ++ suffix) =
      total cutoff group (earlier ++ removed ++ suffix) -
        total cutoff group removed + total cutoff group inserted := by
  simp only [total, List.map_append, List.sum_append]
  omega

def expiring (oldCutoff nextCutoff : Nat) (group : Group) (fact : Fact Group) : Int :=
  if fact.timestamp < nextCutoff then contribution oldCutoff group fact else 0

theorem expiryChangesOnlyCrossingFacts (oldCutoff nextCutoff : Nat)
    (ordered : oldCutoff ≤ nextCutoff) (group : Group) (facts : List (Fact Group)) :
    total nextCutoff group facts =
      total oldCutoff group facts - (facts.map (expiring oldCutoff nextCutoff group)).sum := by
  induction facts with
  | nil => simp [total]
  | cons fact tail ih =>
    simp only [total, List.map_cons, List.sum_cons] at ih ⊢
    by_cases remains : nextCutoff ≤ fact.timestamp
    · have included := Nat.le_trans ordered remains
      have notExpired := Nat.not_lt.mpr remains
      simp only [contribution, expiring, included, remains, notExpired, true_and, ite_false]
      rw [ih]
      omega
    · have expired := Nat.lt_of_not_ge remains
      simp only [contribution, expiring, remains, expired, false_and, ite_false, ite_true]
      rw [ih]
      omega

/- The membership boundary is inclusive. A row precisely at the new
   cutoff must not appear in the expiry batch. -/
theorem stillVisibleAtCutoff (oldCutoff : Nat) (group : Group) (fact : Fact Group) :
    expiring oldCutoff fact.timestamp group fact = 0 := by
  simp [expiring]

#print axioms committedReplacement
#print axioms expiryChangesOnlyCrossingFacts
#print axioms stillVisibleAtCutoff

end StationWindow
