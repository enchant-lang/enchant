// Write the checkpoint once, then atomically advance a small recovery pointer.
// The previous pointer remains valid if either write fails midway.
export class DraftStore {
  constructor(scope,options={}){
    this.key=null;this.warning=null;this.checkpoint=null;this.checkpointKey=null;
    if(options.disabled||!scope)return;
    try{
      let tab=sessionStorage.getItem('enchant.edit.tab');if(!tab){tab=crypto.randomUUID();sessionStorage.setItem('enchant.edit.tab',tab);}
      this.key='enchant.edit.v2:'+encodeURIComponent(scope)+':'+tab;
    }catch(error){this.warning=error;}
  }
  read(){
    if(!this.key)return null;
    try{
      const item=JSON.parse(localStorage.getItem(this.key));
      if(item?.schema===2&&item.checkpoint&&item.recovery)return item;
      if(item?.schema!==3||!item.checkpointKey||!item.recovery)return null;
      const checkpoint=JSON.parse(localStorage.getItem(item.checkpointKey));
      if(!checkpoint)throw Error('The saved checkpoint is unavailable.');
      this.checkpoint=checkpoint;this.checkpointKey=item.checkpointKey;
      return {...item,checkpoint};
    }catch(error){this.warning=error;return null;}
  }
  write(checkpoint,recovery){
    if(!this.key)return false;
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
    if(!this.key)return;
    try{
      const previous=this.checkpointKey||JSON.parse(localStorage.getItem(this.key))?.checkpointKey;
      localStorage.removeItem(this.key);if(previous)localStorage.removeItem(previous);
      this.checkpoint=null;this.checkpointKey=null;
    }catch(error){this.warning=error;}
  }
}
