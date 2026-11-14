# A proof, usable premises, and permission to accept it

This is the common interface being integrated on main. The selected scalar SDK
is still the qualified baseline. The final canonical source projection passed
**1,714 assertions across 18 files**, including the SAT reporting fix and policy
namespace relocation. Its [qualification](../evidence/obligation-integration-prototype/all/qualification.json)
and [actual log](../evidence/obligation-integration-prototype/all/checks.txt) bind
those exact source bytes. The final cold packet rerun and new artifact gates are
pending. Earlier 284/501-assertion passes and the first four-packet/two-reader
pass are retained under their actual historical revisions.

A conditional theorem says that every assignment satisfying the premises also
satisfies the claim. An impossible premise can make that theorem true. A caller
asking for a useful contract therefore needs two independent facts:

1. The claim follows from these exact premises.
2. At least one assignment actually satisfies the premises.

The consumer policy determines what to do when the second fact is unavailable
or the premises are inconsistent. The interface retains every intermediate
result rather than hiding these distinctions in one Boolean.

| Checked conditional proof | Premises | allow | report | reject |
| --- | --- | --- | --- | --- |
| yes | witnessed | accepted | accepted | accepted |
| yes | inconsistent | accepted | reported | rejected |
| yes | not established | accepted | reported | incomplete |
| no | any | not established | not established | not established |

The table concerns accepting conditional entailment. A checked counterexample
remains a separate decisive result. Conflicting independently checked evidence
refuses acceptance. Native UNSAT
alone remains a solver claim, regardless of the selected consumer policy.
Missing policy defaults to report; explicit nil, strings, booleans and unknown
keywords refuse. All question readers preserve allow/report/reject exactly.

## Ordinary data at every portable boundary

A request binds the full original question graph, semantic policy and separate
backend/deadline settings. A certificate binds the full logical subject and its
semantic profile. Switching Z3/OxiZ keeps that mathematical statement and requires
a newly bound outer carrier. No callable, cached inventory, normalization result
or producer success flag is accepted as evidence.

```clojure
(let [r (request/prepare subject {:policy {:profile policy/numeric-word}})
      candidate (finite/candidate r)
      bundle (evidence/propose r
               {:certificate candidate
                :feasibility {:strategy :finite}})
      fresh (evidence/recheck r bundle)]
  {:logical (:logical-conclusion fresh)
   :premises (:feasibility-check fresh)
   :policy (:policy-check fresh)
   :conclusion (:conclusion fresh)})
```

`:proof-check` and `:logical-conclusion` preserve the conditional argument.
`:feasibility-check` reports witnessed/inconsistent/not-established premises.
`:conclusion` applies the original consumer policy and reports its fresh premise
fact. A SAT witness or counterexample is separately checked by point replay.
Premise evidence alone does not establish the original claim.

The finite strategy derives its own domain from the original admitted terms:
at most five combined Boolean/word variable bits, 32 valuations, 64 typed nodes
and word widths up to 16. It does not enumerate unbounded integers or strings.

The integer strategy checks a finite Boolean split/positive weighted linear
combination DAG. Integers retain their unbounded mathematical meaning. The
certificate representation is bounded: 128-bit coefficients, 256 typed nodes,
32 arithmetic/Boolean atoms, 1,024 proof nodes, depth 32 and 2,048 proof contexts.
Affine arithmetic and constant multiplication are supported. General nonlinear
arithmetic, integer choices, division/modulus, Real and String proofs remain
outside this installed strategy.

Integer premise evidence can supply a point and/or a contradiction certificate:

```clojure
{:strategy :supplied-integer
 :point {"input.x" 0}
 :certificate candidate-for-the-derived-background}
```

Either evidence slot may be omitted. The background is freshly derived by
changing only mode/claim/counterexample. The complete assertion graph must stay
byte-identical. Observations, provenance, scope and retained assumptions remain
bound. The main theorem's certificate cannot substitute for a certificate of
this separate background.

## Checking resources and saved packets

The proof allowance defaults to 3,300,000 policy work units. The whole selected
strategy is reserved before invocation: 3,300,000 for finite checking or
2,000,000 for graph integer checking. A separate feasibility allowance defaults
to 3,600,000. Finite background search reserves that full amount. Supplied
integer evidence reserves 100,000 for original admission, another 200,000 for
point admission/replay when present, and 2,000,000 for a contradiction check
when present. Larger allowances do not enlarge representation or domain caps.

These aggregate reservations are distinct from actual primitive/point accounts
and process memory/deadline limits. They are not a proved physical cost model.
Resource refusal means incomplete checking, not a false mathematical claim.

`evidence/pack` saves only request and candidates. `evidence/reopen` freshly
checks them with the current reader's two allowances. Bundle/record version 2
adds the closed feasibility slot. Version 1 remains readable with exactly its
historical fields; the new checker reports version 2 checking semantics.
A saved producer result, stored allowance or extra authority field refuses.
The interface authenticates neither storage nor historical native execution.

## The next program connection

The existing model framework reconstructs contracts and exports explicit
`requires` assertions. Its `formal.obligation` namespace still owns model proof
plans. The new independent consumer helper is `formal.obligation-policy`.

An additional, unqualified prototype in `prototypes/graph-search` proposes graph
integer certificates through bounded Boolean splitting and Fourier–Motzkin
elimination. It uses the kernel's diagnostic normalization to search; that view
never becomes a checking premise. Every candidate must pass the independent
original-subject checker. Search failure is unknown, never satisfiable.

Its pending examples connect a straight affine source contract to the common
carrier, retain a separately checked premise witness, and distinguish a false
contract from search failure through point replay. Integer choices are an
explicit next fragment. The reviewed Source/core interpretation, compiler
preservation and mechanical verification of the BL implementation remain
separate obligations. An accepted symbolic request does not establish all of
those program connections.
