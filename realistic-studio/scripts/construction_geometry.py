"""Concept frame and visible column cages; never substitutes for structural design."""
import math
from construction import construction_plan


def add_construction(scene,base,level,entity,box,cylinder,mat):
    plan=construction_plan(scene)
    concrete=mat((0.48,0.51,0.53),rough=0.9)
    steel=mat((0.29,0.33,0.38),metal=0.75,rough=0.45)
    timber=mat((0.56,0.34,0.15),finish='wood')
    top=base+plan['pitch']
    for column in plan['columns']:
        x,y,h=column['x'],column['y'],column['height']
        entity('structure:'+column['id'],'Structure column')
        box('Concept column',(column['width'],column['depth'],h),(x,y,base+h/2),concrete)
        entity('rebar:'+column['id'],'Rebar concept')
        for dx in (-0.11,0.11):
            for dy in (-0.11,0.11):
                cylinder('Illustrative longitudinal bar',(0.012,0.012,h),(x+dx,y+dy,base+h/2),steel)
        ties=math.ceil(h/0.25)+1
        for index in range(ties):
            z=base+0.02+(h-0.04)*index/(ties-1)
            for dx in (-0.11,0.11):
                box('Illustrative tie',(0.008,0.22,0.008),(x+dx,y,z),steel)
            for dy in (-0.11,0.11):
                box('Illustrative tie',(0.22,0.008,0.008),(x,y+dy,z),steel)
        entity('formwork:'+column['id'],'Formwork concept')
        for dx in (-0.17,0.17):
            box('Concept shutter panel',(0.025,0.35,h),(x+dx,y,base+h/2),timber)
        for dy in (-0.17,0.17):
            box('Concept shutter panel',(0.35,0.025,h),(x,y+dy,base+h/2),timber)
    for group in ('beams','slabs'):
        for member in plan[group]:
            entity('structure:'+member['id'],'Structure '+group)
            z=top-plan['slab_depth']-member['height']/2 if group=='beams' else top-member['height']/2
            box('Concept '+group,(member['width'],member['depth'],member['height']),(member['x'],member['y'],z),concrete)
    if level==0:
        for member in plan['footings']:
            entity('structure:'+member['id'],'Structure footing')
            box('Concept footing',(member['width'],member['depth'],member['height']),(member['x'],member['y'],base-member['height']/2),concrete)
