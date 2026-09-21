"""Text label geometry. Stable part IDs are used by saved presets."""
import math
from Gallery.common import sheet, code_symbol

def render(d,p):
    size=p['font_size'];content=p['label'];lines=content.split('\n')[:4]
    # Fit long labels inside the icon box without depending on platform font metrics.
    size=min(size,224/max(1,max(map(len,lines)))*1.5,208/max(1,len(lines))/1.2)
    for i,s in enumerate(lines):d.label(f'text-{i+1}',128,128+(i-(len(lines)-1)/2)*size*1.2+size*.34,s,size,p['fill'],p['font_weight'])
