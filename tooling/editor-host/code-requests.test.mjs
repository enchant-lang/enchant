import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CodeRequests} from '../../priv/lib/live/edit/code-requests.mjs';
globalThis.location={href:'https://example.test/document',origin:'https://example.test'};
test('late answers cannot describe newer text and disposal aborts outstanding work',async()=>{
 let text='old',resolve,signal;
 const requests=new CodeRequests(()=>text,{url:'/language'},async(_url,options)=>{signal=options.signal;return new Promise(r=>resolve=()=>r({ok:true,json:async()=>({options:[]})}));});
 const pending=requests.request('completion',3);text='new';resolve();assert.equal(await pending,null);
 const disposed=requests.request('hover',2);requests.dispose();assert.equal(signal.aborted,true);resolve();assert.equal(await disposed,null);
});
test('working text and code-point position are sent only to the current origin',async()=>{
 let body;
 const requests=new CodeRequests(()=>'(str "😀")',{url:'/language',context:{document:'shared'}},async(_url,options)=>{body=JSON.parse(options.body);return {ok:true,json:async()=>({text:'string'})};});
 assert.deepEqual(await requests.request('hover',7),{text:'string'});assert.equal(body.offset,7);assert.equal(body.text,'(str "😀")');assert.equal(body.context.document,'shared');
 const external=new CodeRequests(()=>'',{url:'https://other.test/collect'},()=>{throw Error('must not fetch');});
 await assert.rejects(external.request('completion',0),/current origin/);
});
