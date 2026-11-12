"""Serial capped stages for the separate structural graph-model connection."""
import hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/graph-table-model'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');requirement=Path(pin['sdk'])/'artifact.json';assert sha(requirement)==pin['descriptor_sha256']
tool=read(P/'metatheory/tool-pin.json');lean=Path(tool['path'])/'bin/lean';assert sha(lean)==tool['binary_sha256']
stage=sys.argv[1];cleanup=[]
def bounded(argv,extra=(),memory='2G',cwd=R):
    return ['systemd-run','--user','--quiet','--collect','--wait','--pipe','--working-directory='+str(cwd),
            '--property=MemoryMax='+memory,'--property=MemorySwapMax=0','--property=RuntimeMaxSec=900','--property=KillMode=control-group',*extra,*map(str,argv)]
if stage=='export':
    runtime=Path(tempfile.mkdtemp(prefix='formal-graph-model-runtime-'));cwd=Path(tempfile.mkdtemp(prefix='formal-graph-model-cwd-'));cleanup=[runtime,cwd]
    command=bounded(['env','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY','-u','BEAM_LISP_PATH',Path(pin['sdk'])/'bin/bl','--cold','run',P/'graph-table-export.bl','--',E/'exports.json',P/'evidence/question-graphs/owned-points.etf'],['--setenv=XDG_RUNTIME_DIR='+str(runtime)],memory='4G',cwd=cwd)
elif stage=='generate':command=bounded(['python3',P/'graph_table_lean.py',E/'exports.json',E/'instances'])
elif stage=='instances':
    model=E/'GraphTable.olean';assert model.is_file()
    inputs=read(E/'instances/inputs.json');results=[]
    for row in inputs['instances']:
        source=E/'instances'/row['source'];assert sha(source)==row['source_sha256']
        output=source.with_suffix('.olean');log=source.with_suffix('.txt')
        command=bounded([lean,'--root='+str(source.parent),'-o',output,source],['--setenv=LEAN_PATH='+str(E)])
        write(source.with_suffix('.command.json'),command)
        with log.open('w') as f:code=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT).returncode
        write(source.with_suffix('.exit.json'),{'exit_code':code,'olean_present':output.is_file()})
        text=log.read_text();assert code==0 and output.is_file() and 'sorryAx' not in text and 'error:' not in text,(row['id'],code,text[-2000:])
        results.append({**row,'exit_code':code,'olean_sha256':sha(output),'log_sha256':sha(log),'imported_graph_table_sha256':sha(model)})
    write(E/'instances/results.json',{'status':'passed','instances':results,'sdk_pin':pin,'tool_pin':tool,'scope':'Owned exact-wire graph instances and structural node/depth model. No BL implementation or compiler preservation theorem.'})
    print(json.dumps({'stage':stage,'instances':len(results),'status':'passed'}));sys.exit(0)
else:raise ValueError(stage)
write(E/(stage+'-command.json'),command)
with (E/(stage+'-memory-before.txt')).open('w') as f:subprocess.run([R/'scripts/bl-mem'],stdout=f,check=True)
try:
    with (E/(stage+'-checks.txt')).open('w') as f:code=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT).returncode
finally:
    for path in cleanup:shutil.rmtree(path)
    write(E/(stage+'-runtime.json'),{'paths':list(map(str,cleanup)),'retired':all(not p.exists() for p in cleanup)})
write(E/(stage+'-exit.json'),{'exit_code':code});print(json.dumps({'stage':stage,'exit_code':code}));sys.exit(code)
