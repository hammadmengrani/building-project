"""Bounded local floor planner: partitions, topology, wall openings and furniture.

Only this module calculates coordinates. It never imports or calls an AI client.
Candidates vary wing sizes, room allocation and door positions; they are not saved house
layouts. A candidate is accepted only after the existing full geometry validator passes.
"""
import copy
import itertools
import math
import random
from geometry import edges, owners, bbox, intersects, validate
from intent import DesignBrief

class PlanningError(ValueError):
    pass
MIN_AREA = {'bedroom': 9.0, 'bathroom': 2.5, 'living': 10.0, 'kitchen': 5.0, 'dining': 6.0, 'office': 6.0, 'storage': 2.0, 'hall': 0.0, 'gym': 16.0, 'shop': 8.0, 'reception': 8.0, 'meeting': 10.0, 'utility': 3.0, 'garage': 16.0}
SIZES = {'bed': (1.6, 2.0, 0.65), 'wardrobe': (1.2, 0.6, 2.1), 'sofa': (0.9, 2.0, 0.85), 'table': (1.0, 1.3, 0.75), 'chair': (0.5, 0.5, 0.8), 'kitchen': (2.0, 0.6, 0.9), 'toilet': (0.5, 0.7, 0.75), 'basin': (0.6, 0.5, 0.85), 'shower': (0.9, 0.9, 0.08), 'plant': (0.45, 0.45, 1.1), 'box': (0.65, 0.65, 0.65), 'cylinder': (0.5, 0.5, 0.6), 'treadmill': (0.85, 1.9, 1.35), 'exercise_bike': (0.65, 1.3, 1.25), 'weight_rack': (1.5, 0.55, 1.15), 'bench': (0.65, 1.4, 0.6), 'car': (2.0, 4.4, 1.6)}
DEFAULTS = {'bedroom': ['bed', 'wardrobe'], 'bathroom': ['toilet', 'basin', 'shower'], 'living': ['sofa', 'table'], 'kitchen': ['kitchen'], 'dining': ['table'], 'office': ['table', 'chair'], 'storage': ['wardrobe'], 'hall': [], 'gym': ['treadmill', 'exercise_bike', 'weight_rack'], 'shop': ['table', 'wardrobe'], 'reception': ['table', 'chair'], 'meeting': ['table', 'chair', 'chair'], 'utility': ['box'], 'garage': ['car']}

def rounded(value):
    return round(float(value), 4)

def units_for(brief):
    attached = {r.id: [] for r in brief.rooms}
    for r in brief.rooms:
        if r.attached_to:
            attached[r.attached_to].append(r)
    units = []
    for r in brief.rooms:
        if r.kind == 'hall' or r.attached_to:
            continue
        members = [r, *attached[r.id]]
        units.append({'primary': r, 'members': members, 'area': sum((m.target_area for m in members))})
    if not units:
        raise PlanningError('Request at least one usable room besides circulation.')
    return units

def minimum_length(unit, cross):
    clear = cross - 0.18
    if clear < 1.4:
        raise PlanningError('A room strip is too narrow.')
    lengths = []
    for member in unit['members']:
        if member.minimum_width and clear < member.minimum_width - 1e-5:
            raise PlanningError('Requested minimum room width does not fit this wing.')
        required_area = max(MIN_AREA.get(member.kind, 6.), member.minimum_area or 0.)
        lengths.append(max(1.58, required_area / clear + 0.18,
                           (member.minimum_width + 0.18) if member.minimum_width else 0.,
                           3.0 if member.kind == 'bedroom' else 0.))
    return sum(lengths)

