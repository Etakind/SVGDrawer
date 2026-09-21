"""One asset in, one SVG out. No scenes, coordinates, layers or drawing canvas."""
from __future__ import annotations
import importlib
import sys
import html
import re
from .gallery import Gallery, GalleryBusy, ROOT, COMMON
from .primitives import Drawing, color, num, fmt, tag
from .sanitize import safe_import

_GALLERY = None
RECIPE_FORMAT = 'svgdrawer.asset'
_GALLERY_STAMP = None


def gallery():
    global _GALLERY, _GALLERY_STAMP
    if (ROOT / 'Gallery/.write.lock').exists():
        raise GalleryBusy('Gallery is being updated. Retry shortly.')
    stamp = (ROOT / 'Gallery/catalog.json').stat().st_mtime_ns
    if _GALLERY is None or stamp != _GALLERY_STAMP:
        # Catalog publication is the revision signal shared by CLI and server.
        # Evict trusted source modules so an already-running UI sees replacements.
        for name in list(sys.modules):
            if name == 'Gallery' or name.startswith('Gallery.'):
                del sys.modules[name]
        importlib.invalidate_caches()
        _GALLERY = Gallery()
        _GALLERY_STAMP = stamp
    return _GALLERY


def clean_text(value, limit=100):
    return re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value))[:limit]


def normalize_parts(parts):
    if not isinstance(parts, dict):
        return {}
    if len(parts) > 3000:
        raise ValueError('A symbol can have at most 3,000 part overrides.')
    out = {}
    for key, value in parts.items():
        if not isinstance(key, str) or not re.fullmatch(r'[\w-]{1,120}', key) or not isinstance(value, dict):
            continue
        item = {}
        for k in ('fill', 'stroke'):
            if k in value:
                item[k] = color(value[k])
        for k, default, lo, hi in [('stroke_width', 3, 0, 30), ('sx', 1, .05, 4), ('sy', 1, .05, 4),
                                  ('cx', 128, -4096, 4096), ('cy', 128, -4096, 4096),
                                  ('dx', 0, -256, 256), ('dy', 0, -256, 256)]:
            if k in value:
                item[k] = num(value[k], default, lo, hi)
        if 'hidden' in value:
            item['hidden'] = value['hidden'] is True
        out[key] = item
    return out


def normalize_asset(asset, sanitize_source=False):
    if not isinstance(asset, dict):
        raise ValueError('asset must be an object.')
    kind = asset.get('type')
    cat = gallery()
    if kind not in cat.symbols and kind != 'custom':
        raise ValueError(f'Unknown symbol ID {str(kind)[:80]!r}. Its gallery definition may be missing.')
    raw = asset.get('params', {})
    raw = raw if isinstance(raw, dict) else {}
    p = dict(cat.symbols[kind]['defaults'] if kind != 'custom' else COMMON)
    for k in ('fill', 'accent', 'stroke', 'highlight'):
        p[k] = color(raw.get(k, p[k]), p[k])
    for key, hi in [('stroke_width', 20), ('radius', 48)]:
        p[key] = num(raw.get(key), p[key], 0, hi)
    for c in cat.symbols.get(kind, {}).get('controls', []):
        key = c['key']; value = raw.get(key, p.get(key, c['default']))
        if c['type'] == 'number':
            value = num(value, c['default'], c['min'], c['max'])
            # Counts and integer sliders should not silently disagree with the picture.
            step = c.get('step', 1)
            value = c['min'] + round((value-c['min']) / step) * step
            p[key] = round(min(c['max'], max(c['min'], value)), 8)
        elif c['type'] == 'boolean':
            p[key] = value is True
        elif c['type'] == 'select':
            p[key] = value if value in c['options'] else c['default']
        else:
            p[key] = clean_text(value, c.get('max_length', 80))
    result = {'type': kind, 'params': p, 'parts': normalize_parts(asset.get('parts', cat.symbols.get(kind, {}).get('parts', {})))}
    if kind == 'custom':
        source = asset.get('raw_svg', '')
        if not isinstance(source, str) or len(source) > 400000:
            raise ValueError('SVG imports must contain at most 400,000 characters.')
        # The source is sanitized for every render, including stored SVG sources.
        result['raw_svg'] = safe_import(source, prefix='') if sanitize_source else source
    return result


