"""Retain the closed, owned qualification store without leaving a live DB copy."""
import hashlib,json,shutil,tarfile
from pathlib import Path
P=Path(__file__).resolve().parent; E=P/'evidence/graph-consumers'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for stage in ['writer','consumer-one','consumer-two']:
    assert json.loads((E/(stage+'-exit.json')).read_text())['exit_code']==0
roots=[E/'durable-ledger',E/'durable-ledger.blobs']
assert all(p.is_dir() and not p.is_symlink() for p in roots)
archive=E/'owned-ledger.tar.gz';assert not archive.exists()
files=sorted(p for root in roots for p in root.rglob('*') if p.is_file())
assert files and all(not p.is_symlink() for p in files)
manifest={str(p.relative_to(E)):sha(p) for p in files}
with tarfile.open(archive,'w:gz') as out:
    for root in roots:out.add(root,arcname=root.name)
with tarfile.open(archive,'r:gz') as saved:
    for name,digest in manifest.items():assert hashlib.sha256(saved.extractfile(name).read()).hexdigest()==digest
for root in roots:shutil.rmtree(root)
report={'schema':'enchant.formal.owned-graph-ledger-fixture.v1','archive':archive.name,'archive_sha256':sha(archive),'files':manifest,'active_db_retired':all(not p.exists() for p in roots),'scope':'Owned Fjall qualification store and content-addressed sidecar, captured after all three SDK-only processes closed it. Not an untrusted transport format or a logical certificate.'}
(E/'owned-ledger.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'archive':archive.name,'files':len(files),'bytes':archive.stat().st_size,'retired':report['active_db_retired']}))
