import test from 'node:test';
import assert from 'node:assert/strict';
import {waitForSettlement,recoveryMessage} from '../../priv/lib/live/edit/settlement.mjs';
function fixture(initial={pending:1}){
 let state=initial;const listeners=new Set();
 return {read:()=>state,subscribe:fn=>{listeners.add(fn);return ()=>listeners.delete(fn);},
  change:patch=>{state={...state,...patch};for(const fn of [...listeners])fn();},listeners};
}
test('publication includes the whole authoring queue, including writing added while waiting',async()=>{
 const f=fixture({pending:3});let complete=false;
 const ready=waitForSettlement(f.read,f.subscribe).then(()=>{complete=true;});
 f.change({pending:1});await Promise.resolve();assert.equal(complete,false);
 f.change({pending:2});await Promise.resolve();assert.equal(complete,false);
 f.change({pending:0});await ready;assert.equal(complete,true);assert.equal(f.listeners.size,0);
});
test('loss of each publication precondition rejects without waiting for confirmation',async()=>{
 for(const flag of ['readonly','offline','conflict','composing','preview','disposed']){
  const f=fixture(),ready=waitForSettlement(f.read,f.subscribe);
  f.change({[flag]:true});await assert.rejects(ready);assert.equal(f.listeners.size,0);
 }
});
test('unavailable editors never publish even with an empty queue',async()=>{
 for(const flag of ['readonly','offline','conflict','composing','preview','disposed']){
  const f=fixture({pending:0,[flag]:true});await assert.rejects(waitForSettlement(f.read,f.subscribe));assert.equal(f.listeners.size,0);
 }
 const f=fixture({pending:0});await waitForSettlement(f.read,f.subscribe);assert.equal(f.listeners.size,0);
});
test('disposal, an already aborted lifetime and timeout release all observers',async()=>{
 const f=fixture(),controller=new AbortController(),ready=waitForSettlement(f.read,f.subscribe,{signal:controller.signal});
 controller.abort();await assert.rejects(ready,/editor closed/);assert.equal(f.listeners.size,0);
 await assert.rejects(waitForSettlement(f.read,f.subscribe,{signal:controller.signal}),/editor closed/);
 await assert.rejects(waitForSettlement(f.read,f.subscribe,{timeout:5}),/still saving/);assert.equal(f.listeners.size,0);
});
test('recovery explains prose refusals and gives human fallbacks for protocol codes',()=>{
 assert.equal(recoveryMessage('Keep object titles below 300 characters.'),'Keep object titles below 300 characters.');
 assert.match(recoveryMessage('edit-denied'),/cannot edit/);
 assert.match(recoveryMessage('client-outdated'),/New editing tools/);
 assert.equal(recoveryMessage('unrecognized-code'),recoveryMessage(null));
 assert.equal(recoveryMessage('constructor'),recoveryMessage(null));
 assert.match(recoveryMessage(null),/could not be saved/);
});
