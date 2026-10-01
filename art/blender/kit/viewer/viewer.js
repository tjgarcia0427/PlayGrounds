import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';
import {animateCharacter} from '/mvp/assets/campus-animation.js';
const stage=document.querySelector('.stage'),status=document.querySelector('#status'),still=document.querySelector('#still'),motion=document.querySelector('#motion');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const manifest=await (await fetch('../manifest.json')).json();
let renderer,scene,camera,content,mixers=[],directors=[],loaded=[],generation=0,currentGroup='character',currentId=null,clock=0,last=performance.now(),ready=false;
const cache=new Map(),loader=new GLTFLoader();
const title=id=>id.split('-').map(s=>s[0].toUpperCase()+s.slice(1)).join(' ');
const diagnostic={ready:false,error:null,group:currentGroup,ids:[],clock:0,poses:[],drawCalls:0};
window.assetQA=diagnostic; // Read-only observation surface; controls remain public DOM.
try{
 renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor('#eee6de');renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.3;
 stage.append(renderer.domElement);renderer.domElement.setAttribute('aria-label','Exported Blender assets');scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(35,1,.01,150);
 scene.add(new THREE.HemisphereLight('#fff7ec','#b5a4b8',2.5));const key=new THREE.DirectionalLight('#fff3e4',3.2);key.position.set(-3,5,4);scene.add(key);const fill=new THREE.DirectionalLight('#e2eaff',1.7);fill.position.set(4,3,-3);scene.add(fill);
 const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:'#e8dfd5',roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.025;scene.add(floor);
 content=new THREE.Group();scene.add(content);new ResizeObserver(resize).observe(stage);
 renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();fallback('WebGL context lost. Downloads remain available.');});
}catch(error){fallback('WebGL unavailable. Downloads remain available.');}
function fallback(text){ready=false;diagnostic.error=text;document.querySelector('#fallback').hidden=false;renderer?.domElement.remove();status.textContent=text;}
function resize(){if(!renderer)return;const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();if(ready)frame();}
function frame(){
 const box=new THREE.Box3().setFromObject(content),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
 const angle={front:0,quarter:.52,side:Math.PI/2,back:Math.PI}[document.querySelector('#view').value];
 const span=Math.max(size.y,size.x/camera.aspect,size.z*.75,.3),distance=span/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))*1.4;
 camera.position.set(center.x+Math.sin(angle)*distance,center.y+distance*.20,center.z+Math.cos(angle)*distance);camera.lookAt(center);camera.updateProjectionMatrix();
}
function list(){const host=document.querySelector('.assets');host.replaceChildren();for(const a of manifest.assets.filter(a=>a.kind===currentGroup)){
 const button=document.createElement('button');button.dataset.id=a.id;button.setAttribute('aria-pressed',String(currentId===a.id));button.append(document.createTextNode(title(a.id)));const small=document.createElement('small');small.textContent=`${(a.triangles/1000).toFixed(1)}k triangles`;button.append(small);button.onclick=()=>show(a.id);host.append(button);
}}
async function show(id=null){
 currentId=id;list();const entries=id?manifest.assets.filter(a=>a.id===id):manifest.assets.filter(a=>a.kind===currentGroup);
 document.querySelector('#title').textContent=id?title(id):{character:'The companion family',playground:'Playground objects','study-hall':'Study Hall objects'}[currentGroup];
 document.querySelector('#description').textContent=id?entries[0].description:'A scale-normalized collection view. Select an object to inspect its individual proportions.';
 document.querySelector('#triangles').textContent=entries.reduce((n,a)=>n+a.triangles,0).toLocaleString();document.querySelector('#bytes').textContent=(entries.reduce((n,a)=>n+a.bytes,0)/1024).toFixed(0)+' KiB';
 const links=document.querySelector('#downloads');links.replaceChildren();if(id)for(const ext of ['glb','blend']){const a=document.createElement('a');a.href=`../assets/${id}.${ext}`;a.download='';a.textContent=ext.toUpperCase()+' ';links.append(a);}
 if(!renderer||diagnostic.error)return;
 const thisGeneration=++generation;ready=false;diagnostic.ready=false;status.textContent='Loading exported geometry…';
 try{
 const resources=await Promise.all(entries.map(async a=>{if(!cache.has(a.id))cache.set(a.id,loader.loadAsync(`../assets/${a.id}.glb`));return await cache.get(a.id);}));
 if(thisGeneration!==generation)return;
 for(const d of directors)d.dispose();for(const m of mixers){m.stopAllAction();m.uncacheRoot(m.getRoot());}directors=[];mixers=[];loaded=[];content.clear();clock=0;
 for(let i=0;i<entries.length;i++){
   const a=entries[i],resource=resources[i],object=resource.scene.clone(true),pivot=new THREE.Group();pivot.add(object);content.add(pivot);
   if(!id){const box=new THREE.Box3().setFromObject(object),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());const scale=currentGroup==='character'?1:1.6/Math.max(size.x,size.y,size.z);object.scale.setScalar(scale);object.position.set(-center.x*scale,-box.min.y*scale,-center.z*scale);const cols=currentGroup==='character'?3:4;pivot.position.set((i%cols-(Math.min(cols,entries.length)-1)/2)*1.9,0,Math.floor(i/cols)*2.2);}
   const mixer=new THREE.AnimationMixer(object);for(const clip of resource.animations)mixer.clipAction(clip).play();mixers.push(mixer);
   directors.push(a.kind==='character'?animateCharacter(object):{update(){},dispose(){}});loaded.push({object,a,resource});
 }
 applyMotion();ready=true;diagnostic.ready=true;diagnostic.ids=entries.map(a=>a.id);diagnostic.group=currentGroup;frame();status.textContent=`${entries.length} exported ${entries.length===1?'asset':'assets'} ready · ${reduced.matches?'reduced motion':'synthetic study'}`;
 }catch(error){fallback('Asset load failed: '+error.message);}
}
function applyMotion(){for(let i=0;i<loaded.length;i++){
 const {object,a,resource}=loaded[i];mixers[i].stopAllAction();directors[i].dispose();directors[i]=a.kind==='character'?animateCharacter(object):{update(){},dispose(){}};
 // Restore exported rotation channels before switching to campus Euler-driven gestures.
 for(const name of ['Head','Tail']){const o=object.getObjectByName(name);if(o)o.quaternion.identity();}
 if(motion.value==='study'){for(const clip of resource.animations)mixers[i].clipAction(clip).reset().play();}
 else if(a.kind==='character')directors[i].update(motion.value,0,true);
 }clock=0;
}
document.querySelectorAll('[data-group]').forEach(b=>b.onclick=()=>{currentGroup=b.dataset.group;document.querySelectorAll('[data-group]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));show();});
document.querySelector('#collection').onclick=()=>show();document.querySelector('#view').onchange=()=>{if(ready)frame();};motion.onchange=applyMotion;
reduced.addEventListener('change',()=>{last=performance.now();});
function tick(now){requestAnimationFrame(tick);const dt=Math.min(.05,(now-last)/1000);last=now;if(!renderer||!ready||document.hidden||diagnostic.error)return;
 const freeze=still.checked||reduced.matches;if(!freeze){clock+=dt;for(let i=0;i<loaded.length;i++){if(motion.value==='study')mixers[i].update(dt);else directors[i].update(motion.value,dt);}}
 renderer.render(scene,camera);diagnostic.clock=clock;diagnostic.drawCalls=renderer.info.render.calls;diagnostic.poses=loaded.map(({object,a})=>({id:a.id,head:object.getObjectByName('Head')?.quaternion.toArray(),arm:object.getObjectByName('RightArm')?.rotation.toArray().slice(0,3),tail:object.getObjectByName('Tail')?.quaternion.toArray(),deck:object.getObjectByName('RotatingDeck')?.quaternion.toArray()}));document.querySelector('#drawcalls').textContent=renderer.info.render.calls.toLocaleString();
}
list();show();requestAnimationFrame(tick);