def allocate(units, length, cross):
    if not units:
        return []
    mins = [minimum_length(u, cross) for u in units]
    if sum(mins) > length + 1e-05:
        raise PlanningError('Requested rooms do not fit this partition.')
    if any(member.maximum_area is not None for unit in units for member in unit['members']):
        clear = cross - 0.18
        caps = [
            sum(member.maximum_area / cross for member in unit['members'] if member.maximum_area is not None)
            if all(member.maximum_area is not None for member in unit['members'])
            else length
            for unit in units
        ]
        if any(cap + 1e-05 < low for cap, low in zip(caps, mins)):
            raise PlanningError('A requested room maximum area is too small for its minimum width/area.')
        targets = [
            min(cap, max(low, unit['area'] / clear + 0.18))
            for unit, low, cap in zip(units, mins, caps)
        ]
        if sum(targets) > length:
            remaining = length - sum(mins)
            weights = [max(0.0, target - low) for target, low in zip(targets, mins)]
            total = sum(weights)
            return [low + (remaining * weight / total if total else 0.0) for low, weight in zip(mins, weights)]
        spans = list(targets)
        remaining = length - sum(spans)
        for _ in range(len(units) + 1):
            eligible = [i for i, (span, cap) in enumerate(zip(spans, caps)) if cap - span > 1e-05]
            if not eligible or remaining <= 1e-05:
                break
            weights = [max(units[i]['area'], 1.0) for i in eligible]
            total = sum(weights)
            distributed = 0.0
            for index, weight in zip(eligible, weights):
                addition = min(caps[index] - spans[index], remaining * weight / total)
                spans[index] += addition
                distributed += addition
            if distributed <= 1e-05:
                break
            remaining -= distributed
        return spans
    demands = [max(0, u['area'] / cross - low) for u, low in zip(units, mins)]
    surplus = length - sum(mins)
    weights = demands if sum(demands) > 0.001 else [u['area'] for u in units]
    total = sum(weights)
    return [low + surplus * weight / total for low, weight in zip(mins, weights)]

def room_record(intent, rect, brief):
    x, y, w, d = rect
    color = intent.floor_color or (brief.bedroom_floor_color if intent.kind == 'bedroom' else brief.floor_color)
    return dict(id=intent.id, name=intent.name, kind=intent.kind, x=rounded(x), y=rounded(y), width=rounded(w), depth=rounded(d), height=brief.ceiling_height, floor_color=color.model_dump(), interior_style=intent.interior_style or brief.interior_style, furniture_scale=intent.furniture_scale)

def fill_strip(units, rect, axis, brief):
    x, y, w, d = rect
    cross = w if axis == 'y' else d
    length = d if axis == 'y' else w
    lengths = allocate(units, length, cross)
    rooms = []
    cursor = y if axis == 'y' else x
    end = y + d if axis == 'y' else x + w
    has_area_caps = any(member.maximum_area is not None for unit in units for member in unit['members'])
    for index, (unit, span) in enumerate(zip(units, lengths)):
        next_edge = rounded(cursor + span if has_area_caps or index < len(units) - 1 else end)
        span = next_edge - cursor
        member_units = [{'members': [m], 'area': m.target_area} for m in unit['members']]
        portions = allocate(member_units, span, cross)
        subcursor = cursor
        member_caps = any(member.maximum_area is not None for member in unit['members'])
        for i, (member, portion) in enumerate(zip(unit['members'], portions)):
            subend = rounded(subcursor + portion if member_caps or i < len(portions) - 1 else next_edge)
            r = (x, subcursor, w, subend - subcursor) if axis == 'y' else (subcursor, y, subend - subcursor, d)
            rooms.append(room_record(member, r, brief))
            subcursor = subend
        cursor = next_edge
    return rooms

def hall_record(brief, rect, index, used):
    declared = [r for r in brief.rooms if r.kind == 'hall']
    rid = declared[index].id if index < len(declared) else f'circulation_{index + 1}'
    while rid in used:
        rid = '_' + rid
    used.add(rid)
    return dict(id=rid, kind='hall', name=declared[index].name if index < len(declared) else f'Circulation {index + 1}', x=rounded(rect[0]), y=rounded(rect[1]), width=rounded(rect[2]), depth=rounded(rect[3]), height=brief.ceiling_height, floor_color=brief.floor_color.model_dump())

def ordered(units):
    rank = {'front': 0, 'any': 1, 'rear': 2}
    return sorted(units, key=lambda u: (rank[u['primary'].zone], u['primary'].kind == 'bedroom', u['primary'].id))

