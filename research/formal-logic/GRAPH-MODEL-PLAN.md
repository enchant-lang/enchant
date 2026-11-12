# A mechanical model for shared public data

Next foundation after graph-consumer qualification. This is a design, not a
checked theorem or an implementation correspondence claim.

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
