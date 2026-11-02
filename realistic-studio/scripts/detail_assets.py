"""Detailed local furniture geometry: sewn soft goods and shaped sanitary fittings.

Meshes retain the planner's footprints and stable furniture entity root.
"""
import math
import bpy


def signed_power(value,power):
    return math.copysign(abs(value)**power,value)


def soft_mesh(name,size,center,material,angle,tag,exponent=0.45):
    """Closed superellipsoid, with gentle textile deformation instead of hard boxes."""
    vertices=[];faces=[];nu,nv=40,18
    for j in range(nv+1):
        v=-math.pi/2+math.pi*j/nv
        for i in range(nu):
            u=math.tau*i/nu
            x=size[0]/2*signed_power(math.cos(v),exponent)*signed_power(math.cos(u),exponent)
            y=size[1]/2*signed_power(math.cos(v),exponent)*signed_power(math.sin(u),exponent)
            z=size[2]/2*signed_power(math.sin(v),exponent)
            z+=0.002*math.sin(u*9+v*3)*math.cos(v)**2
            vertices.append((x,y,z))
    for j in range(nv):
        for i in range(nu):
            a=j*nu+i;b=j*nu+(i+1)%nu
            faces.append((a,b,b+nu,a+nu))
    obj=mesh_object(name,vertices,faces,center,material,angle,tag)
    return obj


def mesh_object(name,vertices,faces,center,material,angle,tag):
    mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.location=center;obj.rotation_euler.z=angle
    uv=mesh.uv_layers.new(name='UVMap')
    repeat=material.get('repeat_m',1.0)
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co.x/repeat,co.y/repeat)
    tag(obj);return obj


def seam(name,points,center,material,angle,tag,radius=0.0025,closed=True):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
    curve.bevel_depth=radius;curve.bevel_resolution=2;curve.resolution_u=1
    path=curve.splines.new('POLY');path.points.add(len(points)-1)
    for point,value in zip(path.points,points):point.co=(*value,1)
    path.use_cyclic_u=closed
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    obj.location=center;obj.rotation_euler.z=angle;curve.materials.append(material);tag(obj)
    # Convert before grouping so GLB export contains piping geometry.
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.convert(target='MESH');obj.select_set(False)
    return obj


def cushion(name,size,center,material,angle,tag):
    obj=soft_mesh(name,size,center,material,angle,tag)
    points=[]
    thin=min(range(3),key=lambda axis:size[axis])
    plane=[axis for axis in range(3) if axis!=thin]
    for i in range(64):
        t=i*math.tau/64
        point=[0.,0.,0.]
        point[plane[0]]=size[plane[0]]*0.497*signed_power(math.cos(t),0.45)
        point[plane[1]]=size[plane[1]]*0.497*signed_power(math.sin(t),0.45)
        points.append(tuple(point))
    seam(name+' stitched piping',points,center,material,angle,tag)
    return obj


def duvet(name,w,d,center,material,angle,tag):
    nx,ny=32,36;vertices=[];faces=[]
    for j in range(ny+1):
        y=-d/2+d*j/ny
        for i in range(nx+1):
            x=-w/2+w*i/nx
            side=max(0,(abs(x)/(w/2)-0.85)/0.15)
            fold=0.008*math.sin(x*29+y*5)+0.004*math.sin(y*36+x*4)
            z=fold-0.08*side**2+0.018*math.exp(-((y-d*0.34)/0.06)**2)
            vertices.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    obj=mesh_object(name,vertices,faces,center,material,angle,tag)
    mod=obj.modifiers.new('Duvet thickness','SOLIDIFY');mod.thickness=0.018
    return obj


def basin_bowl(name,w,d,center,material,angle,tag):
    """Continuous ceramic rim and recessed inner bowl, rather than a solid slab."""
    rings=[(1.0,0.04),(1.0,-0.08),(0.86,-0.09),(0.78,0.035),(0.68,-0.015),(0.35,-0.12),(0.10,-0.13)]
    n=48;vertices=[];faces=[]
    for scale,z in rings:
        for i in range(n):
            t=math.tau*i/n
            vertices.append((w/2*scale*signed_power(math.cos(t),0.65),d/2*scale*signed_power(math.sin(t),0.65),z))
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
    return mesh_object(name,vertices,faces,center,material,angle,tag)


