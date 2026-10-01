"""Original Blender fox study. Run: blender -b -t 4 -P art/blender/fox/build.py
Z-up authoring; glTF exporter converts to Y-up. No downloaded geometry/textures.
"""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
random.seed(45)
# Packed tangent-space fabric grain survives glTF export (unlike Noise nodes).
img=bpy.data.images.new('Original woven micro-normal',128,128)
pixels=[]
for y in range(128):
    for x in range(128):
        nx=.15*math.sin(x*math.pi/2)+random.uniform(-.07,.07)
        ny=.15*math.sin(y*math.pi/2)+random.uniform(-.07,.07)
        pixels.extend((.5+nx,.5+ny,1,1))
img.colorspace_settings.name='Non-Color'; img.pixels=pixels; img.update(); img.pack()
def mat(name,hex,cloth=False,rough=.8):
    m=bpy.data.materials.new(name); m.use_nodes=True
    c=tuple(int(hex[i:i+2],16)/255 for i in (0,2,4))
    c=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*c,1); p.inputs['Roughness'].default_value=rough
    if cloth:
        p.inputs['Sheen Weight'].default_value=.35
        tex=m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=img
        normal=m.node_tree.nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value=.32
        m.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']); m.node_tree.links.new(normal.outputs['Normal'],p.inputs['Normal'])
    return m
peach=mat('Peach velour','efa77c',True); cream=mat('Warm ivory plush','f7ead5',True); pink=mat('Rose embroidery','e7aaa7',True)
lilac=mat('Lilac headphones','bdaacf',False,.5); seam=mat('Cocoa thread','89635d'); eye=mat('Glossy cocoa eyes','241d24',False,.12)
shine=mat('Ivory catchlight','fff7e9',False,.24)
def group(name,pos=(0,0,0),parent=None):
    o=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(o); o.location=pos; o.parent=parent; return o
root=group('Fox'); body=group('Body',parent=root); head=group('Head',(0,0,.98),body)
def ball(name,pos,scale,material,parent,seg=24,rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=pos)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    for p in o.data.polygons:p.use_smooth=True
    world=o.matrix_world.copy(); o.parent=parent; o.matrix_world=world
    return o
# Front faces negative Y, converted to +Z in glTF.
ball('Pear-shaped body',(0,0,.58),(.32,.255,.43),peach,body)
ball('Ivory bib',(0,-.218,.58),(.239,.067,.325),cream,body)
ball('Broad chibi head',(0,0,1.26),(.51,.35,.435),peach,head,32,20)
for s in (-1,1):
    ball('Cream cheek', (s*.212,-.257,1.115),(.277,.119,.176),cream,head)
    ball('Cheek tuft',(s*.423,-.12,1.17),(.113,.165,.12),peach,head)
    # Tapered rounded triangular ears: sculpted rings, subdivision not cones.
    def ear(name,material,inner=False):
        z0=1.48 if not inner else 1.53
        rings=[(0,.155,.11),(.11,.137,.085),(.23,.093,.058),(.33,.025,.025),(.35,.005,.006)]
        verts=[]; faces=[]
        for dz,w,d in rings:
            for j in range(12):
                a=j*math.tau/12
                verts.append((s*(.33+dz*.23)+math.cos(a)*w*(.64 if inner else 1),(-.065+dz*.08 if inner else .005)+math.sin(a)*d*(.35 if inner else 1),z0+dz*(.72 if inner else 1)))
        for k in range(4):
            for j in range(12):
                a=k*12+j;b=k*12+(j+1)%12;faces.append((a,b,b+12,a+12))
        faces.extend([tuple(reversed(range(12))),tuple(range(48,60))])
        me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
        o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(material)
        sub=o.modifiers.new('Soft sewn ear','SUBSURF');sub.levels=2
        bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.modifier_apply(modifier=sub.name);o.select_set(False)
        for p in me.polygons:p.use_smooth=True
        for p in o.data.polygons:p.use_smooth=True
        world=o.matrix_world.copy();o.parent=head;o.matrix_world=world
    ear('Tapered fox ear',peach);ear('Ivory ear inset',cream,True)
    eye_node=group('LeftEye' if s<0 else 'RightEye', (s*.19,-.338,.245),head)
    ball('Glass eye',(s*.19,-.353,1.225),(.058,.037,.067),eye,eye_node)
    ball('Catchlight',(s*.19-.017,-.387,1.249),(.013,.009,.017),shine,eye_node,12,8)
    ball('Blush stitch',(s*.322,-.359,1.119),(.054,.014,.025),pink,head)
    arm=group('LeftArm' if s<0 else 'RightArm',(s*.365,0,.83),body)
    ball('Soft sleeve',(s*.368,0,.65),(.118,.135,.238),peach,arm)
    ball('Paw pad',(s*.371,-.095,.478),(.075,.047,.077),cream,arm)
    foot=group('LeftFoot' if s<0 else 'RightFoot',(s*.17,-.04,.135),root)
    ball('Rounded foot',(s*.17,-.04,.135),(.145,.19,.135),peach,foot)
    ball('Toe patch',(s*.17,-.215,.12),(.076,.028,.057),cream,foot)
    ball('Headphone cushion',(s*.51,.015,1.28),(.07,.16,.16),cream,head)
    ball('Headphone cup',(s*.555,.015,1.28),(.048,.125,.129),lilac,head)
