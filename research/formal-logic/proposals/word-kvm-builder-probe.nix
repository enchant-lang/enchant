# Capability observation inside an actual Nix build sandbox. A feature label
# alone is insufficient: open the device and create/close an empty KVM VM.
let
  lock = builtins.fromJSON (builtins.readFile ../../../flake.lock);
  pkgs = import (builtins.fetchTree lock.nodes.nixpkgs.locked).outPath { system = "x86_64-linux"; };
in pkgs.runCommand "formal-word-kvm-sandbox-probe-20261113" {
  nativeBuildInputs = [ pkgs.python3 ];
  requiredSystemFeatures = [ "kvm" ];
} ''
  python3 - "$out" <<'PY'
  import datetime, fcntl, json, os, pathlib, stat, sys
  assert stat.S_ISCHR(os.stat('/dev/kvm').st_mode)
  device = os.open('/dev/kvm', os.O_RDWR | os.O_CLOEXEC)
  try:
      version = fcntl.ioctl(device, 0xAE00, 0)
      assert version == 12
      machine = fcntl.ioctl(device, 0xAE01, 0)
      os.close(machine)
  finally:
      os.close(device)
  pathlib.Path(sys.argv[1]).write_text(json.dumps({
      'schema': 'bl.kvm-sandbox-capability.v1', 'status': 'passed',
      'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'api_version': version, 'device_opened_read_write': True,
      'empty_vm_created_and_closed': True,
      'scope': 'Actual Nix sandbox device access, API query and empty VM creation. No guest or compiler was run by this probe.'
  }, indent=2) + '\n')
  PY
''
