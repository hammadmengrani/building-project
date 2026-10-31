"""Pure-Python geometry validation and shared-wall construction."""
import math
EPS = 0.025

def edges(r):
    x, y, w, d = (r['x'], r['y'], r['width'], r['depth'])
    return [('x', y, x, x + w), ('x', y + d, x, x + w), ('y', x, y, y + d), ('y', x + w, y, y + d)]

def opening_span(o):
    return (o['axis'], o['y'] if o['axis'] == 'x' else o['x'], (o['x'] if o['axis'] == 'x' else o['y']) - o['width'] / 2, (o['x'] if o['axis'] == 'x' else o['y']) + o['width'] / 2)

def owners(o, rooms):
    axis, fixed, lo, hi = opening_span(o)
    return [r for r in rooms if any((a == axis and abs(f - fixed) < EPS and (lo >= l + 0.12 - EPS) and (hi <= h - 0.12 + EPS) for a, f, l, h in edges(r)))]

def bbox(f):
    t = math.radians(f['rotation_deg'])
    w, d = (f['width'], f['depth'])
    dx = abs(math.cos(t)) * w + abs(math.sin(t)) * d
    dy = abs(math.sin(t)) * w + abs(math.cos(t)) * d
    return (f['x'] - dx / 2, f['y'] - dy / 2, f['x'] + dx / 2, f['y'] + dy / 2)

