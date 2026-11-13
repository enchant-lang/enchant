import TermFloorModulus
open FormalTerms FormalTermFloorModulus

example : (floorModTerm (.int 7) (.int 0)).eval (fun _ => 0) (fun _ => false) = some 0 := by rfl
