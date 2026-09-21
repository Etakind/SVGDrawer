"""Strict CLI parameter validation. Unlike sliders, mistakes are not silently clamped."""
from __future__ import annotations
import math
import re
import xml.etree.ElementTree as ET
from .common import UserError, json_input, json_value

COLOR_ROLES = ('fill', 'accent', 'stroke', 'highlight')
COMMON_CONTROLS = [
    *[{'key': key, 'label': key.title(), 'type': 'color'} for key in COLOR_ROLES],
    {'key': 'stroke_width', 'label': 'Stroke width', 'type': 'number', 'min': 0, 'max': 20},
    {'key': 'radius', 'label': 'Corner radius', 'type': 'number', 'min': 0, 'max': 48},
]


def hex_color(value, none=True):
    if not isinstance(value, str):
        raise UserError('Colors must be strings, for example "012345" or "#427ABC".')
    value = value.strip()
    if none and value.lower() == 'none':
        return 'none'
    value = value[1:] if value.startswith('#') else value
    if not re.fullmatch(r'(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})', value):
        raise UserError(f'Invalid hex color: {value!r}. Expected 3 or 6 hex digits, with an optional #.')
    if len(value) == 3:
        value = ''.join(c * 2 for c in value)
    return '#' + value.upper()


def color_set(value, gal):
    if value is None:
        return {}
    value = value.strip()
    if value.lower() == 'default':
        return {}
    if value.startswith('[') or value.startswith('@'):
        values = json_input(value, '--color-sets', list)
        if not 1 <= len(values) <= 4:
            raise UserError('--color-sets takes 1–4 hex strings, in fill/accent/stroke/highlight order.')
        return {key: hex_color(v, none=False) for key, v in zip(COLOR_ROLES, values)}
    matches = [p for p in gal.palettes if value.lower() in (p['name'].lower(), p.get('id', '').lower())]
    if not matches:
        raise UserError(f'Unknown color set {value!r}. Run --list-color-sets, or pass a JSON array.')
    return {k: hex_color(matches[0][k]) for k in COLOR_ROLES}


def validate_params(values, spec):
    controls = {c['key']: c for c in COMMON_CONTROLS + spec.get('controls', [])}
    result = {}
    for key, value in values.items():
        if key not in controls:
            raise UserError(f'Unknown parameter {key!r} for {spec["id"]}. Run --describe {spec["id"]} --json.')
        c = controls[key]
        typ = c['type']
        if typ == 'color':
            value = hex_color(value)
        elif typ == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise UserError(f'{key} must be a finite number.')
            if not c['min'] <= value <= c['max']:
                raise UserError(f'{key} must be between {c["min"]} and {c["max"]}; got {value}.')
            if 'step' in c:
                ticks = (value - c['min']) / c['step']
                if abs(ticks - round(ticks)) > 1e-7:
                    raise UserError(f'{key} must advance by step {c["step"]} from {c["min"]}.')
        elif typ == 'select':
            if value not in c['options']:
                raise UserError(f'{key} must be one of {c["options"]}.')
        elif typ == 'boolean':
            if not isinstance(value, bool):
                raise UserError(f'{key} must be true or false, not a string or number.')
        elif typ == 'text':
            if not isinstance(value, str) or len(value) > c.get('max_length', 80):
                raise UserError(f'{key} must be text of at most {c.get("max_length", 80)} characters.')
            if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', value):
                raise UserError(f'{key} contains unsupported control characters.')
        result[key] = value
    return result


def overrides(args, spec, gal, base=None):
    values = dict(base or {})
    # Explicit default restores the symbol's original four colors, including recipes.
    if args.color_sets and args.color_sets.lower() == 'default':
        values.update({k: spec['defaults'][k] for k in COLOR_ROLES})
    else:
        values.update(color_set(args.color_sets, gal))
    values.update(json_input(args.params, '--params', dict) or {})
    for pair in args.set_values:
        if '=' not in pair:
            raise UserError('--set requires KEY=VALUE, for example --set pins=10.')
        key, value = pair.split('=', 1)
        key = key.strip()
        # Text controls stay strings, so labels such as 0123 keep their leading zeroes.
        c = next((c for c in spec.get('controls', []) if c['key'] == key), None)
        if key in COLOR_ROLES or (c and c['type'] in ('text', 'select')):
            parsed = value
        else:
            try:
                parsed = json_value(value, key)
            except UserError:
                parsed = value
        values[key] = parsed
    return validate_params(values, spec)


