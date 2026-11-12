# A compiler check with its own arithmetic proof

Implementation exploration after checkpoint 37. `system.linear` has not yet
been migrated. The selected SDK remains checkpoint 37.

The retained baseline exposes the current boundary: `size-lemma` returns
SMT command forms, the typed query handler sees no question, and `prove-bound`
has no independently checked certificate or explicit model scope. The first
baseline attempt had an extra closing delimiter; only the corrected run counts
as evidence of these semantic failures.

The SDK-only prototype constructs a complete typed question about a declared
constructor recurrence. Every child has a nonnegative source size and emitted
size, with emitted size at most twelve times source size. Constructor overhead
lies between zero and eight. The proposed output size is overhead plus the
placed children; the source node contributes one plus its children's sizes.

BL's existing proof producer and independent certificate checker establish the
single-placement bound at every arity from zero through eight. Search needs
7, 13, …, 55 nodes. These are actual checked objects, rather than native UNSAT
labels. Both engines receive the same additional two questions at arity two.
Z3 reports the single-placement theorem and refutes double placement. OxiZ
0.3.4 returns unknown for both exact questions under the SDK's default settings.
This observation does not establish a general limitation of its integer theory.
The complete native answers are retained in `evidence/compiler-linearity`.

The next architectural split should be:

- A portable constructor-size model builds the complete questions and retains
  coefficient, arity, overhead and placement in its declared scope.
- A positive result carries a freshly checked integer certificate. A concrete
  double-placement counterexample carries explicit bindings checked against
  the original SAT question; constructed evidence keeps its own provenance.
- Optional native comparisons use the ordinary query effect. Unknown or
  untrusted native labels cannot grant or replace the checked result.
- `system.linear` connects these model results to its separate structural and
  emitted-artifact observations, retaining each one's coverage and limits.

The scope needs care. Bounded local overhead, affine child placement and the
chosen recursion measure are premises. Structural recursion alone does not
establish constant work per constructor, and macro expansion can change the
input size before code emission begins. A checked recurrence is therefore not
a whole-compiler complexity or preservation theorem. Compiler proof authority
remains false.

Before choosing a canonical question representation, compare factored,
distributed and addition-based affine terms on both engines, with independent
certificates connecting equivalent forms. This can distinguish native API
normalization behavior from the language's mathematical meaning. Keep the
original question and every observed unknown result.
