import assert from 'node:assert/strict';
import {CAMPUS,ANNEX_PROPS,spot,walkPoint} from './assets/campus-layout.js';
import {createNavigator,blocked} from './assets/campus-navigation.js';
import {routeLength} from './assets/campus-interactions.js';
const route=createNavigator();
assert.ok(CAMPUS.width*CAMPUS.depth/(13.4*16)>1.6);
const destinations=[{x:-14,z:4},{x:-14,z:9},{x:14,z:4},{x:14,z:9}];
let checked=0;
for(const space of ['classroom','playground'])for(let i=0;i<24;i++)for(const dest of destinations){
  const path=route(spot(space,i),dest);assert.ok(path,`${space} ${i} to extension ${JSON.stringify(dest)}`);
  assert.ok(Math.hypot(path.at(-1).x-dest.x,path.at(-1).z-dest.z)<.01);
  const samples=Math.ceil(routeLength(path)*100);
  for(let n=0;n<=samples;n++) {
    const p=walkPoint(path,n/samples);assert.ok(!blocked(p),JSON.stringify({space,i,dest,p,path}));
    if(Math.abs(p.x)<.35)assert.ok(p.z>=5.25&&p.z<=6.65,'only cross through gate');
  }
  checked++;
}
for(const p of ANNEX_PROPS)assert.equal(route({x:p.x,z:p.z},destinations[0]),null,'never walk through new furniture');
assert.equal(route({x:17,z:0},destinations[0]),null,'glass-wall margin');
console.log(`${checked} extension routes clear furniture and cross only at gate; floor expanded >60%.`);
