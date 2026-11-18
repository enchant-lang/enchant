import Std

namespace LiveReceive

-- Ordinary FIFO mailbox, pure tag matcher. Preserve the unmatched prefix.
def pick (accept : α → Bool) : List α → Option (α × List α)
  | [] => none
  | x :: xs =>
      if accept x then some (x, xs)
      else (pick accept xs).map fun (value, rest) => (value, x :: rest)

-- A useful sufficient condition for *this* scan, even if versions differ
-- on messages absent from this snapshot.
theorem same_scan (p q : α → Bool) (xs : List α)
    (agree : ∀ x ∈ xs, p x = q x) : pick p xs = pick q xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
    have head := agree x (List.mem_cons_self ..)
    have tail := ih (fun m hm => agree m (List.mem_cons_of_mem x hm))
    simp only [pick, head, tail]

-- If an update promises identical selection for every possible mailbox,
-- singleton mailboxes force the two matchers to agree everywhere.
theorem all_scans_iff (p q : α → Bool) :
    (∀ xs, pick p xs = pick q xs) ↔ ∀ x, p x = q x := by
  constructor
  · intro h x
    have single := h [x]
    cases hp : p x <;> cases hq : q x <;> simp_all [pick]
  · intro h xs
    exact same_scan p q xs (fun x _ => h x)

inductive Msg where | preview | cancel deriving DecidableEq, Repr
example : pick (· == Msg.cancel) [.preview, .cancel] = some (.cancel, [.preview]) := by decide
example : pick (fun _ => true) [Msg.preview, .cancel] = some (.preview, [.cancel]) := by decide

#print axioms same_scan
#print axioms all_scans_iff
end LiveReceive
