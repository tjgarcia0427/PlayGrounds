import * as THREE from '../../mvp/assets/vendor/three.module.js';
const canvas=document.querySelector('canvas'),fallback=document.querySelector('#fallback');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const palettes={peach:['#ba6e58','#ffc6a3'],blue:['#36569d','#9dcfff'],lilac:['#76539d','#dfbcf7']};
// Original shell-fur implementation. No reference-site code or assets are bundled.
const vertex=`
attribute float layer;
uniform float layers,coat,time,compression;
uniform vec3 partScale,partOffset;
varying vec2 tex;
varying float height;
varying vec3 worldNormal,viewPosition;
void main(){
 height=layer/(layers-1.); tex=uv;
 vec3 n=normalize(normal);
 float wave=sin(position.y*7.+position.x*4.+time*1.8)*.14;
 vec3 bend=vec3(wave,-.28,cos(position.x*6.+time)*.1);
 // Keep short fur around the two eye sockets so the coat cannot cover the eyes.
 vec3 surfacePoint=position*partScale+partOffset;
 float sockets=min(length(surfacePoint-vec3(-.27,.12,.75)),length(surfacePoint-vec3(.27,.12,.75)));
 float grooming=mix(.12,1.,smoothstep(.10,.24,sockets));
 vec3 p=position+(n+bend*height)*coat*height*grooming;
 float sy=1.-compression;
 float sx=inversesqrt(sy);
 p*=vec3(sx,sy,sx);
 // Flatten the lower body slightly during compression, maintaining its ground contact.
 p.y-=compression*.87;
 vec3 deformedNormal=normalize(n/vec3(sx,sy,sx));
 worldNormal=normalize(normalMatrix*deformedNormal);
 vec4 mv=modelViewMatrix*vec4(p,1.);
 viewPosition=-mv.xyz;
 gl_Position=projectionMatrix*mv;
}`;
const fragment=`
uniform vec3 rootColor,tipColor;
varying vec2 tex;
varying float height;
varying vec3 worldNormal,viewPosition;
float random(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){
 // Latitude rows with circumference-adjusted columns: continuous wrapping at the seam.
 float row=tex.y*170.; float coverage=0.; float shade=.5;
 for(int dy=-1;dy<=1;dy++){
  float ry=floor(row)+float(dy);
  float circumference=max(4.,floor(340.*sin(3.14159265*(ry+.5)/170.)));
  float col=tex.x*circumference;
  for(int dx=-1;dx<=1;dx++){
   float cx=floor(col)+float(dx);
   vec2 id=vec2(mod(cx+circumference,circumference),ry);
   float seed=random(id);
   vec2 jitter=vec2(seed,random(id+31.))* .65+.175;
   float strandLength=.48+.52*random(id+67.);
   float h=height/strandLength;
   vec2 curl=vec2(sin(seed*35.+h*2.8),cos(seed*19.+h*2.8))*.24*h*h;
   vec2 delta=vec2(col-cx,row-ry)-jitter-curl;
   float width=mix(.36,.095,clamp(h,0.,1.));
   float aa=max(.025,length(vec2(dFdx(col),dFdy(row)))*.65);
   float a=(1.-smoothstep(width-aa,width+aa,length(delta)))*step(h,1.);
   if(a>coverage){coverage=a;shade=seed;}
  }
 }
 if(height>.001 && coverage<.48)discard;
 vec3 N=normalize(worldNormal),V=normalize(viewPosition);
 vec3 L=normalize(vec3(-.6,1.,1.3));
 float diffuse=pow(clamp((dot(N,L)+.65)/1.65,0.,1.),1.4);
 float rim=pow(1.-max(dot(N,V),0.),3.);
 vec3 color=mix(rootColor,tipColor,pow(height,.55));
 color*=mix(.79,1.06,shade)*(.66+.55*diffuse)*mix(.7,1.,height);
 color+=tipColor*rim*.32*smoothstep(.25,1.,height);
 gl_FragColor=vec4(color,1.);
 #include <tonemapping_fragment>
 #include <colorspace_fragment>
}`;
try{
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
 renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor('#ffffff');
 renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(32,1,.1,40);
 const character=new THREE.Group();scene.add(character);
 scene.add(new THREE.HemisphereLight(0xffffff,0xb1a0b1,2.5));
 const light=new THREE.DirectionalLight(0xffffff,3.);light.position.set(-3,5,5);scene.add(light);
 let dirty=true,model='dot',accessory='signature',generation=0,furParts=[];
 let still=reduced.matches,c=0,velocity=0,elapsed=0,previous=performance.now(),frames=0;
 const signatures={dot:palettes.peach,rabbit:['#89749e','#e5cff7'],turtle:['#477c61','#b9e2aa'],monkey:['#88543a','#d5a277'],bird:palettes.blue};
 const descriptions={dot:'Dot version · over-ear headphones or wired earbuds',rabbit:'Animal version · rabbit / lavender studio headphones',turtle:'Animal version · turtle / round glasses & coral bandana',monkey:'Animal version · monkey / teal beanie & wired earbuds',bird:'Animal version · bird / aviator frames & lilac scarf'};
 const material=(color,roughness=.55,metalness=0)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
 function mesh(g,m,p=[0,0,0],s=[1,1,1]){const o=new THREE.Mesh(g,m);o.position.set(...p);o.scale.set(...s);character.add(o);return o;}
 function ball(p,s,color){return mesh(new THREE.SphereGeometry(1,28,20),material(color),p,s);}
 function tube(points,radius,color){return mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),48,radius,10,false),material(color));}
 function ring(p,radius,width,color){return mesh(new THREE.TorusGeometry(radius,width,12,48),material(color,.28,.55),p);}
 function furBall(p,scale,colors,coat=.16,cloud=false){
  const base=new THREE.SphereGeometry(1,cloud?80:40,cloud?56:28),pos=base.attributes.position;
  for(let i=0;i<pos.count;i++){
   const x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i);
   const bump=cloud?1.+.105*Math.cos(Math.atan2(y,x)*5.+.45)*Math.pow(Math.max(0.,1.-z*z),2.):1.;
   pos.setXYZ(i,x*bump,y*bump,z*bump);
  }base.computeVertexNormals();
  const g=new THREE.InstancedBufferGeometry();g.index=base.index;
  for(const [name,attribute] of Object.entries(base.attributes))g.setAttribute(name,attribute);
  g.setAttribute('layer',new THREE.InstancedBufferAttribute(Float32Array.from({length:64},(_,i)=>i),1));g.instanceCount=Number(document.querySelector('#quality').value);
  const u={partScale:{value:new THREE.Vector3(...scale)},partOffset:{value:new THREE.Vector3(...p)},layers:{value:g.instanceCount},coat:{value:coat},time:{value:elapsed},compression:{value:0},rootColor:{value:new THREE.Color(colors[0])},tipColor:{value:new THREE.Color(colors[1])}};
  const o=mesh(g,new THREE.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,uniforms:u}),p,scale);o.frustumCulled=false;
  furParts.push({object:o,uniforms:u,coat});return o;
 }
 function eyes(){
  for(const x of[-.27,.27]){
   mesh(new THREE.SphereGeometry(1,28,20),new THREE.MeshPhysicalMaterial({color:'#15101c',roughness:.18,clearcoat:1.}),[x,.12,.87],[.083,.13,.07]);
   mesh(new THREE.SphereGeometry(.021,12,8),new THREE.MeshBasicMaterial({color:'white'}),[x-.022,.16,.935]);
  }
 }
 function headphones(width=1.06,y=.13){
  tube([[-width,y,-.08],[-width*.98,y+.6,-.13],[-width*.65,y+1.0,-.18],[0,y+1.12,-.20],[width*.65,y+1.0,-.18],[width*.98,y+.6,-.13],[width,y,-.08]],.065,'#38364c');
  for(const sign of[-1,1]){
   ball([sign*width,y,.06],[.19,.30,.28],'#38364c');
   ball([sign*(width+.09),y,.13],[.13,.245,.235],'#a898cc');
   ball([sign*(width+.14),y+.07,.32],[.045,.065,.025],'#eee8ff');
  }
 }
 function earbuds(width=.84,color='#fff6df'){
  for(const sign of[-1,1]){
   ball([sign*width,.08,.57],[.11,.13,.10],color);
   ball([sign*width,-.08,.63],[.046,.16,.046],color);
   tube([[sign*width,-.18,.64],[sign*.78,-.46,.80],[sign*.40,-.66,.96],[.06,-.75,.96]],.014,color);
  }
  tube([[.06,-.75,.96],[.1,-.94,.89],[.4,-.92,.88],[.43,-.67,.99]],.014,color);
  ball([.43,-.65,.97],[.14,.20,.045],'#6c657d');
  ball([.43,-.62,1.015],[.094,.10,.012],'#bce0d0');
  ball([.43,-.78,1.015],[.03,.03,.012],'#fdf4e9');
 }
 function glasses(color='#b58c51',radius=.20){
  for(const x of[-.27,.27])ring([x,.12,.997],radius,.018,color);
  tube([[-.07,.13,.997],[0,.18,1.005],[.07,.13,.997]],.016,color);
  tube([[-.47,.15,.99],[-.73,.22,.75],[-.87,.21,.22]],.014,color);
  tube([[.47,.15,.99],[.73,.22,.75],[.87,.21,.22]],.014,color);
 }
 function scarf(color){
  const r=ring([0,-.57,.05],.62,.085,color);r.rotation.x=Math.PI/2;r.scale.z=.85;
  const tail=ball([.40,-.73,.68],[.14,.30,.065],color);tail.rotation.z=-.3;
  ball([.43,-.52,.74],[.14,.12,.10],color);
 }
 function build(){
  const geometries=new Set(),materials=new Set();character.traverse(o=>{if(o.isMesh){geometries.add(o.geometry);materials.add(o.material);}});
  character.clear();for(const g of geometries)g.dispose();for(const m of materials)m.dispose();furParts=[];
  const colors=signatures[model];
  if(model==='dot')furBall([0,0,0],[1.04,.91,.78],colors,.16,true);
  if(model==='rabbit'){
   furBall([0,-.08,0],[.80,.87,.78],colors);
   for(const sign of[-1,1]){
    const ear=furBall([sign*.35,1.05,-.03],[.21,.72,.24],colors,.12);ear.rotation.z=-sign*.14;
    const inner=ball([sign*.38,1.09,.20],[.105,.50,.035],'#efb5c8');inner.rotation.z=-sign*.14;
    furBall([sign*.40,-.88,.25],[.27,.18,.32],colors,.12);
   }
   for(const x of[-.12,.12])furBall([x,-.16,.79],[.16,.13,.09],['#ceb7b7','#fff5e9'],.065);
   ball([0,-.07,.92],[.07,.045,.035],'#9f6678');
  }
  if(model==='turtle'){
   // A real domed shell behind the soft head, with discrete raised scutes.
   ball([0,-.14,-.25],[1.07,.91,.65],'#567b60');
   const rim=ring([0,-.14,.08],.94,.065,'#c5ae7e');rim.scale.set(1.08,.91,1);
   for(const sign of[-1,1]){
    ball([sign*.82,-.14,.12],[.25,.34,.15],'#769878');
    furBall([sign*.66,-.79,.24],[.31,.22,.33],colors,.12);
    furBall([sign*.94,-.36,.18],[.23,.30,.25],colors,.12);
   }
   furBall([0,.07,.24],[.75,.77,.58],colors,.16);
   ball([0,-.29,.82],[.24,.095,.07],'#c5deb2');
  }
  if(model==='monkey'){
   tube([[.66,-.68,-.35],[1.10,-.50,-.25],[1.36,.10,-.18],[1.25,.47,-.10],[1.04,.44,-.06],[1.03,.23,-.02]],.095,'#a87955');
   furBall([0,-.06,0],[.82,.88,.76],colors);
   for(const sign of[-1,1]){
    furBall([sign*.89,.17,.02],[.36,.39,.27],colors,.12);
    ball([sign*.92,.18,.27],[.22,.25,.055],'#eac8a4');
    furBall([sign*.41,-.85,.23],[.26,.17,.28],colors,.12);
   }
   furBall([0,-.01,.69],[.58,.52,.13],['#c5a181','#f4d6b2'],.045);
   ball([0,-.19,.86],[.12,.067,.07],'#755744');
  }
  if(model==='bird'){
   furBall([0,-.02,0],[.85,.92,.77],colors);
   for(const sign of[-1,1]){
    const wing=furBall([sign*.78,-.24,.02],[.24,.48,.36],colors,.14);wing.rotation.z=sign*.38;
    ball([sign*.33,-.92,.23],[.24,.105,.22],'#dfaa59');
   }
   for(let i=0;i<3;i++){const tuft=furBall([-.16+i*.14,.87+i*.035,-.04],[.11,.29,.13],colors,.12);tuft.rotation.z=-.3+i*.22;}
   ball([0,-.13,.88],[.18,.105,.21],'#e6b154');
   ball([0,-.20,.87],[.13,.055,.16],'#bd7d3b');
  }
  eyes();
  if(accessory==='headphones'||(accessory==='signature'&&(model==='dot'||model==='rabbit')))headphones(model==='rabbit'?.87:1.06,model==='rabbit'?.25:.13);
  if(accessory==='earbuds'||(accessory==='signature'&&model==='monkey'))earbuds(model==='monkey'?.98:.84,model==='monkey'?'#f7ce91':'#fff6df');
  if(accessory==='signature'){
   if(model==='turtle'){glasses('#a87640',.215);scarf('#cf887c');}
   if(model==='bird'){glasses('#bd985b',.20);scarf('#ac91c4');}
   if(model==='monkey'){
    mesh(new THREE.SphereGeometry(1,36,24,0,Math.PI*2,0,Math.PI/2),material('#447b7c'),[0,.62,-.06],[.77,.46,.69]);
    const brim=ring([0,.64,-.06],.72,.075,'#346467');brim.rotation.x=Math.PI/2;brim.scale.y=.9;
    ball([.24,.81,.56],[.13,.10,.024],'#e9c785');
   }
  }
  generation++;dirty=true;c=velocity=0;
  document.querySelector('#designName').textContent=model==='dot'?'Dot version':`Animal version · ${model[0].toUpperCase()+model.slice(1)}`;
  document.querySelector('#designDescription').textContent=descriptions[model];
 }
 const shadow=new THREE.Mesh(new THREE.PlaneGeometry(3.7,2.6),new THREE.ShaderMaterial({transparent:true,depthWrite:false,vertexShader:'varying vec2 t; void main(){t=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec2 t;void main(){vec2 p=(t-.5)*2.;float a=exp(-dot(p,p)*5.)*.13;gl_FragColor=vec4(.29,.23,.32,a);}' }));shadow.rotation.x=-Math.PI/2;shadow.position.y=-1.13;scene.add(shadow);
 function setStill(){dirty=true;document.querySelector('#still').setAttribute('aria-pressed',String(still));if(still)c=velocity=0;}
 setStill();reduced.addEventListener('change',()=>{still=reduced.matches;setStill();});
 const squish=()=>{if(!still)velocity=3.8;};document.querySelector('#squish').onclick=squish;canvas.addEventListener('pointerdown',squish);
 document.querySelector('#still').onclick=()=>{still=!still;setStill();};
 document.querySelector('#fluff').oninput=()=>dirty=true;document.querySelector('#turn').oninput=()=>dirty=true;
 document.querySelector('#quality').onchange=e=>{const n=Number(e.target.value);for(const f of furParts){f.object.geometry.instanceCount=n;f.uniforms.layers.value=n;}dirty=true;};
 document.querySelector('#model').onchange=e=>{model=e.target.value;build();};
 document.querySelector('#accessory').onchange=e=>{accessory=e.target.value;build();};
 for(const b of document.querySelectorAll('[data-palette]'))b.onclick=()=>{for(const p of document.querySelectorAll('[data-palette]'))p.setAttribute('aria-pressed',String(p===b));const colors=palettes[b.dataset.palette];for(const f of furParts){f.uniforms.rootColor.value.set(colors[0]);f.uniforms.tipColor.value.set(colors[1]);}dirty=true;};
 function resize(){dirty=true;const box=canvas.parentElement.getBoundingClientRect();renderer.setSize(box.width,box.height,false);camera.aspect=box.width/box.height;camera.position.set(0,.53,Math.max(7.1,6.6/camera.aspect+1.));camera.lookAt(0,.38,0);camera.updateProjectionMatrix();}new ResizeObserver(resize).observe(canvas.parentElement);resize();build();
 renderer.setAnimationLoop(now=>{
  const dt=Math.min((now-previous)/1000,.033);previous=now;if(still&&!dirty)return;dirty=false;
  if(!still){elapsed+=dt;velocity+=(-95*c-8*velocity)*dt;c=Math.max(-.16,Math.min(.4,c+velocity*dt));}
  for(const f of furParts){f.uniforms.time.value=elapsed;f.uniforms.coat.value=f.coat*Number(document.querySelector('#fluff').value)/.16;}
  character.rotation.y=Number(document.querySelector('#turn').value)/100*1.5;character.rotation.z=still?0:Math.sin(elapsed*.9)*.015;
  const sy=1-c,sx=1/Math.sqrt(sy);character.scale.set(sx,sy,sx);character.position.y=-c*.87;
  renderer.render(scene,camera);frames++;
  const left=new THREE.Vector3(-1.65,0,1.1).project(camera).x,right=new THREE.Vector3(1.65,0,1.1).project(camera).x;
  const top=new THREE.Vector3(0,2.0,1.1).project(camera).y,bottom=new THREE.Vector3(0,-1.2,1.1).project(camera).y;
  window.furStudy={ready:true,model,accessory,generation,viewportWidth:canvas.clientWidth,framing:[left,right,top,bottom],frames,compression:c,time:elapsed,still,shells:Number(document.querySelector('#quality').value),drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};
 });
}catch(error){fallback.hidden=false;canvas.hidden=true;document.querySelector('#squish').disabled=true;window.furStudy={ready:false,fallback:true};console.warn('WebGL unavailable');}
