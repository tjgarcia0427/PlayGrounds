import assert from 'node:assert/strict';
import {createNavigator,COFFEE,CAROUSEL_ENTRY,blocked} from './assets/campus-navigation.js';
import {spot,walkPoint} from './assets/campus-layout.js';
import {InteractionDirector,routeLength} from './assets/campus-interactions.js';
import {animateCharacter} from './assets/campus-animation.js';
import {Group} from './assets/vendor/three.module.js';
const route=createNavigator();
for(const space of ['classroom','playground'])for(let i=0;i<24;i++) {
 const home=spot(space,i),dest=space==='classroom'?COFFEE:CAROUSEL_ENTRY,path=route(home,dest);
 assert.ok(path,`${space} seat ${i} must have a route`);
 assert.deepEqual(path[0],home);assert.ok(Math.hypot(path.at(-1).x-dest.x,path.at(-1).z-dest.z)<.01);
 for(let n=0;n<=routeLength(path)*100;n++)assert.ok(!blocked(walkPoint(path,n/(routeLength(path)*100))),`${space} ${i} route clips furniture`);
 const cross=route(home,spot(space==='classroom'?'playground':'classroom',i));assert.ok(cross,'cross-space route');
 for(let n=0;n<=200;n++){const p=walkPoint(cross,n/200);assert.ok(!blocked(p));if(Math.abs(p.x)<.35)assert.ok(p.z>=5.25)}
}
assert.equal(route({x:4.6,z:7},COFFEE),null,'no traversal out of furniture');
assert.equal(route(COFFEE,{x:99,z:99}),null,'never accept partial routes');
const actor=(id,space,index=0)=>({id,space,seed:1,target:spot(space,index),stale:false,moving:false});
const a=actor('a','classroom'),b=actor('b','classroom',1),c=actor('c','playground');
const snapshot=JSON.stringify([a,b,c]),d=new InteractionDirector(route);
assert.ok(d.start(a));assert.equal(d.start(b),false,'coffee reservation exclusive');assert.ok(d.start(c),'independent equipment reservation');
const stages={coffee:new Set(),carousel:new Set()};let returnedCoffee=false,returnedCarousel=false;
for(let i=0;i<1000 && (!returnedCoffee||!returnedCarousel);i++) {
 const frames=d.tick(.1,[a,b,c],true,i*.022);
 for(const f of frames.values())if(f.kind)stages[f.kind].add(f.stage);
 if(d.completed.coffee) {returnedCoffee=true;assert.deepEqual(frames.get('a')?.position||a.target,a.target)}
 if(d.completed.carousel)returnedCarousel=true;
}
assert.ok(returnedCoffee&&returnedCarousel,'complete both interaction loops');
for(const phase of ['outbound','serve','sip','return'])assert.ok(stages.coffee.has(phase));
for(const phase of ['outbound','board','ride','unboard','return'])assert.ok(stages.carousel.has(phase));
assert.equal(JSON.stringify([a,b,c]),snapshot,'presentation must never mutate authoritative descriptors');
const q=new InteractionDirector(route);q.start(a);q.tick(.1,[{...a,stale:true}],true,0);assert.equal(q.leases.size,0);
q.start(a);q.tick(.1,[a],false,0);assert.equal(q.active.size,0);assert.equal(q.leases.size,0);
q.start(a);q.tick(.1,[],true,0);assert.equal(q.active.size,0,'departed agent releases slot');
q.start(a);assert.ok(q.cancel(a.id));assert.ok(q.start(b),'interruption releases slot immediately');
const root=new Group();for(const name of ['Body','LeftArm','RightArm','LeftFoot','RightFoot']){const g=new Group();g.name=name;root.add(g)}
const anim=animateCharacter(root);anim.update('typing',.1);for(let i=0;i<20;i++)anim.update('typing',.1);
const y=root.getObjectByName('Body').position.y;assert.ok(y>.2,'seated work pose active');anim.update('walk',.01);assert.ok(Math.abs(root.getObjectByName('Body').position.y-y)<.06,'pose transition blends instead of snapping');
anim.update('idle',0,true);const still=root.getObjectByName('Body').position.y;anim.update('idle',1,true);assert.equal(root.getObjectByName('Body').position.y,still);anim.dispose();
console.log('All 48 workstation/roster routes, furniture clearance, gate paths, complete coffee/carousel loops, leases, cancellation, state isolation, pose blending and still mode passed.');
