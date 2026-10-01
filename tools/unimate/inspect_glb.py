"""Small dependency-free gate for *local* candidate files, not an upload parser.
Checks self-contained GLB, skinned meshes, joint count and animation channels.
This does not replace Khronos validation, Blender roundtrip or visual review.
"""
import json
import struct
import sys
from pathlib import Path

def inspect(path):
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', raw)
    if (magic, version, length) != (b'glTF', 2, len(raw)):
        raise ValueError('Invalid GLB v2 header/length')
    size, kind = struct.unpack_from('<I4s', raw, 12)
    if kind != b'JSON' or 20 + size > len(raw):
        raise ValueError('Missing or truncated JSON chunk')
    doc = json.loads(raw[20:20+size])
    if any('uri' in x for group in ('buffers', 'images') for x in doc.get(group, [])):
        raise ValueError('Candidate must be self-contained (no external/data URIs)')
    nodes, skins = doc.get('nodes', []), doc.get('skins', [])
    if not skins or not any('skin' in n and 'mesh' in n for n in nodes):
        raise ValueError('No skinned mesh')
    joints = set()
    for skin in skins:
        if not 5 <= len(skin['joints']) <= 70:
            raise ValueError('Outside evaluated UniMate v2 joint range (5–70)')
        joints.update(skin['joints'])
    if any(j < 0 or j >= len(nodes) for j in joints):
        raise ValueError('Joint references missing node')
    animations = doc.get('animations', [])
    if not animations or not any(c['target'].get('node') in joints
                                for a in animations for c in a.get('channels', [])):
        raise ValueError('No skeletal seed animation')
    return {'bytes':len(raw), 'joints':len(joints),
            'animations':[a.get('name','unnamed') for a in animations],
            'skinned_meshes':sum('skin' in n and 'mesh' in n for n in nodes)}

if __name__ == '__main__':
    print(json.dumps(inspect(sys.argv[1]), indent=2))
