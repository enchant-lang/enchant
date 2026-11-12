"""Owned SDK graph exports → exact wire checks and structural Lean instances.

This does not prove BL implementation soundness or expose a public byte parser.
Scalar external-size costs remain SDK reports; the model instance checks node
expansion and depth, and its generic scalar-cost law is not a byte-cost bridge.
"""
import hashlib,json,re
from pathlib import Path

PROFILE='bl/public-data-graph-v1'
KINDS={'nil','bool','int','float64','binary','keyword','symbol','vector','list','set','tuple','map'}
CONTAINERS={'vector','list','set','tuple','map'}
BINARY={'float64','binary','keyword','symbol'}
LIMITS={'nodes':4096,'edges':65536,'depth':192,'expanded':4000000,'wire':8388608,'scalar':65536,'integer_bits':4096}
RESERVED={b'symbol',b'meta',b'$blfn',b'$remote',b'$macro',b'$protocol',b'$transient',b'bl_deftype',b'bl_reify',b'bl_vec'}
class Refused(ValueError):pass

def require(ok,message):
    if not ok:raise Refused(message)

def integer(value):return type(value) is int

def hex_bytes(value,limit):
    require(type(value) is str and len(value)<=2*limit and len(value)%2==0 and re.fullmatch('[0-9a-f]*',value) is not None,'bounded lowercase byte encoding required')
    return bytes.fromhex(value)

