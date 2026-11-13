import FloorModulus
open FormalFloorModulus

-- The raw Euclidean remainder cannot replace BL floor modulus.
example : repairedMod 7 (-3) = (7 : Int) % (-3) := by rfl
