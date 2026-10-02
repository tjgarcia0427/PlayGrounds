# Squishy shell-fur study

Original isolated Three.js prototype; not production actors or live-agent proof.
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

Portrait/balanced/light: 64/32/16 instanced layers. One-character study only;
24-agent crowd, skinned rig, scene lighting integration, real-device performance,
fur/eye intersections at every angle and final visual match remain unaccepted.
Chrome CI is software-rendered evidence, not a real-device performance benchmark.

Reference visual capture could not be completed on the CI Chrome runner (the
reference picker never appeared). Public HTML/JS was inspectable by HTTP, but
an exact visual match is NOT established. No copied reference source is shipped.
