"""Arrow geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    length=p['length'];x=(256-length)/2;end=x+length;head=min(p['head_length'],length*.65);s=p['shaft_width']/2;h=p['head_width']/2
    d.path('arrow',f'M {x} {128-s} H {end-head} V {128-h} L {end} 128 L {end-head} {128+h} V {128+s} H {x} Z',p['accent'],p['stroke'])
