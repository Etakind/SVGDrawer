"""Sanitize imported SVG before it is displayed or exported. No raster images or external resources."""
import html
import math
import re
import xml.etree.ElementTree as ET
from .primitives import num, tag, override_attributes

SAFE_TAGS = {'svg','g','defs','path','rect','circle','ellipse','line','polyline','polygon','text','tspan',
             'linearGradient','radialGradient','stop','clipPath','title','desc','use'}
SAFE_ATTRS = {'id','x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','width','height','viewBox',
    'preserveAspectRatio','d','points','fill','stroke','stroke-width','stroke-linecap','stroke-linejoin',
    'stroke-miterlimit','stroke-dasharray','stroke-dashoffset','fill-opacity','stroke-opacity','opacity',
    'fill-rule','clip-rule','clip-path','transform','gradientTransform','gradientUnits','offset',
    'stop-color','stop-opacity','spreadMethod','fx','fy','fr','font-size','font-family','font-weight',
    'font-style','text-anchor','dominant-baseline','dx','dy','letter-spacing','href','visibility'}
SAFE_STYLE = {'fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-dasharray',
    'fill-opacity','stroke-opacity','opacity','fill-rule','clip-rule','clip-path','stop-color',
    'stop-opacity','font-size','font-family','font-weight','font-style','text-anchor','visibility'}
DRAWABLE = {'path','rect','circle','ellipse','line','polyline','polygon','text','use'}


def safe_import(source, prefix='import', overrides=None):
    if not isinstance(source,str) or len(source)>400000:
        raise ValueError('SVG imports must be text files smaller than 400 KB.')
    if re.search(r'<!DOCTYPE|<!ENTITY',source,re.I):
        raise ValueError('SVG imports cannot contain DOCTYPE or ENTITY declarations.')
    try: root=ET.fromstring(source)
    except ET.ParseError as exc: raise ValueError('This file is not valid SVG XML.') from exc
    if root.tag.split('}')[-1]!='svg': raise ValueError('The file must have an SVG root element.')
    if sum(1 for _ in root.iter())>3000:raise ValueError('SVG import is limited to 3,000 elements.')
    # Reject recursive <use> references before a browser or rasterizer sees them.
    ids = {el.attrib.get('id'): el for el in root.iter() if el.attrib.get('id')}
    ref_visits = [0]
    def check_refs(el, visiting, depth=0):
        if depth > 40:
            raise ValueError('SVG reference nesting exceeds 40 levels.')
        for child in el.iter():
            if child.tag.split('}')[-1] == 'use':
                ref_visits[0] += 1
                if ref_visits[0] > 10000:
                    raise ValueError('SVG use references expand beyond the safety limit.')
                ref = child.attrib.get('href', child.attrib.get('{http://www.w3.org/1999/xlink}href', ''))
                if ref.startswith('#') and ref[1:] in ids:
                    target = ref[1:]
                    if target in visiting:
                        raise ValueError('SVG contains a circular use reference.')
                    check_refs(ids[target], visiting | {target}, depth + 1)
    check_refs(root, set())
    prefix=(re.sub(r'[^a-zA-Z0-9_-]','',str(prefix))[:80]+'-') if prefix else ''
    counter=[0];overrides=overrides or {}
    def clean(el,depth=0,in_defs=False):
        name=el.tag.split('}')[-1]
        if name not in SAFE_TAGS or depth>40:return ''
        a={}
        originals=dict(el.attrib)
        style=originals.pop('style','')
        for rule in style.split(';'):
            if ':' in rule:
                k,v=rule.split(':',1)
                if k.strip() in SAFE_STYLE:originals[k.strip()]=v.strip()
        for key,value in originals.items():
            key=key.split('}')[-1]
            if key not in SAFE_ATTRS:continue
            value=str(value)
            if '\\' in value:continue  # Reject obfuscated CSS URLs / escapes.
            if len(value)>250000:continue
            if re.search(r'javascript:|data:|https?:|file:|@import|expression\s*\(',value,re.I):continue
            if 'url' in value.lower():
                if not re.fullmatch(r'url\(\s*[\'\"]?#[a-zA-Z_][\w:.-]*[\'\"]?\s*\)',value):continue
                target=re.search(r'#([\w:.-]+)',value).group(1);value=f'url(#{prefix}{target})'
            if key=='href':
                if not re.fullmatch(r'#[a-zA-Z_][\w:.-]*',value):continue
                value='#'+prefix+value[1:]
            if key=='id':value=prefix+value
            a[key]=value
        if depth==0:
            if 'viewBox' not in a:
                w=num(re.sub('[^0-9.]','',a.get('width','256')),256,1,100000)
                h=num(re.sub('[^0-9.]','',a.get('height','256')),256,1,100000)
                a['viewBox']=f'0 0 {w} {h}'
            vb=a['viewBox'].replace(',',' ').split()
            try:
                values = [float(v) for v in vb]
                valid = len(values) == 4 and all(math.isfinite(v) and abs(v) <= 100000 for v in values) and values[2] > 0 and values[3] > 0
            except ValueError:
                valid = False
            if not valid: raise ValueError('SVG viewBox must have four finite values and positive width and height.')
            a.update(x=0,y=0,width=256,height=256,preserveAspectRatio='xMidYMid meet')
            a.setdefault('fill', '#000000')
        inside=in_defs or name in ('defs','clipPath','linearGradient','radialGradient')
        if name in DRAWABLE and not inside:
            counter[0]+=1;part=f'imported-part-{counter[0]}'
            a.update({'data-part':part,'data-label':f'{name.title()} {counter[0]}'})
            a=override_attributes(a,overrides.get(part))
        children=''.join(clean(c,depth+1,inside)+html.escape(c.tail or '') for c in el)
        body=html.escape(el.text or '')+children
        return tag(name,a,body)
    return clean(root)

