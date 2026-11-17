import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeFieldReplacement} from '../../priv/lib/live/edit/geometry.mjs';

test('editing a visible Unicode title retains native metadata and absolute positions',()=>{
  const before='TODO [#A] 🌱 é title :work:';
  const delta=nativeFieldReplacement(before,'🌱 é revised',{start:10,tail:7,head:22,text:'revised'});
  const points=Array.from(before);
  assert.equal(points.slice(0,delta.from).join('')+delta.text+points.slice(delta.to).join(''),'TODO [#A] 🌱 é revised :work:');
  assert.equal(delta.expected,'title');
  assert.equal(delta.from,15);
});
test('native repeated text and empty intermediate fields preserve their source envelopes',()=>{
  assert.deepEqual(nativeFieldReplacement('TODO aaa :tag:','aaaa',{start:5,tail:6,head:7,text:'a'}),
    {from:6,to:6,text:'a',expected:''});
  assert.deepEqual(nativeFieldReplacement('TODO title :tag:','',{start:5,tail:6,head:5}),
    {from:5,to:10,text:'',expected:'title'});
  assert.deepEqual(nativeFieldReplacement('TODO  :tag:','🌱',{start:5,tail:6,head:6,text:'🌱'}),
    {from:5,to:5,text:'🌱',expected:''});
  assert.equal(nativeFieldReplacement('TODO title :tag:','title',{start:5,tail:6}),null);
});
test('invalid field envelopes refuse before generating a model edit',()=>{
  for(const field of [{start:-1},{tail:-1},{start:4,tail:2},{start:0.5},{tail:1.5}])
    assert.throws(()=>nativeFieldReplacement('title','changed',field),/Invalid projected text range/);
  assert.deepEqual(nativeFieldReplacement('plain','plain!'),{from:5,to:5,text:'!',expected:''});
});
