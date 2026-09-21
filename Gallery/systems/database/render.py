"""Database geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    w=p['diameter'];h=p['stack_height'];rx=w/2;ry=p['ellipse_depth']/2;x=128-rx;y=(256-h)/2; n=int(p['tiers']);step=(h-2*ry)/n
    for i in range(n):
        top=y+ry+i*step;bottom=top+step
        d.path(f'layer-{i+1}',f'M {x} {top} A {rx} {ry} 0 0 0 {x+w} {top} V {bottom} A {rx} {ry} 0 0 1 {x} {bottom} Z',p['fill'],p['stroke'],p['divider_width'],center=(128,(top+bottom)/2))
    d.ellipse('top-rim',128,y+ry,rx,ry,p['fill'],p['stroke'],p['divider_width'])
    d.ellipse('top-surface',128,y+ry,rx-8,max(3,ry-5),p['highlight'],'none',0)
