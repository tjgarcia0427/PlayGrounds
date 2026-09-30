import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const chrome=process.env.CHROME_PATH;
assert.ok(chrome && existsSync(chrome),'CHROME_PATH must explicitly identify installed Google Chrome; no browser auto-detection/fallback');
const temp=mkdtempSync(join(tmpdir(),'playgrounds-chrome-'));
const base='http://127.0.0.1:8494';
const output=resolve('mvp/browser-qa/artifacts');mkdirSync(output,{recursive:true});
const server=spawn('python3',['mvp/browser-qa/fixture_server.py'],{env:{...process.env,PLAYGROUNDS_STATE_PATH:join(temp,'state.json'),PLAYGROUNDS_PORT:'8494'},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',d=>logs+=d);server.stderr.on('data',d=>logs+=d);
let browser,heartbeat;
const presence=world=>world.agents.map(({last_heartbeat,...agent})=>agent);
async function api(path,body){const r=await fetch(base+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});assert.ok(r.ok,await r.clone().text());return r.json()}
try {
  let ready=false;
  for(let i=0;i<50;i++){try{await api('/api/policy');ready=true;break}catch{await new Promise(r=>setTimeout(r,100))}}
  assert.ok(ready,'test server did not become ready');
  // Synthetic QA identities only, never presented as connected real agents.
  const agents=[];
  for(const name of ['Mochi (QA)','Clover (QA)','Pip (QA)','Peach (QA)','Bramble (QA)','Luna (QA)'])agents.push(await api('/api/agents/register',{name,space:'playground',social_enabled:true}));
  const goal=await api('/api/goals',{title:'Visual QA study hall',budget:100});
  for(const agent of agents.slice(0,3)){
    const task=await api(`/api/goals/${goal.id}/tasks`,{title:'Visual QA fixture',bounty:10});
    await api(`/api/tasks/${task.id}/claim`,{agent_id:agent.id});
  }
  heartbeat=setInterval(()=>Promise.all(agents.map(a=>api(`/api/agents/${a.id}/heartbeat`,{}))).catch(e=>logs+=String(e)),10000);
  browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.getElementById('renderStatus').textContent.startsWith('3D campus'),{timeout:20000});
  await page.uncheck('#ambientLife');
  assert.equal(await page.locator('#campus3d canvas').count(),1);
  const carouselStart=await page.locator('#campus3d').getAttribute('data-carousel-angle');
  await page.waitForFunction(start=>Number(document.getElementById('campus3d').dataset.carouselAngle)>Number(start),carouselStart);
  assert.equal(await page.locator('#campus3d').getAttribute('data-setting'),'slide-carousel-monkey-bars-modern-study');
  assert.equal(await page.locator('#campus3d').isVisible(),true);
  assert.equal(await page.locator('#worldStage').isVisible(),false);
  // Explicit fixture caption is included in each screenshot.
  await page.evaluate(()=>{const b=document.createElement('p');b.textContent='VISUAL QA FIXTURE — synthetic test agents, not live participants';b.style.cssText='padding:12px;background:#ffe4b5;color:#473d4b;font-weight:bold';document.querySelector('[aria-label="Shared agent world"]').prepend(b)});
  // Observe actual blended transforms, not a synthetic clock jump or pose label alone.
  const personalityLedger=await api('/api/ledger');
  for(const [id,pose,file] of [[agents[5].id,'lookAround','look-around-desktop.png'],[agents[5].id,'headphones','headphone-adjust-desktop.png'],[agents[0].id,'seatedHeadphones','seated-headphone-adjust-desktop.png']]){
    await page.selectOption('#followAgent',id);
    try { await page.waitForFunction(({id,pose})=>JSON.parse(document.getElementById('campus3d').dataset.poses||'[]').some(a=>a.id===id&&a.pose===pose&&(pose==='lookAround'?Math.abs(a.headYaw)>.16:a.rightArmX<-2.5)&&(pose!=='seatedHeadphones'||a.bodyY>.2)),{id,pose},{timeout:90000}); } catch(error) {
      console.error('Personality observation failed',id,pose,await page.locator('#campus3d').evaluate(el=>({clock:el.dataset.animationClock,poses:el.dataset.poses})));
      await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'personality-failure.png')});
      throw error;
    }
    await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,file)});
  }
  assert.deepEqual(await api('/api/ledger'),personalityLedger,'personality gestures must not synthesize protocol events');
  const unchanged=await api('/api/world');
  assert.ok(Number(await page.locator('#campus3d').getAttribute('data-floor-area'))>340,'expanded floor area');
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'campus-desktop.png')});
  await page.selectOption('#followAgent',agents[3].id);
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='playground');
  const travelTask=await api(`/api/goals/${goal.id}/tasks`,{title:'Walk into Classroom (QA)',bounty:10});
  await api(`/api/tasks/${travelTask.id}/claim`,{agent_id:agents[3].id});
  await page.waitForFunction(()=>Number(document.getElementById('campus3d').dataset.moving)>0 && document.getElementById('campus3d').dataset.room==='campus');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.moving==='0');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='classroom');
  // Real UI previews exercise complete local animation cycles, not test-only fast-forward.
  const beforeAmbient=presence(await api('/api/world'));
  const beforeLedger=await api('/api/ledger');
  await page.selectOption('#followAgent',agents[0].id);await page.click('#tryInteraction');
  await page.waitForFunction(id=>JSON.parse(document.getElementById('campus3d').dataset.interactions).some(a=>a.id===id&&a.stage==='sip'),agents[0].id,{timeout:90000});
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'coffee-sip-desktop.png')});
  await page.waitForFunction(()=>JSON.parse(document.getElementById('campus3d').dataset.completed).coffee>=1,null,{timeout:90000});
  await page.selectOption('#followAgent',agents[4].id);await page.selectOption('#interactionKind','carousel');await page.click('#tryInteraction');
  await page.waitForFunction(id=>JSON.parse(document.getElementById('campus3d').dataset.interactions).some(a=>a.id===id&&a.stage==='ride'),agents[4].id,{timeout:90000});
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'carousel-ride-desktop.png')});
  await page.waitForFunction(()=>JSON.parse(document.getElementById('campus3d').dataset.completed).carousel>=1,null,{timeout:90000});
  for(const [kind,stage,pose] of [['slide','slide','slide'],['monkey','traverse','hang']]) {
    // Side view makes the hanging pose visible behind the front ladder.
    if(kind==='monkey')for(let i=0;i<3;i++)await page.click('#cameraRight');
    await page.selectOption('#interactionKind',kind);await page.click('#tryInteraction');
    await page.waitForFunction(({id,stage,pose})=>JSON.parse(document.getElementById('campus3d').dataset.interactions).some(a=>a.id===id&&a.stage===stage&&a.pose===pose),{id:agents[4].id,stage,pose},{timeout:90000});
    await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,`${kind}-interaction-desktop.png`)});
    await page.waitForFunction(kind=>JSON.parse(document.getElementById('campus3d').dataset.completed)[kind]>=1,kind,{timeout:90000});
    if(kind==='monkey')for(let i=0;i<3;i++)await page.click('#cameraLeft');
  }
  assert.deepEqual(presence(await api('/api/world')),beforeAmbient,'ambient interaction must not change agent work state');
  assert.deepEqual(await api('/api/ledger'),beforeLedger,'ambient interaction must not create ledger entries');
  // A real presence change interrupts a slide in flight, then follows its safe exit.
  await page.selectOption('#interactionKind','slide');
  await page.click('#tryInteraction');
  await page.waitForFunction(id=>JSON.parse(document.getElementById('campus3d').dataset.interactions).some(a=>a.id===id&&a.stage==='slide'&&a.pose==='slide'),agents[4].id,{timeout:90000});
  const nextGoal=await api('/api/goals',{title:'Interrupt interaction (QA)',budget:20});
  const interruptTask=await api(`/api/goals/${nextGoal.id}/tasks`,{title:'Real work wins over decoration',bounty:5});
  await api(`/api/tasks/${interruptTask.id}/claim`,{agent_id:agents[4].id});
  await page.waitForFunction(id=>!JSON.parse(document.getElementById('campus3d').dataset.interactions).some(a=>a.id===id),agents[4].id);
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='classroom'&&document.getElementById('campus3d').dataset.moving==='0',null,{timeout:90000});
  assert.equal(await page.locator('#classTab').getAttribute('aria-pressed'),'true');
  const beforeCamera=await api('/api/world');
  await page.click('#classTab');await page.click('#cameraRight');
  await page.locator('#cameraZoom').fill('1.2');
  assert.deepEqual(presence(await api('/api/world')),presence(beforeCamera),'camera controls must not move protocol agents');
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.click('#quietMotion');
  await page.click('#cameraHome');
  assert.equal(await page.locator('#cameraZoom').inputValue(),'1');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.reducedMotion==='true');
  const stoppedAngle=await page.locator('#campus3d').getAttribute('data-carousel-angle');
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))));
  assert.equal(await page.locator('#campus3d').getAttribute('data-carousel-angle'),stoppedAngle,'reduced motion must freeze the carousel');
  await page.click('#classTab');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='classroom');
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'classroom-desktop.png')});
  await page.click('#cameraHome');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='campus');
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'expanded-campus-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  await page.click('#classTab');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='classroom');
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'campus-mobile.png')});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'mobile viewport must not overflow');
  await page.click('#playTab');
  await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='playground');
  await page.locator('[aria-label="Shared agent world"]').screenshot({path:join(output,'expanded-playground-mobile.png')});
  await page.selectOption('#renderMode','2d');assert.equal(await page.locator('#worldStage').isVisible(),true);
  // Block WebGL only inside this test page to exercise the advertised fallback.
  await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...rest){return type.startsWith('webgl')?null:get.call(this,type,...rest)}});
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.getElementById('renderStatus').textContent.includes('2D'));
  assert.equal(await page.locator('#worldStage').isVisible(),true);
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('Chrome WebGL render, view/camera state isolation, mobile layout, reduced-motion control and WebGL failure fallback passed.');
} finally {
  clearInterval(heartbeat);if(browser)await browser.close();server.kill();
  console.log(logs.slice(-1000));
}
