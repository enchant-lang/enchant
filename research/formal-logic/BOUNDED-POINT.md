# Bound concrete integer work before running it

`formal.term-forest-evaluate/bounded-values` adds an explicit Bool/Int graph
point profile, `:bl/bounded-bool-int-point-preview-v1`. It takes the original
public data graph, ordered source root IDs, portable assignment map and resource
overrides. It freshly admits the graph; a prepared forest, ready planner result
or exported counter map is never accepted as authority.

```clojure
(point/bounded-values original-graph root-ids assignments
 {:integer {:integer-bits 256 :intermediate-bits 512 :work-units 65536}
  :request-work-units 131072 :evaluated-nodes 4096})
```

This is a project preview on the qualified immutable SDK. The general
`values` / `with-point` profile keeps its previous mathematics and result shape.
Both profiles, and the scoped graph reader, now check their creating BEAM
process before invoking a callback or changing private counters. Callbacks
retire on return or failure. These local closures are implementation plumbing,
not portable language terms or a managed native lease.

## Admission and execution are different

The bounded profile inspects the raw sort descriptor of every reachable term
node before SDK constructor admission. Only Bool and Int node sorts enter this
profile. Other sorts and malformed syntax refuse the request, including syntax
in inactive branches. Existing graph node, depth, edge and expansion limits
still apply. No FP or container literal is constructed to discover that its
evaluation policy is unsupported.

Concrete evaluation remains demand driven. ITE visits its condition and chosen
branch. AND/OR stop at a decisive Boolean, retain the SDK's last unavailable
value otherwise, and can complete after a previous child was refused. Implication
keeps the SDK's eager child demand and decisive false-antecedent/true-consequent
rules. Supported scalar primitives delegate their actual mathematical operation
to the selected SDK using private shallow terms. The project does not implement
a second integer arithmetic engine.

Bool/Int literals and variables, ITE, AND, OR, NOT, implication, XOR, equality,
integer addition/subtraction/multiplication/negation/division/modulo and ordered
integer comparisons have policies. Other admitted operations, including
distinct, quantifiers and uninterpreted application, return explicit
`:resource-policy-unsupported` incompleteness before evaluating their children.
They never fall through to an unmetered primitive.

## Reserve first; charge performed work once

The actual scoped evaluator owns its memo and accounting. It derives an
integer forecast from the admitted node and its actual private child values,
using [the integer planner](INTEGER-PREFLIGHT.md). It checks input/result width,
temporary width, per-operation work and remaining request work before invoking
the SDK primitive. Existing integer literals and variable values are width
checked before SDK value checking.

The defaults are 65,536 integer bits, 131,072 intermediate bits, 1,048,576
integer work units per operation and per request, and 16,384 evaluated nodes.
Each newly entered node reserves one node visit before its children run.
Integer work uses the planner's explicit bit-size convention; Boolean work is
covered by node visits and the existing graph admission limits. `sdk-calls`
counts delegated value evaluations; `integer-primitive-calls` counts admitted
integer operations, including an executed division by zero that returns the
SDK's mathematical unavailable value.

Shared nodes spend once, including when several roots request the same node.
A denied arithmetic operation spends no arithmetic work. A smaller later root
can therefore still fit. Entered nodes and already performed child work remain
charged. Refused values are memoized for the request. Ordered roots matter for
cumulative admission, and the evaluation identity binds that order.

A resource refusal is an unavailable value containing `:resource-incomplete`,
the profile, local typed node ID and an explicit reason. It never means false,
UNSAT, an exception in the user's program or a counterexample. Resource
refusals and root completion are separate: `AND(refused, false)` completes as
false, with its refusal retained in diagnostics. Ordinary SDK incompleteness,
such as missing assignments or division by zero, remains ordinary
incompleteness rather than a fabricated resource refusal.

## Identity and evidence

Results carry separate `:data-reference`, `:assignment-reference` and
`:settings-reference` fields. Settings normalize defaults before hashing;
equivalent overrides have the same identity. `:evaluation-reference` additionally
binds the profile and ordered source roots. `:root-statuses` reports each root,
while `:status` reports whether every requested root completed. `:resources`
retains private accounting as diagnostic data. Altering any exported map cannot
authorize another operation.

The point preview does not replay assertions, ask either solver for a verdict,
create a certificate, or grant compiler authority. Values remain term-based and
backend independent. Actual managed-owner admission, retained assumptions and
revision checks are a later integration gate.

These limits are an implementation policy, not a proof of CPU, heap, wall-clock
cost or universal totality. Graph checking, hashing, constructor admission and
the cost of the forecasting machinery have their own costs. A separate
[numeric preview](NUMERIC-POINT.md) now adds rational admission and concrete
work policies. Text, sequences, arrays, FP format admission and aggregate value
budgets still need policies. Whole-process memory/time caps remain part of qualification. A
mechanized correspondence between the cost model and actual BL implementation
is still open.
