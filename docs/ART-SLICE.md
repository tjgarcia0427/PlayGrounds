# Art study 01 — a softer little world

Author: VISIONQUEST. Issue #43. Original art-direction sample; not production UI.

## Run locally

From the repository root:

```sh
python3 -m http.server 8497 --bind 127.0.0.1 --directory mvp
```

Open `http://127.0.0.1:8497/art-lab/` in Chrome. This static page does not talk to
the PlayGrounds server, load credentials or represent a connected agent.

## Implemented recommendation

A cream plush character, padded lavender headphones, upholstered chair, pale wood
table, ceramic mug, book, plant and soft architectural backdrop. Rounded furniture
uses Three's existing RoundedBoxGeometry implementation; studio illumination uses
its RoomEnvironment + PMREM. Both addons are pinned to the same0.186.1 version as
our existing engine, with source hashes and MIT notice in art-lab/addons. No new
framework, paid service, HDRI download or model inference.

Compare **Baseline** and **Soft studio** using the same geometry/camera:

- Baseline: rough standard materials, existing-style hemisphere/directional light.
- Soft studio: selective physical cloth sheen, original deterministic128px fabric
  bump texture, prefiltered room illumination and a subtle fixed-chair contact decal.
- Original cloth grain has no third-party license dependency. It is surface detail,
  not realistic per-strand fur. The fixed contact decal is not a general AO solution.
- Still scene defaults on. OS reduced motion overrides decorative breathing.
- Room data remains completely separate; public app/HTTPS wiring is unchanged.

This sample intentionally does not alter campus.js or require #40. The sample
plush is an original modeled study, not a replacement for stable agent identities.
Do not automatically replace every runtime character with this prototype.

## Verification

`CHROME_PATH=/usr/bin/google-chrome node mvp/browser-qa/art-check.mjs` after the
existing browser-qa npm install. Chrome sandbox stays enabled. CI also runs the
full existing campus/backend/MCP suite.

The sample checks A/B controls, actual renderer draw/triangle counts, desktop and
390px mobile layout, reduced-motion frozen clock, no external/API requests and
WebGL description fallback. Screenshots plus art-metrics.json are in the existing
campus-chrome-visuals artifact. Draw-count/triangle limits are guards for this small
fixture, not measured production capacity. Software Chrome CI is not a GPU/mobile
frame-rate benchmark. Inspect exact-head images before requesting review.

## Adoption plan for Vision

First agree on visual direction from the A/B sample. Then profile a real phone and
desktop: measure frame times, texture memory and loading cost with full24 avatars,
not just this one figure. Apply a small family of beveled props/materials to the
reading wing first; keep plain standard materials as a cheaper path. Reuse/instance
geometry rather than copying all these separate meshes per avatar. The128px grain
texture can be shared; PMREM should be generated once per environment, not per frame.

Before character replacement: integrate the production skeleton, preserve identity
palettes, test face/hand/foot contact and all current travel/equipment interruptions.
Any additional art pack must retain source/license/hash provenance. UniMate motion
inference stays a separate milestone. This PR ships only the reviewable static lab.

Reference rationale and alternative tools: [research brief](ART-DIRECTION-RESEARCH.md).
