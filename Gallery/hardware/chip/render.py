"""AI chip geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    n=int(p['pins']); length=p['pin_length']; width=p['pin_width']
    for i in range(n):
        t=68+i*120/max(1,n-1)
        for side,x,y,w,h in [('top',t-width/2,48-length,width,length+5),('bottom',t-width/2,203,width,length+5),
                             ('left',48-length,t-width/2,length+5,width),('right',203,t-width/2,length+5,width)]:
            d.rect(f'pin-{side}-{i+1}',x,y,w,h,p['stroke'],'none',0,2)
    d.rect('chip-body',46,46,164,164,p['stroke'],'none',0,12)
    d.rect('chip-face',56,56,144,144,p['fill'],p['accent'],3,6)
    s=p['core_size']; a=(256-s)/2
    d.rect('core',a,a,s,s,p['fill'],p['highlight'],3,1)
    d.label('core-label',128,128+p['font_size']*.34,p['label'],p['font_size'])
