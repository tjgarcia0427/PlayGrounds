# Playful polish pass — #20

VISIONQUEST implementation; Vision independent review. Continues milestone #17.

## Added

- **Slide:** reserve → approach rear ladder → climb → slide down the actual chute
  curve → land → happy squish/stretch → return to original social spot.
- **Monkey bars:** reserve → approach → mount → hang/traverse → drop → cheerful
  landing pose → return. Stylized plush arms stretch toward the bars; this is
  keyframed posing, not a finished IK/contact rig.
- **Variety:** each Playground character rotates carousel, slide, monkey bars on
  successful automatic/Surprise me starts, with a seeded starting activity. Activity picker also selects explicitly.
  Coffee remains Study Hall-only; incompatible requests are rejected honestly.
- **Expression:** seeded blinks, subtle idle head tilt, thoughtful reading nod,
  climbing, seated slide, hanging and happy landing clips with existing crossfades.
- **Physical coherence:** raised slide roof for character head clearance; the
  chute and traversal share one Three.js curve. Equipment routes include height,
  and labels follow characters up onto equipment.

## Interruption / accessibility

A real presence change interrupts decoration. Equipment has an explicit 3D exit
route, followed by normal furniture-aware ground navigation. Its lease stays held
until the interrupted character reaches the authoritative destination, preventing
another decorative user from boarding during that exit. Departure clears the lease.
Still scene / reduced motion snaps to authoritative positions and freezes pose
scheduling and blinks. Hidden/2D presentation remains paused. There are no new
network calls, model calls, social messages or ledger writes.

## Reuse and limits

Uses the already integrated MIT Three.js AnimationMixer/curves and MIT
three-pathfinding; no additional dependency, paid service or uploaded asset.
See [ANIMATION-TOOLKIT.md](ANIMATION-TOOLKIT.md) for the researched rigging tools.

These remain procedural toy characters. Final glTF rigging, per-finger/rung
contact, character-to-character crowd avoidance, face/mouth shapes, fabric/fur
surface quality and external session adapters are not claimed finished. An
extremely rapid second state change during an exit may use the existing safe
snap fallback when no ground route starts at the current elevated point.

## Evidence

Pure tests cover all 24 social positions to/from four new entry/exit points,
continuous complete loops, agreement with slide geometry, interruptions at every
equipment stage, held/released exit leases, rotating choices, room restrictions,
spatial path interpolation and reduced-motion blinking. Chrome captures slide and
monkey-bar poses, completes both loops, and interrupts a slide via a real task
claim. Existing coffee/carousel, state isolation, mobile and fallback checks remain.

Review/merge via Vision, never self-merge; no deployment in this pass.
