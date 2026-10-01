"""Small Blender-native modeling helpers. Original shapes; no service dependencies."""
import bpy, math, random, json, hashlib
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent
ASSETS=BASE/'assets';ASSETS.mkdir(exist_ok=True)
PALETTE={'cream':'f7ead5','peach':'efa77c','rose':'dba7bc','lilac':'b7a1d8','mint':'a4c7b1','sky':'a5c9db','butter':'e4c780','wood':'c79566','dark':'74605b','leaf':'7ca88d','white':'fff8e9'}
def reset():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for pool in (bpy.data.meshes,bpy.data.curves,bpy.data.materials,bpy.data.actions,bpy.data.images):
        for item in list(pool):
            if item.users==0:pool.remove(item)
    bpy.context.scene.frame_set(1)
def material(name,color,cloth=False,rough=.72):
    old=bpy.data.materials.get(name)
    if old:return old
    m=bpy.data.materials.new(name);m.use_nodes=True
    color=PALETTE.get(color,color);srgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    rgb=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in srgb]
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Roughness'].default_value=rough
    if cloth:
        p.inputs['Sheen Weight'].default_value=.55;p.inputs['Sheen Roughness'].default_value=.8
        img=bpy.data.images.get('Original velour normal')
        if not img:
            rng=random.Random(45);n=256;img=bpy.data.images.new('Original velour normal',n,n);pixels=[]
            for y in range(n):
                for x in range(n):
                    nx=.10*math.sin(x*2.1+y*.35)+rng.uniform(-.08,.08);ny=.12*math.cos(y*2.2)+rng.uniform(-.08,.08)
                    pixels.extend((.5+nx,.5+ny,math.sqrt(max(0,1-nx*nx-ny*ny)),1))
            img.colorspace_settings.name='Non-Color';img.pixels=pixels;img.update();img.pack()
            assert .25<img.pixels[0]<.75 and img.pixels[2]>.9, 'Normal texture pixels were lost'
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img
        normal=m.node_tree.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.4
        m.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);m.node_tree.links.new(normal.outputs['Normal'],p.inputs['Normal'])
    return m
def group(name,pos=(0,0,0),parent=None):
    o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);o.location=pos;o.parent=parent;return o
def attach(o,parent):
    bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world;return o
def finish(o,name,mat,parent):
    o.name=name;o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return attach(o,parent)
def ball(name,pos,scale,mat,parent,seg=20,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=pos)
    o=bpy.context.object;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat,parent)
def box(name,pos,size,mat,parent,radius=.06):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Rounded toy edges','BEVEL');mod.width=min(radius,min(size)*.45);mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat,parent)
def cylinder(name,pos,radius,depth,mat,parent,verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=pos);o=bpy.context.object
    mod=o.modifiers.new('Soft edge','BEVEL');mod.width=min(.035,depth*.2,radius*.2);mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat,parent)
def rod(name,a,b,r,mat,parent):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,r,(b-a).length,mat,parent,16);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def curve(name,pts,r,mat,parent):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=2;cu.resolution_u=6
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(pts)-1)
    for p,co in zip(sp.bezier_points,pts):p.co=co;p.handle_left_type=p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);cu.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
    return attach(o,parent)
def mesh(name,verts,faces,mats,parent):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
    for m in mats:me.materials.append(m)
    for p in me.polygons:p.use_smooth=True
    return attach(o,parent)
def merge_static_children(root):
    # Preserve named pivot nodes; batch meshes only within the same direct parent.
    for parent in [root]+[o for o in root.children_recursive if o.type=='EMPTY']:
        meshes=[o for o in parent.children if o.type=='MESH']
        if len(meshes)<2:continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in meshes:o.select_set(True)
        bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();meshes[0].name=parent.name+'Surface'
def export_asset(root,key,kind,description):
    scene=bpy.context.scene;scene.frame_set(1);scene.render.fps=30;scene.frame_end=61
    for o in list(root.children_recursive):
        if o.type=='MESH' and not o.data.uv_layers:
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project();bpy.ops.object.mode_set(mode='OBJECT')
    merge_static_children(root)
    # Tangent generation requires triangulated meshes, including beveled prop ngons.
    for o in root.children_recursive:
        if o.type=='MESH':
            bpy.context.view_layer.objects.active=o
            mod=o.modifiers.new('Portable triangulation','TRIANGULATE')
            mod.keep_custom_normals=True
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    path=ASSETS/(key+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_force_sampling=True,export_extras=True,export_tangents=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ASSETS/(key+'.blend')))
    triangles=sum(len(p.vertices)-2 for o in root.children_recursive if o.type=='MESH' for p in o.data.polygons)
    bpy.context.view_layer.update();pts=[o.matrix_world@Vector(c) for o in root.children_recursive if o.type=='MESH' for c in o.bound_box]
    bounds=[[round(min(p[i] for p in pts),4) for i in range(3)],[round(max(p[i] for p in pts),4) for i in range(3)]]
    return dict(id=key,kind=kind,description=description,bytes=path.stat().st_size,triangles=triangles,meshes=sum(o.type=='MESH' for o in root.children_recursive),boundsZUp=bounds,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
def studio(path,center,scale,location,width=1400,height=800,samples=48):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=samples;scene.cycles.use_denoising=False
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));bpy.context.object.data.materials.append(material('Studio ivory','ece4dc'))
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.7,.75,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    for name,loc,power,size in [('Key',(-4,-6,8),1000,6),('Fill',(5,-2,6),650,5),('Rim',(0,5,7),950,5)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.size=size;aim(o,center)
    bpy.ops.object.camera_add(location=location);cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=scale;aim(cam,center);scene.camera=cam
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
