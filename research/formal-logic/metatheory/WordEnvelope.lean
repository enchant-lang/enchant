import Std

/- Mathematical bounds for a future bounded word profile. These are not a
   theorem about BL primitives, allocation, CPU cost, the compiler or a solver. -/
namespace FormalWordEnvelope
set_option autoImplicit false

def capacity (width : Nat) : Nat := 2 ^ width
def wrap (width value : Nat) : Nat := value % capacity width
def admittedWidth (width limit : Nat) : Prop := 0 < width ∧ width ≤ limit

theorem capacity_positive (width : Nat) : 0 < capacity width :=
  Nat.two_pow_pos width

theorem wrapped_value_bound (width value : Nat) : wrap width value < capacity width :=
  Nat.mod_lt value (capacity_positive width)

theorem addition_temporary_bound (width a b : Nat)
    (ha : a < capacity width) (hb : b < capacity width) :
    a + b < capacity (width + 1) := by
  change a + b < 2 ^ (width + 1)
  rw [Nat.pow_add_one, Nat.mul_two]
  exact Nat.add_lt_add ha hb

theorem multiplication_temporary_bound (width a b : Nat)
    (ha : a < capacity width) (hb : b < capacity width) :
    a * b < capacity (width + width) := by
  change a * b < 2 ^ (width + width)
  rw [Nat.pow_add]
  exact Nat.lt_of_le_of_lt
    (Nat.mul_le_mul_left a (Nat.le_of_lt hb))
    (Nat.mul_lt_mul_of_pos_right ha (capacity_positive width))

theorem zero_width_refused (limit : Nat) : ¬ admittedWidth 0 limit := by
  intro h
  exact Nat.lt_irrefl 0 h.1

theorem wrapped_result_does_not_bound_temporary :
    wrap 2 (3 * 3) = 1 ∧ capacity 2 ≤ 3 * 3 := by
  constructor <;> decide

#print axioms capacity_positive
#print axioms wrapped_value_bound
#print axioms addition_temporary_bound
#print axioms multiplication_temporary_bound
#print axioms zero_width_refused
#print axioms wrapped_result_does_not_bound_temporary
end FormalWordEnvelope
