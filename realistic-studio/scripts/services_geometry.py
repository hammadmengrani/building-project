"""Exportable concept electrical overlay. Colors identify circuits, not conductor IDs."""
from mathutils import Vector
from services import electrical_plan


def add_electrical(layout,base,entity,box,cylinder,mat):
    plan=electrical_plan(layout)
    colors={'lighting':mat((1.0,0.56,0.04),rough=0.4),'power':mat((0.04,0.55,0.95),rough=0.4)}
    plate=mat((0.94,0.93,0.88),rough=0.45)
    for device in plan['devices']:
        point=device['point']; pos=(point[0],point[1],base+point[2])
        entity('electrical:device:'+device['id'],'Electrical device',pos)
        kind=device['kind']
        size=(0.35,0.12,0.45) if kind=='board' else (0.12,0.045,0.12)
        if kind=='light': cylinder('Concept light point',(0.2,0.2,0.04),pos,plate)
        else: box('Concept '+kind,size,pos,plate,True)
    for route in plan['routes']:
        entity('electrical:'+route['id'],'Electrical '+route['circuit'])
        for start,end in zip(route['points'],route['points'][1:]):
            a,b=Vector((start[0],start[1],base+start[2])),Vector((end[0],end[1],base+end[2]))
            delta=b-a
            if delta.length<0.001: continue
            obj=cylinder('Concept circuit route',(0.025,0.025,delta.length),(a+b)/2,colors[route['circuit']])
            obj.rotation_euler=delta.to_track_quat('Z','Y').to_euler()


def add_plumbing(layout,base,entity,box,cylinder,mat,level,count):
    from services import plumbing_plan
    plan=plumbing_plan(layout)
    colors={'cold':mat((0.02,0.75,0.9),rough=0.4),
            'hot':mat((0.94,0.13,0.09),rough=0.4),
            'drain':mat((0.34,0.19,0.08),rough=0.8)}
    def pipe(label,start,end,diameter,material):
        a,b=Vector(start),Vector(end); delta=b-a
        if delta.length<0.001:return
        obj=cylinder(label,(diameter,diameter,delta.length),(a+b)/2,material)
        obj.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
    for route in plan['routes']:
        entity('plumbing:'+route['id'],'Plumbing '+route['circuit'])
        for start,end in zip(route['points'],route['points'][1:]):
            pipe('Concept '+route['circuit']+' pipe',(start[0],start[1],base+start[2]),(end[0],end[1],base+end[2]),0.065 if route['circuit']=='drain' else 0.035,colors[route['circuit']])
    if plan['routes']:
        x,y,_=plan['riser']
        for i,circuit in enumerate(colors):
            entity('plumbing:riser:'+circuit,'Plumbing '+circuit)
            pipe('Concept '+circuit+' riser',(x+i*0.12,y,base-0.08),(x+i*0.12,y,base+layout.get('storey_height',3.45)),0.075 if circuit=='drain' else 0.04,colors[circuit])
