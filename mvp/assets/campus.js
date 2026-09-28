import * as THREE from './vendor/three.module.js';
import {hashId,spot,visualActivity,RENDER_LIMIT} from './campus-layout.js';

import {createNavigator,DESK} from './campus-navigation.js';
import {InteractionDirector,routeLength,walkSpatial,SLIDE_CURVE,blinkAmount} from './campus-interactions.js';
import {animateCharacter} from './campus-animation.js';

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
  let orbit=.3, zoom=1, focus=-6.8, room="playground", viewAspect=1, targetExtent=12, currentExtent=12;
  const follow=document.getElementById("followAgent");
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.0;
  renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=THREE.PCFShadowMap;
  renderer.domElement.setAttribute('aria-label','3D toy garden and cutaway Study Hall; full agent details are available in the 2D view.');
  renderer.domElement.setAttribute('role','img');
  host.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight('#fff3e1','#96b7ba',1.7));
  const sun=new THREE.DirectionalLight('#fff0cf',2.3);
  sun.position.set(-10,22,14);sun.castShadow=true;
  sun.shadow.mapSize.set(1024,1024);
  Object.assign(sun.shadow.camera,{left:-20,right:20,top:15,bottom:-15,near:1,far:60});
  sun.shadow.normalBias=.06;scene.add(sun);
  const rim=new THREE.DirectionalLight('#d1d9ff',1.1);rim.position.set(15,10,-12);scene.add(rim);
  const route=createNavigator(),director=new InteractionDirector(route);
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
  box('#c4b5b2',[-6.8,-.9,0],[13.4,1.4,16]);
  box('#c4b5b2',[6.8,-.9,0],[13.4,1.4,16]);
  box('#a2cdb2',[-6.8,-.12,0],[13.4,.3,15.5]);
  box('#eed7b4',[6.8,-.1,0],[13.2,.35,15.5]);
  box('#edbfa9',[0,.08,5.8],[26,.12,1.1]);
  for(let i=0;i<10;i++) disc('#f7e8d3',[-1+.15*Math.sin(i),.1,-6+i*1.2],[.5,.1,.4]);
  // Study hall: dollhouse cutaway, cream walls, big blue windows, pink trim.
  box('#f4e5cb',[6.8,2.15,-6.7],[12.6,4.4,.25]);
  // Low plinth plus airy glass keeps the cutaway room readable from outside.
  box('#e8d2d7',[13,.5,-1.2],[.24,1,11.3]);
  const glass=new THREE.MeshStandardMaterial({color:'#c4e1dc',transparent:true,opacity:.2,roughness:.2,depthWrite:false});
  for(const z of [-4.9,-1.3,2.3]) {
    const pane=new THREE.Mesh(cube,glass);pane.position.set(13,2.65,z);pane.scale.set(.1,3.3,3.4);scene.add(pane);
    box('#ead9c3',[13,2.65,z-1.7],[.14,3.6,.14]);
  }
  // A wood-slat skylight/pergola hints at a modern campus without hiding the agents.
  for(let i=0;i<11;i++)box('#c99f7c',[1.6+i*1.07,4.5,-5.6],[.13,.18,2.4]);
  box('#d6a29f',[6.8,4.45,-6.7],[13,.24,.6]);
  box('#d6a29f',[13,4.45,-1.2],[.6,.24,11.5]);
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
  for(const x of [-11.1,-9.9])for(const z of [-4.1,-3.2])rail('#e6c89c',[x,.1,z],[x,3.75,z],.09);
  box('#cfa57e',[-10.5,1.6,-3.7],[1.4,.15,1.25]);
  const roof=new THREE.Mesh(new THREE.ConeGeometry(1.12,.6,4),mat('#dba8ac'));roof.rotation.y=Math.PI/4;roof.position.set(-10.5,4.05,-3.7);scene.add(roof);
  for(let i=0;i<5;i++)rail('#b4caca',[-11.18,.25+i*.3,-4.6],[-9.82,.25+i*.3,-4.6],.065);
  for(const x of [-11.18,-9.82])rail('#b1b4cf',[x,.1,-4.65],[x,1.8,-4.2],.065);
  const curve=SLIDE_CURVE;
  const chutePoints=[],chuteIndices=[];
  for(let i=0;i<=20;i++){const p=curve.getPoint(i/20);chutePoints.push(p.x-.46,p.y,p.z,p.x+.46,p.y,p.z);if(i<20){const j=i*2;chuteIndices.push(j,j+2,j+1,j+1,j+2,j+3)}}
  const chuteGeometry=new THREE.BufferGeometry();chuteGeometry.setAttribute('position',new THREE.Float32BufferAttribute(chutePoints,3));chuteGeometry.setIndex(chuteIndices);chuteGeometry.computeVertexNormals();
  const chute=new THREE.Mesh(chuteGeometry,new THREE.MeshStandardMaterial({color:'#e9ba77',side:THREE.DoubleSide,roughness:.65}));chute.castShadow=true;chute.userData.space='playground';scene.add(chute);
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
  const palettes=['#f2bbad','#b9cfc1','#c5bce1','#f0d28d','#b4d2df','#e3b6cb'];
  function character(agent) {
    const seed=hashId(agent.id), color=palettes[seed%palettes.length];
    const root=new THREE.Group(), body=new THREE.Group();root.add(body);body.name="Body";scene.add(root);
    ball(color,[0,.59,0],[.36,.48,.29],body);
    const head=new THREE.Group(),eyes=[];head.name='Head';body.add(head);
    ball(color,[0,1.16,0],[.43,.39,.36],head);
    for(const side of [-1,1]) {
      ball(color,[side*.29,1.49,0],[.16,(seed%3===0?.3:.17),.14],head);
      ball('#f9dcd3',[side*.29,1.49,.105],[.09,(seed%3===0?.2:.1),.05],head);
      const eye=new THREE.Group();eye.position.set(side*.14,1.2,.329);head.add(eye);eyes.push(eye);
      ball('#4d455a',[0,0,0],[.048,.07,.027],eye);
      ball('#fff8e9',[-.01,.022,.021],[.013,.018,.008],eye);
      ball('#eaa9a6',[side*.27,1.08,.285],[.085,.04,.025],head);
    }
    ball('#775965',[0,1.1,.362],[.045,.03,.024],head);
    const arms=[-1,1].map((side,i)=>{const pivot=new THREE.Group();pivot.name=i?'RightArm':'LeftArm';pivot.position.set(side*.39,.85,0);body.add(pivot);ball(color,[0,-.19,0],[.13,.28,.14],pivot);return pivot});
    const feet=[-1,1].map(side=>ball('#f4e4cd',[side*.2,.15,.08],[.17,.16,.23],root));
    feet.forEach((foot,i)=>foot.name=i?'RightFoot':'LeftFoot');
    const mug=new THREE.Group();mug.position.set(0,-.43,.05);arms[1].add(mug);
    disc('#f7ebd8',[0,0,0],[.11,.18,.11],mug);disc('#87664e',[0,.093,0],[.085,.008,.085],mug);
    const handle=new THREE.Mesh(new THREE.TorusGeometry(.075,.025,6,10),mat('#f7ebd8'));handle.position.set(.11,0,0);mug.add(handle);mug.visible=false;
    // Deterministic accessories give stable identity without introducing external assets.
    if(seed%3===1) {
      box('#766b97',[0,1.24,.37],[.5,.035,.03],head);
      for(const side of [-1,1]) {
        const ring=new THREE.Mesh(new THREE.TorusGeometry(.105,.018,6,12),mat('#766b97'));
        ring.position.set(side*.145,1.24,.378);head.add(ring);
      }
    } else if(seed%3===2) {
      disc('#91b6a7',[0,1.55,0],[.31,.12,.28],head);
      ball('#e8c88b',[.15,1.64,.08],[.07,.08,.07],head);
    }
    box('#fcf0d6',[0,.77,.28],[.24,.22,.025],body);
    ball(palettes[(seed+2)%palettes.length],[0,.8,.31],[.055,.055,.02],body);
    // Cushioned headphones echo the approved plush reference without costly fur.
    for(const side of [-1,1])ball('#d5cbbf',[side*.44,1.2,0],[.12,.22,.23],head);
    const band=new THREE.Mesh(new THREE.TorusGeometry(.45,.055,8,20,Math.PI),mat('#b6ada6'));
    band.position.set(0,1.2,0);head.add(band);
    head.position.y=.98;for(const child of head.children)child.position.y-=.98;
    const name=label(agent.name,0,2,0,1.7);root.userData.agentId=agent.id;
    return {root,body,head,eyes,arms,feet,mug,animation:animateCharacter(root),name,seed,agent,path:null,start:0,duration:1,space:agent.presence.space};
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
        if(!next){actor.root.position.set(goal.x,0,goal.z);director.finishExit(agent.id);} // no invented route through a blocked set
        actor.start=performance.now();actor.duration=actor.path?Math.max(500,routeLength(actor.path)/1.8*1000):1;
        actor.crossing=actor.space!==agent.presence.space;
      }
      actor.stamp=JSON.stringify(agent.presence);
      actor.target=goal;actor.space=agent.presence.space;actor.agent=agent;
    }
    for(const [id,a] of actors)if(!seen.has(id)) {
      director.cancel(id);director.finishExit(id);a.animation.dispose();scene.remove(a.root,a.name);a.name.material.map.dispose();a.name.material.dispose();
      a.root.traverse(o=>{if(o.geometry && ![sphere,cube,cylinder].includes(o.geometry))o.geometry.dispose()});actors.delete(id);
    }
    stations.forEach((station,i)=>{station.userData.occupied=i<Math.max(4,counts.classroom)});
    const selected=follow.value;
    follow.replaceChildren(new Option('Choose an agent',''),...shown.map(a=>new Option(a.name,a.id)));
    follow.value=actors.has(selected)?selected:'';
    if(selected&&!actors.has(selected))setRoom('campus');
    status.textContent=`3D campus · ${shown.length} characters${world.agents.length>RENDER_LIMIT ? ' shown of '+world.agents.length+' (full roster in 2D)' : ''} · decorative idle animation is not agent activity`;
  }
  function resize() {
    const width=host.clientWidth || 900,height=Math.min(620,Math.max(360,width*.6));
    renderer.setSize(width,height);const aspect=width/height;
    viewAspect=aspect;targetExtent=room==='campus'?Math.max(12,19/aspect):Math.max(9,10/aspect);
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
    room=next;focus=room==='classroom'?6.8:room==='playground'?-6.8:0;
    document.getElementById('classTab').setAttribute('aria-pressed',String(room==='classroom'));
    document.getElementById('playTab').setAttribute('aria-pressed',String(room==='playground'));
    if(room!=='campus') {
      document.getElementById('classroomPanels').hidden=room!=='classroom';
      document.getElementById('socialSection').hidden=room!=='playground';
      fallback.dataset.focus=room;
    }
    resize();
  }
  follow.addEventListener('change',()=>{const a=actors.get(follow.value);if(a)setRoom(a.space)});
  document.getElementById('cameraHome').addEventListener('click',()=>{follow.value='';orbit=.3;zoom=1;setRoom('campus');document.getElementById('cameraZoom').value='1'});
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
  let last=0; const look=new THREE.Vector3();
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
    for(const {o,side} of sets)o.visible=(room==='campus'||side===room)&&(o.userData.occupied!==false);
    host.dataset.room=room;
    host.dataset.following=follow.value;
    currentExtent=ambientMotion?THREE.MathUtils.damp(currentExtent,targetExtent,6,dt):targetExtent;
    camera.left=-currentExtent*viewAspect;camera.right=currentExtent*viewAspect;camera.top=currentExtent;camera.bottom=-currentExtent;
    camera.zoom=zoom;
    look.x=reduce.matches||!ambientMotion?focus:THREE.MathUtils.lerp(look.x,focus,.12);
    camera.position.set(look.x+Math.sin(orbit)*32,24,Math.cos(orbit)*32);
    camera.lookAt(look.x,0,0);camera.updateProjectionMatrix();
    const interactions=director.tick(dt,[...actors.values()].map(describe),ambientMotion,carousel.rotation.y,document.getElementById('ambientLife').checked);
    for(const a of actors.values()) {
      const activity=visualActivity(a.agent,Date.now()/1000), stale=activity==='stale';
      let walking=false;
      if(a.path) {
        const t=reduce.matches||document.getElementById('quietMotion').checked?1:Math.min(1,(now-a.start)/a.duration),p=walkSpatial(a.path,t);
        const dx=p.x-a.root.position.x,dz=p.z-a.root.position.z;
        if(Math.hypot(dx,dz)>.001)a.root.rotation.y=Math.atan2(dx,dz);
        a.root.position.set(p.x,p.y||0,p.z);walking=t<1;
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
      const phase=(director.clock+a.seed%23)%24;
      const pose=interaction?.pose||(walking?'walk':a.space==='classroom'?(activity==='working'?(phase>20?'stretch':phase>16?'read':'typing'):'read'):(phase>20?'wave':'idle'));
      a.animation.update(stale?'idle':pose,dt,!ambientMotion||stale);
      for(const eye of a.eyes)eye.scale.y=blinkAmount(director.clock,a.seed,ambientMotion&&!stale);
      a.mug.visible=!!interaction?.mug;
      a.root.scale.setScalar(stale?.88:1);
      a.root.visible=room==='campus'||a.space===room;
      a.name.visible=a.root.visible;
      a.name.position.set(a.root.position.x,a.root.position.y+2.1,a.root.position.z);
    }
    host.dataset.interactions=JSON.stringify([...director.active].map(([id,a])=>({id,kind:a.kind,stage:a.stage,pose:a.pose})));
    host.dataset.completed=JSON.stringify(director.completed);
    host.dataset.moving=String([...actors.values()].filter(a=>a.path).length);
    host.dataset.reducedMotion=String(reduce.matches || document.getElementById('quietMotion').checked);
    renderer.render(scene,camera);
  }
  if(globalThis.playgroundsWorldSnapshot)sync(globalThis.playgroundsWorldSnapshot.world);
  host.hidden=false;mode.disabled=false;setView();resize();requestAnimationFrame(frame);
}
