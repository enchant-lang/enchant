"""Shorten the measured overflowing caption, preserving every executable span."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-presentation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((E/'graph-geometry-before/geometry.json').read_text())
assert len(g['views'])==2
for v in g['views']:
 bad=[t['text'] for n in v['nodes'] for t in n['texts'] if not t['inside']]
 assert bad==['Scope and assumptions stay visible'] and not [x for x in v['edges'] if x['overlaps']]
doc=P/'ATLAS.bl.org';before=doc.read_text();old=sha(doc)
assert old==json.loads((E/'dossier-check-exit.json').read_text())['document_sha256']
a='node answer | Explicit conclusion | Scope and assumptions stay visible | 2,1 | door'
b='node answer | Explicit conclusion | Scope stays visible | 2,1 | door'
assert before.count(a)==1;after=before.replace(a,b)
for pattern in [r'^#\+begin_src beam-lisp\b[^\n]*\n.*?^#\+end_src[^\n]*',r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*',r'^#\+name:[^\n]*\n(?:\|[^\n]*(?:\n|$))*']:
 assert re.findall(pattern,before,re.M|re.S)==re.findall(pattern,after,re.M|re.S)
proposal=P/'proposals/scalar-dossier-section.org';body=proposal.read_text();assert body.count(a)==1
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();name=str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==Path(__file__).read_bytes()
doc.write_text(after);proposal.write_text(body.replace(a,b))
report={'schema':'bl.scalar-graph-caption-source-change.v1','status':'caption-shortened-awaiting-unchanged-check-and-browser',
 'recorded_utc':datetime.now(timezone.utc).isoformat(),'document_before_sha256':old,'document_sha256':sha(doc),
 'caption_before':'Scope and assumptions stay visible','caption_after':'Scope stays visible',
 'actual_geometry_sha256':sha(E/'graph-geometry-before/geometry.json'),'all_cell_sources_results_and_named_tables_preserved':True,
 'results_authored':False,'recipe':{'code_commit':commit,'path':name,'sha256':sha(Path(__file__))}}
(E/'graph-caption-source-change.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cell_source_and_results_preserved':True}))
