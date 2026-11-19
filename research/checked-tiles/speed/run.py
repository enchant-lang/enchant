"""Matched warm request latency on ordinary BL and Bend application code."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import select
import statistics
import struct
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TILES = HERE.parent
ROOT = TILES.parents[1]
SEED = ROOT / 'research/native-seed'
sys.path[:0] = [str(SEED), str(TILES / 'comparison')]
import native_elf
import native_module
import workstation

TOOLS = json.loads((TILES / 'tools.json').read_text())
BUN = '/nix/store/0gk371kgjyv7s0az07hxjrl8g9k0pf3m-bun-1.4.4/bin/bun'
NAMES = ['ping', 'serial', 'tree', 'scan', 'mapped', 'fused', 'moments', 'pipeline']
CORPUS = (ROOT / 'priv/boot/compiler.bl').read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected=None):
    actual = native_elf.digest(Path(path))
    if expected and expected != actual:
        raise ValueError('Qualified input changed: ' + str(path))
    return actual


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def ms(start):
    return (time.perf_counter_ns() - start) / 1e6


def job(argv, cwd=None, env=None, timeout=240):
    r = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout, text=True)
    if r.returncode:
        raise RuntimeError(f'{argv[0]} exited {r.returncode}: {r.stdout[-4000:]}')
    return r.stdout


def sample(k, n, seed, data=b''):
    if k == 0:
        value = seed
    elif k == 1:
        value = seed
        for _ in range(n):
            value = (3 * value + 1) % 65521
    elif k in (2, 6):
        value = sum(math.comb(n, i) * ((seed+i)**2+1) for i in range(n+1))
    elif k == 3:
        value = len(re.findall(rb'[0-9]+', data))
    elif k == 7:
        value = seed + sum(y for x in data if (y := (3*x+7)%256) < 128)
    else:
        value = sum((x+255)//2 for x in data)
    if not 0 <= value < 2**32 or (k in (3, 4, 5, 7) and len(data) != n):
        raise ValueError('Input outside shared numeric or payload domain')
    return k, n, seed, data, value


def case(k, n, seed):
    # Vary input independently of either implementation. Include actual compiler text.
    data = b''
    if k == 3:
        start = seed * 43
        data = CORPUS[start:start+n]
    elif k in (4, 5, 7):
        data = (bytes((i*37+seed) % 256 for i in range(256)) * ((n+255)//256))[:n]
    return sample(k, n, seed, data)


def controls():
    edge = b'//09a0\x00\xff1_234/55:58'
    rows = [case(k, 0, 0) for k in range(len(NAMES))]
    rows += [case(k, n, s) for k in range(len(NAMES)) for n, s in ((1, 255), (7, 13))]
    rows += [sample(k, len(edge), 127, edge) for k in (3, 4, 5, 7)]
    rows += [sample(k, 256, 99, bytes(range(256))) for k in (3, 4, 5, 7)]
    return rows


def workload_rows(quick, block, trial):
    rows = []
    for k in range(1, len(NAMES)):
        sizes = [8, 12, 15] if k in (2, 6) else [64, 4096, 32768]
        for i, n in enumerate(sizes[:2] if quick else sizes):
            seed = (17 + block*41 + trial*19 + i*7) % 256
            rows.append(case(k, n, seed))
    random.Random(1741 + block*19 + trial).shuffle(rows)
    return rows


def build(out, gpu):
    native = SEED / 'out/compiler-native-owner'
    qualification = json.loads((SEED / 'evidence/scheme-fixpoint/qualification.json').read_text())
    image = native/'stage2'
    bundle = native/'bundle.scm'
    image_sha = next(x['executable_sha256'] for x in qualification['builds'] if x['stage']=='stage2')
    bundle_sha = next(v for k,v in qualification['inputs'].items() if k.endswith('/compiler-native-owner/bundle.scm'))
    if not qualification['stage2-stage3-byte-equal']:
        raise ValueError('Native compiler fixpoint missing')
    sdk = Path(TOOLS['sdk'])
    receipt = dict(stage2=checked(image, image_sha), bundle=checked(bundle, bundle_sha),
                   sdk=checked(sdk/'artifact.json', TOOLS['descriptor_sha256']), steps_ms={}, modules={})
    def timed(name, argv, **kwargs):
        t = time.perf_counter_ns()
        log = job(argv, **kwargs)
        receipt['steps_ms'][name] = ms(t)
        return log

    receipt['lean'] = timed('Lean tree identity', [TOOLS['lean'], '-j2', HERE/'Tree.lean'])
    if 'sorryAx' in receipt['lean'] or 'SpeedTree.same' not in receipt['lean']:
        raise ValueError('Tree equality theorem did not close')
    env = dict(os.environ, SPEED_FIXTURES=str(HERE), SPEED_OUTPUT=str(out))
    timed('stage-two read/compile/emit both policies', [image, '--eval', HERE/'emit.scm', bundle], env=env)
    driver = out/'oracle.bl'
    driver.write_text((ROOT/'research/rt-selfhost/fusion/pipeline.bl').read_text()+'\n'+'\n'.join((HERE/f).read_text() for f in ('kernels.bl','emit.bl','oracle.bl')))
    rows = controls()
    save(out/'oracle-input.json', [dict(id=k,n=n,seed=s,data=list(d)) for k,n,s,d,_ in rows])
    timed('pinned BEAM oracle and current emitter', [sdk/'bin/bl','--cold','-p',SEED/'src','run',driver,
          '--',out,HERE/'kernels.bl'], env=dict(env, ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'))
    if json.loads((out/'oracle.json').read_text()) != [r[-1] for r in rows]:
        raise ValueError('Ordinary BEAM and independent oracle differ')
    receipt['ordinary_beam_observations'] = len(rows)
    commands = {}
    for policy, opt in [('reference',0),('reference',2),('guarded',2),('linked',2),('hoisted',2),('shapes',2)]:
        name = f'{policy}-O{opt}'
        code = (HERE/'arithmetic.scm').read_bytes() + (out/(policy+'.scm')).read_bytes()
        cfg = native_elf.configuration(SEED, True, checked)
        cfg['flags'][0] = f'-O{opt}'
        cfg['tool_identity']['flags'] = cfg['flags']
        def tool_run(label, argv, cwd, build):
            return timed(name+' '+label, argv, cwd=cwd)
        r = native_module.build_module(out/name, code, digest(name.encode()+code), cfg, cache=out/'objects',
            report={}, bind=checked, run=tool_run, save=lambda:None)
        obj = r['artifacts']['module']
        receipt['modules'][name] = dict(source_sha256=digest(code), elf_sha256=obj['sha256'],cflags=cfg['flags'])
        commands[name] = [image, '--eval', HERE/'serve.scm', obj['path']]

    tooling = out/'bend-tools'
    tooling.mkdir()
    tree = Path(env['BEND_TREE']) if 'BEND_TREE' in env else workstation.bend(tooling)
    for name, expected in json.loads((TILES/'comparison/bend-blobs.json').read_text()).items():
        buf = (tree/name).read_bytes()
        if hashlib.sha1(f'blob {len(buf)}\0'.encode()+buf).hexdigest() != expected:
            raise RuntimeError('Bend compiler pin mismatch for '+name)
    env.update(CC=str(cfg['clang']))
    if gpu:
        kit = Path(env['CUDA_HOME']) if 'CUDA_HOME' in env else workstation.cuda(tooling)
        env['CUDA_HOME'] = str(kit)
        env['LD_LIBRARY_PATH'] = ':'.join([str(kit/'lib'),str(kit/'lib64'),'/run/opengl-driver/lib',
            '/nix/store/chqq8mpmpyfi9kgsngya71akv5xicn03-gcc-15.2.0-lib/lib',env.get('LD_LIBRARY_PATH','')])
    exe = out/'bend'
    timed('Bend compile and link', [env.get('BUN',BUN),tree/'bend2/main.ts',HERE/'kernels.bend','-o',exe], env=env)
    receipt.update(bend_commit=workstation.PIN,bend_elf_sha256=checked(exe),
                   bun_sha256=checked(env.get('BUN',BUN)))
    for threads in [1,4]:
        commands[f'bend-cpu{threads}'] = [exe,'+RTS','--threads',str(threads),'--gpu','off']
    if gpu:
        receipt['bend_gpu_sha256'] = checked(out/'bend.gpu')
        receipt['device'] = job(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader']).strip()
        commands['bend-gpu'] = [exe,'+RTS','--threads','4','--gpu','512MB']
    save(out/'build.json',receipt)
    return commands, env, receipt


def run_block(argv, env, out, name, block, trials):
    warm = controls()
    warm.extend(trials[0])
    ping = sample(0, 0, 117)
    requests = [ping, *warm, *[r for trial in trials for r in trial]]
    samples = {}
    with (out/f'{name}-{block}.log').open('wb') as log:
        start = time.perf_counter_ns()
        proc = subprocess.Popen(argv, cwd=out, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
        try:
            proc.stdin.write(struct.pack('>H',len(requests)))
            for i, (k,n,seed,data,want) in enumerate(requests):
                t = time.perf_counter_ns()
                proc.stdin.write(struct.pack('>BHB',k,n,seed)+data)
                proc.stdin.flush()
                if not select.select([proc.stdout],[],[],90)[0]:
                    raise TimeoutError(f'{name}: timeout on {NAMES[k]} {n}')
                answer = proc.stdout.readline()
                duration = ms(t)
                if answer.strip() != str(want).encode():
                    raise RuntimeError(f'{name}: {NAMES[k]} n={n} seed={seed}: got {answer[:100]!r}, expected {want}')
                if i == 0:
                    startup = ms(start)
                if i > len(warm):
                    samples.setdefault(f'{NAMES[k]}/{n}',[]).append(round(duration,5))
            proc.stdin.close()
            proc.wait(timeout=20)
            if proc.returncode:
                raise RuntimeError(f'{name} exited {proc.returncode}')
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdin.close()
            proc.stdout.close()
    return dict(startup_ms=round(startup,4), samples_ms=samples,checked=len(requests))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path,help='new session directory')
    p.add_argument('--quick',action='store_true')
    p.add_argument('--cpu-only',action='store_true')
    args = p.parse_args()
    out=args.out.resolve()
    out.mkdir()
    cmds, env, build_receipt = build(out,not args.cpu_only)
    r = dict(build=build_receipt, cpu=next(l.split(':')[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines()
            if l.startswith('model name')),platform=platform.platform(),quick=args.quick,
            unit='wall milliseconds, request write through checked decimal reply; results checked after timing',
            inputs={p.name:checked(p) for p in [*sorted(HERE.glob('*.bl')),*sorted(HERE.glob('*.scm')),
                    HERE/'kernels.bend',HERE/'Tree.lean',HERE/'run.py',ROOT/'priv/boot/compiler.bl',
                    SEED/'src/native/scheme.bl']},order=[],runs={},medians_ms={})
    for block in range(1 if args.quick else 3):
        order=list(cmds)
        if block==1:
            order.reverse()
        if block==2:
            order=order[3:]+order[:3]
        r['order'].append(order)
        trials=[workload_rows(args.quick,block,t) for t in range(1 if args.quick else 3)]
        for name in order:
            result=run_block(cmds[name],env,out,name,block,trials)
            r['runs'].setdefault(name,[]).append(result)
            print(f'block {block+1}, {name}: {result["checked"]} correct replies',flush=True)
    for name,blocks in r['runs'].items():
        r['medians_ms'][name]={key:statistics.median(t for block in blocks for t in block['samples_ms'][key])
                               for key in blocks[0]['samples_ms']}
    save(out/'receipt.json',r)
    print(out/'receipt.json',flush=True)


if __name__ == '__main__':
    main()
