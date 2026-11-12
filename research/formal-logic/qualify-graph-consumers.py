"""Qualify checkpoint 44 without promoting graph data into proof authority."""
from datetime import datetime, timezone
import hashlib,json,re,subprocess,tarfile
from pathlib import Path
P=Path(__file__).resolve().parent; R=P.parent.parent; E=P/'evidence/graph-consumers'; prior=P/'evidence/question-graphs'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,why):
    if not ok:raise AssertionError(why)
pin=read(E/'sdk-candidate.json');sdk=Path(pin['sdk']);source=Path(pin['source']);meta=read(sdk/'artifact.json')
recipe=read(E/'qualification-recipe-pin.json')
for path,digest in recipe['source_sha256'].items():
    require(sha(R/path)==digest,'qualification recipe bytes: '+path)
    require(hashlib.sha256(subprocess.check_output(['git','show',recipe['code_commit']+':'+path],cwd=R)).hexdigest()==digest,'committed recipe: '+path)
require(sha(sdk/'artifact.json')==pin['descriptor_sha256'] and meta['source']==str(source),'exact selected SDK')
oldmeta=read(Path(read(prior/'sdk-candidate.json')['sdk'])/'artifact.json')
require(meta['formalWorker']==oldmeta['formalWorker'],'unchanged formal worker')
old_inputs=read(Path(oldmeta['compiler'])/'qualification/inputs.json')
new_inputs=read(Path(meta['compiler'])/'qualification/inputs.json')
compiler_changes={p:{'old_sha256':old_inputs.get(p),'new_sha256':new_inputs.get(p)}
                  for p in sorted(old_inputs.keys()|new_inputs.keys()) if old_inputs.get(p)!=new_inputs.get(p)}
require(set(compiler_changes)=={'priv/boot/core.bl'},'explicit existing eager-doseq compiler input transition')
require(sha(R/'priv/boot/core.bl')==sha(source/'priv/boot/core.bl')==compiler_changes['priv/boot/core.bl']['new_sha256'],'actual qualified core input')
require(read(E/'preparation-result.json')['output']==str(sdk),'managed production result')
for name,immutable in [('sdk-source-pin.json',True),('check-source-pin.json',False)]:
    snapshot=read(E/name)
    for path,digest in snapshot['source_sha256'].items():
        require(sha(R/path)==digest,'checked bytes: '+path)
        require(hashlib.sha256(subprocess.check_output(['git','show',snapshot['code_commit']+':'+path],cwd=R)).hexdigest()==digest,'committed bytes: '+path)
        if immutable:require(sha(source/path)==digest,'SDK runtime bytes: '+path)
