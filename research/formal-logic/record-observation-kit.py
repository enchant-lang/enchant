"""Freeze the latest committed kit without following concurrent workspace edits."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

P = Path(__file__).resolve().parent
E = P / 'evidence/observation-semantics'
R = P.parent.parent
baseline = json.loads((P / 'evidence/graph-consumers/kit-state.json').read_text())
repository = Path(baseline['root'])
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
roots = ['bl-org-dossier/kit', 'codebase-review/kit']
tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, *roots], cwd=repository, text=True).splitlines()
names = set(baseline['rendering_source_sha256'])
names.update(name for name in tracked if name.startswith('bl-org-dossier/kit/') and Path(name).suffix in ('.bl', '.org', '.css', '.js'))
archive = subprocess.check_output(['git', 'archive', '--format=tar', commit, *roots], cwd=repository)
with tempfile.TemporaryDirectory(prefix='formal-dossier-kit-') as temporary:
    candidate = Path(temporary) / ('formal-dossier-kit-' + commit[:8])
    candidate.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as saved:
        saved.extractall(candidate, filter='data')
    root = Path(subprocess.check_output(['nix-store', '--add', candidate], text=True).strip())
assert str(root).startswith('/nix/store/')
retention = R / '.bl/formal-dossier-kit'
subprocess.run(['nix-store', '--add-root', retention, '--indirect', '--realise', root], check=True, stdout=subprocess.DEVNULL)
sources = {}
for name in sorted(names):
    body = (root / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=repository) == body
    sources[name] = hashlib.sha256(body).hexdigest()
report = {'root': str(root), 'repository_root': str(repository), 'commit': commit, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
          'observed_dirty_paths': subprocess.check_output(['git', 'status', '--short', '--',
                                  'bl-org-dossier', 'codebase-review'], cwd=repository, text=True).splitlines(),
          'kit_code_changed_by_this_work': False, 'rendering_source_sha256': sources,
          'git_archive_sha256': hashlib.sha256(archive).hexdigest(), 'snapshot_retention_root': str(retention),
          'snapshot_nar_hash': subprocess.check_output(['nix-store', '--query', '--hash', root], text=True).strip(),
          'scope': 'Committed source snapshot for the next browser/cell check, not a live-host qualification.'}
(E / 'kit-state.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'kit_commit': commit, 'source_files': len(sources), 'immutable_root': str(root)}))
