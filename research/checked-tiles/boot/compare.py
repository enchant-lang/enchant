"""Compare a fresh sequential replay with the recorded native boot experiment."""
import argparse
import json
from pathlib import Path
from statistics import median
from run import HERE, sha, write


def compare(fresh, out):
    evidence = HERE.parent/'evidence'
    def pair(name):
        paths = [evidence/f'boot-{name}.json',fresh/name/f'{name}.json']
        return [json.loads(p.read_text()) for p in paths]
    def agree(name, view):
        a,b = pair(name)
        if view(a) != view(b):
            raise ValueError('Observed change in '+name)
    def reader(j):
        return [(r['source'],r['source_sha256'],r['mode'],r['beam_wire'],r['native_wire']) for r in j['rows']]
    agree('reader',reader)
    agree('coverage',lambda j:j['bindings'])
    agree('cli',lambda j:[(r['name'],r['raw_equal'],r['printer_equal']) for r in j['rows']])
    agree('extension',lambda j:[(r['name'],r['phase'],r['beam'],r['native']) for r in j['observations']])
    agree('boundary',lambda j:j['registrations'])
    agree('surface',lambda j:(j['remote_status'],[(ns,u['scheme'],u['activation']) for ns,u in j['units'].items()]))
    agree('behavior',lambda j:j['probes'])
    agree('relink',lambda j:j['control'])
    agree('regions',lambda j:(j['checks'],j['typed_witnesses'],j['token_calls'],j['skip_calls'],j['identity_skip_calls']))
    agree('pipeline',lambda j:[(r['arm'],r['emitted_sha256'],r['emitted_bytes']) for r in j['runs']])
    agree('names',lambda j:[(r['mode'],r['hash'],r['counters']) for r in j['runs']])
    agree('heldout',lambda j:{ns:[(r['mode'],r['sha256'],r['bytes']) for r in v['runs']] for ns,v in j['jobs'].items()})
    results=[]
    for i,label in enumerate(('recorded','fresh')):
        times=lambda j:{k:round(v[-1],3) for k,v in j['medians_ms'].items()}
        regions=pair('regions')[i]
        boot=[r for r in pair('reader')[i]['rows'] if r['source'].startswith('priv/boot/') and r['mode']=='read']
        result=dict(run=label, pipeline_ms=times(pair('pipeline')[i]), names_ms=times(pair('names')[i]),
                    heldout_ms={k:times(v) for k,v in pair('heldout')[i]['jobs'].items()},
                    parse_boot_ms={k:round(sum(median(r['timings_us'][k+'.parse']) for r in boot)/1000,3) for k in ('beam','native')},
                    file_plus_parse_ms={k:round(median(v),3) for k,v in pair('boundary')[i]['timings_ms']['JOB'].items()},
                    matched_io_ms={k:round(median(v),3) for k,v in pair('boundary')[i]['timings_ms']['IO'].items()},
                    reader_regions_ms={k:round(median(v),3) for k,v in regions['boot_ms'].items()},
                    reader_c_flags_ms=times(pair('relink')[i]))
        results.append(result)
    document=dict(checked=['reader','coverage','cli','extension','boundary','surface','behavior','relink','regions','pipeline','names','heldout'],
                  fresh_receipts={p.parent.name:sha(p) for p in fresh.glob('*/*.json') if p.name==p.parent.name+'.json'},
                  fresh_compiler_trials=pair('names')[1]['runs'],
                  fresh_heldout_trials={ns:v['runs'] for ns,v in pair('heldout')[1]['jobs'].items()},
                  runs=results)
    if out: write(out,document)
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('fresh',type=Path)
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    compare(args.fresh,args.out)
