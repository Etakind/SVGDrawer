"""Sync arrows geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    n=int(p['arrows']); sign=1 if p['clockwise'] else -1; r=p['ring_radius']; sweep=360/n*p['sweep']/100
    for i in range(n):
        start=-90+i*360/n; end=start+sign*sweep
        a,b=math.radians(start),math.radians(end)
        x1,y1=128+r*math.cos(a),128+r*math.sin(a); x2,y2=128+r*math.cos(b),128+r*math.sin(b)
        d.path(f'arc-{i+1}',f'M {x1} {y1} A {r} {r} 0 {int(sweep>180)} {int(sign>0)} {x2} {y2}','none',p['accent'],p['arrow_weight'])
        tx,ty=-math.sin(b)*sign,math.cos(b)*sign; nx,ny=-ty,tx; h=p['head_size']; base_x=x2-tx*h*.62; base_y=y2-ty*h*.62
        pts=[(x2+tx*h*.27,y2+ty*h*.27),(base_x+nx*h*.42,base_y+ny*h*.42),(base_x-nx*h*.42,base_y-ny*h*.42)]
        d.path(f'arrowhead-{i+1}','M '+' L '.join(f'{x} {y}' for x,y in pts)+' Z',p['accent'],'none',0,center=(x2,y2))
