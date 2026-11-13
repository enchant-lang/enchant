"""Freeze current kit source without editing the user's skill repository.

Keep prior rendering pins/GC roots intact. Include the observed working CSS
as a recorded read-only overlay; ignore unrelated untracked local settings.
This creates source evidence, not a browser qualification.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

P = Path(__file__).resolve().parent
R = P.parent.parent
stage = sys.argv[1:]
assert stage in ([], ['numeric-semantics']), 'Optional stage: numeric-semantics'
numeric = stage == ['numeric-semantics']
E = P / ('evidence/numeric-semantics-presentation' if numeric else 'evidence/managed-presentation')
E.mkdir(exist_ok=True)
S = Path('/home/othman/projects/enchanted-skills')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(S), *args])


commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
head = git('rev-parse', 'HEAD').decode().strip()
status = git('status', '--short')
style = 'bl-org-dossier/kit/style.css'
css = (S / style).read_bytes()
base_css = git('show', head + ':' + style)
patch = git('diff', head, '--', style)
archive = git('archive', '--format=tar', head, 'bl-org-dossier/kit', 'codebase-review/kit')
retention = R / ('.bl/formal-dossier-kit-numeric-semantics' if numeric else '.bl/formal-dossier-kit-managed-request')
with tempfile.TemporaryDirectory(prefix='formal-managed-kit-') as temporary:
    source = Path(temporary) / ('formal-dossier-kit-' + head[:8])
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as package:
        package.extractall(source, filter='data')
    assert (source / style).read_bytes() == base_css
    (source / style).write_bytes(css)
    # Bind a coherent observed revision even if someone is editing the foreign
    # repository concurrently. Never reset, stage or write a file there.
    assert git('rev-parse', 'HEAD').decode().strip() == head
    assert (S / style).read_bytes() == css
    frozen = subprocess.check_output(['nix-store', '--add', str(source)], text=True).strip()
assert frozen.startswith('/nix/store/') and Path(frozen).is_dir()
if retention.exists() or retention.is_symlink():
    assert str(retention.resolve(strict=True)) == frozen, 'Keep an existing rendering root intact.'
else:
    subprocess.run(['nix-store', '--add-root', str(retention), '--indirect', '--realise', frozen],
                   check=True, stdout=subprocess.DEVNULL)
digests = {str(path.relative_to(frozen)): sha(path.read_bytes())
           for path in sorted(Path(frozen).rglob('*')) if path.is_file()}
assert digests[style] == sha(css)
assert git('rev-parse', 'HEAD').decode().strip() == head and (S / style).read_bytes() == css
state = {'root': frozen, 'repository_root': str(S), 'commit': head,
         'recorded_utc': datetime.now(timezone.utc).isoformat(),
         'observed_dirty_paths': status.decode().splitlines(), 'kit_code_changed_by_this_work': False,
         'git_archive_sha256': sha(archive), 'snapshot_retention_root': str(retention),
         'snapshot_nar_hash': subprocess.check_output(['nix-store', '--query', '--hash', frozen], text=True).strip(),
         'rendering_source_sha256': digests,
         'working_css_overlay': {'path': style, 'dirty': css != base_css, 'base_sha256': sha(base_css),
                                 'snapshot_sha256': sha(css), 'patch_sha256': sha(patch)},
         'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__).read_bytes())},
         'scope': 'Current committed kit plus the observed user-owned working CSS, copied without modifying the skill repository. Immutable source snapshot; cell, live-host and browser qualification remain separate.'}
(E / 'kit-working-css.patch').write_bytes(patch)
(E / 'kit-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'source-frozen', 'commit': head, 'root': frozen,
                  'files': len(digests), 'read_only_css_overlay': css != base_css}))
