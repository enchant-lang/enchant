import WordEnvelope
open FormalWordEnvelope

example : admittedWidth 0 4096 := by
  change (0 : Nat) < 0 ∧ 0 ≤ 4096
  decide
