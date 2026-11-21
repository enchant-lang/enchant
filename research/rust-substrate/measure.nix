# Build one translated stage on the Build host and record what rustc cost.
#   nix build --impure --expr 'import ./measure.nix { src = /abs/build-dir; mode = "release"; }'
# `src` holds main.rs, rt.rs and gen/ (see build.sh). $out/timing.txt has wall, CPU and peak memory.
{ src, mode ? "release", opt ? "2", cgu ? "16", cfg ? "", rev ? "6510408d147d8c5e6d76043e899e9251756f6a75" }:
let
  pkgs = (builtins.getFlake "github:NixOS/nixpkgs/${rev}").legacyPackages.x86_64-linux;
  flags =
    if mode == "check" then "--emit=metadata"
    else if mode == "debug" then "-C opt-level=0 -C debuginfo=0 -C codegen-units=${cgu}"
    else "-C opt-level=${opt} -C debuginfo=0 -C codegen-units=${cgu}";
in
pkgs.runCommandCC "rust-substrate-stage-${mode}" {
  nativeBuildInputs = [ pkgs.rustc pkgs.time ];
  src = builtins.path { path = src; name = "rust-substrate-src"; filter = p: t: !(pkgs.lib.hasPrefix "stage-" (baseNameOf p)); };
} ''
  cp -r $src work && chmod -R u+w work && cd work
  mkdir -p $out/bin
  {
    echo "host: $(uname -m), $(nproc) cores, $(awk '/MemTotal/ {printf "%.0f GB", $2/1048576}' /proc/meminfo)"
    rustc --version
    echo "mode: ${mode}  flags: ${flags} ${cfg}"
    echo "rust source bytes: $(cat main.rs rt.rs gen/*.rs | wc -c)"
  } > $out/timing.txt
  link=""
  if [ "${mode}" != check ]; then
    $CC -O2 -Dstatic= -c gen/host.c -o host.o
    link="-C link-arg=$PWD/host.o -C link-arg=-ldl"
  fi
  command time -f "rustc: %e s wall, %U s user, %S s sys, %M KB peak" -a -o $out/timing.txt \
    rustc --edition 2024 --crate-name stage -A warnings ${flags} ${cfg} $link main.rs -o $out/bin/stage 2> rustc.log \
    || command time -f "rustc: %e s wall, %U s user, %S s sys, %M KB peak" -a -o $out/timing.txt \
       rustc --edition 2024 --crate-name stage -A warnings ${flags} ${cfg} $link main.rs -o $out/bin/stage 2> rustc.log \
    || { head -c 20000 rustc.log; exit 1; }
  cp rustc.log $out/rustc.log
  cat $out/timing.txt
''
