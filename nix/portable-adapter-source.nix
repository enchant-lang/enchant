# A receiver can retain the small Nix adapter without retaining an SDK tree.
# The qualified portable image is a separate immutable input.
{ pkgs }:
pkgs.lib.fileset.toSource {
  root = ../.;
  fileset = pkgs.lib.fileset.unions [
    ./portable-runtime.nix ./application-package.nix ./bounded-build.nix
  ];
}
