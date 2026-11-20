"""Exercise file-to-file native compilation and verified Datom reuse on one resident coordinator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
TILES = HERE.parent.parent
ROOT = TILES.parents[1]
SEED = ROOT/'research/native-seed'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def median(rows, column='us'):
    return statistics.median(r[column] for r in rows)


def coordinator(lab, argv):
    pins = read(TILES/'tools.json')
    sdk = Path(pins['sdk'])
    evidence = TILES/'evidence/boot-self-hosted-fields.json'
    q = read(evidence)
    build = SEED/'out/checked-fields-build'
    contract = [pins['descriptor_sha256'], digest(evidence), digest(HERE/'request.bl'),
                digest(SEED/'src/native/fragments.bl')]
    if digest(sdk/'artifact.json') != contract[0]:
        raise ValueError('SDK digest mismatch')
    # The worker opens only private copies after verification. No mutable image
    # or macro bundle path is consulted between two requests in a session.
    for name, sha in [('stage2',q['images']['stage2']),('eval-prepared.scm',q['prepared_macros']),
                      ('translate.scm',digest(HERE/'translate.scm'))]:
        dest = lab/name
        shutil.copy2((HERE if name=='translate.scm' else build)/name,dest)
        if digest(dest)!=sha:
            raise ValueError('Native compiler input mismatch: '+name)
        contract.append(sha)
    tool = hashlib.sha256(json.dumps(contract).encode()).hexdigest()
    env = dict(os.environ,BL_REPEAT_LAB=str(lab),BL_REPEAT_BUNDLE=str(lab/'eval-prepared.scm'),
               BL_REPEAT_TOOL=tool,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    def run(jobs,cache,allow_failure=False):
        manifest=lab/'jobs.json'
        manifest.write_text(json.dumps(jobs))
        start=time.monotonic_ns()
        result=subprocess.run([sdk/'bin/bl','--cold','-p',SEED/'src','-p',HERE.parent,'run',
                    HERE/'driver.bl','--',cache,manifest],cwd=ROOT,env=env,
                    text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
        wall=(time.monotonic_ns()-start)/1000000
        if allow_failure:
            if not result.returncode or 'Repeat compile:' not in result.stdout:
                raise RuntimeError('Expected profile refusal: '+result.stdout[-1500:])
            return
        if result.returncode:
            raise RuntimeError(result.stdout[-3000:])
        rows=[json.loads(l[9:]) for l in result.stdout.splitlines() if l.startswith('COMPILED ')]
        if len(rows)!=len(jobs):
            raise RuntimeError('Incomplete job list: '+result.stdout[-600:])
        return rows,wall
    if not argv.bench:
        ns=argv.namespace
        source=argv.source.resolve()
        label=argv.label or str(source)
        rows,wall=run([['compile',str(source),label,ns,str(argv.output.resolve()),argv.clean,'stream']],
                      argv.cache.resolve())
        print(json.dumps(dict(request=rows[0],cold_coordinator_ms=wall),indent=2))
        return
    out=argv.bench.resolve()
    out.mkdir()
    cache=out/'datom'
    rows=[]
    jobs=[]
    boot=SEED/'out/checked-boot-replay/pipeline/reader.bl'
    def job(name,path,label,ns,clean=False,order='stream'):
        return [name,str(path),label,ns,str(out/(name+'.scm')),clean,order]
    def reader(name,clean=False,order='stream'):
        return job(name,boot,'priv/boot/reader.bl','reader',clean,order)
    jobs.append(reader('reader-first'))
    jobs.extend(reader('reader-hit-'+str(i)) for i in range(12))
    for i,order in enumerate(['staged','stream','stream','staged']*2):
        jobs.append(reader('baseline-'+str(i)+'-'+order,True,order))
    before=out/'before.bl'
    after=out/'after.bl'
    before.write_text('(ns repeat.demo)\n(defn p-leaf [] 41)\n(defn p-mid [] (p-leaf))\n'
                      '(defn p-main [] (p-mid))\n(defn p-other [] 12)\n')
    after.write_text(before.read_text().replace('41','42'))
    def edit(name,src,clean=False,label='demo.bl'):
        return job(name,src,label,'repeat.demo',clean)
    cyclic=out/'cycle.bl'
    cyclic.write_text(before.read_text().replace('[] 41','[] (p-main)'))
    jobs += [edit('graph-first',before),edit('graph-hit',before),edit('graph-edit',after),
             edit('graph-edit-clean',after,True),edit('graph-revert',before),
             edit('graph-clean',before,True),edit('graph-moved',before,label='moved.bl'),
             edit('graph-cycle',cyclic),edit('graph-cycle-clean',cyclic,True)]
    rows,elapsed=run(jobs,cache)
    by_name={r['job']:r for r in rows}
    assert by_name['reader-first']['compiled']==104
    expected=q['jobs']['reader']['output']
    assert all(r['sha256']==expected for r in rows if r['job'].startswith(('reader','baseline')))
    assert all(r['route']=='artifact' and r['compiled']==0 for r in rows if '-hit' in r['job'])
    assert by_name['graph-first']['compiled']==4
    assert by_name['graph-edit']['names']==['p-leaf','p-mid','p-main']
    assert by_name['graph-edit']['sha256']==by_name['graph-edit-clean']['sha256']!=by_name['graph-first']['sha256']
    assert by_name['graph-revert']['route']=='artifact'
    assert by_name['graph-first']['sha256']==by_name['graph-clean']['sha256']==by_name['graph-revert']['sha256']
    assert by_name['graph-moved']['compiled']==4
    assert by_name['graph-cycle']['route']=='cycle' and by_name['graph-cycle']['sha256']==by_name['graph-cycle-clean']['sha256']
    durable,restart=run([reader('reader-restart')],cache)
    assert durable[0]['route']=='artifact' and durable[0]['sha256']==expected
    bad=out/'bad.bl'
    bad.write_text(before.read_text().replace('(p-mid)','(p-absent)'))
    negative=edit('graph-edit',bad)
    unchanged=digest(Path(negative[4]))
    run([negative],cache,True)
    assert digest(Path(negative[4]))==unchanged
    hits=[r for r in rows if r['job'].startswith('reader-hit-')]
    totals={}
    for mode in ('staged','stream'):
        selected=[r for r in rows if r['job'].startswith('baseline') and r['job'].endswith(mode)]
        totals[mode]=dict(request_ms=median(selected)/1000,native_ms=median(selected,'native-us')/1000)
    hot=median(hits)
    summary=dict(first_ms=by_name['reader-first']['us']/1000,hit_ms=hot/1000,
                 clean_over_hit=totals['stream']['request_ms']*1000/hot,
                 clean=totals,restarted_request_ms=durable[0]['us']/1000,cold_coordinator_hit_ms=restart)
    report=dict(tool=tool,sdk=contract[0],image=q['images']['stage2'],input=digest(boot),
                outputs=rows+durable,summary=summary,invalid_edit_preserved_output=True,
                first_coordinator_ms=elapsed)
    (out/'repeat.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bench',type=Path,help='Write the replay to a fresh directory')
    p.add_argument('--cache',type=Path)
    p.add_argument('--namespace')
    p.add_argument('--label',help='Logical source filename used in diagnostics/emitted code')
    p.add_argument('--clean',action='store_true')
    p.add_argument('source',type=Path,nargs='?')
    p.add_argument('output',type=Path,nargs='?')
    args=p.parse_args()
    if not args.bench and not all((args.source,args.output,args.namespace,args.cache)):
        p.error('supply --bench DIR or --cache DIR --namespace NS SOURCE OUTPUT')
    with tempfile.TemporaryDirectory(prefix='enchant-repeat-') as lab:
        coordinator(Path(lab),args)

if __name__=='__main__':
    main()
