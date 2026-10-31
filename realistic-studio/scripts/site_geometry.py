"""Reusable Blender geometry for site facilities and vertical circulation."""
import math
from mathutils import Vector

def rail(start, end, radius, material, cylinder):
    delta = Vector(end) - Vector(start)
    obj = cylinder('Handrail', (radius * 2, radius * 2, delta.length), (Vector(start) + Vector(end)) / 2, material)
    obj.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()

def add_stairs(core, base, level, count, entity, box, cylinder, concrete, metal, glass):
    if not core:
        return
    entity('stairs:landing', 'Stairs', (0, 0, base))
    width, depth, pitch = (core['width'], core['depth'], core['storey_height'])
    box('Arrival landing', (width, 1.1, 0.25), (width / 2, 0.55, base - 0.125), concrete)
    if level < count - 1:
        entity('stairs:flight', 'Stairs', (0, 0, base))
        risers = math.ceil(pitch / 0.18)
        risers += risers % 2
        half = risers // 2
        rise = pitch / risers
        run = (depth - 2.2) / half
        for step in range(half):
            first = (step + 1) * rise
            second = pitch / 2 + (step + 1) * rise
            box('Ascending stair tread', (1.45, run + 0.008, first), (0.925, 1.1 + (step + 0.5) * run, base + first / 2), concrete)
            box('Returning stair tread', (1.45, run + 0.008, second), (2.675, depth - 1.1 - (step + 0.5) * run, base + second / 2), concrete)
            if step % 2 == 0:
                for x, y, z in [(1.65, 1.1 + (step + 0.5) * run, base + first), (1.95, depth - 1.1 - (step + 0.5) * run, base + second)]:
                    cylinder('Stair baluster', (0.035, 0.035, 0.9), (x, y, z + 0.45), metal)
        box('Half-level landing', (3.6, 1.1, 0.18), (1.8, depth - 0.55, base + pitch / 2 - 0.09), concrete)
        rail((1.65, 1.1, base + 0.9), (1.65, depth - 1.1, base + pitch / 2 + 0.9), 0.025, metal, cylinder)
        rail((1.95, depth - 1.1, base + pitch / 2 + 0.9), (1.95, 1.1, base + pitch + 0.9), 0.025, metal, cylinder)
    if core.get('lift'):
        entity('lift:shaft', 'Lift', (3.6, 3.2, base))
        for x in (3.67, width - 0.07):
            box('Lift shaft side', (0.14, 2.2, pitch), (x, 4.3, base + pitch / 2), concrete)
        box('Lift shaft rear', (width - 3.6, 0.14, pitch), ((width + 3.6) / 2, depth - 0.07, base + pitch / 2), concrete)
        box('Lift doors', (width - 3.9, 0.08, 2.25), ((width + 3.6) / 2, 3.2, base + 1.125), metal, True)
        box('Lift door seam', (0.018, 0.09, 2.25), ((width + 3.6) / 2, 3.145, base + 1.125), concrete)
        box('Lift call button', (0.08, 0.04, 0.14), (width - 0.12, 3.13, base + 1.1), metal)

def add_car(x, y, box, cylinder, metal, glass, paint):
    box('Car lower body', (1.9, 4.25, 0.55), (x, y, 0.58), paint, True)
    box('Car cabin', (1.6, 2.05, 0.65), (x, y + 0.15, 1.15), glass, True)
    box('Car roof', (1.55, 1.7, 0.08), (x, y + 0.15, 1.5), paint, True)
    for xx in (x - 0.94, x + 0.94):
        for yy in (y - 1.25, y + 1.25):
            wheel = cylinder('Car wheel', (0.62, 0.62, 0.16), (xx, yy, 0.35), metal)
            wheel.rotation_euler.y = math.pi / 2
    for xx in (x - 0.65, x + 0.65):
        box('Car headlight', (0.32, 0.05, 0.12), (xx, y - 2.14, 0.67), glass, True)

