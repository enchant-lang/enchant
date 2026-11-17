# Privileged host commands must use PID 1, without relying on a root user bus.
{ pkgs, tools }:
let
  controls = pkgs.runCommand "beam-lisp-command-stream-controls" {} ''
    mkdir -p "$out"
    cp ${../scripts/test_command_domain.py} "$out/test_command_domain.py"
    cp ${../scripts/test_command_stream.py} "$out/test_command_stream.py"
  '';
in pkgs.testers.runNixOSTest {
  name = "beam-lisp-root-command-stream";
  nodes.machine = { ... }: {
    system.stateVersion = "25.05";
    environment.systemPackages = [ pkgs.python3 pkgs.systemd tools ];
    virtualisation.memorySize = 1024;
    virtualisation.cores = 2;
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    with subtest("root has no user manager"):
        machine.fail("systemctl --user is-system-running")
    with subtest("credits and descendant custody through the system manager"):
        machine.succeed("BL_CUSTODY_EXECUTOR=${tools}/bin/bl-command-executor ${pkgs.python3}/bin/python3 -m unittest discover -s ${controls} -p test_command_stream.py -v", timeout=90)
    with subtest("all fixture command domains have stopped"):
        machine.succeed("test -z \"$(systemctl list-units --state=running --no-legend 'bl-custody-*')\"")
  '';
}
