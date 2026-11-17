# Exercise the same root user manager used by immutable SDK production.
{ pkgs, tools }:
(import ../../nix/bounded-build.nix { inherit pkgs; commandManager = true; })
(pkgs.runCommand "beam-lisp-worker-command-stream" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  test ! -S /run/dbus/system_bus_socket
  test -S /run/user/0/bus
  mkdir controls
  cp ${../scripts/test_command_domain.py} controls/test_command_domain.py
  cp ${../scripts/test_command_stream.py} controls/test_command_stream.py
  BL_CUSTODY_EXECUTOR=${tools}/bin/bl-command-executor \
    python3 -m unittest discover -s controls -p test_command_stream.py -v
  mkdir "$out"
'')
