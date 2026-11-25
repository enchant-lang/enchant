set -euo pipefail
cd /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52
export PATH="$PWD/bin:/run/current-system/sw/bin:$PATH"
export BACKDESK_BL=/nix/store/1zngfs6zj00w9vml4b4m3c7wgxjlylxy-beam-lisp-sdk-selection/bin/bl-cold
export XDG_CACHE_HOME="$PWD/.local/qualification/cache-enchant-main"
export BEAM_LISP_AOT_CACHE_DIR="$XDG_CACHE_HOME/aot"
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
cd /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52/.local/enchant-film-cfb9a05ec18d
python3 - <<'VERIFY'
from pathlib import Path
import hashlib
assert hashlib.sha256(Path('source.tar').read_bytes()).hexdigest()=='1219639793f1dbdd7bf561f8b93f92c3a8d14e64a5f94acde79705e6db7c6f83'
VERIFY
tar -xf source.tar
cd /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52
./scripts/bl which > .local/qualification/enchant-film-runtime.txt
env -u BEAM_LISP_BIN -u BL_ROOT -u BL_EBIN -u BL_SDK_PRODUCT -u BL_CHECKOUT_ROOT -u BL_USE -u BACKDESK_AUTHORIZATION_PROFILE_SETTINGS -u BACKDESK_AUTHORIZATION_DIAGNOSTIC DESK_ENV=development BACKDESK_BL="$BACKDESK_BL" BACKDESK_BROWSER_LIB=/home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52/.local/enchant-film-cfb9a05ec18d/optional/browser-port/bl BL_BROWSER_PORT=/home/beam-build/enchant-browser-qualification/14d9bf7e6c07ecb65c89e124974d8305c7104bf2/target/release/bl-browser-port CHROMIUM=/nix/store/ky199ji3a5drs6rm3wr5zidamx9dhz56-chromium-155.0.8059.39/bin/chromium SWAY=/nix/store/cx9mnp0dwj7hy5gmk5ajm5mfzjy5gqhi-sway-unwrapped-1.12/bin/sway WAYVNC=/nix/store/k7n7k5axjlj9aifb58fiz8pcjxyiz72w-wayvnc-0.10.2/bin/wayvnc PATH="$PATH" XDG_CACHE_HOME="$XDG_CACHE_HOME" BEAM_LISP_AOT_CACHE_DIR="$BEAM_LISP_AOT_CACHE_DIR" ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 4' BL_TEST_TIMEOUT=1200 BACKDESK_BWRAP=/nix/store/zri6pfys37ih88s5yckr47khz5zw1rzk-bubblewrap-0.12.0/bin/bwrap ./scripts/qualification-fhs.sh ./scripts/bl -p /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52/.local/enchant-film-cfb9a05ec18d/optional/browser-port/bl test /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52/.local/enchant-film-cfb9a05ec18d/optional/browser-port/test/film_visibility_test.bl /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52/.local/enchant-film-cfb9a05ec18d/optional/browser-port/test/worlds_test.bl /home/beam-build/backdesk-qualification/main-a91a8224650d490abaadd8d49de9bd17f436824562564b942ae64df8f035cd52/.local/enchant-film-cfb9a05ec18d/optional/browser-port/test/multiscreen_test.bl 2>&1 | tee .local/qualification/enchant-film-tests.log
