"""Capture exact committed candidate runtime and qualification sources."""
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent; R=P.parent.parent; E=P/'evidence/graph-consumers'; old=P/'evidence/question-graphs'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
sdk=(R/'.bl/sdks/current-sdk').resolve(strict=True)
meta=read(sdk/'artifact.json');source=Path(meta['source'])
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
pin={'sdk':str(sdk),'descriptor_sha256':sha(sdk/'artifact.json'),'source':str(source),'base_commit':commit}
paths=set(read(old/'sdk-source-pin.json')['source_sha256'])|{'priv/lib/formal/question-graph.bl'}
for path in paths:assert sha(R/path)==sha(source/path),path
write(E/'sdk-candidate.json',pin)
if not (E/'baseline-sdk-pin.json').exists():write(E/'baseline-sdk-pin.json',read(P/'sdk-pin.json'))
write(E/'sdk-source-pin.json',{'sdk_pin':pin,'code_commit':commit,'source_sha256':{p:sha(R/p) for p in sorted(paths)}})
checked=set(read(old/'check-source-pin.json')['source_sha256'])|paths|{
 'test/bl/formal/graph_ops_test.bl','test/bl/formal/graph_context_test.bl','test/bl/veritas/graph_ledger_test.bl',
 'research/formal-logic/test/graph_facade_test.bl','research/formal-logic/graph-consumers-check.bl',
 'research/formal-logic/graph-ledger-writer.bl','research/formal-logic/graph-ledger-consumer.bl',
 'research/formal-logic/run-graph-consumers-check.py'}
write(E/'check-source-pin.json',{'code_commit':commit,'source_sha256':{p:sha(R/p) for p in sorted(checked)}})
results=[(p,read(p)) for p in (R/'.bl/sdks').glob('*/job-*/result.json')]
matching=[(p,d) for p,d in results if d.get('output')==str(sdk)]
assert matching,'retained managed job producing the selected SDK is required'
_,result=sorted(matching,key=lambda pair:pair[0].stat().st_mtime)[-1]
write(E/'preparation-result.json',result)
print(json.dumps(pin))
