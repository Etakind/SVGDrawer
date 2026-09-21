"""Code page geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    sheet(d,p,43,22,170,212,p['fold'])
    d.line('header',66,90,66+p['header_length'],90,p['accent'],p['header_width'])
    code_symbol(d,p,156,p['code_size'],p['code_weight'])
