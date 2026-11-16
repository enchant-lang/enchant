// Exact text recovery. The admission basis travels with the draft, never with
// the latest remote source. The host must still use its authoritative writer.
export class TextDraftStore {
  constructor(resource, storage=globalThis.localStorage, tabs=globalThis.sessionStorage){
    this.storage=storage;this.key=null;this.warning=null;this.unreadable=false;this.corrupt=null;
    try {
      let tab=tabs.getItem('enchant.edit.tab');
      if(!tab){tab=crypto.randomUUID();tabs.setItem('enchant.edit.tab',tab);}
      if(resource)this.key='enchant.text.v1:'+encodeURIComponent(resource)+':'+tab;
    }catch(error){this.warning=error;}
  }
  read(){
    if(!this.key)return null;
    let raw;
    try {
      raw=this.storage.getItem(this.key);if(!raw)return null;
      const item=JSON.parse(raw);
      if(item.schema!==1||typeof item.value!=='string'||typeof item.basis!=='string')throw Error('Unrecognized text recovery');
      return item;
    }catch(error){this.retainUnreadable(error,raw);return null;}
  }
  retainUnreadable(error,raw){
    if(raw===undefined)try{raw=this.key?this.storage.getItem(this.key):null;}catch{}
    this.warning=error;this.unreadable=true;
    this.corrupt={schema:'enchant.unreadable-recovery/1',raw:raw??null};
  }
  write(value,basis){
    if(!this.key||this.unreadable)return false;
    try{this.storage.setItem(this.key,JSON.stringify({schema:1,value,basis,updated:Date.now()}));this.warning=null;return true;}
    catch(error){this.warning=error;return false;}
  }
  remove(force=false){
    if(!this.key)return !this.warning;
    if(this.unreadable&&!force)return false;
    try{this.storage.removeItem(this.key);this.warning=null;this.unreadable=false;this.corrupt=null;return true;}
    catch(error){this.warning=error;return false;}
  }
}
export class TextDraft {
  constructor(model,store){
    this.store=store;this.confirmed=model.confirmed;this.confirmedBasis=model['confirmed-basis'];
    const cached=store.read();
    this.value=cached?.value??model.value??this.confirmed;
    this.basis=cached?.basis??model.basis??this.confirmedBasis;
    this.restored=!!cached;this.normalize();
  }
  get dirty(){return this.value!==this.confirmed;}
  get stale(){return this.dirty&&this.basis!==this.confirmedBasis;}
  normalize(){if(!this.dirty)this.basis=this.confirmedBasis;}
  edit(value){this.value=value;this.normalize();this.persist();}
  receive(model){
    const clean=!this.dirty;
    this.confirmed=model.confirmed;this.confirmedBasis=model['confirmed-basis'];
    const accepted=model.accepted;
    if(clean||(accepted&&accepted.basis===this.confirmedBasis&&accepted.value===this.value)){
      this.value=this.confirmed;this.basis=this.confirmedBasis;
    }
    this.normalize();this.persist();
  }
  discard(){if(this.store.remove(true)===false)return false;this.value=this.confirmed;this.basis=this.confirmedBasis;this.restored=false;return true;}
  persist(){if(this.dirty)this.store.write(this.value,this.basis);else this.store.remove();}
}
