/* Owner-only invitation lifecycle. No token persistence, logging or URL embedding. */
(() => {
  const ui=window.RoomUI, $=id=>document.getElementById(id);
  let actionKey='';
  const date=value=>new Date(value*1000).toLocaleString();
  const status=invite=>invite.used?'Used':invite.revoked?'Revoked':invite.expires_at<=Date.now()/1000?'Expired':'Ready';
  const button=(label,handler,cls='')=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.className=cls;b.onclick=handler;return b;};
  async function manageInvites() {
    const scope=ui.scope(),room=ui.current;
    const box=ui.fields('<p>Single-use invitations make space for one new companion. Only you, the owner, can create or revoke them.</p><div id="inviteList" aria-live="polite">Loading invitations…</div>');
    ui.openDialog('Invite good company',box,null);
    box.prepend(button('＋ Create invitation',()=>mintInvite(scope),'primary'));
    try {
      const result=await ui.request('/api/invites',{},scope);
      if(!ui.isCurrent(scope)||!$('inviteList'))return;
      const list=$('inviteList');list.replaceChildren();
      const invites=result.invites || [];
      if(!invites.length)list.textContent='No invitations yet. Create one for someone you want to work with.';
      for(const invite of invites) {
        const row=document.createElement('div');row.className='invite-row';
        const description=document.createElement('div'),name=document.createElement('strong'),meta=document.createElement('small');
        name.textContent=invite.label || 'An open invitation';
        meta.textContent=`${status(invite)} · Created ${date(invite.created_at)} · Expires ${date(invite.expires_at)}`;
        description.append(name,meta);row.append(description);
        if(status(invite)==='Ready')row.append(button('Revoke',async e=>{
          const b=e.currentTarget;b.disabled=true;
          try {await ui.post(`/api/invites/${encodeURIComponent(invite.id)}/revoke`,{},scope);await manageInvites();}
          catch(error){$('dialogError').textContent=error.message;b.disabled=false;}
        }));
        list.append(row);
      }
    } catch(error) {if($('inviteList'))$('inviteList').textContent=error.message;}
  }
  function mintInvite(scope) {
    const content=ui.fields('<p>Choose who this is for and how long they have to join. Each invitation works once.</p><label>Label (optional)<input id="inviteLabel" maxlength="80" placeholder="For our next study session" autocomplete="off"></label><label>Expires after<select id="inviteTTL"><option value="3600">1 hour</option><option value="86400" selected>24 hours</option><option value="604800">7 days</option><option value="2592000">30 days</option><option value="60">1 minute</option></select></label>');
    ui.openDialog('Save a seat',content,async()=>{
      const data=await ui.post('/api/invites',{label:$('inviteLabel').value.trim(),ttl_seconds:Number($('inviteTTL').value)},scope);
      if(!ui.isCurrent(scope))return;
      showInvite(data,scope.id);
    },'Create invitation');
  }
  function showInvite(data,roomId) {
    const endpoint=data.join?.join_url || new URL(`/api/rooms/${encodeURIComponent(roomId)}/join`,location.origin).href;
    // Display/copy as text only: no clickable executable/credential URL.
    const url=new URL(endpoint), local=['127.0.0.1','localhost','[::1]'].includes(url.hostname);
    const block=`PlayGrounds invitation\nRoom ID: ${roomId}\nJoin endpoint (POST): ${endpoint}\nInvite token: ${data.token}\nExpires: ${date(data.expires_at)}\nOpen the dashboard and choose Join with invite. Single use; share privately.`;
    const content=ui.fields('<p id="inviteReachability"></p><p id="inviteExpiry"></p><label>Invitation token<input id="inviteSecret" type="password" readonly autocomplete="off" spellcheck="false"></label><button type="button" id="revealInvite">Show token</button><button type="button" id="copyInvite">Copy invitation</button><p id="inviteCopyStatus" role="status"></p><label class="check-row"><input type="checkbox" required> I saved this invitation. It will not be shown again.</label>');
    content.querySelector('#inviteReachability').textContent=local?'Localhost only — this invitation works on the server machine. It is not an internet link.':'This uses the server’s configured address. Reachability is not verified here; share only with the intended recipient.';
    content.querySelector('#inviteExpiry').textContent=`Expires ${date(data.expires_at)}. Use it once.`;
    content.querySelector('input').value=data.token;
    ui.openDialog('Your invitation is ready',content,()=>ui.closeDialog(),'Done');
    $('revealInvite').onclick=()=>{const input=$('inviteSecret');input.type=input.type==='password'?'text':'password';$('revealInvite').textContent=input.type==='password'?'Show token':'Hide token';};
    $('copyInvite').onclick=async()=>{try {await navigator.clipboard.writeText(block);$('inviteCopyStatus').textContent='Copied. Send this privately to its intended recipient.';}catch{$('inviteCopyStatus').textContent='Clipboard unavailable. Show the token and copy it manually with the room ID: '+roomId;}};
  }
  function confirmAction(title,description,path,scope,forget=false,confirmation='') {
    const content=ui.fields('<p></p>');content.querySelector('p').textContent=description;
    if(confirmation){const label=document.createElement('label');label.textContent='Type the room name to confirm';const input=document.createElement('input');input.id='confirmRoomName';input.required=true;input.autocomplete='off';label.append(input);content.append(label);}
    ui.openDialog(title,content,async()=>{
      if(confirmation&&$('confirmRoomName').value!==confirmation)throw new Error('The room name does not match. Nothing has changed.');
      await ui.post(path,{},scope);ui.closeDialog();
      if(forget){ui.forgetCurrent();await ui.loadDirectory();}else {await ui.updateMetadata(scope);dispatchEvent(new CustomEvent('playgrounds-members-rendered'));window.refresh();}
    },title);
    $('dialogSubmit').classList.add('danger');
  }
  function manageMembers() {
    const scope=ui.scope(),room=ui.current,content=ui.fields('<p>Removing a companion ends their access and releases their active task claims.</p>');
    for(const member of room.members){const row=document.createElement('div');row.className='invite-row';const name=document.createElement('strong');name.textContent=member.name;row.append(name);
      if(member.agent_id!==room.owner_agent_id)row.append(button('Remove',()=>confirmAction('Remove companion',`Remove ${member.name} from this room? Their room key will stop working.`,`/api/members/${encodeURIComponent(member.agent_id)}/remove`,scope)));
      else {const role=document.createElement('small');role.textContent='Owner';row.append(role);}content.append(row);
    }
    ui.openDialog('Care for your room',content,null);
    content.append(button('Delete room',()=>confirmAction('Delete room','This permanently deletes the room, its goals, messages and history. There is no undo.','/api/delete',scope,true,room.name),'danger'));
  }
  function renderActions() {
    const room=ui.current;if(!room){actionKey='';return;}
    const owner=room.caller_agent_id===room.owner_agent_id,key=room.id+':'+owner;
    if(actionKey===key && $('roomActions').childElementCount)return;actionKey=key;
    $('roomActions').replaceChildren();
    if(owner)$('roomActions').append(button('Invite companions',manageInvites,'primary'),button('Manage members',manageMembers));
    else $('roomActions').append(button('Leave room',()=>confirmAction('Leave room','Your key will stop working. To return, you will need a new invitation.','/api/leave',ui.scope(),true)));
  }
  addEventListener('playgrounds-members-rendered',renderActions);
  addEventListener('playgrounds-room-change',()=>{actionKey='';renderActions();});
})();
