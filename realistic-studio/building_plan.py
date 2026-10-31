"""Compose independently planned storeys around an aligned stair core and site."""
import copy
import math
import json
from geometry import validate, owners, intersects
from intent import DesignBrief
from planner import PlanningError, _compile_single, exposed, opening, collide_opening

def compile_building(brief, previous=None):
    if brief.action == 'palette':
        # Palette compilation is intentionally separate from room placement.
        result = copy.deepcopy(previous)
        if not result:
            raise PlanningError('A palette edit requires a previous building.')
        original_upper = result.pop('upper_floors', [])
        original_count = result.get('storeys', 1)
        original_core = result.pop('vertical_core', None)
        result['storeys'] = 1
        colored = _compile_single(brief, result)
        colored['storeys'] = original_count
        if original_core:
            colored['vertical_core'] = original_core
        upper = []
        for floor in original_upper:
            floor_brief = brief.model_copy(deep=True)
            groups = [group for group in brief.upper_floors if floor['level'] in group.levels]
            if groups:
                floor_brief.rooms = groups[0].rooms
            old = {**result, **floor, 'storeys': 1, 'upper_floors': [], 'vertical_core': None}
            changed = _compile_single(floor_brief, old)
            upper.append({**floor, 'rooms': changed['rooms'], 'furniture': changed['furniture']})
        colored['upper_floors'] = upper
        return colored
    pitch = brief.storey_height or brief.ceiling_height + 0.25
    if brief.storeys > 1 and (brief.width < 10 or brief.depth < 11):
        raise PlanningError('A multi-storey building needs at least a 10 × 11 m envelope for this stair-core planner.')
    levels = []
    core = None
    if brief.storeys > 1:
        core = dict(x=0.0, y=0.0, width=5.4 if brief.lift else 3.6, depth=5.4, storey_height=pitch, lift=brief.lift)
    program_cache = {}
    for level in range(brief.storeys):
        floor_brief = brief.model_copy(deep=True)
        floor_brief.storeys = 1
        floor_brief.upper_floors = []
        groups = [g for g in brief.upper_floors if level in g.levels]
        if groups:
            floor_brief.rooms = groups[0].rooms
        if core:
            floor_brief.depth = brief.depth - core['depth']
            floor_brief.entrance = 'front-center'
        signature = json.dumps(floor_brief.model_dump(), sort_keys=True)
        if signature not in program_cache:
            program_cache[signature] = _compile_single(floor_brief)
        planned = copy.deepcopy(program_cache[signature])
        if core:
            assemble_core(planned, brief, core, level)
        levels.append(planned)
    ground = levels[0]
    ground.update(storeys=brief.storeys, storey_height=pitch, vertical_core=core)
    ground['upper_floors'] = [dict(level=i, elevation=round(i * pitch, 4), name=f'Floor {i + 1}', rooms=f['rooms'], openings=f['openings'], furniture=f['furniture']) for i, f in enumerate(levels[1:], 1)]
    ground['site'] = plan_site(brief)
    errors = validate(ground)
    if errors:
        raise PlanningError('Building validation failed: ' + '; '.join(errors[:5]))
    return ground

