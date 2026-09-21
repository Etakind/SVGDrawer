"""Server racks geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    n=int(p['racks']);available=222;pitch=available/n;fw=pitch*.74;depth=min(p['depth'],pitch*.24);center=(n-1)/2
    order=sorted(range(n),key=lambda j:abs(j-center),reverse=True)
    for i in order:
        distance=abs(i-center)/max(1,center);h=182-distance*42;x=17+i*pitch;y=224-h
        d.path(f'rack-{i+1}-side',f'M {x+fw} {y} L {x+fw+depth} {y+7} V {y+h-7} L {x+fw} {y+h} Z',p['stroke'],p['stroke'],2)
        d.rect(f'rack-{i+1}-body',x,y,fw,h,p['fill'],p['highlight'],2,1)
        count=int(p['slots']);gap=(h-22)/count;bh=min(p['bay_height'],gap*.68)
        for j in range(count):
            by=y+10+j*gap
            d.rect(f'rack-{i+1}-bay-{j+1}',x+4,by,max(5,fw-8),bh,p['stroke'],'none',0,0)
            d.rect(f'rack-{i+1}-slot-{j+1}',x+6,by+bh*.25,max(3,fw-14),max(1,bh*.27),p['accent'],'none',0,0)
            for k in range(int(p['lights'])):
                d.ellipse(f'rack-{i+1}-light-{j+1}-{k+1}',x+fw-6-k*3,by+bh*.72,.85,.85,p['highlight'],'none',0)
        if p['arrows'] and (i in (0,n-1) or abs(i-center)<.6):
            xx=x+fw/2; yy=y-8
            d.line(f'rack-{i+1}-arrow-shaft',xx,max(10,yy-23),xx,yy-5,p['stroke'],3)
            d.path(f'rack-{i+1}-arrowhead',f'M {xx-5} {yy-8} L {xx} {yy} L {xx+5} {yy-8} Z',p['stroke'],'none',0)
