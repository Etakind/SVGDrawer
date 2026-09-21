"""Analytics page geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    d.rect('page-body',37,20,182,216,rx=5)
    n=int(p['lines'])
    for i in range(n):
        l=p['line_length']*(1-.14*i)
        d.line(f'text-line-{i+1}',66,58+i*min(17,55/max(1,n-1)),66+l,58+i*min(17,55/max(1,n-1)),p['accent'],p['line_width'])
    n=int(p['bars']); bw=min(p['bar_width'],130/n*.72); gap=(132-bw*n)/max(1,n-1) if n>1 else 0; total=bw*n+gap*(n-1); start=128-total/2
    for i in range(n):
        h=p['bar_height']*(.3+.7*(i/max(1,n-1)))
        d.rect(f'bar-{i+1}',start+i*(bw+gap),210-h,bw,h,p['accent'],'none',0,0)
