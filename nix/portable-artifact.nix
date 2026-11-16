# A finite operation: package the selected SDK's exact native image.
{ sdk }:
let
  lock = builtins.fromJSON (builtins.readFile ../flake.lock);
  pkgs = import (builtins.fetchTree lock.nodes.nixpkgs.locked).outPath { system = "x86_64-linux"; };
  selected = builtins.fromJSON (builtins.unsafeDiscardStringContext
    (builtins.readFile (builtins.storePath sdk + "/artifact.json")));
  image = builtins.storePath selected.image;
  # Installed producers carry this receipt beside nix/. In a checkout, use
  # the selected SDK's producer receipt rather than rebuilding current tools.
  toolsReceipt = if builtins.pathExists ../portable-tools.json then ../portable-tools.json
    else builtins.storePath selected.platform + "/artifact-platform/portable-tools.json";
  tools = builtins.storePath (builtins.fromJSON (builtins.unsafeDiscardStringContext
    (builtins.readFile toolsReceipt))).tools;
in
assert builtins.match "/nix/store/[0-9a-z]{32}-[^/]+" sdk != null;
assert selected.version == 1 && selected.kind == "sdk";
import ./portable-product.nix { inherit pkgs image tools; }
