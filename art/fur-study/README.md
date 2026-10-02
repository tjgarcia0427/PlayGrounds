# Squishy shell-fur study

Original isolated Three.js design comparison; not production actors or live-agent proof.
Tj's visual target: https://three-fur-test.vercel.app/ (2026-10-01), plush/furry
"dots" with minimal expressive faces, plus more squishy motion.

Uses the repository's licensed vendored Three.js. Reference site inspected as
visual/technical inspiration only; its bundle, shaders, characters and assets
are not redistributed. Independently authored latitude-based strand shader,
instanced shells, procedural cloud body, shaded roots/tips and damped
volume-preserving squash/stretch. Not a TRELLIS generation experiment.

Run `python3 -m http.server 8498 --bind 127.0.0.1` from repository root; visit
http://127.0.0.1:8498/art/fur-study/. No backend, credentials or external assets.
Squish by button or tapping canvas. Still mode and OS reduced motion freeze all
animation. Keyboard-accessible controls adjust palette, rotation, fluff and LOD.

Portrait/balanced/light: 64/32/16 instanced layers. One character rendered at a time;
24-agent crowd, skinned rig, scene lighting integration, real-device performance,
fur/eye intersections at every angle and final visual match remain unaccepted.
Chrome CI is software-rendered evidence, not a real-device performance benchmark.

Reference visual capture could not be completed on the CI Chrome runner (the
reference picker never appeared). Public HTML/JS was inspectable by HTTP, but
an exact visual match is NOT established. No copied reference source is shipped.

## User-requested comparison

- **Dot version:** cloud silhouette with over-ear headphones or wired earbuds.
- **Animal version:** rabbit (studio headphones), turtle (shell, round glasses,
  coral bandana), monkey (teal beanie, wired earbuds, curled tail), bird (wings,
  gold frames, lilac scarf).

Choose Design and Accessories in the viewer. All use the same original fur
shader, lights, camera scale and spring deformation. Accessories move with the
squish; this is stylized whole-character deformation, not a production skeletal
rig or physical fabric/headphone simulation. The comparison sheet is composed
from actual Chrome captures, not image-generation mockups. Tj has approved the
fur treatment; the choice of Dot vs Animal family remains his to compare.

## Selected core roster — 2026-10-01

Tj selected Dot with over-ear headphones, bird, rabbit and turtle as the four
core characters. Monkey and wired-earbud Dot are excluded from the core picker.
Removed the pale mouth/muzzle oval beneath the turtle's eyes. Preserve the
approved fur/squish treatment and existing signature accessories.
