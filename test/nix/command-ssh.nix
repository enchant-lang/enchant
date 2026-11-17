# No production endpoint or credential. The guest creates its own keypair.
{ pkgs, sdk, portable ? false }:
let
  # Preserve the installed SDK's closure instead of copying only its directory.
  installedSdk = if builtins.isPath sdk || builtins.isString sdk
    then builtins.storePath (toString sdk) else sdk;
  responder = pkgs.writeShellScript "command-ssh-responder" ''
  if [ "$SSH_ORIGINAL_COMMAND" != upgrade ]; then exit 64; fi
  exec ${pkgs.coreutils}/bin/cat
'';
in pkgs.testers.runNixOSTest {
  name = if portable then "beam-lisp-portable-command-ssh" else "beam-lisp-native-command-ssh";
  nodes.machine = { ... }: {
    system.stateVersion = "25.05";
    programs.nix-ld.enable = portable;
    services.openssh.enable = true;
    services.openssh.settings.PermitRootLogin = "prohibit-password";
    environment.systemPackages = [ pkgs.openssh ];
    virtualisation.memorySize = 1536;
    virtualisation.cores = 2;
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("sshd.service")
    machine.succeed("install -dm700 /root/.ssh")
    machine.succeed("ssh-keygen -q -t ed25519 -N \"\" -f /root/command-key")
    machine.succeed("sed 's|^|restrict,command=\"${responder}\" |' /root/command-key.pub > /root/.ssh/authorized_keys")
    machine.succeed("ssh-keyscan -t ed25519 127.0.0.1 > /root/known-hosts")
    machine.succeed("touch /root/empty-known-hosts")
    with subtest("installed SDK sends binary stdin over real strict SSH"):
        machine.succeed("${installedSdk}/bin/bl --cold run ${./command-ssh.bl} -- ${pkgs.openssh}/bin/ssh", timeout=90)
    with subtest("all managed local transport domains have stopped"):
        machine.succeed("test -z \"$(systemctl list-units --state=running --no-legend 'bl-custody-*')\"")
  '';
}
