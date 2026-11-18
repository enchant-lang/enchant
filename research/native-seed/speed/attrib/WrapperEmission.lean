import Std

namespace NativeWrapperEmission

abbrev Wrapper (α : Type) := List α × List α

def nested (terminal : List α) : List (Wrapper α) → List α
  | [] => terminal
  | (head, tail) :: rest => head ++ nested terminal rest ++ tail

def finish (heads tails : List (List α)) (terminal : List α) : List α :=
  (heads.reverse ++ terminal :: tails).flatten

def collect (terminal : List α) (heads tails : List (List α)) :
    List (Wrapper α) → List α
  | [] => finish heads tails terminal
  | (head, tail) :: rest => collect terminal (head :: heads) (tail :: tails) rest

theorem finish_step (heads tails : List (List α)) (head tail body : List α) :
    finish (head :: heads) (tail :: tails) body =
      finish heads tails (head ++ body ++ tail) := by
  simp [finish, List.append_assoc]

theorem collected_order (wrappers : List (Wrapper α)) (terminal : List α)
    (heads tails : List (List α)) :
    collect terminal heads tails wrappers = finish heads tails (nested terminal wrappers) := by
  induction wrappers generalizing heads tails with
  | nil => rfl
  | cons wrapper remaining ih =>
    rcases wrapper with ⟨head, tail⟩
    simp only [collect, nested]
    rw [ih]
    exact finish_step heads tails head tail (nested terminal remaining)

theorem flattened_bytes (wrappers : List (Wrapper α)) (terminal : List α) :
    collect terminal [] [] wrappers = nested terminal wrappers := by
  simpa [finish] using collected_order wrappers terminal [] []

-- Model a join as reading every byte supplied to it once. All wrapper
-- layers have the same total prefix and suffix length in this cost model.
def nestedWork (terminalBytes wrapperBytes : Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => nestedWork terminalBytes wrapperBytes n + (terminalBytes + (n + 1) * wrapperBytes)

theorem nested_work (terminalBytes wrapperBytes n : Nat) :
    2 * nestedWork terminalBytes wrapperBytes n =
      2 * n * terminalBytes + n * (n + 1) * wrapperBytes := by
  induction n with
  | zero => simp [nestedWork]
  | succ n ih =>
    rw [nestedWork, Nat.mul_add, ih]
    simp [Nat.add_mul, Nat.mul_add, Nat.add_assoc, Nat.add_left_comm,
      Nat.add_comm, Nat.mul_assoc, Nat.mul_comm]

def weighted (depth : Nat) : List Nat → Nat
  | [] => 0
  | size :: rest => depth * size + weighted (depth + 1) rest

theorem weighted_step (sizes : List Nat) (depth : Nat) :
    weighted (depth + 1) sizes = weighted depth sizes + sizes.sum := by
  induction sizes generalizing depth with
  | nil => simp [weighted]
  | cons size remaining ih =>
    simp only [weighted, List.sum_cons, Nat.add_mul, Nat.one_mul, ih]
    ac_rfl

def nestedVariableWork (terminalBytes : Nat) : List Nat → Nat
  | [] => 0
  | size :: rest =>
      terminalBytes + size + rest.sum + nestedVariableWork terminalBytes rest

-- Each wrapper's bytes are copied once per enclosing join, including its own.
-- The terminal's bytes are copied at every join.
theorem nested_weighted_work (sizes : List Nat) (terminalBytes : Nat) :
    nestedVariableWork terminalBytes sizes =
      sizes.length * terminalBytes + weighted 1 sizes := by
  induction sizes with
  | nil => simp [nestedVariableWork, weighted]
  | cons size remaining ih =>
    simp only [nestedVariableWork, ih, List.length_cons, weighted, Nat.add_mul, Nat.one_mul]
    rw [weighted_step remaining 1]
    ac_rfl

theorem output_bytes (terminal : List α) (wrappers : List (Wrapper α)) :
    (collect terminal [] [] wrappers).length =
      terminal.length + (wrappers.map (fun w => w.1.length + w.2.length)).sum := by
  rw [flattened_bytes]
  induction wrappers with
  | nil => simp [nested]
  | cons wrapper remaining ih =>
    rcases wrapper with ⟨head, tail⟩
    simp [nested, ih, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]

example : collect ([] : List Nat) [] [] [([1], [4]), ([2], [3])] ≠ [1, 2, 4, 3] := by
  decide

#print axioms flattened_bytes
#print axioms nested_work
#print axioms nested_weighted_work
#print axioms output_bytes

end NativeWrapperEmission
