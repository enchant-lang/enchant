"""Check the mathematics of ordered total choice bindings, separate from BL correspondence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess,tempfile,time,os
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/choice-extension-model';E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
tool=read(P/'metatheory/tool-pin.json');lean=Path(tool['path'])/'bin/lean'
assert sha(lean)==tool['binary_sha256']
assert subprocess.check_output(['nix','hash','path',tool['path']],text=True).strip()==tool['narHash']
model=P/'metatheory/ChoiceExtension.lean';controls=sorted((P/'metatheory/choice-extension-controls').glob('*.lean'))
assert len(controls)==4
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in [Path(__file__),model,*controls,P/'metatheory/tool-pin.json']:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
 if f.suffix=='.lean':assert not re.search(r'\b(sorry|axiom|native_decide|unsafe)\b',f.read_text())
write('source-pin.json',{'code_commit':commit,'source_sha256':digests})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
expected={'FormalChoiceExtension.'+name for name in ['guarded_eq_choice','choice_guarded','guarded_unique',
 'run_defines','defines_result','defines_iff_run','unique_extension','extension_length','extension_prefix',
 'existential_projection','universal_projection','counterexample_projection','premise_feasibility',
 'conditional_transfer','original_entailment']}
root=Path(tempfile.mkdtemp(prefix='formal-choice-model-'));results=[]
try:
 for index,source in enumerate([model,*controls]):
  target=E/(source.stem+'.olean');target.unlink(missing_ok=True)
  command=['timeout','--kill-after=15','300',str(lean),'--root='+str(source.parent),'-o',str(target),str(source)]
  write(source.stem+'-command.json',command);started=time.monotonic()
  env=dict(os.environ,LEAN_PATH=str(E))
  with (E/(source.stem+'-checks.txt')).open('w') as out:code=subprocess.run(command,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT).returncode
  log=(E/(source.stem+'-checks.txt')).read_text();accepted=index==0
  result={'source':str(source.relative_to(R)),'accepted':accepted,'exit_code':code,
   'elapsed_seconds':time.monotonic()-started,'log_sha256':sha(E/(source.stem+'-checks.txt')),
   'olean_sha256':sha(target) if target.exists() else None}
  write(source.stem+'-exit.json',result)
  if accepted:
   assert code==0 and target.exists() and 'error:' not in log,log[-5000:]
   audits=re.findall(r"'([^']+)' (?:depends on axioms: \[([^]]*)\]|does not depend on any axioms)",log)
   assert len(audits)==len(expected) and {name for name,_ in audits}==expected
   result['dependency_ledger']={name:re.findall(r'[\w.]+',raw) for name,raw in audits}
   assert all(set(values)<={'propext','Quot.sound'} for values in result['dependency_ledger'].values())
  else:
   assert code!=0 and not target.exists() and log.count('error:')==1 and 'decide' in log and 'false' in log,log[-3000:]
  results.append(result);print(json.dumps({'source':source.name,'status':'accepted' if accepted else 'refused-as-required'}),flush=True)
finally:
 shutil.rmtree(root);write('cleanup.json',{'private_cwd_retired':not root.exists()})
assert all(sha(R/n)==digest for n,digest in digests.items())
write('qualification.json',{'schema':'bl.choice-extension-model.v1','status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'tool_pin':tool,'source_pin':read(E/'source-pin.json'),'checks':results,'theorems':15,'false_claim_controls':4,
 'dependency_policy':'choice-free-v1','explicit_original_target_correspondence_premise':True,
 'bl_implementation_correspondence':False,'compiler_proof_authority':False,
 'scope':'Constructive mathematics of ordered total Boolean-guarded integer bindings: unique extension, original-store prefix preservation, existential/universal/counterexample projection, unchanged premise feasibility and conditional entailment transfer. The original-target evaluator correspondence remains an explicit theorem premise. No theorem that the BL graph transformer implements this model, no graph/name hygiene or serialization correspondence, resource-cost, Source or compiler preservation proof.'})
print(json.dumps({'status':'passed','theorems':15,'false_claim_controls':4,'bl_implementation_correspondence':False}))
