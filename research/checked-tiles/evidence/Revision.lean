import Std

namespace CheckedTiles

-- Human-owned application law. A color channel may brighten or stay unchanged.
def BrightByte (x result : Nat) : Prop := x ≤ result ∧ result < 256
instance (x result : Nat) : Decidable (BrightByte x result) :=
  inferInstanceAs (Decidable (x ≤ result ∧ result < 256))

-- For a nonempty row the last group is (extent - 1) / tile.
theorem launched (x extent tile : Nat) (valid : x < extent) :
    x / tile ≤ (extent - 1) / tile :=
  Nat.div_le_div_right (by omega)


-- Each thread that passes the bounds check writes the same channel as
-- the sequential image at that coordinate. x counts packed channels.
def tiledAt (f : Nat → Nat) (src : Nat → Nat → Nat) (tw th x y : Nat) :=
  f (src ((x / tw) * tw + x % tw) ((y / th) * th + y % th))

theorem stitch (f : Nat → Nat) (src : Nat → Nat → Nat) (tw th x y : Nat)
    : tiledAt f src tw th x y = f (src x y) := by
  simp [tiledAt, Nat.mul_comm, Nat.div_add_mod]

-- Quotient and remainder give a unique owner for every in-bounds channel.
theorem owner (x tile block lane : Nat) (h : 0 < tile) (inside : lane < tile)
    (address : x = block * tile + lane) :
    x / tile = block ∧ x % tile = lane := by
  subst x
  simp [Nat.add_div, Nat.add_mod, Nat.mod_eq_of_lt inside, Nat.div_eq_of_lt inside,
        Nat.mul_comm block tile, h, inside]

-- A block beyond the right or bottom edge produces no observable store.
def storeAt (width height x y : Nat) (value : Nat) : Option Nat :=
  if x < width ∧ y < height then some value else none

theorem clipped (w h x y v : Nat) (outside : w ≤ x ∨ h ≤ y) :
    storeAt w h x y v = none := by
  simp only [storeAt, ite_eq_right_iff]
  omega

end CheckedTiles

set_option maxRecDepth 10000
set_option maxHeartbeats 4000000
def f0 (x : Nat) : Nat := ((x + 255) / 2)
def f1 (x : Nat) : Nat := (f0 x)
def observed : List Nat := [127, 128, 128, 129, 129, 130, 130, 131, 131, 132, 132, 133, 133, 134, 134, 135, 135, 136, 136, 137, 137, 138, 138, 139, 139, 140, 140, 141, 141, 142, 142, 143, 143, 144, 144, 145, 145, 146, 146, 147, 147, 148, 148, 149, 149, 150, 150, 151, 151, 152, 152, 153, 153, 154, 154, 155, 155, 156, 156, 157, 157, 158, 158, 159, 159, 160, 160, 161, 161, 162, 162, 163, 163, 164, 164, 165, 165, 166, 166, 167, 167, 168, 168, 169, 169, 170, 170, 171, 171, 172, 172, 173, 173, 174, 174, 175, 175, 176, 176, 177, 177, 178, 178, 179, 179, 180, 180, 181, 181, 182, 182, 183, 183, 184, 184, 185, 185, 186, 186, 187, 187, 188, 188, 189, 189, 190, 190, 191, 191, 192, 192, 193, 193, 194, 194, 195, 195, 196, 196, 197, 197, 198, 198, 199, 199, 200, 200, 201, 201, 202, 202, 203, 203, 204, 204, 205, 205, 206, 206, 207, 207, 208, 208, 209, 209, 210, 210, 211, 211, 212, 212, 213, 213, 214, 214, 215, 215, 216, 216, 217, 217, 218, 218, 219, 219, 220, 220, 221, 221, 222, 222, 223, 223, 224, 224, 225, 225, 226, 226, 227, 227, 228, 228, 229, 229, 230, 230, 231, 231, 232, 232, 233, 233, 234, 234, 235, 235, 236, 236, 237, 237, 238, 238, 239, 239, 240, 240, 241, 241, 242, 242, 243, 243, 244, 244, 245, 245, 246, 246, 247, 247, 248, 248, 249, 249, 250, 250, 251, 251, 252, 252, 253, 253, 254, 254, 255]
theorem observed_agrees : (List.range 256).map f1 = observed := by decide
theorem channel_verdict : ∀ x : Fin 256, CheckedTiles.BrightByte x.val (f1 x.val) := by decide
#print axioms channel_verdict
#print axioms CheckedTiles.launched
#print axioms observed_agrees
#print axioms CheckedTiles.stitch
#print axioms CheckedTiles.owner
#print axioms CheckedTiles.clipped
