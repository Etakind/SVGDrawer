"""Organization chart geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    if p['frame']: d.rect('frame',15,37,226,182,p['highlight'],p['stroke'],4,5)
    b=int(p['branches']);levels=int(p['levels']);h=p['node_height'];ys=[82+i*(109/(levels-1)) for i in range(levels)]
    rows=[]
    for level in range(levels):
        count=b**level;step=204/count;w=min(p['node_width'],step*.76)
        rows.append([(26+(j+.5)*step,ys[level],w) for j in range(count)])
    for level in range(levels-1):
        for j,(x,y,w) in enumerate(rows[level]):
            children=rows[level+1][j*b:(j+1)*b];mid=(y+ys[level+1])/2
            d.line(f'connector-{level}-{j}-stem',x,y+h/2,x,mid,p['stroke'],p['connector_width'])
            d.line(f'connector-{level}-{j}-cross',children[0][0],mid,children[-1][0],mid,p['stroke'],p['connector_width'])
            for k,(cx,cy,cw) in enumerate(children):d.line(f'connector-{level}-{j}-{k}',cx,mid,cx,cy-h/2,p['stroke'],p['connector_width'])
    for i,row in enumerate(rows):
        for j,(x,y,w) in enumerate(row):d.rect(f'node-{i+1}-{j+1}',x-w/2,y-h/2,w,h,p['fill'],p['stroke'],3,2)
