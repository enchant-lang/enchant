# One checked graph, three raw headers

The isolated `prototypes/request-header` code passed all 54 assertions and six
named test bodies on the selected scalar SDK. Its source-bound report is
`evidence/request-header-prototype/qualification.json`. It
compares the existing request subject-header algorithm with one canonical graph
check followed by raw row selection. It changes no SDK code or dossier input.

The existing request path uses three `question-graph/field-graph` calls for
version, mode and assertion-vector headers. Each operation checks the complete
source and builds a field subgraph. The proposed path validates the same closed
wrapper and complete graph once, then reads only those raw header rows. It
returns the original subject and freshly derived reference as diagnostics. No
consumer accepts this output as a cached typed admission or trusted request.

The six actual tests compare valid and invalid wrappers/headers against both the copied header
block and the actual installed `request/prepare` entry, preserve
unfamiliar shared metadata without decoding, show that a valid header can still
fail later typed admission, count actual `graph/check!` invocations under a calibrated
trace, and deny native/oracle execution. All 54 assertions and all six
named bodies passed. The operation-count observation must come from the
running tests, not from a top-level write during file loading.

A passing prototype would justify review of a shared SDK header helper. It would
not justify removing fresh validation at an external data boundary. Profile
normalization and repeated validation across compound evidence operations need
separate measurements and a private checked-operation design; accepting a
caller-supplied ready flag is not that design. Any timing comparison must name
its fixture, warmup and process; fewer graph checks alone is not a universal
speedup claim.

The trace counts all calls, including validation of the small selected field
subgraphs. Report it as graph-check invocations, not as a count of complete
original-source scans or native solver checks. The proposed path does directly
check the complete original graph once.

The actual small-integer fixture recorded nine `graph/check!` calls in the
reference header block and one in the single-pass implementation. This includes
field-subgraph validation in the reference count. Both paths retain the complete
original reference, and valid-header/invalid-term inputs still fail typed
admission later. The installed SDK remains unchanged.
