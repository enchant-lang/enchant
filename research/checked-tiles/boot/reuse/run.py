"""Exercise file-to-file native compilation and verified Datom reuse on one resident coordinator."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import statistics
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TILES = HERE.parent.parent
ROOT = TILES.parents[1]
SEED = ROOT/'research/native-seed'
sys.path.insert(0, str(HERE.parent))
from cutover_candidate import qualified


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def median(rows, column='us'):
    return statistics.median(r[column] for r in rows)


def exchange(endpoint, job):
    start=time.monotonic_ns()
    payload=json.dumps(job).encode()
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(180)
        client.connect(str(endpoint))
        client.sendall(struct.pack('!I',len(payload))+payload)
        with client.makefile('rb') as response:
            header=response.read(4)
            if len(header)!=4:
                raise RuntimeError('Incomplete response header')
            size,=struct.unpack('!I',header)
            if size>1024*1024:
                raise RuntimeError('Oversized compiler receipt')
            answer=json.loads(response.read(size))
    if 'error' in answer:
        raise ValueError(answer['error'])
    return dict(answer['ok'],roundtrip_us=(time.monotonic_ns()-start)/1000)


def compile_args(args):
    src=args.source.resolve()
    return ['compile',str(src),args.label or str(src),args.namespace,str(args.output.resolve()),args.clean,'staged']


def coordinator(lab, argv):
    pins = read(TILES/'tools.json')
    sdk = Path(pins['sdk'])
    evidence = TILES/'evidence/boot-self-hosted-fields.json'
    captured = lab/'qualification.json'
    shutil.copyfile(evidence,captured)
    q = read(captured)
    build = (argv.candidate or SEED/'out/checked-fields-build').resolve()
    contract = [pins['descriptor_sha256'], digest(captured)]
    if digest(sdk/'artifact.json') != contract[0]:
        raise ValueError('SDK digest mismatch')
    # The worker opens only private copies after verification. No mutable image
    # or macro bundle path is consulted between two requests in a session.
    image, macros = q['images']['stage2'], q['prepared_macros']
    if argv.candidate:
        candidate = qualified(build)
        image, macros = candidate['image'], candidate['bundle']
        contract.append(candidate['qualification'])
    for name, sha in [('stage2',image),('eval-prepared.scm',macros),
                      ('translate.scm',digest(HERE/'translate.scm'))]:
        dest = lab/name
        shutil.copy2((HERE if name=='translate.scm' else build)/name,dest)
        if digest(dest)!=sha:
            raise ValueError('Native compiler input mismatch: '+name)
        contract.append(sha)
    # Lazy BL loads must observe the same emitter and index adapter that
    # selected this cache. Bind relative names and the actual private bytes.
    sources=lab/'sources'
    provider_root=SEED/'src'
    providers=[(p.relative_to(provider_root),p) for p in sorted(provider_root.rglob('*.bl'))]
    providers.extend((Path('reuse')/name,HERE/name) for name in ('request.bl','sdk.bl','driver.bl'))
    for name,src in providers:
        dest=sources/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dest)
        contract.append([str(name),digest(dest)])
    tool = hashlib.sha256(json.dumps(contract).encode()).hexdigest()
    env = dict(os.environ,BL_REPEAT_LAB=str(lab),BL_REPEAT_BUNDLE=str(lab/'eval-prepared.scm'),
               BL_REPEAT_TOOL=tool,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    env.pop('BL_REPEAT_FIXED_BATCH', None)
    def server_args(cache,endpoint):
        return [sdk/'bin/bl','--cold','-p',sources,'run',sources/'reuse/driver.bl','--',cache,endpoint]

    @contextmanager
    def server(cache):
        endpoint=lab/'compiler.sock'
        with (lab/'server.log').open('w+') as log, subprocess.Popen(server_args(cache,endpoint),cwd=ROOT,
                 env=env,stdout=log,stderr=subprocess.STDOUT) as proc:
            try:
                deadline=time.monotonic()+90
                while not endpoint.exists():
                    if proc.poll() is not None or time.monotonic()>deadline:
                        log.seek(0)
                        raise RuntimeError('Compiler did not start: '+log.read()[-2000:])
                    time.sleep(.02)
                yield endpoint
            finally:
                try:
                    if proc.poll() is None and endpoint.exists():
                        exchange(endpoint,'stop')
                        proc.wait(timeout=4)
                finally:
                    if proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()

    def run(jobs,cache):
        start=time.monotonic_ns()
        with server(cache) as endpoint:
            rows=[]
            for job in jobs:
                rows.append(exchange(endpoint,job))
            wall=(time.monotonic_ns()-start)/1000000
            return rows,wall
    if argv.serve:
        endpoint=argv.serve.absolute()
        parent=endpoint.parent.stat()
        if parent.st_uid!=os.getuid() or parent.st_mode & 0o077:
            raise ValueError('Place the socket in a private directory owned by the current user (mode 0700)')
        if os.path.lexists(endpoint):
            raise FileExistsError(endpoint)
        print('Compiler socket will be available at '+str(endpoint),flush=True)
        subprocess.run(server_args(argv.cache.resolve(),endpoint),cwd=ROOT,env=env,check=True)
        return
    if not argv.bench:
        rows,wall=run([compile_args(argv)],argv.cache.resolve())
        print(json.dumps(dict(request=rows[0],cold_coordinator_ms=wall),indent=2))
        return
    out=argv.bench.resolve()
    out.mkdir()
    client=out/'repeat-client'
    subprocess.run([pins['go'],'build','-trimpath','-o',client,HERE/'client.go'],check=True,cwd=HERE,
                   env=dict(os.environ,GO111MODULE='off',GOTOOLCHAIN='local',CGO_ENABLED='0',GOFLAGS='-p=2'))
    cache=out/'datom'
    rows=[]
    jobs=[]
    boot=SEED/'out/checked-boot-replay/pipeline/reader.bl'
    def job(name,path,label,ns,clean=False,order='stream'):
        return [name,str(path),label,ns,str(out/(name+'.scm')),clean,order]
    def reader(name,clean=False,order='staged'):
        return job(name,boot,'priv/boot/reader.bl','reader',clean,order)
    jobs.append(reader('reader-first'))
    jobs.extend(reader('reader-hit-'+str(i)) for i in range(12))
    # A client can request an edit profile before any SDK translation has
    # initialized optional namespaces in the coordinator.
    solo=out/'standalone.bl'
    solo.write_text('(ns repeat.init)\n(defn p-a [x-a] (erlang/+ x-a 2))\n(defn p-b [x-b] (p-a x-b))\n')
    jobs.append(job('standalone-first',solo,'init.bl','repeat.init',order='staged'))
    for i,order in enumerate(['staged','stream','stream','staged']*2):
        jobs.append(reader('baseline-'+str(i)+'-'+order,True,order))
        jobs.append(reader('sdk-clean-'+str(i),True,'sdk'))
    jobs.append(reader('sdk-first',False,'sdk'))
    jobs.extend(reader('sdk-hit-'+str(i),False,'sdk') for i in range(12))
    for namespace in ('anf','diag'):
        label=f'priv/boot/{namespace}.bl'
        for mode,clean in [('first',False),('repeat',False),('sdk',True)]:
            jobs.append(job(f'{namespace}-{mode}',ROOT/label,label,namespace,clean,
                            'sdk' if mode=='sdk' else 'staged'))
    before=out/'before.bl'
    after=out/'after.bl'
    before.write_text('(ns repeat.demo)\n(defn p-leaf [] 41)\n(defn p-mid [] (p-leaf))\n'
                      '(defn p-main [] (p-mid  ))\n(defn p-other [] 12)\n')
    after.write_text(before.read_text().replace('41','42'))
    def edit(name,src,clean=False,label='demo.bl'):
        return job(name,src,label,'repeat.demo',clean)
    cyclic=out/'cycle.bl'
    cyclic.write_text(before.read_text().replace('[] 41','[] (p-main)'))
    rewired=out/'rewired.bl'
    rewired.write_text(after.read_text().replace('(p-mid  )','(p-other)'))
    jobs += [edit('graph-first',before),edit('graph-hit',before),edit('graph-edit',after),
             edit('graph-edit-clean',after,True),edit('graph-revert',before),
             edit('graph-clean',before,True),edit('graph-moved',before,label='moved.bl'),
             edit('graph-rewired',rewired),edit('graph-rewired-clean',rewired,True),
             edit('graph-cycle',cyclic),edit('graph-cycle-clean',cyclic,True)]
    large=out/'arithmetic.bl'
    leaf='(defn p-seed [x-one] (erlang/+ x-one 41))'
    other='(defn p-cost [x-one] (erlang/* x-one 2))'
    lines=[leaf,other,'(defn p-join [x-one] (erlang/+ (p-seed x-one) (p-cost x-one)))']
    for i in range(48):
        expr='x-one'
        for j in range(20):
            expr=f'(erlang/+ {j} {expr})'
        lines.append(f'(defn p-row{i} [x-one] {expr})')
    large.write_text('(ns repeat.demo)\n'+'\n'.join(lines)+'\n')
    changed=out/'arithmetic-edited.bl'
    changed.write_text(large.read_text().replace(leaf,leaf.replace('41','42')))
    jobs.extend([edit('arithmetic-first',large),edit('arithmetic-repeat',large),edit('arithmetic-edit',changed),
                 edit('arithmetic-edit-clean',changed,True),edit('arithmetic-revert',large)])
    rows,elapsed=run(jobs,cache)
    (out/'requests.json').write_text(json.dumps(rows,indent=2)+'\n')
    by_name={r['job']:r for r in rows}
    assert all(r['sha256']==digest(out/(r['job']+'.scm')) for r in rows)
    assert by_name['reader-first']['compiled']==104
    assert by_name['standalone-first']['names']==['p-a','p-b']
    assert by_name['sdk-first']['compiled']==104
    expected=q['jobs']['reader']['output']
    assert all(r['sha256']==expected for r in rows if r['job'].startswith(('reader','baseline','sdk')))
    for namespace in ('anf','diag'):
        first,repeat,sdk_job=(by_name[f'{namespace}-{mode}'] for mode in ('first','repeat','sdk'))
        assert first['sha256']==repeat['sha256']==sdk_job['sha256']==q['jobs'][namespace]['output']
        assert first['compiled']==sdk_job['compiled']>0 and repeat['route']=='artifact'
    assert all(r['route']=='artifact' and r['compiled']==0 for r in rows if '-hit' in r['job'])
    assert by_name['graph-first']['compiled']==4
    assert by_name['graph-first']['codebase']=='indexed' and by_name['graph-edit']['codebase']=='reused'
    assert by_name['graph-rewired']['names']==['p-main'] and by_name['graph-rewired']['codebase']=='indexed'
    assert by_name['graph-rewired']['sha256']==by_name['graph-rewired-clean']['sha256']
    assert by_name['graph-edit']['names']==['p-leaf','p-mid','p-main']
    assert by_name['graph-edit']['sha256']==by_name['graph-edit-clean']['sha256']!=by_name['graph-first']['sha256']
    assert by_name['graph-revert']['route']=='artifact'
    assert by_name['graph-first']['sha256']==by_name['graph-clean']['sha256']==by_name['graph-revert']['sha256']
    assert by_name['graph-moved']['compiled']==4
    assert by_name['graph-cycle']['route']=='cycle' and by_name['graph-cycle']['sha256']==by_name['graph-cycle-clean']['sha256']
    assert by_name['arithmetic-edit']['names']==['p-seed','p-join']
    assert by_name['arithmetic-edit']['sha256']==by_name['arithmetic-edit-clean']['sha256']
    assert by_name['arithmetic-revert']['sha256']==by_name['arithmetic-first']['sha256']
    executed={}
    for name,want in [('graph-first','41 12'),('graph-edit','42 12'),('graph-rewired','12 12'),('graph-revert','41 12'),
                      ('arithmetic-first','47 192'),('arithmetic-edit','48 192'),('arithmetic-revert','47 192')]:
        result=subprocess.check_output([lab/'stage2','--eval',HERE/'check-result.scm','unused'],
                      text=True,env=dict(env,BL_REPEAT_RESULT=str(out/(name+'.scm')),
                                         BL_REPEAT_FIXTURE=name.split('-')[0]),timeout=60).strip()
        assert result==want, (name,result)
        executed[name]=result
    bad=out/'bad.bl'
    bad.write_text(before.read_text().replace('(p-mid  )','(p-absent)'))
    bad_arity=out/'bad-arity.bl'
    bad_arity.write_text(before.read_text().replace('(p-mid  )','(p-mid 1)'))
    process_times=[]
    native_client_times={'hit':[],'clean':[],'sdk':[]}
    begin=time.monotonic_ns()
    with server(cache) as endpoint:
        durable=exchange(endpoint,reader('reader-restart'))
        restart=(time.monotonic_ns()-begin)/1e6
        assert durable['route']=='artifact' and durable['sha256']==expected
        for _ in range(5):
            begin=time.monotonic_ns()
            receipt=subprocess.check_output([sys.executable,__file__,'--connect',str(endpoint),'--namespace','reader',
                    '--label','priv/boot/reader.bl',str(boot),str(out/'client.scm')],text=True,timeout=60)
            process_times.append((time.monotonic_ns()-begin)/1e6)
            assert json.loads(receipt)['route']=='artifact' and digest(out/'client.scm')==expected
        for i in range(5):
            for arm in (('clean','hit','sdk') if i%2==0 else ('sdk','hit','clean')):
                flags=[] if arm=='hit' else ['-'+arm]
                begin=time.monotonic_ns()
                receipt=subprocess.check_output([client,*flags,endpoint,'reader','priv/boot/reader.bl',
                                                boot,out/'client.scm'],timeout=60)
                native_client_times[arm].append((time.monotonic_ns()-begin)/1e6)
                assert json.loads(receipt)['route']==('artifact' if arm=='hit' else 'full')
                assert digest(out/'client.scm')==expected
        for rejected in (bad,bad_arity):
            negative=edit('graph-edit',rejected)
            unchanged=digest(Path(negative[4]))
            try:
                exchange(endpoint,negative)
            except ValueError as exc:
                if 'unresolved, duplicate or wrong-arity' not in str(exc):
                    raise
            else:
                raise ValueError('Invalid request was accepted')
            assert digest(Path(negative[4]))==unchanged
        # Damage only the disposable replay's blob. Reproduction must repair
        # both its content and the next pre-reader hit on this running service.
        blob=cache/'bytes'/expected[:2]/expected[2:4]/expected
        assert digest(blob)==expected
        blob.write_bytes(b'damaged replay blob')
        repair=exchange(endpoint,reader('reader-repair'))
        repaired=exchange(endpoint,reader('reader-repaired-hit'))
        assert repair['compiled']==104 and repair['sha256']==digest(blob)==expected
        assert repaired['route']=='artifact' and digest(out/'reader-repaired-hit.scm')==expected
    hits=[r for r in rows if r['job'].startswith('reader-hit-')]
    totals={}
    for mode in ('staged','stream'):
        selected=[r for r in rows if r['job'].startswith('baseline') and r['job'].endswith(mode)]
        totals[mode]=dict(request_ms=median(selected)/1000,native_ms=median(selected,'native-us')/1000)
    hot=median(hits)
    clean_transport=median([r for r in rows if r['job'].startswith('baseline') and r['job'].endswith('staged')],'roundtrip_us')
    hit_transport=median(hits,'roundtrip_us')
    summary=dict(first_ms=by_name['reader-first']['us']/1000,hit_ms=hot/1000,
                 clean_over_hit=totals['staged']['request_ms']*1000/hot,
                 clean=totals,restarted_request_ms=durable['us']/1000,cold_coordinator_hit_ms=restart,
                 standalone_client_ms=statistics.median(process_times))
    sdk_roundtrip=median([r for r in rows if r['job'].startswith('sdk-clean-')],'roundtrip_us')
    sdk_hit=median([r for r in rows if r['job'].startswith('sdk-hit-')],'roundtrip_us')
    summary.update(sdk_clean_ms=sdk_roundtrip/1000,sdk_hit_ms=sdk_hit/1000,sdk_clean_over_native_hit=sdk_roundtrip/hit_transport)
    summary.update(roundtrip_hit_ms=hit_transport/1000,roundtrip_clean_ms=clean_transport/1000,
                   roundtrip_speedup=clean_transport/hit_transport)
    summary['native_cli_ms']={arm:statistics.median(samples) for arm,samples in native_client_times.items()}
    report=dict(tool=tool,sdk=contract[0],image=image,input=digest(boot),
                outputs=rows+[durable,repair,repaired],summary=summary,invalid_edit_preserved_output=True,
                executed=executed,standalone_client_samples_ms=process_times,native_cli_samples_ms=native_client_times,
                native_client_sha256=digest(client),first_batch_with_startup_ms=elapsed)
    (out/'repeat.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bench',type=Path,help='Write the replay to a fresh directory')
    p.add_argument('--candidate',type=Path,help='A rebuilt native compiler with a complete fixed-point receipt')
    p.add_argument('--serve',type=Path,help='Start a resident compiler on a private Unix socket')
    p.add_argument('--connect',type=Path,help='Use an existing resident compiler')
    p.add_argument('--stop',action='store_true')
    p.add_argument('--cache',type=Path)
    p.add_argument('--namespace')
    p.add_argument('--label',help='Logical source filename used in diagnostics/emitted code')
    p.add_argument('--clean',action='store_true')
    p.add_argument('source',type=Path,nargs='?')
    p.add_argument('output',type=Path,nargs='?')
    args=p.parse_args()
    if args.connect:
        if not args.stop and not all((args.source,args.output,args.namespace)):
            p.error('--connect requires --stop or --namespace NS SOURCE OUTPUT')
        print(json.dumps(exchange(args.connect,'stop' if args.stop else compile_args(args)),indent=2))
        return
    if args.serve and not args.cache:
        p.error('--serve requires --cache DIR')
    if not (args.serve or args.bench) and not all((args.source,args.output,args.namespace,args.cache)):
        p.error('supply --bench DIR or --cache DIR --namespace NS SOURCE OUTPUT')
    with tempfile.TemporaryDirectory(prefix='enchant-repeat-') as lab:
        coordinator(Path(lab),args)

if __name__=='__main__':
    main()
