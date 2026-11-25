# N4d (scripts/dev-sdk): a DEVELOPMENT SDK, assembled on Work without QEMU or the producer.
#
# `scripts/dev-sdk` compiles the edited pinned host units with the base SDK's
# own compiler and writes the few floor files such an edit changes into
# `delta/files/` (paths relative to the image's `beam_lisp-0.1.0`). This
# derivation links every other file of the qualified base SDK by reference and
# writes the launch scripts for its own path. It is never a release, published
# or predecessor product: artifact.json carries `dev`, and
# `scripts/prepare-checkout-sdk`, `nix/bl-drop.nix`, `scripts/ci-check` and
# `scripts/ci-host-nix-check` refuse it.
#
# mode = "source": the engine tree captured exactly as nix/sdk-source.nix's
# `captured` (same filter), without importing nixpkgs, so the selection record
# names immutable bytes whose fingerprint equals the tree's.
{ mode ? "sdk", root ? null, base ? null, delta ? null, python ? null }:
let
  storeObject = value: builtins.isString value
    && builtins.match "/nix/store/[0-9a-z]{32}-[^/]+" value != null;
  hasPrefix = prefix: text: builtins.substring 0 (builtins.stringLength prefix) text == prefix;
  under = parent: child: parent == child || hasPrefix (parent + "/") child;
  source =
    let
      path = /. + root;
      text = toString path;
      policy = builtins.fromJSON (builtins.readFile (path + "/nix/engine-inputs.json"));
    in
    assert policy.version == 1;
    builtins.path {
      name = "beam-lisp-engine-source";
      inherit path;
      filter = file: type:
        let
          full = toString file;
          relative = if full == text then "." else builtins.substring (builtins.stringLength text + 1) (builtins.stringLength full) full;
          reserved = builtins.elem (baseNameOf file) policy.reserved
            || (baseNameOf file == "target" && builtins.any (entry: under entry relative) policy.targetRoots)
            || builtins.any (entry: under entry relative) policy.excluded;
          selected = builtins.any (entry: under entry relative || under relative entry) policy.roots;
        in if relative == "." then true
           else if reserved || !selected then false
           else if type == "symlink" then throw "Engine production requires a self-contained source tree"
           else if type == "directory" || type == "regular" then true
           else throw "Engine production rejects special inputs";
    };
  sdk =
    assert storeObject base && storeObject python;
    let
      selection = builtins.storePath base;
      metadata = builtins.fromJSON (builtins.unsafeDiscardStringContext
        (builtins.readFile (selection + "/artifact.json")));
    in
    assert metadata.kind == "sdk" && !(metadata ? dev);
    derivation {
      name = "beam-lisp-dev-sdk";
      system = "x86_64-linux";
      builder = builtins.storePath python + "/bin/python3";
      args = [ "-I" ./dev-sdk-builder.py ];
      inherit selection;
      image = builtins.storePath metadata.image;
      coordinator = builtins.storePath metadata.coordinator;
      delta = builtins.path { path = /. + delta; name = "beam-lisp-dev-sdk-delta"; };
      # Linking only: never forward this to a remote builder or substitute it.
      preferLocalBuild = true;
      allowSubstitutes = false;
    };
in
assert builtins.elem mode [ "source" "sdk" ];
if mode == "source" then source else sdk
