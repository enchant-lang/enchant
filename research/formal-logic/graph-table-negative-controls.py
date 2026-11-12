"""Reject altered owned packets and false structural-instance proofs."""
import copy,hashlib,json,re,subprocess
from pathlib import Path
import graph_table_lean as bridge
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/graph-table-model'
export=bridge.read_export(E/'exports.json');base=export['packets'][0];results=[]
def mutated(change):
    packet=copy.deepcopy(base);change(packet);return packet

def row_payload(packet,kind,value):
    next(row for row in packet['rows'] if row[0]==kind)[1]=value

def forward(packet):
    for index,(kind,payload) in enumerate(packet['rows']):
        if kind in bridge.CONTAINERS and payload:
            if kind=='map':payload[0][0]=index
            else:payload[0]=index
            return
    raise AssertionError('nonempty container fixture')

def rehashed_wire(packet):
    data=bytearray.fromhex(packet['wire-hex']);data[-1]^=1
    packet['wire-hex']=data.hex();packet['checking']['reference']['sha256']=hashlib.sha256(data).hexdigest()

controls={
 'int-does-not-accept-float':lambda p:row_payload(p,'int',1.0),
 'bool-does-not-accept-int':lambda p:row_payload(p,'bool',0),
 'root-is-not-a-float':lambda p:p.__setitem__('root',float(p['root'])),
 'counts-are-not-floats':lambda p:p['checking'].__setitem__('nodes',float(p['checking']['nodes'])),
 'wrong-expanded-count':lambda p:p['checking'].__setitem__('expanded-nodes',p['checking']['expanded-nodes']+1),
 'wrong-depth':lambda p:p['checking'].__setitem__('depth',p['checking']['depth']+1),
 'nonfinite-runtime-float':lambda p:row_payload(p,'float64','83467ff0000000000000'),
 'reserved-keyword-scalar':lambda p:row_payload(p,'keyword',b'true'.hex()),
 'invalid-keyword-utf8':lambda p:row_payload(p,'keyword','ff'),
 'self-reference':forward,
 'forged-reference':lambda p:p['checking']['reference'].__setitem__('sha256','0'*64),
 'changed-wire-even-after-rehash':rehashed_wire,
 'extra-cached-view':lambda p:p.__setitem__('view',{}),
 'forged-compiler-authority':lambda p:p['checking'].__setitem__('compiler-proof-authority',True)}
for name,change in controls.items():
    try:bridge.read_packet(mutated(change))
    except bridge.Refused as e:results.append({'name':name,'status':'refused','reason':str(e)})
    else:raise AssertionError('accepted negative control: '+name)

T=json.loads((P/'metatheory/tool-pin.json').read_text());lean=Path(T['path'])/'bin/lean'
assert hashlib.sha256(lean.read_bytes()).hexdigest()==T['binary_sha256']
source=(E/'instances/Instance0.lean').read_text();negative=E/'rejected';negative.mkdir(exist_ok=True)
false_count=source.replace(').expandedNodes = 31 := by',').expandedNodes = 32 := by')
assert false_count!=source
# Bypass the packet reader deliberately: Fin bounds must also be enforced by Lean.
lines=source.splitlines();changed=False
for i,line in enumerate(lines):
    if line.startswith('def row') and 'Row.node' in line:
        altered=re.sub(r'⟨\d+, by decide⟩','⟨999999, by decide⟩',line,count=1)
        if altered!=line:lines[i]=altered;changed=True;break
assert changed
for name,body in [('false-original-count',false_count),('invalid-prior-reference','\n'.join(lines)+'\n')]:
    path=negative/(name+'.lean');path.write_text(body);output=path.with_suffix('.olean');log=path.with_suffix('.txt')
    command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--working-directory='+str(R),'--property=MemoryMax=2G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=120','--property=KillMode=control-group','--setenv=LEAN_PATH='+str(E),str(lean),'--root='+str(negative),'-o',str(output),str(path)]
    with log.open('w') as f:code=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT).returncode
    text=log.read_text();assert code!=0 and not output.exists() and 'error' in text,(name,code,text[-1500:])
    results.append({'name':name,'status':'not-accepted-by-Lean','exit_code':code,'source_sha256':hashlib.sha256(body.encode()).hexdigest(),'command':command,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'olean_present':False})
(E/'negative-controls.json').write_text(json.dumps({'status':'passed','controls':results,'compiler_proof_authority':False},indent=2)+'\n')
print(json.dumps({'packet_refusals':len(controls),'Lean_refusals':2,'status':'passed'}))
