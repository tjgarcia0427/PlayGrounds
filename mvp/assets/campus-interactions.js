import {CatmullRomCurve3,Vector3} from './vendor/three.module.js';
import {COFFEE,CAROUSEL_ENTRY,SLIDE_ENTRY,SLIDE_EXIT,MONKEY_ENTRY,MONKEY_EXIT} from './campus-navigation.js';
export const routeLength=path=>path.slice(1).reduce((n,p,i)=>n+Math.hypot(p.x-path[i].x,p.z-path[i].z,(p.y||0)-(path[i].y||0)),0);
const ease=t=>t*t*(3-2*t);
const mix=(a,b,t)=>({x:a.x+(b.x-a.x)*t,z:a.z+(b.z-a.z)*t,y:(a.y||0)+((b.y||0)-(a.y||0))*t});
export function walkSpatial(path,t) {
  if(t>=1)return {...path.at(-1)};
  let remaining=Math.max(0,t)*routeLength(path);
  for(let i=1;i<path.length;i++){const length=routeLength([path[i-1],path[i]]);if(remaining<=length)return mix(path[i-1],path[i],length?remaining/length:1);remaining-=length}
  return {...path.at(-1)};
}
export const SLIDE_CURVE=new CatmullRomCurve3([new Vector3(-10.5,1.65,-3.05),new Vector3(-10.5,1.3,-2.6),new Vector3(-10.5,.45,-1.5),new Vector3(-10.5,.2,-.75)]);
export function slidePoint(t){const p=SLIDE_CURVE.getPoint(Math.max(0,Math.min(1,t)));return {x:p.x,y:p.y+.12,z:p.z}}
export function ridePoint(angle){return {x:-6.4+Math.sin(angle)*.85,z:-2.8+Math.cos(angle)*.85,y:.4}}
export function blinkAmount(clock,seed,enabled=true){if(!enabled)return 1;const phase=(clock+seed%17*.37)%5.1;return phase<.18?1-.94*Math.sin(Math.PI*phase/.18):1}
const climbSlide=[SLIDE_ENTRY,{x:-10.5,y:0,z:-4.65},{x:-10.5,y:1.77,z:-4.2},{x:-10.5,y:1.77,z:-3.7},slidePoint(0)];
const monkeyStart={x:-2.9,y:.3,z:-4.8},monkeyEnd={x:-2.9,y:.3,z:-2};
const destinations={coffee:COFFEE,carousel:CAROUSEL_ENTRY,slide:SLIDE_ENTRY,monkey:MONKEY_ENTRY};
const exits={coffee:COFFEE,carousel:CAROUSEL_ENTRY,slide:SLIDE_EXIT,monkey:MONKEY_EXIT};

