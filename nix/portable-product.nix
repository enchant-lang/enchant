# Portable packaging is a separate product of the exact native image.
# Selecting an SDK cannot realize this derivation or run its ELF mutations.
{ pkgs, image, tools }:
let
  # Keep derivation dependencies intact for a cold flake. Reading the image
  # descriptor here would build the SDK during evaluation, even with --no-build.
  imagePath = image;
  toolsPath = tools;
  worker = import ./bounded-build.nix {
    inherit pkgs; memoryMiB = 4096; diskMiB = 16384; cpuCount = 2;
    commandManager = false; trace = true;
  };
in
worker (pkgs.runCommand "beam-lisp-portable-release" {
  nativeBuildInputs = [ pkgs.patchelf pkgs.python3 pkgs.coreutils ];
} ''
  sdk_phase_start() { sdk_phase_label=$1; sdk_phase_started=$(date +%s%N); }
  sdk_phase_end() {
    local elapsed=$(( ($(date +%s%N) - sdk_phase_started) / 1000 ))
    printf 'SDK-SHELL-PHASE {"stage":"%s","elapsed-us":%s}\n' "$sdk_phase_label" "$elapsed"
  }
  sdk_phase_start materialize-native-image
  cp -a --reflink=auto --no-preserve=ownership ${imagePath}/payload "$TMPDIR/payload"
  chmod -R u+w "$TMPDIR/payload"
  cp ${toolsPath}/bin/drop-launcher "$TMPDIR/launcher"
  cp ${toolsPath}/bin/drop "$TMPDIR/drop"
  chmod u+w "$TMPDIR/launcher"
  patchelf --set-interpreter /lib64/ld-linux-x86-64.so.2 --remove-rpath "$TMPDIR/launcher"
  sdk_phase_end
  sdk_phase_start portable-retarget
  # A portable drop carries bytes rather than references to its build store.
  for native in $TMPDIR/payload/lib/beam_lisp-*/priv/native/*.so; do
    if [ -L "$native" ]; then
      cp --dereference "$native" "$native.materialized"
      mv "$native.materialized" "$native"
    fi
  done
  ${pkgs.python3}/bin/python3 - <<'PORTABLE'
  import json, os
  import hashlib
  from pathlib import Path
  import subprocess
  patcher = '${pkgs.patchelf}/bin/patchelf'
  counts = dict(files=0, elf=0, interpreters=0)
  for manifest in (Path(os.environ['TMPDIR']) / 'payload/lib').glob('beam_lisp-*/priv/formal/artifact.json'):
      metadata = json.loads(manifest.read_text())
      if metadata.get('packaging') != 'nix' or metadata['worker']['path'] != 'bin/formal-worker' or metadata['z3']['path'] != '../z3/bin/libz3.so':
          raise SystemExit('unexpected native formal worker paths')
      for field in ('worker', 'z3'):
          row = metadata[field]
          if hashlib.sha256((manifest.parent / row['path']).read_bytes()).hexdigest() != row['sha256']:
              raise SystemExit('formal worker producer bytes differ before relocation')
  for path in (Path(os.environ['TMPDIR']) / 'payload').rglob('*'):
      if path.is_symlink() or not path.is_file():
          continue
      counts['files'] += 1
      with path.open('rb') as stream:
          marker = stream.read(4)
          first = marker + stream.readline(4092) if marker.startswith(b'#!') else marker
      if marker == b'\x7fELF':
          counts['elf'] += 1
          dynamic = subprocess.run([patcher, '--print-interpreter', path],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
          if dynamic:
              subprocess.run([patcher, '--set-interpreter', '/lib64/ld-linux-x86-64.so.2',
                              '--remove-rpath', path], check=True)
          else:
              subprocess.run([patcher, '--remove-rpath', path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      elif first.startswith(b'#!') and b'/nix/store/' in first:
          interpreter = first.strip().split()[0].rsplit(b'/', 1)[-1]
          if interpreter not in (b'sh', b'bash', b'dash'):
              raise SystemExit(f'undeclared portable interpreter: {path}: {first!r}')
          replacement = b'#!/bin/bash\n' if interpreter == b'bash' else b'#!/bin/sh\n'
          path.write_bytes(replacement + path.read_bytes()[len(first):])
          counts['interpreters'] += 1
  # ELF relocation changes file identity. Preserve the producer's hashes and
  # bind the installed descriptor to the actual portable payload bytes.
  for manifest in (Path(os.environ['TMPDIR']) / 'payload/lib').glob('beam_lisp-*/priv/formal/artifact.json'):
      metadata = json.loads(manifest.read_text())
      if (metadata.get('version'), metadata.get('kind'), metadata.get('protocol'), metadata.get('packaging')) != (1, 'formal-worker', 1, 'nix'):
          raise SystemExit('unexpected formal worker descriptor before relocation')
      if metadata['worker']['path'] != 'bin/formal-worker' or metadata['z3']['path'] != '../z3/bin/libz3.so':
          raise SystemExit('unexpected formal worker payload paths')
      for field in ('worker', 'z3'):
          row = metadata[field]
          row['producer_sha256'] = row['sha256']
          row['sha256'] = hashlib.sha256((manifest.parent / row['path']).read_bytes()).hexdigest()
      metadata['packaging'] = 'portable-shell-v1'
      manifest.write_text(json.dumps(metadata, sort_keys=True) + '\n')
  print('PORTABLE-PAYLOAD ' + json.dumps(counts), flush=True)
  PORTABLE
  sdk_phase_end
  sdk_phase_start pack-portable
  $TMPDIR/drop pack --release $TMPDIR/payload --launcher $TMPDIR/launcher --out $TMPDIR/bl.drop
  sdk_phase_end

  mkdir -p "$out"
  cp "$TMPDIR/bl.drop" "$out/bl.drop"
  ${pkgs.python3}/bin/python3 - <<'RECEIPT'
  import hashlib, json, os
  from pathlib import Path
  output = Path(os.environ['out'])
  image = Path('${imagePath}')
  metadata = json.loads((image / 'artifact.json').read_text())
  assert (metadata['version'], metadata['kind'], metadata['target']) == (1, 'sdk', 'x86_64-linux')
  descriptor = dict(version=1, kind='release', packaging='portable-shell-v1',
                    compiler=metadata['compiler'], target=metadata['target'],
                    image=str(image), file='bl.drop')
  with (output / 'bl.drop').open('rb') as stream:
      descriptor['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
  (output / 'artifact.json').write_text(json.dumps(descriptor, sort_keys=True) + '\n')
  RECEIPT
'')
