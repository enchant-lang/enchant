import Std

namespace NativeMailbox

inductive Tree (α : Type) where
  | leaf (x : α)
  | node (x : α) (left right : Tree α)

def Tree.items : Tree α → List α
  | .leaf x => [x]
  | .node x l r => x :: (l.items ++ r.items)

-- A digit carries its cached weight. The proofs below concern sequence order.
abbrev Digits (α : Type) := List (Nat × Tree α)

def items : Digits α → List α
  | [] => []
  | (_, t) :: ds => t.items ++ items ds

def push (x : α) : Digits α → Digits α
  | (w, a) :: (v, b) :: rest =>
    if w = v then (2*w+1, .node x a b) :: rest
    else (1, .leaf x) :: (w, a) :: (v, b) :: rest
  | ds => (1, .leaf x) :: ds

theorem push_items (x : α) (ds : Digits α) : items (push x ds) = x :: items ds := by
  cases ds with
  | nil => rfl
  | cons a ds =>
    rcases a with ⟨w, a⟩
    cases ds with
    | nil => rfl
    | cons b rest =>
      rcases b with ⟨v, b⟩
      by_cases h : w = v <;> simp [push, h, items, Tree.items, List.append_assoc]

-- The native leaf test uses weight = 1. In a perfect tree with correct
-- weights, this selects exactly the leaf constructor.
inductive Sized : Nat → Tree α → Prop where
  | leaf (x : α) : Sized 1 (.leaf x)
  | node {w l r} (x : α) : Sized w l → Sized w r → Sized (2*w+1) (.node x l r)

theorem positive_weight (h : Sized w t) : 0 < w := by cases h <;> omega

def leafShape : Tree α → Bool
  | .leaf _ => true
  | .node .. => false

theorem leaf_test (h : Sized w t) : (w = 1) ↔ leafShape t = true := by
  cases h with
  | leaf => simp [leafShape]
  | node x l r => have := positive_weight l; simp [leafShape]; omega

def pop : Digits α → Option (α × Digits α)
  | [] => none
  | (_, .leaf x) :: rest => some (x, rest)
  | (w, .node x l r) :: rest => some (x, (w/2, l) :: (w/2, r) :: rest)

theorem pop_items (ds : Digits α) :
    (pop ds).map (fun (x, tail) => x :: items tail) =
      (items ds).head?.map (fun _ => items ds) := by
  cases ds with
  | nil => rfl
  | cons a ds =>
    rcases a with ⟨w, a⟩
    cases a <;> simp [pop, items, Tree.items, List.append_assoc]

def weighted : Digits α → Prop
  | [] => True
  | (w, t) :: rest => Sized w t ∧ weighted rest

theorem push_weighted (x : α) (ds : Digits α) (ok : weighted ds) :
    weighted (push x ds) := by
  cases ds with
  | nil => exact ⟨Sized.leaf x, trivial⟩
  | cons a ds =>
    rcases a with ⟨w,t⟩
    cases ds with
    | nil => exact ⟨Sized.leaf x, ok⟩
    | cons b rest =>
      rcases b with ⟨v,u⟩
      by_cases same : w = v
      · subst v
        exact (by simpa [push, weighted] using
          And.intro (Sized.node x ok.1 ok.2.1) ok.2.2)
      · simpa [push, same, weighted] using And.intro (Sized.leaf x) ok

theorem pop_weighted (ds tail : Digits α) (x : α) (ok : weighted ds)
    (step : pop ds = some (x, tail)) : weighted tail := by
  cases ds with
  | nil => simp [pop] at step
  | cons a rest =>
    rcases a with ⟨w,t⟩
    obtain ⟨weight, restOk⟩ := ok
    cases weight with
    | leaf y =>
      simp [pop] at step
      exact step.2 ▸ restOk
    | node y left right =>
      simp [pop] at step
      obtain ⟨_, rfl⟩ := step
      simpa [weighted] using And.intro left (And.intro right restOk)

-- Fuel is the number of live rear entries. It makes the model total.
def rotate : Nat → Digits α → Digits α → Digits α
  | 0, _, front => front
  | n+1, rear, front =>
    match pop rear with
    | none => front
    | some (x, tail) => rotate n tail (push x front)

theorem rotate_items (n : Nat) (rear front : Digits α) (len : (items rear).length = n) :
    items (rotate n rear front) = (items rear).reverse ++ items front := by
  induction n generalizing rear front with
  | zero =>
    have emp : items rear = [] := List.length_eq_zero_iff.mp len
    simp [rotate, emp]
  | succ n ih =>
    cases e : pop rear with
    | none =>
      cases rear with
      | nil => simp [items] at len
      | cons a ds => rcases a with ⟨w,t⟩; cases t <;> simp [pop] at e
    | some pair =>
      rcases pair with ⟨x, tail⟩
      have view := pop_items rear
      rw [e] at view
      cases q : items rear with
      | nil => simp [q] at len
      | cons y ys =>
        simp [q] at view
        obtain ⟨rfl, eqtail⟩ := view
        have smaller : (items tail).length = n := by simpa [q, ← eqtail] using len
        simp [rotate, e, ih tail (push x front) smaller, eqtail, push_items, List.append_assoc]

#print axioms push_items
#print axioms leaf_test
#print axioms pop_items
#print axioms push_weighted
#print axioms pop_weighted
#print axioms rotate_items
end NativeMailbox
