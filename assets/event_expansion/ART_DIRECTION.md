# Event illustration direction

## Latest user direction — 2026-10-13

The user stopped the impasto batch. Do not continue its prompts or select its
outputs for production. Artificial raised-paint texture and small stippled marks
look like pointillism and are not the requested style.

Use the two newly supplied paintings as the primary visual references:

- `style_reference_quarry.png`: workers, salt-well timber construction, partial
  fossil discovery and scholars studying stone in a believable Sichuan setting.
- `style_reference_observatory.png`: two scholars visibly observing the sky,
  bronze instruments and a mountainous Shu-road environment.

The vanilla reference sheet (`work/event-vanilla-style-reference.png`) and
existing water scene (`work/v020/assets/event_illustrations/water.png`) remain
secondary references for game integration and subdued illumination.

## Painting

- Natural digital painterly realism with coherent light and credible materials.
- Directional brushwork follows timber, stone, fabric, foliage and atmospheric
  depth; do not cover the whole painting in a uniform texture or stippled dabs.
- Readable subject, architecture and figures; moderate detail and breathing space.
- Restrained earthy and grey-green daytime palette, or subdued blue-grey dusk
  where the subject calls for it. Avoid harsh contrast or theatrical rim lighting.
- Do not ask for impasto, raised-paint ridges, embossed texture, pointillism,
  deliberately blurred clarity or an arbitrary three-element composition limit.
- Figures can participate naturally within a scene. They need not be tiny
  silhouettes, but the picture should remain an environmental event illustration.

## Storytelling

Make the event topic and immediate activity legible: examining exposed fossil
fragments, observing the sky, tending a horse, negotiating a bridge repair,
arriving in a village or working at a loom. Let the outcome remain unresolved.
Avoid both a purely empty landscape of obscure clues and an exhaustive tableau
that gives away every discovery or explains every event choice.

## Generation and delivery

Generate new scenes from scratch using the selected paintings only as style
references. Do not run a stylization conversion on a finished image. No UI,
captions, promotional typography, decorative frames or version numbers.

PNG originals and exact prompts belong in this development asset folder.
Reference images and discarded experiments must not be packed into runtime.
Only selected, verified exports should enter the game's illustration database.

`bamboo_traces_regenerated.png` and the impasto prompt set are retained as draft
history; they no longer establish the final style.
