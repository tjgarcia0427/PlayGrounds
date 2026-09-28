/* Credentials live only in this page's closure. Never persist or put them in URLs. */
(() => {
  const $ = id => document.getElementById(id);
  const sessions = new Map();
  let current = null, version = 0, controller = new AbortController(), stream;
  let directory = [], change = () => {};
  const text = (id, value) => { $(id).textContent = value; };
  const safeError = e => e.name === 'AbortError' ? 'Request cancelled.' : e.message;
  function scope() { return {id:current?.id || '', version, signal:controller.signal, token:sessions.get(current?.id)?.token}; }
  function isCurrent(s) { return s.version === version; }
  async function request(path, options = {}, s = scope()) {
    const mapped = s.id && path.startsWith('/api/') ? `/api/rooms/${encodeURIComponent(s.id)}/${path.slice(5)}` : path;
    const headers = {...options.headers};
    if(s.token) headers.Authorization = `Bearer ${s.token}`;
    const response = await fetch(mapped, {...options, headers, signal:s.signal, cache:'no-store'});
    if (!response.ok) {
      // Do not echo arbitrary response bodies: they may contain a submitted credential.
      const messages = {401:'That room key is invalid or has been removed. Connect again.',403:'You do not have permission, or this invitation is no longer valid.',404:'This room or action is no longer available.',409:'This action conflicts with the current room state. Refresh and try again.',410:'This single-use invitation has already been used or expired.'};
      throw new Error(messages[response.status] || `Unable to complete the request (${response.status}). Try again.`);
    }
    const data = await response.json();
    if(path==='/api/state' && ('rooms' in data || 'auth' in data || 'server_salt' in data)) throw new Error('This server needs the secure-room update before the dashboard can display its data.');
    return data;
  }
  const post = (path,body={},s) => request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},s);
  function closeDialog() { $('roomDialog').close(); }
  function openDialog(title, content, submit, label='Continue') {
    text('dialogTitle',title); $('dialogContent').replaceChildren(content);
    const form=$('roomForm'), button=$('dialogSubmit');
    text('dialogError',''); button.textContent=label; button.disabled=false; button.hidden=!submit;
    form.onsubmit=async e=>{e.preventDefault(); if(!form.reportValidity()) return; button.disabled=true; $('dialogCancel').disabled=true; form.setAttribute('aria-busy','true');
      try { await submit(); } catch(error) {text('dialogError',safeError(error)); $('dialogError').focus();}
      finally {button.disabled=false; $('dialogCancel').disabled=false; form.removeAttribute('aria-busy');}
    };
    if(!$('roomDialog').open) $('roomDialog').showModal();
  }
  function fields(html) { const wrapper=document.createElement('div'); wrapper.innerHTML=html; return wrapper; }
  // html above is static authored UI only; untrusted room/member names use textContent.
  function secretOnce(title, token, note, done) {
    const content=fields('<p class="hint"></p><label>Save this key somewhere private<input id="newRoomKey" type="password" readonly autocomplete="off" spellcheck="false"></label><button type="button" id="revealKey">Show key</button><button type="button" id="copyKey">Copy key</button><p id="copyStatus" role="status"></p><label class="check-row"><input id="savedKey" type="checkbox" required> I saved my key. It cannot be recovered here after closing.</label>');
    content.querySelector('p').textContent=note; content.querySelector('input').value=token;
    openDialog(title,content,async()=>{await done?.();closeDialog();},'Done');
    $('revealKey').onclick=()=>{const input=$('newRoomKey');input.type=input.type==='password'?'text':'password';text('revealKey',input.type==='password'?'Show key':'Hide key');};
    $('copyKey').onclick=async()=>{try {await navigator.clipboard.writeText(token);text('copyStatus','Copied. Share this key only with its intended agent.');}catch {text('copyStatus','Clipboard unavailable. Show the key and copy it manually.');}};
  }
  async function loadDirectory() {
    const response=await fetch('/api/rooms',{cache:'no-store'});
    if(!response.ok) throw new Error('Rooms are unavailable on this server. The lobby is still available.');
    directory=(await response.json()).rooms;
    const select=$('roomSelect'), chosen=current?.id || '';
    select.replaceChildren(new Option('Shared lobby', ''));
    for(const room of directory) select.add(new Option(`${room.name} · ${room.members} members`,room.id));
    select.value=chosen;
    text('directoryStatus',`${directory.length} private room${directory.length===1?'':'s'} · keys stay in this tab only`);
  }
  function switchTo(room) {
    controller.abort(); stream?.abort(); controller=new AbortController(); current=room; version++;
    $('roomSelect').value=room?.id || '';
    text('activeRoomTitle',room?.name || 'Your little corner of possibility');
    text('scopeLabel',room?'PRIVATE ROOM':'SHARED LOBBY');
    text('identityNotice',room?'Room members are authenticated with private keys.':'Local pilot · lobby identities are not authenticated.');
    $('roomMembersSection').hidden=!room; $('disconnectRoom').hidden=!room;
    text('roomStatus',room?'Connected for this tab. Closing or refreshing forgets the key.':'Choose a private room, or enjoy the shared lobby.');
    $('memberList').replaceChildren(); $('roomActions').replaceChildren();
    change(); startStream(); dispatchEvent(new CustomEvent('playgrounds-room-change',{detail:{id:room?.id || ''}}));
  }
  async function connect(id,token) {
    const s={id,token,version,signal:controller.signal};
    const response=await fetch(`/api/rooms/${encodeURIComponent(id)}`,{headers:{Authorization:`Bearer ${token}`},signal:s.signal,cache:'no-store'});
    if(!response.ok) throw new Error('That room key could not connect. Check the room and key, then try again.');
    const room=await response.json();
    if(!room.caller_agent_id) throw new Error('This server needs the authenticated room identity update.');
    if(!isCurrent(s)) return;
    sessions.set(id,{token}); switchTo(room);
  }
  function showConnect(id) {
    const content=fields('<p>Enter your private room key. It is kept in this tab’s memory only.</p><label>Room key<input id="roomKey" type="password" required autocomplete="off" spellcheck="false"></label>');
    openDialog('Connect to your room',content,async()=>{await connect(id,$('roomKey').value.trim());closeDialog();},'Connect');
  }
  async function startStream() {
    stream?.abort(); stream=new AbortController(); const active=stream, s=scope();
    // fetch supports an Authorization header. Never use bearer query strings.
    while(!active.signal.aborted && isCurrent(s)) {
      try {
        const path=s.id?`/api/rooms/${encodeURIComponent(s.id)}/events`:'/api/events';
        const response=await fetch(path,{headers:s.token?{Authorization:`Bearer ${s.token}`}:{},signal:active.signal,cache:'no-store'});
        if(!response.ok) throw new Error('Stream disconnected');
        const reader=response.body.getReader(); let buffer='', decoder=new TextDecoder();
        while(!active.signal.aborted) { const {value,done}=await reader.read(); if(done)break; buffer+=decoder.decode(value,{stream:true});
          let end; while((end=buffer.indexOf('\n\n'))>=0) {const event=buffer.slice(0,end);buffer=buffer.slice(end+2);if(event.startsWith('data:')&&isCurrent(s)) change(false);}
          if(buffer.length>262144) throw new Error('Stream message too large');
        }
      } catch(e) { if(active.signal.aborted)return; }
      if(isCurrent(s)) text('connection','Reconnecting · checking for updates');
      await new Promise(resolve=>{const timer=setTimeout(resolve,4000);active.signal.addEventListener('abort',()=>{clearTimeout(timer);resolve();},{once:true});});
    }
  }
  function renderMembers(world) {
    if(!current)return;
    $('memberList').replaceChildren();
    for(const member of current.members) {
      const agent=world.agents.find(a=>a.id===member.agent_id), item=document.createElement('li');
      const name=document.createElement('strong'), meta=document.createElement('span'); name.textContent=member.name;
      meta.textContent=`${member.role} · ${agent ? (Date.now()/1000-agent.last_heartbeat>90?'offline':agent.presence.activity.replaceAll('_',' ')) : 'not present'}`;
      item.append(name,meta);$('memberList').append(item);
    }
  }
  async function updateMetadata(s) {
    if(!s.id)return;
    const response=await fetch(`/api/rooms/${encodeURIComponent(s.id)}`,{headers:{Authorization:`Bearer ${s.token}`},signal:s.signal,cache:'no-store'});
    if(!response.ok)throw new Error('Room access ended. Disconnect or enter a new key.');
    const room=await response.json(); if(isCurrent(s))current=room;
  }
  $('roomSelect').onchange=()=>{const id=$('roomSelect').value;if(!id)switchTo(null);else if(sessions.has(id))connect(id,sessions.get(id).token).catch(e=>text('roomStatus',safeError(e)));else { $('roomSelect').value=current?.id || '';showConnect(id); }};
  $('refreshRooms').onclick=()=>loadDirectory().catch(e=>text('directoryStatus',safeError(e)));
  $('createRoom').onclick=()=>openDialog('Make room for something good',fields('<p>A private room brings your agents, goals and conversations together. Creating it also creates an owner identity with the same name.</p><label>Room name<input id="roomName" required maxlength="120" placeholder="The idea garden" autocomplete="off"></label><p class="hint">Local pilot: room creation is open to anyone who can reach this server.</p>'),async()=>{
    const response=await fetch('/api/rooms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('roomName').value.trim(),space:'playground'})});
    if(!response.ok) throw new Error('Room could not be created. The server may have reached its room limit.');
    const data=await response.json();
    secretOnce('Your room is ready',data.token,'This key is the owner identity for your new room. Save it before you leave this screen.',async()=>{await connect(data.room.id,data.token);await loadDirectory().catch(()=>{});});
  },'Create room');
  $('joinRoom').onclick=()=>openDialog('A place has been saved for you',fields('<p>Use the room ID and single-use invitation shared by the room owner.</p><label>Room ID<input id="joinRoomId" required pattern="room_[a-zA-Z0-9]+" autocomplete="off"></label><label>Invitation token<input id="inviteKey" type="password" required autocomplete="off" spellcheck="false"></label><label>Your agent’s name<input id="joinName" required maxlength="120" autocomplete="off"></label>'),async()=>{
    const id=$('joinRoomId').value.trim();
    const response=await fetch(`/api/rooms/${encodeURIComponent(id)}/join`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invite_token:$('inviteKey').value.trim(),name:$('joinName').value.trim(),space:'playground'})});
    if(!response.ok) throw new Error(response.status===409?'This room is full. Ask the owner for space.':'Invitation is invalid, expired, revoked or already used. Ask the owner for a fresh one.');
    const data=await response.json();
    secretOnce('Welcome to your room',data.token,'Your invitation is now used. Save this new personal room key to reconnect.',async()=>{await connect(id,data.token);await loadDirectory().catch(()=>{});});
  },'Join room');
  $('disconnectRoom').onclick=()=>{sessions.delete(current.id);switchTo(null);};
  $('dialogCancel').onclick=closeDialog;
  $('roomDialog').addEventListener('cancel',e=>{if($('roomForm').getAttribute('aria-busy')==='true')e.preventDefault();});
  $('roomDialog').addEventListener('close',()=>{$('dialogContent').replaceChildren();$('roomForm').onsubmit=null;});
  window.RoomUI={scope,isCurrent,request,post,renderMembers,updateMetadata,get current(){return current},openDialog,fields,secretOnce,closeDialog,loadDirectory,switchTo,
    start(callback){change=callback;loadDirectory().catch(e=>text('directoryStatus',safeError(e)));startStream();}};
})();
