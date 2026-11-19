#!/usr/bin/env python3
"""Measure a complete linked pass with either exact namespace header implementation."""

import argparse
import hashlib
from pathlib import Path
import runpy
import shutil
import subprocess


def metadata_fields(directory, read, etf):
    partition = read(directory / 'partition.json')
    data = (directory / partition['metadata']['path']).read_bytes()
    reader = etf(data)
    if data[1] != 116:
        raise ValueError('Expected partition metadata map')
    offset, fields = 6, {}
    for _ in range(reader.integer(2, 4)):
        key = reader.text(offset, atom=True)
        start = reader.span(offset)
        offset = reader.span(start)
        fields[key] = hashlib.sha256(data[start:offset]).hexdigest()
    if offset != len(data):
        raise ValueError('Unexpected metadata payload after map')
    return fields


def verify_reference(baseline, candidate, updater, new_updater_sha, read, etf):
    old, new = (read(path / 'partition.json') for path in (baseline, candidate))
    if [(row['namespace'], row['sha256']) for row in old['units']] != [
            (row['namespace'], row['sha256']) for row in new['units']]:
        raise ValueError('Linked pass changed a retained member unit')
    old_fields, new_fields = (metadata_fields(path, read, etf) for path in (baseline, candidate))
    changed_fields = {key for key in old_fields.keys() | new_fields.keys()
                      if old_fields.get(key) != new_fields.get(key)}
    if changed_fields != {'provider-sources', 'linked-context-sha256'}:
        raise ValueError(f'Unexpected linked metadata changes: {sorted(changed_fields)}')
    old_identity, new_identity = (read(path / 'identity.json') for path in (baseline, candidate))
    if old_identity['artifact-sha256'] != old['artifact_sha256'] or new_identity['artifact-sha256'] != new['artifact_sha256']:
        raise ValueError('Provider inventory names a different artifact')
    expected = old_identity['providers']
    rewrites = [row for row in expected if row['path'] == str(updater) and row['origin'] == 'checkout']
    if len(rewrites) != 1:
        raise ValueError('Retained inventory does not bind the checkout updater')
    rewrites[0]['sha256'] = new_updater_sha
    if new_identity['providers'] != expected:
        raise ValueError('Provider inventory changed beyond the retargeted updater')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path, help='completed relink matrix directory')
    parser.add_argument('revision', help='revision supplying the literal staging Source')
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    m = runpy.run_path(str(scripts / 'replay-relink-matrix.py'))
    h = runpy.run_path(str(scripts / 'replay-stage-header.py'))
    etf = runpy.run_path(str(m['ROOT'] / m['SEED'] / 'partition-closure.py'))['ETF']
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
    baseline_identity = baseline_directory / 'identity.json'
    retained_paths = [preparation, comparison, baseline_identity]
    inputs = m['seal'](retained_paths)

    def verify_inputs():
        m['verify_prepared'](prepared, original)
        if m['seal'](retained_paths) != inputs:
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
                or row['files']['link-rows.etf'] != baseline['files']['link-rows.etf']):
            raise ValueError('Linked pass changes the original member selection or link rows')
        verify_reference(baseline_directory, result, updater, source[str(updater)], read, etf)
        if passes and row['files']['closure.etf'] != passes[0]['files']['closure.etf']:
            raise ValueError('Full linked closure bytes differ between timing runs')
        row.update({'header': mode, 'sdk': pin['descriptor_sha256'],
                    'overrides': {str(path.relative_to(overlay)): source[str(path.relative_to(overlay))]
                                  for path in (update_source, closure_source, driver, *preview.glob('*.bl'))},
                    'linked-pass-seconds': m['timings'](result / 'linked-pass.seconds'),
                    'final-partition-seconds': m['timings'](result / 'final-partition.seconds')})
        passes.append(row)
        print(f'{index}-{mode}: {len(update["changed"])} exact linked members', flush=True)
    save(out / 'comparison.json', {'revision': revision, 'inputs': inputs, 'passes': passes,
                                    'same-experimental-closure-bytes': True, 'exact-retained-member-units': True,
                                    'exact-retained-link-rows': True})


if __name__ == '__main__':
    main()
