#!/run/current-system/sw/bin/bash
set -e
export PATH='/home/othman/.nix-profile/bin:/etc/profiles/per-user/othman/bin:/run/current-system/sw/bin'
export BL_DAEMON=off
export ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'
cd -- '/home/othman/code/undefine/beam-lisp--execution-protocol'
export PORT=24089
export HOST=127.0.0.1
exec 'env' 'FORMAL_REVIEW_PROFILE=0' 'FORMAL_REVIEW_KIT_ROOT=/nix/store/8y8qxlizxn1f2fz7w8rpwpv9f9z739gq-formal-scalar-dossier-kit-56021417' '/nix/store/ba0hcmidasaw3p2swjdgcbbi8psmx1y0-beam-lisp-sdk-selection/bin/bl' '--cold' '-p' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/src' '-p' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/dossier' '-p' '/nix/store/8y8qxlizxn1f2fz7w8rpwpv9f9z739gq-formal-scalar-dossier-kit-56021417/bl-org-dossier/kit' '-p' '/nix/store/8y8qxlizxn1f2fz7w8rpwpv9f9z739gq-formal-scalar-dossier-kit-56021417/codebase-review/kit' '-p' '/nix/store/8y8qxlizxn1f2fz7w8rpwpv9f9z739gq-formal-scalar-dossier-kit-56021417/research-elements/kit' 'run' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/review-serve.bl' '--' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/ATLAS.bl.org'