def add_site(scene, entity, box, cylinder, mat, concrete, metal, glass, white):
    site = scene.get('site')
    if not site:
        return False
    entity('site', 'Site')
    box('Plot surface', (site['width'], site['depth'], 0.12), (site['x'] + site['width'] / 2, site['y'] + site['depth'] / 2, -0.13), mat((0.14, 0.22, 0.075), finish='grass'))
    asphalt = mat((0.07, 0.08, 0.085), rough=0.95)
    for i, aisle in enumerate(site['aisles']):
        entity(f'parking:aisle{i + 1}', 'Driveway')
        box('Six-metre drive aisle', (aisle['width'], aisle['depth'], 0.06), (aisle['x'] + aisle['width'] / 2, aisle['y'] + aisle['depth'] / 2, -0.04), asphalt)
    for i, bay in enumerate(site['parking']):
        entity('parking:' + bay['id'], 'Parking', (bay['x'], bay['y'], 0))
        x, y, w, d = (bay['x'], bay['y'], bay['width'], bay['depth'])
        box('Parking bay asphalt', (w, d, 0.06), (x + w / 2, y + d / 2, -0.04), asphalt)
        for xx in (x + 0.04, x + w - 0.04):
            box('Parking bay stripe', (0.06, d - 0.1, 0.012), (xx, y + d / 2, 0.001), white)
        box('Wheel stop', (1.8, 0.14, 0.12), (x + w / 2, y + 0.4, 0.04), concrete, True)
        add_car(x + w / 2, y + d / 2, box, cylinder, metal, glass, mat([(0.19, 0.28, 0.36), (0.57, 0.22, 0.16), (0.65, 0.65, 0.6)][i % 3], metal=0.35, rough=0.25))
    park = site.get('park')
    if park:
        entity('park:lawn', 'Park', (park['x'], park['y'], 0))
        x, y, w, d = (park['x'], park['y'], park['width'], park['depth'])
        box('Park lawn', (w, d, 0.08), (x + w / 2, y + d / 2, -0.03), mat((0.18, 0.3, 0.09), finish='grass'))
        path_width = min(1.4, w * 0.3)
        box('Park walking path', (path_width, d, 0.07), (x + w / 2, y + d / 2, 0.025), concrete, True)
        wood = mat((0.48, 0.28, 0.12), finish='wood')
        for i, yy in enumerate((y + d * 0.25, y + d * 0.65)):
            entity('park:bench' + str(i + 1), 'Park furniture', (x + w - 0.6, yy, 0))
            xx = x + w - 0.6
            box('Park bench seat', (0.65, 1.6, 0.1), (xx, yy, 0.5), wood, True)
            box('Park bench back', (0.07, 1.6, 0.55), (xx + 0.27, yy, 0.78), wood, True)
            for dy in (-0.55, 0.55):
                box('Bench legs', (0.5, 0.07, 0.45), (xx, yy + dy, 0.25), metal)
    pool = site.get('pool')
    if pool:
        entity('pool:basin', 'Swimming pool', (pool['x'], pool['y'], 0))
        x, y, w, d = (pool[k] for k in ('x', 'y', 'width', 'depth'))
        tile = mat((0.15, 0.48, 0.62), rough=0.28)
        coping = mat((0.75, 0.72, 0.62), rough=0.65)
        box('Pool tiled basin', (w, d, 0.16), (x+w/2, y+d/2, -0.025), tile)
        for xx in (x+0.1, x+w-0.1):
            box('Pool side coping', (0.2, d, 0.25), (xx, y+d/2, 0.12), coping, True)
        for yy in (y+0.1, y+d-0.1):
            box('Pool end coping', (w, 0.2, 0.25), (x+w/2, yy, 0.12), coping, True)
        water = mat((0.035, 0.43, 0.65), rough=0.09, metal=0.15)
        box('Swimming pool water', (w-0.4, d-0.4, 0.025), (x+w/2, y+d/2, 0.10), water)
        for xx in (x+0.5, x+1.0):
            rail((xx,y+0.1,0.15),(xx,y+0.65,0.75),0.035,metal,cylinder)
        for yy in (y+0.25,y+0.45,y+0.65):
            box('Pool ladder rung',(0.5,0.045,0.045),(x+0.75,yy,0.25),metal)
    return True
