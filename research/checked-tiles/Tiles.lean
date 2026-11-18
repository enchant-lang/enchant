import Std

namespace CheckedTiles

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
