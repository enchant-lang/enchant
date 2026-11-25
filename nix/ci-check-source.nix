# The immutable source a CI check (and a check host's SDK) is built from: the
# engine and test roots of a captured checkout, without recorded research
# evidence (2.2 GB no check reads; scripts/ci-source.py EXCLUDED matches) and
# without the products a checkout keeps beside its source.
{ source }:
let
  root = /. + source;
  roots = builtins.filter (name: builtins.pathExists (root + "/${name}")) [
    ".gitignore" ".github" "AGENTS.md" "README.md" "README.bl.org" "examples" "bin" "nix" "scripts"
    "test" "priv" "native" "tooling/drop" "tooling/build-backends" "packages/job-runner"
    "docs" "research" "optional/browser-port/bl" "optional/browser-port/test" "env.bl" "bl.lock" "flake.nix" "flake.lock"
    "rust-toolchain" "rust-toolchain.toml"
  ];
in import ./project-source.nix {
  inherit source;
  rootsJson = builtins.toJSON roots;
  excludedJson = builtins.toJSON [ "research/formal-logic/evidence" "priv/native" "priv/z3" "priv/codegen.sources"
    "priv/precompiled.term" "priv/sdk-code.term" ];
}
