import test from 'node:test';
import assert from 'node:assert/strict';
import {EditorState} from '@codemirror/state';
import {applySourceChanges,normalizeSource} from '../../priv/lib/live/edit/source-changes.mjs';
function edit(source,changes){
 const before=EditorState.create({doc:source}),transaction=before.update({changes}),edits=[];
 transaction.changes.iterChanges((from,to,_fromB,_toB,text)=>edits.push({from,to,text:text.toString()}));
 const value=applySourceChanges(source,edits);assert.equal(normalizeSource(value),transaction.state.doc.toString());return value;
}
test('a single native edit preserves every unrelated CRLF and mixed separator byte',()=>{
 const original='α\r\nfirst\n🌿 second\r\nend';const at=normalizeSource(original).indexOf('first');
 assert.equal(edit(original,{from:at,to:at+1,insert:'F'}),original.replace('first','First'));
 assert.equal(edit('line\r\nbody\r\n',{from:0,to:1,insert:'L'}),'Line\r\nbody\r\n');
});
test('UTF-16 source positions retain combining text and supplementary characters',()=>{
 const source='x🌿\r\n最後\né';
 assert.equal(edit(source,{from:1,to:3,insert:'é'}),'xé\r\n最後\né');
 const at=normalizeSource(source).indexOf('最後');assert.equal(edit(source,{from:at,to:at+2,insert:'終わり'}),'x🌿\r\n終わり\né');
});
test('multi-range edits map against the original exact source',()=>{
 assert.equal(edit('a\r\nb\nc\r\n',[{from:0,to:1,insert:'A'},{from:4,to:5,insert:'C'}]),'A\r\nb\nC\r\n');
 assert.equal(edit('a\r\nb\nc',{from:1,to:4,insert:'|'}),'a|c');
});
test('only inserted line breaks adopt the file style; EOF and untouched lines stay exact',()=>{
 assert.equal(edit('one\r\ntwo\nend',{from:3,insert:'\nnew'}),'one\r\nnew\r\ntwo\nend');
 assert.equal(edit('',{from:0,insert:'one\nend'}),'one\nend');
 assert.equal(edit('one\rend',{from:3,insert:'\nnew'}),'one\rnew\rend');
 assert.equal(edit('unterminated',{from:12,insert:'.'}),'unterminated.');
 assert.equal(applySourceChanges('exact\r\n',[]),'exact\r\n');
});
test('invalid ranges cannot produce a silently truncated source',()=>{
 for(const changes of [[{from:-1,to:0,text:''}],[{from:99,to:99,text:''}],[{from:0,to:99,text:''}],
   [{from:2,to:3,text:''},{from:1,to:2,text:''}],[{from:0,to:1,text:null}]])assert.throws(()=>applySourceChanges('a\r\nb',changes));
});
