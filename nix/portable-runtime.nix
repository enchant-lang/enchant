# Invoke unchanged portable bytes on NixOS. The raw artifact remains available
# for consumers that attest the actual compound executable rather than a wrapper.
{ pkgs, release ? null, artifact ? null }:
let
  executable = if artifact != null then artifact else pkgs.runCommand "beam-lisp-portable-executable" {
    __structuredAttrs = true;
    nativeBuildInputs = [ pkgs.jq pkgs.coreutils ];
    # Image/compiler paths in the copied receipt describe the producer. They
    # are not receiver dependencies: the portable payload carries its runtime.
    # Keep the bytes/digest intact; the wrapper below declares the host ABI.
    unsafeDiscardReferences.out = true;
    outputChecks.out.allowedReferences = [];
  } ''
    test "$(jq -er '.version == 1 and .kind == "release" and .packaging == "portable-shell-v1" and .target == "x86_64-linux" and .file == "bl.drop"' ${release}/artifact.json)" = true
    test "$(sha256sum ${release}/bl.drop | cut -d' ' -f1)" = "$(jq -er .sha256 ${release}/artifact.json)"
    install -Dm555 ${release}/bl.drop "$out/bin/bl"
    install -Dm444 ${release}/artifact.json "$out/share/beam-lisp/artifact.json"
  '';
  # Hosts may retain the already checked standalone executable rather than a
  # producer release whose provenance still names a whole SDK. Verify its
  # unchanged bytes once at realization; do not hash a drop on every CLI call.
  verification = if artifact == null then executable else pkgs.runCommand "beam-lisp-portable-artifact-verification" {
    nativeBuildInputs = [ pkgs.jq pkgs.coreutils ];
  } ''
    metadata=${artifact}/share/beam-lisp/artifact.json
    test "$(jq -er '.version == 1 and .kind == "release" and .packaging == "portable-shell-v1" and .target == "x86_64-linux" and .file == "bl.drop"' "$metadata")" = true
    test "$(sha256sum ${artifact}/bin/bl | cut -d' ' -f1)" = "$(jq -er .sha256 "$metadata")"
    touch "$out"
  '';
  libraries = pkgs.lib.makeLibraryPath (with pkgs; [ stdenv.cc.cc.lib zlib ncurses openssl brotli zstd ]);
  runtime = (pkgs.writeShellApplication {
  name = "bl";
  text = ''
    test -e ${verification}
    export NIX_LD=${pkgs.glibc}/lib/ld-linux-x86-64.so.2
    export NIX_LD_LIBRARY_PATH="${libraries}''${NIX_LD_LIBRARY_PATH:+:$NIX_LD_LIBRARY_PATH}"
    export ELIXIR_ERL_OPTIONS="''${ELIXIR_ERL_OPTIONS:-+S 2:2 +SDcpu 1:1 +SDio 1}"
    exec ${executable}/bin/bl "$@"
  '';
  }) // {
    releaseArtifact = executable;
    packageApplication = args: import ./application-package.nix (args // { inherit pkgs runtime; });
  };
in assert (release == null) != (artifact == null); runtime
