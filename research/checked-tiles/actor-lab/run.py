#!/usr/bin/env python3
"""Build the mailbox experiment against the qualified native actor units and exercise it."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEED = ROOT / 'research/native-seed'
DONOR = SEED / 'out/real-actors'
sys.path.insert(0, str(SEED))
from native_elf import digest

# All substitutions are local to one checked emitted BL definition. Other
# vector consumers, including the scheduler's runnable queue, keep their ABI.
ADAPTERS = {
    'rt-spawn': {'bl-make-vec': 'lab-empty'},
    'rt-drop-mailbox-msg': {'h-vec-remove': 'lab-remove'},
    'rt-scan-from': {'h-vec-size': 'lab-size', 'h-vec-el': 'lab-ref'},
    'rt-receive-wait': {'h-vec-size': 'lab-size'},
    'rt-observation-rows': {'h-vec-size': 'lab-size'},
    'native-flush-down!': {'h-vec-size': 'lab-size', 'h-vec-el': 'lab-ref'},
    'rt-deliver': {'(lambda arguments (bl-invoke (native-global-exact "rt" "conj") arguments))': 'lab-append'},
}
FOOTER = [
    '(bl-invoke (native-global-exact "native.kernel" "bl-main") (list (native-global-exact "native.actor-posix" "main")))',
    '(if (not (null? seed-errors)) (error "native actor errors"))',
    '(native-real-finish)',
]
COLUMNS = {
    'drain': 'arm n trial enqueue_us drain_us allocated_bytes probes vector_input_slots head_advances transferred peer_turns peer_max_gap_us',
    'middle': 'arm n probes interior_visits elapsed_us',
    'revision': 'arm policy selected_revision selected next_revision residual_consumed weak_held weak_released live_held_bytes live_released_bytes',
    'timeout': 'arm original_deadline repark_deadline completed_at probes',
    'retired': 'arm terminal_replies',
    'compiler': 'policy clean_a clean_b pending_output evaluated',
    'invalidation': 'definitions re_emitted reused update_us clean_and_compare_us',
}


def checked(path, expected):
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f'Missing or changed qualified native input: {path}')
    return path


def relocate(raw):
    # The receipt records its original checkout prefix.
    return SEED / raw.split('/research/native-seed/', 1)[1] if '/research/native-seed/' in raw else Path(raw)


def replaced_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one occurrence of {old}')
    return text.replace(old, new)


def overlay(lines):
    out = []
    for name, leaves in ADAPTERS.items():
        prefix = f'(native-register! "native.kernel" "{name}" '
        matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f'Cannot locate unique native definition of {name}')
        i = matches[0]
        var = lines[i][len(prefix):-1]
        body = replaced_once(lines[i - 1], f'(define {var} ', f'(define lab-{name} ')
        for old, new in leaves.items():
            body = replaced_once(body, f'(callee {old})', f'(callee {new})')
        out.extend([body, f'(native-register! "native.kernel" "{name}" lab-{name})',
                    f'(native-intern "native.kernel" "{name}" lab-{name})'])
    return '\n'.join(out)


def command(argv, cwd, env=None, timeout=120):
    completed = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, timeout=timeout)
    if completed.returncode:
        raise RuntimeError(f'{Path(argv[0]).name} exited {completed.returncode}\n{completed.stdout[-4000:]}')
    return completed.stdout


def build_and_run(folder, quick):
    qualification = SEED / 'evidence/real-actors/qualification.json'
    refs = {relocate(k): v for k, v in json.loads(qualification.read_text())['inputs'].items()}
    receipt = DONOR / 'build.json'
    build = json.loads(checked(receipt, refs[receipt]).read_text())
    manifest_path = DONOR / 'manifest.json'
    manifest = json.loads(checked(manifest_path, refs[manifest_path]).read_text())
    checked(ROOT / manifest['runtime']['path'], manifest['runtime']['sha256'])
    sdk = manifest['link']['sdk-pin']
    checked(Path(sdk['sdk']) / 'artifact.json', sdk['descriptor_sha256'])
    original_image = checked(DONOR / 'actors-posix', refs[DONOR / 'actors-posix'])
    fixture = checked(DONOR / 'fixture.so', refs[DONOR / 'fixture.so'])
    env = dict(os.environ, NATIVE_ACTOR_BUDGET='17', BL_NATIVE_FFI_FIXTURE=str(fixture))
    control = command([original_image], folder, env)
    control_labels = [line[5:] for line in control.splitlines() if line.startswith('PASS ')]
    if len(control_labels) != 14 or 'NATIVE_ACTOR_POSIX_OK' not in control.splitlines():
        raise RuntimeError('Unmodified actor control failed')
    print('Qualified native actor control passed. Building the experiment.', file=sys.stderr, flush=True)
    tool_id = build['tool_identity']
    for raw, sha in tool_id['tools'].items():
        checked(Path(raw), sha)
    tools = {Path(k).name: k for k in tool_id['tools']}
    cfiles, objects, forms = [], [], []
    last = build['units'][-1]['ordinal']

    def compile_unit(name, content):
        scheme, c, obj = [folder / (name + suffix) for suffix in ('.scm', '.c', '.o')]
        scheme.write_text(content)
        command([tools['gsc'], '-c', *tool_id['scheme_compiler_flags'], '-o', c, scheme], folder)
        command([tools['clang'], *tool_id['flags'], '-c', c, '-o', obj], folder)
        cfiles.append(c)
        objects.append(obj)

    for unit in build['units']:
        ordinal = unit['ordinal']
        if ordinal:
            source = DONOR / 'split' / f'forms-{ordinal - 1}.scm'
            lines = checked(source, unit['source_sha256']).read_text().splitlines()
            forms.extend(lines)
        if ordinal == last:
            if lines[-3:] != FOOTER:
                raise ValueError('Unexpected actor startup boundary')
            compile_unit('actor_definitions', '\n'.join(lines[:-3]))
        else:
            cfiles.append(checked(relocate(unit['c']['path']), unit['c']['sha256']))
            objects.append(checked(relocate(unit['object']['path']), unit['object']['sha256']))
    body = (HERE / 'main.scm').read_text()
    start = body.index('(for-each')
    main = (body[:start] + '(with-exception-catcher (lambda (e) (display-exception e) (newline) (exit 1))'
            + ' (lambda ()\n' + body[start:] + '))\n')
    compile_unit('actor_lab', '\n'.join([(HERE / 'mailbox.scm').read_text(), overlay(forms),
                                        (HERE / 'exercise.scm').read_text(), (HERE / 'compiler.scm').read_text(), main]))
    link, obj, image = [folder / s for s in ('lab_.c', 'lab_.o', 'actor-lab')]
    command([tools['gsc'], '-link', '-o', link, *cfiles], folder)
    command([tools['clang'], *tool_id['flags'], '-c', link, '-o', obj], folder)
    command([tools['clang'], *objects, obj, *tool_id['link_flags'], '-o', image], folder)
    print('Exercising the native actor and compiler entries.', file=sys.stderr, flush=True)
    output = command([image], folder, dict(env, ENCHANT_LAB_QUICK=str(int(quick))), timeout=240)
    rows = {name: [] for name in COLUMNS}
    for line in output.splitlines():
        kind, *fields = line.split('\t')
        if kind in rows:
            values = [int(s) if s.isdecimal() else s for s in fields]
            rows[kind].append(dict(zip(COLUMNS[kind].split(), values, strict=True)))
    expected = dict(drain=4 if quick else 30, middle=2, revision=4, timeout=2, retired=2,
                    compiler=2, invalidation=1 if quick else 3)
    if not output.endswith('complete\n') or any(len(rows[k]) != n for k, n in expected.items()):
        raise ValueError('Incomplete native run:\n' + output[-3000:])
    return dict(mode='quick' if quick else 'full', actor_budget=17, virtual_deadlines=True,
                runtime_sha256=manifest['runtime']['sha256'], sdk=sdk, donor_build_sha256=digest(receipt),
                original_elf_sha256=digest(original_image), lab_elf_sha256=digest(image),
                fixture_sha256={p.name: digest(p) for p in sorted(HERE.glob('*.scm'))},
                driver_sha256=digest(Path(__file__)), original_control=control_labels, **rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='short smoke and counterexample run')
    parser.add_argument('--out', type=Path, help='write JSON to a new file (default stdout)')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='enchant-actor-lab-') as tmp:
        result = build_and_run(Path(tmp), args.quick)
    if args.out:
        with args.out.open('x') as stream:
            print(json.dumps(result, indent=2), file=stream)
    else:
        print(json.dumps(result, indent=2))
