# Final implementation draft: realistic architecture and traceable quantities

Status: implementation proposal. Existing application features are unchanged by this document.
Primary outcome: detailed architectural visualization backed by a measurable element model.
Mobile and AR implementation are out of scope for now; preserve units, stable IDs and optimized GLB outputs for later integration.

## 1. Cost boundary and stack

No mandatory paid desktop software or commercial rendering plugin.

| Component | Role | Cost/licensing boundary |
| --- | --- | --- |
| IfcOpenShell | IFC elements, geometry, openings, quantities and IFC export | Open source, LGPL; retain applicable license terms |
| Blender / Cycles | Detailed visualization, asset assembly, final renders and GLB export | Free/open source; no mandatory renderer subscription |
| Bonsai | Optional desktop IFC authoring/inspection and quantity cross-checking | Free/open source; not required on the application server |
| Existing browser viewer | Selection, floor/layer views, editing and quantity inspection | Reuse existing local Three.js viewer |
| Curated CC0 assets | Real-world furniture, PBR surfaces and HDRI lighting | Use only verified free assets with a source/license manifest; avoid paid plugins |
| Groq | Interpret prompt into constrained design and material/asset choices | Free tier has account/model limits; paid usage is possible and is not enabled by this plan |
| Hosting/GPU | Future deployment and rendering hardware | Local computer first; cloud execution is not assumed to be free |

No automatic paid-plan upgrades, purchases or paid asset subscriptions. A local form/manual specification must allow geometry rebuild and quantity checks without an AI call. Provider retries remain explicit, not an unbounded repair loop.

## 2. Single building model

Pipeline:

Prompt or manual specification -> validated design brief -> semantic building elements -> IFC and quantity calculations -> detailed render assembly -> optimized GLB and Cycles images.

Every measurable element needs a stable ID, storey, element type, dimensions, material/layer specification, openings, provenance and review status. IFC is the persistent exchange/element model; a validated application specification controls generation. Do not maintain an unrelated decorative structural frame as the source of production quantities.

Edits must distinguish semantic edits (wall length, thickness, opening dimensions, material layer) from visual-only edits (camera, decorative prop tint). Semantic edits rebuild dependent geometry and quantities. Visual-only changes must not silently change takeoff data.

## 3. Realism work

Replace the primary block-built furniture with a curated set of detailed assets or sufficiently detailed parametric assemblies. Keep collision envelopes separate from visible meshes. A library is acceptable; prompt-selected variants, sizes and combinations must visibly differ.

Initial furniture families: beds/headboards, sofas, dining tables/chairs, wardrobes, kitchen cabinetry and sanitary fixtures. Each asset records source, license, dimensions, orientation, collision envelope and supported material slots. Do not stretch an asset arbitrarily to fit a room.

Architectural components: layered walls, correctly dimensioned openings, door leaves/frames/handles, window frames/sills/reveals, glazing, skirting, ceilings and light fittings. Window/door placement must modify the wall opening rather than place geometry over an uncut wall.

Materials: curated PBR maps at real-world scale, independently controlled wood, upholstery, stone, metal, paint and curtain slots. Keep scans' characteristic appearance; tint only where appropriate, rather than treating every surface as a grayscale recolor. Existing procedural maps may remain fallback assets, not the primary realism solution.

Lighting: HDRI/daylight plus room fixtures, physically sensible exposure, consistent camera settings, material highlights and soft shadows. Produce interior eye-level and exterior final renders. Interactive GLB preview and final Cycles image are distinct quality tiers; do not label the preview as identical to the final render.

## 4. Calculation scope

First deliverable is quantity takeoff from specified geometry, not automatic engineering design.

| Work | Inputs and method |
| --- | --- |
| Walls/masonry | Layer thicknesses, net geometry, declared opening deduction rules, block/brick dimensions and mortar assumptions |
| Concrete | Explicit slab, column, beam and foundation members; declared union/junction rules to avoid duplicate volumes |
| Finishes | Relevant surface areas and explicit opening/edge deduction rules |
| Reinforcement | Supplied/approved bar schedule: diameter, count, centerline cutting length, bends, hooks and laps; no generic kg-per-m3 shortcut presented as an exact quantity |
| Formwork | Actual applicable contact surfaces; distinguish contact area from purchased panels/timber and reuse cycles |
| Cement/ingredients | Approved mix content per m3, bag weight and separate mortar/plaster recipes; otherwise show unknown, not fabricated bags |
| Electrical | Defined devices/circuits and coordinated routes; conductor count, extra lengths and exclusions stated |
| Plumbing | Defined fixtures and routes; separate hot/cold/drain lengths and fittings; coordination, slope and sizing require additional design inputs |

