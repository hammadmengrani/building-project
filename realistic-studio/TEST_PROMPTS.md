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

## Prompt-selected interiors and service layers

Create a NEW single-storey L-shaped courtyard bungalow, footprint 18 × 16 metres, open courtyard at the rear-right. Keep the courtyard uncovered. Use flat roofs.

Include exactly 2 bedrooms, 1 shared bathroom, living/dining, kitchen and connected circulation. Do not add attached bathrooms. All rooms need usable door access and suitable windows.

Use traditional interior style overall: dark panelled timber furniture, burgundy and cream upholstery. Override BOTH bedrooms to coastal style with light slatted timber headboards and wardrobes. Use normal-size furniture, warm timber bedroom floors and pale stone living floors. Exterior: warm ivory plaster, muted coral accents and charcoal roof. Generate a fresh layout rather than reusing the previous apartment building.

Include the locally generated electrical wiring concept, cold-water supply, hot-water supply and drainage for the kitchen and bathroom fixtures. Keep each service network separately viewable. Include the construction concept layers for the frame, column reinforcement cages and column shuttering. These are concept visualizations, not a construction-approved design.

Outside: 2 parking bays with driveway, a 60-square-metre park and a separate 8 × 4 metre pool. Calculate a plot large enough to fit them without overlap.

After generation: select Roof off, Enter selected room; compare the traditional living room and coastal bedrooms. Click Show all services clearly, then test Concrete frame, Column rebar cages and Column shuttering under Construction stage. For a second style comparison ask: "Change the living room to industrial style and both bedrooms to minimalist style. Preserve room counts and the building footprint."

## U-shaped villa — independent materials and normal-view recovery

Create a NEW contemporary single-storey U-shaped courtyard villa.
Building envelope: 22 × 18 metres. Leave the rear central courtyard open and uncovered. Flat roofs only.
Exactly 3 bedrooms, 2 shared bathrooms, living/dining, kitchen and connected circulation. No attached bathrooms. All rooms need usable doors and suitable exterior/courtyard-facing windows.
Exterior: muted dusty-blue plaster, copper-colored accents, charcoal roof.
Use coastal style for bedrooms: light oak bed frames and slatted headboards, cream linen upholstery, oak flooring and white linen curtains.
Use industrial style for living/dining: exposed dark metal furniture frames, burnt-orange leather sofa upholstery, walnut tables and pale grey ceramic flooring.
Kitchen: navy painted cabinets and grey veined marble countertops. Bathrooms: pale grey ceramic floors and dark fittings. Do not reuse the previous beige palette. Store these as separate room/material specifications, not one global furniture tint.
Outside: 3 parking spaces with driveway, a 100-square-metre landscaped park and a separate 10 × 4 metre pool. Calculate a plot large enough for all features.
Keep furniture clear of doors. Make electrical, cold-water, hot-water, drainage and construction-concept layers available separately.
