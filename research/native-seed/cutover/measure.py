#!/usr/bin/env python3
"""Run the verified cutover observer with a bounded process tree; summarize evidence."""
import argparse, hashlib, json, re, statistics, subprocess
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('preparation',type=Path)
    args=ap.parse_args()
    data=json.loads(args.preparation.read_text())
    # Recheck only bytes actually loaded at execution. Preparation already
    # verified build receipts and producer Sources; execution does not read C.
    for p,h in data['runtime_inputs'].items():
        assert sha(p)==h, p
    assert sha(data['observer']['path'])==data['observer']['sha256']
    output=args.preparation.parent
    command=['systemd-run','--user','--quiet','--collect','--wait','--pipe',
             '--working-directory='+str(Path.cwd()),'--property=MemoryMax=1500M',
             '--property=MemorySwapMax=0','--property=RuntimeMaxSec=90','--property=KillMode=control-group',*data['argv']]
    with (output/'native.log').open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=110)
    log=(output/'native.log').read_text()
    rows=[]; counts={}
    for line in log.splitlines():
        if line.startswith('CUTOVER_TIMING\t'):
            _,phase,variant,batch,repeats,seconds=line.split('\t')
            rows.append({'phase':phase,'variant':variant,'batch':int(batch),'repetitions':int(repeats),'seconds':float(seconds),'ms':float(seconds)*1000/int(repeats)})
        if line.startswith('CUTOVER_COUNTS\t'):
            _,variant,remote,matcher=line.split('\t')
            counts[variant]={'remote_calls':int(remote),'matcher_entries':int(matcher)}
    medians={}
    for phase in ['read','pipeline']:
        group={v:[r['ms'] for r in rows if r['phase']==phase and r['variant']==v] for v in ['reference','candidate']}
        if all(group.values()):
            medians[phase]={v:statistics.median(xs) for v,xs in group.items()}
            medians[phase]['speedup']=medians[phase]['reference']/medians[phase]['candidate']
    allocations = {}
    for label, block in re.findall(r'CUTOVER_ALLOCATION (reference|candidate)\n(.*?)(?=CUTOVER_|$)', log, re.S):
        found = re.search(r'(\d+) bytes allocated', block)
        if found:
            allocations[label] = {'repetitions': 5, 'bytes': int(found.group(1)), 'bytes_per_parse': int(found.group(1))/5}
    passed=result.returncode==0 and 'CUTOVER_PASS\n' in log and len(rows)==20
    checks=next((int(x.split()[1]) for x in log.splitlines() if x.startswith('CUTOVER_CHECKS ')),0)
    report={'schema':'bl.native.cutover-observation','passed':passed,'exit':result.returncode,'checks':checks,
            'medians_ms':medians,'allocations':allocations,'samples':rows,'counts':counts,'inventories':data['inventories'],
            'preparation_sha256':sha(args.preparation),'native_log_sha256':sha(output/'native.log'),
            'qualification':'closed serial reader prototype','production_cutover':False,'native_runtime_admission':False,
            'formal_lowering_proof':False,'sdk_builds':0}
    (output/'observation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['passed','exit','checks','medians_ms','counts']},indent=2))
    if not passed:
        print(log[-5000:])
        raise SystemExit(1)
if __name__=='__main__':main()
