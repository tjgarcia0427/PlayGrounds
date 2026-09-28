import {AnimationMixer,AnimationClip,NumberKeyframeTrack,InterpolateSmooth} from './vendor/three.module.js';
// Shared clips / independent mixers. These tracks also work on a later named glTF rig.
const specs={
 idle:{duration:3,bodyY:[0,.022,0],bodyX:[0,.025,0]},
 walk:{duration:.65,bodyY:[0,.065,0],left:[-.45,.45,-.45],right:[.45,-.45,.45],leftFoot:[.15,.29,.15],rightFoot:[.29,.15,.29]},
 typing:{duration:.7,bodyY:[.25,.26,.25],bodyX:[.08,.1,.08],left:[-.85,-.7,-.85],right:[-.7,-.85,-.7],footZ:[.32,.32,.32]},
 read:{duration:3,bodyY:[.25,.25,.25],bodyX:[.12,.04,.12],left:[-.65,-.65,-.65],right:[-.65,-.65,-.65],footZ:[.32,.32,.32]},
 stretch:{duration:3,bodyY:[.25,.3,.25],bodyX:[.02,-.1,.02],left:[-.7,-2.6,-.7],right:[-.7,-2.6,-.7],footZ:[.32,.32,.32]},
 reach:{duration:2,bodyX:[0,.08,0],left:[0,-.7,0],right:[0,-1.5,0]},
 sip:{duration:2,bodyX:[0,-.06,0],left:[-.2,-.2,-.2],right:[-1.2,-2,-1.2]},
 ride:{duration:2,bodyY:[-.12,-.09,-.12],left:[-1,-1.1,-1],right:[-1,-1.1,-1],footZ:[.35,.35,.35]},
 wave:{duration:1.2,left:[0,0,0],right:[-2.4,-2.9,-2.4]}
};
const bindings={'Body.position[y]':'bodyY','Body.rotation[x]':'bodyX','LeftArm.rotation[x]':'left','RightArm.rotation[x]':'right','LeftFoot.position[y]':'leftFoot','RightFoot.position[y]':'rightFoot','LeftFoot.position[z]':'footZ','RightFoot.position[z]':'footZ'};
const clips=Object.entries(specs).map(([name,s])=>new AnimationClip(name,s.duration,Object.entries(bindings).map(([path,key])=>new NumberKeyframeTrack(path,[0,s.duration/2,s.duration],s[key]||[key.endsWith('Foot')?.15:key==='footZ'?.08:0,key.endsWith('Foot')?.15:key==='footZ'?.08:0,key.endsWith('Foot')?.15:key==='footZ'?.08:0],InterpolateSmooth))));
export function animateCharacter(root){
 const mixer=new AnimationMixer(root),actions=Object.fromEntries(clips.map(c=>[c.name,mixer.clipAction(c)]));let current=null;
 return {update(pose,dt,still=false){
   if(pose!==current){const next=actions[pose]||actions.idle;next.reset().setEffectiveWeight(1).play();if(current)actions[current].crossFadeTo(next,.3,false);current=next.getClip().name;}
   if(still){mixer.stopAllAction();actions[current].reset().play();mixer.update(0)}else mixer.update(Math.max(0,Math.min(.1,dt)));
 },dispose(){mixer.stopAllAction();mixer.uncacheRoot(root)}};
}
