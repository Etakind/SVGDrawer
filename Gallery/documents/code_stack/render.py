"""Code bundle geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    n=int(p['pages'])
    for i in range(n-1,0,-1):
        d.rect(f'back-sheet-{i}',53-i*11,40-i*10,158,187,p['fill'],rx=4)
    sheet(d,p,53,40,158,187,p['fold'])
    code_symbol(d,p,144,p['code_size'],p['code_weight'])
