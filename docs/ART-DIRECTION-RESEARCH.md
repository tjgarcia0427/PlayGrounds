# Larger worlds, softer art — research and implementation brief

Research checked 2026-09-29. Author: VISIONQUEST. For Tj and Vision (Muse).

## Decision

Keep the original pastel/plush identity and the current vanilla Three.js renderer.
Use established offline tools for modeled assets; do not rebuild the app in a new
engine just to get nicer trees. The highest-value next art experiment is **one
fully art-directed scene slice**: a plush character, rounded reading chair, plant,
wood desk, soft daylight and subtle contact shading. Compare it against today's
scene before multiplying assets across a larger world.

This research is a source/architecture evaluation, not a performance benchmark or
claim that these libraries are already integrated. This PR implements the larger
scene with our original geometry, without new runtime dependencies or paid tools.

## Implemented enlargement

- Each base grows from 13.4 × 16 to 17.4 × 20 world units: 214.4 → 348 square units,
  **62.3% more floor area**. Character, workstation and equipment sizes stay fixed.
- Garden side adds a planted side promenade, cushion bench and shallow front terrace.
- Study Hall adds a reading-lounge wing, sofa, coffee table and plants; its glass
  boundary/back wall move outward. Existing task workstations stay in place.
- The enlarged navigation mesh includes new prop footprints. Cross-room walking
  still passes through the garden gate, including from the new front terrace.
- Camera framing grows for both individual rooms and campus; mobile remains
  room-focused. No increase to the 24-character renderer cap in this pass.
- New props are **set dressing**, not implemented sit/read interactions. New floor
  is reachable by the route planner but existing ambient schedules still target
  the established coffee/equipment anchors. This is not a crowd-capacity upgrade.
- Extension route tests exposed hundredth-unit rounding in three-pathfinding.
  Inflated obstacle bounds are now rounded outward before mesh generation, keeping
  returned rounded corners outside the actual clearance envelope.

## Evaluated tools and services

All links below are primary project/publisher sources. “Free” here means a usable
no-purchase option, not unlimited hosted GPU time or a commitment to future pricing.

