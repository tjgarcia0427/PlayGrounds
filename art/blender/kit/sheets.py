"""Render the actual exported GLBs, not a separate high-detail source surrogate."""
from common import *
def render_sheets(manifest,category):
    entries=[a for a in manifest['assets'] if (a['kind']=='character')==(category=='characters')]
    assert entries, 'Build assets before rendering sheets'
    out=BASE/'previews';out.mkdir(exist_ok=True)
    if category=='characters':
        for angle,label,frame in [(0,'front',1),(-.5,'three-quarter',1),(-1.45,'posed-side',16)]:
            reset()
            for i,a in enumerate(entries):
                before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(ASSETS/(a['id']+'.glb')))
                imported=set(bpy.context.scene.objects)-before
                pivot=group('Preview '+a['id'])
                for o in imported:
                    if o.parent is None:o.parent=pivot
                pivot.location.x=(i-2.5)*1.6;pivot.rotation_euler.z=angle
            bpy.context.scene.frame_set(frame)
            studio(out/(category+'-'+label+'.png'),(0,0,.97),10.25,(0,-18,3.8),1800,600,48)
    else:
        # Objects shown at individual normalized display scales. Manifest preserves real dimensions.
        for label,angle in [('three-quarter',-.45),('reverse',2.35)]:
            reset()
            for i,a in enumerate(entries):
                before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(ASSETS/(a['id']+'.glb')))
                imported=set(bpy.context.scene.objects)-before;pivot=group('Preview '+a['id'])
                for o in imported:
                    if o.parent is None:o.parent=pivot
                lo,hi=a['boundsZUp'];size=max(hi[j]-lo[j] for j in range(3));scale=1.75/max(size,.1)
                pivot.scale=(scale,)*3;pivot.location=((i%4-1.5)*2.5,(i//4)*2.5,0);pivot.rotation_euler.z=angle
            studio(out/(category+'-'+label+'.png'),(0,3.5,.4),12.7,(0,-14,16),1400,1100,40)
