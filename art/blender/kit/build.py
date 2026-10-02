"""blender -b -t 3 -P art/blender/kit/build.py -- characters|props|sheets"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'characters'
manifest_path=BASE/'manifest.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'version':1,'assets':[],'runtimeIntegrated':False}
if mode=='characters':
    from characters import STYLES,character
    entries=[character(*style) for style in STYLES]
elif mode=='props':
    from props import PROPS,prop
    entries=[prop(key) for key in PROPS]
elif mode=='sheets':
    category=sys.argv[-1] if sys.argv[-1] in ('characters','props') else 'characters'
    from sheets import render_sheets
    render_sheets(manifest,category);entries=[]
else:raise ValueError(mode)
for item in entries:
    manifest['assets']=[a for a in manifest['assets'] if a['id']!=item['id']]+[item]
if entries:manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('KIT_BUILD_COMPLETE',mode,len(entries),flush=True)
