# Kernel UID, host mapping and filesystem admission are independent controls.
{ pkgs, sdk }:
let
  installedSdk = if builtins.isPath sdk || builtins.isString sdk
    then builtins.storePath (toString sdk) else sdk;
  client = user: mode:
    "su - ${user} -c '${installedSdk}/bin/bl --cold run ${./unix-identity-client.bl} -- ${mode}' 2>&1";
in pkgs.testers.runNixOSTest {
  name = "beam-lisp-unix-kernel-identity";
  nodes.machine = { ... }: {
    system.stateVersion = "25.05";
    users.groups.rpc-client.gid = 2000;
    users.users.alice = { isNormalUser = true; uid = 1000; extraGroups = [ "rpc-client" ]; };
    users.users.bob = { isNormalUser = true; uid = 1001; extraGroups = [ "rpc-client" ]; };
    users.users.eve = { isNormalUser = true; uid = 1002; extraGroups = [ "rpc-client" ]; };
    users.users.outsider = { isNormalUser = true; uid = 1003; };
    systemd.tmpfiles.rules = [ "d /run/peercheck 2750 root rpc-client -" ];
    systemd.services.peercheck = {
      wantedBy = [ "multi-user.target" ];
      environment.HOME = "/var/lib/peercheck";
      serviceConfig = {
        ExecStart = "${installedSdk}/bin/bl --cold run ${./unix-identity-server.bl}";
        RuntimeMaxSec = 180;
        Group = "rpc-client";
        StateDirectory = "peercheck";
        StateDirectoryMode = "0700";
      };
    };
    virtualisation.memorySize = 2048;
    virtualisation.cores = 2;
  };
  testScript = ''
    import json
    machine.start()
    machine.wait_for_unit("peercheck.service")
    machine.wait_for_file("/run/peercheck/ready", timeout=60)
    metadata = machine.succeed("stat -c %u:%g:%a /run/peercheck/socket").strip()
    assert metadata == "0:2000:660", metadata
    with subtest("filesystem permission denies an unenrolled Unix group"):
        outsider = machine.succeed("${client "outsider" "filesystem-denied"}", timeout=60).strip()
        assert outsider == "filesystem-denied", repr(outsider)
    with subtest("payload cannot impersonate root and each kernel UID maps separately"):
        alice = json.loads(machine.succeed("${client "alice" "request"}", timeout=60))
        bob = json.loads(machine.succeed("${client "bob" "request"}", timeout=60))
        assert alice == {"ok": True, "uid": 1000, "subject": "person:alice", "application": "messages"}
        assert bob == {"ok": True, "uid": 1001, "subject": "person:bob", "application": "messages"}
    with subtest("socket access alone does not grant an account"):
        eve = json.loads(machine.succeed("${client "eve" "request"}", timeout=60))
        assert eve == {"ok": False}
    machine.wait_until_succeeds("test \"$(systemctl show -p ActiveState --value peercheck.service)\" = inactive", timeout=30)
    machine.succeed("test \"$(systemctl show -p MainPID --value peercheck.service)\" = 0")
    machine.succeed("test \"$(systemctl show -p Result --value peercheck.service)\" = success")
    machine.fail("test -e /run/peercheck/socket")
  '';
}
