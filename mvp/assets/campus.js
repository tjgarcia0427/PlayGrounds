import * as THREE from './vendor/three.module.js';
import {hashId,spot,travelPath,walkPoint,visualActivity,RENDER_LIMIT} from './campus-layout.js';

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
  let orbit=.64, zoom=1, focus=0;
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.0;
  renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=THREE.PCFShadowMap;
  renderer.domElement.setAttribute('aria-label','3D toy garden and cutaway Classroom; full agent details are available in the 2D view.');
  renderer.domElement.setAttribute('role','img');
  host.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight('#fff3e1','#96b7ba',1.7));
  const sun=new THREE.DirectionalLight('#fff0cf',2.3);
  sun.position.set(-10,22,14);sun.castShadow=true;
  sun.shadow.mapSize.set(1024,1024);
  Object.assign(sun.shadow.camera,{left:-20,right:20,top:15,bottom:-15,near:1,far:60});
  sun.shadow.normalBias=.06;scene.add(sun);
  const rim=new THREE.DirectionalLight('#d1d9ff',1.1);rim.position.set(15,10,-12);scene.add(rim);
  const materials=new Map();
  function mat(color) {
    if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.88,metalness:0}));
    return materials.get(color);
  }
  // Shared low-poly geometries reduce allocations and keep the toy silhouette soft.
  const sphere=new THREE.SphereGeometry(1,12,10);
  const cube=new THREE.BoxGeometry(1,1,1);
  const cylinder=new THREE.CylinderGeometry(1,1,1,16);
  function mesh(geometry,color,pos,scale,parent=scene) {
    const m=new THREE.Mesh(geometry,mat(color));m.position.set(...pos);m.scale.set(...scale);
    m.castShadow=Math.max(...scale)>.3;m.receiveShadow=true;parent.add(m);return m;
  }
  const ball=(color,pos,scale,parent)=>mesh(sphere,color,pos,scale,parent);
  const box=(color,pos,scale,parent)=>mesh(cube,color,pos,scale,parent);
  const disc=(color,pos,scale,parent)=>mesh(cylinder,color,pos,scale,parent);
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
  box('#c4b5b2',[0,-.9,0],[27,1.4,16]);
  box('#a2cdb2',[-6.8,-.12,0],[13.4,.3,15.5]);
  box('#eed7b4',[6.8,-.1,0],[13.2,.35,15.5]);
  box('#edbfa9',[0,.08,5.8],[26,.12,1.1]);
  for(let i=0;i<10;i++) disc('#f7e8d3',[-1+.15*Math.sin(i),.1,-6+i*1.2],[.5,.1,.4]);
  // Study hall: dollhouse cutaway, cream walls, big blue windows, pink trim.
  box('#f4e5cb',[6.8,2.15,-6.7],[12.6,4.4,.25]);
  box('#e8d2d7',[13,2.15,-1.2],[.24,4.4,11.3]);
  box('#d6a29f',[6.8,4.45,-6.7],[13,.24,.6]);
  box('#d6a29f',[13,4.45,-1.2],[.6,.24,11.5]);
  for(const x of [3,7,11]) {
    box('#eed3a7',[x,2.65,-6.5],[2.75,2.55,.15]);
    box('#b7dce0',[x,2.65,-6.37],[2.4,2.15,.12]);
    box('#fff1d7',[x,2.65,-6.25],[.1,2.25,.12]);
    box('#fff1d7',[x,2.65,-6.25],[2.5,.1,.12]);
  }
  // Carpet islands and tiny study desks.
  box('#c3bfdc',[6.7,.13,-.5],[10.5,.07,8.2]);
  const stations=[];
  for(let i=0;i<24;i++) {
    const station=new THREE.Group();scene.add(station);stations.push(station);
    const p=spot('classroom',i);
    box('#cd9e73',[p.x,.63,p.z-.5],[1.45,.14,.74],station);
    for(const dx of [-.55,.55]) box('#a77e62',[p.x+dx,.31,p.z-.5],[.09,.62,.48],station);
    box('#fff4d9',[p.x-.15,.735,p.z-.5],[.55,.045,.4],station);
    box('#d59096',[p.x+.14,.76,p.z-.5],[.025,.05,.39],station);
    disc('#c5b4cf',[p.x,.3,p.z+.38],[.32,.5,.32],station);
  }
  disc('#cd9b92',[11,.4,4.2],[.5,.65,.5]);
  for(let i=0;i<5;i++)ball('#88b6a0',[11+Math.sin(i*1.3)*.35,1+i*.15,4.2+Math.cos(i)*.25],[.2,.5,.18]);
  // Bookcase: a little crooked rainbow of books, not photorealistic clutter.
  box('#c69774',[1.1,1.1,-5.2],[1.25,2.2,.65]);
  const books=['#a9c9c3','#e6aca9','#d5c1e7','#e8cf85'];
  for(let row=0;row<3;row++)for(let b=0;b<4;b++)box(books[b],[.68+b*.27,.42+row*.63,-4.81],[.18,.4+(b%2)*.11,.2]);
  // Garden: marshmallow trees, stones, flowers, benches and a little fountain.
  function tree(x,z,size=1) {
    disc('#b29379',[x,.85*size,z],[.19*size,1.7*size,.19*size]);
    ball('#83b99c',[x,2.15*size,z],[1.12*size,1.3*size,1.05*size]);
    ball('#a8d0ac',[x-.55*size,2.5*size,z+.2],[.75*size,.8*size,.7*size]);
    ball('#bfd7aa',[x+.35*size,2.85*size,z],[.65*size,.72*size,.65*size]);
  }
  for(const [x,z,s] of [[-11,-5,1.2],[-7,-6,1],[-3,-5,.85],[-12,3,.8]])tree(x,z,s);
  disc('#dfcfbd',[-7,.2,-2.3],[1.65,.35,1.65]);
  disc('#88c9ce',[-7,.41,-2.3],[1.38,.05,1.38]);
  disc('#c9bdab',[-7,.65,-2.3],[.25,.5,.25]);
  ball('#c6e6df',[-7,1.05,-2.3],[.38,.42,.38]);
  for(const x of [-10.4,-3.7]) {
    box('#c98f79',[x,.52,-.9],[1.8,.15,.55]);box('#dcaf8d',[x,.96,-1.16],[1.8,.65,.12]);
    for(const dx of [-.6,.6])box('#a68373',[x+dx,.25,-.9],[.14,.5,.45]);
  }
  for(let i=0;i<24;i++) {
    const x=-12+(i%12)*.88,z=i<12 ? -6.6 : 6.7;
    disc('#749d83',[x,.24,z],[.025,.4,.025]);
    ball(['#efb9bd','#f4dc8d','#cfb8df'][i%3],[x,.5,z],[.14,.14,.14]);
    ball('#fff1bf',[x,.54,z+.09],[.055,.055,.04]);
  }
  // Gate and pennants connect the two spaces; the travel path uses this opening.
  for(const z of [4.95,6.65])disc('#f7e4ce',[0,1,z],[.11,2,.11]);
  box('#cfaaa7',[0,2,5.8],[.2,.16,1.9]);
  label('THE PLAYGROUND',-7,4.9,-4.8,5);
  label('THE CLASSROOM',7,5.15,-6.7,5);
  // Cotton clouds hang behind the campus like miniature set dressing.
  for(const x of [-12,0,11])for(let i=0;i<3;i++)ball('#fff2e7',[x+i*.8,7+(i%2)*.35,-9],[1.1,.5,.6]);
  const actors=new Map();
  const palettes=['#f2bbad','#b9cfc1','#c5bce1','#f0d28d','#b4d2df','#e3b6cb'];
  function character(agent) {
    const seed=hashId(agent.id), color=palettes[seed%palettes.length];
    const root=new THREE.Group(), body=new THREE.Group();root.add(body);scene.add(root);
    ball(color,[0,.59,0],[.36,.48,.29],body);
    ball(color,[0,1.16,0],[.43,.39,.36],body);
    for(const side of [-1,1]) {
      ball(color,[side*.29,1.49,0],[.16,(seed%3===0?.3:.17),.14],body);
      ball('#f9dcd3',[side*.29,1.49,.105],[.09,(seed%3===0?.2:.1),.05],body);
      ball('#4d455a',[side*.14,1.2,.329],[.048,.07,.027],body);
      ball('#fff8e9',[side*.14-.01,1.222,.35],[.013,.018,.008],body);
      ball('#eaa9a6',[side*.27,1.08,.285],[.085,.04,.025],body);
    }
    ball('#775965',[0,1.1,.362],[.045,.03,.024],body);
    const arms=[-1,1].map(side=>ball(color,[side*.39,.66,0],[.13,.28,.14],body));
    const feet=[-1,1].map(side=>ball('#f4e4cd',[side*.2,.15,.08],[.17,.16,.23],root));
    // Deterministic accessories give stable identity without introducing external assets.
    if(seed%3===1) {
      box('#766b97',[0,1.24,.37],[.5,.035,.03],body);
      for(const side of [-1,1]) {
        const ring=new THREE.Mesh(new THREE.TorusGeometry(.105,.018,6,12),mat('#766b97'));
        ring.position.set(side*.145,1.24,.378);body.add(ring);
      }
    } else if(seed%3===2) {
      disc('#91b6a7',[0,1.55,0],[.31,.12,.28],body);
      ball('#e8c88b',[.15,1.64,.08],[.07,.08,.07],body);
    }
    box('#fcf0d6',[0,.77,.28],[.24,.22,.025],body);
    ball(palettes[(seed+2)%palettes.length],[0,.8,.31],[.055,.055,.02],body);
    const name=label(agent.name,0,2,0,1.7);root.userData.agentId=agent.id;
    return {root,body,arms,feet,name,seed,agent,path:null,start:0,duration:1,space:agent.presence.space};
  }
  function sync(world) {
    const shown=[...world.agents].sort((a,b)=>a.id.localeCompare(b.id)).slice(0,RENDER_LIMIT);
    const seen=new Set(), counts={playground:0,classroom:0};
    for(const agent of shown) {
      seen.add(agent.id);const goal=spot(agent.presence.space,counts[agent.presence.space]++);
      let actor=actors.get(agent.id);
      if(!actor) { actor=character(agent);actors.set(agent.id,actor);actor.root.position.set(goal.x,0,goal.z); }
      else if(actor.target && (actor.target.x!==goal.x || actor.target.z!==goal.z)) {
        const from={x:actor.root.position.x,z:actor.root.position.z};
        actor.path=travelPath(from,goal,actor.space!==agent.presence.space);
        actor.start=performance.now();actor.duration=Math.max(900,Math.hypot(goal.x-from.x,goal.z-from.z)*160);
      }
      actor.target=goal;actor.space=agent.presence.space;actor.agent=agent;
    }
    for(const [id,a] of actors)if(!seen.has(id)) {
      scene.remove(a.root,a.name);a.name.material.map.dispose();a.name.material.dispose();
      a.root.traverse(o=>{if(o.geometry && ![sphere,cube,cylinder].includes(o.geometry))o.geometry.dispose()});actors.delete(id);
    }
    stations.forEach((station,i)=>{station.visible=i<Math.max(4,counts.classroom)});
    status.textContent=`3D campus · ${shown.length} characters${world.agents.length>RENDER_LIMIT ? ' shown of '+world.agents.length+' (full roster in 2D)' : ''} · decorative idle animation is not agent activity`;
  }
  function resize() {
    const width=host.clientWidth || 900,height=Math.min(620,Math.max(360,width*.6));
    renderer.setSize(width,height);const aspect=width/height;
    const extent=Math.max(12,19/aspect);
    camera.left=-extent*aspect;camera.right=extent*aspect;camera.top=extent;camera.bottom=-extent;camera.updateProjectionMatrix();
  }
  function setView() {
    const active=mode.value==='3d';host.hidden=!active;fallback.hidden=active;
    if(active)resize();
  }
  mode.addEventListener('change',setView);
  document.getElementById('cameraLeft').addEventListener('click',()=>{orbit-=.16});
  document.getElementById('cameraRight').addEventListener('click',()=>{orbit+=.16});
  document.getElementById('cameraHome').addEventListener('click',()=>{orbit=.64;zoom=1;focus=0;document.getElementById('cameraZoom').value='1'});
  document.getElementById('cameraZoom').addEventListener('input',e=>{zoom=Number(e.target.value)});
  addEventListener('playgrounds-world',e=>sync(e.detail.world));
  addEventListener('playgrounds-focus',e=>{focus=e.detail==='classroom'?5:-5});
  const observer=new ResizeObserver(resize);observer.observe(host);
  renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();mode.value='2d';mode.disabled=true;setView();status.textContent='3D context lost — 2D remains available. Reload to retry.'});
  let last=0; const look=new THREE.Vector3();
  function frame(now) {
    requestAnimationFrame(frame);
    if(document.hidden || host.hidden || now-last<1000/30)return;
    last=now;
    const seconds=now/1000;
    camera.zoom=zoom;camera.position.set(Math.sin(orbit)*32,24,Math.cos(orbit)*32);
    look.x=reduce.matches?focus:THREE.MathUtils.lerp(look.x,focus,.06);
    camera.lookAt(look.x,0,0);camera.updateProjectionMatrix();
    for(const a of actors.values()) {
      const activity=visualActivity(a.agent,Date.now()/1000), stale=activity==='stale';
      let walking=false;
      if(a.path) {
        const t=reduce.matches||document.getElementById('quietMotion').checked?1:Math.min(1,(now-a.start)/a.duration),p=walkPoint(a.path,t);
        const dx=p.x-a.root.position.x,dz=p.z-a.root.position.z;
        if(Math.hypot(dx,dz)>.001)a.root.rotation.y=Math.atan2(dx,dz);
        a.root.position.set(p.x,0,p.z);walking=t<1;
        if(t===1)a.path=null;
      }
      if(!walking)a.root.rotation.y=a.space==='classroom'?Math.PI:0;
      const motion=reduce.matches||document.getElementById('quietMotion').checked||stale?0:1, phase=seconds*2+a.seed%100;
      a.body.position.y=motion*(walking?Math.abs(Math.sin(seconds*12))*.08:Math.sin(phase)*.018);
      a.body.rotation.z=motion*(walking?Math.sin(seconds*12)*.035:0);
      a.body.rotation.x=motion*(activity==='working'?Math.sin(seconds*3)*.055:activity==='awaiting_review'?.07:0);
      a.root.scale.setScalar(stale?.88:1);
      a.arms.forEach((arm,i)=>arm.rotation.x=motion*(walking?Math.sin(seconds*12+i*Math.PI)*.5:activity==='working'?-.65+Math.sin(seconds*4+i)*.12:0));
      a.feet.forEach((foot,i)=>foot.position.y=.15+motion*(walking?Math.max(0,Math.sin(seconds*12+i*Math.PI))*.15:0));
      a.name.position.set(a.root.position.x,2.1,a.root.position.z);
    }
    host.dataset.moving=String([...actors.values()].filter(a=>a.path).length);
    host.dataset.reducedMotion=String(reduce.matches || document.getElementById('quietMotion').checked);
    renderer.render(scene,camera);
  }
  if(globalThis.playgroundsWorldSnapshot)sync(globalThis.playgroundsWorldSnapshot.world);
  host.hidden=false;mode.disabled=false;setView();resize();requestAnimationFrame(frame);
}
