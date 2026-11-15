#!/usr/bin/env python3
"""Snapshot byte-qualified research Sources and write capped argv; launch no BL."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

STAGE = Path(__file__).resolve().parent
ROOT = next((parent for parent in STAGE.parents
             if (parent / 'research/native-seed/sdk-pin.json').is_file()
             and (parent / 'research/formal-logic/sdk-pin.json').is_file()), None)
if ROOT is None:
    raise RuntimeError('cannot locate repository SDK-pin markers above this stage')


def read(path):
    return json.loads(path.read_text())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def snapshot_qualified_sources(destination):
    """Use complete recorded Source bytes; do not infer a dependency graph."""
    project = ROOT / 'research/formal-logic'
    qualification_path = project / 'evidence/obligation-integration/qualification.json'
    qualification = read(qualification_path)
    pin = read(project / 'sdk-pin.json')
    if qualification['status'] != 'passed' or qualification['sdk_pin'] != pin:
        raise RuntimeError('formal selection is not the qualified narrow artifact')
    prior_path = project / 'evidence/obligation-integration/regression-source-pin.json'
    prior = read(prior_path)
    if prior['sdk_pin'] != pin:
        raise RuntimeError('research Source qualification belongs to another SDK')
    prefix = 'research/formal-logic/src/'
    expected = {name: value for name, value in prior['source_sha256'].items()
                if name.startswith(prefix) and name.endswith('.bl')}
    if not expected:
        raise RuntimeError('qualified research Source inventory is empty')
    commit = prior.get('code_commit', '')
    historical_allowed = bool(re.fullmatch(r'[0-9a-f]{40}', commit))
    rows, excluded_current = [], []
    destination.mkdir()
    for name, wanted in sorted(expected.items()):
        relative = Path(name.removeprefix(prefix))
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('invalid qualified Source path')
        current = ROOT / name
        data = current.read_bytes() if current.is_file() else None
        origin = 'current-byte-match'
        if data is None or digest(data) != wanted:
            exclusion = {'path': str(current), 'expected_sha256': wanted,
                         'current_sha256': digest(data) if data is not None else None,
                         'reason': 'missing-or-different-from-qualified-bytes'}
            excluded_current.append(exclusion)
            data = None
            # A commit label is only a lookup hint. Admit its blob only when
            # its actual bytes match the independently saved qualification.
            if historical_allowed:
                saved = subprocess.run(['git', 'show', commit + ':' + name], cwd=ROOT,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                if saved.returncode == 0 and digest(saved.stdout) == wanted:
                    data, origin = saved.stdout, 'qualified-historical-blob'
                    exclusion['snapshot_recovery'] = {'commit': commit, 'sha256': wanted}
            if data is None:
                exclusion['snapshot_recovery'] = 'unavailable; namespace omitted and fails closed if required'
                continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o444)
        rows.append({'path': str(target), 'sha256': wanted, 'qualified_source': name,
                     'qualified_source_pin': str(prior_path), 'origin': origin})
    for current in sorted((project / 'src').rglob('*.bl')):
        name = str(current.relative_to(ROOT))
        if name not in expected:
            excluded_current.append({'path': str(current), 'current_sha256': sha(current),
                                     'reason': 'absent-from-qualified-source-inventory'})
    return pin, qualification_path, prior_path, rows, excluded_current


def capped(argv, runtime, unit, cwd, memory):
    return ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
            '--expand-environment=no', '--unit=' + unit, '--working-directory=' + str(cwd),
            '--property=MemoryMax=' + memory, '--property=MemorySwapMax=0',
            '--property=RuntimeMaxSec=240', '--property=KillMode=control-group',
            '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH', *argv]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='vertical1')
    parser.add_argument('--reuse-scalar-dir', type=Path,
                        help='reuse an already checked scalar artifact; fresh rechecks perform zero scalar proof search')
    parser.add_argument('--prior-history-dir', type=Path,
                        help='retain actual prior unsupported depth4 answers without rerunning that search')
    parser.add_argument('--runs-root', type=Path,
                        default=ROOT / '.local/native-devtool/vertical-formal-runs')
    parser.add_argument('--native-manifest', type=Path,
                        default=ROOT / 'research/native-seed/out/compiler-native-owner/partition.json')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', args.run_id):
        raise RuntimeError('run-id must be a short lowercase identifier')
    native = read(ROOT / 'research/native-seed/sdk-pin.json')
    formal = read(ROOT / 'research/formal-logic/sdk-pin.json')
    for pin in [native, formal]:
        if sha(Path(pin['sdk']) / 'artifact.json') != pin['descriptor_sha256']:
            raise RuntimeError('immutable SDK descriptor differs from pin')
    native_manifest = args.native_manifest.resolve()
    manifest = read(native_manifest)
    if manifest['schema'] != 'bl.native.partitioned-closure' or manifest['version'] != 1:
        raise RuntimeError('not the retained native closure')
    run = args.runs_root.resolve() / args.run_id
    if run.exists():
        raise RuntimeError('run directory must be new: ' + str(run))
    run.mkdir(parents=True)
    private = run / 'runtime'
    private.mkdir(mode=0o700)
    consumer = run / 'consumer-cwd'
    consumer.mkdir()
    snapshot = run / 'qualified-formal-src'
    qualified_pin, qualification, prior, sources, excluded = snapshot_qualified_sources(snapshot)
    if formal != qualified_pin:
        raise RuntimeError('formal pin changed during snapshot')
    staged = [*sorted(STAGE.rglob('*.bl')), STAGE / 'candidate.source', Path(__file__).resolve()]
    staged = [path for path in staged if 'runs' not in path.relative_to(STAGE).parts]
    stage_rows = [{'path': str(path), 'sha256': sha(path)} for path in staged]
    lock = {'schema': 'bl.native.vertical-formal-inputs', 'version': 1,
            'native_sdk_pin': native, 'formal_sdk_pin': formal,
            'native_manifest': str(native_manifest), 'native_manifest_sha256': sha(native_manifest),
            'formal_qualification': {'path': str(qualification), 'sha256': sha(qualification),
                                     'status': 'passed', 'source_pin': str(prior), 'source_pin_sha256': sha(prior)},
            'qualified_research_sources': sources, 'excluded_current_research_sources': excluded,
            'formal_source_snapshot': str(snapshot), 'current_research_prefix_used': False,
            'staged_sources': stage_rows,
            'native_artifact_owner_sources': [{'path': str(ROOT / 'research/native-seed/src/native/artifact.bl'),
                                                'sha256': sha(ROOT / 'research/native-seed/src/native/artifact.bl')}],
            'candidate_source': str(STAGE / 'candidate.source'),
            'candidate_source_sha256': sha(STAGE / 'candidate.source'),
            'scope': 'Source-linked integer Core comparison and separate Source model histories',
            'native_builds_or_runs': 0, 'compiler_proof_authority': False}
    lock_path = run / 'inputs.json'
    lock_path.write_text(json.dumps(lock, indent=2) + '\n')
    input_dir, proofs, recheck = run / 'input', run / 'proofs', run / 'recheck'
    old_scalar = args.reuse_scalar_dir.resolve() if args.reuse_scalar_dir else None
    if old_scalar:
        for suffix in ['scalar.etf', 'scalar.etf.json', 'scalar-receipt.json']:
            if not (old_scalar / suffix).is_file():
                raise RuntimeError('missing retained scalar artifact: ' + suffix)
        if read(old_scalar / 'scalar.etf.json')['sha256'] != sha(old_scalar / 'scalar.etf'):
            raise RuntimeError('retained scalar bytes differ from their recorded digest')
    scalar_dir = old_scalar or run / 'scalar'
    prior_dir = args.prior_history_dir.resolve() if args.prior_history_dir else old_scalar
    if prior_dir and not (prior_dir / 'history.etf').is_file():
        prior_dir = None
    original = [native['sdk'] + '/bin/bl', '--cold', '-p', str(ROOT / 'research/native-seed/src'),
                'run', str(STAGE / 'extract-helper.bl'), '--', str(lock_path), str(input_dir)]
    formal_prefix = [formal['sdk'] + '/bin/bl', '--cold', '-p', str(snapshot), '-p', str(STAGE)]
    scalar_command = [*formal_prefix, 'run', str(STAGE / 'check-formal.bl'), '--',
                      str(lock_path), str(input_dir), str(scalar_dir)]
    produce = [*formal_prefix, 'run', str(STAGE / 'qualify-history.bl'), '--',
               str(lock_path), str(scalar_dir), str(proofs)]
    if prior_dir:
        produce.append(str(prior_dir))
    check = [*formal_prefix, 'run', str(STAGE / 'recheck-and-replay.bl'), '--',
             str(lock_path), str(scalar_dir), str(proofs), str(recheck)]
    commands = {'schema': 'bl.native.vertical-formal-commands', 'version': 2,
                'native_cwd': str(ROOT), 'formal_cwd': str(consumer), 'serial_only': True,
                'serial_order': ['extract', 'scalar', 'prove', 'recheck'],
                'extract': None if old_scalar else capped(original, private, 'bl-vertical-extract-' + args.run_id, ROOT, '3G'),
                'scalar': None if old_scalar else capped(scalar_command, private, 'bl-vertical-scalar-' + args.run_id, consumer, '4G'),
                'prove': capped(produce, private, 'bl-vertical-prove-' + args.run_id, consumer, '4G'),
                'recheck': capped(check, private, 'bl-vertical-recheck-' + args.run_id, consumer, '4G'),
                'reused_scalar_directory': str(old_scalar) if old_scalar else None,
                'scalar_proof_directory': str(scalar_dir), 'history_proof_directory': str(proofs),
                'prior_unsupported_history_directory': str(prior_dir) if prior_dir else None,
                'native_replay_template': {'prefix': formal_prefix, 'script': str(STAGE / 'recheck-and-replay.bl'),
                    'cwd': str(consumer), 'argv': [str(lock_path), str(scalar_dir), str(proofs), '<NEW_OUTPUT_DIRECTORY>', '<OBSERVATIONS_JSON>']},
                'runtime_directory': str(private), 'processes_launched_by_preparer': 0,
                'historical_git_blob_reads': 'read-only and accepted only by exact qualified SHA'}
    (run / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(json.dumps({'inputs': str(lock_path), 'commands': str(run / 'commands.json'),
                      'qualified_project_sources': len(sources), 'excluded_current_sources': excluded,
                      'bl_or_solver_or_build_processes_launched': 0}))


if __name__ == '__main__':
    main()
