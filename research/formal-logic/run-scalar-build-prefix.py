"""Run one fresh sandbox capability observation, then the gated SDK preparation."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-integration'
E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');packet=read(P/'evidence/scalar-integration-prototype/packets/qualification.json')
assert packet['status']=='passed' and packet['base_sdk_pin']==pin and packet['records']==4
files=[Path(__file__),P/'build-scalar-integration-sdk.py',P/'proposals/scalar-kvm-builder-probe.nix',R/'flake.lock']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('build-prefix-source-pin.json',{'code_commit':commit,'source_sha256':digests,'baseline_sdk_pin':pin,
 'packet_qualification_sha256':sha(P/'evidence/scalar-integration-prototype/packets/qualification.json')})
command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--working-directory='+str(R),
 '--property=MemoryMax=1G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=300','--property=KillMode=control-group',
 'nix-build',str(P/'proposals/scalar-kvm-builder-probe.nix'),'--no-out-link']
write('kvm-command.json',command);(E/'kvm-memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
started=time.monotonic()
with (E/'kvm-checks.txt').open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
write('kvm-exit.json',{'exit_code':code,'elapsed_seconds':time.monotonic()-started});assert code==0
paths=re.findall(r'^(/nix/store/[^\s]+formal-scalar-kvm-sandbox-probe-20261114)$',(E/'kvm-checks.txt').read_text(),re.M)
assert len(paths)==1;product=Path(paths[0]);observed=read(product)
assert observed['status']=='passed' and observed['api_version']==12
assert observed['device_opened_read_write'] and observed['empty_vm_created_and_closed']
(E/'kvm-sandbox.json').write_bytes(product.read_bytes())
write('kvm-sandbox-provenance.json',{'recorded_utc':datetime.now(timezone.utc).isoformat(),
 'source_sha256':sha(P/'proposals/scalar-kvm-builder-probe.nix'),'flake_lock_sha256':sha(R/'flake.lock'),
 'product':str(product),'product_nar_hash':subprocess.check_output(['nix-store','--query','--hash',product],text=True).strip(),
 'scope':'Fresh actual sandbox device open/API/VM observation before scalar integration SDK preparation. No operator Source change.'})
print(json.dumps({'stage':'kvm-sandbox','status':'passed'}),flush=True)
code=subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/'build-scalar-integration-sdk.py')],cwd=R).returncode
assert all(sha(R/n)==d for n,d in digests.items())
raise SystemExit(code)
