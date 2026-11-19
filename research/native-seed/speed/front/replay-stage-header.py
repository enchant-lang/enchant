#!/usr/bin/env python3
"""Compare the current literal namespace stager with a retained donor trace."""

import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess

SEED = Path('research/native-seed')
FRONT = SEED / 'speed/front/native'
MATRIX = Path(__file__).with_name('replay-relink-matrix.py')
EVAL_HEADER = '(BeamLisp.Compiler/eval_string (second (first texts)) (BeamLisp.Compiler/new_env "user") path)'
LITERAL_HEADER = '(namespace-stage/stage! (first forms) (second (first texts)) path)'

PREVIEW = '''(ns tooling.staging-header-candidate)
(let [dir (Path/expand "preview")]
 (doseq [file ["namespace-stage.bl" "build.bl"]]
  (BeamLisp.AOT/compile_file (Path/join dir file) (list (tuple :output_dir dir) (tuple :mark_loaded? true)))))
'''

DRIVER = PREVIEW + '''(BeamLisp.Loader/with_load_path "research/native-seed/speed/front"
 (fn [] (BeamLisp.Loader/load_provider "native.observe-links")))
((BeamLisp.Env/fetch_exact! "native.observe-links" "run-observation") (BeamLisp/argv))
'''


def retarget(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one namespace reference to {old}')
    return text.replace(old, new, 1)


def verify_trace(data, sdk_sha, links_sha):
    if (data['sdk-descriptor-sha256'] != sdk_sha
            or data['link-rows-sha256'] != links_sha or data['reuse-authority']):
        raise ValueError('The trace names a different SDK, link table or reuse scope')
    members = data['members']
    if not members or len({row['namespace'] for row in members}) != len(members):
        raise ValueError('The trace is empty or repeats a member')
    if len(members) != data['source-members']:
        raise ValueError('The trace does not cover the complete closure')
    for row in members:
        repeat = row.get('ordinary-repeat')
        scopes = [row['ordinary'], row['interpreted']]
        if repeat is not None:
            scopes.append(repeat)
        if (not row['same-prepared-inputs'] or (repeat is not None and not repeat['same-prepared-inputs'])
                or not all(scope['code-generation-publications']['matches-publications'] for scope in scopes)):
            raise ValueError(f"{row['namespace']}: incomplete publication trace or mismatched prepared inputs")


def write_preview(overlay, sources, literal):
    preview = overlay / 'preview'
    preview.mkdir()
    for name, source in sources.items():
        text = retarget(source, f'(ns js.{name}', f'(ns staging-preview.{name}')
        if name == 'build':
            text = retarget(text, '[js.namespace-stage :as namespace-stage]',
                            '[staging-preview.namespace-stage :as namespace-stage]')
            if not literal:
                text = retarget(text, LITERAL_HEADER, EVAL_HEADER)
        (preview / (name + '.bl')).write_text(text)
    return preview


def preview_overlay(tools, directory, revision, literal=True):
    digest = tools['digest']
    overlay = tools['new_overlay'](directory, revision, 'source-')
    paths = {name: overlay / 'priv/lib/js' / (name + '.bl') for name in ('namespace-stage', 'build')}
    preview = write_preview(overlay, {name: path.read_text() for name, path in paths.items()}, literal)
    edited = {str(path.relative_to(overlay)): digest(path) for path in paths.values()}
    for name in ('observe-links', 'checked-relink', 'stage-link-guard'):
        module = overlay / FRONT / (name + '.bl')
        edited[str(module.relative_to(overlay))] = digest(module)
        module.write_text(retarget(module.read_text(), '[js.build :as build]',
                                   '[staging-preview.build :as build]'))
    driver = overlay / 'driver.bl'
    driver.write_text(DRIVER)
    transformed = tools['seal']([driver, *preview.glob('*.bl'),
                                 *(overlay / FRONT / (name+'.bl') for name in
                                   ('observe-links', 'checked-relink', 'stage-link-guard'))], overlay)
    return overlay, driver, edited, transformed


def sdk_pin(tools, overlay):
    digest, read = tools['digest'], tools['read']
    pin = read(overlay / SEED / 'sdk-pin.json')
    sdk = Path(pin['sdk'])
    descriptor = sdk / 'artifact.json'
    if digest(descriptor) != pin['descriptor_sha256'] or read(descriptor)['source'] != pin['source']:
        raise ValueError('Pinned native SDK or Source differs')
    return pin


def run_probe(overlay, driver, pin, log_path, arguments):
    env = dict(os.environ, XDG_RUNTIME_DIR=str(overlay / 'runtime'),
               ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    with log_path.open('w') as log:
        subprocess.run([Path(pin['sdk']) / 'bin/bl', '--cold', '-p', overlay / SEED / 'src', '-p',
                        Path(pin['source']) / 'priv/build', 'run', driver, '--', *arguments],
                       cwd=overlay, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=300)


def timed_identities(report):
    return [(row['namespace'], row['prepared-identity'], row['definition-sha256']) for row in report['members']]


def run_timing(args, tools, donor, links, paths, inputs):
    digest, read, save = (tools[name] for name in ('digest', 'read', 'save'))
    baseline = read(args.baseline)
    passes = []
    for index, mode in enumerate(('eval', 'literal', 'literal', 'eval'), start=1):
        trial = args.out / f'{index}-{mode}'
        trial.mkdir(mode=0o700)
        overlay, driver, edited, transformed = preview_overlay(tools, trial, args.revision, mode == 'literal')
        pin = sdk_pin(tools, overlay)
        links_sha = inputs[str(links)]
        verify_trace(baseline, pin['descriptor_sha256'], links_sha)
        pinned_build = Path(pin['source']) / 'priv/lib/js/build.bl'
        if pinned_build.read_text().count(EVAL_HEADER) != 1:
            raise ValueError('Eval header differs from the measured baseline SDK')
        output = trial / 'timing.json'
        run_probe(overlay, driver, pin, trial / 'timing.log', [donor, links, '--staging-timing', output])
        tools['verify'](transformed, overlay)
        if tools['seal'](paths) != inputs:
            raise ValueError('Retained donor or comparison inputs changed')
        report = read(output)
        if (report['schema'] != 'bl.native.staging-timing' or report['reuse-authority']
                or report['sdk-descriptor-sha256'] != pin['descriptor_sha256']
                or report['link-rows-sha256'] != links_sha):
            raise ValueError('Unmatched timing report')
        identities = timed_identities(report)
        expected = [(row['namespace'], row['ordinary']['prepared-identity']) for row in baseline['members']]
        if ([(ns, identity) for ns, identity, _ in identities] != expected
                or report['source-members'] != len(expected)):
            raise ValueError('Timing pass did not match all retained prepared inputs')
        if passes and timed_identities(passes[0]['report']) != identities:
            raise ValueError('Definition bytes differ across timing passes')
        passes.append({'mode': mode, 'source': edited, 'overrides': transformed,
                       'raw-report-sha256': digest(output), 'report': report})
        print(f'{index}-{mode}: {len(identities)} exact member definitions', flush=True)
    save(args.out / 'comparison.json', {'revision': args.revision, 'inputs': inputs, 'passes': passes})


def run(args):
    tools = runpy.run_path(str(MATRIX))
    digest, read, save = (tools[name] for name in ('digest', 'read', 'save'))
    args.out.mkdir(mode=0o700)
    donor = args.donor / 'partition.json'
    links = args.donor / 'link-rows.etf'
    paths = [*tools['partition_paths'](donor), links, args.samples, args.baseline]
    inputs = tools['seal'](paths)
    if args.timing:
        return run_timing(args, tools, donor, links, paths, inputs)
    overlay, driver, edited, transformed = preview_overlay(tools, args.out, args.revision)
    pin = sdk_pin(tools, overlay)
    output = args.out / 'staging.json'
    run_probe(overlay, driver, pin, args.out / 'staging.log',
              [donor, links, '--staging-effects', output, args.samples, '--all', '--repeat-pubs'])
    tools['verify'](transformed, overlay)
    if tools['seal'](paths) != inputs:
        raise ValueError('Retained donor or comparison inputs changed')
    baseline, candidate = read(args.baseline), read(output)
    scopes = ('ordinary', 'interpreted')
    links_sha = inputs[str(links)]
    for data in (baseline, candidate):
        verify_trace(data, pin['descriptor_sha256'], links_sha)
    members = []
    for old, new in zip(baseline['members'], candidate['members'], strict=True):
        namespace = new['namespace']
        if old['namespace'] != namespace:
            raise ValueError('Staging member order changed')
        for mode in scopes:
            if old[mode]['prepared-identity'] != new[mode]['prepared-identity']:
                raise ValueError(f'{namespace}: different {mode} prepared input')
        members.append({'namespace': namespace,
                        'baseline': {mode: old[mode]['code-generation-publications'] for mode in scopes},
                        'candidate': {mode: new[mode]['code-generation-publications']
                                      for mode in (*scopes, 'ordinary-repeat') if mode in new}})
    save(args.out / 'comparison.json', {'revision': args.revision, 'inputs': inputs, 'source': edited,
                                        'overrides': transformed, 'sdk': pin['descriptor_sha256'],
                                        'raw-report-sha256': digest(output), 'members': members})
    print(f'{len(members)} members match the retained prepared inputs', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision')
    for key in ('donor', 'samples', 'baseline', 'out'):
        parser.add_argument(key, type=lambda text: Path(text).resolve())
    parser.add_argument('--timing', action='store_true', help='Compare untraced exact staging in four fresh processes')
    run(parser.parse_args())
