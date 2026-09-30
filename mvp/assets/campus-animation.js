import {AnimationMixer,AnimationClip,NumberKeyframeTrack,InterpolateSmooth} from './vendor/three.module.js';
// Shared clips / independent mixers. These tracks also work on a later named glTF rig.
const specs={
 lookAround:{duration:4,headY:[0,-.2,-.2,.22,0],headZ:[0,.025,0,-.025,0]},
 headphones:{duration:3,headX:[0,.04,.065,.04,0],right:[0,-2.8,-2.8,-2.7,0],rightZ:[0,.1,.1,.08,0]},
 idle:{duration:3,bodyY:[0,.022,0],bodyX:[0,.025,0],headZ:[-.025,.025,-.025]},
 walk:{duration:.65,bodyY:[0,.065,0],left:[-.45,.45,-.45],right:[.45,-.45,.45],leftFoot:[.15,.29,.15],rightFoot:[.29,.15,.29]},
 typing:{duration:.7,bodyY:[.25,.26,.25],bodyX:[.08,.1,.08],left:[-.85,-.7,-.85],right:[-.7,-.85,-.7],footZ:[.32,.32,.32]},
 read:{duration:3,headX:[.06,.13,.06],headZ:[0,.06,0],bodyY:[.25,.25,.25],bodyX:[.12,.04,.12],left:[-.65,-.65,-.65],right:[-.65,-.65,-.65],footZ:[.32,.32,.32]},
 stretch:{duration:3,bodyY:[.25,.3,.25],bodyX:[.02,-.1,.02],left:[-.7,-2.6,-.7],right:[-.7,-2.6,-.7],footZ:[.32,.32,.32]},
 reach:{duration:2,bodyX:[0,.08,0],left:[0,-.7,0],right:[0,-1.5,0]},
 sip:{duration:2,bodyX:[0,-.06,0],left:[-.2,-.2,-.2],right:[-1.2,-2,-1.2]},
 ride:{duration:2,bodyY:[-.12,-.09,-.12],left:[-1,-1.1,-1],right:[-1,-1.1,-1],footZ:[.35,.35,.35]},
 climb:{duration:.75,left:[-1.6,-2.7,-1.6],right:[-2.7,-1.6,-2.7],leftFoot:[.15,.4,.15],rightFoot:[.4,.15,.4]},
 slide:{duration:2.4,bodyY:[-.08,-.1,-.08],bodyX:[-.12,-.2,-.12],left:[-1.3,-1.6,-1.3],right:[-1.3,-1.6,-1.3],footZ:[.38,.38,.38]},
 hang:{duration:1.2,armY:[.99,.99,.99],armScale:[2,2,2],left:[-3.05,-3.2,-3.05],right:[-3.2,-3.05,-3.2],bodyZ:[-.045,.045,-.045],leftFoot:[.2,.3,.2],rightFoot:[.3,.2,.3]},
 cheer:{duration:1.5,bodyY:[0,.18,0],bodyZ:[-.06,.06,-.06],left:[-1.8,-2.6,-1.8],right:[-1.8,-2.6,-1.8],headZ:[-.06,.06,-.06]},
 wave:{duration:1.2,left:[0,0,0],right:[-2.4,-2.9,-2.4]}
};
specs.seatedHeadphones={...specs.headphones,bodyY:[.25,.25,.25],bodyX:[.08,.08,.08],left:[-.7,-.7,-.7],footZ:[.32,.32,.32]};
const bindings={'Head.rotation[y]':'headY','RightArm.rotation[z]':'rightZ','LeftArm.scale[y]':'armScale','RightArm.scale[y]':'armScale','Head.rotation[x]':'headX','Head.rotation[z]':'headZ','Body.rotation[z]':'bodyZ','LeftArm.position[y]':'armY','RightArm.position[y]':'armY','Body.position[y]':'bodyY','Body.rotation[x]':'bodyX','LeftArm.rotation[x]':'left','RightArm.rotation[x]':'right','LeftFoot.position[y]':'leftFoot','RightFoot.position[y]':'rightFoot','LeftFoot.position[z]':'footZ','RightFoot.position[z]':'footZ'};
const defaults={leftFoot:.15,rightFoot:.15,footZ:.08,armY:.85,armScale:1};
function poseTrack(path,key,spec){
 const values=spec[key]||Array(3).fill(defaults[key]??0);
 const times=values.map((_,i)=>i*spec.duration/(values.length-1));
 return new NumberKeyframeTrack(path,times,values,InterpolateSmooth);
}
const clips=Object.entries(specs).map(([name,spec])=>new AnimationClip(name,spec.duration,Object.entries(bindings).map(([path,key])=>poseTrack(path,key,spec))));
export function animateCharacter(root){
 const mixer=new AnimationMixer(root),actions=Object.fromEntries(clips.map(c=>[c.name,mixer.clipAction(c)]));let current=null;
 return {update(pose,dt,still=false){
   if(pose!==current){const next=actions[pose]||actions.idle;next.reset().setEffectiveWeight(1).play();if(current)actions[current].crossFadeTo(next,.3,false);current=next.getClip().name;}
   if(still){mixer.stopAllAction();actions[current].reset().play();mixer.update(0)}else mixer.update(Math.max(0,Math.min(.1,dt)));
 },dispose(){mixer.stopAllAction();mixer.uncacheRoot(root)}};
}

// Decorative only. Authoritative travel/equipment poses take precedence in campus.js.
// The director clock freezes under reduced motion and the manual still control.
export function ambientPose(space,activity,clock,seed=0){
 const phase=((clock+seed%23)%32+32)%32;
 if(activity==='stale')return 'idle';
 if(space==='classroom'){
  if(activity!=='working')return 'read';
  return phase>=12&&phase<15?'seatedHeadphones':phase>=20&&phase<24?'stretch':phase>=24&&phase<28?'read':'typing';
 }
 return phase<4?'lookAround':phase>=12&&phase<15?'headphones':phase>=24&&phase<28?'wave':'idle';
}
