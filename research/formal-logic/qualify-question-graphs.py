"""Qualify complete graph data separately from mathematical/compiler authority."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent; R=P.parent.parent; E=P/'evidence/question-graphs'; prior=P/'evidence/explicit-points'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,why):
    if not ok:raise AssertionError(why)
pin=read(E/'sdk-candidate.json');sdk=Path(pin['sdk']);source=Path(pin['source']);meta=read(sdk/'artifact.json')
require(sha(sdk/'artifact.json')==pin['descriptor_sha256'] and meta['source']==str(source),'immutable selected SDK')
oldmeta=read(Path(read(E/'baseline-sdk-pin.json')['sdk'])/'artifact.json')
require(all(meta[k]==oldmeta[k] for k in ('compiler','formalWorker')),'same compiler and worker')
require(read(E/'preparation-result.json')['output']==str(sdk),'managed SDK production')
snapshot=read(E/'sdk-source-pin.json')
require(snapshot['sdk_pin']==pin,'runtime pin')
for name,digest in snapshot['source_sha256'].items():
    require(sha(R/name)==sha(source/name)==digest,'frozen runtime: '+name)
    require(hashlib.sha256(subprocess.check_output(['git','show',snapshot['code_commit']+':'+name],cwd=R)).hexdigest()==digest,'committed runtime: '+name)
checked=read(E/'check-source-pin.json')
for name,digest in checked['source_sha256'].items():
    require(sha(R/name)==digest,'checked program: '+name)
    require(hashlib.sha256(subprocess.check_output(['git','show',checked['code_commit']+':'+name],cwd=R)).hexdigest()==digest,'committed program: '+name)
units=read(sdk/'unit-store/unit-index.json')['units'];require('formal.data-graph' in units,'production graph namespace')
runs={}
for stage,files in [('focused',3),('regression',31)]:
    text=(E/(stage+'-checks.txt')).read_text(); rows={name:int(count) for name,count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed',text)}
    require(len(rows)==files and f'{files} file(s) passed, 0 failed, 0 incoherent' in text,'complete tests: '+stage)
    runs[stage]=rows
require(runs['focused']['formal.point-test']==92 and runs['focused']['formal.float-points-test']==219 and runs['focused']['formal.data-graph-test']>=281,'old points and new graph coverage')
for stage in ('focused','regression','corpus','consumer-one','consumer-two','compiler-floor','preflight','preflight-controls'):
    require(read(E/(stage+'-exit.json'))['exit_code']==0,'terminal exit: '+stage)
    if stage in ('focused','regression','corpus','consumer-one','consumer-two'):
        command=read(E/(stage+'-command.json'));runtime=read(E/(stage+'-runtime.json'))
        require(str(sdk/'bin/bl') in command,'exact SDK: '+stage)
        require(runtime['retired'] and all(not Path(p).exists() for p in runtime['paths']),'owned runtime cleanup: '+stage)
        require(all(any(command[i:i+2]==['-u',var] for i in range(len(command)-1)) for var in ('ENCHANT_FORMAL_WORKER','ENCHANT_Z3_LIBRARY','BEAM_LISP_PATH')),'immutable artifacts: '+stage)
corpus=read(E/'corpus.json'); old=read(P/'evidence/float-source/question-identities-current.json')
old={r['id']:r for r in old['rows']}; require(len(old)==len(corpus['rows'])==187,'full preceding corpus')
for row in corpus['rows']:
    require(row['content']==old[row['id']]['content'],'independent complete public contents: '+row['id'])
    require(row['standard-identity']==old[row['id']]['standard-identity'],'unchanged standard identity: '+row['id'])
    require(row['roundtrip']=='exact-public-data' and row['graph']['status']=='checked-data-graph','exact graph roundtrip: '+row['id'])
    require(row['graph']['reference']['profile']=='bl/public-data-graph-v1','explicit graph profile')
large=next(r for r in corpus['rows'] if r['id']=='relation/closure-is-transitive')
require(large['content']['walks']==110551 and large['standard-identity']['status']=='unavailable','retained standard capacity boundary')
point=corpus['point-example'];require(point['version-one']['status']=='rejected' and point['checking']['status']=='checked-data-connection','explicit large point migration')
require(point['point']['formal/point']==2 and point['point']['profile']=='bl/independent-original-point-v2' and point['point']['question']==point['reference'],'versioned point identity')
a,b=read(E/'consumer-one.json'),read(E/'consumer-two.json')
require(a['process']!=b['process'],'fresh independent processes')
for data,stage in [(a,'consumer-one'),(b,'consumer-two')]:
    require(data['sdk-only'] and not data['research-import-path'] and not Path(data['cwd']).is_relative_to(R) and '-p' not in read(E/(stage+'-command.json')),'SDK-only unrelated reader')
    require(data['original']==large['graph'] and data['subject']==point['graph'] and data['point']==point['point']['identity'],'same durable graphs and point')
    require(data['managed-query-calls']==0 and data['source-compilation'] is False and data['compiler-proof-authority'] is False,'pure graph/point checking')
    require(data['checking']['status']=='checked-data-connection' and data['checking']['kernel-execution']=='not-run','separate evaluator assurance')
require(corpus['managed-query-calls']==0,'pure graph corpus construction')
paired=0
for family in ('advanced','features','native'):
    now=read(E/'regression'/(family+'.json')); old={r['id']:r for r in read(prior/'regression'/(family+'.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'] and {r['id'] for r in now['cases']}==old.keys(),'healthy preceding native cases')
    for row in now['cases']:
        require(row['question-sha256']==old[row['id']]['question-sha256'],'unchanged native roots')
        for engine in ('z3','oxiz'):
            require(row[engine]['solver-status']==old[row['id']][engine]['solver-status'] and row[engine]['verdict']==old[row['id']][engine]['verdict'],'unchanged native status and verdict')
            require(row[engine]['identity']['sdk']==pin['sdk'],'native artifact provenance')
    paired+=len(now['cases'])
require(paired==187,'all preceding paired questions')
floor,flight=read(E/'produced-compiler.json'),read(E/'source-preflight.json')
require(floor['status']=='passed' and floor['files']==141 and floor['sdk']==pin['sdk'],'compiler floor')
require(flight['root']==pin['source'] and flight['runtime']==pin['sdk'],'frozen source gate')
require(all(flight[k]['modality']=='exhausted' and flight[k]['complete'] for k in ('beam-selection','declaration-cases')) and not any(flight[k] for k in ('source-errors','target-dependency-errors','require-cycles','sources_changed_during_analysis')),'complete source gate')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E/'preflight-controls-checks.txt').read_text(),'negative controls')
total=sum(sum(r.values()) for r in runs.values())
report={'schema':'enchant.formal.question-graph-qualification.v1','status':'passed','checkpoint':43,'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'sdk_pin':pin,'source':snapshot,'checked_programs':checked,'assertion_executions':total,'runs':runs,
        'complete_public_data_roundtrips':187,'same_preceding_native_questions':paired,'standard_identity_unchanged':True,
        'large_original_question':large,'large_point_graph':point['graph'],'fresh_sdk_only_readers':2,'managed_query_calls_during_graph_and_point_checking':0,
        'public_untrusted_byte_ingress':False,'initial_conversion':'bounded-tree-walk','checking_storage':'unique-structure-with-expansion-bounds',
        'scope':'Canonical public data graphs and explicit version-2 original point references. Owned ETF fixture transport, existing-only keyword materialization. No graph model theorem, evaluator soundness theorem, Source preservation, solver proof or compiler authority.',
        'compiler_proof_authority':False}
(E/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checkpoint':43,'status':'passed','assertions':total,'roundtrips':187,'paired':paired,'large_unique_nodes':large['graph']['nodes']}))
