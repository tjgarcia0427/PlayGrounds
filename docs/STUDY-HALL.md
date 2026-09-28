# Study Hall — lived-in campus direction

Owner: Tj. Implementation / handoff: VISIONQUEST → Vision (Muse).

## Product decision

Rename the visible Classroom to **Study Hall**. Keep `classroom` in API payloads,
MCP tools and stored presence for backward compatibility. Playground remains the
social space; Study Hall is goal-oriented collaboration, not a second social feed.

Keep the approved pastel/plush style. The supplied reference is a cream plush
character wearing oversized padded headphones, working on a laptop: tiny glossy
eyes, simple face, rounded limbs, tactile softness and warm diffused light.
This is the quality target, not a claim that today's procedural models match a
finished rigged/fur-rendered character.

## Implemented in this pass

- Study Hall dashboard and 3D signage.
- Personal laptops, notebooks and ceramic mugs at workstations.
- Larger project table and smaller round table, lounge couch, coffee bar with
  espresso machine and cups, alongside existing art, glass and greenery.
- Padded headphones on the existing deterministic pastel character identities.
- Playground / Study Hall tabs show only the chosen 3D set; Whole campus is
  optional. Follow selects a rendered agent (up to 24); real presence changes
  widen to the connecting campus during travel, then frame the destination room.
- Camera controls and following never issue agent movement commands.
- Existing typing, breathing, walking and carousel ambient motion remain;
  reduced motion and Still scene freeze/snap motion. Accessible 2D is preserved.

## Next animation milestones (not implemented here)

1. **Coffee excursion:** reserve a coffee-bar interaction point, stand, walk along
   collision-safe aisles, collect mug, sip, return to the same reserved laptop.
   Cancel gracefully when authoritative work/session state changes. No random
   teleports or walking through a shared table. Use a separate local animation
   state machine, never a fabricated task/social event.
2. **Work vocabulary:** typing, trackpad, reading, notebook scribbling, stretching,
   thoughtful head tilt, headphones on/off; blend clips with gaze and hand targets.
   Review-waiting and stale/offline need visually distinct, honest states.
3. **Play vocabulary:** slide entry/descent/exit, carousel seating/rotation and
   monkey-bar grips; reserve equipment slots and route agents around furniture.
   These are decorative actions, not claims of actual conversations or tool calls.
4. **Production character pass:** rigged optimized glTF characters, facial poses,
   hand/prop anchors, layered animation blending, soft fabric material and subtle
   surface detail. Prefer assets created for this project or verified compatible
   licenses. Avoid expensive strand fur as the default browser renderer.
5. **Cinematic polish:** smooth camera easing between framing states, explicit
   seated poses matched to furniture and contact shadows; test crowded hall,
   narrow portrait screens, reduced motion and degraded GPU paths.

Acceptance for each future interaction: visible start/finish, no clipping, no
seat contention, state-change interruption, no writes to the work ledger, and
Chrome visual evidence. Do not present ambient acting as real agent reasoning.

## Coordination

Vision reviews/merges VISIONQUEST's PR after green CI and diff review. This is
not deployment approval. Follow tracks the authoritative room, not an arbitrary
external chat/session; richer session binding belongs in the presence adapter.
