# Peach fox — Blender prototype 01

Original geometry and packed fabric-normal texture created by VISIONQUEST, following
`docs/art-pack/originals/peach-fox-plush.webp`. No reference pixels, downloaded meshes,
paid service, external runtime texture or particle fur dependency.

**Not installed in the app.** This is a reviewable asset study, not a claim of
reference-quality fur or live PlayGrounds activity. PNGs are CPU studio renders.

## Reproduce

Blender 4.0.2 (tested on this ARM VPS):

```sh
blender -b -t 4 -P art/blender/fox/build.py
python3 art/blender/fox/validate.py
blender -b -t 2 -P art/blender/fox/reimport.py
```

`build.py` writes editable `peach-fox.blend`, web-ready `peach-fox.glb`, three
previews and measured `metrics.json`. The packed micro-normal survives GLB export;
it is lightweight fabric shading, **not fluffy silhouette fur**. CPU denoising is
disabled because this distro build lacks OpenImageDenoiser. No GPU required.

## Rig and integration boundary

- Blender Z-up converts to glTF Y-up; model faces glTF +Z, feet rest at ground.
- Body → Head / LeftArm / RightArm; feet are root children. Eyes are independent
  children of Head. Tail is a child of Body. Head pivot is 0.98 m high.
- Object-joint rig, not a skinned skeletal mesh. Two exported animation studies
  exercise head tilt and tail sway; round-trip test evaluates imported motion.
- Animation studies are **synthetic** and never imply agent activity.
- Existing campus animation contract remains authoritative. Do not run the sample
  clips over live state-driven animation. A production adapter still needs mug,
  blink, limb-contact, reduced-motion, stale-state and travel checks.
- This model is heavier than the current shared procedural actor. Do not substitute
  24 copies without mesh/material batching, a crowd LOD and Chrome profiling.

## Visual review

Front, three-quarter, and posed side previews cover ear taper, ivory cheek patches,
small embroidered mouth, headphone contact and swept ivory-tipped tail. First
inspection caught foot-patch intersections and angular tail silhouette; corrected
before final renders; side inspection also caught and corrected detached ear insets. Further artistry: softer cheek transitions, true short pile,
sewn seams and better paw articulation. This prototype intentionally does not claim
to have reached the concept image's dense photographic fur.

## Acceptance still required before replacement

Muse aesthetic review; runtime adapter and pinned-Chrome close-ups; actual activity
and reduced-motion checks; mobile/24-actor performance; passing exact-head CI and
independent merge. No public deployment in this PR.
