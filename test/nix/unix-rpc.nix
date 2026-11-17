{ pkgs, sdk }:
let
  installedSdk = if builtins.isPath sdk || builtins.isString sdk
    then builtins.storePath (toString sdk) else sdk;
  sources = ../../research/field-station/prototypes/src;
  contract = ../../research/field-station/prototypes/src/station_prototype/messages.bl;
  client = user: mode:
    "su - ${user} -c '${installedSdk}/bin/bl --cold run ${./unix-rpc-client.bl} -- ${mode} ${contract}'";
in pkgs.testers.runNixOSTest {
  name = "beam-lisp-native-unix-rpc-datom";
  nodes.machine = { ... }: {
    system.stateVersion = "25.05";
    users.groups.rpc-client.gid = 2000;
    users.users.alice = { isNormalUser = true; uid = 1000; extraGroups = [ "rpc-client" ]; };
    users.users.bob = { isNormalUser = true; uid = 1001; extraGroups = [ "rpc-client" ]; };
    users.users.eve = { isNormalUser = true; uid = 1002; extraGroups = [ "rpc-client" ]; };
    users.users.outsider = { isNormalUser = true; uid = 1003; };
    systemd.tmpfiles.rules = [ "d /run/rpccheck 2750 root rpc-client -" ];
    systemd.services.rpccheck = {
      wantedBy = [ "multi-user.target" ];
      environment.HOME = "/var/lib/rpccheck";
      serviceConfig = {
        ExecStart = "${installedSdk}/bin/bl --cold -p ${sources} run ${./unix-rpc-server.bl} -- ${contract}";
        RuntimeMaxSec = 240;
        Group = "rpc-client";
        StateDirectory = "rpccheck";
        StateDirectoryMode = "0700";
      };
    };
    virtualisation.memorySize = 2048;
    virtualisation.cores = 2;
  };
  testScript = ''
    import json
    machine.start()
    machine.wait_for_unit("rpccheck.service")
    machine.wait_for_file("/run/rpccheck/ready", timeout=90)
    assert machine.succeed("stat -c %u:%g:%a /run/rpccheck/socket").strip() == "0:2000:660"
    with subtest("socket group and Datom account lookup deny independently"):
        machine.fail("${client "outsider" "inbox"}", timeout=60)
        eve = json.loads(machine.succeed("${client "eve" "inbox"}", timeout=60))
        assert eve == {"protocol": "enchant.rpc.unix/1", "error": "unauthenticated"}, eve
    with subtest("actual accounts see distinct checked Datom inboxes"):
        alice = json.loads(machine.succeed("${client "alice" "inbox"}", timeout=60))
        bob = json.loads(machine.succeed("${client "bob" "inbox"}", timeout=60))
        assert alice["value"]["ok"] == [["alice-message", 1, "Alice native inbox"]], alice
        assert bob["value"]["ok"] == [["bob-message", 2, "Bob native inbox"]], bob
    with subtest("current resource policy refuses another workspace"):
        denied = json.loads(machine.succeed("${client "bob" "private"}", timeout=60))
        assert denied["value"]["error"]["code"] == "auth/denied", denied
        forged = json.loads(machine.succeed("${client "bob" "forged"}", timeout=60))
        assert forged["value"]["error"]["code"] == "auth/malformed", forged
    with subtest("accepted claim commits a native writer receipt"):
        claim = json.loads(machine.succeed("${client "alice" "claim"}", timeout=60))
        assert claim["value"]["ok"][:2] == ["alice-message", "alice"], claim
    machine.wait_until_succeeds("test \"$(systemctl show -p ActiveState --value rpccheck.service)\" = inactive", timeout=30)
    machine.succeed("test \"$(systemctl show -p Result --value rpccheck.service)\" = success")
    machine.succeed("test \"$(systemctl show -p MainPID --value rpccheck.service)\" = 0")
    machine.fail("test -e /run/rpccheck/socket")
  '';
}