def intersects(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 0.01 and min(a[3], b[3]) - max(a[1], b[1]) > 0.01

def _validate_floor(scene, stage='complete'):
    errors = []

    def err(m):
        errors.append(m)

    def finite(v):
        return isinstance(v, (int, float)) and (not isinstance(v, bool)) and math.isfinite(v)
    if not all((finite(scene[k]) and 5 <= scene[k] <= 60 for k in ('width', 'depth'))):
        return ['Footprint must be 5–60m in both directions.']
    rooms = scene['rooms']
    op = scene['openings']
    furn = scene['furniture']
    if not 1 <= len(rooms) <= 24:
        err('Need 1–24 rooms.')
    if stage != 'rooms' and (not 1 <= len(op) <= 80):
        err('Need 1–80 openings.')
    if len(furn) > 100:
        err('Furniture limit is 100.')
    for group in (rooms, op, furn):
        ids = [v['id'] for v in group]
        if len(ids) != len(set(ids)):
            err('Duplicate IDs.')
        if any((not i or len(i) > 40 or (not i.isascii()) for i in ids)):
            err('IDs need 1–40 ASCII characters.')
    byid = {r['id']: r for r in rooms}
    for r in rooms:
        if len(r['name']) > 60:
            err('Room name too long.')
        if not all((finite(r[k]) for k in ('x', 'y', 'width', 'depth', 'height'))):
            err('Nonfinite room geometry.')
            continue
        if r['x'] < 0 or r['y'] < 0 or r['x'] + r['width'] > scene['width'] + EPS or (r['y'] + r['depth'] > scene['depth'] + EPS):
            err(r['id'] + ' outside footprint.')
        if min(r['width'], r['depth']) < 1.58 or not 2.6 <= r['height'] <= 4.2:
            err(r['id'] + ' has implausible room dimensions.')
        if 'bed' in r['name'].lower() and (r['width'] - 0.18) * (r['depth'] - 0.18) < 9:
            err(r['id'] + ' bedroom clear area <9m².')
    for i, r in enumerate(rooms):
        for s in rooms[i + 1:]:
            if intersects((r['x'], r['y'], r['x'] + r['width'], r['y'] + r['depth']), (s['x'], s['y'], s['x'] + s['width'], s['y'] + s['depth'])):
                err(r['id'] + ' overlaps ' + s['id'])
    graph = {r['id']: set() for r in rooms}
    roots = set(scene.get('access_roots', []))
    approaches = []
    if roots - set(graph):
        err('Unknown vertical circulation access root.')
        roots.intersection_update(graph)
    for i, o in enumerate(op):
        if not all((finite(o[k]) for k in ('x', 'y', 'width', 'bottom', 'height'))):
            err('Nonfinite opening.')
            continue
        rs = owners(o, rooms)
        if not 1 <= len(rs) <= 2:
            err(o['id'] + ' must fit an exact room boundary, .12m from corners.')
            continue
        if not 0.4 <= o['width'] <= 6 or o['bottom'] < 0 or o['height'] < 0.3:
            err(o['id'] + ' invalid size.')
        if any((o['bottom'] + o['height'] > r['height'] + 0.01 for r in rs)):
            err(o['id'] + ' above ceiling.')
        if o['kind'] == 'window':
            if len(rs) != 1 or o['entrance']:
                err(o['id'] + ' window must be exterior, not entrance.')
        else:
            if abs(o['bottom']) > 0.001 or o['height'] < 2 or o['width'] < 0.8:
                err(o['id'] + ' invalid door/portal.')
            if len(rs) == 2:
                a, b = rs
                graph[a['id']].add(b['id'])
                graph[b['id']].add(a['id'])
            if o['entrance']:
                if len(rs) != 1 or o['kind'] != 'door':
                    err(o['id'] + ' entrance must be an exterior door.')
                else:
                    roots.add(rs[0]['id'])
            for r in rs:
                if o['axis'] == 'x':
                    sign = 1 if abs(o['y'] - r['y']) < EPS else -1
                    rect = (o['x'] - o['width'] / 2 - 0.075, min(o['y'], o['y'] + sign * 0.85), o['x'] + o['width'] / 2 + 0.075, max(o['y'], o['y'] + sign * 0.85))
                else:
                    sign = 1 if abs(o['x'] - r['x']) < EPS else -1
                    rect = (min(o['x'], o['x'] + sign * 0.85), o['y'] - o['width'] / 2 - 0.075, max(o['x'], o['x'] + sign * 0.85), o['y'] + o['width'] / 2 + 0.075)
                approaches.append((r['id'], rect, o['id']))
        a, f, l, h = opening_span(o)
        for q in op[:i]:
            aa, ff, ll, hh = opening_span(q)
            if a == aa and abs(f - ff) < EPS and (min(h, hh) - max(l, ll) > 0.001):
                err(o['id'] + ' overlaps opening ' + q['id'])
    if stage != 'rooms' and (not roots):
        err('Need an exterior entrance door.')
    visited = set(roots)
    todo = list(roots)
    while todo:
        for n in graph[todo.pop()] - visited:
            visited.add(n)
            todo.append(n)
    if stage != 'rooms':
        for rid in set(byid) - visited:
            err(rid + ' is unreachable from entrance through doors/portals.')
    else:
        # Rooms must share enough boundary to permit a real connecting door later.
        potential = {r['id']: set() for r in rooms}
        for i, r in enumerate(rooms):
            for s in rooms[i + 1:]:
                if any((a == aa and abs(f - ff) < EPS and (min(h, hh) - max(l, ll) >= 1.04) for a, f, l, h in edges(r) for aa, ff, ll, hh in edges(s))):
                    potential[r['id']].add(s['id'])
                    potential[s['id']].add(r['id'])
        reached = {rooms[0]['id']} if rooms else set()
        pending = list(reached)
        while pending:
            for n in potential[pending.pop()] - reached:
                reached.add(n)
                pending.append(n)
        for rid in set(byid) - reached:
            err(rid + ' has no usable shared boundary path to other rooms.')
    for i, f in enumerate(furn):
        r = byid.get(f['room_id'])
        if not r:
            err(f['id'] + ' unknown room.')
            continue
        if not all((finite(f[k]) for k in ('x', 'y', 'width', 'depth', 'height', 'rotation_deg'))):
            err('Nonfinite furniture.')
            continue
        if min(f['width'], f['depth'], f['height']) <= 0.03 or f['height'] > r['height'] - 0.1:
            err(f['id'] + ' invalid furniture size.')
        b = bbox(f)
        if b[0] < r['x'] + 0.15 - EPS or b[1] < r['y'] + 0.15 - EPS or b[2] > r['x'] + r['width'] - 0.15 + EPS or (b[3] > r['y'] + r['depth'] - 0.15 + EPS):
            err(f['id'] + ' furniture outside room/wall clearance.')
        for rid, rect, oid in approaches:
            if rid == r['id'] and intersects(b, rect):
                err(f['id'] + ' blocks door approach ' + oid)
        for q in furn[:i]:
            if q['room_id'] == f['room_id'] and intersects(b, bbox(q)):
                err(f['id'] + ' overlaps furniture ' + q['id'])
    for color in [scene['wall_color'], scene['accent_color'], scene['roof_color']] + [r['floor_color'] for r in rooms] + [f['color'] for f in furn]:
        if not all((finite(color[k]) and 0 <= color[k] <= 1 for k in ('r', 'g', 'b'))):
            err('RGB channels must be 0–1.')
    return list(dict.fromkeys(errors))

def walls(scene):
    groups = {}
    for r in scene['rooms']:
        for axis, fixed, lo, hi in edges(r):
            groups.setdefault((axis, round(fixed, 3)), []).append((lo, hi, r['height']))
    for (axis, fixed), spans in groups.items():
        openings = [o for o in scene['openings'] if o['axis'] == axis and abs((o['y'] if axis == 'x' else o['x']) - fixed) < EPS]
        cuts = {round(x, 4) for l, h, _ in spans for x in (l, h)}
        for o in openings:
            _, _, lo, hi = opening_span(o)
            cuts.update((round(lo, 4), round(hi, 4)))
        cuts = sorted(cuts)
        for lo, hi in zip(cuts, cuts[1:]):
            middle = (lo + hi) / 2
            heights = [h for l, r, h in spans if l - 0.001 <= middle <= r + 0.001]
            if not heights or hi - lo < 0.001:
                continue
            height = max(heights)
            hole = next((o for o in openings if opening_span(o)[2] - 0.001 <= middle <= opening_span(o)[3] + 0.001), None)
            intervals = [(0, height)] if hole is None else [(0, hole['bottom']), (hole['bottom'] + hole['height'], height)]
            for bottom, top in intervals:
                if top - bottom > 0.001:
                    yield (axis, fixed, lo, hi, bottom, top)

def shape_signature(scene):
    # Ignore labels, palette, furniture and ID ordering when judging a new layout.
    rooms = sorted((tuple((round(r[k], 3) for k in ('x', 'y', 'width', 'depth', 'height'))) for r in scene['rooms']))
    return tuple(rooms)

def validate(scene, stage='complete'):
    errors = _validate_floor(scene, stage)
    upper = scene.get('upper_floors', [])
    count = scene.get('storeys', 1)
    if count != len(upper) + 1 or count < 1:
        errors.append('Storey count must match the ground and upper-floor plans (positive floor count).')
    core = scene.get('vertical_core')
    pitch = scene.get('storey_height', 3.45)
    if count > 1:
        if not core:
            errors.append('Multi-storey buildings require an aligned vertical core.')
        if sorted((f.get('level') for f in upper)) != list(range(1, count)):
            errors.append('Upper floors must have consecutive levels.')
        if pitch < max((r['height'] for r in scene['rooms'])) + 0.18:
            errors.append('Storey spacing must include ceiling height and slab thickness.')
    for floor in upper:
        if abs(floor['elevation'] - floor['level'] * pitch) > 0.001:
            errors.append('Incorrect elevation for upper floor ' + str(floor['level']))
        floor_scene = {**scene, **floor, 'access_roots': floor.get('access_roots', ['vertical_core'])}
        errors.extend((f"Floor {floor['level'] + 1}: " + e for e in _validate_floor(floor_scene, stage)))
    if core:
        for floor in [scene, *upper]:
            room = next((r for r in floor['rooms'] if r['id'] == 'vertical_core'), None)
            if not room or any((abs(room[k] - core[k]) > 0.001 for k in ('x', 'y', 'width', 'depth'))):
                errors.append('Stair core must align on every floor.')
    site = scene.get('site')
    if site:
        bounds = (site['x'], site['y'], site['x'] + site['width'], site['y'] + site['depth'])
        zones = [*site.get('parking', []), *site.get('aisles', [])]
        if site.get('park'):
            zones.append(site['park'])
        if site.get('pool'):
            zones.append(site['pool'])
        for zone in zones:
            if zone['width'] <= 0 or zone['depth'] <= 0 or zone['x'] < bounds[0] - 0.001 or (zone['y'] < bounds[1] - 0.001) or (zone['x'] + zone['width'] > bounds[2] + 0.001) or (zone['y'] + zone['depth'] > bounds[3] + 0.001):
                errors.append('Site feature lies outside the plot.')
            if intersects((zone['x'], zone['y'], zone['x'] + zone['width'], zone['y'] + zone['depth']), (0, 0, scene['width'], scene['depth'])):
                errors.append('Site feature overlaps the building.')
        bays = site.get('parking', [])
        for i, b in enumerate(bays):
            for other in bays[i + 1:]:
                if intersects((b['x'], b['y'], b['x'] + b['width'], b['y'] + b['depth']), (other['x'], other['y'], other['x'] + other['width'], other['y'] + other['depth'])):
                    errors.append('Parking bays overlap.')
    return list(dict.fromkeys(errors))
