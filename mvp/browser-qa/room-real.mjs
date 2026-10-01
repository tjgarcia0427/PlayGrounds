// Real HTTP/auth/state integration; synthetic participants, no mocked API routes.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {randomBytes} from 'node:crypto';
const chrome=process.env.CHROME_PATH;
assert.ok(chrome&&existsSync(chrome),'Explicit Google Chrome path required');
assert.ok(process.env.ROOM_BACKEND_ROOT,'Pinned room backend required');
const base='http://127.0.0.1:8496', temp=mkdtempSync(join(tmpdir(),'pg-real-ui-'));
const operator=randomBytes(24).toString('hex'), secrets=[operator], errors=[], urls=[], assetFailures=[];
const server=spawn('python3',['mvp/browser-qa/room_backend.py'],{env:{...process.env,PLAYGROUNDS_STATE_PATH:join(temp,'state.json'),PLAYGROUNDS_PORT:'8496',PLAYGROUNDS_OPERATOR_TOKEN:operator},stdio:'ignore'});
let browser;
const output=resolve('mvp/browser-qa/artifacts');mkdirSync(output,{recursive:true});
async function api(path,token,body){return fetch(base+path,{method:body?'POST':'GET',signal:AbortSignal.timeout(10000),headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});}
async function json(path,token,body){const r=await api(path,token,body);assert.ok(r.ok,`API ${path}: ${r.status}`);return r.json();}
async function label(page){await page.evaluate(()=>{const p=document.createElement('p');p.textContent='QA — synthetic participants on isolated real backend, not live users';p.style.cssText='background:#fff0c9;color:#53432d;padding:12px;margin:0';document.body.prepend(p);});}
async function saved(page){await page.waitForSelector('#newRoomKey');const token=await page.inputValue('#newRoomKey');secrets.push(token);await page.check('#savedKey');await page.click('#dialogSubmit');await page.waitForSelector('#newRoomKey',{state:'detached'});return token;}
try {
  let ready=false;for(let i=0;i<80;i++){try{if((await fetch(base)).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}assert.ok(ready,'backend readiness');
  assert.equal((await api('/api/rooms')).status,403,'directory operator-gated');
  browser=await chromium.launch({executablePath:chrome,headless:true,chromiumSandbox:true});
  const ownerContext=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const memberContext=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
  const owner=await ownerContext.newPage(),member=await memberContext.newPage();
  for(const p of [owner,member]){p.setDefaultTimeout(15000);p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>urls.push(r.url()));p.on('response',r=>{if(new URL(r.url()).pathname.startsWith('/assets/')&&!r.ok())assetFailures.push(new URL(r.url()).pathname+':'+r.status());});}
  console.log('QA stage: open operator shell');await owner.goto(base);await label(owner);
  await owner.click('#operatorConnect');await owner.fill('#operatorKey',operator);await owner.click('#dialogSubmit');
  await owner.waitForSelector('#operatorKey',{state:'detached'});
  console.log('QA stage: create room');await owner.click('#createRoom');await owner.fill('#roomName','QA real garden');await owner.click('#dialogSubmit');const ownerKey=await saved(owner);
  await owner.waitForFunction(()=>window.RoomUI.current?.name==='QA real garden');
  const rid=await owner.evaluate(()=>window.RoomUI.current.id);
  const room=await json(`/api/rooms/${rid}`,ownerKey);
  const goal=await json(`/api/rooms/${rid}/goals`,ownerKey,{title:'Private real integration goal',budget:20,agent_id:room.caller_agent_id});
  await owner.waitForFunction(()=>document.getElementById('goalTitle').textContent.includes('Private real integration goal'));
  console.log('QA stage: private goal rendered');const invitationUI=await owner.getByRole('button',{name:'Invite companions',exact:true}).count();
  let invite;
  if(invitationUI){
    await owner.getByRole('button',{name:'Invite companions',exact:true}).click();await owner.getByRole('button',{name:'+ Create invitation',exact:true}).click();
    await owner.fill('#inviteLabel','Real member invitation');await owner.click('#dialogSubmit');await owner.waitForSelector('#inviteSecret');
    invite={token:await owner.inputValue('#inviteSecret')};await owner.locator('#dialogContent input[type=checkbox]').check();await owner.click('#dialogSubmit');
  }else invite=await json(`/api/rooms/${rid}/invites`,ownerKey,{label:'Real member invitation'});
  secrets.push(invite.token);
  console.log('QA stage: member joins');await member.goto(base);await label(member);await member.locator('#roomTools > summary').click();await member.click('#joinRoom');await member.fill('#joinRoomId',rid);await member.fill('#inviteKey',invite.token);await member.fill('#joinName','QA real companion');await member.click('#dialogSubmit');const memberKey=await saved(member);
  await member.waitForFunction(()=>document.getElementById('goalTitle').textContent.includes('Private real integration goal'));
  assert.equal((await api(`/api/rooms/${rid}/join`,null,{invite_token:invite.token,name:'Reuse'})).status,410,'single-use enforced');
  console.log('QA stage: member sees private goal');const memberInfo=await json(`/api/rooms/${rid}`,memberKey);
  assert.equal(await member.getByRole('button',{name:'Invite companions',exact:true}).count(),0,'no owner controls for member');
  assert.equal((await api(`/api/rooms/${rid}/invites`,memberKey)).status,403,'owner-only API');
  const other=await json('/api/rooms',operator,{name:'QA other room',space:'playground'});secrets.push(other.token);
  assert.equal((await api(`/api/rooms/${other.room.id}/state`,memberKey)).status,401,'cross-room token denied');
  const lobby=await json('/api/state',operator);assert.ok(!JSON.stringify(lobby).includes('Private real integration goal'));
  const privateState=await json(`/api/rooms/${rid}/state`,memberKey);assert.ok(!('rooms' in privateState)&&!('auth' in privateState));
  if(invitationUI){
    await owner.getByRole('button',{name:'Invite companions',exact:true}).click();await owner.waitForFunction(()=>document.getElementById('inviteList').textContent.includes('Used'));await owner.click('#dialogCancel');
    const rev=await json(`/api/rooms/${rid}/invites`,ownerKey,{label:'Revoke in real UI'});secrets.push(rev.token);
    await owner.getByRole('button',{name:'Invite companions',exact:true}).click();await owner.getByRole('button',{name:'Revoke',exact:true}).click();await owner.waitForFunction(()=>document.getElementById('inviteList').textContent.includes('Revoked'));await owner.click('#dialogCancel');
    assert.equal((await api(`/api/rooms/${rid}/join`,null,{invite_token:rev.token,name:'Revoked'})).status,403);
  }
  console.log('QA stage: authenticated workboard lifecycle');
  const limits=(await json(`/api/rooms/${rid}/world`,memberKey)).limits;
  assert.ok((await member.locator('#agentcap').textContent()).includes(`up to ${limits.classroom_per_goal} per Study Hall goal`),'room capacity matches authoritative world');
  const task=await json(`/api/rooms/${rid}/goals/${goal.id}/tasks`,ownerKey,{title:'Private room board acceptance',bounty:10});
  await json(`/api/rooms/${rid}/tasks/${task.id}/claim`,memberKey,{agent_id:memberInfo.caller_agent_id});
  await owner.click('#classTab');await member.click('#classTab');
  for(const p of [owner,member])await p.waitForFunction(()=>document.querySelector('#workboard').textContent.includes('Private room board acceptance'));
  await json(`/api/rooms/${rid}/tasks/${task.id}/progress`,memberKey,{agent_id:memberInfo.caller_agent_id,note:'Authenticated checkpoint',progress_pct:.5});
  for(const p of [owner,member])await p.waitForFunction(()=>document.querySelector('#workboard progress')?.value===50);
  await json(`/api/rooms/${rid}/tasks/${task.id}/complete`,memberKey,{agent_id:memberInfo.caller_agent_id,result:'Room board verified'});
  await owner.waitForFunction(()=>document.querySelector('#workboard').textContent.includes('pending verification'));
  await json(`/api/rooms/${rid}/tasks/${task.id}/verify`,ownerKey,{approved:true,verifier_agent_id:room.caller_agent_id});
  for(const p of [owner,member])await p.waitForFunction(()=>document.querySelector('#workboard').textContent.includes('9.00 credits earned'));
  console.log('QA stage: screenshots');for(const [page,name] of [[owner,'desktop'],[member,'mobile']]){
    await page.waitForFunction(()=>document.getElementById('renderStatus').textContent.includes('3D campus'));
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal overflow');
    await page.screenshot({path:join(output,`ui-real-${name}.png`),fullPage:true});
  }
  console.log('QA stage: revoke access');await json(`/api/rooms/${rid}/members/${memberInfo.caller_agent_id}/remove`,ownerKey,{});
  await member.evaluate(()=>window.refresh());
  await member.waitForFunction(()=>!document.getElementById('goalTitle').textContent.includes('Private real integration goal'));
  assert.equal((await api(`/api/rooms/${rid}/state`,memberKey)).status,401);
  assert.ok(!(await member.locator('#workboard').textContent()).includes('Private room board acceptance'),'revocation clears board');
  await owner.reload();assert.equal(await owner.evaluate(()=>window.RoomUI.current),null,'reload forgets room');
  for(const p of [owner,member]){const storage=await p.evaluate(()=>JSON.stringify([localStorage,sessionStorage]));for(const secret of secrets)assert.ok(!storage.includes(secret),'no persistent credentials');}
  for(const secret of secrets)assert.ok(urls.every(u=>!u.includes(secret)),'no credentials in URLs');
  assert.deepEqual(assetFailures,[],'all UI assets must load');assert.deepEqual(errors,[]);
  console.log('Real backend UI: operator/create/join/auth boundaries, one-time keys, isolation, revocation clearing, reload and responsive checks passed; invitation UI:',Boolean(invitationUI));
}finally{await browser?.close();server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));}
