import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const chrome=process.env.CHROME_PATH;assert.ok(chrome&&existsSync(chrome),'Explicit Google Chrome required');
const temp=mkdtempSync(join(tmpdir(),'workboard-qa-')),base='http://127.0.0.1:8498',output=resolve('mvp/browser-qa/artifacts');mkdirSync(output,{recursive:true});
const server=spawn('python3',['mvp/browser-qa/fixture_server.py'],{env:{...process.env,PLAYGROUNDS_STATE_PATH:join(temp,'state.json'),PLAYGROUNDS_PORT:'8498'},stdio:'pipe'});let browser,logs='';server.stdout.on('data',d=>logs+=d);server.stderr.on('data',d=>logs+=d);
async function api(path,body,status=200){const r=await fetch(base+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});assert.equal(r.status,status,await r.clone().text());return r.json()}
try{
 let ready=false;for(let i=0;i<50;i++){try{await api('/api/policy');ready=true;break}catch{await new Promise(r=>setTimeout(r,100))}}assert.ok(ready);
 const agents=[];for(const name of ['Peach (QA)','Lilac (QA)','Mint (QA)','Sky (QA)','Waiting (QA)'])agents.push(await api('/api/agents/register',{name,space:'playground'}));
 const goal=await api('/api/goals',{title:'A cozy collaborative pilot (QA)',budget:100}),tasks=[];
 for(let i=0;i<5;i++){const t=await api(`/api/goals/${goal.id}/tasks`,{title:['Welcome companions','Review room safety','Arrange the study nook','Test mobile navigation','Next contribution'][i],bounty:10});tasks.push(t);await api(`/api/tasks/${t.id}/claim`,{agent_id:agents[i].id},i===4?409:200)}
 browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 // Disable the10s polling fallback: subsequent updates must arrive through real SSE.
 // WebGL is covered in separate jobs; this lane tests the accessible board directly.
 await page.addInitScript(()=>{const interval=window.setInterval;window.setInterval=(fn,delay,...args)=>delay===10000?0:interval(fn,delay,...args);const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type.startsWith('webgl')?null:get.call(this,type,...args)}});
 await page.goto(base,{waitUntil:'domcontentloaded'});await page.click('#classTab');await page.waitForSelector('#workboard .wb-card');assert.equal(await page.locator('#workboard .wb-card').count(),4);assert.match(await page.locator('.wb-capacity').textContent(),/4 \/ 4.*Full.*no automatic waitlist/);
 const card=page.locator(`[data-agent-id="${agents[0].id}"]`);
 await api(`/api/tasks/${tasks[0].id}/progress`,{agent_id:agents[0].id,note:'<img src=x onerror="window.boardInjected=true">',progress_pct:.35});
 await page.waitForFunction(()=>document.querySelector('#workboard progress')?.value===35);assert.equal(await page.locator('#workboard img').count(),0);assert.equal(await page.evaluate(()=>window.boardInjected),undefined);assert.match(await card.textContent(),/<img src=x/);
 await api(`/api/tasks/${tasks[0].id}/progress`,{agent_id:agents[0].id,note:'First welcome flow is ready for review',progress_pct:.75});await page.waitForFunction(()=>[...document.querySelectorAll('#workboard progress')].some(p=>p.value===75));
 await api(`/api/tasks/${tasks[0].id}/complete`,{agent_id:agents[0].id,result:'Welcome flow complete'});await page.waitForFunction(()=>document.getElementById('workboard').textContent.includes('pending verification'));
 await api(`/api/tasks/${tasks[0].id}/verify`,{approved:true,verifier_agent_id:agents[1].id});await page.waitForFunction(()=>document.getElementById('workboard').textContent.includes('9.00 credits earned'));assert.match(await card.textContent(),/No active task/);await card.locator('summary').click();assert.match(await card.textContent(),/Work reviewed: Welcome companions.*accepted/);
 await api(`/api/tasks/${tasks[1].id}/progress`,{agent_id:agents[1].id,note:'Cross-room denial checks completed',progress_pct:.6});await page.waitForFunction(()=>[...document.querySelectorAll('#workboard progress')].some(p=>p.value===60));assert.equal(await card.locator('details').evaluate(d=>d.open),true,'live refresh preserves disclosure');
 await page.locator('#workboard').evaluate(el=>{const p=document.createElement('p');p.textContent='CHROME QA — synthetic agents, real protocol and SSE; polling disabled';p.style.fontWeight='bold';el.before(p)});
 async function shot(name){await page.evaluate(()=>scrollTo(0,0));const clip=await page.locator('#workboard').boundingBox();await page.screenshot({path:join(output,name),clip,fullPage:true})}
 await shot('workboard-desktop.png');await page.setViewportSize({width:390,height:844});await shot('workboard-mobile.png');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'no mobile overflow');
 const empty=await api('/api/goals',{title:'Another private goal (QA)',budget:10});await page.waitForFunction(id=>[...document.querySelectorAll('#goalSelect option')].some(o=>o.value===id),empty.id);await page.selectOption('#goalSelect',empty.id);await page.waitForFunction(()=>document.querySelectorAll('#workboard .wb-card').length===0);assert.ok(!(await page.locator('#workboard').textContent()).includes('Welcome companions'),'goal switching clears old tasks');
 await page.evaluate(()=>dispatchEvent(new CustomEvent('playgrounds-world',{detail:{world:{agents:[]},state:{goals:{}}}})));assert.equal(await page.locator('#workboard .wb-card').count(),0,'room-clear event removes all cards');
 assert.deepEqual(errors,[]);console.log('Chrome work board: real SSE (poll disabled), capacity denial, progress, safe text, completion/review/earnings, disclosure, goal/scope clear, desktop/mobile passed.');
}finally{if(browser)await browser.close();server.kill();console.log(logs.slice(-500))}
