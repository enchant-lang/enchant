"""Prepare exact isolated namespace projections; never mutate SDK or canonical sources."""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
R = P.parent.parent
S = P / 'prototypes/indexed-ledger'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = json.loads((P / 'sdk-pin.json').read_text())
plan = json.loads((P / 'proposals/indexed-ledger-read-plan.json').read_text())
patch = (P / 'proposals/indexed-ledger-read.patch').read_text()
ledger_patch, record_patch = patch.split('--- a/priv/lib/formal/request-record.bl\n')
changes = []
for name, part, namespace in [
    ('priv/lib/veritas/ledger.bl', ledger_patch, 'formal.indexed-ledger-prototype'),
    ('priv/lib/formal/request-record.bl', record_patch, 'formal.indexed-request-record-prototype')]:
    source = R / name
    assert sha(source) == plan['source_sha256'][name]
    assert sha(source) == sha(Path(pin['source']) / name)
    before = source.read_text()
    added = '\n'.join(line[1:] for line in part.splitlines() if line.startswith('+') and not line.startswith('+++')) + '\n'
    removed = '\n'.join(line[1:] for line in part.splitlines() if line.startswith('-') and not line.startswith('---')) + '\n'
    if removed.strip():
        assert before.count(removed) == 1
        after = before.replace(removed, added)
    else:
        marker = '(defn graph-evidence!\n'
        assert before.count(marker) == 1
        after = before.replace(marker, added + marker)
    old = 'veritas.ledger' if 'veritas/' in name else 'formal.request-record'
    assert after.count('(ns ' + old) == 1
    after = after.replace('(ns ' + old, '(ns ' + namespace, 1)
    if 'request-record' in name:
        assert after.count('[veritas.ledger :as ledger]') == 1
        after = after.replace('[veritas.ledger :as ledger]', '[formal.indexed-ledger-prototype :as ledger]')
    target = S / (namespace.replace('.', '/').replace('formal/', 'formal/', 1) + '.bl')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(after)
    changes.append({'source': name, 'source_sha256': sha(source), 'projection': str(target.relative_to(R)),
                    'projection_sha256': sha(target), 'namespace': namespace})
(S / 'projection.json').write_text(json.dumps({'schema': 'bl.indexed-ledger-projection.v1', 'sdk_pin': pin,
    'patch_sha256': sha(P / 'proposals/indexed-ledger-read.patch'), 'changes': changes,
    'scope': 'Exact proposed lookup/reopen patch plus explicit isolated namespace and require renaming. No canonical or SDK mutation.'}, indent=2) + '\n')
print(json.dumps({'status': 'prepared-not-checked', 'projections': len(changes)}))