def candidates(brief):
    W, D = (brief.width, brief.depth)
    units = ordered(units_for(brief))
    n = len(units)
    hall = 1.8
    used = {r.id for r in brief.rooms if r.kind != 'hall'}
    if brief.shape == 'rectangle':
        # Split points and assignments are searched rather than taking a preset floor plan.
        for fraction in (0.5, 0.42, 0.58, 0.34, 0.66):
            left = rounded((W - hall) * fraction)
            for count in range(n + 1):
                if not count and n > 1:
                    continue
                if count == n and n > 1:
                    continue
                a, b = (units[:count], units[count:])
                try:
                    rooms = fill_strip(a, (0, 0, left, D), 'y', brief) + fill_strip(b, (left + hall, 0, W - left - hall, D), 'y', brief)
                    # A single-room design needs no wasteful empty half-wing.
                    if n == 1:
                        rooms = fill_strip(units, (0, 0, W - hall, D), 'y', brief)
                        halls = [hall_record(brief, (W - hall, 0, hall, D), 0, set(used))]
                    else:
                        halls = [hall_record(brief, (left, 0, hall, D), 0, set(used))]
                    yield (rooms + halls)
                except PlanningError:
                    continue
    elif brief.shape == 'L':
        if n < 2:
            raise PlanningError('An L-shaped house needs at least two room groups.')
        public = [u for u in units if u['primary'].zone == 'front' or u['primary'].kind in ('living', 'kitchen', 'dining')]
        # Include alternative assignments while strongly preferring public rooms in front.
        selections = []
        if 0 < len(public) < n:
            selections.append(public)
        selections.extend((units[:k] for k in range(1, n)))
        seen = set()
        for front in selections:
            key = tuple((u['primary'].id for u in front))
            if key in seen:
                continue
            seen.add(key)
            side = [u for u in units if u not in front]
            for wf in (0.37, 0.42, 0.46, 0.5, 0.55, 0.33):
                wing = rounded(W * wf)
                for df in (0.46, 0.52, 0.58, 0.4, 0.64):
                    front_depth = rounded(D * df)
                    if wing - hall < 2.4 or W - wing < 2.4 or front_depth - hall < 2.4 or (D - front_depth < 2):
                        continue
                    try:
                        rooms = fill_strip(side, (0, 0, wing - hall, D), 'y', brief) + fill_strip(front, (wing, 0, W - wing, front_depth - hall), 'x', brief)
                        ids = set(used)
                        halls = [hall_record(brief, (wing - hall, 0, hall, D), 0, ids), hall_record(brief, (wing, front_depth - hall, W - wing, hall), 1, ids)]
                        yield (rooms + halls)
                    except PlanningError:
                        continue
    else:
        if n < 3:
            raise PlanningError('A U-shaped house needs at least three room groups.')
        public = [u for u in units if u['primary'].zone == 'front' or u['primary'].kind in ('living', 'kitchen', 'dining')]
        for front_count in sorted(set([max(1, min(len(public), n - 2)), 1])):
            front = units[:front_count]
            rear = units[front_count:]
            for split in range(1, len(rear)):
                for wf in (0.33, 0.37, 0.4):
                    wing = rounded(W * wf)
                    for df in (0.43, 0.5, 0.57):
                        fd = rounded(D * df)
                        if wing - hall < 2.4 or W - 2 * wing < 2 or fd - hall < 2.4 or (D - fd < 2.4):
                            continue
                        try:
                            rooms = fill_strip(front, (0, 0, W, fd - hall), 'x', brief) + fill_strip(rear[:split], (0, fd, wing - hall, D - fd), 'y', brief) + fill_strip(rear[split:], (W - wing + hall, fd, wing - hall, D - fd), 'y', brief)
                            ids = set(used)
                            halls = [hall_record(brief, (0, fd - hall, W, hall), 0, ids), hall_record(brief, (wing - hall, fd, hall, D - fd), 1, ids), hall_record(brief, (W - wing, fd, hall, D - fd), 2, ids)]
                            yield (rooms + halls)
                        except PlanningError:
                            continue

def shared(a, b):
    for axis, fixed, lo, hi in edges(a):
        for aa, ff, ll, hh in edges(b):
            if axis == aa and abs(fixed - ff) < 0.001 and (min(hi, hh) - max(lo, ll) >= 1.18):
                return (axis, fixed, max(lo, ll), min(hi, hh))
    return None

def exposed(room, rooms):
    """Subtract all shared wall intervals, including partial neighbours."""
    for axis, fixed, lo, hi in edges(room):
        intervals = [(lo, hi)]
        for other in rooms:
            if other['id'] == room['id']:
                continue
            for aa, ff, ll, hh in edges(other):
                if aa != axis or abs(fixed - ff) > 0.001:
                    continue
                remaining = []
                for left, right in intervals:
                    if hh <= left + 0.001 or ll >= right - 0.001:
                        remaining.append((left, right))
                        continue
                    if ll > left:
                        remaining.append((left, min(ll, right)))
                    if hh < right:
                        remaining.append((max(left, hh), right))
                intervals = remaining
        for left, right in intervals:
            if right - left >= 0.9:
                yield (axis, fixed, left, right)

