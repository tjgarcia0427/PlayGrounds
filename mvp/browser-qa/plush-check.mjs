import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,existsSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const chrome=process.env.CHROME_PATH;
assert.ok(chrome&&existsSync(chrome),'Explicit installed Google Chrome required');
const temp=mkdtempSync(join(tmpdir(),'plush-qa-')),base='http://127.0.0.1:8497',output=resolve('mvp/browser-qa/artifacts');mkdirSync(output,{recursive:true});
const server=spawn('python3',['mvp/browser-qa/fixture_server.py'],{env:{...process.env,PLAYGROUNDS_STATE_PATH:join(temp,'state.json'),PLAYGROUNDS_PORT:'8497'},stdio:'pipe'});
let logs='',browser,heartbeat;server.stdout.on('data',d=>logs+=d);server.stderr.on('data',d=>logs+=d);
async function api(path,body){const r=await fetch(base+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});assert.ok(r.ok,await r.clone().text());return r.json()}
try{
 let ready=false;for(let i=0;i<50;i++){try{await api('/api/policy');ready=true;break}catch{await new Promise(r=>setTimeout(r,100))}}assert.ok(ready);
 const agents=[];for(let i=0;i<24;i++)agents.push(await api('/api/agents/register',{name:`Plush ${i+1} (QA)`,space:'playground',social_enabled:true}));
 heartbeat=setInterval(()=>Promise.all(agents.map(a=>api(`/api/agents/${a.id}/heartbeat`,{}))).catch(e=>logs+=e),10000);
 browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(30000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(base,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.getElementById('campus3d').dataset.artDirection==='plush-pack-2026-09-30');
 await page.uncheck('#ambientLife');await page.emulateMedia({reducedMotion:'reduce'});
 await page.evaluate(()=>{const b=document.createElement('p');b.textContent='ART QA — 24 synthetic agents; original procedural models inspired by Muse’s art pack';b.style.cssText='padding:12px;background:#ffe4b5;color:#473d4b;font-weight:bold';document.querySelector('[aria-label="Shared agent world"]').prepend(b)});
 const worldBefore=await api('/api/world'),ledgerBefore=await api('/api/ledger');
 const styles=JSON.parse(await page.locator('#campus3d').getAttribute('data-character-styles'));assert.equal(styles.length,24);
 async function shot(file){await page.evaluate(()=>window.scrollTo(0,0));const box=await page.locator('[aria-label="Shared agent world"]').boundingBox();await page.screenshot({path:join(output,file),clip:box,fullPage:true,timeout:60000});}
 const seen=new Set();for(const actor of styles){if(seen.has(actor.style))continue;seen.add(actor.style);await page.selectOption('#followAgent',actor.id);if(await page.locator('#portraitView').getAttribute('aria-pressed')!=='true')await page.click('#portraitView');await page.waitForFunction(id=>{const d=document.getElementById('campus3d').dataset;return d.portrait==='true'&&d.following===id},actor.id);await shot(`plush-${actor.style.replaceAll(' ','-')}.png`);}
 await page.click('#cameraHome');await page.click('#playTab');await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='playground'&&document.getElementById('campus3d').dataset.portrait==='false');
 await shot('plush-playground.png');
 const metrics=JSON.parse(await page.locator('#campus3d').getAttribute('data-art-metrics'));assert.ok(metrics.triangles<1500000,'24-agent geometry budget');assert.ok(metrics.textures<80,'bounded shared textures');writeFileSync(join(output,'plush-metrics.json'),JSON.stringify({synthetic:true,agentCount:24,styles:[...seen],...metrics},null,2));
 await page.click('#classTab');await page.waitForFunction(()=>document.getElementById('campus3d').dataset.room==='classroom');await shot('plush-study-hall.png');
 await page.setViewportSize({width:390,height:844});await page.selectOption('#followAgent',agents[0].id);await page.click('#portraitView');await page.waitForFunction(()=>document.getElementById('campus3d').dataset.portrait==='true');await shot('plush-mobile.png');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 const presence=w=>w.agents.map(({last_heartbeat,...a})=>a);assert.deepEqual(presence(await api('/api/world')),presence(worldBefore));assert.deepEqual(await api('/api/ledger'),ledgerBefore);
 await page.selectOption('#renderMode','2d');assert.ok(await page.locator('#worldStage').isVisible());assert.deepEqual(errors,[]);console.log('Plush Chrome: close-ups, 24 agents, budget, room views, reduced motion, mobile, fallback and protocol isolation passed',metrics);
}finally{clearInterval(heartbeat);if(browser)await browser.close();server.kill();console.log(logs.slice(-500))}
