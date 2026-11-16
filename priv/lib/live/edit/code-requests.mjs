// One request lifetime per input. Text and provider identity guard late answers.
export class CodeRequests {
  constructor(read,provider,fetcher=globalThis.fetch){this.read=read;this.provider=provider;this.fetcher=fetcher.bind(globalThis);this.pending=new Set();this.disposed=false;}
  async request(operation,offset){
    const text=this.read(),provider=this.provider;
    if(this.disposed||!provider?.url)return null;
    const url=new URL(provider.url,location.href);if(url.origin!==location.origin)throw Error('Language service must use the current origin.');
    const controller=new AbortController();this.pending.add(controller);
    try{
      const response=await this.fetcher(url,{method:'POST',credentials:'same-origin',signal:controller.signal,
        headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,text,offset,context:provider.context})});
      if(!response.ok)throw Error('Language service is unavailable.');
      const answer=await response.json();
      return !this.disposed&&this.read()===text&&this.provider===provider?answer:null;
    }finally{this.pending.delete(controller);}
  }
  dispose(){this.disposed=true;for(const request of this.pending)request.abort();this.pending.clear();}
}
