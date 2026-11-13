"""Audit the complete paired native observation without promoting the SDK."""
import hashlib
import json
from pathlib import Path
import subprocess
P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pin = read(E / 'sdk-candidate.json')
assert read(P / 'sdk-pin.json') == read(E / 'baseline-sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
exit = read(E / 'native-exit.json')
assert exit['exit_code'] == 0 and exit['runtime_retired'] and exit['consumer_cwd_retired']
source = read(E / 'native-source-pin.json')
assert source['sdk_pin'] == pin
for name,digest in source['source_sha256'].items():
    assert sha(R / name) == digest
    assert hashlib.sha256(subprocess.check_output(['git','show',source['code_commit']+':'+name],cwd=R)).hexdigest() == digest
old = read(P / 'evidence/retained-request/native.json')
current = read(E / 'native.json')
before = {row['id']:row for row in old['rows']}
assert len(current['rows']) == len(before) == 187 and current['compiler-proof-authority'] is False
assert set(before) == {row['id'] for row in current['rows']}
differences = []
for row in current['rows']:
    prior = before[row['id']]
    assert row['roots'] == prior['roots'] and row['standard-identity'] == prior['standard-identity']
    for engine in ('z3','oxiz'):
        a,b = row[engine],prior[engine]
        assert a['identity']['sdk'] == pin['sdk'] and a['identity']['backend'] == engine
        for field in ('worker-sha256','library-sha256'):
            assert a['identity'][field] == b['identity'][field]
        for field in ('solver-status','verdict','phase','observation-basis'):
            if a.get(field) != b.get(field):
                differences.append({'id':row['id'],'backend':engine,'field':field,'before':b.get(field),'after':a.get(field)})
        if a['validation'].get('status') != b['validation'].get('status'):
            differences.append({'id':row['id'],'backend':engine,'field':'validation.status',
                                'before':b['validation'].get('status'),'after':a['validation'].get('status')})
(E / 'native-comparison-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
assert not differences,differences
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+recipe],cwd=R) == Path(__file__).read_bytes()
report = {'schema':'bl.word-paired-native-comparison.v1','status':'passed','sdk_pin':pin,'questions':187,
          'source_pin':source,'native_sha256':sha(E / 'native.json'),'baseline_native_sha256':sha(P / 'evidence/retained-request/native.json'),
          'differences':differences,'actual_exit':exit,'compiler_proof_authority':False,'sdk_selected':False,
          'recipe':{'code_commit':commit,'path':recipe,'sha256':sha(Path(__file__))},
          'scope':'Complete fixed graph/standard identities, worker/library identities and reported status/verdict/phase/observation/validation compatibility. This is not a proof of native soundness, completeness, historical custody or Source/compiler correspondence.'}
(E / 'native-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'passed','questions':187,'differences':0,'selected':False}))
