# One portable request, either native backend

This interface is implemented in candidate SDK4 and passes its focused tests.
The full qualification chain is still running; the live project continues to
select its preceding qualified SDK. This is not a compiler or totality proof.

A request contains an original question graph, a normalized execution policy
and requested adapter settings. Backend choice does not change the subject.
A request reference includes policy and adapter settings; the subject reference
continues to identify the complete original mathematical question.

```clojure
(def x (t/variable "example.x" t/Int))
(def subject
 (qg/prepare (q/sat {:assumptions [(t/eq x (t/int 7))]
                      :observe {"next" (t/add x (t/int 1))}})))
(def request
 (logic/prepare-request subject
  {:adapter {:backend :oxiz :solver-ms 500 :hard-ms 2000}}))
(def result (logic/execute-request request))
(logic/compare-request request)
```

The default numeric policy admits Bool/Int/Real terms and canonical rational
coordinates. Operators without a concrete interpretation leave point replay
incomplete. Other sorts refuse admission before native scope calls. This does
not remove the existing broader typed theory interfaces or their declared
profiles; wider privately metered value policies remain implementation work.

For already saved flat graph data, `logic/request-from-graph` (also
`formal.request/from-graph`) builds the request without opening a materialized
question view. It does not load application code or create input atoms.

## Observations point back into the original graph

The inventory traverses map values in canonical graph-row order. Outer labels
and nested payload keys are not reconstructed as host maps merely to find
terms. An observation row carries `label-source`, `descriptor-source` and its
evaluated original source roots. Those integers are data locations in the
complete question graph, not native arena IDs or live capabilities.

```clojure
(def row (first (get-in result [:point-check :observations])))
(def label-data
 (graph/subgraph (get-in request [:subject :graph]) (:label-source row)))
```

The caller can inspect that graph without materializing its key. Explicit
`graph/decode!` retains the safe existing-atom and runtime-cardinality rules.
A refusal to materialize a key does not discard its original data. Descriptor
materialization and compound-value expansion policies remain deferred.

Numeric coordinates use the same rule: names are string fields, and supported
numeric encodings are read without decoding arbitrary application data.
Unavailable reasons and invalid encodings retain point-graph cursors. The
original point reference remains separate from the privately interpreted
binding reference. Reading a Real encoding never performs an unmetered GCD;
canonicality and arithmetic belong to the metered checker.

## Handlers can supply a point or delegate once

The interface uses the existing oracle effect's explicit `:request` method.
An installed table missing that method refuses before a worker opens. Existing
oracle deny scopes therefore also cover these requests.

```clojure
(logic/with-request-handler
 (fn [request fallback]
  (logic/answer-request request {"example.x" 7}))
 #(logic/execute-request request))
```

A handler can call `fallback` instead. That callback belongs to its creating
process, can be used once, and expires on return. It opens a fresh owner only
when called. Native session handles never enter the portable request.

Every supplied answer is freshly checked. It cannot carry a caller verdict,
validation result, trusted bit or checked-certificate upgrade. Local delegation
reports whether the returned body exactly matches the actual fallback body.
Changed coordinates lose that matching provenance and are checked on their
own merits. Stored delegation or artifact labels do not authenticate execution.

The native owner and fresh reader share the SDK's evaluator and report
aggregation in separate scopes. Their replay is independent of the native SMT
claim and saved validation labels; it is not a separate verified implementation
of the SDK. `owner-ms` bounds the owner operation. Arbitrary handler code and
fresh rechecking have distinct scopes and accounts.

## Evidence is useful without turning into a proof label

A valid point can witness SAT or refute a claim under the stated SDK policy.
A false assertion or malformed supplied coordinate produces `invalid-point`;
the binding and assertion diagnostics distinguish those causes. Missing or
resource-refused information can leave a candidate. A native UNSAT answer
remains `solver-claim`, with its separate reported conclusion and an unchecked
certificate. Backend agreement grants no additional authority.

`logic/recheck-request` consumes the original request and a closed answer.
Coordinates and native diagnostics remain graph data until their specific
interpretation is needed. It performs no native query.

## The ledger stores the request once

`formal.request-record/record!` uses the existing ledger's dedicated request
format. The complete request and a separate answer-body graph live in its blob
tier. The small index carries subject/request references and explicit point
presence, avoiding complete questions in index keys.

```clojure
(def id (request-record/record! connection request (:response result)
          {:claim "An original request and its proposed point"}))
(request-record/reopen connection id)
```

Reopening verifies actual payload/index binding and freshly rechecks the point.
Storage integrity, point validity and native execution remain distinct. The
older ledger formats stay readable under their own declared formats.

The serial qualification includes the full native corpora, two SDK-only point
readers, two fresh persisted-ledger readers, unchanged worker deadlines, absent
application-key atoms, zero query/exchange counts in readers, changed-point
checks, assurance tampering and actual request-index corruption. Consult
[evidence/managed-graph/progress.json](evidence/managed-graph/progress.json) for
completed gates rather than treating this implementation guide as a receipt.
