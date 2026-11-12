"""Parametric villa details placed on real exposed walls and openings.

These are architectural visualization elements, not structural design.
"""
from geometry import edges, owners


def exposed_segments(scene):
    for room in scene['rooms']:
        for axis, fixed, lo, hi in edges(room):
            cuts = {lo, hi}
            for other in scene['rooms']:
                for aa, ff, ll, hh in edges(other):
                    if aa == axis and abs(ff-fixed) < .025:
                        cuts.update(v for v in (ll, hh) if lo < v < hi)
            points = sorted(cuts)
            for left, right in zip(points, points[1:]):
                middle = (left+right)/2
                count = sum(any(aa==axis and abs(ff-fixed)<.025 and ll-.001<middle<hh+.001
                                for aa,ff,ll,hh in edges(other)) for other in scene['rooms'])
                if count == 1:
                    sign = -1 if abs(fixed-(room['y'] if axis=='x' else room['x']))<.025 else 1
                    yield room, axis, fixed, left, right, sign


def solid_intervals(left, right, openings, axis, fixed):
    intervals = [(left+.15, right-.15)]
    for opening in openings:
        if opening['axis'] != axis or abs((opening['y'] if axis=='x' else opening['x'])-fixed)>.025:
            continue
        center=opening['x'] if axis=='x' else opening['y']
        low,high=center-opening['width']/2-.18,center+opening['width']/2+.18
        intervals=[part for a,b in intervals for part in ((a,min(b,low)),(max(a,high),b)) if part[1]-part[0]>.1]
    return intervals


