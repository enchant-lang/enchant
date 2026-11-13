// The server resolves this fixed product element. Data cannot choose a callable.
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-research-save]');
 if(!button||button.dataset.researchSave!=='word-answer-evidence'||button.disabled)return;
 const element=document.getElementById('research-word-answer-evidence');
 const status=element?.querySelector('.research-save-result');
 button.disabled=true;
 try {
  const response=await fetch('/research-elements/word-answer-evidence/save',{
   method:'POST',headers:{'content-type':'application/json'},
   body:JSON.stringify({basis:button.dataset.researchBasis})
  });
  const result=await response.json();
  if(!response.ok||result.ok!==true)throw Error(result.error||'The snapshot was not confirmed.');
  if(status)status.textContent='Saved as native Org · revision '+result.revisions+'.';
  document.dispatchEvent(new CustomEvent('formal:research-saved',{detail:{revision:result.revisions}}));
 }catch(error){if(status)status.textContent=error.message;}
 finally{button.disabled=false;}
});
