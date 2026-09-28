import assert from 'node:assert/strict';
import {hashId,spot,travelPath,walkPoint,visualActivity,RENDER_LIMIT} from './assets/campus-layout.js';
assert.equal(hashId('agent'),hashId('agent'));
assert.notEqual(hashId('agent'),hashId('other'));
for(const space of ['classroom','playground']) {
  const positions=Array.from({length:RENDER_LIMIT},(_,i)=>spot(space,i));
  assert.equal(new Set(positions.map(p=>`${p.x},${p.z}`)).size,RENDER_LIMIT);
  for(const p of positions)assert.ok(space==='classroom'?p.x>0:p.x<0);
}
const from=spot('playground',0),to=spot('classroom',0),path=travelPath(from,to,true);
assert.deepEqual(walkPoint(path,0),from);
assert.deepEqual(walkPoint(path,1),to);
assert.ok(path.some(p=>p.x===0 && p.z===5.8));
assert.ok(path.some(p=>p.x===to.x-.95 && p.z===to.z));
for(let t=0;t<=1;t+=.01) {const p=walkPoint(path,t);assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.z))}
assert.equal(visualActivity({last_heartbeat:0,presence:{activity:'working'}},100),'stale');
assert.equal(visualActivity({last_heartbeat:99,presence:{activity:'working'}},100),'working');
console.log('3D deterministic identity, bounded layout, gate traversal, endpoints and stale-state tests passed.');
