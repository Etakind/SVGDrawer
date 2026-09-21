"""Open folder geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    t=p['tab_width']
    d.path('folder-back',f'M 26 207 V 58 Q 26 49 35 49 H {26+t} L {42+t} 67 H 207 Q 215 67 215 76 V 207 Z',p['accent'])
    for i in range(int(p['papers'])):
        d.rect(f'paper-{i+1}',43+i*3,83+i*7,155-i*5,105,p['highlight'],p['accent'],2,2)
    top=213-p['flap_height']; tilt=p['opening']
    d.path('folder-front',f'M 28 213 L {28+tilt} {top} Q {30+tilt} {top-6} {37+tilt} {top-6} H 231 Q 238 {top-6} 235 {top+3} L 208 211 Q 207 215 202 215 H 33 Q 27 215 28 213 Z')
    d.line('folder-highlight',40+tilt,top+4,221,top+4,p['highlight'],2)
