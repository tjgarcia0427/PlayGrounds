import assert from 'node:assert/strict';
import {ambientPose,animateCharacter} from './assets/campus-animation.js';
import {Group} from './assets/vendor/three.module.js';
for(let seed=0;seed<64;seed++){
 const poses=new Set(),work=new Set();
 for(let t=0;t<32;t+=.1){
  poses.add(ambientPose('playground','socializing',t,seed));
  work.add(ambientPose('classroom','working',t,seed));
  assert.equal(ambientPose('classroom','stale',t,seed),'idle');
  assert.equal(ambientPose('classroom','idle',t,seed),'read');
 }
 for(const pose of ['idle','wave','lookAround','headphones'])assert.ok(poses.has(pose));
 for(const pose of ['typing','read','stretch','seatedHeadphones'])assert.ok(work.has(pose));
}
const root=new Group();
for(const name of ['Head','Body','LeftArm','RightArm','LeftFoot','RightFoot']){const g=new Group();g.name=name;root.add(g)}
const rig=animateCharacter(root),body=root.getObjectByName('Body'),arm=root.getObjectByName('RightArm'),head=root.getObjectByName('Head');
for(let i=0;i<100;i++)rig.update('typing',.02);
let last=arm.rotation.x;
for(let i=0;i<100;i++){
 rig.update('seatedHeadphones',.02);
 assert.ok(body.position.y>.2,'headphone adjustment must not drop seated character');
 assert.ok(Math.abs(arm.rotation.x-last)<.25,'arm blends without a snap');last=arm.rotation.x;
}
assert.ok(arm.rotation.x<-2.5,'hand rises toward ear');
// Authoritative travel can interrupt at any point without retaining a raised arm.
for(let i=0;i<60;i++)rig.update('walk',.02);
assert.ok(Math.abs(arm.rotation.x)<.6);assert.ok(body.position.y<.1);
let turned=false;
for(let i=0;i<220;i++){rig.update('lookAround',.02);turned ||= Math.abs(head.rotation.y)>.16}
assert.ok(turned,'visible head turn');
rig.update('lookAround',0,true);
const before=[head.rotation.y,arm.rotation.x,body.position.y];
for(let i=0;i<100;i++)rig.update('lookAround',.1,true);
assert.deepEqual([head.rotation.y,arm.rotation.x,body.position.y],before,'still pose is stable');
assert.deepEqual(root.position.toArray(),[0,0,0],'clips cannot move navigation root');
rig.dispose();console.log('Personality: 64 schedules, seated support, blending, travel interruption, visible turns, root isolation and still mode passed.');
