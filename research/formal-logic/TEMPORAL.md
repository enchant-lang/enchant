# Time questions are language values

`formal.temporal` builds semantic integer spans, their relations and complete
portable questions. `datom.time` uses this interface for overlap and chronology
checks. Both backends receive the same typed terms through `formal.logic` and
the query method of the oracle effect. No temporal consumer constructs an
SMT-LIB script or opens a legacy solver port.

```beam-lisp
(ns appointment-check
 (:require [formal.temporal :as temporal] [datom.time :as time]))

;; An appointment lasts one tick and starts somewhere in [0,4].
(def appointment
 (temporal/shift (temporal/span 0 1)
                 (temporal/endpoint-range "appointment.start" 0 4)))
(def window (temporal/span 2 3))

(time/overlap-questions appointment window) ; two complete, inspectable questions
(time/overlap-result {:backend :z3} appointment window)
(time/overlap-result {:backend :oxiz} appointment window)
```

The two SAT questions ask for an intersecting assignment and a separated
assignment in the same admitted context. A positive answer must pass the common
independent replay before it establishes either possibility. The result retains
both questions, both answers, concrete endpoint observations and certificate
status. Native UNSAT answers remain unchecked claims; none grants compiler
proof authority.

| Intersection question | Separation question | Aggregate verdict |
| --- | --- | --- |
| Replayed SAT | UNSAT | `:certain` |
| UNSAT | Replayed SAT | `:impossible` |
| Replayed SAT | Replayed SAT | `:possible` |
| UNSAT | UNSAT | `:infeasible` |
| Incomplete, unavailable or failed evidence | Any unresolved counterpart | `:candidate`, `:unknown`, `:unsupported` or `:error` |

The aggregate reports an error if either side fails, then unsupported syntax,
then incomplete model evidence, then unknown. It does not infer certainty from
one undecided side. Two unchecked inconsistent reports can still claim an
infeasible domain; the certificate and authority fields retain that limitation.

## The interval model

Coordinates are unbounded mathematical integers. `span` admits `from <= to`;
`from = to` denotes an empty span. Reversed endpoints, an empty endpoint range,
or an unsuccessful/outside-domain operand leave no admitted assignment.
Endpoint ranges use inclusive limits. Their constraints survive `shift`,
`duration`, relation construction and observation decoding.
The value protocol retains input constraints separately from model admission
(`within`). The complete query asserts both; inspecting `within` alone does
not test whether an assignment satisfies every input range.

`intersects` tests positive-width intersection. Touching intervals and empty
spans do not intersect. `covers` tests inclusion of points, so every span covers
an empty span. `same-points` identifies empty spans at different coordinates.
`formal.value/equal` instead compares the endpoint data of span values.

`allen` constructs each of the thirteen Allen relations. Every relation carries
the positive-width premise for both operands. The concrete `datom.time/allen`
classifier raises for empty operands. The concrete overlap, disjointness,
containment, union and subtraction operations follow the empty-set laws.
The finite-grid check compares these operations with independently enumerated
integer point sets; it does not prove a language-wide correspondence theorem.

Span values use the ordinary `formal.value` protocol. Their predicates can
participate in `q/prove`, the portable certificate producer, the native engines,
handlers and the existing original-term proof export. Integer coordinates model
a common axis; timezone conversion, calendar/resolution record equality, EDTF
qualification flags and recurrence generation require their own interpretations.
A `#time"199X"` interval covers the whole decade. A single year chosen within
that decade is a different input, expressed by an endpoint range.

## Chronology

```beam-lisp
(def bounds {:history/war [1010 1019] :history/treaty [1010 1019]})
(def ordering [[:history/war :history/treaty]])
(time/chronology-question bounds ordering)
(time/consistency-result {:backend :oxiz} bounds ordering)
```

Bounds are inclusive integer start ranges; ordering is strict-before. Complete
portable event keys determine variable identities. Namespaced keywords, symbols
and strings remain distinct. Query construction orders keys canonically and
refuses undeclared edge endpoints, malformed ranges and nonportable keys.
The frontend admits at most 256 events and 2,048 ordering rows; these are input
capacities, not numerical bounds on theorem integers or execution guarantees.

`consistency-result` returns the common query result plus `:consistent` and
`:schedule`. Replayed SAT gives `true` and a schedule keyed by the original
events. UNSAT gives `false`. Other answers leave `:consistent` and `:schedule`
nil and retain their distinct verdict and diagnostic fields.

`consistent?` is a strict predicate: it returns a Boolean for a decisive result
and raises `:temporal-inconclusive` with the complete answer otherwise. This is
a preview API correction. Its first argument is a backend options map. The
ignored legacy port argument and truthy `{:consistent false}` return shape are
removed. Callers that need unresolved outcomes as data use `consistency-result`.

The API checks satisfiability of the declared order. It does not compute a
tightest-bound fixpoint, enumerate every schedule or authenticate the database
history from which a caller extracted its bounds and edges.

## Qualification

The immutable SDK passes 2,373 focused assertions across 14 files and 7,086
formal regression assertions across 22 files. The focused coverage uses the
initial 13 passing files and a targeted rerun of the corrected temporal test;
the first test-assumption failure is retained. All 187 preceding paired native
questions keep their exact identities and solver/verdict statuses. An SDK-only
program runs from an unrelated working directory, and a selected Source
function calls both temporal backends.

Three law certificates pass the portable checker and the pinned Lean
original-term checker: intersection symmetry, preservation of duration under a
shift, and set equality of empty spans at different coordinates. These are
unbounded integer statements about their exact generated typed terms. Their
Lean dependencies are `propext` and `Quot.sound`; compiler proof authority
remains false. Connecting the temporal constructors and concrete BL operations
to those term statements remains reviewed implementation reasoning.

The first external symmetry check refused an incomplete connection proof. The
untrusted proof writer now simplifies Boolean connective permutations before
arithmetic closure. The original statements, normalized certificates, model
and acceptance gates are unchanged. Its regression accepts 17 original-term
proofs and rejects five altered originals across four tests. The initial
refusal, actual commands and exact sources are retained under
`evidence/temporal`; `qualification.json` binds the complete checkpoint.
