"""Qualify the separate graph-table model and its bounded owned instances."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess
from pathlib import Path
import graph_table_lean as bridge
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/graph-table-model'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,why):
    if not ok:raise AssertionError(why)
def audits(text):
    result={}
    for name,tail in re.findall(r"'([^']+)' (does not depend on any axioms|depends on axioms: \[[^\]]*\])",text):
        result[name]=[] if tail.startswith('does not') else [x.strip() for x in tail.split('[',1)[1][:-1].split(',') if x.strip()]
    require('sorryAx' not in text and 'error:' not in text,'accepted axiom report only')
    require(all(set(a)<={'propext','Quot.sound'} for a in result.values()),'explicit ordinary model axioms')
    return result
pin=read(P/'sdk-pin.json');core=read(P/'evidence/graph-consumers/qualification.json')
require(core['status']=='passed' and pin==core['sdk_pin'],'same qualified SDK')
tool=read(P/'metatheory/tool-pin.json');require(sha(Path(tool['path'])/'bin/lean')==tool['binary_sha256'],'exact proof tool')
model=P/'metatheory/GraphTable.lean';source=model.read_text();log=(E/'model-checks.txt').read_text()
require(not re.search(r'(?m)^\s*(axiom|opaque|partial|unsafe|noncomputable)\b',source) and not re.search(r'\b(sorry|admit)\b',source),'no unchecked model declarations')
model_audits=audits(log);names=set(re.findall(r'#print axioms (\w+)',source))
require(set(model_audits)=={'FormalGraphTable.'+n for n in names} and len(names)==9,'complete named model audits')
theorems=re.findall(r'(?m)^(?:@\[[^\]]+\]\s+)?theorem\s+(\w+)',source)
require(len(theorems)==15 and (E/'GraphTable.olean').is_file(),'complete structural model')
for stage in ['export','generate']:
    require(read(E/(stage+'-exit.json'))['exit_code']==0,'terminal stage: '+stage)
command=read(E/'export-command.json');runtime=read(E/'export-runtime.json')
require(pin['sdk']+'/bin/bl' in command and '-p' not in command,'SDK-only model exporter')
require(runtime['retired'] and all(not Path(p).exists() for p in runtime['paths']),'retired export cwd/runtime')
require(not Path(next(x.split('=',1)[1] for x in command if x.startswith('--working-directory='))).is_relative_to(R),'unrelated export cwd')
export=bridge.read_export(E/'exports.json');inputs=read(E/'instances/inputs.json');results=read(E/'instances/results.json')
require(results['status']=='passed' and results['sdk_pin']==pin and results['tool_pin']==tool,'same artifacts for instances')
require(len(export['packets'])==len(inputs['instances'])==len(results['instances'])==3,'all three instance packets')
rows=[]
for packet,declared,row in zip(export['packets'],inputs['instances'],results['instances']):
    generated,summary=bridge.lean_instance(packet);path=E/'instances'/declared['source'];output=path.with_suffix('.olean');text=path.with_suffix('.txt').read_text()
    require(path.read_text()==generated and sha(path)==row['source_sha256']==declared['source_sha256'],'exact generated proof: '+summary['id'])
    require(all(row[k]==summary[k] for k in summary),'exact original instance semantics: '+summary['id'])
    require(row['exit_code']==0 and read(path.with_suffix('.exit.json'))=={'exit_code':0,'olean_present':True},'terminal accepted instance')
    require(sha(output)==row['olean_sha256'] and sha(E/'GraphTable.olean')==row['imported_graph_table_sha256'],'compiled proof/model custody')
    require(sha(path.with_suffix('.txt'))==row['log_sha256'],'actual instance log')
    actual=audits(text);require(set(actual)=={'GraphInstance.original_expanded_nodes','GraphInstance.original_depth'},'both original value theorems')
    require('+kernel' in generated and 'native_decide' not in generated and '+native' not in generated,'kernel checked counter witnesses')
    rows.append({**row,'axioms':actual})
old=next(x for x in read(P/'evidence/question-graphs/corpus.json')['rows'] if x['id']=='relation/closure-is-transitive')
large=next(x for x in rows if x['id']=='saved-original-closure')
require(large['reference']==old['graph']['reference'] and large['expanded_nodes']==110551 and large['nodes']==332 and large['depth']==26,'same original closure graph')
unknown=next(x for x in rows if x['id']=='shared-unknown-keyword')
require(unknown['nodes']==17 and unknown['expanded_nodes']==131071 and unknown['depth']==16,'shared unknown data remains an exact model value')
negative=read(E/'negative-controls.json');require(negative['status']=='passed' and len(negative['controls'])==16,'all controls')
require(sum(x['status']=='refused' for x in negative['controls'])==14 and sum(x['status']=='not-accepted-by-Lean' for x in negative['controls'])==2,'independent packet and proof refusals')
for row in negative['controls']:
    if row['status']=='not-accepted-by-Lean':
        path=E/'rejected'/(row['name']+'.lean');require(row['exit_code']!=0 and not path.with_suffix('.olean').exists() and sha(path)==row['source_sha256'] and sha(path.with_suffix('.txt'))==row['log_sha256'],'actual rejected proof')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
paths=['metatheory/GraphTable.lean','metatheory/tool-pin.json','graph-table-export.bl','graph_table_lean.py','run-graph-table-model.py','graph-table-negative-controls.py','qualify-graph-table-model.py']
sources={str((P/n).relative_to(R)):sha(P/n) for n in paths}
for name,digest in sources.items():require(hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=R)).hexdigest()==digest,'committed source: '+name)
report={'schema':'enchant.formal.graph-table-model-qualification.v1','status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),'tool_pin':tool,'sdk_pin':pin,'code_commit':commit,'source_sha256':sources,'model':{'source_sha256':sha(model),'olean_sha256':sha(E/'GraphTable.olean'),'log_sha256':sha(E/'model-checks.txt'),'theorems':theorems,'axioms':model_audits},'instances':rows,'negative_controls':negative,'owned_export_sha256':sha(E/'exports.json'),'owned_original_fixture_sha256':sha(P/'evidence/question-graphs/owned-points.etf'),'scope':'Total finite prefix table interpretation and fold/quantity laws. Exact owned wire comparison and original expanded-node/depth instance theorems. Scalar external-size costs remain SDK reports; no scalar byte-cost bridge, canonicalization theorem, keyword admission theorem, typed term theorem, BL implementation correspondence, solver proof or compiler preservation theorem.','compiler_proof_authority':False}
(E/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'passed','model_theorems':len(theorems),'audited_model_results':len(names),'instances':len(rows),'instance_theorems':2*len(rows),'negative_controls':16}))
