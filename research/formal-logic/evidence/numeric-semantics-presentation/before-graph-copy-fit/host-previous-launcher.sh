#!/run/current-system/sw/bin/bash
set -e
export PATH='/home/othman/.nix-profile/bin:/etc/profiles/per-user/othman/bin:/run/current-system/sw/bin'
export BL_DAEMON=off
export ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'
cd -- '/home/othman/code/undefine/beam-lisp--execution-protocol'
export PORT=24089
export HOST=127.0.0.1
exec 'env' 'FORMAL_REVIEW_PROFILE=0' 'FORMAL_REVIEW_KIT_ROOT=/nix/store/fmzbh11ibiyzsz73d8x4gi06fvx54hkm-formal-dossier-kit-a86599fc' '/nix/store/f3kqn31wdggd9cdvxfkny1yf56c5i34y-beam-lisp-sdk-selection/bin/bl' '--cold' '-p' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/src' '-p' '/nix/store/fmzbh11ibiyzsz73d8x4gi06fvx54hkm-formal-dossier-kit-a86599fc/bl-org-dossier/kit' '-p' '/nix/store/fmzbh11ibiyzsz73d8x4gi06fvx54hkm-formal-dossier-kit-a86599fc/codebase-review/kit' 'run' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/review-serve.bl' '--' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/ATLAS.bl.org'
