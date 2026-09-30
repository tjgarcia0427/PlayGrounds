"""Run the pinned upstream preprocess/animate pipeline on our original seed.
No model download/inference. No untrusted NPZ accepted: only own generated files.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from inspect_glb import inspect

UPSTREAM = '5d6aabedd947297b5ba6706d8e9113e68c0c3e4f'
MOTION = 'ac236251f90e5ca37c444c53ad383fc85de6d833'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--unimate', type=Path, required=True)
p.add_argument('--motion', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
for repo, expected in ((a.unimate, UPSTREAM), (a.motion, MOTION)):
    head = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], text=True).strip()
    if head != expected:
        p.error(f'{repo}: expected pinned revision {expected}')
    status = subprocess.check_output(['git','-C',str(repo),'status','--porcelain'], text=True)
    if any('/__pycache__/' not in ('/'+line[3:]) for line in status.splitlines()):
        p.error(f'{repo}: use a clean checkout')
out = a.output.resolve()
if out.exists():
    p.error('Output must be a new directory; existing results are never overwritten')
out.mkdir(parents=True)
env = dict(os.environ, PYTHONPATH=str(a.motion.resolve()), PYTHONDONTWRITEBYTECODE="1")
seed = out/'plush-seed.glb'
script = Path(__file__).with_name('create_seed.py').resolve()
subprocess.run(['blender','-b','-t','2','--python-exit-code','1','-P',str(script),'--',str(seed)],check=True)
print('Seed:', inspect(seed), flush=True)
root = a.unimate.resolve()
canonical = out/'canonical'
def upstream(script, *args):
    subprocess.run(['blender','-b','-t','2','--python-exit-code','1','-P',str(root/script),'--',*map(str,args)],
                   cwd=root, env=env, check=True)
upstream(Path('data_process/mesh_animation/preprocess_char.py'),
         '--char_path',seed,'--output_dir',canonical,'--face_r','R_Thigh','--face_l','L_Thigh','--formats','glb')
clips = sorted((canonical/'motions').glob('*.npz'))
if not clips:
    sys.exit('Upstream rejected seed: no motion features produced')
upstream(Path('data_process/mesh_animation/animate_lbs.py'),
         '--char_path',canonical/'plush-seed_canonical.glb','--anim_path',clips[0],
         '--output_dir',out/'roundtrip','--save','glb')
results = list((out/'roundtrip').glob('*.glb'))
if not results:
    sys.exit('No roundtrip GLB exported')
for asset in results:
    info = inspect(asset)
    if info['joints'] != 15:
        sys.exit(f'Unexpected topology after canonicalization: {info}')
    print('Roundtrip:', info)
print('PASS: upstream asset roundtrip. This is NOT model-generated motion.')
