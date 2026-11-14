"""Freeze current committed kit and research contract without touching foreign edits."""
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/scalar-presentation'
E.mkdir(exist_ok=True)
S = Path('/home/othman/projects/enchanted-skills')
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(S),*args])
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+recipe],cwd=R) == Path(__file__).read_bytes()
head = git('rev-parse','HEAD').decode().strip()
status = git('status','--short').decode().splitlines()
archive = git('archive','--format=tar',head,'bl-org-dossier/kit','codebase-review/kit','research-elements/kit')
retention = R / ('.bl/formal-dossier-kit-scalar-' + head[:8])
with tempfile.TemporaryDirectory(prefix='formal-scalar-kit-') as directory:
    source = Path(directory) / ('formal-scalar-dossier-kit-' + head[:8])
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as package:
        package.extractall(source,filter='data')
    assert git('rev-parse','HEAD').decode().strip() == head
    frozen = subprocess.check_output(['nix-store','--add',str(source)],text=True).strip()
assert frozen.startswith('/nix/store/') and Path(frozen).is_dir()
if retention.exists() or retention.is_symlink():
    assert str(retention.resolve(strict=True)) == frozen
else:
    subprocess.run(['nix-store','--add-root',str(retention),'--indirect','--realise',frozen],check=True,stdout=subprocess.DEVNULL)
digests = {str(path.relative_to(frozen)):sha(path.read_bytes()) for path in sorted(Path(frozen).rglob('*')) if path.is_file()}
assert 'research-elements/kit/research/elements.bl' in digests
assert git('rev-parse','HEAD').decode().strip() == head
assert not (E / 'kit-state.json').exists()
(E / 'previous-kit-state.json').write_bytes((P / 'evidence/word-presentation/kit-state.json').read_bytes())
state = {'root':frozen,'repository_root':str(S),'commit':head,'recorded_utc':datetime.now(timezone.utc).isoformat(),
         'observed_dirty_paths':status,'foreign_working_code_included':False,'kit_code_changed_by_this_work':False,
         'git_archive_sha256':sha(archive),'snapshot_retention_root':str(retention),
         'snapshot_nar_hash':subprocess.check_output(['nix-store','--query','--hash',frozen],text=True).strip(),
         'rendering_source_sha256':digests,'research_element_contract_sha256':digests['research-elements/kit/research/elements.bl'],
         'working_css_overlay':{'path':'bl-org-dossier/kit/style.css','dirty':False,
                                'base_sha256':digests['bl-org-dossier/kit/style.css'],
                                'snapshot_sha256':digests['bl-org-dossier/kit/style.css'],
                                'patch_sha256':sha(b'')},
         'recipe':{'code_commit':commit,'path':recipe,'sha256':sha(Path(__file__).read_bytes())},
         'scope':'Current committed dossier, codebase-review and research-element sources. Foreign working edits are observed and untouched. No sharing configuration, publisher route or publication action is installed by this snapshot. SDK/cell/host/browser qualification remains separate.'}
(E / 'kit-state.json').write_text(json.dumps(state,indent=2)+'\n')
(E / 'kit-working-css.patch').write_bytes(b'')
print(json.dumps({'status':'source-frozen','commit':head,'files':len(digests),'root':frozen,'research_contract_included':True,'host_activation':False}))
