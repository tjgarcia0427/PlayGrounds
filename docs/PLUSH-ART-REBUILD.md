# Plush art direction — first runtime pass

VISIONQUEST · 2026-09-30 · issue #45

Tj selected Muse’s `docs/art-pack/` as the new visual target. This is an initial
runtime interpretation, not a claim of reference-render parity or production
performance on phones.

## What ships in this pass

- Six deterministic companion styles: peach fox, lilac owl, mint bunny, sky bear,
  buttercup bear and rose fox. Larger heads, species-specific ears/tufts/tails,
  cream face/belly panels, glossy catchlights, blush, stitched smile and headphones.
- Original seeded fabric bump texture and soft sheen. Experimental geometric fur
  was rejected after Chrome inspection: sparse fibers looked bristly and rounded
  tufts looked pebbly. This pass uses clean fabric shading, not a claim of fluffy
  offline-render fur. No downloaded textures, reference-image pixels or external CDN.
- Tiny face details do not cast separate shadows; head/body/limbs retain shadows.
- Rounded furniture/building edges, mint slide supports and pink toy turret dome.
- Warm rear bookshelves with colored books, arch crowns, window plants and desk
  stationery. Bookshelf footprints are included in pathfinding.
- A labeled Companion portrait control after selecting an agent. Camera position,
  aim and framing blend; reduced-motion switches directly. Actual room travel
  returns to wide framing. The portrait explicitly hides surroundings/other actors for clarity; normal room
  view restores everyone. It never changes protocol presence.

## Existing solutions and licenses

Reuses vendored Three.js `RoundedBoxGeometry` (MIT, 0.186.1), previously evaluated
in the art lab, rather than a new renderer or model service. Runtime import is
adapted to our local module. Exact source and hash are in
`mvp/assets/vendor/ROUNDED-BOX-PROVENANCE.json`; license is `THREE-LICENSE.txt`.

Art pack images are non-shipping visual references. Third-party references do
not confer redistribution rights. All new runtime geometry/texture data here
are original procedural work. No claim is made that the pack grants unrestricted
rights to its images.

## Animation and verification

Named joints and pivot anchors retain the existing procedural clip contract.
`test_plush_art.mjs` tests all six actual rigs, finite animated transforms,
navigation-root isolation, still mode, shared bounded fabric texture and shared geometry
lifetime. Existing route/equipment/interruption/personality suites remain intact.

`browser-qa/plush-check.mjs` uses explicitly pinned Google Chrome with sandbox on,
a real isolated backend and 24 labeled synthetic agents. It captures each observed
style, both rooms and mobile; records render metrics; verifies camera protocol
isolation, reduced-motion behavior and accessible 2D view. The existing full tour
covers equipment and real-session interruption. Software CI is not a phone GPU
benchmark. Review images before approving; do not infer appearance from test pass.

## Muse review / next iteration

Review exact CI head, portraits, both rooms and existing interaction screenshots.
Focus on silhouette, headphone/ear overlap, hand/prop contact, furniture clearance
and material detail at normal room scale. More layered foliage, authored furniture,
rigged contact poses and efficient hair shading remain subsequent art work.
Issue #45 stays open: this pass does not finish the entire art-direction roadmap.

Public application rollout remains blocked on secure-room delivery review. This
art PR changes no authentication, reverse proxy or production deployment.

— VISIONQUEST
