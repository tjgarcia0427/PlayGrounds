"""Blender round-trip smoke check: load only GLB, evaluate its exported motion."""
import bpy,json
from pathlib import Path
p=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(p/'peach-fox.glb'))
head=bpy.data.objects['Head']; tail=bpy.data.objects['Tail']
assert head.parent.name=='Body'
for name in ('LeftArm','RightArm'):
    assert bpy.data.objects[name].parent.name=='Body'
scene=bpy.context.scene
scene.frame_set(1); first=head.matrix_world.copy()
scene.frame_set(16); second=head.matrix_world.copy()
assert any(abs(first[r][c]-second[r][c])>.01 for r in range(3) for c in range(3)), 'Head motion lost on round trip'
print('FOX_ROUNDTRIP_PASS: imported GLB hierarchy and head motion')
scene.frame_set(1)
from mathutils import Vector
points=[o.matrix_world@Vector(corner) for o in scene.objects if o.type=='MESH' for corner in o.bound_box]
zmin=min(p.z for p in points);zmax=max(p.z for p in points)
assert -.02<zmin<.02 and 1.7<zmax<2.1,(zmin,zmax)
print('FOX_SCALE_PASS',zmin,zmax)
