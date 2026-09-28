// DOM-light behavior test: real dashboard functions, not a visual browser test.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const elements = new Map();
function element() { return {style:{},dataset:{},classList:{toggle(){}},children:[],
  appendChild(x){this.children.push(x)},setAttribute(k,v){this[k]=v},remove(){this.removed=true}}; }
const document = {getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},createElement:element};
const html=fs.readFileSync(path.join(__dirname,'dashboard.html'),'utf8');
const script=html.split('<script>')[1].split('</script>')[0].split('\nrefresh();\nconst es')[0];
const context=vm.createContext({document,console,Date,Map,Set});
vm.runInContext(script,context);
const world={agents:[{id:'a',name:'<Agent>',plush:'plush1.png',last_heartbeat:Date.now()/1000,presence:{space:'playground',activity:'idle'}}],social_messages:[{agent_id:'a',text:'<img src=x onerror=bad()>',seq:1}]};
context.renderWorld(world,{goals:{}});
const node=document.getElementById('worldAgents').children[0];
const oldLeft=node.style.left;
assert.equal(node.dataset.space,'playground');
assert.ok(document.getElementById('socialFeed').innerHTML.includes('&lt;img'));
assert.ok(!document.getElementById('socialFeed').innerHTML.includes('<img'));
context.focusSpace('classroom');
assert.equal(world.agents[0].presence.space,'playground'); // viewing is not moving
assert.equal(document.getElementById('classroomPanels').hidden,false);
assert.equal(document.getElementById('socialSection').hidden,true);
world.agents[0].presence={space:'classroom',activity:'working',goal_id:'g'};
context.renderWorld(world,{goals:{g:{title:'Build'}}});
assert.equal(document.getElementById('worldAgents').children.length,1); // retain node for CSS movement
assert.notEqual(node.style.left,oldLeft);
assert.equal(node.dataset.space,'classroom');
assert.ok(node.title.includes('Build'));
context.renderWorld({agents:[],social_messages:[]},{goals:{}});
assert.equal(node.removed,true);
console.log('World view switching, state-driven movement, node reuse and message escaping passed (not visual verification).');
