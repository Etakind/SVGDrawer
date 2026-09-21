"""Rectangle geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    w=p['shape_width'];h=p['shape_height'];d.rect('rectangle',(256-w)/2,(256-h)/2,w,h)
