# Select the needed values without admitting unrelated history

Lean 4.34.1 accepts seven general lemmas, five fixture theorems and four
rejected false proof sources. The exact sources, compiled modules, tool,
axiom reports and resource limits are retained in
[the qualification](evidence/graph-selection-model/qualification.json).
This is a separate extension of the qualified
[finite structural graph model](GRAPH-TABLE-MODEL.md).

The model walks the finite table and constructs optional values for selected
rows. A selected scalar needs an admitted interpretation. A selected container
needs all its children. An unselected row has no decoded value. The finite
sequencing operation handles every ordered slot, including both the key and
value of a map entry. A missing child refuses the container.

The readiness premise is explicit: every selected container's dependencies
must also be selected, and every selected scalar must decode to its original
modeled value. Under that premise, the partial fold equals the ordinary fold
on each selected node. Its value interpretation therefore equals the complete
original interpretation. Two ready selections, even with different admission
functions, agree on a node they both select.

The fixture is a vector containing the integer seven and an unfamiliar keyword
name. Selecting only seven succeeds and preserves the original value; the
unselected keyword has no decoded value. Selecting the complete vector fails
when the keyword is not admitted. This is a mathematical fixture, not a new
SDK export or an execution of BL's keyword conversion.

The four negative sources falsely claim a value of eight, materialization of
the unselected keyword, successful full materialization, and readiness of a
root-only mask whose children were omitted. All four are refused for the
intended proof-goal failures, with no compiled output. The audit rejects
unrelated import or syntax failures as evidence of those controls.

All twelve positive axiom reports use only `propext` and `Quot.sound` where
listed. There is no `sorryAx`, classical-choice dependency or native computation
axiom. An earlier automatic fixture proof used classical choice; it remains
retained but outside this stricter qualification. The explicit constructor
proof removes that dependency.

The next connection is concrete: prove that BL's dependency-selection algorithm
produces the required closed selection, then connect scalar admission and
container reconstruction. This model does not prove that algorithm, runtime
atom admission, collection equality, byte costs, capacity checks, canonical
encoding, hashing, typed binder interpretation or the BL implementation.
Its finite fold is total; that is not whole-language or compiler totality.
The native solver and compiler artifacts are unchanged by this mathematical
extension, and compiler authority remains false.

Sources: [the general model](metatheory/GraphSelection.lean),
[the fixture](metatheory/GraphSelectionExamples.lean),
[the capped qualification recipe](run-graph-selection-model.py), and
[the immutable model pin](metatheory/graph-selection-pin.json).

The focused [dossier presentation receipt](evidence/graph-selection-model/dossier-qualification.json)
records the current proof pane and unchanged executable cells separately from
the mathematical qualification.
