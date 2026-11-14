#!/run/current-system/sw/bin/bash
set -e
export PATH='/home/othman/.nix-profile/bin:/etc/profiles/per-user/othman/bin:/run/current-system/sw/bin'
export BL_DAEMON=off
export ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'
cd -- '/home/othman/code/undefine/beam-lisp--execution-protocol'
export PORT=24089
export HOST=127.0.0.1
exec 'env' 'FORMAL_REVIEW_PROFILE=0' 'FORMAL_REVIEW_KIT_ROOT=/nix/store/1ja584mh4qyz02w7sn3ym3f6zwvx7jxq-formal-word-dossier-kit-5a1679cf' '/nix/store/vhfbs1j03jkbk8blvz9ys5wxxqmpyss2-beam-lisp-sdk-selection/bin/bl' '--cold' '-p' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/src' '-p' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/dossier' '-p' '/nix/store/1ja584mh4qyz02w7sn3ym3f6zwvx7jxq-formal-word-dossier-kit-5a1679cf/bl-org-dossier/kit' '-p' '/nix/store/1ja584mh4qyz02w7sn3ym3f6zwvx7jxq-formal-word-dossier-kit-5a1679cf/codebase-review/kit' '-p' '/nix/store/1ja584mh4qyz02w7sn3ym3f6zwvx7jxq-formal-word-dossier-kit-5a1679cf/research-elements/kit' 'run' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/review-serve.bl' '--' '/home/othman/code/undefine/beam-lisp--execution-protocol/research/formal-logic/ATLAS.bl.org'
