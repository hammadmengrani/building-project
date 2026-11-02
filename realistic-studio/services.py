"""Illustrative services coordinates, deliberately without engineering certification.

Branches indicate topology only, not coordinated installable conduit routes.
Wet rooms have no automatically placed general-purpose sockets.
"""
STATUS = 'Concept only — not engineer reviewed'


def electrical_plan(layout):
    rooms = layout['rooms']
    anchor = next((r for r in rooms if r['id'] == 'floor_lobby'), rooms[0])
    board = [anchor['x']+0.2, anchor['y']+0.15, 1.5]
    devices = [dict(id='distribution_board',kind='board',point=board)]
    routes = []
    for room in rooms:
        if room.get('kind') == 'stairs': continue
        x,y,w,d,h = (room[k] for k in ('x','y','width','depth','height'))
        light=[x+w/2,y+d/2,h-0.12]
        # Prefer a wall containing an actual room door for the illustrative switch.
        from geometry import owners
        doors=[o for o in layout['openings'] if o['kind'] in ('door','portal') and room in owners(o,rooms)]
        switch=[x+0.2,y+0.13,1.15]
        if doors:
            door=doors[0]
            if door['axis']=='x':
                switch=[max(x+0.18,min(x+w-0.18,door['x']-0.18)),door['y']+(0.13 if abs(door['y']-y)<0.025 else -0.13),1.15]
            else:
                switch=[door['x']+(0.13 if abs(door['x']-x)<0.025 else -0.13),max(y+0.18,min(y+d-0.18,door['y']-0.18)),1.15]
        for kind,point in [('light',light),('switch',switch)]:
            devices.append(dict(id=room['id']+':'+kind,kind=kind,point=point))
        top=h-0.15
        routes.append(dict(id=room['id']+':lighting',circuit='lighting',points=[board,[board[0],board[1],top],[switch[0],board[1],top],[switch[0],switch[1],top],switch]))
        routes.append(dict(id=room['id']+':switched',circuit='lighting',points=[switch,[switch[0],switch[1],top],[light[0],switch[1],top],[light[0],light[1],top],light]))
        wet_fixtures = any(f['room_id'] == room['id'] and f['kind'] in ('toilet','shower','kitchen') for f in layout['furniture'])
        if not wet_fixtures and room.get('kind') not in ('bathroom','hall','stairs','kitchen'):
            socket=[x+w-0.18,y+d-0.13,0.35]
            devices.append(dict(id=room['id']+':socket',kind='socket',point=socket))
            routes.append(dict(id=room['id']+':power',circuit='power',points=[board,[board[0],board[1],top],[socket[0],board[1],top],[socket[0],socket[1],top],socket]))
    return dict(status=STATUS,devices=devices,routes=routes,
                omissions=['Load calculations','Cable and protective-device sizing','Earthing and bonding','Wet-area and pool circuits','Clash coordination','Engineer approval'])


def plumbing_plan(layout):
    """Concept networks connected to a common riser; no hydraulic/slope design."""
    core = layout.get('vertical_core')
    anchor = next((r for r in layout['rooms'] if r['id']=='vertical_core'),layout['rooms'][0])
    riser=[anchor['x']+0.15,anchor['y']+0.15,0.1]
    routes=[]
    fixtures=[]
    for item in layout['furniture']:
        if item['kind'] not in ('kitchen','basin','shower','toilet'): continue
        point=[item['x'],item['y'],0.75 if item['kind'] in ('kitchen','basin') else 0.15]
        fixtures.append(dict(id=item['id'],kind=item['kind'],point=point))
        circuits=['cold','drain'] if item['kind']=='toilet' else ['cold','hot','drain']
        for circuit in circuits:
            z=0.12 if circuit=='cold' else 0.19 if circuit=='hot' else -0.08
            # Separate heights make systems readable; drain slope is not calculated.
            target=[point[0],point[1],0.08 if circuit=='drain' else point[2]]
            offset={'cold':0.0,'hot':0.12,'drain':0.24}[circuit]
            points=[[riser[0]+offset,riser[1],z],[point[0],riser[1],z],[point[0],point[1],z],target]
            routes.append(dict(id=item['id']+':'+circuit,circuit=circuit,points=points))
    return dict(status=STATUS,riser=riser,fixtures=fixtures,routes=routes,
                omissions=['Water demand and pressure','Pipe sizing','Drain slope and venting','External supply/sewer connections','Backflow protection','Clash coordination','Engineer approval'])
