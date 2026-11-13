#!/run/current-system/sw/bin/bash
set -e
export PATH='/home/othman/.nix-profile/bin:/etc/profiles/per-user/othman/bin:/run/current-system/sw/bin'
export BL_DAEMON=off
export ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'
cd -- '/home/othman/code/undefine/beam-lisp--execution-protocol'
export PORT=24089
export HOST=127.0.0.1
exec 'env' 'FORMAL_REVIEW_PROFILE=0' 'FORMAL_REVIEW_KIT_ROOT=/nix/store/ifiadn7wnvzxr2ivgd6rv5gsncwgar72-formal-dossier-kit-17ecb6b2' '/nix/store/s353xs74fldvfcvcxvsilagm0ymgx53k-beam-lisp-sdk-selection/bin/bl' '--cold' '-p' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/src' '-p' '/nix/store/ifiadn7wnvzxr2ivgd6rv5gsncwgar72-formal-dossier-kit-17ecb6b2/bl-org-dossier/kit' '-p' '/nix/store/ifiadn7wnvzxr2ivgd6rv5gsncwgar72-formal-dossier-kit-17ecb6b2/codebase-review/kit' 'run' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/review-serve.bl' '--' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/ATLAS.bl.org'