Every quantity row shows element IDs, formula/method, units, gross/net basis, deductions, inputs, uncertainty/review state and exclusions. Net modeled quantities, waste/procurement allowances and priced costs are separate columns. Rates require user-entered values, currency and date.

Automatic structural member/rebar sizing, electrical protective-device sizing and hydraulic/drainage design are separate engineering milestones. They require location/code, occupancy/loads, soil/material data, supply information and appropriate specialist review. Do not imply that an IFC model or quantity calculation certifies strength or installation safety.

## 5. Views and outputs

Views: finished architecture, technical wireframe, structural members, reinforcement, formwork, electrical, cold water, hot water and drainage. Every construction/service object links to the same building element or circuit model where implemented. Retain a one-click Back to building control.

Selectable elements display dimensions, materials, computed quantities and review state. Unsupported calculations show Missing inputs / Not calculated. Export IFC, GLB, Blender project, PNG and quantity CSV/JSON. Spreadsheet formatting is optional after numeric verification.

## 6. Implementation milestones and acceptance gates

### A. Benchmark room + bathroom

Use a fixed, dimensioned bedroom, adjacent bathroom, one connecting door and an exterior window. Build two visibly different interiors from the same geometry: coastal/light oak/linen and industrial/dark frames/leather. Include detailed fixtures, a ceiling and lighting.

Acceptance:
- Eye-level interior and exterior/section images visibly show fitted components, convincing scale and distinct furniture/material choices.
- No furniture/wall/door access collisions in the test scene.
- Element IDs and dimensions agree across application data, IFC and GLB metadata.
- Wall, floor and finish quantities match independently written manual calculations; target numerical tolerance <= 0.1% for the simple benchmark, with agreed deduction rules. This is a numerical test tolerance, not a claim about site-estimate accuracy.
- Increasing a wall length and adding an opening produces the expected quantity change without double subtraction.

### B. Complete single-storey house

Expand validated components to a new bungalow. Add shared-wall/junction handling, spaces, room-specific asset selection, material schedules and missing-input indicators. Keep the old project import path; explicitly label assumptions imported from legacy scenes.

Acceptance: manual spot checks on selected walls/slabs; no duplicate shared walls; courtyard and opening voids preserved; prompt/material revisions propagate correctly; existing projects remain reviewable.

### C. Structural/reinforcement quantities

Add explicit structural members and imported or engineer-specified reinforcement schedules. Replace the current assumed grid frame for quantitative use. Add bar marks/cutting lengths and contact-surface formwork. Keep concept frames visibly labeled until replaced.

Acceptance: junction cases and a known bar schedule reconcile independently; no generic complete-steel claim when only column bars exist.

### D. Coordinated electrical and plumbing

Move from branch diagrams to connected systems with explicit endpoints, routes, risers, fittings and clash flags. Report unresolved clashes. Route lengths become takeoff inputs only when the relevant route is accepted. Size circuits/pipes only after the required analysis inputs and rules are implemented.

### E. Multi-storey expansion and performance

Add stable vertical elements, repeated floor programs, grouped assets and controlled level of detail. Verify quantities across different floor programs and repeated storeys. Declare tested capacity; no fixed arbitrary floor cap, but no unlimited-resource claim.

## 7. Immediate next action

Audit installed IfcOpenShell/Bonsai availability and Blender compatibility without changing the running user server. Prepare the benchmark geometry, asset shortlist with licenses, expected manual quantities and two reference renders. Complete milestone A before expanding the generator or adding further decorative features. Install missing dependencies only through the normal sandbox approval flow when required.

## 8. Sources checked

- Blender licensing: https://www.blender.org/about/license/
- IfcOpenShell license/source: https://github.com/IfcOpenShell/IfcOpenShell
- Bonsai: https://bonsaibim.org/
- IfcOpenShell quantity helpers: https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/shape/index.html
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq billing: https://console.groq.com/docs/billing-faqs
- Poly Haven asset license: https://polyhaven.com/license
- Poly Haven API terms (separate from asset license): https://github.com/Poly-Haven/Public-API/blob/master/ToS.md

Free/open source software does not imply free cloud resources, unlimited API use or free professional engineering sign-off. All implementation milestones above are planned, not completed by writing this draft.
