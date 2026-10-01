"""Original modular playground and airy campus furnishings, modeled at actor scale."""
from common import *
PROPS=['slide','merry-go-round','monkey-bars','campus-gate','shared-table','round-table','chair','sofa','coffee-bar','laptop','bookshelf','planter','reading-lamp','wall-art','garden-tree','rug']
def prop(key):
    reset();root=group('Asset');root['assetId']=key
    m={c:material(c,c,cloth=c in ('rose','lilac','cream')) for c in PALETTE}
    def B(name,p,s,c,r=.06,parent=root):return box(name,p,s,m[c],parent,r)
    def S(name,p,s,c,parent=root):return ball(name,p,s,m[c],parent)
    def C(name,p,r,d,c,parent=root):return cylinder(name,p,r,d,m[c],parent)
    def R(name,a,b,r,c,parent=root):return rod(name,a,b,r,m[c],parent)
    def Q(name,pts,r,c,parent=root):return curve(name,pts,r,m[c],parent)
    def book(p,w=.12,h=.3,c='rose'):
        x,y,z=p;B('Book cover',(x,y,z),(w,.26,h),c,.015);B('Ivory pages',(x,y-.005,z),(w*.72,.264,h*.88),'cream',.009)
    def cup(p):
        x,y,z=p;C('Ceramic mug',(x,y,z+.09),.085,.18,'cream');C('Coffee',(x,y,z+.183),.067,.009,'dark')
        Q('Mug handle',[(x+.072,y,z+.15),(x+.135,y,z+.15),(x+.145,y,z+.06),(x+.074,y,z+.045)],.018,'cream')
    def plant(p,scale=1):
        x,y,z=p;s=scale;C('Ceramic planter',(x,y,z+.16*s),.19*s,.32*s,'rose');C('Pot soil',(x,y,z+.324*s),.166*s,.009*s,'dark')
        for i in range(7):
            a=i*2.4;tip=(x+math.cos(a)*.24*s,y+math.sin(a)*.24*s,z+(.5+(i%3)*.1)*s)
            R('Plant stem',(x,y,z+.3*s),tip,.012*s,'leaf');leaf=S('Soft leaf',tip,(.10*s,.055*s,.17*s),'leaf');leaf.rotation_euler=(.45*math.sin(a),.6*math.cos(a),a)
    if key=='slide':
        B('Landing',(0,.65,1.5),(1.15,1.1,.16),'mint')
        for x in (-.5,.5):
            for y in (.18,1.10):R('Rounded tower post',(x,y,.08),(x,y,2.28),.09,'mint');S('Post cap',(x,y,2.29),(.11,.11,.11),'butter')
        # Open airy canopy with a soft domed roof.
        S('Marshmallow roof',(0,.67,2.34),(.77,.72,.28),'rose')
        for x in (-.51,.51):Q('Platform rail',[(x,.15,1.97),(x,.58,2.03),(x,1.10,1.97)],.06,'butter')
        for i in range(6):B('Wide access step',(0,1.25+i*.19,1.45-i*.245),(.91,.28,.13),'wood',.045)
        for x in (-.46,.46):R('Stair rail',(x,1.1,1.96),(x,2.38,.72),.045,'mint')
        # Continuous chute surface with raised side walls, no staircase slope approximation.
        pts=[]
        for k in range(25):
            t=k/24;y=.15-2.6*t;z=.13+1.45*(1-(3*t*t-2*t*t*t));pts.append((y,z))
        verts=[]
        for y,z in pts:
            for x,dz in [(-.49,.16),(-.39,.018),(0,0),(.39,.018),(.49,.16)]:verts.append((x,y,z+dz))
        faces=[]
        for k in range(24):
            for j in range(4):a=k*5+j;faces.append((a,a+1,a+6,a+5))
        o=mesh('Continuous rounded chute',verts,faces,[m['peach']],root)
        bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Chute thickness','SOLIDIFY');mod.thickness=.055;bpy.ops.object.modifier_apply(modifier=mod.name)
        for x in (-.49,.49):Q('Chute lip',[(x,y,z+.16) for y,z in pts],.055,'peach')
    elif key=='merry-go-round':
        C('Fixed rounded plinth',(0,0,.1),1.13,.2,'mint');deck=group('RotatingDeck',(0,0,.24),root)
        C('Rotating disc',(0,0,.27),1.02,.15,'butter',deck);C('Hub',(0,0,.53),.16,.65,'cream',deck)
        for i,c in enumerate(('rose','lilac','sky','peach')):
            a=i*math.pi/2;x,y=math.cos(a)*.72,math.sin(a)*.72
            seat=B('Padded seat',(x,y,.40),(.50,.40,.14),c,.065,deck);seat.rotation_euler.z=a
            Q('Rounded safety handle',[(x*.55,y*.55,.35),(x*.55,y*.55,.91),(x*.93,y*.93,.91),(x*.93,y*.93,.42)],.04,'cream',deck)
        for frame,angle in [(1,0),(61,math.tau)]:deck.rotation_euler.z=angle;deck.keyframe_insert(data_path='rotation_euler',frame=frame)
        deck.animation_data.action.name='CarouselStudy'
        for f in deck.animation_data.action.fcurves:
            for p in f.keyframe_points:p.interpolation='LINEAR'
    elif key=='monkey-bars':
        for x in (-.58,.58):
            for y in (-1.15,1.15):R('Rounded ladder upright',(x,y,.08),(x,y,2.45),.075,'mint');S('Upright cap',(x,y,2.45),(.087,.087,.087),'mint')
            R('Long top rail',(x,-1.15,2.42),(x,1.15,2.42),.065,'mint')
        for i in range(7):R('Overhead rung',(-.58,-1.12+i*.373,2.42),(.58,-1.12+i*.373,2.42),.045,'butter')
        for y in (-1.15,1.15):
            for z in (.35,.73,1.11,1.49,1.87):R('Ladder rung',(-.58,y,z),(.58,y,z),.045,'butter')
    elif key=='campus-gate':
        for x in (-1.05,1.05):B('Gate column',(x,0,1.0),(.3,.4,2),'mint',.14);S('Gate cap',(x,0,2.04),(.22,.25,.22),'cream')
        Q('Soft campus arch',[(-1.05,0,1.85),(-.8,0,2.45),(0,0,2.74),(.8,0,2.45),(1.05,0,1.85)],.14,'peach')
        for x in (-1.57,1.57):plant((x,0,0),.8)
    elif key in ('shared-table','round-table'):
        if key=='shared-table':
            B('Honey shared tabletop',(0,0,1.08),(2.55,1.12,.14),'wood',.16)
            for x in (-.96,.96):
                for y in (-.34,.34):R('Table leg',(x,y,.05),(x,y,1.03),.075,'cream')
            B('Table runner',(0,0,1.158),(1.45,.24,.018),'mint',.025);plant((0,0,1.17),.40)
            for x in (-.82,.82):book((x,.28,1.21),.3,.09,'rose');cup((x,-.28,1.16))
        else:
            C('Round honey top',(0,0,1.08),.87,.14,'wood');C('Pedestal',(0,0,.55),.12,1.02,'cream');C('Stable rounded base',(0,0,.08),.50,.16,'cream');plant((0,0,1.16),.5);cup((.48,0,1.16))
    elif key=='chair':
        B('Seat cushion',(0,0,.56),(.62,.60,.14),'lilac',.07)
        B('Curved padded back',(0,.23,.98),(.66,.15,.65),'lilac',.11)
        for x in (-.22,.22):
            for y in (-.20,.20):R('Chair leg',(x,y,.04),(x,y,.52),.043,'wood')
        for x in (-.20,.20):R('Back support',(x,.24,.54),(x,.24,1.10),.025,'wood')
    elif key=='sofa':
        for x in (-.91,.91):
            for y in (-.25,.25):C('Wooden sofa foot',(x,y,.10),.075,.2,'wood')
        B('Sofa base',(0,0,.31),(2.20,.86,.32),'rose',.13)
        B('Padded back',(0,.32,.77),(2.16,.25,.83),'rose',.12)
        for x in (-1.02,1.02):B('Rolled arm',(x,0,.63),(.25,.86,.51),'rose',.12)
        for x in (-.5,.5):B('Seat cushion',(x,-.04,.52),(.88,.66,.19),'cream',.075)
        for x,c in [(-.7,'mint'),(.7,'butter')]:
            pillow=B('Throw pillow',(x,.14,.84),(.39,.18,.39),c,.085);pillow.rotation_euler[1]=x*.25
        Q('Back piping',[(-.87,.178,1.13),(0,.177,1.155),(.87,.178,1.13)],.009,'cream')
    elif key=='coffee-bar':
        B('Sage cabinet',(0,0,.51),(2.2,.75,1.02),'mint',.08);B('Wood counter',(0,0,1.07),(2.32,.84,.13),'wood',.07)
        for x in (-.72,0,.72):B('Cabinet door',(x,-.384,.55),(.66,.035,.78),'cream',.025);R('Brass handle',(x-.10,-.412,.78),(x+.10,-.412,.78),.017,'butter')
        B('Espresso machine',(-.48,.05,1.43),(.58,.46,.58),'lilac',.08);B('Drip tray',(-.48,-.23,1.2),(.5,.20,.06),'dark',.025)
        for x in (-.59,-.37):C('Machine dial',(x,-.192,1.59),.044,.018,'butter').rotation_euler.x=math.pi/2
        R('Steam wand',(-.24,-.16,1.47),(-.19,-.24,1.30),.016,'dark');cup((.33,-.12,1.14));plant((.80,.09,1.14),.45)
    elif key=='laptop':
        B('Laptop base',(0,0,.028),(.56,.40,.056),'sky',.025);B('Keyboard',(0,.035,.06),(.45,.19,.008),'dark',.007)
        for row in range(3):
            for col in range(8):B('Key',(-.185+col*.053,-.024+row*.05,.066),(.038,.03,.006),'cream',.003)
        B('Trackpad',(0,-.12,.061),(.16,.064,.006),'cream',.008)
        lid=group('LaptopLid',(0,.17,.045),root);screen=B('Display shell',(0,.184,.255),(.56,.032,.42),'sky',.025,lid)
        B('Display',(0,.165,.255),(.49,.009,.34),'cream',.014,lid)
        for i,c in enumerate(('mint','lilac','peach')):B('Decorative screen tile',(-.135+i*.135,.157,.26),(.104,.006,.15),c,.015,lid)
    elif key=='bookshelf':
        B('Shelf back',(0,.19,1.04),(1.30,.08,2.08),'cream',.045)
        for x in (-.64,.64):B('Wood upright',(x,0,1.04),(.105,.46,2.08),'wood',.04)
        for z in (.10,.68,1.26,1.84):B('Shelf',(0,0,z),(1.28,.46,.08),'wood',.035)
        colors=['rose','sky','butter','lilac','mint']
        for row,z in enumerate((.39,.97,1.55)):
            for i in range(7):book((-.48+i*.157,-.015,z),.11,.38+(i%3)*.04,colors[(i+row)%5])
        plant((.29,0,1.89),.45)
    elif key=='planter':plant((0,0,0),1.8)
    elif key=='reading-lamp':
        C('Lamp base',(0,0,.07),.32,.14,'wood');R('Stem',(0,0,.1),(0,0,1.72),.035,'butter')
        bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.42,radius2=.23,depth=.40,location=(0,0,1.69));o=bpy.context.object;finish(o,'Linen lampshade',m['cream'],root)
        C('Shade rim',(0,0,1.49),.43,.05,'rose');S('Warm bulb',(0,0,1.50),(.10,.10,.10),'butter')
    elif key=='wall-art':
        B('Rounded wooden frame',(0,0,.60),(1.30,.08,1.20),'wood',.06);B('Ivory canvas',(0,-.047,.60),(1.14,.025,1.04),'cream',.025)
        S('Abstract sun',(.23,-.067,.83),(.18,.014,.18),'butter');S('Abstract sage hill',(-.15,-.07,.31),(.43,.016,.21),'mint');S('Abstract lilac hill',(.23,-.085,.22),(.36,.014,.13),'lilac')
    elif key=='garden-tree':
        R('Rounded trunk',(0,0,.04),(0,0,1.42),.13,'wood')
        for p,s in [((0,0,1.90),(.69,.57,.72)),((-.41,0,1.55),(.46,.46,.48)),((.43,.05,1.67),(.46,.48,.51))]:S('Marshmallow foliage',p,s,'mint')
        C('Soft planting ring',(0,0,.05),.52,.10,'cream')
    elif key=='rug':
        B('Plush rounded rug',(0,0,.025),(2.3,1.5,.05),'lilac',.18);B('Inset rug center',(0,0,.053),(2.07,1.28,.016),'cream',.17)
        for x in (-1.07,1.07):
            for y in (-.51,-.34,-.17,0,.17,.34,.51):R('Soft fringe',(x,y,.04),(x*1.11,y,.04),.018,'lilac')
    else:raise ValueError(key)
    return export_asset(root,key,'playground' if key in PROPS[:4] or key=='garden-tree' else 'study-hall','Original rounded '+key.replace('-',' ')+' module; ground-centered, Blender Z-up to glTF Y-up')
