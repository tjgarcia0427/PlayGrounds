import * as THREE from '../../mvp/assets/vendor/three.module.js';
const canvas=document.querySelector('canvas'),fallback=document.querySelector('#fallback');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const palettes={peach:['#ba6e58','#ffc6a3'],blue:['#36569d','#9dcfff'],lilac:['#76539d','#dfbcf7']};
// Original shell-fur implementation. No reference-site code or assets are bundled.
const vertex=`
attribute float layer;
uniform float layers,coat,time,compression;
varying vec2 tex;
varying float height;
varying vec3 worldNormal,viewPosition;
void main(){
 height=layer/(layers-1.); tex=uv;
 vec3 n=normalize(normal);
 float wave=sin(position.y*7.+position.x*4.+time*1.8)*.14;
 vec3 bend=vec3(wave,-.28,cos(position.x*6.+time)*.1);
 vec3 p=position+(n+bend*height)*coat*height;
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
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(32,1,.1,30);
 const character=new THREE.Group();scene.add(character);
 const base=new THREE.SphereGeometry(1,80,56),pos=base.attributes.position;
 for(let i=0;i<pos.count;i++){
  const x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i);
  // Broad continuous cloud lobes rather than a collection of intersecting spheres.
  const angle=Math.atan2(y,x);
  const lobes=1.+.105*Math.cos(angle*5.+.45)*Math.pow(Math.max(0.,1.-z*z),2.);
  pos.setXYZ(i,x*lobes*1.04,y*lobes*.91,z*.78*lobes);
 }base.computeVertexNormals();
 const geometry=new THREE.InstancedBufferGeometry();geometry.index=base.index;
 for(const [name,attribute] of Object.entries(base.attributes))geometry.setAttribute(name,attribute);
 geometry.setAttribute('layer',new THREE.InstancedBufferAttribute(Float32Array.from({length:64},(_,i)=>i),1));geometry.instanceCount=64;
 const uniforms={layers:{value:64},coat:{value:.16},time:{value:0},compression:{value:0},rootColor:{value:new THREE.Color(palettes.peach[0])},tipColor:{value:new THREE.Color(palettes.peach[1])}};
 const material=new THREE.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,uniforms});
 const fur=new THREE.Mesh(geometry,material);fur.frustumCulled=false;character.add(fur);
 const face=new THREE.Group();character.add(face);
 scene.add(new THREE.HemisphereLight(0xffffff,0xb1a0b1,2.5));
 const light=new THREE.DirectionalLight(0xffffff,3.);light.position.set(-3,5,5);scene.add(light);
 const eyeMaterial=new THREE.MeshPhysicalMaterial({color:'#15101c',roughness:.18,clearcoat:1.});
 for(const x of[-.27,.27]){
  const eye=new THREE.Mesh(new THREE.SphereGeometry(1,28,20),eyeMaterial);
  eye.position.set(x,.12,.835);eye.scale.set(.083,.13,.07);face.add(eye);
  const glint=new THREE.Mesh(new THREE.SphereGeometry(.021,12,8),new THREE.MeshBasicMaterial({color:'white'}));glint.position.set(x-.022,.16,.90);face.add(glint);
 }
 // Soft analytic contact shadow, never a downloaded texture.
 const shadow=new THREE.Mesh(new THREE.PlaneGeometry(3.4,2.6),new THREE.ShaderMaterial({transparent:true,depthWrite:false,vertexShader:'varying vec2 t; void main(){t=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec2 t;void main(){vec2 p=(t-.5)*2.;float a=exp(-dot(p,p)*5.)*.13;gl_FragColor=vec4(.29,.23,.32,a);}' }));shadow.rotation.x=-Math.PI/2;shadow.position.y=-1.11;scene.add(shadow);
 let still=reduced.matches,c=0,velocity=0,elapsed=0,previous=performance.now(),frames=0;
 function setStill(){document.querySelector('#still').setAttribute('aria-pressed',String(still));if(still){c=velocity=0;uniforms.compression.value=0;}}
 setStill();reduced.addEventListener('change',()=>{still=reduced.matches;setStill();});
 function squish(){if(!still){velocity=3.8;}}
 document.querySelector('#squish').onclick=squish;canvas.addEventListener('pointerdown',squish);
 document.querySelector('#still').onclick=()=>{still=!still;setStill();};
 document.querySelector('#fluff').oninput=e=>uniforms.coat.value=Number(e.target.value);
 document.querySelector('#quality').onchange=e=>{const n=Number(e.target.value);geometry.instanceCount=n;uniforms.layers.value=n;};
 for(const b of document.querySelectorAll('[data-palette]'))b.onclick=()=>{for(const p of document.querySelectorAll('[data-palette]'))p.setAttribute('aria-pressed',String(p===b));const colors=palettes[b.dataset.palette];uniforms.rootColor.value.set(colors[0]);uniforms.tipColor.value.set(colors[1]);};
 function resize(){const box=canvas.parentElement.getBoundingClientRect();renderer.setSize(box.width,box.height,false);camera.aspect=box.width/box.height;camera.position.set(0,.18,Math.max(5.4,3.15/camera.aspect));camera.lookAt(0,-.03,0);camera.updateProjectionMatrix();}new ResizeObserver(resize).observe(canvas.parentElement);resize();
 renderer.setAnimationLoop(now=>{
  const dt=Math.min((now-previous)/1000,.033);previous=now;
  if(!still){elapsed+=dt;velocity+=(-95*c-8*velocity)*dt;c=Math.max(-.16,Math.min(.4,c+velocity*dt));}
  uniforms.time.value=elapsed;uniforms.compression.value=c;
  character.rotation.y=Number(document.querySelector('#turn').value)/100*1.5;
  character.rotation.z=still?0:Math.sin(elapsed*.9)*.015;
  // Face follows exactly the same global deformation as fur.
  const sy=1-c,sx=1/Math.sqrt(sy);face.scale.set(sx,sy,sx);face.position.y=-c*.87;
  renderer.render(scene,camera);frames++;
  window.furStudy={ready:true,frames,compression:c,time:elapsed,still,shells:geometry.instanceCount,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};
 });
}catch(error){fallback.hidden=false;canvas.hidden=true;document.querySelector('#squish').disabled=true;window.furStudy={ready:false,fallback:true};console.warn('WebGL unavailable');}
