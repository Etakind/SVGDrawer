"""User profile geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    r=p['head_radius']; h=p['body_height'];gap=p['head_gap'];top=(256-(r*2+gap+h))/2;bottom=top+r*2+gap+h;w=p['shoulder_width'];y=top+2*r+gap
    d.ellipse('head',128,top+r,r,r,p['fill'],'none',0)
    d.path('shoulders',f'M {128-w/2} {bottom} V {y+h*.65} C {128-w/2} {y-h*.14} {128+w/2} {y-h*.14} {128+w/2} {y+h*.65} V {bottom} Z',p['fill'],'none',0,center=(128,(y+bottom)/2))
