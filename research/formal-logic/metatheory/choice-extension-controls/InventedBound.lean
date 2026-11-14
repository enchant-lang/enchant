import ChoiceExtension
open FormalChoiceExtension

def binding : Binding := ⟨fun _ => true, fun _ => -1, fun _ => 0⟩
example : 0 ≤ binding.value [] := by decide
