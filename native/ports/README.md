# Native port executables

Port executables have a versioned message protocol and a process lifetime.
Their crates live below this directory, separate from the direct `native/*`
NIF crates and their shared-library ABI declarations.

`formal_worker` serves the typed formal DAG protocol for Z3 and OxiZ. Its
independent SDK product is declared in `nix/formal-worker.nix`; language-facing
ownership and deadlines live in `formal.backend`. It is not loaded into the
BEAM as a NIF.
