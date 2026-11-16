import test from 'node:test';
import assert from 'node:assert/strict';
import {parseTSV,fragmentHTML} from '../../priv/lib/live/edit/clipboard.mjs';
test('TSV respects spreadsheet quotes, Unicode, terminal rows and empty cells',()=>{
 assert.deepEqual(parseTSV('"a\t""b""\n🌱"\t\n\t').map(row=>row.map(cell=>cell.text)),[['a\t"b"\n🌱',''],['','']]);
 assert.deepEqual(parseTSV('a\tb\r\nc\t\r\n').map(row=>row.map(cell=>cell.text)),[['a','b'],['c','']]);
 assert.deepEqual(parseTSV('a\tb\nc').map(row=>row.map(cell=>cell.text)),[['a','b'],['c','']]);
 assert.equal(parseTSV('one cell'),null);
 assert.throws(()=>parseTSV('"unclosed\n'));
 assert.throws(()=>parseTSV('"closed"bad\tfield'));
 assert.throws(()=>parseTSV('x'.repeat(1024*1024+1)));
});
test('table HTML preserves rows, cell roles, alignment and safe inline formatting',()=>{
 const base=(id,type,parent,attrs={},text='',marks=[])=>({id,type,parent,attrs,text,marks,wraps:[]});
 const blocks=[base('t','table',null),base('r','table-row','t'),base('a','table-cell','r',{header:true,align:'right'},'🌱 &',{from:0})];
 blocks[2].marks=[{from:0,to:1,call:{function:'text/bold',args:{}}}];
 assert.equal(fragmentHTML(blocks),'<table><tr><th style="text-align:right"><strong>🌱</strong> &amp;</th></tr></table>');
});