units=read(sdk/'unit-store/unit-index.json')['units'];require('formal.question-graph' in units,'packaged question context namespace')
runs={}
for stage,files in [('focused',6),('facade',7),('regression',31),('compiler-macro',1)]:
    log=(E/(stage+'-checks.txt')).read_text()
    rows={name:int(count) for name,count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed',log)}
    require(len(rows)==files and f'{files} file(s) passed, 0 failed, 0 incoherent' in log,'complete tests: '+stage)
    runs[stage]=rows
require(runs['focused']['formal.graph-context-test']>=149 and runs['focused']['veritas.graph-ledger-test']>=41,'graph context, scope and durable boundaries')
require(runs['compiler-macro']['core.doseq-eager-test']>=25,'eager effects without memo admission')
for stage in ['focused','facade','regression','compiler-macro','corpus','writer','consumer-one','consumer-two','compiler-floor','preflight','preflight-controls']:
    require(read(E/(stage+'-exit.json'))['exit_code']==0,'terminal result: '+stage)
    if stage in ['focused','facade','regression','compiler-macro','corpus','writer','consumer-one','consumer-two']:
        command=read(E/(stage+'-command.json'));runtime=read(E/(stage+'-runtime.json'))
        require(str(sdk/'bin/bl') in command,'exact runtime: '+stage)
        require(runtime['retired'] and all(not Path(x).exists() for x in runtime['paths']),'cleanup: '+stage)
        require(all(any(command[i:i+2]==['-u',v] for i in range(len(command)-1)) for v in ['ENCHANT_FORMAL_WORKER','ENCHANT_Z3_LIBRARY','BEAM_LISP_PATH']),'artifact environment: '+stage)
corpus=read(E/'corpus.json')['rows'];oldgraph={x['id']:x for x in read(prior/'corpus.json')['rows']}
oldnative={x['id']:x for family in ['advanced','features','native'] for x in read(prior/'regression'/(family+'.json'))['cases']}
require(len(corpus)==len(oldgraph)==len(oldnative)==187,'all preceding subjects')
for row in corpus:
    before=oldgraph[row['id']];native=oldnative[row['id']]
    require(row['graph']==before['graph'],'unchanged complete graph/ref/cost: '+row['id'])
    require(row['roots']==before['roots']==native['question-sha256'],'same typed term roots: '+row['id'])
    require(row['standard-identity']==before['standard-identity'],'unchanged v1 identity/capacity: '+row['id'])
    for engine in ['z3','oxiz']:
        require(all(row[engine][k]==native[engine][k] for k in ['solver-status','verdict','phase']),'same native outcome: '+row['id']+'/'+engine)
        require(row[engine]['identity']['sdk']==str(sdk),'native SDK identity: '+row['id'])
for family in ['advanced','features','native']:
    data=read(E/'regression'/(family+'.json'))
    require(not data['disagreements'] and not data['invalid-models'],'healthy old native flow: '+family)
    for row in data['cases']:
        old=oldnative[row['id']]
        require(row['question-sha256']==old['question-sha256'],'old native roots')
        for engine in ['z3','oxiz']:
            require(all(row[engine][k]==old[engine][k] for k in ['solver-status','verdict','phase']),'old native outcomes')
writer=read(E/'writer.json');require(writer['sdk-only'] and writer['rows']==3,'fresh writer mixed formats')
require(writer['graph']['expanded-nodes']>100000 and writer['graph']['nodes']<1000,'graph-first shared opaque provenance')
fixture=read(E/'owned-ledger.json');require(fixture['active_db_retired'] and sha(E/fixture['archive'])==fixture['archive_sha256'],'closed owned fixture archive')
with tarfile.open(E/fixture['archive'],'r:gz') as saved:
    for name,digest in fixture['files'].items():
        require(hashlib.sha256(saved.extractfile(name).read()).hexdigest()==digest,'owned archive file: '+name)
a,b=read(E/'consumer-one.json'),read(E/'consumer-two.json')
require(len({writer['process'],a['process'],b['process']})==3,'three independent processes')
for data,stage in [(writer,'writer'),(a,'consumer-one'),(b,'consumer-two')]:
    require(data['sdk-only'] and not Path(data['cwd']).is_relative_to(R) and '-p' not in read(E/(stage+'-command.json')),'unrelated SDK-only process')
for data in [a,b]:
    require(data['managed-query-calls']==0 and data['source-compilation'] is False and data['compiler-proof-authority'] is False,'pure read/replay scope')
    require({x['engine'] for x in data['rows']}=={'z3','oxiz'},'both durable backend replies')
    for row in data['rows']:
        require(row['reference']==writer['reference'] and row['graph']==writer['graph'] and row['point']==writer['point'],'original durable bytes/reference')
        require(row['materialization']=='refused','unknown metadata stays uninterned')
        require(row['answer']=={'verdict':'sat','solver-status':'sat','delegation':'not-matched','observation-basis':'independent-replay'},'reconstructed answer without custody claim')
        require(row['checking']['status']=='checked-data-connection' and row['checking']['kernel-execution']=='not-run','independent original point')
floor,flight=read(E/'produced-compiler.json'),read(E/'source-preflight.json')
require(floor['status']=='passed' and floor['files']==141 and floor['sdk']==str(sdk),'compiler floor')
require(flight['root']==str(source) and flight['runtime']==str(sdk),'exact source gate')
require(all(flight[k]['modality']=='exhausted' and flight[k]['complete'] for k in ['beam-selection','declaration-cases']) and not any(flight[k] for k in ['source-errors','target-dependency-errors','require-cycles','sources_changed_during_analysis']),'complete source admission')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E/'preflight-controls-checks.txt').read_text(),'negative admission controls')
total=sum(sum(rows.values()) for rows in runs.values())
report={'schema':'enchant.formal.graph-consumers-qualification.v1','checkpoint':44,'status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),'sdk_pin':pin,'runs':runs,'assertion_executions':total,'complete_graph_contexts':187,'same_preceding_native_subjects':187,'fresh_sdk_only_writer':1,'fresh_sdk_only_readers':2,'pure_reader_managed_query_calls':0,'new_untrusted_byte_ingress':False,'compiler_proof_authority':False,'scope':'Explicit graph-backed question contexts, selective composition/materialization, v2 typed answers, named graph effects, retained contexts, versioned durable verdicts and common native check/compare. Formal worker and legacy formal paths retained; the existing main eager-doseq compiler input is separately qualified. Owned ledger codec. No graph evaluator theorem, portable graph proof migration, Source/compiler preservation or universal totality.'}
report['owned_fixture']=fixture
report['compiler_transition']={'previous':oldmeta['compiler'],'qualified':meta['compiler'],'changed_inputs':compiler_changes,
 'basis':'Existing main eager-doseq implementation, with the exact new 141-file P/B/C floor and focused zero-memo-budget behavior checks. No compiler soundness theorem.'}
(E/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checkpoint':44,'status':'passed','assertions':total,'graph_contexts':187,'durable_readers':2}))
