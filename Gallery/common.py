"""Geometry shared by document renderers."""
def sheet(d,p,x,y,w,h,fold,part='page',fill=None):
    f=min(fold,w*.35)
    d.path(part+'-body',f'M {x} {y} H {x+w-f} L {x+w} {y+f} V {y+h} H {x} Z',fill=fill)
    d.path(part+'-fold',f'M {x+w-f} {y} V {y+f} H {x+w} Z',p['accent'],sw=p['stroke_width'])

def code_symbol(d,p,y,size,weight):
    cx=128; half=size/2; height=size*.5
    d.path('code-left',f'M {cx-half+height*.45} {y-height/2} L {cx-half} {y} L {cx-half+height*.45} {y+height/2}', 'none', p['accent'],weight,center=(cx-half,y))
    d.path('code-right',f'M {cx+half-height*.45} {y-height/2} L {cx+half} {y} L {cx+half-height*.45} {y+height/2}', 'none', p['accent'],weight,center=(cx+half,y))
    d.line('code-slash',cx+height*.18,y-height*.63,cx-height*.18,y+height*.63,p['accent'],weight)