| Option | Useful contribution | License/cost evidence | Fit and recommendation |
|---|---|---|---|
| [Poly Haven](https://polyhaven.com/license) | HDRI illumination, wood/material references, selective props | Asset files CC0; free downloads | Strong lighting source. Try one small overcast/studio HDRI, prefilter for PBR lighting, keep our pastel background rather than showing a photographic panorama. Asset permission is not blanket permission to scrape the site. |
| [ambientCG](https://docs.ambientcg.com/license/) | Fabric normal/roughness maps, subtle wood/ceramic detail | Assets CC0; free | Strong material source. Retint into our palette; test at 512–1024px instead of shipping enormous texture sets. Avoid heavy photo albedo/grunge on plush faces. |
| [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit) | Tables/chairs/shelves as clean starting meshes | 140 files, CC0, free | Good prop blockout. Rework proportions/bevels/materials so the world does not look like unrelated asset packs. Older static pack is not inherently unusable. |
| [Quaternius Ultimate Stylized Nature](https://quaternius.com/packs/ultimatestylizednature.html) | Trees, bushes and ground cover with existing stylized silhouettes | 63 models, CC0, FBX/OBJ/Blend/glTF on pack page | Strong garden candidate. Select a tiny subset and recolor; verify downloaded package license/hash. This specific free pack's terms do not imply all premium products are free. |
| [Blender](https://github.com/blender/blender) | Beveled hero props, UVs, rig cleanup, baked lighting/detail, GLB export | Open-source desktop tool; no hosted-service dependency | Preferred authoring tool. Already used for our original rig pipeline. Bake fine fur/material detail into runtime-friendly textures; don't export millions of hair strands. Check component/add-on licenses separately; GitHub reports repository license as NOASSERTION rather than a single simple SPDX value. |
| [glTF Transform](https://gltf-transform.dev/) | Inspect, deduplicate, resample animation, resize/compress textures and optimize GLB | MIT project; local CLI/SDK | Preferred asset build step once GLBs ship. Compression needs corresponding runtime decoders; don't compress blindly and assume our current loader supports it. Store reproducible commands and inspect output visually. |
| [N8AO](https://github.com/N8python/n8ao) | Contact/corner ambient occlusion for depth | CC0 repository; no service charge | Worth an isolated experiment. Supports orthographic cameras and vanilla Three.js, but introduces render passes/dependencies and extra GPU cost. Prefer restrained shading, optional low/disabled tier, and inspect halos, glass and moving plush edges. Not installed here. |
| [pmndrs/postprocessing](https://github.com/pmndrs/postprocessing) | A maintained composition pipeline for screen-space effects | Zlib license | Use only if an accepted visual experiment needs it. No bloom/DOF by default: those can blur faces, labels and interaction cues. Pin compatibility with our vendored Three version. |
| [Three MeshPhysicalMaterial](https://github.com/mrdoob/three.js/blob/dev/src/materials/MeshPhysicalMaterial.js) | Cloth sheen using our existing engine | Three.js MIT; source documents higher per-pixel cost | Best first plush-surface spike: low sheen on character fabric only, rough ceramic/wood elsewhere. Source recommends environment lighting. Sheen is not silhouette fur. Do not enable every physical effect on every mesh. |
| [Drei](https://github.com/pmndrs/drei) | Reference implementations for environment/contact-shadow helpers | MIT; React Three Fiber oriented | Excellent reference ecosystem, not a drop-in for this vanilla app. Do not add React/R3F merely to import a helper. Translate the rendering approach or select a vanilla implementation after checking license. |
| [UniMate](https://github.com/Friedrich-M/UniMate) | Offline generated motion for a compatible skinned character | Separate code/weights/dataset provenance must remain recorded | Motion research, not a mesh/fur generator. Our #37 result proves a hand-authored seed roundtrip only. Keep inference, topology/retargeting and runtime validation in #29; no claim of model-generated gestures yet. |

### Maintenance check, not popularity voting

GitHub API inspected at research time: N8AO, postprocessing, glTF Transform,
Three.js, Blender and Drei were all non-archived. Last observed pushes respectively:
2026-08-10, 2026-09-27, 2026-09-28, 2026-09-30 UTC, 2026-09-30 UTC, 2026-09-28.
A recent push is a health signal, not proof of compatibility/security. No star count
was used as a quality guarantee. Versions must be pinned when actually adopted.

No connector is necessary for this pipeline. Files can be authored locally and
reviewed through the existing GitHub/Chrome process. A Figma connector would help
shared UI design files, not improve mesh quality by itself. No plugin installed,
paid subscription started, or unpublished asset uploaded to a third-party service.

## Art recipe for PlayGrounds

These are our design recommendations, not claims made by the linked projects.

1. **Silhouette before detail.** Beveled edges, bulbous tree crowns, chunky seat
   cushions, clear prop sizes. Keep the character's expressive face and headphones
   readable. One hero plant beats fifty noisy photogrammetry plants.
2. **A small material family.** Soft fabric, pale wood, matte ceramic, muted metal,
   frosted glass. Share palette/materials between both rooms. Use normal/roughness
   variation lightly; keep base colors clean. No uniform glossy plastic treatment.
3. **Light like a miniature set.** Large-feeling warm key, cool fill, restrained rim.
   Contact grounding under feet and furniture is more useful than decorative glow.
   Keep one consistent tone-mapping/color pipeline; avoid double gamma correction
   when adding an effects composer.
4. **Give the floor breathing room.** Distinct pockets for active play, quiet garden,
   focused tables, couch collaboration and coffee. Preserve sightlines and the
   doorway route. Larger floors must not turn into vast empty checkerboards.
5. **Density by view.** Far view: simple silhouettes; near view: better fabric and
   facial detail. Do not add full fur geometry to every distant avatar.
6. **Motion with intent.** Keep anticipation/ease/settle and contact timing. Model
   and motion quality are inseparable: a lovely chair looks wrong if feet penetrate
   it. Pause ambient schedulers as well as transforms in still/reduced-motion mode.

## Phased follow-up for Vision

### A. Material-and-lighting slice (recommended next)

Create an isolated original plush/chair/plant scene, use one verified CC0 material
and one HDRI or existing soft lights. Compare standard material vs selective sheen
and baked contact detail. Include side-by-side Chrome evidence, file sizes,
renderer draw calls/triangles and a real-device frame-time sample. Pick the winner
on appearance **and** smoothness; do not claim software-rendered CI is a mobile
benchmark. No service keys or GPU subscription are required for this experiment.

### B. Asset pipeline, then selective set replacement

Author bevelled props in Blender. Export GLB with stable meter-scale dimensions,
origins and simple collision proxies. Run pinned glTF Transform inspection/cleanup;
keep a source asset manifest with author, exact source URL, license snapshot,
SHA256 and modifications. Preserve license notices where applicable. Introduce
one prop family at a time; reuse/instance repeated meshes. Generated lightmaps
must not bake an avatar into the environment.

Suggested starting budgets (targets, not measured achievements): 1K material maps,
1K environment lighting, a small shared material set and a few MB per room asset
bundle. Measure texture memory, network bytes, draw calls and CPU/GPU frame times
before setting final limits. Lazy-load close-up detail; maintain readable 2D fallback.

### C. Optional contact AO and additional animation

Prototype N8AO only after A/B establishes a need that baked/static shading cannot
meet. Check glass, thin railings, mobile resolution, camera motion and reduced
motion. Provide a plain-render fallback. Separately progress UniMate inference;
retarget approved clips to a production rig, with feet/hands/props checked during
interruptions. Never couple decorative actions to fabricated agent conversations
or ledger writes.

### D. Integration and release

Our expansion branches from main and deliberately excludes #40's unmerged gestures.
Review/merge each independently and rerun integrated Chrome checks after both land.
#27/#28 room UI also needs real backend validation, not only fixture screenshots.
Public HTTPS remains separate: hostname is plushplaygrounds.duckdns.org; #23's
revocation-delivery race and #38's credit/move-secrecy defects still need author
repairs and exact-head re-review. Do not expose those branches just to share art.

## Evidence and limits

Run `node mvp/test_expanded.mjs`, `test_campus.mjs`, `test_interactions.mjs` and
`test_playful.mjs`. The expansion suite covers 192 old-seat-to-extension routes,
new furniture exclusion, the glass-wall margin and gate-only cross-room paths.
Chrome CI runs full existing equipment/interrupt/ledger/reduced-motion/fallback
checks plus both expanded room views and a campus overview. Bind review to the
exact PR head and inspect the uploaded images before marking ready.

These tests do not prove dynamic crowd avoidance, new annex interactions, realistic
fur, GPU performance, or increased concurrent-agent capacity. Those are separate
milestones; do not market this footprint change as completion of them.
