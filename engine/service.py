"""One asset in, one SVG out. No scenes, coordinates, layers or drawing canvas."""
from __future__ import annotations
import copy
import html
import json
import math
import re
import xml.etree.ElementTree as ET
from .gallery import Gallery, COMMON, require_id, RESERVED_CATEGORIES
from .primitives import Drawing, color, num, fmt, tag
from .sanitize import safe_import

_GALLERY = None
LIBRARY_FORMAT = 'svgdrawer.library'
RECIPE_FORMAT = 'svgdrawer.asset'
MAX_SYMBOLS = 1000
MAX_CATEGORIES = 100


def gallery():
    global _GALLERY
    if _GALLERY is None:
        _GALLERY = Gallery()
    return _GALLERY


def clean_text(value, limit=100):
    return re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value))[:limit]


def normalize_parts(parts):
    if not isinstance(parts, dict):
        return {}
    if len(parts) > 3000:
        raise ValueError('An symbol can have at most 3,000 part overrides.')
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
    result = {'type': kind, 'params': p, 'parts': normalize_parts(asset.get('parts', {}))}
    if kind == 'custom':
        source = asset.get('raw_svg', '')
        if not isinstance(source, str) or len(source) > 400000:
            raise ValueError('SVG imports must contain at most 400,000 characters.')
        # The source is sanitized for every render, even after library validation.
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
    o = normalize_options(options)
    p = o['padding']; size = 256 + 2*p
    if asset['type'] == 'custom':
        content = safe_import(asset['raw_svg'], prefix='asset', overrides=asset['parts'])
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


def validate_library(library):
    if not isinstance(library, dict) or library.get('format') not in (LIBRARY_FORMAT, 'vector-foundry.library') or library.get('schema_version') not in (1, 2):
        raise ValueError('Expected a SVGDrawer library backup with schema_version 1 or 2. Canvas projects are not library backups.')
    if len(json.dumps(library, ensure_ascii=False).encode('utf-8')) > 10_000_000:
        raise ValueError('A library backup may not exceed 10 MB.')
    cats = library.get('categories', [])
    # Convert the collection field, never the asset recipes or stable symbol IDs.
    field = 'elements' if library['schema_version'] == 1 else 'symbols'
    if field not in library:
        raise ValueError(f'Library schema {library["schema_version"]} requires {field}.')
    items = library[field]
    favs = library.get('favorites', [])
    if not isinstance(cats, list) or len(cats) > MAX_CATEGORIES:
        raise ValueError(f'A library may contain at most {MAX_CATEGORIES} custom categories.')
    if not isinstance(items, list) or len(items) > MAX_SYMBOLS:
        raise ValueError(f'A library may contain at most {MAX_SYMBOLS} custom symbols.')
    builtin_cats = {c['id'] for c in gallery().categories}
    category_ids = set(builtin_cats)
    clean_cats, clean_items = [], []
    for c in cats:
        if not isinstance(c, dict):
            raise ValueError('A category must be an object.')
        ident = require_id(c.get('id'), 'Custom category ID')
        name = clean_text(c.get('name', ''), 60).strip()
        if not name or ident in category_ids or ident in RESERVED_CATEGORIES:
            raise ValueError(f'Duplicate/reserved category ID or empty category name: {ident}.')
        category_ids.add(ident)
        clean_cats.append(dict(id=ident, name=name, description=clean_text(c.get('description', ''), 240), icon='folder', order=1000+len(clean_cats)))
    item_ids = set(gallery().symbols)
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('A custom symbol must be an object.')
        ident = require_id(item.get('id'), 'Custom symbol ID')
        name = clean_text(item.get('name', ''), 100).strip()
        if not name or ident in item_ids:
            raise ValueError(f'Duplicate symbol ID or empty name: {ident}.')
        item_ids.add(ident)
        category = item.get('category')
        if category not in category_ids:
            raise ValueError(f'{name}: unknown category {category!r}.')
        tags = item.get('tags', [])
        if not isinstance(tags, list):
            raise ValueError(f'{name}: tags must be an array.')
        asset = normalize_asset(item.get('asset'), sanitize_source=True)
        # Validate that the geometry is renderable, not just that the JSON parses.
        render_asset(asset, {'width': 256, 'height': 256})
        clean_items.append(dict(id=ident, name=name, category=category,
            description=clean_text(item.get('description', ''), 300), tags=[clean_text(t, 40) for t in tags[:20]],
            asset=asset, output=normalize_options(item.get('output')), created_at=clean_text(item.get('created_at', ''), 40)))
    clean_favs = list(dict.fromkeys(x for x in favs if isinstance(x, str) and x in item_ids)) if isinstance(favs, list) else []
    return dict(format=LIBRARY_FORMAT, schema_version=2, categories=clean_cats, symbols=clean_items, favorites=clean_favs)


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
    if action == 'validate_library':
        return validate_library(payload.get('library'))
    if action == 'validate_recipe':
        recipe = payload.get('recipe')
        if not isinstance(recipe, dict) or recipe.get('format') not in (RECIPE_FORMAT, 'vector-foundry.asset') or recipe.get('schema_version') != 1:
            raise ValueError('Unsupported asset recipe. Expected format svgdrawer.asset, schema_version 1.')
        result = render_asset(normalize_asset(recipe.get('asset'), True), recipe.get('output'))
        return dict(format=RECIPE_FORMAT, schema_version=1, name=clean_text(recipe.get('name', 'Restored symbol'), 100),
                    asset=result['asset'], output=result['options'])
    raise ValueError(f'Unknown action {str(action)[:80]!r}.')
