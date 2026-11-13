# Original terms inside the native owner

The managed graph source batch takes an original question graph and settings
into the process that owns the solver port. That process derives its own
question inventory, translates portable nodes to its private arena and replays
SAT assignments. Z3 and OxiZ receive the same language question and policy.

This is a candidate interface. Candidate 1 exposed a `reset!` name collision
after a native exchange. Candidate 2 corrected the state update and retires
the port after unexpected post-native errors. It passed 14,520 targeted
assertion executions, the 187-question legacy paired corpus with no exact
baseline differences, and the complete managed corpus. All 94 numeric
questions matched legacy status, verdict, phase and validation status on both
engines. The other 93 questions were refused before any native scope call;
the explicit sessions had already completed their handshake.

A separate pure probe then exposed a policy gap missing from that corpus:
unused quantifier declarations can contain sorts absent from every expression
node's output sort. Bool/Int admitted unused Real, while numeric admitted FP
and Rounding. Each reached one app constructor. The source repair checks raw
binder declarations, including list representations, before any constructor.
Generic theory admission still permits these valid sorts. Candidate 2 and its
actual reproducer are retained under [candidate-2](evidence/managed-graph/candidate-2/candidate-review.json).
Candidate 3 repaired the declared-sort gate and passed 15,674 assertions and
both native corpora. Its first fresh SDK-only reader then found a separate
application-key materialization gap, reproduced by graph-only unknown outer
and nested keys. It remains unpromoted. The [graph-key repair design](GRAPH-KEYS-PLAN.md)
keeps keys as data without creating atoms or importing application Source.
Candidate 4 implements that repair and the common language request API in one
immutable SDK containing 700 BL sources. It has passed namespace preflight and
15,853 targeted assertion executions, including actual owner, unknown-key,
request, oracle and ledger controls. Its legacy native corpus has completed
all 187 questions and 374 backend rows with no exact comparison differences
from the qualified baseline. The managed corpus and fresh persisted readers
are still in qualification. The live project still selects the
qualified shared-primitives SDK. See the [request interface](REQUEST-INTERFACE.md)
for the higher language surface; this document describes the owner primitive.

```clojure
(backend/with-session {:backend :oxiz :solver-ms 500 :hard-ms 2000}
 (fn [session]
  (backend/graph-question! session original-question-graph
   {:owner-ms 30000
    :limits {:integer {:integer-bits 256}
             :rational {:component-bits 256 :intermediate-bits 512}
             :admission-work-units 1073741824
             :request-work-units 1073741824 :evaluated-nodes 4096}})))
```

The query and settings are portable terms. The session and local callbacks are
ephemeral execution plumbing; they never become mathematical query fields.
A caller cannot submit an admitted forest, native IDs, a ready plan or a
validation boolean. The owner normalizes settings again and reads retained
assumptions from its actual state.

## Admit once, evaluate later

`formal.evaluate/with-graph-admission` checks original graph roots before model
coordinates are known. It supplies a diagnostic forest and a local
`with-point` callback. That callback captures the SDK's original admission;
editing the diagnostic forest cannot replace what it evaluates. Literal
admission belongs to the outer scope. Each point gets its own private work
account and memo. Both levels enforce their creating process and retire on
return or failure.

`formal.graph-question/with-numeric-keys` derives the complete question inventory
around that scope. Assertions, the claim, its exact negation, semantic
predicates and observation roots keep their original graph identity. Native
imports follow a dependency closure over admitted nodes. Their shallow
definitions use the same actual arena ID allocator as legacy imports; no
expanded term tree is needed as an interning key.

The graph retained-context format is explicit: `:bl/retained-graph-v1`. It
binds the retained assertion graph and generation. A pre-existing public
context, including explicit nil, stays inside it with a presence flag. This
does not silently replace the legacy tree digest with another kind of hash.

## Check assertions before interpreting the display

