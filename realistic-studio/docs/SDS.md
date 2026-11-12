# Software Design Specification

## 1. Document purpose

This Software Design Specification (SDS) describes the current implementation of FORM / Architectural Studio in `realistic-studio`. It is intended for developers, maintainers, and testers who need to understand the guided and custom design paths, backend processing, data contracts, and current limitations.

This document records implemented behavior, not a promise that every requested architectural constraint can be solved. The studio is a visualization and concept-planning prototype; generated models are not construction documents or professional architectural, structural, or code-compliance advice.

## 2. Product overview

The application is a local browser-based 3D house-design studio. Users can enter a guided room program or write an advanced custom prompt. For a new AI design, the browser sends one text brief to the Python server. Groq interprets the brief into a constrained semantic design description; local Python code calculates room geometry and validates it; Blender builds the visual model and exports files.

The AI does not return room coordinates or executable code. Room layout, openings, furniture placement, geometry validation, and Blender construction run locally. A local planning failure does not trigger an automatic second Groq request.

### Goals

- Make a house brief easier to enter without requiring users to write a long prompt.
- Keep an advanced custom-prompt path for users who want direct control.
- Make clear that guided dimensions refer to the house's outer building footprint, not the plot.
- Keep the generated layout and 3D output inspectable and editable.
- Avoid spending additional provider requests on geometry planning or retries.

### Out of scope

- Architectural or engineering certification, permit documents, or code-compliance checks.
- A guaranteed solver for every room program, site, or dimension combination.
- IFC authoring, structural analysis, or construction-ready quantities.
- Multi-user accounts, production job scheduling, or remote public hosting.

## 3. Users and primary use cases

| User | Primary need |
|---|---|
| Homeowner or design learner | Describe a house using dimensions, floors, room counts, and preferences. |
| Advanced user | Submit a detailed natural-language prompt without the guided defaults. |
| Developer or tester | Exercise the one-request design flow, validate geometry, inspect exports, and diagnose failures. |

Primary use cases:

1. Load and inspect the bundled example without using Groq.
2. Generate a design from guided dimensions and per-floor room counts.
3. Generate a design from an advanced custom prompt.
4. Inspect the result, save/open a project, edit visual objects, and export.
5. Render a final image through Blender Cycles.

## 4. Core terminology: plot versus building footprint

- **Plot**: the land parcel. A 30 m × 40 m plot describes the site boundary; its area is 1,200 m².
- **Building footprint**: the outer width and depth occupied by the house on one floor. A 10 m × 12 m footprint is 120 m² per floor.
- **Storeys**: the number of floors. A two-storey, 10 m × 12 m house still has a 10 m × 12 m footprint; its approximate gross floor area is 240 m² before internal area deductions.

The guided form accepts **building footprint dimensions only**. Enter the house's outer width and depth, including the exterior boundary; the dimensions are not plot dimensions. The guided form does not estimate a house size from plot dimensions and does not collect plot dimensions. If plot context is needed, a user can mention it in the custom prompt, but the custom prompt does not guarantee site-fit analysis.

The guided form does not provide a wall-thickness input. The model builder controls wall construction; a natural-language request for an exact wall thickness is not a guaranteed adjustable constraint.

### Worked example

For a two-storey design with a 10 m × 12 m house footprint and the same program on both floors—2 bedrooms, 2 shared bathrooms, and 1 kitchen—the building dimensions mean:

- House footprint: 10 m × 12 m, including the outer building boundary.
- Approximate gross floor area: 120 m² per floor, or 240 m² over two floors before internal area deductions.

This does not say the plot is 10 m × 12 m. Plot fit, setbacks, access, and regulations are not checked by the guided form. If the requested program does not fit this house footprint, revise the room program or enter a larger building footprint.

## 5. Functional requirements

### FR-1: Guided brief

The guided form collects:

