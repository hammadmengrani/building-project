# FORM / Architectural Studio

A separate local application in `realistic-studio`, with a Three.js editing viewport, a Python API, Groq brief interpretation, a local constraint-based floor planner, and Blender geometry/export/Cycles rendering. The earlier Streamlit applications are untouched.

## Run

From `/home/hammad/building-project`:

```bash
./realistic-studio/run.sh --port 8504
```

Open http://localhost:8504. The existing parent `venv` is used. For another machine install `requirements.txt` into a Python virtual environment and install Blender on PATH. The parent `.env` supplies `GROQ_API_KEY` and optionally `GROQ_MODEL`; a local `.env` can override these. No key is sent to the browser. Stop the server with Ctrl+C.

The example residence is explicitly labelled EXAMPLE RESIDENCE and is generated from `assets/demo.json`, without an AI request. Missing example models are built on server startup. Original texture sets are bundled; regenerate them with `python scripts/make_textures.py` if needed. Three.js 0.180.0 and its MIT licence are vendored locally. The optional Google Fonts stylesheet has system-font fallbacks.

## Included

- Wireframe, solid clay, material preview, and real-time rendered viewport modes.
- Grid and axes, orbit/pan/zoom, frame scene, top/front/right/perspective views.
- Object picking and scene outliner; move/rotate/scale gizmos and numeric properties.
- Movement/rotation/scale snapping, undo/redo, object reset and color overrides.
- Exterior, roof-off interior and low-wall cutaway variants.
- UV-mapped plaster, stone, timber, tile, grass and fabric with albedo, roughness and normal maps.
- Rounded edges, window framing, mullions, sills, door handles, entrance canopy and steps, parapets, facade trim, procedural furniture and individual-leaf trees.
- Project JSON save/open, GLB export with edits, packed Blender project export, viewport PNG screenshot, and a separate Blender Cycles PNG render.
- Local job queue and status, validated scene data and visible provider errors. Groq is called once to interpret requirements; local partition/door/furniture searches make no provider calls. The old paid repair button has been removed. No automatic provider retries.

## Workflow

1. Inspect the labelled example, or fill in the guided design questions (building footprint, floors and exact room counts) and click Generate with Groq. Enter the house's outer width and depth, including exterior walls; these are not plot dimensions. Typical guided room sizes send per-room maximums as planning preferences; they are not hard guarantees if the requested rooms do not fit. The advanced custom prompt is independent and only includes maximums when the user explicitly requests them. Optional preferences are available in an expandable section. Answers are combined locally and sent in one Groq request.
2. Groq returns a compact semantic brief: envelope dimensions, shape, room types/counts, preferred areas/zones, attached-bathroom relationships, furniture kinds and colors. It never calculates coordinates. The local planner searches variable partitions, adds connected circulation, calculates exact shared-wall doors and exterior windows, and searches furniture placements with door clearance. The full geometry validator must pass before Blender runs.
3. Click an object or its outliner entry. Use G / R / S for move / rotate / scale; Q selects, F frames the scene, Esc deselects. Ctrl+Z undoes; Ctrl+Shift+Z redoes.
4. Save project downloads both the scene and visual overrides. Open validates and rebuilds a saved project. Exports rebuild from this data so edits are included.
5. Render image runs Cycles at 1200×900 with denoising and 48 samples, using the current view, camera, sun direction and exposure. Its appearance differs from the real-time Three.js renderer. The output dialog provides a download.

See the [Software Design Specification](docs/SDS.md) for the architecture flow, API/job lifecycle, building-footprint example, guided test case, matching custom prompt, and known limitations.

Viewport coordinates are glTF/Three.js Y-up; source room coordinates are Blender Z-up. The backend converts visual overrides into Blender coordinates. JSON stores source design and separate entity overrides. Free object edits are visual changes; they do not recalculate room boundaries or certify a new structural plan. A moved window does not automatically recut the source wall opening. Use a Groq redesign for changes to room layout or opening placement.

Each request has its own `output/<job-id>/` folder with scene JSON, edits, GLBs, packed `.blend`, Blender log, and a PNG when rendered. Provider responses are saved alongside successful or geometrically invalid requests. Prior designs are retained when a new request fails.

## Scope and limits

This is an architectural visualization prototype, not a complete Blender replacement or a construction/BIM application. The engine supports multi-storey buildings with no fixed floor-count cap, aligned stairs and optional lifts, axis-aligned rectangular rooms, flat roofs, and 5–60 m building footprints. Sites support parking, parks and rectangular outdoor swimming pools. Repeated floor programs are planned once and copied locally. Larger buildings take more memory and export time. Layout and palette are generated from the brief; component construction and texture families are reusable. Curved buildings, arbitrary mesh editing, mesh sculpting, engineering verification and automatic photorealism are outside this version. Photoreal quality still depends on architecture, asset quality, material authoring and lighting.

Mobile layouts keep the brief and viewport available; detailed property editing is currently desktop-oriented. Deployment requires a Python host/container with Blender and writable output storage, rather than static hosting. Keep the default localhost binding for this local prototype; authentication, multi-user storage and production job infrastructure are separate deployment work.

## Verification

```bash
../venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
../venv/bin/python tests/api_smoke.py  # requires the local server; builds one example with edits
../venv/bin/python tests/live_groq.py # OPTIONAL: makes one real Groq request and consumes quota
```

