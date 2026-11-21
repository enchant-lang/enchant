# Time one stage's self-emission on the Build host: the Rust build and the Chez build side by side.
#   nix build --impure --expr 'import ./bench.nix { stage = "/nix/store/...-rust-substrate-stage-release"; image = /abs/image; chez = /abs/native-seed/chez; }'
# `image` holds bundle.scm, host.scm and stage2.scm. $out/bench.txt has each run's wall time and peak
# memory and whether the emitted stage equals the image's stage2.scm byte for byte.
{ stage, image, chez, runs ? "3", rustRuns ? runs, profile ? false, stackMb ? "4096", timeoutS ? "3000", rev ? "6510408d147d8c5e6d76043e899e9251756f6a75",
  pcre ? "/nix/store/6vqahj875znq0wlsy1bg926yki3d5m4r-pcre2-10.48" }:
let
  pkgs = (builtins.getFlake "github:NixOS/nixpkgs/${rev}").legacyPackages.x86_64-linux;
  pick = names: builtins.path { path = image; name = "stage-image"; filter = p: t: builtins.elem (baseNameOf p) names; };
in
pkgs.runCommandCC "rust-substrate-bench" {
  nativeBuildInputs = [ pkgs.chez pkgs.time ] ++ pkgs.lib.optional profile (pkgs.perf or pkgs.linuxPackages.perf);
  image = pick [ "bundle.scm" "host.scm" "stage2.scm" ];
  chez = builtins.path { path = chez; name = "chez-support"; filter = p: t: pkgs.lib.hasSuffix ".ss" p; };
  stage = builtins.storePath stage;
  pcre = builtins.storePath pcre;
} ''
  mkdir -p $out && cd $TMPDIR
  cp $image/bundle.scm $image/host.scm $image/stage2.scm .
  want=$(sha256sum < stage2.scm)
  {
    echo "host: $(nproc) cores, $(awk '/MemTotal/ {printf "%.0f GB", $2/1048576}' /proc/meminfo)"
    echo "self-emission: stage --compile bundle.scm host.scm OUT   (stage2.scm is $(wc -c < stage2.scm) bytes)"
  } > $out/bench.txt
  # Chez: translate, compile at optimize level 2 as one file, then time the compiled stage.
  export BL_CHEZ_HOST_DIR=$chez
  scheme --script $chez/translate.ss stage2.scm stage2.ss host.c > /dev/null
  $CC -O2 -shared -fPIC -Dstatic= host.c -o host.so -ldl
  echo "(optimize-level 2) (load-shared-object \"$PWD/host.so\") (load \"$chez/chez-shim.ss\") (compile-file \"stage2.ss\" \"stage2.so\")" > compile.ss
  sed -i '$ d' stage2.ss
  command time -f "chez compile-file (whole stage, one thread): %e s wall, %M KB peak" -a -o $out/bench.txt scheme --script compile.ss
  echo "(load-shared-object \"$PWD/host.so\") (load \"$chez/chez-shim.ss\") (load \"$PWD/stage2.so\") (native-main (native-command-line))" > run.ss
  for i in $(seq ${runs}); do
    rm -f out.scm
    command time -f "chez run $i: %e s wall, %U s user, %M KB peak" -a -o $out/bench.txt scheme --script run.ss --compile bundle.scm host.scm out.scm > chez.log 2>&1 || tail -5 chez.log >> $out/bench.txt
    [ "$(sha256sum < out.scm)" = "$want" ] && echo "  chez output: identical to stage2.scm" >> $out/bench.txt || echo "  chez output: DIFFERS" >> $out/bench.txt
  done
  for i in $(seq ${rustRuns}); do
    rm -f out.scm
    RS_STATS=1 RS_STACK_MB=${stackMb} command time -f "rust run $i: %e s wall, %U s user, %M KB peak" -a -o $out/bench.txt \
      timeout ${timeoutS} $stage/bin/stage --compile bundle.scm host.scm out.scm > rust.log 2>&1 || { echo "  rust exit status $?" >> $out/bench.txt; tail -c 3000 rust.log >> $out/bench.txt; }
    if [ -f out.scm ]; then
      [ "$(sha256sum < out.scm)" = "$want" ] && echo "  rust output: identical to stage2.scm" >> $out/bench.txt || { echo "  rust output: DIFFERS ($(wc -c < out.scm) bytes)" >> $out/bench.txt; cp out.scm $out/rust-out.scm; }
    fi
  done
  grep "rust-substrate stats" rust.log >> $out/bench.txt || true
  cp rust.log $out/rust.log || true
  ${pkgs.lib.optionalString profile ''
    if RS_STACK_MB=${stackMb} perf record -F 499 -o perf.data $stage/bin/stage --compile bundle.scm host.scm out.scm > perf.log 2>&1; then
      perf report -i perf.data --stdio --sort symbol > perf-full.txt 2>/dev/null || true
      grep -v "^#" perf-full.txt | grep -v "^$" | sed -n '1,70p' > $out/profile.txt || true
    else
      { echo "perf unavailable:"; tail -3 perf.log; } > $out/profile.txt
    fi
  ''}
  cat $out/bench.txt
''
