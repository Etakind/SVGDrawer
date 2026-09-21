"""Settings gear geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    n=int(p['teeth']);r=p['outer_radius'];root=r-p['tooth_depth'];hole=min(p['hole_radius'],root-7); pts=[]
    for i in range(n):
        for offset,rr in [(0,root),(.2,root),(.25,r),(.65,r),(.7,root)]:
            a=(i+offset)/n*math.tau-math.pi/2;pts.append((128+rr*math.cos(a),128+rr*math.sin(a)))
    path='M '+' L '.join(f'{x:.4f} {y:.4f}' for x,y in pts)+' Z '
    path+=f'M {128+hole} 128 A {hole} {hole} 0 1 0 {128-hole} 128 A {hole} {hole} 0 1 0 {128+hole} 128 Z'
    d.path('gear-body',path,p['fill'],p['stroke'],p['stroke_width'],**{'fill-rule':'evenodd'})
