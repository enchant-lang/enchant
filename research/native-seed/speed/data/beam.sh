#!/usr/bin/env bash
# DATA workstream, BEAM half: emit the self-hosted modules and write the oracle.
# One queue slot, two sequential pinned-SDK VMs (each exits):
#   work run --memory 3G --timeout 2400 -- bash research/native-seed/speed/data/beam.sh
set -u
cd "$(dirname "$0")/../../../.."
M=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed/research/native-seed/out
D=research/native-seed/speed/data
research/native-seed/run run "$D/emit.bl" -- "$M/speed-closure/partition.json" "$M/speed-build/leaves.json" "$D/out/a" \
  host.ex-info=priv/host/ex_info.bl=Elixir.BeamLisp.ExInfo \
  host.compile-error=priv/host/compile_error.bl=Elixir.BeamLisp.CompileError \
  host.sorted=priv/host/sorted.bl=Elixir.BeamLisp.Sorted 2>&1 | grep -v "Nix preparation failed"
research/native-seed/run run "$D/oracle.bl" -- "$D/out" 2>&1 | grep -v "Nix preparation failed"
