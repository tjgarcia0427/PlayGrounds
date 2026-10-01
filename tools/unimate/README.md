# UniMate integration experiment

**Status: asset preprocessing + animation export validated locally. Model inference
not run. Not loaded into the production scene.** Issue #29.

## What this implements

- Original pastel plush/headphone calibration rig, 16 bones, one rigid-weighted
  skinned mesh, T-pose rest and four-second hand-authored motion. No third-party
  character assets. This is a technical seed, not final plush/fur art.
- Reproducible pinned UniMate preprocessing into canonical rig + topology +
  motion features; upstream LBS animation/export back to GLB.
- Lightweight GLB acceptance checks and CI roundtrip. This inspector is for
  trusted local artifacts, not a general hostile-upload security validator.
- No model weights, API keys, paid services, runtime dependencies or changes
  to existing app animations. Generated files stay out of Git.

## Reproduce (Blender 4.0 / Ubuntu 24.04 tested)

Install Blender plus its CPU preprocessing Python modules. On Ubuntu:

```sh
sudo apt-get install --no-install-recommends blender python3-numpy python3-scipy python3-loguru python3-tqdm python3-matplotlib python3-imageio
git clone https://github.com/Friedrich-M/UniMate.git /tmp/unimate
git -C /tmp/unimate checkout 5d6aabedd947297b5ba6706d8e9113e68c0c3e4f
git clone https://github.com/inbar-2344/Motion.git /tmp/motion
git -C /tmp/motion checkout ac236251f90e5ca37c444c53ad383fc85de6d833
python3 tools/unimate/preflight.py
python3 tools/unimate/roundtrip.py --unimate /tmp/unimate --motion /tmp/motion --output /tmp/plush-trial
```

Use a fresh output directory. The runner refuses to overwrite results and
rejects changed upstream revisions/source (Python bytecode caches excepted).
Only deserialize NPZ/NPY produced by this trusted pipeline: upstream uses
`allow_pickle=True`; never accept arbitrary uploaded pickle-bearing files.

Optional CPU preview (not a Chrome verification):

```sh
blender -b -t 2 --python-exit-code 1 -P tools/unimate/create_seed.py -- /tmp/seed.glb --preview /tmp/seed.png
```

## Measured result on the ARM64 VPS

- Blender 4.0.2 export: one skinned mesh, 16 bones, ~0.8 MB GLB.
- UniMate canonicalization: 15 bones (unweighted helper Root legitimately
  removed), all limbs retained; 1 accepted motion feature clip, 116 frames.
- Upstream `animate_lbs.py` exports the canonical character driven by the
  extracted seed clip. **That is a roundtrip, not a new AI-generated gesture.**
- First attempt exposed upstream's primary-mesh weighting assumption: separate
  mesh parts caused leg pruning. Join meshes before export. Subtle seed movement
  also failed its activity filter; use a clear calibration gesture. Do not lower
  quality thresholds just to force acceptance.
- Optional Draco compression unavailable in distro Blender; uncompressed GLB
  exports succeed. Do not mistake that warning for failed geometry export.

## Remaining inference gate

The inference entrypoint was attempted; it could not load its ML environment.
This host has no PyTorch/CUDA GPU; paired Windows node was offline. The released
requirements target Python 3.10 + CUDA 12.4. The sampler accepts a configured
CPU device, so CPU inference is not claimed impossible—just unvalidated here.
No weights or dataset bulk download was started and no paid GPU was provisioned.

Use the official v2 `unimate_uniml3d_f60_v2` 100000-step checkpoint and its matching
config/stats. Pin dataset revision `faaa81773b315247b03f183548e3898dbec2ce80` if
using its released dataset. Download only required files, not every checkpoint.

The local canonical `cond.npy` alone is NOT a ready inference dataset: the
sampler resolves object types through processed dataset/features and captions.
Next implementation must register this custom topology with the matching
feature loader/config and text/joint embeddings, without overwriting training
stats. Check the exact upstream APIs before building that adapter.

Upstream code now supports a rest-only preprocessing fallback despite the shell
wrapper describing animated input. We use an animated seed intentionally so
feature extraction and export are exercised, not merely skeleton import.

## Candidate clip and app integration contract

Start with wave, stretch, look-around, celebration—not cup grasping or climbing.
For each output retain upstream/checkpoint revision, rig hash, prompt, seed,
license/provenance, dimensions/fps, and reviewer disposition. Model output is
normally 60 frames at 30fps; longer clips need expansion or deliberate blending.
Code/weights are MIT; third-party dataset assets keep their own licenses.

Export canonical-rig GLB using upstream animation/export utilities. Use the
existing pinned Three.js stack (`GLTFLoader`, `AnimationMixer`, and skeleton-safe
cloning) when adding the real runtime integration. Do not retarget to today's
unskinned procedural avatar merely by matching part names. Keep the old avatar
as fallback until a properly weighted production rig and clip bank are approved.

Runtime movement stays authoritative: apply in-place motion under a navigation
parent; don't let generated root motion teleport agents or bypass equipment
leases. Validate loop seams, feet/contact drift, prop alignment, interruption,
reduced motion, CPU/GPU budget and 64-agent crowd behavior. Respect rooms and
state-driven travel; ambient clips must never fabricate task/social events.

Final gate: exact-head Chrome desktop/mobile screenshots/video against actual
room transitions, then Muse's independent review. No runtime visual claim is
made by this offline proof.

## Primary sources

- [UniMate project](https://linzhanmou.com/unimate/)
- [Pinned upstream source](https://github.com/Friedrich-M/UniMate/tree/5d6aabedd947297b5ba6706d8e9113e68c0c3e4f)
- [Official model card](https://huggingface.co/Linzhan/UniMate)
- [Motion dependency](https://github.com/inbar-2344/Motion/tree/ac236251f90e5ca37c444c53ad383fc85de6d833)

Agent: VISIONQUEST
