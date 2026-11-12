"""Qualify exact-runtime Float terms separately from solver and compiler authority."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/float-source'
prior = P / 'evidence/migrations'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(ok, why):
    if not ok: raise AssertionError(why)
def counts(stage, files):
    text = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(value) for name, value in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in text, 'complete run: ' + stage)
    require(read(E / (stage + '-exit.json'))['exit_code'] == 0, 'terminal process completion: ' + stage)
    return rows
pin = read(E / 'sdk-candidate.json')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'] and meta['source'] == pin['source'], 'immutable SDK')
old_meta = read(Path(read(E / 'baseline-sdk-pin.json')['sdk']) / 'artifact.json')
require(meta['compiler'] == old_meta['compiler'] and meta['formalWorker'] == old_meta['formalWorker'], 'same compiler and native worker')
produced = read(E / 'preparation-result.json')
require(produced['ok'] and produced['value']['output'] == pin['sdk'], 'managed SDK production')
snapshot = read(E / 'sdk-source-pin.json')
require(snapshot['sdk_pin'] == pin, 'exact source pin')
for name, digest in snapshot['source_sha256'].items():
    require(sha(R/name) == sha(source/name) == digest, 'SDK bytes: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest, 'committed runtime: ' + name)
checked = read(E / 'check-source-pin.json')
for name, digest in checked['source_sha256'].items():
    require(sha(R/name) == digest, 'checked source: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', checked['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest, 'committed program: ' + name)
units = read(sdk / 'unit-store/unit-index.json')['units']
require(all(name in units for name in ('formal.beam-float','formal.floating','formal.ieee-arithmetic','formal.migration')), 'production SDK namespaces')
base = read(E / 'baseline.json')
require(base['modeled']['holds'] is True and base['modeled']['checked'] is True and base['modeled']['complete'] is True and base['actual']['value'] is False, 'retained actual false Source proof')
require('823 passed, 2 failed, 1 errored' in (E/'candidate-1/focused-checks.txt').read_text(), 'retained missing canonical division refusal')
stages = {'focused':4,'arithmetic-sdk':1,'migration-focused':4,'preparation-focused':5,'preceding-focused':26,'regression':31}
runs = {stage: counts(stage, files) for stage, files in stages.items()}
require(runs['arithmetic-sdk']['formal.ieee-arithmetic-test'] == 8191, 'arithmetic correspondence scope')
require(runs['focused']['formal.beam-float-test'] > 823, 'integrated runtime, Source, guard and owner tests')
for stage in (*stages, 'examples','ledger-write','ledger-read'):
    command = read(E/(stage+'-command.json'))
    require(str(sdk/'bin/bl') in command, 'one exact SDK: '+stage)
    runtime = read(E/(stage+'-runtime.json'))
    require(runtime['retired'] and all(not Path(p).exists() for p in runtime['paths']), 'owned runtimes retired: '+stage)
    require(read(E/(stage+'-exit.json'))['exit_code'] == 0, 'terminal exit: '+stage)
    require(all(any(command[i:i+2]==['-u',var] for i in range(len(command)-1)) for var in ('ENCHANT_FORMAL_WORKER','ENCHANT_Z3_LIBRARY','BEAM_LISP_PATH')), 'default immutable artifacts: '+stage)
paired, upgrades = 0, []
for family in ('advanced','features','native'):
    now=read(E/'regression'/(family+'.json'))
    old={row['id']:row for row in read(prior/'regression'/(family+'.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'matrix health: '+family)
    require(old.keys()=={row['id'] for row in now['cases']}, 'same preceding cases')
    for row in now['cases']:
        require(row['question-sha256']==old[row['id']]['question-sha256'], 'same root digest: '+row['id'])
        for engine in ('z3','oxiz'):
            a,b=row[engine],old[row['id']][engine]
            require(a['solver-status']==b['solver-status'], 'same native status: '+row['id'])
            require(a['identity']['sdk']==pin['sdk'], 'native provenance')
            if a['verdict'] != b['verdict']:
                require(b['verdict']=='candidate' and a['verdict']=='refuted' and a['replay']['status']=='valid', 'only independently replayed verdict upgrades')
                upgrades.append({'id':row['id'],'backend':engine,'before':b['verdict'],'after':a['verdict']})
    paired+=len(now['cases'])
require(paired==187,'all preceding paired questions')
example=read(E/'examples.json')
require(not example['research-import-path'] and not Path(example['cwd']).is_relative_to(R) and '-p' not in read(E/'examples-command.json'),'SDK-only unrelated consumer')
require(len(example['cases'])==8,'four Source subjects on both engines')
for subject in ('rounded-cancellation','negative-zero','division-failure','exact-rounding'):
    rows=[row for row in example['cases'] if row['id']==subject]
    require({r['backend'] for r in rows}=={'z3','oxiz'} and len({r['question'] for r in rows})==1,'same complete question: '+subject)
    for row in rows:
        r=row['result'];a=r['answer'];observation=row['observation']
        require(r['compiler-proof-authority'] is False and a['trusted'] is False,'no authority')
        require(a['identity']['artifacts']['sdk']==pin['sdk'],'new native provenance')
        require(observation['actual']['module-loaded'] is False,'actual Source module retirement')
        require((observation['actual']['status']=='returned') is observation['term']['defined'],'Source/terms raisedness agrees')
        if row['backend']=='z3':
            require(r['modality']==('solver-claim' if subject=='exact-rounding' else 'refuted'),'Z3 Source evidence')
            if subject!='exact-rounding': require(r['runtime-replay']['status']=='reproduced','concrete original Source refutation')
a,b=read(E/'ledger-write.json'),read(E/'ledger-read.json')
require(a['process']!=b['process'] and a['rows']==b['rows'] and len(a['rows'])==8,'fresh durable reconstruction')
for report in (a,b):
    require(report['managed-query-calls']==0 and report['managed-query-scope']=='record-rechecking' and report['actual-source-observations'] is True and report['compiler-proof-authority'] is False,'recheck scope')
floor,flight=read(E/'produced-compiler.json'),read(E/'source-preflight.json')
require(floor['status']=='passed' and floor['files']==141 and floor['sdk']==pin['sdk'],'same compiler floor')
require(flight['root']==pin['source'] and flight['runtime']==pin['sdk'],'frozen source preflight')
require(all(flight[k]['modality']=='exhausted' and flight[k]['complete'] for k in ('beam-selection','declaration-cases')) and not any(flight[k] for k in ('source-errors','target-dependency-errors','require-cycles','sources_changed_during_analysis')),'complete source gate')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E/'preflight-controls-checks.txt').read_text(),'negative controls')
for stage in ('compiler-floor','preflight','preflight-controls'): require(read(E/(stage+'-exit.json'))['exit_code']==0,'terminal infrastructure check')
total=sum(sum(row.values()) for row in runs.values())
report={'schema':'enchant.formal.float-source-qualification.v1','status':'passed','checkpoint':41,'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'sdk_pin':pin,'source':snapshot,'checked_programs':checked,'assertion_executions':total,'runs':runs,'preceding_paired_questions':paired,'reviewed_replay_upgrades':upgrades,
        'new_paired_source_subjects':4,'sdk_only':True,'durable_fresh_process_rechecking':True,'record_rechecking_managed_query_calls':0,
        'examples_sha256':sha(E/'examples.json'),'scope':'Reviewed finite binary64 scalar Source, exact literal conversions, numeric and strict zero equality, finite-result outcomes and concrete original Source observations; no universal IEEE or compiler preservation theorem.',
        'compiler_proof_authority':False}
(E/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checkpoint':41,'status':'passed','assertions':total,'paired':paired,'reviewed_replay_upgrades':len(upgrades)}))
