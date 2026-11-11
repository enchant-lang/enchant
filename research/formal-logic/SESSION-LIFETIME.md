# A question owns its worker until the session ends

`formal.backend/with-session` gives a borrower one owner process and one native
worker. Its cleanup bracket now starts immediately after owner startup returns.
Retrieving the greeting and constructing the session are inside that bracket,
along with the user's callback. Failed initialization explicitly closes any
opened port and removes the borrower monitor before raising the original error.

Leaving the callback retires its diagnostic state and requests a normal owner
stop. If that owner cannot stop within one second, cleanup kills that exact PID
and waits for its monitor. BEAM closes the dead owner's ports; the native
worker's EOF watchdog ends the OS process independently of the solving thread.
This also handles an owner deliberately suspended during a callback exception.
An ordinary cleanup timeout no longer replaces that exception or leaves the
suspended owner alive. Cleanup never selects a worker by a process name or kills
an unrelated solver.

The previous SDK failed 21 assertions in the new initial 169-assertion check.
Two failures concerned actual behavior: a suspended owner survived its bracket
and hid the callback error, and the decoder accepted trailing bytes after a
valid ETF term. Other failures demanded more precise transport diagnostics.
The initial baseline contains six tests. The expanded eight-test file passes 183
assertions, including oversized requests and idle native borrower death. The
retained baseline is in `evidence/session-lifetime/baseline-checks.txt`;
the first reader-error attempt is retained separately.

The selected immutable SDK passes 686 focused assertions across nine files and
7,086 formal regression assertions across 22 files. All 187 paired native
questions retain their exact identities and solver/verdict statuses. The full
compiler-floor check passes for the same 141 files as the previous SDK. The
exact pin, commands and source hashes are retained in
`evidence/session-lifetime/qualification.json`.

Every reply must now contain exactly one bounded, uncompressed, safe ETF term.
The decoder requests the number of consumed bytes and refuses any remainder.
This validation precedes the existing protocol/backend/generation/schema and
typed observation checks. A rejected frame never becomes a solver verdict.

| Failure | `:why :kind` | `:why :phase` |
| --- | --- | --- |
| Empty, oversized, compressed, malformed or trailing reply bytes | `:invalid-frame` | `:reply` |
| Wrong reply identity or schema | `:invalid` | `:reply` |
| Worker exit, including an incomplete packet followed by exit | `:worker-exit` | `:transport` |
| No reply by the hard deadline | `:timeout` | `:transport` |
| Encoded request exceeds packet capacity | `:packet-capacity` | `:request` |
| Port rejects a nonsuspending write | `:port-busy` | `:transport` |

Exchange failures retain the operation and available exit status/reason. They
close the port and retire the context; a managed reset cannot revive it. An
incomplete packet is observed as worker exit because BEAM's packet decoder
does not deliver a partial payload. The interface does not invent a more
specific framing diagnosis from that observation.

`test/bl/system/formal_lifetime_test.bl` observes the actual owner and Linux OS
PIDs for normal returns, callback exceptions, suspended owners, and idle
borrower death on both native engines. A deliberately faulty Python ETF peer
exercises initialization and exchange failures, packet capacity and borrower
death during a pending exchange. That peer is never a solver: pending-peer
cancellation does not qualify cancellation during a genuine hard solver search.
The fixture records every complete packet and EOF; waits are bounded and test
cleanup stops only processes started by the check.

This is session lifetime and transport evidence. It adds no proof certificate,
language termination theorem, continuation capture, worker pool or global
resource bound. An unresponsive peer still receives a bounded grace period
when closing the bracket. A future reusable pool must additionally enforce
admission/backpressure and prove that reset removes every borrower's state.
