// Write the checkpoint once, then atomically advance a small recovery pointer.
// Preserve unreadable records until explicit discard. A retiring instance must
// never resurrect a discarded pointer through a late update or disposal.
export class DraftStore {
  constructor(scope,options={}){
    this.key=null;this.warning=null;this.checkpoint=null;this.checkpointKey=null;this.corrupt=null;this.discarded=false;
    if(options.disabled||!scope)return;
    try{
      let tab=sessionStorage.getItem('enchant.edit.tab');if(!tab){tab=crypto.randomUUID();sessionStorage.setItem('enchant.edit.tab',tab);}
      this.key='enchant.edit.v2:'+encodeURIComponent(scope)+':'+tab;
    }catch(error){this.warning=error;}
  }
  ownCheckpoint(key){return typeof key==='string'&&key.startsWith(this.key+':checkpoint:');}
  validCheckpoint(value){return value&&typeof value==='object'&&typeof value.digest==='string'&&Number.isSafeInteger(value.revision)&&value.document&&typeof value.document.id==='string'&&Array.isArray(value.document.blocks);}
  read(){
    if(!this.key)return null;
    let raw=null,checkpointRaw=null,checkpointKey=null;this.corrupt=null;
    try{
      raw=localStorage.getItem(this.key);if(raw===null)return null;
      const item=JSON.parse(raw);
      if(item?.schema===2&&this.validCheckpoint(item.checkpoint)&&item.recovery&&typeof item.recovery==='object')return item;
      if(item?.schema!==3||!this.ownCheckpoint(item.checkpointKey)||!item.recovery||typeof item.recovery!=='object')throw Error('Unrecognized editor recovery record.');
      checkpointKey=item.checkpointKey;checkpointRaw=localStorage.getItem(checkpointKey);
      const checkpoint=JSON.parse(checkpointRaw);
      if(!this.validCheckpoint(checkpoint))throw Error('The saved checkpoint is unavailable or invalid.');
      this.checkpoint=checkpoint;this.checkpointKey=checkpointKey;this.warning=null;
      return {...item,checkpoint};
    }catch(error){
      this.warning=error;
      if(raw!==null){
        if(!checkpointKey&&this.ownCheckpoint(this.checkpointKey)){
          checkpointKey=this.checkpointKey;
          try{checkpointRaw=localStorage.getItem(checkpointKey);}catch{}
          if(checkpointRaw===null&&this.checkpoint)checkpointRaw=JSON.stringify(this.checkpoint);
        }
        this.corrupt={schema:'enchant.unreadable-recovery/1',raw,checkpointKey,checkpointRaw};
      }
      return null;
    }
  }
  write(checkpoint,recovery){
    if(this.discarded)return true;
    if(!this.key||this.corrupt)return false;
    const previous=this.checkpointKey;let next=previous,committed=false;
    try{
      if(this.checkpoint!==checkpoint||!next){
        next=this.key+':checkpoint:'+crypto.randomUUID();
        localStorage.setItem(next,JSON.stringify(checkpoint));
      }
      localStorage.setItem(this.key,JSON.stringify({schema:3,updated:Date.now(),checkpointKey:next,recovery}));committed=true;
      this.checkpoint=checkpoint;this.checkpointKey=next;this.warning=null;
      if(previous&&previous!==next)try{localStorage.removeItem(previous);}catch{}
      return true;
    }catch(error){
      if(!committed&&next&&next!==previous)try{localStorage.removeItem(next);}catch{}
      this.warning=error;return false;
    }
  }
  remove(){
    if(!this.key)return true;
    try{
      let previous=this.checkpointKey;
      if(!previous)try{previous=JSON.parse(localStorage.getItem(this.key))?.checkpointKey;}catch{}
      localStorage.removeItem(this.key);if(this.ownCheckpoint(previous))localStorage.removeItem(previous);
      this.checkpoint=null;this.checkpointKey=null;this.warning=null;this.corrupt=null;return true;
    }catch(error){this.warning=error;return false;}
  }
  discard(){this.discarded=true;return this.remove();}
}
