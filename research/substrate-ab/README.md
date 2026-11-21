# Gambit vs Chez substrate comparison (concluded)

This directory compared the qualified native compiler Scheme on Gambit, on Chez
Scheme, and against warm BEAM. Chez won. Measured on the reader job: 169 ms
on Chez, 834 ms on Gambit and 158 ms on warm BEAM. Chez also built the compiler
in 5–9 s, against Gambit's 151 CPU seconds. The interpretation is in
`research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`, with
evidence in `research/checked-tiles/evidence/substrate-*.json`.

The route it chose now lives in `research/native-seed/chez/`. That directory
holds the translator, the shim, the observer and the profiler, and its
`qualify.bl` builds, qualifies, derives, pairs and profiles without Python.
This directory keeps only records:
- `*-pair.txt`: the paired timings each host change was accepted on;
- `floor/`: the warm request floor traces and the Erlang tracers that took them.

The comparison drivers (Python and shell) are retired; they remain in Git
history.
