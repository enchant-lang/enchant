# A mechanical model for shared public data

The first foundation is now qualified in [GRAPH-TABLE-MODEL.md](GRAPH-TABLE-MODEL.md):
a total prefix-table model, fold/quantity laws, certified local counters and
three exact owned-wire node/depth instances. The separate
[selection model](GRAPH-SELECTION-MODEL.md) adds seven general lemmas, five
fixture theorems and four refusal controls: a closed, correctly admitted
selection agrees with the original value. This document retains the broader
plan. The actual dependency-selection algorithm, pruning, canonical encoding/hash theorems,
scalar byte-cost instantiation, typed binders and a universal implementation
connection remain open; the completed results do not imply those connections.

The first model should establish the part that sharing makes subtle: a finite
node table can describe a much larger value, and selecting an operational view
must not change the meaning of its selected nodes.

Use a length-indexed table. A row appended to a table of length `n` may refer
only to `Fin n`. Induction on table construction then gives a total interpreter
without a fuel parameter, an assumed DAG theorem, or a general-recursion escape.
Scalars retain exact tags and payloads. Float64 is a bounded bit pattern, not a
Real; Int, Float, both zero signs, bytes, keyword names and symbols do not share
constructors. Container kinds remain distinct. Map pairs and their order need
an explicit representation rather than borrowing a host map's equality.

Derive a generic bottom-up fold and prove that a fold over the shared table
agrees with folding its expanded value. Instantiate it for expanded node count,
scalar-byte count and depth. The arithmetic uses unbounded naturals; crossing a
budget is a refusal before materialization, never an overflowing counter or a
truncated reconstruction. Working composition budgets may conservatively reject
more than final-result budgets; that is a resource policy, not a semantic change.

For selective decoding, distinguish the interpretation of a keyword name as
data from admission of that name into a runtime vocabulary. Prove that closing
selected roots over dependencies suffices to interpret those roots, and that
an unrelated unadmitted scalar cannot force the selected interpretation to
fail. Full materialization can still refuse. A scope-sensitive typed term
checker is a subsequent consumer: shared node identity alone is insufficient
for caching a bound term independently of its binder environment.

Composition needs its own statements. Importing a table under an injective
renaming preserves interpreted roots; interning merges equal row descriptions
only; pruning unreachable nodes preserves the chosen root; canonical renumbering
preserves all ordered edges. Patch and concatenation laws should follow from
these statements. Duplicate map keys and set elements are rejected according
to the declared structural relation, not silently normalized.

Canonical bytes and content references form another layer. First prove the
finite canonical representation deterministic and its encoder injective over
admitted tagged data. Do not assume SHA-256 is injective. Hashes may reject
collisions and support diagnostic references; exact canonical bytes remain the
binding check where the interface promises exact contents. The cryptographic
assumption, if used by durable references, must be named separately.

Finally connect the implementation. Generate model inputs from exact retained
BL graphs and check their interpretations, counts and selected projections;
retain malformed and altered-reference controls. These instance connections
are useful but do not establish universal preservation of `formal.data-graph`.
A universal connection needs a model of the relevant BL/BEAM operations or a
verified translation for the implementation. The existing Int/Bool term and
Core theorems cannot be borrowed to cover graph loops, arbitrary maps, effects
or compiler behavior they do not model.

## A graph-native typed term consumer

The current context still rebuilds ordinary typed terms and runs the existing
validator/evaluator. End-to-end corpus timings include that work and repeated
public-boundary validation. They are not solver speed measurements.

A next consumer should select a typed forest directly from checked public node
IDs. Its meaning must stay tied to the complete original question, including
vacuity, counterexample construction, observations and semantic domains. A
portable node ID is not a native arena handle. Each native adapter translates
that forest into the actual owner's arena, with its revision checks preserved.

Validate binders under `(node ID, binder environment)`, rather than memoizing a
bound expression by node ID alone. Prove the resulting interpreter agrees with
the existing typed-term semantics before using it to replace a checked path.
Finite operator tags can remain a closed vocabulary; user variable names,
constructor names and inert keyword labels can stay bytes. A later label-aware
value profile could reason about a finite keyword universe without interning
its members, returning graph data until explicit materialization is requested.
That would require its own declared value/observation interface and qualification.

First remove redundant validation inside one public operation using private,
locally derived views. Do not accept a caller's cached view as authority. A
cross-call cache is a separate design: exact complete inputs, checker/profile
identity, explicit capacities and cache-miss equivalence all need treatment.
Optional memo admission must never determine whether validation or effects run;
the eager-doseq compiler transition is a concrete reminder of that requirement.
