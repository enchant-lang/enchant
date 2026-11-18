import assert from 'node:assert/strict';
import test from 'node:test';
import {retainedDrafts, exportRetainedDraft, copyRetainedDraft} from '../../priv/lib/live/edit/assets/draft-inventory.mjs';

const checkpoint = JSON.stringify({digest: 'sha256:original', revision: 7, document: {id: 'doc', blocks: []}});
const recovery = {pending: [{id: 'patch', text: 'Unsaved 🌱'}], basis: 'sha256:original'};
const key = (type, resource, tab) => 'enchant.' + type + ':' + encodeURIComponent(resource) + ':' + tab;
const memory = (items = []) => {
  const values = new Map(items);
  return {
    get length() { return values.size; },
    key: index => Array.from(values.keys())[index] ?? null,
    getItem: name => values.get(name) ?? null,
    setItem: (name, value) => values.set(name, value),
    removeItem: name => values.delete(name)
  };
};

test('lists scoped recovery from every tab without leaking content or checkpoint rows', () => {
  const text = key('text.v1','alice/doc/source','tab-a');
  const rich = key('edit.v2','alice/doc','tab-b');
  const other = key('edit.v2','alice-extra/doc','tab-c');
  const storage = memory([
    [text, JSON.stringify({schema: 1, updated: 5, value: 'Private text', basis: 'sha256:one'})],
    [rich, JSON.stringify({schema: 3, updated: 6, checkpointKey: rich+':checkpoint:old', recovery})],
    [rich+':checkpoint:old', checkpoint],
    [other, '{"updated":9}']
  ]);
  assert.deepEqual(retainedDrafts('alice/',storage),[
    {key:rich, resource:'alice/doc', tab:'tab-b', type:'editor', updated:6},
    {key:text, resource:'alice/doc/source', tab:'tab-a', type:'text', updated:5}
  ]);
  assert.deepEqual(retainedDrafts('',storage),[]);
  assert.throws(() => exportRetainedDraft('alice/',other,storage),/outside/);
});

test('copies rich recovery to a new checkpoint without changing the original basis', () => {
  const rich = key('edit.v2','alice/doc','tab-old');
  const pointer = JSON.stringify({schema:3, updated:6, checkpointKey:rich+':checkpoint:old', recovery});
  const storage = memory([[rich,pointer],[rich+':checkpoint:old',checkpoint]]);
  const target = copyRetainedDraft('alice/',rich,'tab-new',storage,()=>'copy');
  assert.equal(target,key('edit.v2','alice/doc','tab-new'));
  assert.equal(storage.getItem(rich),pointer);
  const restored = JSON.parse(storage.getItem(target));
  assert.equal(restored.checkpointKey,target+':checkpoint:copy');
  assert.deepEqual(restored.recovery,recovery);
  assert.equal(storage.getItem(restored.checkpointKey),checkpoint);
  assert.throws(() => copyRetainedDraft('alice/',rich,'tab-new',storage),/already/);
  assert.equal(exportRetainedDraft('alice/',rich,storage).checkpointRaw,checkpoint);
});

test('preserves exact legacy recovery and text or property draft bytes', () => {
  const text = key('text.v1','alice/doc/source','tab-a');
  const fields = key('text.v1','alice/doc/object/properties','tab-b');
  const legacy = key('edit.v2','alice/doc','tab-c');
  const records = [
    [text, JSON.stringify({schema:1,value:'A\r\nB 💫',basis:'sha256:source'})],
    [fields, JSON.stringify({schema:1,value:'{"state":"DEFER"}',basis:'sha256:form'})],
    [legacy, JSON.stringify({schema:2,checkpoint:JSON.parse(checkpoint),recovery})]
  ];
  const storage = memory(records);
  for (const [name,value] of records) {
    const copied = copyRetainedDraft('alice/',name,'isolated',storage);
    assert.equal(storage.getItem(copied),value);
    assert.equal(exportRetainedDraft('alice/',name,storage).raw,value);
  }
});

test('unreadable and foreign pointers never open another recovery', () => {
  const rich = key('edit.v2','alice/doc','tab-a');
  const foreign = key('edit.v2','bob/doc','tab-a')+':checkpoint:foreign';
  const damaged = key('text.v1','alice/doc/source','tab-b');
  const storage = memory([[rich,JSON.stringify({schema:3,checkpointKey:foreign,recovery})],[foreign,checkpoint],[damaged,'{']]);
  assert.equal(retainedDrafts('alice/',storage).length,2);
  assert.equal(exportRetainedDraft('alice/',rich,storage).checkpointRaw,null);
  assert.equal(exportRetainedDraft('alice/',damaged,storage).raw,'{');
  assert.throws(() => copyRetainedDraft('alice/',rich,'tab-c',storage),/unreadable/);
  assert.equal(storage.getItem(foreign),checkpoint);
});

test('quota failure leaves the prior tab untouched and removes only its staged copy', () => {
  const rich = key('edit.v2','alice/doc','tab-a');
  const checkpointKey = rich+':checkpoint:old';
  const pointer = JSON.stringify({schema:3,checkpointKey,recovery});
  const storage = memory([[rich,pointer],[checkpointKey,checkpoint]]);
  const write = storage.setItem;
  storage.setItem = (name,value) => {
    if (name.endsWith(':tab-b')) throw Error('Quota exceeded');
    write(name,value);
  };
  assert.throws(() => copyRetainedDraft('alice/',rich,'tab-b',storage,()=>'copy'),/Quota/);
  assert.equal(storage.length,2);
  assert.equal(storage.getItem(rich),pointer);
  assert.equal(storage.getItem(checkpointKey),checkpoint);
});