- Outer building width, depth, and units (metres or feet).
- Width, depth, and units (metres or feet).
- Total number of floors.
- Same room program on all floors, or a separate ground-floor program and repeated upper-floor program.
- Counts for bedrooms, shared bathrooms, kitchens, living rooms, dining rooms, and offices/studies; optional named additional rooms.
- Typical or flexible room sizing, optional minimum/maximum requirements, shape, lift preference, site features, and appearance preferences.

The browser converts feet to metres and composes a natural-language brief locally. Room counts are whole numbers from 0 to 20, and each floor program is limited to 20 requested rooms. A floor program must contain at least one usable room.

Typical guided mode adds recommended target/maximum areas to the prompt for supported room categories. These are instructions to the semantic interpreter and local planner, not a promise of exact areas. Flexible guided mode does not inject those typical targets/maximums.

### FR-2: Custom prompt

When custom mode is selected, the textarea is sent directly as the brief. The browser does not compose guided requirements or add guided typical-area limits. Shared server-side validation and planning still apply. Users should include all important dimensions, counts, units, and room-size rules in the custom text.

### FR-3: Single provider request

For a new design, the server submits one Groq chat-completion request with JSON response format and `max_retries=0`. The response must conform to the Pydantic brief contract. No automatic provider retry or provider-based geometry repair is performed.

### FR-4: Local layout and geometry checks

The local planner turns the semantic brief into rooms, circulation, openings, and furniture. The resulting scene is checked against the scene schema and geometry validator before Blender starts. If the brief cannot be fitted, the design job reports a planning/validation failure or requests more input rather than silently reporting a successful model.

### FR-5: Model, edit, and export

Blender builds the validated scene and produces exterior, interior, and cutaway GLBs and a packed Blender project. The browser supports viewport inspection, object transforms and color overrides, project save/open, GLB and Blender exports, and a separate Cycles render.

### FR-6: Example design

The bundled example can be loaded and built without a Groq request. It is labelled as an example and is not represented as a newly generated AI design.

## 6. Non-functional requirements

- **Provider cost control:** one provider request per submitted design; no automatic retries.
- **Separation of responsibilities:** the provider describes design intent; local code calculates coordinates and builds geometry.
- **Type and input validation:** JSON scene and intent data are checked through Pydantic models and geometry validators.
- **User feedback:** job status, validation failures, missing dependencies, and provider errors are reported in the interface.
- **Local secret handling:** the Groq key is read by the Python process and is not returned as a key to the browser.
- **Local deployment:** default binding is `127.0.0.1`; output is written to the application's `output/` directory.
- **Recoverable work:** each job has a separate output directory, and project data can be downloaded as JSON.

## 7. System architecture