def opening(edge, kind, rid, rooms, position=0.5, entrance=False):
    axis, fixed, lo, hi = edge
    width = 1.0 if entrance else 0.9 if kind == 'door' else min(2.0, hi - lo - 0.4)
    center = lo + width / 2 + 0.16 + (hi - lo - width - 0.32) * position
    return dict(id=rid, kind=kind, axis=axis, x=rounded(center if axis == 'x' else fixed), y=rounded(fixed if axis == 'x' else center), width=rounded(width), bottom=0.0 if kind == 'door' else 0.85, height=2.2 if kind == 'door' else 1.35, entrance=entrance)

def collide_opening(o, existing):
    from geometry import opening_span
    a, f, l, h = opening_span(o)
    return any((aa == a and abs(ff - f) < 0.025 and (min(h, hh) - max(l, ll) > 0.001) for aa, ff, ll, hh in map(opening_span, existing)))

def create_openings(scene, brief, door_bias):
    rooms = scene['rooms']
    intents = {r.id: r for r in brief.rooms}
    hallids = {r['id'] for r in rooms if r['id'] not in intents or intents[r['id']].kind == 'hall'}
    graph = {r['id']: set() for r in rooms}
    op = []

    def connect(a, b):
        edge = shared(a, b)
        if not edge:
            return False
        o = opening(edge, 'door', f'door_{len(op) + 1}', rooms, door_bias)
        if collide_opening(o, op):
            return False
        op.append(o)
        graph[a['id']].add(b['id'])
        graph[b['id']].add(a['id'])
        return True
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            if a['id'] in hallids and b['id'] in hallids:
                connect(a, b)
    byid = {r['id']: r for r in rooms}
    for r in rooms:
        intent = intents.get(r['id'])
        if r['id'] in hallids:
            continue
        if intent and intent.attached_to:
            if not connect(r, byid[intent.attached_to]):
                raise PlanningError('Attached bathroom cannot connect to its bedroom.')
        else:
            possible = [h for h in rooms if h['id'] in hallids and shared(r, h)]
            if not possible or not connect(r, possible[0]):
                raise PlanningError('No corridor access for ' + r['name'])
    # Entrance is on a genuine exposed boundary, with enough wall for corner clearance.
    options = []
    for r in rooms:
        for edge in exposed(r, rooms):
            axis, fixed, lo, hi = edge
            if hi - lo < 1.32:
                continue
            requested = brief.entrance
            desired = axis == 'x' and abs(fixed) < 0.001 if requested.startswith('front') else axis == 'x' and abs(fixed - brief.depth) < 0.001 if requested == 'rear' else axis == 'y' and abs(fixed - (0 if requested == 'left' else brief.width)) < 0.001
            if not desired:
                continue
            intent = intents.get(r['id'])
            private = intent and intent.kind in ('bedroom', 'bathroom')
            score = (10 if private else 0) + (0 if r['id'] in hallids else 1)
            score += lo / brief.width if requested == 'front-left' else (brief.width - hi) / brief.width if requested == 'front-right' else abs((lo + hi) / 2 - brief.width / 2) / brief.width if requested == 'front-center' else 0
            options.append((score, r, edge))
    if not options:
        raise PlanningError('No usable exterior entrance on the requested side.')
    for _, r, edge in sorted(options, key=lambda item: item[0]):
        entry = opening(edge, 'door', 'entrance', rooms, 0.5, True)
        if not collide_opening(entry, op):
            op.append(entry)
            break
    else:
        raise PlanningError('Entrance conflicts with another opening.')
    for r in rooms:
        if r['id'] in hallids:
            continue
        intent = intents[r['id']]
        choices = []
        for edge in exposed(r, rooms):
            if edge[3] - edge[2] < 1.0:
                continue
            for fraction in (0.5, 0.2, 0.8):
                window = opening(edge, 'window', f'window_{len(op) + 1}', rooms, fraction)
                if window['width'] < 0.4 or collide_opening(window, op):
                    continue
                # Every window has exactly one owner, including along courtyard boundaries.
                if len(owners(window, rooms)) == 1:
                    choices.append((edge[3] - edge[2], window))
        if choices:
            op.append(max(choices, key=lambda item: item[0])[1])
        elif intent.kind == 'bedroom':
            raise PlanningError('Bedroom lacks a usable exterior window.')
    if brief.architecture:
        settings = brief.architecture
        for window in op:
            if window['kind'] != 'window':
                continue
            room = owners(window, rooms)[0]
            if room.get('kind') == 'bathroom':
                continue  # retain bathroom privacy sill and modest openings
            edge = next(e for e in exposed(room, rooms) if e[0] == window['axis'] and abs(e[1] - (window['y'] if e[0] == 'x' else window['x'])) < .025 and e[2] <= (window['x'] if e[0] == 'x' else window['y']) <= e[3])
            center = window['x'] if window['axis'] == 'x' else window['y']
            available = min(center-edge[2], edge[3]-center)*2 - .3
            trial = dict(window, width=rounded(min(6.0, available, (edge[3]-edge[2])*settings.window_ratio)),
                         bottom=settings.window_sill, height=min(settings.window_height, room['height']-settings.window_sill-.2))
            if trial['width'] >= window['width'] and not collide_opening(trial, [o for o in op if o is not window]):
                window.update(trial)
    scene['openings'] = op

