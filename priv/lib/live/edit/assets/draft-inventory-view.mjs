import {retainedDrafts, exportRetainedDraft, copyRetainedDraft} from './draft-inventory.mjs';

function sameOriginPath(value) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) throw Error("Choose a local recovery location.");
  const url = new URL(value, location.origin);
  if (url.origin !== location.origin) throw Error('The recovery location must belong to this application.');
  if (!url.pathname.startsWith('/')) throw Error('Choose a local recovery location.');
  return url;
}

function label(entry) {
  const parts = entry.resource.split('/').slice(1);
  const suffix = parts.at(-1);
  const kind = entry.type === 'editor' ? 'Rich writing' : suffix === 'source' ? 'Org source' : 'Properties';
  return [kind, entry.title || parts.slice(0, entry.type === 'editor' ? parts.length : -1).join(' / ')];
}

function download(scope, entry) {
  const archive = exportRetainedDraft(scope, entry.key);
  const uri = URL.createObjectURL(new Blob([JSON.stringify(archive, null, 2) + '\n'], {type: 'application/json'}));
  const link = document.createElement('a');
  link.href = uri;
  link.download = 'retained-draft.enchant.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(uri), 1000);
}

export function mountDraftInventory(root, initial) {
  let model = initial;
  const list = root.querySelector('[data-draft-inventory-list]');
  const template = root.querySelector('template[data-draft-inventory-item]');
  const count = root.querySelector('[data-draft-inventory-count]');
  const status = root.querySelector('[data-draft-inventory-status]');
  const lifetime = new AbortController();

  function inform(message) { status.textContent = message; }

  async function reopen(entry, control) {
    const opener = window.open('about:blank', '_blank');
    if (!opener) { inform('Allow a new tab to reopen this draft. You can download a copy here.'); return; }
    opener.opener = null;
    const current = model;
    control.disabled = true;
    try {
      const locate = sameOriginPath(current.location);
      locate.searchParams.set('resource', entry.resource);
      const response = await fetch(locate, {credentials: 'same-origin', signal: lifetime.signal});
      if (!response.ok) throw Error('The saved location is unavailable. You can download the retained draft.');
      const target = sameOriginPath((await response.json()).href);
      if (current.scope !== model.scope) throw Error('The active account changed. Open the draft again.');
      const tab = crypto.randomUUID();
      opener.sessionStorage.setItem('enchant.edit.tab', tab);
      copyRetainedDraft(current.scope, entry.key, tab);
      opener.location.replace(target.href);
      inform('Opened a copy in a new tab.');
    } catch (error) {
      opener.close();
      if (!lifetime.signal.aborted) inform(error?.message || 'Unable to reopen this draft. Download a copy to keep it.');
    } finally {
      control.disabled = false;
    }
  }

  function render() {
    list.replaceChildren();
    try {
      const rows = retainedDrafts(model.scope);
      count.textContent = rows.length ? '' : 'No retained drafts on this device.';
      for (const entry of rows) {
        const item = template.content.cloneNode(true);
        const [kind, resource] = label(entry);
        item.querySelector('[data-draft-inventory-kind]').textContent = entry.readable ? kind : kind + ' · Recovery data only';
        item.querySelector('[data-draft-inventory-resource]').textContent = resource;
        const time = item.querySelector('time');
        if (entry.updated > 0) {
          const date = new Date(entry.updated);
          time.dateTime = date.toISOString();
          time.textContent = new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(date);
        } else {
          time.hidden = true;
        }
        const open = item.querySelector('[data-draft-inventory-open]');
        open.hidden = !model.location || !entry.readable;
        open.addEventListener('click', () => reopen(entry, open));
        item.querySelector('[data-draft-inventory-download]').addEventListener('click', () => {
          try { download(model.scope, entry); inform('Downloaded the original recovery data.'); }
          catch (error) { inform(error.message); }
        });
        list.append(item);
      }
    } catch {
      count.textContent = 'Local storage is unavailable in this browser.';
      inform('Keep the original editing tab open if you still have unsaved writing.');
    }
  }

  window.addEventListener('storage', render, {signal: lifetime.signal});
  render();
  return {
    update(next) { model = next; render(); },
    dispose() { lifetime.abort(); }
  };
}
