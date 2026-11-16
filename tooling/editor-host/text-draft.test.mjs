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
