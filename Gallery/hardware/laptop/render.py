"""Laptop geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    w=p['screen_width'];h=p['screen_height'];b=p['bezel'];base=p['base_depth'];x=(256-w)/2;y=(256-h-base)/2
    d.rect('display-bezel',x,y,w,h,p['stroke'],p['stroke'],2,4)
    d.rect('screen',x+b,y+b,w-2*b,h-2*b,p['fill'],'none',0,0)
    d.path('screen-reflection',f'M {x+b} {y+b} H {x+w-b} V {y+14+b} Z',p['highlight'],'none',0)
    d.path('base',f'M {x} {y+h} H {x+w} L {x+w+15} {y+h+base-5} L {x+w+10} {y+h+base} H {x-10} L {x-15} {y+h+base-5} Z',p['highlight'],p['stroke'],4)
    for i in range(int(p['key_rows'])):
        yy=y+h+5+i*max(2,(base-14)/max(1,int(p['key_rows'])))
        d.line(f'keyboard-row-{i+1}',x+18,yy,x+w-18,yy,p['accent'],2)
    d.rect('trackpad',106,y+h+base-10,44,5,p['stroke'],'none',0,2)
