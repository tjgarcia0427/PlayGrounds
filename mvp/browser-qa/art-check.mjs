import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
const chrome=process.env.CHROME_PATH;
assert.ok(chrome&&existsSync(chrome),'Explicit Google Chrome required; no fallback');
const out=resolve('mvp/browser-qa/artifacts');mkdirSync(out,{recursive:true});
const server=spawn('python3',['-m','http.server','8497','--bind','127.0.0.1','--directory','mvp'],{stdio:'ignore'});
const base='http://127.0.0.1:8497/art-lab/';let browser;
try{
  let ready=false;for(let i=0;i<50;i++){try{if((await fetch(base)).ok){ready=true;break}}catch{}await new Promise(r=>setTimeout(r,100))}assert.ok(ready);
  browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#stage').dataset.ready==='true');
  await page.evaluate(()=>{const p=document.createElement('p');p.textContent='SYNTHETIC ART QA — original sample, not a live agent';p.style.cssText='padding:10px;background:#e6eddf';document.querySelector('main').prepend(p)});
  const evidence={};
  for(const treatment of ['baseline','polished']){
    await page.click('#'+treatment);
    await page.waitForFunction(t=>document.querySelector('#stage').dataset.treatment===t,treatment);
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(r)))));
    await page.screenshot({path:join(out,`art-${treatment}-desktop.png`),fullPage:true});
    evidence[treatment]=await page.locator('#stage').evaluate(el=>({calls:Number(el.dataset.drawCalls),triangles:Number(el.dataset.triangles)}));
    assert.ok(evidence[treatment].calls>0&&evidence[treatment].calls<180,'sample draw-call guard');
    assert.ok(evidence[treatment].triangles>0&&evidence[treatment].triangles<300000,'sample geometry budget');
  }
  await page.click('#front');await page.screenshot({path:join(out,'art-face-desktop.png'),fullPage:true});
  await page.uncheck('#still');const initial=await page.locator('#stage').getAttribute('data-motion-clock');
  await page.waitForFunction(start=>Number(document.querySelector('#stage').dataset.motionClock)>Number(start),initial);
  await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('#stage').dataset.still==='true');
  const stopped=await page.locator('#stage').getAttribute('data-motion-clock');
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(r)))));
  assert.equal(await page.locator('#stage').getAttribute('data-motion-clock'),stopped);
  await page.click('#quarter');await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:join(out,'art-polished-mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.ok(requests.every(u=>u.startsWith('http://127.0.0.1:8497/')),'no external services/credentials');
  assert.ok(!requests.some(u=>u.includes('/api/')),'art sample must not touch room state');
  const fallback=await browser.newPage();await fallback.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...rest){return type.startsWith('webgl')?null:get.call(this,type,...rest)}});
  await fallback.goto(base);await fallback.waitForFunction(()=>!document.querySelector('#fallback').hidden);
  assert.ok(await fallback.locator('#polished').isDisabled());assert.equal(errors.length,0,errors.join('\n'));
  writeFileSync(join(out,'art-metrics.json'),JSON.stringify(evidence,null,2));
  console.log('Art A/B, rendered budgets, desktop/mobile, reduced motion, no external/API requests and WebGL fallback passed.',evidence);
}finally{await browser?.close();server.kill();}
