import ChoiceExtension
open FormalChoiceExtension

def binding : Binding := ⟨fun _ => false, fun _ => 7, fun _ => 0⟩
example : binding.holds [] 99 := by decide
