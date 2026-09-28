import assert from 'node:assert/strict';
import {createNavigator,SLIDE_ENTRY,SLIDE_EXIT,MONKEY_ENTRY,MONKEY_EXIT,blocked} from './assets/campus-navigation.js';
import {InteractionDirector,SLIDE_CURVE,slidePoint,walkSpatial,routeLength,blinkAmount} from './assets/campus-interactions.js';
import {spot} from './assets/campus-layout.js';
const route=createNavigator(),actor={id:'playful',space:'playground',seed:9,target:spot('playground',0),moving:false,stale:false};
for(const p of [SLIDE_ENTRY,SLIDE_EXIT,MONKEY_ENTRY,MONKEY_EXIT])for(let i=0;i<24;i++) {
 const paths=[route(spot('playground',i),p),route(p,spot('playground',i))];
 for(const path of paths){assert.ok(path);for(let n=0;n<=100;n++)assert.ok(!blocked(walkSpatial(path,n/100)))}
}
for(let i=0;i<=100;i++){const t=i/100,p=slidePoint(t),surface=SLIDE_CURVE.getPoint(t);assert.ok(Math.abs(p.y-surface.y-.12)<1e-8);assert.equal(p.x,surface.x);assert.equal(p.z,surface.z)}
for(const kind of ['slide','monkey']) {
 const d=new InteractionDirector(route);assert.ok(d.start(actor,kind));assert.equal(d.start({...actor,id:'other'},kind),false);
 const stages=new Set();let finished=false,previous={...actor.target,y:0};
 for(let i=0;i<1200&&!finished;i++){
   const frame=d.tick(.05,[actor],true,i*.01,false).get(actor.id);assert.ok(frame);
   if(frame.stage)stages.add(frame.stage);
   const step=Math.hypot(frame.position.x-previous.x,frame.position.z-previous.z,(frame.position.y||0)-(previous.y||0));
   assert.ok(step<.35,`${kind} discontinuity: ${step}`);previous=frame.position;
   if(frame.finished){finished=true;assert.deepEqual(frame.position,actor.target)}
 }
 assert.ok(finished);assert.equal(d.completed[kind],1);assert.equal(d.leases.size,0);
 for(const phase of kind==='slide'?['outbound','climb','slide','land','cheer','return']:['outbound','mount','traverse','drop','cheer','return'])assert.ok(stages.has(phase));
 for(const phase of kind==='slide'?['climb','slide','land']:['mount','traverse','drop']) {
   const interrupted=new InteractionDirector(route);interrupted.start(actor,kind);
   for(let i=0;i<1200&&interrupted.active.get(actor.id)?.stage!==phase;i++)interrupted.tick(.05,[actor],true,0,false);
   interrupted.tick(.25,[actor],true,0,false);
   const stopped=interrupted.cancel(actor.id,true);assert.ok(stopped.escape?.length);assert.ok(route(stopped.exit,spot('classroom',0)));
   assert.equal(interrupted.leases.get(kind),actor.id,'hold reservation during equipment exit');
   assert.equal(interrupted.start({...actor,id:'other'},kind),false);
   interrupted.finishExit(actor.id);assert.ok(interrupted.start({...actor,id:'other'},kind));
   for(let i=0;i<=100;i++){const p=walkSpatial(stopped.escape,i/100);assert.ok(Number.isFinite(p.y||0)&&(p.y||0)>=0)}
 }
}
const varied=new InteractionDirector(route);for(const kind of ['carousel','slide','monkey','carousel']){assert.ok(varied.start(actor));assert.equal(varied.active.get(actor.id).kind,kind);varied.cancel(actor.id)}
assert.equal(varied.start({...actor,space:'classroom'},'slide'),false,'room-specific preview');
for(let t=0;t<20;t+=.02){assert.ok(blinkAmount(t,3)>=.06&&blinkAmount(t,3)<=1);assert.equal(blinkAmount(t,3,false),1)}
const path=[{x:0,y:0,z:0},{x:0,y:2,z:0},{x:2,y:2,z:0}];assert.equal(routeLength(path),4);assert.deepEqual(walkSpatial(path,.25),{x:0,y:1,z:0});
console.log('96 entry/exit pairs, matching slide geometry, continuous slide/monkey loops, all equipment interruption stages, held exit leases, rotating variety and reduced-motion blinks passed.');
