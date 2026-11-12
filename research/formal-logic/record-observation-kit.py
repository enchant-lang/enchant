"""Record current committed dossier-kit inputs for a fresh presentation check."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
E = P / 'evidence/observation-semantics'
baseline = json.loads((P / 'evidence/graph-consumers/kit-state.json').read_text())
root = Path(baseline['root'])
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
names = set(baseline['rendering_source_sha256'])
names.update(str(path.relative_to(root)) for path in (root / 'bl-org-dossier/kit').rglob('*')
             if path.is_file() and path.suffix in ('.bl', '.org', '.css', '.js'))
sources = {}
for name in sorted(names):
    body = (root / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=root) == body
    sources[name] = hashlib.sha256(body).hexdigest()
report = {'root': str(root), 'commit': commit, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
          'observed_dirty_paths': subprocess.check_output(['git', 'status', '--short', '--',
                                  'bl-org-dossier', 'codebase-review'], cwd=root, text=True).splitlines(),
          'kit_code_changed_by_this_work': False, 'rendering_source_sha256': sources,
          'scope': 'Committed source snapshot for the next browser/cell check, not a live-host qualification.'}
(E / 'kit-state.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'kit_commit': commit, 'source_files': len(sources)}))