def svg_parts(svg):
    root = check_svg(svg)
    parts, ids = [], set()
    for el in root.iter():
        ident = el.attrib.get('data-part')
        if ident:
            if ident in ids or not re.fullmatch(r'[\w-]{1,120}', ident):
                raise UserError(f'Duplicate or invalid part ID: {ident}', 'renderer_invalid', 4)
            ids.add(ident)
            parts.append({'id': ident, 'shape': el.tag.rsplit('}', 1)[-1],
                          'label': el.attrib.get('data-label', ident),
                          'attributes': {k: v for k, v in el.attrib.items() if not k.startswith('data-')}})
    return parts


def check_svg(svg):
    if len(svg) > 4_000_000 or '<!DOCTYPE' in svg.upper() or '<!ENTITY' in svg.upper():
        raise UserError('SVG output is too large or contains a document/entity declaration.', 'renderer_invalid', 4)
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise UserError(f'Renderer produced invalid SVG: {exc}', 'renderer_invalid', 4) from exc
    if root.tag.rsplit('}', 1)[-1] != 'svg':
        raise UserError('Renderer output must be SVG.', 'renderer_invalid', 4)
    graphical = 0
    for el in root.iter():
        tag = el.tag.rsplit('}', 1)[-1]
        if tag.lower() in ('script', 'foreignobject', 'iframe', 'image', 'animate', 'set'):
            raise UserError(f'Unsupported non-static SVG tag: {tag}', 'renderer_invalid', 4)
        graphical += tag in ('rect', 'path', 'circle', 'ellipse', 'text', 'line', 'polyline', 'polygon', 'use')
        for k, v in el.attrib.items():
            if k.lower().startswith('on') or (k.rsplit('}', 1)[-1] == 'href' and not v.startswith('#')):
                raise UserError('SVG contains an event handler or external reference.', 'renderer_invalid', 4)
            if re.search(r'url\(\s*["\']?(?!#)', v) and 'url(' in v:
                # Only local fragment paint references are portable in both runtimes.
                if not re.fullmatch(r'url\(\s*["\']?#[\w-]+["\']?\s*\)', v):
                    raise UserError('Only local SVG paint references are supported.', 'renderer_invalid', 4)
            if k in ('x', 'y', 'width', 'height', 'cx', 'cy', 'rx', 'ry', 'stroke-width') and v.lower() in ('nan','inf','infinity','-inf'):
                raise UserError(f'Non-finite SVG attribute: {k}', 'renderer_invalid', 4)
    if not graphical:
        raise UserError('Renderer produced no visible SVG geometry.', 'renderer_invalid', 4)
    return root


def validate_parts(values, available):
    if not isinstance(values, dict):
        raise UserError('--parts must be a JSON object keyed by part ID.')
    ids = {p['id'] for p in available}
    result = {}
    ranges = {'stroke_width': (0, 30), 'sx': (.05, 4), 'sy': (.05, 4),
              'cx': (-4096, 4096), 'cy': (-4096, 4096), 'dx': (-256, 256), 'dy': (-256, 256)}
    for ident, fields in values.items():
        if ident not in ids:
            raise UserError(f'Unknown part {ident!r} for the chosen geometry. Run --list-parts with the same --set options.')
        if not isinstance(fields, dict):
            raise UserError(f'Part {ident}: overrides must be an object.')
        clean = {}
        for key, value in fields.items():
            if key in ('fill', 'stroke'):
                clean[key] = hex_color(value)
            elif key == 'hidden':
                if not isinstance(value, bool):
                    raise UserError(f'{ident}.hidden must be true or false.')
                clean[key] = value
            elif key in ranges:
                lo, hi = ranges[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
                    raise UserError(f'{ident}.{key} must be a number between {lo} and {hi}.')
                clean[key] = value
            else:
                raise UserError(f'Unsupported part property: {ident}.{key}')
        result[ident] = clean
    return result
