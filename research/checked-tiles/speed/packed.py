"""Compare the existing Enchant packed descriptor with the same resident Bend job."""
import argparse
import json
import os
from pathlib import Path
import random
import select
import statistics
import struct
import subprocess
import time

from run import ROOT, TOOLS, case, sample, checked, job, ms, save

CRATE = ROOT / 'research/j1_probe'
RUST = Path('/nix/store/yhmi70ln28n1j6wn82h61b8r8q4g562i-rustc-1.95.0')
CARGO = Path('/nix/store/85qbwr3vzfs58m7ywnjblz105p8ahbrv-cargo-1.95.0-x86_64-unknown-linux-gnu/bin/cargo')


class Replies:
    """Collect either protocol in one pipe read when the whole response is ready."""
    def __init__(self, stream):
        self.stream = stream
        self.pending = bytearray()

    def receive(self):
        if not select.select([self.stream], [], [], 30)[0]:
            raise TimeoutError('Worker did not return its reply')
        chunk = os.read(self.stream.fileno(), 64)
        if not chunk:
            raise RuntimeError('Worker closed before its reply was complete')
        self.pending.extend(chunk)

    def take(self, size):
        while len(self.pending) < size:
            self.receive()
        data = bytes(self.pending[:size])
        del self.pending[:size]
        return data

    def line(self):
        while b'\n' not in self.pending:
            if len(self.pending) > 32:
                raise ValueError('Unexpected decimal reply')
            self.receive()
        return self.take(self.pending.index(10) + 1)

    def frame(self):
        size = struct.unpack('>I', self.take(4))[0]
        if size not in (5,16):
            raise RuntimeError(f'Unexpected fold frame length {size}')
        return self.take(size)


def run_arm(command, is_port, env, requests, warm_count, log, *, init_from_seed=True, divisor=1):
    runs = {}
    inner = {}
    started = time.perf_counter_ns()
    with log.open('wb') as sink:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=sink, env=env, bufsize=0)
        replies = Replies(proc.stdout)
        try:
            if is_port:
                if replies.frame() != b'READY':
                    raise RuntimeError('Compiled fold worker did not admit the IR')
            else:
                proc.stdin.write(struct.pack('>H',len(requests)))
            for i,(k,n,seed,data,want) in enumerate(requests):
                message = ((struct.pack('>IQ',len(data)+8,seed if init_from_seed else 0) if is_port else
                            struct.pack('>BHB',k,n,seed)) + data)
                t = time.perf_counter_ns()
                proc.stdin.write(message)
                if is_port:
                    got, duration = struct.unpack('>QQ',replies.frame())
                    got //= divisor
                else:
                    got = int(replies.line())
                elapsed = ms(t)
                if got != want:
                    raise ValueError(f'n={n} seed={seed}: expected {want}, got {got}')
                if i == 0:
                    startup = ms(started)
                if i >= warm_count:
                    runs.setdefault(n,[]).append(round(elapsed,6))
                    if is_port:
                        inner.setdefault(n,[]).append(duration)
            proc.stdin.close()
            if proc.wait(timeout=20):
                raise RuntimeError('Worker exited with a failure')
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdin.close()
            proc.stdout.close()
    return dict(ms=runs,inner_ns=inner,startup_first_reply_ms=startup,checked=len(requests))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path,help='completed speed/run output')
    parser.add_argument('--out',required=True,type=Path,help='new output directory')
    args=parser.parse_args()
    session=args.session.resolve()
    out=args.out.resolve()
    out.mkdir()
    first=json.loads((session/'receipt.json').read_text())
    bend=session/'bend'
    checked(bend,first['build']['bend_elf_sha256'])
    ir=session/'pipeline.ir'
    sha=checked(ir,checked(ROOT/'research/rt-selfhost/fusion/evidence/pipeline.ir'))
    env=dict(os.environ,RUSTC=str(RUST/'bin/rustc'))
    env['PATH']=':'.join([str(RUST/'bin'),str(Path(TOOLS['cc']).parent),env['PATH']])
    env.setdefault('CARGO_TARGET_DIR',str(out/'target'))
    env['LD_LIBRARY_PATH']='/run/opengl-driver/lib:'+env.get('LD_LIBRARY_PATH','')
    started=time.perf_counter_ns()
    job([CARGO,'build','-j1','--release','--locked','--manifest-path',CRATE/'Cargo.toml'],env=env,timeout=1800)
    build_time=ms(started)
    probe=Path(env['CARGO_TARGET_DIR']).resolve()/'release/j1_probe'
    commands={'bend-cpu1':[bend,'+RTS','--threads','1','--gpu','off'],
              'packed':[probe,'--serve-fold',ir]}
    r=dict(backend_build_ms=build_time,ir_sha256=sha,elf_sha256=checked(probe),
           source={str(p.relative_to(ROOT)):checked(p) for p in
             [CRATE/'Cargo.lock',CRATE/'src/fold.rs',CRATE/'src/kernel.rs',
              ROOT/'research/rt-selfhost/fusion/pipeline.bl',Path(__file__).resolve()]},
           rustc=job([RUST/'bin/rustc','--version']).strip(),bend_elf_sha256=checked(bend),
           cpu=first['cpu'],runs={name:[] for name in commands},order=[])
    for block in range(4):
        order=list(commands) if block%2==0 else list(reversed(commands))
        r['order'].append(order)
        sizes=[0,64,4096,32768,65535]
        warm=[case(7,n,1) for n in sizes]
        warm.append(sample(7,256,0,bytes(range(256))))
        rows=[]
        for trial in range(5):
            series=[case(7,n,13+block*17+trial) for n in sizes]
            random.Random(91+trial+block*7).shuffle(series)
            rows.extend(series)
        for name in order:
            result=run_arm(commands[name],name=='packed',env,warm+rows,len(warm),out/f'{name}-{block}.log')
            r['runs'][name].append(result)
    # Mutate the generated cutoff. Preserve the JIT and transport and verify
    # that a difference in the actual compiled result reaches the oracle.
    old='imm 12 128\n'
    original=ir.read_text()
    if original.count(old)!=1:
        raise ValueError('Descriptor cutoff control changed')
    mutant=out/'wrong-cutoff.ir'
    mutant.write_text(original.replace(old,'imm 12 127\n'))
    witness=sample(7,1,0,bytes([40]))
    try:
        run_arm([probe,'--serve-fold',mutant],True,env,[witness],0,out/'mutant.log')
    except ValueError as exc:
        if 'expected 127, got 0' not in str(exc):
            raise
        r['cutoff_witness']=dict(input=40,expected=127,observed=0)
    else:
        raise RuntimeError('The deliberately wrong native result passed')
    for arm in commands:
        r.setdefault('medians_ms',{})[arm]={n:statistics.median(
            x for row in r['runs'][arm] for x in row['ms'][n]) for n in sizes}
    r['inner_medians_ns']={n:statistics.median(x for row in r['runs']['packed'] for x in row['inner_ns'][n])
                           for n in sizes}
    save(out/'receipt.json',r)
    print(json.dumps(r['medians_ms']),flush=True)


if __name__=='__main__':
    main()
