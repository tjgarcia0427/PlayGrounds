import * as THREE from 'three';
import {RoundedBoxGeometry} from './addons/RoundedBoxGeometry.js';
import {RoomEnvironment} from './addons/RoomEnvironment.js';
const host=document.querySelector('#stage'),metrics=document.querySelector('#metrics');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let renderer;
try {renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'low-power'});}
catch {document.querySelector('#fallback').hidden=false;metrics.textContent='Accessible description shown; WebGL unavailable.';document.querySelectorAll('button,input').forEach(e=>e.disabled=true);}
if(renderer) build();
function build(){
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.domElement.setAttribute('role','img');renderer.domElement.setAttribute('aria-label','Original plush with lavender headphones in a pastel reading corner');host.append(renderer.domElement);
  const scene=new THREE.Scene();scene.background=new THREE.Color('#f0e4df');
  const camera=new THREE.PerspectiveCamera(35,1,.1,50);
  const ambient=new THREE.HemisphereLight('#fff2df','#b9a9be',1.15);scene.add(ambient);
  const key=new THREE.DirectionalLight('#ffe8d2',2.6);key.position.set(-3,7,5);key.castShadow=true;
  key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-5,right:5,top:5,bottom:-5,near:.1,far:18});key.shadow.normalBias=.035;key.shadow.bias=-.00015;scene.add(key);
  const fill=new THREE.DirectionalLight('#cfd5ff',.65);fill.position.set(5,3,1);scene.add(fill);
  const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();
  const env=pmrem.fromScene(room,.04);room.dispose();pmrem.dispose();
  // Original deterministic micro-grain: no downloaded texture or per-hair geometry.
  const size=128,data=new Uint8Array(size*size*4);let seed=47;
  for(let i=0;i<size*size;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;const n=112+(seed>>>26);data.set([n,n,n,255],i*4)}
  const fabric=new THREE.DataTexture(data,size,size,THREE.RGBAFormat);fabric.wrapS=fabric.wrapT=THREE.RepeatWrapping;fabric.repeat.set(2,2);fabric.magFilter=THREE.LinearFilter;fabric.minFilter=THREE.LinearMipmapLinearFilter;fabric.generateMipmaps=true;fabric.needsUpdate=true;
  const swappable=[];
  const matte=color=>new THREE.MeshStandardMaterial({color,roughness:.83});
  function cloth(color){
    const baseline=matte(color),soft=new THREE.MeshPhysicalMaterial({color,roughness:.94,sheen:.35,sheenColor:'#eadbd0',sheenRoughness:.8,bumpMap:fabric,bumpScale:.018});
    return {baseline,soft};
  }
  const plush=cloth('#e5d5bb'),lilac=cloth('#b8a8cc'),cushion=cloth('#c4b3d4');
  const wood=matte('#cfac86'),cream=matte('#f5e9d7'),pink=matte('#e7b6a8'),leaf=matte('#93b6a0'),dark=matte('#403846');
  const sphere=new THREE.SphereGeometry(1,32,24),cylinder=new THREE.CylinderGeometry(1,1,1,32);
  function mesh(geo,material,pos,scale,parent=scene){const m=new THREE.Mesh(geo,material.soft||material);m.position.set(...pos);m.scale.set(...scale);m.castShadow=true;m.receiveShadow=true;parent.add(m);if(material.soft)swappable.push({m,...material});return m;}
  const ball=(m,p,s,parent)=>mesh(sphere,m,p,s,parent);
  const disc=(m,p,s,parent)=>mesh(cylinder,m,p,s,parent);
  function box(m,p,s,r=.1,parent=scene){return mesh(new RoundedBoxGeometry(...s,3,Math.min(r,Math.min(...s)/2)),m,p,[1,1,1],parent)}
  // A rounded diorama base and softly architectural back wall.
  box(matte('#e3cebd'),[0,-.18,0],[7,.4,5.3],.18);
  box(matte('#eee1cc'),[0,.04,0],[6.9,.09,5.2],.035);
  box(matte('#ead6cb'),[0,1.8,-2.28],[6.8,3.6,.22],.11);
  box(matte('#f8edda'),[-1.85,2,-2.12],[1.85,2.5,.12],.06);
  box(matte('#c7dfdc'),[-1.85,2,-2.03],[1.62,2.26,.09],.045);
  box(cream,[-1.85,2,-1.96],[.07,2.28,.08],.035);
  box(cream,[-1.85,2,-1.96],[1.63,.07,.08],.035);
  box(matte('#d8c4b2'),[-1.85,.88,-1.89],[2,.11,.36],.05);
  // Raised fabric rug and a little geometric wall print.
  box(cloth('#d6c5d8'),[.05,.12,.4],[4.3,.055,3.6],.025);
  box(wood,[1.65,2.65,-2.06],[1.22,1.12,.1],.04);
  box(cream,[1.65,2.65,-1.99],[1.08,.98,.055],.025);
  ball(pink,[1.43,2.75,-1.947],[.28,.28,.025]);
  const art=box(leaf,[1.83,2.55,-1.94],[.25,.6,.03],.015);art.rotation.z=-.38;
  // A genuinely rounded upholstered chair with wooden feet.
  for(const x of [-.77,.77])for(const z of [-.53,.55])box(wood,[x,.35,z],[.14,.52,.14],.05);
  box(lilac,[0,.68,-.05],[2.1,.42,1.65],.2);
  box(cushion,[0,.92,0],[1.57,.28,1.42],.13);
  box(lilac,[0,1.35,-.64],[2.1,1.28,.4],.18);
  for(const x of [-.95,.95])box(lilac,[x,1.03,0],[.36,.55,1.65],.17);
  // Original plush character: cream fabric, inset face, bead eyes and padded headphones.
  const friend=new THREE.Group();friend.position.set(0,1.06,.12);scene.add(friend);
  ball(plush,[0,.4,0],[.57,.62,.44],friend);
  ball(plush,[0,1.12,-.02],[.65,.585,.52],friend);
  ball(cream,[0,1.12,.46],[.45,.38,.08],friend);
  for(const side of [-1,1]){
    ball(dark,[side*.22,1.2,.55],[.065,.081,.035],friend);
    ball(cream,[side*.22-.018,1.225,.579],[.017,.021,.008],friend);
    ball(pink,[side*.33,1.02,.543],[.085,.038,.009],friend);
    const arm=ball(plush,[side*.55,.37,.21],[.2,.39,.21],friend);arm.rotation.z=side*.2;
    ball(plush,[side*.29,-.06,.41],[.23,.2,.32],friend);
    disc(matte('#a293b2'),[side*.69,1.15,-.015],[.4,.17,.4],friend).rotation.z=Math.PI/2;
    disc(lilac,[side*.8,1.15,-.015],[.32,.12,.32],friend).rotation.z=Math.PI/2;
  }
  const smile=new THREE.Mesh(new THREE.TorusGeometry(.105,.019,8,24,Math.PI),dark);smile.rotation.z=Math.PI;smile.position.set(0,1.025,.546);friend.add(smile);
  const band=new THREE.Mesh(new THREE.TorusGeometry(.68,.09,10,40,Math.PI),lilac.soft);band.position.set(0,1.10,-.05);friend.add(band);swappable.push({m:band,...lilac});
  // Reading table and carefully separated book / ceramic details.
  disc(wood,[1.9,.64,.95],[.72,.16,.72]);disc(wood,[1.9,.34,.95],[.16,.64,.16]);
  box(matte('#94b9ad'),[1.65,.75,.98],[.62,.085,.44],.025);
  box(cream,[1.65,.797,.98],[.56,.025,.4],.01);
  const mug=disc(cream,[2.15,.87,.8],[.16,.3,.16]);
  disc(matte('#816853'),[2.15,1.022,.8],[.127,.006,.127]);
  const handle=new THREE.Mesh(new THREE.TorusGeometry(.12,.036,10,24),cream);handle.position.set(2.31,.88,.8);scene.add(handle);
  // Tall plant balances the low table without obscuring the face.
  disc(pink,[2.32,.38,-1.25],[.38,.55,.38]);disc(matte('#998370'),[2.32,.66,-1.25],[.32,.025,.32]);
  for(let i=0;i<7;i++){
    const angle=i*2.4;const b=ball(leaf,[2.32+Math.sin(angle)*.25,1+i*.12,-1.25+Math.cos(angle)*.2],[.17,.48,.11]);b.rotation.z=Math.sin(angle)*.6;
  }
  // Analytic contact decal for the fixed chair: no screen-space temporal artifacts.
  const contactCanvas=document.createElement('canvas');contactCanvas.width=contactCanvas.height=128;
  const c=contactCanvas.getContext('2d'),g=c.createRadialGradient(64,64,8,64,64,64);g.addColorStop(0,'rgba(91,69,95,.22)');g.addColorStop(1,'rgba(91,69,95,0)');c.fillStyle=g;c.fillRect(0,0,128,128);
  const contact=new THREE.Mesh(new THREE.PlaneGeometry(2.8,2.25),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(contactCanvas),transparent:true,depthWrite:false}));contact.rotation.x=-Math.PI/2;contact.position.set(0,.152,.1);scene.add(contact);
  let polished=true,front=false,clock=0,last=0;
  function treatment(value){polished=value;for(const x of swappable)x.m.material=value?x.soft:x.baseline;scene.environment=value?env.texture:null;scene.environmentIntensity=.12;ambient.intensity=value?.65:1.15;key.intensity=value?2.3:2.6;contact.visible=value;document.querySelector('#baseline').setAttribute('aria-pressed',String(!value));document.querySelector('#polished').setAttribute('aria-pressed',String(value));host.dataset.treatment=value?'polished':'baseline';}
  document.querySelector('#baseline').onclick=()=>treatment(false);document.querySelector('#polished').onclick=()=>treatment(true);
  function angle(value){front=value;document.querySelector('#front').setAttribute('aria-pressed',String(value));document.querySelector('#quarter').setAttribute('aria-pressed',String(!value));resize();}
  document.querySelector('#front').onclick=()=>angle(true);document.querySelector('#quarter').onclick=()=>angle(false);
  function resize(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;const distance=Math.max(10.8,13.5/camera.aspect);camera.position.set(front?0:distance*.53,front?3.2:4.3,front?distance:distance*.81);camera.lookAt(.15,1.35,0);camera.updateProjectionMatrix();}
  new ResizeObserver(resize).observe(host);resize();treatment(true);
  renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();document.querySelector('#fallback').hidden=false;renderer.domElement.hidden=true;host.dataset.ready='false';});
  function frame(now){requestAnimationFrame(frame);if(document.hidden||now-last<1000/30)return;const dt=Math.min(.1,(now-(last||now))/1000);last=now;const still=document.querySelector('#still').checked||reduced.matches;if(!still)clock+=dt;friend.scale.y=1+(still?0:Math.sin(clock*1.8)*.009);renderer.render(scene,camera);host.dataset.ready='true';host.dataset.motionClock=String(clock);host.dataset.still=String(still);host.dataset.drawCalls=String(renderer.info.render.calls);host.dataset.triangles=String(renderer.info.render.triangles);metrics.textContent=`${polished?'Soft studio':'Baseline'} · ${renderer.info.render.calls} draw calls · ${renderer.info.render.triangles.toLocaleString()} triangles · ${size}×${size} shared fabric texture. Synthetic art fixture.`;}
  requestAnimationFrame(frame);
}
