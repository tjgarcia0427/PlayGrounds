"""Import every delivered GLB and evaluate animation and actual mesh bounds."""
import sys,json,bpy
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent
for a in json.loads((BASE/'manifest.json').read_text())['assets']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(BASE/'assets'/(a['id']+'.glb')))
    # Blender imports the first glTF clip as active, stashing the others muted.
    # Activate each object's own imported clip before evaluating both study channels.
    for obj in bpy.context.scene.objects:
        ad=obj.animation_data
        if ad and not ad.action and ad.nla_tracks:
            ad.action=ad.nla_tracks[0].strips[0].action
    scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(c) for o in scene.objects if o.type=='MESH' for c in o.bound_box]
    measured=[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
    assert all(abs(measured[k][i]-a['boundsZUp'][k][i])<.025 for k in range(2) for i in range(3)),(a['id'],measured,a['boundsZUp'])
    if a['kind']=='character':
        assert bpy.data.objects['Head'].parent.name=='Body'
        for name in ('Head','Tail'):
            obj=bpy.data.objects[name];scene.frame_set(1);first=obj.matrix_world.copy();scene.frame_set(16);second=obj.matrix_world.copy()
            assert any(abs(first[r][c]-second[r][c])>.01 for r in range(3) for c in range(3)),(a['id'],name)
    elif a['id']=='merry-go-round':
        o=bpy.data.objects['RotatingDeck'];scene.frame_set(1);first=o.matrix_world.copy();scene.frame_set(16)
        assert abs(first[0][0]-o.matrix_world[0][0])>.5
    print('ROUNDTRIP_PASS',a['id'],flush=True)
print('ALL_22_ROUNDTRIPS_PASS',flush=True)
