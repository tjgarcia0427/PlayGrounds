import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {existsSync,readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../../',import.meta.url)),chrome=process.env.CHROME_PATH;
assert(chrome&&existsSync(chrome),'Set CHROME_PATH to an explicit installed Google Chrome binary');
const out=path.join(root,'mvp/browser-qa/artifacts/blender-kit');mkdirSync(out,{recursive:true});
const manifest=JSON.parse(readFileSync(path.join(root,'art/blender/kit/manifest.json')));
// Isolated static repository fixture on loopback; no production backend or state.
const server=spawn('python3',['-u','-m','http.server','8769','--bind','127.0.0.1','--directory',root],{stdio:['ignore','pipe','pipe']});
let logs='';server.stderr.on('data',d=>{logs=(logs+d).slice(-5000);});
let browser;const base='http://127.0.0.1:8769/art/blender/kit/viewer/';const errors=[],metrics=[];
try{
 let ok=false;for(let i=0;i<60;i++){try{if((await fetch(base)).ok){ok=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}assert(ok,'Fixture did not start: '+logs);
 browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
 const page=await browser.newPage({viewport:{width:1360,height:1060}});page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(30000);
 await page.goto(base);await page.waitForFunction(()=>window.assetQA?.ready);
 for(const group of ['character','playground','study-hall']){
   await page.locator(`[data-group="${group}"]`).click();await page.waitForFunction(g=>window.assetQA.ready&&window.assetQA.group===g,group);
   await page.screenshot({path:path.join(out,group+'-collection.png'),fullPage:true});
   for(const a of manifest.assets.filter(a=>a.kind===group)){
     await page.locator(`[data-id="${a.id}"]`).click();await page.waitForFunction(id=>window.assetQA.ready&&window.assetQA.ids.length===1&&window.assetQA.ids[0]===id,a.id);
     await page.waitForFunction(()=>window.assetQA.drawCalls>0&&window.assetQA.poses.length===1);
     const before=await page.evaluate(()=>structuredClone(window.assetQA));assert.equal(before.error,null,a.id);assert(before.drawCalls<40,`${a.id} excessive draws ${before.drawCalls}`);
     metrics.push({id:a.id,drawCalls:before.drawCalls,triangles:a.triangles,bytes:a.bytes});
     await page.screenshot({path:path.join(out,a.id+'.png'),fullPage:true});
     if(a.kind==='character'){
       await page.waitForFunction(old=>JSON.stringify(window.assetQA.poses[0].head)!==JSON.stringify(old.head)&&JSON.stringify(window.assetQA.poses[0].tail)!==JSON.stringify(old.tail),before.poses[0]);
       await page.selectOption('#view','side');await page.screenshot({path:path.join(out,a.id+'-side.png'),fullPage:true});await page.selectOption('#view','quarter');
       await page.selectOption('#motion','wave');await page.waitForFunction(()=>Math.abs(window.assetQA.poses[0]?.arm?.[0]||0)>1.5);
       await page.selectOption('#motion','typing');await page.waitForFunction(()=>Math.abs(window.assetQA.poses[0]?.arm?.[0]||0)>.5);
       if(a.id==='peach-fox')await page.screenshot({path:path.join(out,'fox-campus-typing.png'),fullPage:true});
       await page.selectOption('#motion','study');
     }
     if(a.id==='merry-go-round')await page.waitForFunction(old=>JSON.stringify(window.assetQA.poses[0].deck)!==JSON.stringify(old),before.poses[0].deck);
     await page.locator('#still').check();const stopped=await page.evaluate(()=>JSON.stringify([window.assetQA.clock,window.assetQA.poses]));await page.waitForTimeout(350);assert.equal(await page.evaluate(()=>JSON.stringify([window.assetQA.clock,window.assetQA.poses])),stopped,a.id+' manual still changed');await page.locator('#still').uncheck();
   }
 }
 await page.locator('[data-group="character"]').click();await page.waitForFunction(()=>window.assetQA.ready&&window.assetQA.group==='character');
 await page.emulateMedia({reducedMotion:'reduce'});const stopped=await page.evaluate(()=>JSON.stringify([window.assetQA.clock,window.assetQA.poses]));await page.waitForTimeout(400);assert.equal(await page.evaluate(()=>JSON.stringify([window.assetQA.clock,window.assetQA.poses])),stopped,'OS reduced motion changed');
 await page.setViewportSize({width:390,height:844});
 for(const group of ['character','playground','study-hall']){
   await page.locator(`[data-group="${group}"]`).click();await page.waitForFunction(g=>window.assetQA.ready&&window.assetQA.group===g,group);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');await page.screenshot({path:path.join(out,group+'-mobile.png'),fullPage:true});
 }
 const fallback=await browser.newPage();await fallback.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/i.test(type)?null:original.call(this,type,...args);};});await fallback.goto(base);await fallback.locator('#fallback').waitFor({state:'visible'});await fallback.locator('[data-id="peach-fox"]').click();assert.equal(await fallback.locator('#downloads a').count(),2);await fallback.screenshot({path:path.join(out,'webgl-fallback.png'),fullPage:true});
 assert.deepEqual(errors,[]);writeFileSync(path.join(out,'metrics.json'),JSON.stringify({assets:metrics,scope:'Isolated synthetic GLB gallery; not live room/crowd/mobile hardware performance',checks:['22 GLBs rendered','6 exported head/tail studies','6 campus wave/typing bindings','carousel motion','22 manual still','OS reduced motion','3 mobile collections','WebGL fallback downloads']},null,2));
 console.log('BLENDER_KIT_CHROME_PASS',metrics.length);
}finally{await browser?.close();server.kill('SIGTERM');}
