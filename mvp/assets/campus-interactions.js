import {walkPoint} from './campus-layout.js';
import {COFFEE,CAROUSEL_ENTRY} from './campus-navigation.js';
export const routeLength=path=>path.slice(1).reduce((n,p,i)=>n+Math.hypot(p.x-path[i].x,p.z-path[i].z),0);
const ease=t=>t*t*(3-2*t);
const mix=(a,b,t)=>({x:a.x+(b.x-a.x)*t,z:a.z+(b.z-a.z)*t,y:(a.y||0)+((b.y||0)-(a.y||0))*t});
export function ridePoint(angle){return {x:-6.4+Math.sin(angle)*.85,z:-2.8+Math.cos(angle)*.85,y:.4}}

// Local presentation only: no API, fetch, messages, timers or work-state writes.
export class InteractionDirector {
  constructor(route){this.route=route;this.clock=0;this.active=new Map();this.leases=new Map();this.due=new Map();this.completed={coffee:0,carousel:0};}
  start(actor) {
    if(!actor||actor.stale||actor.moving||this.active.has(actor.id))return false;
    const kind=actor.space==='classroom'?'coffee':'carousel';
    if(this.leases.has(kind))return false;
    const destination=kind==='coffee'?COFFEE:CAROUSEL_ENTRY,path=this.route(actor.target,destination);
    if(!path)return false;
    this.leases.set(kind,actor.id);
    this.active.set(actor.id,{kind,stage:'outbound',time:0,path,home:{...actor.target},position:{...actor.target},pose:'walk'});
    return true;
  }
  cancel(id) {
    const s=this.active.get(id);if(!s)return null;
    this.active.delete(id);this.leases.delete(s.kind);this.due.set(id,this.clock+30);
    // Platform interactions have an explicit exit before normal ground navigation.
    return {position:{...s.position},exit:s.kind==='carousel'&&['board','ride','unboard'].includes(s.stage)?{...CAROUSEL_ENTRY}:null};
  }
  tick(dt,actors,enabled,angle,automatic=true) {
    this.clock+=enabled?Math.max(0,dt):0;const output=new Map(),seen=new Set(actors.map(a=>a.id));
    for(const id of this.active.keys())if(!seen.has(id))this.cancel(id);
    for(const id of this.due.keys())if(!seen.has(id))this.due.delete(id);
    for(const actor of actors) {
      if(!enabled||actor.stale||actor.moving){if(this.cancel(actor.id))output.set(actor.id,{position:actor.target,pose:'idle',reset:true});continue}
      if(!this.due.has(actor.id))this.due.set(actor.id,this.clock+12+actor.seed%18);
      if(automatic&&!this.active.has(actor.id)&&this.clock>=this.due.get(actor.id)) {
        this.start(actor);this.due.set(actor.id,this.clock+35+actor.seed%20);
      }
      const s=this.active.get(actor.id);if(!s)continue;
      s.time+=dt;
      let duration=1,pose='idle',position=s.position;
      if(s.stage==='outbound'||s.stage==='return') {
        duration=Math.max(.2,routeLength(s.path)/1.8);const t=Math.min(1,s.time/duration);
        position=walkPoint(s.path,t);pose='walk';
      } else if(s.stage==='serve'){duration=2;pose='reach';}
      else if(s.stage==='sip'){duration=3;pose='sip';}
      else if(s.stage==='board'){duration=1.2;position=mix(CAROUSEL_ENTRY,ridePoint(angle),ease(Math.min(1,s.time/duration)));pose='ride';}
      else if(s.stage==='ride'){duration=6;position=ridePoint(angle);pose='ride';}
      else if(s.stage==='unboard'){duration=1.2;position=mix(s.exitStart,CAROUSEL_ENTRY,ease(Math.min(1,s.time/duration)));pose='walk';}
      s.position={...position};s.pose=pose;
      output.set(actor.id,{position:s.position,pose,stage:s.stage,kind:s.kind,mug:s.kind==='coffee'&&['sip','return'].includes(s.stage),angle:s.stage==='ride'?angle+Math.PI:undefined});
      if(s.time>=duration){
        s.time=0;
        if(s.stage==='outbound')s.stage=s.kind==='coffee'?'serve':'board';
        else if(s.stage==='serve')s.stage='sip';
        else if(s.stage==='board')s.stage='ride';
        else if(s.stage==='ride'){s.stage='unboard';s.exitStart={...position}}
        else if(s.stage==='sip'||s.stage==='unboard'){s.stage='return';s.path=[...s.path].reverse()}
        else if(s.stage==='return'){this.completed[s.kind]++;this.cancel(actor.id);output.set(actor.id,{position:s.home,pose:actor.space==='classroom'?'typing':'idle',finished:true})}
      }
    }
    return output;
  }
}
