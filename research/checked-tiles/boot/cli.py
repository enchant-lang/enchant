"""Compare actual successful and failing downstream CLI observations on a private fixture."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from run import HERE, IMAGE, QUAL, sha, write


def observe(argv, cwd, env, stdin=''):
    started=time.perf_counter()
    p=subprocess.run(argv,cwd=cwd,env=env,input=stdin.encode(),capture_output=True,timeout=90)
    return dict(exit=p.returncode,stdout=p.stdout.decode(errors='backslashreplace'),
                stderr=p.stderr.decode(errors='backslashreplace'),ms=(time.perf_counter()-started)*1000)


def run(out):
    out.mkdir()
    tools=json.loads((HERE.parent/'tools.json').read_text())
    sdk=Path(tools['sdk'])
    sha(sdk/'artifact.json',tools['descriptor_sha256'])
    image=IMAGE/'stage2'
    qual=json.loads(QUAL.read_text())
    sha(image,qual['images']['stage2'])
    bundle=IMAGE/'eval-prepared.scm'
    sha(bundle,qual['prepared_macro_bundle_sha256'])
    cases=[
      ('scalar','eval','(+ 40 2)',[]),
      ('stdout','run','(do (println "side effect") {:answer 42})',[]),
      ('unicode','run','(str "é😀" "x")',[]),
      ('stdin','run-stdin','(+ 5 7)',[]),
      ('path-and-args','run','(clojure.io/current-command-line-args)',['arg','two words']),
      ('malformed','run','(ok)\n[α }',[]),
      ('runtime','eval','(throw (ex-info "example failure" {:place 1}))',[]),
    ]
    rows=[]
    for name,operation,src,args in cases:
        path=out/(name+'.bl')
        path.write_text(src)
        if operation=='eval': argv=['eval',src]
        elif operation=='run-stdin': argv=['run','-']
        else: argv=['run',path.name,*( ['--',*args] if args else [])]
        env=dict(os.environ,BL_DAEMON='off',ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1',
                 BOOT_PROGRAM=str(path),BOOT_LABEL=str(path),BOOT_BUNDLE=str(bundle))
        gold=observe([sdk/'bin/bl','--cold',*argv],out,env,src if operation=='run-stdin' else '')
        raw=observe([image,'--eval',bundle,path],out,env)
        printed=observe([image,'--eval',HERE/'cli.scm',path],out,env)
        def eq(observation):
            return all(observation[key]==gold[key] for key in ('exit','stdout','stderr'))
        rows.append(dict(name=name,operation=operation,reference=gold,native_raw=raw,native_printer=printed,
                         raw_equal=eq(raw),printer_equal=eq(printed)))
    write(out/'cli.json',dict(sdk=tools['descriptor_sha256'],image=sha(image),bundle=sha(bundle),
          scope='cold pinned CLI versus native source evaluator; stdin captured to a file by harness, argv adapter absent',rows=rows))
    print([(r['name'],r['raw_equal'],r['printer_equal']) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path)
    run(p.parse_args().out.resolve())
