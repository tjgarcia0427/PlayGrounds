import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
const chrome=process.env.CHROME_PATH;assert.ok(chrome&&existsSync(chrome),'Explicit Chrome required');
const output=resolve('mvp/browser-qa/artifacts/fur-study');mkdirSync(output,{recursive:true});
const server=spawn('python3',['-m','http.server','8498','--bind','127.0.0.1'],{stdio:'ignore'});
let browser;
try{
 for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:8498/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
 const page=await browser.newPage({viewport:{width:850,height:850}});page.setDefaultTimeout(60000);
 // External reference capture only; never use its assets in the prototype.
 console.log('Reference capture starting');
 const ref=await browser.newPage({viewport:{width:850,height:850}});
 try{
  await ref.goto('https://three-fur-test.vercel.app/',{waitUntil:'networkidle',timeout:45000});
  await ref.locator('#picker button').first().waitFor();
  await ref.screenshot({path:output+'/reference-default.png'});
  await ref.getByRole('button',{name:'Iggy',exact:true}).click();
  await ref.screenshot({path:output+'/reference-iggy.png'});
 }catch(e){writeFileSync(output+'/reference-error.txt',String(e)+'\n'+await ref.locator('body').innerText().catch(()=>''));await ref.screenshot({path:output+'/reference-unavailable.png',timeout:15000}).catch(()=>{});}finally{await ref.close();}
 console.log('Prototype capture starting');
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('http://127.0.0.1:8498/art/fur-study/');
 await page.waitForFunction(()=>window.furStudy?.ready&&window.furStudy.frames>3);
 await page.getByRole('button',{name:'Still mode'}).click();
 await page.waitForFunction(()=>window.furStudy.still);
 for(const name of['Peach','Sky','Lilac']){await page.getByRole('button',{name,exact:true}).click();await page.screenshot({path:output+'/'+name.toLowerCase()+'.png'});console.log('Captured',name);}
 await page.getByRole('button',{name:'Peach',exact:true}).click();
 await page.selectOption('#quality','16');
 await page.getByRole('button',{name:'Still mode'}).click();
 console.log('Squish/recovery at light LOD (same deformation shader)');
 await page.getByRole('button',{name:'Squish ✨',exact:true}).click();
 await page.waitForFunction(()=>window.furStudy.compression>.12);
 await page.screenshot({path:output+'/squish.png'});
 await page.waitForFunction(()=>Math.abs(window.furStudy.compression)<.002);
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>window.furStudy.still);
 const frozen=await page.evaluate(()=>window.furStudy.time);await page.getByRole('button',{name:'Squish ✨',exact:true}).click();
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.evaluate(()=>window.furStudy.time),frozen);
 assert.equal(await page.evaluate(()=>window.furStudy.compression),0);
 await page.selectOption('#quality','32');await page.waitForFunction(()=>window.furStudy.shells===32);
 await page.screenshot({path:output+'/balanced.png'});
 await page.setViewportSize({width:390,height:844});await page.selectOption('#quality','16');await page.waitForFunction(()=>window.furStudy.shells===16);
 await page.screenshot({path:output+'/mobile.png'});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 writeFileSync(output+'/metrics.json',JSON.stringify(await page.evaluate(()=>window.furStudy),null,2));
 assert.deepEqual(errors,[]);
 const fallback=await browser.newPage();await fallback.addInitScript(()=>{HTMLCanvasElement.prototype.getContext=function(){return null;};});await fallback.goto('http://127.0.0.1:8498/art/fur-study/');await fallback.locator('#fallback').waitFor({state:'visible'});await fallback.screenshot({path:output+'/fallback.png'});
 console.log('Fur study: shader render, palette controls, squish and recovery, reduced motion, LOD, mobile layout, fallback PASS');
}catch(e){console.error(e);throw e;}finally{server.kill();if(browser)await Promise.race([browser.close(),new Promise(r=>setTimeout(r,15000))]);}