def add_villa_facade(scene, base, level, view, entity, box, mat, surface, resolve_materials):
    config=scene.get('architecture')
    if not config or view == 'cutaway':
        return
    stone=surface(resolve_materials(scene,scene['rooms'][0])['stone'])
    timber=surface(resolve_materials(scene,scene['rooms'][0])['wood'])
    plaster=mat(scene['wall_color'],finish='p_plaster',rough=.9)
    metal=mat((.035,.045,.045),metal=.65,rough=.3)
    top_level=level==scene.get('storeys',1)-1
    courtyard_pergola=False
    for room,axis,fixed,left,right,sign in exposed_segments(scene):
        length=right-left
        height=room['height']
        def pos(along,out,z):
            return (along,fixed+sign*out,base+z) if axis=='x' else (fixed+sign*out,along,base+z)
        def size(along,out,z):
            return (along,out,z) if axis=='x' else (out,along,z)
        key=f"villa:{room['id']}:{axis}:{fixed}:{left}"
        entity(key,'Facade')
        if view=='exterior' and top_level:
            stepped=config['parapet_profile']=='stepped'
            rise=.38 if stepped and room.get('kind') in ('living','dining','kitchen') else .12
            box('Villa roof edge cantilever',size(length+.02,config['roof_overhang']+.1,.16),pos((left+right)/2,config['roof_overhang']/2,height+.07),plaster,True)
            box('Villa raised parapet',size(length,.2,.3+rise),pos((left+right)/2,0,height+.2+rise/2),plaster,True)
            box('Villa floating cornice',size(length+.14,config['roof_overhang']+.22,.12),pos((left+right)/2,config['roof_overhang']/2,height+.43+rise),stone,True)
            box('Villa shadow reveal',size(length,.06,.045),pos((left+right)/2,.13,height+.38+rise),metal)
        if config['facade_panels']:
            for a,b in solid_intervals(left,right,scene['openings'],axis,fixed):
                if b-a<.65:
                    continue
                panel_width=min(1.2,(b-a)*.65)
                box('Villa stone feature panel',size(panel_width,.095,height-.45),pos((a+b)/2,.14,(height-.45)/2+.12),stone,True)
                if config['screens'] and b-a>1.1:
                    screen_width=min(.8,(b-a)-panel_width-.12)
                    if screen_width>.25:
                        center=a+screen_width/2
                        count=max(2,int(screen_width/config['screen_spacing']))
                        for index in range(count):
                            along=center-screen_width/2+(index+.5)*screen_width/count
                            box('Villa timber privacy fin',size(.055,.15,height-.55),pos(along,.22,(height-.55)/2+.2),timber,True)
        for window in scene['openings']:
            if window['kind']!='window' or window['axis']!=axis or abs((window['y'] if axis=='x' else window['x'])-fixed)>.025:
                continue
            center=window['x'] if axis=='x' else window['y']
            if not left<=center<=right:
                continue
            width=window['width']; bottom=window['bottom']; wh=window['height']
            for side in (-1,1):
                box('Villa deep window surround',size(.1,.24,wh+.25),pos(center+side*(width/2+.08),.13,bottom+wh/2),stone,True)
            box('Villa window sun ledge',size(width+.3,.48,.1),pos(center,.22,bottom+wh+.16),stone,True)
            box('Villa projecting sill',size(width+.3,.3,.07),pos(center,.14,bottom-.065),stone,True)
        middle=(left+right)/2
        probe=pos(middle,.4,0)
        inside=0<probe[0]<scene['width'] and 0<probe[1]<scene['depth']
        if config['pergola'] and not courtyard_pergola and inside and length>3.4 and level==0:
            width=min(length-.4,5.0); depth=min(2.8,config['porch_depth']+.3); roof_z=min(height-.15,3.0)
            for side in (-1,1):
                box('Courtyard pergola post',size(.13,.13,roof_z),pos(middle+side*(width/2-.1),depth,roof_z/2),timber,True)
            box('Courtyard pergola front beam',size(width,.16,.2),pos(middle,depth,roof_z),timber,True)
            count=max(5,int(width/.28))
            for index in range(count):
                box('Courtyard open pergola rafter',size(.075,depth+.15,.14),pos(middle-width/2+(index+.5)*width/count,depth/2,roof_z+.12),timber,True)
            courtyard_pergola=True
    for door in scene['openings']:
        if not door.get('entrance') or level!=0:
            continue
        room=owners(door,scene['rooms'])[0]
        axis=door['axis'];fixed=door['y'] if axis=='x' else door['x'];center=door['x'] if axis=='x' else door['y']
        sign=-1 if abs(fixed-(room['y'] if axis=='x' else room['x']))<.025 else 1
        def pos(along,out,z):
            return (along,fixed+sign*out,base+z) if axis=='x' else (fixed+sign*out,along,base+z)
        def size(along,out,z):
            return (along,out,z) if axis=='x' else (out,along,z)
        entity('villa:entrance','Facade')
        width=config['porch_width'];depth=config['porch_depth'];height=room['height']+.12
        box('Villa entrance terrace',size(width+.6,depth+.4,.1),pos(center,depth/2,.01),stone,True)
        if config['entrance_style']=='portal':
            for side in (-1,1):
                box('Villa portal pier',size(.3,.4,height),pos(center+side*(width/2-.15),depth-.1,height/2),stone,True)
            box('Villa entrance portal lintel',size(width,.5,.32),pos(center,depth-.1,height),stone,True)
        if config['entrance_style']=='pergola':
            for side in (-1,1):
                box('Villa entrance pergola post',size(.14,.14,height),pos(center+side*(width/2-.1),depth-.1,height/2),timber,True)
            box('Villa entrance pergola beam',size(width,.16,.2),pos(center,depth-.1,height),timber,True)
            count=max(5,int(width/.25))
            for index in range(count):
                box('Villa entrance open rafter',size(.075,depth,.14),pos(center-width/2+(index+.5)*width/count,depth/2,height+.14),timber,True)
        else:
            box('Villa broad entrance canopy',size(width,depth,.14),pos(center,depth/2,height+.12),plaster,True)
            for index in range(max(4,int(width/.2))):
                along=center-width/2+(index+.5)*.2
                if along<center+width/2:
                    box('Villa porch timber soffit',size(.08,depth-.15,.025),pos(along,depth/2,height+.035),timber)
        for side in (-1,1):
            box('Villa entrance wall light',size(.09,.12,.32),pos(center+side*(door['width']/2+.24),.18,1.9),metal,True)
