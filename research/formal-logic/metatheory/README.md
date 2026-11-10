# A mechanically checked model, with an explicit bridge boundary

[Core.lean](Core.lean) defines an intrinsically typed mathematical Int/Bool
language, lexical environments and a structurally recursive evaluator with
returned values and named raised outcomes. It formalizes the reference profile's
selected branches, left-to-right failure behavior and signed integer division
profiles. Binary Boolean operations and sequencing represent folds of the
finite variadic forms. Lexical variables use typed indices.

The Lean model is a separate artifact. Its proofs are not proofs that the BL
type checker, reference interpreter, canonicalizer, symbolic lowering, compiler,
runtime or source elaborator implement that model correctly. Those bridges are
still reviewed implementations with scoped tests. No production compiler
authority follows from these theorems.

The evaluator's definition passes Lean's structural recursion checker. Its
totality and typed-outcome statements describe that total mathematical function;
the deterministic-outcome statement follows from functional evaluation. The
other results check selected evaluation laws, zero-divisor behavior, signed
division examples, and well-founded ranking rules. These are not an independent
small-step semantics equivalence proof. Lean's treatment of
[structural recursion](https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/)
and [inductive type recursors](https://lean-lang.org/doc/reference/latest/The-Type-System/Inductive-Types/)
explains how such model definitions enter its checked logic.

The generic ranking result establishes well-foundedness of a transition relation
when a ranking map decreases in a well-founded order. Scalar natural ranks and
lexicographic pairs are concrete instances. Each BL loop must still supply
checked obligations for its actual steps, invariant and nonnegative ranks;
proof of the rule does not supply its premises automatically.

Run the exact pinned tool under a memory and time cap:

```sh
research/formal-logic/metatheory/run \
  -o research/formal-logic/evidence/metatheory/Core.olean \
  research/formal-logic/metatheory/Core.lean
```

[tool-pin.json](tool-pin.json) pins Lean 4.34.1 and the Nix store artifact from
the repository's existing nixpkgs revision. The runner verifies the executable
hash. This separate proof tool does not replace or rebuild the pinned BL SDK.
The actual proof log and compiled artifact are retained in
`../evidence/metatheory/`; axiom reports are the tool's output, not hand-written
claims about an unchecked file.

The loop extension adds nonnegative integer scalar and pair ranking rules.
Their current proofs depend on `propext`, `Classical.choice` and `Quot.sound`
through the library's integer-to-natural comparison lemma. The initial eighteen
theorems retain their empty axiom audits. The twenty-theorem compiled artifact,
log and individual axiom lists are retained separately in `../evidence/loops/`;
the initial eighteen-theorem receipt remains historical evidence.
