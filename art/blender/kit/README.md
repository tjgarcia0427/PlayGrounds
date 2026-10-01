# Plush workshop — Blender asset kit

Six companions, followed by sixteen environmental objects, built at Tj's request.
Original script-authored meshes/materials; no concept-image pixels, downloaded
character meshes or paid services. The reference targets remain
`docs/art-pack/originals/` and `docs/ART-DIRECTION.md`.

**Asset studies, not a live deployment.** Existing production actors, room routes
and authoritative activity are unchanged. The gallery is a loopback/CI review tool,
not a production route. Characters are short-velour/smooth plush studies, not the
concept's dense photographic fur. No mobile hardware FPS claim.

## Inventory

- Peach fox, lilac owl, mint bunny, sky bear, buttercup bear, rose fox.
- Playground: slide, merry-go-round, monkey bars, campus gate, garden tree.
- Study Hall: shared table, round table, chair, sofa, coffee bar, laptop,
  bookshelf, planter, reading lamp, wall art, rug.

Every asset has `.blend` source and self-contained `.glb` in `assets/`.
`manifest.json` records exact bytes, triangle counts, meshes, Z-up authored bounds
and SHA-256. Character mesh parts are batched under each named joint. Material
primitives still incur draw calls; mesh count is not a draw-call claim.

## Rebuild and verify

From repository root (Blender 4.0.2, tested on CPU ARM):

```sh
blender -b -t 3 -P art/blender/kit/build.py -- characters
blender -b -t 3 -P art/blender/kit/build.py -- props
python3 art/blender/kit/validate.py
blender -b -t 3 -P art/blender/kit/reimport.py
blender -b -t 3 -P art/blender/kit/build.py -- sheets characters
blender -b -t 3 -P art/blender/kit/build.py -- sheets props
```

Render sheets import the delivered GLBs. Character order is the list above;
prop sheet front-to-back, left-to-right follows the manifest's non-character order.
Props are scale-normalized in sheets/collections; individual assets retain scale.
CPU previews use bounded threads and 32 samples, no denoiser (the distro build lacks
OpenImageDenoiser). Fine image grain includes remaining render noise, not fur.

The formal Khronos `gltf-validator` 2.0.0-dev.3.10 is pinned in the browser QA
lockfile and checks all 22 GLBs with errors **and warnings** treated as failures.
Triangulation and exported tangent frames preserve the fabric normal-map basis.
Informational unused UVs/empty attachment nodes are retained intentionally.

Visual QA caught a valid-but-black normal image: setting Blender image color space
after assigning pixels reset generated image data. Color space now precedes pixel
assignment/update/packing, and Chrome checks decoded normal pixels (neutral red/green,
positive blue). A format-only validator cannot establish this material correctness.
The original fox generator is corrected too; its views are refreshed, not silently
reused. Final GLBs total approximately10.7MB; characters are each under0.84MB.

The original fox study remains in `../fox/` for comparison. The kit fox reduces
32,208 triangles / 34 meshes to 18,568 triangles / 9 joint-batched meshes, with
continuous two-material ears and a sewn rear seam. It is the new asset candidate.

## Browser review

```sh
python3 -m http.server 8769 --bind 127.0.0.1 --directory .
# In explicitly installed Google Chrome:
# http://127.0.0.1:8769/art/blender/kit/viewer/
```

This local static review command is not public hosting. The interactive gallery
loads actual GLBs through the official MIT Three.js 0.186.1 GLTFLoader (no custom
loader). Addon provenance/hashes are in `viewer/vendor/PROVENANCE.json`; core and
license are the existing locally served `mvp/assets/vendor/` files. No CDN.

Public gallery controls expose collection/individual selection, four viewing
angles, exported studies, actual campus idle/wave/typing/headphones animation
bindings, manual still and automatic OS reduced motion. Failed WebGL leaves the
asset list/downloads usable. `window.assetQA` is diagnostic observation only.

Pinned-Chrome CI drives those controls through
`mvp/browser-qa/blender-kit-check.mjs`. It captures every asset, six character side
views, three mobile collections and fallback, and tests head/tail/carousel motion,
campus wave/typing bindings, still and reduced motion. This is **synthetic gallery
QA**, not room travel, live identity or full crowd acceptance.

## Rig and integration boundary

- Object-jointed, not skinned; Blender Z-up converts to glTF Y-up and +Z forward.
- Named Body/Head/LeftArm/RightArm/LeftFoot/RightFoot/LeftEye/RightEye/Tail and
  MugSocket. Feet at ground; default arm/foot pivots match campus animation height.
- Independent exported head/tail study clips; Blender re-import initially activates
  only the first and stashes others muted. The round-trip test explicitly activates
  each target's imported clip; the gallery plays both. No inferred model motion.
- Carousel `RotatingDeck` is separate from the stationary plinth; its clip is a study.
- Before live adoption: full mug/blink/contact adapter, state-driven travel and
  interruptions, stale/removal/reduced-motion behavior in the actual scene, room
  classification, furniture collision/nav updates, crowd LOD/batching and device
  performance, then Muse exact-head review. No self-merge or deployment.