def assemble_core(scene, brief, core, level):
    offset = core['depth']
    for r in scene['rooms']:
        r['y'] = round(r['y'] + offset, 4)
    for record in scene['openings'] + scene['furniture']:
        record['y'] = round(record['y'] + offset, 4)
    used = {r['id'] for r in scene['rooms']}
    if 'vertical_core' in used or 'floor_lobby' in used:
        raise PlanningError('Room IDs vertical_core and floor_lobby are reserved for shared circulation.')
    color = brief.floor_color.model_dump()
    stair = dict(id='vertical_core', name='Stair & lift core' if core['lift'] else 'Stair core', kind='stairs', x=0.0, y=0.0, width=core['width'], depth=core['depth'], height=brief.ceiling_height, floor_color=color)
    lobby = dict(id='floor_lobby', name='Floor lobby', kind='hall', x=core['width'], y=0.0, width=brief.width - core['width'], depth=core['depth'], height=brief.ceiling_height, floor_color=color)
    scene['rooms'].extend([stair, lobby])
    scene['width'], scene['depth'] = (brief.width, brief.depth)
    # The local sub-plan's entrance is now the lobby connection, not a door to air.
    for door in scene['openings']:
        if door['entrance']:
            door['entrance'] = False
    scene['openings'] = [o for o in scene['openings'] if o['kind'] != 'window' or len(owners(o, scene['rooms'])) == 1]
    scene['openings'].append(dict(id='core_access', kind='door', axis='y', x=core['width'], y=1.0, width=0.9, bottom=0.0, height=2.2, entrance=False))
    if level == 0:
        if brief.entrance in ('left', 'rear', 'right'):
            candidates = [(r, edge) for r in (stair, lobby) for edge in exposed(r, scene['rooms']) if edge[0] == 'y' and abs(edge[1] - (0 if brief.entrance == 'left' else brief.width)) < 0.001]
            if not candidates:
                raise PlanningError('The selected entrance side has no ground lobby boundary.')
            edge = candidates[0][1]
        else:
            left = core['width']
            edge = ('x', 0.0, left, brief.width)
        scene['openings'].append(opening(edge, 'door', 'building_entrance', scene['rooms'], 0.15 if brief.entrance == 'front-left' else 0.85 if brief.entrance == 'front-right' else 0.5, True))
    # Replace sub-plan windows that became internal with genuinely exposed windows.
    for r in scene['rooms']:
        if any((o['kind'] == 'window' and r in owners(o, scene['rooms']) for o in scene['openings'])):
            continue
        for edge in sorted(exposed(r, scene['rooms']), key=lambda e: e[3] - e[2], reverse=True):
            if edge[3] - edge[2] < 1.0:
                continue
            window = opening(edge, 'window', f"ext_{r['id']}", scene['rooms'])
            if len(owners(window, scene['rooms'])) == 1 and (not collide_opening(window, scene['openings'])):
                scene['openings'].append(window)
                break
    scene['access_roots'] = ['vertical_core'] if level else []
    scene['storeys'] = 1

def plan_site(brief):
    request = brief.site
    if not request or not (request.parking_spaces or request.park_area or request.pool_width or request.pool_depth or request.width or request.depth):
        return None
    W, D = (brief.width, brief.depth)
    columns = max(1, int((W - 2.0) / 2.6))
    rows = math.ceil(request.parking_spaces / columns)
    front = max(2.0, rows * 11.2 + 0.5)
    park_width = request.park_area / D if request.park_area else 0.0
    if request.park_area and park_width < 2.5:
        park_width = 2.5
    if bool(request.pool_width) != bool(request.pool_depth):
        raise PlanningError("A swimming pool requires both width and depth.")
    pool_strip = request.pool_width + 2.0 if request.pool_width else 0.0
    minimum_w = W + park_width + pool_strip + 3.0
    minimum_d = max(D, request.pool_depth + 2.0) + front + 1.5
    width = request.width or minimum_w
    depth = request.depth or minimum_d
    if width + 0.001 < minimum_w or depth + 0.001 < minimum_d:
        raise PlanningError(f'Parking/park do not fit the supplied plot. This arrangement needs at least {minimum_w:.1f} × {minimum_d:.1f} m; requested plot is {width:.1f} × {depth:.1f} m. No extra Groq call was made.')
    bays = []
    aisles = []
    for row in range(rows):
        y = -front + 0.2 + row * 11.2
        aisles.append(dict(x=0.0, y=y + 5.2, width=W - 2.0, depth=6.0))
        for col in range(columns):
            if len(bays) == request.parking_spaces:
                break
            bays.append(dict(id=f'parking_{len(bays) + 1}', x=col * 2.6, y=y, width=2.6, depth=5.2))
    park = dict(x=W + 1.0, y=0.0, width=park_width, depth=D) if request.park_area else None
    pool = dict(x=W + park_width + 1.5, y=1.0, width=request.pool_width, depth=request.pool_depth) if request.pool_width else None
    return dict(x=-1.5, y=-front, width=width, depth=depth, parking=bays, aisles=aisles, park=park, pool=pool)
