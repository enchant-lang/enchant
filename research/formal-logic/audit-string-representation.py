"""Inspect the exact worker and crate sources; do not infer solver domain behavior."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess,tomllib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/string-representation-review';E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pin=read(P/'evidence/scalar-integration/sdk-candidate.json');sdk=read(Path(pin['sdk'])/'artifact.json')
worker=Path(sdk['formalWorker']);meta=read(worker/'artifact.json');source=Path(meta['source'])
assert sha(worker/meta['worker']['path'])==meta['worker']['sha256']
assert sha(worker/'Cargo.lock')==sha(source/'Cargo.lock')==meta['cargo_lock_sha256']
drv=subprocess.check_output(['nix-store','--query','--deriver',str(worker)],text=True).strip()
drv_json=json.loads(subprocess.check_output(['nix','derivation','show',drv],text=True));spec=next(iter(drv_json['derivations'].values()))
assert spec['structuredAttrs']['src']==str(source)
vendor=Path(spec['structuredAttrs']['cargoDeps']);crate=vendor/'oxiz-core-0.3.4'
lock=tomllib.loads((source/'Cargo.lock').read_text());package=next(x for x in lock['package'] if x['name']=='oxiz-core')
assert package['version']==meta['oxiz_version']=='0.3.4'
assert read(crate/'.cargo-checksum.json')['package']==package['checksum']
names=['z3.rs','oxiz.rs','wire.rs'];files={}
for n in names:
 a=source/'src/formal'/n;b=R/'native/ports/formal_worker/src/formal'/n
 assert a.read_bytes()==b.read_bytes()
 files[str(a)]=sha(a)
files[str(crate/'src/ast/term.rs')]=sha(crate/'src/ast/term.rs')
z3=(source/'src/formal/z3.rs').read_text();oxiz=(source/'src/formal/oxiz.rs').read_text();wire=(source/'src/formal/wire.rs').read_text();term=(crate/'src/ast/term.rs').read_text()
assert 'StringLit(String)' in term and 'mk_string_lit(wire::binary_text(&node.data)?)' in oxiz
assert 'wire::binary_text(&node.data)?.chars().map(u32::from)' in z3 and 'Z3_mk_u32string' in z3
assert 'codepoints.into_iter().map(char::from_u32).collect::<Option<String>>()' in z3
assert 'model string contains a non-Unicode scalar' in z3 and 'from_utf8' in wire
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();recipe=str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+recipe],cwd=R)==Path(__file__).read_bytes()
report={'schema':'bl.string-representation-source-review.v1','status':'source-inspected','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'candidate_sdk_pin':pin,'worker':str(worker),'worker_descriptor_sha256':sha(worker/'artifact.json'),'worker_sha256':meta['worker']['sha256'],
 'derivation':drv,'derivation_json_sha256':hashlib.sha256(json.dumps(drv_json,sort_keys=True).encode()).hexdigest(),
 'immutable_worker_source':str(source),'cargo_vendor':str(vendor),'oxiz_core_source':str(crate.resolve()),'crate_version':package['version'],
 'crate_checksum':package['checksum'],'files_sha256':files,
 'observations':{'both_current_literal_inputs':'UTF-8 binaries decoded through Rust str',
 'z3_literal_construction':'u32 codepoint vector passed to Z3_mk_u32string',
 'z3_model_projection':'non-Unicode-scalar codepoints become opaque; no replacement text invented',
 'oxiz_literal_carrier':'TermKind::StringLit(String)',
 'full_smt_codepoint_carrier_in_bl':False},
 'native_domain_behavior_tested':False,'compiler_proof_authority':False,
 'scope':'Exact source representation only. Does not prove either engine implements the full SMT alphabet, characterize quantified String domains, or qualify a new literal/model carrier.',
 'recipe':{'code_commit':commit,'path':recipe,'sha256':sha(Path(__file__))}}
(E/'source-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'crate_version':package['version'],'native_domain_behavior_tested':False}))
