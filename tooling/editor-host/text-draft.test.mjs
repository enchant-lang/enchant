import {test} from 'node:test';
import assert from 'node:assert/strict';
import {TextDraft,TextDraftStore} from '../../priv/lib/live/edit/text-draft.mjs';
const memory=()=>{const values=new Map();return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};};
const model=(confirmed='one',basis='b1')=>({confirmed,'confirmed-basis':basis,value:confirmed,basis});
test('a recovered draft keeps its admission basis across remote writes and late echoes',()=>{
 const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');
 const store=new TextDraftStore('alice/doc',storage,tabs),first=new TextDraft(model(),store);
 first.edit('mine 😀\r\n');
 const second=new TextDraft(model('remote','b2'),new TextDraftStore('alice/doc',storage,tabs));
 assert.equal(second.value,'mine 😀\r\n');assert.equal(second.basis,'b1');assert.equal(second.stale,true);
 second.edit('newer mine');second.receive({...model('remote','b2'),value:'old echo'});
 assert.equal(second.value,'newer mine');assert.equal(second.basis,'b1');
 assert.equal(new TextDraft(model(),new TextDraftStore('bob/doc',storage,tabs)).value,'one');
 second.receive(model('newer mine','b3'));
 assert.equal(second.dirty,false);assert.equal(second.basis,'b3');assert.equal(store.read(),null);
 second.receive(model('another writer','b4'));assert.equal(second.value,'another writer');
});
test('explicit discard adopts current source; failed storage never discards in-memory words',()=>{
 const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');
 const store=new TextDraftStore('alice/doc',storage,tabs),draft=new TextDraft(model(),store);
 draft.edit('mine');draft.receive(model('remote','b2'));draft.discard();
 assert.equal(draft.value,'remote');assert.equal(draft.basis,'b2');assert.equal(store.read(),null);
 storage.setItem=()=>{throw Error('quota');};draft.edit('important');
 assert.equal(draft.value,'important');assert.equal(store.warning.message,'quota');
});
test('corrupt recovery is retained and surfaced, without changing authoritative source',()=>{
 const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');
 const store=new TextDraftStore('alice/doc',storage,tabs);storage.setItem(store.key,'{broken');
 const draft=new TextDraft(model(),store);assert.equal(draft.value,'one');assert.ok(store.warning);
 draft.persist();assert.equal(storage.getItem(store.key),'{broken');
 draft.edit('new words');assert.equal(storage.getItem(store.key),'{broken');
 draft.discard();assert.equal(store.read(),null);assert.equal(store.warning,null);
});

test('canonical normalization is adopted only for an exact acknowledged draft and current basis',()=>{
 const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');
 const draft=new TextDraft(model(),new TextDraftStore('alice/doc',storage,tabs));
 draft.edit('* New task');
 draft.receive({...model('* New task\n:ID: assigned','b2'),accepted:{value:'* New task',basis:'old'}});
 assert.equal(draft.value,'* New task');assert.equal(draft.dirty,true);
 draft.edit('* Newer typing');
 draft.receive({...model('* New task\n:ID: assigned','b2'),accepted:{value:'* New task',basis:'b2'}});
 assert.equal(draft.value,'* Newer typing');
 draft.receive({...model('* Newer typing\n:ID: assigned','b3'),accepted:{value:'* Newer typing',basis:'b3'}});
 assert.equal(draft.value,'* Newer typing\n:ID: assigned');assert.equal(draft.dirty,false);
});
test('unreadable exact text remains exportable without touching another resource',()=>{
 const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');
 const store=new TextDraftStore('alice/doc',storage,tabs),other=new TextDraftStore('bob/doc',storage,tabs);
 const raw='{unreadable 🌿\r\n';storage.setItem(store.key,raw);other.write('Private other draft','other-basis');
 const draft=new TextDraft(model(),store);assert.equal(store.corrupt.raw,raw);assert.equal(store.unreadable,true);
 draft.edit('New local words');assert.equal(storage.getItem(store.key),raw);assert.equal(other.read().value,'Private other draft');
 assert.equal(draft.discard(),true);assert.equal(store.corrupt,null);assert.equal(storage.getItem(store.key),null);
 assert.equal(other.read().value,'Private other draft');
});
test('failed deletion keeps the current exact draft and recovery until an explicit retry succeeds',()=>{
 const storage=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');const store=new TextDraftStore('actor/doc',storage,tabs),draft=new TextDraft(model(),store);
 draft.edit('Do not lose this');const raw=storage.getItem(store.key),remove=storage.removeItem;
 storage.removeItem=()=>{throw Error('remove denied');};assert.equal(draft.discard(),false);
 assert.equal(draft.value,'Do not lose this');assert.equal(storage.getItem(store.key),raw);
 storage.removeItem=remove;assert.equal(draft.discard(),true);assert.equal(draft.value,'one');assert.equal(storage.getItem(store.key),null);
});
