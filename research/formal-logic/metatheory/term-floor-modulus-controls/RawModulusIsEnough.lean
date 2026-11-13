import TermFloorModulus
open FormalTerms FormalTermFloorModulus

example : (floorModTerm (.int 7) (.int (-3))).eval (fun _ => 0) (fun _ => false) =
    (Term.mod (.int 7) (.int (-3))).eval (fun _ => 0) (fun _ => false) := by rfl
