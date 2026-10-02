"""Validate the delivered binary, not only Blender's source scene."""
import json, struct
from pathlib import Path
p=Path(__file__).with_name('peach-fox.glb'); raw=p.read_bytes()
magic,version,length=struct.unpack_from('<4sII',raw)
assert (magic,version,length)==(b'glTF',2,len(raw))
size,kind=struct.unpack_from('<I4s',raw,12);assert kind==b'JSON'
g=json.loads(raw[20:20+size]);nodes={n.get('name'):n for n in g['nodes']}
required={'Fox','Body','Head','LeftArm','RightArm','LeftFoot','RightFoot','LeftEye','RightEye','Tail'}
assert required<=nodes.keys(),required-nodes.keys()
assert len(raw)<2_000_000,'Prototype exceeds 2MB budget'
triangles=sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives'])
assert triangles<40000,triangles
assert g.get('animations'),'Missing animation clips'
animated={g['nodes'][c['target']['node']]['name'] for a in g['animations'] for c in a['channels']}
assert {'Head','Tail'}<=animated
assert all('uri' not in x for x in g.get('images',[])),'External image dependency'
assert all('uri' not in x for x in g.get('buffers',[])),'External buffer dependency'
assert any('normalTexture' in m for m in g['materials']),'Fabric normal was lost'
assert not any('camera' in n for n in g['nodes']),'Studio camera leaked into GLB'
assert 'Studio ivory' not in {m['name'] for m in g['materials']},'Studio floor leaked'
for a in g['accessors']:
    if a.get('type')=='VEC3' and 'min' in a:
        assert all(abs(x)<4 for x in a['min']+a['max']),'Unexpected scale'
print(json.dumps({'glb_bytes':len(raw),'triangles':triangles,'mesh_count':len(g['meshes']),'animation_count':len(g['animations']),'required_nodes':sorted(required),'embedded_images':len(g.get('images',[]))},indent=2))
