# Prompt-controlled villa geometry

The semantic brief and strict scene now carry an optional `architecture` object. The local planner generates the room plan; the Blender builder creates facade details from actual exposed walls, openings and entrance orientation. There is no replacement static villa mesh.

Supported controls:

- `entrance_style`: canopy, portal or pergola, with independent `porch_width` and `porch_depth`.
- `roof_overhang` and level/stepped `parapet_profile`.
- `facade_panels`, timber `screens` and their `screen_spacing`.
- Optional open courtyard `pergola`; no enclosed roof is placed across the courtyard.
- `window_ratio`, `window_height`, `window_sill`; bathroom privacy windows remain modest. Openings still pass room-boundary/collision validation.
- `landscape_density`: minimal, balanced or lush.
- L/U/rectangular footprint remains an independent floor-plan request. Ask explicitly for L or U to change the building silhouette instead of merely recoloring a rectangle.

Room intents additionally accept `minimum_width` (usable short side) and `minimum_area` (usable square metres). Planner candidates that cannot meet these are rejected, rather than shrinking the requested rooms. Target areas remain preferences. Usable dimensions subtract the existing 0.18 m wall allowance.

Legacy scenes with no architecture object remain compatible. New architecture replaces the old repeated entrance canopy and front timber battens. Stone/wood finish colors come from the scene's material palette. Fixed pitched roofs, curves, arches and arbitrary free-form facades have not been added.

Blender presentation now opens with conceptual structure/formwork/rebar/services hidden, while the full GLB retains those selectable layers. Mobile GLBs continue to contain finished architecture only. Tinted albedos are saved to distinct generated texture files before packing, preserving their colors when a .blend is reopened. Hidden objects are explicitly removed between exported views to prevent duplicate geometry.

## Reproducible example and checks

`assets/luxury-villa-brief.json` is a test input, not a template that replaces user generation. `luxury-villa-project.json` can be opened with the studio's Open button; this builds locally without using Groq. The verified model is L-shaped with an open courtyard, two bedroom/bathroom suites, lounge/dining and kitchen. `output/luxury-villa-check` contains generated verification assets and is ignored by Git.

Tests cover minimum-room constraints, an impossible minimum, prompt-driven window changes, door/window-safe panel intervals and visibly different portal/pergola geometry. Blender smoke checks inspect the real GLB for the new elements; the saved .blend is reopened and rendered for visual verification. These checks do not verify the unresolved physical mobile-device crash.

Restart the existing Python backend after updating these modules. Existing generated scenes retain their geometry until rebuilt with an architecture brief; a palette-only edit intentionally preserves the footprint.
