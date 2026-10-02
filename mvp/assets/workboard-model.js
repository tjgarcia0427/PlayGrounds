// Read-only projection of server state. No inferred work, queues or payouts.
const number=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const active=new Set(['claimed','pending_verification','needs_input']);
export function workboard(state={},world={},goalId=null,openedAt=0,now=Date.now()/1000){
 const all=Object.values(state.tasks||{}),tasks=all.filter(t=>!goalId||t.goal_id===goalId);
 const people=world.agents||[],presence=new Map(people.map(a=>[a.id,a]));
 const cap=number(world.limits?.classroom_per_goal)??number(state.policy?.classroom_agents_per_goal);
 const seated=people.filter(a=>a.presence?.space==='classroom'&&a.presence.goal_id===goalId).length;
 const participants=new Set(people.filter(a=>a.presence?.goal_id===goalId).map(a=>a.id));
 for(const t of tasks){if(t.agent_id)participants.add(t.agent_id);if(t.verification_receipt?.verifier?.id)participants.add(t.verification_receipt.verifier.id);for(const id of Object.keys(t.settlement_receipt?.payouts||{}))participants.add(id);}
 const cards=Object.values(state.agents||{}).filter(a=>!goalId||participants.has(a.id)).sort((a,b)=>String(a.name).localeCompare(String(b.name))||a.id.localeCompare(b.id)).map(a=>{
  const p=presence.get(a.id),heartbeat=number(p?.last_heartbeat??a.last_heartbeat);
  const assigned=tasks.filter(t=>t.agent_id===a.id&&active.has(t.status)).map(t=>{
   const checkpoints=(t.progress||[]).slice(-3).map(c=>({note:String(c.note||''),at:number(c.at),percent:number(c.progress_pct)===null?null:Math.round(Math.max(0,Math.min(1,c.progress_pct))*100)}));
   const expiry=number(t.lease?.expires??t.claim_expires),holder=t.lease?.holder;
   return {id:t.id,title:String(t.title||'Untitled task'),status:t.status,checkpoints,expiry,
    lease:t.status!=='claimed'?'Not currently leased':holder&&holder!==a.id?'Lease holder differs — refresh required':!expiry?'Lease deadline unavailable':expiry<=now?'Deadline passed — awaiting server update':'Lease active'};
  });
  const reviews=tasks.filter(t=>t.verification_receipt&&(t.agent_id===a.id||t.verification_receipt.verifier?.id===a.id)).map(t=>({title:String(t.title||'Untitled task'),decision:String(t.verification_receipt.decision||'unknown'),at:number(t.verification_receipt.issued_at),role:t.verification_receipt.verifier?.id===a.id?'Reviewed':'Work reviewed'})).sort((a,b)=>(b.at||0)-(a.at||0)).slice(0,3);
  let earned=0;const seen=new Set();for(const t of tasks){const r=t.settlement_receipt,key=r?.settlement_id||t.id;if(!r||seen.has(key)||!(r.issued_at>=openedAt&&r.issued_at<=now))continue;seen.add(key);earned+=Math.max(0,number(r.payouts?.[a.id])||0);if(t.verification_receipt?.verifier?.id===a.id)earned+=Math.max(0,number(r.reviewer_paid)||0);}
  return {id:a.id,name:String(a.name||a.id),stale:heartbeat===null||now-heartbeat>90,heartbeat,activity:assigned.length?'Task assigned':p?.presence?.activity?.replaceAll('_',' ')||'No activity reported',tasks:assigned,reviews,earned:Math.round(earned*100)/100};
 });
 return {goal:goalId?String(state.goals?.[goalId]?.title||'Selected goal'):null,cap:cap>0?cap:null,seated,full:!!goalId&&cap>0&&seated>=cap,cards};
}
