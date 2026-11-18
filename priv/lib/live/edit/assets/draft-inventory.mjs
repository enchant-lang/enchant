// A device inventory reads the existing editor and text recovery records.
// An application supplies the exact resource family for the signed-in actor.
const editPrefix = 'enchant.edit.v2:';
const textPrefix = 'enchant.text.v1:';

function identity(key, scope) {
  if (typeof key !== 'string' || typeof scope !== 'string' || !scope.endsWith('/') || scope.length === 1) return null;
  const type = key.startsWith(editPrefix) ? 'editor' : key.startsWith(textPrefix) ? 'text' : null;
  if (!type) return null;
  const prefix = type === 'editor' ? editPrefix : textPrefix;
  const parts = key.slice(prefix.length).split(':');
  if (parts.length !== 2 || !parts[1]) return null;
  try {
    const resource = decodeURIComponent(parts[0]);
    if (resource.length <= scope.length || !resource.startsWith(scope) || encodeURIComponent(resource) !== parts[0]) return null;
    return {key, resource, tab: parts[1], type, prefix};
  } catch {
    return null;
  }
}

export function retainedDrafts(scope, storage = globalThis.localStorage) {
  const entries = [];
  for (let index = 0; index < storage.length; index += 1) {
    const name = identity(storage.key(index), scope);
    if (!name) continue;
    const raw = storage.getItem(name.key);
    if (raw === null) continue;
    let updated = 0, title;
    try {
      const record = JSON.parse(raw);
      if (Number.isFinite(record?.updated) && record.updated > 0 && record.updated <= 8640000000000000) updated = record.updated;
      if (name.type === 'editor') {
        let checkpoint = record?.checkpoint;
        if (record?.schema === 3 && typeof record.checkpointKey === 'string' && record.checkpointKey.startsWith(name.key + ':checkpoint:')) {
          checkpoint = JSON.parse(storage.getItem(record.checkpointKey));
        }
        const localTitle = checkpoint?.document?.meta?.title;
        if (typeof localTitle === 'string' && localTitle.trim()) title = Array.from(localTitle).slice(0, 120).join('');
      }
    } catch {
      // Unreadable records still belong in the inventory and can be exported.
    }
    entries.push({key: name.key, resource: name.resource, tab: name.tab, type: name.type, updated, ...(title ? {title} : {})});
  }
  return entries.sort((left, right) => right.updated - left.updated || left.key.localeCompare(right.key));
}

export function validDraftCheckpoint(value) {
  return typeof value === 'object' && value !== null && typeof value.digest === 'string'
    && Number.isSafeInteger(value.revision) && typeof value.document?.id === 'string' && Array.isArray(value.document.blocks);
}

function readRecord(scope, key, storage) {
  const name = identity(key, scope);
  if (!name) throw Error('This draft is outside the active resource family.');
  const raw = storage.getItem(key);
  if (raw === null) throw Error('This draft is no longer stored on this device.');
  let record, checkpointRaw = null;
  try {
    record = JSON.parse(raw);
    if (name.type === 'text') {
      if (record?.schema !== 1 || typeof record.value !== 'string' || typeof record.basis !== 'string') throw Error();
    } else {
      if (!record?.recovery || typeof record.recovery !== 'object' || Array.isArray(record.recovery)) throw Error();
      let checkpoint = record.checkpoint;
      if (record.schema === 3) {
        if (typeof record.checkpointKey !== 'string' || !record.checkpointKey.startsWith(key + ':checkpoint:')) throw Error();
        checkpointRaw = storage.getItem(record.checkpointKey);
        checkpoint = JSON.parse(checkpointRaw);
      } else if (record.schema !== 2) {
        throw Error();
      }
      if (!validDraftCheckpoint(checkpoint)) throw Error();
    }
  } catch {
    if (storage.getItem(key) !== raw) throw Error('This draft changed in another tab. Refresh the list.');
    return {...name, raw, checkpointRaw, readable: false};
  }
  if (storage.getItem(key) !== raw) throw Error('This draft changed in another tab. Refresh the list.');
  return {...name, raw, checkpointRaw, record, readable: true};
}

export function exportRetainedDraft(scope, key, storage = globalThis.localStorage) {
  const draft = readRecord(scope, key, storage);
  return {
    schema: 'enchant.retained-draft/1', resource: draft.resource, type: draft.type,
    readable: draft.readable, raw: draft.raw, checkpointRaw: draft.checkpointRaw
  };
}

// targetTab is a new tab identity chosen by the opening recovery action.
// The original remains available until its own author explicitly removes it.
export function copyRetainedDraft(scope, key, targetTab, storage = globalThis.localStorage,
                                  checkpointId = () => globalThis.crypto.randomUUID()) {
  const draft = readRecord(scope, key, storage);
  if (!draft.readable) throw Error('Download the unreadable recovery copy to keep its bytes.');
  if (typeof targetTab !== 'string' || !/^[a-zA-Z0-9-]{1,80}$/.test(targetTab)) throw Error('Choose an isolated tab.');
  const target = draft.prefix + encodeURIComponent(draft.resource) + ':' + targetTab;
  if (storage.getItem(target) !== null) throw Error('This tab already has a draft for that resource.');
  if (draft.type === 'text' || draft.record.schema === 2) {
    storage.setItem(target, draft.raw);
    return target;
  }
  const checkpoint = target + ':checkpoint:' + checkpointId();
  storage.setItem(checkpoint, draft.checkpointRaw);
  try {
    storage.setItem(target, JSON.stringify({...draft.record, checkpointKey: checkpoint}));
  } catch (error) {
    try { storage.removeItem(checkpoint); } catch {}
    throw error;
  }
  return target;
}
