// Original procedural art. References set mood/proportion; no reference pixels ship.
import * as THREE from './vendor/three.module.js';
import {RoundedBoxGeometry} from './vendor/RoundedBoxGeometry.js';
import {CORE_STYLES,createCoreCharacter} from './core-characters.js';
export const PLUSH_STYLES=CORE_STYLES;
export function plushStyle(seed){return PLUSH_STYLES[(seed>>>0)%PLUSH_STYLES.length];}
export function createArtKit(){
  const sphere=new THREE.SphereGeometry(1,20,16),cylinder=new THREE.CylinderGeometry(1,1,1,20);
  const rounded=new RoundedBoxGeometry(1,1,1,2,.12);
  const sharedGeometries=new Set([sphere,cylinder,rounded]);
  const colors=new Map(),cloths=new Map();
  const size=128,data=new Uint8Array(size*size*4);let noise=45;
  for(let i=0;i<size*size;i++){noise=(Math.imul(noise,1664525)+1013904223)>>>0;const n=64+(noise>>>25)*4;data.set([n,n,n,255],i*4);}
  const grain=new THREE.DataTexture(data,size,size,THREE.RGBAFormat);grain.wrapS=grain.wrapT=THREE.RepeatWrapping;grain.repeat.set(3,3);grain.magFilter=THREE.LinearFilter;grain.minFilter=THREE.LinearMipmapLinearFilter;grain.generateMipmaps=true;grain.needsUpdate=true;
  const matte=color=>{if(!colors.has(color))colors.set(color,new THREE.MeshStandardMaterial({color,roughness:.78}));return colors.get(color);};
  const cloth=color=>{if(!cloths.has(color))cloths.set(color,new THREE.MeshPhysicalMaterial({color,roughness:.94,sheen:.65,sheenColor:'#f7e6dc',sheenRoughness:.8,bumpMap:grain,bumpScale:.035}));return cloths.get(color);};
  function mesh(geo,material,pos,scale,parent){const o=new THREE.Mesh(geo,material);o.position.set(...pos);o.scale.set(...scale);o.castShadow=Math.max(...scale)>.25;o.receiveShadow=true;parent.add(o);return o;}
  const ball=(material,pos,scale,parent)=>mesh(sphere,material,pos,scale,parent);
  const box=(material,pos,scale,parent)=>mesh(rounded,material,pos,scale,parent);
  const plush=createCoreCharacter;
  return {plush,rounded,matte,cloth,ball,box,sharedGeometries};
}
