set -euo pipefail
mkdir -p /home/beam-build/enchant-native-tests/d6efd00bf
cd /home/beam-build/enchant-native-tests/d6efd00bf
if [ ! -d source ]; then cp -a /nix/store/vfc3m6z02xzwjj2fknc6gnlc0mmq21x2-datom_fjall-source source; chmod -R u+w source; fi
mkdir -p cargo-home
cat > cargo-home/config.toml <<'CONFIG'
[source.crates-io]
replace-with = "vendored-sources"
[source.vendored-sources]
directory = "/nix/store/yydq5x6kl2yxraf1wmgsmnm82insa2kz-cargo-vendor-dir"
CONFIG
export PATH=/nix/store/gmgfpzc0w2pgby0lmq9r88m39albiyfw-cargo-1.98.1/bin:/nix/store/hr3npzrq9l029s5hf948by203m6qz3lw-rustc-wrapper-1.98.1/bin:/nix/store/ii6p6kc1brz3vycqg88q4zb4xd2dmqwp-gcc-wrapper-16.2.0/bin:/run/current-system/sw/bin:$PATH
systemd-run --user --collect --wait --pipe --unit=enchant-directory-custody-tests-d6efd00bf --working-directory="$PWD" --property=MemoryHigh=2G --property=MemoryMax=3G --property=TasksMax=512 --property=RuntimeMaxSec=1200 env PATH="$PATH" CARGO_HOME="$PWD/cargo-home" CARGO_TARGET_DIR="$PWD/target" CARGO_BUILD_JOBS=2 cargo test --manifest-path source/Cargo.toml --offline --locked --lib directory::close_tests -- --nocapture 2>&1 | tee rust-tests.log
