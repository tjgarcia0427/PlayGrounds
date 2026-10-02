import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {existsSync,mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
const chrome=process.env.CHROME_PATH;assert.ok(chrome&&existsSync(chrome),'Explicit Chrome required');
const output=resolve('mvp/browser-qa/artifacts/fur-study');mkdirSync(output,{recursive:true});
const server=spawn('python3',['-m','http.server','8498','--bind','127.0.0.1'],{stdio:'ignore'});
let browser;
try{
 for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:8498/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
 const page=await browser.newPage({viewport:{width:800,height:1000},reducedMotion:'reduce'});page.setDefaultTimeout(60000);
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('http://127.0.0.1:8498/art/fur-study/');await page.waitForFunction(()=>window.furStudy?.ready);
 const metrics=[],views=[['dot','headphones','Dot version · over-ear'],['dot','earbuds','Dot version · wired earbuds'],['rabbit','signature','Animal version · Rabbit'],['turtle','signature','Animal version · Turtle'],['monkey','signature','Animal version · Monkey'],['bird','signature','Animal version · Bird']];
 for(const [model,accessory,label] of views){
  await page.selectOption('#model',model);await page.selectOption('#accessory',accessory);
  await page.waitForFunction(([m,a])=>window.furStudy.model===m&&window.furStudy.accessory===a,[model,accessory]);
  const file=model==='dot'?`dot-${accessory}`:model;
  await page.locator('.stage').screenshot({path:`${output}/${file}.png`,timeout:60000});
  metrics.push({label,...await page.evaluate(()=>window.furStudy)});console.log('Captured',label);
 }
 // Also inspect the shell/tail/headphones from a genuine camera turn.
 await page.selectOption('#model','turtle');await page.locator('#turn').evaluate(el=>{el.value='35';el.dispatchEvent(new Event('input',{bubbles:true}));});
 await page.locator('.stage').screenshot({path:output+'/turtle-three-quarter.png'});
 await page.locator('#turn').evaluate(el=>{el.value='0';el.dispatchEvent(new Event('input',{bubbles:true}));});
 // Same spring and whole-character transform used by every design, at a cheaper LOD.
 await page.selectOption('#quality','16');await page.emulateMedia({reducedMotion:'no-preference'});await page.waitForFunction(()=>!window.furStudy.still);
 await page.getByRole('button',{name:'Squish ✨',exact:true}).click();await page.waitForFunction(()=>window.furStudy.compression>.12);
 await page.screenshot({path:output+'/squish.png'});await page.waitForFunction(()=>Math.abs(window.furStudy.compression)<.002);
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>window.furStudy.still);
 const frozen=await page.evaluate(()=>window.furStudy.time);await page.getByRole('button',{name:'Squish ✨',exact:true}).click();
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.evaluate(()=>window.furStudy.time),frozen);assert.equal(await page.evaluate(()=>window.furStudy.compression),0);
 // Tallest and widest silhouettes on mobile; projected conservative fur/accessory bounds.
 await page.setViewportSize({width:390,height:1000});
 for(const model of ['dot','rabbit','turtle','monkey','bird']){
  await page.selectOption('#model',model);await page.waitForFunction(m=>window.furStudy.viewportWidth===390&&window.furStudy.model===m,model);
  const f=await page.evaluate(()=>window.furStudy.framing);assert.ok(f[0]>-.95&&f[1]<.95&&f[2]<.95&&f[3]>-.95,`${model} envelope fits mobile`);
  await page.screenshot({path:`${output}/mobile-${model}.png`});
 }assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 assert.deepEqual(errors,[]);writeFileSync(output+'/metrics.json',JSON.stringify(metrics,null,2));
 // Presentation sheet from untouched browser captures (not synthetic/image-generated previews).
 const cards=views.map(([m,a,label])=>{const file=m==='dot'?`dot-${a}`:m;return `<article><img src="data:image/png;base64,${readFileSync(`${output}/${file}.png`).toString('base64')}"><h2>${label}</h2></article>`;}).join('');
 const sheet=await browser.newPage({viewport:{width:1500,height:1160}});
 await sheet.setContent(`<style>*{box-sizing:border-box}body{margin:0;background:#faf8fc;color:#514957;font:16px system-ui;padding:26px}h1{text-align:center;font-size:28px;margin:0 0 6px}p{text-align:center;margin:0 0 20px;color:#7d7585}section{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}article{background:white;border:1px solid #ede6ef;border-radius:22px;overflow:hidden;text-align:center}img{width:100%;height:440px;object-fit:contain}h2{font-size:18px;margin:0;padding:0 8px 18px}</style><h1>Dot version / Animal version</h1><p>PlayGrounds · same shader fur, lighting and camera scale · original synthetic character studies</p><section>${cards}</section>`);
 await sheet.evaluate(()=>Promise.all([...document.images].map(i=>i.decode())));await sheet.screenshot({path:output+'/comparison.png',fullPage:true});
 const fallback=await browser.newPage();await fallback.addInitScript(()=>{HTMLCanvasElement.prototype.getContext=function(){return null;};});await fallback.goto('http://127.0.0.1:8498/art/fur-study/');await fallback.locator('#fallback').waitFor({state:'visible'});await fallback.screenshot({path:output+'/fallback.png'});
 console.log('Six designs, comparison sheet, turned turtle, squish/recovery, reduced motion, five mobile fits, no errors, fallback PASS');
}catch(e){console.error(e);throw e;}finally{server.kill();if(browser)await Promise.race([browser.close(),new Promise(r=>setTimeout(r,15000))]);}
