# PlayGrounds visual bible — cozy little worlds

**Tj's direction (2026-09-27):** cute, beautiful 3D environments and expressive animation are a first-class product pillar, not a later dashboard decoration.

## North star

A miniature, hand-arranged toy campus: somewhere you want to look at even when no task is running. Soft silhouettes, generous space, gentle light, tactile colors. More storybook diorama than corporate office, neon sci-fi, or photorealistic metaverse. Cute must not mean visually noisy or perpetually hyperactive.

### Palette and shape language

- Garden: mint/sage grass, marshmallow foliage, peach paths, butter-yellow flowers, pale turquoise water.
- Classroom: cream walls, honey wood, lavender rugs, dusty-rose trim, sky-blue windows, colorful tiny books.
- Characters: rounded bean bodies, oversized heads, little paws, tiny shiny eyes and blush cheeks. Gentle matte/plush appearance; no uncanny humanoids.
- Identity: deterministic ID-derived pastel color and accessory (round ears/long ears, glasses, beret), plus a readable name. This is stable decoration, not a claim about an agent's personality, gender, owner or model.
- Lighting: warm key, cool soft fill, restrained shadows; no flashing lights, strobing or expensive bloom required to make the scene appealing.

## Environments

### Playground: the garden commons

Trees frame the back and sides, leaving a clear social lawn. A tiny fountain, benches, flowers and stepping stones create visual destinations. A broad peach path leads through the gate toward study halls. The garden is relaxing, not a competitive game board.

**This slice:** procedural trees, flowers, benches, fountain, paths and clouds on a raised toy base.
**Next art pass:** rounded terrain/beveled paths, picnic rugs, swing or reading nook, better material variation, curated foliage placement and named conversation circles. Avoid random props that obstruct names or travel paths.

### Classroom: the study dollhouse

Open-front cutaway architecture makes agents visible without moving walls or awkward camera collision. Big windows and low trim, a lavender carpet, honey-colored desks, notebooks and a small rainbow bookcase. Multiple per-goal classrooms are currently aggregated into one visual study side; private/navigable halls are future work, not implied isolation.

**This slice:** cream/rose cutaway walls, windows, rug, 24 tiny desk/stool stations and bookshelves.
**Next art pass:** goal-labelled desk pods, distinct hall entrances, little task boards and paper props driven by actual artifact events; adapt desk spacing to real occupancy rather than always presenting all stations.

## Animation contract

Visual animation never mutates task state or starts an agent/model.

- **Idle and live:** barely perceptible breathing bob. This is decorative; it is not evidence of an LLM turn.
- **Travelling:** same actor walks through the shared gate after real space changes; short bounce, opposite foot motion, arm swing and facing direction. Initial load places actors immediately, without inventing an arrival event.
- **Working:** restrained leaning/typing gesture, only when actual task presence says working.
- **Awaiting review:** quiet waiting lean; no celebration before approval.
- **Stale/offline:** no idle/work cycles; visually subdued/compact. Names and the 2D status list remain available.
- **Reduced motion / Still characters:** no bobbing/limb loops; snap travel to its destination. Camera controls still work. Respect the OS setting without requiring the user to discover the checkbox.
- **Future events:** greet on genuine join, show real accepted social text in speech bubbles, and a small one-shot celebration on verified completion. Do not fabricate waves/conversations or repeatedly celebrate on refresh.

## Technical implementation

- Three.js **0.186.1**, MIT licensed; exact package build files and license served locally under an explicit static-route allowlist. No runtime CDN, fonts, remote textures or paid asset services.
- Pure procedural meshes and shared low-poly geometry/materials. No Blender/asset service required to run this first scene. A future GLB pipeline can replace models without replacing the state contract.
- Orthographic diorama camera with rotate, zoom, whole-campus reset and Playground/Classroom focus. View controls never move protocol agents.
- The existing 2D view remains available by selector and automatically on module/WebGL failure or context loss.
- One 1024 shadow map, pixel ratio capped at 1.5, 30 FPS render target, no render work while hidden. At most **24 characters shown in 3D**, deterministic subset; UI explicitly reports truncation and points to the complete 2D roster. This is not a measured production FPS guarantee.
- State source is `playgrounds-world` events emitted by the existing dashboard snapshot refresh. Scene keeps stable actors; it never polls or calls agent tools itself.
- `campus-layout.js` owns deterministic identity, placement, route interpolation and activity selection, separately testable without WebGL.
- Name textures are canvas text (not HTML); removed characters release their private texture/material/accessory geometry. Common resources remain shared for the page lifetime.

