# A solver worker in the SDK

The term interface needs a native worker without a research checkout. The
packaging slice moves the canonical term worker into `native/ports/formal_worker`,
builds it as its own pinned executable artifact and carries it in the SDK's
`priv/formal` directory. It remains a port worker, separate from NIF libraries.
The original text-worker experiment retains an explicit compatibility entry.

Ordinary `formal.logic/run` calls should select packaged worker and Z3 library
paths from the running language image. Explicit options and existing research
environment overrides remain available and identified separately. No system
PATH lookup selects a solver. Complete questions, native ownership, deadlines,
typed replay and proof authority rules remain unchanged.

The artifact records its source, Cargo lock, enabled solver features and actual
worker bytes. Runtime evidence names the files actually used. Portable
packaging rewrites ELF files, so its manifest must describe the resulting bytes
and retain the producer identity separately. A producer hash cannot stand in
for the relocated executable's hash.

Qualification is pending. The preceding SDK requires an explicitly configured
worker and library. Packaging does not migrate the default legacy text oracle,
add solver theories, establish compiler preservation or prove totality.
