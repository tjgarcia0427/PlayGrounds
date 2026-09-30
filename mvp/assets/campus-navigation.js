import {BufferGeometry,Float32BufferAttribute,Vector3} from './vendor/three.module.js';
import {Pathfinding} from './vendor/three-pathfinding.module.js';
import {spot,RENDER_LIMIT,CAMPUS,ANNEX_PROPS} from './campus-layout.js';

// Scene dimensions are shared with rendering; all desks reserve space even when hidden.
export const DESK={width:1.4,depth:.5,offset:-.72};
export const COFFEE={x:6.8,z:6.05};
export const CAROUSEL_ENTRY={x:-6.4,z:-.45};
export const SLIDE_ENTRY={x:-10.5,z:-5.5},SLIDE_EXIT={x:-10.5,z:.05};
export const MONKEY_ENTRY={x:-2.9,z:-5.5},MONKEY_EXIT={x:-2.9,z:-1.1};
export const RADIUS=.34;
export function obstacles() {
  const boxes=[];
  // three-pathfinding rounds zone vertices to hundredths. Round clearance
  // boxes outward first so a rounded corner cannot cut through furniture.
  const lower=n=>Math.floor(n*100)/100,upper=n=>Math.ceil(n*100)/100;
  const add=(x,z,w,d)=>boxes.push({minX:lower(x-w/2-RADIUS),maxX:upper(x+w/2+RADIUS),minZ:lower(z-d/2-RADIUS),maxZ:upper(z+d/2+RADIUS)});
  for(let i=0;i<RENDER_LIMIT;i++){const p=spot('classroom',i);add(p.x,p.z+DESK.offset,DESK.width,DESK.depth)}
  add(5.6,-4.75,3.4,1.15);add(8.9,-4.65,1.6,1.6);
  add(1.1,-5.2,1.25,.65);add(11.8,-5.2,.9,.9);
  add(11.8,1.4,1.55,2.55);add(11.25,3.6,1.3,1.3);
  add(4.6,7,3.5,.95);
  add(-11,3.4,2.1,2.1);add(-10.5,-2.8,1.5,4.3);
  add(-6.4,-2.8,3.2,3.2);add(-2.9,-3.4,1.6,3);
  add(-12,-5.7,1,1);add(-7,-6.6,1,1);add(-2,-6,1,1);
  for(const p of ANNEX_PROPS)add(p.x,p.z,p.w,p.d);
  for(const x of [-16.5,-12,-8,-4,4,8,12,16.5])add(x,10.3,.17,.17);
  // All crossing uses the gate, not the imaginary room-divider wall.
  boxes.push({minX:-.35,maxX:.35,minZ:-6.2,maxZ:5.25});
  boxes.push({minX:-.35,maxX:.35,minZ:6.65,maxZ:CAMPUS.maxZ+1});
  return boxes;
}
export function blocked(p,boxes=obstacles()) {
  return boxes.some(b=>p.x>b.minX+1e-5&&p.x<b.maxX-1e-5&&p.z>b.minZ+1e-5&&p.z<b.maxZ-1e-5);
}
export function createNavigator() {
  const boxes=obstacles(),bounds=CAMPUS;
  // Rectilinear navmesh derived from furniture bounds, not an approximate sparse waypoint list.
  const axis=(lo,hi,a,b)=>[...new Set([lo,hi,...boxes.flatMap(o=>[Math.max(lo,Math.min(hi,o[a])),Math.max(lo,Math.min(hi,o[b]))])])].sort((a,b)=>a-b);
  const xs=axis(bounds.minX,bounds.maxX,'minX','maxX'),zs=axis(bounds.minZ,bounds.maxZ,'minZ','maxZ'),vertices=[];
  for(let x=0;x<xs.length-1;x++)for(let z=0;z<zs.length-1;z++) {
    const l=xs[x],r=xs[x+1],t=zs[z],b=zs[z+1];
    if(blocked({x:(l+r)/2,z:(t+b)/2},boxes))continue;
    vertices.push(l,0,t,l,0,b,r,0,t, r,0,t,l,0,b,r,0,b);
  }
  const geometry=new BufferGeometry();geometry.setAttribute('position',new Float32BufferAttribute(vertices,3));
  const finder=new Pathfinding();finder.setZoneData('campus',Pathfinding.createZone(geometry,.0001));geometry.dispose();
  const inside=p=>p.x>=bounds.minX&&p.x<=bounds.maxX&&p.z>=bounds.minZ&&p.z<=bounds.maxZ&&!blocked(p,boxes);
  return (from,to)=>{
    if(!inside(from)||!inside(to))return null;
    if(Math.hypot(to.x-from.x,to.z-from.z)<.001)return [{...from},{...to}];
    const a=new Vector3(from.x,0,from.z),b=new Vector3(to.x,0,to.z),group=finder.getGroup('campus',a,true);
    if(group===null||group===undefined)return null;
    const path=finder.findPath(a,b,'campus',group);
    // Library may return a partial route. Never mistake that for arrival.
    if(!path?.length||path.at(-1).distanceTo(b)>.01)return null;
    return [{x:from.x,z:from.z},...path.map(p=>({x:p.x,z:p.z}))];
  };
}