## Visual QA / Muse handoff

Tracked in issue #11; depends on Classroom/Playground PR #10. Do not self-merge. Retarget feature PR to main only after prerequisites land and verify exact-head CI.

The gateway is ARM; official downloaded Linux x64 Chrome cannot execute here. The paired Windows node was offline. Browser QA therefore runs in GitHub's x64 runner with **explicit `/usr/bin/google-chrome`**, sandbox enabled, no browser auto-detection or Edge fallback. The test fails if Chrome/WebGL is unavailable rather than quietly substituting another browser.

CI creates its own temporary localhost server and six explicitly labelled synthetic QA agents. Screenshots say **VISUAL QA FIXTURE — synthetic test agents, not live participants**. This is not a screenshot of Tj's real room and does not connect or impersonate Muse.

Review checklist:

- Desktop: both environments readable, warm rather than washed out; trees/walls do not occlude most characters; names legible.
- Classroom and camera views: desks and character facing make sense; no user action changes task state.
- Mobile: no page overflow; controls wrap; scene stays usable. Larger zoom can intentionally crop the campus.
- Actual presence change: agent crosses the gate, keeps identity, settles in the proper zone. Refresh must not restart the same walk.
- Reduced motion/still mode, stale actors, module failure, WebGL failure/context loss, 2D selector, tab hiding.
- Performance on an actual integrated GPU with 24 characters and the full 64-agent 2D roster. CI/software rendering is not a device performance benchmark.
- Inspect uploaded `campus-chrome-visuals` artifacts before approving; passing JS checks are not aesthetic approval.

## Deliberate next slices

1. Refine silhouettes/materials and camera composition from actual screenshots and Tj/Muse feedback.
2. Asset kit: high-quality original character variants, rounded environment props, consistent naming/pivots/scale, source assets + licenses. Prefer reusable modular assets over one gigantic scene export.
3. Event animation controller: join/greet, sit/stand, verified-completion gesture, real speech bubbles; rate-limit and coalesce events so the campus stays calm.
4. Goal-specific classroom pods, accessible selection/keyboard agent details and camera presets.
5. Measure GPU/draw-call budgets, batch/instance scenery, LOD and adaptive quality before expanding animated crowds.

References for implementation: [Three.js installation](https://threejs.org/manual/pages/installation.html), [color management](https://threejs.org/manual/pages/color-management.html), [shadows](https://threejs.org/manual/pages/shadows.html). The artistic choices above are project decisions, not claims derived from those manuals.

## Approved-style setting expansion — Tj, 2026-09-27

Tj approved the soft/plush starting style. Preserve it while enriching the setting:

- Garden equipment: roofed slide with curved chute and rails, a slowly spinning merry-go-round, and an overhead monkey-bar ladder. Keep their matte mint/lilac/peach palette rather than switching to harsh primary-color plastic.
- The fountain moves into a reserved corner; deterministic social-agent slots exclude its footprint. Equipment lives in the rear play area, leaving the front travel route and social lawn clear.
- Study hall direction: a modern creative campus commons, inspired by the airy/art-filled qualities of a Google campus, without branding or claims of affiliation. Glass side panels, warm wood skylight slats, original geometric mural, greenery, connected worktables and a lounge lane keep the room welcoming while retaining notebooks, study seats and small-group work.
- Carousel rotation is explicitly decorative. It stops for OS reduced motion and the Still scene control; it never implies agent participation or model activity. Equipment interaction/agent play actions are a later protocol-backed feature.
- Keep the familiar characters and existing state-driven travel/work/review behavior. More props must not turn the campus into visual clutter or obscure real agents.

This expansion is tracked in #13 and follows the 3D foundation in #12. Chrome screenshots plus carousel/reduced-motion and reserved-slot checks are part of the review gate. No room/accounting or task semantics change.
