# Evaluation-only tests use inert derivations. They do not claim a booted unit
# or packaged controller acceptance; the real native lifecycle has its own gate.
{ nixpkgs }:
let
  pkgs = import nixpkgs { system = "x86_64-linux"; };
  lib = pkgs.lib;
  old = builtins.concatStringsSep "" (builtins.genList (_: "a") 64);
  fresh = builtins.concatStringsSep "" (builtins.genList (_: "b") 64);
  controller = pkgs.writeShellScriptBin "station-controller" ''
    echo 'evaluation fixture: this controller must never be started' >&2
    exit 77
  '';
  artifact = label: pkgs.runCommand "field-station-eval-${label}" {} ''mkdir "$out"'';
  candidateA = artifact "old";
  candidateB = artifact "new";
  base = {
    messages = { inherit controller; port = 18891; bootstrapCandidate = old; candidates.${old} = candidateA; };
  };
  evaluate = instances: (import (nixpkgs + "/nixos/lib/eval-config.nix") {
    system = "x86_64-linux";
    modules = [ ./module.nix ({ ... }: {
      system.stateVersion = "26.11";
      services.field-station.instances = instances;
    }) ];
  }).config;
  baseline = evaluate base;
  appended = evaluate (base // { messages = base.messages // {
    candidates = base.messages.candidates // { ${fresh} = candidateB; };
  }; });
  changedPort = evaluate (base // { messages = base.messages // { port = 18892; }; });
  invalid = evaluate (base // { messages = base.messages // { stateDirectory = "../foreign"; }; });
  service = c: c.systemd.services.field-station-messages;
  # NixOS assertion messages are intentionally lazy and may reference fields
  # that exist only on failure. Never force messages for successful assertions.
  invalidInstance = c: lib.any (a: !a.assertion && lib.hasPrefix "Field Station instance" a.message) c.assertions;
in
assert (service baseline).serviceConfig.ExecStart == (service appended).serviceConfig.ExecStart;
assert (service baseline).restartTriggers == (service appended).restartTriggers;
assert (service baseline).restartTriggers != (service changedPort).restartTriggers;
assert !(invalidInstance baseline);
assert invalidInstance invalid;
assert baseline.environment.etc."field-station/messages/candidates.json".text
  != appended.environment.etc."field-station/messages/candidates.json".text;
assert builtins.elem candidateB appended.system.extraDependencies;
assert (service baseline).serviceConfig.User == "station-messages";
assert (service baseline).serviceConfig.StateDirectoryMode == "0700";
assert lib.hasInfix "/health/ready" (service baseline).serviceConfig.ExecStartPost;
{
  version = 1;
  kind = "field-station-nixos-module-evaluation";
  passed = 10;
  checks = [
    "candidate addition preserves stable ExecStart"
    "candidate addition preserves restart triggers"
    "topology change changes restart triggers"
    "valid host binding passes assertions"
    "parent traversal binding fails assertions"
    "candidate catalogue changes independently"
    "candidate artifact belongs to the host closure"
    "service runs under a dedicated identity"
    "service state is private"
    "start job checks HTTP readiness"
  ];
  scope = "Actual NixOS module evaluation; inert package fixtures. No build, boot, VM or production activation.";
}