```mermaid
flowchart TD
    U[User] --> UI[Browser UI<br/>HTML, CSS, JavaScript, Three.js]
    UI --> MODE{Generate mode}
    MODE -->|Guided| FORM[Validate answers and compose brief locally]
    MODE -->|Custom| TEXT[Use custom prompt text directly]
    FORM --> DESIGN[POST /api/design]
    TEXT --> DESIGN
    DESIGN --> QUEUE[In-memory job registry<br/>single-worker semaphore]
    QUEUE --> ONESHOT[one_shot.design]
    ONESHOT --> GROQ[One Groq JSON completion<br/>max_retries = 0]
    GROQ --> INTENT[Pydantic BriefResponse / DesignBrief]
    INTENT --> PLANNER[compile_brief<br/>planner + building_plan]
    PLANNER --> SCHEMA[Scene schema + geometry validation]
    SCHEMA -->|Needs input / invalid| STATUS[Job status and message]
    SCHEMA -->|Valid scene| FILES[Write scene.json and edits.json]
    FILES --> BLENDER[Blender background process]
    BLENDER --> OUTPUT[GLB views, .blend, logs,<br/>optional Cycles PNG]
    OUTPUT --> STATUS
    STATUS -->|GET /api/jobs/{id}| UI
    UI --> VIEW[Three.js viewport / project tools]
    UI --> BUILD[POST /api/build or /api/render]
    BUILD --> SCHEMA
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| `static/index.html`, `static/style.css` | Guided/custom controls and studio layout. |
| `static/app.js` | Form validation, prompt composition, job polling, 3D viewport, project operations, and UI feedback. |
| `server.py` | Static/API routes, request checks, in-memory job lifecycle, server-side secrets, and Blender subprocess invocation. |
| `one_shot.py` | Builds the provider request, makes one Groq call, parses the response, and invokes local brief compilation. |
| `intent.py` | Semantic brief models, provider prompt contract, normalization, defaults, and cross-reference validation. |
| `planner.py` | Single-floor room partitioning, doors/windows, furniture placement, and geometry candidate search. |
| `building_plan.py` | Multi-storey room programs, aligned stair/lobby core, and optional site planning. |
| `schema.py`, `geometry.py` | Scene data types and geometric/access/opening/furniture validation. |
| `scripts/building.py` and helpers | Blender geometry, materials, views, project file, and optional Cycles render. |

## 8. Design and request flows

### 8.1 Guided design flow

1. The user enters the building footprint and completes the floor program.
2. `guidedRequirements()` validates the form, converts feet to metres, and creates the prompt text using the entered house dimensions.
3. The browser sends `POST /api/design` with the prompt and optional previous scene. This is the only point where Groq is used.
4. `server.py` validates the request and enqueues a job. A single worker semaphore serializes design/build/render work.
5. `one_shot.design()` sends a JSON brief to Groq with the Pydantic JSON schema and no automatic retries.
6. `BriefResponse` and `DesignBrief` validate semantic intent. Missing colors and a null upper-floor list have defaults; invalid room references are rejected.
7. `compile_brief()` and the local planner produce geometry. Multi-storey designs are assembled with aligned stairs and floor lobbies.
8. The scene schema and full geometry validator run before Blender.
9. Blender writes model assets to `output/<job-id>/`; the browser polls job status and loads the resulting GLB.

### 8.2 Custom prompt flow

Custom mode skips guided form composition and estimate logic. The textarea is submitted as-is through the same `/api/design` route and provider contract. The local schema, planner, validation, and Blender stages are shared with guided mode. The advanced path therefore remains available but does not automatically receive guided sizing defaults.

### 8.3 Build and render flow

`POST /api/build` and `POST /api/render` accept an existing scene and visual edits. They validate scene data and do not call Groq. The render path additionally accepts a view and optional presentation settings, then invokes Blender Cycles.

## 9. API and job lifecycle

All POST requests require the session token in `X-Studio-Token`. The browser obtains the token from `/api/config`.

| Method and path | Purpose |
|---|---|
| `GET /api/config` | Returns local session token, provider/Blender availability flags, and configured model name. |
| `GET /api/demo` | Returns the bundled example scene data. |
| `GET /api/examples/four-storey` | Returns the validated four-storey sample and cached model availability. |
| `GET /api/jobs/{id}` | Returns the current in-memory job status/result. |
| `POST /api/design` | Enqueues one prompt interpretation and local design build. |
| `POST /api/build` | Enqueues a local rebuild/export from scene JSON; no Groq request. |
| `POST /api/render` | Enqueues a local Cycles render from scene JSON; no Groq request. |
| `GET /output/{job-id}/...` | Serves generated output files. |

Typical job status values are `queued`, `running`, `needs_input`, `complete`, and `failed`. The API returns HTTP 202 with a job ID for accepted work, HTTP 409 when another queued/running job prevents a new one, HTTP 403 for an invalid session token, and HTTP 400 for invalid request data. Job state is held in memory; it is not a durable queue and is cleared when the server restarts.

The server limits request bodies to 2 MB, design prompts to 10,000 characters, and validates transforms/material colors before use. Blender subprocesses have finite timeouts; detailed Blender output is recorded in the job's `blender.log`.

## 10. Data model

### Semantic brief

`BriefResponse` carries a user-facing message, readiness state, assumptions, unsupported requirements, and an optional `DesignBrief`. `DesignBrief` includes:

- Outer building width/depth in metres, shape, entrance, and ceiling/storey heights.
- Ground-floor `RoomIntent` values and optional grouped upper-floor programs.
- Room kinds, targets, optional minimum/maximum areas and minimum widths, furniture kinds, and optional bathroom attachment IDs.
- Global/room materials and RGB colors.
- Storey count, optional lift, and optional site data such as plot dimensions or outdoor features.

The provider schema does not accept room coordinates. Coordinates are assigned by the local planner.

### Compiled scene

`Scene` stores the building dimensions, rooms, openings, furniture, colors/materials, storeys, upper-floor layouts, vertical core, site data, and access roots. Coordinates and lengths are in metres. The browser's viewport coordinate convention differs from the Blender/source scene convention; conversion is handled by the frontend/backend.

### Job artifacts

Each job writes relevant artifacts under `output/<job-id>/`, including the provider response when applicable, `scene.json`, `edits.json`, Blender log, GLB view files, and `design.blend`; Cycles render jobs also write a PNG. Exact files depend on the job kind and whether Blender completes successfully.

## 11. Validation and error handling

Validation is layered:

1. Browser validation checks required fields, units, counts, dimensions, and room program size.
2. The server checks JSON shape, request size, session token, prompt length, scene data, and object edits.
3. Pydantic validates provider intent and final scene data, including ranges and references.
4. The geometry validator checks room bounds/overlaps, openings, access connectivity, furniture bounds/collisions, and RGB ranges.
5. Blender validates the scene again before building.

Errors are surfaced as job messages or API errors. Provider connection, authentication, rate-limit, incomplete-response, schema, local planning, missing Blender, and Blender process failures are distinct failure paths. A local planning rejection does not silently trigger another provider request.

### Room-area and width interpretation

- The guided typical-size selection sends target and maximum area preferences for supported room categories.
- Explicit minimum area and minimum width constraints are used by local room allocation; designs can be rejected when their minimums do not fit.
- The full geometry validator does not independently verify every requested room-count or requested maximum-area statement after compilation.
- In the current area-cap allocator, when requested target spans together exceed the available partition length, proportional allocation can exceed a stated maximum. Therefore `maximum_area` is not a hard postcondition in every constrained case.
- Area targets are preferences; room geometry and wall offsets also affect measured usable area. A result should be inspected against the original brief.

## 12. Security and privacy

- `GROQ_API_KEY` is loaded from the parent `.env` or application `.env`; it is not returned as a secret value by the config endpoint.
- Generated text is parsed as JSON under a strict schema. The application does not evaluate provider-generated Python or shell code.
- POST routes require a random token generated for the local server process.
- Static/output file resolution is constrained to the corresponding root directory.
- The default host is `127.0.0.1`; this local token mechanism is not production authentication.
- The application has no multi-user identity, authorization, durable tenant isolation, or automated output-retention policy. Do not expose it directly to an untrusted network without a separate security review and deployment controls.
- Job output may contain user prompts and generated scene content. Users/operators are responsible for protecting and cleaning stored output.

## 13. Deployment and configuration

### Requirements

- Python environment with packages in `requirements.txt`.
- Blender installed and discoverable on `PATH`.
- A Groq API key in the parent `.env` or `realistic-studio/.env` for new AI designs.
- Writable application output directory.
- Modern browser with WebGL enabled.

### Start

From the repository root, with the project's Windows virtual environment:

```powershell
Set-Location .\realistic-studio
..\venv\Scripts\python.exe .\server.py --port 8504
```

On Linux/macOS, the equivalent project launcher is documented in `README.md`. The default server binding is localhost. Set `GROQ_MODEL` optionally to select a model; otherwise the configured default is `openai/gpt-oss-20b`. Restart the Python process after changing server-side code or environment values.

## 14. Test and acceptance plan

### Automated offline checks

From `realistic-studio` with the project Python environment:

```powershell
..\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
node --check static\app.js
```

The tests cover semantic schema normalization, planner constraints, geometry validation, and the single-call provider path using simulated responses. These tests do not consume Groq quota.

### Manual guided test case

Use the following values in the guided form:

| Field | Value |
|---|---|
| Building footprint width × depth | 10 m × 12 m |
| Floors | 2 |
| Floor layout | Same rooms on every floor |
| Bedrooms per floor | 2 |
| Shared bathrooms per floor | 2 |
| Kitchens per floor | 1 |
| Living, dining, offices | 0 each |
| Room size preference | Typical |
| Shape / lift | No preference |
| Additional requirements | Keep the design compact; do not add rooms. |

Expected local prompt construction: the entered 10 m × 12 m dimensions are sent as the building footprint; there is no plot-to-building estimate. This room program and footprint are covered by an offline local-planner test fixture, but a live Groq response may differ. Generating the design makes one Groq request, and the provider or planner can still return an error.

### Equivalent custom-prompt test

Enable custom prompt mode and submit:

> Design a compact two-storey rectangular house. The plot is 30 m wide by 40 m deep. The house outer building footprint must be 10 m wide by 12 m deep on each floor; do not confuse the plot dimensions with the building dimensions. Repeat exactly this room program on both floors: 2 bedrooms, 1 shared bathroom, and 1 kitchen. Add no living room, dining room, office, or other room. Keep bedrooms around 12–14 m², kitchen around 8–10 m², and shared bathroom no larger than 4.5 m². Make every usable room at least 2.4 m wide. Use one central stair and connected circulation, not as extra user rooms. Arrange the rooms so they can have exterior windows where the plan permits. Keep rooms furnished and realistically scaled. If these requirements cannot fit the stated footprint, report the conflict rather than silently enlarging the house. Use a warm neutral wall palette, dark roof, and natural timber bedroom floors.

Expected behavior: custom text is sent directly; guided typical-size limits are not injected. The local planner and validation remain active. Room area ranges and exact 2.4 m widths are still subject to the actual compiled geometry and feasibility; inspect the result rather than treating prompt wording as proof of compliance.

### Optional integration checks

- `tests/api_smoke.py` requires the local server and Blender; it builds an example without Groq.
- `tests/live_groq.py` makes a real provider request and consumes quota; run only when explicitly desired and when credentials/network access are configured.
- Browser/WebGL and final Cycles rendering checks require the corresponding runtime dependencies.

## 15. Known limitations and risks

- The guided form accepts building footprint dimensions, not plot dimensions. It does not perform plot-fit, zoning, setback, orientation, or site-access analysis.
- The planner uses axis-aligned rectangular room geometry and a bounded search. It can reject otherwise plausible briefs, and multi-storey planning has a fixed stair/lobby core.
- The multi-storey planner requires at least a 10 m × 11 m building envelope. The stair core is currently placed at a corner rather than guaranteed to be geometrically centered.
- Room target areas are not exact dimensions; in constrained allocation, even explicit maximum-area caps can be exceeded as described above.
- The generated plan is not checked against local building codes, accessibility rules, structure, MEP design, fire strategy, or construction methods.
- The visual object editor does not recalculate room boundaries or certify a moved opening as a valid architectural change.
- Job state is in-memory and serialized through one worker. This is intended for a local prototype, not concurrent production traffic.
- AI output can be incomplete, ambiguous, or semantically wrong despite schema and geometry validation. A valid 3D scene is not proof that the brief was met exactly.

## 16. Source map

- User interface: `static/index.html`, `static/style.css`, `static/app.js`
- HTTP server and jobs: `server.py`
- Provider request and local compilation: `one_shot.py`
- Brief and scene contracts: `intent.py`, `schema.py`
- Local planning and validation: `planner.py`, `building_plan.py`, `geometry.py`
- Blender assembly: `scripts/building.py` and `scripts/`
- Automated tests: `tests/`
- Quick-start and project notes: `README.md`
