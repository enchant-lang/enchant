# Exact values before stronger logical promises

The selected immutable SDK in `sdk-pin.json` now contains the numeric batch.
Its [core qualification](evidence/numeric-semantics/qualification.json),
[cross-SDK readers](evidence/numeric-semantics/previous-readers-qualification.json)
and [selection record](evidence/numeric-semantics/promotion.json) bind the actual
source, artifact, commands and results. The live dossier refresh has its own
execution and browser gates. No new SDK is needed for that presentation work.

Generic finite numeric equality now compares exact values on BEAM and JS:
`1.5M`, `1.5` and `1.50M` form a coherent equality triple. `0.1M` still differs
from the actual binary64 value `0.1`; `0.50M` equals `0.5`. Decimal coefficient
and scale survive storage, printing and arithmetic. The explicit
`decimal/same-representation?` relation distinguishes scale when a program
needs it. Decimal arithmetic still refuses Float operands; comparison and
arithmetic coercion are different contracts.

The JS runtime decodes the actual binary64 fields and compares exact BigInt
cross-products. The named Decimal API also compiles from ordinary BL: its
constructors, arithmetic, eight rounding modes and conversions use the same
runtime representation as core operators. Exact division computes termination
from denominator factors and preserves preferred operand scale; there is no
guessed 64-place ceiling. Named Float approximation follows the pinned short
formatting policy. Its finite observations do not establish all formatting
options, nonfinite interop or whole-target correspondence.

The legacy `system.smt` translation reconstructs BL divisor-sign modulus from
Euclidean remainder `e`: `if e=0 or b>0 then e else e+b`. It is qualified on an
explicit nonzero-divisor domain. Runtime zero division still raises; the legacy
expression API does not encode that raised outcome. The typed numeric term
interface keeps a separate definedness condition. Three separated native
queries report magnitude, sign and quotient reconstruction. Their UNSAT
answers remain solver claims. The original combined query timed out and is
retained as undecided evidence.

The separate [integer model](FLOOR-MODULUS-MODEL.md) checks ten results and two
actual false-claim rejections. Its exact theorem ledger and eight Std dependency
audits distinguish the two constructive bounds from floor identities that
inherit `Classical.choice`. No axiom about BL execution or compiler preservation
is introduced. The implementation connection remains reviewed and unproved.

| Completed gate | Actual scope |
| --- | --- |
| Compiler product | Complete 141-file floor; P/B/C generations and B/C byte identity |
| Packaged source | All 714 BL/JS files bound; 700 BL sources, eight intended runtime changes |
| Source preflight | 595 namespaces; parse, target-edge and cycle refusal controls |
| Finite numeric observations | The same 30 values and 900 ordered pairs on BEAM, direct JS and actual compiled BL; zero discrepancies |
| Compiled Decimal API | All 1,051 existing JVM-captured cases, five representation cases and eleven named Float approximations per route |
| JS unit checks | 40 passing tests, with source bytes matched to the selected SDK |
| Focused BEAM | 2,853 assertions across numeric laws, host ABI, captured Decimal cases, codec and legacy SMT translation |
| Datom | 205 assertions for payload scale, joins, identity upserts, CAS, retraction and durable reopen |
| Managed formal API | 952 assertions across shared evaluation, admission, actual ownership, requests and graph keys |
| Retained project behavior | 8,141 assertions across 31 files |
| Native corpus | 187 complete questions on both engines, unchanged outcomes at the existing 500/2000ms limits |
| Previous records | Two fresh SDK-only readers; 187 records and 52 point replays each; eleven tamper refusals; zero native exchanges |

The native corpus took about 33 minutes; no speed advantage is established.
The three-route baseline retains six BEAM, fourteen direct-JS and six compiled-BL
pair discrepancies on the earlier qualified SDK. Its source, emitted JS and
receipts remain separate from the selected candidate's zero-difference results.
Captured JVM answers were not rewritten; Java `.equals` spellings now call the
explicit representation relation. The oracle corpus compares values and
raisedness, rather than complete exception classes/messages or effect traces.

Ordinary map/set keys retain their raw relation. Equal numbers therefore do not
yet imply interchangeable ordinary collection keys. Datom's existing semantic
index relation, index version 2 and immutable identity format remain intact in
this batch; the recorded tests establish their stated finite compatibility and
lossless payload behavior. A language collection-key migration needs separate
collision, retained-data and evaluation-order rules. Equality also does not
justify arbitrary program substitution through printing, scale inspection,
kind-sensitive arithmetic or effects.

The previous-record readers pin the recorded producer SDK separately from the
current checker SDK. They preserve original subjects, coordinates, references
and reported native statuses. Mathematical replay is fresh; neither those
labels nor content hashes authenticate historical native execution. The reader
and owner use the same SDK mathematics in separate fresh scopes, rather than
independent implementations of it.

Recovery evidence retains the first numeric SDK's missing `rescale/2` ABI
registration, its source-only bundle and archive ref. The replacement fixes that
registration and passes its own complete gates. Earlier bare-VM floor attempts
remain unqualified recovery evidence; the official compiler-only product
supplied the installed floor. Failed audit-schema assumptions and unqualified
mathematical proof attempts are retained without rewriting passing gate data.

A host ABI test run also printed assertion failures while returning process
status zero. The numeric runner therefore requires the complete green summary
as well as process success and records both. The general CLI outcome contract
needs its own minimal reproduction and subsequent runtime repair if warranted.
No whole-language totality, verified compiler, universal implementation
correspondence, general exception/effect equivalence or complete theory support
is claimed by these finite SDK checks.
