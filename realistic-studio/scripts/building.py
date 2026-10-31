"""Render AI scene data directly with Blender. No generated code execution."""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, Euler
import random
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from geometry import walls, owners, edges, validate
sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_geometry import add_stairs, add_site
p = argparse.ArgumentParser()
p.add_argument('--scene', required=True)
p.add_argument('--out', required=True)
p.add_argument('--edits')
p.add_argument('--presentation')
p.add_argument('--render', action='store_true')
p.add_argument('--view', default='exterior', choices=['exterior', 'interior', 'cutaway'])
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
scene = json.loads(Path(a.scene).read_text())
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
errors = validate(scene)
if errors:
    raise ValueError('Invalid scene: ' + str(errors))
BASE = 0.22
ASSETS = Path(__file__).resolve().parent.parent / 'assets' / 'textures'
EDITS = json.loads(Path(a.edits).read_text()) if a.edits else {}
PRESENTATION = json.loads(Path(a.presentation).read_text()) if a.presentation else {}
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
MASTER = scene
MATERIAL_CACHE = {}
BOX_MESHES = {}
CYLINDER_MESHES = {}

def build(view):
    scene = MASTER
    BASE = 0.22
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    cache = MATERIAL_CACHE
    current = {'key': 'site', 'category': 'Site', 'pivot': (0, 0, 0), 'level': 0, 'source': 'site'}

    def entity(key, category, pivot=(0, 0, 0)):
        source = key
        if current['level'] > 0:
            key = f"floor{current['level']}:" + key
            if pivot == (0, 0, 0):
                pivot = (0, 0, current['level'] * MASTER.get('storey_height', 3.45))
        current.update(key=key, source=source, category=category, pivot=pivot)

    def tag(o):
        o['_entity'] = current['key']
        o['_category'] = current['category']
        o['_pivot'] = list(current['pivot'])
        o['_level'] = current['level']
        o['_source'] = current['source']
        return o

    def uv_project(o):
        uv = o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
        for face in o.data.polygons:
            axis = max(range(3), key=lambda i: abs(face.normal[i]))
            for li in face.loop_indices:
                co = o.data.vertices[o.data.loops[li].vertex_index].co
                coords = (co.y, co.z) if axis == 0 else (co.x, co.z) if axis == 1 else (co.x, co.y)
                uv.data[li].uv = coords

    def mat(rgb, metal=0, rough=0.6, alpha=1, finish=None):
        values = tuple((rgb[k] for k in ('r', 'g', 'b'))) if isinstance(rgb, dict) else tuple(rgb)
        key = (*values, metal, rough, alpha, finish)
        if key in cache:
            return cache[key]
        m = bpy.data.materials.new('Material ' + str(len(cache)))
        m.use_nodes = True
        m.diffuse_color = (*values, alpha)
        n = m.node_tree.nodes.get('Principled BSDF')
        n.inputs['Base Color'].default_value = (*values, 1)
        n.inputs['Roughness'].default_value = rough
        n.inputs['Metallic'].default_value = metal
        n.inputs['Alpha'].default_value = alpha
        if alpha < 1:
            if hasattr(m, 'surface_render_method'):
                m.surface_render_method = 'DITHERED'
            else:
                m.blend_method = 'BLEND'
        if finish:
            nodes = m.node_tree.nodes
            links = m.node_tree.links
            for channel, socket in [('color', 'Base Color'), ('roughness', 'Roughness'), ('normal', 'Normal')]:
                file = ASSETS / (finish + '_' + channel + '.png')
                tex = nodes.new('ShaderNodeTexImage')
                tex.image = bpy.data.images.load(str(file), check_existing=True)
                if channel != 'color':
                    tex.image.colorspace_settings.name = 'Non-Color'
                if channel == 'normal':
                    normal = nodes.new('ShaderNodeNormalMap')
                    normal.inputs['Strength'].default_value = 0.3
                    links.new(tex.outputs['Color'], normal.inputs['Color'])
                    links.new(normal.outputs['Normal'], n.inputs['Normal'])
                elif channel == 'color':
                    mix = nodes.new('ShaderNodeMixRGB')
                    mix.blend_type = 'MULTIPLY'
                    mix.inputs[0].default_value = 1
                    mix.inputs[2].default_value = (*values, 1)
                    links.new(tex.outputs['Color'], mix.inputs[1])
                    links.new(mix.outputs[0], n.inputs[socket])
                    # glTF needs a directly connected base-color texture. Bake the tint into a small copy.
                    from array import array
                    tinted = tex.image.copy()
                    tinted.name = m.name + ' albedo'
                    pixels = array('f', [0]) * len(tinted.pixels)
                    tinted.pixels.foreach_get(pixels)
                    for i in range(0, len(pixels), 4):
                        pixels[i] *= values[0]
                        pixels[i + 1] *= values[1]
                        pixels[i + 2] *= values[2]
                    tinted.pixels.foreach_set(pixels)
                    tinted.update()
                    tex.image = tinted
                    links.new(tex.outputs['Color'], n.inputs[socket])
                    nodes.remove(mix)
                else:
                    links.new(tex.outputs['Color'], n.inputs[socket])
        if alpha < 1:
            n.inputs['Transmission Weight'].default_value = 0.35
            n.inputs['IOR'].default_value = 1.45
        cache[key] = m
        return m
    wall = mat(scene['wall_color'], finish='plaster')
    accent = mat(scene['accent_color'], finish='wood')
    roofmat = mat(scene['roof_color'], finish='stone')
    concrete = mat((0.65, 0.65, 0.6), finish='stone')
    dark = mat((0.035, 0.045, 0.05), 0.65, 0.28)
    wood = mat((0.5, 0.32, 0.16), finish='wood')
    white = mat((0.9, 0.89, 0.85), rough=0.3)
    glass = mat((0.65, 0.78, 0.82), 0.05, 0.09, 0.38)

    def box(name, size, pos, material, bevel=False, rotation=0):
        if min(size) < 0.0001:
            return
        key = tuple((round(v, 6) for v in size)) + (material.name,)
        mesh = BOX_MESHES.get(key)
        fresh = mesh is None
        if fresh:
            x, y, z = (v / 2 for v in size)
            mesh = bpy.data.meshes.new('Box geometry')
            mesh.from_pydata([(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)], [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
            mesh.materials.append(material)
            mesh.update()
            BOX_MESHES[key] = mesh
        o = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(o)
        o.location = pos
        o.rotation_euler.z = rotation
        if fresh:
            uv_project(o)
        tag(o)
        if bevel:
            mod = o.modifiers.new('Edge rounding', 'BEVEL')
            mod.width = min(0.035, min(size) / 4)
            mod.segments = 2
        return o

    def cylinder(name, size, pos, material, rotation=0):
        mesh = CYLINDER_MESHES.get(material.name)
        if mesh is None:
            n = 20
            vertices = [(math.cos(i * math.tau / n), math.sin(i * math.tau / n), z) for z in (-0.5, 0.5) for i in range(n)]
            faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
            mesh = bpy.data.meshes.new('Cylinder geometry')
            mesh.from_pydata(vertices, [], faces)
            mesh.materials.append(material)
            mesh.update()
            for face in mesh.polygons:
                face.use_smooth = len(face.vertices) == 4
            CYLINDER_MESHES[material.name] = mesh
        o = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(o)
        o.location = pos
        o.scale = (size[0] / 2, size[1] / 2, size[2])
        o.rotation_euler.z = rotation
        tag(o)
        return o
    floor_data = [MASTER, *MASTER.get('upper_floors', [])]
    for level, layout in enumerate(floor_data):
        selected = PRESENTATION.get('floor', 'all')
        if selected != 'all' and str(level) != str(selected):
            continue
        scene = {**MASTER, **layout}
        BASE = 0.22 + layout.get('elevation', 0)
        current['level'] = level
        W, D = (scene['width'], scene['depth'])
        if level == 0 and (not add_site(MASTER, entity, box, cylinder, mat, concrete, dark, glass, white)):
            box('Site', (W + 5, D + 5, 0.12), (W / 2, D / 2, -0.13), mat((0.14, 0.22, 0.075), finish='grass'))
        for r in scene['rooms']:
            entity('floor:' + r['id'], 'Floor', (r['x'] + r['width'] / 2, r['y'] + r['depth'] / 2, 0))
            x, y, w, d, h = (r['x'], r['y'], r['width'], r['depth'], r['height'])
            if r['id'] != 'vertical_core' or level == 0:
                box('Foundation ' + r['id'], (w + 0.12, d + 0.12, 0.25), (x + w / 2, y + d / 2, BASE - 0.125), concrete)
            if r['id'] != 'vertical_core':
                box('Floor ' + r['id'], (w - 0.08, d - 0.08, 0.035), (x + w / 2, y + d / 2, BASE + 0.0175), mat(r['floor_color'], finish='wood' if r.get('kind') == 'bedroom' or 'bed' in r['name'].lower() else 'tile'))
            if view == 'exterior' and level == MASTER.get('storeys', 1) - 1:
                entity('roof:' + r['id'], 'Roof', (x + w / 2, y + d / 2, BASE + h))
                box('Roof ' + r['id'], (w + 0.22, d + 0.22, 0.17), (x + w / 2, y + d / 2, BASE + h + 0.07), roofmat, True)
                # Shadow reveal and capping articulate separate AI-designed building volumes.
                for yy in (y - 0.04, y + d + 0.04):
                    box('Roof fascia', (w + 0.22, 0.1, 0.18), (x + w / 2, yy, BASE + h - 0.07), accent)
                for xx in (x - 0.04, x + w + 0.04):
                    box('Roof fascia', (0.1, d + 0.22, 0.18), (xx, y + d / 2, BASE + h - 0.07), accent)
        for axis, fixed, lo, hi, bottom, top in walls(scene):
            if view == 'cutaway':
                top = min(top, 0.9)
            if top <= bottom:
                continue
            size = (hi - lo, 0.18, top - bottom) if axis == 'x' else (0.18, hi - lo, top - bottom)
            pos = ((lo + hi) / 2, fixed, BASE + (bottom + top) / 2) if axis == 'x' else (fixed, (lo + hi) / 2, BASE + (bottom + top) / 2)
            entity('wall:' + ':'.join((str(round(v, 3)) for v in (fixed, lo, hi, bottom))) + axis, 'Wall', ((lo + hi) / 2, fixed, BASE + bottom) if axis == 'x' else (fixed, (lo + hi) / 2, BASE + bottom))
            box('Wall', size, pos, wall, True)
        for o in scene['openings']:
            if view == 'cutaway':
                continue
            x, y, w, b, h, axis = (o['x'], o['y'], o['width'], o['bottom'], o['height'], o['axis'])
            entity('opening:' + o['id'], 'Window' if o['kind'] == 'window' else 'Door', (x, y, BASE))

            def trim(name, offset, z, along, high, ma, thickness=0.075):
                size = (along, thickness, high) if axis == 'x' else (thickness, along, high)
                pos = (x + offset, y, BASE + z) if axis == 'x' else (x, y + offset, BASE + z)
                return box(name, size, pos, ma)
            if o['kind'] == 'portal':
                continue
            for sign in (-1, 1):
                trim(o['id'] + ' frame', sign * (w / 2 - 0.03), b + h / 2, 0.06, h, dark)
            trim('Lintel frame', 0, b + h - 0.03, w, 0.06, dark)
            if o['kind'] == 'window':
                trim('Sill', 0, b - 0.035, w + 0.14, 0.07, concrete, 0.3)
                trim(o['id'] + ' glass', 0, b + h / 2, w - 0.12, h - 0.12, glass, 0.018)
                trim('Mullion', 0, b + h / 2, 0.035, h - 0.12, dark)
                trim('Transom', 0, b + h * 0.7, w - 0.12, 0.035, dark)
                trim('Window bottom frame', 0, b + 0.025, w, 0.05, dark)
            else:
                adjacent = owners(o, scene['rooms'])
                r = adjacent[0] if adjacent else None
                if axis == 'x':
                    sign = 1 if r is None or abs(y - r['y']) < 0.025 else -1
                    pos = (x - w / 2 + 0.03, y + sign * (w - 0.08) / 2, BASE + h / 2)
                    size = (0.045, w - 0.08, h - 0.08)
                else:
                    sign = 1 if r is None or abs(x - r['x']) < 0.025 else -1
                    pos = (x + sign * (w - 0.08) / 2, y - w / 2 + 0.03, BASE + h / 2)
                    size = (w - 0.08, 0.045, h - 0.08)
                box(o['id'] + ' open door', size, pos, wood, True)
                handle = list(pos)
                handle[2] = BASE + 1.05
                if axis == 'x':
                    handle[0] += 0.035
                    handle[1] += 0.2
                else:
                    handle[1] += 0.035
                    handle[0] += 0.2
                cylinder('Brushed door handle', (0.035, 0.035, 0.18), handle, dark)
                if o['entrance']:
                    if axis == 'x':
                        sz = (w + 0.8, 1.0, 0.12)
                        pp = (x, y - 0.45, BASE + h + 0.25)
                    else:
                        sz = (1.0, w + 0.8, 0.12)
                        pp = (x - 0.45, y, BASE + h + 0.25)
                    # Place canopy and approach on the actual outside of this entrance.
                    r = owners(o, scene['rooms'])[0]
                    outward = -1 if (abs(y - r['y']) < 0.025 if axis == 'x' else abs(x - r['x']) < 0.025) else 1
                    if axis == 'x':
                        pp = (x, y + outward * 0.65, BASE + h + 0.3)
                        sz = (w + 1.3, 1.55, 0.16)
                    else:
                        pp = (x + outward * 0.65, y, BASE + h + 0.3)
                        sz = (1.55, w + 1.3, 0.16)
                    box('Floating entrance canopy', sz, pp, roofmat, True)
                    for step in range(3):
                        dist = 0.4 + step * 0.4
                        zz = BASE - (step + 1) * 0.065
                        ps = (x, y + outward * dist, zz) if axis == 'x' else (x + outward * dist, y, zz)
                        ds = (w + 0.7, 0.43, 0.065) if axis == 'x' else (0.43, w + 0.7, 0.065)
                        box('Entrance stair', ds, ps, concrete, True)
                    pp = (x, y + outward * 2.2, -0.035) if axis == 'x' else (x + outward * 2.2, y, -0.035)
                    sz = (w + 0.7, 2.0, 0.08) if axis == 'x' else (2.0, w + 0.7, 0.08)
                    box('Stone approach', sz, pp, concrete, True)
                    for delta in (-w / 2 - 0.3, w / 2 + 0.3):
                        ps = (x + delta, y - 0.11, BASE + 1.7) if axis == 'x' else (x - 0.11, y + delta, BASE + 1.7)
                        box('Wall sconce', (0.09, 0.11, 0.35), ps, dark, True)
        for f in scene['furniture']:
            entity('furniture:' + f['id'], 'Furniture', (f['x'], f['y'], BASE))
            x, y, w, d, h, angle = (f['x'], f['y'], f['width'], f['depth'], f['height'], math.radians(f['rotation_deg']))
            color = mat(f['color'], finish='fabric' if f['kind'] in ('sofa', 'bed') else 'wood' if f['kind'] in ('table', 'wardrobe') else None)
            kind = f['kind']

            def part(label, size, offset, ma=color, rounding=True, shape='box'):
                dx, dy, z = offset
                pos = (x + dx * math.cos(angle) - dy * math.sin(angle), y + dx * math.sin(angle) + dy * math.cos(angle), BASE + 0.035 + z)
                if shape == 'cylinder':
                    return cylinder(f['id'] + ' ' + label, size, pos, ma, angle)
                return box(f['id'] + ' ' + label, size, pos, ma, rounding, angle)
            if kind == 'treadmill':
                part('running deck', (w, d, 0.16), (0, 0, 0.14), dark)
                part('running belt', (w * 0.8, d * 0.8, 0.025), (0, -d * 0.03, 0.235), dark)
                for dx in (-w * 0.42, w * 0.42):
                    part('upright', (0.055, 0.055, h * 0.8), (dx, d * 0.3, h * 0.45), dark)
                part('console', (w * 0.85, 0.32, 0.09), (0, d * 0.3, h * 0.88), white)
                part('console screen', (w * 0.45, 0.22, 0.012), (0, d * 0.3, h * 0.94), dark)
            elif kind == 'exercise_bike':
                part('base', (w, d, 0.1), (0, 0, 0.08), dark)
                part('frame', (0.1, 0.1, h * 0.65), (0, 0, h * 0.4), dark)
                part('seat', (w * 0.6, d * 0.28, 0.09), (0, -d * 0.2, h * 0.7), dark)
                part('handle stem', (0.06, 0.06, h * 0.75), (0, d * 0.3, h * 0.5), dark)
                part('handle bar', (w, 0.06, 0.06), (0, d * 0.3, h * 0.9), dark)
            elif kind == 'weight_rack':
                for dx in (-w * 0.45, w * 0.45):
                    part('rack post', (0.07, d, h), (dx, 0, h / 2), dark)
                for zz in (h * 0.3, h * 0.75):
                    part('rack shelf', (w, d, 0.06), (0, 0, zz), dark)
                    for dx in (-w * 0.3, 0, w * 0.3):
                        part('dumbbell handle', (0.22, 0.035, 0.035), (dx, 0, zz + 0.1), dark)
                        for side in (-1, 1):
                            part('dumbbell plate', (0.06, 0.15, 0.15), (dx + side * 0.11, 0, zz + 0.1), dark)
            elif kind == 'bench':
                part('padded bench', (w, d, 0.12), (0, 0, h), color)
                for dy in (-d * 0.35, d * 0.35):
                    part('bench leg', (w * 0.7, 0.08, h), (0, dy, h / 2), dark)
            elif kind == 'car':
                part('car body', (w, d, h * 0.45), (0, 0, h * 0.3), color)
                part('car cabin', (w * 0.85, d * 0.5, h * 0.4), (0, 0, h * 0.65), glass)
            elif kind == 'bed':
                part('frame', (w, d, h * 0.38), (0, 0, h * 0.19), wood)
                part('mattress', (w * 0.98, d * 0.96, h * 0.32), (0, 0, h * 0.54), white)
                part('duvet', (w, d * 0.7, h * 0.12), (0, -d * 0.13, h * 0.76))
                for dx in (-w * 0.24, w * 0.24):
                    part('pillow', (w * 0.4, d * 0.2, h * 0.12), (dx, d * 0.32, h * 0.8), white)
                part('headboard', (w, d * 0.055, h), (0, d * 0.46, h / 2), wood)
            elif kind == 'sofa':
                part('base', (w, d, h * 0.4), (0, 0, h * 0.25))
                part('back', (w * 0.18, d, h), (w * 0.4, 0, h / 2))
                for dy in (-d * 0.32, d * 0.32):
                    part('arm', (w, d * 0.1, h * 0.75), (0, dy * 1.4, h * 0.375))
                for dy in (-d * 0.25, d * 0.05, d * 0.3):
                    part('cushion', (w * 0.75, d * 0.25, h * 0.13), (-w * 0.04, dy, h * 0.53), white)
            elif kind in ('table', 'chair'):
                part('top', (w, d, 0.08), (0, 0, h - 0.04))
                for dx in (-w * 0.38, w * 0.38):
                    for dy in (-d * 0.38, d * 0.38):
                        part('leg', (0.055, 0.055, h - 0.08), (dx, dy, (h - 0.08) / 2), wood)
                if kind == 'chair':
                    part('back', (w, 0.06, h * 0.6), (0, d * 0.42, h * 0.72))
            elif kind == 'kitchen':
                part('cabinets', (w, d, h * 0.92), (0, 0, h * 0.46), wood)
                part('counter', (w, d, 0.05), (0, 0, h - 0.025), color)
                for dx in (-w * 0.22, w * 0.22):
                    part('cooktop', (0.2, min(0.3, d * 0.5), 0.012), (dx, 0, h + 0.007), dark)
            elif kind == 'wardrobe':
                part('body', (w, d, h), (0, 0, h / 2))
                for dx in (-w * 0.06, w * 0.06):
                    part('handle', (0.025, 0.04, h * 0.18), (dx, -d / 2 - 0.008, h * 0.55), dark)
            elif kind == 'toilet':
                part('pedestal', (w * 0.6, d * 0.6, h * 0.5), (0, -d * 0.06, h * 0.25), white, shape='cylinder')
                part('seat', (w, d * 0.73, h * 0.13), (0, -d * 0.08, h * 0.53), white, shape='cylinder')
                part('cistern', (w * 0.85, d * 0.24, h * 0.85), (0, d * 0.35, h * 0.425), white)
            elif kind == 'basin':
                part('vanity', (w, d, h * 0.85), (0, 0, h * 0.425), wood)
                part('basin', (w, d, 0.09), (0, 0, h - 0.045), white)
                part('tap', (0.04, 0.04, 0.13), (0, d * 0.3, h - 0.01), dark)
            elif kind == 'shower':
                part('tray', (w, d, h), (0, 0, h / 2), white)
                part('drain', (0.1, 0.1, 0.01), (0, 0, h + 0.005), dark)
            elif kind == 'plant':
                part('pot', (w * 0.65, d * 0.65, h * 0.38), (0, 0, h * 0.19), concrete, shape='cylinder')
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, BASE + h * 0.7))
                o = bpy.context.object
                o.name = f['id'] + ' foliage'
                o.scale = (w / 2, d / 2, h * 0.3)
                o.data.materials.append(color)
                tag(o)
            else:
                part(kind, (w, d, h), (0, 0, h / 2), shape='cylinder' if kind == 'cylinder' else 'box')
        # Low exterior plinth, parapet coping and facade battens on exposed boundaries.
        for r in scene['rooms']:
            for axis, fixed, lo, hi in edges(r):
                cuts = {lo, hi}
                for other in scene['rooms']:
                    for aa, ff, ll, hh in edges(other):
                        if aa == axis and abs(ff - fixed) < 0.025:
                            cuts.update((v for v in (ll, hh) if lo < v < hi))
                points = sorted(cuts)
                for left, right in zip(points, points[1:]):
                    middle = (left + right) / 2
                    sharing = sum((any((aa == axis and abs(ff - fixed) < 0.025 and (ll - 0.001 < middle < hh + 0.001) for aa, ff, ll, hh in edges(other))) for other in scene['rooms']))
                    if sharing != 1:
                        continue
                    entity('facade:' + r['id'] + ':' + axis + ':' + str(fixed) + ':' + str(left), 'Facade')
                    along = right - left
                    pp = (middle, fixed, BASE + 0.12) if axis == 'x' else (fixed, middle, BASE + 0.12)
                    sz = (along, 0.205, 0.2) if axis == 'x' else (0.205, along, 0.2)
                    box('Stone plinth', sz, pp, roofmat, True)
                    if view == 'exterior' and level == MASTER.get('storeys', 1) - 1:
                        z = BASE + r['height'] + 0.25
                        pp = (middle, fixed, z) if axis == 'x' else (fixed, middle, z)
                        sz = (along, 0.22, 0.32) if axis == 'x' else (0.22, along, 0.32)
                        box('Parapet', sz, pp, wall, True)
                        pp = (middle, fixed, z + 0.18) if axis == 'x' else (fixed, middle, z + 0.18)
                        sz = (along + 0.04, 0.28, 0.045) if axis == 'x' else (0.28, along + 0.04, 0.045)
                        box('Parapet coping', sz, pp, roofmat, True)
                    if axis == 'x' and abs(fixed) < 0.02:
                        for xx in [left + 0.17, left + 0.29, left + 0.41]:
                            if xx > right - 0.12:
                                continue
                            box('Vertical timber batten', (0.045, 0.08, min(2.8, r['height'] - 0.3)), (xx, fixed - 0.12, BASE + r['height'] / 2), accent, True)
        if level == 0:
            # Landscape outside the actual footprint, leaving the full room plan untouched.
            for side, xx in [('left', -0.75 if MASTER.get('site') else -1.25), ('right', W + 1.8 if MASTER.get('site', {}) and MASTER['site'].get('park') else W + 0.75 if MASTER.get('site') else W + 1.25)]:
                for yy in (D * 0.2, D * 0.65, D * 0.88):
                    entity('garden:' + side + ':' + str(yy), 'Landscape', (xx, yy, 0))
                    box('Raised planter', (1.0, 1.35, 0.32), (xx, yy, 0.1), roofmat, True)
                    cylinder('Tree trunk', (0.1, 0.1, 1.5), (xx, yy, 0.8), wood)
                    rng = random.Random(104 + int(yy * 100) + (0 if side == 'left' else 200))
                    leafmats = [mat(rgb, rough=0.78) for rgb in ((0.11, 0.2, 0.055), (0.18, 0.27, 0.09), (0.25, 0.32, 0.13))]
                    vertices = []
                    faces = []
                    indices = []
                    for i in range(650):
                        theta = rng.uniform(0, math.tau)
                        z = rng.uniform(-1, 1)
                        rad = max(0, 1 - z * z) ** 0.5 * rng.uniform(0.35, 1)
                        center = Vector((xx + math.cos(theta) * rad * 0.65, yy + math.sin(theta) * rad * 0.55, 1.85 + z * 0.6))
                        rot = Euler((rng.uniform(-1, 1), rng.uniform(-1, 1), theta), 'XYZ').to_matrix()
                        length = rng.uniform(0.08, 0.17)
                        width = length * 0.28
                        v0 = len(vertices)
                        for co in [(-length / 2, 0, 0), (-length * 0.15, -width / 2, 0), (length * 0.25, -width * 0.4, 0), (length / 2, 0, 0.012), (length * 0.25, width * 0.4, 0), (-length * 0.15, width / 2, 0)]:
                            vertices.append(center + rot @ Vector(co))
                        for tri in [(0, 1, 5), (1, 2, 5), (2, 4, 5), (2, 3, 4)]:
                            faces.append(tuple((v0 + j for j in tri)))
                            indices.append(i % 3)
                    mesh = bpy.data.meshes.new('Olive leaves mesh')
                    mesh.from_pydata(vertices, [], faces)
                    mesh.update()
                    leaves = bpy.data.objects.new('Individual olive leaves', mesh)
                    bpy.context.collection.objects.link(leaves)
                    for m in leafmats:
                        mesh.materials.append(m)
                    for face, idx in zip(mesh.polygons, indices):
                        face.material_index = idx
                    tag(leaves)
                    for angle in (0, 2.1, 4.2):
                        start = Vector((xx, yy, 1.0))
                        end = Vector((xx + math.cos(angle) * 0.4, yy + math.sin(angle) * 0.4, 1.8))
                        delta = end - start
                        branch = cylinder('Olive branch', (0.025, 0.025, delta.length), (start + end) / 2, wood)
                        branch.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()
        if view != 'exterior':
            for r in scene['rooms']:
                entity('label:' + r['id'], 'Label', (r['x'], r['y'], BASE))
                bpy.ops.object.text_add(location=(r['x'] + r['width'] / 2, r['y'] + 0.3, BASE + 0.06))
                o = bpy.context.object
                o.name = 'Label ' + r['id']
                o.data.body = r['name']
                o.data.align_x = 'CENTER'
                o.data.size = min(0.24, r['width'] / max(1, len(r['name'])))
                o.data.materials.append(dark)
                bpy.ops.object.convert(target='MESH')
                tag(o)
        add_stairs(MASTER.get('vertical_core'), BASE, level, MASTER.get('storeys', 1), entity, box, cylinder, concrete, dark, glass)
    # Stable named entity roots make editing deterministic across all three views.
    groups = {}
    for obj in list(bpy.context.scene.objects):
        key = obj.get('_entity')
        if not key:
            continue
        if key not in groups:
            root = bpy.data.objects.new(key, None)
            bpy.context.collection.objects.link(root)
            root.location = obj['_pivot']
            root['entity'] = key
            root['category'] = obj['_category']
            root['level'] = obj['_level']
            root['source_key'] = obj['_source']
            groups[key] = root
        root = groups[key]
        obj.parent = root
        obj.location -= root.location
        del obj['_entity']
        del obj['_category']
        del obj['_pivot']
        del obj['_level']
        del obj['_source']
    bpy.context.view_layer.update()
    for key, edit in EDITS.items():
        root = groups.get(key)
        if root is None:
            continue
        if 'position' in edit:
            px, py, pz = edit['position']
            root.location = (px, -pz, py)
        if 'rotation' in edit:
            root.rotation_euler = (C.transposed() @ Euler(edit['rotation'], 'XYZ').to_matrix() @ C).to_euler('XYZ')
        if 'scale' in edit:
            sx, sy, sz = edit['scale']
            root.scale = (sx, sz, sy)
        if 'color' in edit:
            raw = edit['color'].lstrip('#')
            rgb = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            rgb = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
            for child in root.children:
                if child.type != 'MESH':
                    continue
                for slot in child.material_slots:
                    slot.material = slot.material.copy()
                    m = slot.material
                    n = m.node_tree.nodes.get('Principled BSDF')
                    for link in list(m.node_tree.links):
                        if link.to_socket == n.inputs['Base Color']:
                            m.node_tree.links.remove(link)
                    n.inputs['Base Color'].default_value = (*rgb, 1)
                    m.diffuse_color = (*rgb, 1)
    bpy.context.scene.unit_settings.system = 'METRIC'
    setup_lighting(view)
    bpy.context.view_layer.update()
    if view == 'exterior' or a.render:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(out / 'design.blend'))
    result = bpy.ops.export_scene.gltf(filepath=str(out / (view + '.glb')), export_format='GLB', export_apply=True, export_extras=True, export_cameras=False, export_lights=False)
    if 'FINISHED' not in result:
        raise RuntimeError('GLB export failed')

