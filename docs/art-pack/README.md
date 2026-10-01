# Art direction pack — plush characters & environments

**Tj's direction (2026-09-30):** rebuild the PlayGrounds art design —
characters and environments — based on this pack. It extends, not replaces,
the visual bible in `docs/ART-DIRECTION.md` (palette, shape language,
animation contract all still apply).

## What's in here

### `originals/` — project-owned, free to use and adapt

AI-generated for Playgrounds in the house style of the existing `mvp/avatars/`
plushes (mint bunny, sky bear lineage): fluffy fur, big round chibi bodies,
glossy black eyes, stitched smiles, pastel palette. Tj approved these on
2026-09-30 as the starting point for the rebuild.

- `peach-fox-plush.webp` — new character concept: peach-orange fluffy fox,
  cream belly and tail tip.
- `lilac-owl-plush.webp` — new character concept: round lilac owl, cream
  belly patch, feather tufts.
- `playground-env.webp` — playground environment concept: mint-teal towers
  with pink domes, orange slides, swing set, soft daylight.
- `study-hall-env.webp` — study hall environment concept: warm library with
  round shared desks, chalkboard wall, plants, window light.

### `references/` — third-party inspiration ONLY

Sourced from the web as design reference. **Do not ship these in the
product** — they are not ours. One candidate (a Sanrio character) was
deliberately excluded for IP reasons; keep that bar for anything added here.

- `fluffy-plush-character-ref.jpg` — fluffy plush texture and personality
  (source: aiscribbles.com).
- `pastel-playground-ref.png` — pastel 3D playground palette and softness
  (source: practicalpie.com).
- `cozy-library-ref.jpg` — study-hall warmth and mood (source: openart.ai).

## Rebuild notes for the art lane

1. New plush characters should sit alongside the existing four
   (`mvp/avatars/plushN.png` style): same fluff language, same chibi
   proportions, distinct silhouettes and pastel colors per character.
2. Environments should match the existing scene's diorama feel —
   `docs/ART-DIRECTION.md` "North star" — while taking composition cues
   from the environment concepts above (playground = open and playful,
   study hall = warm and focused).
3. Nothing in this pack is a runtime asset. The shipping scene stays
   procedural (see `docs/ART-DIRECTION.md` technical section); these images
   are design targets, not textures.
