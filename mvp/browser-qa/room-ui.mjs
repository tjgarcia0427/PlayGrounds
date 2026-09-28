// UI contract fixtures, deliberately distinct from real-backend integration.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const chrome=process.env.CHROME_PATH;assert.ok(chrome&&existsSync(chrome),'Explicit Google Chrome path required');
const temp=mkdtempSync(join(tmpdir(),'playgrounds-ui-')),base='http://127.0.0.1:8495';
const server=spawn('python3',['mvp/server.py'],{env:{...process.env,PLAYGROUNDS_STATE_PATH:join(temp,'state.json'),PLAYGROUNDS_PORT:'8495'},stdio:'ignore'});
const output=resolve('mvp/browser-qa/artifacts');mkdirSync(output,{recursive:true});let browser;
try {
  let seed;for(let i=0;i<60;i++){try{const r=await fetch(base+'/api/state');seed=await r.json();break}catch{await new Promise(r=>setTimeout(r,100));}}
  assert.ok(seed,'server readiness');
  browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const page=await context.newPage(); const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  const rooms=[{id:'room_alpha',name:'The idea garden',members:[{agent_id:'agent_a',name:'Clover (QA)',role:'owner'}],caller_agent_id:'agent_a',owner_agent_id:'agent_a'}, {id:'room_beta',name:'<img src=x onerror=alert(1)>',members:[{agent_id:'agent_b',name:'Bramble (QA)',role:'member'}],caller_agent_id:'agent_b',owner_agent_id:'owner_other'}];
  let delayAlpha=false; const invites=[];
  await page.route('**/api/rooms**',async route=>{
    const request=route.request(),url=new URL(request.url()),parts=url.pathname.split('/').filter(Boolean),id=parts[2],action=parts[3];
    let data,status=200;
    if(parts.length===2){if(request.method()==='POST'){data={room:rooms[0],token:'QA_owner_key'};}else data={rooms:rooms.map(r=>({...r,members:r.members.length}))};}
    else {
      const room=rooms.find(r=>r.id===id);assert.ok(room);
      if(action==='join')data={room,token:'QA_member_key'};
      else if(!request.headers().authorization?.startsWith('Bearer QA_')){status=401;data={error:'Unauthorized'};}
      else if(!action)data=room;
      else if(action==='invites' && request.method()==='GET')data={invites:invites.map(({token,...i})=>i)};
      else if(action==='invites' && parts[5]==='revoke'){const inv=invites.find(i=>i.id===parts[4]);inv.revoked=true;data={ok:true};}
      else if(action==='invites' && request.method()==='POST'){const input=request.postDataJSON(),now=Date.now()/1000;const inv={id:'invite_'+invites.length,label:input.label,created_at:now,expires_at:now+input.ttl_seconds,used:false,revoked:false,token:'QA_invite_secret'};invites.push(inv);data={...inv,invite_id:inv.id};}
      else if(action==='state'){
        if(delayAlpha&&id==='room_alpha')await new Promise(r=>setTimeout(r,600));
        data={...structuredClone(seed),goals:{goal_qa:{id:'goal_qa',title:id==='room_alpha'?'Garden ideas':'Beta focus',budget:100,budget_available:100}},agents:{},tasks:{},events:[]};
      } else if(action==='world') data={agents:[],social_messages:[],authenticated:true};
      else if(action==='ledger')data={events:[],digest:'QA_fixture_digest'};
      else if(action==='messages')data={messages:[]};
      else if(action==='events'){await route.fulfill({status:200,contentType:'text/event-stream',body:': ping\n\n'});return;}
      else {status=404;data={error:'not found'};}
    }
    await route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
  });
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.getElementById('renderStatus').textContent.includes('3D campus'));
  await page.evaluate(()=>{const p=document.createElement('p');p.textContent='VISUAL QA — synthetic UI contract fixtures, not a live room';p.style.cssText='background:#fff0c9;padding:12px 24px;margin:0;color:#53432d;font-size:12px';document.body.prepend(p)});
  await page.click('#createRoom'); await page.fill('#roomName','The idea garden'); await page.click('#dialogSubmit');
  await page.waitForSelector('#newRoomKey');assert.equal(await page.inputValue('#newRoomKey'),'QA_owner_key');
  // Secret screenshots are never captured.
  await page.check('#savedKey');await page.click('#dialogSubmit');
  await page.waitForFunction(()=>document.getElementById('goalTitle').textContent.includes('Garden ideas'));
  assert.equal(await page.locator('#newRoomKey').count(),0);
  await page.screenshot({path:join(output,'ui-room-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Invite companions',exact:true}).click();
  await page.getByRole('button',{name:'+ Create invitation',exact:true}).click();
  await page.fill('#inviteLabel','Garden study group');await page.selectOption('#inviteTTL','3600');await page.click('#dialogSubmit');
  await page.waitForSelector('#inviteSecret');assert.equal(await page.inputValue('#inviteSecret'),'QA_invite_secret');
  assert.match(await page.textContent('#inviteReachability'),/Localhost only/);
  await page.locator('#dialogContent input[type=checkbox]').check();await page.click('#dialogSubmit');
  assert.equal(await page.locator('#inviteSecret').count(),0,'one-time invite screen is cleared');
  await page.getByRole('button',{name:'Invite companions',exact:true}).click();
  await page.getByRole('button',{name:'Revoke',exact:true}).click();await page.waitForFunction(()=>document.getElementById('inviteList').textContent.includes('Revoked'));
  invites.push({id:'invite_expired',label:'Last week',created_at:1,expires_at:2,used:false,revoked:false});
  invites.push({id:'invite_used',label:'Already joined',created_at:1,expires_at:2,used:true,revoked:false});
  await page.click('#dialogCancel');await page.getByRole('button',{name:'Invite companions',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('inviteList').textContent.includes('Expired'));
  assert.match(await page.textContent('#inviteList'),/Used/);
  await page.locator('#dialogTitle').evaluate(e=>{const p=document.createElement('p');p.textContent='Synthetic UI fixture — not a live invitation';e.after(p)});
  await page.screenshot({path:join(output,'ui-invites-desktop.png')});await page.click('#dialogCancel');
  await page.selectOption('#roomSelect','room_beta');await page.fill('#roomKey','bad');await page.click('#dialogSubmit');
  assert.match(await page.textContent('#dialogError'),/could not connect/);
  await page.fill('#roomKey','QA_member_key');await page.click('#dialogSubmit');
  await page.waitForFunction(()=>document.getElementById('goalTitle').textContent.includes('Beta focus'));
  assert.equal(await page.locator('#activeRoomTitle img').count(),0,'hostile room name stays text');
  assert.match(await page.textContent('#identityNotice'),/authenticated/);
  assert.equal(await page.getByRole('button',{name:'Invite companions',exact:true}).count(),0,'member has no owner controls');
  // An in-flight A response must never overwrite B after a quick switch.
  delayAlpha=true;await page.selectOption('#roomSelect','room_alpha');
  await page.waitForFunction(()=>document.getElementById('activeRoomTitle').textContent==='The idea garden');
  await page.selectOption('#roomSelect','room_beta');
  await page.waitForFunction(()=>document.getElementById('goalTitle').textContent.includes('Beta focus'));
  await page.waitForTimeout(700);assert.match(await page.textContent('#goalTitle'),/Beta focus/);
  await page.click('#createRoom');await page.fill('#roomName','Keyboard test');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.getElementById('roomDialog').contains(document.activeElement)),true);
  await page.keyboard.press('Escape');assert.equal(await page.locator('#roomDialog').isVisible(),false);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'createRoom');
  await page.selectOption('#roomSelect','');await page.waitForFunction(()=>!document.getElementById('roomMembersSection').offsetParent);
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  assert.ok(requests.every(url=>!url.includes('QA_owner_key')&&!url.includes('QA_member_key')&&!url.includes('QA_invite_secret')),'no bearer in URL');
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:join(output,'ui-mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'no mobile overflow');
  if(!await page.locator('#roomTools').evaluate(e=>e.open))await page.locator('#roomTools summary').click();
  await page.click('#createRoom');await page.locator('#dialogTitle').evaluate(e=>{const p=document.createElement('p');p.textContent='Synthetic UI fixture — not a live room';e.after(p)});await page.screenshot({path:join(output,'ui-create-mobile.png')});
  await page.keyboard.press('Escape');
  await page.reload({waitUntil:'domcontentloaded'});await page.selectOption('#roomSelect','room_alpha');
  assert.equal(await page.locator('#roomKey').isVisible(),true,'refresh forgets credentials');
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('Room UI contract: create/save key, auth failure, connect/switch/race isolation, escaped names, keyboard modal, mobile, in-memory credentials passed. Backend integration is separately required.');
} finally {await browser?.close();server.kill('SIGTERM');}