def setup_lighting(view):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1200
    sc.render.resolution_y = 900
    sc.render.resolution_percentage = 100
    sc.world = bpy.data.worlds.new('Architectural daylight')
    sc.world.use_nodes = True
    nodes = sc.world.node_tree.nodes
    links = sc.world.node_tree.links
    nodes.get('Background').inputs['Color'].default_value = (0.52, 0.62, 0.78, 1)
    nodes.get('Background').inputs['Strength'].default_value = 0.7
    bpy.ops.object.light_add(type='SUN', location=(-10, -10, 20))
    light = bpy.context.object
    light.name = 'Afternoon sun'
    light.data.energy = 3.0
    light.data.angle = math.radians(4)
    light.rotation_euler = (math.radians(28), math.radians(-24), math.radians(-35))
    W, D = (scene['width'], scene['depth'])
    height = MASTER.get('storeys', 1) * MASTER.get('storey_height', 3.45)
    bpy.ops.object.camera_add(location=(W * 1.7, -D * 0.95, max(W, D, height) * (0.95 if view != 'exterior' else 0.75)))
    cam = bpy.context.object
    cam.name = 'Presentation camera'
    target = Vector((W / 2, D * 0.45, max(1.2, height * 0.4)))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 42
    sc.camera = cam
    if PRESENTATION.get('camera'):
        px, py, pz = PRESENTATION['camera']
        cam.location = (px, -pz, py)
        tx, ty, tz = PRESENTATION['target']
        target = Vector((tx, -tz, ty))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = cam.data.sensor_width / (2 * math.tan(math.radians(43) / 2) * 4 / 3)
    if PRESENTATION.get('sun'):
        px, py, pz = PRESENTATION['sun']
        light.location = (px, -pz, py)
        light.rotation_euler = (target - light.location).to_track_quat('-Z', 'Y').to_euler()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.exposure = math.log2(PRESENTATION.get('exposure', 1)) + 0.75
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.region_3d.view_location = (W / 2, D / 2, 1.3)
                space.region_3d.view_distance = max(W, D) * 1.7
                space.region_3d.view_rotation = cam.rotation_euler.to_quaternion()
                space.shading.type = 'MATERIAL'
                space.overlay.show_axis_x = True
                space.overlay.show_axis_y = True
    # A presentation ground fills the horizon in the Cycles image; excluded from GLB.
    if a.render:
        bpy.ops.mesh.primitive_plane_add(size=2000, location=(W / 2, D / 2, -0.24))
        ground = bpy.context.object
        ground.name = 'Render ground'
        m = bpy.data.materials.new('Render ground')
        m.use_nodes = True
        m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.13, 0.16, 0.12, 1)
        m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = 0.95
        ground.data.materials.append(m)
if a.render:
    build(a.view)
    sc = bpy.context.scene
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = str(out / 'render.png')
    bpy.ops.render.render(write_still=True)
else:
    for mode in ('exterior', 'interior', 'cutaway'):
        build(mode)
print('DYNAMIC_DESIGN_READY', out)
