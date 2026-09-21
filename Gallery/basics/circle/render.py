"""Circle geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    d.ellipse('circle',128,128,p['radius_x'],p['radius_y'])
