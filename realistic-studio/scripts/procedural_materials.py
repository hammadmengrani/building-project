"""Deterministic neutral PBR maps. Colors come from the design, not baked palettes."""
import math
import os
import struct
import zlib
from pathlib import Path


def png(path, pixels, size):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    rows=b''.join(b'\0'+bytes(pixels[y*size*3:(y+1)*size*3]) for y in range(size))
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
    temp=path.with_suffix('.'+str(os.getpid())+'.tmp')
    temp.write_bytes(data);temp.replace(path)


def ensure_maps(directory,finish,roughness=0.6,size=256):
    folder=Path(directory)/'generated';folder.mkdir(parents=True,exist_ok=True)
    name=f'{finish}_r{round(roughness*100)}_v2'
    files={kind:folder/(name+'_'+kind+'.png') for kind in ('color','normal','roughness')}
    if all(p.exists() for p in files.values()):return files
    heights=[]
    for y in range(size):
        for x in range(size):
            u,v=x/size,y/size
            grain=math.sin(math.tau*(u*24+0.18*math.sin(v*math.tau*3)))
            noise=math.sin(x*12.9898+y*78.233)*43758.5453
            noise=noise-math.floor(noise)
            if finish in ('oak','walnut'):
                value=0.91+0.025*grain+0.018*noise
                if x%(size//4)<1:value*=0.9
            elif finish=='marble':
                vein=abs(math.sin(math.tau*(u*3+0.2*math.sin(v*math.tau*2))))
                value=0.65 if vein<0.045 else 0.94+0.03*noise
            elif finish=='linen':value=0.78+0.08*math.sin(x*math.pi/2)*math.sin(y*math.pi/2)+0.05*noise
            elif finish=='leather':value=0.79+0.13*noise
            elif finish=='ceramic':value=0.56 if x<3 or y<3 else 0.94+0.025*noise
            elif finish=='concrete':value=0.79+0.13*noise+0.04*math.sin(u*math.tau*4)*math.cos(v*math.tau*3)
            else:value=0.9+0.06*noise
            heights.append(value)
    colors=[];normals=[];rough=[]
    for y in range(size):
        for x in range(size):
            h=heights[y*size+x]
            c=max(0,min(255,round(h*255)));colors.extend((c,c,c))
            dx=(heights[y*size+(x+1)%size]-heights[y*size+(x-1)%size])*0.6
            dy=(heights[((y+1)%size)*size+x]-heights[((y-1)%size)*size+x])*0.6
            length=math.sqrt(dx*dx+dy*dy+1)
            normals.extend((round(127.5*(1-dx/length)),round(127.5*(1-dy/length)),round(127.5*(1+1/length))))
            c=max(0,min(255,round((roughness+(h-0.85)*0.1)*255)));rough.extend((c,c,c))
    for kind,data in [('color',colors),('normal',normals),('roughness',rough)]:png(files[kind],data,size)
    return files
