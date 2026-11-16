// Only attempted fields are cached; unrelated remote values never become edits.
export class FormDraft {
  constructor(model,store){
    this.store=store;this.values={...model.values};this.basis=model.basis||model['confirmed-basis'];this.restored=false;
    const cached=store.read();
    if(cached)try{
      const values=JSON.parse(cached.value);
      if(!values||Array.isArray(values)||typeof values!=='object'||Object.values(values).some(v=>!['string','boolean','number'].includes(typeof v)&&v!==null))throw Error('Unrecognized property draft');
      this.values=values;this.basis=cached.basis;this.restored=true;
    }catch(error){store.warning=error;store.unreadable=true;}
    this.receive(model);
  }
  get dirty(){return Object.keys(this.values).length>0;}
  get stale(){return this.dirty&&this.basis!==this.model['confirmed-basis'];}
  get orphaned(){const known=new Set(this.model.fields.map(f=>f.key));return Object.keys(this.values).some(k=>!known.has(k));}
  receive(model){
    this.model=model;
    const accepted=model.accepted?.basis===model['confirmed-basis']?model.accepted.values:{};
    for(const key of Object.keys(this.values)){
      if(Object.hasOwn(model.confirmed,key)&&Object.is(this.values[key],model.confirmed[key])||Object.hasOwn(accepted||{},key)&&Object.is(this.values[key],accepted[key]))delete this.values[key];
    }
    if(!this.dirty)this.basis=model['confirmed-basis'];
    this.persist();
  }
  edit(key,value){
    if(!this.dirty)this.basis=this.model['confirmed-basis'];
    if(Object.hasOwn(this.model.confirmed,key)&&Object.is(value,this.model.confirmed[key]))delete this.values[key];else this.values[key]=value;
    this.persist();
  }
  changes(){
    const changes={};
    for(const field of this.model.fields){
      if(!Object.hasOwn(this.values,field.key))continue;
      let at=changes;const path=field.path;
      // Paths are application descriptors, never read from the recovery file.
      if(!path?.length||path.some(k=>['__proto__','prototype','constructor'].includes(k)))throw Error('Invalid draft field path');
      for(const part of path.slice(0,-1))at=at[part]||(at[part]={});
      at[path.at(-1)]=this.values[field.key];
    }
    return changes;
  }
  assignments(locals){
    // Assign leaves through the normal Live path vocabulary. Event payload maps
    // are application data and intentionally keep their string keys on the wire.
    const terms=[['assign',locals.changes,{}],['assign',locals.basis,this.basis]];
    for(const field of this.model.fields){
      if(!Object.hasOwn(this.values,field.key))continue;
      if(!field.path?.length||field.path.some(k=>['__proto__','prototype','constructor'].includes(k)))throw Error('Invalid draft field path');
      terms.push(['assign',[...locals.changes,...field.path],this.values[field.key]]);
    }
    return terms;
  }
  discard(){this.values={};this.basis=this.model['confirmed-basis'];this.restored=false;this.store.remove(true);}
  persist(){if(this.dirty)this.store.write(JSON.stringify(this.values),this.basis);else this.store.remove();}
}