def add_detail_furniture(kind,f,base,part,tag,fabric,wood,frame,white,metal):
    x,y,w,d,h,angle=(f['x'],f['y'],f['width'],f['depth'],f['height'],math.radians(f['rotation_deg']))
    def world(dx,dy,z):
        return (x+dx*math.cos(angle)-dy*math.sin(angle),y+dx*math.sin(angle)+dy*math.cos(angle),base+0.035+z)
    if kind=='bed':
        part('timber bed frame',(w,d,h*0.3),(0,0,h*0.2),frame)
        cushion('Quilted mattress',(w*0.98,d*0.96,h*0.3),world(0,0,h*0.51),white,angle,tag)
        duvet('Draped duvet with folds',w*0.99,d*0.73,world(0,-d*0.115,h*0.71),fabric,angle,tag)
        for dx in (-w*0.24,w*0.24):
            cushion('Pillow with sewn edge',(w*0.44,d*0.22,h*0.18),world(dx,d*0.30,h*0.77),white,angle,tag)
            cushion('Accent cushion',(w*0.28,d*0.15,h*0.20),world(dx,d*0.16,h*0.81),fabric,angle,tag)
        part('Headboard timber surround',(w,0.065,h*1.5),(0,d*0.45,h*0.75),wood)
        for dx in (-w*0.245,w*0.245):
            cushion('Upholstered headboard',(w*0.47,0.08,h*1.1),world(dx,d*0.405,h*0.85),fabric,angle,tag)
        for dx in (-w*0.39,w*0.39):
            for dy in (-d*0.38,d*0.38):part('Bed foot',(0.07,0.07,0.12),(dx,dy,0.06),frame)
        return True
    if kind=='sofa':
        part('Sofa base frame',(w*0.95,d*0.98,h*0.23),(0,0,h*0.21),frame)
        cushion('Upholstered sofa back',(w*0.22,d*0.95,h*0.75),world(w*0.36,0,h*0.58),fabric,angle,tag)
        seats=2 if f.get('design_variant',0)==1 else 3
        for i in range(seats):
            yy=(-0.31+0.62*i/max(1,seats-1))*d
            cushion('Sewn seat cushion',(w*0.72,d*0.86/seats,h*0.19),world(-w*0.045,yy,h*0.42),fabric,angle,tag)
            cushion('Sewn back cushion',(w*0.18,d*0.80/seats,h*0.42),world(w*0.19,yy,h*0.68),fabric,angle,tag)
        for dy in (-d*0.44,d*0.44):
            cushion('Rounded sofa arm',(w*0.94,d*0.12,h*0.52),world(0,dy,h*0.44),fabric,angle,tag)
            cushion('Loose scatter cushion',(w*0.23,d*0.22,h*0.3),world(w*0.02,dy*0.62,h*0.68),white,angle,tag)
        for dx in (-w*0.36,w*0.36):
            for dy in (-d*0.35,d*0.35):part('Sofa leg',(0.045,0.045,h*0.13),(dx,dy,h*0.065),frame)
        return True
    if kind=='toilet':
        soft_mesh('Sculpted toilet pedestal',(w*0.62,d*0.62,h*0.5),world(0,-d*0.06,h*0.25),white,angle,tag,0.65)
        basin_bowl('Hollow toilet bowl',w,d*0.75,world(0,-d*0.08,h*0.56),white,angle,tag)
        points=[(w*0.42*math.cos(i*math.tau/64),d*0.30*math.sin(i*math.tau/64),0) for i in range(64)]
        seam('Oval toilet seat',points,world(0,-d*0.08,h*0.62),white,angle,tag,radius=0.025)
        part('Cistern',(w*0.85,d*0.23,h*0.82),(0,d*0.35,h*0.43),white)
        part('Cistern lid',(w*0.9,d*0.26,0.035),(0,d*0.35,h*0.86),white)
        part('Flush button',(0.06,0.035,0.015),(0,d*0.35,h*0.89),metal)
        return True
    if kind=='basin':
        part('Vanity carcass',(w,d,h*0.75),(0,0,h*0.40),wood)
        for dx in (-w*0.24,w*0.24):
            part('Vanity drawer',(w*0.46,0.025,h*0.3),(dx,-d*0.49,h*0.5),wood)
            part('Vanity drawer pull',(w*0.22,0.025,0.015),(dx,-d*0.52,h*0.6),metal)
        basin_bowl('Hollow ceramic basin',w*0.94,d*0.88,world(0,-d*0.04,h),white,angle,tag)
        part('Mixer tap stem',(0.035,0.035,0.18),(0,d*0.34,h+0.06),metal)
        part('Mixer tap spout',(0.035,d*0.25,0.035),(0,d*0.22,h+0.15),metal)
        part('Mirror',(w*0.85,0.025,0.65),(0,d*0.48,h+0.52),metal)
        part('Basin drain',(0.06,0.06,0.012),(0,-d*0.04,h-0.125),metal,shape='cylinder')
        return True
    return False


def curtain_panel(name,width,height,center,material,angle,tag):
    nx,nz=24,24;vertices=[];faces=[]
    for j in range(nz+1):
        z=height*j/nz
        for i in range(nx+1):
            x=-width/2+width*i/nx
            fold=0.022*math.cos(i/nx*math.tau*5)*(0.8+0.2*j/nz)
            vertices.append((x,fold,z))
    for j in range(nz):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    obj=mesh_object(name,vertices,faces,center,material,angle,tag)
    mod=obj.modifiers.new('Linen thickness','SOLIDIFY');mod.thickness=0.002
    return obj