ball('Muzzle',(0,-.361,1.092),(.143,.08,.103),cream,head)
ball('Embroidered nose',(0,-.435,1.143),(.048,.022,.031),seam,head)
def curve(name,pts,r,material,parent):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=2;cu.resolution_u=12
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(pts)-1)
    for p,co in zip(sp.bezier_points,pts):p.co=co;p.handle_left_type=p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);cu.materials.append(material)
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o.select_set(False)
    world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world
    return o
curve('Tiny stitched smile',[(-.074,-.424,1.101),(-.05,-.438,1.073),(0,-.442,1.091),(.05,-.438,1.073),(.074,-.424,1.101)],.007,seam,head)
curve('Padded headphone band',[(.54*math.cos(a),.085,1.28+.49*math.sin(a)) for a in [i*math.pi/16 for i in range(17)]],.035,lilac,head)
tail=group('Tail',(.19,.17,.37),body)
# Continuous swept tail with ivory tip, not stacked spheres.
verts=[];faces=[];steps=20; sides=16
for k in range(steps+1):
    t=k/steps; c=Vector((.19+.49*math.sin(t*1.7),.17+.22*t,.37+.61*t))
    tangent=Vector((.49*1.7*math.cos(t*1.7),.22,.61)).normalized();u=tangent.cross(Vector((0,1,0))).normalized();v=tangent.cross(u)
    radius=.035+.18*math.sin(math.pi*t)**.75
    if k==steps:radius=.004
    for j in range(sides):
        p=c+radius*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v);verts.append(p)
for k in range(steps):
    for j in range(sides):a=k*sides+j;b=k*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
faces.extend([tuple(reversed(range(sides))),tuple(range(steps*sides,(steps+1)*sides))])
me=bpy.data.meshes.new('Swept tail');me.from_pydata(verts,[],faces);me.materials.append(peach);me.materials.append(cream);me.update()
o=bpy.data.objects.new('Curved plush tail',me);bpy.context.collection.objects.link(o)
for p in me.polygons:p.use_smooth=True;p.material_index=1 if p.center.z>.80 else 0
sub=o.modifiers.new('Soft tail silhouette','SUBSURF');sub.levels=1
bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sub.name)
world=o.matrix_world.copy();o.parent=tail;o.matrix_world=world
# Explicit object-joint animation smoke clip. Runtime adapter is intentionally separate.
for frame,angle in [(1,0),(16,-.12),(31,0),(46,.12),(61,0)]:
    head.rotation_euler[1]=angle;head.keyframe_insert(data_path='rotation_euler',frame=frame)
    tail.rotation_euler[1]=-angle;tail.keyframe_insert(data_path='rotation_euler',frame=frame)
for o in (head,tail):o.animation_data.action.name=o.name+'IdleStudy'
scene=bpy.context.scene;scene.frame_end=61;scene.render.fps=30;scene.frame_set(1)
# Create UVs for authored ears/tail and all fabric parts lacking UVs.
bpy.ops.object.select_all(action='DESELECT')
for o in list(root.children_recursive):
    if o.type=='MESH' and not o.data.uv_layers:
        o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project();bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)
root.select_set(True)
for o in root.children_recursive:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT/'peach-fox.glb'),export_format='GLB',use_selection=True,export_animations=True,export_force_sampling=True)
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in root.children_recursive if o.type=='MESH')
(OUT/'metrics.json').write_text(json.dumps({'triangles':triangles,'meshes':sum(o.type=='MESH' for o in root.children_recursive),'glb_bytes':(OUT/'peach-fox.glb').stat().st_size,'blender':bpy.app.version_string,'runtime_integrated':False},indent=2)+'\n')
# CPU studio previews, not screenshots of the app.
floor=mat('Studio ivory','ece4dc')
bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(floor)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.world.color=(.25,.25,.25)
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(-3,-4,5),450,4),('Fill',(3,-2,3),250,3),('Rim',(1,3,4),450,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.name=name;l.data.energy=power;l.data.shape='DISK';l.data.size=size;aim(l,(0,0,1))
bpy.ops.object.camera_add(location=(2,-5,2.4));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=2.55;scene.camera=camera
scene.render.resolution_x=700;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
for label,loc,frame in [('front',(0,-6,2.1),1),('three-quarter',(3,-6,2.6),1),('side',(6,-.8,2.4),16)]:
    scene.frame_set(frame);camera.location=loc;aim(camera,(.07,0,.92));scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
scene.frame_set(1);camera.location=(3,-6,2.6);aim(camera,(.07,0,.92))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'peach-fox.blend'))
print('FOX_BUILD_COMPLETE',triangles,flush=True)
