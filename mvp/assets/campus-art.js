// Original procedural art. References set mood/proportion; no reference pixels ship.
import * as THREE from './vendor/three.module.js';
import {RoundedBoxGeometry} from './vendor/RoundedBoxGeometry.js';
export const PLUSH_STYLES=Object.freeze([
  {name:'peach fox',color:'#efa77c',type:'fox'},
  {name:'lilac owl',color:'#b7a1d8',type:'owl'},
  {name:'mint bunny',color:'#a4c7b1',type:'bunny'},
  {name:'sky bear',color:'#a5c9db',type:'bear'},
  {name:'buttercup bear',color:'#e4c780',type:'bear'},
  {name:'rose fox',color:'#dba7bc',type:'fox'}
]);
export function plushStyle(seed){return PLUSH_STYLES[(seed>>>0)%PLUSH_STYLES.length];}
export function createArtKit(){
  const sphere=new THREE.SphereGeometry(1,20,16),cylinder=new THREE.CylinderGeometry(1,1,1,20);
  const rounded=new RoundedBoxGeometry(1,1,1,2,.12),fiber=new THREE.IcosahedronGeometry(1,0);
  const sharedGeometries=new Set([sphere,cylinder,rounded,fiber]);
  const colors=new Map(),cloths=new Map(),fiberMats=new Map();
  const size=128,data=new Uint8Array(size*size*4);let noise=45;
  for(let i=0;i<size*size;i++){noise=(Math.imul(noise,1664525)+1013904223)>>>0;const n=100+(noise>>>25);data.set([n,n,n,255],i*4);}
  const grain=new THREE.DataTexture(data,size,size,THREE.RGBAFormat);grain.wrapS=grain.wrapT=THREE.RepeatWrapping;grain.repeat.set(3,3);grain.magFilter=THREE.LinearFilter;grain.minFilter=THREE.LinearMipmapLinearFilter;grain.generateMipmaps=true;grain.needsUpdate=true;
  const matte=color=>{if(!colors.has(color))colors.set(color,new THREE.MeshStandardMaterial({color,roughness:.78}));return colors.get(color);};
  const cloth=color=>{if(!cloths.has(color))cloths.set(color,new THREE.MeshPhysicalMaterial({color,roughness:.94,sheen:.35,sheenColor:'#f7e6dc',sheenRoughness:.8,bumpMap:grain,bumpScale:.015}));return cloths.get(color);};
  function mesh(geo,material,pos,scale,parent){const o=new THREE.Mesh(geo,material);o.position.set(...pos);o.scale.set(...scale);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;}
  const ball=(material,pos,scale,parent)=>mesh(sphere,material,pos,scale,parent);
  const box=(material,pos,scale,parent)=>mesh(rounded,material,pos,scale,parent);
  // Opaque micro-fleece tufts are close-up LOD only: no alpha-shell overdraw.
  // Small rounded tufts soften the surface without projecting stiff bristles.
  function pile(color,center,radii,parent,seed,count=320){
    if(!fiberMats.has(color))fiberMats.set(color,new THREE.MeshStandardMaterial({color,roughness:1}));
    const field=new THREE.InstancedMesh(fiber,fiberMats.get(color),count),dummy=new THREE.Object3D(),normal=new THREE.Vector3(),up=new THREE.Vector3(0,1,0);
    let n=seed>>>0;const rand=()=>{n=(Math.imul(n,1664525)+1013904223)>>>0;return n/4294967296;};
    for(let i=0;i<count;i++){
      const y=rand()*2-1,angle=rand()*Math.PI*2,h=Math.sqrt(1-y*y),x=h*Math.cos(angle),z=h*Math.sin(angle);
      normal.set(x/radii[0],y/radii[1],z/radii[2]).normalize();const length=.008+rand()*.007;
      dummy.position.set(center[0]+x*radii[0],center[1]+y*radii[1],center[2]+z*radii[2]).addScaledVector(normal,length*.18);
      dummy.quaternion.setFromUnitVectors(up,normal);dummy.scale.set(length*.85,length,length*.85);dummy.updateMatrix();field.setMatrixAt(i,dummy.matrix);
    }
    field.instanceMatrix.needsUpdate=true;field.castShadow=false;field.receiveShadow=false;parent.add(field);return field;
  }
  function plush(seed){
    const style=plushStyle(seed),skin=cloth(style.color),cream=cloth('#f3e6cf'),pink=matte('#e7aaa7');
    const fibers=[],root=new THREE.Group(),body=new THREE.Group(),head=new THREE.Group();body.name='Body';head.name='Head';root.add(body);body.add(head);
    ball(skin,[0,.62,0],[.36,.46,.29],body);fibers.push(pile(style.color,[0,.62,0],[.36,.46,.29],body,seed,700));
    ball(cream,[0,.59,.235],[.255,.32,.095],body);
    ball(skin,[0,1.21,0],[.47,.43,.37],head);fibers.push(pile(style.color,[0,1.21,0],[.47,.43,.37],head,seed+7,1100));
    if(style.type==='fox'){
      for(const side of [-1,1]){const ear=ball(skin,[side*.31,1.61,0],[.17,.25,.13],head);ear.rotation.z=-side*.27;ball(cream,[side*.32,1.64,.085],[.095,.16,.07],head);ball(cream,[side*.19,1.08,.3],[.245,.18,.095],head);}
      const tail=ball(skin,[.2,.52,-.26],[.19,.27,.29],body);tail.rotation.z=-.5;
      ball(cream,[.32,.63,-.43],[.12,.16,.13],body);
    }else if(style.type==='owl'){
      for(const side of [-1,1]){const tuft=ball(skin,[side*.34,1.56,-.01],[.11,.2,.1],head);tuft.rotation.z=-side*.45;ball(cream,[side*.18,1.22,.31],[.22,.24,.08],head);}
    }else for(const side of [-1,1]){
      const tall=style.type==='bunny';ball(skin,[side*.29,tall?1.67:1.55,0],[.14,tall?.32:.15,.12],head);ball(pink,[side*.29,tall?1.69:1.57,.08],[.078,tall?.21:.075,.045],head);
    }
    const eyes=[],eyeMat=new THREE.MeshPhysicalMaterial({color:'#252331',roughness:.15,clearcoat:1,clearcoatRoughness:.08});
    for(const side of [-1,1]){
      const eye=new THREE.Group();eye.position.set(side*.17,1.23,.375);head.add(eye);eyes.push(eye);
      ball(eyeMat,[0,0,0],[.063,.077,.035],eye);ball(matte('#fff9e9'),[-.018,.025,.027],[.018,.022,.008],eye);ball(matte('#fff9e9'),[.019,-.025,.03],[.007,.009,.004],eye);
      ball(pink,[side*.29,1.08,.319],[.08,.043,.023],head);
    }
    ball(matte(style.type==='owl'?'#cf9861':'#8d655f'),[0,1.115,.399],[.045,style.type==='owl'?.06:.027,.032],head);
    const smile=new THREE.Mesh(new THREE.TorusGeometry(.064,.009,5,12,Math.PI),matte('#86685f'));smile.rotation.z=Math.PI;smile.position.set(0,1.08,.4);head.add(smile);
    const arms=[-1,1].map((side,i)=>{const p=new THREE.Group();p.name=i?'RightArm':'LeftArm';p.position.set(side*.39,.85,0);body.add(p);ball(skin,[0,-.19,0],[.14,.27,.15],p);ball(cream,[0,-.36,.065],[.10,.095,.095],p);return p;});
    const feet=[-1,1].map((side,i)=>{const p=ball(skin,[side*.2,.15,.08],[.18,.16,.23],root);p.name=i?'RightFoot':'LeftFoot';return p;});
    // Headphone shape and all animation node names/pivots preserve the rig contract.
    for(const side of [-1,1]){ball(matte('#e7d7cc'),[side*.47,1.21,0],[.115,.205,.21],head);ball(matte('#bdaacf'),[side*.54,1.21,0],[.065,.15,.16],head);}
    const band=new THREE.Mesh(new THREE.TorusGeometry(.485,.044,8,24,Math.PI),matte('#c4b0d4'));band.position.set(0,1.2,0);head.add(band);
    const mug=new THREE.Group();mug.position.set(0,-.43,.05);arms[1].add(mug);
    mesh(cylinder,matte('#f7ebd8'),[0,0,0],[.11,.18,.11],mug);mesh(cylinder,matte('#87664e'),[0,.093,0],[.085,.008,.085],mug);
    const handle=new THREE.Mesh(new THREE.TorusGeometry(.075,.025,6,10),matte('#f7ebd8'));handle.position.set(.11,0,0);mug.add(handle);mug.visible=false;
    head.position.y=.98;for(const child of head.children)child.position.y-=.98;
    root.userData.artStyle=style.name;
    return {root,body,head,eyes,arms,feet,mug,fibers,dispose(){root.traverse(o=>{if(o.isInstancedMesh)o.dispose();if(o.geometry&&!sharedGeometries.has(o.geometry))o.geometry.dispose();});eyeMat.dispose();}};
  }
  return {plush,rounded,matte,cloth,ball,box,sharedGeometries};
}
