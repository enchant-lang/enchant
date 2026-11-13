# Reserve rational normalization as well as arithmetic

`formal.term-forest-evaluate/numeric-values` evaluates original public term
graphs under `:bl/bounded-numeric-point-preview-v1`. The profile admits Bool,
Int and exact Real term nodes. It retains separate original graph, assignment,
normalized settings and ordered evaluation references. It uses the qualified
immutable SDK for mathematical operations; neither solver participates.

```clojure
(point/numeric-values original-graph ordered-root-ids assignments
 {:integer {:integer-bits 256 :intermediate-bits 512 :work-units 1048576}
  :rational {:component-bits 256 :intermediate-bits 512 :work-units 1073741824}
  :admission-work-units 1073741824
  :request-work-units 1073741824 :evaluated-nodes 4096})
```

The preceding [Bool/Int profile](BOUNDED-POINT.md) remains separately available
with its existing policy and result shape. The general graph point evaluator
retains its preceding semantics. This is a project preview; it does not yet
install resource policy in ordinary SDK entry points or managed assertion replay.

## First decide whether the syntax can be admitted

Real literals are normalized during SDK constructor admission. Checking only
the eventual arithmetic would already be too late. Fresh numeric preparation
therefore inspects raw sort descriptors before constructors, decodes portable
components, then forecasts every reachable rational literal normalization.
Integer-pair shape is checked without GCD. Unknown sorts refuse the profile.

All literal reservations must fit before any constructor normalization runs.
Shared literal nodes reserve once. A failed reservation returns an admission
refusal with no typed forest, `:constructor-execution :not-run`, zero charged
normalization work and the reserved prefix as a separate diagnostic. It does
not grant permission to evaluate a partially admitted expression.

Successful preparation then invokes the SDK constructors and canonical/scope
checks, and reports the normalization work actually reserved for that complete
admission. Malformed syntax refuses the request. If canonicality itself cannot
be checked within the allowance, the outcome stays incomplete rather than
claiming either canonicality or invalidity.

This includes inactive branches. Their syntax still needs admission; they
spend no concrete evaluation work when demand never reaches them. An admission
refusal can therefore keep an entire root incomplete even when one branch
would have supplied a decisive Boolean after successful syntax admission.

## Then reserve actual demanded work

The actual scoped evaluator derives each plan from its private admitted node
and real child values. [The rational planner](src/formal/rational-preflight.bl)
reads integer magnitude widths and does not compute cross-products, GCDs or
the requested result. A returned ready map is diagnostic data, never an accepted
execution capability or caller-maintained account.

Before delegation, the owner checks component/input/result widths, temporary
widths, per-operation work and remaining request work. Converting a Real to Int
also checks the integer result allowance; embedding Int into Real checks the
rational component allowance. The operation reserves work before SDK execution.
Shared nodes spend once. Denied operations do not spend work they never ran.

The profile supports exact Real addition, subtraction, multiplication, division,
negation, equality, ordered comparisons, Int/Real conversions and integrality,
alongside the earlier supported Bool/Int operations. Unsupported valid operators
remain explicitly incomplete. Real division by zero retains the SDK's
unspecified-division unavailable value; a resource planner does not define it.

The planner includes the selected SDK's real execution paths. Subtraction
normalizes its negated right operand before addition. Arithmetic delegates
through shallow child variables, whose Real binding checks normalize again.
Those input checks are charged too. Equality compares already normalized
rational data; ordering forms the two cross-products. When an eager child walk
has already produced an unavailable value, the numeric evaluator can return
the SDK's first unavailable result without rechecking complete Real siblings.
Boolean implication retains its existing eager child demand and decisive cases.

`rational-primitive-calls` counts planned arithmetic/comparison/conversion
delegations. `rational-value-check-calls` counts planned literal/binding
delegations, not the number of internal GCD calls. `sdk-calls` counts actual
delegated value evaluations. The work forecast includes the additional SDK
input checks inside each rational primitive delegation.

## Make phase and meaning visible

The result carries `:admission`, `:phase`, per-root completion and separate
concrete resource accounting. An admission failure returns unavailable roots
with `:phase :admission`. After admission, resource refusal has
`:phase :evaluation`; a decisive Boolean can still complete its root, retaining
the refusal in diagnostics. Neither phase's refusal is false, UNSAT, a user
program exception, or a counterexample.

Canonicality checking of a supplied Real coordinate is itself concrete work.
A well-shaped but noncanonical pair is ill-sorted when the SDK finishes that
check. If its normalization allowance is exhausted first, it stays resource
incomplete. Cheap malformed wrappers, missing coordinates and explicitly
unavailable coordinates retain the SDK's existing outcomes.

All callbacks check the creating BEAM process and retire on return or failure.
The original graph is freshly checked inside the operation; prepared forests,
admission-refusal maps, plans and exported counts cannot authorize execution.
Assertion replay remains `:not-run`, native calls remain zero and compiler
proof authority stays false.

## These are explicit policy units

Integer work keeps the preceding bit-size convention. Rational normalization
charges `4 * (max(numerator-bits, denominator-bits) + 1)^3`; products charge the
product of operand widths, and sums allow a carry bit. Forecasts include
pre-normalization values, so cancellation does not erase their size or work.
These are conservative policy conventions, not measured CPU instructions,
heap bytes, wall time, or a mechanically established implementation bound.

The default rational per-operation, admission and request work allowances are
1,073,741,824 units. Rational component/intermediate widths default to
65,536/131,072 bits; integer settings keep their preceding defaults. Ordinary
graph node/depth/edge/expansion limits remain independent. Qualification still
uses whole-process memory/time caps. Text, sequences, arrays, FP admission and
aggregate value policies, actual managed-owner integration and a mechanized
cost/implementation correspondence remain open.

Implementation and checks: [rational planner](src/formal/rational-preflight.bl),
[fresh forest admission](src/formal/term-forest.bl),
[scoped evaluator](src/formal/term-forest-evaluate.bl),
[planner controls](test/rational_preflight_test.bl) and
[numeric point controls](test/numeric_point_test.bl).
