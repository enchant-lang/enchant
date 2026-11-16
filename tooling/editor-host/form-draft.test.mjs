import {test} from 'node:test';
import assert from 'node:assert/strict';
import {FormDraft} from '../../priv/lib/live/edit/form-draft.mjs';
import {TextDraftStore} from '../../priv/lib/live/edit/text-draft.mjs';
const memory=()=>{const values=new Map();return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};};
const model=(basis='b1',confirmed={title:'Original',EMAIL:'old@test'})=>({basis,'confirmed-basis':basis,confirmed,values:{},fields:[{key:'title',path:['title']},{key:'EMAIL',path:['properties','EMAIL']}]});
const storage=()=>{const data=memory(),tabs=memory();tabs.setItem('enchant.edit.tab','tab');return new TextDraftStore('actor/doc/object/form',data,tabs);};
test('only attempted fields are restored; unrelated source values never become edits',()=>{
 const draft=new FormDraft(model(),storage());draft.edit('title','Mine');
 assert.deepEqual(draft.changes(),{title:'Mine'});
 draft.receive(model('b2',{title:'Original',EMAIL:'newer@test'}));
 assert.equal(draft.basis,'b1');assert.equal(draft.stale,true);assert.deepEqual(draft.changes(),{title:'Mine'});
});
test('reload and old echoes retain every newer attempted field and its original basis',()=>{
 const store=storage(),first=new FormDraft(model(),store);first.edit('title','Mine');first.edit('EMAIL','mine@test');
 const restored=new FormDraft(model('b2'),store);assert.equal(restored.restored,true);assert.equal(restored.basis,'b1');
 restored.edit('title','Newer mine');restored.receive({...model('b2'),values:{title:'Old echo'}});
 assert.deepEqual(restored.changes(),{title:'Newer mine',properties:{EMAIL:'mine@test'}});
});
test('matching source fulfills an attempt; canonical acknowledgement cannot erase newer typing',()=>{
 const draft=new FormDraft(model(),storage());draft.edit('title','005');
 draft.receive({...model('b2',{title:'5',EMAIL:'old@test'}),accepted:{basis:'old',values:{title:'005'}}});assert.equal(draft.dirty,true);
 draft.edit('title','006');draft.receive({...model('b2',{title:'5',EMAIL:'old@test'}),accepted:{basis:'b2',values:{title:'005'}}});assert.equal(draft.values.title,'006');
 draft.receive({...model('b3',{title:'6',EMAIL:'old@test'}),accepted:{basis:'b3',values:{title:'006'}}});assert.equal(draft.dirty,false);assert.equal(draft.basis,'b3');
});
test('a removed field is retained for download and cannot add an undeclared server path',()=>{
 const store=storage(),draft=new FormDraft(model(),store);draft.edit('EMAIL','mine@test');
 draft.receive({...model('b2'),fields:[{key:'title',path:['title']}]});
 assert.equal(draft.dirty,true);assert.equal(draft.orphaned,true);assert.deepEqual(draft.changes(),{});
 draft.discard();assert.equal(draft.dirty,false);assert.equal(store.read(),null);
});
test('descriptor paths reject prototype traversal; failed storage retains attempted values',()=>{
 const store=storage(),draft=new FormDraft({...model(),fields:[{key:'title',path:['__proto__','x']}]},store);
 draft.edit('title','Mine');assert.throws(()=>draft.changes(),/Invalid draft field/);
 store.storage.setItem=()=>{throw Error('quota');};draft.edit('EMAIL','important@test');
 assert.equal(draft.values.EMAIL,'important@test');assert.equal(store.warning.message,'quota');
});
