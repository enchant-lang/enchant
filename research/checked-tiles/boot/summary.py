"""Print the native boot comparison from a replay or from the recorded evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median


def show(folder):
    def read(name):
        archive = folder/f'boot-{name}.json'
        path = archive if archive.exists() else folder/name/(name+'.json')
        return json.loads(path.read_text())
    reader = read('reader')
    rows = reader['rows']
    print(f"Typed reader observations   {sum(r['same'] for r in rows)} / {len(rows)} identical")
    print("  Differences:", ', '.join(r['source']+' '+r['mode'] for r in rows if not r['same']))
    for tree in ('boot','host'):
        files = [r for r in rows if r['source'].startswith(f'priv/{tree}/') and r['mode']=='read']
        print(f"  {tree:5} {len(files):2} files  {sum(r['bytes'] for r in files):,} bytes")
    pipe = read('pipeline')
    print('104-definition compiler job, medians in ms (read, compile, emit, total)')
    for arm, values in pipe['medians_ms'].items():
        print(' ',arm,*[round(v,2) for v in values])
    print('  Emitted bytes equal:',pipe['same_emitted_bytes'],pipe['runs'][0]['emitted_bytes'])
    coverage = read('coverage')['bindings']
    for tree in ('boot','host'):
        print(' ',tree,'bindings:',dict(Counter(r['prepared'] for r in coverage.values() if r['path'].startswith(f'priv/{tree}/'))))
    surface=read('surface')
    print('Fresh native objects:',{ns:len(v['emitted']) for ns,v in surface['units'].items() if v.get('activation')==['success']})
    print('  Literal remotes against original image:',dict(Counter(surface['remote_status'].values())))
    print('  Executed operations:',{r['ns']:r['same'] for r in read('behavior')['probes']})
    public=read('extension')['observations']
    for phase in ('unlinked','linked'):
        probes=[r for r in public if r['phase']==phase]
        print('  Reader facade',phase,sum(r['equal'] for r in probes),'/',len(probes))
    print('  Data-reader trees:',[(r['phase'],r['tag'],r['equal']) for r in read('boundary')['registrations']])
    print('  Cold CLI:',[(r['name'],r['printer_equal']) for r in read('cli')['rows']])
    print('Same-flags file transport, ms:',{k:round(median(v),2) for k,v in read('boundary')['timings_ms']['IO'].items()})
    print('Reader C flags, whole job ms:',{k:round(v[-1],2) for k,v in read('relink')['medians_ms'].items()})
    print('Reader specialization, boot parse ms:',{k:round(median(v),2) for k,v in read('regions')['boot_ms'].items()})
    print('Compiler name reuse, whole job ms:',{k:round(v[-1],2) for k,v in read('names')['medians_ms'].items()})
    for ns,j in read('heldout')['jobs'].items():
        print(' ',ns,'whole job ms:',{k:round(v[-1],2) for k,v in j['medians_ms'].items()},'identical bytes',j['all_outputs_equal'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'evidence')
    show(p.parse_args().directory)
