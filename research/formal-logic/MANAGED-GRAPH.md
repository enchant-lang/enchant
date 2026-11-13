# Original terms inside the native owner

The managed graph source batch takes an original question graph and settings
into the process that owns the solver port. That process derives its own
question inventory, translates portable nodes to its private arena and replays
SAT assignments. Z3 and OxiZ receive the same language question and policy.

This is a candidate interface. The first immutable candidate passed 130
preceding evaluator assertions and 45 new admission-scope assertions, then
failed its native owner file. A `reset!` name collision selected the session
API after a native exchange, instead of updating the private state atom. The
corrected source uses an explicit atomic update and retires the context after
unexpected post-native errors. A replacement SDK is building; these owner
capabilities are not yet qualified or selected for the live project.

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

`formal.graph-question/with-numeric` derives the complete question inventory
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
The existing generic native decoder remains unchanged. Compatibility of the
new path, including actual Real replies and refusal behavior, is a runtime
qualification obligation rather than an assumed equivalence of decoders.

SAT replay includes retained assumptions and the actual counterexample. A
false assertion invalidates the point. Incomplete replay leaves SAT as a
candidate. Native observations never repair that decision. The first profile
admits Bool/Int/Real sorts; valid operations without a concrete policy can
still leave replay incomplete. Other value-family policies remain open.

Observation output currently retains original descriptor graphs, point root
values and separately labelled native wire data. Full semantic-value
materialization is explicitly deferred. This preserves the data needed for
the structured decoder without presenting a raw backend coordinate as a
checked language value.

## Keep the new result format explicit

The staged result uses `:formal/managed-graph-reply 1` and
`:bl/managed-numeric-graph-preview-v1`. It is separate from the existing
version-2 graph answer/effect interfaces. Integrating those higher layers,
their independent readers and durable records remains part of the work.

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