// Presentation only: no API, messages, timers or work-state writes.
export class InteractionDirector {
  constructor(route){this.route=route;this.clock=0;this.active=new Map();this.leases=new Map();this.due=new Map();this.visits=new Map();this.completed={coffee:0,carousel:0,slide:0,monkey:0};}
  start(actor,requested='auto') {
    if(!actor||actor.stale||actor.moving||this.active.has(actor.id))return false;
    const options=actor.space==='classroom'?['coffee']:['carousel','slide','monkey'];
    const visits=this.visits.get(actor.id)??actor.seed%options.length,kind=requested==='auto'?options[visits%options.length]:requested;
    if(!options.includes(kind)||this.leases.has(kind))return false;
    const path=this.route(actor.target,destinations[kind]),returnPath=this.route(exits[kind],actor.target);
    if(!path||!returnPath)return false;
    this.leases.set(kind,actor.id);this.visits.set(actor.id,visits+1);
    this.active.set(actor.id,{kind,stage:'outbound',time:0,path,returnPath,home:{...actor.target},position:{...actor.target},pose:'walk'});
    return true;
  }
  finishExit(id){for(const [kind,owner] of this.leases)if(owner===id&&!this.active.has(id))this.leases.delete(kind)}
  cancel(id,holdExit=false) {
    const s=this.active.get(id);if(!s)return null;
    let escape=null;
    if(s.kind==='carousel'&&['board','ride','unboard'].includes(s.stage))escape=[{...s.position},{...CAROUSEL_ENTRY}];
    if(s.kind==='slide'&&['climb','slide','land'].includes(s.stage)) {
      if(s.stage==='land')escape=[{...s.position},SLIDE_EXIT];
      else {
        const t=s.stage==='slide'?Math.pow(Math.min(1,s.time/2.4),1.35):0;
        escape=s.stage==='climb'?[{...s.position},...climbSlide.slice(1).filter(p=>p.y>=(s.position.y||0)&&p.z>=s.position.z)]:[{...s.position}];
        for(let i=0;i<=12;i++)escape.push(slidePoint(t+(1-t)*i/12));escape.push(SLIDE_EXIT);
      }
    }
    if(s.kind==='monkey'&&['mount','traverse','drop'].includes(s.stage))escape=[{...s.position},...(s.stage==='drop'?[]:[monkeyEnd]),MONKEY_EXIT];
    this.active.delete(id);this.due.set(id,this.clock+30);
    if(!holdExit||!escape)this.leases.delete(s.kind);
    return {position:{...s.position},exit:escape?.at(-1)||null,escape};
  }
  tick(dt,actors,enabled,angle,automatic=true) {
    this.clock+=enabled?Math.max(0,dt):0;const output=new Map(),seen=new Set(actors.map(a=>a.id));
    for(const id of this.active.keys())if(!seen.has(id))this.cancel(id);
    for(const map of [this.due,this.visits])for(const id of map.keys())if(!seen.has(id))map.delete(id);
    for(const [kind,id] of this.leases)if(!seen.has(id))this.leases.delete(kind);
    for(const actor of actors) {
      if(!enabled||actor.stale||actor.moving){if(this.cancel(actor.id))output.set(actor.id,{position:actor.target,pose:'idle',reset:true});continue}
      if(!this.due.has(actor.id))this.due.set(actor.id,this.clock+12+actor.seed%18);
      if(automatic&&!this.active.has(actor.id)&&this.clock>=this.due.get(actor.id)) {this.start(actor);this.due.set(actor.id,this.clock+35+actor.seed%20)}
      const s=this.active.get(actor.id);if(!s)continue;s.time+=dt;
      let duration=1,pose='idle',position=s.position,facing;
      if(s.stage==='outbound'||s.stage==='return') {
        duration=Math.max(.2,routeLength(s.path)/1.8);position=walkSpatial(s.path,Math.min(1,s.time/duration));pose='walk';
      } else if(s.stage==='serve'){duration=2;pose='reach';}
      else if(s.stage==='sip'){duration=3;pose='sip';}
      else if(s.stage==='board'){duration=1.2;position=mix(CAROUSEL_ENTRY,ridePoint(angle),ease(Math.min(1,s.time/duration)));pose='ride';}
      else if(s.stage==='ride'){duration=6;position=ridePoint(angle);pose='ride';facing=angle+Math.PI;}
      else if(s.stage==='unboard'){duration=1.2;position=mix(s.exitStart,CAROUSEL_ENTRY,ease(Math.min(1,s.time/duration)));pose='walk';}
      else if(s.stage==='climb'){duration=4;position=walkSpatial(climbSlide,ease(Math.min(1,s.time/duration)));pose='climb';facing=0;}
      else if(s.stage==='slide'){duration=2.4;position=slidePoint(Math.pow(Math.min(1,s.time/duration),1.35));pose='slide';facing=0;}
      else if(s.stage==='land'){duration=.8;position=mix(slidePoint(1),SLIDE_EXIT,ease(Math.min(1,s.time/duration)));pose='slide';facing=0;}
      else if(s.stage==='mount'){duration=1.2;position=mix(MONKEY_ENTRY,monkeyStart,ease(Math.min(1,s.time/duration)));pose='hang';facing=0;}
      else if(s.stage==='traverse'){duration=4.5;position=mix(monkeyStart,monkeyEnd,Math.min(1,s.time/duration));pose='hang';facing=0;}
      else if(s.stage==='drop'){duration=1;position=mix(monkeyEnd,MONKEY_EXIT,ease(Math.min(1,s.time/duration)));pose='hang';facing=0;}
      else if(s.stage==='cheer'){duration=1.5;pose='cheer';facing=0;}
      s.position={...position};s.pose=pose;
      output.set(actor.id,{position:s.position,pose,stage:s.stage,kind:s.kind,mug:s.kind==='coffee'&&['sip','return'].includes(s.stage),angle:facing});
      if(s.time>=duration){
        s.time=0;
        if(s.stage==='outbound')s.stage={coffee:'serve',carousel:'board',slide:'climb',monkey:'mount'}[s.kind];
        else if(s.stage==='serve')s.stage='sip';
        else if(s.stage==='board')s.stage='ride';
        else if(s.stage==='ride'){s.stage='unboard';s.exitStart={...position}}
        else if(s.stage==='climb')s.stage='slide';
        else if(s.stage==='slide')s.stage='land';
        else if(s.stage==='mount')s.stage='traverse';
        else if(s.stage==='traverse')s.stage='drop';
        else if(s.stage==='land'||s.stage==='drop')s.stage='cheer';
        else if(['sip','unboard','cheer'].includes(s.stage)){s.stage='return';s.path=s.returnPath;}
        else if(s.stage==='return'){this.completed[s.kind]++;this.cancel(actor.id);output.set(actor.id,{position:s.home,pose:actor.space==='classroom'?'typing':'idle',finished:true})}
      }
    }
    return output;
  }
}
