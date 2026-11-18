import Tiles

namespace FilmGrade

-- The deployed representation is exactly a 256-entry table, independently
-- observed from the ordinary generated Source export and the native export.
def exactGrade (xs : List Nat) : Bool :=
  xs.length == 256 && (xs.zipIdx.all fun pair => decide (CheckedTiles.BrightByte pair.2 pair.1))

theorem atIndex (xs : List Nat) (ok : exactGrade xs = true) (i : Nat) (h : i < xs.length) :
    CheckedTiles.BrightByte i xs[i] := by
  have all := (Bool.and_eq_true_iff.mp ok).2
  have member : (xs[i], i) ∈ xs.zipIdx := by simp [List.mem_zipIdx_iff_getElem, h]
  exact of_decide_eq_true ((List.all_eq_true.mp all) _ member)

end FilmGrade
