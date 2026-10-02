import {validateBytes} from 'gltf-validator';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url));
const manifest=JSON.parse(readFileSync(root+'art/blender/kit/manifest.json'));
const out=root+'mvp/browser-qa/artifacts/blender-kit';mkdirSync(out,{recursive:true});
const reports=[];
for(const a of manifest.assets){
 const report=await validateBytes(new Uint8Array(readFileSync(root+`art/blender/kit/assets/${a.id}.glb`)),{uri:a.id+'.glb',maxIssues:100});
 reports.push({id:a.id,issues:report.issues});
 if(report.issues.numErrors || report.issues.numWarnings)process.exitCode=1;
 console.log(a.id,report.issues.numErrors,'errors',report.issues.numWarnings,'warnings');
}
writeFileSync(out+'/gltf-validator.json',JSON.stringify(reports,null,2));