def door_approaches(scene, room):
    result = []
    for o in scene['openings']:
        if o['kind'] == 'window' or room not in owners(o, scene['rooms']):
            continue
        if o['axis'] == 'x':
            sign = 1 if abs(o['y'] - room['y']) < 0.025 else -1
            result.append((o['x'] - o['width'] / 2 - 0.1, min(o['y'], o['y'] + sign * 0.95), o['x'] + o['width'] / 2 + 0.1, max(o['y'], o['y'] + sign * 0.95)))
        else:
            sign = 1 if abs(o['x'] - room['x']) < 0.025 else -1
            result.append((min(o['x'], o['x'] + sign * 0.95), o['y'] - o['width'] / 2 - 0.1, max(o['x'], o['x'] + sign * 0.95), o['y'] + o['width'] / 2 + 0.1))
    return result

def positions(room, kind):
    w, d, h = SIZES[kind]
    scale = room.get('furniture_scale', 1.0) if kind in ('bed','sofa','table','wardrobe','chair') else 1.0
    w, d = w*scale, d*scale
    candidates = []
    for angle in (0.0, 90.0):
        dx, dy = (w, d) if angle == 0 else (d, w)
        xmin, xmax = (room['x'] + 0.2 + dx / 2, room['x'] + room['width'] - 0.2 - dx / 2)
        ymin, ymax = (room['y'] + 0.2 + dy / 2, room['y'] + room['depth'] - 0.2 - dy / 2)
        if xmin > xmax or ymin > ymax:
            continue
        # Include exact boundary and midpoint positions, plus a bounded regular search grid.
        xs = sorted({rounded(xmin), rounded(xmax), rounded((xmin + xmax) / 2), *[rounded(xmin + (xmax - xmin) * i / 8) for i in range(9)]})
        ys = sorted({rounded(ymin), rounded(ymax), rounded((ymin + ymax) / 2), *[rounded(ymin + (ymax - ymin) * i / 8) for i in range(9)]})
        for x, y in itertools.product(xs, ys):
            wall = min(x - xmin, xmax - x, y - ymin, ymax - y)
            score = wall if kind != 'table' else math.hypot(x - (xmin + xmax) / 2, y - (ymin + ymax) / 2)
            candidates.append((score, dict(x=x, y=y, width=w, depth=d, height=min(h, room['height'] - 0.15), rotation_deg=angle)))
    return [item[1] for item in sorted(candidates, key=lambda item: item[0])]

