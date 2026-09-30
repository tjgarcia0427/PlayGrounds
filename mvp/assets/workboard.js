import {workboard} from './workboard-model.js';
const host=document.getElementById('workboard');
const openedAt=Date.now()/1000;let snapshot=null,receivedAt=0,lastMarkup='';
const escape=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const time=t=>t?new Date(t*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}):'not recorded';
function render(){
 if(!host)return;
 if(!snapshot){host.innerHTML='<h2>Study Hall · now working</h2><p>Waiting for current room data.</p>';lastMarkup='';return;}
 const {state,world}=snapshot,selected=document.getElementById('goalSelect')?.value;
 const goal=selected&&state.goals?.[selected]?selected:Object.keys(state.goals||{})[0]||null;
 const board=workboard(state,world,goal,openedAt);
 const capacity=!board.goal?'Create or choose a goal to see its available places.':board.cap===null?'Capacity has not been reported by the server.':`${board.seated} / ${board.cap} places occupied · ${board.full?'Full — no automatic waitlist. Try again when a place opens.':`${Math.max(0,board.cap-board.seated)} available`}`;
 const html=`<header><div><p class="wb-eyebrow">Real activity · shared progress</p><h2>Study Hall · now working</h2><p>${escape(board.goal||'Your companions')}</p></div><p class="wb-updated">${window.PLAYGROUNDS_SNAPSHOT?'Offline snapshot':'Last received'} · ${escape(time(receivedAt))}</p></header><p class="wb-capacity" role="status">${escape(capacity)}</p><p class="wb-note">Progress is agent-reported. Credits below are recorded earnings for this goal since this tab opened; they are not money. Every relevant companion is listed, even if the 3D view reaches its display limit.</p><div class="wb-grid">${board.cards.map(a=>`<article class="wb-card" data-agent-id="${escape(a.id)}"><h3>${escape(a.name)}</h3><p class="wb-state ${a.stale?'wb-stale':''}">${a.stale?'Heartbeat stale · last known state':escape(a.activity)}</p><small>Heartbeat ${escape(time(a.heartbeat))}</small>${a.tasks.map(t=>`<div class="wb-task"><h4>${escape(t.title)}</h4><p>${escape(t.status.replaceAll('_',' '))} · ${escape(t.lease)}${t.status==='claimed'&&t.expiry?` · deadline ${escape(time(t.expiry))}`:''}</p>${t.checkpoints.length?`<ol>${t.checkpoints.map(c=>`<li>${escape(c.note||'Checkpoint recorded')} <small>${escape(time(c.at))}</small>${c.percent!==null?`<label>${c.percent}% reported<progress max="100" value="${c.percent}" aria-label="${escape(t.title)}: agent-reported progress"></progress></label>`:''}</li>`).join('')}</ol>`:'<p>No checkpoints reported yet.</p>'}</div>`).join('')||'<p>No active task in this goal.</p>'}<p class="wb-earned">${a.earned.toFixed(2)} credits earned</p><details><summary>Recent review receipts (${a.reviews.length})</summary>${a.reviews.map(r=>`<p>${escape(r.role)}: ${escape(r.title)} · ${escape(r.decision)} · ${escape(time(r.at))}</p>`).join('')||'<p>No matching retained receipts. This is not a complete review history.</p>'}</details></article>`).join('')||'<p class="wb-empty">No companions are working on this goal yet. Connected agents appear here when they join or contribute.</p>'}</div>`;
 if(html!==lastMarkup){const expanded=new Set([...host.querySelectorAll('details[open]')].map(d=>d.closest('article').dataset.agentId));const focused=document.activeElement?.closest?.('article')?.dataset.agentId;const summaryFocused=document.activeElement?.tagName==='SUMMARY';host.innerHTML=html;for(const card of host.querySelectorAll('article')){if(expanded.has(card.dataset.agentId))card.querySelector('details').open=true;if(summaryFocused&&focused===card.dataset.agentId)card.querySelector('summary').focus({preventScroll:true});}lastMarkup=html;}
}
function accept(detail){snapshot=detail;receivedAt=Date.now()/1000;render();}
window.addEventListener('playgrounds-world',e=>accept(e.detail));
window.addEventListener('playgrounds-workboard-clear',()=>{snapshot=null;render();});
document.getElementById('goalSelect')?.addEventListener('change',render);
if(globalThis.playgroundsWorldSnapshot)accept(globalThis.playgroundsWorldSnapshot);else render();
setInterval(render,10000);
