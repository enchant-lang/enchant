import test from 'node:test';
import assert from 'node:assert/strict';
import {waitForSettlement,recoveryMessage,settleAssignments} from '../../priv/lib/live/edit/settlement.mjs';
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
test('assignment confirmation repeats when fields change during the ordered round trip',async()=>{
 let token='restored title',confirmations=0;const sent=[];
 const acknowledged=await settleAssignments(()=>({token}),()=>sent.push(token),async()=>{
  if(++confirmations===1)token='newer title';
 });
 assert.equal(acknowledged,'newer title');assert.deepEqual(sent,['restored title','newer title']);assert.equal(confirmations,2);
});
test('unsafe field states and an already expired deadline never send assignments',async()=>{
 for(const flag of ['readonly','offline','conflict','invalid','stale','orphaned','composing','disposed']){
  let sent=false;await assert.rejects(settleAssignments(()=>({token:'mine',[flag]:true}),()=>{sent=true;},async()=>{}));assert.equal(sent,false);
 }
 let sent=false;await assert.rejects(settleAssignments(()=>({token:'mine'}),()=>{sent=true;},async()=>{},{timeout:0}),/pending/);assert.equal(sent,false);
});
test('failed confirmation and source drift retain attempted fields without acknowledging them',async()=>{
 const values={title:'Keep me'};
 await assert.rejects(settleAssignments(()=>({token:JSON.stringify(values)}),()=>{},async()=>{throw Error('socket closed');}),/socket closed/);
 assert.deepEqual(values,{title:'Keep me'});
 let stale=false;await assert.rejects(settleAssignments(()=>({token:'mine',stale}),()=>{},async()=>{stale=true;}),/source changed/);
});
test('an aborted assignment lifetime cannot emit or acknowledge a field',async()=>{
 const controller=new AbortController();controller.abort(Error('closed'));let sent=false;
 await assert.rejects(settleAssignments(()=>({token:'mine'}),()=>{sent=true;},async()=>{},{signal:controller.signal}),/closed/);assert.equal(sent,false);
});
test('loss of each publication precondition rejects without waiting for confirmation',async()=>{
 for(const flag of ['readonly','offline','conflict','invalid','composing','preview','disposed']){
  const f=fixture(),ready=waitForSettlement(f.read,f.subscribe);
  f.change({[flag]:true});await assert.rejects(ready);assert.equal(f.listeners.size,0);
 }
});
test('unavailable editors never publish even with an empty queue',async()=>{
 for(const flag of ['readonly','offline','conflict','invalid','composing','preview','disposed']){
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