Binding checks distinguish a missing coordinate, an ill-sorted supplied value
and a value that could not be checked within policy. They cover the variables
of the actual assertions even when Boolean demand would skip a child. Missing
coordinates can remain irrelevant to a decisive assertion. Invalid supplied
coordinates invalidate the point; a resource-refused binding leaves it
incomplete. These checks share the point memo and its accounting.

Native Real wire components enter this boundary without an unmetered SDK GCD.
The numeric point checks their encoding and canonicality under its policy.
The existing generic native decoder remains unchanged. A focused fixture pins
the deliberate distinction: it normalizes wire `2/4`, while the new managed
profile rejects that noncanonical coordinate. Here `invalid-model` includes
an invalid coordinate encoding; it does not establish that the solver's
mathematical SAT claim is false. Binding diagnostics distinguish that failure
from a false assertion. Actual focused Z3/OxiZ replies provide canonical
`1/3` and `2/5`, with independently replayed product `2/15`. Broader native
compatibility and refusal behavior still need their own corpus gates.

SAT replay includes retained assumptions and the actual counterexample. A
false assertion invalidates the point. Incomplete replay leaves SAT as a
candidate. Native observations never repair that decision. The first profile
admits Bool/Int/Real sorts; valid operations without a concrete policy can
still leave replay incomplete. Other value-family policies remain open.

Observation output is an ordered vector of original source cursors, point root
values and separately labelled native wire data. `label-source` and
`descriptor-source` refer into the complete effective question graph. They are
not native IDs. No application key needs to become an atom or a host map key
merely to find and replay terms. Every map value is traversed in canonical
graph-row order, preserving entries with different original key kinds.

Full semantic-value materialization is explicitly deferred. This preserves
the original data without presenting a raw backend coordinate as a checked
language value. Point assignments and native diagnostics also remain graph
data; the shared coordinate reader interprets only its declared encodings.
Malformed coordinates and unavailable reasons keep original point-graph
cursors. Mathematical canonicality checks remain inside the metered evaluator.

## Keep the new result format explicit

The current candidate result uses `:formal/managed-graph-reply 2` and
`:bl/managed-numeric-graph-preview-v2`. Its new graph-key inventory is separate
from the retained value-key inventory profile. Earlier candidate records stay
under their original formats.

The new `formal.logic` request functions, explicit oracle `:request` method
and dedicated ledger payload are implemented on this owner primitive. The
higher request bridge currently uses fresh owners; retained-session request
integration remains open. Pure readers re-admit the original graphs and replay
points in fresh scopes, using the same SDK mathematics and report functions
as the owner. This is independence from native and saved claims, not a second
independently verified implementation.

| Field | What it describes |
| --- | --- |
| Request graph and reference | The caller's exact original question. |
| Effective question graph and reference | The question including actual retained assumptions. |
| Settings and reference | The normalized execution policy, separate from mathematical identity. |
| Admission account | Literal work performed once in the shared scope. |
| Validation | Original assertion replay at checked coordinates. |
| Observation descriptors and roots | Display data, with materialization state explicit. |
| Native scope attempts | Callback attempts, including a request refused before sending. |
| Native limits and artifact identity | Values held by the actual native owner. |

`owner-ms` is a distinct whole-operation budget, default 30 seconds and capped
at 60 seconds. It does not increase solver or worker deadlines. The owner
checks the remaining allowance before and after import preparation, reserving
enough time for a complete worker exchange. A caller that stops waiting retires
the owner. Unexpected errors after a native attempt retire its port, preventing
reuse of uncertain state.

The actual tests include both backends, mixed legacy/graph imports, corrupted
client mirrors, stale guards, raw-transport invalidation and a highly shared
question. Supplied-coordinate fixtures test model validation separately and
do not claim native execution. The retained first-candidate failure and source
pins are under [candidate-1](evidence/managed-graph/candidate-1/failure-review.json);
[progress](evidence/managed-graph/progress.json) identifies the current gates.

No solver certificate, checked kernel authority, universal cost/termination
bound, implementation correspondence or compiler preservation is established
by this interface. The [owner transaction plan](MANAGED-GRAPH-PLAN.md) retains
the broader qualification and integration requirements.
