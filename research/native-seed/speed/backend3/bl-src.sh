#!/usr/bin/env bash
# The pinned SDK's bl with a chosen native-seed source tree (emitter).
# usage: bl-src.sh SRC CWD BL-ARGS...   (run it under `work run`)
set -euo pipefail
here=$(CDPATH='' cd "$(dirname "$0")/../.." && pwd -P)
src=$(CDPATH='' cd "$1" && pwd -P) cwd=$2
shift 2
sdk=$(jq -r .sdk "$here/sdk-pin.json")
source=$(jq -r .source "$here/sdk-pin.json")
runtime=$(mktemp -d /tmp/bl-backend3-XXXXXXXX)
trap 'rm -rf -- "$runtime"' EXIT
cd "$cwd"
XDG_RUNTIME_DIR="$runtime" "$sdk/bin/bl" --cold -p "$src" -p "$source/priv/build" "$@"