Validated the example's seven-room layout, rejection of invalid geometry/transforms, single-call provider behavior with a simulated response, stable entity IDs and embedded PBR textures in three GLBs, correct parent/child coordinates, a local API build with exported position/rotation/color changes, a packed Blender project and a real Cycles render. Browser checks cover viewport modes, scene selection, numeric transforms and project saving. The new brief-to-geometry provider flow was tested with a simulated single response; no live provider request was made during the local-planner fix. Earlier live verification failed on provider connection/DNS; a loaded API key is labelled as such rather than reported as a successful connection.

## Local-planner fix and restarting an existing server

After updating the source, restart your own terminal server once (Ctrl+C, then `./realistic-studio/run.sh --port 8504` from the parent directory) and refresh the browser. An already-running Python process keeps its old imported generation code. This update does not stop or restart an existing server.

The regression suite now includes the actual failed Groq scene (overlaps, misplaced openings and disconnected rooms), a validated replacement for the 14×12 m L-shaped brief, rear-left courtyard reflection, different dimensions and room counts, rectangle/U configurations, attached-bathroom connections, deterministic variants, exact geometry preservation for palette-only edits and impossible-envelope rejection. Fifteen offline tests pass. A Blender build of the replacement produces three GLBs and a packed project in `output/local-l-courtyard/`.

For a zero-API test use Open in the studio and choose `l-courtyard-project.json`. This compiled design is clearly test data; it is not presented as a fresh Groq answer. Its source semantic brief is `assets/l-courtyard-brief.json`.

Room target areas are preferences, not guaranteed exact per-room dimensions. Circulation may be split into multiple rectangular rooms. Shape, required room groups, exterior bedroom windows and attached-bath access are checked locally. A brief that cannot fit the current partition vocabulary returns a fitting explanation without deleting requested rooms, substituting the example, or sending another Groq call.

After updating Python files, restart your own server with `./realistic-studio/run.sh --port 8504` from the parent directory, then hard-refresh the browser. An already running Python process retains its old imported prompt and schema.

## Detailed interiors and electrical concept

Hard-refresh the browser, then use **Update interior · no Groq call** to rebuild the current scene with the new furniture detail, finishes, ceiling fixtures and separate electrical entities. Select a floor and use **Enter selected room** for an eye-level camera. New generations automatically use the updated local Blender builder.

Under **Electrical concept**, show routes and optionally hide walls/furniture. Amber identifies lighting circuits; blue identifies power circuits, not wire insulation colors. Download the concept JSON report after rebuilding. The overlay is hidden by default in this app but remains separate geometry in exported GLBs. Cycles images currently render architecture without the overlay. There is no engineer sign-off, cable/breaker sizing or installable routing. See [design review notes](docs/DESIGN_REVIEW.md) for research sources and required engineering work.

### Prompt-selected styles, plumbing and construction layers

Restart the Python server after this schema update. Interiors support `modern`, `traditional`, `industrial`, `coastal` and `minimalist`, including room-specific overrides and furniture scale preferences. These select actual parametric furniture forms as well as finishes; arbitrary custom furniture meshes are not generated.

Use **Show all services clearly** to isolate electrical and cold/hot/drain networks. **Construction stage** switches between architecture, assumed concrete frame, column rebar cages and column shuttering. Three downloadable concept JSON reports explain omissions and dimensions. These are visual assumptions, not engineer-approved sizing, installation routes or a complete quantity takeoff. Use **Viewport screenshot** for concept views; Cycles renders finished architecture.

### Return to normal and prompt material roles

Use **Back to building** to clear isolated service/construction views and return to the finished exterior. The toolbar shows the active layer/shading state. Materials may be specified globally and per room using wood, upholstery, stone, curtain, floor and wall roles, each with optional color, finish, roughness and repeat_m. Supported finish families are procedural neutral maps; the prompt controls the tint. Existing projects remain loadable with default material choices. Restart the Python server for the new brief/scene schema, hard-refresh the browser and rebuild to update older GLBs.

### Close-up furniture and architectural detailing

The local builder now uses curved cushions with converted mesh piping, a sewn mattress, pillows, headboard upholstery and a folded/draped duvet mesh. Sofa seats/backs/arms use rounded textile forms. Basins and toilets have shaped recessed bowls; kitchen fittings include sink/tap, hob/burners and conditional upper cabinets. Door panels, hinges and architraves and pleated curtain meshes are modeled separately. Door skirting and curtain placement use opening centers correctly.

Use **Load detailed room** to inspect the dimensioned bedroom/bathroom example without Groq. Its canonical scene is `static/examples/detail-benchmark.json`; cached exports are used when present, otherwise the ordinary local build API builds them. **Enter selected room** enables ceilings; **Show ceilings in room view** controls the ceiling layer. Roof off and Back to building restore open/normal viewing. For an existing project, **Rebuild interior + services** applies the updated builder.

The benchmark Cycles image is stored at `output/detail-benchmark/render.png` when generated. A successful sample render and geometry export do not mean a full IFC quantity engine or engineering analysis has been implemented. Bonsai is not used by this update.

## React Native mobile prototype

The companion app lives in [`../form-mobile`](../form-mobile/README.md). It connects to this backend over a trusted LAN, includes an offline furnished GLB sample and supports native 3D/tabletop AR through a development build. Newly built scenes include clean `mobile-*.glb` exports and a metre-scale `mobile-manifest.json`; existing cached scenes must be rebuilt for mobile. See the mobile README for device support, Android setup and current prototype limits.
