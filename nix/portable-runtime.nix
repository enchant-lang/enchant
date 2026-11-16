# Invoke unchanged portable bytes on NixOS. The raw artifact remains available
# for consumers that attest the actual compound executable rather than a wrapper.
{ pkgs, release }:
let
  executable = pkgs.runCommand "beam-lisp-portable-executable" {
    nativeBuildInputs = [ pkgs.jq pkgs.coreutils ];
  } ''
    test "$(jq -er '.version == 1 and .kind == "release" and .packaging == "portable-shell-v1" and .file == "bl.drop"' ${release}/artifact.json)" = true
    test "$(sha256sum ${release}/bl.drop | cut -d' ' -f1)" = "$(jq -er .sha256 ${release}/artifact.json)"
    install -Dm555 ${release}/bl.drop "$out/bin/bl"
    install -Dm444 ${release}/artifact.json "$out/share/beam-lisp/artifact.json"
  '';
  libraries = pkgs.lib.makeLibraryPath (with pkgs; [ stdenv.cc.cc.lib zlib ncurses openssl brotli zstd ]);
in
(pkgs.writeShellApplication {
  name = "bl";
  text = ''
    export NIX_LD=${pkgs.glibc}/lib/ld-linux-x86-64.so.2
    export NIX_LD_LIBRARY_PATH="${libraries}''${NIX_LD_LIBRARY_PATH:+:$NIX_LD_LIBRARY_PATH}"
    export ELIXIR_ERL_OPTIONS="''${ELIXIR_ERL_OPTIONS:-+S 2:2 +SDcpu 1:1 +SDio 1}"
    exec ${executable}/bin/bl "$@"
  '';
}) // { releaseArtifact = executable; }
