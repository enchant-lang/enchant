import re,sys
text=open(sys.argv[1]).read()
def dec(s):
    try: return ''.join(chr(int(x)) for x in s.split('_') if x)
    except: return '?'+s
for block in re.split(r'\n(?=\(define v_[0-9_]+ )',text):
    m=re.match(r'\(define (v_[0-9_]+) ',block)
    if not m: continue
    name=dec(m.group(1)[2:])
    calls=sorted(set(re.findall(r'\((l?v_[0-9_]+(?:\$[0-9vg]+)?)[ )]',block)))
    out=[]
    for c in calls:
        base,_,suf=c.partition('$')
        if base.startswith('lv_'): out.append('leaf:'+dec(base[3:]))
        else:
            n=dec(base[2:])
            if n!=name: out.append(n+('$'+suf if suf else ''))
    dyn=re.findall(r'native-remote "([^"]*)"',block)+re.findall(r'\(native-global[^)]*\)',block)
    print(name,'->',', '.join(out));
    if dyn: print('   DYNAMIC',dyn)
