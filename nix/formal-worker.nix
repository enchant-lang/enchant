# A port executable, independently retained from the NIF product set.
{ pkgs, root ? ../. }:
let
  lib = pkgs.lib;
  source = lib.fileset.toSource {
    root = root + "/native/ports/formal_worker";
    fileset = lib.fileset.unions (map (name: root + "/native/ports/formal_worker/${name}")
      [ "Cargo.toml" "Cargo.lock" "src" ]);
  };
  manifest = builtins.fromTOML (builtins.readFile (source + "/Cargo.toml"));
  lock = source + "/Cargo.lock";
  cargoDeps = pkgs.rustPlatform.importCargoLock { lockFile = lock; };
  bounded = import ./bounded-build.nix {
    inherit pkgs;
    memoryMiB = 4096;
    diskMiB = 16384;
    cpuCount = 2;
    trace = true;
  };
  compiled = bounded (pkgs.rustPlatform.buildRustPackage {
    pname = manifest.package.name;
    inherit (manifest.package) version;
    src = source;
    cargoLock.lockFile = lock;
    inherit cargoDeps;
    cargoBuildFlags = [ "--bin" "formal-worker" ];
    CARGO_BUILD_JOBS = "1";
    doCheck = false;
    strictDeps = true;
    nativeBuildInputs = [ pkgs.python3 ];
    postFixup = ''
      cp ${lock} "$out/Cargo.lock"
      python3 - "$out" "$cargoDeps" <<'PY'
      import hashlib, json, os, pathlib, sys, tomllib
      output, vendor = map(pathlib.Path, sys.argv[1:])
      records = []
      for directory, folders, files in os.walk(vendor, followlinks=True):
          directory = pathlib.Path(directory)
          if 'Cargo.toml' not in files:
              continue
          metadata = tomllib.loads((directory / 'Cargo.toml').read_text()).get('package', {})
          if not isinstance(metadata.get('name'), str) or not isinstance(metadata.get('version'), str):
              continue
          destination = output / 'notices' / (metadata['name'] + '-' + metadata['version'])
          destination.mkdir(parents=True, exist_ok=True)
          names = set(name for name in files if name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE', 'COPYRIGHT')))
          if isinstance(metadata.get('license-file'), str):
              names.add(metadata['license-file'])
          copied = []
          for name in sorted(names):
              path = (directory / name).resolve()
              if not path.is_relative_to(directory.resolve()) or not path.is_file():
                  raise ValueError('notice escapes its vendored crate: ' + name)
              target = destination / name
              target.parent.mkdir(parents=True, exist_ok=True)
              target.write_bytes(path.read_bytes())
              copied.append(name)
          records.append(dict(name=metadata['name'], version=metadata['version'],
                              license=metadata.get('license'), files=copied))
      (output / 'notices.json').write_text(json.dumps(sorted(records, key=lambda x: (x['name'], x['version'])), sort_keys=True) + '\n')
      worker = output / 'bin/formal-worker'
      descriptor = dict(version=1, kind='formal-worker', protocol=1, target='x86_64-linux',
          source='${source}', package='${manifest.package.name}', package_version='${manifest.package.version}',
          cargo_lock_sha256=hashlib.sha256((output / 'Cargo.lock').read_bytes()).hexdigest(),
          features=['oxiz-core/std', 'oxiz-solver/std'], oxiz_version='0.3.4',
          toolchain=dict(rustc='${pkgs.rustc.version}', identity='${pkgs.rustc}'),
          worker=dict(path='bin/formal-worker', sha256=hashlib.sha256(worker.read_bytes()).hexdigest()),
          bounds=dict(memory_kib=int(os.environ['BL_WORKER_MEMORY_KIB']), swap_kib=int(os.environ['BL_WORKER_SWAP_KIB'])))
      (output / 'artifact.json').write_text(json.dumps(descriptor, sort_keys=True) + '\n')
      PY
    '';
  });
in pkgs.lib.overrideDerivation compiled (old: {
  # Test the real device inside this build sandbox before asking QEMU to run.
  # Declared builder features cannot substitute for actual KVM access.
  preVM = ''
    ${pkgs.python3}/bin/python3 - <<'PY'
    import fcntl, os
    descriptor = os.open('/dev/kvm', os.O_RDWR | os.O_CLOEXEC)
    try:
        version = fcntl.ioctl(descriptor, 0xAE00)
        if version != 12:
            raise SystemExit('formal worker requires KVM API 12')
        print('FORMAL-WORKER-KVM-ACCESS api=' + str(version), flush=True)
    finally:
        os.close(descriptor)
    PY
  '' + old.preVM;
})