def furnish(scene, brief):
    byid = {r.id: r for r in brief.rooms}
    all_furniture = []
    for room in scene['rooms']:
        intent = byid.get(room['id'])
        if not intent or intent.kind == 'hall':
            continue
        wishes = list(intent.furniture or DEFAULTS.get(intent.kind,['table']))
        wishes.sort(key=lambda kind: -(SIZES[kind][0] * SIZES[kind][1]))
        approaches = door_approaches(scene, room)
        choices = []
        for kind in wishes:
            viable = []
            for pos in positions(room, kind):
                rect = bbox(pos)
                if not any((intersects(rect, approach) for approach in approaches)):
                    viable.append(pos)
            choices.append(viable)
        placed = []
        attempts = 0

        def search(index):
            nonlocal attempts
            if index == len(wishes):
                return True
            for pos in choices[index]:
                attempts += 1
                if attempts > 6000:
                    return False
                rect = bbox(pos)
                # Leave a little space between furniture instead of packing touching boxes.
                inflated = (rect[0] - 0.045, rect[1] - 0.045, rect[2] + 0.045, rect[3] + 0.045)
                if any((intersects(inflated, bbox(other)) for other in placed)):
                    continue
                placed.append(pos)
                if search(index + 1):
                    return True
                placed.pop()
            return False
        if not search(0):
            raise PlanningError('Cannot furnish ' + room['name'] + ' without blocking access; increase its available area or reduce furniture.')
        for i, (kind, pos) in enumerate(zip(wishes, placed)):
            color = brief.furniture_color.model_dump() if kind in ('bed', 'sofa', 'chair', 'table') else dict(r=0.9, g=0.9, b=0.87) if kind in ('toilet', 'basin', 'shower') else brief.accent_color.model_dump()
            all_furniture.append(dict(id=f"{room['id']}_f{i + 1}", room_id=room['id'], kind=kind, color=color, **pos))
    scene['furniture'] = all_furniture

def candidate_score(rooms, brief):
    byid = {r.id: r for r in brief.rooms}
    score = 0
    for room in rooms:
        intent = byid.get(room['id'])
        if not intent or intent.kind == 'hall':
            continue
        area = (room['width'] - 0.18) * (room['depth'] - 0.18)
        score += abs(area - intent.target_area) / intent.target_area
        score += max(room['width'] / room['depth'], room['depth'] / room['width']) * 0.06
        center = (room['y'] + room['depth'] / 2) / brief.depth
        if intent.zone == 'front':
            score += center * 0.8
        if intent.zone == 'rear':
            score += (1 - center) * 0.8
    return score

def _compile_single(data, previous=None):
    brief = data if isinstance(data, DesignBrief) else DesignBrief.model_validate(data)
    if brief.action == 'palette':
        if previous is None:
            raise PlanningError('A color-only edit needs an existing generated design.')
        errors = validate(previous)
        if errors:
            raise PlanningError('The previous design is invalid; request a new layout before changing only colors.')
        result = copy.deepcopy(previous)
        intents = {r.id: r for r in brief.rooms}
        if set(intents) != {r['id'] for r in previous['rooms']}:
            raise PlanningError('A palette-only edit must preserve all existing room IDs.')
        for key in ('wall_color', 'accent_color', 'roof_color'):
            result[key] = getattr(brief, key).model_dump()
        for r in result['rooms']:
            intent = intents[r['id']]
            r['floor_color'] = (intent.floor_color or (brief.bedroom_floor_color if intent.kind == 'bedroom' else brief.floor_color)).model_dump()
        for f in result['furniture']:
            if f['kind'] in ('bed', 'sofa', 'chair', 'table'):
                f['color'] = brief.furniture_color.model_dump()
            elif f['kind'] not in ('toilet', 'basin', 'shower'):
                f['color'] = brief.accent_color.model_dump()
        return result
    rng = random.Random(brief.layout_variant)
    scored = [(candidate_score(rooms, brief) + (rng.random() * 0.7 if brief.layout_variant else 0), rooms) for rooms in candidates(brief)]
    ranked = [rooms for _, rooms in sorted(scored, key=lambda item: item[0])]
    failures = []
    for rooms in ranked[:36]:
        if len(rooms) > 24:
            continue
        if brief.shape == 'L' and brief.courtyard_corner == 'rear-left':
            rooms = copy.deepcopy(rooms)
            for r in rooms:
                r['x'] = rounded(brief.width - r['x'] - r['width'])
        for bias in (0.15, 0.85, 0.5):
            scene = dict(shape=brief.shape, courtyard_corner=brief.courtyard_corner, layout_variant=brief.layout_variant, width=brief.width, depth=brief.depth, wall_color=brief.wall_color.model_dump(), accent_color=brief.accent_color.model_dump(), roof_color=brief.roof_color.model_dump(), rooms=copy.deepcopy(rooms), openings=[], furniture=[])
            try:
                create_openings(scene, brief, bias)
                furnish(scene, brief)
                errors = validate(scene)
                if errors:
                    raise PlanningError('; '.join(errors[:3]))
                return scene
            except PlanningError as exc:
                failures.append(str(exc))
    minimums = any(r.minimum_width or r.minimum_area for r in brief.rooms)
    detail = failures[0] if failures else ('Requested minimum usable room widths/areas do not fit the available wings.' if minimums else 'Envelope is too small for the requested room counts and shape.')
    raise PlanningError('Local planner could not fit this brief. ' + detail + ' No extra Groq request was made.')

