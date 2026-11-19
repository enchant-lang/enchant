#!/usr/bin/env python3
"""Measure a complete linked pass with either exact namespace header implementation."""

import argparse
from pathlib import Path
import runpy
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path, help='completed relink matrix directory')
    parser.add_argument('revision', help='revision supplying the literal staging Source')
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    m = runpy.run_path(str(scripts / 'replay-relink-matrix.py'))
    h = runpy.run_path(str(scripts / 'replay-stage-header.py'))
    read, save, digest = m['read'], m['save'], m['digest']
    matrix, out = args.matrix.resolve(strict=True), args.out.resolve()
    preparation = matrix / 'preparation.json'
    comparison = matrix / 'comparison.json'
    prepared, retained = read(preparation), read(comparison)
    if (not retained['exact-closure'] or not retained['exact-link-rows']
            or retained['preparation-sha256'] != digest(preparation)):
        raise ValueError('Matrix lacks a completed exact linked comparison')
    original = Path(prepared['overlay'])
    baseline = next(row for row in retained['passes'] if row['mode'] == 'ordinary')
    baseline_directory = Path(baseline['directory'])
    inputs = m['seal']([preparation, comparison])

    def verify_inputs():
        m['verify_prepared'](prepared, original)
        if m['seal']([preparation, comparison]) != inputs:
            raise ValueError('Retained relink receipts changed')
        m['verify'](baseline['files'], baseline_directory)

    verify_inputs()
    old_update = read(baseline_directory / 'update.json')
    if not old_update['changed'] or old_update['linked-context-reused']:
        raise ValueError('Matrix ordinary arm did not run the changed linked pass')
    revision = subprocess.check_output(['git', 'rev-parse', args.revision], cwd=m['ROOT'], text=True).strip()
    sources = {name: subprocess.check_output(['git', 'show', f'{revision}:priv/lib/js/{name}.bl'],
                                             cwd=m['ROOT'], text=True)
               for name in ('namespace-stage', 'build')}
    seed = m['SEED']
    updater = seed / 'src/native/update-closure.bl'
    closure = seed / 'speed/final/closure-r3.sh'
    out.mkdir(mode=0o700)
    passes = []
    for index, mode in enumerate(('eval', 'literal', 'literal', 'eval'), start=1):
        trial = out / f'{index}-{mode}'
        trial.mkdir(mode=0o700)
        overlay = trial / 'source'
        for path in m['source_paths'](original):
            destination = overlay / path.relative_to(original)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        m['verify_source'](prepared['source'], overlay)
        (overlay / 'runtime').mkdir(mode=0o700)
        pin = h['sdk_pin'](m, overlay)
        pinned_build = Path(pin['source']) / 'priv/lib/js/build.bl'
        if pinned_build.read_text().count(h['EVAL_HEADER']) != 1:
            raise ValueError('Eval header differs from the retained SDK header')
        preview = h['write_preview'](overlay, sources, mode == 'literal')
        driver = overlay / 'linked-header.bl'
        driver.write_text(h['PREVIEW'] + f'(BeamLisp/run_file "{updater}")\n')
        update_source, closure_source = overlay / updater, overlay / closure
        update_source.write_text(h['retarget'](update_source.read_text(), '[js.build :as build]',
                                               '[staging-preview.build :as build]'))
        closure_source.write_text(h['retarget'](closure_source.read_text(),
                                               f'phase linked-pass bl run {updater} --',
                                               f'phase linked-pass bl run {driver.name} --'))
        source = m['seal']([*m['source_paths'](overlay), driver, *preview.glob('*.bl')], overlay)
        row = m['run_link'](overlay, trial, 'ordinary', True, original / 'prepared')
        m['verify'](source, overlay)
        verify_inputs()
        result = Path(row['directory'])
        update = read(result / 'update.json')
        if (update['changed'] != old_update['changed'] or update['linked-context-reused']
                or any(row['files'][name] != baseline['files'][name] for name in ('closure.etf', 'link-rows.etf'))):
            raise ValueError('Linked pass differs from the retained exact ordinary output')
        row.update({'header': mode, 'sdk': pin['descriptor_sha256'],
                    'overrides': {str(path.relative_to(overlay)): source[str(path.relative_to(overlay))]
                                  for path in (update_source, closure_source, driver, *preview.glob('*.bl'))},
                    'linked-pass-seconds': m['timings'](result / 'linked-pass.seconds'),
                    'final-partition-seconds': m['timings'](result / 'final-partition.seconds')})
        passes.append(row)
        print(f'{index}-{mode}: {len(update["changed"])} exact linked members', flush=True)
    save(out / 'comparison.json', {'revision': revision, 'inputs': inputs, 'passes': passes,
                                    'exact-closure': True, 'exact-link-rows': True})


if __name__ == '__main__':
    main()