def normalize_options(options):
    o = options if isinstance(options, dict) else {}
    return dict(width=round(num(o.get('width'), 512, 16, 4096)),
                height=round(num(o.get('height'), 512, 16, 4096)),
                padding=num(o.get('padding'), 8, 0, 96),
                transparent=o.get('transparent', True) is not False,
                background=color(o.get('background'), '#FFFFFF'),
                preserve_aspect=o.get('preserve_aspect', True) is not False)


def render_asset(asset, options=None, clean=False):
    asset = normalize_asset(asset)
    spec = gallery().symbols.get(asset['type'], {})
    o = normalize_options({**spec.get('output', {}), **(options or {})})
    p = o['padding']; size = 256 + 2*p
    if asset['type'] == 'custom' or spec.get('kind') == 'svg':
        source = asset['raw_svg'] if asset['type'] == 'custom' else (gallery().symbol_path(asset['type']) / 'source.svg').read_text(encoding='utf-8')
        content = safe_import(source, prefix='asset', overrides=asset['parts'])
    else:
        drawing = Drawing(asset['params'], asset['parts'])
        gallery().builder(asset['type'])(drawing, asset['params'])
        content = drawing.svg()
    # A nested viewport keeps the optional background fully filled even for non-square exports.
    inner = tag('svg', {'x': 0, 'y': 0, 'width': o['width'], 'height': o['height'],
        'viewBox': f'{fmt(-p)} {fmt(-p)} {fmt(size)} {fmt(size)}',
        'preserveAspectRatio': 'xMidYMid meet' if o['preserve_aspect'] else 'none'}, content)
    background = '' if o['transparent'] else tag('rect', {'width': o['width'], 'height': o['height'], 'fill': o['background']})
    name = gallery().symbols.get(asset['type'], {}).get('name', 'Custom SVG')
    svg = tag('svg', {'xmlns': 'http://www.w3.org/2000/svg', 'width': o['width'], 'height': o['height'],
                     'viewBox': f'0 0 {o["width"]} {o["height"]}'},
              tag('title', {}, html.escape(name)) + background + inner)
    if clean:
        svg = re.sub(r'\sdata-(?:part|label)="[^"]*"', '', svg)
    return {'svg': svg, 'width': o['width'], 'height': o['height'], 'asset': asset, 'options': o}


def handle_request(payload):
    if not isinstance(payload, dict):
        raise ValueError('The request must be an object.')
    action = payload.get('action', 'render')
    if action == 'metadata':
        return gallery().metadata()
    if action in ('render', 'export'):
        return render_asset(payload.get('asset'), payload.get('options'), clean=action == 'export')
    if action == 'import_svg':
        source = payload.get('source')
        asset = normalize_asset({'type': 'custom', 'raw_svg': source}, sanitize_source=True)
        return render_asset(asset, {'width': 256, 'height': 256})
    if action == 'validate_recipe':
        recipe = payload.get('recipe')
        if not isinstance(recipe, dict) or recipe.get('format') not in (RECIPE_FORMAT, 'vector-foundry.asset') or recipe.get('schema_version') != 1:
            raise ValueError('Unsupported asset recipe. Expected format svgdrawer.asset, schema_version 1.')
        result = render_asset(normalize_asset(recipe.get('asset'), True), recipe.get('output'))
        return dict(format=RECIPE_FORMAT, schema_version=1, name=clean_text(recipe.get('name', 'Restored symbol'), 100),
                    asset=result['asset'], output=result['options'])
    raise ValueError(f'Unknown action {str(action)[:80]!r}.')
