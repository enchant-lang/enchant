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

DRIVER = '''(ns tooling.staging-header-candidate)
(let [dir (Path/expand "preview")]
 (doseq [file ["namespace-stage.bl" "build.bl"]]
  (BeamLisp.AOT/compile_file (Path/join dir file) (list (tuple :output_dir dir) (tuple :mark_loaded? true)))))
(BeamLisp.Loader/with_load_path "research/native-seed/speed/front"
 (fn [] (BeamLisp.Loader/load_provider "native.observe-links")))
((BeamLisp.Env/fetch_exact! "native.observe-links" "run-observation") (BeamLisp/argv))
'''


def retarget(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one namespace reference to {old}')
    return text.replace(old, new, 1)


def run(args):
    tools = runpy.run_path(str(MATRIX))
    digest, read, save = (tools[name] for name in ('digest', 'read', 'save'))
    args.out.mkdir(mode=0o700)
    overlay = tools['new_overlay'](args.out, args.revision, 'source-')
    edited = {}
    preview = overlay / 'preview'
    preview.mkdir()
    for name in ('namespace-stage', 'build'):
        source = overlay / 'priv/lib/js' / (name + '.bl')
        text = retarget(source.read_text(), f'(ns js.{name}', f'(ns staging-preview.{name}')
        if name == 'build':
            text = retarget(text, '[js.namespace-stage :as namespace-stage]',
                            '[staging-preview.namespace-stage :as namespace-stage]')
        (preview / source.name).write_text(text)
        edited[str(source.relative_to(overlay))] = digest(source)
    for name in ('observe-links', 'checked-relink', 'stage-link-guard'):
        module = overlay / FRONT / (name + '.bl')
        edited[str(module.relative_to(overlay))] = digest(module)
        module.write_text(retarget(module.read_text(), '[js.build :as build]',
                                   '[staging-preview.build :as build]'))
    driver = overlay / 'driver.bl'
    driver.write_text(DRIVER)
    pin = read(overlay / SEED / 'sdk-pin.json')
    sdk = Path(pin['sdk'])
    descriptor = sdk / 'artifact.json'
    if digest(descriptor) != pin['descriptor_sha256'] or read(descriptor)['source'] != pin['source']:
        raise ValueError('Pinned native SDK or Source differs')
    donor = args.donor / 'partition.json'
    links = args.donor / 'link-rows.etf'
    paths = [*tools['partition_paths'](donor), links, args.samples, args.baseline]
    inputs = tools['seal'](paths)
    transformed = tools['seal']([driver, *preview.glob('*.bl'),
                                 *(overlay / FRONT / (name+'.bl') for name in
                                   ('observe-links', 'checked-relink', 'stage-link-guard'))], overlay)
    output = args.out / 'staging.json'
    env = dict(os.environ, XDG_RUNTIME_DIR=str(overlay / 'runtime'),
               ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    with (args.out / 'staging.log').open('w') as log:
        subprocess.run([sdk / 'bin/bl', '--cold', '-p', overlay / SEED / 'src', '-p',
                        Path(pin['source']) / 'priv/build', 'run', driver, '--', donor, links,
                        '--staging-effects', output, args.samples, '--all', '--repeat-pubs'],
                       cwd=overlay, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=300)
    tools['verify'](transformed, overlay)
    if tools['seal'](paths) != inputs:
        raise ValueError('Retained donor or comparison inputs changed')
    baseline, candidate = read(args.baseline), read(output)
    scopes = ('ordinary', 'interpreted')
    for data in (baseline, candidate):
        if (data['sdk-descriptor-sha256'] != pin['descriptor_sha256']
                or data['link-rows-sha256'] != digest(links)
                or data['reuse-authority']):
            raise ValueError('The trace names a different SDK, link table or reuse scope')
        if not all(row['same-prepared-inputs'] for row in data['members']):
            raise ValueError('Interpreted staging disagreed with ordinary staging')
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
    run(parser.parse_args())
