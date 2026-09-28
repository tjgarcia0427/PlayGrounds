// Pure deterministic layout: render state never changes protocol state.
export const RENDER_LIMIT = 24;
export function hashId(id) {
  let h = 2166136261;
  for (const c of id) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return h >>> 0;
}
export function spot(space, index) {
  if (space === 'classroom') return {x: 3.1 + (index % 4) * 2.1, z: -2.3 + Math.floor(index / 4) * 1.35};
  return {x: -11 + (index % 6) * 1.6, z: .5 + Math.floor(index / 6) * 1.5};
}
export function travelPath(from, to, changedSpace) {
  // A central garden gate keeps cross-space travel out of the walls/desks.
  return changedSpace ? [from, {x:0,z:5.8}, {x:to.x,z:5.8}, to] : [from,to];
}
export function walkPoint(path, progress) {
  const lengths = path.slice(1).map((p,i)=>Math.hypot(p.x-path[i].x,p.z-path[i].z));
  const total = lengths.reduce((a,b)=>a+b,0);
  let remaining = Math.max(0,Math.min(1,progress))*total;
  for (let i=0;i<lengths.length;i++) {
    if (remaining<=lengths[i] || i===lengths.length-1) {
      const t=lengths[i] ? remaining/lengths[i] : 1;
      return {x:path[i].x+(path[i+1].x-path[i].x)*t,z:path[i].z+(path[i+1].z-path[i].z)*t};
    }
    remaining-=lengths[i];
  }
  return {...path[0]};
}
export function visualActivity(agent, now) {
  if(now-agent.last_heartbeat>90) return 'stale';
  return agent.presence.activity;
}
