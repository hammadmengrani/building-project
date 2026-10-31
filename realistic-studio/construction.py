"""Illustrative frame and takeoff, NOT structural analysis or a procurement BOQ.

Member sizes are editable visual assumptions. Quantities describe only these members.
"""
import math
from services import STATUS


def construction_plan(scene):
    width,depth=scene['width'],scene['depth']
    nx,ny=max(1,math.ceil(width/5)),max(1,math.ceil(depth/5))
    xs=[round(i*width/nx,5) for i in range(nx+1)]
    ys=[round(i*depth/ny,5) for i in range(ny+1)]
    rooms=scene['rooms']
    def occupied(x,y):
        return any(r['x']-0.001<=x<=r['x']+r['width']+0.001 and r['y']-0.001<=y<=r['y']+r['depth']+0.001 for r in rooms)
    points={(i,j):(x,y) for i,x in enumerate(xs) for j,y in enumerate(ys) if occupied(x,y)}
    pitch=scene.get('storey_height',3.45)
    column_width=0.3; slab_depth=0.18; beam_depth=0.4; beam_width=0.25
    clear=max(0.1,pitch-slab_depth-beam_depth)
    columns=[dict(id=f'c{i}_{j}',x=x,y=y,width=column_width,depth=column_width,height=clear) for (i,j),(x,y) in points.items()]
    beams=[]
    for (i,j),(x,y) in points.items():
        for next_key in ((i+1,j),(i,j+1)):
            if next_key not in points:continue
            xx,yy=points[next_key]
            if not all(occupied(x+(xx-x)*t/20,y+(yy-y)*t/20) for t in range(21)):continue
            along=math.hypot(xx-x,yy-y)-column_width
            if along<=0:continue
            beams.append(dict(id=f'b{i}_{j}_{next_key[0]}_{next_key[1]}',x=(x+xx)/2,y=(y+yy)/2,width=along if xx!=x else beam_width,depth=beam_width if xx!=x else along,height=beam_depth))
    slabs=[dict(id='slab:'+r['id'],x=r['x']+r['width']/2,y=r['y']+r['depth']/2,width=r['width'],depth=r['depth'],height=slab_depth) for r in rooms if r['id']!='vertical_core']
    footings=[dict(id='footing:'+c['id'],x=c['x'],y=c['y'],width=1.2,depth=1.2,height=0.3) for c in columns]
    concrete=sum(m['width']*m['depth']*m['height'] for m in [*columns,*beams,*slabs])
    footing_volume=sum(f['width']*f['depth']*f['height'] for f in footings)
    # Four straight concept bars and closed rectangular ties; hooks/laps not designed.
    bars_length=len(columns)*4*clear
    ties_count=len(columns)*(math.ceil(clear/0.25)+1)
    ties_length=ties_count*(4*(column_width-0.08))
    steel=bars_length*math.pi*(0.012**2)/4*7850+ties_length*math.pi*(0.008**2)/4*7850
    formwork=sum(2*(c['width']+c['depth'])*c['height'] for c in columns)+sum((b['width']*b['depth']+2*b['height']*(b['width']+b['depth'])) for b in beams)+sum(s['width']*s['depth'] for s in slabs)
    return dict(status=STATUS,columns=columns,beams=beams,slabs=slabs,footings=footings,
                pitch=pitch,slab_depth=slab_depth,beam_depth=beam_depth,
                quantities=dict(concrete_per_floor_m3=round(concrete,3),footings_m3=round(footing_volume,3),illustrative_column_steel_per_floor_kg=round(steel,2),formwork_per_floor_m2=round(formwork,2),cement_bags=None),
                assumptions=['Illustrative ground-plan grid up to 5m; assumes repeated footprint above.', '300mm columns, 250x400mm beams, 180mm slabs and 1.2x1.2x.3m footings are visual defaults, NOT designed sizes.', 'Only column cages: four 12mm bars, 8mm ties at approximately 250mm. No engineered reinforcement schedule.', 'No beam/slab/footing reinforcement, hooks, laps, support intersections, waste, excavation or structural analysis.', 'Formwork is contact-area estimate; purchase quantities need panel layout and reuse.', 'Cement bags need an approved mix cement content and bag weight.'])
