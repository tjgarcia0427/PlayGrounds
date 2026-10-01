"""Dependency-free delivered-asset contract; not a hostile-upload GLTF validator."""
import hashlib,json,struct
from pathlib import Path
BASE=Path(__file__).resolve().parent
manifest=json.loads((BASE/'manifest.json').read_text())
expected={'peach-fox','lilac-owl','mint-bunny','sky-bear','buttercup-bear','rose-fox','slide','merry-go-round','monkey-bars','campus-gate','shared-table','round-table','chair','sofa','coffee-bar','laptop','bookshelf','planter','reading-lamp','wall-art','garden-tree','rug'}
assert {a['id'] for a in manifest['assets']}==expected
assert len(manifest['assets'])==len(expected)
required={'Companion','Body','Head','LeftArm','RightArm','LeftFoot','RightFoot','LeftEye','RightEye','Tail','MugSocket'}
results=[]
for a in manifest['assets']:
    p=BASE/'assets'/(a['id']+'.glb');raw=p.read_bytes()
    assert struct.unpack_from('<4sII',raw)==(b'glTF',2,len(raw)),a['id']
    n,kind=struct.unpack_from('<I4s',raw,12);assert kind==b'JSON';g=json.loads(raw[20:20+n])
    assert hashlib.sha256(raw).hexdigest()==a['sha256'],a['id']+' stale manifest hash'
    assert len(raw)==a['bytes'] and len(raw)<1_500_000
    assert (p.with_suffix('.blend')).is_file()
    assert all('uri' not in x for x in g.get('buffers',[])+g.get('images',[])),a['id']+' external dependency'
    assert not any('camera' in node for node in g['nodes'])
    assert 'Studio ivory' not in {m.get('name') for m in g.get('materials',[])}
    triangles=sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives'])
    assert triangles==a['triangles'] and triangles<65000,(a['id'],triangles,a['triangles'])
    names={n.get('name') for n in g['nodes']}
    if a['kind']=='character':
        assert required<=names,(a['id'],required-names)
        assert triangles<24000 and len(g['meshes'])<=10
        assert any('normalTexture' in m for m in g['materials'])
        animated={g['nodes'][c['target']['node']]['name'] for anim in g['animations'] for c in anim['channels']}
        assert {'Head','Tail'}<=animated
        assert abs(a['boundsZUp'][0][2])<.02 and 1.7<a['boundsZUp'][1][2]<2.3
    elif a['id']=='merry-go-round':
        assert 'RotatingDeck' in names and g.get('animations')
    for material in g.get('materials',[]):
        for k in ('normalTexture','occlusionTexture','emissiveTexture'):
            if k in material:assert material[k]['index']<len(g['textures'])
    results.append({'id':a['id'],'triangles':triangles,'bytes':len(raw),'drawPrimitives':sum(len(m['primitives']) for m in g['meshes'])})
print(json.dumps({'validated':len(results),'assets':results},indent=2))
