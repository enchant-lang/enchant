// Publication waits for confirmed authoring, never just an empty socket queue.
export function settlementError(state){
  if(state.disposed)return 'The editor closed before your writing was confirmed.';
  if(state.readonly)return 'This document is shared for reading. Your draft is retained.';
  if(state.offline)return 'You are offline. Reconnect before sharing your writing.';
  if(state.conflict)return 'Resolve the retained draft before sharing your writing.';
  if(state.composing)return 'Finish entering the current character before sharing.';
  if(state.preview)return 'Apply or cancel the current preview before sharing.';
  return null;
}
export function waitForSettlement(read,subscribe,{signal,timeout=30000}={}){
  return new Promise((resolve,reject)=>{
    let done=false,unsubscribe=()=>{},timer;
    const finish=error=>{
      if(done)return;done=true;clearTimeout(timer);unsubscribe();signal?.removeEventListener('abort',aborted);
      if(error)reject(error);else resolve();
    };
    const aborted=()=>finish(Error('The editor closed before your writing was confirmed.'));
    const check=()=>{
      if(done)return;
      try{const state=read(),error=settlementError(state);if(error)finish(Error(error));else if(!state.pending)finish();}
      catch(error){finish(error);}
    };
    if(signal?.aborted){aborted();return;}
    signal?.addEventListener('abort',aborted,{once:true});
    timer=setTimeout(()=>finish(Error('Writing is still saving. Keep this page open and try again.')),timeout);
    unsubscribe=subscribe(check);if(done)unsubscribe();else check();
  });
}
export function recoveryMessage(reason){
  const known={
    'edit-denied':'You cannot edit this document now. Your draft is retained.',
    'document-replaced':'The document changed. Keep a copy, or return to the saved version.',
    'source-serialization':'This edit could not be written in the document format. Your draft is retained.',
    'client-outdated':'New editing tools are available. Download your draft before reloading.',
  };
  return known[reason]|| (typeof reason==='string'&& !/^[a-z][a-z0-9-]*$/.test(reason)
    ?reason:'This edit could not be saved. Keep a copy, or return to the saved version.');
}
