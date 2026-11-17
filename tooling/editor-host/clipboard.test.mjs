import test from 'node:test';
import assert from 'node:assert/strict';
import {parseTSV,fragmentHTML} from '../../priv/lib/live/edit/clipboard.mjs';
test('TSV respects spreadsheet quotes, Unicode, terminal rows and empty cells',()=>{
 assert.deepEqual(parseTSV('"a\t""b""\n🌱"\t\n\t').map(row=>row.map(cell=>cell.text)),[['a\t"b"\n🌱',''],['','']]);
 assert.deepEqual(parseTSV('a\tb\r\nc\t\r\n').map(row=>row.map(cell=>cell.text)),[['a','b'],['c','']]);
 assert.deepEqual(parseTSV('a\tb\nc').map(row=>row.map(cell=>cell.text)),[['a','b'],['c','']]);
 assert.equal(parseTSV('one cell'),null);
 assert.throws(()=>parseTSV('x\t'.repeat(33)));
 assert.throws(()=>parseTSV('x\n'.repeat(257)));
 assert.throws(()=>parseTSV('x\t'.repeat(33)+'\n'+'y\n'.repeat(257))); 
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
test('rich HTML keeps list hierarchy, checkboxes and child tables without repeating descendants',()=>{
 const base=(id,type,parent=null,text='',attrs={})=>({id,type,parent,text,attrs,marks:[],wraps:[]});
 const blocks=[base('one','ordered',null,'First'),base('nested','bullet','one','Child & note'),
  base('table','table','one'),base('row','table-row','table'),base('cell','table-cell','row','Fact'),
  base('two','task',null,'Review',{checked:true}),base('end','paragraph',null,'After')];
 assert.equal(fragmentHTML(blocks),'<ol><li>First<ul><li>Child &amp; note</li></ul><table><tr><td style="text-align:left">Fact</td></tr></table></li></ol><ul><li><input type="checkbox" disabled checked>Review</li></ul><p>After</p>');
 assert.equal(fragmentHTML([base('partial','bullet','outside','Selected')]),'<ul><li>Selected</li></ul>');
});
