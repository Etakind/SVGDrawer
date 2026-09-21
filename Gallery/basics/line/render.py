"""Line geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    length=p['length'];dash={'solid':None,'dashed':'14 10','dotted':f'1 {p["line_width"]*2}'}[p['dash']]
    d.line('line',128-length/2,128,128+length/2,128,p['accent'],p['line_width'],**{'stroke-dasharray':dash})
