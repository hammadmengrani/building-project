"""Prompt material choices resolved into reproducible, renderer-independent specs."""
import copy

STYLE_MATERIALS = {
    'modern': ('oak', (0.48,0.31,0.17), 'linen', (0.76,0.74,0.68), 'marble'),
    'traditional': ('walnut', (0.23,0.105,0.045), 'linen', (0.42,0.12,0.13), 'stone'),
    'industrial': ('oak', (0.29,0.20,0.13), 'leather', (0.25,0.13,0.08), 'concrete'),
    'coastal': ('oak', (0.75,0.65,0.47), 'linen', (0.55,0.72,0.74), 'stone'),
    'minimalist': ('oak', (0.68,0.58,0.43), 'linen', (0.78,0.77,0.72), 'concrete'),
}


def rgb(values):
    return dict(zip(('r','g','b'),values))


def resolve_materials(scene, room):
    style=room.get('interior_style',scene.get('interior_style','modern'))
    wood,color,fabric,upholstery,stone=STYLE_MATERIALS.get(style,STYLE_MATERIALS['modern'])
    specs={
        'wood':dict(finish=wood,color=rgb(color),roughness=0.48,repeat_m=1.2),
        'upholstery':dict(finish=fabric,color=rgb(upholstery),roughness=0.85 if fabric=='linen' else 0.4,repeat_m=0.5),
        'stone':dict(finish=stone,color=rgb((0.73,0.72,0.67)),roughness=0.32,repeat_m=1.0),
        'curtain':dict(finish='linen',color=rgb((0.83,0.80,0.73)),roughness=0.95,repeat_m=0.5),
        'floor':dict(finish=wood if room.get('kind')=='bedroom' or 'bedroom' in room.get('name','').lower() else 'ceramic',color=room['floor_color'],roughness=0.55,repeat_m=1.2 if room.get('kind')=='bedroom' else 0.6),
        'wall':dict(finish='plaster',color=scene['wall_color'],roughness=0.9,repeat_m=1.0),
    }
    for overrides in (scene.get('materials') or {},room.get('materials') or {}):
        for role, spec in overrides.items():
            if role in specs and spec:
                specs[role].update({k:v for k,v in spec.items() if v is not None})
    return copy.deepcopy(specs)
