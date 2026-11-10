# One proof-data interface for every formal subject

Contracts, loop controllers, state protocols, source handlers, bounded traces,
Core translations and direct questions now expose the same closed obligation
plan. Each required property has an exact label and question. Initial-context
inconsistency and SAT witness questions have separate roles. The plan retains
the prepared model/Source connection without upgrading its reviewed status.

```clojure
(formal/obligation-plan subject)
(def made (formal/certify-obligations subject))
(def bundle (:bundle made))
(formal/check-obligation-proof-data subject bundle)
```

All values are ordinary BL data. The same subject identities, profiles and
question trees can be compared with either native backend. This facet currently
uses BL's independent certificate producer; it does not claim that Z3 or OxiZ
exports certificates in this format.

## Four operations, with distinct jobs

| Operation | Behavior |
| --- | --- |
| `obligation-plan` | Freshly prepares the subject and returns exact required and auxiliary questions. |
| `certify-obligations` | Searches for BL certificates and exports original-term proof packets. Missing required evidence remains visible. |
| `obligation-proof-data` | Packages certificates supplied by label, without certificate search. Missing entries stay pending. |
| `check-obligation-proof-data` | Reconstructs the full plan and checks coverage, certificates, packets and manifest. It never trusts a plan hash alone. |

The common model-preparation dispatch also serves `formal/describe`. Existing
`formal/check`, comparison, compiler/oracle policy and runtime defaults retain
their behavior. No automatic compiler proof authority follows from the new
facet.

Source preparation may compile or execute expansion-phase semantics. These
functions are not a promise that arbitrary Source reconstruction is effect-free.
The proof-data checker does not call the experiment's certificate producer,
formal native backend sessions or external Lean checker. Its successful status
is `:checked-data-connection`, with `:kernel-execution :not-run`.

## Required coverage, unreachable paths and witnesses

A plan's ordered rows are closed records with a label, original key, role,
required flag and complete question. Every required proof question also has an
explicit alternative target: prove false under that same assertion context.

An `:entailment` row carries a theorem of its original typed claim. An
`:unreachable` row instead proves that the path's assertions cannot all hold.
It closes that conditional obligation by unreachability; it does not pretend
that the original property tree was directly checked by the term proof tool.
The fresh BL checker reconstructs the alternative target from the real subject.

All required rows remain present, ordered and unique. Removing one loop premise
is rejected even if all remaining certificates and a smaller manifest are
self-consistent. A missing required proof makes the bundle `:incomplete`.
Unknown and unsupported searches cannot establish satisfiability.

A SAT question requires witness evidence. The refutation facet records
`:requires-witness`, rather than accepting empty proof coverage. Feasibility
rows for conditional models are auxiliary; they do not block a conditional
property proof, but remain visibly unproved. A separately checked false-goal
proof can establish inconsistency of the contained initial term context.
That is distinct from an unreachable transition or a positive initial witness.

The closed model-to-term interpretation and model-rule composition remain
reviewed implementations. Checking all term leaves is not itself a new
mechanized theorem about loop execution, state induction, the Source compiler
or live actor behavior. Their existing mathematical rules retain their own
scoped proofs and bridge premises.

## Supply proof data from another producer

```clojure
(formal/obligation-proof-data subject
 {"property" {:via :entailment :certificate object}})
```

Labels come from the plan, not from guessed backend IDs. The constructor rejects
unknown labels, stale certificates and inadmissible routes. It reconstructs
the original-term packet for each supplied certificate. Missing auxiliary or
required entries remain pending. Callers can transport the result between VMs;
no native solver handle or compiled callback belongs in the bundle.

Diagnostics on pending rows describe production history, not theorem content.
The same valid certificates may therefore be packaged with different pending
diagnostics while retaining identical proof targets and packet identities.

## Explicit proof-foundation policies

The axiom policy belongs to the proof bundle and its external manifest, not the
model's operational semantics:

| Policy | Permitted Lean foundations |
| --- | --- |
| `:choice-free-v1` | `propext`, `Quot.sound` |
| `:lean-standard-v1` | `propext`, `Quot.sound`, `Classical.choice` |

Common bundles default to the standard policy and record it explicitly.
Use `{:axiom-policy :choice-free-v1}` with `certify-obligations`, or as the
third argument to `obligation-proof-data`, to select the stricter policy.
The data constructor does not assert that Lean has already checked a proof
under that policy. External checking records each theorem's actual dependencies
and rejects dependencies outside the selected policy. Unknown policies are
rejected; they cannot expand the trusted axiom list.

The larger countdown example exposed genuine printed `Classical.choice`
dependencies in Lean's arithmetic proofs of two obligations. The standard policy
accepts it and lists it; the choice-free policy rejects the same proof source.
That does not show that no choice-free proof of the statement exists. A proof's
use of classical choice is also distinct from a runtime effect in the BL
program. Neither policy accepts `sorryAx`, native-evaluation axioms or arbitrary
new postulates.

Standalone `check-term-refutation` retains its choice-free default. Its optional
`--axiom-policy lean-standard` uses the same explicit audit policy. The typed
term model and normalized checker definitions/pins do not change with this
selection.

## Check the included term proofs

```sh
research/formal-logic/check-obligation-manifest \
  research/formal-logic/evidence/obligations/examples/manifests/loop.json \
  --output /tmp/countdown-obligations
```

The external manifest is a deliberately narrow projection: subject/plan
identities, exact labelled coverage, proof routes, axiom policy and typed term
packets. The runner reconstructs its canonical identity independently. It
validates role/mode/status distinctions and checks every included term packet
with the pinned Lean kernel. Inconsistency and unreachability routes must prove
the explicit false goal, so an unrelated true theorem cannot stand in for them.
Leaf files use numeric directories; labels remain data.

Exit 0 means all **declared required term evidence** checked. Exit 2 reports
incomplete required evidence, including an unprovided SAT witness. Exit 1
reports invalid data or a rejected proof/policy. A partial manifest can still
retain valid checked leaves; it never becomes a complete model promise.

This runner cannot reconstruct arbitrary BL models from a manifest alone.
It reports that the model connection requires fresh BL subject/plan
reconstruction and that model composition remains reviewed. A rehashed smaller
manifest can correctly describe a smaller set of checked leaves; the fresh BL
checker rejects it as coverage of the original complete subject. Both checks
are necessary for that connection. A self-consistent subject digest is neither
proof of model interpretation nor cryptographic execution attestation.

## Qualified example shapes

Thirteen exports cover all seven subject kinds, including authored and Source
contracts, a countdown loop with eight required premises, authored and Source
state induction, both bounded-trace forms, a dead transition, a vacuous contract,
an unknown contract and a direct SAT query. Eleven bundles have complete declared
required evidence; two remain incomplete. Their 22 ready required leaves consist
of 21 direct entailments and one unreachable-path proof. A further auxiliary
proof establishes the vacuous contract's initial inconsistency.

The external checks retain every actual theorem/axiom audit. Fresh-VM checks
reconstruct full plans and package supplied certificates in a positively
calibrated window that counts certificate-search and formal-backend entry calls.
Source preparation remains allowed in that window; no claim about every
compiler-internal operation follows from those two counters.

[Constructive witnesses](WITNESSES.md) are now implemented as standalone
typed-term packets. This v1 format retains its existing `:requires-witness`
interpretation. A new mixed format can add these packets and keep positive
feasibility separate from required proof coverage. Broader theory rules,
mechanized model composition and data/Source/compiler correspondence remain
work toward the full formal-language goal.
