# Small personality gestures — #39

Adds gentle look-around and headphone-adjust gestures to the **existing live
procedural characters**, independent of the offline UniMate experiment.

- Playground agents vary between breathing idle, a curious head turn, a brief
  headphone adjustment and waving. Stable agent seeds offset their schedules.
- Working Study Hall agents keep typing/reading/stretching and occasionally
  adjust their headphones. A separate seated clip retains body/foot support.
- Locomotion and equipment interactions take precedence; no new API calls,
  messages, conversations, game outcomes or work events are invented.
- The existing frozen director clock controls scheduling for reduced motion and
  still mode. Stale agents use static idle. Root navigation is never animated by
  a decorative clip.
- Three.js smooth tracks now accept different keyframe counts per channel;
  new head yaw and arm roll return to zero in every other clip to avoid residue.

## Verification

`node mvp/test_personality.mjs`: 64 seed schedules; seated height; arm continuity;
travel interruption; actual head turns; static pose and navigation-root isolation.
Existing interaction and playful-loop suites remain unchanged and must pass.

Chrome CI observes real mixed head/arm transforms during natural clock progress,
not just pose labels, and captures standing and seated gestures with synthetic QA
captions. It also checks decorative gestures leave the ledger unchanged. The full
existing travel, equipment, still-scene and mobile suite continues to run.

## Honest limits

This is ambient personality, not a reaction to another agent or generated social
behavior. Contact is approximate procedural posing, not finger IK or a skinned
production rig. UniMate's original seed/asset roundtrip is separate; these clips
are hand-authored and do not claim model inference. Crowded-agent collision and
real mobile GPU performance are not established by software-rendered Chrome CI.

Agent: VISIONQUEST
