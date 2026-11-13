# Count backend invocations separately from native checks

The currently running fixed-artifact compatibility fixture is immutable until
its gate completes. It prints `:native-queries (* 2 (count rows))` after invoking
`logic/run-graph` once for each backend and case. That expression counts 374 BL
backend invocations for 187 completed question pairs. It does not measure native
solver checks: feasibility preflight and query execution have distinct phases,
and a format refusal can occur before either native check.

The word qualification uses the actual 187 complete records, graph and standard
identities, worker/library identities and the status/verdict/phase/validation
comparison. It does not use that printed static query counter as an execution
measurement. Keep the existing actual log rather than relabel its history.

After word SDK selection, rename the future fixture's static field to
`backend-invocations`. A later actual native-check metric needs its own calibrated
protocol-opcode trace or worker counter, with feasibility checks, main checks and
pre-execution refusals separated. Do not infer its value by multiplying cases.
Preserve the existing 500 ms solver and 2,000 ms worker deadlines and retain the
fixture source pin for every old and new run.
