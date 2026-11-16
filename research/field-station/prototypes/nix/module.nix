# Prototype host-binding contract. Candidate artifacts are catalogue data and
# closure roots; changing them must not change the stable owner's unit bytes.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.field-station;
  instanceType = lib.types.submodule ({ name, ... }: {
    options = {
      user = lib.mkOption { type = lib.types.str; default = "station-${name}"; };
      controller = lib.mkOption { type = lib.types.package; };
      stateDirectory = lib.mkOption { type = lib.types.str; default = "field-station/${name}"; };
      port = lib.mkOption { type = lib.types.port; };
      bootstrapCandidate = lib.mkOption { type = lib.types.str; };
      candidates = lib.mkOption { type = lib.types.attrsOf lib.types.package; default = {}; };
    };
  });
  binding = name: instance: pkgs.writeText "field-station-${name}-binding.json" (builtins.toJSON {
    version = 1;
    application = name;
    owner = instance.user;
    stateRoot = "/var/lib/${instance.stateDirectory}";
    initialCandidate = instance.bootstrapCandidate;
    catalogue = "/etc/field-station/${name}/candidates.json";
    inherit (instance) port;
  });
  units = lib.mapAttrs' (name: instance: lib.nameValuePair "field-station-${name}" {
    description = "Foundry lifecycle owner for ${name}";
    wantedBy = [ "multi-user.target" ];
    # Topology/owner/bootstrap changes need a controlled restart. Merely adding
    # a candidate does not change this binding or the stable controller.
    restartTriggers = [ (binding name instance) ];
    serviceConfig = {
      User = instance.user;
      Group = instance.user;
      ExecStart = "${instance.controller}/bin/station-controller /etc/field-station/${name}/binding.json";
      ExecStartPost = "${pkgs.curl}/bin/curl --fail --silent --show-error --output /dev/null --retry 300 --retry-connrefused --retry-delay 1 --retry-max-time 300 --max-time 2 http://127.0.0.1:${toString instance.port}/health/ready";
      TimeoutStartSec = 360;
      StateDirectory = instance.stateDirectory;
      StateDirectoryMode = "0700";
      RuntimeDirectory = "field-station-${name}";
      RuntimeDirectoryMode = "0700";
      Restart = "on-failure";
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      PrivateTmp = true;
      UMask = "0077";
    };
  }) cfg.instances;
  etc = lib.foldlAttrs (all: name: instance: all // {
    "field-station/${name}/binding.json".source = binding name instance;
    "field-station/${name}/candidates.json".text = builtins.toJSON {
      version = 1;
      candidates = lib.mapAttrs (_: artifact: toString artifact) instance.candidates;
    };
  }) {} cfg.instances;
in {
  options.services.field-station.instances = lib.mkOption {
    type = lib.types.attrsOf instanceType;
    default = {};
    description = "Host bindings for independently owned Foundry applications";
  };
  config = lib.mkIf (cfg.instances != {}) {
    assertions = lib.mapAttrsToList (name: instance: {
      assertion = builtins.match "[a-z][a-z0-9-]{0,47}" name != null
        && builtins.match "[a-z][a-z0-9-]{0,47}" instance.user != null
        && instance.stateDirectory == "field-station/${name}"
        && builtins.match "[0-9a-f]{64}" instance.bootstrapCandidate != null
        && builtins.hasAttr instance.bootstrapCandidate instance.candidates
        && lib.all (id: builtins.match "[0-9a-f]{64}" id != null) (builtins.attrNames instance.candidates);
      message = "Field Station instance ${name}: invalid host binding or missing bootstrap artifact";
    }) cfg.instances;
    users.groups = lib.mapAttrs' (_: instance: lib.nameValuePair instance.user {}) cfg.instances;
    users.users = lib.mapAttrs' (_: instance: lib.nameValuePair instance.user {
      isSystemUser = true;
      group = instance.user;
    }) cfg.instances;
    systemd.services = units;
    environment.etc = etc;
    system.extraDependencies = lib.concatMap (instance: builtins.attrValues instance.candidates)
      (builtins.attrValues cfg.instances);
  };
}
