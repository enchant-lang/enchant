# Native String representations differ before we discuss proof search

The [exact source receipt](evidence/string-representation-review/source-review.json)
binds the built candidate SDK's unchanged worker binary, its immutable source,
its actual derivation's Cargo vendor directory and the locked OxiZ 0.3.4 crate
checksum. It inspects those immutable files rather than assuming a mutable local
Cargo registry is the build source. This is a source-level finding, not a new
native domain experiment.

Both current BL adapters accept String literals through the same UTF-8 binary
wire function. The Z3 adapter converts Rust scalar characters to a vector of
32-bit codepoints and calls `Z3_mk_u32string`. For model output, it reads codepoints
and converts them through `char::from_u32`; if a codepoint is not a Unicode scalar,
it returns an opaque observation with an explicit reason. It does not invent a
replacement character or claim that BL replay has checked that model.

The pinned OxiZ core represents a literal as `TermKind::StringLit(String)`, and
our adapter supplies the decoded UTF-8 text to `mk_string_lit`. Rust `String`
cannot carry a surrogate as a Unicode scalar. This observation concerns that
literal/model representation; it does not prove what values OxiZ's symbolic
String domain includes or excludes internally.

A full SMT-codepoint BL representation is therefore a real architectural choice.
Z3's native constructor and model reader already expose a 32-bit interface,
although our portable literal and coordinate formats would still need extension,
resource accounting and independent replay. The OxiZ literal representation
would require an explicit encoding or a core representation change to carry
non-scalar literal codepoints. Do not infer that either engine is incapable of
reasoning about a domain merely from this carrier inspection.

This qualifies the original question about language nativeness. A native Rust
library does not by itself supply every BL value representation or settle its
semantics. The term interface, ownership, exact carrier and checker matter for
both engines. A future scalar-domain restriction might instead keep BL's UTF-8
representation and add explicit constraints; that requires regex/domain terms,
quantifier handling and independent evidence which are not implemented here.

Read [the domain review](SCALAR-TEXT-DOMAIN.md) for the separate distinction
between the specified SMT alphabet and valid UTF-8 scalar points. General native
String soundness, quantified-domain equivalence, a complete codepoint carrier,
Source semantics and compiler preservation remain unestablished.
