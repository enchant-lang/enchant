# One SDK implementation of mathematical primitives

The shared-primitives candidate moves fresh typed graph admission, scalar
resource forecasts and graph point evaluation into the immutable SDK. Ordinary
`formal.evaluate/value` and graph evaluation call the same language-private
primitive dispatcher. The graph entry does not accept a caller's prepared
forest, checked-value marker, cached plan or counter as authority.

```clojure
(e/graph-values original-graph ordered-source-root-ids assignments
 {:profile e/direct-numeric-graph-profile
  :limits {:integer {:integer-bits 256}
           :rational {:component-bits 256 :intermediate-bits 512}
           :admission-work-units 1073741824
           :request-work-units 1073741824 :evaluated-nodes 4096}})
```

Every public query argument here is ordinary portable BL data. A separate
`with-graph-point` callback API is local implementation plumbing: only its
creating process can use its lookups, and they retire on return or failure.
Neither API returns native solver pointers or grants proof authority.

## Keep the policy version explicit

| Profile | Evaluation path | Derived-value policy |
| --- | --- | --- |
| `:bl/graph-point-evaluation-preview-v1` | Earlier shallow SDK child bindings | Structural admission only |
| `:bl/bounded-bool-int-point-preview-v1` | Earlier shallow child bindings | Integer forecasts and private request work |
| `:bl/bounded-numeric-point-preview-v1` | Earlier shallow child bindings | Separate rational admission and concrete numeric work, including child rechecks |
| `:bl/graph-point-evaluation-preview-v2` | Shared private SDK primitives; canonical rational literal reuse | Structural admission only |
| `:bl/bounded-numeric-point-preview-v2` | Shared private SDK primitives; canonical rational literal reuse | Separate admission and numeric work without redundant child rechecks |

The default graph profile is general v2. Select numeric v2 explicitly for
Bool/Int/Real derived-value forecasting. General profiles accept no resource
overrides; they do not promise bounds on concrete value growth. Unsupported
valid operators in strict numeric profiles remain incomplete before their
concrete arithmetic. The preceding profiles remain explicit comparison options.

The ordinary two-argument tree evaluator keeps its existing contract. ITE and
AND/OR retain selective demand; implication still evaluates both children and
retains its decisive cases. Other operations share the private dispatcher.
Graph values are memoized once per fresh scope. Leaves check supplied variable
coordinates through the SDK. A graph's Real literal can reuse canonical data
because the SDK itself freshly admitted that original literal in this operation.

## Account for the code that actually runs

Numeric v2 first reserves all literal normalizations, as the preceding numeric
profile does. Only complete fresh admission permits evaluation. Its arithmetic
forecast then uses the private checked child values without charging or running
shallow child-variable revalidation. The new rational planner charging profile
has its own identity; a ready plan still is not an admission token.

Actual candidate-SDK call controls observe three normalizer calls for the
small multiplication `1/3 * 2/5`, versus seven in numeric v1. Two calls admit
the distinct literals; the third normalizes the product. Direct ordinary tree
evaluation also makes three calls. A shared literal used twice needs one
admission and one product normalization in graph v2. Separate call-count
controls observe both engines entering the same private dispatcher.

The mathematical value stays `2/15`. The concrete evaluation charge is 872
units under numeric v2 versus 1,600 under numeric v1; both separately charge
364 units for literal admission. Consequently a request allowance of 872
admits the v2 calculation and leaves v1 incomplete. Their original graph and
assignment references agree; their profile/settings and evaluation references
differ. This is an explicit execution-policy change, not a changed theorem.

`primitive-applications` counts direct private dispatcher entries;
`literal-reuses` counts freshly admitted Real literals reused as concrete
values; `assignment-checks` counts demanded variable checks. `sdk-calls`
retains the earlier recursive-value delegation counter. These counts do not
establish a wall-clock speed advantage or a universal cost/heap theorem.

## Language privacy and native interop are different boundaries

The candidate's SDK declarations mark `primitive-value` private. Both a
qualified language value fetch and a qualified language call are refused with
`is not public`. The SDK's native BEAM namespace shim nevertheless exports a
bridge for that function. The first test incorrectly equated `defn-` with
absence of a BEAM export; that failed assertion and its actual trace remain
under `evidence/shared-primitives/before-native-export-assumption`.

Language privacy is therefore not VM isolation. Raw native interop is outside
that boundary and does not create checked evidence or execution authority.
The checked formal interfaces still freshly validate original terms/data and
do not accept a caller's fabricated result as an admitted forest or proof.
Full language/implementation and compiler preservation remain open.

## Qualification state and remaining integration

The candidate passes 130 SDK boundary assertions and the preceding 4,412
project assertions. Its packaged runtime binds 691 BL source files to the
managed build receipt, captured engine, assembly source and actual runtime.
Only the evaluator and three new SDK library files differ from the preceding
SDK. Compiler, dependencies, platform and backend worker artifacts are
identical. Fresh source preflight and its negative controls pass.

Wider regression, complete point corpora, fresh SDK-only readers and paired
native questions are separate gates in progress. The project keeps its
preceding qualified pin until those gates qualify the candidate. No managed
assertion replay, native retained-context promotion, additional backend theory
support or checked proof/kernel/compiler authority is claimed by these point
APIs. Other value-family policies and mechanized cost/implementation
correspondence remain open.

Sources: [SDK evaluator](/home/othman/code/undefine/beam-lisp--execution-protocol/priv/lib/formal/evaluate.bl),
[typed graph admission](/home/othman/code/undefine/beam-lisp--execution-protocol/priv/lib/formal/graph-terms.bl),
[SDK boundary controls](/home/othman/code/undefine/beam-lisp--execution-protocol/test/bl/formal/shared_evaluator_test.bl),
[candidate pin](evidence/shared-primitives/sdk-candidate.json) and
[actual SDK traces](evidence/shared-primitives/sdk-traces.json).
