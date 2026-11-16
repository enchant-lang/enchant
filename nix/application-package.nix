# Existing application.package producer, under a bounded release-build worker.
# PRoot supplies the FHS loader for unchanged portable drops inside the sandbox;
# it is a build adapter and is absent from the resulting application package.
{ pkgs, runtime, entry, searchPaths ? [] }:
let
  worker = import ./bounded-build.nix {
    inherit pkgs; memoryMiB = 4096; diskMiB = 16384; cpuCount = 2; trace = true;
  };
  produce = pkgs.writeText "produce-application-package.bl" ''
    (ns produce-application-package (:require [application.package :as package]))
    (let [result (package/build! "${entry}" (str (System/fetch_env! "out") "/library") [])]
      (println (pr-str (select-keys result [:built :artifacts :source-fallback]))))
    (System/halt 0)
  '';
in worker (pkgs.runCommand "beam-lisp-application-package" {
  nativeBuildInputs = [ pkgs.proot pkgs.coreutils ];
} ''
  export HOME=/build/home BL_DAEMON=off
  export ELIXIR_ERL_OPTIONS="+fnu +S 2:2 +SDcpu 1:1 +SDio 1"
  mkdir -p "$out" "$HOME" /build/fhs/lib64 /build/fhs/bin /build/fhs/usr/bin
  ln -s ${pkgs.glibc}/lib/ld-linux-x86-64.so.2 /build/fhs/lib64/ld-linux-x86-64.so.2
  ln -s ${pkgs.bash}/bin/sh /build/fhs/bin/sh
  ln -s ${pkgs.bash}/bin/bash /build/fhs/bin/bash
  ln -s ${pkgs.coreutils}/bin/env /build/fhs/usr/bin/env
  PROOT_NO_SECCOMP=1 proot -r /build/fhs \
    -b /nix/store -b /build -b /dev -b /proc -w /build \
    ${pkgs.coreutils}/bin/env \
    LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath (with pkgs; [ stdenv.cc.cc.lib zlib ncurses openssl brotli zstd ])} \
    ${runtime}/bin/bl --cold ${pkgs.lib.concatMapStringsSep " " (path: "-p ${pkgs.lib.escapeShellArg (toString path)}") searchPaths} run ${produce}
  rm "$out/library.package.lock"
'')
