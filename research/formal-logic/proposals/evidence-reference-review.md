# Make evidence references cheap without changing what they bind

This review concerns the projected wide-owner batch, not a production performance
guarantee. Its [baseline trace](../evidence/wide-owner-prototype/reader-profile/qualification.json)
and [component trace](../evidence/wide-owner-prototype/reader-profile-components/qualification.json)
use one exact 27,291-byte, 1,257-node native candidate packet on the selected SDK.
The component trace initializes through one public reopen outside its five
measured windows. Both traces deny oracle methods; every measured window records
an actual integer zero for native transport calls.

The warmed reopen took about 15.1 seconds. Typed admission took 0.13 seconds;
answer rechecking took 1.14 seconds in the separate component run. Encoding the
whole evidence carrier took 3.67 seconds, and computing its reference took
4.49 seconds. These are serial, instrumented observations on this host and
namespace projection, not a backend benchmark or a physical cost theorem.

The current `formal.request-evidence/recheck` computes `(graph/of e)` twice:
once for `:evidence-reference`, again inside `:checking-reference`. Both calls
inspect the same immutable, already envelope-checked carrier. There is no need
for two separately reconstructed copies of that reference in one operation.

## First change: reuse one computed value

Compute the current full-data reference once in a local binding and use it in
both result fields. Preserve its exact algorithm, domain, bytes and profile.
Keep all request, answer, premise, proof and acceptance checks. Do not accept a
caller-supplied reference or cached ready/admission value.

This changes evaluation cost, not the public meaning of a reference. It does
not introduce a persistent cache, cross-request custody or new authority.
Qualification should compare the entire resulting identity fields against the
current full-data calculation, including old version-one and current version-two
candidate carriers. Record the prospective allowance and fresh-check behavior
unchanged. Measure the improvement rather than inferring it from call removal.

## A possible later format: commit to already checked graph references

The request reference already binds its original flat subject graph by that
graph's freshly checked reference. It avoids encoding the entire graph as an
ordinary nested data value again. An evidence reference could use the same idea:

```
format tag
carrier schema version and profile
complete request reference
complete subject reference
ordered roles present: answer / certificate / feasibility
freshly computed complete graph reference for every present role
```

The roles and presence bits are part of the commitment. A certificate graph in
the answer slot cannot have the same commitment as the same graph in its proper
slot. Omitting a role differs from including it. Every graph reference must be
computed from its complete checked graph, including native diagnostics; a
producer's claimed hash is not input authority. The original closed-envelope
and exact-request checks still apply.

This would intentionally change the reference algorithm. Give it a new explicit
reference profile and version the checking-result policy that uses it. Keep old
packet schemas readable and preserve the original request and subject identities.
Historical full-data references remain reconstructible through `graph/of`.
Do not silently label a new digest as the old full-data reference.

The commitment binds candidate data under the existing hash assumptions. It
authenticates no producer or execution, and proves nothing about the candidate's
mathematical content. It cannot replace point, certificate or premise checking.

Before implementing that later format, qualify changed-role and missing-role
controls, changed nested diagnostic data, old/new carriers, unchanged logical
and consumer conclusions, and fresh readers with no native access. A smaller
representation or faster digest must not enlarge a theory or strengthen a
claim. This format change remains proposed; the first local reuse is the next
implementation step.
