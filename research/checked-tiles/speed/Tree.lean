import Std

namespace SpeedTree

structure Poly where
  a : Nat
  b : Nat
  c : Nat

def value (p : Poly) (x : Nat) := p.a * x * x + p.b * x + p.c

def step (p : Poly) : Poly :=
  ⟨p.a + p.a, (p.a + p.a) + (p.b + p.b), (p.a + p.b) + (p.c + p.c)⟩

def walk : Nat → Poly → Nat → Nat
  | 0, p, x => value p x
  | d+1, p, x => walk d p x + walk d p (x+1)

def loop : Nat → Poly → Nat → Nat
  | 0, p, x => value p x
  | d+1, p, x => loop d (step p) x

theorem step_value (p : Poly) (x : Nat) :
    value (step p) x = value p x + value p (x+1) := by
  simp [value, step, Nat.add_mul, Nat.mul_add]
  omega

theorem step_walk (d : Nat) (p : Poly) (x : Nat) :
    walk d (step p) x = walk d p x + walk d p (x+1) := by
  induction d generalizing x with
  | zero => exact step_value p x
  | succ d ih => simp only [walk, ih]

theorem same (d : Nat) (p : Poly) (x : Nat) : loop d p x = walk d p x := by
  induction d generalizing p with
  | zero => rfl
  | succ d ih => simp only [loop, walk, ih, step_walk]

#print axioms same
end SpeedTree
