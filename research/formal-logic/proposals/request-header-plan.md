# One checked graph, three raw headers

The isolated `prototypes/request-header` code is prepared and has not run. It
compares the existing request subject-header algorithm with one canonical graph
check followed by raw row selection. It changes no SDK code or dossier input.

The existing request path uses three `question-graph/field-graph` calls for
version, mode and assertion-vector headers. Each operation checks the complete
source and builds a field subgraph. The proposed path validates the same closed
wrapper and complete graph once, then reads only those raw header rows. It
returns the original subject and freshly derived reference as diagnostics. No
consumer accepts this output as a cached typed admission or trusted request.

The six prepared tests compare valid and invalid wrappers/headers, preserve
unfamiliar shared metadata without decoding, show that a valid header can still
fail later typed admission, count actual `graph/check!` invocations under a calibrated
trace, and deny native/oracle execution. At least forty assertions and all six
named bodies are required. The operation-count observation must come from the
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
