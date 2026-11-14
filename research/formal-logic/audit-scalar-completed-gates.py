"""Run the committed qualifier's completed-gate prefix without selecting an SDK."""
from datetime import datetime,timezone
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
recipe=P/'qualify-scalar-integration.py';source=recipe.read_text()
marker="previous_word = read(E / 'previous-word-readers-qualification.json')"
assert source.count(marker)==1
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
for p in [Path(__file__),recipe]:
 name=str(p.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==p.read_bytes()
namespace={'__file__':str(recipe),'__name__':'scalar_completed_gate_audit'}
exec(compile(source.split(marker)[0],str(recipe),'exec'),namespace)
report={'schema':'bl.scalar-completed-gate-audit.v1','status':'completed-gates-passed-history-still-pending',
 'recorded_utc':datetime.now(timezone.utc).isoformat(),'sdk_pin':namespace['pin'],'code_commit':commit,
 'qualifier_sha256':sha(recipe),'recipe_sha256':sha(Path(__file__)),'stages':list(namespace['stages']),
 'beam_assertions':sum(sum(rows.values()) for rows in namespace['runs'].values()),
 'focused_artifact_sha256':namespace['focused_artifacts'],'records_qualification_sha256':sha(E/'records-qualification.json'),
 'all_history_gates_audited':False,'sdk_selected':False,'compiler_proof_authority':False}
(E/'completed-gates-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'beam_assertions':report['beam_assertions'],'sdk_selected':False}))
