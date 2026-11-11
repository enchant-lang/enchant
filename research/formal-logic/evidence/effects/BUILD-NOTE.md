# Production boundary

The retained manual regeneration failures produced no installed floor:

- `regen-launcher-path-error.txt`: the bare shell had no `elixir` executable.
- `regen-incoherent-build-error.txt`: the checkout's stale build could not load
  current reader source (`compiler/list` was unavailable).
- `regen-kernel-mismatch.txt`: a coherent preceding SDK compiled the current
  native hosts, then refused artifact production after retargeting to the
  checkout's different committed floor. Its loaded compiler kernel and the
  checkout manifest did not match. The kernel attestation stayed enforced.

The optional SDK-based manual regenerator was reverted. These attempts are
diagnostic evidence, not an alternate qualified build procedure. The checkout
floor remains unchanged, with its preceding manifest retained here.

The standard managed SDK producer starts P from the committed foundation,
then freshly boots the actual P and B predecessors to produce B and C. It
checks equal B/C inventories and the complete SDK floor. The active production
is recorded by `sdk-production.txt`; runtime qualification will bind its exact
result and compiler receipt before selecting a new research SDK pin.
