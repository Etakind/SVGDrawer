"""Stacked pages geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    n=int(p['pages']); offset=10; x=38+(n-1)*offset/2; y=24+(n-1)*offset/2; w=174-(n-1)*offset/2; h=206-(n-1)*offset/2
    for i in range(n-1,0,-1):
        d.rect(f'back-sheet-{i}',x-i*offset,y-i*offset,w,h,p['accent'],rx=2)
    sheet(d,p,x,y,w,h,p['fold'])
    nlines=int(p['lines']); gap=min(p['line_gap'],(h-80)/max(1,nlines-1))
    for i in range(nlines):
        length=min(p['line_length'],w-32)*(0.58 if i==0 else 1)
        d.line(f'text-line-{i+1}',x+18,y+54+i*gap,x+18+length,y+54+i*gap,p['stroke'],p['line_width'])
