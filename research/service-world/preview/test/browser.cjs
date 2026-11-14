// Actual native form/navigation behavior; only an explicitly marked loopback fixture.
const {chromium} = require('/home/othman/projects/general/gather-social-studio/scripts/browser.cjs');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const base = process.env.CONNECTED_BASE_URL;
const url = new URL(base);
assert(url.protocol === 'http:' && url.hostname === '127.0.0.1' && url.port);
const evidence = path.resolve('../evidence/connected-workspace');
fs.mkdirSync(evidence, {recursive: true});
const checks = [], errors = [], overflow = [], screenshots = [];
let browser, context, page;
async function check(name, fn) { await fn(); checks.push({name, passed:true}); console.log('passed:',name); }
async function go(side, view, target = page) {
  const r = await target.goto(`${base}/${side}?view=${view}`, {waitUntil:'domcontentloaded'});
  assert.equal(r.status(), 200); await target.locator('.preview-controls').waitFor();
}
async function submit(button) {
  await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}), button.click()]);
  await page.locator('.preview-controls').waitFor();
}
const button = name => page.getByRole('button', {name, exact:true});
async function state() { return (await context.request.get(base+'/demo/state')).json(); }
async function fields(form) {
  return form.evaluate(f=>Object.fromEntries(new FormData(f)));
}
async function post(data, route='/action', origin=base) {
  return context.request.post(base+route, {form:data, headers:{Origin:origin}});
}
async function noOverflow(side, view) {
  const extra = await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  if(extra>2) overflow.push({side,view,extra,width:page.viewportSize().width});
}
async function shot(name) {
  await page.evaluate(()=>Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,2000))]));
  const file = name+'.png'; await page.screenshot({path:path.join(evidence,file),fullPage:true}); screenshots.push(file);
}
(async()=>{
try {
  const health=await(await fetch(base+'/health')).json(); assert.equal(health.fixture,true);
  browser=await chromium.launch({headless:true, executablePath:cp.execFileSync('which',['chromium'],{encoding:'utf8'}).trim(),
    args:['--no-sandbox','--disable-dev-shm-usage']});
  context=await browser.newContext({viewport:{width:1440,height:1050},deviceScaleFactor:1});
  page=await context.newPage();
  page.on('pageerror', e=>errors.push(e.message));
  page.on('response', r=>{if(r.url().startsWith(base)&&r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
  await check('both original product shells and all 34 screens render',async()=>{
    for(const side of ['team','station']) for(const view of ['today','project','services','inbox','tasks','knowledge','jobs','access','runtime','activity','connections','recovery','clients','gateway','roadmap','capture','features']) {
      await go(side,view); assert(await page.locator(side==='team'?'.app-frame':'.brand-row').count()); await noOverflow(side,view);
    }
  });
  await check('all 44 capabilities link to functional screens in each design',async()=>{
    for(const side of ['team','station']) { await go(side,'features'); assert.equal(await page.locator('[data-feature]').count(),44);
      assert.equal(await page.locator('.preview-feature-list a').count(),44); }
  });
  await check('handoff claim, duplicate-safe task conversion and independent completion',async()=>{
    await go('team','inbox'); await submit(button('Mark read')); assert.equal((await state())['inbox-state'],'read');
    await submit(button('Claim work')); await submit(button('Create linked task')); await submit(button('Create linked task'));
    assert.equal((await state()).tasks.filter(t=>t.id==='handoff').length,1);
    await go('station','tasks'); await submit(page.locator('.preview-row').filter({hasText:"Review Ahmed's Station handoff"}).getByRole('button',{name:'Complete',exact:true}));
    assert.equal((await state())['inbox-state'],'claimed');
    await go('team','inbox'); await submit(button('Mark handled')); assert.equal((await state())['inbox-state'],'handled');
    await submit(button('Rehearse a new incoming reply')); assert.equal((await state())['inbox-state'],'new');
    assert.equal((await state()).tasks.find(t=>t.id==='handoff').state,'done');
  });
  await check('service lifecycle changes are shared across the two interfaces',async()=>{
    await go('station','services'); const card=()=>page.locator('[data-service="website"]');
    await submit(card().getByRole('button',{name:'Start',exact:true}));
    await submit(card().getByRole('button',{name:'Publish preview',exact:true}));
    await go('team','services'); assert(await page.locator('[data-service="website"]').innerText().then(t=>t.includes('Listening')&&t.includes('Published')));
    await page.locator('[data-service="website"] summary').click();
    await submit(page.locator('[data-service="website"]').getByRole('button',{name:'Update to r43',exact:true}));
    assert.equal((await state()).services.find(s=>s.id==='website').version,'r43');
    await page.locator('[data-service="website"] summary').click();
    await submit(page.locator('[data-service="website"]').getByRole('button',{name:'Roll back',exact:true}));
    assert.equal((await state()).services.find(s=>s.id==='website').version,'r12');
  });
  await check('stale draft preserves words and publication keeps its accepted revision',async()=>{
    await go('team','knowledge'); await page.locator('textarea[name=text]').fill('My draft must survive a stale submission');
    const other=await context.newPage(); await go('station','inbox',other);
    await Promise.all([other.waitForNavigation({waitUntil:'domcontentloaded'}),other.getByRole('button',{name:'Mark read',exact:true}).click()]); await other.close();
    await submit(button('Save a new revision')); assert(await page.locator('.preview-error').innerText().then(t=>t.includes('My draft must survive')));
    assert.equal((await state()).document.revision,7);
    await go('team','knowledge'); await page.locator('textarea[name=text]').fill('The accepted rehearsal brief');
    await submit(button('Save a new revision')); await submit(button('Accept this revision')); await submit(button('Share accepted copy'));
    await page.locator('textarea[name=text]').fill('Later unreviewed source'); await submit(button('Save a new revision'));
    const w=await state(); assert.equal(w['snapshot-basis'],7); assert.equal(w.document.revision,9); assert.equal(w.publication.revision,8);
    const shared=await context.request.get(base+'/demo/publication'); assert((await shared.text()).includes('The accepted rehearsal brief'));
    assert(!(await shared.text()).includes('Later unreviewed source'));
  });
  await check('lost product acknowledgement is inspected without another execution',async()=>{
    await go('station','clients'); await submit(button('Rehearse a lost reply'));
    assert.equal((await state()).invitation.state,'uncertain'); await submit(button('Inspect product receipt'));
    await submit(button('Create trial invitation')); assert.equal((await state()).invitation.executions,1);
    assert.equal((await state()).invitation.state,'completed');
  });
  await check('failed refresh retains stale observations and interface mismatch refuses submission',async()=>{
    await go('team','connections'); await submit(button('Disconnect')); const before=(await state()).services;
    await go('team','services'); await submit(button('Refresh services')); assert(await page.locator('.preview-error').count());
    assert.deepEqual((await state()).services,before); assert.equal((await state()).observation,'stale');
    await go('station','connections'); await submit(button('Version mismatch'));
    await go('station','services'); await submit(page.locator('[data-service="app"]').getByRole('button',{name:'Stop',exact:true}));
    assert((await page.locator('.preview-error').innerText()).includes('incompatible'));
    assert.equal((await state()).services.find(s=>s.id==='app')['running?'],true);
    await go('team','connections'); await submit(button('Reconnect')); await go('team','services'); await submit(button('Refresh services'));
  });
  await check('reader controls and forged writes enforce the current server-side role',async()=>{
    await go('team','access'); await submit(button('Revoke folder access'));
    await page.getByLabel('Rehearsal role').selectOption('reader'); await submit(button('Switch'));
    assert.equal(await button('Grant read-write').isDisabled(),true);
    const form=await fields(page.locator('form[data-operation=grant]').first());
    form.request='forged-reader'; form.op='start'; form.id='website'; delete form.value;
    const before=await state(); const response=await post(form); assert((await response.text()).includes('Read-only access'));
    assert.equal((await state()).revision,before.revision);
    await submit(button('Join project')); assert((await page.locator('.preview-error').innerText()).includes('Folder access was revoked'));
    await page.getByLabel('Rehearsal role').selectOption('operator'); await submit(button('Switch'));
  });
  await check('exact replay does not duplicate a task; CSRF and foreign origins are refused',async()=>{
    await go('team','tasks'); const form=await fields(page.locator('form[data-operation=new-task]')); form.text='One exact command';
    const first=await post(form); assert.equal(first.status(),200); const count=(await state()).tasks.length;
    await post(form); assert.equal((await state()).tasks.length,count);
    const bad=await post({...form,csrf:'wrong',request:'wrong-csrf'}); assert.equal(bad.status(),400);
    const foreign=await post({...form,request:'foreign-origin'},'/action','https://foreign.invalid'); assert.equal(foreign.status(),400);
  });
  await check('procedure, placement and recovery actions have visible receipts',async()=>{
    await go('team','jobs'); await submit(button('Prepare brief')); assert.equal((await state()).job.executions,1);
    await submit(button('Keep output')); assert.equal((await state()).job.state,'accepted');
    await go('station','runtime'); await submit(button('Split into dedicated VM')); assert.equal((await state()).pool,'dedicated');
    await go('team','recovery'); await submit(button('Prepare separate copy')); assert((await state()).restore.includes('live files unchanged'));
    await submit(button('Send for operator review')); assert((await state()).operator.includes('no privileged action'));
  });
  await check('future feature controls remain explicitly scoped to a design model',async()=>{
    await go('team','roadmap'); await submit(button("Rehearse today's occurrence")); await submit(button("Rehearse today's occurrence"));
    assert.equal((await state()).occurrences,1); await page.locator('input[name=value]').fill('21');
    await submit(button("Replace today's total")); assert.equal((await state())['daily-total'],21);
    await submit(button('Toggle rehearsal pairing')); assert.equal((await state())['browser-paired?'],true);
    await submit(button('Receive an illustrative release receipt')); assert.equal((await state())['release-receipt?'],true);
  });
  await check('separate browser context does not inherit another rehearsal',async()=>{
    const isolated=await browser.newContext(); const tab=await isolated.newPage(); await tab.goto(base+'/team');
    const w=await(await isolated.request.get(base+'/demo/state')).json(); assert.equal(w.revision,1); assert.equal(w.tasks.length,1); await isolated.close();
  });
  await check('desktop and phone layouts, themes, search and Station drawer work',async()=>{
    for(const side of ['team','station']) {
      await page.setViewportSize({width:1440,height:1050}); await go(side,'today');
      await page.evaluate(()=>{document.documentElement.dataset.theme='light';localStorage.setItem('connected-theme','light')});
      await shot(side+'-desktop');
      await go(side,'services'); await shot(side+'-services');
      await page.setViewportSize({width:390,height:844});
      for(const view of ['today','services','inbox','knowledge','access','features']) {await go(side,view);await noOverflow(side,view)}
      await go(side,'today'); await page.locator('[data-demo-theme]').click();
      assert.equal(await page.locator('html').getAttribute('data-theme'),'dark'); await shot(side+'-phone-dark');
      if(side==='station') {await page.locator('[data-rail-toggle]').click(); assert(await page.locator('body').evaluate(b=>b.classList.contains('demo-rail-open'))); await page.locator('[data-rail-close]').first().click();}
      await go(side,'features'); await page.locator('#feature-search').fill('snapshot');
      await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.locator('.preview-search').getByRole('button',{name:'Search',exact:true}).click()]);
      assert((await page.locator('[data-feature]').count())<44); assert((await page.locator('[data-feature]').count())>0);
    }
  });
  await check('all three Org dossiers render and both embedded native mockups navigate',async()=>{
    await page.setViewportSize({width:1440,height:1050});
    for(const key of ['inventory','team','station']) {
      const r=await page.goto(base+'/dossiers/'+key,{waitUntil:'domcontentloaded'}); assert.equal(r.status(),200);
      await page.locator('#doc').waitFor();
      if(key!=='inventory') {
        await page.locator('.source-frame').waitFor(); const frame=page.frameLocator('.source-frame');
        await frame.locator('.preview-controls').waitFor();
        await frame.getByRole('link',{name:'Services',exact:true}).last().click(); await frame.locator('[data-service]').first().waitFor();
      }
      await shot('dossier-'+key);
    }
  });
  assert.deepEqual(overflow,[],'Horizontal overflow: '+JSON.stringify(overflow));
  assert.deepEqual(errors,[],'Browser errors: '+JSON.stringify(errors));
} catch(error) {
  errors.push(error.stack||String(error));
  if(page)try{await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true})}catch{}
  process.exitCode=1;
} finally {
  if(browser)await browser.close();
  const result={passed:!process.exitCode,checkedAt:new Date().toISOString(),scope:'Synthetic native UI rehearsal; no production effects',checks,errors,overflow,screenshots};
  fs.writeFileSync(path.join(evidence,'browser.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({passed:result.passed,checks:checks.length,screenshots:screenshots.length}));
}
})();
