import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DraftStore} from '../../priv/lib/live/edit/drafts.mjs';
function memory(){const values=new Map();return {values,failWrite:null,failRemove:false,getItem:k=>values.get(k)??null,setItem(k,v){if(this.failWrite===k)throw Error('quota');values.set(k,v);},removeItem(k){if(this.failRemove)throw Error('storage denied');values.delete(k);}};}
function fixture(run){const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');const oldStorage=Object.getOwnPropertyDescriptor(globalThis,'localStorage'),oldTabs=Object.getOwnPropertyDescriptor(globalThis,'sessionStorage');Object.defineProperty(globalThis,'localStorage',{configurable:true,value:storage});Object.defineProperty(globalThis,'sessionStorage',{configurable:true,value:tabs});try{return run(storage,tabs);}finally{if(oldStorage)Object.defineProperty(globalThis,'localStorage',oldStorage);else delete globalThis.localStorage;if(oldTabs)Object.defineProperty(globalThis,'sessionStorage',oldTabs);else delete globalThis.sessionStorage;}}
const checkpoint=text=>({revision:0,digest:'fixture-digest',document:{schema:2,id:'document',meta:{title:'Fixture'},blocks:[{id:'p',type:'paragraph',text,attrs:{},marks:[],wraps:[],parent:null,slot:'body'}]}});
const recovery=text=>({schema:1,pending:[{id:'typing',op:{op:'text/replace',block:'p',from:0,to:0,text}}]});
test('explicit retirement prevents disposal and late updates from resurrecting a discarded draft',()=>fixture(storage=>{
 const old=new DraftStore('actor/doc');old.write(checkpoint('base'),recovery('mine'));assert.equal(old.discard(),true);
 assert.equal(old.write(checkpoint('old echo'),recovery('mine')),true);assert.equal(storage.getItem(old.key),null);
 const next=new DraftStore('actor/doc');next.write(checkpoint('current'),recovery('new writing'));
 old.write(checkpoint('late disposal'),recovery('mine'));assert.equal(next.read().recovery.pending[0].op.text,'new writing');
}));
test('ordinary clear leaves the active editor able to recover subsequent writing',()=>fixture(()=>{
 const store=new DraftStore('actor/doc');store.write(checkpoint('base'),recovery('mine'));assert.equal(store.remove(),true);
 store.write(checkpoint('current'),recovery('next'));assert.equal(store.read().recovery.pending[0].op.text,'next');
}));
test('a failed pointer update preserves the previous checkpoint and removes only its uncommitted replacement',()=>fixture(storage=>{
 const store=new DraftStore('actor/doc'),before=checkpoint('base');store.write(before,recovery('first'));const pointer=storage.getItem(store.key),keys=[...storage.values.keys()];
 storage.failWrite=store.key;assert.equal(store.write(checkpoint('next'),recovery('second')),false);
 assert.equal(storage.getItem(store.key),pointer);assert.deepEqual([...storage.values.keys()],keys);assert.equal(store.read().checkpoint.document.blocks[0].text,'base');
 storage.failWrite=null;assert.equal(store.write(checkpoint('next'),recovery('second')),true);assert.equal(storage.values.size,2);
}));
test('corrupt pointers and missing or malformed checkpoints remain exportable until explicit discard',()=>fixture(storage=>{
 for(const variant of ['pointer','missing','checkpoint']){
  const store=new DraftStore('actor/'+variant);store.write(checkpoint('base'),recovery('mine'));
  const pointer=JSON.parse(storage.getItem(store.key));if(variant==='pointer')storage.setItem(store.key,'{broken');else if(variant==='missing')storage.removeItem(pointer.checkpointKey);else storage.setItem(pointer.checkpointKey,'{"invalid":"retain this"}');
  const raw=storage.getItem(store.key),broken=variant==='checkpoint'?storage.getItem(pointer.checkpointKey):null;
  assert.equal(store.read(),null);assert.equal(store.corrupt.raw,raw);if(broken)assert.equal(store.corrupt.checkpointRaw,broken);
  if(variant==='pointer')assert.equal(JSON.parse(store.corrupt.checkpointRaw).document.blocks[0].text,'base');
  assert.equal(store.write(checkpoint('current'),recovery('new')),false);assert.equal(storage.getItem(store.key),raw);
  assert.equal(store.discard(),true);assert.equal(storage.getItem(store.key),null);
 }
}));
test('a foreign checkpoint pointer cannot read or remove another scope',()=>fixture(storage=>{
 const mine=new DraftStore('alice/doc'),other=new DraftStore('bob/doc');other.write(checkpoint('private'),recovery('private'));
 const pointer=JSON.parse(storage.getItem(other.key));storage.setItem(mine.key,JSON.stringify({...pointer}));
 assert.equal(mine.read(),null);assert.equal(mine.corrupt.checkpointRaw,null);assert.equal(mine.discard(),true);
 assert.equal(other.read().checkpoint.document.blocks[0].text,'private');
}));
test('failed explicit deletion reports failure and can be retried without overwriting retained data',()=>fixture(storage=>{
 const store=new DraftStore('actor/doc');store.write(checkpoint('base'),recovery('mine'));const raw=storage.getItem(store.key);
 storage.failRemove=true;assert.equal(store.discard(),false);store.write(checkpoint('echo'),recovery('old'));assert.equal(storage.getItem(store.key),raw);
 storage.failRemove=false;assert.equal(store.discard(),true);assert.equal(storage.getItem(store.key),null);
}));
test('valid legacy embedded checkpoints remain readable',()=>fixture(storage=>{
 const store=new DraftStore('actor/doc'),saved={schema:2,checkpoint:checkpoint('legacy'),recovery:recovery('mine')};
 storage.setItem(store.key,JSON.stringify(saved));assert.deepEqual(store.read(),saved);assert.equal(store.corrupt,null);
}));
