import FloorModulus
open FormalFloorModulus

-- A totalized arithmetic value cannot erase the failed outcome.
example : outcome 7 0 = some (0, 0) := by rfl