def summarize_scene(scene):
    """Compress repeated storeys; send no openings, transforms or site meshes to Groq."""
    import json
    def room_kind(room):
        if room.get('kind'):
            return 'hall' if room['kind']=='stairs' else room['kind']
        name=room['name'].lower()
        for token,kind in [('bed','bedroom'),('bath','bathroom'),('kitchen','kitchen'),('living','living'),('lounge','living'),('dining','dining'),('gym','gym'),('office','office'),('storage','storage')]:
            if token in name:return kind
        return 'hall'
    def program(floor):
        return [dict(id=r['id'],name=r['name'],kind=room_kind(r),area=rounded(r['width']*r['depth']),floor_color=r['floor_color'],materials=r.get('materials'),interior_style=r.get('interior_style','modern'),furniture_scale=r.get('furniture_scale',1.0)) for r in floor['rooms']]
    def occupied(x,y):
        return any(r['x']<=x<=r['x']+r['width'] and r['y']<=y<=r['y']+r['depth'] for r in scene['rooms'])
    width,depth=scene['width'],scene['depth']
    left,right=occupied(.01,depth-.01),occupied(width-.01,depth-.01)
    shape='L' if left!=right else 'U' if left and right and not occupied(width/2,depth-.01) else 'rectangle'
    groups={}
    for floor in scene.get('upper_floors',[]):
        rooms=program(floor);signature=json.dumps(rooms,sort_keys=True)
        if signature not in groups:groups[signature]=dict(levels=[],rooms=rooms)
        groups[signature]['levels'].append(floor['level'])
    site=scene.get('site')
    site_summary=None
    if site:
        park=site.get('park')
        pool=site.get('pool')
        site_summary=dict(width=site['width'],depth=site['depth'],parking_spaces=len(site.get('parking',[])),park_area=rounded(park['width']*park['depth']) if park else 0.,pool_width=pool['width'] if pool else 0.,pool_depth=pool['depth'] if pool else 0.)
    return dict(architecture=scene.get('architecture'),materials=scene.get('materials'),interior_style=scene.get('interior_style','modern'),storeys=scene.get('storeys',1),lift=bool((scene.get('vertical_core') or {}).get('lift')),site=site_summary,upper_floors=list(groups.values()),shape=scene.get('shape') or shape,courtyard_corner=scene.get('courtyard_corner') or ('rear-right' if left else 'rear-left'),layout_variant=scene.get('layout_variant',0),width=width,depth=depth,wall_color=scene['wall_color'],accent_color=scene['accent_color'],roof_color=scene['roof_color'],rooms=program(scene))


def compile_brief(data, previous=None):
    brief = data if isinstance(data, DesignBrief) else DesignBrief.model_validate(data)
    if brief.storeys > 1 or brief.site is not None or (previous and previous.get('storeys', 1) > 1):
        from building_plan import compile_building
        result = compile_building(brief, previous)
    else:
        result = _compile_single(brief, previous)
    result['architecture'] = (brief.architecture.model_dump() if brief.architecture else (previous or {}).get('architecture') if brief.action == 'palette' else None)
    result['interior_style'] = brief.interior_style
    result['materials'] = brief.materials.model_dump(exclude_none=True) if brief.materials else None
    for level, layout in enumerate([result, *result.get('upper_floors', [])]):
        programs = [g.rooms for g in brief.upper_floors if level in g.levels]
        intents = {r.id:r for r in (programs[0] if programs else brief.rooms)}
        for room in layout['rooms']:
            intent = intents.get(room['id'])
            room['interior_style'] = (intent.interior_style if intent else None) or brief.interior_style
            room['materials'] = intent.materials.model_dump(exclude_none=True) if intent and intent.materials else None
        for index, item in enumerate(layout['furniture']):
            if brief.action != 'palette':
                item['design_variant'] = (brief.layout_variant + index + level) % 3
    return result
