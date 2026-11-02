"""Local interior finishing; dimensions are visual defaults, not specifications."""
from geometry import owners


def add_finishing(scene, base, entity, box, cylinder, mat, metal, white, view, curtain_material=None, curtain_builder=None):
    trim = mat((0.86, 0.83, 0.76), rough=0.5)
    fabric = mat((0.76, 0.70, 0.59), rough=0.95, finish='fabric')
    for room in scene['rooms']:
        if room['id'] == 'vertical_core':
            continue
        x, y, w, d, h = (room[k] for k in ('x', 'y', 'width', 'depth', 'height'))
        entity('finish:' + room['id'], 'Interior finish', (x, y, base))
        # Split skirting at every door/portal, rather than running it through openings.
        boundaries = [('x', y, x, x+w, 1), ('x', y+d, x, x+w, -1),
                      ('y', x, y, y+d, 1), ('y', x+w, y, y+d, -1)]
        for axis, fixed, low, high, inward in boundaries:
            cuts = [(low+0.12, high-0.12)]
            for opening in scene['openings']:
                if opening['kind'] == 'window' or opening['axis'] != axis:
                    continue
                if abs(opening['y' if axis == 'x' else 'x']-fixed) > 0.025:
                    continue
                start = opening['x' if axis == 'x' else 'y']-opening['width']/2
                end = start+opening['width']
                pieces = []
                for a, b in cuts:
                    if end <= a or start >= b:
                        pieces.append((a,b))
                    else:
                        if start-0.04 > a: pieces.append((a,start-0.04))
                        if end+0.04 < b: pieces.append((end+0.04,b))
                cuts = pieces
            for a,b in cuts:
                if b-a <= 0.01: continue
                size = (b-a,0.025,0.10) if axis == 'x' else (0.025,b-a,0.10)
                pos = ((a+b)/2,fixed+inward*0.105,base+0.065) if axis == 'x' else (fixed+inward*0.105,(a+b)/2,base+0.065)
                box('Painted skirting',size,pos,trim,True)
        entity('fixture:' + room['id'], 'Light fixture', (x+w/2,y+d/2,base))
        cylinder('Ceiling light trim',(0.34,0.34,0.035),(x+w/2,y+d/2,base+h-0.065),metal)
        cylinder('Opal diffuser',(0.29,0.29,0.025),(x+w/2,y+d/2,base+h-0.09),white)
    if view == 'cutaway': return
    for opening in scene['openings']:
        if opening['kind'] != 'window': continue
        attached = owners(opening, scene['rooms'])
        if len(attached) != 1: continue
        room = attached[0]
        x,y,w,h = (opening[k] for k in ('x','y','width','height'))
        axis=opening['axis']; bottom=base+opening['bottom']
        fixed=y if axis=='x' else x
        inward=1 if abs(fixed-room['y' if axis=='x' else 'x'])<0.025 else -1
        chosen_fabric = curtain_material(room) if curtain_material else fabric
        entity('curtain:'+opening['id'],'Interior finish',(x,y,base))
        if curtain_builder:
            panel_width=min(0.38,w*0.22)
            height=opening['bottom']+h+0.10
            for side in (-1,1):
                offset=side*(w/2-panel_width/2)
                center=(x+offset,y+inward*0.15,base+0.08) if axis=='x' else (x+inward*0.15,y+offset,base+0.08)
                curtain_builder('Pleated linen curtain',panel_width,height,center,chosen_fabric,0 if axis=='x' else 1.57079632679)
            # Concealed track and hems remain separate visible details.
            size=(w,0.04,0.035) if axis=='x' else (0.04,w,0.035)
            pos=(x,y+inward*0.15,bottom+h+0.16) if axis=='x' else (x+inward*0.15,y,bottom+h+0.16)
            box('Curtain track',size,pos,metal,True)
        else:
            for side in (0.12,w-0.12):
                for fold in range(4):
                    along=-w/2+side+(fold-1.5)*0.045
                    pos=(x+along,y+inward*(0.14+(fold%2)*0.02),bottom+h/2) if axis=='x' else (x+inward*(0.14+(fold%2)*0.02),y+along,bottom+h/2)
                    size=(0.05,0.045,h+0.12) if axis=='x' else (0.045,0.05,h+0.12)
                    box('Linen curtain pleat',size,pos,chosen_fabric,True)
