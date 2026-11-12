"""Retain this candidate's closed owned store after independent SDK readers."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

E = Path(__file__).resolve().parent / 'evidence/observation-semantics'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for stage in ('writer', 'consumer-one', 'consumer-two'):
    assert json.loads((E / (stage + '-exit.json')).read_text())['exit_code'] == 0
roots = [E / 'durable-ledger', E / 'durable-ledger.blobs']
assert all(p.is_dir() and not p.is_symlink() for p in roots)
archive = E / 'owned-ledger.tar.gz'
assert not archive.exists()
files = sorted(p for root in roots for p in root.rglob('*') if p.is_file())
assert files and all(not p.is_symlink() for p in files)
manifest = {str(p.relative_to(E)): sha(p) for p in files}
with tarfile.open(archive, 'w:gz') as saved:
    for root in roots:
        saved.add(root, arcname=root.name)
with tarfile.open(archive, 'r:gz') as saved:
    for name, digest in manifest.items():
        assert hashlib.sha256(saved.extractfile(name).read()).hexdigest() == digest
for root in roots:
    shutil.rmtree(root)
report = {'schema': 'enchant.formal.owned-graph-ledger-fixture.v1', 'archive': archive.name,
          'archive_sha256': sha(archive), 'files': manifest,
          'active_db_retired': all(not p.exists() for p in roots),
          'scope': 'Owned closed Fjall store and sidecar after three SDK-only processes; not an untrusted transport or logical certificate.'}
(E / 'owned-ledger.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'archive': archive.name, 'files': len(files), 'retired': report['active_db_retired']}))
