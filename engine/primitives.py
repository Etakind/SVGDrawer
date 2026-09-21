"""Shared, dependency-free SVG primitives. Local design space: 256 x 256 units."""
from __future__ import annotations
import html
import math
import re

def num(value, default=0, lo=-100000, hi=100000):
    try:
        n = float(value)
        return min(hi, max(lo, n)) if math.isfinite(n) else default
    except (ValueError, TypeError):
        return default

def color(value, default="#193E5B"):
    v = str(value or "")
    return v if re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|none", v) else default

def fmt(n):
    return f"{float(n):.4f}".rstrip('0').rstrip('.') if isinstance(n, (int, float)) else str(n)

def attrs(d):
    return ' '.join(f'{k}="{html.escape(fmt(v), quote=True)}"' for k, v in d.items() if v is not None)

def tag(name, attributes, body=None):
    a = attrs(attributes)
    return f'<{name} {a}/>' if body is None else f'<{name} {a}>{body}</{name}>'

def override_attributes(a, o, center=(128, 128)):
    """Only a small, safe set of per-part changes can reach SVG attributes."""
    a = dict(a)
    if not isinstance(o, dict):
        return a
    for key in ('fill', 'stroke'):
        if key in o:
            a[key] = color(o[key], a.get(key, '#193E5B'))
    if 'stroke_width' in o:
        a['stroke-width'] = num(o['stroke_width'], 3, 0, 30)
    if o.get('hidden') is True:
        a['visibility'] = 'hidden'
    dx, dy = num(o.get('dx')), num(o.get('dy'))
    sx, sy = num(o.get('sx'), 1, .05, 4), num(o.get('sy'), 1, .05, 4)
    cx, cy = num(o.get('cx'), center[0], -4096, 4096), num(o.get('cy'), center[1], -4096, 4096)
    if dx or dy or sx != 1 or sy != 1:
        t = f'translate({fmt(dx)} {fmt(dy)}) translate({fmt(cx)} {fmt(cy)}) scale({fmt(sx)} {fmt(sy)}) translate({fmt(-cx)} {fmt(-cy)})'
        a['transform'] = str(a.get('transform', '')) + ' ' + t
    return a

class Drawing:
    def __init__(self, p, overrides=None):
        self.p = p
        self.parts = overrides or {}
        self.out = []

    def add(self, part, kind, a, body=None, center=(128, 128)):
        a = dict(a, **{'data-part': part, 'data-label': part.replace('-', ' ').title()})
        a = override_attributes(a, self.parts.get(part), center)
        self.out.append(tag(kind, a, body))

    def rect(self, part, x, y, w, h, fill=None, stroke=None, sw=None, rx=None, **extra):
        self.add(part, 'rect', dict(x=x, y=y, width=max(.01,w), height=max(.01,h),
            rx=self.p['radius'] if rx is None else rx, fill=self.p['fill'] if fill is None else fill,
            stroke=self.p['stroke'] if stroke is None else stroke,
            **{'stroke-width': self.p['stroke_width'] if sw is None else sw}, **extra), center=(x+w/2,y+h/2))

    def path(self, part, d, fill=None, stroke=None, sw=None, center=(128,128), **extra):
        self.add(part, 'path', dict(d=d, fill=self.p['fill'] if fill is None else fill,
            stroke=self.p['stroke'] if stroke is None else stroke,
            **{'stroke-width': self.p['stroke_width'] if sw is None else sw,
               'stroke-linecap': 'round', 'stroke-linejoin': 'round'}, **extra), center=center)

    def line(self, part, x1, y1, x2, y2, stroke=None, sw=None, **extra):
        self.add(part, 'line', dict(x1=x1, y1=y1, x2=x2, y2=y2,
            stroke=self.p['accent'] if stroke is None else stroke,
            **{'stroke-width': self.p['stroke_width'] if sw is None else sw, 'stroke-linecap':'round'}, **extra),
            center=((x1+x2)/2,(y1+y2)/2))

    def ellipse(self, part, cx, cy, rx, ry, fill=None, stroke=None, sw=None):
        self.add(part, 'ellipse', dict(cx=cx,cy=cy,rx=rx,ry=ry,
            fill=self.p['fill'] if fill is None else fill, stroke=self.p['stroke'] if stroke is None else stroke,
            **{'stroke-width': self.p['stroke_width'] if sw is None else sw}), center=(cx,cy))

    def label(self, part, x, y, content, size=32, fill=None, weight=600):
        self.add(part, 'text', dict(x=x, y=y, fill=self.p['highlight'] if fill is None else fill,
            **{'font-family':'Arial, Helvetica, sans-serif', 'font-size':size, 'font-weight':weight,
               'text-anchor':'middle'}), html.escape(str(content)), center=(x,y-size*.35))

    def svg(self):
        return ''.join(self.out)

