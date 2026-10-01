import assert from 'node:assert/strict';
import {createArtKit,PLUSH_STYLES} from './assets/campus-art.js';
import {animateCharacter} from './assets/campus-animation.js';
const kit=createArtKit();let sharedDisposals=0;
for(const geo of kit.sharedGeometries)geo.addEventListener('dispose',()=>sharedDisposals++);
for(let seed=0;seed<6;seed++){
 const actor=kit.plush(seed),twin=kit.plush(seed),rig=animateCharacter(actor.root);
 assert.equal(actor.root.userData.artStyle,PLUSH_STYLES[seed].name);
 for(const name of ['Head','Body','LeftArm','RightArm','LeftFoot','RightFoot'])assert.ok(actor.root.getObjectByName(name));
 const materials=[];actor.root.traverse(o=>{if(o.material?.bumpMap)materials.push(o.material)});
 assert.ok(materials.length>0);assert.ok(materials.every(m=>m.bumpMap.image.data.length===128*128*4));
 assert.ok(materials.every(m=>m.bumpMap===materials[0].bumpMap),'shared fabric texture');
 for(const pose of ['typing','walk','wave','seatedHeadphones','climb','slide','hang','sip']){
  for(let i=0;i<60;i++)rig.update(pose,.02);
  actor.root.updateMatrixWorld(true);actor.root.traverse(o=>assert.ok(o.matrixWorld.elements.every(Number.isFinite)));
  assert.deepEqual(actor.root.position.toArray(),[0,0,0]);
 }
 rig.update('idle',0,true);actor.root.updateMatrixWorld(true);const state=actor.head.matrix.toArray();
 for(let i=0;i<20;i++)rig.update('idle',.1,true);
 actor.root.updateMatrixWorld(true);assert.deepEqual(actor.head.matrix.toArray(),state);
 rig.dispose();actor.dispose();twin.dispose();
}
assert.equal(sharedDisposals,0,'removing actors must not dispose geometry used by surviving actors');
console.log('Six plush rigs: all animation bindings, finite transforms, root isolation, shared bounded fabric texture, still mode and shared geometry lifetime passed.');
