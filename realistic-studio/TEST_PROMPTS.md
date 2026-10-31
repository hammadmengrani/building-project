# Try a different building

Replace the whole brief with this prompt, then click Generate with Groq. The initial example does not change until a new Groq design passes validation and Blender finishes building it. A failed request keeps the previous scene and displays the error.

```text
Create a completely NEW single-storey L-shaped courtyard house, different from the example square bungalow.

Use a 14 m wide × 12 m deep design envelope, front road at y=0. The left wing extends towards the rear; the front wing extends to the right. Leave a substantial rectangular courtyard gap at the rear-right so the building has a clearly visible L-shaped outline. Do not fill this courtyard with rooms or roof.

Include exactly 2 bedrooms, 1 shared bathroom, a living/dining room, a kitchen and connected circulation. Put the entrance near the front-left, bedrooms in the quieter rear part, and living/dining towards the front. Every room must be reachable through actual doors or portals. Provide exterior bedroom windows and courtyard-facing windows where possible. Furniture must stay inside rooms and clear of door approaches.

Use sage-green plaster walls (RGB 0.18, 0.31, 0.25), terracotta accents (RGB 0.66, 0.23, 0.12), charcoal flat roofs (RGB 0.09, 0.10, 0.11), warm timber bedroom floors and pale stone-colored living floors. Use rust and cream furniture colors.

Generate new room coordinates, openings and furniture placement. Do not reuse the example's 12 × 12 m square plan, central entrance or beige palette. Stay within supported rectangular-room, single-storey, flat-roof geometry. Return a complete valid furnished scene.
```

# Change only the building palette afterwards

Use this after successfully generating the L-shaped house:

```text
Keep the current room coordinates, room dimensions, openings and furniture positions exactly unchanged. Change only the color palette: exterior walls deep blue (RGB 0.06, 0.14, 0.28), accents warm copper (RGB 0.65, 0.30, 0.13), roofs dark graphite (RGB 0.07, 0.08, 0.09), living floors warm light grey, and sofa upholstery mustard yellow. Return the complete scene with the same layout and the new colors.
```

The provider may occasionally alter coordinates despite instructions. Compare roof-off views and saved project JSON when checking whether only colors changed.
