import json,sys,hashlib
main,mine=sys.argv[1],sys.argv[2]
plan=json.load(open(main+'/chunks.json'))
for ns in sys.argv[3].split(','):
    rows=[r for r in plan['chunks'] if r['namespace']==ns]
    old=''.join(open(main+'/chunks/'+r['key']+'.functions.scm').read() for r in rows)
    oldi=''.join(open(main+'/chunks/'+r['key']+'.initializers.scm').read() for r in rows)
    new=open(mine+'/self-'+ns+'.functions.scm').read()
    newi=open(mine+'/self-'+ns+'.initializers.scm').read()
    print(ns,'round1-driver == new-self functions:',old==new,'initializers:',oldi==newi,len(old),len(new))
