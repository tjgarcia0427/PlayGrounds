"""Six original chibi companions sharing the PlayGrounds object-joint contract."""
from common import *
STYLES=[('peach-fox','fox','peach'),('lilac-owl','owl','lilac'),('mint-bunny','bunny','mint'),('sky-bear','bear','sky'),('buttercup-bear','bear','butter'),('rose-fox','fox','rose')]
def tapered_ear(side,head,skin,cream):
    # One continuous shell; assign its forward faces ivory. No detached inset mesh.
    verts=[];faces=[];rings=[(0,.15,.10),(.10,.137,.085),(.23,.09,.06),(.33,.025,.025),(.35,.004,.005)]
    for dz,w,d in rings:
        for j in range(16):
            a=j*math.tau/16;verts.append((side*(.33+dz*.22)+math.cos(a)*w,.005+math.sin(a)*d,1.48+dz))
    for k in range(4):
        for j in range(16):a=k*16+j;b=k*16+(j+1)%16;faces.append((a,b,b+16,a+16))
    faces.extend([tuple(reversed(range(16))),tuple(range(64,80))])
    o=mesh('Sewn fox ear',verts,faces,[skin,cream],head)
    for k in range(4):
        for j in range(16):
            if 9<=j<=13 and k<3:o.data.polygons[k*16+j].material_index=1
    bpy.context.view_layer.objects.active=o;sub=o.modifiers.new('Soft ear','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
def fox_tail(body,skin,cream):
    tail=group('Tail',(.19,.17,.37),body);verts=[];faces=[];steps=18;sides=16
    for k in range(steps+1):
        t=k/steps;c=Vector((.19+.49*math.sin(t*1.7),.17+.22*t,.37+.61*t))
        tangent=Vector((.833*math.cos(t*1.7),.22,.61)).normalized();u=tangent.cross(Vector((0,1,0))).normalized();v=tangent.cross(u);r=.028+.18*math.sin(math.pi*t)**.75
        if k==steps:r=.004
        for j in range(sides):verts.append(c+r*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v))
    for k in range(steps):
        for j in range(sides):a=k*sides+j;b=k*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple(range(steps*sides,(steps+1)*sides))]);o=mesh('Swept tail',verts,faces,[skin,cream],tail)
    for k in range(steps):
        for j in range(sides):
            if k>=12+(j%3==0):o.data.polygons[k*sides+j].material_index=1
    bpy.context.view_layer.objects.active=o;sub=o.modifiers.new('Soft tail','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    return tail
def character(key,kind,color):
    reset();root=group('Companion');root['style']=key;body=group('Body',parent=root);head=group('Head',(0,0,.98),body)
    skin=material('Velour '+color,color,True);cream=material('Ivory velour','cream',True);pink=material('Rose embroidery','e7aaa7',True)
    dark=material('Cocoa embroidery','89635d');gloss=material('Glossy eyes','241d24',rough=.13);white=material('Catchlight','white',rough=.2);lilac=material('Lilac headphones','lilac',rough=.48)
    roundness=.37 if kind=='owl' else .32
    ball('Bean body',(0,0,.60),(roundness,.265,.44),skin,body)
    ball('Ivory bib',(0,-.233,.59),(.236,.065,.315),cream,body)
    ball('Oversized head',(0,0,1.27),(.515,.35,.43),skin,head,28,18)
    tail=group('Tail',(0,.22,.41),body) if kind!='fox' else fox_tail(body,skin,cream)
    if kind=='bunny':
        ball('Cotton tail',(0,.28,.40),(.145,.15,.14),cream,tail)
    elif kind=='bear':ball('Bear tail',(0,.235,.41),(.10,.11,.10),skin,tail)
    for s in (-1,1):
        if kind=='fox':
            tapered_ear(s,head,skin,cream)
            ball('Cream cheek',(s*.207,-.265,1.115),(.267,.107,.165),cream,head)
            # Overlapping broad sculpted cheek tufts, not noisy sphere fur.
            for dz,dx in [(0,0),(.055,-.02)]:
                tuft=ball('Cheek fringe',(s*(.428+dx),-.125,1.15+dz),(.105,.13,.078),skin,head,16,10);tuft.rotation_euler[1]=-s*.35
        elif kind=='owl':
            tuft=ball('Owl crest',(s*.344,0,1.63),(.092,.085,.205),skin,head);tuft.rotation_euler[1]=s*.43
            ball('Owl facial disk',(s*.19,-.276,1.23),(.215,.094,.23),cream,head)
        elif kind=='bunny':
            ear=ball('Long bunny ear',(s*.285,.012,1.76),(.12,.098,.34),skin,head);ear.rotation_euler[1]=s*.13
            inset=ball('Bunny ear embroidery',(s*.291,-.074,1.79),(.061,.02,.218),pink,head);inset.rotation_euler[1]=s*.13
        else:
            ball('Round bear ear',(s*.34,.005,1.61),(.153,.105,.15),skin,head)
            ball('Bear ear embroidery',(s*.34,-.084,1.615),(.084,.026,.085),cream,head)
        eyes=group('LeftEye' if s<0 else 'RightEye',(s*.19,-.354,.245),head)
        ball('Glass eye',(s*.19,-.363,1.225),(.057,.033,.066),gloss,eyes)
        ball('Eye shine',(s*.19-.016,-.392,1.249),(.012,.008,.015),white,eyes,12,8)
        ball('Blush',(s*.313,-.345,1.119),(.051,.019,.026),pink,head)
        arm=group('LeftArm' if s<0 else 'RightArm',(s*.37,0,.85),body)
        sleeve=ball('Wing' if kind=='owl' else 'Paw',(s*.38,0,.64),(.135 if kind=='owl' else .117,.128,.243),skin,arm)
        if kind=='owl':sleeve.rotation_euler[1]=s*.22
        else:ball('Paw pad',(s*.38,-.09,.477),(.07,.045,.07),cream,arm)
        # Tiny inset seam; batched with limb, no separate draw call per stitch.
        curve('Limb seam',[(s*.422,-.104,.70),(s*.451,-.095,.59),(s*.424,-.107,.49)],.0035,cream,arm)
        foot=group('LeftFoot' if s<0 else 'RightFoot',(s*.17,-.08,.15),root)
        ball('Round foot',(s*.17,-.08,.15),(.145,.185,.15),skin,foot)
        ball('Foot pad',(s*.17,-.25,.135),(.073,.023,.060),cream,foot)
        ball('Headphone cushion',(s*.511,.02,1.28),(.066,.153,.154),cream,head)
        ball('Headphone cup',(s*.551,.02,1.28),(.042,.117,.121),lilac,head)
        ball('Cup button',(s*.59,-.003,1.28),(.009,.027,.027),white,head,12,8)
    if kind=='owl':
        beak=ball('Small owl beak',(0,-.358,1.12),(.045,.047,.065),material('Apricot beak','d6a167'),head);beak.rotation_euler[0]=-.3
        for row in range(3):
            for s in (-1,1):curve('Belly feather stitch',[(s*.08-.025,-.296,.70-row*.09),(s*.08,-.303,.678-row*.09),(s*.08+.025,-.296,.70-row*.09)],.0035,dark,body)
    else:
        ball('Cream muzzle',(0,-.353,1.09),(.136,.08,.092),cream,head)
        ball('Embroidered nose',(0,-.429,1.139),(.041,.02,.027),dark,head)
        curve('Smile',[(-.07,-.416,1.10),(-.046,-.430,1.074),(0,-.435,1.09),(.046,-.430,1.074),(.07,-.416,1.10)],.006,dark,head)
    curve('Headphone band',[(.54*math.cos(a),.085,1.28+.49*math.sin(a)) for a in [i*math.pi/16 for i in range(17)]],.032,lilac,head)
    # Delicate rear construction seam provides useful back-view detail.
    curve('Head back seam',[(0,.05,1.687),(0,.292,1.50),(0,.35,1.27),(0,.286,1.03)],.003,cream,head)
    group('MugSocket',(0,-.04,-.43),bpy.data.objects['RightArm'])
    for frame,angle in [(1,0),(16,-.09),(31,0),(46,.09),(61,0)]:
        head.rotation_euler[1]=angle;head.keyframe_insert(data_path='rotation_euler',frame=frame)
        tail.rotation_euler[1]=-angle;tail.keyframe_insert(data_path='rotation_euler',frame=frame)
    for o in (head,tail):o.animation_data.action.name='Study'+o.name
    return export_asset(root,key,'character',kind+' companion · original velour geometry, headphones and study motion')
