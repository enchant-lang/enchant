# A compiler check with its own arithmetic proof

The term migration is now on main and under checkpoint 39 SDK qualification.
The selected SDK remains checkpoint 38. The retained arithmetic probes use
the checkpoint 37 SDK, regardless of later selected SDKs.

The retained baseline records the preceding boundary: `size-lemma` returns
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

The new implementation replaces the ignored port argument with an options map.
`(linear/prove-bound 12 8 6)` requests portable evidence; adding an initial
`{:backend :z3}` or `{:backend :oxiz}` requests a separate native comparison.
`:holds` depends on the positive portable certificates, constructed feasible
premises and checked double-placement counterexamples. Native unknown or an
unchecked positive label cannot decide it. The admitted family is explicitly
nonempty, with maximum arity one through eight; `size-lemma` separately supports
arity zero, where there is no child to duplicate. Runtime qualification is
still pending, and compiler proof authority remains false.

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

The controlled comparison now retains eighteen cases: arities zero through
two, single and double placement, and original, affine and repeated-addition
forms. All 162 component equivalences have checked certificates. Z3 settles
every case. OxiZ settles the affine and addition forms, including the concrete
double-placement refutations that were unknown in the original form. Arity zero
has no child to duplicate and retains the bound in every form.

This makes checked query preparation a useful language capability. An explicit
plan should retain its original question, executed question and independently
checked connection. No backend silently changes the public mathematical
meaning. SAT responses need replay against the original question and original
observations; native UNSAT remains an unchecked claim. The small probe does
not prove a general normalizer or qualify an implicit rewrite of live retained
contexts. [PREPARATION.md](PREPARATION.md) records the next interface design.
