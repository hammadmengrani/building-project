# Interior and electrical concept review

Status: **Concept only — not engineer reviewed.** No engineer has signed this generator's outputs.

## References researched

- Pakistan Engineering Council, Building Code of Pakistan — Fire Safety Provisions 2016, chapter 7, electrical fire safety: https://www.pec.org.pk/wp-content/uploads/2021/05/Building-Code-of-Pakistan-Fire-Safety-Provisions-2016.pdf
- NFPA 70 official overview: https://www.nfpa.org/codes-and-standards/nfpa-70-standard-development/70
- Blender Principled BSDF material reference: https://docs.blender.org/manual/en/5.1/render/shader_nodes/shader/principled.html

These references inform the review boundary; they do not certify the generated model or establish which edition a particular authority currently enforces.

## Implemented visualization

Furniture detail remains inside the existing planned footprints. Added bed panels/runner/feet, sofa pillows/feet, wardrobe and kitchen door fronts, cabinet pulls, backsplash, vanity mirror and shower screen/fittings. Skirting splits at doors. Narrow curtain panels occupy the window opening width. Ceiling fixtures and warm area lights are added to interior Cycles renders. Eye-level room cameras are available in the browser.

Electrical overlay uses amber for lighting circuit routes and blue for power circuit routes. These colors are diagram colors, not live/neutral/earth identification. Each floor has an illustrative distribution board. Each non-stair room has a light point and switch; dry occupied rooms also have one illustrative socket. Circuits are separate conceptual branches, not a final circuit schedule. Branches use orthogonal segments and can cross walls, openings, structural elements and other services. Switch placement is indicative, not clearance-verified against fittings. No mains riser or panel supply is designed.

The overlay and circuit report are generated locally without any extra provider requests. Architectural views hide the overlay by default in the app. GLB exports contain the overlay entities as separate categories; other viewers may show them all. Final Cycles images currently render the architectural interior, not an electrical diagram.

## Required before installation or engineer sign-off

A qualified electrical designer must confirm site jurisdiction and applicable code edition, supply characteristics, connected loads and diversity, circuit schedules, conductor sizing and voltage drop, short-circuit ratings, protective devices, earthing/bonding, wet-area and pool protection, equipment clearances, risers, firestopping and coordinated routes. Wet-area/pool sockets and circuits are deliberately not auto-generated.

Structural reinforcement is not designed by this change. Rebar diameter, spacing, anchorage and member sizes require structural loads, material properties, soil/seismic information and signed calculations. Mesh wireframe remains a mesh display, not a reinforcement drawing.

## Prompt-selected interiors and additional concept layers

The brief now stores a global interior style plus optional room overrides: modern, traditional, industrial, coastal or minimalist. Furniture-scale preferences are applied before collision/access validation. Stable design variants select different detailing. Traditional bed posts/panels, coastal slats, industrial metal frames, minimalist low bed bases and modern elliptical table variants are real geometry changes, not just recoloring. This is a bounded parametric vocabulary, not arbitrary text-to-mesh generation.

Plumbing concepts connect kitchen/basin/shower/toilet fixtures to cold/hot/drain riser diagrams. Toilets have no hot-water branch. Separate circuit elevations aid readability; drain gradients, venting, hydraulic sizing, external connections and equipment are not designed. Legacy wet rooms are recognized from their fixtures to avoid generating general-purpose socket markers there.

Construction stage views now contain a separate illustrative grid frame, column cages and column shuttering. Grid and member dimensions are assumptions, not structural design results. The model shows column reinforcement only; there is no complete beam/slab/footing reinforcement schedule. Construction JSON reports traceable assumed member volumes and indicative column steel/contact areas. It does not produce a procurement BOQ. Cement bag quantities remain unknown until an approved mix and bag mass are supplied. Report assumptions explicitly exclude structural analysis, reinforcement hooks/laps, waste and detailed intersection coordination.

All these layers are hidden in the normal architectural view and included in GLB exports. Concept views use viewport screenshots; Cycles rendering is restricted to finished architecture to avoid silently rendering a different layer selection.

## Normal view and material role update

Back to building clears electrical/plumbing isolation and construction-stage selection, restores Exterior / All floors / Rendered, and reframes the model without changing the design or object edits. The toolbar labels the active layer state.

Global and per-room material roles (wood, upholstery, stone, curtain, floor and wall) support independent RGB colors, finish family, roughness and metre-based texture repeat. Room overrides win over global overrides. Generated neutral grayscale albedo is tinted by the selected color, rather than forcing the original library image's hue. Finishes include oak, walnut, marble, stone, concrete, ceramic, linen, leather and plaster; plain is untextured. These are reproducible procedural materials, not scanned photogrammetry assets. Existing texture files remain in use for some reusable exterior/site components.

Browser lighting intensity and Cycles exposure were reduced to preserve bright-surface detail. Sofa seat count, low backs and traditional rolled arms add further geometry variation. Eye-level room cameras retain the selected room and aim at its bed/sofa when present, choosing a clear corner when available. This is camera positioning assistance, not a collision-controlled walking simulator.

## Detailed local furniture benchmark

The current detailed example contains a 4x5m bedroom, entry and bathroom within a 6x5m envelope. Scene access/openings/furniture clearances are validated before export. Curved furniture and textile meshes replace basic cushion blocks for bed/sofa furniture; separate converted piping meshes, folded duvet surfaces, pleated curtains, fitted door trim and recessed sanitary bowls are included. Geometry remains generated locally and uses the same entity IDs. These are custom parametric assets, not a scanned asset library.

The three view exports were inspected for mattress, piping, basin and ceiling entities, and a real 1200x900 Cycles bedroom image was rendered and visually reviewed. Numeric/geometry tests include centered opening deductions for skirting and curtain bounds. Live verification of the newly added detailed-example/ceiling controls was unavailable because the existing port 8504 server refused connection; it was not restarted by the agent.

This update changes visible detail and render assembly. The production BIM takeoff/structural-analysis work described in REALISM_BIM_FINAL_DRAFT.md remains separate and incomplete. No professional sign-off is implied.
