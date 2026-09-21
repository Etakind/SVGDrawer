"""Waveform geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    w=p['screen_width'];h=p['screen_height'];x=(256-w)/2;y=(256-h)/2;px=x+9;py=y+9;pw=w-18;ph=h-18
    if p['frame']:d.rect('display-frame',x-2,y-2,w+4,h+4,p['highlight'],p['stroke'],3,7)
    d.rect('screen',x+2,y+2,w-4,h-4,p['fill'],'none',0,4)
    if p['grid']:
        for i in range(1,12):d.line(f'grid-vertical-{i}',px+i*pw/12,py,px+i*pw/12,py+ph,p['highlight'],.6,opacity=.3)
        for i in range(1,6):d.line(f'grid-horizontal-{i}',px,py+i*ph/6,px+pw,py+i*ph/6,p['highlight'],.6,opacity=.3)
    amp=min(p['amplitude'],ph-10)/2;n=int(p['cycles']);mid=128;step=pw/n;duty=p['duty']/100;kind=p['wave_type']
    if kind=='digital':
        path=f'M {px} {mid+amp}'
        for i in range(n):
            a=px+i*step;rise=a+step*(1-duty)/2;fall=rise+step*duty
            path+=f' H {rise} V {mid-amp} H {fall} V {mid+amp} H {a+step}'
    else:
        pts=[]
        for i in range(n*64+1):
            t=i/(n*64);phase=t*n
            if kind=='sine':value=math.sin(phase*math.tau)
            elif kind=='triangle':value=1-4*abs((phase+.25)%1-.5)
            else:value=2*(phase%1)-1
            pts.append((px+t*pw,mid-amp*value))
        path='M '+' L '.join(f'{xx:.3f} {yy:.3f}' for xx,yy in pts)
    d.path('signal-trace',path,'none',p['accent'],p['trace_width'])
