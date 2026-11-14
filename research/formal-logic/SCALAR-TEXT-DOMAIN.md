# A text point domain is not automatically the solver's String domain

The selected SDK value checker accepts well-formed UTF-8 whose decoded scalar
values are at most 196607 (`0x2FFFF`). This is the existing evaluator's rule,
now shared with managed admission. Its intervals are `0..0xD7FF` and
`0xE000..0x2FFFF`: surrogate codepoints cannot appear in well-formed UTF-8.
Noncharacters such as `0x2FFFF` are not rejected merely for being noncharacters.

The [SMT-LIB Unicode Strings definition](https://smt-lib.org/theories-UnicodeStrings.shtml)
defines its alphabet as all integer codepoints from `0` through `0x2FFFF` and
String as finite words over that alphabet. That interval includes surrogate
codepoints. By contrast, the [Unicode scalar-value and encoding definitions](https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3/)
exclude surrogates from scalar values and well-formed UTF encodings. Thus the
host-representable point domain is a proper subset of the specified SMT alphabet.
This is an inference from the two definitions, not a measured claim about every
solver's treatment of an unrepresentable model value.

The current `formal.term/String` remains the existing solver-facing sort. The
`formal.scalar-text` interface builds terms over that sort and describes the
checked scalar point representation. Its domain metadata does not inject a
native UTF-8-validity assumption into a symbolic variable or quantifier. Likewise,
the `formal.point-profile` text-domain descriptor concerns checked point values;
it is not a native-domain equivalence theorem. Declaring an alphabet interval
alongside UTF-8 does not make every integer in that interval a scalar value.

For literal-ground examples, the new admission checks all actual text values
after reserving their work and before constructing terms. Native and supplied
coordinates get the same demanded value check. An unavailable or unrepresentable
model cannot become a valid BL point. Native String UNSAT remains a solver claim;
the installed finite certificate strategy refuses String sorts. No new String
quantifier proof or Source-domain bridge is authorized by this integration.

Before checking general theorems about ordinary BL text, choose an explicit
connection. Options include a separate full SMT-codepoint value representation,
or portable domain constraints restricting native String variables and quantified
binders to the scalar subset. Regex membership could express the two intervals
and repetition, but needs its own term admission, resource/replay support and
backend evidence. A broader native search domain alone does not establish
equivalence for quantifiers, feasibility, synthesis or arbitrary text operations.
The connection must be retained as part of the complete question and proof scope.

The selected SDK cold packet reader passed four records, four negative
controls and 52 checks with no native or oracle exchange. Its concrete controls
accept the scalars immediately before and after the surrogate range and the
highest SMT codepoint; they reject raw surrogate-shaped UTF-8 bytes and the
first larger valid Unicode scalar. These controls ran only after the first
packet reopened, so they could not conceal a missing cold schema load. The
actual observations are retained in `evidence/scalar-integration/text-packets.json`;
the complete SDK qualification and selection are retained separately.
