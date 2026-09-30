import * as THREE from './vendor/three.module.js';
import {createArtKit} from './campus-art.js';
import {hashId,spot,visualActivity,RENDER_LIMIT,CAMPUS,ANNEX_PROPS} from './campus-layout.js';

import {createNavigator,DESK} from './campus-navigation.js';
import {InteractionDirector,routeLength,walkSpatial,SLIDE_CURVE,blinkAmount} from './campus-interactions.js';
import {animateCharacter,ambientPose} from './campus-animation.js';

const host=document.getElementById('campus3d');
const status=document.getElementById('renderStatus');
const fallback=document.getElementById('worldStage');
const mode=document.getElementById('renderMode');
const reduce=matchMedia('(prefers-reduced-motion: reduce)');
let renderer;
try {
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
} catch(error) {
  status.textContent='3D unavailable — showing the accessible 2D world.';
  mode.value='2d'; mode.disabled=true;
}
if(renderer) buildCampus();

function buildCampus() {
  const scene=new THREE.Scene();
  scene.background=new THREE.Color('#f4dfd5');
  scene.fog=new THREE.Fog('#f4dfd5',45,85);
  const camera=new THREE.OrthographicCamera(-18,18,12,-12,.1,120);
  let orbit=.3, zoom=1, focus=-CAMPUS.roomCenter, room="playground", viewAspect=1, targetExtent=12, currentExtent=12;
  const follow=document.getElementById("followAgent");
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.0;
  renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.domElement.setAttribute('aria-label','3D toy garden and cutaway Study Hall; full agent details are available in the 2D view.');
  renderer.domElement.setAttribute('role','img');
  host.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight('#fff3e1','#96b7ba',1.7));
  const sun=new THREE.DirectionalLight('#fff0cf',2.3);
  sun.position.set(-10,22,14);sun.castShadow=true;
  sun.shadow.mapSize.set(1024,1024);
  Object.assign(sun.shadow.camera,{left:-25,right:25,top:20,bottom:-20,near:1,far:60});
  sun.shadow.normalBias=.06;scene.add(sun);
  const rim=new THREE.DirectionalLight('#d1d9ff',1.1);rim.position.set(15,10,-12);scene.add(rim);
  const route=createNavigator(),director=new InteractionDirector(route),art=createArtKit();
  let portrait=false;const portraitButton=document.getElementById('portraitView');
  const materials=new Map();
  function mat(color) {
    if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.88,metalness:0}));
    return materials.get(color);
  }
  // Shared low-poly geometries reduce allocations and keep the toy silhouette soft.
  const sphere=new THREE.SphereGeometry(1,12,10);
  const cube=art.rounded;
  const cylinder=new THREE.CylinderGeometry(1,1,1,16);
  function mesh(geometry,color,pos,scale,parent=scene) {
    const m=new THREE.Mesh(geometry,mat(color));m.position.set(...pos);m.scale.set(...scale);
    m.castShadow=Math.max(...scale)>.3;m.receiveShadow=true;parent.add(m);return m;
  }
  const ball=(color,pos,scale,parent)=>mesh(sphere,color,pos,scale,parent);
  const box=(color,pos,scale,parent)=>mesh(cube,color,pos,scale,parent);
  const disc=(color,pos,scale,parent)=>mesh(cylinder,color,pos,scale,parent);
  function rail(color,from,to,r=.06,parent=scene) {
    const a=new THREE.Vector3(...from),b=new THREE.Vector3(...to),delta=b.clone().sub(a);
    const m=disc(color,a.clone().add(b).multiplyScalar(.5).toArray(),[r,delta.length(),r],parent);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());return m;
  }
  function label(text,x,y,z,width=3,color='#4b435f') {
    const canvas=document.createElement('canvas');canvas.width=512;canvas.height=96;
    const ctx=canvas.getContext('2d');ctx.clearRect(0,0,512,96);
    ctx.fillStyle=color;ctx.font='bold 40px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText(text.slice(0,30),256,48,500);
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}));
    sprite.position.set(x,y,z);sprite.scale.set(width,width*96/512,1);scene.add(sprite);
    return sprite;
  }
  // Rounded floating base and two distinct material worlds.
  box('#c4b5b2',[-CAMPUS.roomCenter,-.9,CAMPUS.centerZ],[CAMPUS.width,1.4,CAMPUS.depth]);
  box('#c4b5b2',[CAMPUS.roomCenter,-.9,CAMPUS.centerZ],[CAMPUS.width,1.4,CAMPUS.depth]);
  box('#a2cdb2',[-CAMPUS.roomCenter,-.12,CAMPUS.centerZ],[CAMPUS.width,.3,CAMPUS.depth-.5]);
  box('#eed7b4',[CAMPUS.roomCenter,-.1,CAMPUS.centerZ],[CAMPUS.width-.2,.35,CAMPUS.depth-.5]);
  box('#edbfa9',[0,.08,5.8],[34,.12,1.1]);
  for(let i=0;i<10;i++) disc('#f7e8d3',[-1+.15*Math.sin(i),.1,-6+i*1.2],[.5,.1,.4]);
  // Study hall: dollhouse cutaway, cream walls, big blue windows, pink trim.
  box('#f4e5cb',[8.8,2.15,-6.7],[16.6,4.4,.25]);
  // Low plinth plus airy glass keeps the cutaway room readable from outside.
  box('#e8d2d7',[17,.5,-1.2],[.24,1,11.3]);
  const glass=new THREE.MeshStandardMaterial({color:'#c4e1dc',transparent:true,opacity:.2,roughness:.2,depthWrite:false});
  for(const z of [-4.9,-1.3,2.3]) {
    const pane=new THREE.Mesh(cube,glass);pane.position.set(17,2.65,z);pane.scale.set(.1,3.3,3.4);scene.add(pane);
    box('#ead9c3',[17,2.65,z-1.7],[.14,3.6,.14]);
  }
  // A wood-slat skylight/pergola hints at a modern campus without hiding the agents.
  for(let i=0;i<15;i++)box('#c99f7c',[1.6+i*1.07,4.5,-5.6],[.13,.18,2.4]);
  box('#d6a29f',[8.8,4.45,-6.7],[17,.24,.6]);
  box('#d6a29f',[17,4.45,-1.2],[.6,.24,11.5]);
  for(const x of [3,11]) {
    box('#eed3a7',[x,2.65,-6.5],[2.75,2.55,.15]);
    box('#b7dce0',[x,2.65,-6.37],[2.4,2.15,.12]);
    box('#fff1d7',[x,2.65,-6.25],[.1,2.25,.12]);
    box('#fff1d7',[x,2.65,-6.25],[2.5,.1,.12]);
  }
  // Original geometric mural: campus inspiration, not company branding.
  box('#fff3dc',[7,2.65,-6.44],[3.55,2.6,.12]);
  const mural=disc('#cfaaa9',[6.5,2.72,-6.32],[.75,.04,.75]);mural.rotation.x=Math.PI/2;
  const stroke=box('#8fb8b7',[7.7,2.65,-6.28],[.6,1.9,.06]);stroke.rotation.z=-.4;
  ball('#e6c576',[7.6,3.32,-6.24],[.35,.35,.05]);
  box('#968ab2',[7.15,1.75,-6.23],[2.45,.12,.05]);
  // Carpet islands and connected worktables retain the study-hall purpose.
  box('#c3bfdc',[6.7,.13,-.5],[10.5,.07,8.2]);
  const stations=[];
  for(let i=0;i<24;i++) {
    const station=new THREE.Group();scene.add(station);stations.push(station);
    const p=spot('classroom',i);
    box('#cd9e73',[p.x,.63,p.z+DESK.offset],[DESK.width,.14,DESK.depth],station);
    for(const dx of [-.55,.55]) box('#a77e62',[p.x+dx,.31,p.z+DESK.offset],[.09,.62,.4],station);
    // Each occupied workspace gets a laptop, notebook and ceramic mug.
    box('#aaa7bc',[p.x,.75,p.z-.65],[.68,.045,.43],station);
    box('#77758e',[p.x,1,p.z-.87],[.68,.48,.045],station);
    box('#c4e2dc',[p.x,1,p.z-.838],[.59,.38,.012],station);
    for(let line=0;line<3;line++)box('#fff3df',[p.x-.06,1.08-line*.08,p.z-.827],[.36-line*.07,.015,.005],station);
    box('#f1d2aa',[p.x-.52,.74,p.z-.7],[.3,.035,.35],station);
    disc('#f4e4cf',[p.x+.52,.83,p.z-.7],[.1,.19,.1],station);
    disc('#856c5b',[p.x+.52,.929,p.z-.7],[.077,.006,.077],station);
    disc(['#c5b4cf','#a7c3b0','#e3b199','#d9c582'][i%4],[p.x,.3,p.z],[.32,.5,.32],station);
  }
  // A four-person project table and a smaller round collaboration table.
  box('#d5ad86',[5.6,.68,-4.75],[3.4,.15,1.15]);
  for(const x of [4.4,6.8])for(const z of [-5.65,-3.85])disc('#b7c8c1',[x,.35,z],[.35,.65,.35]);
  for(const x of [4.5,6.7])box('#e8c9d2',[x,.78,-4.75],[.55,.04,.4]);
  disc('#e1bb91',[8.9,.68,-4.65],[.8,.14,.8]);
  disc('#bca8cb',[8.9,.32,-3.55],[.35,.6,.35]);
  // Coffee bar on the front promenade, separated from desk aisles.
  box('#aabcb0',[4.6,.55,7],[3.3,1.1,.8]);
  box('#e6c8a5',[4.6,1.14,7],[3.5,.12,.95]);
  box('#77788b',[5.4,1.48,7],[.7,.6,.55]);
  box('#e0d7d1',[5.4,1.48,7.3],[.52,.35,.05]);
  for(const x of [3.4,3.75,4.1,6.1])disc('#f8edd9',[x,1.3,7],[.12,.2,.12]);
  label('COFFEE & IDEAS',4.5,1.9,7,2.6);
  // Compact lounge lane stays outside every agent seat/aisle.
  box('#abbcc9',[11.65,.4,1.4],[1.25,.7,2.5]);
  box('#b7c8d0',[12.2,.95,1.4],[.24,1.1,2.55]);
  for(const z of [.7,2.1])ball('#e6b5a2',[11.62,.95,z],[.42,.24,.5]);
  disc('#ceab86',[11.25,.55,3.6],[.65,.14,.65]);
  disc('#f1e5cb',[11.25,.28,3.6],[.16,.5,.16]);
  box('#d0ba76',[11.15,.65,3.6],[.5,.05,.35]);
  disc('#cd9b92',[11.8,.4,-5.2],[.45,.65,.45]);
  for(let i=0;i<5;i++)ball('#88b6a0',[11.8+Math.sin(i*1.3)*.3,1+i*.15,-5.2+Math.cos(i)*.2],[.2,.5,.18]);
  // Bookcase: a little crooked rainbow of books, not photorealistic clutter.
  box('#c69774',[1.1,1.1,-5.2],[1.25,2.2,.65]);
  const books=['#a9c9c3','#e6aca9','#d5c1e7','#e8cf85'];
  for(let row=0;row<3;row++)for(let b=0;b<4;b++)box(books[b],[.68+b*.27,.42+row*.63,-4.81],[.18,.4+(b%2)*.11,.2]);
  // Warm library wall: shallow shelving behind the navigable floor. Repeated
  // book colors use shared materials; reference images never become textures.
  for(const x of [13.3,15.6]) {
    box('#d6b58f',[x,2.0,-6.46],[2.05,3.8,.32]);
    box('#ad8a6c',[x,2.0,-6.25],[1.87,3.5,.12]);
    for(let row=0;row<4;row++){
      box('#e8cfac',[x,.55+row*.85,-6.05],[2.0,.09,.38]);
      for(let b=0;b<7;b++){
        const bx=x-.78+b*.25,h=.44+(b%3)*.085;
        box(books[(row+b)%4],[bx,.61+row*.85+h/2,-6.11],[.18,h,.22]);
        box('#f5e8cf',[bx,.67+row*.85+h*.4,-5.993],[.12,.022,.015]);
      }
    }
  }
  // Rounded arched window crowns and tiny botanical details warm the room.
  for(const x of [3,11]){
    const arch=new THREE.Mesh(new THREE.TorusGeometry(1.16,.09,6,24,Math.PI),mat('#f4e3c8'));arch.position.set(x,3.53,-6.20);scene.add(arch);
    box('#e0be94',[x,1.44,-6.09],[2.7,.13,.43]);
    disc('#d1a29b',[x+.83,1.66,-6.09],[.14,.3,.14]);
    for(let i=0;i<3;i++)ball('#97b79a',[x+.83+(i-1)*.10,1.96+Math.sin(i)*.13,-6.09],[.12,.24,.07]);
  }
  // Authored wood inlay/planks, kept flat and below walking height.
  for(let i=0;i<24;i++)box('#dfc49f',[8.8,.086,-7.9+i*.76],[17.1,.009,.015]);
  for(const x of [4.4,6.8,8.9]){
    box('#ede0bd',[x,.81,-4.72],[.43,.035,.3]);
    box('#bdadca',[x+.04,.85,-4.72],[.39,.027,.27]);
    disc('#e2b6a6',[x+.25,.86,-4.72],[.09,.21,.09]);
  }
  // Garden: marshmallow trees, stones, flowers, benches and a little fountain.
  function tree(x,z,size=1) {
    disc('#b29379',[x,.85*size,z],[.19*size,1.7*size,.19*size]);
    ball('#83b99c',[x,2.15*size,z],[1.12*size,1.3*size,1.05*size]);
    ball('#a8d0ac',[x-.55*size,2.5*size,z+.2],[.75*size,.8*size,.7*size]);
    ball('#bfd7aa',[x+.35*size,2.85*size,z],[.65*size,.72*size,.65*size]);
  }
  for(const [x,z,s] of [[-12,-5.7,1.05],[-7,-6.6,.8],[-2,-6,.75]])tree(x,z,s);
  disc('#dfcfbd',[-11,.2,3.4],[1.05,.35,1.05]);
  disc('#88c9ce',[-11,.41,3.4],[.86,.05,.86]);
  disc('#c9bdab',[-11,.65,3.4],[.18,.5,.18]);
  ball('#c6e6df',[-11,.98,3.4],[.25,.32,.25]);
  // Slide: a tiny roofed tower, ladder and smooth curved pastel chute.
  disc('#d5cfa7',[-10.5,.07,-2.9],[1.75,.12,2.1]);
  for(const x of [-11.1,-9.9])for(const z of [-4.1,-3.2])rail('#9fc8c1',[x,.1,z],[x,3.75,z],.16);
  box('#cfa57e',[-10.5,1.6,-3.7],[1.4,.15,1.25]);
  const dome=new THREE.Mesh(new THREE.SphereGeometry(1,20,12,0,Math.PI*2,0,Math.PI/2),mat('#e5b4c3'));dome.position.set(-10.5,3.8,-3.7);dome.scale.set(1.03,.62,.92);dome.castShadow=true;scene.add(dome);
  disc('#f0ce9e',[-10.5,3.78,-3.7],[1.08,.16,.97]);
  for(const x of [-11.1,-9.9]){disc('#e8d5ae',[x,1.75,-3.7],[.24,.15,.24]);ball('#d6b8d2',[x,3.65,-3.7],[.24,.26,.24]);}
  ball('#f3d488',[-10.5,4.5,-3.7],[.16,.23,.16]);
  for(let i=0;i<5;i++)rail('#b4caca',[-11.18,.25+i*.3,-4.6],[-9.82,.25+i*.3,-4.6],.065);
  for(const x of [-11.18,-9.82])rail('#b1b4cf',[x,.1,-4.65],[x,1.8,-4.2],.065);
  const curve=SLIDE_CURVE;
  const chutePoints=[],chuteIndices=[];
  for(let i=0;i<=20;i++){const p=curve.getPoint(i/20);chutePoints.push(p.x-.46,p.y,p.z,p.x+.46,p.y,p.z);if(i<20){const j=i*2;chuteIndices.push(j,j+2,j+1,j+1,j+2,j+3)}}
  const chuteGeometry=new THREE.BufferGeometry();chuteGeometry.setAttribute('position',new THREE.Float32BufferAttribute(chutePoints,3));chuteGeometry.setIndex(chuteIndices);chuteGeometry.computeVertexNormals();
  const chute=new THREE.Mesh(chuteGeometry,new THREE.MeshStandardMaterial({color:'#edb176',side:THREE.DoubleSide,roughness:.65}));chute.castShadow=true;chute.userData.space='playground';scene.add(chute);
  for(const side of [-.49,.49]) {
    const points=curve.getPoints(20).map(p=>p.add(new THREE.Vector3(side,.14,0)));
    const edge=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),20,.08,6,false),mat('#d5999e'));edge.userData.space='playground';scene.add(edge);
  }
  // Merry-go-round: a decorative slow turn, never fabricated agent participation.
  disc('#d9c8bd',[-6.4,.12,-2.8],[1.6,.15,1.6]);
  const carousel=new THREE.Group();carousel.name='playground-carousel';carousel.position.set(-6.4,.3,-2.8);scene.add(carousel);
  disc('#a6c7c5',[0,0,0],[1.3,.2,1.3],carousel);
  disc('#e6c589',[0,.13,0],[.3,.14,.3],carousel);
  for(let i=0;i<4;i++) {
    const a=i*Math.PI/2,x=Math.cos(a)*.85,z=Math.sin(a)*.85;
    rail('#d99a9e',[x,.1,z],[x,.85,z],.055,carousel);
    rail('#eedbaf',[x,.85,z],[0,.85,0],.055,carousel);
    ball(['#d8b1c7','#e9ca88','#a7b7d5','#a8c6a3'][i],[x,.18,z],[.32,.09,.32],carousel);
  }
  // Monkey bars: two ladders and an overhead rung bridge in mint and lilac.
  disc('#c4c7b0',[-2.9,.08,-3.4],[1.1,.1,1.9]);
  for(const x of [-3.6,-2.2])for(const z of [-4.8,-2])rail('#a6b8cf',[x,.1,z],[x,2.15,z],.075);
  for(const x of [-3.6,-2.2])rail('#a0c3af',[x,2.15,-4.8],[x,2.15,-2],.09);
  for(let i=0;i<6;i++)rail('#e3c293',[-3.6,2.15,-4.8+i*.56],[-2.2,2.15,-4.8+i*.56],.06);
  for(const z of [-4.8,-2])for(let i=0;i<5;i++)rail('#c7afd4',[-3.6,.25+i*.38,z],[-2.2,.25+i*.38,z],.06);
  for(let i=0;i<24;i++) {
    const x=-12+(i%12)*.88,z=i<12 ? -6.6 : 6.7;
    disc('#749d83',[x,.24,z],[.025,.4,.025]);
    ball(['#efb9bd','#f4dc8d','#cfb8df'][i%3],[x,.5,z],[.14,.14,.14]);
    ball('#fff1bf',[x,.54,z+.09],[.055,.055,.04]);
  }
  // New side wings: a garden promenade and a quiet reading lounge. These are
  // real floor extensions, not enlarged toys. Furniture footprints share nav data.
  box('#d5ddbd',[-14.3,.06,1.5],[1,.07,14.5]);
  box('#e7cbbb',[14.35,.13,1.2],[3.9,.07,9.8]);
  for(const p of ANNEX_PROPS) {
    if(p.kind==='planter') {
      box('#ead2bb',[p.x,.3,p.z],[p.w,.5,p.d]);
      box('#a5b990',[p.x,.56,p.z],[p.w-.16,.04,p.d-.16]);
      for(let i=0;i<3;i++)ball(['#94bcab','#afc9a4','#c1cca6'][i],
        [p.x+(i-1)*.34,1.05+(i%2)*.3,p.z],[.43,.65,.43]);
    } else if(p.kind==='bench'||p.kind==='sofa') {
      const sofa=p.kind==='sofa',color=sofa?'#d3bed7':'#c9a27e';
      box(color,[p.x,.48,p.z],[p.w,.55,p.d]);
      box(color,[p.x+(sofa?.57:-.45),.95,p.z],[.25,1.1,p.d]);
      for(const dz of [-1,0,1])ball(sofa?'#f0d4bd':'#bdd0b0',
        [p.x,.83,p.z+dz],[.5,.18,.43]);
    } else {
      disc('#d2ad89',[p.x,.52,p.z],[.75,.15,.75]);
      disc('#b9987c',[p.x,.25,p.z],[.18,.5,.18]);
      box('#9bbfba',[p.x-.12,.62,p.z],[.5,.045,.37]);
      disc('#fff0d9',[p.x+.3,.7,p.z],[.1,.19,.1]);
    }
  }
  // A shallow front terrace stays clear for future shared activities.
  for(const x of [-9,-5,5,9])disc(x<0?'#c0d8b5':'#e8cdb6',[x,.12,9],[1.35,.06,.7]);
  // Garden edging and warm, low bollards frame rather than obscure the room.
  for(const x of [-16.5,-12,-8,-4,4,8,12,16.5]) {
    disc('#c5ad95',[x,.36,10.3],[.085,.65,.085]);
    ball('#fff0c9',[x,.73,10.3],[.16,.18,.16]);
  }
  tree(-15.5,-4.8,.65);
  label('GARDEN WALK',-14.9,2.8,4.6,2.5);
  label('READ & RECHARGE',14.4,3.1,-4.8,3);
  // Gate and pennants connect the two spaces; the travel path uses this opening.
  for(const z of [4.95,6.65])disc('#f7e4ce',[0,1,z],[.11,2,.11]);
  box('#cfaaa7',[0,2,5.8],[.2,.16,1.9]);
  label('THE PLAYGROUND',-7,4.9,-4.8,5);
  label('THE STUDY HALL',7,5.15,-6.7,5);
  // Cotton clouds hang behind the campus like miniature set dressing.
  for(const x of [-12,0,11])for(let i=0;i<3;i++)ball('#fff2e7',[x+i*.8,7+(i%2)*.35,-9],[1.1,.5,.6]);
  // Static sets are independently visible. Lights remain shared.
  const sets=scene.children.filter(o=>o.isMesh||o.isSprite||o.isGroup).map(o=>({o,side:o.userData.space||(o.position.x<0?'playground':o.position.x>0?'classroom':'shared')}));
  // Station groups use world-space children, so classify explicitly.
  for(const entry of sets)if(stations.includes(entry.o))entry.side='classroom';
  const actors=new Map();
  function character(agent) {
    const seed=hashId(agent.id),parts=art.plush(seed);scene.add(parts.root);
    const name=label(agent.name,0,2,0,1.7);parts.root.userData.agentId=agent.id;
    return {...parts,animation:animateCharacter(parts.root),name,seed,agent,path:null,start:0,duration:1,space:agent.presence.space};
  }
  function sync(world) {
    const shown=[...world.agents].sort((a,b)=>a.id.localeCompare(b.id)).slice(0,RENDER_LIMIT);
    const seen=new Set(), counts={playground:0,classroom:0};
    for(const agent of shown) {
      seen.add(agent.id);const goal=spot(agent.presence.space,counts[agent.presence.space]++);
      let actor=actors.get(agent.id);
      if(!actor) { actor=character(agent);actors.set(agent.id,actor);actor.root.position.set(goal.x,0,goal.z); }
      else if(actor.target && (actor.target.x!==goal.x || actor.target.z!==goal.z || actor.stamp!==JSON.stringify(agent.presence))) {
        const interrupted=director.cancel(agent.id,true),from={x:actor.root.position.x,y:actor.root.position.y,z:actor.root.position.z};
        const exit=interrupted?.exit,next=route(exit||from,goal);
        actor.path=next?(exit?[...(interrupted.escape||[from,exit]),...next.slice(1)]:next):null;
        actor.exitPose=exit?interrupted.exitPose:null;actor.exitDistance=exit?routeLength(interrupted.escape):0;
        if(!next){actor.root.position.set(goal.x,0,goal.z);director.finishExit(agent.id);} // no invented route through a blocked set
        actor.pathLength=actor.path?routeLength(actor.path):0;
        actor.start=performance.now();actor.duration=actor.path?Math.max(500,actor.pathLength/1.8*1000):1;
        actor.crossing=actor.space!==agent.presence.space;
      }
      actor.stamp=JSON.stringify(agent.presence);
      actor.target=goal;actor.space=agent.presence.space;actor.agent=agent;
    }
    for(const [id,a] of actors)if(!seen.has(id)) {
      director.cancel(id);director.finishExit(id);a.animation.dispose();scene.remove(a.root,a.name);a.name.material.map.dispose();a.name.material.dispose();
      a.dispose();actors.delete(id);
    }
    stations.forEach((station,i)=>{station.userData.occupied=i<Math.max(4,counts.classroom)});
    const selected=follow.value;
    follow.replaceChildren(new Option('Choose an agent',''),...shown.map(a=>new Option(a.name,a.id)));
    follow.value=actors.has(selected)?selected:'';portraitButton.disabled=!follow.value;if(!follow.value){portrait=false;portraitButton.setAttribute('aria-pressed','false');}
    if(selected&&!actors.has(selected))setRoom('campus');
    status.textContent=`3D campus · ${shown.length} characters${world.agents.length>RENDER_LIMIT ? ' shown of '+world.agents.length+' (full roster in 2D)' : ''} · decorative idle animation is not agent activity`;
  }
  function resize() {
    const width=host.clientWidth || 900,height=Math.min(620,Math.max(360,width*.6));
    renderer.setSize(width,height);const aspect=width/height;
    viewAspect=aspect;targetExtent=room==='campus'?Math.max(14,24/aspect):Math.max(11,13/aspect);
  }
  function setView() {
    const active=mode.value==='3d';host.hidden=!active;fallback.hidden=active;
    if(active)resize();
  }
  mode.addEventListener('change',setView);
  document.getElementById('cameraLeft').addEventListener('click',()=>{orbit-=.16});
  document.getElementById('cameraRight').addEventListener('click',()=>{orbit+=.16});
  function setRoom(next) {
    if(room===next)return;
    room=next;focus=room==='classroom'?CAMPUS.roomCenter:room==='playground'?-CAMPUS.roomCenter:0;
    document.getElementById('classTab').setAttribute('aria-pressed',String(room==='classroom'));
    document.getElementById('playTab').setAttribute('aria-pressed',String(room==='playground'));
    if(room!=='campus') {
      document.getElementById('classroomPanels').hidden=room!=='classroom';
      document.getElementById('socialSection').hidden=room!=='playground';
      fallback.dataset.focus=room;
    }
    resize();
  }
  follow.addEventListener('change',()=>{const a=actors.get(follow.value);portraitButton.disabled=!a;if(a)setRoom(a.space);else {portrait=false;portraitButton.setAttribute('aria-pressed','false');}});
  portraitButton.addEventListener('click',()=>{portrait=!portrait;portraitButton.setAttribute('aria-pressed',String(portrait));});
  document.getElementById('cameraHome').addEventListener('click',()=>{follow.value='';portrait=false;portraitButton.disabled=true;portraitButton.setAttribute('aria-pressed','false');orbit=.3;zoom=1;setRoom('campus');document.getElementById('cameraZoom').value='1'});
  document.getElementById('cameraZoom').addEventListener('input',e=>{zoom=Number(e.target.value)});
  addEventListener('playgrounds-world',e=>sync(e.detail.world));
  addEventListener('playgrounds-focus',e=>{follow.value='';setRoom(e.detail)});
  const describe=a=>({id:a.agent.id,seed:a.seed,space:a.space,target:a.target,moving:!!a.path,stale:visualActivity(a.agent,Date.now()/1000)==='stale'});
  document.getElementById('tryInteraction').addEventListener('click',()=>{
    const a=actors.get(follow.value),enabled=!reduce.matches&&!document.getElementById('quietMotion').checked;
    const started=enabled&&a&&director.start(describe(a),document.getElementById('interactionKind').value);
    document.getElementById('interactionStatus').textContent=started?'Decorative interaction started; task state is unchanged.':!enabled?'Turn off Still scene / reduced motion to preview interactions.':'Choose a fresh, stationary agent and an activity in its room; the spot may already be occupied.';
  });
  const observer=new ResizeObserver(resize);observer.observe(host);
  renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();mode.value='2d';mode.disabled=true;setView();status.textContent='3D context lost — 2D remains available. Reload to retry.'});
  let last=0; const look=new THREE.Vector3(),cameraTarget=new THREE.Vector3(),cameraGoal=new THREE.Vector3(),aim=new THREE.Vector3();
  function frame(now) {
    requestAnimationFrame(frame);
    if(document.hidden || host.hidden || now-last<1000/30)return;
    const dt=Math.min(.1,Math.max(0,(now-(last||now))/1000));last=now;
    const seconds=now/1000;
    const ambientMotion=!reduce.matches && !document.getElementById('quietMotion').checked;
    if(ambientMotion)carousel.rotation.y+=Math.min((now-(carousel.userData.lastFrame||now))/1000,.05)*.22;
    carousel.userData.lastFrame=now;
    host.dataset.carouselAngle=String(carousel.rotation.y);
    host.dataset.setting='slide-carousel-monkey-bars-modern-study';
    const followed=actors.get(follow.value);
    if(followed)setRoom(followed.path&&followed.crossing?'campus':followed.space);
    for(const {o,side} of sets)o.visible=!(portrait&&followed&&!followed.path)&&(room==='campus'||side===room)&&(o.userData.occupied!==false);
    host.dataset.room=room;
    host.dataset.floorArea=String(CAMPUS.width*CAMPUS.depth);
    host.dataset.following=follow.value;
    const detail=portrait&&followed&&!followed.path,extent=detail?Math.max(1.4,1.6/viewAspect):targetExtent;
    currentExtent=ambientMotion?THREE.MathUtils.damp(currentExtent,extent,6,dt):extent;
    camera.left=-currentExtent*viewAspect;camera.right=currentExtent*viewAspect;camera.top=currentExtent;camera.bottom=-currentExtent;
    camera.zoom=zoom;
    look.x=reduce.matches||!ambientMotion?focus:THREE.MathUtils.lerp(look.x,focus,.12);
    cameraGoal.set(look.x+Math.sin(orbit)*32,24,CAMPUS.centerZ+Math.cos(orbit)*32);
    cameraTarget.set(look.x,0,CAMPUS.centerZ);
    if(detail){const p=followed.root.position;const angle=followed.root.rotation.y;cameraGoal.set(p.x+Math.sin(angle+.12)*6,p.y+2.4,p.z+Math.cos(angle+.12)*6);cameraTarget.set(p.x,p.y+1,p.z);}
    const cameraBlend=ambientMotion&&dt>0?1-Math.exp(-6*dt):1;
    camera.position.lerp(cameraGoal,cameraBlend);aim.lerp(cameraTarget,cameraBlend);camera.lookAt(aim);
    camera.updateProjectionMatrix();
    const interactions=director.tick(dt,[...actors.values()].map(describe),ambientMotion,carousel.rotation.y,document.getElementById('ambientLife').checked);
    for(const a of actors.values()) {
      const activity=visualActivity(a.agent,Date.now()/1000), stale=activity==='stale';
      let walking=false;
      if(a.path) {
        const t=reduce.matches||document.getElementById('quietMotion').checked?1:Math.min(1,(now-a.start)/a.duration),p=walkSpatial(a.path,t);
        const dx=p.x-a.root.position.x,dz=p.z-a.root.position.z;
        if(Math.hypot(dx,dz)>.001)a.root.rotation.y=Math.atan2(dx,dz);
        a.root.position.set(p.x,p.y||0,p.z);walking=t<1;
        if(t*a.pathLength>=a.exitDistance)a.exitPose=null;
        if(t===1){a.path=null;director.finishExit(a.agent.id);}
      }
      const interaction=interactions.get(a.agent.id);
      if(interaction&&!a.path){
        const p=interaction.position,dx=p.x-a.root.position.x,dz=p.z-a.root.position.z;
        if(Math.hypot(dx,dz)>.002)a.root.rotation.y+=Math.atan2(Math.sin(Math.atan2(dx,dz)-a.root.rotation.y),Math.cos(Math.atan2(dx,dz)-a.root.rotation.y))*.25;
        a.root.position.set(p.x,p.y||0,p.z);walking=interaction.pose==='walk';
        if(interaction.angle!==undefined)a.root.rotation.y=interaction.angle;
        if(interaction.kind==='coffee'&&!walking)a.root.rotation.y=0;
      }
      if(!walking&&!interaction){a.root.rotation.y=a.space==='classroom'?Math.PI:0;a.root.position.y=0;}
      const pose=interaction?.pose||(walking?(a.exitPose||'walk'):ambientPose(a.space,activity,director.clock,a.seed));
      a.pose=stale?'idle':pose;
      a.animation.update(stale?'idle':pose,dt,!ambientMotion||stale);
      for(const eye of a.eyes)eye.scale.y=blinkAmount(director.clock,a.seed,ambientMotion&&!stale);
      a.mug.visible=!!interaction?.mug;
      a.root.scale.setScalar(stale?.88:1);
      a.root.visible=detail?a===followed:room==='campus'||a.space===room;
      for(const tuft of a.fibers)tuft.visible=!!detail&&a===followed;
      a.name.visible=a.root.visible;
      a.name.position.set(a.root.position.x,a.root.position.y+2.1,a.root.position.z);
    }
    host.dataset.animationClock=String(director.clock);
    host.dataset.poses=JSON.stringify([...actors.values()].map(a=>({id:a.agent.id,pose:a.pose,space:a.space,headYaw:a.head.rotation.y,rightArmX:a.arms[1].rotation.x,bodyY:a.body.position.y})));
    host.dataset.interactions=JSON.stringify([...director.active].map(([id,a])=>({id,kind:a.kind,stage:a.stage,pose:a.pose})));
    host.dataset.completed=JSON.stringify(director.completed);
    host.dataset.moving=String([...actors.values()].filter(a=>a.path).length);
    host.dataset.reducedMotion=String(reduce.matches || document.getElementById('quietMotion').checked);
    renderer.render(scene,camera);
    document.getElementById('portraitNote').hidden=!detail;
    host.dataset.artDirection='plush-pack-2026-09-30';host.dataset.portrait=String(!!detail);
    host.dataset.artMetrics=JSON.stringify({calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures});
    host.dataset.characterStyles=JSON.stringify([...actors.values()].map(a=>({id:a.agent.id,style:a.root.userData.artStyle})));
  }
  if(globalThis.playgroundsWorldSnapshot)sync(globalThis.playgroundsWorldSnapshot.world);
  host.hidden=false;mode.disabled=false;setView();resize();requestAnimationFrame(frame);
}
