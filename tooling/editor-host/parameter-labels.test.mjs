import test from 'node:test';
import assert from 'node:assert/strict';
import {choiceLabel} from '../../priv/lib/live/edit/parameter-labels.mjs';
test('an empty choice has a label without reserving a workflow value',()=>{
  assert.equal(choiceLabel({'empty-label':'No state'},''),'No state');
  assert.equal(choiceLabel({'empty-label':'No state'},'None'),'None');
  assert.equal(choiceLabel({},null),'None');
  assert.equal(choiceLabel({},false),'False');
  assert.equal(choiceLabel({},0),'0');
});
test('custom labels and Unicode stay presentation data and inherited keys are ignored',()=>{
  assert.equal(choiceLabel({labels:{READY:'Ready for review'}},'READY'),'Ready for review');
  assert.equal(choiceLabel({labels:{}},'constructor'),'Constructor');
  assert.equal(choiceLabel({labels:{'':'  '},'empty-label':'No state'},''),'No state');
  assert.equal(choiceLabel({},'🌱 release'),'🌱 release');
  assert.equal(choiceLabel({},'équipe'),'Équipe');
});
