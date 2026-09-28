# Animation toolkit and interaction pass

Research: 2026-09-27. Owner: VISIONQUEST. Review: Vision (Muse).

## Reuse decisions

| Tool | License / cost | Decision |
| --- | --- | --- |
| [Three.js animation system](https://threejs.org/docs/#api/en/animation/AnimationMixer) and [official blending example](https://github.com/mrdoob/three.js/blob/dev/examples/webgl_animation_skinning_blending.html) | MIT; existing dependency | Adopted AnimationMixer, reusable keyframe clips and crossfades. Custom clips match our current named plush parts, without swapping the approved characters for a generic humanoid. |
| [three-pathfinding](https://github.com/donmccurdy/three-pathfinding) | MIT; no service | Adopted pinned 1.3.0. Local vendored ESM ~10.5 KB; license, original tarball hash and adapted-file hash recorded. No CDN/runtime network requests. |
| [Quaternius Universal Animation Library](https://quaternius.com/packs/universalanimationlibrary.html), [download tiers](https://quaternius.itch.io/universal-animation-library) | CC0 assets; free Standard subset, paid expanded/source tiers | Candidate for the later glTF rig pass. Do not assume all advertised 120+ clips are in the free subset. None imported or purchased here. Need rig retargeting and per-clip review against plush proportions. |
| [Mesh2Motion](https://github.com/Mesh2Motion/mesh2motion-app) | Project documents MIT code / CC0 art | Promising free self-hostable GLB/GLTF rigging + animation-export workflow. Evaluated documentation only, not installed or claimed proven on our characters. Prefer local execution when we reach the authored mesh pass. |

No paid tool/service, hosted model generation, asset upload, or public deployment
was used. Blender remains a possible authoring stage, not a runtime dependency.
These libraries accelerate mechanics; they do not automatically produce the
reference's fur, expressive art direction, or polished hand/prop contact.

## Implemented first interaction slice

- Coffee: reserve spot → walk there → reach → sip with carried cup → return to
  the same workstation. One coffee visitor at a time.
- Carousel: reserve spot → approach → board → ride with rotating platform →
  dismount → return to the original social position. One rider at a time.
- Blended idle, walking, seated typing, reading, stretching, reaching, sipping,
  riding and waving poses via independent mixers sharing immutable clips.
- Ambient life checkbox schedules staggered visits. Follow + Preview interaction
  requests the same local loop on demand (no protocol commands).
- Fresh task/presence changes cancel decorative actions and release reservations.
  Carousel interruption exits its platform before ground navigation. Stale agents,
  departure and reduced motion cancel safely; hidden/2D view pauses presentation.
- Camera framing extent eases between room/campus states.

## Navigation and invariants

The small rectilinear navmesh is generated from shared desk dimensions and
expanded furniture footprints (0.34-unit navigation radius). The library finds
paths; our integration rejects partial routes. Every one of 24 desk positions
and 24 social positions is tested for complete routes, furniture clearance and
cross-room gate routing. Desk width/spacing changed to create real aisles.

Chair contact is represented by the seated pose, not a separately blocked navmesh
obstacle. Static furnishings and equipment footprints are modeled, not tiny
flowers or character-to-character collision bodies. Simultaneous protocol-driven
travel is not a crowd-simulation system; agents can pass each other. Do not claim
full dynamic collision avoidance. Avatar accessories can exceed the navigation
radius and may still need further contact/clearance tuning after art changes.

`InteractionDirector` has no network, messages or task writes. Authoritative
presence determines the room; decorative activity does not alter it. Read-only
DOM diagnostics expose current interaction stage/completion for browser QA.
This is not actual model reasoning, coffee acquisition, or social conversation.

## Validation

- Pure tests: 48 routes; obstacle sampling; gate traversal; both complete loops;
  exclusive leases; stale/departed/cancelled state cleanup; no descriptor mutation;
  Three.js pose blending and still mode.
- Chrome CI: public UI starts coffee and carousel cycles; captures sip and ride;
  waits for return; checks unchanged presence/ledger; desktop/mobile; real
  task-driven cross-room movement; reduced motion; 2D and WebGL failure fallback.
- Screenshots are labeled synthetic QA fixtures. Software-rendered CI is visual
  correctness evidence, not a mobile GPU benchmark.

## Remaining in #17

Slide and monkey-bar interactions; richer hand/foot contact and seated poses;
proper rigged glTF characters and facial expressions; cloth/fur material polish;
dynamic crowd avoidance; session-adapter wiring beyond the current task-derived
presence. Keep the approved pastel/plush direction throughout.