def etf(value):
    """Exact uncompressed minor-version-2 subset used by graph wire tuples."""
    if value is None:return b'w\x03nil'
    if type(value) is bool:
        name=b'true' if value else b'false'
        return b'w'+bytes([len(name)])+name
    if type(value) is bytes:return b'm'+len(value).to_bytes(4,'big')+value
    if integer(value):
        if 0<=value<=255:return b'a'+bytes([value])
        if -(2**31)<=value<2**31:return b'b'+value.to_bytes(4,'big',signed=True)
        magnitude=abs(value).to_bytes(max(1,(abs(value).bit_length()+7)//8),'little')
        tag=b'n'+bytes([len(magnitude)]) if len(magnitude)<256 else b'o'+len(magnitude).to_bytes(4,'big')
        return tag+bytes([int(value<0)])+magnitude
    if type(value) is tuple:
        require(len(value)<256,'small wire tuple required')
        return b'h'+bytes([len(value)])+b''.join(etf(x) for x in value)
    if type(value) is list:
        if not value:return b'j'
        if len(value)<=65535 and all(integer(x) and 0<=x<=255 for x in value):
            return b'k'+len(value).to_bytes(2,'big')+bytes(value)
        return b'l'+len(value).to_bytes(4,'big')+b''.join(etf(x) for x in value)+b'j'
    raise Refused('unsupported owned wire value')

def encoded(value):return b'\x83'+etf(value)
def digest(data):return hashlib.sha256(data).hexdigest()
def wire_row(row):
    kind,payload=row
    return (kind.encode(),[tuple(pair) for pair in payload] if kind=='map' else payload)

def read_packet(packet):
    require(type(packet) is dict and set(packet)=={'id','root','data-profile','checking','rows','wire-hex'},'closed owned graph packet required')
    require(type(packet['id']) is str and len(packet['id'].encode())<=256,'bounded instance label required')
    require(packet['data-profile']==PROFILE,'explicit data profile required')
    raw=packet['rows'];require(type(raw) is list and 1<=len(raw)<=LIMITS['nodes'],'model table capacity')
    require(integer(packet['root']) and packet['root']==len(raw)-1,'dense original root required')
    rows=[];infos=[];seen=set();edges=0
    for index,row in enumerate(raw):
        require(type(row) is list and len(row)==2,'two-field row required')
        kind,payload=row;require(type(kind) is str and kind in KINDS,'known row kind required')
        if kind in BINARY:payload=hex_bytes(payload,LIMITS['scalar'])
        if kind=='nil':require(payload is None,'nil kind required')
        if kind=='bool':require(type(payload) is bool,'Boolean kind required')
        if kind=='int':require(integer(payload) and abs(payload).bit_length()<=LIMITS['integer_bits'],'bounded mathematical Int required')
        if kind=='float64':
            require(len(payload)==10 and payload[:2]==b'\x83F','Float64 bit payload required')
            bits=int.from_bytes(payload[2:],'big');require((bits>>52)&2047!=2047,'finite runtime Float64 required')
        if kind=='keyword':
            require(len(payload)<=1020 and payload not in [b'nil',b'true',b'false'],'keyword name capacity or reserved scalar')
            try:name=payload.decode('utf-8')
            except UnicodeError:raise Refused('valid keyword UTF-8 required')
            require(len(name)<=255,'keyword character capacity')
        children=[]
        if kind in CONTAINERS:
            require(type(payload) is list and len(payload)<=LIMITS['edges'],'bounded child list required')
            if kind=='map':
                require(all(type(pair) is list and len(pair)==2 for pair in payload),'map pairs required')
                children=[child for pair in payload for child in pair]
            else:children=payload
            require(all(integer(child) and 0<=child<index for child in children),'only earlier node references are admitted')
            if kind in {'set','map'}:
                keys=[pair[0] for pair in payload] if kind=='map' else payload
                hashes=[infos[key]['hash'] for key in keys]
                require(hashes==sorted(set(hashes)),'unique canonical key order required')
            if kind=='map':require(all(rows[key]!=['keyword',b'__struct__'] for key,_ in payload),'runtime struct key refused')
            if kind=='tuple' and payload:
                head=rows[payload[0]];require(not(head[0]=='keyword' and head[1] in RESERVED),'runtime machinery tuple refused')
        edges+=len(children);require(edges<=LIMITS['edges'],'model edge capacity')
        height=1+max(infos[c]['height'] for c in children) if children else 0
        expanded=1+sum(infos[c]['expanded'] for c in children)
        require(height<=LIMITS['depth'] and expanded<=LIMITS['expanded'],'expanded model capacity')
        if kind=='map':content=[(infos[k]['hash'].encode(),infos[v]['hash'].encode()) for k,v in payload]
        elif kind in CONTAINERS:content=[infos[c]['hash'].encode() for c in children]
        else:content=payload
        h=digest(encoded((b'bl/public-data-node-v1',kind.encode(),content)))
        require(h not in seen,'duplicate content or hash collision refused')
        require(not infos or (height,h)>(infos[-1]['height'],infos[-1]['hash']),'canonical table order required')
        rows.append([kind,payload]);infos.append({'hash':h,'height':height,'expanded':expanded,'children':children});seen.add(h)
    reached=set();pending=[packet['root']]
    while pending:
        i=pending.pop()
        if i not in reached:reached.add(i);pending.extend(infos[i]['children'])
    require(len(reached)==len(rows),'unreachable model rows refused')
    wire=encoded((PROFILE.encode(),packet['root'],[wire_row(row) for row in rows]))
    require(len(wire)<=LIMITS['wire'] and wire==hex_bytes(packet['wire-hex'],LIMITS['wire']),'exact original canonical wire required')
    checking=packet['checking'];require(type(checking) is dict,'SDK check report required')
    require(all(integer(checking.get(k)) for k in ['nodes','edges','bytes','expanded-nodes','depth']),'integer count claims required')
    require(checking['status']=='checked-data-graph' and checking['profile']==PROFILE and checking['compiler-proof-authority'] is False,'explicit SDK report scope required')
    require(checking['reference']=={'profile':PROFILE,'sha256':digest(wire)},'original reference required')
    require(checking['nodes']==len(rows) and checking['edges']==edges and checking['bytes']==len(wire),'same physical structure as SDK report')
    require(checking['expanded-nodes']==infos[-1]['expanded'] and checking['depth']==infos[-1]['height'],'same node expansion and depth as SDK report')
    return rows,infos,wire

def lean_bytes(data):return '['+', '.join(str(x) for x in data)+']'
def lean_scalar(kind,payload):
    if kind=='nil':return 'Scalar.nil'
    if kind=='bool':return 'Scalar.boolean '+str(payload).lower()
    if kind=='int':return 'Scalar.integer ('+str(payload)+')'
    if kind=='float64':return 'Scalar.float64 ⟨'+str(int.from_bytes(payload[2:],'big'))+', by decide⟩'
    return 'Scalar.'+{'binary':'bytes','keyword':'keyword','symbol':'symbol'}[kind]+' '+lean_bytes(payload)

def lean_refs(refs,bound):
    # An explicit element type avoids dependent-motive inference across a
    # nested Fin.cases chain; the same ordered finite coordinates remain.
    return '(List.get (['+', '.join('⟨'+str(ref)+', by decide⟩' for ref in refs)+'] : List (Fin '+str(bound)+')))'

def lean_instance(packet):
    rows,infos,wire=read_packet(packet)
    lines=['import GraphTable','set_option autoImplicit false','set_option maxRecDepth 100000','set_option maxHeartbeats 8000000','open FormalGraphTable','namespace GraphInstance','def table0 : Table 0 := .empty']
    for i,(kind,payload) in enumerate(rows):
        if kind not in CONTAINERS:row='Row.scalar ('+lean_scalar(kind,payload)+')'
        else:
            if kind=='map':
                children='(fun (slot : Fin '+str(len(payload))+' × Bool) => if slot.2 then '+lean_refs([v for _,v in payload],i)+' slot.1 else '+lean_refs([k for k,_ in payload],i)+' slot.1)'
            else:children=lean_refs(payload,i)
            row='Row.node (Kind.'+kind+' '+str(len(payload))+') '+children
        lines.append('def table'+str(i+1)+' : Table '+str(i+1)+' := .push table'+str(i)+' ('+row+')')
    n=len(rows);root='⟨'+str(packet['root'])+', by decide⟩'
    lines.extend([
      'theorem original_expanded_nodes : (interpret table'+str(n)+' '+root+').expandedNodes = '+str(infos[-1]['expanded'])+' := by',
      '  exact (expanded_node_count_agrees table'+str(n)+' '+root+').trans (by decide +kernel)',
      'theorem original_depth : (interpret table'+str(n)+' '+root+').height = '+str(infos[-1]['height'])+' := by',
      '  exact (height_agrees table'+str(n)+' '+root+').trans (by decide +kernel)',
      '#print axioms original_expanded_nodes','#print axioms original_depth','end GraphInstance'])
    source='\n'.join(lines)+'\n';require(len(source.encode())<=LIMITS['wire'],'generated proof source capacity')
    return source,{'id':packet['id'],'reference':packet['checking']['reference'],'wire_sha256':digest(wire),'nodes':len(rows),'edges':sum(len(x['children']) for x in infos),'expanded_nodes':infos[-1]['expanded'],'depth':infos[-1]['height'],'scalar_cost_bridge':'not-instantiated','scope':'Exact owned graph wire and structural node/depth instances; no BL implementation or compiler theorem.'}

def read_export(path):
    with Path(path).open('rb') as f:data=f.read(16*1024*1024+1)
    require(len(data)<=16*1024*1024,'owned model export byte capacity')
    value=json.loads(data)
    require(type(value) is dict and set(value)=={'schema','binary-fields','packets','managed-query-calls','compiler-proof-authority','scope'},'closed model export required')
    require(value['schema']=='enchant.formal.graph-table-instances.v1' and value['binary-fields']=='hex','explicit owned model export version')
    require(integer(value['managed-query-calls']) and value['managed-query-calls']==0 and value['compiler-proof-authority'] is False,'export scope required')
    require(type(value['packets']) is list and 1<=len(value['packets'])<=128,'packet capacity')
    return value

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('input');parser.add_argument('output');args=parser.parse_args()
    value=read_export(args.input);out=Path(args.output);out.mkdir(parents=True,exist_ok=True);summaries=[]
    for index,packet in enumerate(value['packets']):
        source,summary=lean_instance(packet);file=out/('Instance'+str(index)+'.lean');file.write_text(source)
        summary['source']=file.name;summary['source_sha256']=digest(source.encode());summaries.append(summary)
    (out/'inputs.json').write_text(json.dumps({'schema':'enchant.formal.graph-table-lean-inputs.v1','instances':summaries,'lean_status':'not-run','compiler_proof_authority':False},indent=2)+'\n')
    print(json.dumps({'instances':len(summaries),'status':'generated-not-checked'}))
